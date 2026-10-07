"""Data records and on-disk layout.

Raw data (data/raw/<run_id>/) is append-only:
  manifest.json                      run manifest (config snapshot, catalog entries, phase info)
  catalog_full.json                  full OpenRouter /models catalog at run start
  source_calls.jsonl                 one SourceRecord per source call (valid or invalid)
  judgment_calls.jsonl               one JudgmentRecord per judgment call (valid or invalid)
  preflight_calls.jsonl              structured-output preflight calls, if any
  responses/source/<sample_id>.json  complete raw API response per call
  responses/judgment/<judgment_id>.json
  responses/preflight/<id>.json
  trials/trials.json                 all TrialRecords for the run
  trials/trial_manifest.md           human-readable trial manifest
  trials/balance_report.json / .md   balance report

Derived CSVs (data/derived/<run_id>/) and results (results/<run_id>/) are rebuilt from raw.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal, TypeVar

from pydantic import BaseModel

SCHEMA_VERSION = "1.0"

Judgment = Literal["SAME", "DIFFERENT"]
Cell = Literal["A", "B", "C", "D"]

_T = TypeVar("_T", bound=BaseModel)
_write_lock = threading.Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(ts: datetime) -> str:
    return ts.isoformat(timespec="milliseconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SourceRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    sample_id: str
    source_model_label: str
    requested_model_id: str
    returned_model_id: str | None = None
    provider: str | None = None
    prompt_text: str
    prompt_hash: str
    request_payload_sanitized: dict[str, Any]
    request_id: str | None = None
    raw_response_path: str | None = None
    raw_completion: str | None = None
    parsed_string: str | None = None
    valid: bool
    invalid_reason: str | None = None
    replacement_for: str | None = None
    attempt_number: int
    started_at: str
    completed_at: str
    latency_ms: int
    token_usage: dict[str, Any] | None = None
    # reported_cost: usage.cost as returned by OpenRouter (None if the route did not report it).
    # estimated_cost: our own estimate from token usage x catalog price (or the pre-call estimate),
    # used for budget accounting only when reported_cost is missing.
    reported_cost: float | None = None
    estimated_cost: float | None = None
    # number of HTTP attempts the client needed (retries + 1); >1 means a retried request that
    # the provider may have billed more than once.
    call_attempts: int | None = None
    finish_reason: str | None = None
    error: str | None = None


class TrialRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    trial_id: str
    judge_model_label: str
    analytical_cell: Cell
    # Sub-cell for B and C records which "other" model is involved; A -> "A", D -> "D".
    subcell: str
    correct_answer: Judgment
    source_1_model_label: str
    source_2_model_label: str
    source_1_sample_id: str
    source_2_sample_id: str
    # "orig" = the pair's canonical (first, second) order was kept; "flipped" = swapped.
    display_order: Literal["orig", "flipped"]
    trial_position: int
    construction_seed: str
    stimulus_hash: str
    string_1_display: str
    string_2_display: str


class JudgmentRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    judgment_id: str
    trial_id: str
    judge_model_label: str
    requested_model_id: str
    returned_model_id: str | None = None
    provider: str | None = None
    response_mode: Literal["structured", "one_word"]
    prompt_hash: str
    request_payload_sanitized: dict[str, Any]
    raw_response_path: str | None = None
    raw_completion: str | None = None
    parsed_judgment: Judgment | None = None
    valid: bool
    invalid_reason: str | None = None
    correct: bool | None = None
    replacement_for: str | None = None
    attempt_number: int
    request_id: str | None = None
    started_at: str
    completed_at: str
    latency_ms: int
    token_usage: dict[str, Any] | None = None
    # reported_cost: usage.cost as returned by OpenRouter (None if the route did not report it).
    # estimated_cost: our own estimate from token usage x catalog price (or the pre-call estimate),
    # used for budget accounting only when reported_cost is missing.
    reported_cost: float | None = None
    estimated_cost: float | None = None
    # number of HTTP attempts the client needed (retries + 1); >1 means a retried request that
    # the provider may have billed more than once.
    call_attempts: int | None = None
    finish_reason: str | None = None
    error: str | None = None


class RunPaths:
    """All paths for one run, derived from the config's data/results directories."""

    def __init__(self, raw_dir: Path, derived_dir: Path, results_dir: Path):
        self.raw_dir = raw_dir
        self.derived_dir = derived_dir
        self.results_dir = results_dir

    @property
    def manifest(self) -> Path:
        return self.raw_dir / "manifest.json"

    @property
    def catalog_full(self) -> Path:
        return self.raw_dir / "catalog_full.json"

    @property
    def source_calls(self) -> Path:
        return self.raw_dir / "source_calls.jsonl"

    @property
    def judgment_calls(self) -> Path:
        return self.raw_dir / "judgment_calls.jsonl"

    @property
    def preflight_calls(self) -> Path:
        return self.raw_dir / "preflight_calls.jsonl"

    @property
    def responses_dir(self) -> Path:
        return self.raw_dir / "responses"

    @property
    def trials_dir(self) -> Path:
        return self.raw_dir / "trials"

    @property
    def trials_json(self) -> Path:
        return self.trials_dir / "trials.json"

    @property
    def trial_manifest_md(self) -> Path:
        return self.trials_dir / "trial_manifest.md"

    @property
    def balance_report_json(self) -> Path:
        return self.trials_dir / "balance_report.json"

    @property
    def balance_report_md(self) -> Path:
        return self.trials_dir / "balance_report.md"

    def ensure(self) -> None:
        for d in (self.raw_dir, self.derived_dir, self.results_dir, self.trials_dir,
                  self.responses_dir / "source", self.responses_dir / "judgment",
                  self.responses_dir / "preflight"):
            d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- JSON / JSONL helpers

def append_jsonl(path: Path, record: BaseModel) -> None:
    """Append one record. The file is never rewritten or truncated by this package."""
    line = json.dumps(record.model_dump(mode="json"), ensure_ascii=False)
    with _write_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()


def read_jsonl(path: Path, model: type[_T]) -> list[_T]:
    if not path.exists():
        return []
    out: list[_T] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(model.model_validate_json(line))
    return out


def iter_jsonl_dicts(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_raw_response(path: Path, payload: dict) -> Path:
    """Write a raw response file exactly once. Existing files are never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"raw response file already exists (append-only store): {path}")
    with path.open("x", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
    return path


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
    tmp.replace(path)


def load_manifest(paths: RunPaths) -> dict:
    if not paths.manifest.exists():
        raise FileNotFoundError(f"no manifest at {paths.manifest}; run `generate` first")
    return read_json(paths.manifest)


def update_manifest(paths: RunPaths, **updates: Any) -> dict:
    """Merge top-level keys into the manifest and write it back."""
    with _write_lock:
        manifest = read_json(paths.manifest) if paths.manifest.exists() else {}
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(manifest.get(k), dict):
                manifest[k].update(v)
            else:
                manifest[k] = v
        manifest["updated_at"] = iso(utc_now())
        write_json(paths.manifest, manifest)
    return manifest


def load_trials(paths: RunPaths) -> list[TrialRecord]:
    if not paths.trials_json.exists():
        raise FileNotFoundError(f"no trials at {paths.trials_json}; run `build-trials` first")
    return [TrialRecord.model_validate(t) for t in read_json(paths.trials_json)]


def valid_sources_by_model(records: list[SourceRecord], labels: list[str]) -> dict[str, list[SourceRecord]]:
    """Valid source records per model, in call order (the order used by the trial builder)."""
    out: dict[str, list[SourceRecord]] = {label: [] for label in labels}
    for r in records:
        if r.valid and r.source_model_label in out:
            out[r.source_model_label].append(r)
    return out


def effective_cost(r: "SourceRecord | JudgmentRecord") -> float:
    """Cost to count against the budget: reported if present, else our estimate, else 0."""
    if r.reported_cost is not None:
        return float(r.reported_cost)
    if r.estimated_cost is not None:
        return float(r.estimated_cost)
    return 0.0


def latest_judgments_by_trial(records: list[JudgmentRecord]) -> dict[str, JudgmentRecord]:
    """The most recent judgment attempt for each trial (valid or not)."""
    latest: dict[str, JudgmentRecord] = {}
    for r in records:
        prev = latest.get(r.trial_id)
        if prev is None or r.attempt_number >= prev.attempt_number:
            latest[r.trial_id] = r
    return latest
