"""Analysis of paint-and-circle sessions (handoff §7-§8).

Per session and seat (A = paint/matcher, B = circle/mismatcher):
  win, EI          realized win rate and EI = 2(win - .5)
  pi, act          own predictability: shadow Proteus (W = session window) on
                   the seat's own choices/outcomes; PI = 2(p_shadow - .5)
  bench            information-matched shadow benchmark: mean probability that
                   a Proteus recommendation from the opponent's history beats
                   the opponent's recorded choice (offline replay, not a
                   counterfactual game)
  p_T, alt, runs_z, win_stay, lose_shift
  br_*             Brown-Rosenthal logistic regression of the current choice
                   (T=1) on own lag 1-2, opponent lag 1-2, own-outcome lag 1-2
                   (all +/-1); likelihood-ratio tests for removing each block;
                   own and opponent lag-1 coefficients; the opponent's current
                   choice is a post-hoc diagnostic block.

Cell summaries average sessions; contrasts against the matching baseline
cell (same models, no disclosure) use Welch t on session-level values.

Usage: python -m paint_circle.analysis <batch_dir> [<batch_dir> ...] --out <dir>
"""

from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import math
import os
from typing import Dict, List, Optional

import numpy as np

from paint_circle import shadow

# ------------------------------------------------------------------ io --


def load_sessions(batch_dirs: List[str], min_rounds: Optional[int] = None) -> List[Dict]:
    """Complete sessions only by default; with min_rounds, also partial
    sessions that reached at least that many rounds (sensitivity analysis)."""
    out = []
    for b in batch_dirs:
        plan = json.load(open(os.path.join(b, "plan.json"), encoding="utf-8"))
        for s in plan["sessions"]:
            p = os.path.join(b, s["session_id"], "rounds.jsonl")
            if not os.path.exists(p):
                continue
            rs = [json.loads(l) for l in open(p, encoding="utf-8")]
            if len(rs) < (min_rounds if min_rounds is not None else s["rounds"]):
                continue
            out.append(dict(s, batch=os.path.basename(os.path.normpath(b)),
                            paint="".join(r["paint"] for r in rs),
                            circle="".join(r["circle"] for r in rs),
                            cost=sum(r["round_cost_usd"] for r in rs),
                            texts_A=[r["response_A"]["text"] for r in rs],
                            texts_B=[r["response_B"]["text"] for r in rs]))
    return out

# ------------------------------------------------------------ measures --


def runs_z(x: str) -> float:
    n1, n2 = x.count("T"), x.count("S")
    n = n1 + n2
    if n1 == 0 or n2 == 0:
        return float("nan")
    runs = 1 + sum(x[i] != x[i - 1] for i in range(1, n))
    mu = 2 * n1 * n2 / n + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n * n * (n - 1))
    return (runs - mu) / math.sqrt(var)


def _logit_fit(X: np.ndarray, y: np.ndarray, lam: float = 1e-4, iters: int = 100):
    """Ridge-penalised IRLS (penalty excludes intercept). Returns beta, loglik, separated flag."""
    beta = np.zeros(X.shape[1])
    P = lam * np.eye(X.shape[1])
    P[0, 0] = 0
    for _ in range(iters):
        eta = np.clip(X @ beta, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        W = p * (1 - p) + 1e-9
        g = X.T @ (y - p) - P @ beta
        H = X.T @ (X * W[:, None]) + P
        step = np.linalg.solve(H, g)
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    eta = np.clip(X @ beta, -30, 30)
    p = np.clip(1 / (1 + np.exp(-eta)), 1e-12, 1 - 1e-12)
    ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return beta, ll, bool(np.max(np.abs(beta)) > 15)


def _chi2_sf(x: float, df: int) -> float:
    # survival function for small integer df via the regularized gamma series
    if x <= 0:
        return 1.0
    a, z = df / 2.0, x / 2.0
    s, term, k = 0.0, 1.0 / a, 0
    while term > 1e-12 and k < 1000:
        s += term
        k += 1
        term *= z / (a + k)
    lower = math.exp(-z + a * math.log(z) - math.lgamma(a)) * s
    return max(0.0, 1.0 - lower)


def brown_rosenthal(own: str, opp: str, wins: str) -> Dict[str, float]:
    pm = lambda c: 1.0 if c in ("T", "1") else -1.0
    rows, y = [], []
    for t in range(2, len(own)):
        rows.append(dict(own1=pm(own[t - 1]), own2=pm(own[t - 2]), opp1=pm(opp[t - 1]), opp2=pm(opp[t - 2]),
                         out1=pm(wins[t - 1]), out2=pm(wins[t - 2]), oppcur=pm(opp[t])))
        y.append(1.0 if own[t] == "T" else 0.0)
    y = np.array(y)
    blocks = {"own": ["own1", "own2"], "opp": ["opp1", "opp2"], "out": ["out1", "out2"], "cur": ["oppcur"]}
    names = sum(blocks.values(), [])

    def design(cols):
        return np.column_stack([np.ones(len(rows))] + [[r[c] for r in rows] for c in cols])

    beta, ll_full, sep = _logit_fit(design(names), y)
    res = dict(br_own1=float(beta[1 + names.index("own1")]), br_opp1=float(beta[1 + names.index("opp1")]),
               br_separated=sep)
    for b, cols in blocks.items():
        _, ll_red, _ = _logit_fit(design([c for c in names if c not in cols]), y)
        res[f"br_p_{b}"] = _chi2_sf(2 * (ll_full - ll_red), len(cols))
    return res


# Exploitation efficiency is reported only when the opponent was exploitable
# enough for the ratio to be stable (fixed 2026-10-21, before the Fable
# specificity batch was analysed).
EFFICIENCY_MIN_BENCH = 0.55


def exploitation(own: str, opp: str, matcher: bool, window: int) -> Dict[str, float]:
    """Three exploitation indices for the focal seat.

    ei          2 * (win - .5): realized advantage
    eff         (win - .5) / (bench - .5): realized advantage as a share of what
                an information-matched shadow Proteus could have taken from the
                same opponent history; NaN when bench < EFFICIENCY_MIN_BENCH
    cond        win rate on rounds where the shadow detected a bias in the
                opponent minus win rate on rounds where it did not: does the
                player gain specifically when there is something to exploit?
    opp_active  fraction of rounds with a detectable opponent bias
    """
    wins = shadow.wins_string(own, opp, matcher)
    opp_wins = shadow.wins_string(opp, own, not matcher)
    fc = shadow.forecasts_for(opp, opp_wins, window)
    bench = float(np.mean([f.p_triangle if opp[t] == "T" else 1 - f.p_triangle for t, f in enumerate(fc)]))
    win = wins.count("1") / len(wins)
    act = [wins[t] == "1" for t, f in enumerate(fc) if f.active]
    inact = [wins[t] == "1" for t, f in enumerate(fc) if not f.active]
    cond = (float(np.mean(act)) - float(np.mean(inact))) if len(act) >= 10 and len(inact) >= 10 else float("nan")
    return dict(ei=2 * (win - 0.5),
                eff=(win - 0.5) / (bench - 0.5) if bench >= EFFICIENCY_MIN_BENCH else float("nan"),
                cond=cond, opp_active=len(act) / len(fc), bench=bench)


def seat_measures(own: str, opp: str, matcher: bool, window: int) -> Dict[str, float]:
    wins = shadow.wins_string(own, opp, matcher)
    pr = shadow.predictability(own, wins, window)
    ex = exploitation(own, opp, matcher, window)
    stays_after_win = [own[t] == own[t - 1] for t in range(1, len(own)) if wins[t - 1] == "1"]
    shifts_after_loss = [own[t] != own[t - 1] for t in range(1, len(own)) if wins[t - 1] == "0"]
    win = wins.count("1") / len(wins)
    m = dict(win=win, pi=pr.pi, p_shadow=pr.p_shadow, act=pr.activation, **ex,
             p_T=own.count("T") / len(own),
             alt=sum(own[t] != own[t - 1] for t in range(1, len(own))) / (len(own) - 1),
             runs_z=runs_z(own),
             win_stay=float(np.mean(stays_after_win)) if stays_after_win else float("nan"),
             lose_shift=float(np.mean(shifts_after_loss)) if shifts_after_loss else float("nan"))
    m.update(brown_rosenthal(own, opp, wins))
    return m


SELF_TERMS = ("myself", "same model", "same language model", "instance of", "copy of", "itself", "my own")


def self_reference_rate(texts: List[str]) -> float:
    return float(np.mean([any(t in (x or "").lower() for t in SELF_TERMS) for x in texts]))


def session_rows(s: Dict) -> List[Dict]:
    out = []
    for seat, own, opp, matcher, model, disc, texts in (
            ("A", s["paint"], s["circle"], True, s["model_A"], s["disclosure_A"], s["texts_A"]),
            ("B", s["circle"], s["paint"], False, s["model_B"], s["disclosure_B"], s["texts_B"])):
        out.append(dict(batch=s["batch"], session_id=s["session_id"], seat=seat, model=model,
                        opponent=s["model_B"] if seat == "A" else s["model_A"],
                        disclosure=disc or "none",
                        opp_disclosure=(s["disclosure_B"] if seat == "A" else s["disclosure_A"]) or "none",
                        cell=f"{s['model_A']}-{s['model_B']}|A-{s['disclosure_A'] or 'none'}|B-{s['disclosure_B'] or 'none'}",
                        rounds=len(s["paint"]), cost=s["cost"] / 2, self_ref=self_reference_rate(texts),
                        **seat_measures(own, opp, matcher, s["window"])))
    return out

# ------------------------------------------------------------ summaries --


METRICS = ["win", "ei", "eff", "cond", "opp_active", "pi", "act", "bench", "p_T", "alt", "runs_z", "win_stay", "lose_shift",
           "br_own1", "br_opp1", "br_p_own", "br_p_opp", "br_p_out", "self_ref"]


def welch(a: List[float], b: List[float]):
    a, b = np.array(a, float), np.array(b, float)
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = math.sqrt(va + vb)
    if se == 0:
        return float(a.mean() - b.mean()), float("nan")
    t = (a.mean() - b.mean()) / se
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    # two-sided p from t via normal approx corrected for df (Hill's approx is overkill here)
    p = 2 * _t_sf(abs(t), df)
    return float(a.mean() - b.mean()), p


def _t_sf(t: float, df: float) -> float:
    x = df / (df + t * t)
    return 0.5 * _betainc(df / 2, 0.5, x)


def _betainc(a, b, x, iters=200):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b + lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(iters):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1 + num * d
        d = 1 / d if abs(d) > 1e-30 else 1e30
        c = 1 + num / c if abs(c) > 1e-30 else 1e30
        f *= c * d
        if abs(c * d - 1) < 1e-10:
            break
    return front * (f - 1)


def summarize(rows: List[Dict]) -> List[Dict]:
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["cell"], r["seat"])].append(r)
    out = []
    for (cell, seat), rs in sorted(groups.items()):
        rec = dict(cell=cell, seat=seat, model=rs[0]["model"], opponent=rs[0]["opponent"],
                   disclosure=rs[0]["disclosure"], opp_disclosure=rs[0]["opp_disclosure"], n=len(rs))
        for m in METRICS:
            v = np.array([r[m] for r in rs], float)
            rec[m] = float(np.nanmean(v))
            rec[f"{m}_se"] = float(np.nanstd(v, ddof=1) / math.sqrt(np.sum(~np.isnan(v)))) if len(v) > 1 else float("nan")
        rec["br_opp_sig_frac"] = float(np.mean([r["br_p_opp"] < 0.05 for r in rs]))
        rec["br_own_sig_frac"] = float(np.mean([r["br_p_own"] < 0.05 for r in rs]))
        out.append(rec)
    return out


def contrasts(rows: List[Dict]) -> List[Dict]:
    """Each non-baseline cell vs the no-disclosure cell with the same model pairing, per seat."""
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["cell"], r["seat"])].append(r)
    out = []
    for (cell, seat), rs in sorted(by.items()):
        pairing = cell.split("|")[0]
        base = f"{pairing}|A-none|B-none"
        if cell == base or (base, seat) not in by:
            continue
        b = by[(base, seat)]
        rec = dict(cell=cell, seat=seat, baseline=base, n=len(rs), n_base=len(b))
        for m in ("win", "pi", "eff", "cond", "bench", "alt", "p_T", "br_own1", "br_opp1", "self_ref"):
            d, p = welch([r[m] for r in rs], [r[m] for r in b])
            rec[f"d_{m}"], rec[f"p_{m}"] = d, p
        out.append(rec)
    return out


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def plot(summary: List[Dict], out_dir: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharex=True, sharey=True)
    colors = {"none": "#555555", "self": "#d1495b", "other": "#00798c", "agent": "#edae49",
              "salmon": "#8d6a9f", "program": "#66a182"}
    markers = {"astra": "o", "fable": "s", "qwen": "^"}
    for ax, seat in zip(axes, "AB"):
        for r in summary:
            if r["seat"] != seat:
                continue
            ax.errorbar(r["pi"], r["win"], xerr=r["pi_se"], yerr=r["win_se"], fmt=markers[r["model"]],
                        color=colors.get(r["disclosure"], "k"), ms=7, capsize=2, alpha=0.85)
        ax.axhline(0.5, ls="--", c="grey", lw=0.8)
        ax.axvline(0.0, ls="--", c="grey", lw=0.8)
        ax.set_title(f"Seat {seat} ({'paint / matcher' if seat == 'A' else 'circle / mismatcher'})")
        ax.set_xlabel("own predictability PI (shadow Proteus, W=50)")
    axes[0].set_ylabel("realized win rate")
    handles = [plt.Line2D([], [], color=c, marker="o", ls="", label=f"told: {d}") for d, c in colors.items()]
    handles += [plt.Line2D([], [], color="k", marker=m, ls="", label=n) for n, m in markers.items()]
    axes[1].legend(handles=handles, fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "pi_vs_win.png"), dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dirs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-rounds", type=int, default=None,
                    help="also include partial sessions with at least this many rounds")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sessions = load_sessions(a.batch_dirs, a.min_rounds)
    rows = [r for s in sessions for r in session_rows(s)]
    summary = summarize(rows)
    con = contrasts(rows)
    write_csv(os.path.join(a.out, "seat_sessions.csv"), rows)
    write_csv(os.path.join(a.out, "cell_summary.csv"), summary)
    write_csv(os.path.join(a.out, "contrasts_vs_baseline.csv"), con)
    plot(summary, a.out)
    with open(os.path.join(a.out, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(dict(n_sessions=len(sessions), summary=summary, contrasts=con), f, indent=2)
    print(f"{len(sessions)} complete sessions; wrote {a.out}")


if __name__ == "__main__":
    main()
