"""Top-level orchestration: preflight, scored collection, resume logic."""

import csv, json, os, random, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from . import config as F
from .pairs import Trial, build_prompt
from .runner import (CostLedger, TrialOutcome, _append_jsonl, _run_one_trial,
                     _write_json_atomic, _read_json, judge_request_config_hash,
                     snapshot_prices)


# -- Outcome store ------------------------------------------------------------
def _outcomes_path(run_dir: str) -> str:
    return os.path.join(run_dir, "trial_outcomes.json")


def load_outcomes(run_dir: str) -> Dict[str, Dict]:
    return _read_json(_outcomes_path(run_dir), {})


def save_outcomes(run_dir: str, outcomes: Dict[str, Dict]):
    _write_json_atomic(_outcomes_path(run_dir), outcomes)


def _ledger_path(run_dir: str) -> str:
    return os.path.join(run_dir, "cost_ledger.json")


def load_ledger(run_dir: str, cap_usd: float) -> CostLedger:
    d = _read_json(_ledger_path(run_dir), None)
    if d is None:
        return CostLedger(cap_usd=cap_usd)
    return CostLedger(cap_usd=cap_usd,
                      spent_usd=float(d.get("spent_usd", 0.0)),
                      reserved_usd=0.0)   # reservations don't survive a restart


def save_ledger(run_dir: str, ledger: CostLedger):
    _write_json_atomic(_ledger_path(run_dir), ledger.to_dict())


# -- Resume policy -----------------------------------------------------------
def _done_trial_ids(outcomes: Dict[str, Dict]) -> set:
    return {tid for tid, o in outcomes.items() if o.get("status") == "ok"}


# -- Execution order (section 14) --------------------------------------------
def execution_order(trials: List[Trial], seed: int = F.EXECUTION_SEED) -> List[Trial]:
    """Shuffle trials across judges/targets/wordings/splits, avoiding immediate
    repetition of a pair within a judge where feasible."""
    rng = random.Random(seed)
    pool = list(trials)
    rng.shuffle(pool)
    # soft constraint: nudge away from back-to-back same (judge, pair)
    out: List[Trial] = []
    recent: Dict[str, str] = {}  # judge_label -> last pair_id
    deferred: List[Trial] = []
    while pool or deferred:
        candidate_pool = (pool + deferred) if pool else list(deferred)
        if deferred and not pool:
            deferred = []
        picked = None
        # Try to pick from pool first
        for i, t in enumerate(pool):
            if recent.get(t.judge_label) != t.pair_id:
                picked = pool.pop(i); break
        if picked is None and deferred:
            picked = deferred.pop(0)
        if picked is None and pool:
            picked = pool.pop(0)
        if picked is None:
            break
        if recent.get(picked.judge_label) == picked.pair_id and len(pool) > 0:
            # push to deferred; try again later
            deferred.append(picked)
            continue
        out.append(picked)
        recent[picked.judge_label] = picked.pair_id
    return out


# -- Preflight (section 12) --------------------------------------------------
def preflight_trial_subset(trials: List[Trial]) -> List[Trial]:
    """Pick a 12-trial subset: for each judge, 2 target-NAMED + 2 matching SELF
    trials from the development split, covering both competitors.
    """
    dev = [t for t in trials if t.split == "development"]
    picked: List[Trial] = []
    for judge in F.JUDGE_LABELS:
        for target in [judge]:  # named-self-target: judge == target
            for competitor in [c for c in F.JUDGE_LABELS if c != judge]:
                # one NAMED trial where judge==target and distractor==competitor
                named = next((t for t in dev
                              if t.wording_condition == "NAMED"
                              and t.judge_label == judge
                              and t.target_label == target
                              and t.distractor_label == competitor), None)
                selfv = next((t for t in dev
                              if t.wording_condition == "SELF"
                              and t.judge_label == judge
                              and t.target_label == target
                              and t.distractor_label == competitor), None)
                if named is not None: picked.append(named)
                if selfv is not None: picked.append(selfv)
    return picked


def run_preflight(client: OpenAI, trials: List[Trial], run_dir: str,
                  prices: Dict[str, Dict[str, float]], provider_pins: Dict[str, Optional[str]],
                  cap_usd: float, log=print,
                  source_method: str = F.SOURCE_METHOD) -> Dict:
    pre_subset = preflight_trial_subset(trials)
    log(f"[preflight] running {len(pre_subset)} trials source_method={source_method}")
    ledger = load_ledger(run_dir, cap_usd)
    results: List[TrialOutcome] = []
    for t in pre_subset:
        judge = F.JUDGE_BY_LABEL[t.judge_label]
        price = prices.get(judge.slug, {"prompt": 0.0, "completion": 0.0})
        req_hash = judge_request_config_hash(F.INITIAL_MAX_TOKENS,
                                              provider_pins.get(t.judge_label),
                                              judge_label=t.judge_label,
                                              source_method=source_method)
        outcome = _run_one_trial(t, judge, provider_pins.get(t.judge_label),
                                 client, F.INITIAL_MAX_TOKENS, run_dir, ledger,
                                 price, kind="preflight",
                                 request_config_hash=req_hash,
                                 source_method=source_method)
        save_ledger(run_dir, ledger)
        log(f"[preflight]   {t.trial_id[:60]} -> status={outcome.status} answer={outcome.visible_answer} "
            f"attempts={outcome.attempts} r_toks={outcome.reasoning_tokens_total} "
            f"c_toks={outcome.completion_tokens_total} cost=${outcome.total_cost_usd:.4f}")
        results.append(outcome)
    # Section 12: all 12 must be valid; at least 11 first-attempt valid
    n_valid = sum(1 for r in results if r.status == "ok")
    n_first_valid = sum(1 for r in results if r.first_attempt_valid)
    summary = {
        "n": len(results),
        "n_valid": n_valid,
        "n_first_attempt_valid": n_first_valid,
        "total_cost_usd": sum(r.total_cost_usd for r in results),
        "passes": n_valid == len(results) and n_first_valid >= max(0, len(results) - 1),
        "per_judge_truncated": [r.trial_id for r in results if r.status == "ok"
                                 and r.first_attempt_valid is False],
    }
    _write_json_atomic(os.path.join(run_dir, "preflight_summary.json"),
                       {"summary": summary,
                        "per_trial": [asdict(r) for r in results]})
    log(f"[preflight] summary: valid {n_valid}/{len(results)} "
        f"first_attempt {n_first_valid}/{len(results)} "
        f"spend=${ledger.spent_usd:.4f}  passes={summary['passes']}")
    return summary


# -- Scored collection (section 14) ------------------------------------------
def run_scored(client: OpenAI, trials: List[Trial], run_dir: str,
               prices: Dict[str, Dict[str, float]],
               provider_pins: Dict[str, Optional[str]],
               max_tokens: int, cap_usd: float,
               log=print,
               source_method: str = F.SOURCE_METHOD) -> Dict:
    outcomes = load_outcomes(run_dir)
    ledger = load_ledger(run_dir, cap_usd)
    log(f"[scored] starting with {len(outcomes)} prior trial outcomes, "
        f"spent=${ledger.spent_usd:.4f}, cap=${cap_usd:.2f}")

    done = _done_trial_ids(outcomes)
    pending = [t for t in trials if t.trial_id not in done]
    pending = execution_order(pending)

    # Simple semaphore via one lock per judge; overall cap via thread pool
    import threading
    judge_locks: Dict[str, threading.Lock] = {j: threading.Lock() for j in F.JUDGE_LABELS}
    outcomes_lock = threading.Lock()
    ledger_lock = threading.Lock()
    stop_flag = {"stop": False}
    judge_recent_fails: Dict[str, int] = {j: 0 for j in F.JUDGE_LABELS}

    def _work(t: Trial):
        if stop_flag["stop"]: return None
        judge = F.JUDGE_BY_LABEL[t.judge_label]
        price = prices.get(judge.slug, {"prompt": 0.0, "completion": 0.0})
        req_hash = judge_request_config_hash(max_tokens, provider_pins.get(t.judge_label),
                                              judge_label=t.judge_label,
                                              source_method=source_method)
        with judge_locks[t.judge_label]:
            with ledger_lock:
                # Pre-check (worst case) before dispatch
                if not ledger.can_reserve(0):
                    stop_flag["stop"] = True
                    return None
            outcome = _run_one_trial(t, judge, provider_pins.get(t.judge_label),
                                     client, max_tokens, run_dir, ledger,
                                     price, kind="scored",
                                     request_config_hash=req_hash,
                                     source_method=source_method)
            with ledger_lock:
                save_ledger(run_dir, ledger)
            with outcomes_lock:
                outcomes[t.trial_id] = asdict(outcome)
                save_outcomes(run_dir, outcomes)
                if outcome.status == "abandoned" and outcome.missing_reason != "budget_cap_prevents_dispatch":
                    judge_recent_fails[t.judge_label] += 1
                else:
                    judge_recent_fails[t.judge_label] = 0
                if judge_recent_fails[t.judge_label] >= F.ABANDON_CONSEC_CAP:
                    stop_flag["stop"] = True
                    log(f"[scored] stop: judge {t.judge_label} hit {F.ABANDON_CONSEC_CAP} consec abandons")
            return outcome

    completed = 0
    with ThreadPoolExecutor(max_workers=F.CONCURRENCY_OVERALL) as pool:
        futs = {pool.submit(_work, t): t for t in pending}
        for fut in as_completed(futs):
            res = fut.result()
            if res is None: continue
            completed += 1
            if completed % 10 == 0 or res.status != "ok":
                log(f"[scored] {completed}/{len(pending)} done "
                    f"(spent=${ledger.spent_usd:.4f}  last={res.trial_id[:60]} "
                    f"status={res.status})")

    final = load_outcomes(run_dir)
    summary = {
        "n_outcomes": len(final),
        "n_ok": sum(1 for o in final.values() if o["status"] == "ok"),
        "n_abandoned": sum(1 for o in final.values() if o["status"] == "abandoned"),
        "spent_usd": ledger.spent_usd,
    }
    log(f"[scored] FINAL: {summary}")
    return summary


# -- Dry-run (no API calls) --------------------------------------------------
def dry_run(trials: List[Trial], run_dir: str, log=print,
            source_method: str = F.SOURCE_METHOD) -> Dict:
    """Smoke everything short of actual API calls: build prompts, hash them,
    check manifest invariants, write prompts.jsonl. No cost."""
    from .pairs import write_prompts_jsonl
    prompts_path = os.path.join(run_dir, "prompts.jsonl")
    write_prompts_jsonl(prompts_path, trials, source_method=source_method)
    log(f"[dry-run] wrote {len(trials)} prompts to {prompts_path}")
    # Minimal invariant check: NAMED prompts for same (pair_id, target_label) must be identical across judges
    from collections import defaultdict
    import hashlib
    named_hashes: Dict[tuple, set] = defaultdict(set)
    for t in trials:
        if t.wording_condition == "NAMED":
            h = hashlib.sha256(build_prompt(t, source_method=source_method).encode()).hexdigest()
            named_hashes[(t.pair_id, t.target_label)].add(h)
    bad = [k for k, s in named_hashes.items() if len(s) != 1]
    assert not bad, f"NAMED prompt not byte-identical across judges for: {bad[:5]}"
    log(f"[dry-run] NAMED prompt-identity check passed on {len(named_hashes)} (pair, target) items")
    # Also verify the prefix actually matches source_method
    sample_prompt = build_prompt(trials[0], source_method=source_method)
    expected_prefix = F.SHARED_PROTOCOL_PREFIX_BY_METHOD[source_method]
    assert sample_prompt.startswith(expected_prefix), \
        f"build_prompt did not select the {source_method} prefix"
    log(f"[dry-run] source_method prefix check passed (prefix matches {source_method})")
    return {"n_trials": len(trials), "n_named_targets": len(named_hashes)}
