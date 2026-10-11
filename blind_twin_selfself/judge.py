"""Game loading, judge prompt rendering, strict judge parser, frozen schedule, approval gate, resumable runner."""
from __future__ import annotations

import hashlib
import importlib
import json
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from spar_dynamic.phase2.client import (Accountant, BudgetExceeded, CallLog, OpenRouterTransport,
                                        TransientError, _extract, git_state, utc_now)

from . import config as C

PARSER_VERSION = "btexp1_v1_json"


# ---------------------------------------------------------------------------
# Games (frozen Experiment 1 logs) and rendering
# ---------------------------------------------------------------------------

def load_games() -> List[Dict[str, Any]]:
    """Complete self-self games from conditions 00 and 11, both types, in a fixed order; adds game_type and gid."""
    out = []
    for gt in C.GAME_TYPES:
        rows = [json.loads(l) for l in (C.REPO / C.SOURCES[gt]["games"]).read_text().splitlines() if l.strip()]
        gs = sorted((g for g in rows if g["status"] == "complete" and g["condition"] in C.SOURCE_CONDITIONS
                     and g["p1_model"] == g["p2_model"]),
                    key=lambda g: (g["p1_model"], g["condition"], g["game_id"]))
        for g in gs:
            told = g["condition"] == "11"
            assert len(g["rounds"]) == C.N_ROUNDS and g["p1_informed"] is told and g["p2_informed"] is told
            out.append({**g, "game_type": gt, "gid": f"{gt}:{g['game_id']}"})
    return out


def games_hash(games) -> str:
    return hashlib.sha256(json.dumps([[g["gid"], g["p1_model"], g["p2_model"], g["rounds"]] for g in games]).encode()).hexdigest()


def history_text(gt: str, rows) -> str:
    return importlib.import_module(f"{C.SOURCES[gt]['pkg']}.game").history_text(rows)


def labels(cond: str, p1: str, p2: str) -> Optional[Tuple[str, str]]:
    if cond == "TRUE":
        return p1, p2
    if cond == "FALSE":
        return C.FALSE_LABEL[p1], C.FALSE_LABEL[p2]
    return None


def judge_prompt(judge: str, g: Dict[str, Any], t: int, cond: str) -> str:
    gt = g["game_type"]
    lab = labels(cond, g["p1_model"], g["p2_model"])
    ident = C.IDENTITY_ANONYMOUS if lab is None else C.IDENTITY_KNOWN.format(P1=C.MODELS[lab[0]]["name"], P2=C.MODELS[lab[1]]["name"])
    rows = g["rounds"][: t - 1]
    assert len(rows) == t - 1
    return C.JUDGE_TEMPLATE.format(RULES=C.RULES[gt], JUDGE_NAME=C.MODELS[judge]["name"], IDENTITY_SENTENCE=ident,
                                   INFO_SENTENCE=C.INFO[g["condition"]],
                                   PUBLIC_HISTORY=history_text(gt, rows), T=t,
                                   EXAMPLE=C.EXAMPLE[gt].format(), VALUES=C.VALUES[gt])


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S | re.I)


def parse_judge(text: Optional[str], gt: str, finish_reason: str = "") -> Tuple[Optional[Dict[str, str]], str]:
    """Bare JSON object with exactly keys player_1, player_2 and legal moves (case-insensitive), optionally alone in one
    code fence. Anything else yields no prediction (as Blind Twin v2's judge parser)."""
    if text is None or not text.strip():
        return None, "empty"
    if (finish_reason or "").lower() == "length":
        return None, "truncated_length"
    s = text.strip()
    wrapped = False
    m = _FENCE.match(s)
    if m:
        s, wrapped = m.group(1).strip(), True
    try:
        obj = json.loads(s)
    except Exception:
        return None, "not_json"
    if not isinstance(obj, dict) or set(obj) != {"player_1", "player_2"}:
        return None, "wrong_keys"
    out = {}
    for k in ("player_1", "player_2"):
        v = obj[k]
        if not isinstance(v, str) or v.strip().upper() not in C.MOVES[gt]:
            return None, "bad_value"
        out[k] = v.strip().upper()
    return out, "ok_wrapped" if wrapped else "ok"


# ---------------------------------------------------------------------------
# Frozen schedule
# ---------------------------------------------------------------------------

def schedule(games) -> List[Dict[str, Any]]:
    items = [{"slot_id": f"judge:{j}:{g['gid']}:r{t:02d}:{c}", "judge": j, "gid": g["gid"], "round": t, "condition": c}
             for g in games for t in range(1, C.N_ROUNDS + 1) for j in C.JUDGES for c in C.CONDITIONS]
    random.Random(C.derive_seed("judge_schedule")).shuffle(items)
    return items


def schedule_hash(s) -> str:
    return hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()


def approved(rd: Path) -> bool:
    p = rd / "APPROVAL.md"
    return p.exists() and any(l.strip() == "LIVE RUN APPROVED BY CHRIS: yes" for l in p.read_text().splitlines())


def progress(rd: Path, msg: str) -> None:
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(rd / "PROGRESS.md", "a") as f:
        f.write(line)
    print(line, end="", flush=True)


# ---------------------------------------------------------------------------
# Transport and runner
# ---------------------------------------------------------------------------

class FakeTransport:
    """Offline judge: predicts from the prompt deterministically, sometimes malformed, sometimes label-sensitive."""
    name = "fake"

    def __init__(self, malformed_rate: float = 0.0):
        self.n, self.lock, self.malformed_rate = 0, threading.Lock(), malformed_rate

    def send(self, body):
        text = body["messages"][-1]["content"]
        with self.lock:
            self.n += 1
            n = self.n
        rng = random.Random(C.derive_seed("fake", text))
        moves = C.MOVES["rps"] if "ROCK" in text.split("\n")[0] else C.MOVES["mp"]
        if rng.random() < self.malformed_rate:
            out = "I think Player 1 will play " + moves[0]
        else:
            out = json.dumps({"player_1": rng.choice(moves).lower(), "player_2": rng.choice(moves)})
            if rng.random() < 0.2:
                out = "```json\n" + out + "\n```"
        return {"id": f"fake-{n}", "model": body["model"], "provider": "Fake", "_http_status": 200,
                "choices": [{"message": {"content": out}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(text) // 4, "completion_tokens": 12, "cost": 0.0}}


def request_body(judge: str, prompt: str) -> Dict[str, Any]:
    m = C.MODELS[judge]
    return {"model": m["slug"], "messages": [{"role": "user", "content": prompt}], "reasoning": dict(C.REASONING),
            "max_tokens": C.MAX_TOKENS, "provider": {"order": [m["provider"]], "allow_fallbacks": False},
            "usage": {"include": True}}


def snapshot_prices(snap: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    out = {}
    for m in C.MODELS.values():
        ep = [e for e in snap["endpoints"][m["slug"]] if e["tag"] == m["provider"]]
        assert len(ep) == 1, f"pinned endpoint {m['provider']} not unique for {m['slug']}"
        out[m["slug"]] = {"prompt": float(ep[0]["pricing"]["prompt"]), "completion": float(ep[0]["pricing"]["completion"])}
    return out


class Runner:
    def __init__(self, rd: Path, live: bool, transport=None):
        self.rd = rd
        rd.mkdir(parents=True, exist_ok=True)
        if live and not approved(rd):
            raise SystemExit("live run requested but APPROVAL.md lacks explicit approval; no network calls made")
        if live:
            import spar_dynamic.phase2.config as P2
            P2.REQUEST_TIMEOUT_S = C.REQUEST_TIMEOUT_S          # process-local; the shared client reads it per call
        self.transport = transport or (OpenRouterTransport() if live else FakeTransport())
        prices = (snapshot_prices(json.loads((rd / "endpoint_and_price_snapshots.json").read_text())) if live
                  else {m["slug"]: {"prompt": 1e-5, "completion": 5e-5} for m in C.MODELS.values()})
        self.log = CallLog(rd / "calls.jsonl")
        self.done = self.log.done_ids()
        self.lock = threading.Lock()
        spent = sum(float(r.get("cost_usd") or 0) for r in self.done.values())
        self.acct = Accountant(C.BUDGET_CAP_USD, prices, spent=spent)
        self.ctx = {"protocol": C.PROTOCOL, "code_hash": C.code_hash(), "code": git_state(), "parser_version": PARSER_VERSION,
                    "transport": self.transport.name}
        self.stop = threading.Event()
        self.n_new = 0

    def call(self, item: Dict[str, Any], g: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self.lock:
            prev = self.done.get(item["slot_id"])
        if prev is not None and prev["status"] != "transport_failed":
            return prev
        if self.stop.is_set():
            return None
        prompt = judge_prompt(item["judge"], g, item["round"], item["condition"])
        body = request_body(item["judge"], prompt)
        try:
            reserved = self.acct.reserve(SimpleNamespace(params=body, messages=body["messages"]))
        except BudgetExceeded as e:
            self.stop.set(); progress(self.rd, f"BUDGET STOP (no new dispatches): {e}"); return None
        t0, attempts, obj = time.monotonic(), [], None
        for i in range(1 + C.MAX_TRANSIENT_RETRIES):
            disp = utc_now()
            try:
                obj = self.transport.send(body); attempts.append({"attempt": i, "dispatch_utc": disp, "ok": True}); break
            except TransientError as e:
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": False, "error": str(e)[:600]})
                if i < C.MAX_TRANSIENT_RETRIES:
                    time.sleep([10, 30, 90][i])
        rec = {**item, "kind": "judge", "model": item["judge"], "game_type": g["game_type"], "p1_model": g["p1_model"],
               "p2_model": g["p2_model"], "request": body, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
               "completed_utc": utc_now(), "elapsed_s": round(time.monotonic() - t0, 3), "attempts": attempts, **self.ctx}
        if obj is None or obj.get("_nontransient"):
            rec["status"] = "transport_failed" if obj is None else "http_error"
            if obj is not None:
                rec["http_status"], rec["error_body"] = obj["_http_status"], obj["_error_body"]
            rec["cost_usd"] = 0.0
            self.acct.settle(reserved, 0.0)
        else:
            ex = _extract(obj)
            cost = ex["usage"].get("cost")
            if cost is None:
                pr = self.acct.prices[body["model"]]
                cost = (ex["usage"].get("prompt_tokens") or 0) * pr["prompt"] + (ex["usage"].get("completion_tokens") or 0) * pr["completion"]
            self.acct.settle(reserved, float(cost))
            pred, why = parse_judge(ex["text"], g["game_type"], ex["finish_reason"] or "")
            rec.update(status="completed", cost_usd=float(cost), response=ex, returned_provider=ex.get("provider"),
                       parse={"valid": pred is not None, "prediction": pred, "reason": why})
        self.log.append(rec)
        with self.lock:
            self.done[item["slot_id"]] = rec
            self.n_new += 1
            n = self.n_new
        if n % 500 == 0:
            progress(self.rd, f"  {len(self.done)} judge calls recorded; spent ${self.acct.spent:.2f}")
        return rec

    def run(self, sched, games) -> None:
        by = {g["gid"]: g for g in games}
        progress(self.rd, f"judge calls: {len(sched)} scheduled, {len(self.done)} already recorded, {C.CONCURRENCY} concurrent "
                          f"(spent ${self.acct.spent:.2f}, cap ${C.BUDGET_CAP_USD:.0f})")
        with ThreadPoolExecutor(max_workers=C.CONCURRENCY) as pool:
            list(pool.map(lambda it: self.call(it, by[it["gid"]]), sched))
