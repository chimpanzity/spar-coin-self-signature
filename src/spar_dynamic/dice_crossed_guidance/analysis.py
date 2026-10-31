"""Gates, item/trial construction, metrics and the frozen estimands for SPAR_CROSSED_GUIDED_SELFPRED_v1.0 (offline)."""

from __future__ import annotations

import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from spar_dynamic.dice_crossed_guidance import config as C
from spar_dynamic.dice_crossed_guidance import prompts as P

FACES = C.FACES
VALID10 = re.compile(r"[1-6]( [1-6]){9}")
OTHER = {"qwen": "mistral", "mistral": "qwen"}


def read_jsonl(path) -> list:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


# ---------- distributions and scores ----------

def _lp(d: dict) -> list:
    d = d.get("bare", d)
    return [d[str(f)] if str(f) in d else d[f] for f in FACES]


def six(face_logprobs: dict) -> tuple[list, float]:
    """Six-face distribution renormalised over the faces, and the raw full-vocabulary mass on them."""
    lp = _lp(face_logprobs)
    m = max(lp)
    w = [math.exp(v - m) for v in lp]
    z = sum(w)
    return [x / z for x in w], sum(math.exp(v) for v in lp)


def temper(p: list, t: float) -> list:
    w = [x ** (1 / t) for x in p]
    z = sum(w)
    return [x / z for x in w]


def js_bits(p: list, q: list) -> float:
    m = [(a + b) / 2 for a, b in zip(p, q)]
    kl = lambda a, b: sum(x * math.log2(x / y) for x, y in zip(a, b) if x > 0)
    return max(0.0, 0.5 * kl(p, m) + 0.5 * kl(q, m))


def tv(p: list, q: list) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def kl_bits(q: list, p: list) -> float:
    """KL(q || p) in bits = cross-entropy of p under reference q minus H(q) (excess cross-entropy)."""
    return sum(a * math.log2(a / max(b, 1e-300)) for a, b in zip(q, p) if a > 0)


def entropy_bits(q: list) -> float:
    return -sum(a * math.log2(a) for a in q if a > 0)


def max_dp(a: dict, b: dict) -> float:
    return max(abs(x - y) for x, y in zip(six(a)[0], six(b)[0]))


def rank_of(p: list, face: int) -> int:
    return 1 + sum(1 for x in p if x > p[face - 1])


def parse_n(text: str, n: int):
    if not re.fullmatch(r"[1-6]( [1-6])*", text) or len(text.split(" ")) != n:
        return None
    return [int(x) for x in text.split(" ")]


def _gate(ok: bool, detail) -> dict:
    return dict(status="PASS" if ok else "FAIL", detail=detail)


# ---------- preflight ----------

def archive21() -> dict:
    raw = read_jsonl(C.EXP21 / "raw_attempts.jsonl")
    gen = {c: [s["face_logprobs_exact"] for s in next(r for r in raw if r["condition"] == c)["raw_logprobs_content"]
               if s["token"].strip().isdigit()] for c in ("G", "F")}
    mp = {(r["instruction"], r["history"], r["method"], r["position"]): r["face_logprobs_exact"]
          for r in read_jsonl(C.EXP21 / "matched_prefix.jsonl")}
    return dict(gen=gen, mp=mp)


def archive26() -> dict:
    return {(r["condition"], r["original_position"]): r["face_logprobs_exact"]
            for r in read_jsonl(C.EXP26 / "main" / "teacher_forced.jsonl") if r["replicate"] == 1}


def scorer_diff(rec: dict) -> float:
    """Max |logprob| difference between generation digit steps and incremental rescoring of the same output."""
    a, b = rec["digit_steps"], rec.get("own_rescored", [])
    if len(a) != len(b):
        return float("inf")
    return max((abs(x["face_logprobs"][str(f)] - y["face_logprobs"][str(f)]) for x, y in zip(a, b) for f in FACES), default=0.0)


def floor_pairs(recs, inc_key, full_key) -> list:
    out = []
    for r in recs:
        if r.get(full_key):
            out += [max_dp(x["face_logprobs"], y["face_logprobs"]) for x, y in zip(r[inc_key], r[full_key])]
    return out


def preflight_gates(model: str, d: Path | None = None) -> dict:
    d = d or C.PRE / model
    env = json.load(open(d / "env_preflight.json", encoding="utf-8"))
    raw = read_jsonl(d / "raw_attempts.jsonl")
    mp = read_jsonl(d / "matched_prefix.jsonl")
    spec, refs = C.MODEL[model], P.references()
    g = {}
    want = {**{k: v["prompt_sha256"] for k, v in refs.items()}, **({c["condition"]: c["prompt_sha256"] for c in P.archival26()} if model == "qwen" else {})}
    ok = env["model_commit"] == spec["revision"] and all(env["prompt_sha256"][k] == v for k, v in want.items()) \
        and all(r["prompt_sha256"] == P.sha256(r["prompt"]) for r in raw)
    if model == "qwen":
        ok &= env["chat_template_sha256"] == C.QWEN_CHAT_TEMPLATE_SHA256
    g["serving"] = _gate(ok, dict(model_id=env["model_id"], model_commit=env["model_commit"], gpu=env["gpu"], torch=env["torch"],
                                  transformers=env["transformers"], cuda=env["cuda"], chat_template_sha256=env.get("chat_template_sha256"),
                                  tekken_sha256=env.get("tekken_sha256"), mistral_common=env.get("mistral_common")))
    rg = env["rendered_G"]
    if model == "qwen":
        tmpl_ok = rg.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n") and "<|im_start|>system" not in rg
    else:
        tmpl_ok = rg == "<s>[INST]" + P.GEN + "[/INST]"
    tmpl_ok &= not any("<think" in r["content"] or "[SYSTEM" in r["content"] for r in raw)
    g["template"] = _gate(tmpl_ok, dict(rendered_G=rg))
    fid = {str(f): v for f, v in spec["face_ids"].items()}
    h = env["g10_history_ids"]
    tok_ok = {str(k): v for k, v in env["face_ids"].items()} == fid and \
        all(env["face_single_tokens"][str(f)] == [fid[str(f)]] for f in FACES) and \
        h[0::2] == [fid[str(f)] for f in C.QWEN_G_REF] and len(set(h[1::2])) == 1 and len(h) == 19
    g["face_tokens"] = _gate(tok_ok, dict(face_ids=env["face_ids"], separator_id=h[1] if len(h) > 1 else None))
    steps = [s["face_logprobs"] for r in raw for s in r["digit_steps"]] + [s["face_logprobs"] for r in raw for s in r.get("teacher_forced", [])] \
        + [s["face_logprobs"] for s in mp]
    masses = [six(s)[1] for s in steps]
    g["face_logprobs"] = _gate(all(math.isfinite(v) for s in steps for v in _lp(s)) and min(masses) >= C.MIN_FACE_MASS,
                               dict(n_steps=len(steps), min_six_face_mass=min(masses)))
    sd = max(scorer_diff(r) for r in raw if r["content"].strip())
    g["scorer_matches_generation"] = _gate(sd <= C.SCORER_TOL_LOGP, dict(max_abs_logprob_diff=sd, tol=C.SCORER_TOL_LOGP))
    det = {}
    for cond in ("G", "F"):
        rs = [r for r in raw if r["condition"] == cond]
        det[cond] = dict(outputs=sorted({r["content"] for r in rs}), max_spread=max(
            abs(a["face_logprobs"][str(f)] - b["face_logprobs"][str(f)]) for r in rs[1:] for a, b in zip(r["digit_steps"], rs[0]["digit_steps"]) for f in FACES))
    g["determinism"] = _gate(all(len(v["outputs"]) == 1 and v["max_spread"] == 0.0 for v in det.values()), det)
    gref = next(r["content"] for r in raw if r["condition"] == "G")
    g["greedy_G_valid"] = _gate(bool(VALID10.fullmatch(gref)), dict(G=gref, F=next(r["content"] for r in raw if r["condition"] == "F")))
    if model == "qwen":
        arc = archive21()
        dps, seq_ok = [], True
        for r in raw:
            if r["condition"] in ("G", "F"):
                seq_ok &= r["content"] == " ".join(map(str, C.QWEN_G_REF if r["condition"] == "G" else C.QWEN_F_REF))
                dps += [max_dp(a["face_logprobs"], b) for a, b in zip(r["digit_steps"], arc["gen"][r["condition"]])]
        for x in mp:
            key = (x["instruction"], x["history"], "incremental", x["position"])
            if x["method"] == "incremental" and key in arc["mp"]:
                dps.append(max_dp(x["face_logprobs"], arc["mp"][key]))
        g["qwen_exp21_regression"] = _gate(seq_ok and max(dps) <= C.REPRO_TOL_P, dict(sequences_identical=seq_ok, n=len(dps), max_abs_dp=max(dps), tol=C.REPRO_TOL_P))
        a26 = archive26()
        x26 = {r["condition"][4:]: r for r in raw if r["condition"].startswith("x26_")}
        free_ok = {k: x26[k]["content"] == v for k, v in C.EXP26_FREE.items()}
        d26 = [max_dp(s["face_logprobs"], a26[(k, r["k"] + s["position"])]) for k, r in x26.items() for s in r["teacher_forced"]]
        g["qwen_exp26_regression"] = _gate(all(free_ok.values()) and max(d26) <= C.REPRO_TOL_P,
                                           dict(free_outputs_identical=free_ok, n=len(d26), max_abs_dp=max(d26), k3_free={k: x26[k]["content"] for k in ("H3", "N3", "S3", "O3")}))
        eq = json.load(open(d / "engine_equivalence.json", encoding="utf-8"))
        g["engine_equals_exp21_class"] = _gate(all(e.get("content_equal", True) and e["max_abs_face_logprob_diff"] <= C.ENGINE_TOL_LOGP for e in eq), eq)
    fl = floor_pairs(raw, "own_rescored", "own_rescored_full_pass") + floor_pairs(raw, "teacher_forced", "teacher_forced_full_pass")
    inc = {(x["instruction"], x["history"], x["position"]): x["face_logprobs"] for x in mp if x["method"] == "incremental"}
    fl += [max_dp(inc[(x["instruction"], x["history"], x["position"])], x["face_logprobs"]) for x in mp if x["method"] == "full_pass"]
    g["numerical_floor"] = _gate(max(fl) <= C.FLOOR_STOP_P, dict(max_abs_dp_incremental_vs_full_pass=max(fl), n=len(fl), stop_above=C.FLOOR_STOP_P))
    info = dict(feasibility=[r["content"] for r in raw if r["condition"] == "feasibility"],
                feasibility_valid=sum(bool(VALID10.fullmatch(r["content"])) for r in raw if r["condition"] == "feasibility"),
                crossed_format_check={r["condition"]: r["content"] for r in raw if r["condition"].startswith("crossed_")},
                sec_per_crossed_trial=env.get("sec_per_crossed_trial"), max_memory_allocated_gb=env.get("max_memory_allocated_gb"),
                floor=max(fl))
    return dict(tag=C.TAG, model=model, models=[model], gates=g, info=info,
                overall="PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL")


# ---------- corpus, items and trials ----------

def corpus_gate(model: str, d: Path | None = None) -> dict:
    d = d or C.CORPUS / model
    recs = read_jsonl(d / "sampled.jsonl")
    g = {}
    for kind, n in (("reference", C.N_REFERENCE), ("target", C.N_TARGETS)):
        v = [r for r in recs if r["condition"] == kind and r["valid"]]
        g[f"{kind}_complete"] = _gate(len(v) == n, dict(valid=len(v), drawn=sum(r["condition"] == kind for r in recs)))
    sd = max(scorer_diff(r) for r in recs if r["valid"])
    g["scorer_matches_generation"] = _gate(sd <= C.SCORER_TOL_LOGP, dict(max_abs_logprob_diff=sd))
    seeds = [r["seed"] for r in recs]
    g["seeds_unique_and_tabled"] = _gate(len(set(seeds)) == len(seeds), dict(n=len(seeds), first=seeds[:3]))
    fl = [max_dp(x["face_logprobs"], y["face_logprobs"]) for r in recs if r["valid"] for x, y in zip(r["own_rescored"], r["full_pass"])]
    tgt = [r["content"] for r in recs if r["condition"] == "target" and r["valid"]]
    ref = [r["content"] for r in recs if r["condition"] == "reference" and r["valid"]]
    info = dict(duplicate_targets={s: c for s, c in Counter(tgt).items() if c > 1}, n_unique_targets=len(set(tgt)),
                targets_equal_to_a_reference=sorted(set(tgt) & set(ref)), floor_sampled=max(fl),
                six_distinct_first6_targets=sum(len(set(s.split()[:6])) == 6 for s in tgt),
                six_distinct_first6_references=sum(len(set(s.split()[:6])) == 6 for s in ref))
    return dict(model=model, models=[model], gates=g, info=info, overall="PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL")


def build_items() -> list:
    items = []
    for m in C.MODELS:
        pre = read_jsonl(C.PRE / m / "raw_attempts.jsonl")
        recs = read_jsonl(C.CORPUS / m / "sampled.jsonl")
        refs = [r for r in recs if r["condition"] == "reference" and r["valid"]]
        tgts = [r for r in recs if r["condition"] == "target" and r["valid"]]
        gref = next(r for r in pre if r["condition"] == "G")
        assert VALID10.fullmatch(gref["content"])
        if m == "qwen":
            assert gref["content"] == " ".join(map(str, C.QWEN_G_REF))
        rs = lambda i: [int(x) for x in refs[i]["content"].split()]
        items.append(dict(item_id=f"A-{m}", tier="A", generator=m, sequence=[int(x) for x in gref["content"].split()],
                          source="greedy G (preflight)", seed=None, ref_id=f"R-{m}-01", ref_sequence=rs(0)))
        for i, t in enumerate(tgts):
            items.append(dict(item_id=f"B-{m}-{i + 1:02d}", tier="B", generator=m, sequence=[int(x) for x in t["content"].split()],
                              source=f"sampled T={C.TEMPERATURE}", seed=t["seed"], ref_id=f"R-{m}-{i % C.N_REFERENCE + 1:02d}",
                              ref_sequence=rs(i % C.N_REFERENCE)))
    return items


def integrity_rows(items: list) -> list:
    rows = []
    for it in items:
        s, r = it["sequence"], it["ref_sequence"]
        rows.append(dict(item_id=it["item_id"], tier=it["tier"], generator=it["generator"], sequence=P.seq_str(s), source=it["source"],
                         seed=it["seed"], D_ref_id=it["ref_id"], D_ref_sequence=P.seq_str(r), D_source_model=it["generator"],
                         D_from_reference_corpus=True, D_is_scored_target=False, ref_equals_target=s == r,
                         ref_shared_prefix_len=next((i for i in range(10) if s[i] != r[i]), 10),
                         ref_matches_positions_7_9=r[6:9] == s[6:9], ref_matches_positions_4_6=r[3:6] == s[3:6],
                         six_distinct_first6=len(set(s[:6])) == 6))
    return rows


def call_table(trials: list, items: list) -> dict:
    n = Counter(t["predictor"] for t in trials)
    secs = {m: n[m] * C.EST_SEC_PER_TRIAL[m] + len(items) * 6 * 0.5 for m in C.MODELS}
    hours = (sum(secs.values()) / 3600) + C.EST_SETUP_MIN / 60
    return dict(n_trials=len(trials), per_predictor=dict(n), per_cell={f"{p}->{g}": sum(1 for t in trials if t["predictor"] == p and t["generator"] == g)
                                                                       for p in C.MODELS for g in C.MODELS},
                forward_scored_positions=sum(len(t["positions"]) for t in trials), est_seconds=secs,
                est_hours_incl_setup=hours, est_cost_usd=hours * C.EST_RATE_USD_H, cap_usd=C.GPU_CAP_USD)


# ---------- main checks ----------

def load_main(d: Path | None = None) -> dict:
    d = d or C.MAIN
    trials = {t["trial_id"]: t for t in read_jsonl(C.TRIALS / "trials.jsonl")}
    items = {i["item_id"]: i for i in json.load(open(C.TRIALS / "items.json", encoding="utf-8"))}
    preds, policy, env = {}, [], {}
    for m in C.MODELS:
        for r in read_jsonl(d / m / "predictions.jsonl"):
            preds[r["trial_id"]] = r
        policy += read_jsonl(d / m / f"policy_{m}.jsonl")
        env[m] = json.load(open(d / m / f"env_predict_{m}.json", encoding="utf-8"))
    pol = {(x["scorer"], x["item_id"], x["instruction"], x["method"], x["position"]): x["face_logprobs"] for x in policy}
    return dict(trials=trials, items=items, preds=preds, pol=pol, env=env)


def main_checks(data: dict) -> dict:
    T, R, pol, items = data["trials"], data["preds"], data["pol"], data["items"]
    g = {}
    g["complete"] = _gate(set(T) == set(R) and all(len(R[k]["teacher_forced"]) == len(T[k]["positions"]) for k in T),
                          dict(trials=len(T), records=len(R), missing=len(set(T) - set(R))))
    g["prompt_hashes"] = _gate(all(R[k]["prompt_sha256"] == T[k]["prompt_sha256"] for k in R if k in T), "every record's prompt sha256 equals the frozen trial's")
    g["teacher_forced_history"] = _gate(all([s["history_face"] for s in R[k]["teacher_forced"]] == T[k]["target"] for k in R if k in T),
                                        "forced faces equal the target window at every trial")
    steps = [s["face_logprobs"] for r in R.values() for s in r["teacher_forced"]]
    masses = [six(s)[1] for s in steps]
    g["face_logprobs"] = _gate(all(math.isfinite(v) for s in steps for v in _lp(s)), dict(n=len(steps), min_mass=min(masses),
                                                                                       n_mass_below_0_5=sum(m < C.MIN_FACE_MASS for m in masses)))
    sd = max((scorer_diff(r) for r in R.values() if r.get("own_rescored") and r["content"].strip()), default=0.0)
    g["scorer_matches_generation"] = _gate(sd <= C.SCORER_TOL_LOGP, dict(max_abs_logprob_diff=sd))
    pol_ok = all((m, i, ins, "incremental", j) in pol for m in C.MODELS for i in items for ins in ("G", "F", "Fanon") for j in range(1, 11))
    g["policy_complete"] = _gate(pol_ok, dict(items=len(items)))
    # oracle check: G scored on the generator's own sampled sequence equals the sampling-time distribution
    corp = {r["content"]: r for m in C.MODELS for r in read_jsonl(C.CORPUS / m / "sampled.jsonl") if r["valid"]}
    od = []
    for i, it in items.items():
        if it["tier"] == "B":
            gen = corp[P.seq_str(it["sequence"])]["digit_steps"]
            od += [max(abs(gen[j - 1]["face_logprobs"][str(f)] - pol[(it["generator"], i, "G", "incremental", j)][str(f)]) for f in FACES) for j in range(1, 11)]
    g["oracle_equals_sampling_distribution"] = _gate(max(od) <= C.SCORER_TOL_LOGP, dict(max_abs_logprob_diff=max(od), n=len(od)))
    floors = {}
    for m in C.MODELS:
        fl = [max_dp(x["face_logprobs"], y["face_logprobs"]) for r in R.values() if r["predictor"] == m and r.get("teacher_forced_full_pass")
              for x, y in zip(r["teacher_forced"], r["teacher_forced_full_pass"])]
        fl += [max_dp(pol[(m, i, ins, "incremental", j)], pol[(m, i, ins, "full_pass", j)]) for i in items for ins in ("G", "F", "Fanon") for j in range(1, 11)]
        floors[m] = dict(max_abs_dp=max(fl), p99=sorted(fl)[int(0.99 * (len(fl) - 1))], median=statistics.median(fl), n=len(fl))
    g["numerical_floor"] = _gate(all(v["max_abs_dp"] <= C.FLOOR_STOP_P for v in floors.values()), floors)
    return dict(gates=g, floors=floors, overall="PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL")


# ---------- tidy rows ----------

def tidy(data: dict) -> list:
    T, R, pol, items = data["trials"], data["preds"], data["pol"], data["items"]
    rows = []
    for k, t in T.items():
        r = R[k]
        it = items[t["item_id"]]
        free = parse_n(r["content"], len(t["positions"]))
        for i, s in enumerate(r["teacher_forced"]):
            j = t["positions"][i]
            p, mass = six(s["face_logprobs"])
            q = six(pol[(t["generator"], t["item_id"], "G", "incremental", j)])[0]
            nat = six(pol[(t["predictor"], t["item_id"], "G", "incremental", j)])[0]
            qt = temper(q, C.TEMPERATURE)
            truth = it["sequence"][j - 1]
            rows.append(dict(trial_id=k, predictor=t["predictor"], generator=t["generator"], diagonal=t["diagonal"], tier=t["tier"],
                             item_id=t["item_id"], sequence=P.seq_str(it["sequence"]), cond=t["cond"], suite=t["suite"], framing=t["framing"],
                             evidence=t["evidence"], arm=t["arm"], position=j, window_index=i + 1, true_face=truth,
                             **{f"p{f}": p[f - 1] for f in FACES}, **{f"q{f}": q[f - 1] for f in FACES}, **{f"n{f}": nat[f - 1] for f in FACES},
                             six_face_mass=mass, js=js_bits(p, q), tv=tv(p, q), kl=kl_bits(q, p), H_target=entropy_bits(q),
                             js_tempered=js_bits(p, qt), js_native=js_bits(nat, q), kl_native=kl_bits(q, nat), js_pred_vs_native=js_bits(p, nat),
                             p_true=p[truth - 1], log2_p_true=math.log2(p[truth - 1]), q_p_true=q[truth - 1], rank_true=rank_of(p, truth),
                             top_is_true=p.index(max(p)) + 1 == truth, top_is_target_top=p.index(max(p)) == q.index(max(q)),
                             free_output=r["content"], free_valid=free is not None,
                             free_match=(free is not None and free[i] == truth), free_window_exact=free == t["target"]))
    return rows


# ---------- estimands ----------

def clusters(items: dict) -> dict:
    """Tier B items grouped by identical sequence string within generator (duplicates are one resampling unit)."""
    out = {m: defaultdict(list) for m in C.MODELS}
    for i, it in items.items():
        if it["tier"] == "B":
            out[it["generator"]][P.seq_str(it["sequence"])].append(i)
    return {m: list(v.values()) for m, v in out.items()}


def item_means(rows: list, metric: str, **filt) -> dict:
    """(predictor, item) -> mean metric over the matching rows (conditions, positions and arms pooled with equal weight)."""
    acc = defaultdict(list)
    for r in rows:
        if r["tier"] == "B" and all((r[k] in v) if isinstance(v, (tuple, list, set)) else r[k] == v for k, v in filt.items()):
            acc[(r["predictor"], r["item_id"])].append(r[metric])
    return {k: sum(v) / len(v) for k, v in acc.items()}


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def self_advantage(vals: dict) -> callable:
    """vals: (predictor, item) -> metric where LOWER is closer. Returns stat(sample) -> dict of the 2x2 contrasts."""
    def stat(s):
        sq = _mean([vals[("mistral", i)] - vals[("qwen", i)] for i in s["qwen"]])        # on Qwen targets: Mistral - Qwen
        sm = _mean([vals[("qwen", i)] - vals[("mistral", i)] for i in s["mistral"]])     # on Mistral targets: Qwen - Mistral
        return dict(self_adv_qwen_targets=sq, self_adv_mistral_targets=sm, interaction=(sq + sm) / 2)
    return stat


def boot_dict(stat, cl) -> dict:
    """Bootstrap each key of a dict-valued statistic."""
    rng = random.Random(C.BOOTSTRAP_SEED)
    est = stat({m: [i for c in cl[m] for i in c] for m in C.MODELS})
    draws = defaultdict(list)
    for _ in range(C.BOOTSTRAP_B):
        s = {m: [i for c in (rng.choice(cl[m]) for _ in cl[m]) for i in c] for m in C.MODELS}
        for k, v in stat(s).items():
            draws[k].append(v)
    out = {}
    for k, v in est.items():
        d = sorted(draws[k])
        out[k] = dict(est=v, lo=d[int(0.025 * len(d))], hi=d[int(0.975 * len(d)) - 1])
    return out


def cell_table(rows: list, metric: str, **filt) -> dict:
    vals = item_means(rows, metric, **filt)
    out = {}
    for p in C.MODELS:
        for g in C.MODELS:
            v = [x for (pp, i), x in vals.items() if pp == p and i.startswith(f"B-{g}-")]
            out[f"{p}->{g}"] = dict(mean=_mean(v), n_items=len(v))
    return out


def estimands(rows: list, items: dict) -> dict:
    cl = clusters(items)
    res = {}
    # E1 (RQ2, primary): self-advantage interaction, anonymous framing, history only, all conditions and positions
    for metric in ("js", "kl", "tv"):
        res[f"E1_selfadv_AH_{metric}"] = boot_dict(self_advantage(item_means(rows, metric, arm="AH")), cl)
    res["E1_selfadv_allarms_js"] = boot_dict(self_advantage(item_means(rows, "js")), cl)
    res["E1_selfadv_AH_neglog2ptrue"] = boot_dict(self_advantage({k: -v for k, v in item_means(rows, "log2_p_true", arm="AH").items()}), cl)
    # E2 (RQ4): the same interaction for each predictor's own direct-generation policy (no prediction wrapper)
    res["E2_selfadv_native_js"] = boot_dict(self_advantage(item_means(rows, "js_native", arm="AH")), cl)
    res["E2_selfadv_native_kl"] = boot_dict(self_advantage(item_means(rows, "kl_native", arm="AH")), cl)
    # E2b: prediction minus native, per cell (positive = the prediction is further from the target than plain generation)
    pv, nv = item_means(rows, "js", arm="AH"), item_means(rows, "js_native", arm="AH")
    def pred_minus_native(s):
        out = {}
        for p in C.MODELS:
            for g in C.MODELS:
                out[f"{p}->{g}"] = _mean([pv[(p, i)] - nv[(p, i)] for i in s[g]])
        return out
    res["E2b_pred_minus_native_js"] = boot_dict(pred_minus_native, cl)
    # E3 (RQ3, identity): change from A to T (or R), paired on item/cond/evidence, diagonal minus off-diagonal
    for x in ("T", "R"):
        for metric in ("js", "kl"):
            vx = item_means(rows, metric, framing=x)
            va = item_means(rows, metric, framing="A")
            def did(s, vx=vx, va=va):
                d = {p_g: _mean([vx[(p_g[0], i)] - va[(p_g[0], i)] for i in s[p_g[1]]]) for p_g in
                     [(p, g) for p in C.MODELS for g in C.MODELS]}
                out = {f"{p}->{g}": v for (p, g), v in d.items()}
                out["DiD_qwen_targets"] = d[("qwen", "qwen")] - d[("mistral", "qwen")]
                out["DiD_mistral_targets"] = d[("mistral", "mistral")] - d[("qwen", "mistral")]
                out["DiD"] = (out["DiD_qwen_targets"] + out["DiD_mistral_targets"]) / 2
                return out
            res[f"E3_identity_{x}_minus_A_{metric}"] = boot_dict(did, cl)
    # E4 (RQ3, guidance): evidence contrasts per cell under anonymous framing
    for a, b in (("D", "H"), ("I", "H"), ("D", "I")):
        va, vb = item_means(rows, "js", framing="A", evidence=a), item_means(rows, "js", framing="A", evidence=b)
        def ev(s, va=va, vb=vb):
            return {f"{p}->{g}": _mean([va[(p, i)] - vb[(p, i)] for i in s[g]]) for p in C.MODELS for g in C.MODELS}
        res[f"E4_evidence_{a}_minus_{b}_js"] = boot_dict(ev, cl)
    # E5: history suites (AH), per cell, and the self-advantage interaction within each suite
    for name, conds in (("fixed7_pos7", C.FIXED7), ("immediate_first", C.IMMEDIATE), ("bridge", C.BRIDGE)):
        filt = dict(arm="AH", cond=conds)
        if name != "bridge":
            filt["window_index"] = 1
        res[f"E5_{name}_selfadv_js"] = boot_dict(self_advantage(item_means(rows, "js", **filt)), cl)
    # E6: tempered-target sensitivity (target distribution at the sampling temperature)
    res["E6_selfadv_AH_js_tempered"] = boot_dict(self_advantage(item_means(rows, "js_tempered", arm="AH")), cl)
    return res


def by_condition(rows: list) -> list:
    """Per cell x condition x revealed history: mean JS over Tier B items, AH arm, first and all window positions."""
    out = []
    for p in C.MODELS:
        for g in C.MODELS:
            for cond in C.CONDITIONS:
                for wi in (1, None):
                    rs = [r for r in rows if r["tier"] == "B" and r["predictor"] == p and r["generator"] == g and r["cond"] == cond
                          and r["arm"] == "AH" and (wi is None or r["window_index"] == wi)]
                    out.append(dict(cell=f"{p}->{g}", predictor=p, generator=g, cond=cond, positions="first" if wi else "window",
                                    n=len(rs), js=_mean([r["js"] for r in rs]), js_native=_mean([r["js_native"] for r in rs]),
                                    kl=_mean([r["kl"] for r in rs]), H_target=_mean([r["H_target"] for r in rs]),
                                    p_true=_mean([r["p_true"] for r in rs]), top_is_true=_mean([r["top_is_true"] for r in rs]),
                                    top_is_target_top=_mean([r["top_is_target_top"] for r in rs])))
    return out


def by_arm(rows: list) -> list:
    out = []
    for p in C.MODELS:
        for g in C.MODELS:
            for fr in C.FRAMINGS:
                for ev in C.EVIDENCE:
                    rs = [r for r in rows if r["tier"] == "B" and r["predictor"] == p and r["generator"] == g and r["arm"] == fr + ev]
                    out.append(dict(cell=f"{p}->{g}", predictor=p, generator=g, arm=fr + ev, framing=fr, evidence=ev, n=len(rs),
                                    js=_mean([r["js"] for r in rs]), kl=_mean([r["kl"] for r in rs]), p_true=_mean([r["p_true"] for r in rs]),
                                    free_valid=_mean([r["free_valid"] for r in rs]), free_match=_mean([r["free_match"] for r in rs]),
                                    six_face_mass=_mean([r["six_face_mass"] for r in rs])))
    return out


def tier_a(rows: list) -> list:
    out = []
    for r in rows:
        if r["tier"] == "A":
            out.append({k: r[k] for k in ("predictor", "generator", "item_id", "sequence", "cond", "arm", "position", "true_face", "js",
                                          "kl", "p_true", "top_is_true", "js_native", "free_output", "free_window_exact")})
    return out


def rq1_tables() -> list:
    """RQ1: each model's G, F and Fanon six-face distributions along its own greedy G (preflight matched prefix)."""
    out = []
    for m in C.MODELS:
        mp = [x for x in read_jsonl(C.PRE / m / "matched_prefix.jsonl") if x["method"] == "incremental" and x["history"] == "G"]
        g = {x["position"]: six(x["face_logprobs"])[0] for x in mp if x["instruction"] == "G"}
        for x in mp:
            p = six(x["face_logprobs"])[0]
            j = x["position"]
            out.append(dict(model=m, instruction=x["instruction"], position=j, history_face=x["history_face"],
                            **{f"p{f}": p[f - 1] for f in FACES}, js_vs_G=js_bits(p, g[j]), top=p.index(max(p)) + 1,
                            G_top=g[j].index(max(g[j])) + 1))
    return out
