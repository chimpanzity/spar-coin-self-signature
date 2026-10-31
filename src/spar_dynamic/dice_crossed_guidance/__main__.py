"""SPAR_CROSSED_GUIDED_SELFPRED_v1.0 offline phases.

  freeze                 write PROTOCOL_FROZEN.md, prompts_frozen.md, inputs_sha256.json (refuses to change them once written)
  dryrun                 print the design, example prompts and the call/cost table for the planned corpus size; no model
  gate_preflight <model> preflight/<model>/ -> preflight_gates.json + PREFLIGHT_REPORT.md
  gate_corpus <model>    corpus/<model>/ -> corpus_gate.json
  build_trials           items.json, trials.jsonl, integrity.csv, call_table.json and trials_gate.json (needs both corpora)
  analyse                main checks, tidy CSVs, estimands (cluster bootstrap) and figures in analysis/

Usage: PYTHONPATH=src python -m spar_dynamic.dice_crossed_guidance <phase> [model]
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from spar_dynamic.dice_crossed_guidance import analysis as A
from spar_dynamic.dice_crossed_guidance import config as C
from spar_dynamic.dice_crossed_guidance import prompts as P

SRC = Path(__file__).resolve().parent


def file_sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def protocol_text() -> str:
    q, m = C.MODEL["qwen"], C.MODEL["mistral"]
    n_trials = len(C.MODELS) * (2 + 2 * C.N_TARGETS) * len(C.CONDITIONS) * len(C.FRAMINGS) * len(C.EVIDENCE)
    return f"""# {C.TAG}: frozen protocol

Design source: {C.DESIGN_SOURCE}. Exploratory, staged study. Experiments 01-26 are read, never written.

## Models and serving (one model loaded at a time, one A100-SXM4-80GB)
| | Qwen | Mistral |
|---|---|---|
| Weights | `{q['model_id']}` @ `{q['revision']}` | `{m['model_id']}` @ `{m['revision']}` |
| Identity evidence | Experiments 21/26 commit | OpenRouter's `hugging_face_id` for `{C.OPENROUTER_MISTRAL}` (Experiment 22's model) is this repo |
| Class | `AutoModelForCausalLM` via Experiment 21's `Qwen` class, unchanged | `Mistral3ForConditionalGeneration`, text path only (input_ids, no pixel_values) |
| Tokenizer / template | {q['tokenizer']} | {m['tokenizer']} |
| Face tokens | ids {list(q['face_ids'].values())}; digit, space, digit | ids {list(m['face_ids'].values())}; digit, space, digit |
| Precision | bf16 weights/activations, separate fp32 copy of lm_head, fp32 logits | same |

Both: batch 1, prompt prefilled once, then one token at a time through the KV cache (generation and primary scoring use the same
arithmetic), exact full-vocabulary log-softmax at every step, deterministic flags as in Experiment 21, max 128 new tokens.
Greedy = argmax. Sampling = softmax(fp32 logits / {C.TEMPERATURE}), top_p 1.0, no top_k, `torch.multinomial` with a CUDA generator
seeded per call from the seed table (feasibility {C.SEED_BASE['feasibility']}+, reference {C.SEED_BASE['reference']}+, target
{C.SEED_BASE['target']}+; Mistral offset +{C.MODEL_SEED_OFFSET['mistral']}). Mistral is served without its optional
SYSTEM_PROMPT.txt (one user message, as in Experiment 22's API calls). Experiment 22 used DeepInfra's hosted copy; its
precision there is unknown, so Experiment 22 responses are not reused as observations.

## Stages and stop rules
1. Preflight, per model: G x3, F x3, Fanon x1 (Experiment 21's prompts), Qwen also Experiment 26's twelve prompts; four
   feasibility samples (discarded); three crossed prompts as a format check; matched-prefix G|G, F|G, F|F, Fanon|G.
   Gates (all must pass; otherwise STOP): serving identity; template (Qwen empty think block and no system turn; Mistral
   rendered G exactly `<s>[INST]<instruction>[/INST]`); face tokens; finite face log-probs and raw six-face mass >= {C.MIN_FACE_MASS};
   scorer reproduces generation within {C.SCORER_TOL_LOGP} nats; G/F repeats bit-identical; greedy G is ten valid integers;
   numerical floor (incremental vs full pass) <= {C.FLOOR_STOP_P}. Qwen only: G/F equal Experiment 21 and every six-face vector
   within {C.REPRO_TOL_P}; Experiment 26's twelve free outputs identical and teacher-forced vectors within {C.REPRO_TOL_P};
   this package's engine bit-identical to Experiment 21's class. No accuracy gate.
2. Corpus, per model: {C.N_REFERENCE} reference then {C.N_TARGETS} target sequences under Experiment 21's G prompt at T={C.TEMPERATURE},
   seeds in table order; invalid draws are kept and skipped; STOP if more than {C.MAX_DRAW_FACTOR}N draws are needed. Duplicates
   are kept and reported. The corpus is written and hashed before any prediction prompt is built. N={C.N_TARGETS} per generator is
   final for this run (no expansion).
3. Trials: built mechanically from the frozen templates and both corpora; trial file hashed; integrity table written.
4. Predict, per model: every trial with that predictor, seeded shuffle; then policy scoring (G, F, Fanon) of all items.
5. Main checks before analysis: completeness, prompt hashes, forced faces equal targets, finite log-probs, scorer = generation
   (subset), oracle = sampling distribution, per-model floor <= {C.FLOOR_STOP_P}.

## Target items
- Tier A (2, descriptive bridge): Qwen's greedy G `{P.seq_str(C.QWEN_G_REF)}` and Mistral's greedy G (preflight).
- Tier B (primary): {C.N_TARGETS} sampled sequences per generator.
- Each item's D evidence: the generator's reference sequence number (i mod {C.N_REFERENCE}) + 1 (Tier A: number 1); never a scored target.

## Trials ({n_trials} = 2 predictors x {2 + 2 * C.N_TARGETS} items x 6 conditions x 9 arms)
Conditions (scored original positions; revealed prefix): {', '.join(f"{k} ({v['positions'][0]}-{v['positions'][-1]}; 1-{v['reveal']})" for k, v in C.CONDITIONS.items())}.
Suites: bridge to Experiment 26 = {C.BRIDGE}; fixed position 7 with growing partial history = {C.FIXED7}; immediate next = {C.IMMEDIATE}.
Arms: framing A/T/R x evidence H/I/D (`prompts_frozen.md`). R is "your own model" on the diagonal and "a different model, not your
own model" off it, so the relational claim is true in every cell; T always names the true target generator.

## Measurements
- Teacher-forced six-face distribution p at every scored position, with the true target window as the assistant history
  (incremental arithmetic; primary). Free greedy output with its digit-step vectors (secondary).
- Target distribution q_j: the generator's six-face distribution under the G prompt given the item's true rolls 1..j-1
  (assistant history). The prediction prompt puts the revealed rolls in the user text instead; these are different computations.
- Native policy n_j: the predictor's own G distribution at the same history.
- Full-pass rescoring of all Tier A trials and a seeded {C.FULL_PASS_FRACTION_B:.0%} of Tier B trials, and of all policy rows: per-model floor.

## Estimands (Tier B; resampling unit = distinct target string within generator; {C.BOOTSTRAP_B} cluster-bootstrap draws, seed {C.BOOTSTRAP_SEED})
Per (predictor, item), a metric is averaged with equal weight over the selected conditions, arms and positions.
- E1 (primary, RQ2): self-advantage interaction on JS(p, q) in bits, arm AH, all conditions and positions:
  S_Qwen = mean over Qwen items of JS(Mistral) - JS(Qwen); S_Mistral = mean over Mistral items of JS(Qwen) - JS(Mistral);
  interaction = (S_Qwen + S_Mistral) / 2. Positive = predictors are closer to their own model. Also KL(q||p), TV, -log2 p(true roll), all arms.
- E2 (RQ4): the same interaction for the native policies n (no prediction wrapper), and prediction minus native per cell.
- E3 (RQ3 identity): change T-A and R-A per cell (paired on item, condition, evidence) and the difference-in-differences
  diagonal minus off-diagonal. Negative DiD = the identity cue helps a predictor more on its own model.
- E4 (RQ3 guidance): D-H, I-H, D-I per cell under framing A.
- E5: E1 within the fixed-position suite (position 7), the immediate-next suite (first window position) and the bridge suite.
- E6: E1 against the target distribution tempered to T={C.TEMPERATURE} (sensitivity).
- RQ1: G vs F (and Fanon) matched-prefix distributions per model on its own greedy G (Tier A, descriptive), and k0 arms vs q.
Secondary: p(true roll), rank, top-1 = true roll, top-1 = target's top, free-output exact match, six-face mass, free vs forced.
Tier A is reported per cell as a case study, never pooled with Tier B. Interpretation rules: a diagonal advantage on AH that is
matched by the native-policy advantage (E2) is shared procedural tendency, not identity knowledge; only a negative DiD (E3)
beyond the floor would point to identity-sensitive prediction, and even that is not evidence of introspective access.

## Budget
GPU cap ${C.GPU_CAP_USD:.0f}, warn at ${C.GPU_WARN_USD:.0f}; estimate printed by `dryrun` and recomputed from preflight timings before predict.
The instance is destroyed at the end, also after a failure.
"""


def write_once(path: Path, text: str):
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{path} is frozen and would change; refusing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def freeze():
    write_once(C.EXP / "PROTOCOL_FROZEN.md", protocol_text())
    write_once(C.EXP / "prompts_frozen.md", P.render_frozen())
    files = {f"src/spar_dynamic/dice_crossed_guidance/{p.name}": file_sha(p) for p in sorted(SRC.glob("*.py"))}
    for p in (C.EXP21 / "raw_attempts.jsonl", C.EXP21 / "matched_prefix.jsonl", C.EXP26 / "main" / "teacher_forced.jsonl"):
        files[str(p.relative_to(C.EXP.parents[1])).replace("\\", "/")] = file_sha(p)
    files["PROTOCOL_FROZEN.md"] = file_sha(C.EXP / "PROTOCOL_FROZEN.md")
    files["prompts_frozen.md"] = file_sha(C.EXP / "prompts_frozen.md")
    inputs = C.EXP / "inputs_sha256.json"
    if inputs.exists():
        old = json.load(open(inputs, encoding="utf-8"))["files"]
        if any(old[k] != files[k] for k in ("PROTOCOL_FROZEN.md", "prompts_frozen.md")):
            raise SystemExit("inputs_sha256.json disagrees with the frozen protocol")
        print("already frozen:", old["PROTOCOL_FROZEN.md"][:12])
        return
    json.dump(dict(tag=C.TAG, files=files), open(inputs, "w", encoding="utf-8"), indent=2)
    print("frozen:", files["PROTOCOL_FROZEN.md"][:12], files["prompts_frozen.md"][:12])


def dryrun():
    print(protocol_text())
    seq, ref = list(C.QWEN_G_REF), [3, 1, 5, 6, 2, 4, 1, 3, 6, 2]
    for fr, ev, cond, pred, tgt in (("A", "H", "k3", "qwen", "qwen"), ("T", "D", "m3", "mistral", "qwen"), ("R", "I", "k8", "qwen", "mistral")):
        print(f"\n=== {pred} predicts {tgt}, {cond}, {fr}{ev}\n{P.prompt(fr, ev, cond, pred, tgt, seq, ref)}")
    fake = [dict(item_id=f"{t}-{g}-{i}", tier=t, generator=g, sequence=seq, ref_id="r", ref_sequence=ref)
            for g in C.MODELS for t, n in (("A", 1), ("B", C.N_TARGETS)) for i in range(n)]
    print("\n", json.dumps(A.call_table(P.build_trials(fake), fake), indent=2))


def _report(res: dict, title: str) -> str:
    lines = [f"# {title}\n", f"**Overall: {res['overall']}**\n", "| Gate | Status | Detail |", "|---|---|---|"]
    for k, v in res["gates"].items():
        lines.append(f"| {k} | {v['status']} | `{json.dumps(v['detail'], default=str)[:400]}` |")
    if res.get("info"):
        lines.append(f"\nInformation (not gated): `{json.dumps(res['info'], default=str)}`\n")
    return "\n".join(lines) + "\n"


def gate_preflight(model: str):
    res = A.preflight_gates(model)
    json.dump(res, open(C.PRE / model / "preflight_gates.json", "w", encoding="utf-8"), indent=2, default=str)
    (C.PRE / model / "PREFLIGHT_REPORT.md").write_text(_report(res, f"Preflight, {model} ({C.TAG})"), encoding="utf-8")
    print(res["overall"], {k: v["status"] for k, v in res["gates"].items()})
    print(json.dumps(res["info"], default=str))


def gate_corpus(model: str):
    res = A.corpus_gate(model)
    json.dump(res, open(C.CORPUS / model / "corpus_gate.json", "w", encoding="utf-8"), indent=2, default=str)
    print(res["overall"], {k: v["status"] for k, v in res["gates"].items()})
    print(json.dumps(res["info"], default=str))


def _csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def build_trials():
    for m in C.MODELS:
        for p in (C.PRE / m / "preflight_gates.json", C.CORPUS / m / "corpus_gate.json"):
            if json.load(open(p, encoding="utf-8"))["overall"] != "PASS":
                raise SystemExit(f"{p} did not pass")
    out = C.TRIALS / "trials.jsonl"
    if out.exists():
        raise SystemExit(f"{out} exists; trials are built once")
    items = A.build_items()
    trials = P.build_trials(items)
    C.TRIALS.mkdir(parents=True, exist_ok=True)
    json.dump(items, open(C.TRIALS / "items.json", "w", encoding="utf-8"), indent=1)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for t in trials:
            f.write(json.dumps(t) + "\n")
    _csv(C.TRIALS / "integrity.csv", A.integrity_rows(items))
    ct = A.call_table(trials, items)
    json.dump(ct, open(C.TRIALS / "call_table.json", "w", encoding="utf-8"), indent=2)
    corpus_sha = {m: file_sha(C.CORPUS / m / "sampled.jsonl") for m in C.MODELS}
    gate = dict(overall="PASS", models=list(C.MODELS), trials_sha256=file_sha(out), items_sha256=file_sha(C.TRIALS / "items.json"),
                corpus_sha256=corpus_sha, n_trials=len(trials), call_table=ct)
    json.dump(gate, open(C.TRIALS / "trials_gate.json", "w", encoding="utf-8"), indent=2)
    print(json.dumps(gate, indent=2))


def analyse():
    from spar_dynamic.dice_crossed_guidance.figures import all_figures
    data = A.load_main()
    checks = A.main_checks(data)
    json.dump(checks, open(C.MAIN / "main_checks.json", "w", encoding="utf-8"), indent=2, default=str)
    print("main checks:", checks["overall"], {k: v["status"] for k, v in checks["gates"].items()})
    if checks["overall"] != "PASS":
        print("comparative analysis not run: a main check failed")
        return
    rows = A.tidy(data)
    _csv(C.ANALYSIS / "tidy_positions.csv", rows)
    _csv(C.ANALYSIS / "by_condition.csv", A.by_condition(rows))
    _csv(C.ANALYSIS / "by_arm.csv", A.by_arm(rows))
    _csv(C.ANALYSIS / "tier_a.csv", A.tier_a(rows))
    _csv(C.ANALYSIS / "mass_by_cell_arm.csv", A.mass_by_cell_arm(rows))
    est = A.estimands(rows, data["items"])
    rq1 = A.rq1_tables()
    _csv(C.ANALYSIS / "rq1_G_vs_F.csv", rq1)
    summary = dict(tag=C.TAG, main_checks=checks["overall"], floors=checks["floors"], estimands=est,
                   cells_AH_js=A.cell_table(rows, "js", arm="AH"), cells_AH_js_native=A.cell_table(rows, "js_native", arm="AH"),
                   cells_AH_kl=A.cell_table(rows, "kl", arm="AH"), cells_AH_H_target=A.cell_table(rows, "H_target", arm="AH"),
                   cells_all_js=A.cell_table(rows, "js"), clusters={m: len(v) for m, v in A.clusters(data["items"]).items()})
    json.dump(summary, open(C.ANALYSIS / "summary.json", "w", encoding="utf-8"), indent=2, default=str)
    all_figures(rows, summary, rq1, C.ANALYSIS / "figures")
    print("analysis written to", C.ANALYSIS)


if __name__ == "__main__":
    phase = sys.argv[1]
    fns = {"freeze": freeze, "dryrun": dryrun, "build_trials": build_trials, "analyse": analyse,
           "gate_preflight": lambda: gate_preflight(sys.argv[2]), "gate_corpus": lambda: gate_corpus(sys.argv[2])}
    fns[phase]()
