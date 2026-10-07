"""Run validation: a concise PASS/FAIL report over the raw records of one run.

A run is labeled COMPLETE only if every check passes. Warnings never block completion.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .build_trials import balance_report, build_all_sessions, render_prompt, stimulus_hash
from .config import PilotConfig
from .judge import template_for_mode
from .records import (
    JudgmentRecord,
    RunPaths,
    SourceRecord,
    TrialRecord,
    effective_cost,
    latest_judgments_by_trial,
    load_manifest,
    load_trials,
    read_jsonl,
    sha256_text,
    valid_sources_by_model,
)


@dataclass
class Check:
    name: str
    status: str  # PASS | FAIL | WARN
    detail: str


@dataclass
class ValidationReport:
    run_id: str
    checks: list[Check] = field(default_factory=list)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.status == "FAIL"]

    @property
    def complete(self) -> bool:
        return not self.failed

    def add(self, name: str, ok: bool, detail: str, warn_only: bool = False) -> None:
        status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        self.checks.append(Check(name, status, detail))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": "COMPLETE" if self.complete else "INCOMPLETE",
            "n_pass": sum(c.status == "PASS" for c in self.checks),
            "n_fail": len(self.failed),
            "n_warn": sum(c.status == "WARN" for c in self.checks),
            "checks": [c.__dict__ for c in self.checks],
        }

    def markdown(self) -> str:
        d = self.to_dict()
        lines = [f"# Validation report: {self.run_id}", "",
                 f"**Status: {d['status']}** ({d['n_pass']} pass, {d['n_fail']} fail, {d['n_warn']} warn)", "",
                 "| check | status | detail |", "|---|---|---|"]
        for c in self.checks:
            lines.append(f"| {c.name} | {c.status} | {c.detail} |")
        lines.append("")
        return "\n".join(lines)


def _forbidden_tokens(cfg: PilotConfig, manifest: dict, sources: list[SourceRecord], judgments: list[JudgmentRecord]) -> list[str]:
    toks: set[str] = set()
    for label, m in cfg.models.items():
        toks.add(label)
        toks.add(m.model_id)
        toks.add(m.model_id.split("/")[0])
    for r in sources:
        toks.add(r.sample_id)
        if r.provider:
            toks.add(r.provider)
    for r in judgments:
        if r.provider:
            toks.add(r.provider)
    toks.add(manifest.get("run_id", "\u0000"))
    toks.add("src_")
    # Very short tokens would false-positive on ordinary words (e.g. a provider called "AI").
    return sorted(t for t in toks if t and len(t) >= 4)


def validate_run(cfg: PilotConfig, paths: RunPaths) -> ValidationReport:
    manifest = load_manifest(paths)
    run_id = manifest["run_id"]
    rep = ValidationReport(run_id=run_id)
    labels = cfg.model_labels
    g, j = cfg.generation, cfg.judgment

    sources = read_jsonl(paths.source_calls, SourceRecord)
    judgments = read_jsonl(paths.judgment_calls, JudgmentRecord)
    try:
        trials = load_trials(paths)
    except FileNotFoundError:
        trials = []

    # ---- catalog
    cat_models = (manifest.get("catalog") or {}).get("models") or {}
    missing = [l for l in labels if l not in cat_models
               or (cat_models[l].get("catalog_entry") or {}).get("id") != cfg.model_id(l)]
    rep.add("catalog_ids_present_in_manifest", not missing,
            "all configured IDs snapshotted" if not missing else f"missing/mismatched: {missing}")
    # A route may report the catalog id or its dated canonical slug; both identify the same entry.
    accepted_ids: dict[str, set[str]] = {}
    for l in labels:
        entry = (cat_models.get(l) or {}).get("catalog_entry") or {}
        accepted_ids[l] = {cfg.model_id(l)} | {v for v in (entry.get("id"), entry.get("canonical_slug")) if v}

    # ---- sources
    pattern = re.compile(rf"^[{re.escape(g.alphabet)}]{{{g.string_length}}}$")
    by_model = valid_sources_by_model(sources, labels)
    counts = {l: len(v) for l, v in by_model.items()}
    rep.add("valid_strings_per_model", all(c == g.valid_strings_per_model for c in counts.values()),
            f"{counts} (expected exactly {g.valid_strings_per_model} each)")
    bad_valid = [r.sample_id for r in sources if r.valid and not (r.parsed_string and pattern.fullmatch(r.parsed_string))]
    bad_invalid = [r.sample_id for r in sources if not r.valid and r.parsed_string is not None]
    rep.add("source_records_consistent_with_parser", not bad_valid and not bad_invalid,
            f"valid-but-malformed: {bad_valid}; invalid-with-parsed: {bad_invalid}")
    dup_sample_ids = [s for s, c in Counter(r.sample_id for r in sources).items() if c > 1]
    rep.add("sample_ids_unique", not dup_sample_ids, f"duplicates: {dup_sample_ids}")
    invalid_sources = [r for r in sources if not r.valid]
    n_api = sum(1 for r in invalid_sources if r.invalid_reason == "api_error")
    missing_raw = [r.sample_id for r in invalid_sources if not r.raw_response_path or not (paths.raw_dir / r.raw_response_path).exists()]
    rep.add("invalid_source_raw_retained", not missing_raw,
            f"{len(invalid_sources) - n_api} malformed + {n_api} api-error source calls; missing raw files: {missing_raw}")
    retried = [r.sample_id for r in sources if (r.call_attempts or 1) > 1]
    rep.add("no_retried_source_requests", not retried,
            f"requests that needed HTTP retries (possible double billing): {retried}", warn_only=True)
    # replacement links: every invalid call must be followed by a call pointing back at it (unless it is the model's last call)
    last_by_model = {l: next((r.sample_id for r in reversed(sources) if r.source_model_label == l), None) for l in labels}
    replaced = {r.replacement_for for r in sources if r.replacement_for}
    unlinked = [r.sample_id for r in invalid_sources
                if r.sample_id not in replaced and r.sample_id != last_by_model[r.source_model_label]]
    rep.add("invalid_sources_have_replacements", not unlinked, f"invalid without replacement link: {unlinked}")
    multi_linked = [k for k, c in Counter(r.replacement_for for r in sources if r.replacement_for).items() if c > 1]
    dangling = sorted({r.replacement_for for r in sources if r.replacement_for} - {r.sample_id for r in sources})
    rep.add("replacement_links_one_to_one", not multi_linked and not dangling,
            f"invalid samples referenced by >1 replacement: {multi_linked}; links to unknown samples: {dangling}")
    mism = [(r.sample_id, r.returned_model_id) for r in sources
            if r.valid and r.returned_model_id not in accepted_ids.get(r.source_model_label, set())]
    rep.add("source_returned_model_matches_requested", not mism,
            f"accepted ids: {dict((l, sorted(v)) for l, v in accepted_ids.items())}; mismatches: {mism[:5]}{'...' if len(mism) > 5 else ''}")
    providers = defaultdict(set)
    for r in sources + judgments:
        if r.provider:
            providers[getattr(r, "source_model_label", None) or r.judge_model_label].add(r.provider)
    multi = {l: sorted(p) for l, p in providers.items() if len(p) > 1}
    rep.add("single_provider_per_model", not multi, f"providers: {dict((l, sorted(p)) for l, p in providers.items())}", warn_only=True)
    pins = {l: m.provider for l, m in cfg.models.items() if m.provider}
    if pins:
        off = {l: sorted(p for p in providers.get(l, set()) if p.lower() != pins[l].lower()) for l in pins}
        off = {l: v for l, v in off.items() if v}
        rep.add("provider_pins_honored", not off, f"pins: {pins}; calls served elsewhere: {off}")

    # ---- trials
    if not trials:
        rep.add("trials_present", False, "no trials built")
        return rep
    rep.add("trials_present", True, f"{len(trials)} trials")
    n_per_judge = Counter(t.judge_model_label for t in trials)
    rep.add("trials_per_judge", all(n_per_judge.get(l, 0) == j.trials_per_judge for l in labels),
            f"{dict(n_per_judge)} (expected {j.trials_per_judge} each)")
    breport = balance_report(trials, labels, j.trials_per_cell)
    for judge, r in breport.items():
        for c in r["checks"]:
            rep.add(f"trials[{judge}].{c['check']}", c["pass"], c["detail"])
    valid_ids = {r.sample_id: r for r in sources if r.valid}
    unknown = [t.trial_id for t in trials if t.source_1_sample_id not in valid_ids or t.source_2_sample_id not in valid_ids]
    rep.add("trial_sources_are_valid_strings", not unknown, f"trials citing unknown/invalid samples: {unknown}")
    from .representation import render
    bad_display = []
    bad_hash = []
    for t in trials:
        if t.source_1_sample_id in valid_ids and t.source_2_sample_id in valid_ids:
            d1 = render(valid_ids[t.source_1_sample_id].parsed_string or "", j.display_alphabet, g.alphabet)
            d2 = render(valid_ids[t.source_2_sample_id].parsed_string or "", j.display_alphabet, g.alphabet)
            if (d1, d2) != (t.string_1_display, t.string_2_display):
                bad_display.append(t.trial_id)
            if stimulus_hash(d1, d2) != t.stimulus_hash:
                bad_hash.append(t.trial_id)
    rep.add("trial_display_strings_match_sources", not bad_display, f"mismatched: {bad_display}")
    rep.add("stimulus_hashes_match", not bad_hash, f"mismatched: {bad_hash}")

    # reproducibility: rebuild from seed and compare
    seed = int((manifest.get("config") or {}).get("run", {}).get("seed", cfg.run.seed))
    pool = {l: [(r.sample_id, r.parsed_string or "") for r in by_model[l]] for l in labels}
    if all(len(pool[l]) >= 2 for l in labels):
        rebuilt, _ = build_all_sessions(run_id, labels, pool, j.trials_per_cell, seed, j.display_alphabet, g.alphabet)
        key = lambda t: (t.trial_id, t.analytical_cell, t.correct_answer, t.source_1_sample_id, t.source_2_sample_id,
                         t.display_order, t.trial_position)
        same = sorted(map(key, rebuilt)) == sorted(map(key, trials))
        rep.add("trial_sequence_reproducible_from_seed", same, f"seed {seed}; rebuilt {'matches' if same else 'DIFFERS from'} stored trials")
    else:
        rep.add("trial_sequence_reproducible_from_seed", False, "not enough valid sources to rebuild")

    # ---- judgments
    if not judgments:
        rep.add("judgments_present", False, "no judgment calls recorded")
        return rep
    rep.add("judgments_present", True, f"{len(judgments)} judgment calls")
    modes = Counter(r.response_mode for r in judgments)
    rep.add("single_response_mode", len(modes) == 1, f"modes used: {dict(modes)}")
    mode = judgments[0].response_mode
    template = template_for_mode(manifest["prompts"], mode)
    trial_by_id = {t.trial_id: t for t in trials}
    forbidden = _forbidden_tokens(cfg, manifest, sources, judgments)
    leak, not_fresh, wrong_prompt = [], [], []
    for r in judgments:
        msgs = r.request_payload_sanitized.get("messages", [])
        roles = [m.get("role") for m in msgs]
        if roles.count("user") != 1 or "assistant" in roles or roles[-1] != "user":
            not_fresh.append(r.judgment_id)
        user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
        t = trial_by_id.get(r.trial_id)
        if t is not None:
            expected = render_prompt(template, t.string_1_display, t.string_2_display)
            if user != expected or r.prompt_hash != sha256_text(expected):
                wrong_prompt.append(r.judgment_id)
        low = user.lower()
        if any(tok.lower() in low for tok in forbidden):
            leak.append(r.judgment_id)
    rep.add("fresh_context_per_judgment", not not_fresh, f"non-fresh payloads: {not_fresh[:5]}")
    rep.add("judgment_prompts_match_template_and_trial", not wrong_prompt, f"mismatched: {wrong_prompt[:5]}")
    rep.add("no_source_metadata_in_stimulus", not leak, f"tokens screened: {len(forbidden)}; leaks: {leak[:5]}")
    dup_j = [k for k, c in Counter(r.judgment_id for r in judgments).items() if c > 1]
    dup_attempt = [k for k, c in Counter((r.trial_id, r.attempt_number) for r in judgments).items() if c > 1]
    multi_valid = [tid for tid, c in Counter(r.trial_id for r in judgments if r.valid).items() if c > 1]
    rep.add("no_duplicate_judgment_calls", not dup_j and not dup_attempt and not multi_valid,
            f"dup ids: {dup_j}; dup (trial, attempt): {dup_attempt}; trials with >1 valid judgment: {multi_valid}")
    invalid_j = [r for r in judgments if not r.valid]
    n_api_j = sum(1 for r in invalid_j if r.invalid_reason == "api_error")
    missing_raw_j = [r.judgment_id for r in invalid_j if not r.raw_response_path or not (paths.raw_dir / r.raw_response_path).exists()]
    rep.add("invalid_judgment_raw_retained", not missing_raw_j,
            f"{len(invalid_j) - n_api_j} malformed + {n_api_j} api-error judgment calls; missing raw: {missing_raw_j}")
    retried_j = [r.judgment_id for r in judgments if (r.call_attempts or 1) > 1]
    rep.add("no_retried_judgment_requests", not retried_j,
            f"requests that needed HTTP retries (possible double billing): {retried_j}", warn_only=True)
    replaced_j = {r.replacement_for for r in judgments if r.replacement_for}
    latest = latest_judgments_by_trial(judgments)
    unlinked_j = [r.judgment_id for r in invalid_j if r.judgment_id not in replaced_j and latest[r.trial_id].judgment_id != r.judgment_id]
    rep.add("invalid_judgments_linked_to_replacements", not unlinked_j, f"unlinked: {unlinked_j}")
    multi_linked_j = [k for k, c in Counter(r.replacement_for for r in judgments if r.replacement_for).items() if c > 1]
    rep.add("judgment_replacement_links_one_to_one", not multi_linked_j, f"referenced by >1 replacement: {multi_linked_j}")
    mism_j = [(r.judgment_id, r.returned_model_id) for r in judgments
              if r.valid and r.returned_model_id not in accepted_ids.get(r.judge_model_label, set())]
    rep.add("judgment_returned_model_matches_requested", not mism_j, f"mismatches: {mism_j[:5]}")
    wrong_correct = [r.judgment_id for r in judgments if r.valid and r.trial_id in trial_by_id
                     and r.correct != (r.parsed_judgment == trial_by_id[r.trial_id].correct_answer)]
    rep.add("correctness_scored_consistently", not wrong_correct, f"mis-scored: {wrong_correct}")
    unjudged = [t.trial_id for t in trials if not (latest.get(t.trial_id) and latest[t.trial_id].valid)]
    rep.add("every_trial_has_valid_judgment", not unjudged, f"{len(trials) - len(unjudged)}/{len(trials)} trials judged; missing: {unjudged[:8]}")
    per_judge_cells = defaultdict(Counter)
    for t in trials:
        if latest.get(t.trial_id) and latest[t.trial_id].valid:
            per_judge_cells[t.judge_model_label][t.analytical_cell] += 1
    incomplete_cells = {jl: dict(c) for jl, c in per_judge_cells.items() if any(c.get(cell, 0) != j.trials_per_cell for cell in "ABCD")}
    rep.add("every_design_cell_complete", not incomplete_cells and len(per_judge_cells) == len(labels),
            f"valid judgments per cell: {dict((k, dict(v)) for k, v in per_judge_cells.items())}")

    # ---- budget
    all_calls = sources + judgments + read_jsonl(paths.preflight_calls, JudgmentRecord)
    spent = sum(effective_cost(r) for r in all_calls)
    unreported = sum(1 for r in all_calls if r.reported_cost is None and r.invalid_reason != "api_error")
    rep.add("budget_ceiling_respected", spent <= cfg.run.max_cost_usd,
            f"spend ${spent:.4f} <= ${cfg.run.max_cost_usd:.2f} ({unreported} calls without a reported cost, counted at our estimate)")
    return rep
