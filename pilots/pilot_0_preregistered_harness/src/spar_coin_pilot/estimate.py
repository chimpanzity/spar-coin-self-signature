"""Call counts and pre-run cost estimate from live catalog prices and configured token assumptions."""

from __future__ import annotations

from typing import Any

from .config import PilotConfig
from .openrouter_client import estimate_call_cost, price_per_token
from .records import JudgmentRecord, SourceRecord, TrialRecord, latest_judgments_by_trial


def call_counts(cfg: PilotConfig) -> dict[str, int]:
    n_models = len(cfg.model_labels)
    source_calls = n_models * cfg.generation.valid_strings_per_model
    judgment_calls = n_models * cfg.judgment.trials_per_judge
    preflight_calls = n_models if (cfg.judgment.response_mode == "structured" and cfg.judgment.preflight_live) else 0
    return {
        "source_calls": source_calls,
        "judgment_calls": judgment_calls,
        "preflight_calls": preflight_calls,
        "total_without_replacements": source_calls + judgment_calls,
        "total_with_preflight": source_calls + judgment_calls + preflight_calls,
        "max_source_replacements": n_models * cfg.generation.max_invalid_attempts_per_model,
        "max_judgment_replacements": n_models * cfg.judgment.trials_per_judge * (cfg.judgment.max_attempts_per_trial - 1),
    }


def cost_estimate(cfg: PilotConfig, catalog_entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    e = cfg.estimate
    rows = []
    total = 0.0
    worst = 0.0
    for label in cfg.model_labels:
        entry = catalog_entries[label]
        src_n = cfg.generation.valid_strings_per_model
        jud_n = cfg.judgment.trials_per_judge
        src_cost = src_n * estimate_call_cost(entry, e.source_prompt_tokens, e.source_completion_tokens)
        jud_cost = jud_n * estimate_call_cost(entry, e.judgment_prompt_tokens, e.judgment_completion_tokens)
        pre_cost = estimate_call_cost(entry, 40, 100) if cfg.judgment.preflight_live and cfg.judgment.response_mode == "structured" else 0.0
        # worst case: every allowed replacement happens and completions hit max_tokens
        worst_src = (src_n + cfg.generation.max_invalid_attempts_per_model) * estimate_call_cost(
            entry, e.source_prompt_tokens, cfg.generation.max_tokens)
        worst_jud = jud_n * cfg.judgment.max_attempts_per_trial * estimate_call_cost(
            entry, e.judgment_prompt_tokens, cfg.judgment.max_tokens)
        row = {
            "label": label,
            "model_id": entry.get("id"),
            "prompt_usd_per_mtok": round(price_per_token(entry, "prompt") * 1e6, 4),
            "completion_usd_per_mtok": round(price_per_token(entry, "completion") * 1e6, 4),
            "source_calls": src_n,
            "judgment_calls": jud_n,
            "est_source_usd": round(src_cost, 4),
            "est_judgment_usd": round(jud_cost, 4),
            "est_preflight_usd": round(pre_cost, 4),
            "est_total_usd": round(src_cost + jud_cost + pre_cost, 4),
            "worst_case_usd": round(worst_src + worst_jud + pre_cost, 2),
        }
        rows.append(row)
        total += row["est_total_usd"]
        worst += row["worst_case_usd"]
    return {
        "assumptions": cfg.estimate.model_dump(),
        "rows": rows,
        "est_total_usd": round(total, 4),
        "worst_case_total_usd": round(worst, 2),
        "max_cost_usd": cfg.run.max_cost_usd,
        "within_budget": total <= cfg.run.max_cost_usd,
        "counts": call_counts(cfg),
    }


def estimate_markdown(est: dict[str, Any]) -> str:
    c = est["counts"]
    lines = [
        "## Planned calls",
        "",
        f"- source calls: {c['source_calls']} ({c['source_calls'] // 3} per model)",
        f"- judgment calls: {c['judgment_calls']} ({c['judgment_calls'] // 3} per judge)",
        f"- structured-output preflight calls: {c['preflight_calls']}",
        f"- total successful calls before replacements: {c['total_without_replacements']}",
        f"- replacement ceiling: up to {c['max_source_replacements']} extra source calls and "
        f"{c['max_judgment_replacements']} extra judgment calls",
        "",
        "## Cost estimate (catalog prices x configured token assumptions)",
        "",
        f"Token assumptions per call: {est['assumptions']}",
        "",
        "| model | prompt $/Mtok | completion $/Mtok | source calls | judgment calls | est. USD | worst case USD |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in est["rows"]:
        lines.append(
            f"| {r['label']} ({r['model_id']}) | {r['prompt_usd_per_mtok']} | {r['completion_usd_per_mtok']} "
            f"| {r['source_calls']} | {r['judgment_calls']} | {r['est_total_usd']} | {r['worst_case_usd']} |"
        )
    lines += [
        "",
        f"Estimated total: ${est['est_total_usd']} (ceiling max_cost_usd = ${est['max_cost_usd']}; "
        f"{'within' if est['within_budget'] else 'EXCEEDS'} budget). "
        f"Worst case if every replacement fires and every completion hits max_tokens: ${est['worst_case_total_usd']}.",
        "",
    ]
    return "\n".join(lines)


def _mean_tokens(records: list) -> tuple[float | None, float | None, int]:
    ps, cs = [], []
    for r in records:
        u = r.token_usage or {}
        if u.get("prompt_tokens") is not None and u.get("completion_tokens") is not None:
            ps.append(float(u["prompt_tokens"]))
            cs.append(float(u["completion_tokens"]))
    if not ps:
        return None, None, 0
    return sum(ps) / len(ps), sum(cs) / len(cs), len(ps)


def usage_based_estimate(cfg: PilotConfig, catalog_entries: dict[str, Any], sources: list[SourceRecord],
                         judgments: list[JudgmentRecord], trials: list[TrialRecord], spent_usd: float) -> dict[str, Any]:
    """Re-project the remaining cost of a run from the token usage actually observed so far.

    Per model, mean prompt/completion tokens of the recorded source calls (and judgment calls,
    if any) replace the config's assumptions. Where a model has no observed calls of a kind, the
    config assumption is used and flagged.
    """
    e = cfg.estimate
    latest = latest_judgments_by_trial(judgments)
    rows = []
    total_remaining = 0.0
    for label in cfg.model_labels:
        entry = catalog_entries[label]
        src = [r for r in sources if r.source_model_label == label]
        jud = [r for r in judgments if r.judge_model_label == label]
        sp, sc, ns = _mean_tokens(src)
        jp, jc, nj = _mean_tokens(jud)
        src_valid = sum(1 for r in src if r.valid)
        remaining_src = max(0, cfg.generation.valid_strings_per_model - src_valid)
        if trials:
            js = [t for t in trials if t.judge_model_label == label]
            remaining_jud = sum(1 for t in js if not (latest.get(t.trial_id) and latest[t.trial_id].valid))
        else:
            remaining_jud = cfg.judgment.trials_per_judge
        sp_eff = sp if sp is not None else e.source_prompt_tokens
        sc_eff = sc if sc is not None else e.source_completion_tokens
        jp_eff = jp if jp is not None else e.judgment_prompt_tokens
        jc_eff = jc if jc is not None else e.judgment_completion_tokens
        # Reasoning tokens inflate judgment completions the same way as source completions; when no
        # judgment call has been observed yet, scale the judgment assumption by the observed
        # source-completion ratio so the projection reflects what this model actually does.
        if jc is None and sc is not None and e.source_completion_tokens:
            jc_eff = e.judgment_completion_tokens * (sc / e.source_completion_tokens)
        rem_cost = (remaining_src * estimate_call_cost(entry, sp_eff, sc_eff)
                    + remaining_jud * estimate_call_cost(entry, jp_eff, jc_eff))
        total_remaining += rem_cost
        rows.append({
            "label": label,
            "observed_source_calls": ns, "mean_source_prompt_tokens": sp, "mean_source_completion_tokens": sc,
            "observed_judgment_calls": nj, "mean_judgment_prompt_tokens": jp, "mean_judgment_completion_tokens": jc,
            "remaining_source_calls": remaining_src, "remaining_judgment_calls": remaining_jud,
            "assumed_judgment_completion_tokens": jc_eff,
            "projected_remaining_usd": round(rem_cost, 4),
            "spent_usd": round(sum((r.reported_cost if r.reported_cost is not None else (r.estimated_cost or 0.0))
                                   for r in src + jud), 4),
        })
    return {"rows": rows, "spent_usd": round(spent_usd, 4), "projected_remaining_usd": round(total_remaining, 4),
            "projected_total_usd": round(spent_usd + total_remaining, 4), "max_cost_usd": cfg.run.max_cost_usd}


def usage_estimate_markdown(ub: dict[str, Any], run_id: str) -> str:
    def f(x: Any) -> str:
        return "n/a" if x is None else (f"{x:.0f}" if isinstance(x, float) else str(x))
    lines = [f"## Re-projection from actual usage in run {run_id}", "",
             "| model | src calls seen | mean src tokens in/out | jud calls seen | mean jud tokens in/out | remaining src/jud | spent USD | projected remaining USD |",
             "|---|---|---|---|---|---|---|---|"]
    for r in ub["rows"]:
        lines.append(f"| {r['label']} | {r['observed_source_calls']} | {f(r['mean_source_prompt_tokens'])}/{f(r['mean_source_completion_tokens'])} "
                     f"| {r['observed_judgment_calls']} | {f(r['mean_judgment_prompt_tokens'])}/{f(r['mean_judgment_completion_tokens'])} "
                     f"| {r['remaining_source_calls']}/{r['remaining_judgment_calls']} | {r['spent_usd']} | {r['projected_remaining_usd']} |")
    lines += ["", f"Spent so far: ${ub['spent_usd']}; projected remaining: ${ub['projected_remaining_usd']}; "
                  f"projected total: ${ub['projected_total_usd']} (ceiling ${ub['max_cost_usd']}). "
                  "Completion means include hidden reasoning tokens. Where no judgment call has been observed, the "
                  "judgment completion assumption is scaled by the observed source-completion ratio.", ""]
    return "\n".join(lines)
