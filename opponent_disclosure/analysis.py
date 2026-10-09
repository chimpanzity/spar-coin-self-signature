"""Prespecified analysis (Claude's defaults; the handoff's analysis section was truncated).

Unit of analysis: the game (8 per condition). Primary outcome: Matcher win rate. Factorial contrasts
(percentage points): effect of informing the Matcher, effect of informing the Mismatcher, interaction.
Secondary: per-player STAR rate, switch rate, longest run, history-only predictability, and opponent-
specific factorial effects; descriptive manipulation check. 5,000 bootstrap resamples of games within
each condition. Exploratory pilot: no multiplicity correction, no confirmatory claims.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config as C

ROLES = ("matcher", "mismatcher")
BASELINES = ("frequency", "repeat_last", "alternate_last", "win_stay_lose_shift", "markov1")


def _base(prior, role):
    own = [r[role] for r in prior]
    if not own:
        return {b: None for b in BASELINES}
    ns, nt = own.count("STAR"), own.count("TRIANGLE")
    alt = "TRIANGLE" if own[-1] == "STAR" else "STAR"
    won = prior[-1]["winner"].lower() == role
    last = own[-1]
    nxt = [b for a, b in zip(own, own[1:]) if a == last]
    s, t = nxt.count("STAR") + 1, nxt.count("TRIANGLE") + 1
    return {"frequency": None if ns == nt else ("STAR" if ns > nt else "TRIANGLE"), "repeat_last": own[-1],
            "alternate_last": alt, "win_stay_lose_shift": own[-1] if won else alt,
            "markov1": None if s == t else ("STAR" if s > t else "TRIANGLE")}


def _credit(pred, actual):
    return 0.5 if pred is None else float(pred == actual)


def game_measures(g: Dict[str, Any]) -> Dict[str, Any]:
    rows = g["rounds"]
    n = len(rows)
    m: Dict[str, Any] = {"game_id": g["game_id"], "condition": g["condition"], "n_rounds": n,
                         "matcher_win_rate": 100 * sum(r["winner"] == "Matcher" for r in rows) / n if n else None}
    for role in ROLES:
        seq = [r[role] for r in rows]
        runs, cur = [], 1
        for a, b in zip(seq, seq[1:]):
            if a == b:
                cur += 1
            else:
                runs.append(cur); cur = 1
        if seq:
            runs.append(cur)
        m[f"{role}_pct_star"] = 100 * seq.count("STAR") / n if n else None
        m[f"{role}_switch_rate"] = 100 * sum(a != b for a, b in zip(seq, seq[1:])) / (n - 1) if n > 1 else None
        m[f"{role}_longest_run"] = max(runs) if runs else None
        accs = {b: [] for b in BASELINES}
        for t in range(n):
            bp = _base(rows[:t], role)
            for b in BASELINES:
                accs[b].append(_credit(bp[b], rows[t][role]))
        for b in BASELINES:
            m[f"{role}_pred_{b}"] = 100 * sum(accs[b]) / n if n else None
        m[f"{role}_pred_best"] = max(m[f"{role}_pred_{b}"] for b in BASELINES) if n else None
    return m


OUTCOMES = ["matcher_win_rate"] + [f"{r}_{k}" for r in ROLES for k in
                                   ("pct_star", "switch_rate", "longest_run", "pred_best", "pred_repeat_last",
                                    "pred_alternate_last", "pred_win_stay_lose_shift")]


def cond_means(meas: List[Dict[str, Any]], outcome: str, sample: Optional[Dict[str, List[Dict]]] = None) -> Dict[str, Optional[float]]:
    by = sample or {c: [x for x in meas if x["condition"] == c] for c in C.COND_ORDER}
    out = {}
    for c in C.COND_ORDER:
        v = [x[outcome] for x in by[c] if x[outcome] is not None]
        out[c] = sum(v) / len(v) if v else None
    return out


def contrasts(cm: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
    if any(cm[c] is None for c in C.COND_ORDER):
        return {k: None for k in ("matcher_informed", "mismatcher_informed", "interaction", "10_vs_11", "01_vs_11", "11_vs_00")}
    return {"matcher_informed": (cm["10"] + cm["11"]) / 2 - (cm["00"] + cm["01"]) / 2,
            "mismatcher_informed": (cm["01"] + cm["11"]) / 2 - (cm["00"] + cm["10"]) / 2,
            "interaction": (cm["11"] - cm["01"]) - (cm["10"] - cm["00"]),
            "10_vs_11": cm["10"] - cm["11"], "01_vs_11": cm["01"] - cm["11"], "11_vs_00": cm["11"] - cm["00"]}


def bootstrap(meas, outcome, n_boot=C.N_BOOT):
    by = {c: [x for x in meas if x["condition"] == c] for c in C.COND_ORDER}
    rng = random.Random(C.derive_seed("bootstrap", outcome))
    reps = defaultdict(list)
    und = 0
    for _ in range(n_boot):
        s = {c: [lst[rng.randrange(len(lst))] for _ in lst] if lst else [] for c, lst in by.items()}
        ct = contrasts(cond_means(meas, outcome, s))
        if any(v is None for v in ct.values()):
            und += 1; continue
        for k, v in ct.items():
            reps[k].append(v)
    ci = {}
    for k, v in reps.items():
        v.sort()
        ci[k] = (v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))])
    return ci, und / n_boot


def manipulation_check(calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agg = defaultdict(lambda: [0, 0, []])
    for r in calls:
        if r.get("kind") != "player" or r["status"] != "completed":
            continue
        txt = (r["response"]["text"] or "").lower()
        hit = any(term in txt for term in C.SELF_REFERENCE_TERMS)
        k = (r["role"], r["informed"])
        agg[k][0] += 1; agg[k][1] += int(hit); agg[k][2].append(r["response"]["usage"].get("completion_tokens") or 0)
    return [{"role": k[0], "informed": k[1], "n": v[0], "pct_mentions_self_or_same_model": 100 * v[1] / v[0],
             "median_completion_tokens": statistics.median(v[2]), "pct_multiline": None} for k, v in sorted(agg.items())]


def _w(path, rows):
    if not rows:
        path.write_text(""); return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def f(x, nd=1, sign=False):
    return "NA" if x is None else (f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}")


def analyze(rd: Path) -> Dict[str, Any]:
    games = [json.loads(l) for l in (rd / "game_logs.jsonl").read_text().splitlines() if l.strip()]
    calls = [json.loads(l) for l in (rd / "calls.jsonl").read_text().splitlines() if l.strip()]
    meas = [game_measures(g) for g in games if g["n_valid_rounds"] > 0]
    _w(rd / "game_measures.csv", meas)
    res = {}
    for o in OUTCOMES:
        cm = cond_means(meas, o)
        ci, und = bootstrap(meas, o)
        res[o] = {"cond_means": cm, "contrasts": contrasts(cm), "ci": ci, "undefined_frac": und}
    mc = manipulation_check(calls)
    for x in mc:
        rs = [r for r in calls if r.get("kind") == "player" and r["status"] == "completed" and r["role"] == x["role"] and r["informed"] == x["informed"]]
        x["pct_multiline"] = 100 * sum(len([l for l in (r["response"]["text"] or "").strip().splitlines() if l.strip()]) > 1 for r in rs) / len(rs) if rs else None
    _w(rd / "manipulation_check.csv", mc)
    summ = [{"outcome": o, "contrast": k, "estimate": v, "ci_lo": res[o]["ci"].get(k, (None, None))[0],
             "ci_hi": res[o]["ci"].get(k, (None, None))[1], "undefined_frac": res[o]["undefined_frac"]}
            for o in OUTCOMES for k, v in res[o]["contrasts"].items()]
    _w(rd / "summary.csv", summ)
    invalid = [{"slot_id": r["slot_id"], "status": r["status"], "reason": (r.get("parse") or {}).get("reason"),
                "text": ((r.get("response") or {}).get("text") or "")[-300:]} for r in calls if not (r.get("parse") or {}).get("valid")]
    _w(rd / "invalids.csv", invalid)
    (rd / "results.json").write_text(json.dumps({"results": res, "manipulation_check": mc}, indent=1, default=str))
    report(rd, games, calls, res, mc, meas)
    files = sorted(p for p in rd.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (rd / "checksums.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    return res


def report(rd, games, calls, res, mc, meas):
    cost = sum(float(r.get("cost_usd") or 0) for r in calls)
    sp = rd / "smoke_calls.jsonl"
    scost = sum(float(json.loads(l).get("cost_usd") or 0) for l in sp.read_text().splitlines() if l.strip()) if sp.exists() else 0.0
    L = ["# Opponent self-identity disclosure: Astra vs Astra matching pennies (pilot report)", "",
         f"Run `{rd.name}`. Protocol {C.PROTOCOL}. Exploratory pilot; game-level bootstrap (8 games per condition); no multiplicity correction.", "",
         "## Completion and cost", "", "| condition (matcher, mismatcher informed) | games complete / 8 | valid rounds |", "|---|---:|---:|"]
    for c in C.COND_ORDER:
        gs = [g for g in games if g["condition"] == c]
        L.append(f"| {c} | {sum(g['status'] == 'complete' for g in gs)} | {sum(g['n_valid_rounds'] for g in gs)} / {8 * C.N_ROUNDS} |")
    pl = [r for r in calls if r.get("kind") == "player"]
    L += ["", f"- Player calls: {len(pl)} recorded, {sum(1 for r in pl if (r.get('parse') or {}).get('valid'))} valid.",
          f"- Charged cost: ${cost:.2f} scientific + ${scost:.2f} technical smoke = ${cost + scost:.2f} (ceiling ${C.BUDGET_CAP_USD:.0f}).",
          "- Incomplete games: " + (", ".join(f"{g['game_id']} ({g['note']})" for g in games if g["status"] != "complete") or "none") + ".", "",
          "## Primary outcome: Matcher win rate (percent of rounds; 50% = equilibrium)", "",
          "| condition | mean Matcher win rate |", "|---|---:|"]
    p = res["matcher_win_rate"]
    for c in C.COND_ORDER:
        L.append(f"| {c} | {f(p['cond_means'][c])} |")
    L += ["", "| contrast (percentage points) | estimate | 95% bootstrap interval |", "|---|---:|---|"]
    labels = {"matcher_informed": "Informing the Matcher: mean(10,11) - mean(00,01)",
              "mismatcher_informed": "Informing the Mismatcher: mean(01,11) - mean(00,10)",
              "interaction": "Interaction: (11-01) - (10-00)", "10_vs_11": "Unilateral Matcher (10) - mutual (11)",
              "01_vs_11": "Unilateral Mismatcher (01) - mutual (11)", "11_vs_00": "Mutual (11) - neither (00)"}
    for k, lab in labels.items():
        ci = p["ci"].get(k, (None, None))
        L.append(f"| {lab} | {f(p['contrasts'][k], 1, True)} | [{f(ci[0], 1, True)}, {f(ci[1], 1, True)}] |")
    L += ["", f"Undefined bootstrap replicates: {p['undefined_frac']:.3f}. A positive Matcher-informed effect means informing the Matcher raised its win rate.", "",
          "## Player behaviour by condition (means over games)", "",
          "| outcome | 00 | 10 | 01 | 11 | own-informed effect | opponent-informed effect |", "|---|---:|---:|---:|---:|---:|---:|"]
    for o in OUTCOMES[1:]:
        r = res[o]; role = o.split("_")[0]
        own = "matcher_informed" if role == "matcher" else "mismatcher_informed"
        opp = "mismatcher_informed" if role == "matcher" else "matcher_informed"
        ci_own, ci_opp = r["ci"].get(own, (None, None)), r["ci"].get(opp, (None, None))
        L.append(f"| {o} | " + " | ".join(f(r["cond_means"][c]) for c in C.COND_ORDER) +
                 f" | {f(r['contrasts'][own], 1, True)} [{f(ci_own[0], 1, True)}, {f(ci_own[1], 1, True)}] | {f(r['contrasts'][opp], 1, True)} [{f(ci_opp[0], 1, True)}, {f(ci_opp[1], 1, True)}] |")
    L += ["", "`pred_*` = percent of a player's choices predicted by a history-only rule (round 1 and ties = half credit); `pred_best` = the best of five rules per game (optimistic exploitability index).", "",
          "## Manipulation check (descriptive)", "", "| role | informed | responses | % mentioning same model / instance / Astra / self | % with reasoning lines | median completion tokens |", "|---|---|---:|---:|---:|---:|"]
    for x in mc:
        L.append(f"| {x['role']} | {x['informed']} | {x['n']} | {f(x['pct_mentions_self_or_same_model'])} | {f(x['pct_multiline'])} | {x['median_completion_tokens']} |")
    L += ["", "## Games", "", "| game | condition | rounds | Matcher wins | matcher %STAR | mismatcher %STAR |", "|---|---|---:|---:|---:|---:|"]
    for m in meas:
        L.append(f"| {m['game_id']} | {m['condition']} | {m['n_rounds']} | {f(m['matcher_win_rate'] * m['n_rounds'] / 100, 0)} | {f(m['matcher_pct_star'])} | {f(m['mismatcher_pct_star'])} |")
    L += ["", "## Limitations", "",
          "- One model (Astra), 8 games per condition, 20 rounds: exploratory. Intervals reflect game-to-game variation only.",
          "- 'Same model' means another independently queried instance; an effect shows the behavioural consequence of the identity sentence, not introspection.",
          "- Astra's endpoint has no temperature control; games ran at provider-default sampling with low hidden reasoning.",
          "- The handoff text ended mid-way through the parsing section. Invalid-answer handling, the analysis plan and the budget are Claude's prespecified defaults (protocol.md), fixed before data.", ""]
    (rd / "report.md").write_text("\n".join(L) + "\n")
