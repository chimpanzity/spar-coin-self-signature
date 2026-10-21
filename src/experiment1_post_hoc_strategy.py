"""Post hoc, exploratory strategy measures for Study 1 Experiment 1 (opponent disclosure), 2026-10-11.

Computed offline from the amended (with make-ups) complete games; no API calls. Not a replacement for the
pre-registered payoff endpoint. Two measures per player-game, grouped by what the player was told:

  uninformed_self    not told (00 either seat; 10 as P2; 01 as P1), opponent is the same model
  uninformed_other   not told, opponent is a different model
  told_self          told, opponent is the same model (10 as P1, 01 as P2, 11 either seat)
  told_other         told, opponent is a different model
  Contrasts are matched on opponent type: told_self - uninformed_self and told_other - uninformed_other. The
  self-specific effect is their difference (the told x opponent-type interaction).

1. Defensive measure: predictability of the player's own moves by a history-only predictor.
   Predictor A (primary): a backoff n-gram predictor trained on ALL other games of the same player model (all
   groups pooled) and evaluated on the held-out game (leave-one-game-out). The same predictor is applied to every
   group, so group differences cannot come from different training sets.
   Predictor B (secondary): the same predictor trained only on other player-games of the same model AND same group,
   with the training set size equalised across groups at 7 player-games (all 7 for the self groups; the mean over 5
   random 7-game subsets for the other groups, seed 20261011), so that group differences cannot come from
   training-set size.
   Lower accuracy = harder to predict. Chance: RPS 33.3, MP 50.0.

2. Offensive measure: counter-prediction alignment. The player's move is "aligned" when it is the best response to
   the move a history-only predictor forecasts for the opponent this round (RPS: beats it; MP: Matcher matches it,
   Mismatcher mismatches it). Two predictors are used for the opponent's move:
   - opponent-model predictor: trained on the true opponent model's play (LOGO; held-out game excluded);
   - own-model predictor: trained on the player's own model's play (what a copy of the player would tend to do).
   In told_self games these coincide. Chance: RPS 33.3, MP 50.0.

Uncertainty: percentile bootstrap over player-games within group (seed 20261011, 4000 resamples).
"""
from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

REPO = repo_paths.REPO   # was Path(__file__).resolve().parent
SOURCES = {
    "rps": repo_paths.legacy("opponent_disclosure_rps_3models/results/rps3m-p2-20261010/with_makeups/rounds.csv"),
    "mp": repo_paths.legacy("opponent_disclosure_mp_3models/results/mp3m-p2-20261010/with_makeups/rounds.csv"),
}
OUT = repo_paths.legacy("post_hoc/experiment1_strategy_measures")
MOVES = {"rps": ("ROCK", "PAPER", "SCISSORS"), "mp": ("STAR", "TRIANGLE")}
BEATS = {"ROCK": "PAPER", "PAPER": "SCISSORS", "SCISSORS": "ROCK"}   # value beats key
MIN_N = 8
ALPHA = 2.0
SEED = 20261011
N_BOOT = 4000
MODELS = ("astra", "fable", "qwen")
GROUPS = ("uninformed_self", "uninformed_other", "told_self", "told_other")
BASE = {"told_self": "uninformed_self", "told_other": "uninformed_other"}


def load_player_games(gt: str):
    rows = list(csv.DictReader(open(SOURCES[gt])))
    games = defaultdict(list)
    for r in rows:
        if r["complete_game"] != "True":
            continue
        games[r["game_id"]].append(r)
    out = []
    for gid, rs in games.items():
        rs.sort(key=lambda r: int(r["round"]))
        assert len(rs) == 20, (gid, len(rs))
        p1, p2, cond = rs[0]["p1_model"], rs[0]["p2_model"], rs[0]["condition"]
        for seat in ("p1", "p2"):
            own = [r[seat] for r in rs]
            opp = [r["p2" if seat == "p1" else "p1"] for r in rs]
            pay = [float(r["p1_payoff"]) if seat == "p1" else 1 - float(r["p1_payoff"]) for r in rs]
            res = ["win" if p == 1 else "lose" if p == 0 else "tie" for p in pay]
            model = p1 if seat == "p1" else p2
            oppm = p2 if seat == "p1" else p1
            informed = (cond in ("10", "11")) if seat == "p1" else (cond in ("01", "11"))
            group = ("told_" if informed else "uninformed_") + ("self" if model == oppm else "other")
            role = ("matcher" if seat == "p1" else "mismatcher") if gt == "mp" else "sym"
            out.append(dict(gid=gid, seat=seat, model=model, opp_model=oppm, condition=cond, group=group, role=role,
                            own=own, opp=opp, res=res, payoff=sum(pay) / 20))
    return out


def contexts(role, own, opp, res, t):
    """Contexts for predicting own[t] (0-based t), most specific first."""
    if t == 0:
        return [(role, "first")]
    c = [(role, own[t - 1], opp[t - 1], res[t - 1]), (role, own[t - 1], opp[t - 1]), (role, own[t - 1]), (role,)]
    if t >= 2:
        c = [(role, own[t - 1], opp[t - 1], res[t - 1], own[t - 2], opp[t - 2])] + c
    return c


class Backoff:
    def __init__(self, gt, train):
        self.moves = MOVES[gt]
        self.tab = defaultdict(Counter)
        for pg in train:
            for t in range(20):
                for c in contexts(pg["role"], pg["own"], pg["opp"], pg["res"], t):
                    self.tab[c][pg["own"][t]] += 1

    def proba(self, role, own, opp, res, t):
        """Interpolated backoff distribution over moves: each context's counts are smoothed toward the next less
        specific context (alpha = 2), with a uniform root."""
        cs = contexts(role, own, opp, res, t)
        dist = {m: 1.0 / len(self.moves) for m in self.moves}
        for c in reversed(cs):
            cnt = self.tab[c]; n = sum(cnt.values())
            dist = {m: (cnt[m] + ALPHA * dist[m]) / (n + ALPHA) for m in self.moves}
        return dist

    def predict(self, role, own, opp, res, t):
        cs = contexts(role, own, opp, res, t)
        chain = [self.tab[c] for c in cs if sum(self.tab[c].values()) >= MIN_N] or [self.tab[cs[-1]]]
        # argmax at the most specific usable context; ties broken by the next contexts, then fixed move order
        def key(m):
            return tuple(cnt[m] for cnt in chain) + (-self.moves.index(m),)
        return max(self.moves, key=key)


def best_response(gt, role, predicted_opp):
    if gt == "rps":
        return BEATS[predicted_opp]
    return predicted_opp if role == "matcher" else [m for m in MOVES["mp"] if m != predicted_opp][0]


def analyse(gt):
    pgs = load_player_games(gt)
    by_model = defaultdict(list)
    for pg in pgs:
        by_model[pg["model"]].append(pg)
    # Predictor A: LOGO within model, pooled over groups. Cache per (model, held-out gid).
    cacheA = {}
    def predA(model, gid):
        k = (model, gid)
        if k not in cacheA:
            cacheA[k] = Backoff(gt, [p for p in by_model[model] if p["gid"] != gid])
        return cacheA[k]
    cacheB = {}
    rngB = random.Random(SEED)
    def predB(model, group, gid):
        """List of predictors trained on 7-player-game subsets of the same model and group (held-out game excluded)."""
        k = (model, group, gid)
        if k not in cacheB:
            pool = [p for p in by_model[model] if p["gid"] != gid and p["group"] == group]
            if len(pool) <= 7:
                cacheB[k] = [Backoff(gt, pool)]
            else:
                cacheB[k] = [Backoff(gt, rngB.sample(pool, 7)) for _ in range(5)]
        return cacheB[k]
    cacheP = {}
    def predP(gid):
        """Trained on all player-games of all models except the held-out game (no model identity)."""
        if gid not in cacheP:
            cacheP[gid] = Backoff(gt, [p for p in pgs if p["gid"] != gid])
        return cacheP[gid]
    recs = []
    for pg in pgs:
        A = predA(pg["model"], pg["gid"])
        Pm = predP(pg["gid"])
        B = predB(pg["model"], pg["group"], pg["gid"])
        Opp = predA(pg["opp_model"], pg["gid"])            # predicts the opponent's moves (opponent's own history view)
        Own = predA(pg["model"], pg["gid"])                # what a copy of the player would do in the opponent's seat
        opp_role = {"matcher": "mismatcher", "mismatcher": "matcher", "sym": "sym"}[pg["role"]]
        opp_res = [{"win": "lose", "lose": "win", "tie": "tie"}[x] for x in pg["res"]]
        accA = accB = al_opp = al_own = 0
        llA = llP = 0.0
        for t in range(20):
            llA -= math.log(A.proba(pg["role"], pg["own"], pg["opp"], pg["res"], t)[pg["own"][t]])
            llP -= math.log(Pm.proba(pg["role"], pg["own"], pg["opp"], pg["res"], t)[pg["own"][t]])
            accA += A.predict(pg["role"], pg["own"], pg["opp"], pg["res"], t) == pg["own"][t]
            accB += sum(b.predict(pg["role"], pg["own"], pg["opp"], pg["res"], t) == pg["own"][t] for b in B) / len(B)
            po = Opp.predict(opp_role, pg["opp"], pg["own"], opp_res, t)
            pw = Own.predict(opp_role, pg["opp"], pg["own"], opp_res, t)
            al_opp += best_response(gt, pg["role"], po) == pg["own"][t]
            al_own += best_response(gt, pg["role"], pw) == pg["own"][t]
        recs.append(dict(game_type=gt, game_id=pg["gid"], seat=pg["seat"], model=pg["model"], opp_model=pg["opp_model"],
                         condition=pg["condition"], group=pg["group"], payoff=pg["payoff"],
                         predA_acc=100 * accA / 20, predB_acc=100 * accB / 20,
                         logloss_A=round(llA / 20, 4), logloss_pooled=round(llP / 20, 4),
                         align_opp_model=100 * al_opp / 20, align_own_model=100 * al_own / 20))
    return recs


def boot_mean(vals, rng):
    n = len(vals)
    return [sum(rng.choice(vals) for _ in range(n)) / n for _ in range(N_BOOT)]


def summarise(recs, rng):
    metrics = ("predA_acc", "predB_acc", "logloss_A", "logloss_pooled", "align_opp_model", "align_own_model", "payoff")
    rows = []
    for gt in ("rps", "mp"):
        for model in MODELS + ("all",):
            for group in GROUPS:
                sel = [r for r in recs if r["game_type"] == gt and r["group"] == group and (model == "all" or r["model"] == model)]
                row = dict(game_type=gt, model=model, group=group, n_player_games=len(sel))
                for m in metrics:
                    vals = [r[m] for r in sel]
                    bs = sorted(boot_mean(vals, rng))
                    nd = 3 if m.startswith("logloss") else 2
                    row[m] = round(sum(vals) / len(vals), nd)
                    row[m + "_lo"] = round(bs[int(0.025 * N_BOOT)], nd)
                    row[m + "_hi"] = round(bs[int(0.975 * N_BOOT) - 1], nd)
                rows.append(row)
    return rows


def contrasts(recs, rng):
    """Matched contrasts: told_self - uninformed_self, told_other - uninformed_other, and their difference
    (self-specific interaction). Percentile bootstrap over player-games, independent resampling within groups."""
    out = []
    metrics = ("predA_acc", "predB_acc", "logloss_A", "logloss_pooled", "align_opp_model", "align_own_model", "payoff")
    for gt in ("rps", "mp"):
        for model in MODELS + ("all",):
            pick = lambda g: [r for r in recs if r["game_type"] == gt and r["group"] == g and (model == "all" or r["model"] == model)]
            for m in metrics:
                bs = {g: boot_mean([r[m] for r in pick(g)], rng) for g in GROUPS}
                est = {g: sum(r[m] for r in pick(g)) / len(pick(g)) for g in GROUPS}
                d_self = [a - b for a, b in zip(bs["told_self"], bs["uninformed_self"])]
                d_other = [a - b for a, b in zip(bs["told_other"], bs["uninformed_other"])]
                inter = [a - b for a, b in zip(d_self, d_other)]
                for name, est_v, dist in (("told_self - uninformed_self", est["told_self"] - est["uninformed_self"], d_self),
                                          ("told_other - uninformed_other", est["told_other"] - est["uninformed_other"], d_other),
                                          ("self-specific (interaction)", (est["told_self"] - est["uninformed_self"]) - (est["told_other"] - est["uninformed_other"]), inter)):
                    dist = sorted(dist)
                    nd = 3 if m.startswith("logloss") else 2
                    out.append(dict(game_type=gt, model=model, contrast=name, metric=m, estimate=round(est_v, nd),
                                    lo=round(dist[int(0.025 * N_BOOT)], nd), hi=round(dist[int(0.975 * N_BOOT) - 1], nd)))
    return out


def classifier_floor(gt):
    """History-only predictor accuracy on the condition-00 games (the games Experiment 2 judged), stratified like
    Experiment 2 (equal weight over seat x opponent strata, then games). A: trained on the same model's other games;
    C: trained on the other two models' games only (generic LLM play); U: same model, uninformed games only."""
    pgs = load_player_games(gt)
    by_model = defaultdict(list)
    for pg in pgs:
        by_model[pg["model"]].append(pg)
    rows = []
    for pg in pgs:
        if pg["condition"] != "00":
            continue
        trainA = [p for p in by_model[pg["model"]] if p["gid"] != pg["gid"]]
        trainC = [p for m in MODELS if m != pg["model"] for p in by_model[m] if p["gid"] != pg["gid"]]
        trainU = [p for p in by_model[pg["model"]] if p["gid"] != pg["gid"] and p["group"].startswith("uninformed")]
        preds = {"A": Backoff(gt, trainA), "C": Backoff(gt, trainC), "U": Backoff(gt, trainU)}
        acc = {k: 0 for k in preds}
        for t in range(20):
            for k, P in preds.items():
                acc[k] += P.predict(pg["role"], pg["own"], pg["opp"], pg["res"], t) == pg["own"][t]
        rows.append(dict(model=pg["model"], seat=pg["seat"], opp_model=pg["opp_model"], **{k: 100 * v / 20 for k, v in acc.items()}))
    out = []
    for m in MODELS:
        sel = [r for r in rows if r["model"] == m]
        strata = defaultdict(lambda: defaultdict(list))
        for r in sel:
            for k in ("A", "C", "U"):
                strata[k][(r["seat"], r["opp_model"])].append(r[k])
        out.append(dict(game_type=gt, target_model=m, n_player_games=len(sel),
                        **{f"pred{k}_acc": round(sum(sum(v) / len(v) for v in strata[k].values()) / len(strata[k]), 2) for k in ("A", "C", "U")}))
    return out


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    recs = analyse("rps") + analyse("mp")
    write_csv(OUT / "player_games.csv", recs)
    summ = summarise(recs, rng)
    write_csv(OUT / "group_means.csv", summ)
    con = contrasts(recs, rng)
    write_csv(OUT / "contrasts.csv", con)
    floor = classifier_floor("rps") + classifier_floor("mp")
    write_csv(OUT / "classifier_floor_condition00.csv", floor)
    json.dump(dict(min_n=MIN_N, seed=SEED, n_boot=N_BOOT, sources={k: str(v.relative_to(REPO)) for k, v in SOURCES.items()},
                   n_player_games=len(recs)), open(OUT / "settings.json", "w"), indent=1)
    chance = {"rps": 33.3, "mp": 50.0}
    print("\nHistory-only predictor accuracy on the condition-00 games Experiment 2 judged (A same-model, C other-models, U same-model uninformed-only):")
    for r in floor:
        print(f"  {r['game_type']:3s} {r['target_model']:6s} n={r['n_player_games']:2d}  A {r['predA_acc']:5.1f}  C {r['predC_acc']:5.1f}  U {r['predU_acc']:5.1f}")
    for gt in ("rps", "mp"):
        print(f"\n=== {gt.upper()} (chance {chance[gt]}) ===")
        print(f"{'model':6s} {'group':17s} {'n':>3s} | {'predA':>14s} | {'predB':>6s} | {'align_opp':>14s} | {'align_own':>14s} | payoff")
        for r in summ:
            if r["game_type"] != gt: continue
            print(f"{r['model']:6s} {r['group']:17s} {r['n_player_games']:3d} | {r['predA_acc']:5.1f} [{r['predA_acc_lo']:4.1f},{r['predA_acc_hi']:4.1f}] | {r['predB_acc']:5.1f}  | "
                  f"{r['align_opp_model']:5.1f} [{r['align_opp_model_lo']:4.1f},{r['align_opp_model_hi']:4.1f}] | {r['align_own_model']:5.1f} [{r['align_own_model_lo']:4.1f},{r['align_own_model_hi']:4.1f}] | {r['payoff']:.3f}")
        print("-- matched contrasts (pp), all models pooled --")
        for c in con:
            if c["game_type"] == gt and c["model"] == "all" and c["metric"] not in ("payoff", "logloss_A", "logloss_pooled"):
                print(f"all    {c['contrast']:30s} {c['metric']:16s} {c['estimate']:+6.1f} [{c['lo']:+5.1f}, {c['hi']:+5.1f}]")
        print("-- log-loss (nats/round; positive = harder to predict when told) --")
        for c in con:
            if c["game_type"] == gt and c["metric"] in ("logloss_A", "logloss_pooled"):
                print(f"{c['model']:6s} {c['contrast']:30s} {c['metric']:16s} {c['estimate']:+7.3f} [{c['lo']:+6.3f}, {c['hi']:+6.3f}]")


if __name__ == "__main__":
    main()
