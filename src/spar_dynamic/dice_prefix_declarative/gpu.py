"""Open-weight collection for SPAR_DICE_PREFIX_DECLARATIVE_v1.0 (runs on the rented GPU).

Serving, generation and scoring are Experiment 21's validated `Qwen` class, imported unchanged: Qwen3-32B at the
archived commit, bf16 with an fp32 output layer, non-thinking chat template, one user message, greedy, batch 1,
128-token cap, exact full-vocabulary log-softmax for the six face tokens at every step.

Two measurements per prediction prompt (handoff section 3):
  free             greedy generation; the six-face distribution at each emitted digit, conditioned on the model's
                   own earlier predicted digits (Measurement A).
  teacher_forced   the six-face distribution at each target position with the TRUE G window fed as the assistant
                   history, incremental KV-cache arithmetic (Measurement B, primary).
The direct-generation reference G_j is Experiment 21's G prompt teacher-forced with its own greedy output.

Modes:
  preflight  G x3, F x3, H3/N3/S3/O3 x1 (seeded shuffle); scorer-vs-generation on every output; reference and k=3
             window scoring by both arithmetic paths. Gates are evaluated locally (`__main__ preflight_eval`).
  main       12 conditions x 3 repeats (seeded shuffle), both measurements, scorer check, full-pass floor per
             condition, reference rescoring. Needs --execute and --confirm-preflight-id <passed preflight run id>.

Usage: python -m spar_dynamic.dice_prefix_declarative.gpu {preflight,main} --out <dir> [--revision REV]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import time

from spar_dynamic.dice_logprob.gpu_runner import Qwen, sha
from spar_dynamic.dice_prefix_declarative import config as C
from spar_dynamic.dice_prefix_declarative import prompts as P

THINK_SUFFIX = "<|im_start|>assistant\n<think>\n\n</think>\n\n"


def guard_out(out_dir: str):
    """Never write into experiment folders 01-25."""
    for part in os.path.abspath(out_dir).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= C.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def jobs(mode: str) -> list:
    conds = {c["condition"]: c for c in P.conditions()}
    if mode == "preflight":
        j = [(r, i) for r in ("G", "F") for i in range(1, C.PREFLIGHT_REF_REPEATS + 1)]
        j += [(f"{a}{C.PREFLIGHT_ARMS_K}", 1) for a in C.ARMS]
    else:
        j = [(c, i) for c in conds for i in range(1, C.REPEATS + 1)]
    random.Random(C.ORDER_SEED + (0 if mode == "main" else 1)).shuffle(j)
    return j


def digits(gen: dict) -> list:
    """Per emitted digit step: face, exact face log-probs, the chosen token's log-prob."""
    out = []
    for s in gen["raw_logprobs_content"]:
        if s["token"].strip() in {str(f) for f in C.FACES} and len(s["token"].strip()) == 1:
            out.append(dict(face=int(s["token"].strip()), token=s["token"], logprob=s["logprob"],
                            face_logprobs_exact=s["face_logprobs_exact"]))
    return out


def run(mode: str, out_dir: str, revision: str | None):
    guard_out(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, "raw_attempts.jsonl")
    if os.path.exists(raw_path):
        raise SystemExit(f"{raw_path} exists; this runner never appends to or reruns a collection")
    refs = P.references()
    conds = {c["condition"]: c for c in P.conditions()}
    allc = {**conds, **refs}
    job = jobs(mode)
    t0 = time.time()
    q = Qwen(C.MODEL_ID, revision)
    rendered = {k: q.render(c["prompt"]) for k, c in allc.items()}
    env = dict(q.env(), load_seconds=round(time.time() - t0, 1), mode=mode, tag=C.TAG, order_seed=C.ORDER_SEED,
               started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), job_order=job,
               chat_template_sha256=sha(q.tok.chat_template or ""),
               prompt_sha256={k: c["prompt_sha256"] for k, c in allc.items()},
               rendered_sha256={k: sha(v) for k, v in rendered.items()},
               rendered_ends_with_empty_think={k: v.endswith(THINK_SUFFIX) for k, v in rendered.items()},
               rendered_has_system_turn={k: "<|im_start|>system" in v for k, v in rendered.items()},
               g_window_token_ids={str(k): q.tok(" ".join(map(str, C.G_REF[k:k + C.WINDOW])), add_special_tokens=False).input_ids
                                   for k in C.KS},
               g_full_token_ids=q.tok(" ".join(map(str, C.G_REF)), add_special_tokens=False).input_ids)
    with open(os.path.join(out_dir, f"env_{mode}.json"), "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)

    tf_path = os.path.join(out_dir, "teacher_forced.jsonl")
    for n, (cid, rep) in enumerate(job, 1):
        c = allc[cid]
        g = q.generate(c["prompt"])
        own = q.score_prefix(c["prompt"], g["raw_choice_content"], "incremental") if g["raw_choice_content"].strip() else []
        rec = dict(run_id=os.path.basename(out_dir.rstrip("/\\")), mode=mode, trial_id=f"{cid}-{rep}", condition=cid,
                   arm=c.get("arm", cid), k=c.get("k"), positions=c.get("positions"), target=c.get("target"),
                   replicate=rep, order_index=n, prompt_text=c["prompt"], prompt_sha256=c["prompt_sha256"],
                   model_id=C.MODEL_ID, served_provider="local-transformers", reasoning_mode="enable_thinking=False",
                   decoding="greedy", timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                   free_digits=digits(g), own_output_rescored=own, **g)
        with open(raw_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        if cid in conds:
            hist = " ".join(map(str, c["target"]))
            for s in q.score_prefix(c["prompt"], hist, "incremental"):
                row = dict(condition=cid, arm=c["arm"], k=c["k"], replicate=rep, history=hist,
                           original_position=c["k"] + s["position"], **s)
                with open(tf_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
        print(f"[{n}/{len(job)}] {cid}-{rep}: {g['raw_choice_content']!r} ({g['finish_reason']}, {g['latency_ms']} ms)", flush=True)

    # one full-pass score per prediction condition: the numerical floor (reported, never used as a result)
    floor_conds = [c for c in conds.values() if mode == "main" or c["k"] == C.PREFLIGHT_ARMS_K]
    with open(os.path.join(out_dir, "teacher_forced_full_pass.jsonl"), "w", encoding="utf-8") as f:
        for c in floor_conds:
            hist = " ".join(map(str, c["target"]))
            for s in q.score_prefix(c["prompt"], hist, "full_pass"):
                f.write(json.dumps(dict(condition=c["condition"], arm=c["arm"], k=c["k"], history=hist,
                                        original_position=c["k"] + s["position"], **s)) + "\n")
    # direct-generation reference G_j and F at the same G history, both arithmetic paths
    g_hist, f_hist = " ".join(map(str, C.G_REF)), " ".join(map(str, C.F_REF))
    with open(os.path.join(out_dir, "reference.jsonl"), "w", encoding="utf-8") as f:
        for instr, hname, hist in (("G", "G", g_hist), ("F", "G", g_hist), ("F", "F", f_hist)):
            for method in ("incremental", "full_pass"):
                for s in q.score_prefix(refs[instr]["prompt"], hist, method):
                    f.write(json.dumps(dict(instruction=instr, history=hname, history_sequence=hist, **s)) + "\n")
    env["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(os.path.join(out_dir, f"env_{mode}.json"), "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)
    print(json.dumps(dict(mode=mode, n_jobs=len(job), seconds=round(time.time() - t0, 1))), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preflight", "main"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--revision", default=C.REVISION)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--confirm-preflight-id", default=None)
    ap.add_argument("--gate", default=None, help="preflight_gates.json written locally by `__main__ preflight_eval`")
    a = ap.parse_args()
    if a.mode == "main":
        if not (a.execute and a.confirm_preflight_id and a.gate):
            raise SystemExit("main collection needs --execute, --confirm-preflight-id <run id> and --gate <preflight_gates.json>")
        gate = json.load(open(a.gate, encoding="utf-8"))
        if gate.get("overall") != "PASS" or gate.get("preflight_run_id") != a.confirm_preflight_id:
            raise SystemExit(f"preflight gate is {gate.get('overall')} for run {gate.get('preflight_run_id')}; refusing main")
    run(a.mode, a.out, a.revision)
