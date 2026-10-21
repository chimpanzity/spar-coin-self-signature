"""Descriptive pilot summary: source-string diagnostics and judge results (CSV + Markdown).

Everything here is rebuilt from the raw records; nothing inferential beyond simple binomial
confidence intervals and the Wald-Wolfowitz runs test on individual strings.
"""

from __future__ import annotations

import math
from collections import Counter
from itertools import groupby
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .config import PilotConfig
from .records import (
    JudgmentRecord,
    RunPaths,
    SourceRecord,
    TrialRecord,
    latest_judgments_by_trial,
    load_manifest,
    load_trials,
    read_jsonl,
)

CELLS = ("A", "B", "C", "D")


# ---------------------------------------------------------------- source diagnostics

def runs_test(s: str, symbol_a: str) -> dict[str, float]:
    """Wald-Wolfowitz runs test for a binary string (normal approximation, two-sided)."""
    n = len(s)
    n1 = s.count(symbol_a)
    n2 = n - n1
    runs = sum(1 for _ in groupby(s))
    if n1 == 0 or n2 == 0 or n < 2:
        return {"n_runs": runs, "expected_runs": float("nan"), "z": float("nan"), "p_two_sided": float("nan")}
    mu = 1 + 2 * n1 * n2 / n
    var = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n ** 2 * (n - 1))
    if var <= 0:
        return {"n_runs": runs, "expected_runs": mu, "z": float("nan"), "p_two_sided": float("nan")}
    z = (runs - mu) / math.sqrt(var)
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"n_runs": runs, "expected_runs": mu, "z": z, "p_two_sided": p}


def string_diagnostics(s: str, alphabet: str) -> dict[str, Any]:
    a, b = alphabet[0], alphabet[1]
    n = len(s)
    switches = sum(1 for i in range(1, n) if s[i] != s[i - 1])
    longest = max((len(list(g)) for _, g in groupby(s)), default=0)
    bigrams = Counter(s[i:i + 2] for i in range(n - 1))
    rt = runs_test(s, a)
    return {
        "length": n,
        f"prop_{a}": s.count(a) / n if n else float("nan"),
        "alternation_rate": switches / (n - 1) if n > 1 else float("nan"),
        "n_runs": rt["n_runs"],
        "expected_runs": rt["expected_runs"],
        "runs_test_z": rt["z"],
        "runs_test_p": rt["p_two_sided"],
        "longest_run": longest,
        "first_outcome": s[0] if s else None,
        **{f"bigram_{a}{a}": bigrams.get(a + a, 0), f"bigram_{a}{b}": bigrams.get(a + b, 0),
           f"bigram_{b}{a}": bigrams.get(b + a, 0), f"bigram_{b}{b}": bigrams.get(b + b, 0)},
    }


def source_tables(cfg: PilotConfig, sources: list[SourceRecord]) -> tuple[pd.DataFrame, pd.DataFrame]:
    a, b = cfg.generation.alphabet[0], cfg.generation.alphabet[1]
    rows = []
    for r in sources:
        if r.valid and r.parsed_string:
            rows.append({"source_model_label": r.source_model_label, "sample_id": r.sample_id,
                         "string": r.parsed_string, **string_diagnostics(r.parsed_string, cfg.generation.alphabet)})
    by_string = pd.DataFrame(rows)
    model_rows = []
    for label in cfg.model_labels:
        recs = [r for r in sources if r.source_model_label == label]
        valid = [r for r in recs if r.valid]
        invalid = [r for r in recs if not r.valid]
        d = by_string[by_string["source_model_label"] == label] if not by_string.empty else pd.DataFrame()
        pooled = "".join(r.parsed_string or "" for r in valid)
        bigram_counts: Counter = Counter()
        for r in valid:
            s = r.parsed_string or ""
            bigram_counts.update(s[i:i + 2] for i in range(len(s) - 1))
        n_big = sum(bigram_counts.values()) or 1
        row = {
            "source_model_label": label,
            "requested_model_id": cfg.model_id(label),
            "returned_model_ids": ";".join(sorted({r.returned_model_id or "" for r in valid})),
            "providers": ";".join(sorted({r.provider or "" for r in valid})),
            "n_calls": len(recs),
            "n_valid": len(valid),
            "n_invalid": len(invalid),
            "invalid_reasons": ";".join(sorted({r.invalid_reason or "" for r in invalid})),
            "n_distinct_strings": len({r.parsed_string for r in valid}),
            f"mean_prop_{a}": d[f"prop_{a}"].mean() if not d.empty else float("nan"),
            f"pooled_prop_{a}": pooled.count(a) / len(pooled) if pooled else float("nan"),
            "mean_alternation_rate": d["alternation_rate"].mean() if not d.empty else float("nan"),
            "mean_n_runs": d["n_runs"].mean() if not d.empty else float("nan"),
            "mean_runs_test_z": d["runs_test_z"].mean() if not d.empty else float("nan"),
            "n_strings_runs_test_p_lt_05": int((d["runs_test_p"] < 0.05).sum()) if not d.empty else 0,
            "mean_longest_run": d["longest_run"].mean() if not d.empty else float("nan"),
            "max_longest_run": int(d["longest_run"].max()) if not d.empty else 0,
            f"first_outcome_{a}_freq": (d["first_outcome"] == a).mean() if not d.empty else float("nan"),
            **{f"bigram_{k}_prop": bigram_counts.get(k, 0) / n_big for k in (a + a, a + b, b + a, b + b)},
            "mean_latency_ms": np.mean([r.latency_ms for r in recs]) if recs else float("nan"),
            "total_reported_cost_usd": sum((r.reported_cost or 0.0) for r in recs),
            "mean_completion_tokens": np.mean([(r.token_usage or {}).get("completion_tokens", np.nan) for r in valid]) if valid else float("nan"),
        }
        model_rows.append(row)
    return by_string, pd.DataFrame(model_rows)


# ---------------------------------------------------------------- judgment results

def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    lo = stats.beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return (float(lo), float(hi))


def trial_level_table(cfg: PilotConfig, trials: list[TrialRecord], judgments_flat: pd.DataFrame) -> pd.DataFrame:
    """One row per trial: the latest judgment attempt's full flat row (every column of
    judgments.csv), or a stub for a trial that has no judgment yet."""
    order = {t.trial_id: (cfg.model_labels.index(t.judge_model_label), t.trial_position) for t in trials}
    if len(judgments_flat):
        latest = (judgments_flat.sort_values(["trial_id", "attempt_number"])
                  .groupby("trial_id", as_index=False).tail(1))
        latest = latest[latest["trial_id"].isin(order)]
    else:
        latest = pd.DataFrame(columns=judgments_flat.columns)
    have = set(latest["trial_id"]) if len(latest) else set()
    stubs = []
    for t in trials:
        if t.trial_id in have:
            continue
        stubs.append({
            "trial_id": t.trial_id, "judge_model_label": t.judge_model_label, "trial_position": t.trial_position,
            "analytical_cell": t.analytical_cell, "subcell": t.subcell, "correct_answer": t.correct_answer,
            "source_pair": "-".join(sorted([t.source_1_model_label, t.source_2_model_label])),
            "source_1_model_label": t.source_1_model_label, "source_2_model_label": t.source_2_model_label,
            "source_1_sample_id": t.source_1_sample_id, "source_2_sample_id": t.source_2_sample_id,
            "display_order": t.display_order, "construction_seed": t.construction_seed,
            "stimulus_hash": t.stimulus_hash, "string_1_display": t.string_1_display,
            "string_2_display": t.string_2_display, "valid": False, "invalid_reason": "no_judgment",
            "correct": None, "n_attempts_for_trial": 0,
        })
    tl = pd.concat([latest, pd.DataFrame(stubs)], ignore_index=True) if stubs else latest.copy()
    if len(tl):
        tl["valid"] = tl["valid"].fillna(False).astype(bool)
        tl["_order"] = tl["trial_id"].map(order)
        tl = tl.sort_values("_order").drop(columns="_order").reset_index(drop=True)
        tl.insert(0, "judgment_id", tl.pop("record_id") if "record_id" in tl.columns else None)
        tl["attempts"] = tl["n_attempts_for_trial"]
    return tl


def judge_results(cfg: PilotConfig, tl: pd.DataFrame, judgments: list[JudgmentRecord]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    judge_rows, cell_rows, conf_rows = [], [], []
    for label in cfg.model_labels:
        d = tl[(tl["judge_model_label"] == label)]
        v = d[d["valid"]]
        n, k = len(v), int(v["correct"].sum()) if len(v) else 0
        lo, hi = clopper_pearson(k, n)
        cells: dict[str, dict[str, float]] = {}
        for c in CELLS:
            vc = v[v["analytical_cell"] == c]
            nc = len(vc)
            acc = vc["correct"].mean() if nc else float("nan")
            same_rate = (vc["parsed_judgment"] == "SAME").mean() if nc else float("nan")
            cells[c] = {"n": nc, "accuracy": acc, "same_response_rate": same_rate}
            cell_rows.append({"judge_model_label": label, "analytical_cell": c, "correct_answer": "SAME" if c in "AC" else "DIFFERENT",
                              "n_valid": nc, "n_correct": int(vc["correct"].sum()) if nc else 0,
                              "accuracy": acc, "same_response_rate": same_rate})
        own = v[v["analytical_cell"].isin(["A", "B"])]
        other = v[v["analytical_cell"].isin(["C", "D"])]
        n_invalid = sum(1 for r in judgments if r.judge_model_label == label and not r.valid)
        judge_rows.append({
            "judge_model_label": label,
            "requested_model_id": cfg.model_id(label),
            "n_trials": len(d),
            "n_valid_judgments": n,
            "n_invalid_attempts": n_invalid,
            "n_correct": k,
            "accuracy": k / n if n else float("nan"),
            "accuracy_ci95_low": lo,
            "accuracy_ci95_high": hi,
            "same_response_rate": (v["parsed_judgment"] == "SAME").mean() if n else float("nan"),
            **{f"acc_{c}": cells[c]["accuracy"] for c in CELLS},
            **{f"same_rate_{c}": cells[c]["same_response_rate"] for c in CELLS},
            "contrast_same_A_minus_C": cells["A"]["accuracy"] - cells["C"]["accuracy"],
            "contrast_different_B_minus_D": cells["B"]["accuracy"] - cells["D"]["accuracy"],
            "own_involved_accuracy_AB": own["correct"].mean() if len(own) else float("nan"),
            "other_only_accuracy_CD": other["correct"].mean() if len(other) else float("nan"),
            "own_minus_other": (own["correct"].mean() - other["correct"].mean()) if len(own) and len(other) else float("nan"),
            "mean_latency_ms": v["latency_ms"].mean() if n else float("nan"),
            "total_reported_cost_usd": sum((r.reported_cost or 0.0) for r in judgments if r.judge_model_label == label),
        })
        for truth in ("SAME", "DIFFERENT"):
            for resp in ("SAME", "DIFFERENT"):
                conf_rows.append({"judge_model_label": label, "correct_answer": truth, "response": resp,
                                  "n": int(((v["correct_answer"] == truth) & (v["parsed_judgment"] == resp)).sum())})
    return pd.DataFrame(judge_rows), pd.DataFrame(cell_rows), pd.DataFrame(conf_rows)


def pooled_by_source_pair(tl: pd.DataFrame) -> pd.DataFrame:
    v = tl[tl["valid"]]
    if v.empty:
        return pd.DataFrame()
    g = v.groupby(["source_pair", "correct_answer"]).agg(n=("correct", "size"), accuracy=("correct", "mean"),
                                                         same_response_rate=("parsed_judgment", lambda s: (s == "SAME").mean()))
    return g.reset_index()


# ---------------------------------------------------------------- external baselines

BASELINE_FEATURES = ["prop_H", "alternation_rate", "longest_run", "first_outcome_is_H", "bigram_HH_prop", "bigram_TT_prop"]


def string_feature_vector(s: str, alphabet: str) -> dict[str, float]:
    a, b = alphabet[0], alphabet[1]
    d = string_diagnostics(s, alphabet)
    n_big = max(1, len(s) - 1)
    return {
        "prop_H": d[f"prop_{a}"],
        "alternation_rate": d["alternation_rate"],
        "longest_run": float(d["longest_run"]),
        "first_outcome_is_H": 1.0 if d["first_outcome"] == a else 0.0,
        "bigram_HH_prop": d[f"bigram_{a}{a}"] / n_big,
        "bigram_TT_prop": d[f"bigram_{b}{b}"] / n_big,
    }


def _standardized_features(cfg: PilotConfig, sources: list[SourceRecord]) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Standardized feature vectors (z-scores over all valid strings) keyed by sample id, plus labels."""
    rows, ids, labels = [], [], {}
    for r in sources:
        if r.valid and r.parsed_string:
            rows.append([string_feature_vector(r.parsed_string, cfg.generation.alphabet)[f] for f in BASELINE_FEATURES])
            ids.append(r.sample_id)
            labels[r.sample_id] = r.source_model_label
    if not rows:
        return {}, {}
    X = np.array(rows, dtype=float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    return {sid: Z[i] for i, sid in enumerate(ids)}, labels


def baseline_loo_nearest_centroid(cfg: PilotConfig, sources: list[SourceRecord]) -> dict[str, Any]:
    """Baseline 1: leave-one-out nearest-centroid classification of source model from visible statistics."""
    feats, labels = _standardized_features(cfg, sources)
    ids = list(feats)
    if len(ids) < 6:
        return {"n": len(ids), "correct": 0, "accuracy": float("nan"), "chance": 1 / 3, "confusion": {}, "recall_by_model": {}}
    correct = 0
    confusion: dict[str, dict[str, int]] = {l: {m: 0 for m in cfg.model_labels} for l in cfg.model_labels}
    for sid in ids:
        centroids = {}
        for label in cfg.model_labels:
            members = [feats[o] for o in ids if o != sid and labels[o] == label]
            if members:
                centroids[label] = np.mean(members, axis=0)
        if not centroids:
            continue
        pred = min(centroids, key=lambda l: float(np.linalg.norm(feats[sid] - centroids[l])))
        confusion[labels[sid]][pred] += 1
        correct += int(pred == labels[sid])
    recall = {l: (confusion[l][l] / sum(confusion[l].values())) if sum(confusion[l].values()) else float("nan") for l in cfg.model_labels}
    return {"n": len(ids), "correct": correct, "accuracy": correct / len(ids), "chance": 1 / 3,
            "confusion": confusion, "recall_by_model": recall, "features": BASELINE_FEATURES}


def baseline_distance_judge(cfg: PilotConfig, sources: list[SourceRecord], trials: list[TrialRecord]) -> pd.DataFrame:
    """Baseline 2: answer SAME when the standardized feature distance between the two strings is
    below the median distance over all trials; scored per trial like an LLM judge."""
    feats, _ = _standardized_features(cfg, sources)
    rows = []
    for t in trials:
        if t.source_1_sample_id in feats and t.source_2_sample_id in feats:
            dist = float(np.linalg.norm(feats[t.source_1_sample_id] - feats[t.source_2_sample_id]))
        else:
            dist = float("nan")
        rows.append({"trial_id": t.trial_id, "judge_model_label": t.judge_model_label, "analytical_cell": t.analytical_cell,
                     "correct_answer": t.correct_answer, "feature_distance": dist})
    df = pd.DataFrame(rows)
    if df.empty or df["feature_distance"].isna().all():
        return df
    median = df["feature_distance"].median()
    df["baseline_judgment"] = np.where(df["feature_distance"] < median, "SAME", "DIFFERENT")
    df["baseline_correct"] = df["baseline_judgment"] == df["correct_answer"]
    df["median_distance"] = median
    return df


# ---------------------------------------------------------------- preregistered decision rules

def evaluate_decision_rules(cfg: PilotConfig, by_model: pd.DataFrame, jr: pd.DataFrame, tl: pd.DataFrame,
                            b1: dict[str, Any], b2: pd.DataFrame, judgments: list[JudgmentRecord],
                            sources: list[SourceRecord], manifest: dict) -> pd.DataFrame:
    """Evaluate the rules R0..RB of the preregistration (v1.0, 2026-09-21) and return one row per rule."""
    a = cfg.generation.alphabet[0]
    rows: list[dict[str, Any]] = []

    def add(rule: str, met: Any, value: str, threshold: str) -> None:
        rows.append({"rule": rule, "met": met, "value": value, "threshold": threshold})

    # R0 source signal
    loo_ok = (b1.get("correct", 0) >= 15) if b1.get("n", 0) >= 30 else (b1.get("accuracy", 0) >= 0.5)
    alt_spread = float(by_model["mean_alternation_rate"].max() - by_model["mean_alternation_rate"].min()) if len(by_model) else float("nan")
    run_spread = float(by_model["mean_longest_run"].max() - by_model["mean_longest_run"].min()) if len(by_model) else float("nan")
    stats_ok = (alt_spread >= 0.10) or (run_spread >= 2)
    add("R0 source signal present", bool(loo_ok and stats_ok),
        f"LOO {b1.get('correct')}/{b1.get('n')} ({_fmt(b1.get('accuracy'))}); alternation spread {_fmt(alt_spread)}; longest-run spread {_fmt(run_spread, 2)}",
        "LOO >= 15/30 and (alternation spread >= 0.10 or longest-run spread >= 2)")
    # R0' degenerate strings
    low = {r["source_model_label"]: int(r["n_distinct_strings"]) for _, r in by_model.iterrows() if r["n_distinct_strings"] < 8} if len(by_model) else {}
    add("R0' degenerate strings flag", "flag" if low else "clear", f"distinct strings below 8: {low or 'none'}", "any model with < 8 distinct strings among 10 is flagged")
    # R1
    if len(tl):
        v = tl[tl["valid"]]
        pooled_k, pooled_n = int(v["correct"].sum()), int(len(v))
        add("R1 pooled above chance", pooled_k >= 44 if pooled_n == 72 else (pooled_k / pooled_n >= 0.611 if pooled_n else False),
            f"{pooled_k}/{pooled_n} ({_fmt(pooled_k / pooled_n) if pooled_n else 'n/a'})", ">= 44/72 (0.611)")
        for _, r in jr.iterrows():
            k, n = int(r["n_correct"]), int(r["n_valid_judgments"])
            add(f"R1 {r['judge_model_label']} above chance", (k >= 17) if n == 24 else (k / n >= 0.708 if n else False),
                f"{k}/{n} ({_fmt(r['accuracy'])})", ">= 17/24 (0.708)")
    # R2 per judge, R2', R2d
    n_met, n_rev = 0, 0
    for _, r in jr.iterrows():
        own_other = r["own_minus_other"]
        met = bool(own_other >= 0.25 and r["contrast_same_A_minus_C"] >= 0 and r["contrast_different_B_minus_D"] >= 0)
        n_met += int(met)
        n_rev += int(own_other <= -0.25)
        add(f"R2 {r['judge_model_label']} own-model advantage", met,
            f"own-other {_fmt(own_other)}; A-C {_fmt(r['contrast_same_A_minus_C'])}; B-D {_fmt(r['contrast_different_B_minus_D'])}",
            "own-other >= +0.25 with A-C >= 0 and B-D >= 0")
    if len(tl):
        v = tl[tl["valid"]]
        own = v[v["analytical_cell"].isin(["A", "B"])]
        oth = v[v["analytical_cell"].isin(["C", "D"])]
        if len(own) and len(oth):
            diff = own["correct"].mean() - oth["correct"].mean()
            table = [[int(own["correct"].sum()), int(len(own) - own["correct"].sum())],
                     [int(oth["correct"].sum()), int(len(oth) - oth["correct"].sum())]]
            p_fisher = float(stats.fisher_exact(table, alternative="greater")[1])
            add("R2' pooled advantage", bool(diff >= 0.20),
                f"own {table[0][0]}/{len(own)} vs other {table[1][0]}/{len(oth)}; diff {_fmt(diff)}; Fisher one-sided p {_fmt(p_fisher)} (exploratory)",
                "pooled own-other >= +0.20")
    n_judges = len(jr)
    if n_judges:
        pattern = "reciprocal" if n_met == n_judges else ("reversed" if n_rev >= 2 else ("partial" if n_met >= 1 else "absent"))
        add("R2d reciprocal selectivity", pattern, f"{n_met} of {n_judges} judges meet R2; {n_rev} reversed", "all = reciprocal; 1-2 = partial; 0 = absent; >= 2 reversed = reversed")
    # R3 feasibility
    n_src_invalid = sum(1 for r in sources if not r.valid)
    n_jud_invalid = sum(1 for r in judgments if not r.valid and r.invalid_reason != "api_error")
    mode = (manifest.get("judgment_response_mode") or {}).get("effective")
    spent = sum((r.reported_cost if r.reported_cost is not None else (r.estimated_cost or 0.0)) for r in sources + judgments)
    add("R3 feasibility", bool(n_src_invalid <= 3 and n_jud_invalid <= 3 and mode == "structured" and spent < 10),
        f"invalid source calls {n_src_invalid}; invalid judgment attempts {n_jud_invalid}; mode {mode}; spend ${spent:.2f}",
        "<= 3 invalid source calls, <= 3 invalid judgment attempts, structured mode, spend < $10")
    # RB baselines
    if len(b2) and "baseline_correct" in b2.columns:
        b2_acc = float(b2["baseline_correct"].mean())
        add("RB baseline 2 (distance judge) accuracy", f"{int(b2['baseline_correct'].sum())}/{len(b2)}", f"{_fmt(b2_acc)}; chance 0.5; 44/72 is P = 0.038",
            "reference only")
        for _, r in jr.iterrows():
            b2j = b2[b2["judge_model_label"] == r["judge_model_label"]]
            b2j_acc = float(b2j["baseline_correct"].mean()) if len(b2j) else float("nan")
            add(f"RB {r['judge_model_label']} informative beyond visible statistics", bool(r["accuracy"] - b2j_acc >= 0.10) if not math.isnan(b2j_acc) else "n/a",
                f"judge {_fmt(r['accuracy'])} vs distance judge {_fmt(b2j_acc)} on the same trials", "judge accuracy exceeds baseline 2 by >= 0.10")
    add("RB baseline 1 (LOO nearest centroid) accuracy", f"{b1.get('correct')}/{b1.get('n')}", f"{_fmt(b1.get('accuracy'))}; chance 0.333; recall {dict((k, round(v, 2)) for k, v in (b1.get('recall_by_model') or {}).items())}",
        "reference only")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- report

def _fmt(x: Any, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, (float, np.floating)):
        return f"{x:.{nd}f}"
    return str(x)


def summary_markdown(cfg: PilotConfig, manifest: dict, by_model: pd.DataFrame, jr: pd.DataFrame,
                     cr: pd.DataFrame, conf: pd.DataFrame, pooled: pd.DataFrame, tl: pd.DataFrame,
                     validation_status: str | None, b1: dict[str, Any] | None = None,
                     b2: pd.DataFrame | None = None, rules: pd.DataFrame | None = None) -> str:
    a = cfg.generation.alphabet[0]
    run_id = manifest["run_id"]
    lines = [f"# Pilot summary: {run_id}", ""]
    lines.append(f"Validation status: **{validation_status or 'not run'}** (see validation_report.md). "
                 "This pilot is descriptive; it is not powered as a confirmatory test.")
    lines.append("")
    eff = ((manifest.get("phases") or {}).get("judgments") or {})
    mode = (manifest.get("judgment_response_mode") or {}).get("effective")
    lines.append(f"Judgment response mode: {mode or 'n/a'}. Display alphabet: {cfg.judgment.display_alphabet}. "
                 f"Reasoning effort: {cfg.judgment.reasoning_effort}.")
    lines.append("")
    lines.append("## Source-string diagnostics by model")
    lines.append("")
    if not by_model.empty:
        cols = ["source_model_label", "n_valid", "n_invalid", "n_distinct_strings", f"mean_prop_{a}", "mean_alternation_rate",
                "mean_n_runs", "mean_runs_test_z", "n_strings_runs_test_p_lt_05", "mean_longest_run", "max_longest_run",
                f"first_outcome_{a}_freq"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "---|" * len(cols))
        for _, r in by_model.iterrows():
            lines.append("| " + " | ".join(_fmt(r[c]) for c in cols) + " |")
        lines.append("")
        b = cfg.generation.alphabet
        bcols = [f"bigram_{k}_prop" for k in (b[0] + b[0], b[0] + b[1], b[1] + b[0], b[1] + b[1])]
        lines.append("2-gram proportions (pooled within model): " + "; ".join(
            f"{r['source_model_label']}: " + ", ".join(f"{c.split('_')[1]}={_fmt(r[c])}" for c in bcols)
            for _, r in by_model.iterrows()))
        lines.append("")
        lines.append("Returned model / provider per source model: " + "; ".join(
            f"{r['source_model_label']}: {r['returned_model_ids']} via {r['providers']}" for _, r in by_model.iterrows()))
        lines.append("")
    lines.append("## Judgment results by judge")
    lines.append("")
    if not jr.empty:
        lines.append("| judge | valid | invalid attempts | accuracy [95% CI] | SAME-rate | acc A | acc B | acc C | acc D | A-C | B-D | own (A+B) | other (C+D) | own-other |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in jr.iterrows():
            lines.append(
                f"| {r['judge_model_label']} | {r['n_valid_judgments']}/{r['n_trials']} | {r['n_invalid_attempts']} "
                f"| {_fmt(r['accuracy'])} [{_fmt(r['accuracy_ci95_low'], 2)}, {_fmt(r['accuracy_ci95_high'], 2)}] "
                f"| {_fmt(r['same_response_rate'])} | {_fmt(r['acc_A'])} | {_fmt(r['acc_B'])} | {_fmt(r['acc_C'])} | {_fmt(r['acc_D'])} "
                f"| {_fmt(r['contrast_same_A_minus_C'])} | {_fmt(r['contrast_different_B_minus_D'])} "
                f"| {_fmt(r['own_involved_accuracy_AB'])} | {_fmt(r['other_only_accuracy_CD'])} | {_fmt(r['own_minus_other'])} |"
            )
        lines.append("")
        lines.append("SAME-response rate by cell (A, C are SAME trials; B, D are DIFFERENT trials):")
        lines.append("")
        lines.append("| judge | A | B | C | D |")
        lines.append("|---|---|---|---|---|")
        for _, r in jr.iterrows():
            lines.append(f"| {r['judge_model_label']} | " + " | ".join(_fmt(r[f'same_rate_{c}']) for c in CELLS) + " |")
        lines.append("")
        lines.append("Confusion matrices (rows: correct answer; columns: response):")
        lines.append("")
        for label in cfg.model_labels:
            c = conf[conf["judge_model_label"] == label]
            if c.empty:
                continue
            get = lambda t, r: int(c[(c["correct_answer"] == t) & (c["response"] == r)]["n"].iloc[0])
            lines.append(f"- {label}: SAME->SAME {get('SAME', 'SAME')}, SAME->DIFFERENT {get('SAME', 'DIFFERENT')}, "
                         f"DIFFERENT->SAME {get('DIFFERENT', 'SAME')}, DIFFERENT->DIFFERENT {get('DIFFERENT', 'DIFFERENT')}")
        lines.append("")
    if not pooled.empty:
        lines.append("## Pooled over judges: accuracy by source pair")
        lines.append("")
        lines.append("| source pair | correct answer | n | accuracy | SAME-rate |")
        lines.append("|---|---|---|---|---|")
        for _, r in pooled.iterrows():
            lines.append(f"| {r['source_pair']} | {r['correct_answer']} | {r['n']} | {_fmt(r['accuracy'])} | {_fmt(r['same_response_rate'])} |")
        lines.append("")
    invalid_rows = tl[~tl["valid"]] if not tl.empty else pd.DataFrame()
    lines.append(f"Trials without a valid judgment: {len(invalid_rows)}. Trial-level detail: trial_level.csv.")
    lines.append("")
    if b1 is not None and b1.get("n"):
        lines.append("## External baselines (no notion of model identity)")
        lines.append("")
        lines.append(f"Baseline 1, leave-one-out nearest centroid on standardized {', '.join(b1.get('features', []))}: "
                     f"{b1['correct']}/{b1['n']} correct ({_fmt(b1['accuracy'])}; chance 0.333). Recall by model: "
                     + ", ".join(f"{k} {_fmt(v)}" for k, v in b1["recall_by_model"].items()) + ".")
        lines.append("")
    if b2 is not None and len(b2) and "baseline_correct" in b2.columns:
        lines.append(f"Baseline 2, distance-rule judge on the same trials (SAME when feature distance < median {_fmt(float(b2['median_distance'].iloc[0]))}): "
                     f"overall {int(b2['baseline_correct'].sum())}/{len(b2)} ({_fmt(float(b2['baseline_correct'].mean()))}).")
        lines.append("")
        lines.append("| judge session | acc A | acc B | acc C | acc D | overall |")
        lines.append("|---|---|---|---|---|---|")
        for label in cfg.model_labels:
            d = b2[b2["judge_model_label"] == label]
            cells = [d[d["analytical_cell"] == c]["baseline_correct"].mean() if len(d[d["analytical_cell"] == c]) else float("nan") for c in CELLS]
            lines.append(f"| {label} | " + " | ".join(_fmt(x) for x in cells) + f" | {_fmt(float(d['baseline_correct'].mean()) if len(d) else float('nan'))} |")
        lines.append("")
    if rules is not None and len(rules):
        lines.append("## Preregistered decision rules (v1.0, 2026-09-21)")
        lines.append("")
        lines.append("| rule | met | value | threshold |")
        lines.append("|---|---|---|---|")
        for _, r in rules.iterrows():
            lines.append(f"| {r['rule']} | {r['met']} | {r['value']} | {r['threshold']} |")
        lines.append("")
    lines.append("## Reading these numbers")
    lines.append("")
    lines.append("Above-chance accuracy alone shows that the source models produce discriminable strings; it does not "
                 "establish self-recognition. The pattern of interest is a judge-specific advantage that follows the "
                 "judge's own model: A > C on SAME trials and B > D on DIFFERENT trials, ideally for every judge "
                 "(reciprocal selectivity). Describe any such result as a behavioral self-signature or an own-model "
                 "discrimination advantage, not as self-awareness. With 6 trials per cell, cell accuracies move in "
                 "steps of 0.167; treat contrasts as directional hints for planning a preregistered study.")
    lines.append("")
    return "\n".join(lines)


def summarize_run(cfg: PilotConfig, paths: RunPaths, validation_status: str | None = None) -> dict[str, Any]:
    manifest = load_manifest(paths)
    sources = read_jsonl(paths.source_calls, SourceRecord)
    judgments = read_jsonl(paths.judgment_calls, JudgmentRecord)
    trials = load_trials(paths) if paths.trials_json.exists() else []

    paths.derived_dir.mkdir(parents=True, exist_ok=True)
    paths.results_dir.mkdir(parents=True, exist_ok=True)

    # flat, self-contained CSVs (rebuilt from raw every time)
    from .export import export_run
    exported = export_run(cfg, paths)

    by_string, by_model = source_tables(cfg, sources)
    by_string.to_csv(paths.results_dir / "source_diagnostics_by_string.csv", index=False)
    by_model.to_csv(paths.results_dir / "source_diagnostics_by_model.csv", index=False)

    tl = trial_level_table(cfg, trials, exported["frames"]["judgments"]) if trials else pd.DataFrame()
    if not tl.empty:
        tl.to_csv(paths.results_dir / "trial_level.csv", index=False)
        jr, cr, conf = judge_results(cfg, tl, judgments)
        pooled = pooled_by_source_pair(tl)
    else:
        jr, cr, conf, pooled = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    jr.to_csv(paths.results_dir / "judge_results.csv", index=False)
    cr.to_csv(paths.results_dir / "cell_results.csv", index=False)
    conf.to_csv(paths.results_dir / "confusion_matrices.csv", index=False)
    pooled.to_csv(paths.results_dir / "pooled_by_source_pair.csv", index=False)

    b1 = baseline_loo_nearest_centroid(cfg, sources)
    b2 = baseline_distance_judge(cfg, sources, trials) if trials else pd.DataFrame()
    b2.to_csv(paths.results_dir / "baseline_distance_judge.csv", index=False)
    pd.DataFrame([{"baseline": "loo_nearest_centroid", "n": b1.get("n"), "correct": b1.get("correct"),
                   "accuracy": b1.get("accuracy"), "chance": b1.get("chance"),
                   **{f"recall_{k}": v for k, v in (b1.get("recall_by_model") or {}).items()}}]) \
        .to_csv(paths.results_dir / "baseline_loo_classifier.csv", index=False)
    rules = evaluate_decision_rules(cfg, by_model, jr, tl, b1, b2, judgments, sources, manifest) if len(jr) else pd.DataFrame()
    rules.to_csv(paths.results_dir / "decision_rules.csv", index=False)

    md = summary_markdown(cfg, manifest, by_model, jr, cr, conf, pooled, tl, validation_status, b1, b2, rules)
    (paths.results_dir / "summary.md").write_text(md, encoding="utf-8")
    return {"summary_md": paths.results_dir / "summary.md", "judge_results": jr, "by_model": by_model, "trial_level": tl,
            "baseline_loo": b1, "baseline_distance": b2, "decision_rules": rules}
