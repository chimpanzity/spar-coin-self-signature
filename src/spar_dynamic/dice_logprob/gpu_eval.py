"""Gate evaluation for an open-weight preflight run (handoff 4.5, amended 2026-10-29). Offline, no GPU.

Reads raw_attempts.jsonl, matched_prefix.jsonl and env_preflight.json written by gpu_runner and writes
preflight_summary.json and preflight_report.md into the same folder.

Usage: python -m spar_dynamic.dice_logprob.gpu_eval <run_dir>
"""

from __future__ import annotations

import collections
import json
import os
import re
import sys

from spar_dynamic.dice_logprob import extract

THINK_SUFFIX = "<think>\n\n</think>\n\n"
# Incremental matched-prefix scoring uses the same arithmetic path as generation, so scoring a model's own
# output must reproduce its generation (gate). The full-pass variant differs by bf16 summation order; its
# gap to generation is reported as the numerical precision floor, not gated.
PREFIX_TOL_P6 = 1e-4


def load(run_dir):
    rows = [json.loads(l) for l in open(os.path.join(run_dir, "raw_attempts.jsonl"), encoding="utf-8")]
    mp_path = os.path.join(run_dir, "matched_prefix.jsonl")
    mp = [json.loads(l) for l in open(mp_path, encoding="utf-8")] if os.path.exists(mp_path) else []
    env = json.load(open(os.path.join(run_dir, "env_preflight.json"), encoding="utf-8"))
    return rows, mp, env


def evaluate(run_dir: str) -> dict:
    rows, mp, env = load(run_dir)
    per = []
    for r in rows:
        p = extract.parse(r["raw_choice_content"], len(r["target_positions"]), r["finish_reason"])
        faces = extract.align_faces(r["raw_choice_content"], r["raw_logprobs_content"]) if p["verdict"] == "valid" else []
        per.append(dict(trial_id=r["trial_id"], condition=r["condition"], verdict=p["verdict"], content=r["raw_choice_content"],
                        n_positions=len(faces), comparable=sum(f["comparable_flag"] for f in faces),
                        complete=sum(f["candidate_coverage_complete"] for f in faces),
                        ambiguity=sum(f["tokenization_ambiguity_flag"] for f in faces),
                        min_face_mass=min((f["six_face_mass"] for f in faces if f["six_face_mass"] is not None), default=None),
                        think_suffix=r["rendered_prompt"].endswith(THINK_SUFFIX),
                        think_in_output="<think" in r["raw_choice_content"].lower(), finish=r["finish_reason"]))
    repro = {}
    for k in ("G", "F"):
        rs = [r for r in rows if r["condition"] == k]
        c = collections.Counter(r["raw_choice_content"] for r in rs)
        mode, n = c.most_common(1)[0]
        same = [r for r in rs if r["raw_choice_content"] == mode]
        diffs = [abs(a["logprob"] - b["logprob"]) for r in same[1:] for a, b in zip(same[0]["raw_logprobs_content"], r["raw_logprobs_content"])]
        diffs += [abs(a["face_logprobs_exact"]["bare"][f] - b["face_logprobs_exact"]["bare"][f])
                  for r in same[1:] for a, b in zip(same[0]["raw_logprobs_content"], r["raw_logprobs_content"]) for f in a["face_logprobs_exact"]["bare"]]
        repro[k] = dict(n=len(rs), modal_sequence=mode, modal_count=n, distinct=len(c),
                        max_abs_logprob_diff_across_identical=max(diffs, default=0.0))
    # teacher-forced scoring must reproduce generation for (X, own modal history)
    tf = {}
    for k in ("G", "F"):
        gen = next(r for r in rows if r["condition"] == k and r["raw_choice_content"] == repro[k]["modal_sequence"])
        gen_faces = [t["face_logprobs_exact"]["bare"] for t in gen["raw_logprobs_content"] if re.fullmatch(r" ?[1-6]", t["token"])]
        for method in ("incremental", "full_pass"):
            sc = sorted([m for m in mp if m["instruction"] == k and m["history"] == k and m.get("method", "full_pass") == method],
                        key=lambda m: m["position"])
            d = [abs(_g(g, f) - _g(s["face_logprobs_exact"]["bare"], f)) for g, s in zip(gen_faces, sc) for f in range(1, 7)]
            dp = [abs(_p6(g)[f] - _p6(s["face_logprobs_exact"]["bare"])[f]) for g, s in zip(gen_faces, sc) for f in range(1, 7)]
            tf[f"{k}|{method}"] = dict(n_positions=len(sc), max_abs_diff_nats=max(d, default=None), max_abs_diff_p6=max(dp, default=None),
                                       argmax_agree=all(max(range(1, 7), key=lambda f: _g(g, f)) == max(range(1, 7), key=lambda f: _g(s["face_logprobs_exact"]["bare"], f))
                                                        for g, s in zip(gen_faces, sc)))
    gf = [x for x in per if x["condition"] in ("G", "F")]
    gates = collections.OrderedDict()
    gates["serving_recorded"] = bool(env.get("model_commit")) and bool(env.get("gpu"))
    gates["non_thinking"] = all(x["think_suffix"] and not x["think_in_output"] for x in per)
    gates["valid_numeric_outputs_all_conditions"] = all(x["verdict"] == "valid" for x in per)
    gates["complete_six_face_vectors_all_positions_G_F"] = all(x["n_positions"] == 10 and x["complete"] == 10 for x in gf)
    gates["references_repeatable_9_of_10"] = all(repro[k]["modal_count"] >= 9 for k in ("G", "F"))
    gates["matched_prefix_scoring_valid"] = all(tf[f"{k}|incremental"]["n_positions"] == 10 and tf[f"{k}|incremental"]["argmax_agree"]
                                                and tf[f"{k}|incremental"]["max_abs_diff_p6"] < PREFIX_TOL_P6 for k in ("G", "F"))
    return dict(gates=gates, overall="PASS" if all(gates.values()) else "FAIL", env=env, responses=per,
                reproducibility=repro, teacher_forcing_check=tf)


def _g(d, f):
    return d[str(f)] if str(f) in d else d[f]


def _p6(d):
    return extract.p6_from_logp([_g(d, f) for f in range(1, 7)])


def report(s: dict, run_dir: str) -> str:
    e = s["env"]
    L = [f"# DICE_LOGPROB_v1.0 open-weight preflight report\n\n",
         f"Run folder: `{os.path.basename(run_dir.rstrip('/'))}`. Overall: **{s['overall']}**. Main collection not started.\n\n",
         f"Serving: `{e['model_id']}` @ `{e['model_commit']}`, {e['dtype']}, {e['gpu']} ({e['gpu_mem_gb']} GB), driver {e['driver']}, "
         f"CUDA {e['cuda']}, torch {e['torch']}, transformers {e['transformers']}, Python {e['python']}. Greedy, batch 1, "
         f"chat template `enable_thinking=False` (template sha256 `{e['chat_template_sha256'][:16]}…`). Model load {e['load_seconds']} s.\n\n",
         "## Gates\n\n| Gate | Result |\n|---|---|\n"]
    L += [f"| {g} | {'PASS' if v else 'FAIL'} |\n" for g, v in s["gates"].items()]
    L.append("\n## Reproducibility\n\n")
    for k, v in s["reproducibility"].items():
        L.append(f"- **{k}**: modal `{v['modal_sequence']}` in {v['modal_count']}/{v['n']}; {v['distinct']} distinct; "
                 f"max |Δ logprob| across identical outputs {v['max_abs_logprob_diff_across_identical']:.2e}\n")
    L.append("\n## Teacher-forced scoring vs generation (own modal history)\n\n"
             "`incremental` (gated) feeds the history through the KV cache like generation; `full_pass` is one forward pass, "
             "and its gap to generation estimates the bf16 numerical precision floor.\n\n")
    for k, v in s["teacher_forcing_check"].items():
        L.append(f"- **{k}**: {v['n_positions']} positions, argmax agrees: {v['argmax_agree']}, max |Δ p6| {v['max_abs_diff_p6']:.2e}"
                 f"{f' (gate < {PREFIX_TOL_P6})' if k.endswith('incremental') else ' (reported, not gated)'}; "
                 f"max |Δ logprob| {v['max_abs_diff_nats']:.2e} nats\n")
    L.append("\n## Responses\n\n| Trial | Verdict | Content | Comparable positions | Ambiguity flags | Min six-face mass |\n|---|---|---|---|---|---|\n")
    for x in sorted(s["responses"], key=lambda x: (x["condition"], x["trial_id"])):
        m = f"{x['min_face_mass']:.4f}" if x["min_face_mass"] is not None else "NA"
        L.append(f"| {x['trial_id']} | {x['verdict']} | `{x['content']}` | {x['comparable']}/{x['n_positions']} | {x['ambiguity']} | {m} |\n")
    return "".join(L)


def main(run_dir: str):
    s = evaluate(run_dir)
    with open(os.path.join(run_dir, "preflight_summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, default=str)
    with open(os.path.join(run_dir, "preflight_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(report(s, run_dir))
    print(json.dumps(dict(overall=s["overall"], gates=s["gates"], reproducibility=s["reproducibility"],
                          teacher_forcing=s["teacher_forcing_check"]), indent=2, default=str))
    return s


if __name__ == "__main__":
    main(sys.argv[1])
