"""Resume-safe on-disk state for the SPAR pilot.

Directory layout for a run:
  data/spar_dynamic/<run_id>/
    manifest.json                       — top-level run status
    catalog_snapshot.json               — OpenRouter model pricing snapshot
    source/
      batch/
        {model_label}/
          trajectory-{k}.json           — full trajectory record (raw + parsed)
      online/
        {model_label}/
          trajectory-{k}.json           — trajectory-level record
          trajectory-{k}.steps.jsonl    — per-step call records (append-only)
    trials/
      trial_manifest.json               — 144 planned trials with metadata
    judgment/
      judgment-{trial_id}.json          — one record per judgment trial
    results/
      *.csv, *.md, summary.md, FINAL_OVERNIGHT_REPORT.md, etc.
    logs/
      orchestrator.log

Every write flushes. Every read is idempotent so orchestrator restart is safe.
"""

import json, os
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional


def _write_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_default)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _default(o):
    if is_dataclass(o):
        return asdict(o)
    raise TypeError(f"not JSON-serializable: {type(o)}")


def append_jsonl(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=_default) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def read_json(path: str) -> Optional[Any]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, obj: Any):
    _write_json(path, obj)


class RunPaths:
    def __init__(self, root: str, run_id: str):
        self.root = os.path.join(root, run_id)
        self.run_id = run_id
        self.manifest = os.path.join(self.root, "manifest.json")
        self.catalog = os.path.join(self.root, "catalog_snapshot.json")
        self.source_batch = os.path.join(self.root, "source", "batch")
        self.source_online = os.path.join(self.root, "source", "online")
        self.trials = os.path.join(self.root, "trials")
        self.trial_manifest = os.path.join(self.trials, "trial_manifest.json")
        self.judgment = os.path.join(self.root, "judgment")
        self.results = os.path.join(self.root, "results")
        self.logs = os.path.join(self.root, "logs")
        self.smoke = os.path.join(self.root, "smoke")

    def ensure(self):
        for d in (self.root, self.source_batch, self.source_online,
                  self.trials, self.judgment, self.results, self.logs, self.smoke):
            os.makedirs(d, exist_ok=True)

    def batch_trajectory_path(self, model_label: str, k: int) -> str:
        return os.path.join(self.source_batch, model_label, f"trajectory-{k:02d}.json")

    def online_trajectory_path(self, model_label: str, k: int) -> str:
        return os.path.join(self.source_online, model_label, f"trajectory-{k:02d}.json")

    def online_steps_path(self, model_label: str, k: int) -> str:
        return os.path.join(self.source_online, model_label, f"trajectory-{k:02d}.steps.jsonl")

    def judgment_path(self, trial_id: str) -> str:
        return os.path.join(self.judgment, f"judgment-{trial_id}.json")
