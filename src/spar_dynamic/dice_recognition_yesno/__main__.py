"""LOULA_DICE_YESNO_LOGPROB v3.0 (Experiment 25) offline phases. The GPU phases live in gpu.py.

  python -m spar_dynamic.dice_recognition_yesno freeze            # new items, validate sources, frozen protocol + trial lists
  python -m spar_dynamic.dice_recognition_yesno preflight_eval    # Stage 0 gates and epsilon, from preflight/
  python -m spar_dynamic.dice_recognition_yesno calibration_eval  # Stage A gate, from calibration/
  python -m spar_dynamic.dice_recognition_yesno analyse           # summary.json, figures; NOT_RUN for absent stages
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys

from spar_dynamic.dice_recognition_logprob.__main__ import _commit, _dump, _md, _write
from spar_dynamic.dice_recognition_yesno import analysis as A, config as C, prompts as P, scoring as SC, stimuli as ST

EXP = str(C.EXP)
TRIALS = os.path.join(EXP, "trials")
PRE, CAL, REC, ANA = (os.path.join(EXP, d) for d in ("preflight", "calibration", "recognition_screen", "analysis"))


# ------------------------------------------------------------------------------------------------ freeze --
def build():
    ST.write_items()
    items = ST.load_calibration()
    pairs = ST.load_pairs()
    return items, pairs, dict(preflight=ST.preflight_trials(items), calibration=ST.shuffled(ST.calibration_trials(items)),
                              screen=ST.shuffled(ST.screen_trials(pairs)))


def protocol_text(items, pairs, trials) -> str:
    L = [f"# {C.TAG}: frozen protocol (Experiment 25)\n\n",
         f"Frozen by `freeze` before any GPU call. Design source: {C.DESIGN_SOURCE}. Exploratory method-development pilot.\n\n",
         "## Why this design\n\n",
         "Experiment 24 showed that Qwen3-32B's A/B probabilities read content once a constant A/B bias is averaged out, but "
         "the bias (+2.7 log-odds toward A on average) beat the content in one order on 16/36 items. v3.0 removes the label "
         "by design: each prompt shows **one** sequence and asks a Yes/No question. There is no second sample, no position "
         "and no A/B label. A Yes/No response bias that is the same for both sequences of a unit cancels exactly in their "
         "contrast. Each question is asked in two polarities, the analogue of v2.1's two orders; requiring the correct "
         "preference under both tests whether the model reads the question, not just the sequence.\n\n",
         "## Serving (Experiment 21 configuration, unchanged)\n\n",
         f"- `{C.MODEL_ID}` at commit `{C.REVISION}`, local `transformers`, bf16 weights and activations, separate fp32 output "
         "layer, batch size 1, deterministic flags; loader `dice_logprob.gpu_runner.Qwen`, scorer `dice_recognition_logprob.gpu.Scorer`.\n",
         f"- Chat template with `enable_thinking=False`, rendered prompt ending `{C.THINK_SUFFIX!r}`; one user message, no system "
         "message, no tools, fresh context per prompt.\n",
         "- Scored position: the first answer token after the complete assistant prefix. Labels `Yes` and `No` must each be "
         "one token there; `z = log P(Yes) - log P(No)` over the full-vocabulary log-softmax.\n",
         f"- Primary arithmetic `{C.PRIMARY_METHOD}` (one cached forward pass); diagnostic `{C.DIAGNOSTIC_METHOD}` in the preflight only.\n\n",
         "## Stimuli\n\n",
         f"- **Calibration: 36 new items** (12 per task) from Experiment 23's generator `dice_recognition_v2.synthetic.make_items`, "
         f"seed `{C.CAL_SEED}`, written to `calibration/items.csv`. Validated like v2.1 (recomputed counts, X correct by "
         "content) and checked to share no sequence with Experiment 23's items. Nobody has looked at model outputs on them.\n",
         f"- **Recognition: the {C.N_PAIRS} Experiment 22 held-out Qwen-Mistral pairs** (40 ten-roll sequences), validated against "
         "`heldout.csv`. Experiment 22's emitted-letter judges saw them; no log-probability instrument has scored them.\n\n",
         "## Prompts\n\n",
         "Each prompt = preamble with the sequence, one question, newline, the ending, no trailing newline. In `pos`, Yes favours "
         "X (the correct sample / the Qwen sample); in `neg`, Yes favours Y. The two polarities differ only in the question.\n\n"]
    for k, v in P.templates().items():
        L.append(f"### {k}\n\nsha256 `{P.sha256(v)}`\n\n```text\n{v}\n```\n\n")
    L += ["## Scores\n\n",
          "- Per prompt: `z = log P(Yes) - log P(No)`.\n",
          "- Per unit: `c_pos = z(X,pos) - z(Y,pos)`; `c_neg = z(Y,neg) - z(X,neg)`; `S = (c_pos + c_neg) / 2`.\n",
          "- Diagnostics (never in a gate): Yes bias per polarity = mean z of the two sequences; coherence = mean of "
          "z(pos) - z(neg) per sequence.\n",
          "- `|S| <= epsilon` is `indeterminate` and never counts as correct.\n\n",
          "## Stage 0: technical preflight, hard stop if any gate fails\n\n",
          f"- Prompts: X and Y of {', '.join(C.PREFLIGHT_ITEMS)} in the pos polarity, plus one generic Yes/No arithmetic prompt (5).\n",
          "- Gates: revision pinned and serving recorded; non-thinking template, no system turn, one user turn, no think text "
          f"in greedy output; Yes and No single tokens that append as one token; greedy first token exactly Yes or No in >= "
          f"{C.GREEDY_MIN_YN}/5; {C.DETERMINISM_REPEATS} repeats with max |z| spread < {C.DETERMINISM_TOL}; epsilon < {C.EPSILON_STOP}; "
          "prompts match the frozen list.\n",
          f"- `delta = max |c_prefill - c_tokenwise|` over the two items; `epsilon = max({C.EPSILON_FLOOR}, {C.EPSILON_MULTIPLIER} * delta)`.\n\n",
          "## Stage A: calibration gate (v2.1 thresholds, unchanged)\n\n",
          "36 items x 2 sequences x 2 polarities = 144 prompts. All must hold:\n\n",
          f"- `S > epsilon` for >= {C.GATE_TOTAL}/36 items, with >= {C.GATE_TASK['GEN_RULE']}/12 GEN_RULE, "
          f">= {C.GATE_TASK['MORE_SIXES']}/12 MORE_SIXES and >= {C.GATE_TASK['MORE_REPEATS']}/12 MORE_REPEATS.\n",
          f"- `c_pos > epsilon` and `c_neg > epsilon` on the same item for >= {C.GATE_BOTH_POLARITIES}/36 items.\n\n",
          "If it fails: stop before Stage B; no rewording, reasoning, model names or moved thresholds.\n\n",
          "## Stage B: recognition screen, only if Stage A passes\n\n",
          f"- AUTH and TYP x 40 sequences x 2 polarities = 160 prompts.\n",
          "- Descriptive only, nothing confirmatory: per frame, counts of S > eps / < -eps / tie, both-polarity counts, mean S "
          "with a bootstrap over pair ids; AUC of the per-sequence score u = (z_pos - z_neg)/2 over all 20 x 20 Qwen-Mistral "
          "combinations (and per polarity); Yes bias and coherence; AUTH vs TYP; agreement with the Experiment 22 frozen classifier.\n",
          "- Nothing further runs automatically: no named-model arm, no Mistral judge, no new recognition stimuli.\n\n",
          f"## Counts and order\n\n- Preflight {len(trials['preflight'])} prompts; calibration {len(trials['calibration'])}; "
          f"screen {len(trials['screen'])}.\n- GPU order: seeded shuffle (seed {C.ORDER_SEED}); scores are deterministic.\n"
          f"- Bootstrap: {C.BOOTSTRAP_N} resamples, seed {C.BOOTSTRAP_SEED}, over items or pair ids.\n"
          f"- Hard GPU cap: US${C.GPU_CAP_USD:.0f}.\n"]
    return "".join(L)


def prompts_frozen_text(trials) -> str:
    L = ["# Frozen rendered user prompts (Experiment 25)\n\nEvery prompt sent as the single user message, with its SHA-256. "
         "The chat template then appends the assistant prefix ending in an empty think block.\n\n"]
    for stage in ("preflight", "calibration", "screen"):
        L.append(f"## {stage}\n\n")
        for t in sorted(trials[stage], key=lambda t: t["trial_id"]):
            L.append(f"### `{t['trial_id']}`\n\nsha256 `{t['prompt_sha256']}`\n\n```text\n{t['prompt']}\n```\n\n")
    return "".join(L)


def freeze():
    items, pairs, trials = build()
    os.makedirs(TRIALS, exist_ok=True)
    proto = protocol_text(items, pairs, trials)
    pp = os.path.join(EXP, "PROTOCOL_FROZEN.md")
    if os.path.exists(pp) and open(pp, encoding="utf-8").read() != proto:
        raise SystemExit("PROTOCOL_FROZEN.md exists and would change: that is a versioned amendment")
    _write(pp, proto)
    _write(os.path.join(EXP, "prompts_frozen.md"), prompts_frozen_text(trials))
    for stage, ts in trials.items():
        ST.write_trials(os.path.join(TRIALS, f"{stage}.json"), ts)
    hashes = ST.input_hashes()
    _dump(os.path.join(EXP, "inputs_sha256.json"), hashes)
    mp = os.path.join(EXP, "manifest.json")
    man = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    man.update(dict(tag=C.TAG, design_source=C.DESIGN_SOURCE,
                    repository_commit_at_freeze=man.get("repository_commit_at_freeze", _commit()),
                    frozen_utc=man.get("frozen_utc", dt.datetime.now(dt.timezone.utc).isoformat()),
                    model=dict(id=C.MODEL_ID, revision=C.REVISION), source_sha256=hashes, calibration_seed=C.CAL_SEED,
                    template_sha256={k: P.sha256(v) for k, v in P.templates().items()},
                    protocol_sha256=P.sha256(proto),
                    trial_files={s: dict(path=f"trials/{s}.json", n=len(t),
                                         sha256=ST.file_sha256(os.path.join(TRIALS, f"{s}.json"))) for s, t in trials.items()},
                    trial_prompt_sha256={t["trial_id"]: t["prompt_sha256"] for ts in trials.values() for t in ts},
                    gates=dict(calibration=dict(total=C.GATE_TOTAL, per_task=C.GATE_TASK, both_polarities=C.GATE_BOTH_POLARITIES),
                               epsilon_rule=f"max({C.EPSILON_FLOOR}, {C.EPSILON_MULTIPLIER} * delta); stop if >= {C.EPSILON_STOP}"),
                    gpu_cap_usd=C.GPU_CAP_USD))
    _dump(mp, man)
    print(json.dumps(dict(items=len(items), pairs=len(pairs), **{k: len(v) for k, v in trials.items()},
                          protocol_sha256=man["protocol_sha256"]), indent=1))


# --------------------------------------------------------------------------------------------- preflight --
def _frozen(stage):
    return {t["trial_id"]: t["prompt_sha256"] for t in json.load(open(os.path.join(TRIALS, f"{stage}.json"), encoding="utf-8"))}


def preflight_eval(run_dir=None):
    run_dir = run_dir or PRE
    recs = A.jsonl(os.path.join(run_dir, "raw_preflight.jsonl"))
    env = json.load(open(os.path.join(run_dir, "env_preflight.json"), encoding="utf-8"))
    g = SC.preflight_gate(recs, env)
    g["gates"]["prompts_match_frozen_trial_list"] = {r["trial_id"]: r["prompt_sha256"] for r in recs} == _frozen("preflight")
    g["overall"] = "PASS" if all(g["gates"].values()) else "FAIL"
    g["env"] = env
    g["records"] = [dict(trial_id=r["trial_id"], logp_Yes=r["logp_Yes"], logp_No=r["logp_No"], mass_YN=r["mass_YN"], z=r["z"],
                         z_tokenwise=r["diagnostic"]["z"], argmax=r["argmax_token"], greedy_text=r["greedy_text"],
                         prompt_tokens=r["prompt_tokens"], top5=[(t["token"], round(t["logprob"], 4)) for t in r["top"][:5]])
                    for r in recs]
    _dump(os.path.join(run_dir, "diagnostics.json"), g)
    _write(os.path.join(run_dir, "preflight_report.md"), preflight_report(g))
    print(json.dumps({k: g[k] for k in ("overall", "gates", "delta", "epsilon", "determinism_spread", "greedy_first_token_YN")}, indent=1))
    return g


def preflight_report(g) -> str:
    e = g["env"]
    L = [f"# {C.TAG} technical preflight\n\nOverall: **{g['overall']}**.\n\n",
         f"Serving: `{e['model_id']}` @ `{e['model_commit']}`, {e['dtype']}, {e['gpu']} ({e['gpu_mem_gb']} GB), driver {e['driver']}, "
         f"CUDA {e['cuda']}, torch {e['torch']}, transformers {e['transformers']}, Python {e['python']}. Chat template sha256 "
         f"`{e['chat_template_sha256'][:16]}…`. Labels: " + ", ".join(f"`{k}` id {v['id']}" for k, v in e["label_tokens"].items())
         + f". Model load {e['load_seconds']} s.\n\n## Gates\n\n| Gate | Result |\n|---|---|\n"]
    L += [f"| {k} | {'PASS' if v else 'FAIL'} |\n" for k, v in g["gates"].items()]
    L.append(f"\n**Numerical floor:** delta = {g['delta']:.4g} log-odds (max |c_prefill - c_tokenwise| over the two items); "
             f"**epsilon = {g['epsilon']:.4g}** ({g['epsilon_rule']}). Determinism spread over repeats: {g['determinism_spread']:.3g}.\n\n")
    L.append("## Technical prompts\n\n| Prompt | log P(Yes) | log P(No) | P(Yes)+P(No) | z (prefill) | z (tokenwise) | argmax | "
             "greedy completion | top 5 |\n|---|---|---|---|---|---|---|---|---|\n")
    for r in g["records"]:
        top = ", ".join(f"`{t!r}` {v}" for t, v in r["top5"])
        L.append(f"| {_md(r['trial_id'])} | {r['logp_Yes']:.4f} | {r['logp_No']:.4f} | {r['mass_YN']:.4f} | {r['z']:+.4f} | "
                 f"{r['z_tokenwise']:+.4f} | `{r['argmax']}` | `{r['greedy_text']!r}` | {top} |\n")
    return "".join(L)


# ------------------------------------------------------------------------------------------- calibration --
def _epsilon():
    g = json.load(open(os.path.join(PRE, "diagnostics.json"), encoding="utf-8"))
    if g["overall"] != "PASS":
        raise SystemExit("preflight did not pass")
    return g["epsilon"]


def calibration_eval():
    eps = _epsilon()
    recs = A.jsonl(os.path.join(CAL, "scored_orientations.jsonl"))
    if {r["trial_id"]: r["prompt_sha256"] for r in recs} != _frozen("calibration"):
        raise SystemExit("calibration records do not match the frozen trial list (missing, extra or changed prompts)")
    rows = SC.unit_records(recs, eps)
    gate = SC.calibration_gate(rows, eps)
    summ = A.calibration_summary(rows, gate)
    A.write_csv(os.path.join(CAL, "unit_scores.csv"), rows)
    _dump(os.path.join(CAL, "calibration_gate.json"), gate)
    _write(os.path.join(CAL, "calibration_report.md"), calibration_report(summ))
    print(json.dumps({k: gate[k] for k in ("overall", "criteria", "total_correct", "both_polarities_correct", "epsilon")}, indent=1))
    return gate


def calibration_report(s) -> str:
    g = s["gate"]
    L = [f"# {C.TAG} Stage A calibration\n\nGate: **{g['overall']}** (epsilon = {g['epsilon']:.4g} log-odds). "
         "36 new items, never scored before.\n\n| Criterion | Result |\n|---|---|\n"]
    L += [f"| {k} | {'PASS' if v else 'FAIL'} |\n" for k, v in g["criteria"].items()]
    L.append("\n## Per task (units are items; CIs bootstrap items)\n\n| Task | S > eps | S < -eps | tie | both polarities correct | "
             "mean S [95% CI] | mean c_pos | mean c_neg | Yes bias pos / neg | coherence | min P(Yes)+P(No) | "
             "greedy separates X from Y: pos / neg |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for t in C.TASKS + ("overall",):
        d = s["overall"] if t == "overall" else s["per_task"][t]
        L.append(f"| {t} | {d['favors_X']}/{d['n']} | {d['favors_Y']} | {d['indeterminate']} | {d['both_polarities_X']}/{d['n']} | "
                 f"{A.fmt_ci(d['mean_S'])} | {d['mean_c_pos']:+.2f} | {d['mean_c_neg']:+.2f} | "
                 f"{d['mean_yes_bias_pos']:+.2f} / {d['mean_yes_bias_neg']:+.2f} | {d['mean_coherence']:+.2f} | {d['mass_YN_min']:.3f} | "
                 f"{d['greedy_separates_pos']}/{d['n']} / {d['greedy_separates_neg']}/{d['n']} |\n")
    L.append("\n## Historical comparison: Experiment 24 (A/B, two orders, Experiment 23 items)\n\n"
             "Different items and a different question format; descriptive only.\n\n"
             "| Task | v2.1: S > eps /12 | v2.1: both orders /12 | v2.1 mean S | v2.1 mean A bias | v3.0: S > eps /12 | v3.0: both polarities /12 | v3.0 mean S |\n"
             "|---|---|---|---|---|---|---|---|\n")
    for t in C.TASKS + ("overall",):
        h, d = s["exp24"][t], (s["overall"] if t == "overall" else s["per_task"][t])
        L.append(f"| {t} | {h['correct']} | {h['both_orders_correct']} | {h['mean_S']:+.2f} | {h['mean_B_pair']:+.2f} | "
                 f"{d['favors_X']} | {d['both_polarities_X']} | {d['mean_S']['point']:+.2f} |\n")
    L.append("\n## S by size of the count difference (X minus Y)\n\n")
    for t, v in s["S_by_count_difference"].items():
        L.append(f"- **{t}**: " + "; ".join(f"diff {d}: n {x['n']}, mean S {x['mean_S']:+.2f}, min {x['min_S']:+.2f}" for d, x in v.items()) + "\n")
    return "".join(L)


# ----------------------------------------------------------------------------------------------- analyse --
def analyse():
    os.makedirs(os.path.join(ANA, "figures"), exist_ok=True)
    out = dict(tag=C.TAG, stages={})
    pre = os.path.join(PRE, "diagnostics.json")
    if not os.path.exists(pre):
        out["stages"] = dict(preflight="NOT_RUN", calibration="NOT_RUN", recognition_screen="NOT_RUN")
        _dump(os.path.join(ANA, "summary.json"), out)
        return out
    g0 = json.load(open(pre, encoding="utf-8"))
    out["stages"]["preflight"] = g0["overall"]
    out["preflight"] = {k: g0[k] for k in ("gates", "delta", "epsilon", "determinism_spread", "greedy_first_token_YN")}
    cal_gate = os.path.join(CAL, "calibration_gate.json")
    if g0["overall"] != "PASS" or not os.path.exists(cal_gate):
        out["stages"].update(calibration="NOT_RUN", recognition_screen="NOT_RUN")
        _dump(os.path.join(ANA, "summary.json"), out)
        return out
    eps = g0["epsilon"]
    cal_rows = SC.unit_records(A.jsonl(os.path.join(CAL, "scored_orientations.jsonl")), eps)
    gate = json.load(open(cal_gate, encoding="utf-8"))
    out["stages"]["calibration"] = gate["overall"]
    out["calibration"] = A.calibration_summary(cal_rows, gate)
    labels = {t: A.TASK_LABEL[t] for t in C.TASKS}
    A.fig_strip(cal_rows, C.TASKS, labels, eps, os.path.join(ANA, "figures", "calibration_scores_by_task.png"),
                f"Stage A: polarity-averaged preference for the correct sample (gray band = tie, |S| ≤ {eps:.2f})",
                "S (log-odds; > 0 favours the correct sample)")
    A.fig_polarities(cal_rows, C.TASKS, labels, eps, os.path.join(ANA, "figures", "calibration_polarities.png"),
                     "Stage A: preference for the correct sample under each question",
                     "'more 6s / more repeats / from R?':  z(correct) − z(other)",
                     "'fewer / from S?':  z(other) − z(correct)")
    rec_path = os.path.join(REC, "scored_orientations.jsonl")
    if gate["overall"] != "PASS" or not os.path.exists(rec_path):
        out["stages"]["recognition_screen"] = "NOT_RUN"
    else:
        rows = SC.unit_records(A.jsonl(rec_path), eps)
        A.write_csv(os.path.join(REC, "unit_scores.csv"), rows)
        out["stages"]["recognition_screen"] = "RUN"
        out["recognition_screen"] = A.screen_summary(rows, ST.load_pairs(), eps)
        A.fig_strip(rows, C.FRAMES, A.KIND_LABEL, eps, os.path.join(ANA, "figures", "recognition_scores.png"),
                    "Stage B: polarity-averaged preference for the Qwen sample (one dot per pair)",
                    "S_Qwen (log-odds; > 0 favours the Qwen sample)")
        A.fig_polarities(rows, C.FRAMES, A.KIND_LABEL, eps, os.path.join(ANA, "figures", "recognition_polarities.png"),
                         "Stage B: preference for the Qwen sample under each question",
                         "'your model? / typical?':  z(Qwen) − z(Mistral)", "'different model? / unlike?':  z(Mistral) − z(Qwen)")
    _dump(os.path.join(ANA, "summary.json"), out)
    print(json.dumps(out["stages"]))
    return out


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = dict(freeze=freeze, preflight_eval=preflight_eval, calibration_eval=calibration_eval, analyse=analyse).get(phase)
    if fn is None:
        raise SystemExit(__doc__)
    fn()
