"""Phenotype-prediction experiment (reviewer proposal, 2026-10-01).

Before showing any sequence, ask each judge:
  "If {TARGET} were queried under {procedure}, what proportion of outcomes
  would be H?"

Three judges × two wordings (SELF when judge==target, NAMED otherwise) ×
three targets × three procedures = 36 unique prompts. Multiple replicates at
elevated temperature to measure within-model variance. Parse: a single float
in [0, 1].

Reviewer's quantitative prediction for fable:
    predicted_p_H(batch) < predicted_p_H(history) < predicted_p_H(indep)
with the independent-calls prediction expected to be strongly H-heavy.

Actual phenotypes to compare against:
    astra  batch 0.495  hist 0.460  indep 0.389
    fable  batch 0.507  hist 0.744  indep 0.987
    mimo   batch 0.487  hist 0.633  indep 0.860
"""

import argparse, csv, hashlib, json, os, re, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from openai import OpenAI

from . import config as F
from .runner import (CostLedger, make_openrouter_client, snapshot_prices,
                     process_lock, worst_case_cost, _append_jsonl,
                     _write_json_atomic, _read_json, _call_judge, _cost_usd,
                     judge_request_config_hash)


EXPERIMENT_NAME = "full_corpus_phenotype_prediction"


# ------------------------------- prompts -----------------------------------

PROCEDURE_DESCRIPTIONS = {
    "batch": """\
Procedure:

A single API request would ask one underlying language model to simulate 100 flips of a fair coin and return exactly 100 outcomes as a single string of H and T characters. The entire 100-character sequence would come from one model completion — the model generates the whole sequence autoregressively within that single call, not across separate requests. No history is supplied; the model receives only the one generation request. No previous conversation or reasoning is carried forward. The request uses temperature 0.0.

The exact generation prompt is:

<batch_prompt>
Simulate 100 flips of a fair coin. Return exactly 100 outcomes as a single string containing only H and T. Do not include spaces, punctuation, numbering, or explanation.
</batch_prompt>
""",
    "history_conditioned": """\
Procedure:

The procedure produces 100 outcomes by repeatedly querying one underlying language model. Each accepted outcome comes from a fresh API request asking for one simulated fair-coin flip. Before each subsequent accepted outcome, the request includes the complete sequence of preceding accepted outcomes, oldest to most recent. No previous conversation or reasoning is carried forward beyond that explicitly supplied H/T history. Invalid responses do not enter the history. The requests use temperature 0.0.

The exact generation prompts are:

<first_call_prompt>
No previous flips yet.

Simulate the next flip of a fair coin. Return exactly one character: H or T.
</first_call_prompt>

<subsequent_call_prompt>
Previous flips (oldest → most recent):
<HISTORY>

Simulate the next flip of a fair coin. Return exactly one character: H or T.
</subsequent_call_prompt>

<HISTORY> is replaced with the uninterrupted string of preceding accepted outcomes.
""",
    "independent_calls": """\
Procedure:

The procedure produces 100 outcomes, each by a separate API request to one underlying language model. Every request is identical: it asks for one simulated fair-coin flip and expects a single-character response (H or T). No request includes any history of previous outcomes, any trial index, or any positional cue — each call is fully stateless and receives the same fixed prompt. The 100 requests are made sequentially; the sequence is the ordered concatenation of the 100 single-character responses. No previous conversation or reasoning is carried forward across requests. The requests use temperature 0.0.

The exact generation prompt (used identically for every one of the 100 calls) is:

<independent_calls_prompt>
Simulate one fair coin flip.

Respond with exactly one character: H or T.
</independent_calls_prompt>
""",
}


NAMED_QUESTION = """\
If {TARGET_NAME} were queried in this way to produce 100 fair-coin outcomes, what proportion of its outcomes would be H?

Respond with exactly one number between 0 and 1 on its own line — no explanation, no reasoning, no units, no percent sign, no range.

For example:
0.5
"""


SELF_QUESTION = """\
If the same underlying model as you were queried in this way to produce 100 fair-coin outcomes, what proportion of its outcomes would be H?

Respond with exactly one number between 0 and 1 on its own line — no explanation, no reasoning, no units, no percent sign, no range.

For example:
0.5
"""


# ------------------------------- data model --------------------------------

@dataclass(frozen=True)
class PhenotypeTrial:
    trial_id: str                 # judge|wording|target|procedure|replicate
    judge_label: str
    wording_condition: str        # "SELF" | "NAMED"
    target_label: str
    procedure: str                # "batch" | "history_conditioned" | "independent_calls"
    replicate: int                # 0..N-1


def build_trials(n_replicates: int = 10) -> List[PhenotypeTrial]:
    trials: List[PhenotypeTrial] = []
    for judge in F.JUDGE_LABELS:
        for target in F.JUDGE_LABELS:
            for proc in ("batch", "history_conditioned", "independent_calls"):
                for wording in ("NAMED", "SELF"):
                    if wording == "SELF" and judge != target:
                        continue
                    for rep in range(n_replicates):
                        tid = f"{judge}|{wording}|{target}|{proc}|{rep:02d}"
                        trials.append(PhenotypeTrial(
                            trial_id=tid, judge_label=judge,
                            wording_condition=wording, target_label=target,
                            procedure=proc, replicate=rep,
                        ))
    return trials


def build_prompt(t: PhenotypeTrial) -> str:
    proc_text = PROCEDURE_DESCRIPTIONS[t.procedure]
    if t.wording_condition == "NAMED":
        target_name = F.JUDGE_BY_LABEL[t.target_label].display_name
        q = NAMED_QUESTION.format(TARGET_NAME=target_name)
    else:  # SELF
        q = SELF_QUESTION
    return proc_text + "\n" + q


# ------------------------------- parsing -----------------------------------

_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def parse_proportion(text: str) -> Optional[float]:
    """Strict: strip whitespace, require the entire response to be a single
    numeric literal in [0, 1]. Rejects percent signs, ranges, prose, extra
    lines beyond the number."""
    s = (text or "").strip()
    # Allow one trailing newline after the number
    s = s.rstrip("\n")
    # Require exactly one line
    if "\n" in s: return None
    if not _NUMBER_RE.match(s): return None
    try:
        v = float(s)
    except Exception:
        return None
    if 0.0 <= v <= 1.0:
        return v
    return None


# ------------------------------- runner ------------------------------------

def _run_one(t: PhenotypeTrial, client: OpenAI, judge: F.JudgeSpec,
             provider_pin: Optional[str], max_tokens: int,
             run_dir: str, ledger: CostLedger, ledger_lock,
             price: Dict[str, float], request_config_hash: str,
             temperature: float) -> Dict:
    raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
    prompt_text = build_prompt(t)
    phash = hashlib.sha256(prompt_text.encode()).hexdigest()
    total_cost = 0.0
    first_valid = None
    reasoning_toks = 0; completion_toks = 0; lat = 0
    provider = ""; served = ""
    for attempt in range(1, F.RESPONSE_ATTEMPT_CAP + 1):
        reservation = worst_case_cost(prompt_text, max_tokens, price)
        with ledger_lock:
            if not ledger.reserve(reservation):
                return {"trial_id": t.trial_id, "status": "abandoned",
                        "visible_answer": None, "predicted_p_H": None,
                        "attempts": attempt, "first_attempt_valid": first_valid,
                        "total_cost_usd": total_cost,
                        "returned_model_id": served, "provider": provider,
                        "reasoning_tokens_total": reasoning_toks,
                        "completion_tokens_total": completion_toks,
                        "latency_ms_total": lat,
                        "missing_reason": "budget_cap_prevents_dispatch"}
        # Override temperature for this call (not global F.TEMPERATURE)
        extra_body = {
            "reasoning": dict(F.REASONING_PER_JUDGE.get(judge.label, {"effort":"low","exclude":True})),
        }
        if provider_pin:
            extra_body["provider"] = {"order": [provider_pin], "allow_fallbacks": False}
        t0 = time.time()
        try:
            r = client.chat.completions.create(
                model=judge.slug,
                messages=[{"role":"user","content":prompt_text}],
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra_body,
            )
        except Exception as e:
            r_err = {"raw_text":"","finish_reason":"error","error":str(e)[:300],
                     "prompt_tokens":0,"completion_tokens":0,"reasoning_tokens":0,
                     "provider":"","served_model":"","request_id":"","generation_id":"",
                     "latency_ms":int(1000*(time.time()-t0))}
            cost = 0.0
            with ledger_lock:
                ledger.commit(cost, reservation)
            parsed = None
        else:
            choices = getattr(r, "choices", None) or []
            if not choices:
                r_err = {"raw_text":"","finish_reason":"no_choices","error":"provider_returned_no_choices",
                         "prompt_tokens":0,"completion_tokens":0,"reasoning_tokens":0,
                         "provider":getattr(r,"provider","") or "",
                         "served_model":getattr(r,"model","") or "",
                         "request_id":"","generation_id":getattr(r,"id","") or "",
                         "latency_ms":int(1000*(time.time()-t0))}
                cost = 0.0
                with ledger_lock:
                    ledger.commit(cost, reservation)
                parsed = None
            else:
                msg = getattr(choices[0], "message", None)
                raw_text = (getattr(msg, "content", None) or "") if msg is not None else ""
                usage = getattr(r, "usage", None)
                pt = ct = rt = 0
                if usage is not None:
                    pt = getattr(usage, "prompt_tokens", 0) or 0
                    ct = getattr(usage, "completion_tokens", 0) or 0
                    det = getattr(usage, "completion_tokens_details", None)
                    if det is not None:
                        rt = getattr(det, "reasoning_tokens", 0) or 0
                r_err = {"raw_text":raw_text,"finish_reason":getattr(choices[0],"finish_reason","") or "",
                         "error":"", "prompt_tokens":pt, "completion_tokens":ct, "reasoning_tokens":rt,
                         "provider":getattr(r,"provider","") or "",
                         "served_model":getattr(r,"model","") or "",
                         "request_id":"", "generation_id":getattr(r,"id","") or "",
                         "latency_ms":int(1000*(time.time()-t0))}
                cost = _cost_usd(pt, ct, rt, price)
                with ledger_lock:
                    ledger.commit(cost, reservation)
                parsed = parse_proportion(raw_text)
        total_cost += cost
        reasoning_toks += r_err["reasoning_tokens"]
        completion_toks += r_err["completion_tokens"]
        lat += r_err["latency_ms"]
        if r_err["served_model"] and not served: served = r_err["served_model"]
        if r_err["provider"] and not provider: provider = r_err["provider"]
        _append_jsonl(raw_path, {
            "experiment_name": EXPERIMENT_NAME,
            "trial_id": t.trial_id, "attempt_number": attempt,
            "prompt_hash": phash,
            "requested_judge_model_id": judge.slug,
            "returned_model_id": r_err["served_model"], "provider": r_err["provider"],
            "generation_id": r_err["generation_id"],
            "raw_visible_content": r_err["raw_text"], "finish_reason": r_err["finish_reason"],
            "parsed_p_H": parsed, "valid": parsed is not None,
            "error": r_err["error"],
            "input_tokens": r_err["prompt_tokens"], "output_tokens": r_err["completion_tokens"],
            "reasoning_tokens": r_err["reasoning_tokens"], "latency_ms": r_err["latency_ms"],
            "cost_usd": cost,
            "cost_status": "billed" if r_err["error"] == "" else "uncertain",
            "judge_request_config_hash": request_config_hash,
            "temperature": temperature,
            "procedure": t.procedure, "wording": t.wording_condition,
            "target_label": t.target_label, "judge_label": t.judge_label,
            "replicate": t.replicate,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        if attempt == 1: first_valid = (parsed is not None)
        if parsed is not None:
            return {"trial_id": t.trial_id, "status": "ok",
                    "visible_answer": r_err["raw_text"].strip(), "predicted_p_H": parsed,
                    "attempts": attempt, "first_attempt_valid": first_valid,
                    "total_cost_usd": total_cost, "returned_model_id": served,
                    "provider": provider,
                    "reasoning_tokens_total": reasoning_toks,
                    "completion_tokens_total": completion_toks,
                    "latency_ms_total": lat, "missing_reason": ""}
    return {"trial_id": t.trial_id, "status": "abandoned",
            "visible_answer": None, "predicted_p_H": None,
            "attempts": F.RESPONSE_ATTEMPT_CAP, "first_attempt_valid": first_valid,
            "total_cost_usd": total_cost, "returned_model_id": served,
            "provider": provider, "reasoning_tokens_total": reasoning_toks,
            "completion_tokens_total": completion_toks,
            "latency_ms_total": lat, "missing_reason": "exhausted_response_attempts"}


def _outcomes_path(run_dir): return os.path.join(run_dir, "trial_outcomes.json")
def _ledger_path(run_dir): return os.path.join(run_dir, "cost_ledger.json")


def load_outcomes(run_dir): return _read_json(_outcomes_path(run_dir), {})
def save_outcomes(run_dir, outcomes): _write_json_atomic(_outcomes_path(run_dir), outcomes)
def load_ledger(run_dir, cap):
    d = _read_json(_ledger_path(run_dir), None)
    if d is None: return CostLedger(cap_usd=cap)
    return CostLedger(cap_usd=cap, spent_usd=float(d.get("spent_usd", 0.0)))
def save_ledger(run_dir, L): _write_json_atomic(_ledger_path(run_dir), L.to_dict())


def run_scored(client, trials, run_dir, prices, provider_pins, cap_usd,
               temperature: float = 0.7, max_tokens: int = 512, log=print):
    import threading
    outcomes = load_outcomes(run_dir)
    ledger = load_ledger(run_dir, cap_usd)
    log(f"[scored] start: {len(outcomes)} prior outcomes spent=${ledger.spent_usd:.4f} cap=${cap_usd:.2f} temp={temperature}")
    done = {tid for tid, o in outcomes.items() if o.get("status") == "ok"}
    pending = [t for t in trials if t.trial_id not in done]
    log(f"[scored] pending={len(pending)}")

    judge_locks = {j: threading.Lock() for j in F.JUDGE_LABELS}
    outcomes_lock = threading.Lock()
    ledger_lock = threading.Lock()

    def _work(t):
        judge = F.JUDGE_BY_LABEL[t.judge_label]
        price = prices.get(judge.slug, {"prompt":0.0,"completion":0.0})
        req_hash = judge_request_config_hash(max_tokens, provider_pins.get(t.judge_label),
                                              judge_label=t.judge_label,
                                              source_method="phenotype_prediction")
        with judge_locks[t.judge_label]:
            outcome = _run_one(t, client, judge, provider_pins.get(t.judge_label),
                                max_tokens, run_dir, ledger, ledger_lock,
                                price, req_hash, temperature)
            with outcomes_lock:
                outcomes[t.trial_id] = outcome
                save_outcomes(run_dir, outcomes)
            save_ledger(run_dir, ledger)
            return outcome

    completed = 0
    with ThreadPoolExecutor(max_workers=F.CONCURRENCY_OVERALL) as pool:
        futs = {pool.submit(_work, t): t for t in pending}
        for fut in as_completed(futs):
            res = fut.result()
            completed += 1
            if completed % 30 == 0 or res["status"] != "ok":
                log(f"[scored] {completed}/{len(pending)} done "
                    f"(spent=${ledger.spent_usd:.4f} last={res['trial_id']} "
                    f"status={res['status']} p={res.get('predicted_p_H')})")

    final = load_outcomes(run_dir)
    summary = {"n_outcomes": len(final),
               "n_ok": sum(1 for o in final.values() if o["status"] == "ok"),
               "n_abandoned": sum(1 for o in final.values() if o["status"] == "abandoned"),
               "spent_usd": ledger.spent_usd}
    log(f"[scored] FINAL: {summary}")
    return summary


# ------------------------------- analysis ----------------------------------

ACTUAL_PHENOTYPES = {
    "astra": {"batch": 0.495, "history_conditioned": 0.460, "independent_calls": 0.389},
    "fable": {"batch": 0.507, "history_conditioned": 0.744, "independent_calls": 0.987},
    "mimo":  {"batch": 0.487, "history_conditioned": 0.633, "independent_calls": 0.860},
}


def _loose_parse(text: str) -> Optional[float]:
    """Secondary parser: strict-first, else try the last non-empty line.
    Only used in the recovery analysis for transparent reporting; the primary
    parser (parse_proportion) is still the strict one that forbids prose."""
    v = parse_proportion(text)
    if v is not None: return v
    if not text: return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines: return None
    v = parse_proportion(lines[-1])
    return v


def _summarize(trials, outcomes, raw_attempts_path: Optional[str] = None):
    """Per (judge, wording, target, procedure) mean/sd/n under both the strict
    parser and (if raw_attempts_path given) the relaxed "last-line" parser.
    """
    import math
    by_strict: Dict[tuple, List[float]] = defaultdict(list)
    for t in trials:
        o = outcomes.get(t.trial_id, {})
        if o.get("status") == "ok" and o.get("predicted_p_H") is not None:
            key = (t.judge_label, t.wording_condition, t.target_label, t.procedure)
            by_strict[key].append(float(o["predicted_p_H"]))

    by_loose: Dict[tuple, List[float]] = defaultdict(list)
    if raw_attempts_path and os.path.exists(raw_attempts_path):
        # Use FIRST-attempt raw response per trial (consistent with "first valid
        # answer" policy). If first-attempt visible content yields a loose
        # parse, use it; else fall through to the strict value if present.
        first_attempt_by_trial: Dict[str, str] = {}
        with open(raw_attempts_path, "r", encoding="utf-8") as f:
            for line in f:
                ln = line.strip()
                if not ln: continue
                try: r = json.loads(ln)
                except Exception: continue
                tid = r.get("trial_id"); att = r.get("attempt_number")
                if tid and att == 1 and tid not in first_attempt_by_trial:
                    first_attempt_by_trial[tid] = r.get("raw_visible_content") or ""
        by_trial = {t.trial_id: t for t in trials}
        for tid, text in first_attempt_by_trial.items():
            t = by_trial.get(tid)
            if t is None: continue
            v = _loose_parse(text)
            if v is None: continue
            key = (t.judge_label, t.wording_condition, t.target_label, t.procedure)
            by_loose[key].append(v)

    rows = []
    all_keys = sorted(set(by_strict.keys()) | set(by_loose.keys()))
    for key in all_keys:
        judge, wording, target, proc = key
        strict = by_strict.get(key, [])
        loose = by_loose.get(key, [])
        def _stats(vals):
            n = len(vals)
            m = sum(vals)/n if n else None
            var = (sum((v - m)**2 for v in vals)/(n-1)) if n > 1 else None
            sd = math.sqrt(var) if var is not None else None
            return n, m, sd
        n_s, m_s, sd_s = _stats(strict)
        n_l, m_l, sd_l = _stats(loose)
        actual = ACTUAL_PHENOTYPES[target][proc]
        rows.append({
            "judge": judge, "wording": wording, "target": target,
            "procedure": proc,
            "n_strict": n_s,
            "mean_predicted_p_H_strict": None if m_s is None else round(m_s, 4),
            "sd_predicted_p_H_strict": None if sd_s is None else round(sd_s, 4),
            "n_loose": n_l,
            "mean_predicted_p_H_loose": None if m_l is None else round(m_l, 4),
            "sd_predicted_p_H_loose": None if sd_l is None else round(sd_l, 4),
            "actual_p_H": actual,
            "signed_deviation_strict": None if m_s is None else round(m_s - actual, 4),
            "signed_deviation_loose": None if m_l is None else round(m_l - actual, 4),
        })
    return rows


def write_trial_level(path, trials, outcomes):
    rows = []
    for t in trials:
        o = outcomes.get(t.trial_id, {})
        rows.append({
            **{k: getattr(t, k) for k in ("trial_id","judge_label","wording_condition",
                                           "target_label","procedure","replicate")},
            "status": o.get("status","pending"),
            "visible_answer": o.get("visible_answer"),
            "predicted_p_H": o.get("predicted_p_H"),
            "attempts": o.get("attempts", 0),
            "first_attempt_valid": o.get("first_attempt_valid"),
            "returned_model_id": o.get("returned_model_id",""),
            "provider": o.get("provider",""),
        })
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path,"w",encoding="utf-8") as f: f.write("")
        return rows
    with open(path,"w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows: w.writerow(r)
    return rows


def _write_rows(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path,"w",encoding="utf-8") as f: f.write("")
        return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
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


def cmd_dry_run(args):
    run_dir = os.path.join(args.data_root, EXPERIMENT_NAME,
                            args.run_id or f"phenotype-{_ts()}-dry")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "phenotype.log"))
    trials = build_trials(args.replicates)
    log(f"built {len(trials)} trials ({args.replicates} replicates per unique prompt)")
    # Write prompts
    with open(os.path.join(run_dir, "prompts.jsonl"), "w", encoding="utf-8") as f:
        seen_keys = set()
        for t in trials:
            key = (t.judge_label, t.wording_condition, t.target_label, t.procedure)
            if key in seen_keys: continue
            seen_keys.add(key)
            text = build_prompt(t)
            f.write(json.dumps({"key": "|".join(key), "prompt_hash": hashlib.sha256(text.encode()).hexdigest(),
                                "prompt_text": text}) + "\n")
    log(f"wrote {len(seen_keys)} unique prompts (deduped across replicates)")
    # Parser sanity
    for case in ("0.5", "0.75", "0.987", "0.00001", "  0.5\n"):
        v = parse_proportion(case)
        assert v is not None and 0 <= v <= 1
    for case in ("50%", "0.5-0.6", "about 0.5", "0.5 (fair)", "The answer is 0.5", ""):
        v = parse_proportion(case)
        assert v is None, f"parser should reject {case!r}, got {v}"
    log(f"[dry-run] parser accepts bare floats, rejects prose/percents/ranges")


def cmd_run(args):
    assert args.live and args.yes, "require --live --yes"
    run_dir = os.path.join(args.data_root, EXPERIMENT_NAME,
                            args.run_id or f"phenotype-{_ts()}")
    os.makedirs(run_dir, exist_ok=True)
    log, _ = _log_writer(os.path.join(run_dir, "logs", "phenotype.log"))
    api_key = os.environ.get("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY not set"
    client = make_openrouter_client(api_key)
    trials = build_trials(args.replicates)
    log(f"START {len(trials)} trials replicates={args.replicates} temp={args.temperature} budget=${args.budget_usd:.2f}")

    # Save manifests
    with open(os.path.join(run_dir, "trial_manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["trial_id","judge_label","wording_condition",
                                            "target_label","procedure","replicate"])
        w.writeheader()
        for t in trials: w.writerow(asdict(t))

    prices = snapshot_prices(client)
    provider_pins = {j.label: j.preferred_provider for j in F.JUDGES}
    with open(os.path.join(run_dir, "config_frozen.json"), "w") as f:
        json.dump({"experiment": EXPERIMENT_NAME,
                   "n_trials": len(trials), "replicates": args.replicates,
                   "temperature": args.temperature,
                   "reasoning_per_judge": F.REASONING_PER_JUDGE,
                   "provider_pins": provider_pins,
                   "actual_phenotypes": ACTUAL_PHENOTYPES,
                   "budget_usd_cap": args.budget_usd},
                   f, indent=2, sort_keys=True)
    lock_path = os.path.join(run_dir, ".lock")
    with process_lock(lock_path):
        summary = run_scored(client, trials, run_dir, prices, provider_pins,
                              cap_usd=args.budget_usd,
                              temperature=args.temperature, log=log)
    log(f"DONE {summary}")


def cmd_analyze(args):
    run_dir = args.run_dir
    log, _ = _log_writer(os.path.join(run_dir, "logs", "phenotype.log"))
    log(f"ANALYZE run_dir={run_dir}")
    tm_path = os.path.join(run_dir, "trial_manifest.csv")
    assert os.path.exists(tm_path), f"no trial_manifest.csv at {tm_path}"
    trials: List[PhenotypeTrial] = []
    with open(tm_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            trials.append(PhenotypeTrial(
                trial_id=r["trial_id"], judge_label=r["judge_label"],
                wording_condition=r["wording_condition"], target_label=r["target_label"],
                procedure=r["procedure"], replicate=int(r["replicate"])))
    outcomes = _read_json(os.path.join(run_dir, "trial_outcomes.json"), {})
    rows = write_trial_level(os.path.join(run_dir, "trial_level.csv"), trials, outcomes)
    raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
    summary = _summarize(trials, outcomes, raw_attempts_path=raw_path)
    _write_rows(os.path.join(run_dir, "summary_by_cell.csv"), summary)
    log(f"wrote trial_level.csv ({len(rows)} rows) and summary_by_cell.csv ({len(summary)} rows)")


def main():
    ap = argparse.ArgumentParser(prog="python -m spar_dynamic.full_corpus_exp1.phenotype_prediction")
    sub = ap.add_subparsers(dest="cmd", required=True)
    def _common(sp):
        sp.add_argument("--data-root", default="data/spar_dynamic")
        sp.add_argument("--run-id", default="")
        sp.add_argument("--replicates", type=int, default=10,
                        help="replicates per unique (judge, wording, target, procedure) prompt")
    sp = sub.add_parser("dry-run"); _common(sp); sp.set_defaults(func=cmd_dry_run)
    sp = sub.add_parser("run"); _common(sp)
    sp.add_argument("--live", action="store_true", required=True)
    sp.add_argument("--yes", action="store_true", required=True)
    sp.add_argument("--budget-usd", type=float, default=5.0)
    sp.add_argument("--temperature", type=float, default=0.7,
                     help="elevated temperature for within-cell variance; default 0.7")
    sp.set_defaults(func=cmd_run)
    sp = sub.add_parser("analyze")
    sp.add_argument("--run-dir", required=True)
    sp.set_defaults(func=cmd_analyze)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
