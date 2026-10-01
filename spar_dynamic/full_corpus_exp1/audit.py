"""Section 4: source audit. Read-only validation of the corpus before paid calls.

Stops the paid run on any hard failure. Produces source_audit.json, input_hashes.json,
source_provider_audit.csv, and duplicate_sequence_audit.csv.
"""

import csv, hashlib, json, os, re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from . import config as F


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_raw_attempts(path: str) -> List[Dict]:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s: continue
            try:
                rows.append(json.loads(s))
            except Exception:
                continue
    return rows


def _attempts_by_trajectory(raw: List[Dict], source_method: str) -> Dict[str, List[Dict]]:
    by: Dict[str, List[Dict]] = defaultdict(list)
    for r in raw:
        if r.get("method") == source_method:
            tid = r.get("trajectory_id")
            if tid: by[tid].append(r)
    for tid in by:
        by[tid].sort(key=lambda a: (a.get("trial_index") or 0, a.get("attempt_index") or 0))
    return by


def _reconstruct_sequence(attempts: List[Dict]) -> Tuple[Optional[str], List[str]]:
    """Return (sequence, errors). sequence is the first-valid-per-step join."""
    errors = []
    chosen: Dict[int, str] = {}
    for a in attempts:
        step = a.get("trial_index")
        if not isinstance(step, int):
            continue
        if a.get("valid") and a.get("parsed_flip") in ("H", "T") and step not in chosen:
            chosen[step] = a["parsed_flip"]
    seq = ""
    step = 1
    while step in chosen:
        seq += chosen[step]
        step += 1
    if len(seq) != 100:
        errors.append(f"reconstructed length {len(seq)} != 100")
        return (None, errors)
    # Verify history_before invariants
    for a in attempts:
        step = a.get("trial_index")
        if not isinstance(step, int): continue
        if not a.get("valid"): continue
        if step not in chosen: continue
        expected = seq[:step - 1]
        got = (a.get("history_before") or "")
        if expected != got:
            errors.append(f"step {step}: history_before mismatch (expected len {len(expected)}, got len {len(got)})")
    # Verify saved source prompts match templates
    for a in attempts:
        if not a.get("valid"): continue
        step = a.get("trial_index")
        if not isinstance(step, int): continue
        prompt = a.get("prompt_text", "")
        if step == 1:
            if prompt != F.SOURCE_TEMPLATE_FIRST_CALL:
                errors.append(f"step 1: prompt_text does not match first-call template")
        else:
            hist = a.get("history_before") or ""
            want = F.SOURCE_TEMPLATE_SUBSEQUENT_PATTERN.format(history=hist)
            if prompt != want:
                errors.append(f"step {step}: prompt_text does not match subsequent-call template")
    return (seq, errors)


def _providers_for_trajectory(attempts: List[Dict]) -> Dict[str, Any]:
    """Report provider mixture across *accepted* attempts of a trajectory."""
    provs = Counter()
    returned_ids = Counter()
    valid_attempts = 0
    retried_steps = Counter()
    for a in attempts:
        if a.get("valid"):
            provs[a.get("provider") or ""] += 1
            returned_ids[a.get("returned_model_id") or ""] += 1
            valid_attempts += 1
        step = a.get("trial_index")
        if isinstance(step, int):
            retried_steps[step] += 1
    retries_above_one = sum(1 for s, n in retried_steps.items() if n > 1)
    return {
        "providers_accepted": dict(provs),
        "returned_ids_accepted": dict(returned_ids),
        "n_valid_attempts": valid_attempts,
        "n_steps_with_retry": retries_above_one,
    }


def audit_sources(corpus_dir: str, source_run_dir: str, trajectory_ids: List[str],
                  source_method: str = F.SOURCE_METHOD) -> Dict[str, Any]:
    """Full audit. Returns a report dict; raises AssertionError on hard failure."""
    trajectories_csv = os.path.join(corpus_dir, "trajectories.csv")
    manifest_path = os.path.join(corpus_dir, "manifest.json")
    raw_path = os.path.join(source_run_dir, "raw_attempts.jsonl")

    missing = [p for p in (trajectories_csv, manifest_path, raw_path) if not os.path.exists(p)]
    assert not missing, f"missing required inputs: {missing}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Load corpus rows
    rows_by_tid: Dict[str, Dict] = {}
    with open(trajectories_csv, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows_by_tid[r["trajectory_id"]] = r

    missing_tids = [t for t in trajectory_ids if t not in rows_by_tid]
    assert not missing_tids, f"trajectory_ids missing from corpus CSV: {missing_tids}"

    # Load raw and group
    raw = _load_raw_attempts(raw_path)
    attempts_by_tid = _attempts_by_trajectory(raw, source_method)

    # Verify per-trajectory
    per_traj: Dict[str, Any] = {}
    hard_errors: List[str] = []
    sequence_hashes: Dict[str, str] = {}
    for tid in trajectory_ids:
        row = rows_by_tid[tid]
        if row["method"] != source_method:
            hard_errors.append(f"{tid}: method={row['method']} (expected {source_method})")
            continue
        if not re.fullmatch(r"[HT]{100}", row["sequence"] or ""):
            hard_errors.append(f"{tid}: sequence not ^[HT]{{100}}$")
            continue
        if row["model"] not in F.JUDGE_BY_LABEL:
            hard_errors.append(f"{tid}: unknown model {row['model']}")
            continue
        if row["requested_model_id"] != F.JUDGE_BY_LABEL[row["model"]].slug:
            hard_errors.append(f"{tid}: requested_model_id {row['requested_model_id']} does not match registry")
            continue
        # temperature
        try:
            if float(row.get("temperature", "0")) != 0.0:
                hard_errors.append(f"{tid}: temperature {row.get('temperature')} != 0.0")
        except Exception:
            hard_errors.append(f"{tid}: temperature field unparseable")
        attempts = attempts_by_tid.get(tid, [])
        # Reconstruction + prompt-template verification only applies to
        # history_conditioned trajectories (single-step batch and
        # independent_calls use different source prompts and have no history_before).
        if source_method == "history_conditioned":
            seq, errs = _reconstruct_sequence(attempts)
            if seq is None:
                hard_errors.append(f"{tid}: reconstruction failed: {errs}")
                continue
            if seq != row["sequence"]:
                hard_errors.append(f"{tid}: reconstructed sequence differs from CSV")
                continue
            if errs:
                for e in errs: hard_errors.append(f"{tid}: {e}")
        prov = _providers_for_trajectory(attempts)
        per_traj[tid] = {
            "model": row["model"], "split": row["split"],
            "sequence_sha256": sha256_text(row["sequence"]),
            "n_valid_attempts": prov["n_valid_attempts"],
            "n_steps_with_retry": prov["n_steps_with_retry"],
            "providers_accepted": prov["providers_accepted"],
            "returned_ids_accepted": prov["returned_ids_accepted"],
        }
        sequence_hashes[tid] = per_traj[tid]["sequence_sha256"]

    # Section 4: duplicates
    by_seq: Dict[str, List[str]] = defaultdict(list)
    for tid in trajectory_ids:
        if tid in rows_by_tid:
            by_seq[rows_by_tid[tid]["sequence"]].append(tid)
    duplicates = {s: ts for s, ts in by_seq.items() if len(ts) > 1}

    # Hashes of key inputs
    input_hashes = {
        "trajectories_csv": sha256_file(trajectories_csv),
        "manifest_json":    sha256_file(manifest_path),
        "raw_attempts_jsonl": sha256_file(raw_path),
    }

    report = {
        "corpus_dir": corpus_dir,
        "source_run_dir": source_run_dir,
        "source_method": source_method,
        "trajectory_count": len(trajectory_ids),
        "hard_errors": hard_errors,
        "input_hashes": input_hashes,
        "per_trajectory": per_traj,
        "duplicates": duplicates,
        "manifest_experiment_tag": manifest.get("experiment_tag"),
        "manifest_prompt_version": manifest.get("prompt_version"),
    }
    assert not hard_errors, f"audit hard errors: {hard_errors[:5]} (total {len(hard_errors)})"
    return report


def write_audit_outputs(audit_report: Dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "source_audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    with open(os.path.join(out_dir, "input_hashes.json"), "w", encoding="utf-8") as f:
        json.dump(audit_report["input_hashes"], f, indent=2)
    # provider audit CSV
    with open(os.path.join(out_dir, "source_provider_audit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trajectory_id", "model", "split", "n_valid_attempts",
                    "n_steps_with_retry", "providers_accepted", "returned_ids_accepted"])
        for tid, p in sorted(audit_report["per_trajectory"].items()):
            w.writerow([tid, p["model"], p["split"], p["n_valid_attempts"],
                        p["n_steps_with_retry"],
                        json.dumps(p["providers_accepted"], sort_keys=True),
                        json.dumps(p["returned_ids_accepted"], sort_keys=True)])
    # duplicates CSV
    with open(os.path.join(out_dir, "duplicate_sequence_audit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sequence_sha256", "trajectory_ids", "n"])
        for seq, tids in sorted(audit_report["duplicates"].items()):
            w.writerow([sha256_text(seq), ";".join(sorted(tids)), len(tids)])
