"""GPU stages for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (one model per process; run on the rented GPU).

Serving is Experiment 27's engine (`dice_crossed_guidance.models`), unchanged: bf16 weights and activations, a separate fp32
copy of the output layer, batch 1, prompt prefilled once and every further token fed one at a time through the KV cache,
exact full-vocabulary log-softmax, greedy argmax, no logit processors, max 128 new tokens. Qwen via Experiment 21's class
(enable_thinking=False); Mistral via mistral_common tekken (one user message, no system prompt), text path only.

  preflight --model M   G x3, F x3, each S and W condition once (seeded shuffle); every output rescored by both arithmetic
                        paths; matched prefix (2 instructions x 2 histories) and matched windows on this run's G/F; vocabulary
                        scan for contextual face tokens; timings.
  main --model M        N_REPLICATES of all 15 conditions (seeded shuffle; resumable, append-only); the first record of each
                        distinct (condition, output) rescored by both paths; then matched prefix and matched windows on the
                        main run's G/F. Needs --gate (a PASS preflight gate for M).

Usage: python -m spar_dynamic.dice_logprob_crossmodel.gpu <stage> --model {qwen,mistral} --out <dir> [--gate <json>]
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import random
import re
import time
from pathlib import Path

from spar_dynamic.dice_logprob_crossmodel import config as C
from spar_dynamic.dice_logprob_crossmodel import prompts as P

PKG = Path(__file__).resolve().parent
VALID10 = re.compile(r"[1-6]( [1-6]){9}")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def guard_out(out_dir: str):
    for part in os.path.abspath(out_dir).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= C.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def append(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def file_sha(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def code_sha() -> dict:
    """SHA-256 of this package and of the reused engine/prompt modules, as deployed."""
    files = sorted(PKG.glob("*.py")) + [PKG.parent / "dice_crossed_guidance" / "models.py",
                                        PKG.parent / "dice_crossed_guidance" / "config.py",
                                        PKG.parent / "dice_logprob" / "prompts.py", PKG.parent / "dice_logprob" / "gpu_runner.py"]
    return {f"{p.parent.name}/{p.name}": file_sha(p) for p in files}


def check_gate(path, model):
    g = json.load(open(path, encoding="utf-8"))
    if g.get("overall") != "PASS" or g.get("model") != model:
        raise SystemExit(f"gate {path} is {g.get('overall')} for {g.get('model')}; refusing")
    if g.get("prompt_sha256") != {c["condition"]: c["prompt_sha256"] for c in P.conditions()}:
        raise SystemExit("gate prompt hashes differ from the frozen prompts; refusing")
    return g


def vocab_scan(eng) -> dict:
    """Every vocabulary token whose text is a face digit with whitespace, or a run of ASCII digits containing a face."""
    if eng.key == "qwen":
        n, first, dec = len(eng.tok), 0, lambda i: eng.tok.decode([i])
    else:
        n, first, dec = eng.t.n_words, eng.t.num_special_tokens, lambda i: eng.t.decode([i])
    face_like, multi = [], []
    for i in range(first, n):
        try:
            s = dec(i)
        except Exception:
            continue
        if re.fullmatch(r"\s*[1-6]\s*", s):
            face_like.append([i, s])
        elif re.fullmatch(r"\s*[0-9]{2,}\s*", s) and re.search(r"[1-6]", s):
            multi.append([i, s])
    bare = {str(f): i for f, i in eng.face_ids.items()}
    variants = [x for x in face_like if x[0] not in bare.values()]
    return dict(vocab_size=n, face_like=face_like, variant_face_tokens=variants, multi_digit_ascii_tokens=multi)


def env_record(eng, stage, jobs) -> dict:
    conds = P.conditions()
    g10 = " ".join(map(str, C.QWEN_G_REF))
    import accelerate
    import huggingface_hub
    return dict(eng.env(), study=C.TAG, stage=stage, started_utc=now(), order_seed=_seed(eng.key, stage), job_order=jobs,
                n_jobs=len(jobs), prompt_sha256={c["condition"]: c["prompt_sha256"] for c in conds},
                rendered_sha256={c["condition"]: P.sha256(eng.rendered_text(c["prompt"])) for c in conds},
                rendered_G=eng.rendered_text(P.GEN), g10_history_ids=eng.hist_ids(g10),
                face_single_tokens={str(f): eng.hist_ids(str(f)) for f in C.FACES},
                accelerate=accelerate.__version__, huggingface_hub=huggingface_hub.__version__,
                code_sha256=code_sha(), code_commit=os.environ.get("SPAR_CODE_COMMIT", "unknown"),
                hourly_usd=os.environ.get("SPAR_HOURLY_USD"), max_new_tokens=C.MAX_NEW_TOKENS)


def _seed(model, stage):
    return C.ORDER_SEED[model] + (100 if stage == "preflight" else 0)


def rescore(eng, rec, full: bool):
    """Own-output rescoring (handoff: must reproduce generation). Only when re-encoding the text gives the generated ids."""
    ids = eng.hist_ids(rec["content"]) if rec["content"] else []
    rec["rescore_tokens_equal"] = ids == rec["generated_ids"]
    if rec["rescore_tokens_equal"] and ids:
        rec["own_rescored"] = eng.score(rec["prompt"], rec["content"], "incremental")
        if full:
            rec["own_rescored_full_pass"] = eng.score(rec["prompt"], rec["content"], "full_pass")


def gen_record(eng, stage, c, rep, order_index) -> dict:
    g = eng.generate(c["prompt"])
    return dict(study=C.TAG, stage=stage, model=eng.key, model_id=eng.model_id, model_commit=eng.commit,
                trial_id=f"{eng.key}-{c['condition']}-{rep:02d}", condition=c["condition"], condition_type=c["condition_type"],
                target_positions=c["positions"], n_expected=c["n_expected"], replicate=rep, order_index=order_index,
                prompt=c["prompt"], prompt_sha256=P.sha256(c["prompt"]), rendered_prompt=eng.rendered_text(c["prompt"]),
                decoding="greedy argmax, no sampling, no logit processors", timestamp=now(), **g)


def matched(eng, refs: dict) -> list:
    """Teacher-forced six-face rows. mp: instruction in {G, F} x history in {G, F} over all ten positions.
    window: each W prompt with the G or F reference's own window as its assistant history."""
    conds = P.by_id()
    rows = []
    for x in ("G", "F"):
        for h in ("G", "F"):
            for method in ("incremental", "full_pass"):
                for s in eng.score(conds[x]["prompt"], refs[h], method):
                    rows.append(dict(kind="mp", instruction=x, history=h, history_sequence=refs[h],
                                     original_position=s["position"], **s))
    for a, b in C.WINDOWS:
        w = f"W{a}-{b}"
        for h in ("G", "F"):
            sub = " ".join(refs[h].split(" ")[a - 1:b])
            for method in ("incremental", "full_pass"):
                for s in eng.score(conds[w]["prompt"], sub, method):
                    rows.append(dict(kind="window", instruction=w, history=h, history_sequence=sub,
                                     original_position=a + s["position"] - 1, **s))
    return rows


def unique_refs(recs) -> dict:
    refs = {}
    for k in ("G", "F"):
        outs = {r["content"] for r in recs if r["condition"] == k}
        if len(outs) != 1 or not VALID10.fullmatch(next(iter(outs))):
            raise SystemExit(f"{k} reference is not a single valid sequence: {sorted(outs)}; matched-prefix scoring not run")
        refs[k] = outs.pop()
    return refs


def preflight(eng, out):
    raw = os.path.join(out, "raw_attempts.jsonl")
    if os.path.exists(raw):
        raise SystemExit(f"{raw} exists; preflight is never appended to")
    conds = P.by_id()
    jobs = [[k, i] for k in ("G", "F") for i in range(1, C.PREFLIGHT_REPEATS + 1)] + \
        [[k, 1] for k in conds if k not in ("G", "F")]
    random.Random(_seed(eng.key, "preflight")).shuffle(jobs)
    env = env_record(eng, "preflight", jobs)
    t0 = time.time()
    env["vocab_scan"] = vocab_scan(eng)
    env["vocab_scan_seconds"] = round(time.time() - t0, 1)
    json.dump(env, open(os.path.join(out, "env_preflight.json"), "w", encoding="utf-8"), indent=2)
    timing = collections.defaultdict(list)
    for n, (k, i) in enumerate(jobs, 1):
        t0 = time.time()
        rec = gen_record(eng, "preflight", conds[k], i, n)
        rescore(eng, rec, full=True)
        append(raw, rec)
        timing[k].append(time.time() - t0)
        print(f"[{n}/{len(jobs)}] {k}-{i}: {rec['content'][:120]!r} ({rec['finish_reason']}, {rec['latency_ms']} ms)", flush=True)
    recs = [json.loads(l) for l in open(raw, encoding="utf-8")]
    t0 = time.time()
    rows = matched(eng, unique_refs(recs))
    with open(os.path.join(out, "matched_prefix.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    env.update(finished_utc=now(), sec_per_job={k: sum(v) / len(v) for k, v in timing.items()},
               matched_seconds=round(time.time() - t0, 1), max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"])
    json.dump(env, open(os.path.join(out, "env_preflight.json"), "w", encoding="utf-8"), indent=2)


def main(eng, out, gate_path):
    raw = os.path.join(out, "raw_attempts.jsonl")
    conds = P.by_id()
    jobs = [[k, i] for k in conds for i in range(1, C.N_REPLICATES + 1)]
    random.Random(_seed(eng.key, "main")).shuffle(jobs)
    done, seen = set(), set()
    if os.path.exists(raw):                         # resume: refuse drift, skip completed trials
        for l in open(raw, encoding="utf-8"):
            r = json.loads(l)
            if r["prompt_sha256"] != conds[r["condition"]]["prompt_sha256"] or r["model"] != eng.key:
                raise SystemExit(f"prompt or model drift in {raw} at {r['trial_id']}; refusing to resume")
            done.add((r["condition"], r["replicate"]))
            seen.add((r["condition"], r["content"]))
    env = dict(env_record(eng, "main", jobs), gate_sha256=file_sha(gate_path), resumed_with=len(done))
    env_path = os.path.join(out, "env_main.json" if not done else f"env_main_resume{len(done)}.json")
    json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2)
    t_start = time.time()
    todo = [(n, k, i) for n, (k, i) in enumerate(jobs, 1) if (k, i) not in done]
    for j, (n, k, i) in enumerate(todo, 1):
        rec = gen_record(eng, "main", conds[k], i, n)
        first = (k, rec["content"]) not in seen
        rec["rescored_subset"] = first
        if first:
            rescore(eng, rec, full=True)
            seen.add((k, rec["content"]))
        append(raw, rec)
        el = time.time() - t_start
        print(f"[{n}/{len(jobs)}] {k}-{i}: {rec['content'][:80]!r} ({rec['finish_reason']}) | {el / j:.2f} s/trial, "
              f"eta {(len(todo) - j) * el / j / 60:.1f} min", flush=True)
    recs = [json.loads(l) for l in open(raw, encoding="utf-8")]
    t0 = time.time()
    rows = matched(eng, unique_refs(recs))
    with open(os.path.join(out, "matched_prefix.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    env.update(finished_utc=now(), generation_seconds=round(t0 - t_start, 1), matched_seconds=round(time.time() - t0, 1),
               raw_attempts_sha256=file_sha(raw), matched_prefix_sha256=file_sha(os.path.join(out, "matched_prefix.jsonl")),
               max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"])
    json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["preflight", "main"])
    ap.add_argument("--model", required=True, choices=C.MODELS)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gate", default=None)
    a = ap.parse_args()
    guard_out(a.out)
    os.makedirs(a.out, exist_ok=True)
    if a.stage == "main":
        if not a.gate:
            raise SystemExit("main needs --gate <PASS preflight gate json for this model>")
        check_gate(a.gate, a.model)
    from spar_dynamic.dice_crossed_guidance.models import load
    t0 = time.time()
    eng = load(a.model)
    print(f"loaded {a.model} in {time.time() - t0:.1f} s", flush=True)
    preflight(eng, a.out) if a.stage == "preflight" else main(eng, a.out, a.gate)
    print(json.dumps(dict(stage=a.stage, model=a.model, seconds=round(time.time() - t0, 1))), flush=True)
