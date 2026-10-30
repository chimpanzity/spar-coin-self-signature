"""Single-sample Yes/No scores and the frozen gates. Pure Python, no GPU.

For each prompt, z = log P(Yes) - log P(No) at the first answer token. For a unit with candidates X and Y:
  c_pos = z(X, pos) - z(Y, pos)      preference for X under the pos question (Yes favours X)
  c_neg = z(Y, neg) - z(X, neg)      preference for X under the neg question (Yes favours Y)
  S = (c_pos + c_neg) / 2            polarity-averaged preference for X
  yes_bias_pos, yes_bias_neg         mean z of the two sequences under each question; never enters c_pos or c_neg
  coherence = [z(X,pos) - z(X,neg) + z(Y,pos) - z(Y,neg)] / 2   does the model answer the two polarities differently?
A Yes/No response bias that is constant within a question cancels exactly in c_pos and c_neg: there is no position or
label to prefer, because each prompt shows one sequence. |S| <= epsilon is `indeterminate` and never counts as correct.
"""

from __future__ import annotations

import collections

from spar_dynamic.dice_recognition_logprob.scoring import epsilon_from_delta as _eps24, outcome
from spar_dynamic.dice_recognition_yesno import config as C


def epsilon_from_delta(delta: float) -> float:
    assert (C.EPSILON_FLOOR, C.EPSILON_MULTIPLIER) == (0.05, 2.0)       # same rule as v2.1
    return _eps24(delta)


def unit_score(z: dict, eps: float) -> dict:
    """z: {(role, polarity): z} for the four prompts of a unit."""
    c_pos = z["X", "pos"] - z["Y", "pos"]
    c_neg = z["Y", "neg"] - z["X", "neg"]
    s = 0.5 * (c_pos + c_neg)
    return dict(z_X_pos=z["X", "pos"], z_Y_pos=z["Y", "pos"], z_X_neg=z["X", "neg"], z_Y_neg=z["Y", "neg"],
                c_pos=c_pos, c_neg=c_neg, S=s, outcome=outcome(s, eps),
                yes_bias_pos=0.5 * (z["X", "pos"] + z["Y", "pos"]), yes_bias_neg=0.5 * (z["X", "neg"] + z["Y", "neg"]),
                coherence=0.5 * (z["X", "pos"] - z["X", "neg"] + z["Y", "pos"] - z["Y", "neg"]),
                both_polarities_X=c_pos > eps and c_neg > eps, both_polarities_Y=c_pos < -eps and c_neg < -eps,
                polarity_sensitive=not ((c_pos > eps and c_neg > eps) or (c_pos < -eps and c_neg < -eps)))


def unit_records(records: list, eps: float) -> list:
    """Join the four prompts of each (kind, unit_id) into one row."""
    by = collections.defaultdict(dict)
    for r in records:
        k = (r["kind"], r["unit_id"])
        rp = (r["role"], r["polarity"])
        if rp in by[k]:
            raise ValueError(f"duplicate {rp} for {k}")
        by[k][rp] = r
    rows = []
    for (kind, uid), o in sorted(by.items()):
        want = {(r, p) for r in C.ROLES for p in C.POLARITIES}
        if set(o) != want:
            raise ValueError(f"{kind} {uid}: have {sorted(o)}, need all of X/Y x pos/neg")
        x = o["X", "pos"]
        rows.append(dict(unit_id=uid, kind=kind, X=x["X"], Y=x["Y"], **unit_score({k: v["z"] for k, v in o.items()}, eps),
                         mass_YN_min=min(v["mass_YN"] for v in o.values()),
                         argmax=" ".join(o[k]["argmax_token"].strip() or repr(o[k]["argmax_token"]) for k in sorted(o)),
                         greedy_yes_X_pos=o["X", "pos"]["argmax_token"] == "Yes", greedy_yes_Y_pos=o["Y", "pos"]["argmax_token"] == "Yes",
                         greedy_yes_X_neg=o["X", "neg"]["argmax_token"] == "Yes", greedy_yes_Y_neg=o["Y", "neg"]["argmax_token"] == "Yes"))
    return rows


def calibration_gate(rows: list, eps: float) -> dict:
    if len(rows) != C.N_PER_TASK * len(C.TASKS):
        raise ValueError(f"calibration gate needs {C.N_PER_TASK * len(C.TASKS)} items, got {len(rows)}")
    per = {}
    for t in C.TASKS:
        rs = [r for r in rows if r["kind"] == t]
        per[t] = dict(n=len(rs), correct=sum(r["outcome"] == "X" for r in rs), wrong=sum(r["outcome"] == "Y" for r in rs),
                      indeterminate=sum(r["outcome"] == "indeterminate" for r in rs),
                      both_polarities_correct=sum(r["both_polarities_X"] for r in rs), min_correct=C.GATE_TASK[t])
        per[t]["pass"] = per[t]["correct"] >= C.GATE_TASK[t]
    total = sum(p["correct"] for p in per.values())
    both = sum(p["both_polarities_correct"] for p in per.values())
    crit = collections.OrderedDict()
    crit[f"S > eps in >= {C.GATE_TOTAL}/36"] = total >= C.GATE_TOTAL
    for t in C.TASKS:
        crit[f"{t} >= {C.GATE_TASK[t]}/12"] = per[t]["pass"]
    crit[f"both polarities correct in >= {C.GATE_BOTH_POLARITIES}/36"] = both >= C.GATE_BOTH_POLARITIES
    return dict(stage="calibration", epsilon=eps, total_correct=total, both_polarities_correct=both, per_task=per,
                criteria=crit, overall="PASS" if all(crit.values()) else "FAIL")


def preflight_gate(records: list, env: dict) -> dict:
    """Stage 0 technical gates. delta = max |c_prefill - c_tokenwise| over the two preflight items (pos polarity)."""
    by = collections.defaultdict(dict)
    for r in records:
        if r["kind"] != "GENERIC":
            by[r["unit_id"]][r["role"]] = r
    deltas = {}
    for uid, o in by.items():
        if set(o) == {"X", "Y"}:
            c_p = o["X"]["z"] - o["Y"]["z"]
            c_t = o["X"]["diagnostic"]["z"] - o["Y"]["diagnostic"]["z"]
            deltas[uid] = dict(c_prefill=c_p, c_tokenwise=c_t, abs_diff=abs(c_p - c_t))
    delta = max((v["abs_diff"] for v in deltas.values()), default=float("nan"))
    eps = epsilon_from_delta(delta) if deltas else float("nan")
    rep = next((r for r in records if r.get("determinism_repeats")), None)
    spread = (max(rep["determinism_repeats"] + [rep["z"]]) - min(rep["determinism_repeats"] + [rep["z"]])) if rep else float("nan")
    first_yn = sum(r["greedy_first_token"] in C.LABELS for r in records)
    tc = [r["template_checks"] for r in records]
    g = collections.OrderedDict()
    g["serving_recorded_and_revision_pinned"] = bool(env.get("revision_match")) and bool(env.get("gpu"))
    g["non_thinking_template_no_system_one_user_turn"] = all(c["ends_with_empty_think"] and not c["has_system_turn"]
                                                            and c["n_user_turns"] == 1 for c in tc) \
        and not any("<think" in r["greedy_text"] for r in records)
    g["labels_single_tokens_in_answer_context"] = all(all(c["label_appends_single_token"].values()) for c in tc)
    g[f"greedy_first_token_Yes_or_No_{C.GREEDY_MIN_YN}_of_{len(records)}"] = first_yn >= C.GREEDY_MIN_YN
    g["two_complete_contrasts"] = len(deltas) == 2
    g[f"determinism_spread_lt_{C.DETERMINISM_TOL}"] = spread < C.DETERMINISM_TOL
    g[f"epsilon_lt_{C.EPSILON_STOP}"] = eps < C.EPSILON_STOP
    return dict(stage="preflight", overall="PASS" if all(g.values()) else "FAIL", gates=g, delta=delta, epsilon=eps,
                epsilon_rule=f"max({C.EPSILON_FLOOR}, {C.EPSILON_MULTIPLIER} * delta)", delta_by_item=deltas,
                abs_z_gap_by_prompt={r["trial_id"]: abs(r["z"] - r["diagnostic"]["z"]) for r in records},
                determinism_spread=spread, greedy_first_token_YN=first_yn,
                greedy=[dict(trial_id=r["trial_id"], greedy_text=r["greedy_text"], argmax=r["argmax_token"],
                             greedy_matches_argmax=r["greedy_first_token"] == r["argmax_token"], z=r["z"],
                             mass_YN=r["mass_YN"]) for r in records])
