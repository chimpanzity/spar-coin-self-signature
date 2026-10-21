"""
analyze_pilot.py — descriptive summaries for the implicit-truth pilot.

Loads every per-session CSV listed in a pilot manifest, computes the standard
PACA measures (win rate, marginal choice frequencies, switch rate, Wald-Wolfowitz
runs Z, Proteus activation rate) plus the paper's Brown-Rosenthal per-session
sequential-dependence test (imported verbatim from code/verify_brown_rosenthal.py),
scans response_text for explicit prime references, and emits:

  data/implicit_truth_pilot/summary/session_measures.csv
  data/implicit_truth_pilot/summary/two_by_two.csv
  data/implicit_truth_pilot/summary/interaction_contrasts.csv
  data/implicit_truth_pilot/summary/prime_reference_check.csv
  data/implicit_truth_pilot/summary/plot_*.png
  data/implicit_truth_pilot/summary/implicit_truth_pilot_report.md

No inferential p-values are quoted for the truth x frame interaction; item-level
values are retained so directionality can be inspected.
"""

import argparse, csv, os, re, sys
from collections import defaultdict
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "code"))
from verify_brown_rosenthal import br as brown_rosenthal   # paper's implementation

MEASURES = [
    "win_rate", "p_triangle", "p_star", "switch_rate", "runs_z",
    "activation_rate", "br_own_p", "br_opp_p", "br_out_p", "br_lag1",
]

PRIME_TERMS = ["maryland", "annapolis", "baltimore", "capital", "largest city",
               "the statement", "the fact"]


def wald_wolfowitz_runs_z(seq):
    """Runs test Z for a binary sequence with two symbols. Continuity-correction free.
    Returns nan if either symbol has count < 1.
    """
    a = [s for s in seq if s in ("T", "S")]
    n1 = a.count("T"); n2 = a.count("S")
    if n1 < 1 or n2 < 1:
        return float("nan")
    N = n1 + n2
    runs = 1
    for i in range(1, len(a)):
        if a[i] != a[i - 1]:
            runs += 1
    mu = 2 * n1 * n2 / N + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - N) / (N * N * (N - 1))
    if var <= 0:
        return float("nan")
    return (runs - mu) / np.sqrt(var)


def load_session(csv_path):
    df = pd.read_csv(csv_path)
    return df


def session_measures(df) -> dict:
    """Compute all PACA measures for one session dataframe."""
    m = {}
    n = len(df)
    m["n_trials"] = n
    if n == 0:
        for k in MEASURES:
            m[k] = float("nan")
        return m
    m["win_rate"] = float(df["subject_win"].astype(int).mean())
    m["p_triangle"] = float((df["subject_choice"] == "T").mean())
    m["p_star"] = float((df["subject_choice"] == "S").mean())
    seq = df.sort_values("trial")["subject_choice"].tolist()
    switches = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
    m["switch_rate"] = switches / (len(seq) - 1) if len(seq) > 1 else float("nan")
    m["runs_z"] = wald_wolfowitz_runs_z(seq)
    m["activation_rate"] = float((df["n_channels_active"].astype(int) > 0).mean())
    if n >= 4:
        try:
            own_p, opp_p, out_p, lag1 = brown_rosenthal(df.copy())
        except Exception as e:
            print(f"  BR failed on session ({e}); leaving NaN")
            own_p = opp_p = out_p = lag1 = float("nan")
    else:
        own_p = opp_p = out_p = lag1 = float("nan")
    m["br_own_p"] = float(own_p) if own_p == own_p else float("nan")
    m["br_opp_p"] = float(opp_p) if opp_p == opp_p else float("nan")
    m["br_out_p"] = float(out_p) if out_p == out_p else float("nan")
    m["br_lag1"]  = float(lag1)  if lag1  == lag1  else float("nan")
    return m


def prime_reference_hits(df, prime_text: str):
    """Return rows whose response_text case-insensitively contains prime tokens."""
    rows = []
    for _, r in df.iterrows():
        text = str(r.get("response_text", "") or "")
        low = text.lower()
        hits = [t for t in PRIME_TERMS if t in low]
        if hits:
            rows.append({
                "condition_id": r.get("_condition_id", ""),
                "trial": int(r["trial"]),
                "prime_text": prime_text,
                "response_text": text,
                "matched_terms": "|".join(hits),
            })
    return rows


def two_by_two(session_df: pd.DataFrame, measure: str) -> pd.DataFrame:
    """Aggregate one measure across (truth x frame) collapsing item family."""
    pivot = session_df.pivot_table(
        index="prime_truth", columns="frame", values=measure, aggfunc="mean")
    # ensure canonical ordering
    pivot = pivot.reindex(index=["true", "false"],
                          columns=["minimalist", "informed"])
    return pivot


def interaction_contrast(pivot: pd.DataFrame) -> float:
    """(False - True)_Informed - (False - True)_Minimalist."""
    try:
        false_min = pivot.loc["false", "minimalist"]
        true_min  = pivot.loc["true", "minimalist"]
        false_inf = pivot.loc["false", "informed"]
        true_inf  = pivot.loc["true", "informed"]
        return float((false_inf - true_inf) - (false_min - true_min))
    except KeyError:
        return float("nan")


def item_consistency(session_df: pd.DataFrame, measure: str) -> dict:
    """For each item family, sign of (false - true) collapsed across frames if
    both cells exist; then report whether the two items agree in direction."""
    out = {}
    for item in sorted(session_df["prime_item"].unique()):
        sub = session_df[session_df["prime_item"] == item]
        f = sub[sub["prime_truth"] == "false"][measure].mean()
        t = sub[sub["prime_truth"] == "true"][measure].mean()
        out[item] = f - t
    if len(out) == 2:
        vals = list(out.values())
        out["_agree"] = bool(np.sign(vals[0]) == np.sign(vals[1]) and not np.isnan(vals[0]) and not np.isnan(vals[1]))
    return out


def load_manifest(path):
    # Force string dtypes on truth-label columns so "true"/"false" aren't
    # auto-coerced to Python bools by pandas.
    return pd.read_csv(path, dtype={"prime_truth": str, "prime_item": str,
                                    "frame": str, "prime_text": str, "status": str})


def plot_2x2(session_df: pd.DataFrame, measure: str, out_path: str, title: str):
    fig, ax = plt.subplots(figsize=(5.5, 4))
    # x = frame, group = truth; show session-level points and mean lines
    x_positions = {"minimalist": 0, "informed": 1}
    colors = {"true": "#1f77b4", "false": "#d62728"}
    markers = {"maryland_capital": "o", "maryland_largest_city": "s"}
    means = defaultdict(list)
    for _, r in session_df.iterrows():
        x = x_positions[r["frame"]]
        val = r[measure]
        if pd.isna(val):
            continue
        ax.scatter(x, val, c=colors[r["prime_truth"]],
                   marker=markers.get(r["prime_item"], "x"),
                   s=90, alpha=0.85, edgecolor="black", linewidth=0.5)
        means[(r["frame"], r["prime_truth"])].append(val)
    for (frame, truth), vals in means.items():
        ax.plot([x_positions[frame] - 0.12, x_positions[frame] + 0.12],
                [np.mean(vals)] * 2, color=colors[truth], linewidth=2.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["minimalist", "informed"])
    ax.set_ylabel(measure)
    ax.set_title(title)
    # legend
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker='o', color='w', label='true prime',
               markerfacecolor=colors['true'], markersize=9, markeredgecolor='black'),
        Line2D([0], [0], marker='o', color='w', label='false prime',
               markerfacecolor=colors['false'], markersize=9, markeredgecolor='black'),
        Line2D([0], [0], marker='o', color='w', label='item: capital',
               markerfacecolor='gray', markersize=9, markeredgecolor='black'),
        Line2D([0], [0], marker='s', color='w', label='item: largest city',
               markerfacecolor='gray', markersize=9, markeredgecolor='black'),
    ]
    ax.legend(handles=legend_elems, fontsize=8, loc='best')
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", default="data/implicit_truth_pilot/summary")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    man = load_manifest(args.manifest)
    # Only successful rows enter the analysis; failed rows are reported separately.
    ok = man[man["status"] == "ok"].copy()

    session_rows = []
    prime_hits_all = []
    integrity = {
        "expected_sessions": len(man),
        "completed_sessions": int((man["status"] == "ok").sum()),
        "failed_sessions": int((man["status"] != "ok").sum()),
        "expected_trials": int(man["n_trials"].sum()),
        "completed_trials": 0,
        "parse_fallbacks": 0,
        "truncation_fallbacks": 0,
        "api_fallbacks": 0,
        "served_models": set(),
    }

    for _, mrow in ok.iterrows():
        p = mrow["csv_path"]
        if not p or not os.path.exists(p):
            print(f"[warn] missing CSV for condition {mrow['condition_id']}: {p!r}")
            continue
        df = load_session(p)
        m = session_measures(df)
        integrity["completed_trials"] += len(df)
        cs = df.get("choice_source", pd.Series([]))
        integrity["parse_fallbacks"]     += int((cs == "fallback_parse_fail").sum())
        integrity["truncation_fallbacks"]+= int((cs == "fallback_truncation").sum())
        integrity["api_fallbacks"]       += int((cs == "fallback_api_fail").sum())
        for s in df.get("served_model", pd.Series([])).dropna().unique():
            integrity["served_models"].add(s)

        row = {
            "condition_id": int(mrow["condition_id"]),
            "frame": mrow["frame"],
            "prime_item": mrow["prime_item"],
            "prime_truth": mrow["prime_truth"],
            "prime_text": mrow["prime_text"],
            "pair_id": int(mrow["pair_id"]),
            "csv_path": p,
        }
        row.update(m)
        session_rows.append(row)

        df["_condition_id"] = mrow["condition_id"]
        prime_hits_all.extend(prime_reference_hits(df, mrow["prime_text"]))

    sdf = pd.DataFrame(session_rows).sort_values("condition_id")
    sdf.to_csv(os.path.join(args.out_dir, "session_measures.csv"), index=False)

    # 2x2 tables per measure
    tables = {}
    contrasts = {}
    item_agreement = {}
    for measure in MEASURES:
        pivot = two_by_two(sdf, measure)
        tables[measure] = pivot
        contrasts[measure] = interaction_contrast(pivot)
        item_agreement[measure] = item_consistency(sdf, measure)

    # write 2x2 tables (long format for easy reading)
    with open(os.path.join(args.out_dir, "two_by_two.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["measure", "prime_truth", "frame", "value"])
        for measure, pivot in tables.items():
            for truth in ["true", "false"]:
                for frame in ["minimalist", "informed"]:
                    try:
                        v = pivot.loc[truth, frame]
                    except KeyError:
                        v = float("nan")
                    w.writerow([measure, truth, frame, v])

    with open(os.path.join(args.out_dir, "interaction_contrasts.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["measure", "interaction_false_minus_true_informed_minus_minimalist"])
        for measure, v in contrasts.items():
            w.writerow([measure, v])

    # prime reference check
    with open(os.path.join(args.out_dir, "prime_reference_check.csv"), "w",
              newline="", encoding="utf-8") as f:
        cols = ["condition_id", "trial", "prime_text", "matched_terms", "response_text"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in prime_hits_all:
            w.writerow({k: r[k] for k in cols})

    # plots
    plot_2x2(sdf, "win_rate",        os.path.join(args.out_dir, "plot_win_rate.png"),        "Win rate by truth x frame")
    plot_2x2(sdf, "switch_rate",     os.path.join(args.out_dir, "plot_switch_rate.png"),     "Switch rate by truth x frame")
    plot_2x2(sdf, "activation_rate", os.path.join(args.out_dir, "plot_activation.png"),      "Proteus activation by truth x frame")
    plot_2x2(sdf, "p_star",          os.path.join(args.out_dir, "plot_p_star.png"),          "P(STAR) by truth x frame")
    plot_2x2(sdf, "br_lag1",         os.path.join(args.out_dir, "plot_br_lag1.png"),         "Brown-Rosenthal lag-1 own coefficient")

    # Markdown report
    lines = []
    lines.append("# Implicit-Truth Pilot Report")
    lines.append("")
    lines.append(f"Experiment tag: `{'implicit_truth_pilot_v1'}`")
    lines.append("")
    lines.append("## A. Run integrity")
    lines.append(f"- Expected sessions: {integrity['expected_sessions']}")
    lines.append(f"- Completed sessions: {integrity['completed_sessions']}")
    lines.append(f"- Failed sessions: {integrity['failed_sessions']}")
    lines.append(f"- Expected trials: {integrity['expected_trials']}")
    lines.append(f"- Completed trials: {integrity['completed_trials']}")
    lines.append(f"- Parse fallbacks: {integrity['parse_fallbacks']}")
    lines.append(f"- Truncation fallbacks: {integrity['truncation_fallbacks']}")
    lines.append(f"- API fallbacks: {integrity['api_fallbacks']}")
    lines.append(f"- Served models observed: {sorted(integrity['served_models'])}")
    lines.append("")

    lines.append("## B. Eight-session measures")
    lines.append("")
    lines.append("| cond | frame | item | truth | win | P(T) | P(S) | switch | runs_z | activation | BR own p | BR opp p | BR out p | BR lag1 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in sdf.iterrows():
        lines.append("| {cid} | {fr} | {it} | {tr} | {win:.3f} | {pt:.3f} | {ps:.3f} | {sw:.3f} | {rz:.2f} | {ac:.3f} | {bo:.3f} | {bp:.3f} | {bu:.3f} | {bl:+.2f} |".format(
            cid=int(r["condition_id"]), fr=r["frame"], it=r["prime_item"], tr=r["prime_truth"],
            win=r["win_rate"], pt=r["p_triangle"], ps=r["p_star"], sw=r["switch_rate"],
            rz=r["runs_z"], ac=r["activation_rate"], bo=r["br_own_p"], bp=r["br_opp_p"],
            bu=r["br_out_p"], bl=r["br_lag1"]))
    lines.append("")

    lines.append("## C. Truth x Frame descriptive tables")
    for measure, pivot in tables.items():
        lines.append(f"")
        lines.append(f"### {measure}")
        lines.append("")
        lines.append("| truth \\\\ frame | minimalist | informed |")
        lines.append("|---|---|---|")
        for truth in ["true", "false"]:
            row = f"| {truth} |"
            for frame in ["minimalist", "informed"]:
                try:
                    v = pivot.loc[truth, frame]
                    row += f" {v:.3f} |"
                except KeyError:
                    row += " NaN |"
            lines.append(row)
    lines.append("")

    lines.append("## D. Interaction contrasts")
    lines.append("")
    lines.append("Contrast = (False - True)_Informed - (False - True)_Minimalist")
    lines.append("")
    lines.append("| measure | contrast |")
    lines.append("|---|---|")
    for measure, v in contrasts.items():
        lines.append(f"| {measure} | {v:+.4f} |")
    lines.append("")

    lines.append("## E. Item consistency")
    lines.append("")
    lines.append("For each item, value = (False - True) collapsed across frames. "
                 "`agree` = both items point in the same direction.")
    lines.append("")
    lines.append("| measure | capital | largest_city | agree |")
    lines.append("|---|---|---|---|")
    for measure, ia in item_agreement.items():
        cap = ia.get("maryland_capital", float("nan"))
        lc  = ia.get("maryland_largest_city", float("nan"))
        ag  = ia.get("_agree", False)
        lines.append(f"| {measure} | {cap:+.4f} | {lc:+.4f} | {ag} |")
    lines.append("")

    lines.append("## F. Prime-reference leakage check")
    lines.append("")
    hits_by_cond = defaultdict(int)
    trials_by_cond = defaultdict(int)
    for _, r in sdf.iterrows():
        trials_by_cond[r["condition_id"]] = r["n_trials"]
    for r in prime_hits_all:
        hits_by_cond[r["condition_id"]] += 1
    lines.append("| condition | hits | trials | fraction |")
    lines.append("|---|---|---|---|")
    for cid in sorted({r["condition_id"] for _, r in sdf.iterrows()}):
        h = hits_by_cond.get(cid, 0)
        n = trials_by_cond.get(cid, 0)
        frac = h / n if n else 0.0
        lines.append(f"| {cid} | {h} | {n} | {frac:.3f} |")
    lines.append("")
    lines.append(f"Total flagged trials: **{len(prime_hits_all)}**. "
                 f"Details in `prime_reference_check.csv`. Not excluded automatically.")
    lines.append("")

    lines.append("## G. Interpretation caveats")
    lines.append("")
    lines.append("- This is an 8-session pilot (2 item families x 2 frames x 2 truth "
                 "statuses). It cannot support inferential claims about implicit "
                 "truth processing.")
    lines.append("- Item-family agreement in direction is the primary signal to "
                 "inspect; disagreement means whatever effect exists is not yet "
                 "clearly separable from lexical / factual idiosyncrasies.")
    lines.append("- Explicit prime references, if any, should be inspected manually "
                 "before drawing conclusions.")

    with open(os.path.join(args.out_dir, "implicit_truth_pilot_report.md"),
              "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[analyze] wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()
