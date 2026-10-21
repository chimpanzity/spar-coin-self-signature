"""Shared fixtures: an isolated copy of the project (config, prompts, schemas) under tmp_path."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from spar_coin_pilot.config import PilotConfig, load_config

REPO_ROOT = Path(__file__).resolve().parent.parent
LABELS = ["astra", "fable", "qwen"]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    for sub in ("config", "prompts", "schemas"):
        shutil.copytree(REPO_ROOT / sub, tmp_path / sub)
    return tmp_path


def make_config(project: Path, **overrides) -> PilotConfig:
    """Load the real pilot config from the temp project, applying nested overrides like
    {"run": {"max_cost_usd": 0.01}}."""
    cfg_path = project / "config" / "pilot_coin.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    for section, values in overrides.items():
        raw.setdefault(section, {}).update(values)
    raw["run"]["dry_run"] = False
    cfg_path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return load_config(cfg_path, project_root=project)


@pytest.fixture
def cfg(project: Path) -> PilotConfig:
    return make_config(project)
