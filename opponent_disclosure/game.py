"""Renderers, parser and game runner for the opponent-disclosure experiment."""
from __future__ import annotations

import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from spar_dynamic.phase2.client import (Accountant, BudgetExceeded, CallLog, OpenRouterTransport,
                                        TransientError, _extract, fetch_prices, git_state, utc_now)

from . import config as C

PARSER_VERSION = "od_v1_final_line_exact"

# ---------------------------------------------------------------------------
# Rendering (public history only)
# ---------------------------------------------------------------------------


def winner(m: str, mm: str) -> str:
    return "Matcher" if m == mm else "Mismatcher"


def history_text(rows: Sequence[Dict]) -> str:
    if not rows:
        return C.EMPTY_HISTORY
    out = [C.HISTORY_HEADER]
    for r in rows:
        out.append(f"{str(r['round']):<6}| {r['matcher']:<8}| {r['mismatcher']:<10}| {r['winner']}")
    return "\n".join(out)


def player_prompt(role: str, informed: bool, rows: Sequence[Dict], t: int) -> str:
    assert len(rows) == t - 1, "history must contain exactly the rounds before round t"
    for i, r in enumerate(rows, 1):
        assert r["round"] == i and set(r) == {"round", "matcher", "mismatcher", "winner"}, "public rows only"
    tpl = C.MATCHER_TEMPLATE if role == "matcher" else C.MISMATCHER_TEMPLATE
    return tpl.format(SHARED=C.SHARED, OPPONENT_IDENTITY_SENTENCE=C.INFORMED if informed else C.UNINFORMED,
                      PUBLIC_HISTORY=history_text(rows), T=t)


# ---------------------------------------------------------------------------
# Parsing: final non-empty line must be exactly STAR or TRIANGLE (whitespace/case only)
# ---------------------------------------------------------------------------

def parse_choice(text: Optional[str], finish_reason: str = "") -> Tuple[Optional[str], str]:
    if text is None or not text.strip():
        return None, "empty"
    if (finish_reason or "").lower() == "length":
        return None, "truncated_length"
    last = [l for l in text.strip().splitlines() if l.strip()][-1].strip().upper()
    if last in ("STAR", "TRIANGLE"):
        return last, "ok"
    return None, "final_line_not_exact_choice"


# ---------------------------------------------------------------------------
# Fake transport (offline)
# ---------------------------------------------------------------------------

class FakeTransport:
    name = "fake"

    def __init__(self, malformed_rate: float = 0.0):
        self.n, self.lock, self.malformed_rate = 0, threading.Lock(), malformed_rate

    def send(self, body: Dict[str, Any]) -> Dict[str, Any]:
        text = body["messages"][-1]["content"]
        with self.lock:
            self.n += 1
            n = self.n
        rng = random.Random(C.derive_seed("fake", text, n))
        if rng.random() < self.malformed_rate:
            out = "I think STAR."
        else:
            informed = C.INFORMED in text
            out = rng.choice(["STAR", "TRIANGLE"]) if not informed else rng.choice(["STAR", "STAR", "TRIANGLE", "Same model, so I mirror.\ntriangle"])
        return {"id": f"fake-{n}", "model": body["model"], "provider": "Fake", "_http_status": 200,
                "choices": [{"message": {"content": out}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(text) // 4, "completion_tokens": 3, "cost": 0.0}}


def request_body(prompt: str) -> Dict[str, Any]:
    return {"model": C.MODEL["slug"], "messages": [{"role": "user", "content": prompt}],
            "reasoning": dict(C.REASONING), "max_tokens": C.MAX_TOKENS,
            "provider": {"order": [C.MODEL["provider"]], "allow_fallbacks": False}, "usage": {"include": True}}


def progress(rd: Path, msg: str) -> None:
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(rd / "PROGRESS.md", "a") as f:
        f.write(line)
    print(line, end="", flush=True)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class Runner:
    def __init__(self, rd: Path, live: bool, log_name: str = "calls.jsonl"):
        self.rd = rd
        rd.mkdir(parents=True, exist_ok=True)
        self.transport = OpenRouterTransport() if live else FakeTransport()
        pp = rd / "pricing_snapshot.json"
        if live:
            if not pp.exists():
                pp.write_text(json.dumps({"fetched_utc": utc_now(), **fetch_prices([C.MODEL["slug"]])}, indent=1))
            prices = {k: v for k, v in json.loads(pp.read_text()).items() if k != "fetched_utc"}
        else:
            prices = {C.MODEL["slug"]: {"prompt": 1e-5, "completion": 5e-5}}
        self.log = CallLog(rd / log_name)
        spent = 0.0
        for nm in ("calls.jsonl", "smoke_calls.jsonl"):
            p = rd / nm
            if p.exists():
                spent += sum(float(json.loads(l).get("cost_usd") or 0) for l in p.read_text().splitlines() if l.strip())
        self.acct = Accountant(C.BUDGET_CAP_USD, prices, spent=spent)
        self.ctx = {"protocol": C.PROTOCOL, "code_hash": C.code_hash(), "code": git_state(), "parser_version": PARSER_VERSION,
                    "transport": self.transport.name, "seed": {"intent": "none", "status": "not transmitted (omitted by policy)"}}
        self.stop = threading.Event()

    def call(self, slot_id, prompt, meta, private) -> Optional[Dict[str, Any]]:
        done = self.log.done_ids()
        if slot_id in done and done[slot_id]["status"] != "transport_failed":
            return done[slot_id]
        if self.stop.is_set():
            return None
        body = request_body(prompt)
        try:
            reserved = self.acct.reserve(SimpleNamespace(params=body, messages=body["messages"]))
        except BudgetExceeded as e:
            self.stop.set(); progress(self.rd, f"BUDGET STOP: {e}"); return None
        queued, t0, attempts, obj = utc_now(), time.monotonic(), [], None
        for i in range(1 + C.MAX_TRANSIENT_RETRIES):
            disp = utc_now()
            try:
                obj = self.transport.send(body); attempts.append({"attempt": i, "dispatch_utc": disp, "ok": True}); break
            except TransientError as e:
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": False, "error": str(e)[:600]})
                if i < C.MAX_TRANSIENT_RETRIES:
                    time.sleep([10, 30, 90][i])
        rec = {"slot_id": slot_id, **meta, "private": private, "request": body, "queued_utc": queued,
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
            v, why = parse_choice(ex["text"], ex["finish_reason"] or "")
            rec.update(status="completed", cost_usd=float(cost), response=ex, returned_provider=ex.get("provider"),
                       returned_model=ex.get("returned_model"), parse={"valid": v is not None, "choice": v, "reason": why})
        self.log.append(rec)
        return rec

    def games(self) -> List[Dict[str, Any]]:
        out = []
        for k in range(C.GAMES_PER_CONDITION):              # interleave: replicate k of every condition, order seeded
            order = list(C.COND_ORDER)
            random.Random(C.derive_seed("cond_order", k)).shuffle(order)
            for c in order:
                mi, msi = C.CONDITIONS[c]
                out.append({"game_id": f"D{c}_{k + 1}", "condition": c, "matcher_informed": mi,
                            "mismatcher_informed": msi, "replicate": k + 1})
        return out

    def play(self, g: Dict[str, Any], prefix: str = "player") -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        status, note = "complete", ""
        for t in range(1, C.N_ROUNDS + 1):
            hist = [dict(r) for r in rows]
            recs = {}
            with ThreadPoolExecutor(max_workers=2) as pool:
                futs = {}
                for role, inf in (("matcher", g["matcher_informed"]), ("mismatcher", g["mismatcher_informed"])):
                    futs[pool.submit(self.call, f"{prefix}:{g['game_id']}:r{t:02d}:{role}", player_prompt(role, inf, hist, t),
                                     {"kind": "player", "game_id": g["game_id"], "condition": g["condition"], "round": t,
                                      "role": role, "informed": inf, "public_history": hist},
                                     {"opponent_actual": "astra", "opponent_informed": g["mismatcher_informed"] if role == "matcher" else g["matcher_informed"]})] = role
                for f in as_completed(futs):
                    recs[futs[f]] = f.result()
            if any(r is None for r in recs.values()):
                status, note = "incomplete", f"stopped at round {t} (budget/stop)"; break
            ch = {k: (r.get("parse") or {}).get("choice") for k, r in recs.items()}
            if None in ch.values():
                bad = {k: (recs[k].get("parse") or {}).get("reason", recs[k]["status"]) for k in ch if ch[k] is None}
                status, note = "incomplete", f"invalid round {t}: {bad}"; break
            rows.append({"round": t, "matcher": ch["matcher"], "mismatcher": ch["mismatcher"],
                         "winner": winner(ch["matcher"], ch["mismatcher"])})
        return {**g, "status": status, "note": note, "n_valid_rounds": len(rows), "rounds": rows}

    def run_all(self) -> List[Dict[str, Any]]:
        gs = self.games()
        progress(self.rd, f"games: {len(gs)} games x {C.N_ROUNDS} rounds, {C.GAME_CONCURRENCY} concurrent (spent ${self.acct.spent:.2f})")
        res = {}
        with ThreadPoolExecutor(max_workers=C.GAME_CONCURRENCY) as pool:
            futs = {pool.submit(self.play, g): g["game_id"] for g in gs}
            for f in as_completed(futs):
                r = f.result(); res[r["game_id"]] = r
                progress(self.rd, f"  game {r['game_id']}: {r['status']}, {r['n_valid_rounds']} rounds {r['note']} spent ${self.acct.spent:.2f}")
        ordered = [res[g["game_id"]] for g in gs]
        with open(self.rd / "game_logs.jsonl", "w") as f:
            for g in ordered:
                f.write(json.dumps(g) + "\n")
        return ordered
