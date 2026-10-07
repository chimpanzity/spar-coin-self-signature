"""End-to-end pipeline with the fake client, plus budget, fallback, and leak checks."""

import json
from collections import Counter

import pandas as pd
import pytest

from spar_coin_pilot import pipeline
from spar_coin_pilot.estimate import call_counts
from spar_coin_pilot.openrouter_client import BudgetExceeded, BudgetGuard
from spar_coin_pilot.records import JudgmentRecord, SourceRecord, load_manifest, read_jsonl
from spar_coin_pilot.run_setup import run_paths

from conftest import LABELS, make_config


def test_full_pipeline_validates_complete_and_summarizes(cfg):
    fake = {"invalid_source_schedule": {4, 17}, "invalid_judgment_schedule": {5, 40}}
    run_id = pipeline.cmd_demo_fake(cfg, fake_kwargs=fake)
    paths = run_paths(cfg, run_id)
    manifest = load_manifest(paths)

    # catalog: the three configured IDs are in the saved snapshot
    cat = manifest["catalog"]["models"]
    assert {cat[l]["catalog_entry"]["id"] for l in LABELS} == {m.model_id for m in cfg.models.values()}
    assert paths.catalog_full.exists()

    # sources: exactly 10 valid per model, invalid ones retained with raw responses
    sources = read_jsonl(paths.source_calls, SourceRecord)
    assert Counter(r.source_model_label for r in sources if r.valid) == {l: 10 for l in LABELS}
    invalid = [r for r in sources if not r.valid]
    assert len(invalid) == 2
    for r in invalid:
        raw = json.loads((paths.raw_dir / r.raw_response_path).read_text(encoding="utf-8"))
        assert raw["response_json"]["choices"][0]["message"]["content"] == r.raw_completion
        assert r.parsed_string is None

    # judgments: every trial judged once validly; invalid attempts kept and linked
    judgments = read_jsonl(paths.judgment_calls, JudgmentRecord)
    valid_by_trial = Counter(r.trial_id for r in judgments if r.valid)
    assert len(valid_by_trial) == 72 and set(valid_by_trial.values()) == {1}
    bad = [r for r in judgments if not r.valid]
    assert len(bad) == 2 and all((paths.raw_dir / r.raw_response_path).exists() for r in bad)
    for r in judgments:
        msgs = r.request_payload_sanitized["messages"]
        assert [m["role"] for m in msgs] == ["user"], "fresh context: exactly one user message, no history"
        assert r.request_payload_sanitized["reasoning"] == {"effort": "low", "exclude": True}
        assert "temperature" not in r.request_payload_sanitized
    assert manifest["judgment_response_mode"]["effective"] == "structured"

    # validation and summary outputs
    vr = json.loads((paths.results_dir / "validation_report.json").read_text(encoding="utf-8"))
    assert vr["status"] == "COMPLETE" and vr["n_fail"] == 0, [c for c in vr["checks"] if c["status"] != "PASS"]
    for name in ("summary.md", "judge_results.csv", "cell_results.csv", "trial_level.csv",
                 "source_diagnostics_by_model.csv", "source_diagnostics_by_string.csv", "confusion_matrices.csv"):
        assert (paths.results_dir / name).exists(), name
    cells = pd.read_csv(paths.results_dir / "cell_results.csv")
    assert (cells["n_valid"] == 6).all() and len(cells) == 12
    jr = pd.read_csv(paths.results_dir / "judge_results.csv")
    assert list(jr["judge_model_label"]) == LABELS
    assert (jr["n_valid_judgments"] == 24).all()
    assert jr["n_invalid_attempts"].sum() == 2
    tl = pd.read_csv(paths.results_dir / "trial_level.csv")
    assert len(tl) == 72 and tl["valid"].all()
    by_model = pd.read_csv(paths.results_dir / "source_diagnostics_by_model.csv")
    assert list(by_model["n_valid"]) == [10, 10, 10] and by_model["n_invalid"].sum() == 2
    assert by_model["mean_n_runs"].between(1, 50).all()
    for name in ("sources.csv", "trials.csv", "judgments.csv"):
        assert (paths.derived_dir / name).exists()


def test_planned_call_counts(cfg):
    c = call_counts(cfg)
    assert c["source_calls"] == 30 and c["judgment_calls"] == 72 and c["total_without_replacements"] == 102


def test_budget_ceiling_stops_dispatch_cleanly(project):
    # Each fake call reports $0.001; the ceiling allows only a few calls. Estimated per-call
    # cost from the fake catalog prices is 60*2e-6 + 400*1e-5 ~= $0.0041.
    cfg = make_config(project, run={"max_cost_usd": 0.015})
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    paths = run_paths(cfg, run_id)
    sources = read_jsonl(paths.source_calls, SourceRecord)
    manifest = load_manifest(paths)
    phase = manifest["phases"]["generate"]
    assert not phase["complete"]
    assert any(v["stop_reason"] == "budget" for v in phase["per_model"].values())
    assert sum(r.reported_cost or 0 for r in sources) <= 0.015
    assert 0 < len(sources) < 30
    assert phase["calls_made_this_invocation"] == len(sources)


def test_budget_guard_accounts_for_inflight_reservations():
    g = BudgetGuard(max_cost_usd=1.0, spent_usd=0.5)
    g.reserve(0.3)
    with pytest.raises(BudgetExceeded):
        g.reserve(0.3)
    g.settle(0.3, actual_cost_usd=0.1)
    assert g.spent_usd == pytest.approx(0.6)
    g.reserve(0.3)  # fits again once the reservation is settled at the lower actual cost


def test_structured_fallback_applies_to_all_judges(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    out = pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True,
                                     fake_kwargs={"structured_supported": False})
    assert out["mode"] == "one_word"
    paths = run_paths(cfg, run_id)
    manifest = load_manifest(paths)
    assert manifest["judgment_response_mode"]["reason"].startswith("fallback")
    judgments = read_jsonl(paths.judgment_calls, JudgmentRecord)
    assert {r.response_mode for r in judgments} == {"one_word"}
    assert all("Respond with only SAME or DIFFERENT." in r.request_payload_sanitized["messages"][0]["content"] for r in judgments)
    preflight = read_jsonl(paths.preflight_calls, JudgmentRecord)
    assert len(preflight) == 3 and all(r.invalid_reason == "api_error" for r in preflight)
    rep = pipeline.cmd_validate(cfg, run_id)
    assert rep.complete


def test_dry_run_makes_no_chat_calls_and_reports_30_and_72(cfg, capsys):
    out_dir = pipeline.cmd_dry_run(cfg, fake=True)
    text = (out_dir / "dry_run_report.md").read_text(encoding="utf-8")
    assert "30 source calls, 72 judgment calls" in text
    assert "102 successful calls before any replacements" in text
    assert "Simulate 50 flips of a fair coin." in text
    assert (out_dir / "balance_report.md").exists() and (out_dir / "trials_placeholder.json").exists()
    payloads = json.loads((out_dir / "generation_payloads.json").read_text(encoding="utf-8"))
    assert set(payloads) == set(LABELS)
    # no run directory was created by the dry run
    assert not (cfg.root() / "data" / "raw").exists() or not any((cfg.root() / "data" / "raw").iterdir())


def test_config_dry_run_flag_blocks_paid_calls(project):
    cfg = make_config(project)
    cfg.run.dry_run = True
    rid = pipeline.cmd_generate(cfg, None, dry_run=cfg.run.dry_run, limit=None, yes=True, fake=True)
    assert rid.startswith("(new run id")
    assert not (cfg.root() / "data" / "raw").exists() or not any((cfg.root() / "data" / "raw").iterdir())


def test_validation_fails_on_contaminated_stimulus(cfg):
    run_id = pipeline.cmd_demo_fake(cfg)
    paths = run_paths(cfg, run_id)
    # Tamper: inject a model name into one judgment's recorded prompt and re-validate.
    lines = paths.judgment_calls.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["request_payload_sanitized"]["messages"][0]["content"] += " (generated by anthropic/claude-fable-5.1)"
    lines[0] = json.dumps(rec)
    paths.judgment_calls.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rep = pipeline.cmd_validate(cfg, run_id)
    assert not rep.complete
    names = {c.name for c in rep.failed}
    assert "no_source_metadata_in_stimulus" in names and "judgment_prompts_match_template_and_trial" in names


def test_validation_refuses_incomplete_cells(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=50, yes=True, fake=True)
    rep = pipeline.cmd_validate(cfg, run_id)
    assert not rep.complete
    assert {"every_trial_has_valid_judgment", "every_design_cell_complete"} <= {c.name for c in rep.failed}


def test_baselines_and_decision_rules_are_computed(cfg):
    from spar_coin_pilot.summarize import baseline_distance_judge, baseline_loo_nearest_centroid
    run_id = pipeline.cmd_demo_fake(cfg)
    paths = run_paths(cfg, run_id)
    sources = read_jsonl(paths.source_calls, SourceRecord)
    trials = pipeline.load_trials(paths)
    b1 = baseline_loo_nearest_centroid(cfg, sources)
    assert b1["n"] == 30 and 0 <= b1["accuracy"] <= 1 and set(b1["recall_by_model"]) == set(LABELS)
    assert sum(sum(row.values()) for row in b1["confusion"].values()) == 30
    b2 = baseline_distance_judge(cfg, sources, trials)
    assert len(b2) == 72 and set(b2["baseline_judgment"]) <= {"SAME", "DIFFERENT"}
    assert (b2["baseline_judgment"] == "SAME").sum() == 36, "median split answers SAME on exactly half the trials"
    rules = pd.read_csv(paths.results_dir / "decision_rules.csv")
    names = set(rules["rule"])
    for expected in ("R0 source signal present", "R0' degenerate strings flag", "R1 pooled above chance",
                     "R2' pooled advantage", "R2d reciprocal selectivity", "R3 feasibility",
                     "RB baseline 2 (distance judge) accuracy", "RB baseline 1 (LOO nearest centroid) accuracy"):
        assert expected in names, expected
    for label in LABELS:
        assert f"R1 {label} above chance" in names and f"R2 {label} own-model advantage" in names
    assert str(rules.set_index("rule").loc["R2d reciprocal selectivity", "met"]) in {"reciprocal", "partial", "absent", "reversed"}
    assert (paths.results_dir / "baseline_loo_classifier.csv").exists() and (paths.results_dir / "baseline_distance_judge.csv").exists()
    text = (paths.results_dir / "summary.md").read_text(encoding="utf-8")
    assert "Preregistered decision rules" in text and "External baselines" in text
