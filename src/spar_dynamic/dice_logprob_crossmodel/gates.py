"""Preflight gates and main-run checks for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (offline; reads GPU run folders).

Every gate is PASS/FAIL with its evidence. A main run needs a PASS preflight gate for that model; analysis needs PASS main
checks. Nothing here changes a run folder except writing the gate/check files next to it.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from spar_dynamic.dice_crossed_guidance.analysis import _gate, _lp, max_dp, parse_n, read_jsonl, scorer_diff, six
from spar_dynamic.dice_logprob_crossmodel import config as C
from spar_dynamic.dice_logprob_crossmodel import prompts as P

FACES = C.FACES


def file_sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def seq(t) -> str:
    return " ".join(map(str, t))


# ---------- archives (read only) ----------

def archive21() -> dict:
    """Experiment 21 main run: free output and digit-step face log-probs per condition (replicate 1), matched-prefix rows."""
    gen = {}
    for r in read_jsonl(C.EXP21 / "raw_attempts.jsonl"):
        if r["replicate"] == 1:
            gen[r["condition"]] = dict(content=r["raw_choice_content"], prompt_sha256=r["prompt_sha256"],
                                       steps=[s["face_logprobs_exact"] for s in r["raw_logprobs_content"] if s["token"].strip().isdigit()])
    mp = {(r["instruction"], r["history"], r["method"], r["position"]): r["face_logprobs_exact"]
          for r in read_jsonl(C.EXP21 / "matched_prefix.jsonl")}
    return dict(gen=gen, mp=mp)


def archive27(model: str) -> dict:
    raw = read_jsonl(C.EXP27_PRE / model / "raw_attempts.jsonl")
    gen = {}
    for r in raw:
        if r["condition"] in ("G", "F") and r["condition"] not in gen:
            gen[r["condition"]] = dict(content=r["content"], prompt_sha256=r["prompt_sha256"],
                                       steps=[s["face_logprobs"] for s in r["digit_steps"]])
    mp = {(r["instruction"], r["history"], r["method"], r["position"]): r["face_logprobs"]
          for r in read_jsonl(C.EXP27_PRE / model / "matched_prefix.jsonl")}
    return dict(gen=gen, mp=mp)


# ---------- shared checks ----------

def _floor(raw, mp) -> list:
    out = []
    for r in raw:
        if r.get("own_rescored_full_pass"):
            out += [max_dp(x["face_logprobs"], y["face_logprobs"]) for x, y in zip(r["own_rescored"], r["own_rescored_full_pass"])]
    inc = {(x["kind"], x["instruction"], x["history"], x["position"]): x["face_logprobs"] for x in mp if x["method"] == "incremental"}
    out += [max_dp(inc[(x["kind"], x["instruction"], x["history"], x["position"])], x["face_logprobs"])
            for x in mp if x["method"] == "full_pass"]
    return out


def _serving(env, raw, model) -> dict:
    spec = C.MODEL[model]
    want = {c["condition"]: c["prompt_sha256"] for c in P.conditions()}
    ok = env["model_commit"] == spec["revision"] and env["model_id"] == spec["model_id"] and env["prompt_sha256"] == want \
        and all(r["prompt_sha256"] == P.sha256(r["prompt"]) == want[r["condition"]] for r in raw)
    if model == "qwen":
        ok &= env.get("chat_template_sha256") == C.QWEN_CHAT_TEMPLATE_SHA256
    else:
        ok &= env.get("tekken_sha256") == C.MISTRAL_TEKKEN_SHA256
    return _gate(ok, {k: env.get(k) for k in ("model_id", "model_commit", "gpu", "driver", "cuda", "torch", "transformers",
                                               "accelerate", "huggingface_hub", "mistral_common", "chat_template_sha256",
                                               "tekken_sha256", "code_commit")})


def _template(env, raw, model) -> dict:
    rg = env["rendered_G"]
    if model == "qwen":
        ok = rg.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n") and "<|im_start|>system" not in rg
    else:
        ok = rg == "<s>[INST]" + P.GEN + "[/INST]"
    ok &= not any("<think" in r["content"] or "[SYSTEM" in r["content"] for r in raw)
    return _gate(ok, dict(rendered_G=rg))


def _face_tokens(env, model) -> dict:
    fid = {str(f): v for f, v in C.MODEL[model]["face_ids"].items()}
    h = env["g10_history_ids"]
    vs = env.get("vocab_scan")
    ok = {str(k): v for k, v in env["face_ids"].items()} == fid and \
        all(env["face_single_tokens"][str(f)] == [fid[str(f)]] for f in FACES) and \
        h[0::2] == [fid[str(f)] for f in C.QWEN_G_REF] and set(h[1::2]) == {C.SEPARATOR_ID[model]} and len(h) == 19
    detail = dict(face_ids=env["face_ids"], separator_id=h[1] if len(h) > 1 else None)
    if vs is not None:
        ok &= len(vs["variant_face_tokens"]) <= C.VARIANT_FACE_TOKENS_ALLOWED and not vs["multi_digit_ascii_tokens"]
        detail.update(vocab_size=vs["vocab_size"], variant_face_tokens=vs["variant_face_tokens"],
                      multi_digit_ascii_tokens=vs["multi_digit_ascii_tokens"])
    return _gate(ok, detail)


def _finite_and_mass(raw, mp) -> tuple:
    steps = [s["face_logprobs"] for r in raw for s in r["digit_steps"]] + [s["face_logprobs"] for s in mp]
    fin = _gate(all(math.isfinite(v) for s in steps for v in _lp(s)), dict(n_steps=len(steps)))
    gsteps = [s["face_logprobs"] for r in raw if r["condition"] == "G" for s in r["digit_steps"]] + \
        [s["face_logprobs"] for s in mp if s["instruction"] == "G"]
    gm = min(six(s)[1] for s in gsteps)
    mass = _gate(gm >= C.MIN_FACE_MASS_G, dict(n_steps=len(gsteps), min_six_face_mass=gm, threshold=C.MIN_FACE_MASS_G))
    return fin, mass


def _scorer(raw) -> dict:
    sub = [r for r in raw if "rescore_tokens_equal" in r]
    valid_not_equal = [r["trial_id"] for r in sub if parse_n(r["content"], r["n_expected"]) and not r["rescore_tokens_equal"]]
    diffs = [scorer_diff(r) for r in sub if r.get("own_rescored") is not None]
    sd = max(diffs, default=float("inf"))
    return _gate(sd <= C.SCORER_TOL_LOGP and not valid_not_equal,
                 dict(n_rescored=len(diffs), max_abs_logprob_diff=sd, tol=C.SCORER_TOL_LOGP,
                      retokenisation_mismatch_valid=valid_not_equal,
                      retokenisation_mismatch_invalid=[r["trial_id"] for r in sub if not r["rescore_tokens_equal"]]))


def _determinism(raw, conds=("G", "F")) -> dict:
    det = {}
    for cond in conds:
        rs = [r for r in raw if r["condition"] == cond]
        spread = max((abs(a["face_logprobs"][str(f)] - b["face_logprobs"][str(f)])
                      for r in rs[1:] for a, b in zip(r["digit_steps"], rs[0]["digit_steps"]) for f in FACES), default=0.0)
        det[cond] = dict(n=len(rs), outputs=sorted({r["content"] for r in rs}), max_logprob_spread=spread)
    return det


def _regression(model, raw, mp) -> dict:
    """Qwen vs Experiment 21 (all conditions it shares, and its matched prefix); Mistral vs Experiment 27's preflight (G, F, mp)."""
    first = {}
    for r in raw:
        first.setdefault(r["condition"], r)
    arc = archive21() if model == "qwen" else archive27("mistral")
    compared, dps, same = {}, [], True
    for k, a in arc["gen"].items():
        if k not in first or a["prompt_sha256"] != first[k]["prompt_sha256"]:
            continue                                  # Experiment 21's W3-8 and W5-10 are not in this design
        r = first[k]
        eq = r["content"] == a["content"]
        d = [max_dp(x["face_logprobs"], y) for x, y in zip(r["digit_steps"], a["steps"])]
        compared[k] = dict(output=r["content"], archived=a["content"], identical=eq, max_abs_dp=max(d, default=None))
        same &= eq and len(r["digit_steps"]) == len(a["steps"])
        dps += d
    for x in mp:
        key = (x["instruction"], x["history"], "incremental", x["position"])
        if x["kind"] == "mp" and x["method"] == "incremental" and key in arc["mp"]:
            dps.append(max_dp(x["face_logprobs"], arc["mp"][key]))
    want = {"qwen": ("G", "F", "W1-5", *[f"S{k}" for k in range(1, 11)]), "mistral": ("G", "F")}[model]
    ok = same and set(want) <= set(compared) and max(dps) <= C.REPRO_TOL_P
    return _gate(ok, dict(archive="Experiment 21 main" if model == "qwen" else "Experiment 27 Mistral preflight",
                          conditions=compared, n_vectors=len(dps), max_abs_dp=max(dps), tol=C.REPRO_TOL_P))


def _formats(raw) -> dict:
    out = defaultdict(lambda: dict(n=0, valid=0, outputs=set(), finish=set()))
    for r in raw:
        o = out[r["condition"]]
        o["n"] += 1
        o["valid"] += bool(parse_n(r["content"], r["n_expected"])) and r["finish_reason"] == "stop"
        o["outputs"].add(r["content"])
        o["finish"].add(r["finish_reason"])
    return {k: dict(n=v["n"], valid=v["valid"], outputs=sorted(v["outputs"]), finish=sorted(v["finish"])) for k, v in out.items()}


def prediction_mass(raw, mp) -> dict:
    """Minimum raw six-face mass by condition (prediction prompts; reported, not gated)."""
    pm = {}
    for r in raw:
        ms = [six(s["face_logprobs"])[1] for s in r["digit_steps"]]
        if ms:
            pm[r["condition"]] = min(pm.get(r["condition"], 1.0), min(ms))
        first = six(r["steps"][0]["face_logprobs"])[1] if r.get("steps") else None
        if first is not None:
            pm[f"{r['condition']}_first_token"] = min(pm.get(f"{r['condition']}_first_token", 1.0), first)
    for s in mp:
        if s["method"] == "incremental":
            k = f"{s['kind']}_{s['instruction']}|{s['history']}"
            pm[k] = min(pm.get(k, 1.0), six(s["face_logprobs"])[1])
    return pm


def _overall(g):
    return "PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL"


# ---------- preflight ----------

def preflight_gates(model: str, d: Path | None = None) -> dict:
    d = Path(d or C.PRE / model)
    env = json.load(open(d / "env_preflight.json", encoding="utf-8"))
    raw = read_jsonl(d / "raw_attempts.jsonl")
    mp = read_jsonl(d / "matched_prefix.jsonl")
    g = dict(serving=_serving(env, raw, model), template=_template(env, raw, model), face_tokens=_face_tokens(env, model))
    g["face_logprobs_finite"], g["face_mass_direct_generation"] = _finite_and_mass(raw, mp)
    fm = _formats(raw)
    g["format_references"] = _gate(all(fm[k]["valid"] == fm[k]["n"] for k in ("G", "F")), {k: fm[k] for k in ("G", "F")})
    g["format_all_conditions"] = _gate(all(v["valid"] == v["n"] for v in fm.values()) and len(fm) == 15, fm)
    g["scorer_matches_generation"] = _scorer(raw)
    det = _determinism(raw)
    g["determinism"] = _gate(all(len(v["outputs"]) == 1 and v["max_logprob_spread"] == 0.0 and v["n"] == C.PREFLIGHT_REPEATS
                                 for v in det.values()), det)
    fl = _floor(raw, mp)
    g["numerical_floor"] = _gate(max(fl) <= C.FLOOR_STOP_P, dict(max_abs_dp_incremental_vs_full_pass=max(fl), n=len(fl),
                                                                  stop_above=C.FLOOR_STOP_P))
    n_mp = sum(1 for x in mp if x["kind"] == "mp")
    n_w = sum(1 for x in mp if x["kind"] == "window")
    g["matched_prefix_complete"] = _gate(n_mp == 2 * 2 * 2 * C.SEQ_LEN and n_w == sum(2 * 2 * (b - a + 1) for a, b in C.WINDOWS),
                                         dict(mp_rows=n_mp, window_rows=n_w))
    g["archival_regression"] = _regression(model, raw, mp)
    sec = env.get("sec_per_job", {})
    proj_min = sum(sec.get(c["condition"], 0) for c in P.conditions()) * C.N_REPLICATES / 60
    info = dict(sec_per_job=sec, projected_main_generation_minutes=proj_min, matched_seconds=env.get("matched_seconds"),
                vocab_scan_seconds=env.get("vocab_scan_seconds"), floor=max(fl),
                prediction_prompt_min_mass_reported_not_gated=prediction_mass(raw, mp),
                max_memory_allocated_gb=env.get("max_memory_allocated_gb"))
    return dict(tag=C.TAG, stage="preflight", model=model, gates=g, info=info, overall=_overall(g),
                prompt_sha256={c["condition"]: c["prompt_sha256"] for c in P.conditions()},
                raw_attempts_sha256=file_sha(d / "raw_attempts.jsonl"), matched_prefix_sha256=file_sha(d / "matched_prefix.jsonl"))


# ---------- main ----------

def main_checks(model: str, d: Path | None = None, preflight_dir: Path | None = None) -> dict:
    d = Path(d or C.MAIN / model)
    envs = [json.load(open(p, encoding="utf-8")) for p in sorted(d.glob("env_main*.json"))]
    env = max((e for e in envs if e.get("finished_utc")), key=lambda e: e["finished_utc"], default=envs[0])
    raw = read_jsonl(d / "raw_attempts.jsonl")
    mp = read_jsonl(d / "matched_prefix.jsonl")
    pre = read_jsonl(Path(preflight_dir or C.PRE / model) / "raw_attempts.jsonl")
    g = dict(serving=_serving(env, raw, model), template=_template(env, raw, model), face_tokens=_face_tokens(env, model))
    keys = sorted((r["condition"], r["replicate"]) for r in raw)
    want = sorted((c["condition"], i) for c in P.conditions() for i in range(1, C.N_REPLICATES + 1))
    g["complete"] = _gate(keys == want, dict(n=len(raw), expected=len(want), duplicates=len(keys) - len(set(keys))))
    g["face_logprobs_finite"], g["face_mass_direct_generation"] = _finite_and_mass(raw, mp)
    fm = _formats(raw)
    g["format_references"] = _gate(all(fm[k]["valid"] == fm[k]["n"] for k in ("G", "F")), {k: fm[k] for k in ("G", "F")})
    g["scorer_matches_generation"] = _scorer(raw)
    pre_first = {}
    for r in pre:
        pre_first.setdefault(r["condition"], r["content"])
    det = _determinism(raw, [c["condition"] for c in P.conditions()])
    same_as_pre = {k: v["outputs"] == [pre_first.get(k)] for k, v in det.items()}
    g["references_reproducible"] = _gate(all(len(det[k]["outputs"]) == 1 and det[k]["max_logprob_spread"] == 0.0 and same_as_pre[k]
                                             for k in ("G", "F")), {k: det[k] for k in ("G", "F")})
    fl = _floor(raw, mp)
    g["numerical_floor"] = _gate(max(fl) <= C.FLOOR_STOP_P, dict(max_abs_dp_incremental_vs_full_pass=max(fl), n=len(fl)))
    n_mp = sum(1 for x in mp if x["kind"] == "mp")
    n_w = sum(1 for x in mp if x["kind"] == "window")
    g["matched_prefix_complete"] = _gate(n_mp == 80 and n_w == sum(4 * (b - a + 1) for a, b in C.WINDOWS),
                                         dict(mp_rows=n_mp, window_rows=n_w))
    hashes_ok = env.get("raw_attempts_sha256") == file_sha(d / "raw_attempts.jsonl") and \
        env.get("matched_prefix_sha256") == file_sha(d / "matched_prefix.jsonl")
    g["raw_files_untampered"] = _gate(hashes_ok, dict(raw_attempts_sha256=file_sha(d / "raw_attempts.jsonl")))
    info = dict(formats=fm, determinism_all_conditions=det, same_output_as_preflight=same_as_pre, floor=max(fl),
                prediction_prompt_min_mass_reported_not_gated=prediction_mass(raw, mp),
                generation_seconds=env.get("generation_seconds"), gpu=env.get("gpu"))
    return dict(tag=C.TAG, stage="main", model=model, gates=g, info=info, overall=_overall(g))


def report_md(res: dict, title: str) -> str:
    lines = [f"# {title}\n", f"**Overall: {res['overall']}**\n", "| Gate | Status | Detail |", "|---|---|---|"]
    for k, v in res["gates"].items():
        lines.append(f"| {k} | {v['status']} | `{json.dumps(v['detail'], default=str)[:600]}` |")
    if res.get("info"):
        lines.append(f"\nInformation (not gated):\n\n```json\n{json.dumps(res['info'], indent=1, default=str)[:6000]}\n```\n")
    return "\n".join(lines) + "\n"
