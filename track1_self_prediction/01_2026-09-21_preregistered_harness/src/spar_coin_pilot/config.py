"""Run configuration: YAML -> validated pydantic model.

The API key is read from the environment (optionally via a .env file); it is never part of
the config object that gets written into run manifests.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator


class RunConfig(BaseModel):
    name: str
    seed: int
    dry_run: bool = True
    max_cost_usd: float = Field(gt=0)


class OpenRouterConfig(BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key_env: str = "OPENROUTER_API_KEY"
    request_timeout_seconds: float = 180
    max_retries: int = 5
    concurrency: int = Field(default=3, ge=1)
    provider_allow_fallbacks: bool = False
    provider_require_parameters: bool = True
    app_title: str | None = "spar-coin-pilot"
    # When true, every call carries a deterministic `seed` (sha256 of run seed + record id), sent
    # only to models whose catalog entry lists `seed` among supported parameters. It changes
    # nothing about the sampling distribution; it lets providers that honor seeds reproduce a
    # call. Off by default (the handoff does not ask for it). When sent, the seed is recorded per
    # call (api_seed / api_seed_sent in the flat CSVs).
    send_seed: bool = False


class ModelConfig(BaseModel):
    model_id: str
    # Optional provider pin (OpenRouter provider name as listed in the model's endpoints, e.g.
    # "OpenAI", "Anthropic", "DeepInfra"). When set, every request for this model carries
    # provider.order = [provider] with allow_fallbacks false, so all calls go to one serving stack.
    provider: str | None = None


class GenerationConfig(BaseModel):
    valid_strings_per_model: int = Field(default=10, ge=1)
    string_length: int = Field(default=50, ge=1)
    alphabet: str = "HT"
    reasoning_effort: Literal["low", "medium", "high"] | None = "low"
    include_reasoning: bool = False
    max_invalid_attempts_per_model: int = Field(default=10, ge=0)
    max_tokens: int = Field(default=6000, ge=1)
    system_prompt: str | None = None
    temperature: float | None = None

    @field_validator("alphabet")
    @classmethod
    def _alphabet_two_distinct(cls, v: str) -> str:
        if len(v) != 2 or v[0] == v[1]:
            raise ValueError("alphabet must be exactly two distinct characters, e.g. HT")
        return v


class JudgmentConfig(BaseModel):
    trials_per_judge: int = Field(default=24, ge=4)
    trials_per_cell: int = Field(default=6, ge=1)
    reasoning_effort: Literal["low", "medium", "high"] | None = "low"
    include_reasoning: bool = False
    response_mode: Literal["structured", "one_word"] = "structured"
    fallback_response_mode: Literal["structured", "one_word"] = "one_word"
    preflight_live: bool = True
    display_alphabet: Literal["HT", "AB"] = "HT"
    fresh_context_per_trial: bool = True
    max_tokens: int = Field(default=6000, ge=1)
    system_prompt: str | None = None
    temperature: float | None = None
    max_attempts_per_trial: int = Field(default=3, ge=1)
    lenient_parse: bool = False

    @model_validator(mode="after")
    def _cells_match(self) -> "JudgmentConfig":
        if self.trials_per_cell * 4 != self.trials_per_judge:
            raise ValueError(
                "judgment.trials_per_judge must equal 4 * judgment.trials_per_cell "
                f"(got {self.trials_per_judge} and {self.trials_per_cell})"
            )
        if self.trials_per_cell % 2 != 0:
            raise ValueError("judgment.trials_per_cell must be even so that cells B and C split evenly "
                             "across the two other models and display order can be balanced")
        if not self.fresh_context_per_trial:
            raise ValueError("fresh_context_per_trial must be true: every trial is a stateless call")
        return self


class EstimateConfig(BaseModel):
    source_prompt_tokens: int = 60
    source_completion_tokens: int = 400
    judgment_prompt_tokens: int = 220
    judgment_completion_tokens: int = 400


class PathsConfig(BaseModel):
    data_dir: str = "data"
    results_dir: str = "results"
    prompts_dir: str = "prompts"
    schemas_dir: str = "schemas"


class PilotConfig(BaseModel):
    run: RunConfig
    openrouter: OpenRouterConfig = OpenRouterConfig()
    models: dict[str, ModelConfig]
    generation: GenerationConfig = GenerationConfig()
    judgment: JudgmentConfig = JudgmentConfig()
    estimate: EstimateConfig = EstimateConfig()
    paths: PathsConfig = PathsConfig()

    # Populated by load_config; excluded from manifests via sanitized_dict().
    config_path: Path | None = Field(default=None, exclude=True)
    project_root: Path | None = Field(default=None, exclude=True)

    @field_validator("models")
    @classmethod
    def _three_models(cls, v: dict[str, ModelConfig]) -> dict[str, ModelConfig]:
        if len(v) != 3:
            raise ValueError("exactly three models are required for the four-cell design")
        ids = [m.model_id for m in v.values()]
        if len(set(ids)) != 3:
            raise ValueError("model_ids must be distinct")
        for label in v:
            if not label.isidentifier() or label != label.lower():
                raise ValueError(f"model label {label!r} must be a lowercase identifier")
        return v

    @property
    def model_labels(self) -> list[str]:
        """Labels in config order (this order is fixed for the whole run)."""
        return list(self.models.keys())

    def model_id(self, label: str) -> str:
        return self.models[label].model_id

    def root(self) -> Path:
        return self.project_root or Path.cwd()

    def data_raw_dir(self, run_id: str) -> Path:
        return self.root() / self.paths.data_dir / "raw" / run_id

    def data_derived_dir(self, run_id: str) -> Path:
        return self.root() / self.paths.data_dir / "derived" / run_id

    def results_dir(self, run_id: str) -> Path:
        return self.root() / self.paths.results_dir / run_id

    def prompt_path(self, name: str) -> Path:
        return self.root() / self.paths.prompts_dir / name

    def schema_path(self, name: str) -> Path:
        return self.root() / self.paths.schemas_dir / name

    def sanitized_dict(self) -> dict:
        """Config as stored in manifests (never contains the API key)."""
        return self.model_dump(mode="json")

    def config_hash(self) -> str:
        return hashlib.sha256(
            yaml.safe_dump(self.sanitized_dict(), sort_keys=True).encode("utf-8")
        ).hexdigest()


# Config keys that define the design of a run. Once a run has been created, these must not
# change between invocations; a change means a new run. Everything else (timeouts, retries,
# concurrency, budget ceiling, provider pins, token limits, ceilings, estimate assumptions,
# paths, dry_run) is operational and may change between invocations of the same run.
DESIGN_LOCKED_KEYS: tuple[str, ...] = (
    "run.name",
    "run.seed",
    "openrouter.send_seed",
    "models.*.model_id",
    "generation.valid_strings_per_model",
    "generation.string_length",
    "generation.alphabet",
    "generation.reasoning_effort",
    "generation.include_reasoning",
    "generation.system_prompt",
    "generation.temperature",
    # max_tokens sets the reasoning budget on Anthropic routes (effort -> share of max_tokens),
    # so it is part of the treatment, not an operational knob.
    "generation.max_tokens",
    "judgment.trials_per_judge",
    "judgment.trials_per_cell",
    "judgment.reasoning_effort",
    "judgment.include_reasoning",
    "judgment.response_mode",
    "judgment.fallback_response_mode",
    "judgment.display_alphabet",
    "judgment.fresh_context_per_trial",
    "judgment.system_prompt",
    "judgment.temperature",
    "judgment.max_tokens",
    "judgment.lenient_parse",
)


def _flatten(d: dict, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def _is_locked(key: str) -> bool:
    for pattern in DESIGN_LOCKED_KEYS:
        if pattern == key:
            return True
        if "*" in pattern:
            head, tail = pattern.split("*", 1)
            if key.startswith(head) and key.endswith(tail):
                return True
    return False


def config_diff(stored: dict, live: dict) -> tuple[list[str], list[str]]:
    """Compare two sanitized config dicts. Returns (design_locked_changes, operational_changes),
    each a list of 'key: stored -> live' strings. Model labels and their order are design-locked
    too: they are compared as a whole."""
    a, b = _flatten(stored), _flatten(live)
    locked: list[str] = []
    operational: list[str] = []
    if list((stored.get("models") or {}).keys()) != list((live.get("models") or {}).keys()):
        locked.append(f"models (labels/order): {list((stored.get('models') or {}).keys())} -> "
                      f"{list((live.get('models') or {}).keys())}")
    for key in sorted(set(a) | set(b)):
        if a.get(key) == b.get(key):
            continue
        line = f"{key}: {a.get(key)!r} -> {b.get(key)!r}"
        (locked if _is_locked(key) else operational).append(line)
    return locked, operational


def load_config(path: str | os.PathLike, project_root: str | os.PathLike | None = None) -> PilotConfig:
    """Load and validate a YAML config.

    project_root defaults to the parent of the config file's directory (i.e. the folder
    containing config/, prompts/, data/ ...). Relative paths in the config resolve against it.
    """
    cfg_path = Path(path).resolve()
    with cfg_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    cfg = PilotConfig.model_validate(raw)
    cfg.config_path = cfg_path
    cfg.project_root = Path(project_root).resolve() if project_root else cfg_path.parent.parent
    return cfg


def load_api_key(cfg: PilotConfig, required: bool = True) -> str | None:
    """Read the API key from the environment, loading .env from the project root if present."""
    load_dotenv(cfg.root() / ".env", override=False)
    key = os.environ.get(cfg.openrouter.api_key_env, "").strip()
    if not key:
        if required:
            raise RuntimeError(
                f"{cfg.openrouter.api_key_env} is not set. Copy .env.example to .env and add your key."
            )
        return None
    return key
