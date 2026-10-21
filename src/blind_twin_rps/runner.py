"""Blind Twin runner: games -> freeze -> blinded judging. Resumable, append-only.

Reuses the audited SPAR Phase 2 transport, budget accountant and call log.
"""
from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from spar_dynamic.phase2.client import (Accountant, BudgetExceeded, CallLog, OpenRouterTransport,
                                        TransientError, _extract, fetch_prices, git_state, utc_now)

from . import config as C
from .parse import PARSER_VERSION, parse_judge, parse_shape
from .render import judge_prompt, player_prompt, winner


def progress(rd: Path, msg: str) -> None:
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with open(rd / "PROGRESS.md", "a") as f:
        f.write(line)
    print(line, end="", flush=True)


class FakeTransport:
    """Offline stand-in. Seeded per request text + call count; never touches the network."""
    name = "fake"

    def __init__(self, malformed_rate: float = 0.0):
        self.n = 0
        self.lock = threading.Lock()
        self.malformed_rate = malformed_rate

    def send(self, body: Dict[str, Any]) -> Dict[str, Any]:
        text = body["messages"][-1]["content"]
        with self.lock:
            self.n += 1
            n = self.n
        rng = random.Random(C.derive_seed("fake", body["model"], text, n))
        if rng.random() < self.malformed_rate:
            out = "I would pick ROCK or maybe PAPER, hard to say."
        elif "alone on the final line" in text:
            out = rng.choice(["ROCK", "Opponent cycles.\n\nPAPER", "Thinking briefly.\n**SCISSORS**", "Paper"])
        else:
            out = json.dumps({"player_a": rng.choice(C.SHAPES), "player_b": rng.choice(C.SHAPES)})
        return {"id": f"fake-{n}", "model": body["model"], "provider": "Fake", "_http_status": 200,
                "choices": [{"message": {"content": out}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(text) // 4, "completion_tokens": 5, "cost": 0.0}}


def request_body(model: str, prompt: str, slot_id: str = "") -> Dict[str, Any]:
    m = C.MODELS[model]
    body = {"model": m["slug"], "messages": [{"role": "user", "content": prompt}],
            "reasoning": dict(C.REASONING), "max_tokens": C.MAX_TOKENS,
            "provider": {"order": [m["provider"]], "allow_fallbacks": False},
            "usage": {"include": True}}
    if m.get("send_seed"):
        body["seed"] = C.derive_seed("request_seed", slot_id) % 2**31     # distinct, recorded, per slot
    return body


class Runner:
    def __init__(self, run_dir: Path, live: bool, log_name: str = "calls.jsonl"):
        self.rd = run_dir
        self.rd.mkdir(parents=True, exist_ok=True)
        self.live = live
        self.transport = OpenRouterTransport() if live else FakeTransport()
        prices_path = self.rd / "pricing_snapshot.json"
        if live:
            if not prices_path.exists():
                pr = fetch_prices([m["slug"] for m in C.MODELS.values()])
                prices_path.write_text(json.dumps({"fetched_utc": utc_now(), **pr}, indent=1))
            prices = {k: v for k, v in json.loads(prices_path.read_text()).items() if k != "fetched_utc"}
        else:
            prices = {m["slug"]: {"prompt": 1e-5, "completion": 5e-5} for m in C.MODELS.values()}
        self.log = CallLog(self.rd / log_name)
        spent = sum(float(r.get("cost_usd") or 0) for r in self.log.done_ids().values())
        for extra in ("smoke_calls.jsonl", "calls.jsonl"):
            p = self.rd / extra
            if p.exists() and extra != log_name:
                spent += sum(float(json.loads(l).get("cost_usd") or 0) for l in p.read_text().splitlines() if l.strip())
        self.acct = Accountant(C.BUDGET_CAP_USD, prices, spent=spent)
        self.ctx = {"protocol": C.PROTOCOL, "code_hash": C.code_hash(), "code": git_state(),
                    "parser_version": PARSER_VERSION, "transport": self.transport.name,
                    "seed": {"intent": "none", "status": "not transmitted (temperature/seed unsupported or omitted by policy)"}}
        self.stop = threading.Event()

    # -- single audited call --------------------------------------------
    def call(self, slot_id: str, model: str, prompt: str, kind: str, meta: Dict[str, Any],
             private: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        done = self.log.done_ids()
        if slot_id in done and done[slot_id]["status"] != "transport_failed":
            return done[slot_id]
        if self.stop.is_set():
            return None
        body = request_body(model, prompt, slot_id)
        shim = SimpleNamespace(params=body, messages=body["messages"])
        try:
            reserved = self.acct.reserve(shim)
        except BudgetExceeded as e:
            self.stop.set()
            progress(self.rd, f"BUDGET STOP: {e}")
            return None
        queued, t0, attempts, obj = utc_now(), time.monotonic(), [], None
        for i in range(1 + C.MAX_TRANSIENT_RETRIES):
            disp = utc_now()
            try:
                obj = self.transport.send(body)
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": True})
                break
            except TransientError as e:
                attempts.append({"attempt": i, "dispatch_utc": disp, "ok": False, "error": str(e)[:600]})
                if i < C.MAX_TRANSIENT_RETRIES:
                    time.sleep([10, 30, 90][i])
        rec: Dict[str, Any] = {"slot_id": slot_id, "kind": kind, "model": model, **meta, "private": private,
                               "request": body, "queued_utc": queued, "completed_utc": utc_now(),
                               "elapsed_s": round(time.monotonic() - t0, 3), "attempts": attempts, **self.ctx}
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
                rec["cost_status"] = "estimated"
            else:
                rec["cost_status"] = "reported"
            self.acct.settle(reserved, float(cost))
            rec.update(status="completed", cost_usd=float(cost), response=ex,
                       returned_provider=ex.get("provider"), returned_model=ex.get("returned_model"))
            if kind == "player":
                v, why = parse_shape(ex["text"], ex["finish_reason"] or "")
                rec["parse"] = {"valid": v is not None, "choice": v, "reason": why}
            else:
                v, why = parse_judge(ex["text"], ex["finish_reason"] or "")
                rec["parse"] = {"valid": v is not None, "prediction": v, "reason": why}
        self.log.append(rec)
        return rec

    # -- games -------------------------------------------------------------
    def game_ids(self) -> List[Dict[str, Any]]:
        games = []
        for k in range(C.GAMES_PER_MATCHUP):
            for (mm, ms) in C.MATCHUPS:
                games.append({"game_id": f"G{mm[0].upper()}{ms[0].upper()}{k + 1}", "matchup": f"{mm}-{ms}",
                              "player_a_model": mm, "player_b_model": ms, "replicate": k + 1})
        return games   # interleaved: replicate 1 of all four matchups, then 2, then 3

    def play_game(self, g: Dict[str, Any]) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        status, note = "complete", ""
        for t in range(1, C.N_ROUNDS + 1):
            hist = [dict(r) for r in rows]                       # identical prior history for both seats
            recs = {}
            with ThreadPoolExecutor(max_workers=2) as pool:
                futs = {}
                for role, model in (("player_a", g["player_a_model"]), ("player_b", g["player_b_model"])):
                    prompt = player_prompt(role, hist, t)
                    sid = f"player:{g['game_id']}:r{t:02d}:{role}"
                    meta = {"game_id": g["game_id"], "matchup": g["matchup"], "round": t, "role": role,
                            "public_history": hist}
                    futs[pool.submit(self.call, sid, model, prompt, "player", meta,
                                     {"actual_player_a": g["player_a_model"], "actual_player_b": g["player_b_model"]})] = role
                for f in as_completed(futs):
                    recs[futs[f]] = f.result()
            if any(r is None for r in recs.values()):
                status, note = "incomplete", f"stopped at round {t} (budget/stop)"
                break
            ch = {role: (r.get("parse") or {}).get("choice") for role, r in recs.items()}
            if ch["player_a"] is None or ch["player_b"] is None:
                bad = {role: (recs[role].get("parse") or {}).get("reason", recs[role]["status"]) for role in recs if ch[role] is None}
                status, note = "incomplete", f"invalid round {t}: {bad}"
                break
            rows.append({"round": t, "player_a": ch["player_a"], "player_b": ch["player_b"],
                         "winner": winner(ch["player_a"], ch["player_b"])})
        return {**g, "status": status, "note": note, "n_valid_rounds": len(rows), "rounds": rows}

    def run_games(self) -> List[Dict[str, Any]]:
        games = self.game_ids()
        progress(self.rd, f"games: playing {len(games)} games x {C.N_ROUNDS} rounds (spent so far ${self.acct.spent:.2f})")
        out: Dict[str, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=len(games)) as pool:
            futs = {pool.submit(self.play_game, g): g["game_id"] for g in games}
            for f in as_completed(futs):
                res = f.result()
                out[res["game_id"]] = res
                progress(self.rd, f"  game {res['game_id']} ({res['matchup']}): {res['status']}, "
                                  f"{res['n_valid_rounds']} valid rounds {res['note']} spent ${self.acct.spent:.2f}")
        ordered = [out[g["game_id"]] for g in games]
        with open(self.rd / "game_logs.jsonl", "w") as f:
            for g in ordered:
                f.write(json.dumps(g) + "\n")
        return ordered

    # -- freeze + judging -------------------------------------------------
    def judge_schedule(self, games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sched = []
        for g in games:
            for t in range(1, g["n_valid_rounds"] + 1):
                for j in C.JUDGES:
                    for cnd in C.CONDITIONS:
                        sched.append({"slot_id": f"judge:{g['game_id']}:r{t:02d}:{j}:{cnd}", "game_id": g["game_id"],
                                      "round": t, "judge": j, "condition": cnd})
        rng = random.Random(C.derive_seed("judge_schedule"))
        rng.shuffle(sched)
        return sched

    def freeze(self, games: List[Dict[str, Any]]) -> Dict[str, Any]:
        sched = self.judge_schedule(games)
        (self.rd / "judge_schedule.json").write_text(json.dumps(sched))
        fz = {"frozen_utc": utc_now(), "code_hash": C.code_hash(),
              "game_logs_sha256": hashlib.sha256((self.rd / "game_logs.jsonl").read_bytes()).hexdigest(),
              "judge_schedule_sha256": hashlib.sha256((self.rd / "judge_schedule.json").read_bytes()).hexdigest(),
              "config_sha256": hashlib.sha256((self.rd / "config.json").read_bytes()).hexdigest(),
              "n_judge_calls": len(sched)}
        (self.rd / "freeze.json").write_text(json.dumps(fz, indent=1))
        progress(self.rd, f"FREEZE: game logs and {len(sched)}-call judge schedule frozen (code {fz['code_hash'][:12]})")
        return fz

    def run_judges(self) -> None:
        fz = json.loads((self.rd / "freeze.json").read_text())
        assert hashlib.sha256((self.rd / "game_logs.jsonl").read_bytes()).hexdigest() == fz["game_logs_sha256"], "game logs changed after freeze"
        assert fz["code_hash"] == C.code_hash(), "code changed after freeze"
        games = {json.loads(l)["game_id"]: json.loads(l) for l in (self.rd / "game_logs.jsonl").read_text().splitlines()}
        sched = json.loads((self.rd / "judge_schedule.json").read_text())
        done = self.log.done_ids()
        todo = [s for s in sched if s["slot_id"] not in done or done[s["slot_id"]]["status"] == "transport_failed"]
        progress(self.rd, f"judges: {len(todo)} of {len(sched)} calls to dispatch (spent so far ${self.acct.spent:.2f})")
        n = 0

        def one(s):
            g = games[s["game_id"]]
            t = s["round"]
            hist = g["rounds"][: t - 1]
            target = g["rounds"][t - 1]
            prompt = judge_prompt(s["judge"], s["condition"], g["player_a_model"], g["player_b_model"], hist, t)
            shown = {"TRUE": (g["player_a_model"], g["player_b_model"]),
                     "FALSE": (C.other_model(g["player_a_model"]), C.other_model(g["player_b_model"])),
                     "ANONYMOUS": (None, None)}[s["condition"]]
            meta = {"game_id": g["game_id"], "matchup": g["matchup"], "round": t, "judge": s["judge"],
                    "condition": s["condition"], "public_history": hist}
            private = {"actual_player_a": g["player_a_model"], "actual_player_b": g["player_b_model"],
                       "displayed_player_a": shown[0], "displayed_player_b": shown[1],
                       "target_player_a": target["player_a"], "target_player_b": target["player_b"]}
            return self.call(s["slot_id"], s["judge"], prompt, "judge", meta, private)

        with ThreadPoolExecutor(max_workers=C.JUDGE_CONCURRENCY) as pool:
            for f in as_completed([pool.submit(one, s) for s in todo]):
                f.result()
                n += 1
                if n % 100 == 0:
                    progress(self.rd, f"  judges: {n}/{len(todo)} recorded, spent ${self.acct.spent:.2f}")
        recs = [self.log.done_ids().get(s["slot_id"]) for s in sched]
        nv = sum(1 for r in recs if r and (r.get("parse") or {}).get("valid"))
        progress(self.rd, f"judges finished: {sum(1 for r in recs if r)}/{len(sched)} recorded, {nv} valid; spent ${self.acct.spent:.2f}")

    # -- smoke games (v2): two full technical games, separate log ---------------
    def smoke_games(self) -> List[Dict[str, Any]]:
        x, y = C.ORDER
        games = [{"game_id": f"SMK_{x[0].upper()}{y[0].upper()}", "matchup": f"{x}-{y}", "player_a_model": x, "player_b_model": y, "replicate": 0},
                 {"game_id": f"SMK_{y[0].upper()}{y[0].upper()}", "matchup": f"{y}-{y}", "player_a_model": y, "player_b_model": y, "replicate": 0}]
        with ThreadPoolExecutor(max_workers=2) as pool:
            res = list(pool.map(self.play_game, games))
        with open(self.rd / "smoke_game_logs.jsonl", "w") as f:
            for g in res:
                f.write(json.dumps(g) + "\n")
        return res

    # -- smoke ---------------------------------------------------------------
    def smoke(self) -> List[Dict[str, Any]]:
        out = []
        for m in C.ORDER:
            out.append(self.call(f"smoke:player:{m}", m, player_prompt("player_a", [], 1), "player",
                                 {"game_id": "SMOKE", "round": 1, "role": "player_a", "public_history": []}, {}))
            rows = [{"round": 1, "player_a": "ROCK", "player_b": "PAPER", "winner": "Player B"}]
            out.append(self.call(f"smoke:judge:{m}", m, judge_prompt(m, "ANONYMOUS", C.ORDER[0], C.ORDER[1], rows, 2), "judge",
                                 {"game_id": "SMOKE", "round": 2, "judge": m, "condition": "ANONYMOUS", "public_history": rows}, {}))
        return out
