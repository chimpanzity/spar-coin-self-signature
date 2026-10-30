"""Order-corrected A/B scores (handoff 4.3) and the frozen gates (handoff 5 and 6). Pure Python, no GPU.

For candidate X (calibration: the correct sample; recognition: the Qwen sample) and the other sample Y:
  d_XY = log P(A) - log P(B) with A = X, B = Y   (orientation XA)
  d_YX = log P(A) - log P(B) with A = Y, B = X   (orientation XB)
  S_X = (d_XY - d_YX) / 2        order-corrected preference for X; a constant A/B logit bias cancels
  B_pair = (d_XY + d_YX) / 2     residual label/order bias
  pref_X_as_A = d_XY, pref_X_as_B = -d_YX   per-orientation preferences for X
sigmoid(S_X) is a display scale only, not a likelihood of authorship. |S_X| <= epsilon is `indeterminate`.
"""

from __future__ import annotations

import collections
import math

from spar_dynamic.dice_recognition_logprob import config as C


def epsilon_from_delta(delta: float) -> float:
    return max(C.EPSILON_FLOOR, C.EPSILON_MULTIPLIER * delta)


def outcome(s: float, eps: float) -> str:
    return "X" if s > eps else "Y" if s < -eps else "indeterminate"


def pair_score(d_xy: float, d_yx: float, eps: float) -> dict:
    s = 0.5 * (d_xy - d_yx)
    pa, pb = d_xy, -d_yx
    return dict(d_XY=d_xy, d_YX=d_yx, S_X=s, B_pair=0.5 * (d_xy + d_yx), sigmoid_S=1 / (1 + math.exp(-s)),
                pref_X_as_A=pa, pref_X_as_B=pb, outcome=outcome(s, eps),
                both_orders_X=pa > eps and pb > eps, both_orders_Y=pa < -eps and pb < -eps,
                orientation_sensitive=not ((pa > eps and pb > eps) or (pa < -eps and pb < -eps)))


def unit_key(r: dict) -> tuple:
    return (r["kind"], r["unit_id"], r.get("name_order"))


def pair_records(records: list, eps: float) -> list:
    """Join the XA and XB records of each unit (kind, unit_id, name_order) into one paired row."""
    by = collections.defaultdict(dict)
    for r in records:
        k = unit_key(r)
        if r["orientation"] in by[k]:
            raise ValueError(f"duplicate orientation {r['orientation']} for {k}")
        by[k][r["orientation"]] = r
    rows = []
    for (kind, uid, no), o in sorted(by.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        if set(o) != {"XA", "XB"}:
            raise ValueError(f"{kind} {uid} {no}: missing orientation, have {sorted(o)}")
        xa, xb = o["XA"], o["XB"]
        rows.append(dict(unit_id=uid, kind=kind, name_order=no, X=xa["A"], Y=xa["B"],
                         **pair_score(xa["d"], xb["d"], eps),
                         mass_AB_XA=xa["mass_AB"], mass_AB_XB=xb["mass_AB"],
                         argmax_XA=xa["argmax_token"], argmax_XB=xb["argmax_token"],
                         greedy_picks_X_XA=xa["argmax_token"] == "A", greedy_picks_X_XB=xb["argmax_token"] == "B"))
    return rows


def calibration_gate(rows: list, eps: float) -> dict:
    """Frozen Stage A rule (handoff 6). Ties (|S| <= eps) never count as correct."""
    if len(rows) != C.N_PER_TASK * len(C.TASKS):
        raise ValueError(f"calibration gate needs {C.N_PER_TASK * len(C.TASKS)} paired items, got {len(rows)}")
    per = {}
    for t in C.TASKS:
        rs = [r for r in rows if r["kind"] == t]
        per[t] = dict(n=len(rs), correct=sum(r["outcome"] == "X" for r in rs), wrong=sum(r["outcome"] == "Y" for r in rs),
                      indeterminate=sum(r["outcome"] == "indeterminate" for r in rs),
                      both_orders_correct=sum(r["both_orders_X"] for r in rs), min_correct=C.GATE_TASK[t])
        per[t]["pass"] = per[t]["correct"] >= C.GATE_TASK[t]
    total = sum(p["correct"] for p in per.values())
    both = sum(p["both_orders_correct"] for p in per.values())
    crit = collections.OrderedDict()
    crit[f"S_correct > eps in >= {C.GATE_TOTAL}/36"] = total >= C.GATE_TOTAL
    for t in C.TASKS:
        crit[f"{t} >= {C.GATE_TASK[t]}/12"] = per[t]["pass"]
    crit[f"both orders correct in >= {C.GATE_BOTH_ORDERS}/36"] = both >= C.GATE_BOTH_ORDERS
    return dict(stage="calibration", epsilon=eps, total_correct=total, both_orders_correct=both, per_task=per,
                criteria=crit, overall="PASS" if all(crit.values()) else "FAIL")


def preflight_gate(records: list, env: dict) -> dict:
    """Stage 0 technical gates (handoff 5). records: raw_preflight.jsonl rows."""
    pairs = collections.defaultdict(dict)
    for r in records:
        if r["kind"] != "GENERIC":
            pairs[r["unit_id"]][r["orientation"]] = r
    deltas, d_gaps = {}, {}
    for uid, o in pairs.items():
        if set(o) == {"XA", "XB"}:
            s_p = 0.5 * (o["XA"]["d"] - o["XB"]["d"])
            s_t = 0.5 * (o["XA"]["diagnostic"]["d"] - o["XB"]["diagnostic"]["d"])
            deltas[uid] = dict(S_prefill=s_p, S_tokenwise=s_t, abs_diff=abs(s_p - s_t))
    for r in records:
        d_gaps[r["trial_id"]] = abs(r["d"] - r["diagnostic"]["d"])
    delta = max((v["abs_diff"] for v in deltas.values()), default=float("nan"))
    eps = epsilon_from_delta(delta) if deltas else float("nan")
    rep = next((r for r in records if r.get("determinism_repeats")), None)
    spread = (max(rep["determinism_repeats"] + [rep["d"]]) - min(rep["determinism_repeats"] + [rep["d"]])) if rep else float("nan")
    first_ab = sum(r["greedy_first_token"] in C.LABELS for r in records)
    tc = [r["template_checks"] for r in records]
    g = collections.OrderedDict()
    g["serving_recorded_and_revision_pinned"] = bool(env.get("revision_match")) and bool(env.get("gpu"))
    g["non_thinking_template_no_system_one_user_turn"] = all(c["ends_with_empty_think"] and not c["has_system_turn"]
                                                            and c["n_user_turns"] == 1 for c in tc) \
        and not any("<think" in r["greedy_text"] for r in records)
    g["labels_single_tokens_in_answer_context"] = all(all(c["label_appends_single_token"].values()) for c in tc)
    g[f"greedy_first_token_A_or_B_{C.GREEDY_MIN_AB}_of_{len(records)}"] = first_ab >= C.GREEDY_MIN_AB
    g["two_complete_pairs"] = len(deltas) == 2
    g[f"determinism_spread_lt_{C.DETERMINISM_TOL}"] = spread < C.DETERMINISM_TOL
    g[f"epsilon_lt_{C.EPSILON_STOP}"] = eps < C.EPSILON_STOP
    return dict(stage="preflight", overall="PASS" if all(g.values()) else "FAIL", gates=g, delta=delta, epsilon=eps,
                epsilon_rule=f"max({C.EPSILON_FLOOR}, {C.EPSILON_MULTIPLIER} * delta)", delta_by_pair=deltas,
                abs_d_gap_by_prompt=d_gaps, determinism_spread=spread, greedy_first_token_AB=first_ab,
                greedy=[dict(trial_id=r["trial_id"], greedy_text=r["greedy_text"], argmax=r["argmax_token"],
                             greedy_matches_argmax=r["greedy_first_token"] == r["argmax_token"], d=r["d"],
                             mass_AB=r["mass_AB"]) for r in records])
