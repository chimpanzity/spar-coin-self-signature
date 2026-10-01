"""Task-validation study: is the A-position bias specific to source attribution?

Design (per reviewer proposal):
- Reuse the exact same 60 corpus-pair sequences as FCE1/FCE2 (independent_calls
  trajectories; the method with the sharpest objective differences across models).
- Each pair is asked TWICE: once in its natural A/B order from the pair manifest,
  once with A/B reversed. Everything else is held fixed.
- Each (pair, ordering) is asked TWO objective questions, each with a
  deterministic correct answer:
    Q1 "more_H":        which sequence contains more H outcomes
    Q2 "more_switches": which sequence has more switches between H and T
- 3 judges × 60 pairs × 2 orderings × 2 questions = 720 trials.
- Same judge client config as FCE1/FCE2: temperature 0, strict A/B parser,
  per-judge reasoning config, provider pins, worst-case cost ledger.

If judges accurately pick the correct sequence on these objective comparisons,
the A-position bias observed in source-attribution trials is task-specific and
scientifically meaningful. If judges still answer A nearly categorically on
these objective questions, the A/B forced-choice format itself is unusable for
them and the FCE1/FCE2 source-attribution results are confounded by format bias.
"""

import argparse, csv, hashlib, json, os, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from . import config as F
from .runner import (CostLedger, make_openrouter_client, snapshot_prices,
                     process_lock, worst_case_cost, _append_jsonl,
                     _write_json_atomic, _read_json, parse_ab,
                     judge_request_config_hash, _run_one_trial)
from .pairs import Pair, load_trials_from_manifest  # just to reuse helpers; we build our own trials


EXPERIMENT_NAME = "full_corpus_validation"


# ------------------------------- data types -------------------------------

@dataclass(frozen=True)
class ValidationTrial:
    trial_id: str                       # pair_id:ordering:question|judge
    pair_id: str
    triplet_id: str
    split: str                          # "development" | "holdout"
    ordering: str                       # "natural" | "reversed"
    question: str                       # "more_H" | "more_switches"
    judge_label: str
    sequence_A_id: str
    sequence_B_id: str
    sequence_A: str                     # as displayed
    sequence_B: str                     # as displayed
    correct_answer: str                 # "A", "B", or "TIE" when exactly equal


# ------------------------------- prompts -----------------------------------

QUESTION_TEXT = {
    "more_H":        "has more H outcomes",
    "more_switches": "has more switches between H and T",
}


VALIDATION_PROMPT_TEMPLATE = """\
Each sequence below is a string of 100 H and T characters.

Sequence A:
{SEQ_A}

Sequence B:
{SEQ_B}

Which sequence {QUESTION_TEXT}?

Respond with exactly one character on its own line — no explanation, no reasoning, no punctuation.

A

or

B
"""


def build_prompt(trial: ValidationTrial) -> str:
    return VALIDATION_PROMPT_TEMPLATE.format(
        SEQ_A=trial.sequence_A, SEQ_B=trial.sequence_B,
        QUESTION_TEXT=QUESTION_TEXT[trial.question])


# ------------------------------- objective ground truth ---------------------

def _count_H(seq: str) -> int:
    return seq.count("H")


def _count_switches(seq: str) -> int:
    return sum(1 for i in range(1, len(seq)) if seq[i] != seq[i-1])


def correct_answer_for(seq_a: str, seq_b: str, question: str) -> str:
    if question == "more_H":
        va, vb = _count_H(seq_a), _count_H(seq_b)
    elif question == "more_switches":
        va, vb = _count_switches(seq_a), _count_switches(seq_b)
    else:
        raise ValueError(f"unknown question {question}")
    if va > vb: return "A"
    if vb > va: return "B"
    return "TIE"


# ------------------------------- trial construction ------------------------

def build_validation_trials(pair_rows: List[Dict], seq_lookup: Dict[str, str]
                            ) -> List[ValidationTrial]:
    """Build all 720 validation trials from a saved pair_manifest.csv + a
    trajectory_id -> sequence lookup (filtered to the chosen source_method).
    """
    trials: List[ValidationTrial] = []
    for p in pair_rows:
        A_id, B_id = p["sequence_A_id"], p["sequence_B_id"]
        seq_a, seq_b = seq_lookup[A_id], seq_lookup[B_id]
        for ordering in ("natural", "reversed"):
            if ordering == "natural":
                disp_A_id, disp_B_id, disp_a, disp_b = A_id, B_id, seq_a, seq_b
            else:
                disp_A_id, disp_B_id, disp_a, disp_b = B_id, A_id, seq_b, seq_a
            for question in ("more_H", "more_switches"):
                correct = correct_answer_for(disp_a, disp_b, question)
                for judge in F.JUDGE_LABELS:
                    tid = f"{p['pair_id']}:{ordering}:{question}|{judge}"
                    trials.append(ValidationTrial(
                        trial_id=tid, pair_id=p["pair_id"], triplet_id=p["triplet_id"],
                        split=p["split"], ordering=ordering, question=question,
                        judge_label=judge,
                        sequence_A_id=disp_A_id, sequence_B_id=disp_B_id,
                        sequence_A=disp_a, sequence_B=disp_b,
                        correct_answer=correct,
                    ))
    return trials


# ------------------------------- writers -----------------------------------

def write_trial_manifest(path: str, trials: List[ValidationTrial]):
    fields = ["trial_id","pair_id","triplet_id","split","ordering","question",
              "judge_label","sequence_A_id","sequence_B_id","correct_answer"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for t in trials:
            w.writerow({k: getattr(t, k) for k in fields})


def write_prompts_jsonl(path: str, trials: List[ValidationTrial]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for t in trials:
            text = build_prompt(t)
            f.write(json.dumps({
                "trial_id": t.trial_id,
                "prompt_hash": hashlib.sha256(text.encode()).hexdigest(),
                "prompt_text": text,
            }) + "\n")


# ------------------------------- adapter for _run_one_trial ---------------

def _trial_adapter(vt: ValidationTrial):
    """_run_one_trial expects a Trial with build_prompt(trial, source_method).
    We construct a tiny shim object with the attributes needed by build_prompt
    AND set an attribute pattern that lets our validation build_prompt be
    chosen instead of pairs.build_prompt."""
    class _T: pass
    t = _T()
    for f in ("trial_id","target_label","distractor_label","wording_condition",
              "sequence_A","sequence_B","pair_id","triplet_id","split",
              "source_label_A","source_label_B","sequence_A_id","sequence_B_id",
              "source_pair_type","judge_label","target_item_id","judge_role",
              "correct_answer"):
        setattr(t, f, "")
    # Fields referenced by prompt
    t.trial_id = vt.trial_id
    t.sequence_A = vt.sequence_A
    t.sequence_B = vt.sequence_B
    t.correct_answer = vt.correct_answer
    return t


# ------------------------------- runner ------------------------------------

def _run_validation_trials(client: OpenAI, trials: List[ValidationTrial],
                            run_dir: str, prices: Dict, provider_pins: Dict,
                            cap_usd: float, log=print,
                            max_tokens: int = F.INITIAL_MAX_TOKENS) -> Dict:
    """Variant of orchestration.run_scored tailored to validation trials.

    Builds its own prompt (not from pairs.build_prompt). Reuses the FCE1
    runner machinery: strict A/B parser, worst-case cost reservation, same
    judge client config, same per-judge reasoning.
    """
    import threading
    from .orchestration import load_outcomes, save_outcomes, load_ledger, save_ledger

    outcomes = load_outcomes(run_dir)
    ledger = load_ledger(run_dir, cap_usd)
    log(f"[scored] start with {len(outcomes)} prior outcomes spent=${ledger.spent_usd:.4f} cap=${cap_usd:.2f}")

    done = {tid for tid, o in outcomes.items() if o.get("status") == "ok"}
    pending = [t for t in trials if t.trial_id not in done]
    log(f"[scored] pending={len(pending)}")

    judge_locks = {j: threading.Lock() for j in F.JUDGE_LABELS}
    outcomes_lock = threading.Lock()
    ledger_lock = threading.Lock()

    def _work(vt: ValidationTrial):
        judge = F.JUDGE_BY_LABEL[vt.judge_label]
        price = prices.get(judge.slug, {"prompt": 0.0, "completion": 0.0})
        req_hash = judge_request_config_hash(max_tokens, provider_pins.get(vt.judge_label),
                                              judge_label=vt.judge_label,
                                              source_method="validation")
        prompt_text = build_prompt(vt)
        with judge_locks[vt.judge_label]:
            # Reserve + call directly (not via _run_one_trial which uses
            # pairs.build_prompt). Simplified: 1 response-attempt policy with
            # 3 retries for invalid output, same backoff.
            outcome = _one_trial_direct(vt, judge, provider_pins.get(vt.judge_label),
                                         client, prompt_text, max_tokens,
                                         run_dir, ledger, ledger_lock, price,
                                         req_hash)
            with outcomes_lock:
                outcomes[vt.trial_id] = outcome
                save_outcomes(run_dir, outcomes)
            with ledger_lock:
                save_ledger(run_dir, ledger)
            return outcome

    completed = 0
    with ThreadPoolExecutor(max_workers=F.CONCURRENCY_OVERALL) as pool:
        futs = {pool.submit(_work, t): t for t in pending}
        for fut in as_completed(futs):
            res = fut.result()
            completed += 1
            if completed % 20 == 0 or res["status"] != "ok":
                log(f"[scored] {completed}/{len(pending)} done "
                    f"(spent=${ledger.spent_usd:.4f} last={res['trial_id'][:60]} status={res['status']})")

    final = load_outcomes(run_dir)
    summary = {"n_outcomes": len(final),
               "n_ok": sum(1 for o in final.values() if o["status"] == "ok"),
               "n_abandoned": sum(1 for o in final.values() if o["status"] == "abandoned"),
               "spent_usd": ledger.spent_usd}
    log(f"[scored] FINAL: {summary}")
    return summary


def _one_trial_direct(vt: ValidationTrial, judge: F.JudgeSpec,
                       provider_pin: Optional[str], client: OpenAI,
                       prompt_text: str, max_tokens: int, run_dir: str,
                       ledger: CostLedger, ledger_lock, price: Dict[str, float],
                       request_config_hash: str) -> Dict:
    """Simplified single-trial runner for validation (no retry-with-identical
    prompt; just transport-level retries via the OpenAI client's own)."""
    from .runner import _call_judge, _cost_usd
    raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
    phash = hashlib.sha256(prompt_text.encode()).hexdigest()
    total_cost = 0.0
    first_valid = None
    reasoning_toks = 0; completion_toks = 0; lat = 0
    provider = ""; served = ""
    for attempt in range(1, F.RESPONSE_ATTEMPT_CAP + 1):
        reservation = worst_case_cost(prompt_text, max_tokens, price)
        with ledger_lock:
            if not ledger.reserve(reservation):
                return {"trial_id": vt.trial_id, "status": "abandoned",
                        "visible_answer": None, "correct": None,
                        "attempts": attempt, "first_attempt_valid": first_valid,
                        "total_cost_usd": total_cost,
                        "returned_model_id": served, "provider": provider,
                        "reasoning_tokens_total": reasoning_toks,
                        "completion_tokens_total": completion_toks,
                        "latency_ms_total": lat,
                        "missing_reason": "budget_cap_prevents_dispatch"}
        r = _call_judge(client, judge, prompt_text, max_tokens, provider_pin)
        cost = _cost_usd(r["prompt_tokens"], r["completion_tokens"],
                         r["reasoning_tokens"], price)
        with ledger_lock:
            ledger.commit(cost, reservation)
        total_cost += cost
        reasoning_toks += r["reasoning_tokens"]
        completion_toks += r["completion_tokens"]
        lat += r["latency_ms"]
        if r["served_model"] and not served: served = r["served_model"]
        if r["provider"] and not provider: provider = r["provider"]
        parsed = parse_ab(r["raw_text"]) if r["error"] == "" else None
        _append_jsonl(raw_path, {
            "experiment_name": EXPERIMENT_NAME, "kind": "scored",
            "trial_id": vt.trial_id, "attempt_number": attempt,
            "prompt_hash": phash,
            "requested_judge_model_id": judge.slug,
            "returned_model_id": r["served_model"], "provider": r["provider"],
            "request_id": r["request_id"], "generation_id": r["generation_id"],
            "raw_visible_content": r["raw_text"], "finish_reason": r["finish_reason"],
            "parsed_answer": parsed, "valid": parsed is not None,
            "error": r["error"],
            "input_tokens": r["prompt_tokens"], "output_tokens": r["completion_tokens"],
            "reasoning_tokens": r["reasoning_tokens"], "latency_ms": r["latency_ms"],
            "cost_usd": cost,
            "cost_status": "billed" if r["error"] == "" else "uncertain",
            "judge_request_config_hash": request_config_hash,
            "question": vt.question, "ordering": vt.ordering,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        if attempt == 1: first_valid = (parsed is not None)
        if parsed is not None:
            correct = None if vt.correct_answer == "TIE" else (parsed == vt.correct_answer)
            return {"trial_id": vt.trial_id, "status": "ok",
                    "visible_answer": parsed, "correct": correct,
                    "attempts": attempt, "first_attempt_valid": first_valid,
                    "total_cost_usd": total_cost, "returned_model_id": served,
                    "provider": provider,
                    "reasoning_tokens_total": reasoning_toks,
                    "completion_tokens_total": completion_toks,
                    "latency_ms_total": lat, "missing_reason": ""}
    return {"trial_id": vt.trial_id, "status": "abandoned",
            "visible_answer": None, "correct": None,
            "attempts": F.RESPONSE_ATTEMPT_CAP, "first_attempt_valid": first_valid,
            "total_cost_usd": total_cost, "returned_model_id": served,
            "provider": provider, "reasoning_tokens_total": reasoning_toks,
            "completion_tokens_total": completion_toks,
            "latency_ms_total": lat, "missing_reason": "exhausted_response_attempts"}


# ------------------------------- analysis ----------------------------------

def write_trial_level(path: str, trials: List[ValidationTrial],
                      outcomes: Dict[str, Dict]):
    rows = []
    for t in trials:
        o = outcomes.get(t.trial_id, {})
        rows.append({
            **{k: getattr(t, k) for k in (
                "trial_id","pair_id","triplet_id","split","ordering","question",
                "judge_label","sequence_A_id","sequence_B_id","correct_answer",
            )},
            "status": o.get("status", "pending"),
            "visible_answer": o.get("visible_answer"),
            "correct": o.get("correct"),
            "first_attempt_valid": o.get("first_attempt_valid"),
            "total_cost_usd": o.get("total_cost_usd", 0.0),
            "returned_model_id": o.get("returned_model_id", ""),
            "provider": o.get("provider", ""),
        })
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write("")
        return rows
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows: w.writerow(r)
    return rows


def summarize(rows: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Per (judge, question, split) accuracy + position rate.
    Plus per (judge, question, split, ordering) breakdown."""
    def _acc(subset):
        done = [r for r in subset if r["status"] == "ok" and r["visible_answer"] in ("A", "B")]
        scorable = [r for r in done if r["correct_answer"] in ("A", "B")]
        if not scorable: return (None, 0, 0)
        correct = sum(1 for r in scorable if str(r["correct"]) == "True")
        return (correct / len(scorable), len(scorable), len(done))

    def _a_rate(subset):
        done = [r for r in subset if r["status"] == "ok" and r["visible_answer"] in ("A", "B")]
        if not done: return None
        return sum(1 for r in done if r["visible_answer"] == "A") / len(done)

    main = []
    for judge in F.JUDGE_LABELS:
        for question in ("more_H", "more_switches"):
            for split in ("development", "holdout"):
                subset = [r for r in rows if r["judge_label"] == judge
                          and r["question"] == question and r["split"] == split]
                acc, n_scorable, n_done = _acc(subset)
                main.append({
                    "judge": judge, "question": question, "split": split,
                    "n_planned": len(subset), "n_scored_nontie": n_scorable,
                    "n_responded": n_done,
                    "accuracy_on_nontie": None if acc is None else round(acc, 4),
                    "a_response_rate": None if _a_rate(subset) is None else round(_a_rate(subset), 4),
                })
    byorder = []
    for judge in F.JUDGE_LABELS:
        for question in ("more_H", "more_switches"):
            for split in ("development", "holdout"):
                for ordering in ("natural", "reversed"):
                    subset = [r for r in rows if r["judge_label"] == judge
                              and r["question"] == question
                              and r["split"] == split and r["ordering"] == ordering]
                    acc, n_scorable, n_done = _acc(subset)
                    byorder.append({
                        "judge": judge, "question": question, "split": split,
                        "ordering": ordering, "n_planned": len(subset),
                        "n_scored_nontie": n_scorable, "n_responded": n_done,
                        "accuracy_on_nontie": None if acc is None else round(acc, 4),
                        "a_response_rate": None if _a_rate(subset) is None else round(_a_rate(subset), 4),
                    })
    return main, byorder


def _write_rows(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f: f.write("")
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow(r)


# ------------------------------- CLI ---------------------------------------

def _ts(): return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
def _utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log_writer(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8", buffering=1)
    def log(msg):
        line = f"[{_utc()}] {msg}"
        print(line, flush=True); f.write(line + "\n"); f.flush()
    return log, f


DEFAULT_CORPUS_DIR = "data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/results/corpus"


def _load_corpus_seq_lookup(corpus_dir: str, source_method: str) -> Dict[str, str]:
    out = {}
    with open(os.path.join(corpus_dir, "trajectories.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["method"] == source_method:
                out[r["trajectory_id"]] = r["sequence"]
    return out


def _load_pair_rows(fce_run_dir: str) -> List[Dict]:
    with open(os.path.join(fce_run_dir, "pair_manifest.csv"), "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cmd_dry_run(args):
    run_dir = os.path.join(args.data_root, EXPERIMENT_NAME,
                            args.run_id or f"validation-{_ts()}-dry")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "validation.log"))
    log(f"START dry-run run_dir={run_dir} source_method={args.source_method}")
    seq = _load_corpus_seq_lookup(args.corpus_dir, args.source_method)
    pair_rows = _load_pair_rows(args.fce_run_dir)
    trials = build_validation_trials(pair_rows, seq)
    log(f"built {len(trials)} trials from {len(pair_rows)} pairs")
    write_trial_manifest(os.path.join(run_dir, "trial_manifest.csv"), trials)
    write_prompts_jsonl(os.path.join(run_dir, "prompts.jsonl"), trials)
    # Sanity: distribution of correct answers across judge-independent axes
    c = Counter(t.correct_answer for t in trials)
    log(f"correct_answer distribution: {dict(c)}")
    # Non-tie rate per question
    for q in ("more_H","more_switches"):
        qt = [t for t in trials if t.question == q]
        n_tie = sum(1 for t in qt if t.correct_answer == "TIE")
        log(f"  question={q}: {len(qt)} trials, {n_tie} ties")


def cmd_run(args):
    assert args.live and args.yes, "require --live --yes"
    run_dir = os.path.join(args.data_root, EXPERIMENT_NAME,
                            args.run_id or f"validation-{_ts()}")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "validation.log"))
    log(f"START run run_dir={run_dir} source_method={args.source_method} "
        f"budget_cap=${args.budget_usd:.2f}")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)
    seq = _load_corpus_seq_lookup(args.corpus_dir, args.source_method)
    pair_rows = _load_pair_rows(args.fce_run_dir)
    trials = build_validation_trials(pair_rows, seq)
    log(f"built {len(trials)} trials")
    write_trial_manifest(os.path.join(run_dir, "trial_manifest.csv"), trials)
    write_prompts_jsonl(os.path.join(run_dir, "prompts.jsonl"), trials)

    prices = snapshot_prices(client)
    provider_pins = {j.label: j.preferred_provider for j in F.JUDGES}
    with open(os.path.join(run_dir, "config_frozen.json"), "w") as f:
        json.dump({"experiment": EXPERIMENT_NAME,
                   "source_method": args.source_method,
                   "fce_run_dir": args.fce_run_dir,
                   "pair_count": len(pair_rows),
                   "trial_count": len(trials),
                   "temperature": F.TEMPERATURE,
                   "max_tokens": F.INITIAL_MAX_TOKENS,
                   "reasoning_per_judge": F.REASONING_PER_JUDGE,
                   "provider_pins": provider_pins,
                   "budget_usd_cap": args.budget_usd,
                   }, f, indent=2, sort_keys=True)

    lock_path = os.path.join(run_dir, ".lock")
    with process_lock(lock_path):
        summary = _run_validation_trials(client, trials, run_dir,
                                          prices, provider_pins,
                                          cap_usd=args.budget_usd, log=log)
    log(f"DONE {summary}")


def cmd_analyze(args):
    run_dir = args.run_dir
    log, _ = _log_writer(os.path.join(run_dir, "logs", "validation.log"))
    log(f"ANALYZE run_dir={run_dir}")
    # Rehydrate trials from the saved manifest
    tm_path = os.path.join(run_dir, "trial_manifest.csv")
    assert os.path.exists(tm_path), f"no trial_manifest.csv at {tm_path}"
    seq = _load_corpus_seq_lookup(args.corpus_dir, args.source_method)
    trials: List[ValidationTrial] = []
    with open(tm_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # Reconstruct sequence_A/sequence_B from the ids via corpus (same
            # ordering as the live run because sequence_A_id was recorded).
            trials.append(ValidationTrial(
                trial_id=r["trial_id"], pair_id=r["pair_id"],
                triplet_id=r["triplet_id"], split=r["split"],
                ordering=r["ordering"], question=r["question"],
                judge_label=r["judge_label"],
                sequence_A_id=r["sequence_A_id"], sequence_B_id=r["sequence_B_id"],
                sequence_A=seq[r["sequence_A_id"]], sequence_B=seq[r["sequence_B_id"]],
                correct_answer=r["correct_answer"],
            ))
    outcomes = _read_json(os.path.join(run_dir, "trial_outcomes.json"), {})
    rows = write_trial_level(os.path.join(run_dir, "trial_level.csv"),
                              trials, outcomes)
    main, byorder = summarize(rows)
    _write_rows(os.path.join(run_dir, "summary_by_judge_question_split.csv"), main)
    _write_rows(os.path.join(run_dir, "summary_by_ordering.csv"), byorder)
    log("wrote trial_level.csv, summary_by_judge_question_split.csv, summary_by_ordering.csv")


def main():
    ap = argparse.ArgumentParser(prog="python -m spar_dynamic.full_corpus_exp1.validation")
    sub = ap.add_subparsers(dest="cmd", required=True)
    def _common(sp):
        sp.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
        sp.add_argument("--source-method", default="independent_calls",
                        choices=F.ALLOWED_SOURCE_METHODS)
        sp.add_argument("--fce-run-dir", required=True,
                        help="an FCE1/FCE2 run dir whose pair_manifest.csv names "
                             "the 60 pairs to reuse for this validation study")
        sp.add_argument("--data-root", default="data/spar_dynamic")
        sp.add_argument("--run-id", default="")

    sp = sub.add_parser("dry-run"); _common(sp); sp.set_defaults(func=cmd_dry_run)
    sp = sub.add_parser("run"); _common(sp)
    sp.add_argument("--live", action="store_true", required=True)
    sp.add_argument("--yes", action="store_true", required=True)
    sp.add_argument("--budget-usd", type=float, default=10.0)
    sp.set_defaults(func=cmd_run)
    sp = sub.add_parser("analyze")
    sp.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    sp.add_argument("--source-method", default="independent_calls",
                     choices=F.ALLOWED_SOURCE_METHODS)
    sp.add_argument("--run-dir", required=True)
    sp.set_defaults(func=cmd_analyze)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
