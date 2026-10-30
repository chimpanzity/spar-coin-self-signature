"""Gates, tidy tables and figures for SPAR_DICE_PREFIX_DECLARATIVE_v1.0 (offline; reads the GPU records)."""

from __future__ import annotations

import json
import math
from pathlib import Path

from spar_dynamic.dice_prefix_declarative import config as C
from spar_dynamic.dice_prefix_declarative import prompts as P

FACES = C.FACES
CONTRASTS = (("N", "H"), ("S", "H"), ("S", "N"), ("O", "H"), ("S", "O"))


def read_jsonl(path) -> list:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


# ---------- distributions ----------

def six(face_logprobs: dict) -> tuple[list, float]:
    """Six-face distribution renormalised over the faces, and the raw full-vocabulary mass on them."""
    lp = [face_logprobs["bare"][str(f)] for f in FACES]
    m = max(lp)
    w = [math.exp(v - m) for v in lp]
    z = sum(w)
    return [x / z for x in w], sum(math.exp(v) for v in lp)


def js_bits(p: list, q: list) -> float:
    m = [(a + b) / 2 for a, b in zip(p, q)]
    kl = lambda a, b: sum(x * math.log2(x / y) for x, y in zip(a, b) if x > 0)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def tv(p: list, q: list) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def max_dp(a: dict, b: dict) -> float:
    return max(abs(x - y) for x, y in zip(six(a)[0], six(b)[0]))


def rank_of(p: list, face: int) -> int:
    return 1 + sum(1 for x in p if x > p[face - 1])


def near_tie(p: list, floor: float) -> bool:
    s = sorted(p, reverse=True)
    return s[0] - s[1] < floor


def parse_three(text: str) -> list | None:
    toks = text.strip().split(" ")
    if len(toks) != 3 or not all(t in {str(f) for f in FACES} for t in toks):
        return None
    return [int(t) for t in toks]


# ---------- archive ----------

def archive() -> dict:
    """Experiment 21 main run: generation steps of the first G and F record, and the matched-prefix rows."""
    raw = read_jsonl(C.EXP21 / "raw_attempts.jsonl")
    gen = {}
    for cond in ("G", "F"):
        r = next(r for r in raw if r["condition"] == cond)
        gen[cond] = [s["face_logprobs_exact"] for s in r["raw_logprobs_content"] if s["token"].strip().isdigit()]
    mp = {(r["instruction"], r["history"], r["method"], r["position"]): r["face_logprobs_exact"]
          for r in read_jsonl(C.EXP21 / "matched_prefix.jsonl")}
    return dict(gen=gen, mp=mp)


# ---------- preflight ----------

def _gate(ok: bool, detail) -> dict:
    return dict(status="PASS" if ok else "FAIL", detail=detail)


def common_checks(d: Path, mode: str, arc: dict) -> tuple[dict, dict]:
    env = json.load(open(d / f"env_{mode}.json", encoding="utf-8"))
    raw = read_jsonl(d / "raw_attempts.jsonl")
    tf = read_jsonl(d / "teacher_forced.jsonl")
    fp = read_jsonl(d / "teacher_forced_full_pass.jsonl")
    ref = read_jsonl(d / "reference.jsonl")
    g = {}
    exp_prompts = {**{c["condition"]: c["prompt_sha256"] for c in P.conditions()},
                   **{k: v["prompt_sha256"] for k, v in P.references().items()}}
    g["serving"] = _gate(env["model_commit"] == C.REVISION and env["chat_template_sha256"] == C.CHAT_TEMPLATE_SHA256
                         and env["rendered_sha256"]["G"] == C.G_RENDERED_SHA256
                         and all(env["prompt_sha256"][k] == v for k, v in exp_prompts.items())
                         and all(r["prompt_sha256"] == exp_prompts[r["condition"]] for r in raw),
                         dict(model_commit=env["model_commit"], chat_template_sha256=env["chat_template_sha256"],
                              rendered_G=env["rendered_sha256"]["G"], gpu=env["gpu"], torch=env["torch"],
                              transformers=env["transformers"], cuda=env["cuda"]))
    g["non_thinking"] = _gate(all(env["rendered_ends_with_empty_think"].values())
                              and not any(env["rendered_has_system_turn"].values())
                              and not any("think" in r["raw_choice_content"] for r in raw),
                              "every rendered prompt ends with the empty think block; no system turn; no think text in outputs")
    face_ids = {str(f): 15 + f for f in FACES}
    space = env["g_full_token_ids"][1]
    tok_ok = env["face_bare_ids"] == face_ids and env["g_full_token_ids"] == \
        [x for f in C.G_REF for x in (face_ids[str(f)], space)][:-1] and \
        all(v == [x for f in C.G_REF[int(k):int(k) + 3] for x in (face_ids[str(f)], space)][:-1]
            for k, v in env["g_window_token_ids"].items())
    g["face_tokens"] = _gate(tok_ok, dict(face_bare_ids=env["face_bare_ids"], separator_id=space,
                                          note="each digit is one bare token, separated by one space token"))
    allsteps = [s["face_logprobs_exact"] for s in tf] + [s["face_logprobs_exact"] for r in raw for s in r["free_digits"]]
    masses = [six(s)[1] for s in allsteps]
    finite = all(math.isfinite(v) for s in allsteps for v in s["bare"].values())
    g["face_logprobs"] = _gate(finite and min(masses) >= C.MIN_FACE_MASS,
                               dict(n_steps=len(allsteps), min_six_face_mass=round(min(masses), 6)))
    worst = 0.0
    for r in raw:
        for a, b in zip(r["free_digits"], r["own_output_rescored"]):
            worst = max(worst, max(abs(a["face_logprobs_exact"]["bare"][f] - b["face_logprobs_exact"]["bare"][f]) for f in a["face_logprobs_exact"]["bare"]))
        if len(r["free_digits"]) != len(r["own_output_rescored"]):
            worst = float("inf")
    g["scorer_matches_generation"] = _gate(worst <= C.SCORER_TOL_LOGP, dict(max_abs_logprob_diff=worst, tol=C.SCORER_TOL_LOGP))
    # reference reproduction against Experiment 21
    seq_ok, dps = True, []
    for r in raw:
        if r["condition"] in ("G", "F"):
            want = C.G_REF if r["condition"] == "G" else C.F_REF
            seq_ok &= r["raw_choice_content"] == " ".join(map(str, want))
            dps += [max_dp(a["face_logprobs_exact"], b) for a, b in zip(r["free_digits"], arc["gen"][r["condition"]])]
    for x in ref:
        if x["method"] == "incremental":
            dps.append(max_dp(x["face_logprobs_exact"], arc["mp"][(x["instruction"], x["history"], "incremental", x["position"])]))
    n_gf = sum(r["condition"] in ("G", "F") for r in raw)
    g["reference_reproduction"] = _gate((seq_ok and max(dps) <= C.REPRO_TOL_P) if dps else True,
                                        dict(sequences_identical=bool(seq_ok), n_G_F_runs=n_gf,
                                             max_abs_dp_vs_archive=max(dps) if dps else None, tol=C.REPRO_TOL_P))
    # numerical floor: incremental vs full pass on the same contexts
    inc = {(t["condition"], t["original_position"]): t["face_logprobs_exact"] for t in tf if t["replicate"] == 1}
    fl = [max_dp(inc[(t["condition"], t["original_position"])], t["face_logprobs_exact"]) for t in fp if (t["condition"], t["original_position"]) in inc]
    refi = {(x["instruction"], x["history"], x["position"]): x["face_logprobs_exact"] for x in ref if x["method"] == "incremental"}
    fl += [max_dp(refi[(x["instruction"], x["history"], x["position"])], x["face_logprobs_exact"]) for x in ref if x["method"] == "full_pass"]
    delta = max(fl)
    numerics = dict(delta_incremental_vs_full_pass=delta, n_compared=len(fl),
                    near_tie_floor=max(C.ARCHIVED_FLOOR_P, delta), archived_floor=C.ARCHIVED_FLOOR_P)
    return g, dict(env=env, raw=raw, tf=tf, fp=fp, ref=ref, numerics=numerics)


def preflight_gates(d: Path) -> dict:
    arc = archive()
    g, data = common_checks(d, "preflight", arc)
    raw = data["raw"]
    det = {}
    for cond in ("G", "F"):
        rs = [r for r in raw if r["condition"] == cond]
        det[cond] = max(abs(a["face_logprobs_exact"]["bare"][f] - b["face_logprobs_exact"]["bare"][f])
                        for r in rs[1:] for a, b in zip(r["free_digits"], rs[0]["free_digits"]) for f in a["face_logprobs_exact"]["bare"])
    g["determinism"] = _gate(all(v == 0.0 for v in det.values()), dict(max_spread_logprob=det))
    arms = {r["condition"]: r["raw_choice_content"] for r in raw if r["arm"] in C.ARMS}
    g["k3_outputs_valid"] = _gate(len(arms) == 4 and all(parse_three(v) for v in arms.values()), arms)
    n_tf = len([t for t in data["tf"] if t["k"] == C.PREFLIGHT_ARMS_K])
    g["k3_teacher_forced_complete"] = _gate(n_tf == 4 * C.WINDOW, dict(n_rows=n_tf))
    return dict(tag=C.TAG, preflight_run_id=raw[0]["run_id"], gates=g, numerics=data["numerics"],
                overall="PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL")


# ---------- main ----------

def main_checks(d: Path) -> tuple[dict, dict]:
    arc = archive()
    g, data = common_checks(d, "main", arc)
    raw = data["raw"]
    n_expected = len(P.conditions()) * C.REPEATS
    g["complete"] = _gate(len(raw) == n_expected and len(data["tf"]) == n_expected * C.WINDOW,
                          dict(n_records=len(raw), n_teacher_forced=len(data["tf"]), expected=n_expected))
    spread = 0.0
    by = {}
    for t in data["tf"]:
        by.setdefault((t["condition"], t["original_position"]), []).append(t["face_logprobs_exact"])
    for v in by.values():
        spread = max(spread, max(max_dp(v[0], x) for x in v))
    outs = {}
    for r in raw:
        outs.setdefault(r["condition"], set()).add(r["raw_choice_content"])
    data["repeat_spread"] = dict(max_dp_teacher_forced=spread, conditions_with_varying_free_output=sorted(k for k, v in outs.items() if len(v) > 1))
    return g, data


def g_ref(data: dict) -> dict:
    """G_j: six-face distribution of direct generation at original position j given the true G prefix (this run)."""
    return {x["position"]: six(x["face_logprobs_exact"])[0] for x in data["ref"]
            if x["instruction"] == "G" and x["history"] == "G" and x["method"] == "incremental"}


def tidy(data: dict) -> dict:
    floor = data["numerics"]["near_tie_floor"]
    G = g_ref(data)
    F_at_G = {x["position"]: six(x["face_logprobs_exact"])[0] for x in data["ref"]
              if x["instruction"] == "F" and x["history"] == "G" and x["method"] == "incremental"}
    rows = []
    for t in data["tf"]:
        if t["replicate"] != 1:
            continue
        j = t["original_position"]
        truth = C.G_REF[j - 1]
        p, mass = six(t["face_logprobs_exact"])
        rows.append(dict(condition=t["condition"], arm=t["arm"], k=t["k"], position=j, window_index=j - t["k"], true_face=truth,
                         **{f"p{f}": p[f - 1] for f in FACES}, **{f"G_p{f}": G[j][f - 1] for f in FACES},
                         p_true=p[truth - 1], logp_true_six=math.log(p[truth - 1]),
                         logp_true_raw=t["face_logprobs_exact"]["bare"][str(truth)], six_face_mass=mass,
                         js_bits=js_bits(p, G[j]), tv=tv(p, G[j]), rank_true=rank_of(p, truth),
                         top_face=1 + p.index(max(p)), top_is_true=p.index(max(p)) + 1 == truth,
                         near_tie=near_tie(p, floor), G_top=1 + G[j].index(max(G[j])), G_p_true=G[j][truth - 1]))
    idx = {(r["arm"], r["k"], r["position"]): r for r in rows}
    contrasts = []
    for k in C.KS:
        for j in range(k + 1, k + C.WINDOW + 1):
            for a, b in CONTRASTS:
                ra, rb = idx[(a, k, j)], idx[(b, k, j)]
                dpt = ra["p_true"] - rb["p_true"]
                contrasts.append(dict(k=k, position=j, contrast=f"{a}-{b}", d_p_true=dpt,
                                      d_logp_true=ra["logp_true_six"] - rb["logp_true_six"],
                                      d_js_bits=ra["js_bits"] - rb["js_bits"], within_floor=abs(dpt) < floor))
    window = []
    for c in P.conditions():
        rs = [idx[(c["arm"], c["k"], j)] for j in c["positions"]]
        window.append(dict(condition=c["condition"], arm=c["arm"], k=c["k"],
                           sum_logp_true_six=sum(r["logp_true_six"] for r in rs),
                           mean_logp_true_six=sum(r["logp_true_six"] for r in rs) / len(rs),
                           sum_logp_true_raw=sum(r["logp_true_raw"] for r in rs),
                           mean_js_bits=sum(r["js_bits"] for r in rs) / len(rs)))
    free = []
    for r in data["raw"]:
        if r["replicate"] != 1 or r["arm"] not in C.ARMS:
            continue
        pred = parse_three(r["raw_choice_content"])
        k, tgt = r["k"], r["target"]
        first6 = list(C.G_REF[:k]) + (pred or [])
        allowed = set(FACES) - set(C.G_REF[:k])
        free.append(dict(condition=r["condition"], arm=r["arm"], k=k, output=r["raw_choice_content"], valid=pred is not None,
                         target=" ".join(map(str, tgt)), whole_match=pred == tgt,
                         **{f"match_{i + 1}": (pred is not None and pred[i] == tgt[i]) for i in range(3)},
                         first_wrong_index=next((i + 1 for i in range(3) if pred is None or pred[i] != tgt[i]), None),
                         no_repeat_in_first_six=(len(set(first6[:6])) == len(first6[:6])) if pred else None,
                         k3_rule_set_only=(set(pred) <= allowed if (pred and k == 3) else None),
                         path_logp=sum(s["logprob"] for s in r["free_digits"]),
                         **{f"free_p_true_{i + 1}": six(s["face_logprobs_exact"])[0][tgt[i] - 1] for i, s in enumerate(r["free_digits"][:3])}))
    # k=3 rule adherence on the teacher-forced distributions: mass on faces still unused among the first six
    rule = []
    for a in C.ARMS:
        for j in (4, 5, 6):
            r = idx[(a, 3, j)]
            unused = set(FACES) - set(C.G_REF[:j - 1])
            rule.append(dict(arm=a, position=j, unused_faces=" ".join(map(str, sorted(unused))),
                             mass_on_unused=sum(r[f"p{f}"] for f in unused), G_mass_on_unused=sum(r[f"G_p{f}"] for f in unused)))
    pos1 = dict(G=G[1], F_at_G=F_at_G[1], **{f"{a}0": [idx[(a, 0, 1)][f"p{f}"] for f in FACES] for a in C.ARMS})
    return dict(rows=rows, contrasts=contrasts, window=window, free=free, rule=rule, position1=pos1,
                G=G, F_at_G=F_at_G, floor=floor)
