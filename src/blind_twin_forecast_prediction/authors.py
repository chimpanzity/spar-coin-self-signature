"""The four author calls (handoff sections 2-3): one isolated request per cell, one generation, resumable, never regenerated.

Transport is the repo's OpenRouter client (spar_dynamic.phase2.client), as in the archived Blind Twin runs: pinned provider,
fallbacks off, reasoning effort low (excluded from the response), temperature omitted, no tools, max_tokens 4000. Worst-case
cost (prompt estimate + max_tokens at the snapshot price) is reserved before each call against the $5 ceiling.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Optional, Tuple

from blind_twin_forecast_prediction import config as C
from blind_twin_forecast_prediction import prompts as P
from spar_dynamic.phase2.client import Accountant, BudgetExceeded, CallLog, TransientError, _extract, git_state, utc_now

PARSER_VERSION = "btfp_v1_source_or_one_fence"
APPROVAL_LINE = "LIVE RUN APPROVED BY CHRIS: yes"
_FENCE = re.compile(r"\A```[ \t]*(?:python|py|python3)?[ \t]*\r?\n(.*?)\r?\n?```\Z", re.S | re.I)


def extract_source(text: Optional[str]) -> Tuple[Optional[str], str]:
    """Bare source, or the content of exactly one code fence enclosing the whole (stripped) response. Nothing else."""
    if text is None or not text.strip():
        return None, "empty"
    s = text.strip()
    m = _FENCE.match(s)
    if m:
        inner = m.group(1)
        if "```" in inner:
            return None, "more_than_one_fence"
        return inner.strip("\n") + "\n", "one_fence_stripped"
    if "```" in s:
        return None, "fence_not_enclosing"
    return s + "\n", "bare"


def cell_id(author: str, target: str) -> str:
    return f"author:{author}:target:{target}"


def snapshot_prices(snap: dict) -> Dict[str, Dict[str, float]]:
    out = {}
    for m in C.MODELS.values():
        ep = [e for e in snap["endpoints"][m["slug"]] if e["tag"] == m["provider"]]
        assert len(ep) == 1, f"pinned endpoint {m['provider']} not unique for {m['slug']}"
        out[m["slug"]] = {"prompt": float(ep[0]["pricing"]["prompt"]), "completion": float(ep[0]["pricing"]["completion"])}
    return out


def approved(rd: Path, plan_sha: str) -> bool:
    p = rd / "APPROVAL.md"
    if not p.exists():
        return False
    text = p.read_text(encoding="utf-8")
    return any(l.strip() == APPROVAL_LINE for l in text.splitlines()) and plan_sha in text


class FakeAuthor:
    """Offline stand-in: returns a small, valid predictor per (author, target); some fenced, as real models might."""
    name = "fake"

    SOURCES = {
        ("astra", "astra"): "def predict(history):\n    if not history:\n        return (0.5, 0.5)\n    last = history[-1]\n"
                            "    return (0.7 if last['p1'] == 'STAR' else 0.3, 0.7 if last['p2'] == 'STAR' else 0.3)\n",
        ("astra", "fable"): "def predict(history):\n    if not history:\n        return (0.5, 0.5)\n    last = history[-1]\n"
                            "    return (0.65 if last['p1'] == 'STAR' else 0.35, 0.65 if last['p2'] == 'STAR' else 0.35)\n",
        ("fable", "astra"): "import math\n\ndef predict(history):\n    n = len(history)\n    s1 = sum(r['p1'] == 'STAR' for r in history)\n"
                            "    s2 = sum(r['p2'] == 'STAR' for r in history)\n    return ((s1 + 1) / (n + 2), (s2 + 1) / (n + 2))\n",
        ("fable", "fable"): "def predict(history):\n    if not history:\n        return (0.6, 0.4)\n    last = history[-1]\n"
                            "    flip = last['result'] == 'Mismatcher'\n    return (0.4 if flip else 0.6, 0.6 if flip else 0.4)\n",
    }

    def send(self, body):
        author = next(a for a, m in C.MODELS.items() if m["slug"] == body["model"])
        target = next(j for j in C.TARGETS if body["messages"][0]["content"] == P.author_message(j))
        src = self.SOURCES[(author, target)]
        text = f"```python\n{src}```" if author == "fable" else src
        return {"id": f"fake-{author}-{target}", "model": body["model"], "provider": "Fake", "_http_status": 200,
                "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(body["messages"][0]["content"]) // 4, "completion_tokens": len(src) // 4, "cost": 0.0}}


def run_cells(rd: Path, transport, prices: Dict[str, Dict[str, float]], plan_sha: str, log=print) -> Dict[str, dict]:
    """One request per cell in fixed order; resumes from responses/calls.jsonl; never regenerates a completed cell."""
    (rd / "responses").mkdir(parents=True, exist_ok=True)
    calls = CallLog(rd / "responses" / "calls.jsonl")
    done = calls.done_ids()
    spent = sum(float(r.get("cost_usd") or 0) for r in done.values())
    acct = Accountant(C.CAP_USD, prices, spent=spent)
    ctx = {"protocol": C.PROTOCOL, "plan_sha256": plan_sha, "parser_version": PARSER_VERSION, "code": git_state(),
           "transport": transport.name}
    for author, target in C.CELLS:
        cid = cell_id(author, target)
        prev = done.get(cid)
        if prev is not None and prev["status"] == "completed":
            log(f"{cid}: already recorded, not regenerated")
            continue
        body = P.request_body(author, target)
        try:
            reserved = acct.reserve(SimpleNamespace(params=body, messages=body["messages"]))
        except BudgetExceeded as e:
            log(f"BUDGET STOP before {cid}: {e}")
            break
        t0, attempts, obj = time.monotonic(), [], None
        for i in range(1 + C.MAX_TRANSIENT_RETRIES):
            disp = utc_now()
            try:
                obj = transport.send(body)
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": True})
                break
            except TransientError as e:
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": False, "error": str(e)[:600]})
                if i < C.MAX_TRANSIENT_RETRIES:
                    time.sleep([10, 30, 90][i])
        rec = {"slot_id": cid, "author": author, "target": target, "request": body, "message_sha256": C.sha(body["messages"][0]["content"]),
               "reserved_usd": reserved, "completed_utc": utc_now(), "elapsed_s": round(time.monotonic() - t0, 3), "attempts": attempts, **ctx}
        if obj is None or obj.get("_nontransient"):
            rec["status"] = "transport_failed" if obj is None else "http_error"
            if obj is not None:
                rec["http_status"], rec["error_body"] = obj["_http_status"], obj["_error_body"]
            rec["cost_usd"] = 0.0
            acct.settle(reserved, 0.0)
        else:
            ex = _extract(obj)
            cost = ex["usage"].get("cost")
            if cost is None:
                pr = prices[body["model"]]
                cost = (ex["usage"].get("prompt_tokens") or 0) * pr["prompt"] + (ex["usage"].get("completion_tokens") or 0) * pr["completion"]
            acct.settle(reserved, float(cost))
            rec.update(status="completed", cost_usd=float(cost), response=ex, raw_response={k: v for k, v in obj.items() if k != "_http_status"},
                       returned_model=ex.get("returned_model"), returned_provider=ex.get("provider"))
        calls.append(rec)
        done[cid] = rec
        log(f"{cid}: {rec['status']} ${rec['cost_usd']:.4f} (spent ${acct.spent:.4f} of ${C.CAP_USD:.2f}) "
            f"model {rec.get('returned_model')} provider {rec.get('returned_provider')}")
    return done


def freeze_programs(rd: Path) -> dict:
    """Extract each completed response with the fixed parser, write the four programs, hash them. Refuses to overwrite."""
    calls = CallLog(rd / "responses" / "calls.jsonl").done_ids()
    pd = rd / "programs"
    pd.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for author, target in C.CELLS:
        rec = calls.get(cell_id(author, target))
        name = C.PROGRAM[(author, target)]
        if rec is None or rec["status"] != "completed":
            manifest[name] = dict(status="missing_response")
            continue
        src, why = extract_source(rec["response"]["text"])
        finish = rec["response"].get("finish_reason")
        if src is None:
            manifest[name] = dict(status="unparseable", reason=why, finish_reason=finish)
            continue
        path = pd / name
        if path.exists() and path.read_text(encoding="utf-8") != src:
            raise SystemExit(f"{path} is frozen and differs from the parsed response; refusing")
        path.write_text(src, encoding="utf-8", newline="\n")
        manifest[name] = dict(status="frozen", parse=why, finish_reason=finish, sha256=C.sha(src), n_lines=src.count("\n"),
                              response_sha256=C.sha(rec["response"]["text"]))
    out = rd / "programs" / "sources_sha256.json"
    if out.exists() and json.loads(out.read_text(encoding="utf-8")) != manifest:
        raise SystemExit("sources_sha256.json already frozen with different content; refusing")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest
