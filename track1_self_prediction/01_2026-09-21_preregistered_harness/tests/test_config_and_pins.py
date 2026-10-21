"""Round-robin --limit, provider pins, design-locked config, usage-based estimate, prompt wording."""

from collections import Counter

import pytest

from spar_coin_pilot import pipeline
from spar_coin_pilot.build_trials import render_prompt
from spar_coin_pilot.config import config_diff
from spar_coin_pilot.openrouter_client import ModelCatalogError
from spar_coin_pilot.records import JudgmentRecord, SourceRecord, load_manifest, read_jsonl
from spar_coin_pilot.run_setup import ConfigConflict, load_prompts, run_paths

from conftest import LABELS, make_config


def _sources(cfg, run_id):
    return read_jsonl(run_paths(cfg, run_id).source_calls, SourceRecord)


def test_limit_three_means_one_call_per_model(cfg):
    # --limit 3 is exactly one call per model; any limit keeps the models within one call of
    # each other (which model gets the extra call in a partial round depends on latency).
    for _ in range(3):
        run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=3, yes=True, fake=True)
        assert Counter(r.source_model_label for r in _sources(cfg, run_id)) == {l: 1 for l in LABELS}
    for limit in (4, 7, 11):
        run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=limit, yes=True, fake=True)
        counts = Counter(r.source_model_label for r in _sources(cfg, run_id))
        assert sum(counts.values()) == limit and set(counts) == set(LABELS)
        assert max(counts.values()) - min(counts.values()) <= 1, (limit, counts)
    # a full run also finishes with every model at 10 valid, dispatched round-robin
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    assert Counter(r.source_model_label for r in _sources(cfg, run_id) if r.valid) == {l: 10 for l in LABELS}


def test_judgment_limit_three_touches_every_judge(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=3, yes=True, fake=True)
    recs = read_jsonl(run_paths(cfg, run_id).judgment_calls, JudgmentRecord)
    assert Counter(r.judge_model_label for r in recs) == {l: 1 for l in LABELS}
    assert all(r.trial_id.endswith("_01") for r in recs)


def test_provider_pin_is_sent_and_validated(project):
    cfg = make_config(project)
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=3, yes=True, fake=True)
    # pin to the provider actually seen: allowed, and every later payload carries provider.order
    cfg2 = make_config(project, models={"qwen": {"model_id": "qwen/qwen3.8-27b", "provider": "FakeProvider"}})
    pipeline.cmd_generate(cfg2, run_id, dry_run=False, limit=None, yes=True, fake=True)
    recs = _sources(cfg2, run_id)
    qwen_later = [r for r in recs if r.source_model_label == "qwen"][1:]
    assert all(r.request_payload_sanitized["provider"]["order"] == ["FakeProvider"] for r in qwen_later)
    assert all("order" not in r.request_payload_sanitized["provider"] for r in recs if r.source_model_label != "qwen")
    assert all(r.request_payload_sanitized["provider"]["allow_fallbacks"] is False for r in recs)
    manifest = load_manifest(run_paths(cfg2, run_id))
    assert manifest["config"]["models"]["qwen"]["provider"] == "FakeProvider"
    assert len(manifest["config_history"]) == 1 and "models.qwen.provider" in manifest["config_history"][0]["changes"][0]
    pipeline.cmd_build_trials(cfg2, run_id)
    pipeline.cmd_run_judgments(cfg2, run_id, dry_run=False, limit=None, yes=True, fake=True)
    rep = pipeline.cmd_validate(cfg2, run_id)
    assert rep.complete and any(c.name == "provider_pins_honored" and c.status == "PASS" for c in rep.checks)


def test_provider_pin_must_be_a_listed_endpoint_and_match_history(project):
    cfg = make_config(project)
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=3, yes=True, fake=True,
                                   fake_kwargs={"provider_name": "ProvA"})
    # not among the model's endpoints -> refused before any call
    bad = make_config(project, models={"astra": {"model_id": "openai/gpt-6-astra", "provider": "Nowhere"}})
    with pytest.raises(ModelCatalogError):
        pipeline.cmd_generate(bad, run_id, dry_run=False, limit=None, yes=True, fake=True, fake_kwargs={"provider_name": "ProvA"})
    assert len(_sources(cfg, run_id)) == 3
    # listed, but the run's earlier calls went to a different provider -> refused
    other = make_config(project, models={"astra": {"model_id": "openai/gpt-6-astra", "provider": "ProvB"}})
    with pytest.raises(ModelCatalogError):
        pipeline.cmd_generate(other, run_id, dry_run=False, limit=None, yes=True, fake=True, fake_kwargs={"provider_name": "ProvB"})
    assert len(_sources(cfg, run_id)) == 3


def test_design_locked_change_refused_operational_change_logged(project):
    cfg = make_config(project)
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=3, yes=True, fake=True)
    locked = make_config(project, run={"seed": 1})
    with pytest.raises(ConfigConflict):
        pipeline.cmd_generate(locked, run_id, dry_run=False, limit=None, yes=True, fake=True)
    assert len(_sources(cfg, run_id)) == 3
    # max_tokens is part of the treatment (reasoning budget on Anthropic routes): locked too
    locked2 = make_config(project, run={"seed": 20260921}, generation={"max_tokens": 3000})
    with pytest.raises(ConfigConflict):
        pipeline.cmd_generate(locked2, run_id, dry_run=False, limit=None, yes=True, fake=True)
    ok = make_config(project, generation={"max_tokens": 6000}, run={"seed": 20260921, "max_cost_usd": 10.0},
                     openrouter={"request_timeout_seconds": 60})
    pipeline.cmd_generate(ok, run_id, dry_run=False, limit=1, yes=True, fake=True)
    manifest = load_manifest(run_paths(ok, run_id))
    assert manifest["config"]["run"]["max_cost_usd"] == 10.0
    changes = manifest["config_history"][0]["changes"]
    assert any("openrouter.request_timeout_seconds" in c for c in changes) and any("run.max_cost_usd" in c for c in changes)
    assert len(_sources(cfg, run_id)) == 4


def test_config_diff_classification():
    a = {"run": {"seed": 1, "max_cost_usd": 25}, "models": {"x": {"model_id": "m", "provider": None}}, "generation": {"max_tokens": 6000}}
    b = {"run": {"seed": 2, "max_cost_usd": 30}, "models": {"x": {"model_id": "m", "provider": "P"}}, "generation": {"max_tokens": 100}}
    locked, operational = config_diff(a, b)
    assert locked == ["generation.max_tokens: 6000 -> 100", "run.seed: 1 -> 2"]
    assert sorted(operational) == ["models.x.provider: None -> 'P'", "run.max_cost_usd: 25 -> 30"]
    locked, _ = config_diff(a, {**b, "models": {"y": {"model_id": "m", "provider": None}}})
    assert any(c.startswith("models (labels/order)") for c in locked)


def test_estimate_from_run_uses_observed_usage(cfg, capsys):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=3, yes=True, fake=True)
    est = pipeline.cmd_estimate(cfg, fake=True, run_id=run_id)
    ub = est["usage_based"]
    rows = {r["label"]: r for r in ub["rows"]}
    assert all(rows[l]["observed_source_calls"] == 1 and rows[l]["remaining_source_calls"] == 9 for l in LABELS)
    assert all(rows[l]["remaining_judgment_calls"] == 24 for l in LABELS)
    assert ub["projected_total_usd"] > ub["spent_usd"] > 0
    assert "Re-projection from actual usage" in capsys.readouterr().out


def test_judge_prompt_wording(cfg):
    prompts = load_prompts(cfg)
    for key in ("judge_same_different", "judge_same_different_structured"):
        text = prompts[key]["text"]
        assert text.startswith("Each of the two strings below was generated by an LLM asked to simulate 50 flips of a fair coin. "
                               "The strings may have been generated by the same underlying model or by two different models.")
        assert "Two language models" not in text
    rendered = render_prompt(prompts["judge_same_different"]["text"], "H" * 50, "T" * 50)
    assert rendered.endswith("Respond with only SAME or DIFFERENT.")
    assert render_prompt(prompts["judge_same_different_structured"]["text"], "H" * 50, "T" * 50).endswith("Return only the requested JSON.")
