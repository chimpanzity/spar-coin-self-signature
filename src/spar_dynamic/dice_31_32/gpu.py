"""GPU stage for Experiments 31 and 32 (one model per process; run on the rented GPU).

Serving is Experiment 27-30's engine (`dice_crossed_guidance.models`), unchanged: bf16 weights and activations, fp32 output layer
and logits, batch 1, the prompt prefilled once and every further token fed one at a time through the KV cache, full-vocabulary
log-softmax, greedy argmax, no sampling, no logit processors. That is the arithmetic of greedy generation and of Experiment 28's
`incremental` matched-prefix scoring; `full_pass` (one forward pass over prompt + forced tokens) is the numerical floor only.

`run --model M` does, in order, stopping at the first failure:
  1. preflight: vocabulary scan (no whitespace/multi-digit face variants), archival G and F (Experiment 28 prompts) x2, checked
     on the host against Experiment 28's raw records (identical output, six-face |dp| <= 0.01, bit-identical repeats);
  2. Experiment 31: 8 teacher-forced streams for this scorer (2 scorer instructions x 4 source trajectories), incremental x2 and
     full_pass x1 -> <EXP31>/raw/<M>/streams.jsonl;
  3. Experiment 32: 6 prediction prompts, free greedy generation x2 plus scored readouts (first answer token; for A, roll 7
     after the generated sixth and separator, and a separately labelled constrained readout after the top first face and the
     separator), incremental x2 and full_pass x1 -> <EXP32>/raw/<M>/cells.jsonl.
Raw files are written once (never appended to after a completed run). Usage:
  python -m spar_dynamic.dice_31_32.gpu run --model {qwen,mistral} [--root31 DIR --root32 DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
import time
from pathlib import Path

from spar_dynamic.dice_31_32 import config as C
from spar_dynamic.dice_31_32 import stimuli as S

PKG = Path(__file__).resolve().parent
LN2 = 0.6931471805599453


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical_sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def guard_out(out_dir):
    for part in os.path.abspath(str(out_dir)).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= C.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def code_sha() -> dict:
    files = sorted(PKG.glob("*.py")) + [PKG.parent / "dice_crossed_guidance" / "models.py", PKG.parent / "dice_crossed_guidance" / "config.py",
                                        PKG.parent / "dice_logprob_crossmodel" / "gpu.py", PKG.parent / "dice_logprob" / "prompts.py",
                                        PKG.parent / "dice_logprob" / "gpu_runner.py"]
    return {f"{p.parent.name}/{p.name}": canonical_sha(p) for p in files}


def write_jsonl(path, rows):
    path = Path(path)
    if path.exists():
        raise SystemExit(f"{path} exists; raw files are written once")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


# ---------- scoring ----------

def detail(eng, lp) -> dict:
    """Everything stored about one next-token distribution (lp: full-vocabulary log-softmax, fp32)."""
    import torch
    top = torch.topk(lp, C.TOP_N)
    sep = C.SEPARATOR_ID[eng.key]
    arg = int(top.indices[0])
    return dict(face_logprobs={str(f): float(lp[i]) for f, i in eng.face_ids.items()},
                face_token_ids={str(f): int(i) for f, i in eng.face_ids.items()},
                separator_logprob=float(lp[sep]), eos_logprobs={str(e): float(lp[e]) for e in sorted(eng.eos)},
                argmax_token_id=arg, argmax_token=eng.decode([arg]), argmax_logprob=float(lp[arg]),
                entropy_bits=float(-(lp.exp() * lp).sum() / LN2),
                top=[[int(i), eng.decode([int(i)]), float(v)] for v, i in zip(top.values.tolist(), top.indices.tolist())])


def forced_dists(eng, prompt, forced, method, at=None) -> list:
    """Next-token distributions after prompt + forced[:k] for k in `at` (default: every k = 0..len(forced)).

    incremental: prompt prefilled once, then forced tokens one at a time through the KV cache (generation arithmetic; primary).
    full_pass:   one forward pass over prompt + forced (numerical floor only)."""
    import torch
    pre = eng.prompt_ids(prompt)
    at = list(range(len(forced) + 1)) if at is None else list(at)
    out_rows = {}
    with torch.no_grad():
        if method == "incremental":
            out = eng._fwd(pre)
            for k in range(len(forced) + 1):
                if k in at:
                    out_rows[k] = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
                if k < len(forced):
                    out = eng._fwd([forced[k]], out.past_key_values)
        else:
            lp = torch.log_softmax(eng.model(input_ids=torch.tensor([pre + list(forced)], device=eng.device)).logits[0].float(), dim=-1)
            for k in at:
                out_rows[k] = lp[len(pre) + k - 1]
    return [dict(n_forced=k, forced_ids=list(forced[:k]), **detail(eng, out_rows[k])) for k in at]


def history_ids(eng, faces) -> list:
    """The scorer's tokenisation of `d d d ...` (Experiment 28 rendering), asserted to be face, separator, face, ..."""
    ids = eng.hist_ids(S.seq(faces))
    want = []
    for n, f in enumerate(faces):
        want += ([C.SEPARATOR_ID[eng.key]] if n else []) + [eng.face_ids[f]]
    assert ids == want, f"{eng.key}: history tokenisation {ids} != face/separator interleave {want}"
    return ids


# ---------- preflight ----------

def archival(eng) -> list:
    rows = []
    for k in C.INSTRUCTIONS:
        for rep in range(1, C.ARCHIVAL_REPEATS + 1):
            p = S.SOURCE_INSTRUCTION[k]
            g = eng.generate(p)
            rows.append(dict(kind="archival", model=eng.key, condition=k, replicate=rep, prompt=p, prompt_sha256=S.sha256(p),
                             timestamp=now(), **g))
    return rows


def archival_check(eng, rows, exp28_main) -> dict:
    """Host-side stop rule (handoff test 6): identical output to Experiment 28, six-face |dp| <= REPRO_TOL_P, bit-identical repeats."""
    import math
    from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl
    ref = read_jsonl(Path(exp28_main) / eng.key / "raw_attempts.jsonl")
    res = {}
    for k in C.INSTRUCTIONS:
        mine = [r for r in rows if r["condition"] == k]
        r28 = next(r for r in ref if r["condition"] == k)
        dp = max(abs(math.exp(a["face_logprobs"][f]) - math.exp(b["face_logprobs"][f]))
                 for a, b in zip(mine[0]["digit_steps"], r28["digit_steps"]) for f in a["face_logprobs"])
        res[k] = dict(content=mine[0]["content"], exp28_content=r28["content"], equal=mine[0]["content"] == r28["content"],
                      reference_equal=mine[0]["content"] == S.seq(C.REFERENCES[(eng.key, k)]), max_dp_vs_exp28=dp,
                      repeats_identical=all(m["steps"] == mine[0]["steps"] for m in mine),
                      min_face_mass=min(sum(math.exp(v) for v in s["face_logprobs"].values()) for s in mine[0]["digit_steps"]))
    ok = all(v["equal"] and v["reference_equal"] and v["max_dp_vs_exp28"] <= C.REPRO_TOL_P and v["repeats_identical"] for v in res.values())
    ok = ok and res["G"]["min_face_mass"] >= C.MIN_FACE_MASS_G
    return dict(ok=ok, per_instruction=res)


# ---------- Experiment 31 ----------

def exp31(eng) -> list:
    out = []
    for st in [s for s in S.streams31() if s["scorer_model"] == eng.key]:
        x = C.REFERENCES[(st["source_model"], st["source_mode"])]
        ids = history_ids(eng, x)
        face_k = [n for n, t in enumerate(ids) if t in eng.face_ids.values()]      # index of each face token in the forced ids
        assert len(face_k) == 10
        for method, rep in (("incremental", 1), ("incremental", 2), ("full_pass", 1)):
            t0 = time.time()
            ds = forced_dists(eng, st["prompt"], ids, method, at=face_k)
            pos = []
            for j, (k, d) in enumerate(zip(face_k, ds), 1):
                assert d["n_forced"] == k and x[j - 1] == [f for f, i in eng.face_ids.items() if i == ids[k]][0]
                pos.append(dict(position=j, forced_prefix=S.seq(x[:j - 1]), forced_prefix_text=eng.decode(ids[:k]),
                                authentic_face=x[j - 1], **d))
            out.append(dict(study=C.TAG31, model_id=eng.model_id, model_commit=eng.commit, method=method,
                            replicate=rep, timestamp=now(), seconds=round(time.time() - t0, 3), **st, prompt_tokens=len(eng.prompt_ids(st["prompt"])),
                            rendered_prompt=eng.rendered_text(st["prompt"]), rendered_prompt_sha256=S.sha256(eng.rendered_text(st["prompt"])),
                            prompt_ids=eng.prompt_ids(st["prompt"]), history_ids=ids, positions=pos))
            print(f"[31] {st['stream_id']} {method}-{rep}: " + " ".join(
                max(p["face_logprobs"], key=p["face_logprobs"].get) for p in pos), flush=True)
    return out


# ---------- Experiment 32 ----------

STRICT = {"A": re.compile(r"[1-6] [1-6]"), "B": re.compile(r"[1-6]"), "C": re.compile(r"[1-6]")}


def exp32(eng) -> list:
    out = []
    sep = C.SEPARATOR_ID[eng.key]
    face_of = {i: f for f, i in eng.face_ids.items()}
    for pid, pr in S.prompts32().items():
        cond = pid.split("-")[-1]
        prompt = pr["prompt"]
        for rep in range(1, C.N_REPLICATES + 1):
            t0 = time.time()
            g = eng.generate(prompt)
            first = forced_dists(eng, prompt, [], "incremental")[0]                       # roll-6 (A) / roll-7 (B, C) boundary
            first_fp = forced_dists(eng, prompt, [], "full_pass")[0] if rep == 1 else None
            rec = dict(study=C.TAG32, predictor=eng.key, model_id=eng.model_id, model_commit=eng.commit, prompt_id=pid, condition=cond,
                       replicate=rep, timestamp=now(), prompt=prompt, prompt_sha256=pr["prompt_sha256"],
                       rendered_prompt=eng.rendered_text(prompt), rendered_prompt_sha256=S.sha256(eng.rendered_text(prompt)),
                       prompt_ids=eng.prompt_ids(prompt), free=g, free_strict_valid=bool(STRICT[cond].fullmatch(g["content"])) and g["finish_reason"] == "stop",
                       first_boundary=first, first_boundary_full_pass=first_fp,
                       first_boundary_matches_generation=first["face_logprobs"] == g["steps"][0]["face_logprobs"])
            if cond == "A":
                gen = g["generated_ids"]
                # Free roll 7: after the generated sixth face and the exact separator, never the authentic sixth.
                free7 = None
                if len(gen) >= 2 and gen[0] in face_of and gen[1] == sep and len(g["steps"]) >= 3:
                    free7 = dict(step_index=2, generated_sixth=face_of[gen[0]], forced_ids=gen[:2],
                                 face_logprobs=g["steps"][2]["face_logprobs"], top5=g["steps"][2]["top5"])
                rec["free_roll7"] = free7
                top6 = max(first["face_logprobs"], key=first["face_logprobs"].get)
                forced = [eng.face_ids[int(top6)], sep]
                cons = forced_dists(eng, prompt, forced, "incremental", at=[2])[0]
                rec["constrained_roll7"] = dict(label="constrained-digit readout: highest-probability first face + separator, scorer arithmetic",
                                                forced_sixth=int(top6), **cons)
                if rep == 1:
                    rec["constrained_roll7_full_pass"] = forced_dists(eng, prompt, forced, "full_pass", at=[2])[0]
                if free7:
                    rec["constrained_equals_free"] = free7["generated_sixth"] == int(top6) and cons["face_logprobs"] == free7["face_logprobs"]
            rec["seconds"] = round(time.time() - t0, 3)
            out.append(rec)
            print(f"[32] {pid} rep {rep}: free {g['content'][:60]!r} ({g['finish_reason']}, {g['completion_tokens']} tok) | "
                  f"first-boundary top face {max(first['face_logprobs'], key=first['face_logprobs'].get)}", flush=True)
    return out


# ---------- driver ----------

def env_record(eng, extra) -> dict:
    import accelerate
    import huggingface_hub
    from spar_dynamic.dice_logprob_crossmodel.gpu import vocab_scan
    t0 = time.time()
    vs = vocab_scan(eng)
    return dict(eng.env(), started_utc=now(), vocab_scan=vs, vocab_scan_seconds=round(time.time() - t0, 1),
                face_single_tokens={str(f): eng.hist_ids(str(f)) for f in C.FACES}, separator_id=C.SEPARATOR_ID[eng.key],
                separator_text=repr(eng.decode([C.SEPARATOR_ID[eng.key]])), rendered_G=eng.rendered_text(S.SOURCE_INSTRUCTION["G"]),
                prompt_sha256=S.all_prompt_sha(), accelerate=accelerate.__version__, huggingface_hub=huggingface_hub.__version__,
                code_sha256=code_sha(), code_commit=os.environ.get("SPAR_CODE_COMMIT", "unknown"),
                hourly_usd=os.environ.get("SPAR_HOURLY_USD"), job_order_seed=C.ORDER_SEED[eng.key], **extra)


def run(eng, root31, root32, exp28_main):
    r31, r32 = Path(root31) / "raw" / eng.key, Path(root32) / "raw" / eng.key
    for d in (r31, r32):
        if (d / "env.json").exists():
            raise SystemExit(f"{d} already holds a run; refusing")
        d.mkdir(parents=True, exist_ok=True)
    env = env_record(eng, {})
    if env["vocab_scan"]["variant_face_tokens"]:
        raise SystemExit(f"STOP: whitespace/variant face tokens exist: {env['vocab_scan']['variant_face_tokens'][:5]}")
    t0 = time.time()
    arch = archival(eng)
    write_jsonl(r31 / "archival.jsonl", arch)
    chk = archival_check(eng, arch, exp28_main)
    env.update(archival_seconds=round(time.time() - t0, 1), archival_check=chk)
    json.dump(env, open(r31 / "env.json", "w", encoding="utf-8"), indent=2)
    if not chk["ok"]:
        json.dump(dict(env, note="Experiment 32 not run: archival check failed"), open(r32 / "env.json", "w", encoding="utf-8"), indent=2)
        raise SystemExit(f"STOP: archival check failed: {json.dumps(chk)}")
    t0 = time.time()
    write_jsonl(r31 / "streams.jsonl", exp31(eng))
    env31 = dict(env, exp31_seconds=round(time.time() - t0, 1), streams_sha256=canonical_sha(r31 / "streams.jsonl"),
                 archival_sha256=canonical_sha(r31 / "archival.jsonl"), finished_utc=now(),
                 max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"])
    json.dump(env31, open(r31 / "env.json", "w", encoding="utf-8"), indent=2)
    t0 = time.time()
    write_jsonl(r32 / "cells.jsonl", exp32(eng))
    env32 = dict(env, exp32_seconds=round(time.time() - t0, 1), cells_sha256=canonical_sha(r32 / "cells.jsonl"),
                 archival_file=f"{Path(root31).name}/raw/{eng.key}/archival.jsonl", archival_sha256=canonical_sha(r31 / "archival.jsonl"),
                 finished_utc=now(), max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"])
    json.dump(env32, open(r32 / "env.json", "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run"])
    ap.add_argument("--model", required=True, choices=C.MODELS)
    ap.add_argument("--root31", default=str(C.EXP31))
    ap.add_argument("--root32", default=str(C.EXP32))
    ap.add_argument("--exp28-main", default=str(C.EXP28_MAIN))
    a = ap.parse_args()
    guard_out(a.root31)
    guard_out(a.root32)
    random.seed(C.ORDER_SEED[a.model])
    from spar_dynamic.dice_31_32.__main__ import verify_frozen
    if Path(a.root31).resolve() == C.EXP31.resolve():
        verify_frozen()
    S.ground_truth(Path(a.exp28_main))
    from spar_dynamic.dice_crossed_guidance.models import load
    t0 = time.time()
    eng = load(a.model)
    print(f"loaded {a.model} in {time.time() - t0:.1f} s", flush=True)
    run(eng, a.root31, a.root32, a.exp28_main)
    print(json.dumps(dict(stage=a.stage, model=a.model, seconds=round(time.time() - t0, 1))), flush=True)
