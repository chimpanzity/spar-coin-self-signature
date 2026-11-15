"""Experiments 31 and 32 command line (dry-run -> validate -> run -> analyse).

  freeze           verify the ground truth against Experiment 28, then write prompts_frozen.md, design tables and
                   inputs_sha256.json into both experiment folders (refuses to change them once written)
  dryrun           counts, design tables, example prompts, leakage scan and cost estimate; no model
  validate         verify_frozen + ground truth + leakage (also run on the GPU host before any model call)
  run              GPU stage, on the rented host: python -m spar_dynamic.dice_31_32.gpu run --model {qwen,mistral}
  checks           post-run integrity checks per experiment -> <EXP>/results/checks.json + CHECKS.md
  analyse          tables, summary.json and figures for both experiments (idempotent)

Usage: PYTHONPATH=src python -m spar_dynamic.dice_31_32 <phase>
"""

from __future__ import annotations

import csv
import io
import json
import math
import sys
from pathlib import Path

from spar_dynamic.dice_31_32 import analysis as A
from spar_dynamic.dice_31_32 import config as C
from spar_dynamic.dice_31_32 import stimuli as S
from spar_dynamic.dice_31_32.gpu import canonical_sha

PKG = Path(__file__).resolve().parent
FROZEN31 = ("PROTOCOL.md", "prompts_frozen.md", "design_rows.csv", "manifest.json")
FROZEN32 = ("PROTOCOL.md", "prompts_frozen.md", "design_cells.csv", "manifest.json")


def _csv(rows, cols) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def design31_csv() -> str:
    return _csv(S.labeled_rows31(), ["row_id", "scorer_model", "scorer_mode", "source_model", "source_mode", "position", "forced_prefix",
                                     "authentic_face", "context_key", "cross_model", "replay_kind", "prompt_sha256"])


def design32_csv() -> str:
    return _csv(S.cells32(), ["cell_id", "prompt_id", "predictor", "source_id", "condition", "condition_name", "own_source", "prefix5",
                              "sixth_in_prompt", "authentic_sixth", "authentic_seventh", "prompt_sha256"])


METRICS = {
    "p_f": "six-face normalised probability exp(logp_f) / sum over the six bare face tokens 1-6 (conditional on a face being emitted)",
    "digit_mass": "raw full-vocabulary probability mass on the six bare face tokens at the scored boundary (not a probability of a face)",
    "logloss": "-ln p_authentic (nats), six-face normalised; primary predictive quantity",
    "rank": "1 + number of faces with strictly higher p than the authentic face",
    "top_face": f"argmax of p over the six faces; near_tie if the top-two margin < {C.NEAR_TIE_P}",
    "js_bits": "Jensen-Shannon divergence between two six-face normalised distributions, log base 2 (0..1)",
    "boundary": "next-token distribution directly after the rendered assistant prefix (position 1 / first answer token) or after the "
                "separator token that follows the previous face; faces are single bare-digit tokens in both tokenizers and no "
                "whitespace-prefixed face token exists (vocabulary scan), so post-space digits are scored as bare digits",
}


def manifest_frozen(tag) -> dict:
    """The machine-readable frozen manifest (handoff 1.6): expected keys, prompts, provenance, metrics, versions."""
    base = dict(tag=tag, design_source=C.DESIGN_SOURCE, status="frozen before GPU collection",
                models={m: dict(model_id=C.MODEL[m]["model_id"], revision=C.MODEL[m]["revision"], tokenizer=C.MODEL[m]["tokenizer"],
                                face_token_ids=C.MODEL[m]["face_ids"], separator_id=C.SEPARATOR_ID[m]) for m in C.MODELS},
                serving=dict(engine="spar_dynamic.dice_crossed_guidance.models (Experiments 27-30, unchanged)",
                             dtype="bf16 weights/activations, fp32 lm_head and logits", decoding="greedy argmax, temperature 0, no sampling",
                             thinking="disabled (Qwen3 enable_thinking=False)", system_prompt="none", tools="none", batch=1,
                             pins=dict(torch="2.11.0+cu128", transformers="5.22.0", accelerate="1.15.0", huggingface_hub="2.4.0",
                                       mistral_common="1.13.0"), replicates=C.N_REPLICATES, job_order_seed=C.ORDER_SEED),
                ground_truth=dict(source="Experiment 28 main raw_attempts.jsonl (20 identical greedy replicates per sequence)",
                                  sequences={S.source_id(*k): S.seq(v) for k, v in C.REFERENCES.items()}, handoff_table_agrees=True),
                prompt_sha256=S.all_prompt_sha(), metrics=METRICS, gpu_cap_usd=C.GPU_CAP_USD)
    if tag == C.TAG31:
        base.update(counts=C.EXPECTED31, expected_row_keys=[r["row_id"] for r in S.labeled_rows31()],
                    archival_equivalence="all 160 rows computed fresh; rows with an exactly equivalent archival record (Exp 28 "
                                         "within-model matched-prefix, Exp 30 authentic policy rows) are cross-checked within "
                                         f"{C.ARCHIVE_EQUIV_TOL_LOGP} nats and their provenance recorded")
    else:
        base.update(counts=C.EXPECTED32, expected_cell_keys=[c["cell_id"] for c in S.cells32()],
                    targets={S.source_id(s, i): dict(prefix5=S.seq(C.REFERENCES[(s, i)][:5]), authentic_sixth=C.REFERENCES[(s, i)][5],
                                                     authentic_seventh=C.REFERENCES[(s, i)][6]) for s, i in C.SOURCES32})
    return base


def built_files() -> dict:
    return {C.EXP31: {"prompts_frozen.md": S.render_frozen(), "design_rows.csv": design31_csv(),
                      "manifest.json": json.dumps(manifest_frozen(C.TAG31), indent=2) + "\n"},
            C.EXP32: {"prompts_frozen.md": S.render_frozen(), "design_cells.csv": design32_csv(),
                      "manifest.json": json.dumps(manifest_frozen(C.TAG32), indent=2) + "\n"}}


def code_hashes() -> dict:
    from spar_dynamic.dice_31_32.gpu import code_sha
    return code_sha()


def archived_inputs() -> dict:
    files = [C.EXP28_MAIN / m / n for m in C.MODELS for n in ("raw_attempts.jsonl", "matched_prefix.jsonl")]
    files += [C.EXP30_POLICY / m / "policy_teacher_forced.jsonl" for m in C.MODELS]
    return {str(p.relative_to(C.EXP28.parent)).replace("\\", "/"): canonical_sha(p) for p in files}


def freeze():
    S.ground_truth()
    ha = S.handoff_agreement()
    if not ha["all_equal"]:
        raise SystemExit(f"handoff table differs from the archive; resolve before freezing: {json.dumps(ha, indent=1)}")
    if S.leakage_findings():
        raise SystemExit(f"leakage: {S.leakage_findings()}")
    for exp, frozen in ((C.EXP31, FROZEN31), (C.EXP32, FROZEN32)):
        if (exp / "inputs_sha256.json").exists():
            raise SystemExit(f"{exp.name} is already frozen")
        if not (exp / "PROTOCOL.md").exists():
            raise SystemExit(f"{exp.name}/PROTOCOL.md must be written before freezing")
        for name, text in built_files()[exp].items():
            (exp / name).write_text(text, encoding="utf-8", newline="\n")
        json.dump(dict(files={n: canonical_sha(exp / n) for n in frozen}, prompt_sha256=S.all_prompt_sha(), code_sha256=code_hashes(),
                       archived_inputs=archived_inputs(), handoff_agreement=ha),
                  open(exp / "inputs_sha256.json", "w", encoding="utf-8", newline="\n"), indent=2)
        print(f"froze {exp.name}")


def verify_frozen(check_code=True):
    bad = []
    for exp, frozen in ((C.EXP31, FROZEN31), (C.EXP32, FROZEN32)):
        old = json.load(open(exp / "inputs_sha256.json", encoding="utf-8"))
        bad += [f"{exp.name}/{n}" for n in frozen if canonical_sha(exp / n) != old["files"][n]]
        for name, text in built_files()[exp].items():
            if text != (exp / name).read_text(encoding="utf-8").replace("\r\n", "\n"):
                bad.append(f"{exp.name}/{name} built by the code differs from the frozen file")
        if old["prompt_sha256"] != S.all_prompt_sha():
            bad.append(f"{exp.name}: prompt hashes differ")
        if old["archived_inputs"] != archived_inputs():
            bad.append(f"{exp.name}: archived Experiment 28/30 inputs changed")
        if check_code and old["code_sha256"] != code_hashes():
            bad.append(f"{exp.name}: code differs from the frozen code {[k for k in old['code_sha256'] if old['code_sha256'][k] != code_hashes().get(k)]}")
    if bad:
        raise SystemExit(f"frozen inputs changed: {bad}")


def validate():
    verify_frozen()
    S.ground_truth()
    assert not S.leakage_findings()
    print("validate: frozen files, code, ground truth and prompts OK")


def estimate() -> dict:
    """Experiment 30's North Carolina host: setup + download ~15 min, each model load ~3 min; the scored work is seconds."""
    per_model_min = dict(load=3, vocab=1, archival=1, exp31=1, exp32=3)
    hours = (15 + sum(per_model_min.values()) * 2 + 10) / 60
    return dict(per_model_minutes=per_model_min, total_hours=round(hours, 2), usd_at_exp30_rates=round(hours * 1.97 + 103 * 0.013, 2),
                cap=C.GPU_CAP_USD)


def dryrun():
    rows, cells = S.labeled_rows31(), S.cells32()
    ctx = {r["context_key"] for r in rows}
    print(json.dumps(dict(exp31=dict(labeled_rows=len(rows), cross_model_rows=sum(r["cross_model"] for r in rows), streams=len(S.streams31()),
                                     unique_contexts=len(ctx), replay_rows=sum(r["replay_kind"].endswith("replay") for r in rows)),
                          exp32=dict(cells=len(cells), unique_prompts=len(S.prompts32())), leakage=S.leakage_findings(),
                          handoff_agreement=S.handoff_agreement()["all_equal"], estimate=estimate()), indent=2))
    for (s, i), x in C.REFERENCES.items():
        print(S.source_id(s, i), S.seq(x), "| heuristic:", [S.remaining_faces(x, j) for j in C.POSITIONS])
    for pid, v in S.prompts32().items():
        print(f"\n=== {pid}\n{v['prompt']}")


# ---------- post-run checks ----------

def _chk(ok, detail=None):
    return dict(status="PASS" if ok else "FAIL", detail=detail)


def checks31(root=None) -> dict:
    root = Path(root or C.EXP31)
    g = {}
    g["ground_truth"] = _chk(S.ground_truth() == {k: tuple(v) for k, v in C.REFERENCES.items()})
    envs = {m: json.load(open(root / "raw" / m / "env.json", encoding="utf-8")) for m in C.MODELS if (root / "raw" / m / "env.json").exists()}
    g["both_models_ran"] = _chk(set(envs) == set(C.MODELS), sorted(envs))
    from spar_dynamic.dice_logprob_crossmodel import config as C28
    g["serving_identity"] = _chk(all(e["model_commit"] == C.MODEL[m]["revision"] for m, e in envs.items())
                                 and envs.get("qwen", {}).get("chat_template_sha256") == C28.QWEN_CHAT_TEMPLATE_SHA256
                                 and envs.get("mistral", {}).get("tekken_sha256") == C28.MISTRAL_TEKKEN_SHA256)
    g["no_variant_face_tokens"] = _chk(all(not e["vocab_scan"]["variant_face_tokens"] for e in envs.values()))
    g["archival_reproduces_exp28"] = _chk(all(e["archival_check"]["ok"] for e in envs.values()),
                                          {m: {k: dict(max_dp=v["max_dp_vs_exp28"], equal=v["equal"]) for k, v in e["archival_check"]["per_instruction"].items()}
                                           for m, e in envs.items()})
    g["raw_file_hashes"] = _chk(all(canonical_sha(root / "raw" / m / "streams.jsonl") == e.get("streams_sha256") for m, e in envs.items()))
    g["prompt_hashes"] = _chk(all(e["prompt_sha256"] == S.all_prompt_sha() for e in envs.values()))
    data = A.load31(root)
    streams = [s for m in data.values() for s in m["streams"]]
    g["stream_records"] = _chk(len(streams) == 3 * C.EXPECTED31["streams"], len(streams))
    rows = A.rows31(data)
    g["labeled_rows_160"] = _chk(len(rows) == 160 and sum(r["cross_model"] for r in rows) == 80 and len({r["row_id"] for r in rows}) == 160)
    vals = [v for s in streams for p in s["positions"] for v in p["face_logprobs"].values()]
    g["finite"] = _chk(all(math.isfinite(v) for v in vals))
    g["mass_in_0_1"] = _chk(all(-1e-6 <= r["digit_mass"] <= 1 + 1e-6 for r in rows))
    g["normalised_sum_1"] = _chk(all(abs(sum(r[f"p{f}"] for f in A.FACES) - 1) < 1e-9 for r in rows))
    g["logprob_consistency"] = _chk(all(abs(math.exp(r["raw_logp_authentic"]) / r["digit_mass"] - r["p_authentic"]) < 1e-9 for r in rows))
    from spar_dynamic.dice_crossed_guidance.analysis import js_bits
    pv = [[r[f"p{f}"] for f in A.FACES] for r in rows]
    js_ok = all(js_bits(p, p) < C.JS_TOL for p in pv) and all(0 <= js_bits(p, q) <= 1 + 1e-12 for p in pv[:40] for q in pv[:40])
    g["js_identity_and_bounds"] = _chk(js_ok)
    ok_idx = True
    for s in streams:
        for p in s["positions"]:
            ok_idx &= p["n_forced"] == 2 * (p["position"] - 1) and len(p["forced_prefix"].split()) == p["position"] - 1
            ok_idx &= p["forced_prefix"] == S.seq(C.REFERENCES[(s["source_model"], s["source_mode"])][:p["position"] - 1])
    g["indexing_prefix_j_minus_1_no_target"] = _chk(ok_idx)
    cc = A.context_check(rows)
    g["identical_contexts_identical_scores"] = _chk(not cc["mismatched_contexts"], cc)
    g["replicates_bit_identical"] = _chk(all(r["rep2_identical"] for r in rows))
    fl = max(r["floor_max_dp"] for r in rows)
    g["floor_incremental_vs_full_pass"] = _chk(fl <= C.FLOOR_STOP_P, dict(max_dp=fl))
    arch = [r for r in rows if r["archival_equivalents"]]
    g["archival_equivalents_agree"] = _chk(all(r["archival_max_abs_dlogp"] <= C.ARCHIVE_EQUIV_TOL_LOGP for r in arch),
                                           dict(rows_with_archive=len(arch), max_abs_dlogp=max((r["archival_max_abs_dlogp"] for r in arch), default=None)))
    g["no_model_names_in_prompts"] = _chk(not [x for x in S.leakage_findings() if x.startswith("exp31")])
    return dict(experiment=C.TAG31, overall="PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL", checks=g)


def checks32(root=None) -> dict:
    root = Path(root or C.EXP32)
    g = {}
    envs = {m: json.load(open(root / "raw" / m / "env.json", encoding="utf-8")) for m in C.MODELS if (root / "raw" / m / "env.json").exists()}
    g["both_models_ran"] = _chk(set(envs) == set(C.MODELS) and all("cells_sha256" in e for e in envs.values()), sorted(envs))
    g["raw_file_hashes"] = _chk(all(canonical_sha(root / "raw" / m / "cells.jsonl") == e.get("cells_sha256") for m, e in envs.items()))
    g["prompt_hashes"] = _chk(all(e["prompt_sha256"] == S.all_prompt_sha() for e in envs.values()))
    data = A.load32(root)
    recs = [r for v in data.values() for r in v]
    g["records"] = _chk(len(recs) == 2 * 6 * C.N_REPLICATES, len(recs))
    cells = A.cells32(data)
    g["cells_12"] = _chk(len(cells) == 12 and len({c["cell_id"] for c in cells}) == 12)
    frozen = {c["prompt_id"]: c["prompt_sha256"] for c in S.cells32()}
    g["identical_stimuli_both_predictors"] = _chk(all(r["prompt_sha256"] == frozen[r["prompt_id"]] for r in recs))
    g["no_leakage"] = _chk(not S.leakage_findings(), S.leakage_findings())
    ok = True
    for r in recs:
        if r["condition"] == "A" and r.get("free_roll7"):
            ok &= r["free_roll7"]["forced_ids"] == r["free"]["generated_ids"][:2]
        if r["condition"] == "A":
            ok &= "constrained_roll7" in r and r["constrained_roll7"]["n_forced"] == 2
    g["A_scored_after_predicted_sixth"] = _chk(ok)
    g["B_five_rolls_C_authentic_sixth"] = _chk(all(("The first six rolls" in r["prompt"]) == (r["condition"] == "C") for r in recs))
    g["replicates_bit_identical"] = _chk(all(c["replicates_identical"] for c in cells))
    g["first_boundary_matches_generation"] = _chk(all(c["first_boundary_matches_generation"] for c in cells))
    vals = [v for r in recs for v in r["first_boundary"]["face_logprobs"].values()]
    g["finite"] = _chk(all(math.isfinite(v) for v in vals))
    fl = max(max(c["floor_max_dp_first"], c.get("floor_max_dp_constrained", 0)) for c in cells)
    g["floor_incremental_vs_full_pass"] = _chk(fl <= C.FLOOR_STOP_P, dict(max_dp=fl))
    g["constrained_equals_free_when_defined"] = _chk(all(c["constrained_equals_free"] for c in cells if c["condition"] == "A" and c["free_roll7_defined"]))
    return dict(experiment=C.TAG32, overall="PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL", checks=g)


def write_checks():
    for exp, fn in ((C.EXP31, checks31), (C.EXP32, checks32)):
        res = fn()
        (exp / "results").mkdir(parents=True, exist_ok=True)
        json.dump(res, open(exp / "results" / "checks.json", "w", encoding="utf-8", newline="\n"), indent=2)
        md = [f"# {res['experiment']} post-run checks: **{res['overall']}**\n", "| Check | Status | Detail |", "|---|---|---|"]
        md += [f"| {k} | {v['status']} | {json.dumps(v['detail'])[:160] if v['detail'] is not None else ''} |" for k, v in res["checks"].items()]
        (exp / "results" / "CHECKS.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
        print(exp.name, res["overall"], [k for k, v in res["checks"].items() if v["status"] != "PASS"])


# ---------- analysis outputs ----------

def _write_csv(path, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    for r in rows[1:]:
        cols += [k for k in r if k not in cols]
    conv = [{k: (" | ".join(v) if isinstance(v, list) else v) for k, v in r.items()} for r in rows]
    Path(path).write_text(_csv(conv, cols), encoding="utf-8", newline="\n")


def analyse():
    from spar_dynamic.dice_31_32 import figures as Fg
    r31 = A.analyse31()
    out = C.EXP31 / "results"
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "labeled_rows.csv", r31["rows"])
    _write_csv(out / "crossed_own_vs_other.csv", r31["crossed"])
    _write_csv(out / "reciprocal_contrast.csv", r31["reciprocal"])
    _write_csv(out / "js_between_scorers.csv", r31["js"]["between"])
    _write_csv(out / "js_G_vs_F_within_scorer.csv", r31["js"]["within"])
    _write_csv(out / "js_between_summary.csv", r31["js"]["between_summary"])
    _write_csv(out / "js_within_summary.csv", r31["js"]["within_summary"])
    _write_csv(out / "heuristic_summary.csv", r31["heuristic"])
    _write_csv(out / "own_vs_other_discriminating.csv", r31["own_vs_other_discriminating"])
    json.dump({k: v for k, v in r31.items() if k not in ("rows",)} | dict(js=dict(between_summary=r31["js"]["between_summary"],
                                                                                   within_summary=r31["js"]["within_summary"])),
              open(out / "summary.json", "w", encoding="utf-8", newline="\n"), indent=2)
    Fg.all31(r31, C.EXP31 / "figures")
    r32 = A.analyse32()
    out = C.EXP32 / "results"
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "cells_12.csv", r32["cells"])
    _write_csv(out / "contrasts.csv", r32["contrasts"])
    json.dump(r32, open(out / "summary.json", "w", encoding="utf-8", newline="\n"), indent=2)
    Fg.all32(r32, C.EXP32 / "figures")
    print(json.dumps(dict(exp31=r31["integrity"], reciprocal=r31["reciprocal"], exp32=r32["integrity"]), indent=1))


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "dryrun"
    {"freeze": freeze, "dryrun": dryrun, "validate": validate, "checks": write_checks, "analyse": analyse}[phase]()
