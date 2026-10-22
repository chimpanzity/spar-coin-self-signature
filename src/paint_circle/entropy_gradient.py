"""Entropy-gradient pilot analysis (handoff 2026-10-22).

Fable paints against a scripted noisy double-alternation: latent SSTT/TTSS with
each round flipped with probability epsilon (sequence fixed in advance). For each
session, on rounds 1-100 and the primary window 51-100:

  A_win                      Fable's realized win rate
  oracle_win_realized        latent-phase oracle (knows phase and epsilon, not the
                             flips): fraction of rounds where B equals the latent pattern
  EI_oracle_realized         (A_win - .5) / (oracle_win_realized - .5), NA if oracle <= .55
  A_minus_oracle             A_win - oracle_win_realized
  PI_A, PI_B, shadow_win, exploitation_gap, EI_shadow (NA if shadow_win <= .55),
  shadow activation/channels  existing shadow Proteus, W = 50, unchanged
  pattern_following          P(A choice == latent pattern)
  A_follows_last_circle, A_switch_rate, P(TRIANGLE), runs z, win-stay, lose-shift,
  Brown-Rosenthal own/opponent lag-1 coefficients
  losses by block (1-20, 21-50, 51-100) and by cause:
    flip_induced   A followed the latent pattern but the script flipped that round
    A_deviation    A left the latent pattern on a round the script did not flip
No significance tests: one session per epsilon.

Usage: python -m paint_circle.entropy_gradient <batch_dir>
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np

from paint_circle import analysis, scripted, shadow
from paint_circle.scripted_pilot import session_metrics

WINDOWS = {"full": (1, 100), "late": (51, 100)}
BLOCKS = [(1, 20), (21, 50), (51, 100)]
EI_MIN = 0.55


def h2(e: float) -> float:
    return 0.0 if e in (0.0, 1.0) else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))


def gradient_metrics(paint: str, circle: str, latent: str, window: int = 50) -> dict:
    base = session_metrics(paint, circle, window)
    a_wins_str = shadow.wins_string(paint, circle, matcher=True)
    fa = shadow.forecasts_for(paint, a_wins_str, window)
    out = {}
    for label, (lo, hi) in WINDOWS.items():
        sl = slice(lo - 1, hi)
        P, C, L = paint[sl], circle[sl], latent[sl]
        a_win = float(np.mean([p == c for p, c in zip(P, C)]))
        oracle = float(np.mean([l == c for l, c in zip(L, C)]))
        b = base[label]
        sw = b["shadow_win"]
        losses = [(t, paint[t], circle[t], latent[t]) for t in range(lo - 1, hi) if paint[t] != circle[t]]
        br = analysis.brown_rosenthal(P, C, shadow.wins_string(P, C, matcher=True))
        out[label] = dict(
            A_win=a_win, oracle_win_realized=oracle, A_minus_oracle=a_win - oracle,
            EI_oracle_realized=(a_win - 0.5) / (oracle - 0.5) if oracle > EI_MIN else None,
            PI_A=b["PI_A"], PI_B=b["PI_B"], shadow_win=sw, exploitation_gap=a_win - sw,
            EI_shadow=(a_win - 0.5) / (sw - 0.5) if sw > EI_MIN else None,
            activation_B=b["activation_B"], fired_accuracy_B=b["fired_accuracy_B"], channels_B=b["channels_B"],
            activation_A=float(np.mean([f.active for f in fa[lo - 1:hi]])),
            pattern_following=float(np.mean([p == l for p, l in zip(P, L)])),
            A_follows_last_circle=b["A_follows_last_circle"], A_switch_rate=b["A_switch_rate"],
            A_p_triangle=b["A_p_triangle"], A_runs_z=analysis.runs_z(P),
            A_win_stay=b["A_win_stay"], A_lose_shift=b["A_lose_shift"],
            br_own1=br["br_own1"], br_opp1=br["br_opp1"], br_separated=br["br_separated"],
            losses=len(losses),
            losses_flip_induced=sum(1 for _, p, c, l in losses if p == l and c != l),
            losses_A_deviation=sum(1 for _, p, c, l in losses if p != l and c == l),
        )
    out["losses_by_block"] = {f"{lo}-{hi}": sum(1 for t in range(lo - 1, hi) if paint[t] != circle[t]) for lo, hi in BLOCKS}
    out["deviation_rounds"] = [t + 1 for t in range(len(paint)) if paint[t] != latent[t] and circle[t] == latent[t]]
    out["bins_A_win"] = base["bins_A_win"]
    return out


def main(batch_dir: str):
    plan = json.load(open(os.path.join(batch_dir, "plan.json"), encoding="utf-8"))
    rows, per = [], {}
    for s in plan["sessions"]:
        p = os.path.join(batch_dir, s["session_id"], "rounds.jsonl")
        if not os.path.exists(p):
            continue
        rs = [json.loads(l) for l in open(p, encoding="utf-8")]
        paint = "".join(r["paint"] for r in rs)
        circle = "".join(r["circle"] for r in rs)
        phase, eps, seed = scripted.nda_parse(s["script_B"])
        assert circle == scripted.nda_sequence(phase, eps, seed)[:len(rs)], "B deviated from its frozen script"
        latent = scripted.nda_latent(phase)[:len(rs)]
        rej = os.path.join(batch_dir, s["session_id"], "rejected_attempts.jsonl")
        rej_rows = [json.loads(l) for l in open(rej, encoding="utf-8")] if os.path.exists(rej) else []
        cost = sum(r["round_cost_usd"] for r in rs) + sum(r.get("cost_usd", 0) for r in rej_rows)
        m = gradient_metrics(paint, circle, latent)
        per[s["session_id"]] = dict(epsilon=eps, phase=phase, seed=seed, m=m)
        for label in WINDOWS:
            rows.append(dict(tag="ENTROPY_GRADIENT_PILOT", session_id=s["session_id"], epsilon=eps, H2=round(h2(eps), 3),
                             oracle_expected=1 - eps if eps < 0.5 else 0.5, phase=phase, seed=seed, window=label,
                             rounds=len(rs), parse_or_transport_rejections=len(rej_rows),
                             rate_limit_retries=sum(1 for r in rej_rows if "429" in str(r.get("error", ""))),
                             cost_usd=round(cost, 4),
                             losses_1_20=m["losses_by_block"]["1-20"], losses_21_50=m["losses_by_block"]["21-50"],
                             losses_51_100=m["losses_by_block"]["51-100"],
                             **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m[label].items()}))
    rows.sort(key=lambda r: (r["epsilon"], r["window"]))
    out = os.path.join(batch_dir, "analysis")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "entropy_gradient_sessions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: ("NA" if v is None else json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()})
    with open(os.path.join(out, "entropy_gradient.json"), "w", encoding="utf-8") as f:
        json.dump(dict(tag="ENTROPY_GRADIENT_PILOT", windows=WINDOWS, ei_min=EI_MIN, sessions=rows,
                       deviation_rounds={k: v["m"]["deviation_rounds"] for k, v in per.items()},
                       bins_A_win={k: v["m"]["bins_A_win"] for k, v in per.items()},
                       total_cost_usd=round(sum(r["cost_usd"] for r in rows if r["window"] == "full"), 4)), f, indent=2)
    _plot(rows, out)
    for r in rows:
        if r["window"] == "late":
            print({k: r[k] for k in ("epsilon", "A_win", "oracle_win_realized", "A_minus_oracle", "pattern_following",
                                     "PI_A", "PI_B", "shadow_win", "losses", "losses_flip_induced", "losses_A_deviation")})


def _plot(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
    for ax, win in zip(axes, ("full", "late")):
        rs = sorted([r for r in rows if r["window"] == win], key=lambda r: r["epsilon"])
        e = [r["epsilon"] for r in rs]
        ax.plot(e, [r["A_win"] for r in rs], "o-", color="#d1495b", label="Fable win (A_win)")
        ax.plot(e, [r["oracle_win_realized"] for r in rs], "s--", color="#333333", label="latent-phase oracle (realized)")
        ax.plot(e, [r["shadow_win"] for r in rs], "^:", color="#00798c", label="shadow benchmark (shadow_win)")
        ax.plot(e, [r["pattern_following"] for r in rs], "d-", color="#edae49", label="Fable follows latent pattern")
        ax.plot(e, [r["PI_A"] for r in rs], "v-", color="#8d6a9f", label="PI_A (Fable's own predictability)")
        ax.plot(e, [r["PI_B"] for r in rs], "x-", color="#66a182", label="PI_B (script's predictability to shadow)")
        ax.axhline(0.5, color="grey", lw=0.6, ls=":")
        ax.set_title(f"rounds {'1-100' if win == 'full' else '51-100'}")
        ax.set_xlabel("noise epsilon (one session per level)")
        ax.set_ylim(-0.05, 1.05)
    axes[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("ENTROPY_GRADIENT_PILOT: Fable vs noisy double-alternation")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "entropy_gradient.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
