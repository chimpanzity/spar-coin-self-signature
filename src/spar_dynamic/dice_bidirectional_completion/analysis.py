"""Offline analysis for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1 (prespecified in PROTOCOL_FROZEN.md, "Analysis plan").

Inputs: main/<predictor>/{raw_attempts,teacher_forced}.jsonl and Experiment 28's main matched-prefix rows (source reference).
Four fixed deterministic ground-truth strings; triplicates are reproducibility checks. No p-values or CIs anywhere.

Primary metric: conditional face log loss -ln p6(true face) in nats, p6 = the six face log-probs renormalised over the faces
(conditional on emitting a face). Cell summaries weight positions equally within a cell and cells equally across a set.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from spar_dynamic.dice_bidirectional_completion import config as C
from spar_dynamic.dice_bidirectional_completion import prompts as P
from spar_dynamic.dice_crossed_guidance.analysis import _lp, js_bits, max_dp, parse_n, read_jsonl, six

FACES = C.FACES
LN6 = math.log(6)
OTHER = {"qwen": "mistral", "mistral": "qwen"}


def r4(x):
    return None if x is None else round(x, 4)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def load(model: str, d=None) -> dict:
    d = d or C.MAIN / model
    return dict(model=model, raw=read_jsonl(d / "raw_attempts.jsonl"), tf=read_jsonl(d / "teacher_forced.jsonl"))


def floor(data: dict) -> dict:
    dps, jss = [], []
    for r in data["raw"]:
        if r.get("own_rescored_full_pass"):
            for x, y in zip(r["own_rescored"], r["own_rescored_full_pass"]):
                dps.append(max_dp(x["face_logprobs"], y["face_logprobs"]))
                jss.append(js_bits(six(x["face_logprobs"])[0], six(y["face_logprobs"])[0]))
    inc = {(x["cell_id"], x["output_step"]): x["face_logprobs"] for x in data["tf"] if x["method"] == "incremental"}
    for x in data["tf"]:
        if x["method"] == "full_pass":
            a = inc[(x["cell_id"], x["output_step"])]
            dps.append(max_dp(a, x["face_logprobs"]))
            jss.append(js_bits(six(a)[0], six(x["face_logprobs"])[0]))
    return dict(dp=max(dps), js_bits=max(jss), n=len(dps))


def source_reference() -> dict:
    """Experiment 28: each source's own I|I six-face vector at every original position (true prefix in the assistant turn)."""
    out = {}
    for s in C.MODELS:
        for x in read_jsonl(C.EXP28_MAIN / s / "matched_prefix.jsonl"):
            if x["kind"] == "mp" and x["method"] == "incremental" and x["instruction"] == x["history"]:
                out[(s, x["instruction"], x["original_position"])] = six(x["face_logprobs"])[0]
    return out


def positions(data: dict, fl: dict, sref: dict) -> list:
    """One row per teacher-forced missing position (incremental arithmetic)."""
    rows = []
    for x in data["tf"]:
        if x["method"] != "incremental":
            continue
        p, mass = six(x["face_logprobs"])
        lp = _lp(x["face_logprobs"])
        t = x["true_face"]
        order = sorted(FACES, key=lambda f: -p[f - 1])
        margin = p[order[0] - 1] - p[order[1] - 1]
        ref = sref.get((x["source"], x["source_instruction"], x["original_position"]))
        fwd = x["task_type"] == "primary" and x["direction"] == "forward"
        rows.append(dict(cell_id=x["cell_id"], predictor=x["predictor"], source=x["source"], diagonal=x["predictor"] == x["source"],
                         source_instruction=x["source_instruction"], task_type=x["task_type"], direction=x["direction"] or "middle",
                         k=x["k"], output_step=x["output_step"], original_position=x["original_position"],
                         forced_prefix=x["forced_prefix"], true_face=t, p6=[r4(v) for v in p], raw_mass=r4(mass),
                         p_true=p[t - 1], p_true_full_vocab=math.exp(lp[t - 1]), cond_loss=-math.log(p[t - 1]),
                         full_loss=-lp[t - 1], argmax=order[0], margin=margin, near_tie=margin < fl["dp"],
                         top_correct=order[0] == t and margin >= fl["dp"], top_correct_or_tie=p[t - 1] >= p[order[0] - 1] - fl["dp"],
                         entropy_bits=-sum(v * math.log2(v) for v in p if v > 0),
                         source_ref_js=js_bits(p, ref) if (ref and fwd) else None,
                         source_ref_js_descriptive=js_bits(p, ref) if (ref and not fwd) else None))
    return rows


def free_by_cell(data: dict) -> dict:
    out = {}
    for r in data["raw"]:
        if r["kind"] != "cell":
            continue
        o = out.setdefault(r["cell_id"], dict(outputs=Counter(), n=0, n_valid=0, first_token_mass=None, first_token_top=None, rec=None))
        o["n"] += 1
        ok = bool(parse_n(r["content"], r["n_expected"])) and r["finish_reason"] == "stop"
        o["n_valid"] += ok
        o["outputs"][r["content"]] += 1
        if o["rec"] is None or r["replicate"] < o["rec"]["replicate"]:
            o["rec"] = r
    for o in out.values():
        r = o["rec"]
        if r["steps"]:
            p, m = six(r["steps"][0]["face_logprobs"])
            o["first_token_mass"], o["first_token_top"] = m, 1 + max(range(6), key=lambda i: p[i])
        o["first_token_is_face"] = bool(r["steps"]) and bool(r["digit_steps"]) and r["steps"][0]["token_id"] == r["digit_steps"][0]["token_id"]
    return out


def cells(pos: list, free: dict) -> list:
    by = defaultdict(list)
    for x in pos:
        by[x["cell_id"]].append(x)
    meta = P.by_cell()
    out = []
    for cid, xs in by.items():
        xs.sort(key=lambda x: x["output_step"])
        c, f = meta[cid], free.get(cid)
        modal = f["outputs"].most_common(1)[0][0] if f else None
        faces = parse_n(modal, c["n_missing"]) if (f and f["n_valid"] == f["n"]) else None
        truth = c["missing_values"]
        out.append(dict(cell_id=cid, predictor=c["predictor"], source=c["source"], diagonal=c["diagonal"], source_instruction=c["source_instruction"],
                        task_type=c["task_type"], direction=c["direction"] or "middle", k=c["k"], n_missing=c["n_missing"],
                        first_loss=xs[0]["cond_loss"], mean_loss=mean(x["cond_loss"] for x in xs), mean_full_loss=mean(x["full_loss"] for x in xs),
                        first_p_true=xs[0]["p_true"], mean_p_true=mean(x["p_true"] for x in xs),
                        first_raw_mass=xs[0]["raw_mass"], mean_raw_mass=mean(x["raw_mass"] for x in xs), min_raw_mass=min(x["raw_mass"] for x in xs),
                        top_correct=sum(x["top_correct"] for x in xs), top_correct_or_tie=sum(x["top_correct_or_tie"] for x in xs),
                        near_ties=sum(x["near_tie"] for x in xs), mean_entropy_bits=mean(x["entropy_bits"] for x in xs),
                        mean_source_ref_js=mean(x["source_ref_js"] for x in xs),
                        free_valid=f"{f['n_valid']}/{f['n']}" if f else None, free_all_valid=bool(f) and f["n_valid"] == f["n"],
                        free_distinct_outputs=len(f["outputs"]) if f else None, free_output=(modal or "")[:80],
                        free_digit_correct=sum(a == b for a, b in zip(faces, truth)) if faces else None,
                        free_exact=faces == truth if faces else None, free_first_token_mass=f["first_token_mass"] if f else None,
                        free_first_equals_tf_argmax=(faces[0] == xs[0]["argmax"]) if faces else None,
                        target=c["target"], revealed=" ".join(map(str, c["revealed_values"]))))
    return sorted(out, key=lambda r: (r["predictor"], r["source"], r["source_instruction"], r["direction"], r["k"] or 0))


def contrast(L: dict) -> dict:
    """Balanced diagonal contrast on a 2x2 loss matrix L[(predictor, source)]; positive = self cells have lower loss."""
    q, m = "qwen", "mistral"
    sa = (L[(q, m)] + L[(m, q)] - L[(q, q)] - L[(m, m)]) / 2
    return dict(matrix={f"{p}<-{s}": r4(v) for (p, s), v in L.items()}, self_advantage=r4(sa),
                qwen_self_minus_other=r4(L[(q, q)] - L[(q, m)]), mistral_self_minus_other=r4(L[(m, m)] - L[(m, q)]),
                row_qwen=r4((L[(q, q)] + L[(q, m)]) / 2), row_mistral=r4((L[(m, q)] + L[(m, m)]) / 2),
                col_qwen_source=r4((L[(q, q)] + L[(m, q)]) / 2), col_mistral_source=r4((L[(q, m)] + L[(m, m)]) / 2))


def crossed(cl: list, metric: str) -> list:
    """2x2 per (instruction, direction, k) for the primary grid."""
    by = defaultdict(dict)
    for c in cl:
        if c["task_type"] == "primary":
            by[(c["source_instruction"], c["direction"], c["k"])][(c["predictor"], c["source"])] = c[metric]
    return [dict(source_instruction=i, direction=d, k=k, metric=metric, **contrast(L)) for (i, d, k), L in sorted(by.items())]


def crossed_averaged(cl: list, metric: str) -> list:
    """2x2 per (instruction, direction) averaged over k with equal weight per condition (descriptive)."""
    by = defaultdict(lambda: defaultdict(list))
    for c in cl:
        if c["task_type"] == "primary":
            by[(c["source_instruction"], c["direction"])][(c["predictor"], c["source"])].append(c[metric])
    return [dict(source_instruction=i, direction=d, metric=metric, k_levels=9, **contrast({k: mean(v) for k, v in L.items()}))
            for (i, d), L in sorted(by.items())]


def middle(pos: list) -> dict:
    """Supplementary arm: early pair (positions 1, 2), late pair (9, 10) and the four-position mean, with 2x2 contrasts per G/F."""
    rows = [x for x in pos if x["task_type"] == "middle"]
    parts = {"early_1_2": (1, 2), "late_9_10": (9, 10), "all_four": (1, 2, 9, 10)}
    table, contrasts = [], []
    for part, keep in parts.items():
        L = defaultdict(dict)
        for cid in sorted({x["cell_id"] for x in rows}):
            xs = [x for x in rows if x["cell_id"] == cid and x["original_position"] in keep]
            x0 = xs[0]
            v = dict(part=part, cell_id=cid, predictor=x0["predictor"], source=x0["source"], source_instruction=x0["source_instruction"],
                     mean_cond_loss=mean(x["cond_loss"] for x in xs), first_digit_loss=xs[0]["cond_loss"],
                     top_correct=sum(x["top_correct"] for x in xs), top_correct_or_tie=sum(x["top_correct_or_tie"] for x in xs),
                     mean_raw_mass=mean(x["raw_mass"] for x in xs), n=len(xs))
            table.append(v)
            L[x0["source_instruction"]][(x0["predictor"], x0["source"])] = v["mean_cond_loss"]
        contrasts += [dict(part=part, source_instruction=i, **contrast(m)) for i, m in sorted(L.items())]
    return dict(table=table, contrasts=contrasts)


def hypotheses(cl: list) -> dict:
    prim = [c for c in cl if c["task_type"] == "primary"]
    out = {}
    # H1: forward boundary next-roll loss by k
    h1 = defaultdict(dict)
    for c in prim:
        if c["direction"] == "forward":
            h1[f"{c['predictor']}<-{c['source']}:{c['source_instruction']}"][c["k"]] = r4(c["first_loss"])
    out["H1_forward_boundary_loss_by_k"] = dict(h1)
    out["H1_forward_boundary_mean_k1_3_vs_k7_9"] = {key: dict(k1_3=r4(mean(v[k] for k in (1, 2, 3))), k7_9=r4(mean(v[k] for k in (7, 8, 9))))
                                                    for key, v in h1.items()}
    # H3: forward vs backward, same (P, S, I, k), mean span loss and first missing output digit
    by = {(c["predictor"], c["source"], c["source_instruction"], c["direction"], c["k"]): c for c in prim}
    h3 = []
    for (p, s, i, d, k), c in by.items():
        if d == "forward":
            b = by[(p, s, i, "backward", k)]
            h3.append(dict(predictor=p, source=s, source_instruction=i, k=k, fwd_mean_loss=r4(c["mean_loss"]), bwd_mean_loss=r4(b["mean_loss"]),
                           bwd_minus_fwd_mean=r4(b["mean_loss"] - c["mean_loss"]), fwd_first_loss=r4(c["first_loss"]),
                           bwd_first_loss=r4(b["first_loss"]), bwd_minus_fwd_first=r4(b["first_loss"] - c["first_loss"])))
    out["H3_backward_minus_forward"] = sorted(h3, key=lambda r: (r["predictor"], r["source"], r["source_instruction"], r["k"]))
    out["H3_mean_bwd_minus_fwd"] = {f"{p}<-{s}:{i}": r4(mean(r["bwd_minus_fwd_mean"] for r in h3 if (r["predictor"], r["source"], r["source_instruction"]) == (p, s, i)))
                                    for p in C.MODELS for s in C.MODELS for i in C.INSTRUCTIONS}
    # H4: free behaviour vs teacher-forced probabilities
    h4 = {}
    for p in C.MODELS:
        mine = [c for c in cl if c["predictor"] == p]
        valid = [c for c in mine if c["free_all_valid"]]
        h4[p] = dict(cells=len(mine), cells_free_valid=len(valid),
                     free_digit_accuracy=r4(sum(c["free_digit_correct"] for c in valid) / sum(c["n_missing"] for c in valid)) if valid else None,
                     tf_top_correct_rate=r4(sum(c["top_correct"] for c in mine) / sum(c["n_missing"] for c in mine)),
                     tf_mean_p_true=r4(mean(c["mean_p_true"] for c in mine)),
                     free_first_digit_equals_tf_argmax=f"{sum(bool(c['free_first_equals_tf_argmax']) for c in valid)}/{len(valid)}",
                     free_exact_spans=sum(bool(c["free_exact"]) for c in valid),
                     mean_first_token_mass_invalid=r4(mean(c["free_first_token_mass"] for c in mine if not c["free_all_valid"])))
    out["H4_free_vs_teacher_forced"] = h4
    return out


def analyse(datas: dict) -> dict:
    sref = source_reference()
    fl = {m: floor(d) for m, d in datas.items()}
    pos = [x for m, d in datas.items() for x in positions(d, fl[m], sref)]
    free = {k: v for d in datas.values() for k, v in free_by_cell(d).items()}
    cl = cells(pos, free)
    return dict(floor=fl, positions=pos, cells=cl,
                crossed_mean=crossed(cl, "mean_loss"), crossed_first=crossed(cl, "first_loss"),
                crossed_avg_mean=crossed_averaged(cl, "mean_loss"), crossed_avg_first=crossed_averaged(cl, "first_loss"),
                middle=middle(pos), hypotheses=hypotheses(cl), uniform_loss=LN6)
