"""
analyze_believed_self.py — analysis for the PACA believed-self generator pilot. Written before any live data.

    python task/analyze_believed_self.py [--data data/believed_self_pilot]

Primary (per session, PACA Brown-Rosenthal framework, imported from code/verify_brown_rosenthal.py unchanged):
  logistic regression of the current forecast (TRIANGLE = 1) on own1, own2 (previous forecasts), opp1, opp2 (previous
  blue-circle locations, i.e. the presumed generator's previous choices) and out1, out2 (previous outcomes, correct = +1),
  all coded +/-1, fitted with PACA's ridge-IRLS `fit`. Own and Circle block p-values are PACA's `br` (Own vs intercept;
  Circle incremental over Own). NOTE: PACA's Outcome block uses own x outcome, which under +/-1 coding equals the circle
  lag exactly (outcome = own x circle), so it can add no information; it is reported for continuity only. The outcome
  main-effect block (out1, out2) is tested here incrementally over Own + Circle. Separation is flagged.
  Descriptive: P(forecast_t = circle_{t-1}) ("copy last location").
Secondary: P(TRIANGLE), |P(T) - .5|, switch rate, Wald-Wolfowitz runs z (PACA convention: + = over-alternation),
  transition frequencies, accuracy, Proteus channel activation.
Contrasts: believed self - believed other within each (model, actual generator); difference of those differences.
One session per cell: everything here is descriptive. No inferential error bars across rounds.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
import believed_self as B                                      # noqa: E402
from analyze_pilot import wald_wolfowitz_runs_z                # noqa: E402  (PACA implementation)
from verify_brown_rosenthal import br, fit, ll                 # noqa: E402  (PACA implementation)
from scipy import stats                                        # noqa: E402

SELF_C, OTHER_C = "#2a78d6", "#eb6834"      # dataviz default categorical slots 1-2 (believed self / believed other)
INK, MUTED, GRID = "#2b2b2a", "#6b6a64", "#e4e3de"
COEFS = ["own1", "own2", "opp1", "opp2", "out1", "out2"]


def load(data_dir):
    rows = []
    for p in sorted(glob.glob(os.path.join(data_dir, "*", "*", "trials.jsonl"))):
        if "_validation" in os.path.relpath(p, data_dir):
            continue
        with open(p) as f:
            rows += [json.loads(l) for l in f if l.strip()]
    return pd.DataFrame(rows)


def br_full(d):
    """Full-model coefficients with PACA's design and ridge; separation flagged."""
    d = d.sort_values("trial").reset_index(drop=True)
    cs = np.where(d.forecast == "T", 1, -1); os_ = np.where(d.circle == "T", 1, -1); ws = np.where(d.correct == 1, 1, -1)
    s = lambda a, k: pd.Series(a).shift(k)
    X = pd.DataFrame({"own1": s(cs, 1), "own2": s(cs, 2), "opp1": s(os_, 1), "opp2": s(os_, 2),
                      "out1": s(ws, 1), "out2": s(ws, 2)}).iloc[2:]
    y = (d.forecast == "T").astype(float).values[2:]
    des = lambda ks: np.column_stack([np.ones(len(X))] + [X[k].values for k in ks])
    D = des(COEFS)
    b = fit(D, y)
    p = 1 / (1 + np.exp(-np.clip(D @ b, -30, 30)))
    sep = bool(np.max(np.abs(b[1:])) > 8 or np.mean((p < 1e-3) | (p > 1 - 1e-3)) > 0.05)
    base = des(COEFS[:4])
    lr = 2 * (ll(D, y, b) - ll(base, y, fit(base, y)))
    out_main_p = float(stats.chi2.sf(max(lr, 0.0), df=2))
    return dict(zip(["intercept"] + COEFS, b)), sep, out_main_p


def session_measures(d):
    d = d.sort_values("trial")
    f, c = d.forecast.tolist(), d.circle.tolist()
    n = len(f)
    m = {"n_trials": n, "accuracy": d.correct.mean(), "p_triangle": f.count("T") / n, "p_star": f.count("S") / n}
    m["abs_bias"] = abs(m["p_triangle"] - 0.5)
    m["switch_rate"] = sum(a != b for a, b in zip(f, f[1:])) / (n - 1)
    m["runs_z"] = wald_wolfowitz_runs_z(f)
    for a in "TS":
        for b_ in "TS":
            prev = [i for i in range(n - 1) if f[i] == a]
            m[f"P({b_}|{a})"] = (sum(f[i + 1] == b_ for i in prev) / len(prev)) if prev else np.nan
    m["copy_last_circle"] = sum(f[i] == c[i - 1] for i in range(1, n)) / (n - 1)
    m["circle_p_triangle"] = c.count("T") / n
    m["circle_switch_rate"] = sum(a != b for a, b in zip(c, c[1:])) / (n - 1)
    m["proteus_activation"] = d.proteus_active.mean()        # meaningful for Proteus; computed (not acted on) for random
    m["mean_attempts"] = d.attempts.mean()
    m["final_line_exact_rate"] = d.final_line_exact.mean()
    m["cost_usd"] = d.cost_usd.sum()
    m["mean_completion_tokens"] = d.completion_tokens.mean()
    g = d.rename(columns={"forecast": "subject_choice", "circle": "computer_choice", "correct": "subject_win"})
    own_p, opp_p, out_p, lag1 = br(g)
    m.update(br_own_p=own_p, br_opp_p=opp_p, br_out_p=out_p, br_lag1=lag1)
    coefs, sep, out_main_p = br_full(d)
    m.update({f"coef_{k}": v for k, v in coefs.items()})
    m["br_separation_flag"] = sep
    m["br_outcome_main_p"] = out_main_p
    return m


def analyze(data_dir):
    df = load(data_dir)
    out = os.path.join(data_dir, "analysis")
    os.makedirs(out, exist_ok=True)
    statuses = {os.path.basename(os.path.dirname(p)): json.load(open(p))
                for p in glob.glob(os.path.join(data_dir, "*", "*", "status.json")) if "_validation" not in os.path.relpath(p, data_dir)}
    sess = []
    for s in B.sessions():
        d = df[df.session_id == s.session_id] if len(df) else df
        st = statuses.get(s.session_id, {"status": "not_run", "completed_trials": 0, "note": ""})
        base = {"session_id": s.session_id, "model": s.model, "actual_generator": s.generator, "believed_generator": s.belief,
                "condition": s.code, "session_seed": s.seed, "status": st["status"], "note": st.get("note", "")}
        sess.append({**base, **(session_measures(d) if len(d) >= 4 else {"n_trials": len(d)})})
    S = pd.DataFrame(sess)
    S.to_csv(os.path.join(out, "session_measures.csv"), index=False)
    if len(df):
        df.drop(columns=["user_prompt", "response_text"]).to_csv(os.path.join(out, "trials.csv"), index=False)
    measures = ["accuracy", "p_triangle", "abs_bias", "switch_rate", "runs_z", "copy_last_circle", "proteus_activation",
                "br_lag1", "coef_own1", "coef_own2", "coef_opp1", "coef_opp2", "coef_out1", "coef_out2"]
    C = []
    for m in B.MODEL_ORDER:
        for meas in measures:
            row = {"model": m, "measure": meas}
            for g in B.GENERATORS:
                def v(b):
                    x = S[(S.model == m) & (S.actual_generator == g) & (S.believed_generator == b)]
                    return float(x[meas].iloc[0]) if len(x) and meas in x and pd.notna(x[meas].iloc[0]) else np.nan
                row[f"{g}_self"], row[f"{g}_other"] = v("self"), v("other")
                row[f"{g}_self_minus_other"] = row[f"{g}_self"] - row[f"{g}_other"]
            row["diff_of_diffs_proteus_minus_random"] = row["proteus_self_minus_other"] - row["random_self_minus_other"]
            C.append(row)
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(out, "cross_condition_contrasts.csv"), index=False)
    figures(S, out)
    report(S, C, df, data_dir, out)
    with zipfile.ZipFile(os.path.join(data_dir, "PACA_believed_self_pilot_outputs.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(data_dir):
            if "_validation" in os.path.relpath(root, data_dir):
                continue
            for fn in files:
                if not fn.endswith(".zip"):
                    p = os.path.join(root, fn)
                    z.write(p, os.path.relpath(p, data_dir))
        for p in (os.path.join(HERE, "believed_self.py"), os.path.join(HERE, "run_believed_self_pilot.py"), __file__):
            z.write(p, os.path.join("code", os.path.basename(p)))
    return S, C


# ---------------------------------------------------------------------------
# Figures (static PNGs; one axis per panel; believed self = blue, other = orange; Proteus filled, random hollow)
# ---------------------------------------------------------------------------

def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _points(ax, S, measure, ylabel, ref=None):
    present = [m for m in B.MODEL_ORDER if measure in S and S[(S.model == m)][measure].notna().any()]
    xs = {m: i for i, m in enumerate(present)}
    S = S[S.model.isin(present)]
    off = {("proteus", "self"): -0.22, ("proteus", "other"): -0.08, ("random", "self"): 0.08, ("random", "other"): 0.22}
    for (g, b), dx in off.items():
        sub = S[(S.actual_generator == g) & (S.believed_generator == b)]
        if measure not in sub:
            continue
        col = SELF_C if b == "self" else OTHER_C
        ax.scatter([xs[m] + dx for m in sub.model], sub[measure], s=70, marker="o" if g == "proteus" else "s",
                   facecolor=col if g == "proteus" else "white", edgecolor=col, linewidth=2, zorder=3,
                   label=f"{'Proteus' if g == 'proteus' else 'IID coin'}, believed {b}")
    if ref is not None:
        ax.axhline(ref, color=MUTED, linewidth=1, linestyle="--", zorder=1)
    ax.set_xticks(range(len(present)), [m.capitalize() for m in present])
    ax.set_xlim(-0.5, len(present) - 0.5)
    ax.set_ylabel(ylabel, color=INK)
    _style(ax)


def figures(S, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold"})

    fig, ax = plt.subplots(figsize=(7, 4))
    _points(ax, S, "accuracy", "Forecast accuracy", ref=0.5)
    ax.set_title("Figure 1. Forecast accuracy by model and condition", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=8, loc="best")
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig1_accuracy.png"), dpi=200); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    _points(axs[0], S, "abs_bias", "|P(TRIANGLE) - 0.5|", ref=0)
    axs[0].set_title("A. Marginal bias", loc="left", color=INK)
    _points(axs[1], S, "runs_z", "Runs z (+ = over-alternation)", ref=0)
    axs[1].set_title("B. Wald-Wolfowitz runs z", loc="left", color=INK)
    axs[1].legend(frameon=False, fontsize=8, loc="best")
    fig.suptitle("Figure 2. Marginal bias and sequential structure", x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig2_bias_runs.png"), dpi=200); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    _points(axs[0], S, "coef_opp1", "Coefficient (logit, +/-1 coding)", ref=0)
    axs[0].set_title("A. Previous circle location (lag 1)", loc="left", color=INK)
    _points(axs[1], S, "coef_opp2", "", ref=0)
    axs[1].set_title("B. Circle location two trials back (lag 2)", loc="left", color=INK)
    axs[1].legend(frameon=False, fontsize=8, loc="best")
    fig.suptitle("Figure 3. Brown-Rosenthal weight on the presumed generator's previous locations "
                 "(+ = forecast repeats it)", x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig3_br_circle_coefficients.png"), dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    P = S[(S.actual_generator == "proteus") & S.get("accuracy", pd.Series(dtype=float)).notna()]
    markers = {"fable": "o", "astra": "^", "qwen": "D"}
    for _, r in P.iterrows():
        col = SELF_C if r.believed_generator == "self" else OTHER_C
        ax.scatter(r.proteus_activation, r.accuracy, s=80, marker=markers[r.model], color=col, edgecolor="white", linewidth=1.5, zorder=3)
        ax.annotate(f"{r.model.capitalize()} ({r.believed_generator})", (r.proteus_activation, r.accuracy),
                    textcoords="offset points", xytext=(6, 4), fontsize=8, color=INK)
    ax.axhline(0.5, color=MUTED, linewidth=1, linestyle="--")
    ax.set_xlabel("Proteus channel activation (share of trials)", color=INK)
    ax.set_ylabel("Forecast accuracy against Proteus", color=INK)
    ax.set_title("Figure 4. Exploitation vs accuracy, Proteus sessions", loc="left", color=INK)
    _style(ax)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="o", color=SELF_C, linestyle="", label="believed self"),
                       Line2D([], [], marker="o", color=OTHER_C, linestyle="", label="believed other")], frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig4_activation_vs_accuracy.png"), dpi=200); plt.close(fig)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _f(x, nd=3, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def report(S, C, df, data_dir, out):
    cost = S["cost_usd"].sum() if "cost_usd" in S else 0.0
    pre = os.path.join(data_dir, "preflight_calls.jsonl")
    pre_cost = sum(json.loads(l)["cost_usd"] for l in open(pre)) if os.path.exists(pre) else 0.0
    att = [json.loads(l) for p in glob.glob(os.path.join(data_dir, "*", "*", "attempts.jsonl")) if "_validation" not in os.path.relpath(p, data_dir) for l in open(p)]
    att_cost = sum(a["cost_usd"] for a in att)
    failed = [a for a in att if not a["accepted"]]
    L = ["# PACA believed-self generator pilot: report", "",
         f"Experiment `{B.EXPERIMENT_TAG}`. Generated by `task/analyze_believed_self.py`. One 200-trial session per "
         "(model x actual generator x believed generator); all comparisons are descriptive.", "",
         "## Design and execution", "",
         "- Baseline PACA minimalist forecasting task: the model chooses where the blue circle will land (TRIANGLE/STAR); it "
         "sees the last 5 trials in words and a 25-trial grid of its forecasts and the circle's locations. The only "
         "manipulation is one sentence prepended to the system prompt: *\"Another instance of your model is generating the "
         "sequence of blue circle landings.\"* vs *\"An instance of a different language model is generating "
         "the sequence of blue circle landings.\"*",
         "- Actual generator, hidden in both conditions: Proteus (PACA's nine-channel opponent, full-session history, "
         "commits before the model's forecast) or an IID fair coin. Believed-self and believed-other sessions of the same "
         "model and generator share an opponent seed, so the IID coin sequences are identical across the belief contrast.",
         f"- Charged cost: ${att_cost:.2f} for session calls (incl. {len(failed)} re-requested attempts) + ${pre_cost:.2f} preflight.", "",
         "| session | status | trials | accuracy | P(T) | switch | runs z | copy last circle | Proteus activation | mean attempts | exact final line |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in S.iterrows():
        L.append(f"| {r.session_id} | {r.status} | {r.n_trials} | {_f(r.get('accuracy'))} | {_f(r.get('p_triangle'))} | "
                 f"{_f(r.get('switch_rate'))} | {_f(r.get('runs_z'), 2, True)} | {_f(r.get('copy_last_circle'))} | "
                 f"{_f(r.get('proteus_activation'))} | {_f(r.get('mean_attempts'), 2)} | {_f(r.get('final_line_exact_rate'))} |")
    L += ["", "## Primary: history dependence (Brown-Rosenthal, per session)", "",
          "Coefficients are logits with +/-1 coding (TRIANGLE = +1): a positive circle coefficient means the forecast tends "
          "to repeat that earlier landing. Block p-values are PACA's nested likelihood-ratio tests. `sep` flags separation "
          "or near-separation (coefficients unreliable). Outcome is a main effect (previous forecast correct = +1). PACA's "
          "own x outcome block is omitted: with +/-1 coding it is identical to the circle lags.", "",
          "| session | own1 | own2 | circle lag1 | circle lag2 | outcome1 | outcome2 | p Own | p Circle | p Outcome (main) | sep |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in S.iterrows():
        if "coef_own1" not in r or pd.isna(r.get("coef_own1")):
            continue
        L.append(f"| {r.session_id} | " + " | ".join(_f(r[f'coef_{k}'], 2, True) for k in COEFS) +
                 f" | {_f(r.br_own_p, 3)} | {_f(r.br_opp_p, 3)} | {_f(r.br_outcome_main_p, 3)} | {'yes' if r.br_separation_flag else ''} |")
    L += ["", "## Believed self minus believed other (descriptive)", "",
          "| model | measure | Proteus: self − other | IID coin: self − other | difference (Proteus − coin) |", "|---|---|---:|---:|---:|"]
    for _, r in C.iterrows():
        if r.measure in ("coef_opp1", "coef_opp2", "copy_last_circle", "runs_z", "abs_bias", "accuracy", "proteus_activation"):
            L.append(f"| {r.model} | {r.measure} | {_f(r.proteus_self_minus_other, 3, True)} | {_f(r.random_self_minus_other, 3, True)} | "
                     f"{_f(r.diff_of_diffs_proteus_minus_random, 3, True)} |")
    L += ["", "## Parsing and completion", ""]
    if all(S[S.model == "qwen"].status == "not_run"):
        L.append("- Qwen: not run by decision (APPROVAL.md, 2026-10-11). At PACA's default reasoning its preflight "
                 "forecasts used 28-31k output tokens (~$0.075, ~10 min) each, making 800 sequential calls infeasible.")
    for _, r in S.iterrows():
        if r.status != "complete" and not (r.model == "qwen" and r.status == "not_run"):
            L.append(f"- {r.session_id}: {r.status}. {r.note}")
    reasons = pd.Series([f"{a['choice_source']}/{a['finish_reason']}" for a in failed]).value_counts().to_dict() if failed else {}
    L += [f"- Failed attempts (re-requested; never coin-substituted): {len(failed)} {reasons}.", "",
          "## Figures", "", "![Figure 1](fig1_accuracy.png)", "", "![Figure 2](fig2_bias_runs.png)", "",
          "![Figure 3](fig3_br_circle_coefficients.png)", "", "![Figure 4](fig4_activation_vs_accuracy.png)", "",
          "## Interpretation limits", "",
          "- One session per cell: a self − other difference confounds the framing with session-to-session variation "
          "(the test-retest work in the SPAR repo found models reproduce only ~80% of their own choices on identical prompts). "
          "Rounds are not independent replications of the framing effect.",
          "- Against the IID coin, accuracy is 0.5 in expectation whatever the policy; behavioural measures can still differ.",
          "- This pilot can show an identity-framing effect on forecasting policy and its consequence against Proteus. It "
          "cannot show accurate self-modelling or privileged self-knowledge.", ""]
    with open(os.path.join(out, "REPORT.md"), "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=B.DATA_DIR)
    a = ap.parse_args()
    analyze(a.data)
