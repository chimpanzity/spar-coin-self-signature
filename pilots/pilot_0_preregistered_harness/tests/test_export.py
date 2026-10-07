"""Flat CSV export: one self-contained row per call, with seeds, config, catalog, request, response."""

import json

import pandas as pd

from spar_coin_pilot import pipeline
from spar_coin_pilot.export import (
    CALL_COLUMNS,
    CATALOG_COLUMNS,
    DIAG_COLUMNS,
    REQUEST_COLUMNS,
    RESPONSE_COLUMNS,
    RUN_COLUMNS,
    TRIAL_COLUMNS,
    USAGE_COLUMNS,
)
from spar_coin_pilot.openrouter_client import deterministic_seed, seed_for_call
from spar_coin_pilot.records import JudgmentRecord, SourceRecord, read_jsonl
from spar_coin_pilot.run_setup import run_paths

from conftest import LABELS, make_config


def test_flat_export_is_self_contained(cfg):
    run_id = pipeline.cmd_demo_fake(cfg, fake_kwargs={"invalid_source_schedule": {4}, "invalid_judgment_schedule": {7}})
    paths = run_paths(cfg, run_id)
    d = paths.derived_dir
    calls = pd.read_csv(d / "calls_all.csv")
    sources = pd.read_csv(d / "sources.csv")
    judgments = pd.read_csv(d / "judgments.csv")
    preflight = pd.read_csv(d / "preflight.csv")
    trials = pd.read_csv(d / "trials.csv")
    assert (d / "columns.md").exists()

    # every documented column group is present on the union file
    for group in (RUN_COLUMNS, CALL_COLUMNS, REQUEST_COLUMNS, RESPONSE_COLUMNS, USAGE_COLUMNS,
                  CATALOG_COLUMNS, TRIAL_COLUMNS, DIAG_COLUMNS):
        missing = [c for c in group if c not in calls.columns]
        assert not missing, missing
    assert len(calls) == len(sources) + len(preflight) + len(judgments) == 31 + 3 + 73
    assert set(calls["call_kind"]) == {"source", "preflight", "judgment"}
    assert len(trials) == 72 and (trials["run_seed"] == cfg.run.seed).all()

    # seeds and run context on every row
    assert (calls["run_seed"] == cfg.run.seed).all()
    assert calls["config_hash"].notna().all() and calls["package_version"].notna().all()
    assert (judgments["construction_seed"] == judgments["judge_model_label"].map(lambda j: f"{cfg.run.seed}:{j}")).all()
    assert judgments["build_attempts"].notna().all() and judgments["order_max_cell_run"].le(2).all()

    # request and response detail on every row
    src_recs = {r.sample_id: r for r in read_jsonl(paths.source_calls, SourceRecord)}
    jud_recs = {r.judgment_id: r for r in read_jsonl(paths.judgment_calls, JudgmentRecord)}
    for _, row in judgments.iterrows():
        rec = jud_recs[row["record_id"]]
        assert json.loads(row["request_payload_json"]) == json.loads(json.dumps(rec.request_payload_sanitized, sort_keys=True))
        assert row["prompt_text"] == rec.request_payload_sanitized["messages"][0]["content"]
        assert row["raw_completion"] == rec.raw_completion
        assert row["max_tokens"] == cfg.judgment.max_tokens and row["reasoning_effort"] == "low" and bool(row["reasoning_exclude"])
        assert row["response_format_type"] == "json_schema" and bool(row["response_schema_strict"])
        assert row["prompt_tokens"] == rec.token_usage["prompt_tokens"] and row["usage_cost"] == rec.reported_cost
        assert row["string_1_canonical"] == src_recs[row["source_1_sample_id"]].parsed_string
        assert row["string_2_canonical"] == src_recs[row["source_2_sample_id"]].parsed_string
        assert row["source_1_provider"] == "FakeProvider" and row["catalog_name"].startswith("Fake ")
        assert row["source_pair"] == "-".join(sorted([row["source_1_model_label"], row["source_2_model_label"]]))
    invalid_j = judgments[~judgments["valid"]]
    assert len(invalid_j) == 1 and invalid_j.iloc[0]["invalid_reason"].startswith("judgment_not_in_enum")
    replaced = judgments[judgments["replacement_for"] == invalid_j.iloc[0]["record_id"]]
    assert len(replaced) == 1 and replaced.iloc[0]["n_attempts_for_trial"] == 2

    # source rows carry the string diagnostics for valid strings and nothing for invalid ones
    valid_src = sources[sources["valid"]]
    assert valid_src["prop_H"].between(0, 1).all() and (valid_src["length"] == 50).all()
    assert valid_src["n_runs"].between(1, 50).all() and valid_src["runs_test_z"].notna().all()
    assert sources[~sources["valid"]]["prop_H"].isna().all()
    assert (sources["temperature_sent"].isna()).all() and (~sources["api_seed_sent"]).all()

    # export is deterministic and rebuildable
    before = (d / "calls_all.csv").read_bytes()
    pipeline.cmd_export(cfg, run_id)
    assert (d / "calls_all.csv").read_bytes() == before

    # trial_level.csv carries the full judgment row for the latest attempt of every trial
    tl = pd.read_csv(paths.results_dir / "trial_level.csv")
    assert len(tl) == 72 and tl["valid"].all() and "request_payload_json" in tl.columns
    assert set(tl["judgment_id"]) <= set(judgments["record_id"])


def test_api_seed_sent_only_when_enabled_and_supported(project):
    cfg = make_config(project)
    entry_with = {"supported_parameters": ["max_tokens", "seed"]}
    entry_without = {"supported_parameters": ["max_tokens"]}
    val, send = seed_for_call(True, 20260921, "src_astra_001", entry_with)
    assert send and val == deterministic_seed(20260921, "src_astra_001") and 0 <= val < 2 ** 31
    assert seed_for_call(True, 20260921, "src_astra_001", entry_without)[1] is False
    assert seed_for_call(False, 20260921, "src_astra_001", entry_with)[1] is False
    assert deterministic_seed(1, "a") != deterministic_seed(1, "b") != deterministic_seed(2, "b")

    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=3, yes=True, fake=True)
    recs = read_jsonl(run_paths(cfg, run_id).source_calls, SourceRecord)
    assert all("seed" not in r.request_payload_sanitized for r in recs)

    cfg2 = make_config(project, openrouter={"send_seed": True})
    run_id = pipeline.cmd_generate(cfg2, None, dry_run=False, limit=3, yes=True, fake=True)
    recs = read_jsonl(run_paths(cfg2, run_id).source_calls, SourceRecord)
    for r in recs:  # the fake catalog advertises `seed` for every model
        assert r.request_payload_sanitized["seed"] == deterministic_seed(cfg2.run.seed, r.sample_id)
    pipeline.cmd_export(cfg2, run_id)
    src = pd.read_csv(run_paths(cfg2, run_id).derived_dir / "sources.csv")
    assert src["api_seed_sent"].all() and src["api_seed"].notna().all()
