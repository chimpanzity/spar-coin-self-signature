"""Preflight gates and main-run checks for SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1 (offline; reads GPU run folders).

Hard gates are PASS/FAIL. Free-output format and prediction-prompt face mass are reported, not gated (Experiment 28 amendment
v1.1, predeclared in this protocol), except for the frozen stop-for-review rule on teacher-forced mass.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from spar_dynamic.dice_bidirectional_completion import config as C
from spar_dynamic.dice_bidirectional_completion import prompts as P
from spar_dynamic.dice_crossed_guidance.analysis import _gate, _lp, max_dp, parse_n, read_jsonl, six
from spar_dynamic.dice_logprob_crossmodel import config as C28
from spar_dynamic.dice_logprob_crossmodel.gates import _determinism, _face_tokens, _scorer, _template

FACES = C.FACES


def canonical_sha(p) -> str:
    """SHA-256 of a text file with CRLF normalised to LF (= the committed git blob on this Windows checkout)."""
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def file_sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _overall(g):
    return "PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL"


def verify_references() -> dict:
    """The four ground truths against Experiment 28's raw main records (every replicate)."""
    out, ok = {}, True
    for s in C.MODELS:
        raw = read_jsonl(C.EXP28_MAIN / s / "raw_attempts.jsonl")
        for i in C.INSTRUCTIONS:
            outs = sorted({r["content"] for r in raw if r["condition"] == i})
            want = P.seq(C.REFERENCES[(s, i)])
            out[f"{s}-{i}"] = dict(exp28_outputs=outs, n=sum(r["condition"] == i for r in raw), frozen=want)
            ok &= outs == [want]
    return dict(ok=ok, detail=out)


def archive28(model) -> dict:
    gen = {}
    for r in read_jsonl(C.EXP28_MAIN / model / "raw_attempts.jsonl"):
        if r["condition"] in C.INSTRUCTIONS and r["condition"] not in gen:
            gen[r["condition"]] = dict(content=r["content"], prompt_sha256=r["prompt_sha256"], steps=[s["face_logprobs"] for s in r["digit_steps"]])
    return gen


def _serving(env, raw, model) -> dict:
    spec = C.MODEL[model]
    want = {c["prompt_id"]: c["prompt_sha256"] for c in P.prompt_cells()}
    cells = P.by_cell()
    arch = {k: P.sha256(v) for k, v in P.SOURCE_INSTRUCTION.items()}
    ok = env["model_commit"] == spec["revision"] and env["model_id"] == spec["model_id"] and env["prompt_sha256"] == want \
        and env["archival_prompt_sha256"] == arch
    for r in raw:
        ok &= r["prompt_sha256"] == P.sha256(r["prompt"]) == (cells[r["job"]]["prompt_sha256"] if r["kind"] == "cell" else arch[r["job"]])
    if model == "qwen":
        ok &= env.get("chat_template_sha256") == C28.QWEN_CHAT_TEMPLATE_SHA256
    else:
        ok &= env.get("tekken_sha256") == C28.MISTRAL_TEKKEN_SHA256
    return _gate(ok, {k: env.get(k) for k in ("model_id", "model_commit", "gpu", "driver", "cuda", "torch", "transformers", "accelerate",
                                               "huggingface_hub", "mistral_common", "chat_template_sha256", "tekken_sha256", "code_commit")})


def _finite(raw, tf) -> dict:
    vals = [v for r in raw for s in r["digit_steps"] for v in _lp(s["face_logprobs"])] + [v for x in tf for v in _lp(x["face_logprobs"])]
    sums = [sum(six(x["face_logprobs"])[0]) for x in tf]
    return _gate(all(math.isfinite(v) for v in vals) and all(abs(s - 1) < 1e-9 for s in sums),
                 dict(n_values=len(vals), n_tf_rows=len(tf), max_abs_p6_sum_error=max((abs(s - 1) for s in sums), default=0.0)))


def _g_mass(raw) -> dict:
    ms = [six(s["face_logprobs"])[1] for r in raw if r["kind"] == "archival" and r["job"] == "G" for s in r["digit_steps"]]
    return _gate(bool(ms) and min(ms) >= C.MIN_FACE_MASS_G, dict(n=len(ms), min_six_face_mass=min(ms, default=None)))


def _regression(model, raw) -> dict:
    arc = archive28(model)
    out, dps, ok = {}, [], True
    for k in C.INSTRUCTIONS:
        rs = [r for r in raw if r["kind"] == "archival" and r["job"] == k]
        for r in rs:
            same = r["content"] == arc[k]["content"] == P.seq(C.REFERENCES[(model, k)]) and len(r["digit_steps"]) == len(arc[k]["steps"])
            d = [max_dp(x["face_logprobs"], y) for x, y in zip(r["digit_steps"], arc[k]["steps"])]
            ok &= same and bool(rs)
            dps += d
        out[k] = dict(outputs=sorted({r["content"] for r in rs}), archived=arc[k]["content"], n=len(rs))
    ok &= bool(dps) and max(dps) <= C.REPRO_TOL_P
    return _gate(ok, dict(archive="Experiment 28 main", conditions=out, n_vectors=len(dps), max_abs_dp=max(dps, default=None), tol=C.REPRO_TOL_P))


def _mapping(tf, expected_cells) -> dict:
    """Every expected cell has exactly n_missing incremental and full-pass rows, forced faces equal the frozen target."""
    cells = P.by_cell()
    bad, have = [], defaultdict(lambda: defaultdict(list))
    for x in tf:
        c = cells[x["cell_id"]]
        have[x["method"]][x["cell_id"]].append(x["output_step"])
        if not (x["original_position"] == c["missing_positions"][x["output_step"] - 1] and
                x["true_face"] == C.REFERENCES[(c["source"], c["source_instruction"])][x["original_position"] - 1] and
                x["prompt_sha256"] == c["prompt_sha256"] and x["forced_prefix"] == " ".join(c["target"].split(" ")[:x["output_step"] - 1])):
            bad.append((x["cell_id"], x["output_step"]))
    for m in ("incremental", "full_pass"):
        for cid in expected_cells:
            if sorted(have[m][cid]) != list(range(1, cells[cid]["n_missing"] + 1)):
                bad.append((m, cid, "rows"))
        bad += [(m, cid, "unexpected") for cid in have[m] if cid not in expected_cells]
    n_inc = sum(len(v) for v in have["incremental"].values())
    return _gate(not bad, dict(cells=len(expected_cells), incremental_rows=n_inc,
                               expected_rows=sum(cells[c]["n_missing"] for c in expected_cells), problems=bad[:20]))


def _floor(raw, tf) -> dict:
    fl = []
    for r in raw:
        if r.get("own_rescored_full_pass"):
            fl += [max_dp(x["face_logprobs"], y["face_logprobs"]) for x, y in zip(r["own_rescored"], r["own_rescored_full_pass"])]
    inc = {(x["cell_id"], x["output_step"]): x["face_logprobs"] for x in tf if x["method"] == "incremental"}
    fl += [max_dp(inc[(x["cell_id"], x["output_step"])], x["face_logprobs"]) for x in tf if x["method"] == "full_pass"]
    return _gate(bool(fl) and max(fl) <= C.FLOOR_STOP_P, dict(max_abs_dp_incremental_vs_full_pass=max(fl, default=None), n=len(fl),
                                                               stop_above=C.FLOOR_STOP_P))


def _tf_mass(tf) -> dict:
    """Frozen stop-for-review rule: median raw mass < TF_MASS_REVIEW_MEDIAN, or a cell whose every row is < TF_MASS_REVIEW_CELL."""
    inc = [x for x in tf if x["method"] == "incremental"]
    ms = [six(x["face_logprobs"])[1] for x in inc]
    by = defaultdict(list)
    for x, m in zip(inc, ms):
        by[x["cell_id"]].append(m)
    dead = sorted(c for c, v in by.items() if max(v) < C.TF_MASS_REVIEW_CELL)
    med = statistics.median(ms) if ms else 0.0
    return _gate(med >= C.TF_MASS_REVIEW_MEDIAN and not dead,
                 dict(median_raw_mass=med, min_raw_mass=min(ms, default=None), cells_all_below=dead,
                      thresholds=[C.TF_MASS_REVIEW_MEDIAN, C.TF_MASS_REVIEW_CELL]))


def _no_source_names(raw) -> dict:
    leaks = [r["trial_id"] for r in raw if r["kind"] == "cell" and any(w in r["prompt"].lower() for w in ("qwen", "mistral", "alibaba"))]
    return _gate(not leaks, dict(leaks=leaks))


def formats(raw) -> dict:
    out = {}
    for r in raw:
        if r["kind"] != "cell":
            continue
        o = out.setdefault(r["cell_id"], dict(n=0, valid=0, outputs=set(), first_token_mass=None))
        o["n"] += 1
        o["valid"] += bool(parse_n(r["content"], r["n_expected"])) and r["finish_reason"] == "stop"
        o["outputs"].add(r["content"])
        o["first_token_mass"] = round(six(r["steps"][0]["face_logprobs"])[1], 4) if r["steps"] else None
    return {k: dict(v, outputs=sorted(v["outputs"])) for k, v in out.items()}


def _examples(raw) -> dict:
    fm = formats(raw)
    valid = [(k, v["outputs"][0]) for k, v in fm.items() if v["valid"] == v["n"]][:4]
    invalid = [(k, v["outputs"][0][:300]) for k, v in fm.items() if v["valid"] < v["n"]][:4]
    return dict(valid=valid, invalid=invalid, n_cells=len(fm), n_cells_all_valid=sum(v["valid"] == v["n"] for v in fm.values()))


def preflight_gates(model: str, d: Path | None = None) -> dict:
    d = Path(d or C.PRE / model)
    env = json.load(open(d / "env_preflight.json", encoding="utf-8"))
    raw = read_jsonl(d / "raw_attempts.jsonl")
    tf = read_jsonl(d / "teacher_forced.jsonl")
    expected = [c["cell_id"] for c in P.preflight_cells(model)]
    ref = verify_references()
    g = dict(references_equal_exp28=_gate(ref["ok"], ref["detail"]), serving=_serving(env, raw, model),
             template=_template(env, raw, model), face_tokens=_face_tokens(env, model), face_logprobs_finite=_finite(raw, tf),
             face_mass_archival_G=_g_mass(raw), archival_regression=_regression(model, raw))
    det = _determinism([r for r in raw if r["kind"] == "archival"])
    g["archival_determinism"] = _gate(all(len(v["outputs"]) == 1 and v["max_logprob_spread"] == 0.0 and v["n"] == C.ARCHIVAL_REPEATS
                                          for v in det.values()), det)
    calls = sorted(r["job"] for r in raw if r["kind"] == "cell")
    g["preflight_calls_complete"] = _gate(calls == sorted(expected), dict(n=len(calls), expected=len(expected)))
    g["scorer_matches_generation"] = _scorer(raw)
    g["target_mapping"] = _mapping(tf, expected)
    g["numerical_floor"] = _floor(raw, tf)
    g["teacher_forced_mass_review"] = _tf_mass(tf)
    g["no_source_names_in_prompts"] = _no_source_names(raw)
    sec = [r["latency_ms"] / 1000 for r in raw if r["kind"] == "cell"]
    info = dict(format_reported_not_gated=formats(raw), examples=_examples(raw), mean_sec_per_cell_call=sum(sec) / len(sec) if sec else None,
                projected_main_generation_minutes=(sum(sec) / len(sec)) * 76 * C.N_REPLICATES / 60 if sec else None,
                generation_seconds=env.get("generation_seconds"), teacher_forced_seconds=env.get("teacher_forced_seconds"),
                max_memory_allocated_gb=env.get("max_memory_allocated_gb"))
    return dict(tag=C.TAG, stage="preflight", model=model, gates=g, info=info, overall=_overall(g),
                prompt_sha256={c["prompt_id"]: c["prompt_sha256"] for c in P.prompt_cells()},
                raw_attempts_sha256=file_sha(d / "raw_attempts.jsonl"), teacher_forced_sha256=file_sha(d / "teacher_forced.jsonl"))


def main_checks(model: str, d: Path | None = None) -> dict:
    d = Path(d or C.MAIN / model)
    envs = [json.load(open(p, encoding="utf-8")) for p in sorted(d.glob("env_main*.json"))]
    env = max((e for e in envs if e.get("finished_utc")), key=lambda e: e["finished_utc"], default=envs[0])
    raw = read_jsonl(d / "raw_attempts.jsonl")
    tf = read_jsonl(d / "teacher_forced.jsonl")
    mine = [c["cell_id"] for c in P.conditions() if c["predictor"] == model]
    ref = verify_references()
    g = dict(references_equal_exp28=_gate(ref["ok"], ref["detail"]), serving=_serving(env, raw, model),
             template=_template(env, raw, model), face_tokens=_face_tokens(env, model))
    keys = sorted((r["job"], r["replicate"]) for r in raw)
    want = sorted([(c, i) for c in mine for i in range(1, C.N_REPLICATES + 1)] +
                  [(k, i) for k in C.INSTRUCTIONS for i in range(1, C.ARCHIVAL_REPEATS + 1)])
    g["complete"] = _gate(keys == want, dict(n=len(keys), expected=len(want), cell_calls=sum(r["kind"] == "cell" for r in raw),
                                             distinct_cells=len({r["job"] for r in raw if r["kind"] == "cell"})))
    g["face_logprobs_finite"] = _finite(raw, tf)
    g["face_mass_archival_G"] = _g_mass(raw)
    g["archival_regression"] = _regression(model, raw)
    det = _determinism(raw, sorted({r["condition"] for r in raw}))
    g["deterministic_replicates"] = _gate(all(len(v["outputs"]) == 1 and v["max_logprob_spread"] == 0.0 for v in det.values()),
                                          {k: v for k, v in det.items() if len(v["outputs"]) != 1 or v["max_logprob_spread"] != 0.0})
    g["scorer_matches_generation"] = _scorer(raw)
    g["target_mapping"] = _mapping(tf, mine)
    g["numerical_floor"] = _floor(raw, tf)
    g["teacher_forced_mass_review"] = _tf_mass(tf)
    g["no_source_names_in_prompts"] = _no_source_names(raw)
    g["raw_files_untampered"] = _gate(env.get("raw_attempts_sha256") == file_sha(d / "raw_attempts.jsonl") and
                                      env.get("teacher_forced_sha256") == file_sha(d / "teacher_forced.jsonl"),
                                      dict(raw_attempts_sha256=file_sha(d / "raw_attempts.jsonl")))
    info = dict(format_reported_not_gated=formats(raw), examples=_examples(raw), generation_seconds=env.get("generation_seconds"))
    return dict(tag=C.TAG, stage="main", model=model, gates=g, info=info, overall=_overall(g))


def report_md(res: dict, title: str) -> str:
    lines = [f"# {title}\n", f"**Overall: {res['overall']}**\n", "| Gate | Status | Detail |", "|---|---|---|"]
    for k, v in res["gates"].items():
        lines.append(f"| {k} | {v['status']} | `{json.dumps(v['detail'], default=str)[:600]}` |")
    ex = res.get("info", {}).get("examples")
    if ex:
        lines.append(f"\n## Example outputs ({ex['n_cells_all_valid']}/{ex['n_cells']} cells strictly valid; format is reported, not gated)\n")
        for kind in ("valid", "invalid"):
            lines.append(f"\n**{kind.capitalize()}:**\n")
            lines += [f"- `{cid}`: `{json.dumps(out)}`" for cid, out in ex[kind]] or ["- none"]
    info = {k: v for k, v in res.get("info", {}).items() if k not in ("examples",)}
    lines.append(f"\n## Information (not gated)\n\n```json\n{json.dumps(info, indent=1, default=str)[:8000]}\n```\n")
    return "\n".join(lines) + "\n"
