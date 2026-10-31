"""SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 offline phases.

  freeze                 write PROTOCOL_FROZEN.md, prompts_frozen.md, prompts_frozen.json, inputs_sha256.json (refuses to change them)
  dryrun                 print the 15 prompts with hashes, the job counts and the GPU estimate; no model
  gate_preflight <model> preflight/<model>/ -> preflight_gates.json + PREFLIGHT_REPORT.md
  gate_main <model>      main/<model>/ -> main_checks.json + MAIN_CHECKS.md
  analyse                needs PASS main checks for both models; tables, summary.json and figures in analysis/

Usage: PYTHONPATH=src python -m spar_dynamic.dice_logprob_crossmodel <phase> [model]
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from spar_dynamic.dice_logprob_crossmodel import analysis as A
from spar_dynamic.dice_logprob_crossmodel import config as C
from spar_dynamic.dice_logprob_crossmodel import gates as Gt
from spar_dynamic.dice_logprob_crossmodel import prompts as P

SRC = Path(__file__).resolve().parent


def file_sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def protocol_text() -> str:
    q, m = C.MODEL["qwen"], C.MODEL["mistral"]
    w = ", ".join(f"W{a}-{b}" for a, b in C.WINDOWS)
    return f"""# {C.TAG}: frozen protocol

Design source: {C.DESIGN_SOURCE}, from the 2026-10-25 discussion with Christopher Ackerman. Experiments 01-27 are read, never
written. Behavioural study on output log-probabilities; no layer-wise or mechanistic analysis.

## Questions
- RQ1 (shared vs distinct policy): are G/F mismatches near-tie swaps or a re-run of one conditional distribution (H1a), or does
  the prediction wrapper induce a different distribution (H1b)? Natural-path and matched-prefix six-face differences.
- RQ2 (scope): do isolated position predictions S1-S10 recover G(k) or F(k)? Systematic bias toward particular faces?
- RQ3 (multi-position coherence): do five-position windows reproduce G or F better than S(k)? Do overlapping windows agree?
- RQ4 (two checkpoints): are the patterns alike for Qwen3-32B and Mistral Small 3.2 24B? Descriptive only.
Prior result incorporated, not rediscovered (Experiment 21, Qwen): natural G/F differ at 9/10 positions; on G's prefix the F
instruction picks G's face at positions 2-10; the generic-model control showed the opening shift is a prediction-wrapper effect,
not specific to self-reference.

## Models and serving (one model loaded at a time, one A100-SXM4-80GB on vast.ai; no hosted inference API)
| | Qwen | Mistral |
|---|---|---|
| Weights | `{q['model_id']}` @ `{q['revision']}` | `{m['model_id']}` @ `{m['revision']}` |
| Class | Experiment 21's `Qwen` class (via Experiment 27's `QwenEngine`), unchanged | Experiment 27's `MistralEngine`: transformers Mistral 3 conditional-generation class, text path only |
| Tokenizer / template | {q['tokenizer']} | {m['tokenizer']} |
| Face tokens | ids {list(q['face_ids'].values())}; separator id {C.SEPARATOR_ID['qwen']} | ids {list(m['face_ids'].values())}; separator id {C.SEPARATOR_ID['mistral']} |

Both: bf16 weights/activations, separate fp32 copy of lm_head, fp32 logits, batch 1, prompt prefilled once then one token at a
time through the KV cache, exact full-vocabulary log-softmax at every step, greedy argmax, no sampling, no logit processors, no
tools, no system message, max {C.MAX_NEW_TOKENS} new tokens, deterministic flags as in Experiment 21. Code: Experiment 27's
`dice_crossed_guidance/models.py`, unchanged. Offline check (2026-10-31, pinned tokenizer files): in both vocabularies each face
1-6 is exactly one token, a digit after a space encodes as separator + bare digit, and no other token's text is a face digit
(with or without whitespace) or a run of ASCII digits. So the six bare ids are the only ways to emit a face; this is re-checked
on the GPU host by a full vocabulary scan (gate `face_tokens`).

## Conditions (15 per model; prompts in `prompts_frozen.md`)
G (generate 10), F (predict all 10 of "another instance of your model"), S1-S10 (only position k), {w} (only those five
positions, original order). G, F, S1-S10 and W1-5 are byte-identical to Experiment 21; W3-7 and W6-10 are new (Experiment 21
used W3-8 and W5-10, which are not reused as this design's windows).

## Collection
1. Preflight per model: G x{C.PREFLIGHT_REPEATS}, F x{C.PREFLIGHT_REPEATS}, every S and W once, in seeded shuffled order (seed
   {C.ORDER_SEED['qwen'] + 100} Qwen / {C.ORDER_SEED['mistral'] + 100} Mistral). Every output rescored (incremental and full pass); matched prefix and matched windows
   (below); vocabulary scan; timings.
2. Gates (all must PASS, else STOP and report): serving identity and hashes; template (Qwen empty think block, no system turn;
   Mistral rendered G exactly `<s>[INST]<G>[/INST]`); face tokens (ids, separator alternation, no variant face tokens); finite
   face log-probs; raw six-face mass >= {C.MIN_FACE_MASS_G} at every G-prompt digit step (prediction-prompt mass reported, not gated, as in
   Experiment 27 amendment v1.1); valid numeric-only output for G, F and every S/W condition; incremental rescoring of each
   output reproduces generation within {C.SCORER_TOL_LOGP} nats; G and F repeats bit-identical; floor (incremental vs full pass)
   <= {C.FLOOR_STOP_P}; matched rows complete; archival regression (Qwen: G, F, S1-S10, W1-5 outputs identical to Experiment 21 main
   and every six-face vector, including matched prefix, within {C.REPRO_TOL_P}; Mistral: G and F identical to Experiment 27's
   Mistral preflight and vectors within {C.REPRO_TOL_P}).
3. Main per model (only after its preflight PASS and investigator authorisation): {C.N_REPLICATES} fresh-context greedy calls of
   each of the 15 conditions ({15 * C.N_REPLICATES} per model, {2 * 15 * C.N_REPLICATES} total), seeded shuffled order (seed
   {C.ORDER_SEED['qwen']} Qwen / {C.ORDER_SEED['mistral']} Mistral), append-only and resumable (refuses prompt or model drift). The first
   record of each distinct (condition, output) is rescored by both arithmetic paths (the predefined full-pass subset). Then
   matched prefix and matched windows on the main run's G and F. Raw-file hashes written to the environment record.
4. Main checks (all must PASS before analysis): serving, template, face tokens, completeness ({15 * C.N_REPLICATES} records, each
   (condition, replicate) once), finite, G mass, G/F format, scorer, G and F single output equal to preflight, floor, matched
   rows complete, raw files unchanged since collection (SHA-256).

## Matched-prefix design (teacher-forced, incremental = generation arithmetic; full pass = floor only)
- mp: instruction in {{G, F}} x history in {{G_ref, F_ref}} (the model's own greedy sequences), six-face vector at every position.
- window: each W(a-b) prompt with G_ref[a..b] or F_ref[a..b] as its assistant history (secondary; compared with G|G and F|F).

## Analysis plan (per model, then side by side; descriptive, no p-values over deterministic replicates)
1. Integrity: valid rate, distinct outputs and max six-face spread across replicates per condition, raw mass, floor
   (max |dp6| and max JS between arithmetic paths), tokenizer diagnostics.
2. G vs F natural: per position six-face vectors, JS (bits), probability and rank of the other's chosen face; exact sequence
   match, aligned matches, shared bigrams, best shift alignment, longest common run. Position 1 (same empty history) reported
   separately.
3. G vs F matched prefix: JS and top-face agreement per position on each history; disagreements at 2-10 with and without near-ties
   (margin below floor); how many natural disagreements at 2-10 disappear under a matched prefix (cascade) and what remains
   (residual framing effect).
4. S(k): first-token six-face vector and answer vs G(k) and F(k) natural (contexts differ; labelled). Counts vs chance 10/6,
   face counts, mean distribution and entropy (generic bias).
5. Windows: each position vs G(k), F(k), S(k) (JS and chosen face); matched windows vs G|G and F|F; overlaps W1-5/W3-7 at 3-5 and
   W3-7/W6-10 at 6-7, each pair reported once.
6. Conditional dynamics: face counts, adjacent repeats, permutation structure, step sizes mod 6, probability given to repeating
   the previous face (vs 1/6).
7. Cross-model table with identical metrics.
Interpretation rules: similarity can come from shared priors or prompt-conditioned computation; dissimilarity does not show
absence of self-modelling; Experiment 21's generic-model control shows part of the G/F difference is a prediction-wrapper effect.
Top-face differences within the floor are ties. Archival Experiment 21 windows are labelled where compared.

## Budget and stop rules
GPU cap ${C.GPU_CAP_USD:.0f} (GPU + disk + bandwidth), warn at ${C.GPU_WARN_USD:.0f}. Stop for the investigator on unexpected cost, checkpoint mismatch,
tokenizer ambiguity, scoring failure, numerical instability or a gate failure. Sample size is not changed without approval. The
instance is destroyed at the end, also after a failure.
"""


DATA_DICTIONARY = """# Data dictionary (SPAR_DICE_LOGPROB_CROSSMODEL_v2.0)

## `{preflight,main}/<model>/raw_attempts.jsonl`: one generation per line
| Field | Meaning |
|---|---|
| study, stage, model, model_id, model_commit | study tag; preflight/main; qwen/mistral; HF repo and pinned commit |
| trial_id, condition, condition_type, replicate, order_index | `<model>-<cond>-<rep>`; G, F, S1..S10, W1-5, W3-7, W6-10; type G/F/S/W; 1..20; position in the seeded shuffled job order |
| target_positions, n_expected | original serial positions (1-based) in output order; number of faces a valid answer has |
| prompt, prompt_sha256, rendered_prompt, rendered_prompt_sha256, prompt_tokens | user message, its SHA-256, the chat-templated text, token count |
| content, generated_ids, completion_tokens, finish_reason | decoded output; generated token ids (EOS excluded); `stop` = EOS, `length` = 128-token cap |
| steps[] | every decoding step: token, token_id, logprob (full vocabulary), face_logprobs {"1".."6": full-vocabulary log-prob of each bare face token}, top5 [[id, logprob]], entropy_bits; last step is EOS when finish_reason = stop |
| digit_steps[] | the steps whose chosen token is a face (same fields) |
| own_rescored[], own_rescored_full_pass[] | teacher-forced six-face rows for this output (incremental; one full forward pass); present on the rescored subset |
| rescore_tokens_equal, rescored_subset | re-encoding the content gives the generated ids; main: first record of this (condition, output) |
| latency_ms, timestamp, decoding | generation wall time; UTC; decoding rule |

## `matched_prefix.jsonl`: one teacher-forced face position per line
| Field | Meaning |
|---|---|
| kind | `mp` (G or F instruction over a full reference) or `window` (a W prompt over a reference's window) |
| instruction, history, history_sequence | prompt condition; G or F reference; the forced assistant text |
| method | `incremental` (generation arithmetic, primary) or `full_pass` (numerical floor only) |
| position, original_position | index within the forced text; original serial position |
| history_face, face_logprobs, argmax_token_id, argmax_logprob | forced face; six bare-face full-vocabulary log-probs before it; the unconstrained argmax |

## Derived (analysis/)
p6 = face log-probs renormalised over the six faces; mass = their summed raw probability. JS = Jensen-Shannon divergence in bits
(0..1). Floor = max |dp6| between incremental and full-pass scoring of the same rows; near-tie = top-two margin below the floor.
"""


def write_once(path: Path, text: str):
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{path} is frozen and would change; refusing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def freeze():
    write_once(C.EXP / "PROTOCOL_FROZEN.md", protocol_text())
    write_once(C.EXP / "prompts_frozen.md", P.render_frozen())
    write_once(C.EXP / "prompts_frozen.json", json.dumps(P.conditions(), indent=1) + "\n")
    write_once(C.EXP / "DATA_DICTIONARY.md", DATA_DICTIONARY)
    files = {f"src/spar_dynamic/dice_logprob_crossmodel/{p.name}": file_sha(p) for p in sorted(SRC.glob("*.py"))}
    for p in (SRC.parent / "dice_crossed_guidance" / "models.py", SRC.parent / "dice_crossed_guidance" / "config.py",
              SRC.parent / "dice_logprob" / "prompts.py", SRC.parent / "dice_logprob" / "gpu_runner.py"):
        files[f"src/spar_dynamic/{p.parent.name}/{p.name}"] = file_sha(p)
    for p in (C.EXP21 / "raw_attempts.jsonl", C.EXP21 / "matched_prefix.jsonl",
              C.EXP27_PRE / "mistral" / "raw_attempts.jsonl", C.EXP27_PRE / "mistral" / "matched_prefix.jsonl"):
        files[str(p.relative_to(C.EXP.parents[1])).replace("\\", "/")] = file_sha(p)
    for n in ("PROTOCOL_FROZEN.md", "prompts_frozen.md", "prompts_frozen.json", "DATA_DICTIONARY.md"):
        files[n] = file_sha(C.EXP / n)
    inputs = C.EXP / "inputs_sha256.json"
    if inputs.exists():
        old = json.load(open(inputs, encoding="utf-8"))["files"]
        if any(old[k] != files[k] for k in ("PROTOCOL_FROZEN.md", "prompts_frozen.md", "prompts_frozen.json")):
            raise SystemExit("inputs_sha256.json disagrees with the frozen protocol")
        print("already frozen:", old["PROTOCOL_FROZEN.md"][:12])
        return
    json.dump(dict(tag=C.TAG, files=files), open(inputs, "w", encoding="utf-8"), indent=2)
    print("frozen:", files["PROTOCOL_FROZEN.md"][:12], files["prompts_frozen.md"][:12])


def verify_frozen():
    """Tamper check: the frozen files and the prompts the code builds now must match inputs_sha256.json."""
    old = json.load(open(C.EXP / "inputs_sha256.json", encoding="utf-8"))["files"]
    bad = [n for n in ("PROTOCOL_FROZEN.md", "prompts_frozen.md", "prompts_frozen.json") if file_sha(C.EXP / n) != old[n]]
    if json.loads((C.EXP / "prompts_frozen.json").read_text(encoding="utf-8")) != P.conditions():
        bad.append("prompts built by the code differ from prompts_frozen.json")
    if bad:
        raise SystemExit(f"frozen inputs changed: {bad}")


def dryrun():
    for c in P.conditions():
        print(f"--- {c['condition']} positions {c['positions']} sha {c['prompt_sha256'][:16]}\n{c['prompt']}\n")
    pre = 2 * C.PREFLIGHT_REPEATS + 13
    print(json.dumps(dict(preflight_generations_per_model=pre, main_generations_per_model=15 * C.N_REPLICATES,
                          matched_rows_per_model=dict(mp=80, window=sum(4 * (b - a + 1) for a, b in C.WINDOWS)),
                          estimate=estimate()), indent=2))


def estimate(sec=None) -> dict:
    """Wall-time and cost estimate from Experiment 27 timings (or measured preflight seconds per job)."""
    sec = sec or {"qwen": dict(G=1.5, F=1.5, S=0.6, W=1.0), "mistral": dict(G=1.4, F=1.4, S=5.6, W=5.6)}   # Mistral S/W: prose worst case
    gen_min = {m: (C.N_REPLICATES * (s["G"] + s["F"] + 10 * s["S"] + 3 * s["W"]) + 19 * max(s.values()) * 2) / 60 for m, s in sec.items()}
    hours = (30 + 2 * 6 + sum(gen_min.values()) * 1.15 + 15) / 60      # setup+downloads, loads, generation (+rescoring), slack
    return dict(generation_minutes=gen_min, total_hours=round(hours, 2),
                usd_at_1_11_gpu_0_35_disk_plus_110GB_at_0_039=round(hours * (1.11 + 0.35) + 110 * 0.039, 2), cap=C.GPU_CAP_USD)


def _csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict, tuple)) else v) for k, v in r.items()})


def gate_preflight(model: str):
    verify_frozen()
    res = Gt.preflight_gates(model)
    json.dump(res, open(C.PRE / model / "preflight_gates.json", "w", encoding="utf-8"), indent=2, default=str)
    (C.PRE / model / "PREFLIGHT_REPORT.md").write_text(Gt.report_md(res, f"Preflight, {model} ({C.TAG})"), encoding="utf-8")
    print(res["overall"], {k: v["status"] for k, v in res["gates"].items()})
    print(json.dumps(res["info"], default=str)[:3000])


def gate_main(model: str):
    verify_frozen()
    res = Gt.main_checks(model)
    json.dump(res, open(C.MAIN / model / "main_checks.json", "w", encoding="utf-8"), indent=2, default=str)
    (C.MAIN / model / "MAIN_CHECKS.md").write_text(Gt.report_md(res, f"Main checks, {model} ({C.TAG})"), encoding="utf-8")
    print(res["overall"], {k: v["status"] for k, v in res["gates"].items()})


def analyse():
    verify_frozen()
    from spar_dynamic.dice_logprob_crossmodel.figures import all_figures
    for m in C.MODELS:
        if json.load(open(C.MAIN / m / "main_checks.json", encoding="utf-8"))["overall"] != "PASS":
            raise SystemExit(f"main checks for {m} did not pass; analysis not run")
    res = {m: A.analyse_model(A.load(m)) for m in C.MODELS}
    out = C.ANALYSIS
    for m, r in res.items():
        _csv(out / f"{m}_integrity.csv", r["integrity"])
        _csv(out / f"{m}_natural_G_vs_F.csv", r["natural"]["rows"])
        _csv(out / f"{m}_matched_prefix_G_vs_F.csv", r["matched"]["rows"])
        _csv(out / f"{m}_singles.csv", r["singles"]["rows"])
        _csv(out / f"{m}_windows.csv", r["windows"]["rows"])
        _csv(out / f"{m}_window_overlaps.csv", r["windows"]["overlaps"])
    _csv(out / "cross_model.csv", A.cross_model(res))
    summary = {m: dict(floor=r["floor"], modal=r["modal"], natural=r["natural"]["summary"], matched=r["matched"]["summary"],
                       singles=r["singles"]["summary"], windows=r["windows"]["summary"], overlaps=r["windows"]["overlaps"],
                       dynamics=r["dynamics"]) for m, r in res.items()}
    summary["raw_sha256"] = {m: {f: file_sha(C.MAIN / m / f) for f in ("raw_attempts.jsonl", "matched_prefix.jsonl")} for m in C.MODELS}
    json.dump(dict(tag=C.TAG, **summary), open(out / "summary.json", "w", encoding="utf-8"), indent=2, default=str)
    all_figures(res, out / "figures")
    print("analysis written to", out)


if __name__ == "__main__":
    phase = sys.argv[1]
    fns = {"freeze": freeze, "dryrun": dryrun, "analyse": analyse,
           "gate_preflight": lambda: gate_preflight(sys.argv[2]), "gate_main": lambda: gate_main(sys.argv[2])}
    fns[phase]()
