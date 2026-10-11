"""Observation-equivalence calibration for Experiment 2 (Blind Twin on logs), 2026-10-11. Offline, no API calls.

Question: how many logged games of a target model does a history-only outsider need before it predicts that model's
moves as well as the LLM judges do? Evaluated on the condition-00 games Experiment 2 judged, stratified as in
Experiment 2 (equal weight over seat x opponent strata, then games, then rounds).

For k in K_GRID, train the backoff n-gram predictor from experiment1_post_hoc_strategy on k randomly chosen other
player-games of the target model (held-out game excluded; R random subsets per held-out game, seed 20261011) and
record held-out accuracy. k = 0 is the history-free predictor (uniform root: predicts a fixed move), i.e. chance.
Also reported: the generic predictor trained on k player-games of the OTHER two models (no target-model data).

Outputs: post_hoc/experiment2_observation_equivalence/learning_curve.csv and REPORT.md.
"""
from __future__ import annotations

import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment1_post_hoc_strategy as X   # noqa: E402

OUT = X.REPO / "post_hoc" / "experiment2_observation_equivalence"
K_GRID = (0, 1, 2, 3, 5, 8, 12, 16, 24, 32, 47)
R = 8
SEED = 20261011

# Experiment 2 judge accuracies on the same games (REPORT.md of btx1-20261010), percent
JUDGES = {
    ("rps", "astra"): {"self TRUE": 43.8, "self ANON": 40.0, "best other TRUE": 40.8},
    ("rps", "fable"): {"self TRUE": 53.4, "self ANON": 45.0, "best other TRUE": 46.7},
    ("rps", "qwen"):  {"self TRUE": 37.5, "self ANON": 38.8, "best other TRUE": 46.3},
    ("mp", "astra"):  {"self TRUE": 58.3, "self ANON": 55.0, "best other TRUE": 58.3},
    ("mp", "fable"):  {"self TRUE": 65.0, "self ANON": 62.1, "best other TRUE": 55.4},
    ("mp", "qwen"):   {"self TRUE": 56.7, "self ANON": 58.3, "best other TRUE": 57.5},
}


def strat_mean(items):
    """items: list of (stratum, gid, acc) -> equal weight over strata, then games."""
    strata = defaultdict(lambda: defaultdict(list))
    for s, g, a in items:
        strata[s][g].append(a)
    return sum(sum(sum(v) / len(v) for v in gs.values()) / len(gs) for gs in strata.values()) / len(strata)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    rows = []
    for gt in ("rps", "mp"):
        pgs = X.load_player_games(gt)
        by_model = defaultdict(list)
        for pg in pgs:
            by_model[pg["model"]].append(pg)
        for target in X.MODELS:
            tests = [pg for pg in by_model[target] if pg["condition"] == "00"]
            for k in K_GRID:
                for kind in ("same_model", "other_models"):
                    items = []
                    for pg in tests:
                        if kind == "same_model":
                            pool = [p for p in by_model[target] if p["gid"] != pg["gid"]]
                        else:
                            pool = [p for m in X.MODELS if m != target for p in by_model[m] if p["gid"] != pg["gid"]]
                        kk = min(k, len(pool))
                        reps = 1 if kk in (0, len(pool)) else R
                        accs = []
                        for _ in range(reps):
                            P = X.Backoff(gt, rng.sample(pool, kk) if kk < len(pool) else pool)
                            accs.append(100 * sum(P.predict(pg["role"], pg["own"], pg["opp"], pg["res"], t) == pg["own"][t] for t in range(20)) / 20)
                        items.append(((pg["seat"], pg["opp_model"]), pg["gid"], sum(accs) / len(accs)))
                    rows.append(dict(game_type=gt, target_model=target, predictor=kind, k_games=k, n_test_player_games=len(tests),
                                     accuracy=round(strat_mean(items), 2)))
    with open(OUT / "learning_curve.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    lines = ["# Observation equivalence: how many logged games match the LLM judges? (exploratory, 2026-10-11)", "",
             "History-only n-gram predictor trained on k player-games of the target model (same_model) or of the other two",
             "models only (other_models), evaluated on the condition-00 games Experiment 2 judged. Judge figures from",
             "`blind_twin_exp1/results/btx1-20261010/REPORT.md`. Accuracy in percent; chance RPS 33.3, MP 50.0.", ""]
    for gt in ("rps", "mp"):
        lines.append(f"## {gt.upper()}")
        lines.append("")
        lines.append("| target | predictor | " + " | ".join(f"k={k}" for k in K_GRID) + " | self-judge TRUE | self-judge ANON | best other judge TRUE | k to match self TRUE |")
        lines.append("|---|---|" + "---:|" * len(K_GRID) + "---:|---:|---:|---:|")
        for target in X.MODELS:
            j = JUDGES[(gt, target)]
            for kind in ("same_model", "other_models"):
                curve = [r["accuracy"] for r in rows if r["game_type"] == gt and r["target_model"] == target and r["predictor"] == kind]
                match = next((k for k, a in zip(K_GRID, curve) if a >= j["self TRUE"]), None)
                lines.append(f"| {target} | {kind} | " + " | ".join(f"{a:.1f}" for a in curve) +
                             f" | {j['self TRUE']} | {j['self ANON']} | {j['best other TRUE']} | {match if match is not None else '> 47'} |")
        lines.append("")
    (OUT / "REPORT.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
