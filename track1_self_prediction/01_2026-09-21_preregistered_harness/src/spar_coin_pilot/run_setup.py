"""Run lifecycle: run IDs, manifest creation, and the startup catalog check.

Every command that could spend money calls `snapshot_catalog_into_manifest` first. It
fetches the live OpenRouter catalog, confirms the three configured IDs exist, stores the
relevant entries (plus per-provider endpoint details) in the manifest, and refuses to
continue if a previously snapshotted entry has changed identity.
"""

from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from . import __version__
from .config import PilotConfig, config_diff
from .openrouter_client import ChatClient, ModelCatalogError, supported_parameters, validate_catalog
from .records import (
    JudgmentRecord,
    RunPaths,
    SourceRecord,
    iso,
    load_manifest,
    read_json,
    read_jsonl,
    sha256_text,
    update_manifest,
    utc_now,
    write_json,
)

log = logging.getLogger(__name__)

PROMPT_FILES = {
    "generate_coin": "generate_coin.txt",
    "judge_same_different": "judge_same_different.txt",
    "judge_same_different_structured": "judge_same_different_structured.txt",
}

# Catalog fields whose change between snapshot and now means "this ID no longer points at the
# same thing": refuse to spend money until the operator has looked.
IDENTITY_FIELDS = ("id", "name", "created", "canonical_slug")


def new_run_id(cfg: PilotConfig, fake: bool = False, now: datetime | None = None) -> str:
    """<run.name>_<UTC timestamp>; never reuses an id whose run directory already exists."""
    ts = (now or utc_now()).strftime("%Y%m%d_%H%M%S")
    prefix = "fake_" if fake else ""
    base = f"{prefix}{cfg.run.name}_{ts}"
    run_id, n = base, 1
    while cfg.data_raw_dir(run_id).exists():
        n += 1
        run_id = f"{base}_{n}"
    return run_id


def _git_commit(root: Path) -> str | None:
    """Short commit hash of the project checkout, if it is a git repository (best effort)."""
    try:
        import subprocess
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            commit = out.stdout.strip()
            dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                                   capture_output=True, text=True, timeout=5)
            if dirty.returncode == 0 and dirty.stdout.strip():
                commit += "-dirty"
            return commit
    except Exception:  # git missing, not a repo, or timeout: not an error for the run
        pass
    return None


def run_paths(cfg: PilotConfig, run_id: str) -> RunPaths:
    return RunPaths(cfg.data_raw_dir(run_id), cfg.data_derived_dir(run_id), cfg.results_dir(run_id))


def load_prompts(cfg: PilotConfig) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for key, fname in PROMPT_FILES.items():
        path = cfg.prompt_path(fname)
        text = path.read_text(encoding="utf-8")
        out[key] = {"path": str(path), "text": text, "sha256": sha256_text(text)}
    return out


def load_judgment_schema(cfg: PilotConfig) -> dict[str, Any]:
    return read_json(cfg.schema_path("judgment.schema.json"))


def create_or_open_run(cfg: PilotConfig, run_id: str | None, fake: bool = False) -> tuple[str, RunPaths, dict]:
    """Create a new run (manifest + directories) or open an existing one for resume."""
    if run_id is None:
        run_id = new_run_id(cfg, fake=fake)
    paths = run_paths(cfg, run_id)
    paths.ensure()
    if paths.manifest.exists():
        manifest = load_manifest(paths)
        return run_id, paths, manifest

    prompts = load_prompts(cfg)
    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "run_name": cfg.run.name,
        "fake_client": fake,
        "created_at": iso(utc_now()),
        "config_path": str(cfg.config_path),
        "config_hash": cfg.config_hash(),
        "config": cfg.sanitized_dict(),
        "prompts": prompts,
        "judgment_schema": load_judgment_schema(cfg),
        "environment": {
            "package_version": __version__,
            "git_commit": _git_commit(cfg.root()),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "hostname": platform.node(),
        },
        "phases": {},
    }
    write_json(paths.manifest, manifest)
    return run_id, paths, manifest


def snapshot_catalog_into_manifest(
    cfg: PilotConfig, client: ChatClient, paths: RunPaths, manifest: dict, allow_drift: bool = False,
) -> dict[str, dict[str, Any]]:
    """Fetch the live catalog, validate the configured IDs, and store the entries in the manifest.

    Returns {label: catalog_entry}. Raises ModelCatalogError if an ID is missing or (unless
    allow_drift) an already-snapshotted entry's identity fields changed.
    """
    model_ids = {label: m.model_id for label, m in cfg.models.items()}
    catalog = client.list_models()
    entries = validate_catalog(catalog, model_ids)
    fetched_at = iso(utc_now())

    previous = (manifest.get("catalog") or {}).get("models") or {}
    drift: list[str] = []
    for label, entry in entries.items():
        prev_entry = (previous.get(label) or {}).get("catalog_entry")
        if not prev_entry:
            continue
        for field in IDENTITY_FIELDS:
            if field in prev_entry and prev_entry.get(field) != entry.get(field):
                drift.append(f"{label} ({entry.get('id')}): {field} {prev_entry.get(field)!r} -> {entry.get(field)!r}")
        if prev_entry.get("pricing") != entry.get("pricing"):
            log.warning("pricing for %s changed since the run's first snapshot: %s -> %s",
                        label, prev_entry.get("pricing"), entry.get("pricing"))
    if drift and not allow_drift:
        raise ModelCatalogError(
            "catalog entry identity changed since this run was started (refusing to spend money):\n  "
            + "\n  ".join(drift) + "\nRe-run with --allow-catalog-drift only if this is understood."
        )

    if not paths.catalog_full.exists():
        write_json(paths.catalog_full, {"fetched_at": fetched_at, "n_models": len(catalog), "data": catalog})

    if previous:
        # Keep the run's original snapshot; record later fetches (with their pricing) alongside.
        catalog_info = dict(manifest.get("catalog") or {})
        history = list(catalog_info.get("fetch_history") or [])
        history.append({"fetched_at": fetched_at, "n_models_in_catalog": len(catalog),
                        "pricing": {label: entry.get("pricing") for label, entry in entries.items()}})
        catalog_info["fetch_history"] = history
        catalog_info["last_fetched_at"] = fetched_at
        update_manifest(paths, catalog=catalog_info)
        manifest["catalog"] = catalog_info
        return entries

    models_snapshot: dict[str, Any] = {}
    for label, entry in entries.items():
        endpoints = client.get_endpoints(entry["id"])
        models_snapshot[label] = {
            "requested_model_id": entry["id"],
            "catalog_entry": entry,
            "supported_parameters": supported_parameters(entry),
            "endpoints": endpoints,
        }
    catalog_info = {
        "fetched_at": fetched_at,
        "last_fetched_at": fetched_at,
        "n_models_in_catalog": len(catalog),
        "models": models_snapshot,
        "fetch_history": [{"fetched_at": fetched_at, "n_models_in_catalog": len(catalog),
                           "pricing": {label: entry.get("pricing") for label, entry in entries.items()}}],
    }
    update_manifest(paths, catalog=catalog_info)
    manifest["catalog"] = catalog_info
    return entries


def config_from_manifest(manifest: dict, live_cfg: PilotConfig) -> tuple[PilotConfig, list[str]]:
    """The run's own config snapshot as a PilotConfig, plus the top-level sections in which
    the live YAML now differs from it. Validation and trial building use the snapshot so that
    later edits to the YAML cannot change what a run is checked against."""
    snap = PilotConfig.model_validate(manifest["config"])
    snap.config_path = live_cfg.config_path
    snap.project_root = live_cfg.project_root
    live = live_cfg.sanitized_dict()
    stored = snap.sanitized_dict()
    differing = [k for k in stored if stored.get(k) != live.get(k)]
    return snap, differing


def record_key_usage(client: ChatClient, paths: RunPaths, when: str) -> None:
    """Best-effort: store the API key's usage counter before/after a phase for cross-checking."""
    try:
        info = client.get_key_info()
    except Exception as exc:  # pragma: no cover - never fatal
        info = {"error": str(exc)}
    if info is None:
        return
    keep = {k: info.get(k) for k in ("label", "usage", "limit", "limit_remaining", "is_free_tier") if k in info}
    if "error" in info:
        keep["error"] = info["error"]
    keep["at"] = iso(utc_now())
    manifest = load_manifest(paths)
    usage_log = list(manifest.get("key_usage_log") or [])
    usage_log.append({"when": when, **keep})
    update_manifest(paths, key_usage_log=usage_log)


def relative_to_run(paths: RunPaths, p: Path) -> str:
    """Path relative to the run's raw dir, always with forward slashes (portable across OSes)."""
    try:
        return p.relative_to(paths.raw_dir).as_posix()
    except ValueError:
        return p.as_posix()


class ConfigConflict(RuntimeError):
    """The live YAML changes a design-locked parameter of an existing run."""


def reconcile_config(cfg: PilotConfig, paths: RunPaths, manifest: dict, allow: bool = False) -> list[str]:
    """Before spending money on an existing run: refuse design-locked changes, accept operational
    ones (recording the previous config in the manifest's config_history). Returns the list of
    operational changes applied."""
    stored = manifest.get("config") or {}
    live = cfg.sanitized_dict()
    if stored == live:
        return []
    locked, operational = config_diff(stored, live)
    if locked and not allow:
        raise ConfigConflict(
            "the config changes design parameters of run "
            f"{manifest.get('run_id')} (start a new run instead, or revert the YAML):\n  "
            + "\n  ".join(locked)
        )
    history = list(manifest.get("config_history") or [])
    history.append({
        "replaced_at": iso(utc_now()),
        "config_hash": manifest.get("config_hash"),
        "config": stored,
        "changes": operational + ([f"[design-locked, forced] {c}" for c in locked] if locked else []),
    })
    update_manifest(paths, config=live, config_hash=cfg.config_hash(), config_history=history)
    manifest["config"] = live
    manifest["config_hash"] = cfg.config_hash()
    manifest["config_history"] = history
    return operational + locked


def check_provider_pins(cfg: PilotConfig, manifest: dict, paths: RunPaths) -> list[str]:
    """Validate models.<label>.provider pins before spending money.

    A pin must name a provider that serves the model (per the endpoints stored in the manifest,
    when available) and must agree with the provider of every call already recorded for that
    model in this run. Returns human-readable notes; raises ModelCatalogError on a violation.
    """
    notes: list[str] = []
    cat_models = (manifest.get("catalog") or {}).get("models") or {}
    sources = read_jsonl(paths.source_calls, SourceRecord)
    judgments = read_jsonl(paths.judgment_calls, JudgmentRecord) + read_jsonl(paths.preflight_calls, JudgmentRecord)
    for label, m in cfg.models.items():
        pin = m.provider
        if not pin:
            continue
        eps = ((cat_models.get(label) or {}).get("endpoints") or {})
        names = [e.get("provider_name") for e in (eps.get("endpoints") or [])] if isinstance(eps, dict) else []
        names = [n for n in names if n]
        if names:
            if pin.lower() not in {n.lower() for n in names}:
                raise ModelCatalogError(
                    f"models.{label}.provider = {pin!r} is not among the providers serving "
                    f"{m.model_id} per the catalog endpoints: {names}"
                )
        else:
            notes.append(f"{label}: could not verify pin {pin!r} against endpoints (none stored); OpenRouter will reject it if unknown")
        seen = {r.provider for r in sources if r.source_model_label == label and r.provider}
        seen |= {r.provider for r in judgments if r.judge_model_label == label and r.provider}
        others = sorted(p for p in seen if p.lower() != pin.lower())
        if others:
            raise ModelCatalogError(
                f"models.{label}.provider = {pin!r} but calls already recorded in this run used {others}; "
                "pin the provider that was actually used, or start a new run"
            )
        notes.append(f"{label}: pinned to {pin}" + (f" (consistent with {len(seen)} provider name(s) seen so far)" if seen else ""))
    return notes
