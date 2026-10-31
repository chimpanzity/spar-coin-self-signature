"""SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1 command line.

  freeze                  PROTOCOL_FROZEN.md, prompts_frozen.md, conditions.csv, DATA_DICTIONARY.md, manifest_template.json,
                          inputs_sha256.json (refuses to change them once written; verifies the four references first)
  dryrun                  counts, example prompts, preflight subset and cost estimate; no model
  preflight / main        GPU stages (on the rented host): same as `python -m ...gpu <stage> --model M --out D [--gate G]`
  gate_preflight <model>  preflight/<model>/ -> preflight_gates.json + PREFLIGHT_REPORT.md
  gate_main <model>       main/<model>/ -> main_checks.json + MAIN_CHECKS.md
  analyse                 needs PASS main checks for both predictors; tables, summary.json, figures in analysis/

Usage: PYTHONPATH=src python -m spar_dynamic.dice_bidirectional_completion <phase> [args]
"""

from __future__ import annotations

import csv
import json
import runpy
import sys
from pathlib import Path

from spar_dynamic.dice_bidirectional_completion import config as C
from spar_dynamic.dice_bidirectional_completion import gates as Gt
from spar_dynamic.dice_bidirectional_completion import prompts as P

SRC = Path(__file__).resolve().parent
FROZEN = ("PROTOCOL_FROZEN.md", "prompts_frozen.md", "conditions.csv", "DATA_DICTIONARY.md", "manifest_template.json")


def counts() -> dict:
    cs, pc = P.conditions(), P.prompt_cells()
    return dict(cells=len(cs), primary_cells=sum(c["task_type"] == "primary" for c in cs),
                supplementary_cells=sum(c["task_type"] == "middle" for c in cs), prompt_slots=len(pc),
                distinct_prompt_texts=len({c["prompt_sha256"] for c in pc}), main_generations=len(cs) * C.N_REPLICATES,
                archival_generations=2 * len(C.MODELS) * C.ARCHIVAL_REPEATS, tf_rows=sum(c["n_missing"] for c in cs),
                tf_rows_primary=sum(c["n_missing"] for c in cs if c["task_type"] == "primary"),
                tf_rows_supplementary=sum(c["n_missing"] for c in cs if c["task_type"] == "middle"),
                preflight_cells=sum(len(P.preflight_cells(m)) for m in C.MODELS))


def duplicate_prompts() -> list:
    by = {}
    for c in P.prompt_cells():
        by.setdefault(c["prompt_sha256"], []).append(c["prompt_id"])
    return [v for v in by.values() if len(v) > 1]


def protocol_text() -> str:
    n = counts()
    dup = duplicate_prompts()
    q, m = C.MODEL["qwen"], C.MODEL["mistral"]
    refs = "\n".join(f"| {s} | {i} | `{P.seq(C.REFERENCES[(s, i)])}` |" for s in C.MODELS for i in C.INSTRUCTIONS)
    return f"""# {C.TAG}: frozen protocol

Design source: {C.DESIGN_SOURCE}. Direct sequel to Experiment 28; Experiments 26 and 27 are historical controls. Experiments
01-28 are read, never written. A descriptive, fixed-reference behavioural assay: 4 distinct ground-truth strings. No
replicate-, position- or source-based significance tests. Behaviour and output probabilities only; no mechanistic analysis.

## Questions and predeclared expectations (handoff section 1)
- H1, forward conditioning: loss at the next missing roll may fall with informative revealed prefixes (not introspection).
- H2, self-specific advantage: predictor x source interaction favouring diagonal cells beyond source difficulty, separately for
  G/F and forward/backward.
- H3, direction asymmetry: backward reconstruction (known suffix, missing prefix emitted left to right) differs from forward
  continuation. Retrospective inference in ordinary output order, not reverse-time generation.
- H4, calibration: free completions and teacher-forced six-face probabilities may diverge; both are reported.
- Supplementary (v1.1): the revealed middle (positions 3-8) may help the late tail (9, 10) more than the early head (1, 2).

## Ground truth (Experiment 28 main greedy outputs; verified against every Experiment 28 main replicate at freeze)
| Source | Instruction | Sequence |
|---|---|---|
{refs}

## Models and serving
Experiment 28 exactly: `{q['model_id']}` @ `{q['revision']}` (Qwen3 template, enable_thinking=False) and `{m['model_id']}` @
`{m['revision']}` (mistral_common tekken, text path only), via Experiment 27/28's engine, unchanged. bf16 weights/activations,
fp32 output layer and logits, batch 1, KV-cache incremental decoding, full-vocabulary log-softmax, greedy argmax, no sampling,
no logit processors, no tools, no system message, max {C.MAX_NEW_TOKENS} new tokens. Face ids Qwen 16-21 / separator 220,
Mistral 1049-1054 / separator 1032; re-validated on the host by a full vocabulary scan. One A100-80GB on vast.ai, one checkpoint
loaded at a time; no hosted API.

## Design
- Primary grid: predictor x source x instruction (G, F) x direction (forward, backward) x k = 1..9: {n['primary_cells']} cells.
  Forward reveals positions 1..k and asks for k+1..10; backward reveals 11-k..10 and asks for 1..10-k, both emitted in
  original left-to-right order.
- Supplementary middle-anchored arm (v1.1): reveal positions 3-8, ask for 1, 2, 9, 10 in that order: {n['supplementary_cells']} cells.
- Total {n['cells']} cells; {n['prompt_slots']} prompt slots (each sent byte-identically to both predictors); the source model is
  never named. Prompts in `prompts_frozen.md`, table in `conditions.csv`.
- **Count discrepancy found at freeze (documented, nothing changed):** the handoff expects 76 unique prompt texts; the frozen
  renderer gives {n['distinct_prompt_texts']} distinct texts over {n['prompt_slots']} slots. Qwen F (`3 1 4 ...`) and Mistral F
  (`3 1 5 ...`) share their first two rolls, so these slots are byte-identical: {dup}. Their targets differ. Both predictors'
  free outputs for each pair must therefore be identical; teacher-forced scores differ by target. In these four cells the
  predictor cannot know the source, so their diagonal contrast measures source difficulty alone. All cells, targets, estimands
  and counts of calls and rows are as specified.
- Prompt wrapper: handoff 3.1 (primary) and 3.3 (middle), byte-exact, with Experiment 28's G or F prompt quoted verbatim inside
  `<ORIGINAL INSTRUCTION>`. No trailing newline after the final sentence (same policy for all prompts).

## Collection
1. Preflight per predictor: archival G and F (Experiment 28 prompts) x{C.ARCHIVAL_REPEATS}; 28 cells once each (all
   sources/instructions/directions at k in {C.PREFLIGHT_KS}, plus the 4 middle cells) = {n['preflight_cells']} cells in total; seeded
   shuffled order (seed {C.ORDER_SEED['qwen'] + 100} / {C.ORDER_SEED['mistral'] + 100}); own-output rescoring and teacher-forced targets
   by both arithmetic paths; vocabulary scan. Diagnostic only; never substituted for main data.
2. Preflight gates (all must PASS): references equal Experiment 28; serving identity and prompt hashes; template; face tokens
   and vocabulary scan; finite face log-probs and p6 sums; archival G mass >= {C.MIN_FACE_MASS_G}; archival G/F identical to
   Experiment 28 with six-face vectors within {C.REPRO_TOL_P}; archival repeats bit-identical; preflight calls complete;
   own-output rescoring within {C.SCORER_TOL_LOGP} nats for valid outputs; target mapping (positions, forced faces, prefixes, row
   counts); floor (incremental vs full pass) <= {C.FLOOR_STOP_P}; no model name in any prompt; teacher-forced mass review (STOP for
   investigator review if a predictor's median raw six-face mass over its teacher-forced rows is < {C.TF_MASS_REVIEW_MEDIAN}, or if
   any cell has every row < {C.TF_MASS_REVIEW_CELL}). Free-output format and prediction-prompt mass are reported, not gated.
3. Main per predictor (only after its PASS preflight and explicit investigator approval): archival G and F x{C.ARCHIVAL_REPEATS}
   (in addition) plus all 76 cell slots x {C.N_REPLICATES} = {n['main_generations'] // 2} cell calls per predictor ({n['main_generations']} total), seeded
   shuffled order (seed {C.ORDER_SEED['qwen']} / {C.ORDER_SEED['mistral']}), append-only, resumable. The first record of each distinct
   (cell, output) is rescored by both paths. Then every cell's true target is teacher-forced once by both paths:
   {n['tf_rows']} incremental rows in total ({n['tf_rows_primary']} primary + {n['tf_rows_supplementary']} middle), and the same number of full-pass rows.
4. Main checks (all must PASS before analysis): the preflight hard gates, plus completeness (each (cell, replicate) and archival
   call exactly once), deterministic text and log-probs across triplicates, and raw-file hashes unchanged since collection.

## Measurements
- Free completion: raw text, token ids, finish reason, per-step full-vocabulary log-probs, six face log-probs at every step,
  digit steps, strict validity. Valid = exactly n integers 1-6 separated by single ASCII spaces, nothing else (no leading or
  trailing whitespace, no newline), ended by EOS. Digits embedded in prose are never extracted or scored.
- Teacher-forced true targets: the true missing digits forced as the assistant answer (separators between them), never in the
  user prompt; at each missing position the six-face vector before the forced face, raw mass, p_true, conditional and
  full-vocabulary log loss, argmax, margin, forced prefix text and token ids. Middle arm: steps 1-4 score positions 1, 2, 9, 10
  after forcing the earlier true answer digits; positions 3-8 stay in the user prompt only.
- Numerical floor per predictor: max |dp6| between incremental and full-pass scoring of the same rows. A top face whose margin is
  below the floor is a near-tie (counted separately; `top_correct` requires margin >= floor).

## Analysis plan (no p-values or CIs; deterministic fixed references)
- Position-level table and condition-level table (first missing position and the equal-weighted mean over the missing span).
- Primary metric: conditional log loss -ln p6(true) in nats (uniform = ln 6 = 1.792). Secondary: full-vocabulary log loss, raw
  mass, top-face correctness beyond the floor, free validity, free digit accuracy and exact span match, entropy, and JS to the
  source's Experiment 28 I|I vector at the same original position (a source continuation reference for forward cells only;
  shown as descriptive for backward and middle cells).
- Self vs other: for each (instruction, direction, k) the 2x2 L[predictor, source] of mean span loss (and separately of
  first-position loss), its row and column effects, per-predictor self-minus-other, and
  self_advantage = (L[Q,M] + L[M,Q] - L[Q,Q] - L[M,M]) / 2 (positive = diagonal lower). Also averaged over k with equal weight per
  condition, separately for G/F and forward/backward. A positive contrast is not evidence of introspection.
- H1: forward boundary (position k+1) loss by k per predictor/source/instruction. H3: backward minus forward at equal k, mean
  span and first missing output digit (labelled: position 1 vs position k+1, not temporally equivalent). H4: free validity,
  free digit accuracy, teacher-forced top-1 rate and mean p_true, free first digit vs teacher-forced argmax.
- Middle arm, separate from all primary summaries: early pair (1, 2), late pair (9, 10), four-position mean; loss, first-digit
  loss, top-face correctness, raw mass, validity; 2x2 crossed contrasts per G/F for each part. Compared with k = 6 only as
  equal amount of revealed information.

## Budget and stop rules
Hard cap ${C.GPU_CAP_USD:.0f} total (GPU + disk + bandwidth). Stop for the investigator on any hard gate failure, the mass review
rule, unexpected cost, or any deviation. The instance is destroyed after work or failure.
"""


DATA_DICTIONARY = """# Data dictionary (SPAR_DICE_BIDIRECTIONAL_COMPLETION_v1.1)

## `conditions.csv` (152 rows)
cell_id `<predictor><-<source>-<instruction>-<fwdK|bwdK|mid>`; predictor; source (metadata only, never in the prompt);
source_instruction G/F; task_type primary/middle; direction forward/backward (empty for middle); k (empty for middle); diagonal
(predictor = source); original (the 10-roll ground truth); revealed_positions/values; missing_positions/values (target, in
output order); n_missing; prompt_id (shared by both predictors); prompt_sha256.

## `{preflight,main}/<predictor>/raw_attempts.jsonl`: one generation per line
kind (`archival` = Experiment 28 G/F prompt, `cell`); job (G, F or cell_id); replicate; order_index; trial_id; cell metadata;
prompt, prompt_sha256, rendered_prompt; content, generated_ids, completion_tokens, finish_reason; steps[] (token, token_id,
full-vocabulary logprob, face_logprobs {"1".."6"}, top5, entropy_bits; last = EOS when stopped); digit_steps[]; own_rescored[] and
own_rescored_full_pass[] on the rescored subset; rescore_tokens_equal; latency_ms; timestamp.

## `teacher_forced.jsonl`: one forced missing position per line
cell_id, predictor, source, source_instruction, task_type, direction, k, prompt_id, prompt_sha256; method (incremental = primary,
full_pass = floor); output_step (1 = first answer digit); original_position; true_face; forced_prefix (true answer digits before
this one) and forced_prefix_ids; face_logprobs (full-vocabulary log-probs of the six bare face tokens); argmax_token_id,
argmax_logprob (unconstrained next token).

## `analysis/`
positions.csv (one row per incremental teacher-forced position: p6, raw_mass, p_true, cond_loss = -ln p6[true], full_loss =
-ln p_full[true], argmax, margin, near_tie, top_correct, entropy_bits, source_ref_js); cells.csv (per cell: first_loss,
mean_loss, ..., free validity and accuracy); crossed_*.csv (2x2 matrices and contrasts); middle_*.csv; summary.json.
"""


def write_once(path: Path, text: str):
    if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise SystemExit(f"{path} is frozen and would change; refusing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def conditions_csv() -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(P.CSV_FIELDS), lineterminator="\n")
    w.writeheader()
    for c in P.conditions():
        w.writerow({k: (" ".join(map(str, c[k])) if isinstance(c[k], list) else c[k]) for k in P.CSV_FIELDS})
    return buf.getvalue()


def manifest_template() -> str:
    return json.dumps(dict(tag=C.TAG, expected=C.EXPECTED, counts=counts(), duplicate_prompt_texts=duplicate_prompts(),
                           commits=dict(freeze=None, preflight=None, results=None), instance=None, cost_usd=None,
                           environments=None, files=None), indent=2) + "\n"


def input_files() -> dict:
    files = {f"src/spar_dynamic/dice_bidirectional_completion/{p.name}": Gt.canonical_sha(p) for p in sorted(SRC.glob("*.py"))}
    for p in (SRC.parent / "dice_crossed_guidance" / "models.py", SRC.parent / "dice_crossed_guidance" / "config.py",
              SRC.parent / "dice_logprob_crossmodel" / "gpu.py", SRC.parent / "dice_logprob_crossmodel" / "prompts.py",
              SRC.parent / "dice_logprob_crossmodel" / "gates.py", SRC.parent / "dice_logprob" / "prompts.py",
              SRC.parent / "dice_logprob" / "gpu_runner.py"):
        files[f"src/spar_dynamic/{p.parent.name}/{p.name}"] = Gt.canonical_sha(p)
    for s in C.MODELS:
        for f in ("raw_attempts.jsonl", "matched_prefix.jsonl", "env_main.json"):
            p = C.EXP28_MAIN / s / f
            files[str(p.relative_to(C.EXP.parents[1])).replace("\\", "/")] = Gt.canonical_sha(p)
    for f in ("prompts_frozen.md", "prompts_frozen.json", "PROTOCOL_FROZEN.md"):
        files[f"track1_self_prediction/{C.EXP28.name}/{f}"] = Gt.canonical_sha(C.EXP28 / f)
    for n in FROZEN:
        files[n] = Gt.canonical_sha(C.EXP / n)
    return files


def freeze():
    ref = Gt.verify_references()
    if not ref["ok"]:
        raise SystemExit(f"reference mismatch against Experiment 28: {ref['detail']}")
    write_once(C.EXP / "PROTOCOL_FROZEN.md", protocol_text())
    write_once(C.EXP / "prompts_frozen.md", P.render_frozen())
    write_once(C.EXP / "conditions.csv", conditions_csv())
    write_once(C.EXP / "DATA_DICTIONARY.md", DATA_DICTIONARY)
    write_once(C.EXP / "manifest_template.json", manifest_template())
    files = input_files()
    inputs = C.EXP / "inputs_sha256.json"
    if inputs.exists():
        old = json.load(open(inputs, encoding="utf-8"))["files"]
        if any(old[k] != files[k] for k in FROZEN):
            raise SystemExit("inputs_sha256.json disagrees with the frozen files")
        print("already frozen:", old["PROTOCOL_FROZEN.md"][:12])
        return
    json.dump(dict(tag=C.TAG, hash_rule="SHA-256 of file bytes with CRLF normalised to LF (= the committed git blob)",
                   references_verified=ref["detail"], files=files), open(inputs, "w", encoding="utf-8", newline="\n"), indent=2)
    print("frozen:", files["PROTOCOL_FROZEN.md"][:12], files["prompts_frozen.md"][:12], files["conditions.csv"][:12])


def verify_frozen():
    old = json.load(open(C.EXP / "inputs_sha256.json", encoding="utf-8"))["files"]
    bad = [n for n in FROZEN if Gt.canonical_sha(C.EXP / n) != old[n]]
    if conditions_csv() != (C.EXP / "conditions.csv").read_text(encoding="utf-8").replace("\r\n", "\n"):
        bad.append("conditions built by the code differ from conditions.csv")
    if P.render_frozen() != (C.EXP / "prompts_frozen.md").read_text(encoding="utf-8").replace("\r\n", "\n"):
        bad.append("prompts built by the code differ from prompts_frozen.md")
    if bad:
        raise SystemExit(f"frozen inputs changed: {bad}")


def estimate(sec=None) -> dict:
    """Wall time and cost from Experiment 28 timings (Mistral prose worst case for completion prompts)."""
    sec = sec or {"qwen": 0.9, "mistral": 2.5}            # s per cell call incl. own rescoring of distinct outputs
    gen = {m: (76 * C.N_REPLICATES + 4) * s / 60 for m, s in sec.items()}
    pre = {m: (28 + 4) * s / 60 for m, s in sec.items()}
    hours = (12 + 2 * 3 + sum(gen.values()) + sum(pre.values()) + 4 * 2 + 15) / 60   # setup+download, loads, runs, scoring, slack
    return dict(main_generation_minutes=gen, preflight_minutes=pre, total_hours=round(hours, 2),
                usd_at_exp28_rates=round(hours * 1.97 + 103 * 0.013, 2), cap=C.GPU_CAP_USD)


def dryrun():
    print(json.dumps(dict(counts=counts(), expected_by_handoff=C.EXPECTED, duplicate_prompt_texts=duplicate_prompts(),
                          estimate=estimate()), indent=2))
    d = {c["prompt_id"]: c for c in P.prompt_cells()}
    for pid in ("qwen-G-fwd3", "qwen-G-bwd3", "mistral-F-bwd9", "qwen-G-mid"):
        c = d[pid]
        print(f"\n=== {pid}: reveal {c['revealed_positions']} = {c['revealed_values']}; target {c['missing_positions']} = `{c['target']}`\n{c['prompt']}")


def _report(res, path_json, path_md, title):
    json.dump(res, open(path_json, "w", encoding="utf-8"), indent=2, default=str)
    Path(path_md).write_text(Gt.report_md(res, title), encoding="utf-8")
    print(res["overall"], {k: v["status"] for k, v in res["gates"].items()})


def gate_preflight(model):
    verify_frozen()
    _report(Gt.preflight_gates(model), C.PRE / model / "preflight_gates.json", C.PRE / model / "PREFLIGHT_REPORT.md",
            f"Preflight, {model} ({C.TAG})")


def gate_main(model):
    verify_frozen()
    _report(Gt.main_checks(model), C.MAIN / model / "main_checks.json", C.MAIN / model / "MAIN_CHECKS.md", f"Main checks, {model} ({C.TAG})")


def _csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict, tuple)) else v) for k, v in r.items()})


def analyse():
    from spar_dynamic.dice_bidirectional_completion import analysis as A
    from spar_dynamic.dice_bidirectional_completion.figures import all_figures
    verify_frozen()
    for m in C.MODELS:
        if json.load(open(C.MAIN / m / "main_checks.json", encoding="utf-8"))["overall"] != "PASS":
            raise SystemExit(f"main checks for {m} did not pass; analysis not run")
    res = A.analyse({m: A.load(m) for m in C.MODELS})
    out = C.ANALYSIS
    _csv(out / "positions.csv", res["positions"])
    _csv(out / "cells.csv", res["cells"])
    for k in ("crossed_mean", "crossed_first", "crossed_avg_mean", "crossed_avg_first"):
        _csv(out / f"{k}.csv", res[k])
    _csv(out / "middle_table.csv", res["middle"]["table"])
    _csv(out / "middle_contrasts.csv", res["middle"]["contrasts"])
    summary = {k: res[k] for k in ("floor", "crossed_avg_mean", "crossed_avg_first", "hypotheses", "uniform_loss")}
    summary["middle_contrasts"] = res["middle"]["contrasts"]
    summary["raw_sha256"] = {m: {f: Gt.file_sha(C.MAIN / m / f) for f in ("raw_attempts.jsonl", "teacher_forced.jsonl")} for m in C.MODELS}
    json.dump(dict(tag=C.TAG, **summary), open(out / "summary.json", "w", encoding="utf-8"), indent=2, default=str)
    all_figures(res, out / "figures")
    print("analysis written to", out)


if __name__ == "__main__":
    phase = sys.argv[1]
    if phase in ("preflight", "main"):
        sys.argv = [sys.argv[0]] + sys.argv[1:]
        runpy.run_module("spar_dynamic.dice_bidirectional_completion.gpu", run_name="__main__")
    else:
        fns = {"freeze": freeze, "dryrun": dryrun, "analyse": analyse,
               "gate_preflight": lambda: gate_preflight(sys.argv[2]), "gate_main": lambda: gate_main(sys.argv[2])}
        fns[phase]()
