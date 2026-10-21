"""Main data collection for STATIC_SELFPRED_v1.0.

Four model configurations run as independent pipelines:
    astra  R_min   (pilot settings: OpenAI pin, effort=minimal, no temperature)
    fable  R_min   (pilot settings: Anthropic pin, effort=minimal, no temperature)
    qwen   R_off   (SiliconFlow, temperature 0, reasoning disabled)
    qwen   R_high  (SiliconFlow, temperature 0, effort=high)

Each pipeline runs phase A (animal and dice object level, 100 calls each),
fixes its supplied-answer name as the modal valid animal from phase A, then
runs phase B (every other cell) in a seeded random order. Every call is a
fresh single-turn request; no tools are sent.

Resumable: `--resume <run_dir>` skips trial_ids already logged with any
category other than transport_error.

Usage:
    python -m spar_dynamic.static_selfpred.main_run
    python -m spar_dynamic.static_selfpred.main_run --resume data/spar_dynamic/static_selfpred/main-<stamp>
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import json
import os
import random
import subprocess
import threading
import time
from typing import Any, Dict, List

from openai import OpenAI

from spar_dynamic.dice_pilot_v41.config import MODELS_BY_LABEL as _V41
from spar_dynamic.static_selfpred import config, prompts
from spar_dynamic.static_selfpred.parse_check import (
    _TOOL_TEXT_RE, build_prompt_list, classify,
)

SPEC = "STATIC_SELFPRED_v1.0"
COST_CAP_USD = 25.00
MAX_RETRIES = 6
CONCURRENCY = {"astra|R_min": 6, "fable|R_min": 6, "qwen|R_off": 8, "qwen|R_high": 12}


# Fallback (prompt, completion) $/token, used only if OpenRouter omits usage.cost.
# Highest listed endpoint price for the pinned provider, so the cap errs safe.
_FALLBACK_PRICE = {"astra": (6e-5, 3e-4), "fable": (1e-5, 5e-5)}


def _pilot_cfg(label: str) -> Dict[str, Any]:
    m = _V41[label]
    return dict(label=label, config=m.reasoning_config_label, slug=m.slug,
                provider=m.preferred_provider, max_tokens=m.max_tokens,
                temperature=None, reasoning={"effort": m.reasoning_effort_requested},
                price=_FALLBACK_PRICE[label])


MODEL_CONFIGS: List[Dict[str, Any]] = (
    [_pilot_cfg(m.label) for m in config.MODELS]
    + [dict(c, label="qwen") for c in config.QWEN_CONFIGS]
)


def prompts_sha256() -> str:
    return hashlib.sha256(prompts.render_all().encode("utf-8")).hexdigest()


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def phase_a_items() -> List[Dict[str, Any]]:
    return [dict(cell="animal_object", position="", prompt=prompts.ANIMAL_OBJECT, kind="animal"),
            dict(cell="dice_object", position="", prompt=prompts.DICE_OBJECT, kind="seq")]


def phase_b_items(supplied_name: str) -> List[Dict[str, Any]]:
    items = [i for i in build_prompt_list(supplied_name) if i["cell"] != "dice_object"]
    reps = {cell: n for cell, (_, n) in {**config.ANIMAL_CELLS, **config.DICE_CELLS}.items()}
    return [(i, reps[i["cell"]]) for i in items]


def trial_id(cfg, item, rep) -> str:
    return f"{cfg['label']}|{cfg['config']}|{item['cell']}|{item['position']}|rep{rep:03d}"


class Collector:
    def __init__(self, run_dir: str, client: OpenAI):
        self.run_dir = run_dir
        self.client = client
        self.lock = threading.Lock()
        self.raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
        self.rows: Dict[str, Dict[str, Any]] = {}
        self.spent = 0.0
        self.done_this_session = 0
        self.stop = threading.Event()
        if os.path.exists(self.raw_path):
            for line in open(self.raw_path, encoding="utf-8"):
                r = json.loads(line)
                self.spent += r.get("cost_usd", 0.0)
                if r["category"] != "transport_error":
                    self.rows[r["trial_id"]] = r

    def log(self, msg: str):
        line = f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}"
        with self.lock:
            with open(os.path.join(self.run_dir, "progress.log"), "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def request(self, cfg, prompt_text) -> Dict[str, Any]:
        extra = {"reasoning": cfg["reasoning"],
                 "provider": {"order": [cfg["provider"]], "allow_fallbacks": False}}
        kwargs = dict(model=cfg["slug"], messages=[{"role": "user", "content": prompt_text}],
                      max_tokens=cfg["max_tokens"], extra_body=extra)
        if cfg["temperature"] is not None:
            kwargs["temperature"] = cfg["temperature"]
        err = ""
        for attempt in range(1, MAX_RETRIES + 1):
            t0 = time.time()
            try:
                r = self.client.chat.completions.create(**kwargs)
                if not r.choices:
                    raise RuntimeError("no_choices")
            except Exception as e:
                err = str(e)[:400]
                time.sleep(min(60, 2 ** attempt))
                continue
            ch, usage = r.choices[0], r.usage
            msg = ch.message
            reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
            details = getattr(usage, "completion_tokens_details", None)
            pt = getattr(usage, "prompt_tokens", 0) or 0
            ct = getattr(usage, "completion_tokens", 0) or 0
            cost = getattr(usage, "cost", None)
            cost_source = "openrouter"
            if cost is None:
                cost, cost_source = pt * cfg["price"][0] + ct * cfg["price"][1], "fallback_price"
            return dict(ok=True, attempts=attempt, error="", text=msg.content or "",
                        finish_reason=ch.finish_reason or "",
                        tool_calls=bool(getattr(msg, "tool_calls", None)),
                        reasoning=reasoning if isinstance(reasoning, str) else (json.dumps(reasoning) if reasoning else None),
                        provider=getattr(r, "provider", "") or "", served_model=r.model or "",
                        generation_id=r.id or "",
                        prompt_tokens=pt, completion_tokens=ct,
                        reasoning_tokens=(getattr(details, "reasoning_tokens", 0) or 0) if details else 0,
                        latency_ms=int(1000 * (time.time() - t0)),
                        cost_usd=float(cost), cost_source=cost_source)
        return dict(ok=False, attempts=MAX_RETRIES, error=err, text="", finish_reason="error",
                    tool_calls=False, reasoning=None, provider="", served_model="", generation_id="",
                    prompt_tokens=0, completion_tokens=0, reasoning_tokens=0, latency_ms=0, cost_usd=0.0,
                    cost_source="none")

    def one(self, cfg, item, rep):
        tid = trial_id(cfg, item, rep)
        if self.stop.is_set():
            return None
        res = self.request(cfg, item["prompt"])
        if not res["ok"]:
            cat = dict(category="transport_error", value=None, reason=res["error"])
        elif res["tool_calls"] or res["finish_reason"] == "tool_calls" or _TOOL_TEXT_RE.search(res["text"]):
            cat = dict(category="tool_use", value=None, reason="tool call in response")
        elif res["finish_reason"] == "length":
            cat = dict(category="truncated", value=None, reason="finish_reason=length")
        else:
            cat = classify(item["kind"], res["text"])
        row = dict(trial_id=tid, spec=SPEC, model_label=cfg["label"], config=cfg["config"],
                   cell=item["cell"], position=item["position"], replicate=rep, kind=item["kind"],
                   requested_model=cfg["slug"], requested_provider=cfg["provider"],
                   requested_reasoning=cfg["reasoning"], requested_temperature=cfg["temperature"],
                   requested_max_tokens=cfg["max_tokens"],
                   prompt_sha256=hashlib.sha256(item["prompt"].encode()).hexdigest(),
                   prompt=item["prompt"], timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
                   **cat, **res)
        with self.lock:
            self.spent += res["cost_usd"]
            if row["category"] != "transport_error":
                self.rows[tid] = row
            self.done_this_session += 1
            with open(self.raw_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            if self.spent >= COST_CAP_USD:
                self.stop.set()
        if self.done_this_session % 100 == 0:
            self.log(f"calls this session={self.done_this_session} logged={len(self.rows)} spent=${self.spent:.2f}")
        return row

    def pipeline(self, cfg, seed: int):
        key = f"{cfg['label']}|{cfg['config']}"
        workers = CONCURRENCY[key]
        n_obj = config.ANIMAL_CELLS["animal_object"][1]
        with cf.ThreadPoolExecutor(workers) as ex:
            jobs = [(cfg, item, rep) for item in phase_a_items() for rep in range(n_obj)]
            list(ex.map(lambda j: self.one(*j), [j for j in jobs if trial_id(*j) not in self.rows]))
            animals = [r["value"] for r in self.rows.values()
                       if r["model_label"] == cfg["label"] and r["config"] == cfg["config"]
                       and r["cell"] == "animal_object" and r["category"] == "valid"]
            name = collections.Counter(animals).most_common(1)[0][0] if animals else "octopus"
            self.log(f"{key}: phase A done; supplied name = {name!r} (from {len(animals)} valid)")
            jobs = [(cfg, item, rep) for item, n in phase_b_items(name) for rep in range(n)]
            random.Random(f"{seed}|{key}").shuffle(jobs)
            list(ex.map(lambda j: self.one(*j), [j for j in jobs if trial_id(*j) not in self.rows]))
        self.log(f"{key}: phase B done")
        return key, name


def write_outputs(col: Collector, names: Dict[str, str]):
    rows = sorted(col.rows.values(), key=lambda r: r["trial_id"])
    counts = collections.defaultdict(collections.Counter)
    for r in rows:
        counts[f"{r['model_label']}|{r['config']}|{r['cell']}"][r["category"]] += 1
    planned = config.calls_per_model() * len(MODEL_CONFIGS)
    summary = dict(spec=SPEC, logged=len(rows), planned=planned, spent_usd=round(col.spent, 4),
                   cost_cap_hit=col.stop.is_set(), supplied_names=names,
                   category_counts={k: dict(v) for k, v in sorted(counts.items())})
    with open(os.path.join(col.run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    fields = ["trial_id", "model_label", "config", "cell", "position", "replicate", "category", "value",
              "reason", "finish_reason", "reasoning_tokens", "completion_tokens", "tool_calls",
              "provider", "served_model", "cost_usd", "text"]
    with open(os.path.join(col.run_dir, "responses.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", default=None)
    args = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set (load .env first)")
    prompts.assert_consistency()

    if args.resume:
        run_dir = args.resume
        manifest = json.load(open(os.path.join(run_dir, "manifest.json"), encoding="utf-8"))
        if manifest["prompts_sha256"] != prompts_sha256():
            raise SystemExit("prompts changed since this run started; refusing to resume")
    else:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = os.path.join("data", "spar_dynamic", "static_selfpred", f"main-{stamp}")
        os.makedirs(run_dir)
        manifest = dict(spec=SPEC, started_utc=stamp, git_head=git_head(),
                        prompts_sha256=prompts_sha256(), order_seed=config.ORDER_SEED,
                        model_configs=MODEL_CONFIGS, concurrency=CONCURRENCY,
                        cells={**config.ANIMAL_CELLS, **config.DICE_CELLS},
                        planned_calls=config.calls_per_model() * len(MODEL_CONFIGS),
                        cost_cap_usd=COST_CAP_USD, tools="none sent; responses checked for tool calls")
        with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=list)
        with open(os.path.join(run_dir, "prompts_frozen.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(prompts.render_all())

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=900.0, max_retries=0)
    col = Collector(run_dir, client)
    col.log(f"start: run_dir={run_dir} already logged={len(col.rows)} spent=${col.spent:.2f}")
    names = {}
    with cf.ThreadPoolExecutor(len(MODEL_CONFIGS)) as ex:
        for fut in cf.as_completed([ex.submit(col.pipeline, cfg, config.ORDER_SEED) for cfg in MODEL_CONFIGS]):
            k, name = fut.result()
            names[k] = name
    summary = write_outputs(col, names)
    col.log(f"finished: logged={summary['logged']}/{summary['planned']} spent=${summary['spent_usd']}")
    print(json.dumps({k: summary[k] for k in ("logged", "planned", "spent_usd", "cost_cap_hit", "supplied_names")}, indent=2))
    print("run_dir:", run_dir)


if __name__ == "__main__":
    main()
