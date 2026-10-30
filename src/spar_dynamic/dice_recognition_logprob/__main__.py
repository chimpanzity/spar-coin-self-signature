"""LOULA_DICE_AB_LOGPROB v2.1 (Experiment 24) offline phases. The GPU phases live in gpu.py.

  python -m spar_dynamic.dice_recognition_logprob freeze            # validate sources, write frozen protocol + trial lists
  python -m spar_dynamic.dice_recognition_logprob preflight_eval    # Stage 0 gates and epsilon, from preflight/
  python -m spar_dynamic.dice_recognition_logprob calibration_eval  # Stage A gate, from calibration/
  python -m spar_dynamic.dice_recognition_logprob analyse           # summary.json, figures; NOT_RUN for absent stages
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys

from spar_dynamic.dice_recognition_logprob import analysis as A, config as C, prompts as P, scoring as SC, stimuli as ST

EXP = str(C.EXP)
TRIALS = os.path.join(EXP, "trials")
PRE, CAL, REC, ANA = (os.path.join(EXP, d) for d in ("preflight", "calibration", "recognition_screen", "analysis"))


def _dump(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, default=str)


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _md(s: str) -> str:
    """Escape pipes for markdown table cells."""
    return s.replace("|", "\\|")


def _commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=EXP).strip()
    except Exception:
        return "unknown"


# ------------------------------------------------------------------------------------------------ freeze --
def build():
    items = ST.load_calibration()
    pairs = ST.load_pairs()
    return items, pairs, dict(preflight=ST.preflight_trials(items), calibration=ST.shuffled(ST.calibration_trials(items)),
                              screen=ST.shuffled(ST.screen_trials(pairs)))


def protocol_text(items, pairs, trials) -> str:
    L = [f"# {C.TAG}: frozen protocol (Experiment 24)\n\n",
         f"Frozen by `freeze` before any GPU call. Handoff: `{C.HANDOFF}` (2026-10-29). Exploratory method-development pilot; "
         "the calibration items (Experiment 23) and recognition pairs (Experiment 22) were inspected before this design, so "
         "nothing here is confirmatory.\n\n",
         "## Serving (Experiment 21 configuration)\n\n",
         f"- `{C.MODEL_ID}` at commit `{C.REVISION}`, local `transformers`, bf16 weights and activations, separate fp32 output "
         "layer and logits, batch size 1, deterministic flags; loader imported unchanged from `dice_logprob.gpu_runner.Qwen`.\n",
         "- Chat template with `enable_thinking=False`; the rendered prompt must end with the fixed empty think block "
         f"`{C.THINK_SUFFIX!r}`. One user message, no system message, no tools, fresh context per item and orientation.\n",
         "- Scored position: the next token after the complete assistant prefix (the first visible answer token). "
         f"Labels `A` and `B` must each be one token in that context; their ids and bytes are archived.\n",
         f"- Primary arithmetic (`{C.PRIMARY_METHOD}`): one cached forward pass over the rendered prompt, the same first step "
         "greedy generation takes (Experiment 21's incremental path with empty history). Used for every primary score.\n",
         f"- Diagnostic (`{C.DIAGNOSTIC_METHOD}`, preflight only): prefill `<|im_start|>user\\n`, then every remaining "
         "prompt token one at a time through the KV cache.\n\n",
         "## Prompts (handoff 4.1)\n\n",
         "Question bodies are Experiment 23's frozen templates (`dice_recognition_v2.prompts`), unchanged. Each ends with "
         "`\\n{answer_instruction}`; v2.1 fills that slot with the ending below, so a rendered prompt is the v2.0 body, one "
         "newline, the ending, and no trailing newline. The two orientations of a unit differ only in which sequence fills "
         "Sample A. No brief-observation instruction is used.\n\n"]
    for k, v in P.templates().items():
        L.append(f"### {k}\n\nsha256 `{P.sha256(v)}`\n\n```text\n{v}\n```\n\n")
    L += ["## Scores (handoff 4.3)\n\n",
          "- `d_XY = log P(A) - log P(B)` with A = X, B = Y; `d_YX` the same with A = Y, B = X (full-vocabulary log-softmax).\n",
          "- X = the correct sample (calibration) or the Qwen sample (recognition).\n",
          "- `S_X = (d_XY - d_YX) / 2`; `B_pair = (d_XY + d_YX) / 2`; per-orientation preferences `d_XY` and `-d_YX`; "
          "`sigmoid(S_X)` is a display scale only.\n",
          "- `|S_X| <= epsilon` is `indeterminate` and never counts as correct.\n\n",
          "## Stage 0: technical preflight (handoff 5), hard stop if any gate fails\n\n",
          f"- Prompts: {', '.join(C.PREFLIGHT_ITEMS)} in both orientations, plus one generic A/B arithmetic prompt (5 total).\n",
          "- Gates: revision pinned and serving recorded; non-thinking template with no system turn and one user turn, no "
          "think text in greedy output; A and B single tokens that append as one token after the assistant prefix; "
          f"greedy first token is exactly A or B in >= {C.GREEDY_MIN_AB}/5 (a natural response starting with whitespace, "
          "a newline, `ANSWER:` or anything else counts against this; the scored position is never moved); "
          f"{C.DETERMINISM_REPEATS} repeats of one prompt with max |d| spread < {C.DETERMINISM_TOL}; epsilon < {C.EPSILON_STOP}.\n",
          f"- `delta = max |S_prefill - S_tokenwise|` over the two complete pairs; `epsilon = max({C.EPSILON_FLOOR}, "
          f"{C.EPSILON_MULTIPLIER} * delta)` log-odds units, frozen once the preflight passes.\n\n",
          "## Stage A: calibration (handoff 6), exploratory\n\n",
          "36 archived Experiment 23 items x 2 orientations = 72 scored prompts, primary method only. Gate (all must hold):\n\n",
          f"- `S_correct > epsilon` for >= {C.GATE_TOTAL}/36 items, with >= {C.GATE_TASK['GEN_RULE']}/12 GEN_RULE, "
          f">= {C.GATE_TASK['MORE_SIXES']}/12 MORE_SIXES and >= {C.GATE_TASK['MORE_REPEATS']}/12 MORE_REPEATS.\n",
          f"- `d_XY > epsilon` and `-d_YX > epsilon` on the same item for >= {C.GATE_BOTH_ORDERS}/36 items.\n\n",
          "If it fails: stop before Stage B; no new label phrasing, reasoning, model names or moved thresholds.\n\n",
          "## Stage B: recognition screen (handoff 7), only if Stage A passes\n\n",
          f"- The {C.N_PAIRS} archived Experiment 22 held-out Qwen-Mistral pairs, one ten-roll sequence per sample.\n",
          "- AUTH and TYP (v2.0 bodies, K = 1, no examples) x 2 orientations = 80 prompts.\n",
          f"- Named comparator `NAMED_QWEN`: **{C.NAMED_ARM}** (decided now, before Stage A). v2.0 `NAMED`, target Qwen3-32B, "
          "name order QM / MQ crossed with both orientations = 80 prompts.\n",
          "- Descriptive only: counts of S > eps / < -eps / indeterminate, mean and median S with a bootstrap over pair ids, "
          "orientation stability, label bias, AUTH vs TYP paired difference, agreement with the Experiment 22 frozen "
          "classifier, NAMED name-order effect and AUTH vs NAMED contrast.\n",
          "- Nothing further runs automatically: no Stage C/D, no Mistral judge, no new stimuli.\n\n",
          f"## Counts and order\n\n- Preflight {len(trials['preflight'])} prompts; calibration {len(trials['calibration'])}; "
          f"screen {len(trials['screen'])}.\n- GPU order: seeded shuffle (seed {C.ORDER_SEED}); scores are deterministic, so order "
          f"only matters for resume.\n- Bootstrap: {C.BOOTSTRAP_N} resamples, seed {C.BOOTSTRAP_SEED}, over items or pair ids.\n"
          f"- Hard GPU cap: US${C.GPU_CAP_USD:.0f} for this experiment.\n"]
    return "".join(L)


def prompts_frozen_text(trials) -> str:
    L = ["# Frozen rendered user prompts (Experiment 24)\n\nEvery prompt sent as the single user message, with its SHA-256. "
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
    man.update(dict(tag=C.TAG, handoff=C.HANDOFF, repository_commit_at_freeze=man.get("repository_commit_at_freeze", _commit()),
                    frozen_utc=man.get("frozen_utc", dt.datetime.now(dt.timezone.utc).isoformat()),
                    model=dict(id=C.MODEL_ID, revision=C.REVISION), source_sha256=hashes,
                    template_sha256={k: P.sha256(v) for k, v in P.templates().items()},
                    protocol_sha256=P.sha256(proto),
                    trial_files={s: dict(path=f"trials/{s}.json", n=len(t),
                                         sha256=ST.file_sha256(os.path.join(TRIALS, f"{s}.json"))) for s, t in trials.items()},
                    trial_prompt_sha256={t["trial_id"]: t["prompt_sha256"] for ts in trials.values() for t in ts},
                    gates=dict(calibration=dict(total=C.GATE_TOTAL, per_task=C.GATE_TASK, both_orders=C.GATE_BOTH_ORDERS),
                               epsilon_rule=f"max({C.EPSILON_FLOOR}, {C.EPSILON_MULTIPLIER} * delta); stop if >= {C.EPSILON_STOP}"),
                    named_arm=C.NAMED_ARM, gpu_cap_usd=C.GPU_CAP_USD))
    _dump(mp, man)
    print(json.dumps(dict(items=len(items), pairs=len(pairs), **{k: len(v) for k, v in trials.items()},
                          protocol_sha256=man["protocol_sha256"]), indent=1))


# --------------------------------------------------------------------------------------------- preflight --
def preflight_eval(run_dir=PRE):
    recs = A.jsonl(os.path.join(run_dir, "raw_preflight.jsonl"))
    env = json.load(open(os.path.join(run_dir, "env_preflight.json"), encoding="utf-8"))
    frozen = {t["trial_id"]: t["prompt_sha256"] for t in json.load(open(os.path.join(TRIALS, "preflight.json"), encoding="utf-8"))}
    g = SC.preflight_gate(recs, env)
    g["gates"]["prompts_match_frozen_trial_list"] = {r["trial_id"]: r["prompt_sha256"] for r in recs} == frozen
    g["overall"] = "PASS" if all(g["gates"].values()) else "FAIL"
    g["env"] = env
    g["records"] = [dict(trial_id=r["trial_id"], z_A=r["z_A"], z_B=r["z_B"], logp_A=r["logp_A"], logp_B=r["logp_B"],
                         mass_AB=r["mass_AB"], d=r["d"], d_tokenwise=r["diagnostic"]["d"], argmax=r["argmax_token"],
                         greedy_text=r["greedy_text"], prompt_tokens=r["prompt_tokens"],
                         top5=[(t["token"], round(t["logprob"], 4)) for t in r["top"][:5]]) for r in recs]
    _dump(os.path.join(run_dir, "diagnostics.json"), g)
    _write(os.path.join(run_dir, "preflight_report.md"), preflight_report(g))
    print(json.dumps({k: g[k] for k in ("overall", "gates", "delta", "epsilon", "determinism_spread", "greedy_first_token_AB")}, indent=1))
    return g


def preflight_report(g) -> str:
    e = g["env"]
    L = [f"# {C.TAG} technical preflight\n\nOverall: **{g['overall']}**.\n\n",
         f"Serving: `{e['model_id']}` @ `{e['model_commit']}`, {e['dtype']}, {e['gpu']} ({e['gpu_mem_gb']} GB), driver {e['driver']}, "
         f"CUDA {e['cuda']}, torch {e['torch']}, transformers {e['transformers']}, Python {e['python']}. Chat template sha256 "
         f"`{e['chat_template_sha256'][:16]}…`. Labels: " + ", ".join(f"`{k}` id {v['id']}" for k, v in e["label_tokens"].items())
         + f". Model load {e['load_seconds']} s.\n\n## Gates\n\n| Gate | Result |\n|---|---|\n"]
    L += [f"| {k} | {'PASS' if v else 'FAIL'} |\n" for k, v in g["gates"].items()]
    L.append(f"\n**Numerical floor:** delta = {g['delta']:.4g} log-odds (max |S_prefill - S_tokenwise| over the two pairs); "
             f"**epsilon = {g['epsilon']:.4g}** ({g['epsilon_rule']}). Determinism spread over repeats: {g['determinism_spread']:.3g}.\n\n")
    L.append("## Technical prompts\n\n| Prompt | log P(A) | log P(B) | P(A)+P(B) | d (prefill) | d (tokenwise) | argmax | greedy completion | top 5 |\n"
             "|---|---|---|---|---|---|---|---|---|\n")
    for r in g["records"]:
        top = ", ".join(f"`{t!r}` {v}" for t, v in r["top5"])
        L.append(f"| {_md(r['trial_id'])} | {r['logp_A']:.4f} | {r['logp_B']:.4f} | {r['mass_AB']:.4f} | {r['d']:+.4f} | "
                 f"{r['d_tokenwise']:+.4f} | `{r['argmax']}` | `{r['greedy_text']!r}` | {top} |\n")
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
    frozen = {t["trial_id"]: t["prompt_sha256"] for t in json.load(open(os.path.join(TRIALS, "calibration.json"), encoding="utf-8"))}
    if {r["trial_id"]: r["prompt_sha256"] for r in recs} != frozen:
        raise SystemExit("calibration records do not match the frozen trial list (missing, extra or changed prompts)")
    rows = SC.pair_records(recs, eps)
    gate = SC.calibration_gate(rows, eps)
    summ = A.calibration_summary(rows, gate)
    A.write_csv(os.path.join(CAL, "paired_scores.csv"), rows)
    _dump(os.path.join(CAL, "calibration_gate.json"), gate)
    _write(os.path.join(CAL, "calibration_report.md"), calibration_report(summ))
    print(json.dumps({k: gate[k] for k in ("overall", "criteria", "total_correct", "both_orders_correct", "epsilon")}, indent=1))
    return gate


def calibration_report(s) -> str:
    g = s["gate"]
    L = [f"# {C.TAG} Stage A calibration\n\nGate: **{g['overall']}** (epsilon = {g['epsilon']:.4g} log-odds). "
         "Exploratory: these 36 items were already used in Experiment 23.\n\n| Criterion | Result |\n|---|---|\n"]
    L += [f"| {k} | {'PASS' if v else 'FAIL'} |\n" for k, v in g["criteria"].items()]
    L.append("\n## Per task (units are items; CIs bootstrap items)\n\n| Task | S > eps | S < -eps | tie | both orders correct | "
             "mean S [95% CI] | median S | mean B_pair | min P(A)+P(B) | greedy argmax correct /24 (consistent /12) |\n"
             "|---|---|---|---|---|---|---|---|---|---|\n")
    for t in C.TASKS + ("overall",):
        d = s["overall"] if t == "overall" else s["per_task"][t]
        L.append(f"| {t} | {d['favors_X']}/{d['n']} | {d['favors_Y']} | {d['indeterminate']} | {d['both_orders_X']}/{d['n']} | "
                 f"{A.fmt_ci(d['mean_S'])} | {d['median_S']:+.2f} | {d['mean_B_pair']:+.2f} | {d['mass_AB_min']:.3f} | "
                 f"{d['greedy_argmax_correct']}/{2 * d['n']} ({d['greedy_argmax_consistent']}/{d['n']}) |\n")
    L.append("\n## Historical benchmark: Experiment 23 emitted Qwen answers (OpenRouter/SiliconFlow, temperature 0)\n\n"
             "Different serving and different answer instruction; descriptive only, not paired trials.\n\n"
             "| Task | bare: correct /24, consistent /12, A-rate | brief: correct /24, consistent /12, A-rate |\n|---|---|---|\n")
    for t in C.TASKS:
        b, r = s["exp23_qwen_emitted"]["bare"][t], s["exp23_qwen_emitted"]["brief"][t]
        L.append(f"| {t} | {b['correct_of_24']}, {b['consistent_of_12']}, {b['A_rate']:.2f} | {r['correct_of_24']}, {r['consistent_of_12']}, {r['A_rate']:.2f} |\n")
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
    out["preflight"] = {k: g0[k] for k in ("gates", "delta", "epsilon", "determinism_spread", "greedy_first_token_AB")}
    cal_gate = os.path.join(CAL, "calibration_gate.json")
    if g0["overall"] != "PASS" or not os.path.exists(cal_gate):
        out["stages"].update(calibration="NOT_RUN", recognition_screen="NOT_RUN")
        _dump(os.path.join(ANA, "summary.json"), out)
        return out
    eps = g0["epsilon"]
    cal_rows = SC.pair_records(A.jsonl(os.path.join(CAL, "scored_orientations.jsonl")), eps)
    gate = json.load(open(cal_gate, encoding="utf-8"))
    out["stages"]["calibration"] = gate["overall"]
    out["calibration"] = A.calibration_summary(cal_rows, gate)
    labels = {t: A.TASK_LABEL[t] for t in C.TASKS}
    A.fig_strip(cal_rows, C.TASKS, labels, eps, os.path.join(ANA, "figures", "calibration_scores_by_task.png"),
                f"Stage A: order-corrected preference for the correct sample (gray band = tie, |S| ≤ {eps:.2f})",
                "S_correct (log-odds; > 0 favours the correct sample)")
    A.fig_orders(cal_rows, C.TASKS, labels, eps, os.path.join(ANA, "figures", "calibration_order_bias.png"),
                 "Stage A: preference for the correct sample in each order",
                 "correct sample shown as A:  log P(A) − log P(B)", "correct sample shown as B:  log P(B) − log P(A)")
    rec_path = os.path.join(REC, "scored_orientations.jsonl")
    if gate["overall"] != "PASS" or not os.path.exists(rec_path):
        out["stages"]["recognition_screen"] = "NOT_RUN"
    else:
        rows = SC.pair_records(A.jsonl(rec_path), eps)
        A.write_csv(os.path.join(REC, "paired_scores.csv"), rows)
        out["stages"]["recognition_screen"] = "RUN"
        out["recognition_screen"] = A.screen_summary(rows, ST.load_pairs(), eps)
        kinds = [k for k in ("AUTH", "TYP", "NAMED_QWEN") if any(r["kind"] == k for r in rows)]
        A.fig_strip(rows, kinds, A.KIND_LABEL, eps, os.path.join(ANA, "figures", "recognition_scored_preferences.png"),
                    "Stage B: order-corrected preference for the Qwen sample (NAMED: one dot per pair × name order)",
                    "S_Qwen (log-odds; > 0 favours the Qwen sample)")
        A.fig_orders(rows, kinds, A.KIND_LABEL, eps, os.path.join(ANA, "figures", "recognition_orientation_sensitivity.png"),
                     "Stage B: preference for the Qwen sample in each order",
                     "Qwen sample shown as A:  log P(A) − log P(B)", "Qwen sample shown as B:  log P(B) − log P(A)")
    _dump(os.path.join(ANA, "summary.json"), out)
    print(json.dumps(out["stages"]))
    return out


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = dict(freeze=freeze, preflight_eval=preflight_eval, calibration_eval=calibration_eval, analyse=analyse).get(phase)
    if fn is None:
        raise SystemExit(__doc__)
    fn()
