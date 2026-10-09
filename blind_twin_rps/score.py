"""Frozen scoring, baselines, game-level bootstrap, report and plots."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import config as C

SEATS = ("player_a", "player_b")


def load(rd: Path):
    games = [json.loads(l) for l in (rd / "game_logs.jsonl").read_text().splitlines() if l.strip()]
    calls = {}
    for l in (rd / "calls.jsonl").read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            calls[r["slot_id"]] = r
    return games, calls


def seat_model(g, seat):
    return g["player_a_model"] if seat == "player_a" else g["player_b_model"]


def prediction_rows(games, calls) -> List[Dict[str, Any]]:
    rows = []
    for g in games:
        for t in range(1, g["n_valid_rounds"] + 1):
            tgt = g["rounds"][t - 1]
            for j in C.JUDGES:
                for cnd in C.CONDITIONS:
                    r = calls.get(f"judge:{g['game_id']}:r{t:02d}:{j}:{cnd}")
                    pr = ((r or {}).get("parse") or {}).get("prediction")
                    for seat in SEATS:
                        rows.append({
                            "game_id": g["game_id"], "matchup": g["matchup"], "round": t, "seat": seat,
                            "seat_model": seat_model(g, seat), "opponent_model": seat_model(g, "player_b" if seat == "player_a" else "player_a"),
                            "judge": j, "condition": cnd, "valid": pr is not None,
                            "predicted": pr[seat] if pr else None, "actual": tgt[seat],
                            "correct": (1 if pr[seat] == tgt[seat] else 0) if pr else None,
                            "parse_reason": ((r or {}).get("parse") or {}).get("reason", (r or {}).get("status", "missing"))})
    return rows


# ---------------------------------------------------------------------------
# Baselines (prior history only). A baseline may return a SET of tied moves; credit = 1/|set| if the
# actual move is in the set, else 0. Round 1 (no history) predicts all three moves (credit 1/3).
# ---------------------------------------------------------------------------
MOVES = C.SHAPES


def _score(pred, actual: str) -> float:
    s = set(MOVES) if pred is None else (set(pred) if isinstance(pred, (set, frozenset, tuple, list)) else {pred})
    return (1.0 / len(s)) if actual in s else 0.0


def _argmax(counts: Dict[str, float]):
    m = max(counts.values())
    top = tuple(sorted(k for k, v in counts.items() if v == m))
    return top[0] if len(top) == 1 else top


def _up(m):      # R -> P -> S -> R
    return MOVES[(MOVES.index(m) + 1) % 3]


def _down(m):
    return MOVES[(MOVES.index(m) - 1) % 3]


def baseline_predictions(prior: List[Dict], seat: str):
    other = "player_b" if seat == "player_a" else "player_a"
    own = [r[seat] for r in prior]
    if not own:
        return {b: None for b in BASELINES}
    out = {}
    out["frequency"] = _argmax({m: own.count(m) for m in MOVES})
    out["repeat_last"] = own[-1]
    out["cycle_up"] = _up(own[-1])
    out["cycle_down"] = _down(own[-1])
    out["counter_opponent_last"] = C.BEATEN_BY[prior[-1][other]]
    won = prior[-1]["winner"] == ("Player A" if seat == "player_a" else "Player B")
    out["win_stay_lose_shift"] = own[-1] if won else C.BEATEN_BY[prior[-1][other]]
    last = own[-1]
    nxt = [b for a, b in zip(own, own[1:]) if a == last]
    out["markov1"] = _argmax({m: nxt.count(m) + 1 for m in MOVES})
    return out


BASELINES = ("frequency", "repeat_last", "cycle_up", "cycle_down", "counter_opponent_last", "win_stay_lose_shift", "markov1")


def baseline_rows(games) -> List[Dict[str, Any]]:
    rows = []
    for g in games:
        for t in range(1, g["n_valid_rounds"] + 1):
            prior = g["rounds"][: t - 1]
            tgt = g["rounds"][t - 1]
            for seat in SEATS:
                bp = baseline_predictions(prior, seat)
                rows.append({"game_id": g["game_id"], "matchup": g["matchup"], "round": t, "seat": seat,
                             "seat_model": seat_model(g, seat), "actual": tgt[seat],
                             **{f"pred_{b}": ("|".join(bp[b]) if isinstance(bp[b], tuple) else bp[b]) for b in BASELINES},
                             **{f"score_{b}": _score(bp[b], tgt[seat]) for b in BASELINES}})
    return rows


# ---------------------------------------------------------------------------
# Primary indices
# ---------------------------------------------------------------------------

def paired_items(prows) -> Dict[Tuple, Dict[str, int]]:
    """(judge, game, round, seat) -> {condition: correct}, only items valid in ALL three conditions."""
    by = defaultdict(dict)
    meta = {}
    for r in prows:
        if r["valid"]:
            k = (r["judge"], r["game_id"], r["round"], r["seat"])
            by[k][r["condition"]] = r["correct"]
            meta[k] = r
    return {k: v for k, v in by.items() if len(v) == 3}, meta


def strata_for(g_model: str) -> List[Tuple[str, str]]:
    return [(seat, opp) for seat in SEATS for opp in C.ORDER]


def acc_table(items, meta, game_subset: Optional[List[str]] = None) -> Dict[Tuple, Optional[float]]:
    """Acc[j, g, c] in percent: equal weight over (seat x opponent) strata, then games, then rounds."""
    cell = defaultdict(list)   # (j, g, c, seat, opp, game) -> [correct]
    for k, v in items.items():
        j, game, t, seat = k
        m = meta[k]
        for c, x in v.items():
            cell[(j, m["seat_model"], c, seat, m["opponent_model"], game)].append(x)
    games_mult = defaultdict(int)
    if game_subset is not None:
        for gid in game_subset:
            games_mult[gid] += 1
    out = {}
    for j in C.JUDGES:
        for gm in C.ORDER:
            for c in C.CONDITIONS:
                strata = []
                for seat, opp in strata_for(gm):
                    gvals = []
                    for (jj, gg, cc, ss, oo, game), xs in cell.items():
                        if (jj, gg, cc, ss, oo) == (j, gm, c, seat, opp):
                            w = games_mult[game] if game_subset is not None else 1
                            gvals += [sum(xs) / len(xs)] * w
                    if gvals:
                        strata.append(sum(gvals) / len(gvals))
                out[(j, gm, c)] = 100 * sum(strata) / len(strata) if len(strata) == 4 else None
    return out


def indices(acc) -> Dict[str, Optional[float]]:
    def d(j, g, a, b):
        x, y = acc.get((j, g, a)), acc.get((j, g, b))
        return None if x is None or y is None else x - y
    out = {}
    for j in C.JUDGES:
        for g in C.ORDER:
            out[f"T[{j},{g}]"] = d(j, g, "TRUE", "ANONYMOUS")
            out[f"F[{j},{g}]"] = d(j, g, "TRUE", "FALSE")
    def inter(L):
        a, b, c, e = out[f"{L}[astra,astra]"], out[f"{L}[fable,astra]"], out[f"{L}[fable,fable]"], out[f"{L}[astra,fable]"]
        return None if None in (a, b, c, e) else 0.5 * ((a - b) + (c - e))
    out["S"] = inter("T")
    out["S_false"] = inter("F")
    return out


def responsiveness(prows) -> List[Dict[str, Any]]:
    by = defaultdict(dict)
    for r in prows:
        if r["valid"]:
            by[(r["judge"], r["game_id"], r["round"], r["seat"])][r["condition"]] = r["predicted"]
    out = []
    for j in C.JUDGES:
        for seat in SEATS:
            ks = [k for k in by if k[0] == j and k[3] == seat]
            for a, b in (("TRUE", "FALSE"), ("TRUE", "ANONYMOUS"), ("FALSE", "ANONYMOUS")):
                pairs = [by[k] for k in ks if a in by[k] and b in by[k]]
                out.append({"judge": j, "seat": seat, "comparison": f"{a} vs {b}", "n": len(pairs),
                            "pct_differ": 100 * sum(1 for p in pairs if p[a] != p[b]) / len(pairs) if pairs else None})
    return out


def bootstrap(items, meta, games, n_boot: int) -> Dict[str, Any]:
    by_type = defaultdict(list)
    for g in games:
        by_type[g["matchup"]].append(g["game_id"])
    rng = random.Random(C.derive_seed("bootstrap"))
    keys = None
    reps = defaultdict(list)
    undefined = defaultdict(int)
    for _ in range(n_boot):
        subset = []
        for mt, gids in by_type.items():
            subset += [gids[rng.randrange(len(gids))] for _ in gids]
        ix = indices(acc_table(items, meta, subset))
        for k, v in ix.items():
            if v is None:
                undefined[k] += 1
            else:
                reps[k].append(v)
        keys = ix.keys()
    ci = {}
    for k in keys:
        v = sorted(reps[k])
        ci[k] = {"lo": v[int(0.025 * (len(v) - 1))] if v else None, "hi": v[int(0.975 * (len(v) - 1))] if v else None,
                 "undefined_frac": undefined[k] / n_boot}
    return ci


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _w(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def fmt(x, nd=1, sign=False):
    if x is None:
        return "NA"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def analyze(rd: Path) -> Dict[str, Any]:
    games, calls = load(rd)
    prows = prediction_rows(games, calls)
    brows = baseline_rows(games)
    _w(rd / "predictions.csv", prows)
    _w(rd / "baseline_scores.csv", brows)
    invalid = [{"slot_id": k, "kind": r["kind"], "model": r["model"], "status": r["status"],
                "reason": (r.get("parse") or {}).get("reason"), "text": ((r.get("response") or {}).get("text") or "")[:300]}
               for k, r in calls.items() if not (r.get("parse") or {}).get("valid")]
    _w(rd / "invalids.csv", invalid)

    items, meta = paired_items(prows)
    acc = acc_table(items, meta)
    ix = indices(acc)
    ci = bootstrap(items, meta, games, C.N_BOOT)
    resp = responsiveness(prows)

    # descriptive breakdowns on the paired set
    def mean_pct(filt):
        xs = [v[c] for k, v in items.items() for c in v if filt(k, meta[k], c)]
        return (100 * sum(xs) / len(xs), len(xs)) if xs else (None, 0)
    breakdown = []
    for j in C.JUDGES:
        for c in C.CONDITIONS:
            for seat in SEATS:
                for gm in C.ORDER:
                    for half, lo, hi in (("rounds 1-10", 1, 10), ("rounds 11-20", 11, 20), ("all", 1, 20)):
                        p, n = mean_pct(lambda k, m, cc: k[0] == j and cc == c and k[3] == seat and m["seat_model"] == gm and lo <= k[2] <= hi)
                        breakdown.append({"judge": j, "condition": c, "seat": seat, "seat_model": gm, "rounds": half, "pct_correct": p, "n": n})
    by_game = []
    for g in games:
        for j in C.JUDGES:
            for c in C.CONDITIONS:
                p, n = mean_pct(lambda k, m, cc: k[0] == j and k[1] == g["game_id"] and cc == c)
                by_game.append({"game_id": g["game_id"], "matchup": g["matchup"], "judge": j, "condition": c, "pct_correct": p, "n": n})
    both = []
    for j in C.JUDGES:
        for c in C.CONDITIONS:
            rnd = defaultdict(list)
            for k, v in items.items():
                if k[0] == j:
                    rnd[(k[1], k[2])].append(v[c])
            full = [x for x in rnd.values() if len(x) == 2]
            both.append({"judge": j, "condition": c, "n_rounds": len(full),
                         "pct_both_correct": 100 * sum(1 for x in full if all(x)) / len(full) if full else None})
    base_summary = []
    for b in BASELINES:
        xs = [r[f"score_{b}"] for r in brows]
        base_summary.append({"baseline": b, "pct": 100 * sum(xs) / len(xs) if xs else None, "n": len(xs)})
    # baseline on the same items as each judge's paired set
    bidx = {(r["game_id"], r["round"], r["seat"]): r for r in brows}
    base_paired = []
    for j in C.JUDGES:
        ks = [k for k in items if k[0] == j]
        for b in BASELINES:
            xs = [bidx[(k[1], k[2], k[3])][f"score_{b}"] for k in ks]
            base_paired.append({"judge_item_set": j, "baseline": b, "pct": 100 * sum(xs) / len(xs) if xs else None, "n": len(xs)})
    # choice behaviour of players
    play = []
    for g in games:
        for seat in SEATS:
            ch = [r[seat] for r in g["rounds"]]
            play.append({"game_id": g["game_id"], "seat": seat, "model": seat_model(g, seat), "n": len(ch),
                         **{f"pct_{m.lower()}": (100 * ch.count(m) / len(ch) if ch else None) for m in MOVES},
                         "pct_switch": 100 * sum(1 for a, b in zip(ch, ch[1:]) if a != b) / (len(ch) - 1) if len(ch) > 1 else None,
                         "wins": sum(1 for r in g["rounds"] if r["winner"] == ("Player A" if seat == "player_a" else "Player B")),
                         "ties": sum(1 for r in g["rounds"] if r["winner"] == "Tie")})
    summary = [{"quantity": k, "value_pp": v, "ci_lo": ci[k]["lo"], "ci_hi": ci[k]["hi"], "undefined_boot_frac": ci[k]["undefined_frac"]}
               for k, v in ix.items()]
    summary += [{"quantity": f"Acc[{j},{g},{c}]", "value_pp": v, "ci_lo": None, "ci_hi": None, "undefined_boot_frac": None}
                for (j, g, c), v in acc.items()]
    _w(rd / "summary.csv", summary)
    _w(rd / "breakdown.csv", breakdown)
    _w(rd / "by_game.csv", by_game)
    _w(rd / "responsiveness.csv", resp)
    _w(rd / "player_behaviour.csv", play)
    out = {"acc": {f"{a}|{b}|{c}": v for (a, b, c), v in acc.items()}, "indices": ix, "ci": ci,
           "responsiveness": resp, "both_correct": both, "baselines_all_rounds": base_summary,
           "baselines_on_judge_items": base_paired, "n_paired_items": {j: sum(1 for k in items if k[0] == j) for j in C.JUDGES}}
    (rd / "results.json").write_text(json.dumps(out, indent=1))
    plots(rd, games, prows)
    write_report(rd, games, calls, out, acc, breakdown, play, by_game)
    files = sorted(p for p in rd.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (rd / "checksums.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    return out


def plots(rd: Path, games, prows) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figdir = rd / "figures"
    figdir.mkdir(exist_ok=True)
    colors = {"TRUE": "#2a7", "FALSE": "#c33", "ANONYMOUS": "#777"}
    for j in C.JUDGES:
        fig, axes = plt.subplots(3, 4, figsize=(16, 9), sharex=True, sharey=True)
        for ax, g in zip(axes.T.flatten(), sorted(games, key=lambda x: (x["matchup"], x["replicate"]))):
            for c in C.CONDITIONS:
                pts = []
                for t in range(1, g["n_valid_rounds"] + 1):
                    xs = [r["correct"] for r in prows if r["game_id"] == g["game_id"] and r["judge"] == j and r["condition"] == c and r["round"] == t and r["valid"]]
                    pts.append(sum(xs) / len(xs) if xs else float("nan"))
                cum, acc_ = [], []
                for p in pts:
                    if p == p:
                        acc_.append(p)
                    cum.append(sum(acc_) / len(acc_) if acc_ else float("nan"))
                ax.plot(range(1, len(cum) + 1), cum, color=colors[c], label=c)
            ax.axhline(1 / 3, color="#bbb", lw=0.8, ls="--")
            ax.set_title(f"{g['game_id']} ({g['matchup']})", fontsize=9)
            ax.set_ylim(0, 1)
        axes[0, 0].legend(fontsize=8)
        fig.suptitle(f"Judge {C.MODELS[j]['display']}: cumulative accuracy (mean of both seats) by round")
        fig.supxlabel("round"); fig.supylabel("cumulative proportion correct")
        fig.tight_layout()
        fig.savefig(figdir / f"trajectory_judge_{j}.png", dpi=110)
        plt.close(fig)
    fig, axes = plt.subplots(len(games), 1, figsize=(10, 0.55 * len(games) + 1), sharex=True)
    for ax, g in zip(axes, games):
        for i, seat in enumerate(SEATS):
            ys = [MOVES.index(r[seat]) for r in g["rounds"]]
            ax.step(range(1, len(ys) + 1), [y + 3.5 * i for y in ys], where="mid", lw=1)
        ax.set_yticks([1, 4.5]); ax.set_yticklabels(["A", "B"], fontsize=6)
        ax.set_ylabel(g["game_id"], rotation=0, fontsize=7, labelpad=18)
    axes[-1].set_xlabel("round (0 = ROCK, 1 = PAPER, 2 = SCISSORS)")
    fig.tight_layout()
    fig.savefig(figdir / "choices_by_game.png", dpi=110)
    plt.close(fig)


def write_report(rd, games, calls, out, acc, breakdown, play, by_game) -> None:
    ix, ci = out["indices"], out["ci"]
    pl = [r for r in calls.values() if r["kind"] == "player"]
    jd = [r for r in calls.values() if r["kind"] == "judge"]
    cost = sum(float(r.get("cost_usd") or 0) for r in calls.values())
    smoke = rd / "smoke_calls.jsonl"
    smoke_cost = sum(float(json.loads(l).get("cost_usd") or 0) for l in smoke.read_text().splitlines() if l.strip()) if smoke.exists() else 0.0
    L = ["# Blind Twin RPS pilot: morning report", "",
         f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Exploratory feasibility pilot, not confirmatory.", "",
         "## Completion and cost", "",
         "| matchup (player_a-player_b) | games complete / 3 | valid rounds |", "|---|---:|---:|"]
    for mm, ms in C.MATCHUPS:
        gs = [g for g in games if g["matchup"] == f"{mm}-{ms}"]
        L.append(f"| {mm}-{ms} | {sum(1 for g in gs if g['status'] == 'complete')} | {sum(g['n_valid_rounds'] for g in gs)} / {3 * C.N_ROUNDS} |")
    L += ["", f"- Player calls: {len(pl)} recorded, {sum(1 for r in pl if (r.get('parse') or {}).get('valid'))} valid choices.",
          f"- Judge calls: {len(jd)} recorded, {sum(1 for r in jd if (r.get('parse') or {}).get('valid'))} valid predictions "
          f"(paired items valid in all three conditions: {out['n_paired_items']}).",
          f"- Charged cost: ${cost:.2f} scientific + ${smoke_cost:.2f} technical smoke = ${cost + smoke_cost:.2f} (ceiling ${C.BUDGET_CAP_USD:.0f}).",
          "- Incomplete games: " + (", ".join(f"{g['game_id']} ({g['note']})" for g in games if g["status"] != "complete") or "none") + ".", "",
          "## Accuracy table (percent correct, equal-weight over seat x opponent strata and games; 33.3% = random guess)", "",
          "| judge | predicted player model | TRUE | FALSE | ANONYMOUS |", "|---|---|---:|---:|---:|"]
    for j in C.JUDGES:
        for g in C.ORDER:
            L.append(f"| {j} | {g}{' (self)' if g == j else ''} | " + " | ".join(fmt(acc[(j, g, c)]) for c in C.CONDITIONS) + " |")
    def row(k, label):
        c = ci[k]
        tag = " (unstable)" if c["undefined_frac"] > 0.01 else ""
        return f"| {label} | {fmt(ix[k], 1, True)} | [{fmt(c['lo'], 1, True)}, {fmt(c['hi'], 1, True)}]{tag} |"
    L += ["", "## Identity indices (percentage points; game-level bootstrap within matchup, 5,000 resamples of 3 games per type)", "",
          "| index | estimate | 95% interval |", "|---|---:|---|",
          row("S", "**S: self-specific truth benefit (TRUE vs ANONYMOUS), primary**"),
          row("S_false", "S_false: self-specific false-label cost (TRUE vs FALSE), key companion")]
    for j in C.JUDGES:
        for g in C.ORDER:
            L.append(row(f"T[{j},{g}]", f"T[{j},{g}] truth benefit"))
    for j in C.JUDGES:
        for g in C.ORDER:
            L.append(row(f"F[{j},{g}]", f"F[{j},{g}] false-label cost"))
    L += ["", "With 3 games per matchup these intervals describe game-to-game variation only; rounds within a game are not independent subjects.", "",
          "## Label responsiveness (percent of paired items whose hard prediction differs)", "",
          "| judge | seat | comparison | n | % differ |", "|---|---|---|---:|---:|"]
    for r in out["responsiveness"]:
        L.append(f"| {r['judge']} | {r['seat']} | {r['comparison']} | {r['n']} | {fmt(r['pct_differ'])} |")
    L += ["", "## Simple history-only baselines (percent correct; round 1 and tied predictions get fractional credit; chance 33.3%)", "",
          "| baseline | all valid rounds | on Astra judge items | on Fable judge items |", "|---|---:|---:|---:|"]
    bp = {(r["judge_item_set"], r["baseline"]): r["pct"] for r in out["baselines_on_judge_items"]}
    for r in out["baselines_all_rounds"]:
        L.append(f"| {r['baseline']} | {fmt(r['pct'])} | {fmt(bp.get(('astra', r['baseline'])))} | {fmt(bp.get(('fable', r['baseline'])))} |")
    L += ["", "Both-seats-correct rate (descriptive only): " + "; ".join(f"{r['judge']}/{r['condition']} {fmt(r['pct_both_correct'])}% of {r['n_rounds']}" for r in out["both_correct"]), "",
          "## Per-judge, role-specific breakdown (all rounds, paired items)", "",
          "| judge | condition | seat | player model | % correct | n |", "|---|---|---|---|---:|---:|"]
    for r in breakdown:
        if r["rounds"] == "all":
            L.append(f"| {r['judge']} | {r['condition']} | {r['seat']} | {r['seat_model']} | {fmt(r['pct_correct'])} | {r['n']} |")
    L += ["", "Early vs late rounds:", "", "| judge | condition | rounds 1-10 | rounds 11-20 |", "|---|---|---:|---:|"]
    for j in C.JUDGES:
        for c in C.CONDITIONS:
            def avg(h):
                xs = [r for r in breakdown if r["judge"] == j and r["condition"] == c and r["rounds"] == h and r["pct_correct"] is not None]
                n = sum(r["n"] for r in xs)
                return sum(r["pct_correct"] * r["n"] for r in xs) / n if n else None
            L.append(f"| {j} | {c} | {fmt(avg('rounds 1-10'))} | {fmt(avg('rounds 11-20'))} |")
    L += ["", "## Players", "", "| game | seat | model | % ROCK | % PAPER | % SCISSORS | % switch | wins | ties |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in play:
        L.append(f"| {r['game_id']} | {r['seat']} | {r['model']} | {fmt(r['pct_rock'])} | {fmt(r['pct_paper'])} | {fmt(r['pct_scissors'])} | {fmt(r['pct_switch'])} | {r['wins']} | {r['ties']} |")
    # v2 additions: player response lengths and replicate openings
    L += ["", "Player responses (protocol " + C.PROTOCOL + "; player format line: \"" + C.PLAYER_FORMAT_LINE + "\"):", "",
          "| model | responses | valid | median completion tokens | max completion tokens | % with reasoning before the shape |", "|---|---:|---:|---:|---:|---:|"]
    for m in C.ORDER:
        rs = [r for r in pl if r["model"] == m and r["status"] == "completed"]
        toks = sorted((r["response"]["usage"].get("completion_tokens") or 0) for r in rs)
        multi = [r for r in rs if len([l for l in (r["response"]["text"] or "").strip().splitlines() if l.strip()]) > 1]
        L.append(f"| {m} | {len(rs)} | {sum(1 for r in rs if r['parse']['valid'])} | {toks[len(toks) // 2] if toks else 'NA'} | "
                 f"{toks[-1] if toks else 'NA'} | {fmt(100 * len(multi) / len(rs) if rs else None)} |")
    L += ["", "Replicate independence (first three rounds, player_a/player_b):", ""]
    for mm, ms in C.MATCHUPS:
        gs = [g for g in games if g["matchup"] == f"{mm}-{ms}"]
        ops = ["".join(r["player_a"][0] for r in g["rounds"][:3]) + "/" + "".join(r["player_b"][0] for r in g["rounds"][:3]) for g in gs]  # R/P/S initials
        full = ["".join(r["player_a"][0] + r["player_b"][0] for r in g["rounds"]) for g in gs]
        L.append(f"- {mm}-{ms}: openings {ops}; distinct openings {len(set(ops))}/{len(ops)}; distinct full games {len(set(full))}/{len(full)}")
    L += ["", "Per-game accuracy: `by_game.csv`; trajectories: `figures/trajectory_judge_astra.png`, `figures/trajectory_judge_fable.png`, `figures/choices_by_game.png`.", "",
          "## Limitations", "",
          "- Two models, three games per matchup, 20 rounds: a feasibility pilot. Effects are described at game level; no confirmatory claim.",
          "- 'Same model' means another independently queried instance, not memory of the actions. A truth benefit measures the functional value of identity information, not introspection or privileged access.",
          "- Neither endpoint supports temperature control; both ran at provider-default sampling with low hidden reasoning (effort=low, excluded). Hidden reasoning content is unobserved.",
          "- Players see the full public history afresh each round; there is no carried conversation state.",
          "- Beating 33.3% by exploiting simple action biases is not self-knowledge; compare with the history-only baselines above.",
          "- The dollar ceiling was set by Claude from Chris's standing $100 project cap and 'build and run it' instruction; see approvals.jsonl.", ""]
    (rd / "report.md").write_text("\n".join(L) + "\n")
