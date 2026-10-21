"""Parse-compliance check for STATIC_SELFPRED_v1.0 (open-weight model gate).

Sends every draft prompt N times per reasoning configuration and classifies
each response with the pilot parsers. No analysis of answer content; the only
question is whether the model returns parseable answers.

Rule fixed before any call (written to manifest.json at start):
  A configuration FAILS if its non-valid rate (invalid + decline +
  prefix_leak + truncated + transport_error + tool_use) is >= 40% on the
  dice_self cell (the cell where Qwen was 50% invalid in the v3.1 pilot) or
  >= 40% across all cells.
  If every Qwen configuration fails, the open-weight model switches to
  OSS-120, which then gets the same check.

Tools: requests send no `tools` or `tool_choice`. Every response is checked
for `message.tool_calls`, `finish_reason == "tool_calls"` and literal
`<tool_call>` text; any of these classifies the response as tool_use.

Usage:
    python -m spar_dynamic.static_selfpred.parse_check qwen
    python -m spar_dynamic.static_selfpred.parse_check oss120
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import csv
import datetime as dt
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from spar_dynamic.dice_pilot import parsers as dice_parsers
from spar_dynamic.favorite_animal import parsers as animal_parsers
from spar_dynamic.static_selfpred import prompts
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

N_PER_PROMPT = 5
FAIL_THRESHOLD = 0.40
COST_CAP_USD = 5.00
MAX_WORKERS = 8
MAX_RETRIES = 3

# label -> request settings. Temperature 0 throughout.
CONFIGS: Dict[str, List[Dict[str, Any]]] = {
    # SiliconFlow, not the pilots' DeepInfra: on 2026-10-20 DeepInfra ignored
    # reasoning.enabled=false (and effort="none", chat_template_kwargs) and
    # still produced ~1,200 reasoning tokens, while SiliconFlow returned 0.
    # Both configs use the same provider. effort="high" there spent ~16k
    # reasoning tokens with max_tokens=32768.
    "qwen": [
        dict(config="R_off", slug="qwen/qwen3-32b", provider="SiliconFlow",
             max_tokens=32768, temperature=0.0, reasoning={"enabled": False},
             price=(0.14e-6, 0.57e-6)),
        dict(config="R_high", slug="qwen/qwen3-32b", provider="SiliconFlow",
             max_tokens=32768, temperature=0.0, reasoning={"effort": "high"},
             price=(0.14e-6, 0.57e-6)),
    ],
    # Fallback. GPT-OSS cannot disable reasoning; "low" matches the pilots.
    "oss120": [
        dict(config="R_low", slug="openai/gpt-oss-120b", provider="DeepInfra",
             max_tokens=16384, temperature=0.0, reasoning={"effort": "low"},
             price=(0.037e-6, 0.17e-6)),
    ],
}

_TOOL_TEXT_RE = re.compile(r"<\s*/?\s*tool_call", re.I)


def build_prompt_list(supplied_name: str) -> List[Dict[str, Any]]:
    """(cell, position, prompt, parser kind) for every non-object prompt."""
    items = []
    for pos in prompts.ANIMAL_POSITIONS:
        items.append(dict(cell="animal_self", position=pos, prompt=prompts.animal_self(pos), kind="letter"))
        items.append(dict(cell="animal_generic", position=pos, prompt=prompts.animal_generic(pos), kind="letter"))
        items.append(dict(cell="animal_neutral", position=pos, prompt=prompts.animal_neutral(pos), kind="letter"))
        items.append(dict(cell="animal_supplied", position=pos,
                          prompt=prompts.animal_supplied(supplied_name, pos), kind="letter"))
    items.append(dict(cell="animal_generic_name", position="", prompt=prompts.ANIMAL_GENERIC_NAME, kind="animal"))
    for pos in prompts.DICE_ORDINALS:
        items.append(dict(cell="dice_self", position=pos, prompt=prompts.dice_self(pos), kind="int"))
        items.append(dict(cell="dice_generic", position=pos, prompt=prompts.dice_generic(pos), kind="int"))
    items.append(dict(cell="dice_single_roll", position="", prompt=prompts.DICE_SINGLE_ROLL, kind="int"))
    items.append(dict(cell="dice_object", position="", prompt=prompts.DICE_OBJECT, kind="seq"))
    return items


def classify(kind: str, text: str) -> Dict[str, Any]:
    if kind == "letter":
        p = animal_parsers.parse_phase2a(text)
        return dict(category=p.category, value=p.letter, reason=p.reason)
    if kind == "int":
        p = dice_parsers.parse_phase2(text)
        return dict(category=p.category, value=p.value, reason=p.reason)
    if kind == "animal":
        p = animal_parsers.parse_animal(text)
        return dict(category="valid" if p.valid else "invalid", value=p.scoring_string, reason=p.reason)
    if kind == "seq":
        p = dice_parsers.parse_phase1(text)
        return dict(category="valid" if p.valid else "invalid",
                    value=" ".join(map(str, p.values)) if p.valid else None, reason=p.reason)
    raise ValueError(kind)


def call(client: OpenAI, cfg: Dict[str, Any], prompt_text: str) -> Dict[str, Any]:
    kwargs = dict(
        model=cfg["slug"],
        messages=[{"role": "user", "content": prompt_text}],
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        extra_body={"reasoning": cfg["reasoning"],
                    "provider": {"order": [cfg["provider"]], "allow_fallbacks": False}},
    )
    last_err = ""
    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.time()
        try:
            r = client.chat.completions.create(**kwargs)
        except Exception as e:
            last_err = str(e)[:400]
            time.sleep(2 ** attempt)
            continue
        latency_ms = int(1000 * (time.time() - t0))
        if not r.choices:
            last_err = "no_choices"
            time.sleep(2 ** attempt)
            continue
        ch = r.choices[0]
        msg = ch.message
        reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
        usage = r.usage
        pt = getattr(usage, "prompt_tokens", 0) or 0
        ct = getattr(usage, "completion_tokens", 0) or 0
        details = getattr(usage, "completion_tokens_details", None)
        rt = (getattr(details, "reasoning_tokens", 0) or 0) if details else 0
        return dict(
            ok=True, attempts=attempt, error="", text=msg.content or "",
            finish_reason=ch.finish_reason or "",
            tool_calls=bool(getattr(msg, "tool_calls", None)),
            reasoning=reasoning if isinstance(reasoning, str) else (json.dumps(reasoning) if reasoning else None),
            provider=getattr(r, "provider", "") or "", served_model=r.model or "",
            generation_id=r.id or "", prompt_tokens=pt, completion_tokens=ct,
            reasoning_tokens=rt, latency_ms=latency_ms,
            cost_usd=pt * cfg["price"][0] + ct * cfg["price"][1],
        )
    return dict(ok=False, attempts=MAX_RETRIES, error=last_err, text="", finish_reason="error",
                tool_calls=False, reasoning=None, provider="", served_model="", generation_id="",
                prompt_tokens=0, completion_tokens=0, reasoning_tokens=0, latency_ms=0, cost_usd=0.0)


def response_category(kind: str, res: Dict[str, Any]) -> Dict[str, Any]:
    if not res["ok"]:
        return dict(category="transport_error", value=None, reason=res["error"])
    if res["tool_calls"] or res["finish_reason"] == "tool_calls" or _TOOL_TEXT_RE.search(res["text"]):
        return dict(category="tool_use", value=None, reason="tool call in response")
    if res["finish_reason"] == "length":
        return dict(category="truncated", value=None, reason="finish_reason=length")
    return classify(kind, res["text"])


class Runner:
    def __init__(self, client: OpenAI, run_dir: str):
        self.client = client
        self.run_dir = run_dir
        self.lock = threading.Lock()
        self.spent = 0.0
        self.rows: List[Dict[str, Any]] = []

    def one(self, cfg, item, rep) -> Dict[str, Any]:
        with self.lock:
            if self.spent >= COST_CAP_USD:
                raise RuntimeError(f"cost cap ${COST_CAP_USD} reached")
        res = call(self.client, cfg, item["prompt"])
        cat = response_category(item["kind"], res)
        row = dict(model_label=cfg["label"], config=cfg["config"], cell=item["cell"],
                   position=item["position"], replicate=rep, kind=item["kind"],
                   category=cat["category"], value=cat["value"], reason=cat["reason"],
                   think_tag_in_content="<think" in res["text"].lower(),
                   prompt=item["prompt"], **res)
        with self.lock:
            self.spent += res["cost_usd"]
            self.rows.append(row)
            with open(os.path.join(self.run_dir, "raw_attempts.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        return row

    def batch(self, jobs):
        with cf.ThreadPoolExecutor(MAX_WORKERS) as ex:
            return [f.result() for f in [ex.submit(self.one, *j) for j in jobs]]


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        by[(r["model_label"], r["config"], r["cell"])][r["category"]] += 1
        by[(r["model_label"], r["config"], "ALL")][r["category"]] += 1
    out = {}
    for key, c in sorted(by.items()):
        n = sum(c.values())
        out["|".join(key)] = dict(n=n, counts=dict(c), nonvalid_rate=round(1 - c["valid"] / n, 3))
    return out


def verdicts(summary: Dict[str, Any], label: str) -> Dict[str, Dict[str, Any]]:
    res = {}
    for cfg in CONFIGS[label]:
        k = f"{label}|{cfg['config']}"
        dice = summary.get(f"{k}|dice_self", {}).get("nonvalid_rate", 1.0)
        overall = summary.get(f"{k}|ALL", {}).get("nonvalid_rate", 1.0)
        res[cfg["config"]] = dict(dice_self_nonvalid=dice, overall_nonvalid=overall,
                                  fails=dice >= FAIL_THRESHOLD or overall >= FAIL_THRESHOLD)
    return res


def run(label: str) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set (load .env first)")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = str(repo_paths.legacy(os.path.join("data", "spar_dynamic", "static_selfpred", f"parsecheck-{label}-{stamp}")))
    os.makedirs(run_dir)
    cfgs = [dict(c, label=label) for c in CONFIGS[label]]
    manifest = dict(
        spec="STATIC_SELFPRED_v1.0 parse check", started_utc=stamp, model=label,
        configs=cfgs, n_per_prompt=N_PER_PROMPT, fail_threshold=FAIL_THRESHOLD,
        rule=__doc__.split("Rule fixed before any call (written to manifest.json at start):")[1]
                    .split("Tools:")[0].strip(),
        tools="no tools/tool_choice sent; responses checked for tool calls",
        cost_cap_usd=COST_CAP_USD,
    )
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=600.0)
    runner = Runner(client, run_dir)

    # Object level first: the supplied-answer name is that config's modal animal.
    obj_item = dict(cell="animal_object", position="", prompt=prompts.ANIMAL_OBJECT, kind="animal")
    names = {}
    for cfg in cfgs:
        rows = runner.batch([(cfg, obj_item, rep) for rep in range(N_PER_PROMPT)])
        valid = [r["value"] for r in rows if r["category"] == "valid"]
        names[cfg["config"]] = collections.Counter(valid).most_common(1)[0][0] if valid else "octopus"

    jobs = [(cfg, item, rep)
            for cfg in cfgs
            for item in build_prompt_list(names[cfg["config"]])
            for rep in range(N_PER_PROMPT)]
    runner.batch(jobs)

    with open(os.path.join(run_dir, "prompts_frozen.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(prompts.render_all({f"{c}": n for c, n in names.items()}))
    summary = summarize(runner.rows)
    result = dict(supplied_names=names, spent_usd=round(runner.spent, 4),
                  verdicts=verdicts(summary, label), summary=summary)
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    fields = ["model_label", "config", "cell", "position", "replicate", "category", "value",
              "reason", "finish_reason", "reasoning_tokens", "completion_tokens", "think_tag_in_content",
              "tool_calls", "served_model", "provider", "text"]
    with open(os.path.join(run_dir, "responses.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(runner.rows, key=lambda r: (r["config"], r["cell"], str(r["position"]), r["replicate"])):
            w.writerow(r)
    print(json.dumps(dict(run_dir=run_dir, **{k: result[k] for k in ("supplied_names", "spent_usd", "verdicts")}), indent=2))
    return run_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=sorted(CONFIGS))
    run(ap.parse_args().model)
