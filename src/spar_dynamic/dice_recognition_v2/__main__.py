"""LOULA_DICE_RECOGNITION v2.0 CLI (Experiment 23). Each phase refuses to start unless its prerequisite passed.

  python -m spar_dynamic.dice_recognition_v2 dryrun              # 0 API calls: PROTOCOL_FROZEN.md, manifest, cost estimate
  python -m spar_dynamic.dice_recognition_v2 api_preflight       # 12 calls: pins, reasoning-off, parsers, multi-turn
  python -m spar_dynamic.dice_recognition_v2 calibrate           # Stage A: 288 calls; per judge x format gate; format freeze
  python -m spar_dynamic.dice_recognition_v2 elicitation_screen  # Stage B: Exp 22 pairs, AUTH/TYP x passing formats
  python -m spar_dynamic.dice_recognition_v2 generate_corpus     # Stage C corpus: 110 valid per source (cap 160)
  python -m spar_dynamic.dice_recognition_v2 recognition_dose    # Stage C: K=1/3/5 AUTH+TYP, named control at K=5
  python -m spar_dynamic.dice_recognition_v2 familiarization     # Stage D: D1 own/other exposure; D2 live sessions
  python -m spar_dynamic.dice_recognition_v2 analyse             # offline: tables, bootstrap, figures, readout
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import platform
import subprocess
import sys

import numpy as np

import repo_paths
from spar_dynamic.dice_recognition_v2 import (analysis as A, client as CL, config as C, corpus as CO, prompts as P,
                                              synthetic as S, trials as T)

EXP = str(repo_paths.T1_EXP["dice_recognition_v2"])
V1 = str(repo_paths.T1_EXP[C.V1_EXP_KEY])
D = {k: os.path.join(EXP, k) for k in ("api_preflight", "calibration", "elicitation_screen", "corpus_v2",
                                       "recognition_dose", "familiarization", "analysis", "reports")}
PREFLIGHT_PAIR = ("6 6 2 6 1 6 4 6 3 5", "1 2 3 4 5 1 2 3 4 5")     # preflight only; X has more 6s


def _client():
    from openai import OpenAI
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set (load .env first)")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, max_retries=0, timeout=120.0)


def _ledger():
    os.makedirs(EXP, exist_ok=True)
    return CL.Ledger(os.path.join(EXP, "cost_ledger.json"))


def _jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")] if os.path.exists(path) else []


def _csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def _dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def _load(path):
    return json.load(open(path, encoding="utf-8"))


def _require(path, label):
    if not os.path.exists(path) or _load(path).get("overall") not in ("PASS", "COMPLETE"):
        raise SystemExit(f"STOP: {label} has not passed/completed ({path})")


def old_pairs():
    return _csv(os.path.join(V1, "judgments", "pairs.csv"))


def frozen_classifier():
    return _load(os.path.join(V1, "corpus", "classifier_gate.json"))["frozen_model"]


# ------------------------------------------------------------------------------------------------ dryrun --
def _token_est(text):
    return len(text) / 3.2 + 8


def cost_estimate():
    """Per-stage call counts at the frozen maxima, with expected and worst-case USD (listed per-token prices)."""
    items = S.make_items()
    ex = ["5 2 6 1 3 4 6 2 5 1"] * 5
    p = {
        "cal": np.mean([_token_est(t["prompt"]) for t in T.calibration_trials(items)]),
        "k1": _token_est(P.frame_prompt("AUTH", "brief", ex[:1], ex[:1])),
        "k3": _token_est(P.frame_prompt("AUTH", "brief", ex[:3], ex[:3])),
        "k5": _token_est(P.frame_prompt("AUTH", "brief", ex, ex)),
        "named": _token_est(P.named_prompt("brief", ex, ex, "qwen", ("qwen", "mistral"))),
        "exp": _token_est(P.exposure_prompt("own", ex, "brief", ex, ex)),
        "gen": _token_est(P.GEN)}
    stages = {  # (calls, mean prompt tokens, completion tokens expected/worst)
        "api_preflight": (12, p["cal"], 60, 160),
        "calibration": (288, p["cal"], 45, 84),
        "elicitation_screen": (320, p["k1"], 45, 84),
        "corpus_v2": (2 * C.MAX_ATTEMPTS_PER_SOURCE, p["gen"], 20, 64),
        "dose": (480, (p["k1"] + p["k3"] + p["k5"]) / 3, 60, 160),
        "named": (320, p["named"], 60, 160),
        "exposure_D1": (160, p["exp"], 60, 160),
        "live_D2": (2 * C.N_LIVE_FAMILIES * 2 * (C.N_LIVE_GEN_TURNS + 1), p["k5"] + 100, 50, 160)}
    price = max(C.MODELS[m]["price_per_token"][0] for m in C.SOURCES), max(C.MODELS[m]["price_per_token"][1] for m in C.SOURCES)
    out = {k: dict(max_calls=n, expected_usd=round(n * (pt * price[0] + ce * price[1]), 4),
                   worst_case_usd=round(n * (pt * price[0] + cw * price[1]), 4)) for k, (n, pt, ce, cw) in stages.items()}
    out["total"] = {f: round(sum(v[f] for v in out.values()), 4) for f in ("max_calls", "expected_usd", "worst_case_usd")}
    out["note"] = ("Upper-bound prices = the dearer model's listed input/output price per token; the call cap guard uses "
                   f"${C.MAX_CALL_COST_PRIOR_USD}/call. Real spend comes from OpenRouter usage.cost.")
    return out


def protocol_md(items, est):
    ex = ["5 2 6 1 3 4 6 2 5 1", "1 3 5 2 6 4 1 3 2 5", "4 1 6 3 5 2 6 4 1 3", "5 3 1 6 2 4 3 5 6 1", "2 5 1 6 3 4 6 2 5 1"]
    rendered = {
        "CAL_MORE_SIXES_bare": P.calibration_prompt("MORE_SIXES", "bare", items[0]["X"], items[0]["Y"]),
        "CAL_GEN_RULE_brief": P.calibration_prompt("GEN_RULE", "brief", items[24]["X"], items[24]["Y"]),
        "AUTH_K1_bare": P.frame_prompt("AUTH", "bare", ex[:1], ex[1:2]),
        "TYP_K3_brief": P.frame_prompt("TYP", "brief", ex[:3], ex[2:5]),
        "NAMED_K5_brief_targetQwen_namesMQ": P.named_prompt("brief", ex, ex[::-1], "qwen", ("mistral", "qwen")),
        "EXPOSURE_own_K5_brief": P.exposure_prompt("own", ex, "brief", ex, ex[::-1]),
        "EXPOSURE_other_K5_brief": P.exposure_prompt("other", ex, "brief", ex, ex[::-1])}
    L = [f"# {C.TAG}: frozen protocol (Experiment 23)\n",
         f"Frozen by `dryrun` on {dt.date.today().isoformat()}, before any v2 API call. Handoff: "
         "`GPT_SPAR_Loula_Dice_Recognition_Redesign_Claude_Code_Handoff_v2.0`. Exploratory staged pilot, not confirmatory.\n",
         "\n## Models and settings\n",
         "| Key | Slug | Pinned provider | Reasoning |\n|---|---|---|---|\n" +
         "".join(f"| {k} | `{m['slug']}` | {m['provider']} (order+only, no fallbacks, require_parameters) | "
                 f"{'enabled=false' if m['reasoning'] else 'not sent'} |\n" for k, m in C.MODELS.items()),
         f"\nGeneration: {C.GENERATION}. Judgment bare: {C.JUDGMENT['bare']}; brief: {C.JUDGMENT['brief']}. "
         "No system message. Fresh single-message chat for every call except D2 live sessions. "
         f"Bounded concurrency {C.CONCURRENCY}; dispatch order recorded.\n",
         "\n## Templates (filled by literal slot replacement)\n"]
    for k, t in P.templates().items():
        L.append(f"\n### {k}\n\nsha256 `{P.sha256(t)}`\n\n```text\n{t}\n```\n")
    L.append("\n## Rendered examples (illustrative content; hashes of the full rendered text)\n")
    for k, t in rendered.items():
        L.append(f"\n### {k}\n\nsha256 `{P.sha256(t)}`\n\n```text\n{t}\n```\n")
    L.append(f"""
## Parsing
- **bare:** the whole reply, stripped, is exactly `A` or `B`.
- **brief:** reply must finish with `stop`; at least two non-empty lines; the last non-empty line, stripped, is exactly
  `ANSWER: A` or `ANSWER: B`; any other `ANSWER: X` line in the text must agree. Letters in prose are never read.
- Any provider drift, reasoning payload/`<think>` text, or transport failure makes the answer invalid. Invalid answers
  are kept and never re-asked.

## Stage A: calibration (synthetic items, seed {C.SEEDS['calibration_items']})
{S.__doc__}
Per judge x format: 3 tasks x 12 items x 2 orders = 72 calls (288 total). Gates (all must hold): MORE_SIXES
>= {C.GATES['MORE_SIXES']['min_correct']}/24 correct and >= {C.GATES['MORE_SIXES']['min_consistent']}/12 same-candidate
pairs; MORE_REPEATS >= {C.GATES['MORE_REPEATS']['min_correct']}/24 and >= {C.GATES['MORE_REPEATS']['min_consistent']}/12;
GEN_RULE >= {C.GATES['GEN_RULE']['min_correct']}/24 and >= {C.GATES['GEN_RULE']['min_consistent']}/12; validity
>= {C.MIN_FORMAT_VALIDITY:.0%} of the 72. Generator R repeats with p={C.RULE_R_REPEAT}, S with p={C.RULE_S_REPEAT}.
A judge with no passing format is excluded from all identity judgments. No judge passing -> STOP after Stage A.

**Primary-format freeze rule (applied at the end of Stage A, before Stage B):** brief if it passed for that judge,
else bare if it passed, else excluded. Never chosen on Stage B accuracy.

## Stage B: elicitation screen (Experiment 22's 20 pairs, read-only)
Judge x passing format x AUTH/TYP x 20 pairs x 2 orders (max 320). Method-development material only.

## Stage C: corpus and evidence dose
{CO.__doc__}
Dose: per included judge, primary format, AUTH and TYP, K = 1, 3, 5 nested blocks, 20 families x 2 orders
(max 480). Named control at K=5: target Qwen/Mistral x name order (QM/MQ) x 2 sample orders x 20 families per judge
(max 320). Runs if at least one judge passed Stage A.

External reference: Experiment 22's frozen development classifier (no refitting). K-block rule: sum of per-block
Qwen logits per candidate; larger sum = called Qwen; ties 0.5.

## Stage D: familiarization
D1: K=5, AUTH, primary format; OWN / OTHER exposure preambles with 5 real reserved exemplars (seeded choice of 5 of
the source's 10 reserved records per family, seed {C.SEEDS['exposure_select']}); NONE = Stage C K=5 AUTH (reused).
Max 160 calls. D2 (exploratory feasibility): first {C.N_LIVE_FAMILIES} families x 2 orders per judge; one chat with
{C.N_LIVE_GEN_TURNS} live generation turns (replies kept verbatim) then the TYP question; max 128 calls.

## Estimands and analysis
Handoff section 8. Units: calibration item, Exp 22 pair, or family. Orientations averaged within unit first.
Orientation consistency is reported beside every accuracy. 95% intervals from {C.N_BOOTSTRAP} unit resamples applied
jointly to all cells (seed {C.SEEDS['bootstrap']}). S_named = 0.5[(Q->Qwen - M->Qwen) + (M->Mistral - Q->Mistral)] at
K=5, averaged over name orders; not estimable if a judge is excluded. Self minus named-own at K=5. Dose differences
K3-K1, K5-K1. Familiarization OWN-NONE, OWN-OTHER. No p-values.

## Stop rules
Provider drift, reasoning output, cost cap, attempt cap, or a judge's invalid share > {C.STAGE_MAX_INVALID_SHARE:.0%}
after {C.STAGE_MIN_N} calls in a live stage -> STOP and report. Any change after freeze is a versioned amendment.

## Budget
Hard cap ${C.COST_CAP_USD:.2f} across all v2 calls. Pre-run estimate (listed prices, conservative tokens):

```json
{json.dumps(est, indent=1)}
```

## Seeds
```json
{json.dumps(C.SEEDS, indent=1)}
```

## Hypotheses (exploratory)
H1 judges that pass Stage A give content-sensitive choices (orientation consistency well above 0) in B-D.
H2 accuracy and consistency rise with K. H3 AUTH and TYP can diverge. H4 own-source advantage S_named > 0.
H5 OWN exposure > NONE and > OTHER. None is confirmatory; positive findings would need a separately approved replication.
""")
    return "".join(L)


def dryrun():
    os.makedirs(EXP, exist_ok=True)
    items = S.make_items()
    est = cost_estimate()
    md = protocol_md(items, est)
    pf = os.path.join(EXP, "PROTOCOL_FROZEN.md")
    if os.path.exists(pf) and open(pf, encoding="utf-8").read().split("\n", 3)[3] != md.split("\n", 3)[3]:
        raise SystemExit("PROTOCOL_FROZEN.md exists and differs: a change after freeze needs a versioned amendment")
    if not os.path.exists(pf):
        with open(pf, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
    os.makedirs(D["calibration"], exist_ok=True)
    CO.write_csv(os.path.join(D["calibration"], "items.csv"), [dict(i, correct_by_content=S.correct_side(i)) for i in items])
    _dump(os.path.join(D["calibration"], "generator_rules.json"),
          dict(R=dict(repeat_probability=C.RULE_R_REPEAT, otherwise="uniform over the 5 other faces", first="uniform"),
               S=dict(repeat_probability=C.RULE_S_REPEAT, otherwise="uniform over the 5 other faces", first="uniform"),
               length_range=C.RULE_LEN, seed=C.SEEDS["calibration_items"], doc=S.__doc__))
    man = dict(tag=C.TAG, created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
               git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
               python=sys.version, platform=platform.platform(), models=C.MODELS, generation=C.GENERATION,
               judgment=C.JUDGMENT, template_sha256={k: P.sha256(v) for k, v in P.templates().items()},
               inputs=dict(exp22_pairs=os.path.relpath(os.path.join(V1, "judgments", "pairs.csv"), EXP),
                           exp22_classifier=os.path.relpath(os.path.join(V1, "corpus", "classifier_gate.json"), EXP)),
               caps=dict(cost_usd=C.COST_CAP_USD, attempts_per_source=C.MAX_ATTEMPTS_PER_SOURCE),
               seeds=C.SEEDS, cost_estimate=est, cost_ledger="cost_ledger.json",
               request_examples={m: {k: v for k, v in CL.request_body(m, [{"role": "user", "content": "..."}], "brief").items()
                                     if k != "messages"} for m in C.SOURCES})
    _dump(os.path.join(EXP, "manifest.json"), man)
    print(json.dumps(dict(exp=EXP, api_calls_made=0, cost_estimate=est["total"]), indent=1))


# --------------------------------------------------------------------------------------------- preflight --
def api_preflight():
    if not os.path.exists(os.path.join(EXP, "PROTOCOL_FROZEN.md")):
        raise SystemExit("run dryrun first")
    path = os.path.join(D["api_preflight"], "raw_attempts.jsonl")
    if os.path.exists(path):
        raise SystemExit("preflight already run; inspect api_preflight/")
    oai, led = _client(), _ledger()
    os.makedirs(D["api_preflight"], exist_ok=True)
    X, Y = PREFLIGHT_PAIR
    rows = []
    for m in C.SOURCES:
        g = CL.call(oai, led, m, [{"role": "user", "content": P.GEN}], "generation", "api_preflight")
        rows.append(dict(g, check="generation", valid=P.parse_sequence(g.get("content")) is not None))
        for fmt in C.FORMATS:
            for orient, (a, b), corr in (("XA", (X, Y), "A"), ("XB", (Y, X), "B")):
                r = CL.call(oai, led, m, [{"role": "user", "content": P.calibration_prompt("MORE_SIXES", fmt, a, b)}], fmt, "api_preflight")
                ch = CL.judged(r, fmt)
                rows.append(dict(r, check=f"judge_{fmt}_{orient}", choice=ch, valid=ch is not None, correct=corr,
                                 is_correct=ch == corr))
        msgs = [{"role": "user", "content": P.GEN}, {"role": "assistant", "content": g.get("content") or ""},
                {"role": "user", "content": P.calibration_prompt("MORE_SIXES", "bare", X, Y)}]
        r = CL.call(oai, led, m, msgs, "bare", "api_preflight")
        ch = CL.judged(r, "bare")
        rows.append(dict(r, check="multiturn_bare_XA", choice=ch, valid=ch is not None, correct="A", is_correct=ch == "A"))
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    g = {}
    for m in C.SOURCES:
        rs = [r for r in rows if r["model_key"] == m]
        g[f"{m}_provider_pinned"] = all(r.get("ok") and CL.provider_ok(r) for r in rs)
        g[f"{m}_no_thinking"] = all(CL.thinking_clean(r) for r in rs)
        if m == "qwen":
            g["qwen_reasoning_tokens_reported_zero"] = all(r.get("reasoning_tokens") == 0 for r in rs)
        g[f"{m}_generation_valid"] = rs[0]["valid"]
        g[f"{m}_multiturn_ok"] = bool(rs[-1].get("ok"))
    info = {f"{m}_{r['check']}": dict(content=r.get("content"), choice=r.get("choice"), correct=r.get("correct"),
                                      is_correct=r.get("is_correct"), finish=r.get("finish_reason"),
                                      provider=r.get("served_provider"), reasoning_tokens=r.get("reasoning_tokens"),
                                      cost=r.get("cost_usd"))
            for m in C.SOURCES for r in rows if r["model_key"] == m}
    content = {f"{m}_{fmt}": [info[f"{m}_judge_{fmt}_XA"]["is_correct"], info[f"{m}_judge_{fmt}_XB"]["is_correct"]]
               for m in C.SOURCES for fmt in C.FORMATS}
    res = dict(infrastructure_gates=g, overall="PASS" if all(g.values()) else "FAIL",
               content_check_both_orders_correct=content,
               note="Infrastructure gates are binding. Parse validity and the two-order content check are reported here "
                    "and enforced per judge x format in Stage A.", spent_usd=led.spent, responses=info)
    _dump(os.path.join(D["api_preflight"], "preflight_summary.json"), res)
    print(json.dumps(res, indent=1))


# ------------------------------------------------------------------------------------------------ Stage A --
def calibrate():
    _require(os.path.join(D["api_preflight"], "preflight_summary.json"), "API preflight")
    items = S.make_items()
    trials = T.calibration_trials(items)
    CO.write_csv(os.path.join(D["calibration"], "trials.csv"), [{k: v for k, v in t.items() if k != "prompt"} for t in trials])
    resp = CL.run_judgments(_client(), _ledger(), trials, os.path.join(D["calibration"], "raw_attempts.jsonl"), "calibration")
    gate = A.calibration_gate(resp)
    primary = {}
    for j in C.SOURCES:
        if gate[f"{j}|brief"]["PASS"]:
            primary[j] = "brief"
        elif gate[f"{j}|bare"]["PASS"]:
            primary[j] = "bare"
    passing = {j: [f for f in C.FORMATS if gate[f"{j}|{f}"]["PASS"]] for j in C.SOURCES}
    out = dict(gate=gate, passing_formats=passing, overall="PASS" if primary else "FAIL",
               excluded_judges=[j for j in C.SOURCES if j not in primary])
    _dump(os.path.join(D["calibration"], "gate.json"), out)
    _dump(os.path.join(D["elicitation_screen"], "format_freeze.json"),
          dict(primary_format=primary, rule="brief if it passed Stage A, else bare if it passed, else excluded",
               frozen_utc=dt.datetime.now(dt.timezone.utc).isoformat(), frozen_before="Stage B and Stage C stimuli"))
    _write_responses(resp, os.path.join(D["calibration"], "responses.csv"))
    for k, r in gate.items():
        print(k, "PASS" if r["PASS"] else "FAIL", f"validity {r['validity']:.2f}",
              {t: (r[t]["correct"], r[t]["consistent_pairs"]) for t in C.CAL_TASKS})
    if not primary:
        raise SystemExit("STOP: neither judge passed Stage A in either format (methodological failure)")


def _write_responses(resp, path):
    keep = ("trial_id", "stage", "judge", "fmt", "task", "frame", "exposure", "K", "name_order", "item_id", "unit_id",
            "orientation", "A_source", "B_source", "target_source", "correct", "A_content", "B_content", "content",
            "choice", "valid", "is_correct", "finish_reason", "served_provider", "reasoning_tokens", "prompt_sha256",
            "cost_usd", "response_id", "dispatch_index", "completed_utc")
    CO.write_csv(path, [{k: r.get(k) for k in keep if k in r} for r in resp])


# ------------------------------------------------------------------------------------------------ Stage B --
def elicitation_screen():
    _require(os.path.join(D["calibration"], "gate.json"), "Stage A calibration")
    passing = {j: f for j, f in _load(os.path.join(D["calibration"], "gate.json"))["passing_formats"].items() if f}
    trials = T.screen_trials(old_pairs(), passing)
    CO.write_csv(os.path.join(D["elicitation_screen"], "trials.csv"), [{k: v for k, v in t.items() if k != "prompt"} for t in trials])
    resp = CL.run_judgments(_client(), _ledger(), trials, os.path.join(D["elicitation_screen"], "raw_attempts.jsonl"), "screen")
    _write_responses(resp, os.path.join(D["elicitation_screen"], "responses.csv"))
    _dump(os.path.join(D["elicitation_screen"], "status.json"), dict(overall="COMPLETE", n=len(resp), cells=passing))


# ------------------------------------------------------------------------------------------------ Stage C --
def generate_corpus():
    _require(os.path.join(D["elicitation_screen"], "status.json"), "Stage B screen")
    valid = CO.collect(_client(), _ledger(), D["corpus_v2"])
    ok = all(valid.get(s, 0) >= C.N_VALID_PER_SOURCE for s in C.SOURCES)
    rows = _jsonl(os.path.join(D["corpus_v2"], "raw_attempts.jsonl"))
    status = dict(valid=valid, target=C.N_VALID_PER_SOURCE, attempts={m: sum(r["model_key"] == m for r in rows) for m in C.SOURCES},
                  invalid_reasons={m: dict(__import__("collections").Counter(r["invalid_reason"] for r in rows
                                                                              if r["model_key"] == m and not r["valid"])) for m in C.SOURCES},
                  overall="PASS" if ok else "FAIL")
    if ok:
        recs = CO.records(D["corpus_v2"])
        fams, fam = CO.partition(recs)
        status["duplicates"] = CO.duplicate_report(recs, fams, fam)
        CO.write_csv(os.path.join(D["corpus_v2"], "records.csv"),
                     [dict(r, role=("familiarization" if r in fam[m] else "evaluation" if any(r["record_id"] in f[f"{m}_record_ids"] for f in fams) else "unused"))
                      for m in C.SOURCES for r in recs[m]])
        _dump(os.path.join(D["corpus_v2"], "families.json"), fams)
        _dump(os.path.join(D["corpus_v2"], "familiarization_reserve.json"), fam)
    _dump(os.path.join(D["corpus_v2"], "corpus_status.json"), status)
    print(json.dumps({k: v for k, v in status.items()}, indent=1, default=str))
    if not ok:
        raise SystemExit("STOP: corpus quota not met within the attempt cap")


def _primary():
    return _load(os.path.join(D["elicitation_screen"], "format_freeze.json"))["primary_format"]


def recognition_dose():
    _require(os.path.join(D["corpus_v2"], "corpus_status.json"), "Stage C corpus")
    fams, prim = _load(os.path.join(D["corpus_v2"], "families.json")), _primary()
    oai, led = _client(), _ledger()
    rd = D["recognition_dose"]
    dose = T.dose_trials(fams, prim)
    named = T.named_trials(fams, prim)
    CO.write_csv(os.path.join(rd, "dose_trials.csv"), [{k: v for k, v in t.items() if k != "prompt"} for t in dose])
    CO.write_csv(os.path.join(rd, "named_trials.csv"), [{k: v for k, v in t.items() if k != "prompt"} for t in named])
    r1 = CL.run_judgments(oai, led, dose, os.path.join(rd, "dose_raw_attempts.jsonl"), "dose")
    r2 = CL.run_judgments(oai, led, named, os.path.join(rd, "named_raw_attempts.jsonl"), "named")
    _write_responses(r1, os.path.join(rd, "dose_responses.csv"))
    _write_responses(r2, os.path.join(rd, "named_responses.csv"))
    _dump(os.path.join(rd, "status.json"), dict(overall="COMPLETE", dose=len(r1), named=len(r2), primary=prim))


# ------------------------------------------------------------------------------------------------ Stage D --
def familiarization():
    _require(os.path.join(D["recognition_dose"], "status.json"), "Stage C recognition")
    fams, prim = _load(os.path.join(D["corpus_v2"], "families.json")), _primary()
    fam = _load(os.path.join(D["corpus_v2"], "familiarization_reserve.json"))
    sel = T.exposure_examples(fams, fam)
    fd = D["familiarization"]
    _dump(os.path.join(fd, "exposure_manifest.json"),
          {f"{k[0]}|{k[1]}": [dict(record_id=x["record_id"], response_id=x["response_id"], sequence=x["sequence"]) for x in v]
           for k, v in sel.items()})
    oai, led = _client(), _ledger()
    d1 = T.exposure_trials(fams, sel, prim)
    CO.write_csv(os.path.join(fd, "d1_trials.csv"), [{k: v for k, v in t.items() if k != "prompt"} for t in d1])
    r1 = CL.run_judgments(oai, led, d1, os.path.join(fd, "d1_raw_attempts.jsonl"), "exposure")
    _write_responses(r1, os.path.join(fd, "d1_responses.csv"))
    live = T.live_sessions(fams, prim)
    T.run_live(oai, led, live, os.path.join(fd, "d2_live_sessions.jsonl"))
    r2 = _jsonl(os.path.join(fd, "d2_live_sessions.jsonl"))
    _write_responses(r2, os.path.join(fd, "d2_responses.csv"))
    _dump(os.path.join(fd, "status.json"), dict(overall="COMPLETE", d1=len(r1), d2=len(r2)))


# --------------------------------------------------------------------------------------------- analyse --
def analyse():
    from spar_dynamic.dice_recognition_v2 import report
    report.run(EXP, D, old_pairs(), frozen_classifier())


if __name__ == "__main__":
    {"dryrun": dryrun, "api_preflight": api_preflight, "calibrate": calibrate, "elicitation_screen": elicitation_screen,
     "generate_corpus": generate_corpus, "recognition_dose": recognition_dose, "familiarization": familiarization,
     "analyse": analyse}[sys.argv[1]]()
