"""Corpus tables and descriptors (Sections 4.4, 5.3)."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import config as C
from .parse import GEN_PARSER_VERSION, parse_generation


def load_calls(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    p = run_dir / "calls.jsonl"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    out[r["slot_id"]] = r      # last record wins (resume)
    return out


def sequence_rows(calls: Dict[str, Dict[str, Any]],
                  tasks: tuple = ("generation", "historical_generation")) -> List[Dict[str, Any]]:
    rows = []
    for sid, r in calls.items():
        if r["task"] not in tasks:
            continue
        m = r["meta"]
        # Always re-parse raw text with the CURRENT frozen parser (versioned);
        # the dispatch-time parse remains in calls.jsonl.
        parse = {}
        if r["status"] == "completed":
            gp = parse_generation(r["response"]["text"], r["response"].get("finish_reason") or "")
            parse = {"valid": gp.valid, "outcomes": gp.outcomes, "reason": gp.reason,
                     "repeated_list": gp.repeated_list}
        rows.append({
            "slot_id": sid, "parent_id": m["parent_id"], "split": m["split"], "source": m["source"],
            "prompt": m["prompt"], "temperature": m.get("temperature"), "idx": m["idx"],
            "time_block": m["time_block"], "smoke": m.get("smoke", False),
            "status": r["status"], "valid": bool(parse.get("valid")),
            "reason": parse.get("reason") if r["status"] == "completed" else r["status"],
            "outcomes": parse.get("outcomes") if parse.get("valid") else None,
            "repeated_list": parse.get("repeated_list"),
            "finish_reason": (r.get("response") or {}).get("finish_reason"),
            "completed_utc": r.get("completed_utc"),
            "cost_usd": r.get("cost_usd"),
            "parser_version": GEN_PARSER_VERSION,
            "dispatch_parse_valid": (r.get("parse") or {}).get("valid"),
        })
    rows.sort(key=lambda x: (x["split"], x["source"], x["prompt"], str(x["temperature"]), x["idx"]))
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})


# ---------------------------------------------------------------------------
# Descriptors
# ---------------------------------------------------------------------------

def runs(seq: str) -> List[int]:
    out, n = [], 1
    for a, b in zip(seq, seq[1:]):
        if a == b:
            n += 1
        else:
            out.append(n); n = 1
    out.append(n)
    return out


def describe(seq: str) -> Dict[str, Any]:
    r = runs(seq)
    return {
        "heads": seq.count("H"),
        "first_H": seq[0] == "H",
        "switches": sum(1 for a, b in zip(seq, seq[1:]) if a != b),
        "longest_run": max(r),
        "terminal_run": r[-1],
        "window8_heads": [seq[i:i + 8].count("H") for i in range(len(seq) - 7)],
    }


def ngram_freq(seqs: Iterable[str], n: int) -> Dict[str, float]:
    c: Counter = Counter()
    for s in seqs:
        for i in range(len(s) - n + 1):
            c[s[i:i + n]] += 1
    tot = sum(c.values()) or 1
    return {k: round(v / tot, 4) for k, v in sorted(c.items())}


def effective_count(items: List[str]) -> float:
    if not items:
        return 0.0
    c = Counter(items)
    n = len(items)
    return 1.0 / sum((v / n) ** 2 for v in c.values())


def cell_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cells: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        cells[(r["split"], r["source"], r["prompt"], r["temperature"])].append(r)
    out = []
    for (split, src, p, temp), rs in sorted(cells.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        seqs = [r["outcomes"] for r in rs if r["valid"]]
        reasons = Counter(r["reason"] for r in rs if not r["valid"])
        d = [describe(s) for s in seqs]
        n = len(seqs)
        mean = lambda k: round(sum(x[k] for x in d) / n, 3) if n else None
        prefixes = [s[: C.PREFIX_LEN] for s in seqs]
        out.append({
            "split": split, "source": src, "prompt": p, "temperature": temp,
            "attempted": len(rs), "valid": n, "valid_rate": round(n / len(rs), 3) if rs else None,
            "failure_reasons": dict(reasons),
            "mean_heads": mean("heads"), "first_H_rate": mean("first_H"),
            "mean_switches": mean("switches"), "switch_rate": round(mean("switches") / 19, 3) if n else None,
            "mean_longest_run": mean("longest_run"),
            "distinct_strings": len(set(seqs)), "max_string_freq": max(Counter(seqs).values()) if seqs else 0,
            "effective_strings": round(effective_count(seqs), 2),
            "distinct_prefix10": len(set(prefixes)), "max_prefix10_freq": max(Counter(prefixes).values()) if prefixes else 0,
            "effective_prefix10": round(effective_count(prefixes), 2),
            "top_strings": Counter(seqs).most_common(3),
            "bigrams": ngram_freq(seqs, 2), "trigrams": ngram_freq(seqs, 3),
            "window8_heads_hist": dict(sorted(Counter(h for x in d for h in x["window8_heads"]).items())),
        })
    return out


def valid_parents(rows: List[Dict[str, Any]], split: str) -> Dict[str, Dict[str, Any]]:
    return {r["parent_id"]: r for r in rows if r["split"] == split and r["valid"]}
