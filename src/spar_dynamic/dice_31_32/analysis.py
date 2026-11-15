"""Offline analysis for Experiments 31 and 32 (descriptive; no p-values, no population claims).

Conventions. Six-face conditional probabilities p1..p6 = exp(logp_f) / sum over the six bare face tokens (the digit mass is
reported beside them, never confused with them). Log loss = -ln p(authentic face) in nats, primary. JS divergence in bits.
Rank 1 = the scorer's most probable face (ties share the better rank). Primary values come from the first incremental replicate.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

from spar_dynamic.dice_31_32 import config as C
from spar_dynamic.dice_31_32 import stimuli as S
from spar_dynamic.dice_crossed_guidance.analysis import js_bits, read_jsonl, six

FACES = [str(f) for f in C.FACES]


def r4(x):
    return None if x is None else round(float(x), 4)


def mn(xs):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else None


def dist(face_logprobs: dict) -> dict:
    """Normalised six-face probabilities, raw mass, top face, margin, near-tie flag."""
    p, mass = six(face_logprobs)
    order = sorted(range(6), key=lambda k: -p[k])
    return dict(p=p, mass=mass, top=int(FACES[order[0]]), margin=p[order[0]] - p[order[1]],
                near_tie=p[order[0]] - p[order[1]] < C.NEAR_TIE_P)


def rank_of(p, face) -> int:
    return 1 + sum(1 for v in p if v > p[face - 1])


# ---------- Experiment 31 ----------

def load31(root=None) -> dict:
    root = Path(root or C.EXP31)
    return {m: dict(streams=read_jsonl(root / "raw" / m / "streams.jsonl"), archival=read_jsonl(root / "raw" / m / "archival.jsonl"))
            for m in C.MODELS if (root / "raw" / m / "streams.jsonl").exists()}


def _streams(data, method="incremental", rep=1) -> dict:
    return {s["stream_id"]: s for m in data.values() for s in m["streams"] if s["method"] == method and s["replicate"] == rep}


def archive_index() -> dict:
    """Equivalent archival records (handoff 31.2): Experiment 28 within-model matched-prefix rows (scorer = source, any scorer
    instruction x source instruction; same pins, prompt, forced history and incremental arithmetic) and Experiment 30
    policy-benchmark authentic six-roll rows (both scorers, scorer instruction = source instruction, positions 1-6)."""
    idx = {}
    for m in C.MODELS:
        p28 = C.EXP28_MAIN / m / "matched_prefix.jsonl"
        for n, r in enumerate(read_jsonl(p28), 1):
            if r["method"] == "incremental":
                key = f"{m}|{r['instruction']}|{m}-{r['history']}|{r['position']}"
                idx.setdefault(key, []).append(dict(experiment=28, path=str(p28.relative_to(C.EXP28.parent)), line=n,
                                                    face_logprobs=r["face_logprobs"]))
        p30 = C.EXP30_POLICY / m / "policy_teacher_forced.jsonl"
        if p30.exists():
            for n, r in enumerate(read_jsonl(p30), 1):
                if r["method"] == "incremental" and r["candidate"] == "authentic":
                    key = f"{m}|{r['source_instruction']}|{r['source_id']}|{r['position']}"
                    idx.setdefault(key, []).append(dict(experiment=30, path=str(p30.relative_to(C.EXP28.parent)), line=n,
                                                        face_logprobs=r["face_logprobs"]))
    return idx


def rows31(data) -> list:
    inc, inc2, fp = _streams(data), _streams(data, rep=2), _streams(data, "full_pass")
    arch = archive_index()
    out = []
    for lab in S.labeled_rows31():
        st = inc.get(lab["stream_id"])
        if st is None:
            continue
        pos = st["positions"][lab["position"] - 1]
        assert pos["position"] == lab["position"] and pos["authentic_face"] == lab["authentic_face"] and pos["forced_prefix"] == lab["forced_prefix"]
        d = dist(pos["face_logprobs"])
        a = lab["authentic_face"]
        p2 = inc2[lab["stream_id"]]["positions"][lab["position"] - 1]["face_logprobs"]
        pf = fp[lab["stream_id"]]["positions"][lab["position"] - 1]["face_logprobs"]
        x = C.REFERENCES[(lab["source_model"], lab["source_mode"])]
        rule, rem = S.remaining_faces(x, lab["position"])
        h = dict(heuristic_rule=rule, remaining=" ".join(map(str, rem)) if rem is not None else None,
                 n_remaining=len(rem) if rem is not None else None)
        if rem is not None:
            prem = sum(d["p"][f - 1] for f in rem)
            inside = a in rem
            h.update(p_on_remaining=prem, authentic_in_remaining=inside,
                     p_authentic_renorm_remaining=(d["p"][a - 1] / prem) if inside and prem > 0 else None,
                     heuristic_uniform_logloss=math.log(len(rem)) if inside else None,
                     heuristic_status=("uninformative_one_left" if len(rem) == 1 else "unconstrained_six_left" if len(rem) == 6
                                       else "discriminating" if inside else "authentic_outside_remaining"))
        else:
            h.update(p_on_remaining=None, authentic_in_remaining=None, p_authentic_renorm_remaining=None, heuristic_uniform_logloss=None,
                     heuristic_status=rule)
        key = f"{lab['scorer_model']}|{lab['scorer_mode']}|{lab['source_id']}|{lab['position']}"
        eq = arch.get(key, [])
        out.append(dict(lab, **{f"logp_raw_{f}": pos["face_logprobs"][f] for f in FACES}, **{f"p{f}": d["p"][k] for k, f in enumerate(FACES)},
                        digit_mass=d["mass"], top_face=d["top"], top_margin=d["margin"], near_tie=d["near_tie"],
                        authentic_rank=rank_of(d["p"], a), p_authentic=d["p"][a - 1], logloss=-math.log(d["p"][a - 1]),
                        raw_logp_authentic=pos["face_logprobs"][str(a)], top_matches_authentic=d["top"] == a,
                        argmax_token=pos["argmax_token"], argmax_is_face=pos["argmax_token_id"] in pos["face_token_ids"].values(),
                        separator_logprob=pos["separator_logprob"], forced_prefix_text=pos["forced_prefix_text"],
                        rep2_identical=p2 == pos["face_logprobs"],
                        floor_max_dp=max(abs(math.exp(pos["face_logprobs"][f]) - math.exp(pf[f])) for f in FACES),
                        provenance="computed_fresh", archival_equivalents=[f"exp{e['experiment']}:{e['path']}:{e['line']}" for e in eq],
                        archival_max_abs_dlogp=max((abs(e["face_logprobs"][f] - pos["face_logprobs"][f]) for e in eq for f in FACES), default=None),
                        **h))
    return out


def context_check(rows) -> dict:
    """Identical scorer + instruction + forced prefix => identical scores (handoff test 4)."""
    by = defaultdict(list)
    for r in rows:
        by[r["context_key"]].append(r)
    bad = [k for k, rs in by.items() if len({tuple(r[f"logp_raw_{f}"] for f in FACES) for r in rs}) > 1]
    return dict(labeled_rows=len(rows), unique_contexts=len(by), shared_contexts=sum(len(v) > 1 for v in by.values()),
                max_rows_per_context=max(len(v) for v in by.values()) if by else 0, mismatched_contexts=bad)


def _ll(rows, **kw):
    sel = [r for r in rows if all(r[k] == v for k, v in kw.items())]
    return mn([r["logloss"] for r in sel if r["position"] >= 2]), mn([r["logloss"] for r in sel if r["position"] == 1]), len(sel)


def crossed31(rows) -> list:
    """Comparison A: per source trajectory x scorer instruction, both scorers on identical authentic targets (positions 2-10;
    position 1 separately). own_minus_other < 0 means the source's own model assigns the authentic faces more probability."""
    out = []
    for s in C.MODELS:
        for i in C.INSTRUCTIONS:
            for sm in C.INSTRUCTIONS:
                other = [m for m in C.MODELS if m != s][0]
                own, own1, n = _ll(rows, source_model=s, source_mode=i, scorer_mode=sm, scorer_model=s)
                oth, oth1, _ = _ll(rows, source_model=s, source_mode=i, scorer_mode=sm, scorer_model=other)
                if n == 0:
                    continue
                out.append(dict(source_id=S.source_id(s, i), source_model=s, source_mode=i, scorer_mode=sm,
                                own_scorer=s, other_scorer=other, logloss_own_2_10=r4(own), logloss_other_2_10=r4(oth),
                                own_minus_other_2_10=r4(own - oth) if None not in (own, oth) else None,
                                logloss_own_pos1=r4(own1), logloss_other_pos1=r4(oth1),
                                own_cell_kind=S.replay_kind(s, sm, s, i), own_cell_is_replay=sm == i))
    return out


def reciprocal31(cr) -> list:
    """Balanced crossed contrast per (source instruction, scorer instruction): mean over the two source models of
    (other scorer - own scorer) log loss, positions 2-10. Positive = own-model likelihood advantage."""
    out = []
    for i in C.INSTRUCTIONS:
        for sm in C.INSTRUCTIONS:
            xs = [c for c in cr if c["source_mode"] == i and c["scorer_mode"] == sm]
            if len(xs) == 2 and all(c["own_minus_other_2_10"] is not None for c in xs):
                out.append(dict(source_mode=i, scorer_mode=sm, own_advantage_nats=r4(-mean(c["own_minus_other_2_10"] for c in xs)),
                                qwen_source_other_minus_own=r4(-next(c for c in xs if c["source_model"] == "qwen")["own_minus_other_2_10"]),
                                mistral_source_other_minus_own=r4(-next(c for c in xs if c["source_model"] == "mistral")["own_minus_other_2_10"]),
                                includes_replay_cells=sm == i))
    return out


def js31(rows) -> dict:
    """Comparison B: matched-context JS between the two scorers, and within a scorer between its G and F instruction."""
    by = {(r["scorer_model"], r["scorer_mode"], r["source_id"], r["position"]): r for r in rows}
    vec = lambda r: [r[f"p{f}"] for f in FACES]   # noqa: E731
    between, within = [], []
    for sid in [S.source_id(s, i) for s in C.MODELS for i in C.INSTRUCTIONS]:
        for j in C.POSITIONS:
            for sm in C.INSTRUCTIONS:
                q, m = by.get(("qwen", sm, sid, j)), by.get(("mistral", sm, sid, j))
                if q and m:
                    between.append(dict(source_id=sid, scorer_mode=sm, position=j, js_bits=js_bits(vec(q), vec(m)), top_qwen=q["top_face"],
                                        top_mistral=m["top_face"], top_agree=q["top_face"] == m["top_face"],
                                        mass_qwen=q["digit_mass"], mass_mistral=m["digit_mass"]))
            for sc in C.MODELS:
                g, f = by.get((sc, "G", sid, j)), by.get((sc, "F", sid, j))
                if g and f:
                    within.append(dict(scorer_model=sc, source_id=sid, position=j, js_bits_G_vs_F=js_bits(vec(g), vec(f)),
                                       top_G=g["top_face"], top_F=f["top_face"], top_same=g["top_face"] == f["top_face"],
                                       authentic_rank_G=g["authentic_rank"], authentic_rank_F=f["authentic_rank"],
                                       rank_change=f["authentic_rank"] - g["authentic_rank"], mass_G=g["digit_mass"], mass_F=f["digit_mass"]))

    def summ(xs, key, by_keys):
        out = []
        groups = defaultdict(list)
        for x in xs:
            groups[tuple(x[k] for k in by_keys)].append(x)
        for k, v in sorted(groups.items()):
            out.append(dict(zip(by_keys, k), js_pos1=r4(mn([x[key] for x in v if x["position"] == 1])),
                            js_mean_2_10=r4(mn([x[key] for x in v if x["position"] >= 2])), js_max_2_10=r4(max(x[key] for x in v if x["position"] >= 2)),
                            top_agree_2_10=sum(x.get("top_agree", x.get("top_same")) for x in v if x["position"] >= 2), n_2_10=sum(x["position"] >= 2 for x in v)))
        return out
    return dict(between=between, within=within, between_summary=summ(between, "js_bits", ("source_id", "scorer_mode")),
                within_summary=summ(within, "js_bits_G_vs_F", ("scorer_model", "source_id")))


def heuristic31(rows) -> list:
    """Comparison D: by scorer x source x scorer instruction, over discriminating rows only (2-5 eligible faces, authentic among
    them), model log loss vs the uniform-over-remaining heuristic, and the mass the model puts on the remaining faces."""
    out = []
    groups = defaultdict(list)
    for r in rows:
        groups[(r["scorer_model"], r["source_id"], r["scorer_mode"])].append(r)
    for (sc, sid, sm), v in sorted(groups.items()):
        disc = [r for r in v if r["heuristic_status"] == "discriminating"]
        out.append(dict(scorer_model=sc, source_id=sid, scorer_mode=sm, cross_model=not sid.startswith(sc),
                        n_discriminating=len(disc), positions_discriminating=" ".join(str(r["position"]) for r in disc),
                        n_uninformative_one_left=sum(r["heuristic_status"] == "uninformative_one_left" for r in v),
                        n_unconstrained=sum(r["heuristic_status"] in ("unconstrained_six_left", "opening") for r in v),
                        model_logloss_discriminating=r4(mn([r["logloss"] for r in disc])),
                        heuristic_logloss_discriminating=r4(mn([r["heuristic_uniform_logloss"] for r in disc])),
                        model_minus_heuristic=r4(mn([r["logloss"] - r["heuristic_uniform_logloss"] for r in disc])),
                        mean_p_on_remaining_discriminating=r4(mn([r["p_on_remaining"] for r in disc])),
                        mean_p_auth_renorm_discriminating=r4(mn([r["p_authentic_renorm_remaining"] for r in disc])),
                        model_logloss_uninformative=r4(mn([r["logloss"] for r in v if r["heuristic_status"] == "uninformative_one_left"]))))
    return out


def own_vs_other_discriminating(rows) -> list:
    """Comparison A restricted to the heuristic's discriminating positions (where generic exhaustion does not fix the answer)."""
    out = []
    for s in C.MODELS:
        other = [m for m in C.MODELS if m != s][0]
        for i in C.INSTRUCTIONS:
            for sm in C.INSTRUCTIONS:
                sel = lambda sc: [r for r in rows if r["source_model"] == s and r["source_mode"] == i and r["scorer_mode"] == sm  # noqa: E731
                                  and r["scorer_model"] == sc and r["heuristic_status"] == "discriminating"]
                a, b = mn([r["logloss"] for r in sel(s)]), mn([r["logloss"] for r in sel(other)])
                if a is not None:
                    out.append(dict(source_id=S.source_id(s, i), scorer_mode=sm, n=len(sel(s)), logloss_own=r4(a), logloss_other=r4(b),
                                    own_minus_other=r4(a - b), own_cell_is_replay=sm == i))
    return out


def analyse31(root=None) -> dict:
    data = load31(root)
    rows = rows31(data)
    cr = crossed31(rows)
    return dict(rows=rows, context=context_check(rows), crossed=cr, reciprocal=reciprocal31(cr), js=js31(rows),
                heuristic=heuristic31(rows), own_vs_other_discriminating=own_vs_other_discriminating(rows),
                integrity=dict(n_rows=len(rows), rep2_all_identical=all(r["rep2_identical"] for r in rows),
                               floor_max_dp=r4(max((r["floor_max_dp"] for r in rows), default=None)),
                               archival_rows=sum(bool(r["archival_equivalents"]) for r in rows),
                               archival_max_abs_dlogp=max((r["archival_max_abs_dlogp"] for r in rows if r["archival_max_abs_dlogp"] is not None), default=None),
                               near_ties=sum(r["near_tie"] for r in rows), min_digit_mass=r4(min((r["digit_mass"] for r in rows), default=None)),
                               argmax_not_face=sum(not r["argmax_is_face"] for r in rows)))


# ---------- Experiment 32 ----------

def load32(root=None) -> dict:
    root = Path(root or C.EXP32)
    return {m: read_jsonl(root / "raw" / m / "cells.jsonl") for m in C.MODELS if (root / "raw" / m / "cells.jsonl").exists()}


def _p7(face_logprobs, a7):
    d = dist(face_logprobs)
    return dict(p_true7=d["p"][a7 - 1], raw_p_true7=math.exp(face_logprobs[str(a7)]), logloss_true7=-math.log(d["p"][a7 - 1]),
                top7=d["top"], rank_true7=rank_of(d["p"], a7), digit_mass7=d["mass"], near_tie7=d["near_tie"],
                **{f"p7_{f}": d["p"][k] for k, f in enumerate(FACES)})


def _det(g) -> dict:
    """A generation record without its wall-clock latency (the deterministic part)."""
    return {k: v for k, v in g.items() if k != "latency_ms"}


def cells32(data) -> list:
    out = []
    for c in S.cells32():
        recs = [r for r in data.get(c["predictor"], []) if r["prompt_id"] == c["prompt_id"]]
        if not recs:
            continue
        r1 = next(r for r in recs if r["replicate"] == 1)
        r2 = next((r for r in recs if r["replicate"] == 2), None)
        fb = r1["first_boundary"]
        row = dict({k: v for k, v in c.items() if k != "prompt"}, free_text=r1["free"]["content"], finish_reason=r1["free"]["finish_reason"],
                   completion_tokens=r1["free"]["completion_tokens"], free_strict_valid=r1["free_strict_valid"],
                   first_boundary_argmax=fb["argmax_token"], first_boundary_mass=dist(fb["face_logprobs"])["mass"],
                   first_boundary_separator_logprob=fb["separator_logprob"], first_boundary_eos_logprob=max(fb["eos_logprobs"].values()),
                   replicates_identical=r2 is not None and _det(r2["free"]) == _det(r1["free"]) and r2["first_boundary"] == fb
                   and r2.get("constrained_roll7") == r1.get("constrained_roll7"),
                   first_boundary_matches_generation=r1["first_boundary_matches_generation"],
                   floor_max_dp_first=max(abs(math.exp(fb["face_logprobs"][f]) - math.exp(r1["first_boundary_full_pass"]["face_logprobs"][f])) for f in FACES))
        a6, a7 = c["authentic_sixth"], c["authentic_seventh"]
        if c["condition"] == "A":
            d6 = dist(fb["face_logprobs"])
            fr7 = r1.get("free_roll7")
            row.update(p_true6=d6["p"][a6 - 1], logloss_true6=-math.log(d6["p"][a6 - 1]), top6=d6["top"], digit_mass6=d6["mass"],
                       generated_sixth=fr7["generated_sixth"] if fr7 else None,
                       sixth_reconstructed=(fr7["generated_sixth"] == a6) if fr7 else None,
                       free_roll7_defined=fr7 is not None, constrained_forced_sixth=r1["constrained_roll7"]["forced_sixth"],
                       constrained_sixth_correct=r1["constrained_roll7"]["forced_sixth"] == a6,
                       constrained_equals_free=r1.get("constrained_equals_free"))
            if fr7:
                row.update(_p7(fr7["face_logprobs"], a7), roll7_readout="free (after generated sixth + separator)")
            else:
                row.update({k: None for k in ("p_true7", "raw_p_true7", "logloss_true7", "top7", "rank_true7", "digit_mass7")},
                           roll7_readout="free undefined (no digit + separator); see constrained")
            row.update({f"constrained_{k}": v for k, v in _p7(r1["constrained_roll7"]["face_logprobs"], a7).items()
                        if k in ("p_true7", "raw_p_true7", "logloss_true7", "top7", "rank_true7", "digit_mass7")})
            row["floor_max_dp_constrained"] = max(abs(math.exp(r1["constrained_roll7"]["face_logprobs"][f]) -
                                                     math.exp(r1["constrained_roll7_full_pass"]["face_logprobs"][f])) for f in FACES)
        else:
            row.update(_p7(fb["face_logprobs"], a7), roll7_readout="first answer token")
            row.update(free_answer_correct=row["free_strict_valid"] and row["free_text"] == str(a7))
        out.append(row)
    return out


def contrasts32(cells) -> list:
    """A-B, C-B, C-A per predictor x source on p(true seventh), with log-loss differences. A uses the free readout when defined;
    the constrained-digit A readout is reported separately and labelled."""
    out = []
    by = {(c["predictor"], c["source_id"], c["condition"]): c for c in cells}
    for p in C.MODELS:
        for s, i in C.SOURCES32:
            sid = S.source_id(s, i)
            a, b, cc = by.get((p, sid, "A")), by.get((p, sid, "B")), by.get((p, sid, "C"))
            if not (a and b and cc):
                continue
            pa, pac = a["p_true7"], a["constrained_p_true7"]
            d = lambda x, y: None if x is None or y is None else r4(x - y)  # noqa: E731
            out.append(dict(predictor=p, source_id=sid, own_source=p == s, p_true7_A=r4(pa), p_true7_A_constrained=r4(pac),
                            p_true7_B=r4(b["p_true7"]), p_true7_C=r4(cc["p_true7"]),
                            A_minus_B=d(pa, b["p_true7"]), C_minus_B=d(cc["p_true7"], b["p_true7"]), C_minus_A=d(cc["p_true7"], pa),
                            A_constrained_minus_B=d(pac, b["p_true7"]), C_minus_A_constrained=d(cc["p_true7"], pac),
                            logloss_A=r4(a["logloss_true7"]), logloss_B=r4(b["logloss_true7"]), logloss_C=r4(cc["logloss_true7"]),
                            A_sixth_generated=a["generated_sixth"], A_sixth_reconstructed=a["sixth_reconstructed"],
                            digit_mass7_A=r4(a["digit_mass7"]), digit_mass7_B=r4(b["digit_mass7"]), digit_mass7_C=r4(cc["digit_mass7"]),
                            free_valid_A=a["free_strict_valid"], free_valid_B=b["free_strict_valid"], free_valid_C=cc["free_strict_valid"]))
    return out


def analyse32(root=None) -> dict:
    cells = cells32(load32(root))
    return dict(cells=cells, contrasts=contrasts32(cells),
                integrity=dict(n_cells=len(cells), replicates_identical=all(c["replicates_identical"] for c in cells),
                               first_boundary_matches_generation=all(c["first_boundary_matches_generation"] for c in cells),
                               floor_max_dp=r4(max((max(c["floor_max_dp_first"], c.get("floor_max_dp_constrained", 0)) for c in cells), default=None)),
                               free_valid=sum(c["free_strict_valid"] for c in cells),
                               constrained_equals_free_when_defined=all(c["constrained_equals_free"] for c in cells
                                                                        if c["condition"] == "A" and c["free_roll7_defined"])))
