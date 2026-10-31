"""GPU stages for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1 (one predictor per process; run on the rented GPU).

Serving is Experiment 27/28's engine (`dice_crossed_guidance.models`), unchanged: bf16 weights and activations, fp32 output
layer and logits, batch 1, KV-cache incremental decoding, full-vocabulary log-softmax, greedy argmax, max 128 new tokens.

  preflight --model P   archival G and F (Experiment 28 prompts) x2; the 28 preflight cells once each (k in 1, 5, 9 and the
                        4 middle-anchored cells), seeded shuffle; own-output rescoring (both arithmetic paths); teacher-forced
                        true targets (both paths); vocabulary scan.
  main --model P        archival G and F x2 plus all 76 cells x 3 replicates (seeded shuffle; resumable, append-only); the
                        first record of each distinct (cell, output) rescored by both paths; then every cell's true target
                        teacher-forced once by both paths. Needs --gate (a PASS preflight gate for P).

Usage: python -m spar_dynamic.dice_bidirectional_completion.gpu <stage> --model {qwen,mistral} --out <dir> [--gate <json>]
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

from spar_dynamic.dice_bidirectional_completion import config as C
from spar_dynamic.dice_bidirectional_completion import prompts as P
from spar_dynamic.dice_logprob_crossmodel import prompts as P28
from spar_dynamic.dice_logprob_crossmodel.gpu import append, rescore, vocab_scan

PKG = Path(__file__).resolve().parent


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def file_sha(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def guard_out(out_dir: str):
    for part in os.path.abspath(out_dir).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= C.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def code_sha() -> dict:
    files = sorted(PKG.glob("*.py")) + [PKG.parent / "dice_crossed_guidance" / "models.py", PKG.parent / "dice_crossed_guidance" / "config.py",
                                        PKG.parent / "dice_logprob_crossmodel" / "gpu.py", PKG.parent / "dice_logprob_crossmodel" / "prompts.py",
                                        PKG.parent / "dice_logprob" / "prompts.py", PKG.parent / "dice_logprob" / "gpu_runner.py"]
    return {f"{p.parent.name}/{p.name}": file_sha(p) for p in files}


def check_gate(path, model):
    g = json.load(open(path, encoding="utf-8"))
    if g.get("overall") != "PASS" or g.get("model") != model:
        raise SystemExit(f"gate {path} is {g.get('overall')} for {g.get('model')}; refusing")
    if g.get("prompt_sha256") != {c["prompt_id"]: c["prompt_sha256"] for c in P.prompt_cells()}:
        raise SystemExit("gate prompt hashes differ from the frozen prompts; refusing")
    return g


def _seed(model, stage):
    return C.ORDER_SEED[model] + (100 if stage == "preflight" else 0)


def archival_prompts() -> dict:
    return {k: P28.by_id()[k]["prompt"] for k in C.INSTRUCTIONS}


def env_record(eng, stage, jobs) -> dict:
    import accelerate
    import huggingface_hub
    pc = P.prompt_cells()
    g10 = P.seq(C.REFERENCES[("qwen", "G")])
    return dict(eng.env(), study=C.TAG, stage=stage, started_utc=now(), order_seed=_seed(eng.key, stage), job_order=jobs,
                n_jobs=len(jobs), prompt_sha256={c["prompt_id"]: c["prompt_sha256"] for c in pc},
                rendered_sha256={c["prompt_id"]: P.sha256(eng.rendered_text(c["prompt"])) for c in pc},
                archival_prompt_sha256={k: P.sha256(v) for k, v in archival_prompts().items()},
                rendered_G=eng.rendered_text(archival_prompts()["G"]), g10_history_ids=eng.hist_ids(g10),
                face_single_tokens={str(f): eng.hist_ids(str(f)) for f in C.FACES},
                accelerate=accelerate.__version__, huggingface_hub=huggingface_hub.__version__,
                code_sha256=code_sha(), code_commit=os.environ.get("SPAR_CODE_COMMIT", "unknown"),
                hourly_usd=os.environ.get("SPAR_HOURLY_USD"), max_new_tokens=C.MAX_NEW_TOKENS)


def gen_record(eng, stage, job, prompt, rep, order_index, cell=None) -> dict:
    g = eng.generate(prompt)
    rec = dict(study=C.TAG, stage=stage, model=eng.key, predictor=eng.key, model_id=eng.model_id, model_commit=eng.commit,
               job=job, replicate=rep, order_index=order_index, prompt=prompt, prompt_sha256=P.sha256(prompt),
               rendered_prompt=eng.rendered_text(prompt), decoding="greedy argmax, no sampling, no logit processors",
               timestamp=now(), **g)
    if cell is None:
        rec.update(kind="archival", condition=job, n_expected=10, trial_id=f"{eng.key}-archival-{job}-{rep}")
    else:
        rec.update(kind="cell", cell_id=cell["cell_id"], prompt_id=cell["prompt_id"], condition=cell["prompt_id"],
                   n_expected=cell["n_missing"], trial_id=f"{cell['cell_id']}-{rep}",
                   **{k: cell[k] for k in ("source", "source_instruction", "task_type", "direction", "k", "missing_positions", "target")})
    return rec


def teacher_force(eng, cell) -> list:
    """True missing digits forced as the assistant answer; six-face log-probs before each, by both arithmetic paths."""
    ids = eng.hist_ids(cell["target"])
    face_ids = set(eng.face_ids.values())
    face_at = [j for j, t in enumerate(ids) if t in face_ids]
    assert len(face_at) == cell["n_missing"], "target does not tokenise to one token per face"
    rows = []
    for method in ("incremental", "full_pass"):
        for s in eng.score(cell["prompt"], cell["target"], method):
            step = s["position"]
            assert s["history_face"] == cell["missing_values"][step - 1]
            rows.append(dict(cell_id=cell["cell_id"], predictor=eng.key, source=cell["source"],
                             source_instruction=cell["source_instruction"], task_type=cell["task_type"],
                             direction=cell["direction"], k=cell["k"], prompt_id=cell["prompt_id"], prompt_sha256=cell["prompt_sha256"],
                             output_step=step, original_position=cell["missing_positions"][step - 1], true_face=s["history_face"],
                             forced_prefix=" ".join(cell["target"].split(" ")[:step - 1]), forced_prefix_ids=ids[:face_at[step - 1]],
                             **{k: v for k, v in s.items() if k not in ("position", "history_face")}))
    return rows


def _run(eng, out, stage, jobs, cells, archival, gate_path=None):
    raw = os.path.join(out, "raw_attempts.jsonl")
    done, seen = set(), set()
    if os.path.exists(raw):
        if stage == "preflight":
            raise SystemExit(f"{raw} exists; preflight is never appended to")
        for l in open(raw, encoding="utf-8"):                       # resume: refuse drift, skip completed jobs
            r = json.loads(l)
            want = cells[r["job"]]["prompt_sha256"] if r["kind"] == "cell" else P.sha256(archival[r["job"]])
            if r["prompt_sha256"] != want or r["model"] != eng.key:
                raise SystemExit(f"prompt or model drift in {raw} at {r['trial_id']}; refusing to resume")
            done.add((r["job"], r["replicate"]))
            seen.add((r["job"], r["content"]))
    env = env_record(eng, stage, jobs)
    if stage == "preflight":
        t0 = time.time()
        env["vocab_scan"] = vocab_scan(eng)
        env["vocab_scan_seconds"] = round(time.time() - t0, 1)
    if gate_path:
        env["gate_sha256"] = file_sha(gate_path)
    env["resumed_with"] = len(done)
    env_path = os.path.join(out, f"env_{stage}.json" if not done else f"env_{stage}_resume{len(done)}.json")
    json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2)
    t_start = time.time()
    todo = [(n, job, rep) for n, (job, rep) in enumerate(jobs, 1) if (job, rep) not in done]
    for j, (n, job, rep) in enumerate(todo, 1):
        cell = cells.get(job)
        rec = gen_record(eng, stage, job, cell["prompt"] if cell else archival[job], rep, n, cell)
        first = (job, rec["content"]) not in seen
        rec["rescored_subset"] = first
        if first:
            rescore(eng, rec, full=True)
            seen.add((job, rec["content"]))
        append(raw, rec)
        el = time.time() - t_start
        print(f"[{n}/{len(jobs)}] {job}-{rep}: {rec['content'][:70]!r} ({rec['finish_reason']}) | {el / j:.2f} s/call, "
              f"eta {(len(todo) - j) * el / j / 60:.1f} min", flush=True)
    t0 = time.time()
    tf_path = os.path.join(out, "teacher_forced.jsonl")
    with open(tf_path, "w", encoding="utf-8") as f:                 # one scoring pass per distinct cell (deterministic)
        for cid in sorted({job for job, _ in jobs if job in cells}):
            for row in teacher_force(eng, cells[cid]):
                f.write(json.dumps(row) + "\n")
    env.update(finished_utc=now(), generation_seconds=round(t0 - t_start, 1), teacher_forced_seconds=round(time.time() - t0, 1),
               raw_attempts_sha256=file_sha(raw), teacher_forced_sha256=file_sha(tf_path),
               max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"])
    json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2)


def jobs_for(model, stage) -> list:
    cells = P.preflight_cells(model) if stage == "preflight" else [c for c in P.conditions() if c["predictor"] == model]
    reps = 1 if stage == "preflight" else C.N_REPLICATES
    jobs = [[k, i] for k in C.INSTRUCTIONS for i in range(1, C.ARCHIVAL_REPEATS + 1)] + \
        [[c["cell_id"], i] for c in cells for i in range(1, reps + 1)]
    random.Random(_seed(model, stage)).shuffle(jobs)
    return jobs


def run(eng, out, stage, gate_path=None):
    _run(eng, out, stage, jobs_for(eng.key, stage), P.by_cell(), archival_prompts(), gate_path)


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
    run(eng, a.out, a.stage, a.gate)
    print(json.dumps(dict(stage=a.stage, model=a.model, seconds=round(time.time() - t0, 1))), flush=True)
