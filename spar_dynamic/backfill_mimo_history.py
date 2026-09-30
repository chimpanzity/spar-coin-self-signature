"""Backfill mimo history_conditioned trajectories until 20 valid.

Main pilot 5 run left mimo/history_conditioned at 13/20 valid + 7 failed
(mimo occasionally emits non-parseable output; STEP_MAX_ATTEMPTS=3 is too
tight). This backfill:

- picks up replicate_index starting at 20 (fresh indices)
- runs with STEP_MAX_ATTEMPTS temporarily bumped to 10 to reduce per-step
  failure rate
- writes trajectory-*.json into the same trajectories/ dir as the main run
- appends per-attempt records to the same raw_attempts.jsonl so cost
  accounting remains coherent
- stops when the cell reaches 20 valid, or after MAX_BACKFILL_ATTEMPTS
- respects the same STIMULUS_CORPUS budget cap
"""

import argparse, glob, json, os, sys, time
from dataclasses import asdict

from . import config as C
from .api import CostAccountant, make_client, BudgetExceeded
from .state import RunPaths, read_json, write_json
from .stimulus_corpus import (generate_history_conditioned_trajectory,
                              rebuild_trajectory_state_from_attempts)


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _count_cell_valid(traj_dir: str, model_label: str, method: str) -> int:
    n = 0
    for f in glob.glob(os.path.join(traj_dir, "trajectory-*.json")):
        r = read_json(f)
        if r and r.get("status") == "ok" and r.get("model_label") == model_label \
                and r.get("method") == method \
                and len(r.get("parsed_sequence", "")) == C.CORPUS_SEQUENCE_LENGTH:
            n += 1
    return n


def _next_replicate_index(traj_dir: str, model_label: str, method: str) -> int:
    """Return the smallest replicate_index >= 0 not yet used by ANY trajectory
    (ok or failed) in this cell — so we never collide with existing files."""
    used = set()
    prefix = f"trajectory-{model_label}_{method}_"
    for f in glob.glob(os.path.join(traj_dir, prefix + "*.json")):
        base = os.path.basename(f)[len(prefix):].split(".", 1)[0]
        try:
            used.add(int(base))
        except ValueError:
            pass
    k = 0
    while k in used:
        k += 1
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", required=True)
    ap.add_argument("--yes", action="store_true", required=True)
    ap.add_argument("--run-id", required=True,
                    help="existing spar-stimulus-corpus-* run to backfill into")
    ap.add_argument("--data-root", default="data/spar_dynamic")
    ap.add_argument("--target-per-cell", type=int, default=20)
    ap.add_argument("--max-attempts", type=int, default=25,
                    help="max new trajectories to attempt before giving up")
    ap.add_argument("--step-max-attempts", type=int, default=10,
                    help="override CORPUS_STEP_MAX_ATTEMPTS for the backfill")
    args = ap.parse_args()

    paths = RunPaths(args.data_root, args.run_id); paths.ensure()
    traj_dir = os.path.join(paths.root, "trajectories")
    raw_jsonl = os.path.join(paths.root, "raw_attempts.jsonl")
    log_path = os.path.join(paths.logs, "backfill_mimo_history.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logf = open(log_path, "a", encoding="utf-8", buffering=1)

    def log(msg):
        line = f"[{_now()}] {msg}"
        print(line, flush=True); logf.write(line + "\n"); logf.flush()

    log(f"START backfill run_id={args.run_id} target={args.target_per_cell} "
        f"step_max_attempts={args.step_max_attempts}")

    # temporarily raise step max attempts for backfill only
    orig_step_max_attempts = C.CORPUS_STEP_MAX_ATTEMPTS
    C.CORPUS_STEP_MAX_ATTEMPTS = args.step_max_attempts
    log(f"  CORPUS_STEP_MAX_ATTEMPTS: {orig_step_max_attempts} -> {C.CORPUS_STEP_MAX_ATTEMPTS}")

    client = make_client()
    accountant = CostAccountant(client)
    accountant.bootstrap_from_disk(raw_jsonl)
    preflight_raw = os.path.join(paths.root, "preflight", "raw_attempts.jsonl")
    if os.path.exists(preflight_raw):
        accountant.bootstrap_from_disk(preflight_raw)
    log(f"  bootstrap spend = ${accountant.spent_usd:.4f}")
    accountant.snapshot_catalog()

    model_label = "mimo"
    method = "history_conditioned"
    model = C.CORPUS_MODEL_BY_LABEL[model_label]

    attempts = 0
    while attempts < args.max_attempts:
        valid = _count_cell_valid(traj_dir, model_label, method)
        log(f"  cell {model_label}/{method} = {valid}/{args.target_per_cell} valid "
            f"(spend=${accountant.spent_usd:.4f})")
        if valid >= args.target_per_cell:
            log(f"DONE {model_label}/{method} reached target")
            break
        k = _next_replicate_index(traj_dir, model_label, method)
        traj_id = f"{model_label}_{method}_{k:02d}"
        resume_seq = rebuild_trajectory_state_from_attempts(raw_jsonl, traj_id)
        if resume_seq:
            log(f"  attempt {attempts+1}: resuming {traj_id} from step {len(resume_seq)+1}")
        else:
            log(f"  attempt {attempts+1}: launching {traj_id}")
        try:
            rec = generate_history_conditioned_trajectory(
                client, accountant,
                run_id=args.run_id, trajectory_id=traj_id,
                model=model, replicate_index=k,
                raw_jsonl_path=raw_jsonl,
                resume_history=resume_seq, log=log)
        except BudgetExceeded as e:
            log(f"BUDGET STOP: {e}")
            break
        write_json(os.path.join(traj_dir, f"trajectory-{traj_id}.json"), asdict(rec))
        log(f"    {traj_id}: status={rec.status} n_calls={rec.n_calls} "
            f"cost=${rec.total_cost_usd:.4f} spent=${accountant.spent_usd:.4f}")
        attempts += 1

    final = _count_cell_valid(traj_dir, model_label, method)
    log(f"BACKFILL END: {model_label}/{method} = {final}/{args.target_per_cell} valid "
        f"after {attempts} new trajectories, total spend=${accountant.spent_usd:.4f}")
    C.CORPUS_STEP_MAX_ATTEMPTS = orig_step_max_attempts
    logf.close()


if __name__ == "__main__":
    main()
