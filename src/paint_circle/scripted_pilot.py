"""SCRIPTED_OPPONENT_PILOT: analysis (handoff 2026-10-21, "can Fable exploit obvious
sequential patterns?").

Per session (A = Fable painter, B = scripted circle), on the full game and on the
primary late window (rounds 51-100):
  A_win, A_advantage = A_win - .5
  PI_B    shadow Proteus (W=50, standard 9 channels, B's choices and B's outcomes)
          predicting B; 2 * (mean forecast prob of B's actual move - .5)
  shadow_win  the same shadow used as the painter: mean prob it matches B (equals
          the PI_B forecast accuracy by construction; replay benchmark)
  shadow_advantage, exploitation_gap = A_win - shadow_win
  EI_A    (A_win - .5) / (shadow_win - .5), NA when shadow_win <= .55
  PI_A    the same shadow predicting A's own choices
  oracle  ideal periodic oracle (period/phase from the prior 4 B moves): its win
          rate, and how often A's choice agreed with it
  activation, active-channel distribution, raw accuracy of B forecasts on fired rounds
  10-round bins of A_win
No p-values: the sequences are deterministic and rounds are autocorrelated.

Usage: python -m paint_circle.scripted_pilot <batch_dir>
"""

from __future__ import annotations

import collections
import csv
import json
import os
import sys

import numpy as np

from paint_circle import scripted, shadow

LATE = (51, 100)          # 1-based inclusive primary window
EI_MIN_SHADOW_WIN = 0.55


def _window(xs, lo, hi):
    return xs[lo - 1:hi]


def session_metrics(paint: str, circle: str, window: int) -> dict:
    n = len(paint)
    a_wins = [p == c for p, c in zip(paint, circle)]
    b_wins_str = shadow.wins_string(circle, paint, matcher=False)
    a_wins_str = shadow.wins_string(paint, circle, matcher=True)
    fb = shadow.forecasts_for(circle, b_wins_str, window)        # forecasts of B, round t uses rounds < t
    fa = shadow.forecasts_for(paint, a_wins_str, window)
    pb = [f.p_triangle if circle[t] == "T" else 1 - f.p_triangle for t, f in enumerate(fb)]
    pa = [f.p_triangle if paint[t] == "T" else 1 - f.p_triangle for t, f in enumerate(fa)]
    oracle = [scripted.oracle_prediction(circle[:t]) for t in range(n)]
    out = {}
    for label, (lo, hi) in (("full", (1, n)), ("late", LATE)):
        if hi > n:
            continue
        aw = np.mean(_window(a_wins, lo, hi))
        sw = float(np.mean(_window(pb, lo, hi)))
        fired = [(f, circle[t]) for t, f in enumerate(fb) if lo - 1 <= t < hi and f.active]
        orc = [(o, circle[t], paint[t]) for t, o in enumerate(oracle) if lo - 1 <= t < hi]
        out[label] = dict(
            A_win=float(aw), A_advantage=float(aw - 0.5),
            PI_B=2 * (sw - 0.5), shadow_win=sw, shadow_advantage=sw - 0.5,
            exploitation_gap=float(aw - sw),
            EI_A=float((aw - 0.5) / (sw - 0.5)) if sw > EI_MIN_SHADOW_WIN else None,
            PI_A=2 * (float(np.mean(_window(pa, lo, hi))) - 0.5),
            activation_B=len(fired) / (hi - lo + 1),
            fired_accuracy_B=float(np.mean([(f.p_triangle > 0.5) == (b == "T") for f, b in fired])) if fired else None,
            channels_B=dict(collections.Counter(int(f.channel) for f, _ in fired)),
            oracle_win=float(np.mean([1.0 if o == b else 0.5 if o is None else 0.0 for o, b, _ in orc])),
            A_agrees_with_oracle=float(np.mean([o == a for o, _, a in orc if o is not None])) if any(o for o, _, _ in orc) else None,
            A_switch_rate=float(np.mean([paint[t] != paint[t - 1] for t in range(max(lo - 1, 1), hi)])),
        )
    out["bins_A_win"] = [float(np.mean(a_wins[i:i + 10])) for i in range(0, n, 10)]
    out["onset"] = learning_onset(a_wins)
    return out


def learning_onset(a_wins, run: int = 10):
    """Learning-onset measures (added 2026-10-21 for the identity-framing pilot).

    first_run10       first round of the first run of `run` consecutive wins
    last_loss         last round A lost (0 if never)
    sustained_from    round after the last loss (A wins every round from here on), or None if
                      A lost the final round
    """
    first = next((t + 1 for t in range(len(a_wins) - run + 1) if all(a_wins[t:t + run])), None)
    losses = [t + 1 for t, w in enumerate(a_wins) if not w]
    last = losses[-1] if losses else 0
    return dict(first_run10=first, last_loss=last,
                sustained_from=(last + 1) if last < len(a_wins) else None, n_losses=len(losses))


def main(batch_dir: str):
    plan = json.load(open(os.path.join(batch_dir, "plan.json"), encoding="utf-8"))
    rows, bins, cost = [], {}, {}
    for s in plan["sessions"]:
        p = os.path.join(batch_dir, s["session_id"], "rounds.jsonl")
        if not os.path.exists(p):
            continue
        rs = [json.loads(l) for l in open(p, encoding="utf-8")]
        paint = "".join(r["paint"] for r in rs)
        circle = "".join(r["circle"] for r in rs)
        assert circle == "".join(scripted.move(s["script_B"], t) for t in range(1, len(rs) + 1)), "B deviated from script"
        rej = os.path.join(batch_dir, s["session_id"], "rejected_attempts.jsonl")
        n_rej = sum(1 for _ in open(rej, encoding="utf-8")) if os.path.exists(rej) else 0
        rej_cost = sum(json.loads(l).get("cost_usd", 0) for l in open(rej, encoding="utf-8")) if n_rej else 0.0
        m = session_metrics(paint, circle, s["window"])
        bins[s["session_id"]] = m["bins_A_win"]
        cost[s["session_id"]] = sum(r["round_cost_usd"] for r in rs) + rej_cost
        for label in ("full", "late"):
            if label in m:
                rows.append(dict(tag=plan.get("tag", "SCRIPTED_OPPONENT_PILOT"), session_id=s["session_id"], script=s["script_B"],
                                 A_told=s["disclosure_A"] or "nothing",
                                 **{f"onset_{k}": v for k, v in m["onset"].items()},
                                 sequence=s["script_B"].split("_")[0], phase=s["script_B"].split("_")[1],
                                 window=label, rounds=len(rs), parse_rejections=n_rej, cost_usd=round(cost[s["session_id"]], 4),
                                 **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m[label].items()}))
    out_dir = os.path.join(batch_dir, "analysis")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "scripted_pilot_sessions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: ("NA" if v is None else json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()})
    with open(os.path.join(out_dir, "scripted_pilot.json"), "w", encoding="utf-8") as f:
        json.dump(dict(tag="SCRIPTED_OPPONENT_PILOT", late_window=LATE, ei_min_shadow_win=EI_MIN_SHADOW_WIN,
                       sessions=rows, bins_A_win=bins, total_cost_usd=round(sum(cost.values()), 4)), f, indent=2)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    styles = {"ALT_S": ("#d1495b", "-"), "ALT_T": ("#d1495b", "--"), "DOUBLE_S": ("#00798c", "-"), "DOUBLE_T": ("#00798c", "--")}
    for k, v in bins.items():
        scripts = [x.split("__")[-1] for x in bins]
        c, ls = styles[k.split("__")[-1]] if len(set(scripts)) == len(scripts) else (None, "-")
        label = k if len(set(scripts)) == len(scripts) else k.split("__")[1] if k.count("__") >= 2 else k
        ax.plot(np.arange(len(v)) * 10 + 5, v, ls, color=c, marker="o", label=label)
    ax.axhline(0.5, color="grey", lw=0.8, ls=":")
    ax.axvline(50.5, color="grey", lw=0.8)
    ax.set_xlabel("round (10-round bins)"); ax.set_ylabel("Fable (paint) win rate"); ax.set_ylim(0, 1.05)
    ax.set_title("SCRIPTED_OPPONENT_PILOT: Fable vs scripted circle")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "win_rate_bins.png"), dpi=150)
    print(json.dumps([{k: r[k] for k in ("script", "A_told", "onset_last_loss", "onset_n_losses", "window", "A_win", "PI_A", "PI_B", "shadow_win", "EI_A",
                                          "exploitation_gap", "oracle_win", "A_agrees_with_oracle", "activation_B")}
                      for r in rows], indent=1))
    print("total cost", round(sum(cost.values()), 4))


if __name__ == "__main__":
    main(sys.argv[1])
