"""Preflight gates, the calibration gate and main-run checks for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0 (offline; read stage folders).

Judge-level gating (prespecified): each judge passes or fails independently. A judge that fails preflight or calibration is
NOT INTERPRETABLE / NOT RUN for recognition; the other judge may still be collected, and crossed contrasts are then unavailable.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from spar_dynamic.dice_bidirectional_completion.gates import _g_mass, _regression
from spar_dynamic.dice_crossed_guidance.analysis import _gate, _lp, max_dp, read_jsonl, six
from spar_dynamic.dice_logprob_crossmodel import config as C28
from spar_dynamic.dice_logprob_crossmodel.gates import _determinism, _face_tokens, _template
from spar_dynamic.dice_six_roll_recognition import config as C
from spar_dynamic.dice_six_roll_recognition import stimuli as S


def canonical_sha(p) -> str:
    """SHA-256 of a text file with CRLF normalised to LF (= the committed git blob on this Windows checkout, = the host bytes)."""
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _overall(g):
    return "PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL"


def _dir(root, stage, model) -> Path:
    return Path(root or C.EXP) / stage / model


def _env(d: Path, stage) -> dict:
    envs = [json.load(open(p, encoding="utf-8")) for p in sorted(d.glob(f"env_{stage}*.json"))]
    return max((e for e in envs if e.get("finished_utc")), key=lambda e: e["finished_utc"], default=envs[0])


# ---------- shared ----------

def verify_references() -> dict:
    """Ground truth re-read from Experiment 28, fixture assertions, and the handoff's archived fifth-roll probabilities."""
    detail, ok = {}, True
    try:
        gt = S.ground_truth()
        fx = S.fixtures(gt)
    except (ValueError, AssertionError) as e:
        return dict(ok=False, detail=dict(error=str(e)))
    for (s, i), x in gt.items():
        raw = read_jsonl(C.EXP28_MAIN / s / "raw_attempts.jsonl")
        r = next(r for r in raw if r["condition"] == i)
        p5 = six(r["digit_steps"][4]["face_logprobs"])[0]
        a, b = x[4], x[5]
        got = (p5[a - 1], p5[b - 1])
        want = C.ARCHIVED_P5[(s, i)]
        close = all(abs(g - w) <= C.ARCHIVED_P5_TOL for g, w in zip(got, want))
        ok &= close
        detail[S.source_id(s, i)] = dict(sequence10=S.seq(x), authentic=S.seq(fx[(s, i)]["authentic"]), swap=S.seq(fx[(s, i)]["swap"]),
                                         repeat=S.seq(fx[(s, i)]["repeat"]), p5_authentic_swap=[round(v, 6) for v in got],
                                         handoff_p5=want, p5_match=close)
    return dict(ok=ok, detail=detail)


def _serving(env, model) -> dict:
    spec = C.MODEL[model]
    ok = env["model_commit"] == spec["revision"] and env["model_id"] == spec["model_id"] and env["prompt_sha256"] == S.all_prompt_sha() \
        and env["archival_prompt_sha256"] == {k: S.sha256(v) for k, v in S.SOURCE_INSTRUCTION.items()}
    ok &= env.get("chat_template_sha256") == C28.QWEN_CHAT_TEMPLATE_SHA256 if model == "qwen" else env.get("tekken_sha256") == C28.MISTRAL_TEKKEN_SHA256
    return _gate(ok, {k: env.get(k) for k in ("model_id", "model_commit", "gpu", "driver", "cuda", "torch", "transformers", "accelerate",
                                               "huggingface_hub", "mistral_common", "chat_template_sha256", "tekken_sha256", "code_commit")})


def _labels(env) -> dict:
    lt = env["label_tokens"]
    ids = [lt[l]["id"] for l in C.LABELS]
    ok = all(i is not None for i in ids) and len(set(ids)) == 2 and all(env["label_context"]["label_appends_single_token"].values())
    return _gate(ok, dict(label_tokens=lt, context=env["label_context"]))


def _prompts_ok(recs, cells) -> dict:
    bad = [r["trial_id"] for r in recs if r["prompt_id"] not in cells or r["prompt_sha256"] != cells[r["prompt_id"]]["prompt_sha256"]
           or S.sha256(r["prompt"]) != r["prompt_sha256"]]
    leaks = [r["trial_id"] for r in recs if any(w in r["prompt"].lower() for w in ("qwen", "mistral", "alibaba"))]
    return _gate(not bad and not leaks, dict(hash_mismatch=bad[:10], model_names_in_prompt=leaks[:10]))


def _finite(recs) -> dict:
    vals = [r[k] for r in recs for k in ("logp_A", "logp_B", "d") if r.get(k) is not None] + \
        [r[k] for r in recs for k in ("logp_A_tokenwise", "logp_B_tokenwise") if k in r]
    return _gate(bool(vals) and all(math.isfinite(v) for v in vals), dict(n_values=len(vals)))


def _complete(recs, stage, model) -> dict:
    from spar_dynamic.dice_six_roll_recognition.gpu import jobs_for
    keys = sorted((r["prompt_id"], r["replicate"]) for r in recs)
    want = sorted(tuple(j) for j in jobs_for(model, stage))
    tw = sorted(r["prompt_id"] for r in recs if "d_tokenwise" in r)
    return _gate(keys == want and tw == sorted({p for p, _ in want}), dict(n=len(keys), expected=len(want), tokenwise=len(tw)))


def _repeat_identical(recs) -> dict:
    by = defaultdict(list)
    for r in recs:
        by[r["prompt_id"]].append(r)
    bad = {}
    for pid, rs in by.items():
        if len({(r["logp_A"], r["logp_B"], r["greedy_text"]) for r in rs}) != 1:
            bad[pid] = [(r["replicate"], r["d"], r["greedy_text"]) for r in rs]
    return _gate(not bad, dict(n_prompts=len(by), differing=bad))


def floor(recs) -> float:
    return max((r["abs_delta_d"] for r in recs if "abs_delta_d" in r), default=float("inf"))


def epsilon(recs) -> float:
    return max(C.EPS_MIN, C.EPS_MULT * floor(recs))


def _write(res, d: Path, name, title):
    d.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(d / f"{name}.json", "w", encoding="utf-8", newline="\n"), indent=2, default=str)
    (d / f"{name.upper()}.md").write_text(report_md(res, title), encoding="utf-8", newline="\n")
    return res


# ---------- preflight ----------

def _policy(model, rows) -> dict:
    inc = [x for x in rows if x["method"] == "incremental"]
    n_ok = len(inc) == len(rows) // 2 == 4 * 3 * 6 and all(x["scorer"] == model for x in rows)
    # shared contexts: authentic/swap/repeat agree at positions 1-5 except swap at 5 has the same context (prefix4) and repeat
    # at 6 has authentic's context (prefix4 + roll 5); these vectors must be bit-identical
    v = {(x["source_id"], x["candidate"], x["position"]): x["face_logprobs"] for x in inc}
    shared = []
    for sid in {x["source_id"] for x in inc}:
        for pos in range(1, 6):
            shared.append(v[(sid, "authentic", pos)] == v[(sid, "swap", pos)] == v[(sid, "repeat", pos)])
        shared.append(v[(sid, "authentic", 6)] == v[(sid, "repeat", 6)])
    # diagonal regression: the source model's authentic history vs its own Experiment 28 generation steps 1-6
    dps = []
    for (s, i) in C.REFERENCES:
        if s != model:
            continue
        r = next(r for r in read_jsonl(C.EXP28_MAIN / s / "raw_attempts.jsonl") if r["condition"] == i)
        dps += [max_dp(v[(S.source_id(s, i), "authentic", p)], r["digit_steps"][p - 1]["face_logprobs"]) for p in range(1, 7)]
    full = {(x["source_id"], x["candidate"], x["position"]): x["face_logprobs"] for x in rows if x["method"] == "full_pass"}
    fl = max(max_dp(v[k], full[k]) for k in v) if v and set(v) == set(full) else float("inf")
    ms = [six(x["face_logprobs"])[1] for x in inc]
    fin = all(math.isfinite(z) for x in rows for z in _lp(x["face_logprobs"]))
    return dict(policy_complete=_gate(n_ok and fin, dict(rows=len(rows), incremental=len(inc), finite=fin)),
                policy_shared_contexts_identical=_gate(all(shared) and len(shared) == 4 * 6, dict(n=len(shared))),
                policy_diagonal_regression=_gate(len(dps) == 12 and max(dps) <= C.REPRO_TOL_P,
                                                 dict(archive="Experiment 28 main generation steps 1-6", max_abs_dp=max(dps, default=None), tol=C.REPRO_TOL_P)),
                policy_floor=_gate(fl <= C.FLOOR_STOP_P, dict(max_abs_dp_incremental_vs_full_pass=fl, stop_above=C.FLOOR_STOP_P)),
                policy_mass=_gate(statistics.median(ms) >= 0.10, dict(median_raw_mass=statistics.median(ms), min_raw_mass=min(ms))))


def preflight_gates(model: str, root=None) -> dict:
    d = _dir(root, "preflight", model)
    env = _env(d, "preflight")
    arch = read_jsonl(d / "archival.jsonl")
    recs = read_jsonl(d / S_RAW)
    pol = read_jsonl(_dir(root, "policy_benchmark", model) / "policy_teacher_forced.jsonl")
    ref = verify_references()
    g = dict(references_equal_exp28=_gate(ref["ok"], ref["detail"]), serving=_serving(env, model), template=_template(env, arch, model),
             face_tokens=_face_tokens(env, model), label_tokens=_labels(env), prompts=_prompts_ok(recs, {c["prompt_id"]: c for c in S.tech_cells()}))
    g["face_mass_archival_G"] = _g_mass(arch)
    g["archival_regression"] = _regression(model, arch)
    det = _determinism(arch)
    g["archival_determinism"] = _gate(all(len(v["outputs"]) == 1 and v["max_logprob_spread"] == 0.0 and v["n"] == C.ARCHIVAL_REPEATS
                                          for v in det.values()), det)
    g["tech_complete"] = _complete(recs, "preflight", model)
    g["tech_finite"] = _finite(recs)
    g["tech_repeats_identical"] = _repeat_identical(recs)
    ms = [r["mass_AB"] for r in recs]
    g["tech_label_mass"] = _gate(bool(ms) and min(ms) >= C.MIN_MASS_TECH, dict(min_mass_AB=min(ms, default=None), threshold=C.MIN_MASS_TECH))
    ar = {r["orientation"]: r["d"] for r in recs if r["tech"] == "arith" and r["replicate"] == 1}
    g["tech_arithmetic_both_orders"] = _gate(ar.get(1, -1) > 0 and ar.get(2, 1) < 0, dict(d_by_orientation=ar))
    eps = epsilon(recs)
    g["tech_floor"] = _gate(eps < C.EPS_STOP, dict(max_abs_delta_d=floor(recs), provisional_epsilon=eps, stop_at=C.EPS_STOP))
    g.update(_policy(model, pol))
    info = dict(greedy_answers={r["prompt_id"]: r["greedy_text"] for r in recs if r["replicate"] == 1},
                strict_valid=f"{sum(r['strict_valid'] for r in recs)}/{len(recs)}",
                tech_scores={r["prompt_id"]: dict(d=r["d"], mass_AB=r["mass_AB"], top=r["top"][:5]) for r in recs if r["replicate"] == 1},
                seconds=dict(vocab=env.get("vocab_scan_seconds"), archival=env.get("archival_seconds"), policy=env.get("policy_seconds"),
                             tech=env.get("seconds")), max_memory_allocated_gb=env.get("max_memory_allocated_gb"))
    return dict(tag=C.TAG, stage="preflight", model=model, gates=g, info=info, overall=_overall(g), prompt_sha256=S.all_prompt_sha(),
                presentations_sha256=canonical_sha(d / S_RAW), archival_sha256=canonical_sha(d / "archival.jsonl"),
                policy_sha256=canonical_sha(_dir(root, "policy_benchmark", model) / "policy_teacher_forced.jsonl"))


# ---------- calibration ----------

def paired(recs, key="prompt_id") -> dict:
    """Per content item: s1 (correct/authentic in A), s2 (in B), S, both-order classification inputs (first replicate)."""
    out = {}
    for r in recs:
        if r["replicate"] != 1:
            continue
        item = r[key].rsplit("-o", 1)[0]
        o = out.setdefault(item, {})
        o[f"d{r['orientation']}"] = r["d"]
        o[f"mass{r['orientation']}"] = r["mass_AB"]
        o[f"greedy{r['orientation']}"] = r["greedy_text"]
    for o in out.values():
        o["s1"], o["s2"] = o["d1"], -o["d2"]
        o["S"] = (o["s1"] + o["s2"]) / 2
        o["label_bias"] = (o["d1"] + o["d2"]) / 2
    return out


def classify(s1, s2, eps) -> str:
    if s1 > eps and s2 > eps:
        return "consistent_target"
    if s1 < -eps and s2 < -eps:
        return "consistent_foil"
    return "mixed_or_tied"


def calibration_gate(model: str, root=None) -> dict:
    d = _dir(root, "calibration", model)
    pre = json.load(open(_dir(root, "preflight", model) / "preflight_gates.json", encoding="utf-8"))
    env = _env(d, "calibration")
    recs = read_jsonl(d / S_RAW)
    tech = read_jsonl(_dir(root, "preflight", model) / S_RAW)
    g = dict(preflight_passed=_gate(pre["overall"] == "PASS", pre["overall"]), serving=_serving(env, model),
             prompts=_prompts_ok(recs, {c["prompt_id"]: c for c in S.calibration_cells()}), complete=_complete(recs, "calibration", model),
             finite=_finite(recs))
    eps = epsilon(tech + recs)
    g["floor"] = _gate(eps < C.EPS_STOP, dict(max_abs_delta_d_preflight_and_calibration=floor(tech + recs), epsilon=eps, stop_at=C.EPS_STOP))
    med = statistics.median(r["mass_AB"] for r in recs) if recs else 0.0
    g["label_mass"] = _gate(med >= C.MIN_MEDIAN_MASS_CAL, dict(median_mass_AB=med, min_mass_AB=min((r["mass_AB"] for r in recs), default=None),
                                                               threshold=C.MIN_MEDIAN_MASS_CAL))
    pr = paired(recs)
    tasks = {}
    for it in S.calibration_items():
        p = pr.get(f"cal-{it['cal_id']}")
        if p is None:
            continue
        t = tasks.setdefault(it["task"], dict(n=0, S_correct=0, both_orders=0, items={}))
        t["n"] += 1
        t["S_correct"] += p["S"] > eps
        t["both_orders"] += p["s1"] > eps and p["s2"] > eps
        t["items"][it["cal_id"]] = dict(correct=it["correct"], foil=it["foil"], s1=round(p["s1"], 4), s2=round(p["s2"], 4),
                                        S=round(p["S"], 4), label_bias=round(p["label_bias"], 4), cls=classify(p["s1"], p["s2"], eps),
                                        greedy=[p["greedy1"], p["greedy2"]])
    for task in C.CAL_GATED:
        t = tasks.get(task, dict(n=0, S_correct=0, both_orders=0))
        g[f"cal_{task}"] = _gate(t["n"] == C.CAL_ITEMS_PER_TYPE and t["S_correct"] >= C.CAL_MIN_S_CORRECT and t["both_orders"] >= C.CAL_MIN_BOTH_ORDERS,
                                 dict(n=t["n"], S_correct=t["S_correct"], both_orders=t["both_orders"],
                                      required=[C.CAL_MIN_S_CORRECT, C.CAL_MIN_BOTH_ORDERS]))
    info = dict(tasks=tasks, reported_not_gated=dict(order56={k: v for k, v in tasks.get("order56", {}).items() if k != "items"}),
                strict_valid=f"{sum(r['strict_valid'] for r in recs)}/{len(recs)}",
                mean_label_bias=statistics.mean(p["label_bias"] for p in pr.values()) if pr else None, seconds=env.get("seconds"))
    return dict(tag=C.TAG, stage="calibration", model=model, gates=g, info=info, overall=_overall(g), epsilon=eps,
                prompt_sha256=S.all_prompt_sha(), presentations_sha256=canonical_sha(d / S_RAW))


# ---------- main ----------

def main_checks(model: str, root=None) -> dict:
    d = _dir(root, "main", model)
    cal = json.load(open(_dir(root, "calibration", model) / "calibration_gate.json", encoding="utf-8"))
    env = _env(d, "main")
    recs = read_jsonl(d / S_RAW)
    g = dict(calibration_passed=_gate(cal["overall"] == "PASS" and env.get("epsilon") == cal["epsilon"], dict(epsilon=cal["epsilon"])),
             references_equal_exp28=_gate(verify_references()["ok"], None), serving=_serving(env, model),
             prompts=_prompts_ok(recs, {c["prompt_id"]: c for c in S.prompt_cells()}), complete=_complete(recs, "main", model),
             finite=_finite(recs), deterministic_replicates=_repeat_identical(recs))
    g["raw_files_untampered"] = _gate(env.get("presentations_sha256") == canonical_sha(d / S_RAW), dict(presentations_sha256=canonical_sha(d / S_RAW)))
    ms = [r["mass_AB"] for r in recs if r["replicate"] == 1]
    info = dict(epsilon=cal["epsilon"], main_floor=floor(recs), main_floor_exceeds_epsilon=floor(recs) > cal["epsilon"],
                median_mass_AB=statistics.median(ms) if ms else None,
                low_mass_presentations=sorted(r["prompt_id"] for r in recs if r["replicate"] == 1 and r["mass_AB"] < C.LOW_MASS_FLAG),
                strict_valid=f"{sum(r['strict_valid'] for r in recs)}/{len(recs)}", seconds=env.get("seconds"))
    return dict(tag=C.TAG, stage="main", model=model, gates=g, info=info, overall=_overall(g))


S_RAW = "presentations.jsonl"


def write_preflight_gate(model, root=None):
    return _write(preflight_gates(model, root), _dir(root, "preflight", model), "preflight_gates", f"Preflight, {model} ({C.TAG})")


def write_calibration_gate(model, root=None):
    return _write(calibration_gate(model, root), _dir(root, "calibration", model), "calibration_gate", f"Calibration gate, {model} ({C.TAG})")


def write_main_checks(model, root=None):
    return _write(main_checks(model, root), _dir(root, "main", model), "main_checks", f"Main checks, {model} ({C.TAG})")


def report_md(res: dict, title: str) -> str:
    lines = [f"# {title}\n", f"**Overall: {res['overall']}**\n"]
    if "epsilon" in res:
        lines.append(f"Frozen epsilon for this judge: {res['epsilon']:.4f} log-odds\n")
    lines += ["| Gate | Status | Detail |", "|---|---|---|"]
    for k, v in res["gates"].items():
        lines.append(f"| {k} | {v['status']} | `{json.dumps(v['detail'], default=str)[:600]}` |")
    lines.append(f"\n## Information (not gated)\n\n```json\n{json.dumps(res.get('info', {}), indent=1, default=str)[:12000]}\n```\n")
    return "\n".join(lines) + "\n"
