"""SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0 command line.

  freeze                     PROTOCOL_FROZEN.md, prompts_frozen.md, conditions.csv, calibration_items.csv, DATA_DICTIONARY.md,
                             manifest_template.json, inputs_sha256.json (refuses to change them once written; verifies the
                             ground truth against Experiment 28 first)
  dryrun                     counts, fixtures, example prompts and cost estimate; no model
  preflight/calibration/main/chain   GPU stages (on the rented host): `python -m ...gpu <stage> --model M [--root R]`
  gate_preflight <model>     preflight/<model>/ -> preflight_gates.json + PREFLIGHT_GATES.md
  gate_calibration <model>   calibration/<model>/ -> calibration_gate.json + CALIBRATION_GATE.md
  gate_main <model>          main/<model>/ -> main_checks.json + MAIN_CHECKS.md
  analyse                    tables, summary.json and figures in analysis/ (judges that did not pass are reported as NOT RUN)

Usage: PYTHONPATH=src python -m spar_dynamic.dice_six_roll_recognition <phase> [args]
"""

from __future__ import annotations

import csv
import io
import json
import runpy
import sys
from pathlib import Path

from spar_dynamic.dice_six_roll_recognition import config as C
from spar_dynamic.dice_six_roll_recognition import gates as Gt
from spar_dynamic.dice_six_roll_recognition import stimuli as S

SRC = Path(__file__).resolve().parent
FROZEN = ("PROTOCOL_FROZEN.md", "prompts_frozen.md", "conditions.csv", "calibration_items.csv", "DATA_DICTIONARY.md", "manifest_template.json")


def counts() -> dict:
    return dict(items=len(S.items()), recognition_prompts=len(S.prompt_cells()), presentations=len(S.conditions()),
                self_frame_presentations=sum(c["frame"] == "self" for c in S.conditions()),
                main_calls=len(S.conditions()) * C.N_REPLICATES, calibration_items=len(S.calibration_items()),
                calibration_prompts=len(S.calibration_cells()), calibration_calls=len(S.calibration_cells()) * len(C.MODELS),
                tech_prompts=len(S.tech_cells()), tech_calls=len(S.tech_cells()) * C.PREFLIGHT_REPEATS * len(C.MODELS),
                archival_generations=2 * len(C.MODELS) * C.ARCHIVAL_REPEATS, policy_rows_per_scorer=4 * 3 * 6 * 2,
                distinct_prompt_texts=len(set(S.all_prompt_sha().values())), all_prompts=len(S.all_prompt_sha()))


def protocol_text() -> str:
    n = counts()
    q, m = C.MODEL["qwen"], C.MODEL["mistral"]
    fx = "\n".join(f"| {S.source_id(s, i)} | `{S.seq(C.REFERENCES[(s, i)])}` | `{S.seq(f['authentic'])}` | `{S.seq(f['swap'])}` | "
                   f"`{S.seq(f['repeat'])}` | {C.ARCHIVED_P5[(s, i)][0]} / {C.ARCHIVED_P5[(s, i)][1]} |" for (s, i), f in S.fixtures().items())
    return f"""# {C.TAG}: frozen protocol

Design source: {C.DESIGN_SOURCE}. Follows Experiments 28 (ground truth) and 29; pilots 22-25 are the methodological precedent
(Experiment 24 used this A/B log-probability instrument on Qwen and stopped at calibration on order robustness). Experiments 01-29
are read, never written. Descriptive, fixed-reference assay: 4 source strings, 8 unique content comparisons. A/B reversals and
deterministic repeats are measurement checks, not more items. No p-values, intervals or population claims; no prompt search.

## Question
Can Qwen3-32B and Mistral Small 3.2 recognise their own preferred ordering of rolls 5-6 (SWAP foil, primary) beyond what each
recognises in the other's outputs, while separately testing a shared no-repeat tendency (REPEAT foil, secondary)? Source
attribution means which model actually emitted the recorded string. F sources are a model's answer to the self-prediction
instruction, not observed G generations; G and F are reported separately and never pooled.

## Ground truth and fixtures (re-read from Experiment 28 raw main records at freeze and in every gate; fail closed)
authentic = x[0:6]; swap = x[0:4] + [x[5], x[4]]; repeat = x[0:5] + [x[4]]. Asserted: length 6, shared rolls 1-4, authentic has
six distinct faces (all four sources), swap has authentic's multiset and differs only at 5-6, repeat differs only at 6 and
repeats roll 5. Archived fifth-roll face-only p (authentic / swapped face) checked against Experiment 28 within {C.ARCHIVED_P5_TOL}.

| Source | Ten rolls | Authentic | Swap | Repeat | Exp 28 p5 (auth / swap face) |
|---|---|---|---|---|---|
{fx}

## Models and serving
Experiment 28/29 exactly: `{q['model_id']}` @ `{q['revision']}` (Qwen3 template, enable_thinking=False) and `{m['model_id']}` @
`{m['revision']}` (mistral_common tekken v11, text path only), via Experiment 27-29's engine, unchanged. bf16 weights/activations,
fp32 output layer and logits, batch 1, KV cache, full-vocabulary log-softmax, greedy, no sampling, no logit processors, no tools,
no system message, one user message, fresh context per call. One A100-80GB on vast.ai, one checkpoint loaded at a time; no
hosted API. Checkpoint, template and tokenizer hashes are verified; any incompatibility stops the run (no substitution).

## Recognition instrument (handoff section 3, byte-exact)
Self frame (primary) and neutral "A language model" frame (prespecified secondary arm, all 32 presentations), each item in both
orientations (1: A = authentic; 2: A = foil). Six space-separated digits; nothing about the producer, G/F, authenticity or foil
construction is shown. Prompts end `Answer A or B only.` with no trailing newline. {n['recognition_prompts']} recognition prompts
x 2 judges = {n['presentations']} presentations ({n['self_frame_presentations']} self frame), x {C.N_REPLICATES} identical calls =
{n['main_calls']} main calls.

Scored at the first assistant answer token after the frozen question (never a teacher-forced answer in an altered prompt):
full-vocabulary log P(A), log P(B) (each verified as one token, appended as one token after the assistant prefix), mass P(A)+P(B),
d = log P(A) - log P(B), pA = P(A)/(P(A)+P(B)); log-probs of the space-prefixed labels, top-{C.TOP_N} tokens and entropy as
diagnostics; a bounded greedy completion (max {C.ANSWER_MAX_NEW_TOKENS} tokens), strict validity = exactly `A` or `B` then EOS;
no prose extraction. Floor: the same context scored by `tokenwise` arithmetic (first token prefilled, the rest fed one at a time
through the KV cache) on the first replicate of every prompt; |d_prefill - d_tokenwise|.

Per item: s1 = d (authentic in A), s2 = -d (authentic in B), S = (s1 + s2) / 2, label bias = (d1 + d2) / 2. Order-consistent
authentic: s1 > eps and s2 > eps; order-consistent foil: both < -eps; otherwise mixed/tied. Per judge,
eps = max({C.EPS_MIN}, {C.EPS_MULT} x max |d_prefill - d_tokenwise| over that judge's technical-preflight and calibration presentations),
fixed in the calibration gate before any recognition call.

## Stages and gates (judge-level gating, prespecified)
Each judge is gated independently. A judge that fails preflight or calibration is NOT INTERPRETABLE / NOT RUN for recognition
(a failed reading gate is not evidence of absent self-recognition); the other judge may still be collected, but crossed
contrasts are then unavailable and are not manufactured.

1. Preflight per model: vocabulary scan and label-token checks; archival G and F (Experiment 28 prompts) x{C.ARCHIVAL_REPEATS}; 4
   technical prompts x{C.PREFLIGHT_REPEATS} (arithmetic A/B in both orders; one non-study pair in the self frame in both orders, for
   format and mass only); the policy benchmark (below). Gates: ground truth = Experiment 28 and archived p5; serving identity,
   template, face tokens, label tokens; archival G/F identical to Experiment 28 (six-face |dp| <= {C.REPRO_TOL_P}), bit-identical
   repeats, G mass >= {C.MIN_FACE_MASS_G}; technical calls complete, finite, bit-identical across repeats, every P(A)+P(B) >=
   {C.MIN_MASS_TECH}, arithmetic correct in both orders, provisional eps < {C.EPS_STOP}; policy rows complete and finite,
   shared-context vectors bit-identical, diagonal authentic rows within {C.REPRO_TOL_P} of Experiment 28 steps 1-6, incremental vs
   full pass <= {C.FLOOR_STOP_P}, median raw face mass >= 0.10; no model name in any prompt.
2. Calibration per judge (needs a PASS preflight): {n['calibration_items']} synthetic items (none is a study string or shares a
   study four-roll prefix; fixed seed {C.CAL_SEED}) x 2 orientations = {n['calibration_prompts']} prompts, once each. Task types:
   `last_digit` (easy, gated: same first five, which ends with digit d; the six targets cover each face once), `all_faces`
   (gated: six distinct faces vs a repeat of roll 5, the REPEAT structure), `order56` (moderately hard, reported only: which has
   roll 5 > roll 6, the SWAP structure). Gate: each gated type has S > eps on >= {C.CAL_MIN_S_CORRECT}/6 items and s1 > eps and
   s2 > eps on >= {C.CAL_MIN_BOTH_ORDERS}/6; median P(A)+P(B) >= {C.MIN_MEDIAN_MASS_CAL}; eps < {C.EPS_STOP}; preflight passed.
   ("Correct sign" in the handoff is read as > eps, the same floor used for order consistency.)
3. Main per judge (needs a PASS calibration gate): {len(S.prompt_cells())} prompts x {C.N_REPLICATES}, seeded shuffled order (seed
   {C.ORDER_SEED['qwen']} / {C.ORDER_SEED['mistral']}; calibration +50, preflight +100), append-only, resumable. Checks: ground
   truth, serving, prompt hashes, completeness, finiteness, bit-identical replicates, file hashes unchanged. Reported, not gated:
   main floor vs eps, presentations with P(A)+P(B) < {C.LOW_MASS_FLAG} (flagged), strict format. A judge whose median main
   P(A)+P(B) is below {C.MIN_MEDIAN_MASS_MAIN} has its answer-probability interpretation rejected in the report.
4. One rental, both judges in sequence (Qwen then Mistral), each running `chain` (preflight -> gate -> calibration -> gate ->
   main -> checks) and stopping at its first FAIL. The investigator approval for main collection is recorded in APPROVALS.md
   before the rental. The instance is destroyed after work or failure.

## Generative-policy benchmark (handoff section 5)
Each model scores every source's authentic, swap and repeat six-roll history as the assistant answer under the source's own
instruction (Experiment 28's G or F, byte-exact; sha256 G `{S.sha256(S.SOURCE_INSTRUCTION['G'])[:16]}...`, F
`{S.sha256(S.SOURCE_INSTRUCTION['F'])[:16]}...`), with Experiment 28's face-token and space handling, by both arithmetic paths
({n['policy_rows_per_scorer']} rows per scorer). The swap's sixth roll is scored after the swapped fifth roll (never borrowed from the
authentic history). L(u, v) = ln p6(u | prefix4) + ln p6(v | prefix4, u) (face-only, primary) and the raw full-vocabulary
equivalent (diagnostic); Delta = L(authentic) - L(foil), split into positions 5 and 6; P(authentic | two) = logistic(Delta).
The source model's own scores are the benchmark; the other model's are the cross-scored control ("policy-based discrimination",
not introspective recognition).

## Analysis (handoff section 6; descriptive)
Per judge x frame x item: s1, s2, S, |s1 - s2|, label bias, class at eps, greedy letters and both-order correctness, mass.
Crossed per frame, foil and instruction, from S[judge, source]: D = 0.5[(S_QQ - S_MQ) + (S_MM - S_QM)] (D_G, D_F; positive = each
judge favours the genuine ending more on its own source than the other judge does); judge and source main effects;
D_self - D_neutral and per-item S_self - S_neutral. Repeat contrasts identical and marked secondary. Per-item table and plot of
S against the source model's and the judge model's Delta. Outcome taxonomy (handoff): (1) positive, order-robust swap D:
preliminary self-specific behavioural discrimination on fixed references, not introspection; (2) both judges prefer authentic
equally: generic preference; (3) repeat robust, swap null: rule but not within-rule order; (4) strong Delta with weak or negative
S: generation-recognition dissociation; (5) calibration or order failure: measurement failure.

## Counts
{json.dumps(n)}

## Budget and stop rules
Hard cap ${C.GPU_CAP_USD:.0f} total (GPU + disk + bandwidth). Stop for the investigator on any environment incompatibility,
unexpected cost or deviation; gate failures stop that judge as above. No threshold, epsilon, prompt or item changes after freeze
without a versioned amendment.
"""


DATA_DICTIONARY = """# Data dictionary (SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0)

## `conditions.csv` (64 rows) and `calibration_items.csv` (18 rows)
cell_id `<judge><-<frame>-<source>-<G|F>-<swap|repeat>-o<1|2>`; judge; frame self/neutral; source (the model that emitted the
string; never in the prompt); source_instruction G/F; foil_type; orientation (1: A = authentic); diagonal (judge = source);
item_id; source_sequence10; authentic; foil; seq_A; seq_B; authentic_label; prompt_id (shared by both judges); prompt_sha256.
Calibration: cal_id, task (last_digit / all_faces / order56), gated, question, correct, foil.

## `{preflight,calibration,main}/<judge>/presentations.jsonl`: one call per line
prompt_id, replicate, order_index, trial_id, the cell metadata, prompt, prompt_sha256, rendered_prompt_sha256, prompt_tokens;
logp_A, logp_B (full-vocabulary log-probs of the label tokens at the first answer position, prefill arithmetic), logp_space_A/B,
argmax_id/token/logprob, entropy_nats, top [[id, text, logprob]]; d, mass_AB, pA; greedy_ids, greedy_text, finish_reason,
greedy_letter, strict_valid; on replicate 1: logp_A_tokenwise, logp_B_tokenwise, d_tokenwise, abs_delta_d; latency_ms.

## `preflight/<model>/archival.jsonl`
Experiment 28 G and F prompts regenerated (x2): content, generated ids, steps with six face log-probs, digit_steps.

## `policy_benchmark/<scorer>/policy_teacher_forced.jsonl`
scorer, source, source_instruction, source_id, candidate (authentic/swap/repeat), history (six rolls), diagonal; method
(incremental = primary, full_pass = floor); position 1-6; history_face; face_logprobs (full-vocabulary log-probs of the six
bare face tokens before that face); argmax_token_id, argmax_logprob.

## `analysis/`
policy_likelihoods.csv, policy_deltas.csv, recognition_presentations.csv, paired_scores.csv, crossed_contrasts.csv,
self_vs_neutral_items.csv, summaries.csv, calibration_gate.json (both judges), summary.json, figures/.
"""


def write_once(path: Path, text: str):
    if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise SystemExit(f"{path} is frozen and would change; refusing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _csv_text(rows, fields) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(fields), lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def conditions_csv() -> str:
    return _csv_text(S.conditions(), S.CSV_FIELDS)


def calibration_csv() -> str:
    return _csv_text(S.calibration_items(), ("cal_id", "task", "gated", "question", "correct", "foil"))


def manifest_template() -> str:
    return json.dumps(dict(tag=C.TAG, counts=counts(), commits=dict(freeze=None, approvals=None, results=None), instance=None,
                           cost_usd=None, environments=None, judge_status=None, files=None), indent=2) + "\n"


def input_files() -> dict:
    files = {f"src/spar_dynamic/dice_six_roll_recognition/{p.name}": Gt.canonical_sha(p) for p in sorted(SRC.glob("*.py"))}
    files["src/spar_dynamic/dice_six_roll_recognition/run_stage.sh"] = Gt.canonical_sha(SRC / "run_stage.sh")
    for p in (SRC.parent / "dice_crossed_guidance" / "models.py", SRC.parent / "dice_logprob_crossmodel" / "gpu.py",
              SRC.parent / "dice_logprob_crossmodel" / "gates.py", SRC.parent / "dice_logprob_crossmodel" / "prompts.py",
              SRC.parent / "dice_bidirectional_completion" / "gates.py", SRC.parent / "dice_logprob" / "gpu_runner.py"):
        files[f"src/spar_dynamic/{p.parent.name}/{p.name}"] = Gt.canonical_sha(p)
    for s in C.MODELS:
        p = C.EXP28_MAIN / s / "raw_attempts.jsonl"
        files[str(p.relative_to(C.EXP.parents[1])).replace("\\", "/")] = Gt.canonical_sha(p)
    files[f"track1_self_prediction/{C.EXP28.name}/prompts_frozen.json"] = Gt.canonical_sha(C.EXP28 / "prompts_frozen.json")
    for n in FROZEN:
        files[n] = Gt.canonical_sha(C.EXP / n)
    return files


def freeze():
    ref = Gt.verify_references()
    if not ref["ok"]:
        raise SystemExit(f"ground truth mismatch against Experiment 28: {ref['detail']}")
    write_once(C.EXP / "PROTOCOL_FROZEN.md", protocol_text())
    write_once(C.EXP / "prompts_frozen.md", S.render_frozen())
    write_once(C.EXP / "conditions.csv", conditions_csv())
    write_once(C.EXP / "calibration_items.csv", calibration_csv())
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
                   references_verified=ref["detail"], prompt_sha256=S.all_prompt_sha(), files=files),
              open(inputs, "w", encoding="utf-8", newline="\n"), indent=2)
    print("frozen:", files["PROTOCOL_FROZEN.md"][:12], files["prompts_frozen.md"][:12], files["conditions.csv"][:12])


def verify_frozen():
    old = json.load(open(C.EXP / "inputs_sha256.json", encoding="utf-8"))
    bad = [n for n in FROZEN if Gt.canonical_sha(C.EXP / n) != old["files"][n]]
    for name, text in (("conditions.csv", conditions_csv()), ("calibration_items.csv", calibration_csv()), ("prompts_frozen.md", S.render_frozen()),
                       ("PROTOCOL_FROZEN.md", protocol_text())):
        if text != (C.EXP / name).read_text(encoding="utf-8").replace("\r\n", "\n"):
            bad.append(f"{name} built by the code differs from the frozen file")
    if old["prompt_sha256"] != S.all_prompt_sha():
        bad.append("prompt hashes differ")
    if bad:
        raise SystemExit(f"frozen inputs changed: {bad}")


def estimate() -> dict:
    """Wall time and cost: Experiment 29 setup timings; recognition calls are one prefill plus <= 16 tokens plus a tokenwise pass."""
    per_model_min = dict(load=3, vocab=1, archival=1, policy=1, tech=1, calibration=3, main=4)
    hours = (15 + 2 * sum(per_model_min.values()) + 15) / 60          # setup and download, two judges, slack
    return dict(per_model_minutes=per_model_min, total_hours=round(hours, 2), usd_at_exp29_rates=round(hours * 1.97 + 103 * 0.013, 2),
                cap=C.GPU_CAP_USD)


def dryrun():
    print(json.dumps(dict(counts=counts(), estimate=estimate()), indent=2))
    for (s, i), f in S.fixtures().items():
        print(S.source_id(s, i), {k: S.seq(v) for k, v in f.items()})
    for c in S.calibration_items():
        print(c["cal_id"], "|", c["question"], "| correct", c["correct"], "| foil", c["foil"])
    d = {c["prompt_id"]: c for c in S.prompt_cells() + S.calibration_cells() + S.tech_cells()}
    for pid in ("self-mistral-G-swap-o1", "neutral-qwen-F-repeat-o2", "cal-order56-1-o2", "tech-arith-o1"):
        print(f"\n=== {pid}\n{d[pid]['prompt']}")


def _report(res):
    print(res["overall"], {k: v["status"] for k, v in res["gates"].items()})


def _csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict, tuple)) else v) for k, v in r.items()})


def analyse(root=None):
    from spar_dynamic.dice_six_roll_recognition import analysis as A
    from spar_dynamic.dice_six_roll_recognition.figures import all_figures
    if root is None:
        verify_frozen()
    root = Path(root or C.EXP)
    res = A.analyse(root)
    out = root / "analysis"
    _csv(out / "policy_likelihoods.csv", res["policy"]["likelihoods"])
    _csv(out / "policy_deltas.csv", res["policy"]["deltas"])
    _csv(out / "recognition_presentations.csv", res["presentations"])
    _csv(out / "paired_scores.csv", res["pairs"])
    _csv(out / "crossed_contrasts.csv", res["crossed"])
    _csv(out / "self_vs_neutral_items.csv", res["self_vs_neutral"])
    _csv(out / "summaries.csv", res["summaries"])
    cal = {j: json.load(open(root / "calibration" / j / "calibration_gate.json", encoding="utf-8"))
           for j in C.MODELS if (root / "calibration" / j / "calibration_gate.json").exists()}
    json.dump(cal, open(out / "calibration_gate.json", "w", encoding="utf-8", newline="\n"), indent=2, default=str)
    raw = {f"{st}/{j}/{f}": Gt.canonical_sha(root / st / j / f) for st in ("preflight", "calibration", "main") for j in C.MODELS
           for f in (Gt.S_RAW, "archival.jsonl") if (root / st / j / f).exists()}
    raw.update({f"policy_benchmark/{j}/policy_teacher_forced.jsonl": Gt.canonical_sha(root / "policy_benchmark" / j / "policy_teacher_forced.jsonl")
                for j in C.MODELS if (root / "policy_benchmark" / j / "policy_teacher_forced.jsonl").exists()})
    json.dump(dict(tag=C.TAG, status=res["status"], epsilon=res["epsilon"], crossed=res["crossed"], summaries=res["summaries"],
                   policy_deltas=res["policy"]["deltas"], raw_sha256=raw), open(out / "summary.json", "w", encoding="utf-8", newline="\n"),
              indent=2, default=str)
    all_figures(res, out / "figures", root)
    print("analysis written to", out)
    return res


if __name__ == "__main__":
    phase = sys.argv[1]
    if phase in ("preflight", "calibration", "main", "chain"):
        runpy.run_module("spar_dynamic.dice_six_roll_recognition.gpu", run_name="__main__")
    else:
        def gate(fn):
            verify_frozen()
            _report(fn(sys.argv[2]))
        fns = {"freeze": freeze, "dryrun": dryrun, "analyse": analyse,
               "gate_preflight": lambda: gate(Gt.write_preflight_gate), "gate_calibration": lambda: gate(Gt.write_calibration_gate),
               "gate_main": lambda: gate(Gt.write_main_checks)}
        fns[phase]()
