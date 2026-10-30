"""SPAR_DICE_PREFIX_DECLARATIVE_v1.0 offline phases.

  freeze          write PROTOCOL_FROZEN.md, prompts_frozen.md, inputs_sha256.json (refuses to change them once written)
  dryrun          print all 12 prompts, targets, job counts and the GPU estimate; no model, no spend
  preflight_eval  gates from preflight/ -> preflight/preflight_gates.json and PREFLIGHT_REPORT.md
  analyse         main/ checks, tidy CSVs, summary.json and figures in analysis/

Usage: PYTHONPATH=src python -m spar_dynamic.dice_prefix_declarative <phase>
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from spar_dynamic.dice_prefix_declarative import analysis as A
from spar_dynamic.dice_prefix_declarative import config as C
from spar_dynamic.dice_prefix_declarative import prompts as P

SRC = Path(__file__).resolve().parent


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def o_evidence() -> list:
    """Experiment 22 Mistral Small 3.2 sequences (exact G instruction) whose first six integers use each face once."""
    out = []
    for split in ("development", "heldout"):
        for r in csv.DictReader(open(C.EXP22 / "corpus" / f"{split}.csv", encoding="utf-8")):
            s = r["sequence"].split()
            if r["source"] == C.O_EVIDENCE_SOURCE and r["valid"] == "True" and len(set(s[:6])) == 6:
                out.append(dict(stimulus_id=r["stimulus_id"], sequence=r["sequence"], split=split))
    return out


def protocol_text() -> str:
    ev = o_evidence()
    return f"""# {C.TAG}: frozen protocol

Design source: {C.DESIGN_SOURCE}. Exploratory, gated pilot; a follow-up to Experiment 21, not to the Loula line.

## Serving (Experiment 21, unchanged)
- `{C.MODEL_ID}` at commit `{C.REVISION}`; transformers; bf16 weights with an fp32 output layer; Qwen3 chat template with
  `enable_thinking=False` (template sha256 `{C.CHAT_TEMPLATE_SHA256}`); one user message, no system message, no tools;
  greedy, batch 1, no logits processors, 128-token cap. Generation and scoring use Experiment 21's `Qwen` class unchanged.
- Six-face log-probabilities are the exact full-vocabulary log-softmax at the face tokens `1`-`6` (ids 16-21). Digits and the
  space separator are separate tokens.

## Reference
- G: Experiment 21's direct-generation prompt (sha `{C.G_PROMPT_SHA256[:12]}…`), greedy output `{' '.join(map(str, C.G_REF))}`.
- F: Experiment 21's full self-prediction prompt (sha `{C.F_PROMPT_SHA256[:12]}…`), greedy output `{' '.join(map(str, C.F_REF))}`.
- G_j = six-face distribution of the G prompt at original position j with the true G history (incremental arithmetic).

## Conditions: 3 prefix lengths x 4 arms
k = {C.KS}; targets are the next three G rolls (positions k+1..k+3). Arms: H (prefix only), N/S/O (H plus one paragraph
directly before "Predict" reporting a separate earlier response whose first six integers use each face once; source
"an unspecified model" / "your own model" / "a different model"). Exact strings and hashes: `prompts_frozen.md`.

Why this wording (handoff 4.3): the draft neutral sentence described the target itself while the self sentence described a
prior sample, which would make the neutral version more informative. All three versions here describe a *separate earlier
response*, say it is an observation and not a guarantee, and say it does not determine order. Only the source phrase differs;
each paragraph has the same word count. The paragraph contains no digit and no order information.

Truth of each paragraph:
- S and N: Experiment 21's greedy G (`{' '.join(map(str, C.G_REF))}`) is an earlier response to this exact instruction by Qwen3-32B.
- O: Experiment 22 sampled Mistral Small 3.2 24B on this exact instruction at temperature 0.7; {len(ev)} of its valid
  sequences use each face once in their first six integers (e.g. `{ev[0]['stimulus_id']}`: `{ev[0]['sequence']}`).
- No paragraph claims a population propensity; Experiment 22's Qwen and Mistral prevalence is context in the report only.

## Measurements
- Measurement B (primary): teacher-forced six-face distribution at each target position, true G window as assistant history,
  incremental KV-cache arithmetic. Labelled conditional scoring, never "generated".
- Measurement A (supplementary): free greedy three-integer output, with the six-face distribution at each emitted digit.
- Each prompt's own free output is rescored with the teacher-forced scorer (scorer = generator check).
- One full-pass score per condition and for the references: numerical floor.

## Order and repeats
Preflight: G x{C.PREFLIGHT_REF_REPEATS}, F x{C.PREFLIGHT_REF_REPEATS}, H3/N3/S3/O3 x1, seeded shuffle (seed {C.ORDER_SEED + 1}).
Main: 12 conditions x {C.REPEATS} fresh-context repeats, seeded shuffle (seed {C.ORDER_SEED}). Greedy repeats establish
determinism, not independent observations; analysis uses repeat 1 and reports the spread.

## Preflight gates (all must pass before main)
1. serving: commit, chat-template hash, rendered-G hash and all prompt hashes match.
2. non_thinking: every rendered prompt ends with the empty think block, no system turn, no think text in outputs.
3. face_tokens: face ids 16-21, single tokens; G history tokenises as digit, space, digit, ...
4. face_logprobs: all finite; raw six-face mass >= {C.MIN_FACE_MASS} at every scored digit step.
5. scorer_matches_generation: rescoring each output reproduces its generation log-probs within {C.SCORER_TOL_LOGP}.
6. reference_reproduction: G and F greedy outputs identical to Experiment 21 on every repeat, and every six-face distribution
   (generation steps; matched-prefix G|G, F|G, F|F) within max |dp| <= {C.REPRO_TOL_P} of the archive. Otherwise stop and ask
   before establishing a new baseline.
7. determinism: G and F repeats bit-identical.
8. k3_outputs_valid / k3_teacher_forced_complete: H3/N3/S3/O3 each return three integers 1-6; all 12 forced rows present.
Numerical floor: delta = max |dp| incremental vs full pass; near-tie floor = max({C.ARCHIVED_FLOOR_P}, delta).

## Main checks before comparative analysis
The same gates on the main data, completeness (36 records, 108 forced rows), and G_j within {C.REPRO_TOL_P} of the archive.
No accuracy gate: scientific nulls are reported.

## Outcomes (per original position; positions are not pooled as independent)
1. P(true roll), six-face normalised; also raw log P and raw six-face mass.
2. JS divergence (bits) and total variation between the arm and G_j. Primary contrasts at the same k and position:
   N-H, S-H, S-N; framing control O-H, S-O.
3. Rank and top face of the true roll; near-ties flagged by the floor.
4. Teacher-forced window log-likelihood (sum and mean over 3 positions).
Supplementary (free): predicted triple, exact match by position and whole window, k=3 rule adherence (faces in {{1,3,4}}),
path log-prob. Prefix-length (k) comparisons change the predicted position too; they are descriptive only.

## Budget
GPU cap ${C.GPU_CAP_USD:.0f} for preflight plus pilot; estimate {C.EST_MINUTES} min x ${C.EST_RATE_USD_H}/h on one A100 80 GB.
"""


def write_once(path: Path, text: str):
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{path} is frozen and would change; refusing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def freeze():
    write_once(C.EXP / "PROTOCOL_FROZEN.md", protocol_text())
    write_once(C.EXP / "prompts_frozen.md", P.render_frozen())
    files = {p.name: file_sha(p) for p in sorted(SRC.glob("*.py"))}
    files.update({str(p.relative_to(C.EXP21.parents[1])).replace("\\", "/"): file_sha(p)
                  for p in (C.EXP21 / "raw_attempts.jsonl", C.EXP21 / "matched_prefix.jsonl",
                            C.EXP22 / "corpus" / "development.csv", C.EXP22 / "corpus" / "heldout.csv")})
    files["PROTOCOL_FROZEN.md"] = file_sha(C.EXP / "PROTOCOL_FROZEN.md")
    files["prompts_frozen.md"] = file_sha(C.EXP / "prompts_frozen.md")
    inputs = C.EXP / "inputs_sha256.json"
    old = json.load(open(inputs, encoding="utf-8")) if inputs.exists() else {}
    if old and {k: v for k, v in old["files"].items() if k in ("PROTOCOL_FROZEN.md", "prompts_frozen.md")} != \
            {k: files[k] for k in ("PROTOCOL_FROZEN.md", "prompts_frozen.md")}:
        raise SystemExit("inputs_sha256.json disagrees with the frozen protocol")
    if not old:
        json.dump(dict(tag=C.TAG, prompt_sha256={c["condition"]: c["prompt_sha256"] for c in P.conditions()}, files=files),
                  open(inputs, "w", encoding="utf-8"), indent=2)
    print("frozen:", files["PROTOCOL_FROZEN.md"][:12], files["prompts_frozen.md"][:12])


def dryrun():
    from spar_dynamic.dice_prefix_declarative.gpu import jobs
    for c in P.conditions():
        print(f"\n=== {c['condition']} (positions {c['positions']}, expected true window {c['target']}) sha {c['prompt_sha256'][:12]}\n{c['prompt']}")
    pre, main = jobs("preflight"), jobs("main")
    est = C.EST_MINUTES / 60 * C.EST_RATE_USD_H
    print(f"\npreflight jobs {len(pre)}: {pre}\nmain jobs {len(main)}\nestimate: {C.EST_MINUTES} min, ${est:.2f} (cap ${C.GPU_CAP_USD:.0f})")


def preflight_eval():
    res = A.preflight_gates(C.PRE)
    json.dump(res, open(C.PRE / "preflight_gates.json", "w", encoding="utf-8"), indent=2, default=str)
    lines = [f"# Preflight report ({C.TAG})\n", f"Run `{res['preflight_run_id']}`. **Overall: {res['overall']}**\n",
             "| Gate | Status | Detail |", "|---|---|---|"]
    for k, v in res["gates"].items():
        lines.append(f"| {k} | {v['status']} | `{json.dumps(v['detail'], default=str)[:300]}` |")
    n = res["numerics"]
    lines.append(f"\nNumerical floor: incremental vs full pass max |dp| = {n['delta_incremental_vs_full_pass']:.4f} over "
                 f"{n['n_compared']} distributions; near-tie floor = {n['near_tie_floor']:.3f}.\n")
    (C.PRE / "PREFLIGHT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(res["overall"], {k: v["status"] for k, v in res["gates"].items()}, n)


def _csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def analyse(main_dir: Path | None = None, out_dir: Path | None = None):
    from spar_dynamic.dice_prefix_declarative.figures import all_figures
    main_dir, out_dir = main_dir or C.MAIN, out_dir or C.ANALYSIS
    gates, data = A.main_checks(main_dir)
    ok = all(v["status"] == "PASS" for v in gates.values())
    checks = dict(overall="PASS" if ok else "FAIL", gates=gates, numerics=data["numerics"], repeat_spread=data["repeat_spread"])
    json.dump(checks, open(main_dir / "main_checks.json", "w", encoding="utf-8"), indent=2, default=str)
    print("main checks:", checks["overall"], {k: v["status"] for k, v in gates.items()})
    if not ok:
        print("comparative analysis not run: a main check failed")
        return
    t = A.tidy(data)
    _csv(out_dir / "teacher_forced_by_position.csv", t["rows"])
    _csv(out_dir / "paired_contrasts.csv", t["contrasts"])
    _csv(out_dir / "window_loglik.csv", t["window"])
    _csv(out_dir / "free_continuation.csv", t["free"])
    _csv(out_dir / "k3_rule_mass.csv", t["rule"])
    _csv(out_dir / "reference_G_F_at_G_history.csv",
         [dict(position=j, true_face=C.G_REF[j - 1], **{f"G_p{f}": t["G"][j][f - 1] for f in C.FACES},
               **{f"F_p{f}": t["F_at_G"][j][f - 1] for f in C.FACES}) for j in sorted(t["G"])])
    _csv(out_dir / "position1_G_F_arms.csv", [dict(series=k, **{f"p{f}": v[f - 1] for f in C.FACES}) for k, v in t["position1"].items()])
    summary = dict(tag=C.TAG, near_tie_floor=t["floor"], main_checks=checks["overall"], repeat_spread=data["repeat_spread"],
                   window=t["window"], free=t["free"], rule=t["rule"], contrasts=t["contrasts"])
    json.dump(summary, open(out_dir / "summary.json", "w", encoding="utf-8"), indent=2, default=str)
    all_figures(t, out_dir / "figures")
    print("analysis written to", out_dir)


if __name__ == "__main__":
    {"freeze": freeze, "dryrun": dryrun, "preflight_eval": preflight_eval, "analyse": analyse}[sys.argv[1]]()
