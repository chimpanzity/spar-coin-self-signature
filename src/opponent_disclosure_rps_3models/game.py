"""Rendering, parsing, frozen schedule, approval gate and resumable runner."""
from __future__ import annotations

import hashlib
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

PARSER_VERSION = "rps3m_v1_last_line_exact"


# ---------------------------------------------------------------------------
# Game logic and rendering (public history only)
# ---------------------------------------------------------------------------

def result(p1: str, p2: str) -> str:
    if p1 == p2:
        return "Tie"
    return "Player 1" if C.BEATS[p1] == p2 else "Player 2"


def payoff_p1(res: str) -> float:
    return {"Player 1": 1.0, "Player 2": 0.0, "Tie": 0.5}[res]


def history_text(rows: Sequence[Dict]) -> str:
    if not rows:
        return C.EMPTY_HISTORY
    return "\n".join([C.HISTORY_HEADER] + [f"{r['round']} | {r['p1']} | {r['p2']} | {r['result']}" for r in rows])


def player_prompt(seat: str, own: str, opponent: str, informed: bool, rows: Sequence[Dict], t: int) -> str:
    assert seat in ("Player 1", "Player 2")
    assert len(rows) == t - 1, "history must contain exactly the completed rounds before round t"
    for i, r in enumerate(rows, 1):
        assert r["round"] == i and set(r) == {"round", "p1", "p2", "result"}, "public rows only"
    sent = C.INFORMED.format(TRUE_OPPONENT_MODEL_NAME=C.MODELS[opponent]["name"]) if informed else C.UNINFORMED
    return C.GAME_TEMPLATE.format(SEAT=seat, OWN_MODEL_NAME=C.MODELS[own]["name"], OPPONENT_IDENTITY_SENTENCE=sent,
                                  PUBLIC_HISTORY=history_text(rows), T=t)


def parse_move(text: Optional[str], finish_reason: str = "") -> Tuple[Optional[str], str]:
    if text is None or not text.strip():
        return None, "empty"
    if (finish_reason or "").lower() == "length":
        return None, "truncated_length"
    last = [l for l in text.strip().splitlines() if l.strip()][-1].strip().upper()
    return (last, "ok") if last in C.MOVES else (None, "final_line_not_exact_move")


# ---------------------------------------------------------------------------
# Frozen schedule
# ---------------------------------------------------------------------------

def schedule() -> List[Dict[str, Any]]:
    games = []
    for p1, p2 in C.PAIRINGS:
        for c, (i1, i2) in C.CONDITIONS.items():
            for k in range(1, C.REPLICATES + 1):
                gid = f"{p1[0].upper()}{p2[0].upper()}_{c}_{k}"
                games.append({"game_id": gid, "p1_model": p1, "p2_model": p2, "condition": c,
                              "p1_informed": i1, "p2_informed": i2, "replicate": k,
                              "game_seed": C.derive_seed("game", gid)})
    # interleave across time: order by replicate wave, then a seeded shuffle within the wave
    waves = {}
    for g in games:
        waves.setdefault(g["replicate"], []).append(g)
    out = []
    for k in sorted(waves):
        w = waves[k]
        random.Random(C.derive_seed("wave_order", k)).shuffle(w)
        out += w
    for i, g in enumerate(out):
        g["order"] = i
    return out


def schedule_hash(sched: List[Dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(sched, sort_keys=True).encode()).hexdigest()


def approved(rd: Path) -> bool:
    """Live calls require APPROVAL.md containing the exact line 'LIVE RUN APPROVED BY CHRIS: yes'."""
    p = rd / "APPROVAL.md"
    return p.exists() and any(l.strip() == "LIVE RUN APPROVED BY CHRIS: yes" for l in p.read_text().splitlines())


# ---------------------------------------------------------------------------
# Transport and runner
# ---------------------------------------------------------------------------

class FakeTransport:
    name = "fake"

    def __init__(self, malformed_rate: float = 0.0):
        self.n, self.lock, self.malformed_rate = 0, threading.Lock(), malformed_rate

    def send(self, body):
        text = body["messages"][-1]["content"]
        with self.lock:
            self.n += 1
            n = self.n
        rng = random.Random(C.derive_seed("fake", text, n))
        if rng.random() < self.malformed_rate:
            out = "Probably ROCK, maybe PAPER."
        else:
            out = rng.choice(["ROCK", "PAPER", "SCISSORS", "Thinking.\n\nPaper", "  scissors  "])
        return {"id": f"fake-{n}", "model": body["model"], "provider": "Fake", "_http_status": 200,
                "choices": [{"message": {"content": out}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(text) // 4, "completion_tokens": 4, "cost": 0.0}}


def request_body(model: str, prompt: str) -> Dict[str, Any]:
    m = C.MODELS[model]
    return {"model": m["slug"], "messages": [{"role": "user", "content": prompt}], "reasoning": dict(C.REASONING),
            "max_tokens": C.MAX_TOKENS, "provider": {"order": [m["provider"]], "allow_fallbacks": False},
            "usage": {"include": True}}


def progress(rd: Path, msg: str) -> None:
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(rd / "PROGRESS.md", "a") as f:
        f.write(line)
    print(line, end="", flush=True)


def snapshot_prices(snap: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Per-token prices for the pinned provider of each model, from the plan-time endpoint snapshot
    ({"endpoints": {slug: [{"tag", "pricing"}, ...]}}) or a fetch_prices()-style {slug: {prompt, completion}} dict."""
    if "endpoints" not in snap:
        return {k: v for k, v in snap.items() if k != "fetched_utc"}
    out = {}
    for m in C.MODELS.values():
        ep = [e for e in snap["endpoints"][m["slug"]] if e["tag"] == m["provider"]]
        assert len(ep) == 1, f"pinned endpoint {m['provider']} not unique in snapshot for {m['slug']}"
        out[m["slug"]] = {"prompt": float(ep[0]["pricing"]["prompt"]), "completion": float(ep[0]["pricing"]["completion"])}
    return out


class Runner:
    def __init__(self, rd: Path, live: bool, log_name: str = "calls.jsonl", transport=None):
        self.rd = rd
        rd.mkdir(parents=True, exist_ok=True)
        if live and not approved(rd):
            raise SystemExit("live run requested but APPROVAL.md does not contain explicit approval; no network calls made")
        self.live = live
        self.transport = transport or (OpenRouterTransport() if live else FakeTransport())
        snap = rd / "endpoint_and_price_snapshots.json"
        if live:
            if not snap.exists():
                snap.write_text(json.dumps({"fetched_utc": utc_now(), **fetch_prices([m["slug"] for m in C.MODELS.values()])}, indent=1))
            prices = snapshot_prices(json.loads(snap.read_text()))
        else:
            prices = {m["slug"]: {"prompt": 1e-5, "completion": 5e-5} for m in C.MODELS.values()}
        self.log = CallLog(rd / log_name)
        self.done = self.log.done_ids()          # loaded once; updated on every append (resume index)
        self.done_lock = threading.Lock()
        spent = 0.0
        for nm in ("calls.jsonl", "smoke_calls.jsonl"):
            p = rd / nm
            if p.exists():
                spent += sum(float(json.loads(l).get("cost_usd") or 0) for l in p.read_text().splitlines() if l.strip())
        self.acct = Accountant(C.BUDGET_CAP_USD, prices, spent=spent)
        self.ctx = {"protocol": C.PROTOCOL, "code_hash": C.code_hash(), "code": git_state(), "parser_version": PARSER_VERSION,
                    "transport": self.transport.name, "seed": {"intent": "none", "status": "not transmitted"}}
        self.stop = threading.Event()

    def call(self, slot_id, model, prompt, meta, private):
        with self.done_lock:
            prev = self.done.get(slot_id)
        if prev is not None and prev["status"] != "transport_failed":
            return prev
        if self.stop.is_set():
            return None
        body = request_body(model, prompt)
        try:
            reserved = self.acct.reserve(SimpleNamespace(params=body, messages=body["messages"]))
        except BudgetExceeded as e:
            self.stop.set(); progress(self.rd, f"BUDGET STOP (no new dispatches): {e}"); return None
        queued, t0, attempts, obj = utc_now(), time.monotonic(), [], None
        for i in range(1 + C.MAX_TRANSIENT_RETRIES):
            disp = utc_now()
            try:
                obj = self.transport.send(body); attempts.append({"attempt": i, "dispatch_utc": disp, "ok": True}); break
            except TransientError as e:
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": False, "error": str(e)[:600]})
                if i < C.MAX_TRANSIENT_RETRIES:
                    time.sleep([10, 30, 90][i])
        rec = {"slot_id": slot_id, "model": model, **meta, "private": private, "request": body,
               "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "queued_utc": queued,
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
            v, why = parse_move(ex["text"], ex["finish_reason"] or "")
            rec.update(status="completed", cost_usd=float(cost), response=ex, returned_provider=ex.get("provider"),
                       returned_model=ex.get("returned_model"), parse={"valid": v is not None, "move": v, "reason": why})
        self.log.append(rec)
        with self.done_lock:
            self.done[slot_id] = rec
        return rec

    def play(self, g: Dict[str, Any], prefix: str = "player") -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        status, note = "complete", ""
        for t in range(1, C.N_ROUNDS + 1):
            hist = [dict(r) for r in rows]
            hist_hash = hashlib.sha256(json.dumps(hist).encode()).hexdigest()
            seats = (("Player 1", "p1", g["p1_model"], g["p2_model"], g["p1_informed"]),
                     ("Player 2", "p2", g["p2_model"], g["p1_model"], g["p2_informed"]))
            recs = {}
            with ThreadPoolExecutor(max_workers=2) as pool:
                futs = {}
                for seat, key, own, opp, inf in seats:
                    meta = {"kind": "player", "game_id": g["game_id"], "pairing": f"{g['p1_model']}-{g['p2_model']}",
                            "condition": g["condition"], "round": t, "seat": seat, "public_history": hist,
                            "history_sha256": hist_hash}
                    private = {"own_model": own, "true_opponent": opp, "informed": inf}
                    futs[pool.submit(self.call, f"{prefix}:{g['game_id']}:r{t:02d}:{key}", own,
                                     player_prompt(seat, own, opp, inf, hist, t), meta, private)] = key
                for f in as_completed(futs):
                    recs[futs[f]] = f.result()
            if any(r is None for r in recs.values()):
                status, note = "interrupted", f"stopped before round {t} completed (budget/stop)"; break
            mv = {k: (r.get("parse") or {}).get("move") for k, r in recs.items()}
            if None in mv.values():
                bad = {k: (recs[k].get("parse") or {}).get("reason", recs[k]["status"]) for k in mv if mv[k] is None}
                status, note = "interrupted", f"invalid response at round {t}: {bad}"; break
            rows.append({"round": t, "p1": mv["p1"], "p2": mv["p2"], "result": result(mv["p1"], mv["p2"])})
        return {**g, "status": status, "note": note, "n_valid_rounds": len(rows), "rounds": rows}

    def run(self, sched: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        progress(self.rd, f"games: {len(sched)} scheduled, {C.GAME_CONCURRENCY} concurrent (spent so far ${self.acct.spent:.2f}, cap ${C.BUDGET_CAP_USD:.0f})")
        res = {}
        n = 0
        with ThreadPoolExecutor(max_workers=C.GAME_CONCURRENCY) as pool:
            futs = {pool.submit(self.play, g): g["game_id"] for g in sched}
            for f in as_completed(futs):
                r = f.result(); res[r["game_id"]] = r; n += 1
                if r["status"] != "complete" or n % 24 == 0:
                    progress(self.rd, f"  {n}/{len(sched)} games done; last {r['game_id']} {r['status']} {r['note']}; spent ${self.acct.spent:.2f}")
        ordered = [res[g["game_id"]] for g in sched]
        with open(self.rd / "game_logs.jsonl", "w") as fh:
            for g in ordered:
                fh.write(json.dumps(g) + "\n")
        return ordered
