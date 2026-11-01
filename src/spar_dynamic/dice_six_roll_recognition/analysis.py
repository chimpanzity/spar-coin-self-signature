"""Offline analysis for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0 (handoff section 6). Descriptive only: eight unique content
comparisons, deterministic cells; no p-values, intervals or population claims.

Recognition: per presentation d = log P(A) - log P(B); authentic-oriented s = d (authentic in A) or -d (authentic in B);
S = (s1 + s2) / 2 per (judge, frame, item); order-consistent classes at the judge's frozen epsilon.
Crossed diagonal advantage per (frame, foil, instruction): D = 0.5 [(S_QQ - S_MQ) + (S_MM - S_QM)], S_judge,source.
Policy benchmark: L(u, v) = ln p6(u | prefix4) + ln p6(v | prefix4, u) under each scorer and the source's instruction;
Delta = L(authentic) - L(foil); P(authentic | two) = logistic(Delta).
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from spar_dynamic.dice_crossed_guidance.analysis import _lp, read_jsonl
from spar_dynamic.dice_six_roll_recognition import config as C
from spar_dynamic.dice_six_roll_recognition import gates as Gt
from spar_dynamic.dice_six_roll_recognition import stimuli as S

Q, M = "qwen", "mistral"


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x)) if x >= 0 else math.exp(x) / (1.0 + math.exp(x))


def log_p6(face_logprobs: dict) -> list:
    """Face-only log-probabilities, renormalised over the six faces in log space (no underflow)."""
    lp = _lp(face_logprobs)
    m = max(lp)
    z = m + math.log(sum(math.exp(v - m) for v in lp))
    return [v - z for v in lp]


# ---------- policy benchmark ----------

def policy(rows_by_scorer: dict) -> dict:
    lik, deltas = [], []
    for scorer, rows in rows_by_scorer.items():
        v = {(x["source_id"], x["candidate"], x["position"]): x["face_logprobs"] for x in rows if x["method"] == "incremental"}
        for (s, i), fx in S.fixtures().items():
            sid = S.source_id(s, i)
            L = {}
            for cand in ("authentic", "swap", "repeat"):
                u, w = fx[cand][4], fx[cand][5]
                f5, f6 = v[(sid, cand, 5)], v[(sid, cand, 6)]
                n5, n6 = log_p6(f5)[u - 1], log_p6(f6)[w - 1]
                r5, r6 = _lp(f5)[u - 1], _lp(f6)[w - 1]
                L[cand] = dict(n5=n5, n6=n6, r5=r5, r6=r6)
                lik.append(dict(scorer=scorer, source_id=sid, source=s, source_instruction=i, diagonal=scorer == s, candidate=cand,
                                ending=f"{u} {w}", sequence6=S.seq(fx[cand]), logp5_face_only=n5, logp6_face_only=n6, L_face_only=n5 + n6,
                                logp5_raw=r5, logp6_raw=r6, L_raw=r5 + r6, raw_mass5=sum(math.exp(z) for z in _lp(f5)),
                                raw_mass6=sum(math.exp(z) for z in _lp(f6))))
            for foil in C.FOILS:
                a, f = L["authentic"], L[foil]
                dl = (a["n5"] + a["n6"]) - (f["n5"] + f["n6"])
                deltas.append(dict(scorer=scorer, source_id=sid, source=s, source_instruction=i, foil_type=foil, item_id=f"{sid}-{foil}",
                                   scorer_is_source=scorer == s, delta=dl, delta_pos5=a["n5"] - f["n5"], delta_pos6=a["n6"] - f["n6"],
                                   delta_raw=(a["r5"] + a["r6"]) - (f["r5"] + f["r6"]), p_authentic_of_two=logistic(dl)))
    return dict(likelihoods=lik, deltas=deltas)


# ---------- recognition ----------

def presentations(recs_by_judge: dict) -> list:
    out = []
    for j, recs in recs_by_judge.items():
        for r in recs:
            if r["replicate"] != 1:
                continue
            s = r["d"] if r["orientation"] == 1 else -r["d"]
            out.append(dict(judge=j, frame=r["frame"], item_id=r["item_id"], source=r["source"], source_instruction=r["source_instruction"],
                            foil_type=r["foil_type"], orientation=r["orientation"], diagonal=j == r["source"], seq_A=r["seq_A"],
                            seq_B=r["seq_B"], authentic_label=r["authentic_label"], logp_A=r["logp_A"], logp_B=r["logp_B"], d=r["d"],
                            s_authentic=s, pA=r["pA"], mass_AB=r["mass_AB"], low_mass=r["mass_AB"] < C.LOW_MASS_FLAG,
                            greedy_text=r["greedy_text"], strict_valid=r["strict_valid"],
                            greedy_chose_authentic=(r["greedy_letter"] == r["authentic_label"]) if r["greedy_letter"] else None,
                            argmax_token=r["argmax_token"], d_tokenwise=r.get("d_tokenwise"), abs_delta_d=r.get("abs_delta_d"),
                            prompt_id=r["prompt_id"], prompt_sha256=r["prompt_sha256"]))
    return out


def paired(pres: list, eps: dict, deltas: list) -> list:
    dl = {(x["scorer"], x["item_id"]): x["delta"] for x in deltas}
    by = {}
    for p in pres:
        by.setdefault((p["judge"], p["frame"], p["item_id"]), {})[p["orientation"]] = p
    out = []
    for (j, frame, item), o in sorted(by.items()):
        a, b = o[1], o[2]
        s1, s2 = a["s_authentic"], b["s_authentic"]
        g = [a["greedy_chose_authentic"], b["greedy_chose_authentic"]]
        out.append(dict(judge=j, frame=frame, item_id=item, source=a["source"], source_instruction=a["source_instruction"],
                        foil_type=a["foil_type"], diagonal=a["diagonal"], s1=s1, s2=s2, S=(s1 + s2) / 2, abs_s1_minus_s2=abs(s1 - s2),
                        label_bias=(a["d"] + b["d"]) / 2, epsilon=eps[j], cls=Gt.classify(s1, s2, eps[j]),
                        greedy_authentic_both_orders=all(x is True for x in g), greedy_letters=[a["greedy_text"], b["greedy_text"]],
                        mean_mass_AB=(a["mass_AB"] + b["mass_AB"]) / 2, low_mass=a["low_mass"] or b["low_mass"],
                        source_model_delta=dl.get((a["source"], item)), judge_model_delta=dl.get((j, item))))
    return out


def crossed(pairs: list) -> list:
    """D per (frame, foil, instruction) from the 2x2 S[judge, source]; then D_self - D_neutral."""
    S_ = {(p["frame"], p["foil_type"], p["source_instruction"], p["judge"], p["source"]): p["S"] for p in pairs}
    out = []
    for frame in C.FRAMES:
        for foil in C.FOILS:
            for i in C.INSTRUCTIONS:
                k = lambda j, s: S_.get((frame, foil, i, j, s))
                m = {f"S_{j[0].upper()}{s[0].upper()}": k(j, s) for j in C.MODELS for s in C.MODELS}
                ok = all(v is not None for v in m.values())
                D = 0.5 * ((m["S_QQ"] - m["S_MQ"]) + (m["S_MM"] - m["S_QM"])) if ok else None
                out.append(dict(frame=frame, foil_type=foil, source_instruction=i, contrast=f"D_{i}", **m, D=D,
                                qwen_self_minus_other=(m["S_QQ"] - m["S_MQ"]) if ok else None,
                                mistral_self_minus_other=(m["S_MM"] - m["S_QM"]) if ok else None,
                                judge_main_effect_Q_minus_M=0.5 * ((m["S_QQ"] + m["S_QM"]) - (m["S_MQ"] + m["S_MM"])) if ok else None,
                                source_main_effect_Q_minus_M=0.5 * ((m["S_QQ"] + m["S_MQ"]) - (m["S_QM"] + m["S_MM"])) if ok else None,
                                available=ok))
    by = {(r["frame"], r["foil_type"], r["source_instruction"]): r["D"] for r in out}
    for foil in C.FOILS:
        for i in C.INSTRUCTIONS:
            a, b = by[("self", foil, i)], by[("neutral", foil, i)]
            out.append(dict(frame="self_minus_neutral", foil_type=foil, source_instruction=i, contrast=f"D_{i}_self - D_{i}_neutral",
                            D=(a - b) if a is not None and b is not None else None, available=a is not None and b is not None))
    return out


def self_vs_neutral_items(pairs: list) -> list:
    by = {(p["judge"], p["item_id"], p["frame"]): p for p in pairs}
    out = []
    for (j, item, frame), p in sorted(by.items()):
        if frame != "self" or (j, item, "neutral") not in by:
            continue
        n = by[(j, item, "neutral")]
        out.append(dict(judge=j, item_id=item, diagonal=p["diagonal"], foil_type=p["foil_type"], S_self=p["S"], S_neutral=n["S"],
                        S_self_minus_neutral=p["S"] - n["S"], cls_self=p["cls"], cls_neutral=n["cls"]))
    return out


def summaries(pairs: list) -> list:
    out = []
    for j in sorted({p["judge"] for p in pairs}):
        for frame in C.FRAMES:
            for foil in C.FOILS:
                ps = [p for p in pairs if p["judge"] == j and p["frame"] == frame and p["foil_type"] == foil]
                if not ps:
                    continue
                out.append(dict(judge=j, frame=frame, foil_type=foil, n_items=len(ps), mean_S=statistics.mean(p["S"] for p in ps),
                                n_consistent_authentic=sum(p["cls"] == "consistent_target" for p in ps),
                                n_consistent_foil=sum(p["cls"] == "consistent_foil" for p in ps),
                                n_mixed_or_tied=sum(p["cls"] == "mixed_or_tied" for p in ps),
                                n_greedy_authentic_both=sum(p["greedy_authentic_both_orders"] for p in ps),
                                mean_label_bias=statistics.mean(p["label_bias"] for p in ps),
                                mean_abs_s1_minus_s2=statistics.mean(p["abs_s1_minus_s2"] for p in ps)))
    return out


# ---------- loading ----------

def judge_status(root=None) -> dict:
    """Per judge: the last stage reached and whether its recognition data are analysable."""
    out = {}
    for j in C.MODELS:
        st = {}
        for stage, name in (("preflight", "preflight_gates"), ("calibration", "calibration_gate"), ("main", "main_checks")):
            p = Path(root or C.EXP) / stage / j / f"{name}.json"
            st[stage] = json.load(open(p, encoding="utf-8"))["overall"] if p.exists() else "NOT_RUN"
        st["recognition"] = "ANALYSABLE" if all(st[s] == "PASS" for s in ("preflight", "calibration", "main")) else "NOT INTERPRETABLE / NOT RUN"
        out[j] = st
    return out


def analyse(root=None) -> dict:
    root = Path(root or C.EXP)
    status = judge_status(root)
    pol_rows = {m: read_jsonl(root / "policy_benchmark" / m / "policy_teacher_forced.jsonl") for m in C.MODELS
                if (root / "policy_benchmark" / m / "policy_teacher_forced.jsonl").exists() and status[m]["preflight"] == "PASS"}
    pol = policy(pol_rows)
    ok = [j for j in C.MODELS if status[j]["recognition"] == "ANALYSABLE"]
    eps = {j: json.load(open(root / "calibration" / j / "calibration_gate.json", encoding="utf-8"))["epsilon"] for j in ok}
    recs = {j: read_jsonl(root / "main" / j / Gt.S_RAW) for j in ok}
    pres = presentations(recs)
    pairs = paired(pres, eps, pol["deltas"])
    mass = {j: statistics.median(p["mass_AB"] for p in pres if p["judge"] == j) for j in ok}
    for j in ok:
        status[j]["median_main_mass_AB"] = mass[j]
        status[j]["answer_probability_interpretation"] = "rejected (median A+B mass below threshold)" \
            if mass[j] < C.MIN_MEDIAN_MASS_MAIN else "usable"
    return dict(status=status, epsilon=eps, policy=pol, presentations=pres, pairs=pairs,
                crossed=crossed(pairs) if len(ok) == 2 else [], self_vs_neutral=self_vs_neutral_items(pairs),
                summaries=summaries(pairs))
