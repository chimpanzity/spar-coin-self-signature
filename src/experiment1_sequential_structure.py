"""Sequential-structure measures for Study 1 Experiment 1 by disclosure group (post hoc, offline, 2026-10-11).

Tests the original hypothesis in its own terms: does being told the opponent is another instance of oneself change
(a) marginal choice frequencies, (b) run structure, (c) Brown-Rosenthal-style sequential dependence of the current
choice on lagged own choice, lagged opponent choice and lagged outcome, and (d) win rate?

Groups (player-game level, from experiment1_post_hoc_strategy): uninformed_self, uninformed_other, told_self,
told_other. Contrasts are matched on opponent type; the self-specific effect is the interaction.

Per player-game: marginal entropy (bits, all 20 rounds), switch rate, generalised Wald-Wolfowitz runs z (positive =
more runs than expected from the marginals, i.e. over-alternation), payoff. Pooled per group (rounds 2-20): G-tests
and Cramer's V for current choice x own previous choice, x opponent previous choice, x previous outcome, and the joint
lag-1 table (own x opponent previous). Uncertainty: percentile bootstrap over player-games (seed 20261011, 3000).
"""
from __future__ import annotations

import csv
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment1_post_hoc_strategy as X  # noqa: E402
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

OUT = repo_paths.legacy("post_hoc/experiment1_sequential_structure")
SEED = 20261011
N_BOOT = 3000
GROUPS = ("uninformed_self", "uninformed_other", "told_self", "told_other")


def entropy_bits(seq, moves):
    n = len(seq)
    return -sum((c / n) * math.log2(c / n) for c in Counter(seq).values() if c)


def runs_z(seq):
    n = len(seq)
    counts = Counter(seq).values()
    s2 = sum(c * c for c in counts); s3 = sum(c ** 3 for c in counts)
    R = 1 + sum(a != b for a, b in zip(seq, seq[1:]))
    ER = (n * (n + 1) - s2) / n
    VR = (s2 * (s2 + n * (n + 1)) - 2 * n * s3 - n ** 3) / (n * n * (n - 1))
    return (R - ER) / math.sqrt(VR) if VR > 0 else 0.0


def g_test(table):
    """table: dict[(row, col)] -> count. Returns G, df, Cramer's V, n."""
    rows = sorted({r for r, _ in table}); cols = sorted({c for _, c in table})
    n = sum(table.values())
    rs = {r: sum(v for (rr, _), v in table.items() if rr == r) for r in rows}
    cs = {c: sum(v for (_, cc), v in table.items() if cc == c) for c in cols}
    G = 0.0; chi = 0.0
    for r in rows:
        for c in cols:
            o = table.get((r, c), 0); e = rs[r] * cs[c] / n
            if o > 0:
                G += 2 * o * math.log(o / e)
            chi += (o - e) ** 2 / e if e > 0 else 0
    df = (len(rows) - 1) * (len(cols) - 1)
    V = math.sqrt(chi / (n * (min(len(rows), len(cols)) - 1))) if n > 0 and min(len(rows), len(cols)) > 1 else 0.0
    return G, df, V, n


def chi2_sf(x, k):
    """Survival function of chi-square with k df (Wilson-Hilferty approximation; fine for k >= 2)."""
    if x <= 0:
        return 1.0
    z = ((x / k) ** (1 / 3) - (1 - 2 / (9 * k))) / math.sqrt(2 / (9 * k))
    return 0.5 * math.erfc(z / math.sqrt(2))


def per_game_measures(pg, gt):
    own = pg["own"]
    return dict(entropy=entropy_bits(own, X.MOVES[gt]), switch=100 * sum(a != b for a, b in zip(own, own[1:])) / 19,
                runs_z=runs_z(own), payoff=pg["payoff"],
                p_first=100 * Counter(own)[X.MOVES[gt][0]] / 20)   # share of ROCK (RPS) / STAR (MP)


def pooled_tables(pgs):
    t_own, t_opp, t_out, t_joint = Counter(), Counter(), Counter(), Counter()
    for pg in pgs:
        own, opp, res = pg["own"], pg["opp"], pg["res"]
        for t in range(1, 20):
            t_own[(own[t], own[t - 1])] += 1
            t_opp[(own[t], opp[t - 1])] += 1
            t_out[(own[t], res[t - 1])] += 1
            t_joint[(own[t], own[t - 1] + "|" + opp[t - 1])] += 1
    return t_own, t_opp, t_out, t_joint


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    rows_pg, rows_grp, rows_con = [], [], []
    for gt in ("rps", "mp"):
        pgs = X.load_player_games(gt)
        for pg in pgs:
            m = per_game_measures(pg, gt)
            rows_pg.append(dict(game_type=gt, game_id=pg["gid"], seat=pg["seat"], model=pg["model"], opp_model=pg["opp_model"],
                                condition=pg["condition"], group=pg["group"], **{k: round(v, 4) for k, v in m.items()}))
        for model in X.MODELS + ("all",):
            sel_all = [p for p in pgs if model == "all" or p["model"] == model]
            for group in GROUPS:
                sel = [p for p in sel_all if p["group"] == group]
                marg = Counter(mv for p in sel for mv in p["own"]); n = sum(marg.values())
                t_own, t_opp, t_out, t_joint = pooled_tables(sel)
                G1, df1, V1, _ = g_test(t_own); G2, df2, V2, _ = g_test(t_opp); G3, df3, V3, _ = g_test(t_out); G4, df4, V4, _ = g_test(t_joint)
                pm = [per_game_measures(p, gt) for p in sel]
                row = dict(game_type=gt, model=model, group=group, n_player_games=len(sel),
                           **{f"marg_{mv}": round(100 * marg[mv] / n, 1) for mv in X.MOVES[gt]},
                           entropy=round(sum(x["entropy"] for x in pm) / len(pm), 3),
                           switch_rate=round(sum(x["switch"] for x in pm) / len(pm), 1),
                           runs_z=round(sum(x["runs_z"] for x in pm) / len(pm), 3),
                           payoff=round(sum(x["payoff"] for x in pm) / len(pm), 3),
                           V_own_lag1=round(V1, 3), p_own_lag1=round(chi2_sf(G1, df1), 4),
                           V_opp_lag1=round(V2, 3), p_opp_lag1=round(chi2_sf(G2, df2), 4),
                           V_outcome_lag1=round(V3, 3), p_outcome_lag1=round(chi2_sf(G3, df3), 4),
                           V_joint_lag1=round(V4, 3), p_joint_lag1=round(chi2_sf(G4, df4), 4))
                rows_grp.append(row)
            # matched contrasts with bootstrap over player-games
            def stats_of(sample):
                pm = [per_game_measures(p, gt) for p in sample]
                t_own, t_opp, t_out, t_joint = pooled_tables(sample)
                return dict(entropy=sum(x["entropy"] for x in pm) / len(pm), switch_rate=sum(x["switch"] for x in pm) / len(pm),
                            runs_z=sum(x["runs_z"] for x in pm) / len(pm), payoff=sum(x["payoff"] for x in pm) / len(pm),
                            V_own_lag1=g_test(t_own)[2], V_opp_lag1=g_test(t_opp)[2], V_outcome_lag1=g_test(t_out)[2], V_joint_lag1=g_test(t_joint)[2])
            groups = {g: [p for p in sel_all if p["group"] == g] for g in GROUPS}
            est = {g: stats_of(groups[g]) for g in GROUPS}
            boots = {g: [] for g in GROUPS}
            for _ in range(N_BOOT):
                for g in GROUPS:
                    boots[g].append(stats_of([rng.choice(groups[g]) for _ in groups[g]]))
            for metric in est["told_self"]:
                d_self = [a[metric] - b[metric] for a, b in zip(boots["told_self"], boots["uninformed_self"])]
                d_other = [a[metric] - b[metric] for a, b in zip(boots["told_other"], boots["uninformed_other"])]
                inter = [a - b for a, b in zip(d_self, d_other)]
                for name, e, dist in (("told_self - uninformed_self", est["told_self"][metric] - est["uninformed_self"][metric], d_self),
                                      ("told_other - uninformed_other", est["told_other"][metric] - est["uninformed_other"][metric], d_other),
                                      ("self-specific (interaction)", (est["told_self"][metric] - est["uninformed_self"][metric]) - (est["told_other"][metric] - est["uninformed_other"][metric]), inter)):
                    dist = sorted(dist)
                    rows_con.append(dict(game_type=gt, model=model, metric=metric, contrast=name, estimate=round(e, 3),
                                         lo=round(dist[int(0.025 * N_BOOT)], 3), hi=round(dist[int(0.975 * N_BOOT) - 1], 3)))
    for name, rows in (("player_games.csv", rows_pg), ("group_summary.csv", rows_grp), ("contrasts.csv", rows_con)):
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
        with open(OUT / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    # console summary
    for gt in ("rps", "mp"):
        print(f"\n=== {gt.upper()} group summary (all models pooled) ===")
        for r in rows_grp:
            if r["game_type"] == gt and r["model"] == "all":
                margs = " ".join(f"{k[5:]} {v}" for k, v in r.items() if k.startswith("marg_"))
                print(f"  {r['group']:17s} n={r['n_player_games']:2d} | marg {margs} | H {r['entropy']:.3f} | switch {r['switch_rate']:.1f} | runs z {r['runs_z']:+.2f} | "
                      f"V own {r['V_own_lag1']:.3f} (p {r['p_own_lag1']:.3f}) opp {r['V_opp_lag1']:.3f} (p {r['p_opp_lag1']:.3f}) outcome {r['V_outcome_lag1']:.3f} (p {r['p_outcome_lag1']:.3f}) joint {r['V_joint_lag1']:.3f} (p {r['p_joint_lag1']:.3f}) | payoff {r['payoff']:.3f}")
        print(f"--- {gt.upper()} matched contrasts, all models pooled ---")
        for c in rows_con:
            if c["game_type"] == gt and c["model"] == "all":
                print(f"  {c['metric']:15s} {c['contrast']:30s} {c['estimate']:+8.3f} [{c['lo']:+7.3f}, {c['hi']:+7.3f}]")
        print(f"--- {gt.upper()} self-specific interaction by model ---")
        for c in rows_con:
            if c["game_type"] == gt and c["model"] != "all" and c["contrast"].startswith("self-specific"):
                print(f"  {c['model']:6s} {c['metric']:15s} {c['estimate']:+8.3f} [{c['lo']:+7.3f}, {c['hi']:+7.3f}]")


if __name__ == "__main__":
    main()
