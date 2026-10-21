"""Resume semantics: interrupted phases continue without duplicating completed calls."""

from collections import Counter

from spar_coin_pilot import pipeline
from spar_coin_pilot.records import JudgmentRecord, SourceRecord, read_jsonl
from spar_coin_pilot.run_setup import run_paths

from conftest import LABELS


def _sources(cfg, run_id):
    return read_jsonl(run_paths(cfg, run_id).source_calls, SourceRecord)


def _judgments(cfg, run_id):
    return read_jsonl(run_paths(cfg, run_id).judgment_calls, JudgmentRecord)


def test_generation_resumes_without_duplicates(cfg):
    fake = {"invalid_source_schedule": {2, 9}}
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=7, yes=True, fake=True, fake_kwargs=fake)
    first = _sources(cfg, run_id)
    assert len(first) == 7, "limit caps the number of calls in one invocation"

    # second invocation resumes: a fresh fake client, so its invalid schedule restarts at call 1
    pipeline.cmd_generate(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True, fake_kwargs={"invalid_source_schedule": {3}})
    all_recs = _sources(cfg, run_id)
    assert all_recs[:7] == first, "earlier records are untouched (append-only)"
    valid = Counter(r.source_model_label for r in all_recs if r.valid)
    assert valid == {l: 10 for l in LABELS}
    ids = [r.sample_id for r in all_recs]
    assert len(ids) == len(set(ids))
    for label in LABELS:
        nums = sorted(int(r.sample_id.split("_")[-1]) for r in all_recs if r.source_model_label == label)
        assert nums == list(range(1, len(nums) + 1)), "sample numbering continues across invocations"
    # every invalid call has a replacement pointing back at it
    replaced = {r.replacement_for for r in all_recs if r.replacement_for}
    for r in all_recs:
        if not r.valid:
            assert r.sample_id in replaced

    # third invocation: nothing left to do
    n_before = len(all_recs)
    pipeline.cmd_generate(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True)
    assert len(_sources(cfg, run_id)) == n_before


def test_judgments_resume_without_duplicates(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=10, yes=True, fake=True,
                               fake_kwargs={"invalid_judgment_schedule": {4}})
    first = _judgments(cfg, run_id)
    assert len(first) == 10
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True)
    recs = _judgments(cfg, run_id)
    assert recs[:10] == first
    valid_by_trial = Counter(r.trial_id for r in recs if r.valid)
    assert len(valid_by_trial) == 72 and max(valid_by_trial.values()) == 1
    assert len({r.judgment_id for r in recs}) == len(recs)
    invalid = [r for r in recs if not r.valid]
    assert len(invalid) == 1
    assert any(r.replacement_for == invalid[0].judgment_id for r in recs)
    n = len(recs)
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True)
    assert len(_judgments(cfg, run_id)) == n, "completed run makes no further calls"


def test_response_mode_is_fixed_for_the_run_on_resume(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    # First invocation: structured unsupported -> global fallback to one_word.
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=5, yes=True, fake=True,
                               fake_kwargs={"structured_supported": False})
    # Resume with a client that would support structured output: mode must stay one_word.
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True,
                               fake_kwargs={"structured_supported": True})
    recs = _judgments(cfg, run_id)
    assert {r.response_mode for r in recs} == {"one_word"}
    assert all(r.request_payload_sanitized.get("response_format") is None for r in recs)


def test_api_error_stops_cleanly_and_resume_completes(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True,
                                   fake_kwargs={"fail_on_call": {5}})
    recs = _sources(cfg, run_id)
    errors = [r for r in recs if r.invalid_reason == "api_error"]
    assert len(errors) == 1 and errors[0].error and errors[0].raw_response_path
    assert Counter(r.source_model_label for r in recs if r.valid) != {l: 10 for l in LABELS}
    pipeline.cmd_generate(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True)
    recs = _sources(cfg, run_id)
    assert Counter(r.source_model_label for r in recs if r.valid) == {l: 10 for l in LABELS}
    assert any(r.replacement_for == errors[0].sample_id for r in recs)


def test_judgment_api_error_stops_cleanly_and_does_not_consume_attempt_ceiling(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    # preflight uses 3 calls; the 6th call overall is the 3rd judgment call
    out = pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True,
                                     fake_kwargs={"fail_on_call": {6}})
    assert out["outcome"].stop_reason == "api_error" and out["outcome"].error
    recs = _judgments(cfg, run_id)
    errs = [r for r in recs if r.invalid_reason == "api_error"]
    assert len(errs) == 1 and errs[0].raw_response_path
    n_before = len(recs)
    assert n_before < 72
    # two more outages on the same trial would exceed max_attempts_per_trial if they counted
    for _ in range(2):
        pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=1, yes=True, fake=True,
                                   fake_kwargs={"fail_on_call": {1}})
    out = pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True)
    assert out["outcome"].complete
    recs = _judgments(cfg, run_id)
    assert Counter(r.trial_id for r in recs if r.valid) == {t: 1 for t in {r.trial_id for r in recs}}
    assert sum(1 for r in recs if r.invalid_reason == "api_error") == 3
    rep = pipeline.cmd_validate(cfg, run_id)
    assert rep.complete, [c for c in rep.failed]


def test_judgment_resume_after_crash_between_raw_write_and_record(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=4, yes=True, fake=True)
    paths = run_paths(cfg, run_id)
    lines = paths.judgment_calls.read_text(encoding="utf-8").splitlines()
    # simulate: raw file written, JSONL append lost
    paths.judgment_calls.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    out = pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True)
    assert out["outcome"].complete
    recs = _judgments(cfg, run_id)
    assert len({r.judgment_id for r in recs}) == len(recs)
    # the orphaned raw file was not overwritten and its trial got a fresh attempt number
    orphan = next(r for r in recs if r.attempt_number == 2 and r.replacement_for is None)
    assert (paths.raw_dir / "responses" / "judgment" / f"j_{orphan.trial_id}_a1.json").exists()
    assert pipeline.cmd_validate(cfg, run_id).complete


def test_max_attempts_exhaustion_is_reported_and_fails_validation(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=None, yes=True, fake=True)
    pipeline.cmd_build_trials(cfg, run_id)
    # every attempt at judgment call #1 is malformed; attempts 1..3 hit the ceiling for that trial
    out = pipeline.cmd_run_judgments(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True,
                                     fake_kwargs={"invalid_judgment_schedule": {1, 73, 74}})
    assert not out["outcome"].complete
    assert sum(p["abandoned_trials"] for p in out["outcome"].per_judge.values()) == 1
    plan = pipeline.plan_judgments(cfg, run_paths(cfg, run_id), pipeline.load_trials(run_paths(cfg, run_id)))
    assert len(plan.abandoned_trial_ids) == 1 and plan.total_planned_calls == 0
    rep = pipeline.cmd_validate(cfg, run_id)
    assert not rep.complete and "every_trial_has_valid_judgment" in {c.name for c in rep.failed}


def test_catalog_identity_drift_is_refused_before_spending(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=2, yes=True, fake=True)
    import pytest
    from spar_coin_pilot.openrouter_client import ModelCatalogError
    with pytest.raises(ModelCatalogError):
        pipeline.cmd_generate(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True,
                              fake_kwargs={"catalog_name_suffix": " (renamed)"})
    assert len(_sources(cfg, run_id)) == 2, "no call was made after the drift was detected"
    pipeline.cmd_generate(cfg, run_id, dry_run=False, limit=None, yes=True, fake=True,
                          fake_kwargs={"catalog_name_suffix": " (renamed)"}, allow_drift=True)
    assert Counter(r.source_model_label for r in _sources(cfg, run_id) if r.valid) == {l: 10 for l in LABELS}


def test_budget_uses_estimates_when_cost_is_not_reported(cfg):
    run_id = pipeline.cmd_generate(cfg, None, dry_run=False, limit=5, yes=True, fake=True,
                                   fake_kwargs={"report_cost": False})
    recs = _sources(cfg, run_id)
    assert all(r.reported_cost is None and r.estimated_cost and r.estimated_cost > 0 for r in recs)
    assert pipeline.spent_so_far(run_paths(cfg, run_id)) == pytest_approx(sum(r.estimated_cost for r in recs))


def pytest_approx(x):
    import pytest
    return pytest.approx(x)
