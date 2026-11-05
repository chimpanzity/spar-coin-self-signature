"""The 40 author calls (handoff section 2): ten blocks, each one fresh request per cell, order shuffled within blocks by a recorded
seed; dispatched one at a time in schedule order. Resumable by slot id (provider response ids recorded); a completed slot is
never reissued; no rerolls for any reason. Transport, budget accounting, the source parser and the approval gate are the repo's /
folder 21's, imported unchanged.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

from blind_coder_player_choices import config as C
from blind_coder_player_choices import prompts as P
from blind_twin_forecast_prediction.authors import APPROVAL_LINE, approved, extract_source, snapshot_prices  # noqa: F401 (re-exported)
from spar_dynamic.phase2.client import Accountant, BudgetExceeded, CallLog, TransientError, _extract, git_state, utc_now

PARSER_VERSION = "btfp_v1_source_or_one_fence (folder 21 parser, unchanged)"


def slot_id(block: int, author: str, target: str) -> str:
    return f"b{block:02d}:{author}->{target}"


def schedule() -> List[dict]:
    rng = random.Random(C.SCHEDULE_SEED)
    out = []
    for b in range(1, C.N_BLOCKS + 1):
        cells = list(C.CELLS)
        rng.shuffle(cells)
        out += [dict(order=len(out) + 1, block=b, author=a, target=j, slot_id=slot_id(b, a, j)) for a, j in cells]
    return out


class FakeAuthor:
    """Offline stand-in: a small valid predictor that depends on (author, target, block); fable's replies are fenced."""
    name = "fake"

    def __init__(self):
        self.n = 0

    def send(self, body):
        self.n += 1
        author = next(a for a, m in C.MODELS.items() if m["slug"] == body["model"])
        target = next(j for j in C.TARGETS if body["messages"][0]["content"] == P.author_message(j))
        k = (self.n % 5) / 20
        stay = {"astra": 0.40, "fable": 0.55}[target] + (0.05 if author == target else -0.05) + k / 4
        src = ("def predict(history, seat):\n    if not history:\n        return 0.5\n"
               f"    last = history[-1][seat]\n    stay = {stay:.3f}\n    return stay if last == 'STAR' else 1 - stay\n")
        text = f"```python\n{src}```" if author == "fable" else src
        return {"id": f"fake-{self.n}", "model": body["model"], "provider": "Fake", "_http_status": 200,
                "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(body["messages"][0]["content"]) // 4, "completion_tokens": len(src) // 4, "cost": 0.0}}


def run_schedule(rd: Path, transport, prices: Dict[str, Dict[str, float]], plan_sha: str, log=print) -> Dict[str, dict]:
    (rd / "responses").mkdir(parents=True, exist_ok=True)
    calls = CallLog(rd / "responses" / "calls.jsonl")
    done = calls.done_ids()
    acct = Accountant(C.CAP_USD, prices, spent=sum(float(r.get("cost_usd") or 0) for r in done.values()))
    ctx = {"protocol": C.PROTOCOL, "plan_sha256": plan_sha, "parser_version": PARSER_VERSION, "code": git_state(), "transport": transport.name}
    for s in schedule():
        prev = done.get(s["slot_id"])
        if prev is not None and prev["status"] == "completed":
            continue
        body = P.request_body(s["author"], s["target"])
        try:
            reserved = acct.reserve(SimpleNamespace(params=body, messages=body["messages"]))
        except BudgetExceeded as e:
            log(f"BUDGET STOP before {s['slot_id']}: {e}")
            break
        t0, attempts, obj = time.monotonic(), [], None
        for i in range(1 + C.MAX_TRANSIENT_RETRIES):       # transport errors only; never a content reroll
            disp = utc_now()
            try:
                obj = transport.send(body)
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": True})
                break
            except TransientError as e:
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": False, "error": str(e)[:600]})
                if i < C.MAX_TRANSIENT_RETRIES:
                    time.sleep([10, 30, 90][i])
        rec = {**s, "request": body, "message_sha256": C.sha(body["messages"][0]["content"]), "reserved_usd": reserved,
               "completed_utc": utc_now(), "elapsed_s": round(time.monotonic() - t0, 3), "attempts": attempts, **ctx}
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
                       response_id=obj.get("id"), returned_model=ex.get("returned_model"), returned_provider=ex.get("provider"))
        calls.append(rec)
        done[s["slot_id"]] = rec
        log(f"[{s['order']:2d}/40] {s['slot_id']}: {rec['status']} ${rec['cost_usd']:.4f} (spent ${acct.spent:.3f} of ${C.CAP_USD:.0f}) "
            f"{rec.get('returned_model')} / {rec.get('returned_provider')} id {rec.get('response_id')}")
    return done


def program_name(s) -> str:
    return f"b{s['block']:02d}_{s['author']}_for_{s['target']}.py"


def freeze_programs(rd: Path) -> dict:
    """Fixed parser over every scheduled slot; write sources; hash; refuse to overwrite. Missing/unparseable slots recorded."""
    calls = CallLog(rd / "responses" / "calls.jsonl").done_ids()
    pd = rd / "programs"
    pd.mkdir(parents=True, exist_ok=True)
    man = {}
    for s in schedule():
        name = program_name(s)
        rec = calls.get(s["slot_id"])
        base = dict(slot_id=s["slot_id"], block=s["block"], author=s["author"], target=s["target"])
        if rec is None or rec["status"] != "completed":
            man[name] = dict(base, status="missing_response" if rec is None else rec["status"])
            continue
        src, why = extract_source(rec["response"]["text"])
        if src is None:
            man[name] = dict(base, status="unparseable", reason=why, finish_reason=rec["response"].get("finish_reason"))
            continue
        path = pd / name
        if path.exists() and path.read_text(encoding="utf-8").replace("\r\n", "\n") != src:
            raise SystemExit(f"{path} is frozen and differs from the parsed response; refusing")
        path.write_text(src, encoding="utf-8", newline="\n")
        man[name] = dict(base, status="frozen", parse=why, finish_reason=rec["response"].get("finish_reason"), sha256=C.sha(src),
                         response_sha256=C.sha(rec["response"]["text"]), response_id=rec.get("response_id"))
    out = pd / "sources_sha256.json"
    if out.exists() and json.loads(out.read_text(encoding="utf-8")) != man:
        raise SystemExit("sources_sha256.json already frozen with different content; refusing")
    out.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8", newline="\n")
    return man
