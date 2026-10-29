"""Technical preflight for DICE_LOGPROB_v1.0 (handoff section 4). Small, capped; never starts the main run.

Stages (all calls fresh-context, one user message, no tools, no system message):
  A  endpoint acceptance: G and F once each under the frozen configuration
     (SiliconFlow pinned, no fallback, require_parameters=true, logprobs=true,
     top_logprobs=20, reasoning.enabled=false, temperature 0, max_tokens 128).
  B  diagnostic, only if A is refused before reaching a provider: the same
     G and F with require_parameters=false (still pinned, no fallback), to see
     whether the parameters are silently ignored. Labelled diagnostic; never
     a reference.
  C  reproducibility and format: 10 G + 10 F, plus S5 and W3-8 once each, in a
     seeded shuffled order, under the configuration that reached SiliconFlow
     (A if accepted, else B, labelled as such).
Gates (4.5) are evaluated from the archived responses and written to
preflight_report.md and preflight_summary.json in the run folder.

Usage: python -m spar_dynamic.dice_logprob.preflight
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import os
import random

from openai import OpenAI

import repo_paths
from spar_dynamic.dice_logprob import client as C, extract, prompts

PREFLIGHT_CAP_USD = 1.00
ORDER_SEED = 20261029
N_REPRO = 10


class Run:
    def __init__(self, run_dir: str):
        self.dir = run_dir
        self.spent = 0.0
        self.rows = []
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise SystemExit("OPENROUTER_API_KEY not set (load .env first)")
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, max_retries=0, timeout=120.0)

    def one(self, stage: str, cond: dict, replicate: int, cfg: dict, config_label: str) -> dict:
        if self.spent >= PREFLIGHT_CAP_USD:
            raise RuntimeError(f"preflight cap ${PREFLIGHT_CAP_USD} reached")
        res = C.call(self.client, cond["prompt"], cfg)
        p = extract.parse(res["raw_choice_content"], cond["n_expected"], res["finish_reason"] or "", res["tool_calls"]) \
            if res["ok"] else dict(verdict="transport_or_request_error", faces=None)
        row = dict(run_id=os.path.basename(self.dir), stage=stage, config_label=config_label,
                   trial_id=f"{stage}-{cond['condition']}-{replicate}", replicate=replicate,
                   condition=cond["condition"], condition_type=cond["condition_type"], target_positions=cond["positions"],
                   prompt_text=cond["prompt"], prompt_sha256=cond["prompt_sha256"],
                   requested_model=cfg["slug"], requested_provider=cfg["provider"],
                   requested_reasoning=cfg["reasoning"], requested_temperature=cfg["temperature"],
                   requested_config=cfg, parser_verdict=p["verdict"], faces=p["faces"],
                   software_version="dice_logprob preflight v1.0", git_commit=C.git_commit(), **res)
        self.spent += res["cost_usd"]
        self.rows.append(row)
        with open(os.path.join(self.dir, "raw_attempts.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
        return row


def _refused(row) -> bool:
    return not row["ok"]


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = str(repo_paths.T1_EXP["dice_logprob"] / f"preflight-{stamp}")
    os.makedirs(run_dir)
    conds = {c["condition"]: c for c in prompts.conditions()}
    with open(os.path.join(run_dir, "prompts_frozen.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(prompts.render_frozen())
    cfg_a = dict(C.CONFIG)
    cfg_b = dict(C.CONFIG, require_parameters=False)
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(dict(spec="DICE_LOGPROB_v1.0 preflight", started_utc=stamp, git_commit=C.git_commit(),
                       frozen_config=cfg_a, diagnostic_config=cfg_b, cap_usd=PREFLIGHT_CAP_USD,
                       order_seed=ORDER_SEED, n_repro=N_REPRO,
                       prompt_sha256={k: c["prompt_sha256"] for k, c in conds.items()},
                       stages=__doc__.split("Stages")[1].split("Gates")[0].strip()), f, indent=2)
    R = Run(run_dir)

    a = [R.one("A", conds[k], 0, cfg_a, "frozen") for k in ("G", "F")]
    stage_c_cfg, stage_c_label = cfg_a, "frozen"
    if all(_refused(r) for r in a):
        b = [R.one("B", conds[k], 0, cfg_b, "diagnostic_require_parameters_false") for k in ("G", "F")]
        if all(_refused(r) for r in b):
            stage_c_cfg = None
        else:
            stage_c_cfg, stage_c_label = cfg_b, "diagnostic_require_parameters_false"
    if stage_c_cfg is not None:
        jobs = [("G", i) for i in range(N_REPRO)] + [("F", i) for i in range(N_REPRO)] + [("S5", 0), ("W3-8", 0)]
        random.Random(ORDER_SEED).shuffle(jobs)
        for k, i in jobs:
            R.one("C", conds[k], i + 1, stage_c_cfg, stage_c_label)

    summary = evaluate(R.rows)
    summary.update(run_dir=run_dir, spent_usd=round(R.spent, 6), stage_c_config=stage_c_label if stage_c_cfg else None)
    with open(os.path.join(run_dir, "preflight_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(os.path.join(run_dir, "preflight_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(report(summary, R.rows))
    print(json.dumps({k: summary[k] for k in ("run_dir", "spent_usd", "gates", "overall")}, indent=2, default=str))


def evaluate(rows) -> dict:
    ok = [r for r in rows if r["ok"]]
    per_row = []
    for r in ok:
        lp = r["raw_logprobs_content"]
        faces = extract.align_faces(r["raw_choice_content"] or "", lp) if (lp and r["parser_verdict"] == "valid") else []
        per_row.append(dict(trial_id=r["trial_id"], config=r["config_label"], condition=r["condition"],
                            verdict=r["parser_verdict"], content=r["raw_choice_content"],
                            served_provider=r["served_provider"], served_model=r["served_model"],
                            reasoning_tokens=r["reasoning_tokens"], reasoning_fields=bool(r["raw_reasoning_fields"]),
                            finish_reason=r["finish_reason"], logprobs_present=bool(lp),
                            n_logprob_tokens=len(lp) if lp else 0,
                            max_top_alternatives=max((len(t.get("top_logprobs") or []) for t in lp), default=0) if lp else 0,
                            positions_complete=sum(f["candidate_coverage_complete"] for f in faces),
                            positions_comparable=sum(f["comparable_flag"] for f in faces),
                            n_positions=len(faces)))
    refused = [dict(trial_id=r["trial_id"], config=r["config_label"],
                    errors=[(a.get("status_code"), a.get("error", "")[:400]) for a in r["attempts"]]) for r in rows if not r["ok"]]

    frozen_ok = [x for x in per_row if x["config"] == "frozen"]
    repro = {}
    for k in ("G", "F"):
        seqs = [r["raw_choice_content"] for r in rows if r["stage"] == "C" and r["condition"] == k and r["parser_verdict"] == "valid"]
        c = collections.Counter(seqs)
        mode, n_mode = (c.most_common(1)[0] if c else (None, 0))
        by_pos = []
        valid_faces = [s.split(" ") for s in seqs]
        for j in range(10):
            pc = collections.Counter(v[j] for v in valid_faces if len(v) == 10)
            by_pos.append(pc.most_common(1)[0][1] if pc else 0)
        repro[k] = dict(n_calls=sum(1 for r in rows if r["stage"] == "C" and r["condition"] == k), n_valid=len(seqs),
                        modal_sequence=mode, modal_count=n_mode, distinct=len(c), modal_count_by_position=by_pos)

    gates = collections.OrderedDict()
    gates["provider_pinned_frozen_config_accepted"] = bool(frozen_ok) and all(x["served_provider"] == "SiliconFlow" for x in frozen_ok)
    reached = [x for x in per_row]
    gates["non_thinking"] = bool(reached) and all((x["reasoning_tokens"] in (0, "unknown")) and not x["reasoning_fields"] for x in reached)
    gates["valid_numeric_outputs_G_F_S_W"] = all(any(x["condition"] == c and x["verdict"] == "valid" for x in reached) for c in ("G", "F", "S5", "W3-8"))
    gates["complete_six_face_vectors_all_positions_G_F"] = bool(frozen_ok) and all(
        x["n_positions"] == 10 and x["positions_comparable"] == 10 for x in frozen_ok if x["condition"] in ("G", "F"))
    gates["references_repeatable_9_of_10"] = all(repro.get(k, {}).get("modal_count", 0) >= 9 for k in ("G", "F"))
    gates["no_parameter_silently_ignored"] = bool(frozen_ok) and all(x["logprobs_present"] and x["max_top_alternatives"] >= 6 for x in frozen_ok)
    return dict(gates=gates, overall="PASS" if all(gates.values()) else "FAIL", responses=per_row,
                refused=refused, reproducibility=repro)


def report(s, rows) -> str:
    L = [f"# DICE_LOGPROB_v1.0 preflight report\n", f"Run folder: `{os.path.basename(s['run_dir'])}`. Spent ${s['spent_usd']:.6f} (cap ${PREFLIGHT_CAP_USD:.2f}). "
         f"Overall: **{s['overall']}**. Main collection was not started.\n", "\n## Gates (handoff 4.5)\n", "| Gate | Result |\n|---|---|\n"]
    for g, v in s["gates"].items():
        L.append(f"| {g} | {'PASS' if v else 'FAIL'} |\n")
    L.append("\n## Refused requests\n\n")
    if s["refused"]:
        for x in s["refused"]:
            L.append(f"- `{x['trial_id']}` ({x['config']}): " + "; ".join(f"HTTP {c}: {e}" for c, e in x["errors"]) + "\n")
    else:
        L.append("None.\n")
    L.append("\n## Responses that reached a provider\n\n| Trial | Config | Provider | Verdict | Content | Reasoning tokens | logprobs | top alts | comparable positions |\n|---|---|---|---|---|---|---|---|---|\n")
    for x in s["responses"]:
        L.append(f"| {x['trial_id']} | {x['config']} | {x['served_provider']} | {x['verdict']} | `{x['content']!r}` | {x['reasoning_tokens']} | "
                 f"{'yes' if x['logprobs_present'] else 'no'} | {x['max_top_alternatives']} | {x['positions_comparable']}/{x['n_positions']} |\n")
    L.append("\n## Reproducibility (stage C)\n\n")
    for k, v in s["reproducibility"].items():
        L.append(f"- **{k}**: {v['n_valid']}/{v['n_calls']} valid; modal `{v['modal_sequence']}` in {v['modal_count']}; {v['distinct']} distinct; modal count by position {v['modal_count_by_position']}\n")
    if s.get("stage_c_config") and s["stage_c_config"] != "frozen":
        L.append(f"\nStage C ran under `{s['stage_c_config']}` (diagnostic), not the frozen configuration; these sequences are not references.\n")
    return "".join(L)


if __name__ == "__main__":
    main()
