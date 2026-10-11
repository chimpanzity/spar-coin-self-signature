"""
run_believed_self_pilot.py — PACA believed-self generator pilot (SPAR, 2026-10-11).

    python task/run_believed_self_pilot.py plan                 # manifest, exact prompts, prices, cost estimate, APPROVAL.md
    python task/run_believed_self_pilot.py validate             # offline: fake model, full 12-session dry run + checks
    python task/run_believed_self_pilot.py preflight --live     # 4 cheap calls per model (needs approval)
    python task/run_believed_self_pilot.py run --live [--model fable]   # full pilot, Fable -> Astra -> Qwen; resumable

Order of operations per trial t (identical to run_session.py):
  1. opponent (Proteus or IID coin) commits its trial-t landing from trials 1..t-1 only;
  2. the model is asked, with the PACA minimalist system prompt (+ believed-generator sentence) and the PACA user prompt
     built from the completed history (5 described rounds + 25-trial grid);
  3. the trial is scored (correct = forecast == landing) and appended to the history.
Proteus's random draws come from the session RNG (one draw per trial, as in PACA). call_model receives a separate
throwaway RNG, and its coin-flip fallbacks are never used: an attempt without a parsed model choice is re-requested
(identical request) up to MAX_TRIAL_ATTEMPTS in total; if all fail, the session stops and is preserved as incomplete.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from api_client import CLIENT_VERSION, PARSER_VERSION, call_model, make_client, parse_choice   # noqa: E402
from prime import apply_prime                                                                 # noqa: E402
from prompts import PROMPT_VERSION, SYS_MINIMALIST, build_prompt                               # noqa: E402
from protean_committed import choose_opponent_move                                            # noqa: E402
import believed_self as B                                                                     # noqa: E402

RUNNER_VERSION = "believed-self-runner-v1"
FORBIDDEN_IN_PROMPTS = ("proteus", "matching pennies", "opponent", "exploit", "random", "equilibrium", "50/50",
                        "adversar", "predict your", "unpredictab", "strategy")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def system_prompt(belief: str) -> str:
    return apply_prime(SYS_MINIMALIST, B.BELIEF_SENTENCE[belief])


def final_line_exact(text: str, choice: str) -> bool:
    """Audit flag (not used for parsing): last nonempty line, stripped of whitespace and markdown emphasis, equals the word."""
    lines = [l for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return False
    return lines[-1].strip().strip("*_`'\".").strip().upper() == ("TRIANGLE" if choice == "T" else "STAR")


def load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    with open(os.path.join(B.ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY not found (environment or PACA_implicit/.env)")


# ---------------------------------------------------------------------------
# Clients: provider-pinned OpenRouter wrapper around the PACA OpenAI client; offline fake
# ---------------------------------------------------------------------------

class PinnedClient:
    """Exposes chat.completions.create for api_client.call_model; adds provider pinning and usage accounting."""

    def __init__(self, model: str):
        self._inner = make_client(load_api_key(), timeout=240.0)
        self._provider = B.MODELS[model]["provider"]
        self.last = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        kwargs["extra_body"] = {"provider": {"order": [self._provider], "allow_fallbacks": False}, "usage": {"include": True}}
        self.last = None
        resp = self._inner.chat.completions.create(**kwargs)
        self.last = resp
        return resp


class FakeClient:
    """Offline stand-in. Deterministic in the prompt; optional malformed / empty responses."""

    def __init__(self, model: str, fail_rate: float = 0.0, policy: str = "mixed"):
        self.model, self.fail_rate, self.policy, self.n, self.last = model, fail_rate, policy, 0, None
        self.lock = threading.Lock()
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        msgs = kwargs["messages"]
        text = msgs[0]["content"] + "\n" + msgs[1]["content"]
        with self.lock:
            self.n += 1
            n = self.n
        rng = random.Random(B.sha256(text + str(n if self.fail_rate else 0)))
        if rng.random() < self.fail_rate:
            content, finish = "", "content_filter"
        elif self.policy == "copy_last" and "landed on" in msgs[1]["content"]:
            last = [l for l in msgs[1]["content"].splitlines() if "blue circle landed on" in l][-1]
            landed = last.split("landed on", 1)[1].split()[0]
            content, finish = "Looking at it.\n\n" + landed, "stop"
        else:
            content, finish = rng.choice(["TRIANGLE", "STAR", "I think it lands on the star.\n\n**STAR**", "triangle"]), "stop"
        u = SimpleNamespace(prompt_tokens=len(text) // 4, completion_tokens=8, total_tokens=len(text) // 4 + 8,
                            completion_tokens_details=None, cost=0.001)
        resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)],
                               model=kwargs["model"], id=f"fake-{n}", provider="Fake", usage=u)
        self.last = resp
        return resp


def response_cost(client, prices, slug, res) -> float:
    u = getattr(getattr(client, "last", None), "usage", None)
    c = getattr(u, "cost", None) if u is not None else None
    if c is None and u is not None and getattr(u, "model_extra", None):
        c = u.model_extra.get("cost")
    if c is not None:
        return float(c)
    p = prices[slug]
    return res.prompt_tokens * p["prompt"] + res.completion_tokens * p["completion"]


# ---------------------------------------------------------------------------
# Budget guard (shared across concurrent sessions)
# ---------------------------------------------------------------------------

class Budget:
    def __init__(self, cap: float, spent: float):
        self.cap, self.spent, self.reserved, self.lock = cap, spent, 0.0, threading.Lock()

    def reserve(self, amount: float) -> bool:
        with self.lock:
            if self.spent + self.reserved + amount > self.cap:
                return False
            self.reserved += amount
            return True

    def settle(self, reserved: float, actual: float) -> None:
        with self.lock:
            self.reserved -= reserved
            self.spent += actual


# ---------------------------------------------------------------------------
# One session (resumable)
# ---------------------------------------------------------------------------

def _jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def run_session(s: B.Session, out_dir: str, client, prices, budget: Budget, live: bool, log=print) -> dict:
    sd = os.path.join(out_dir, s.model, s.session_id)
    os.makedirs(sd, exist_ok=True)
    trials_path, attempts_path, status_path = (os.path.join(sd, n) for n in ("trials.jsonl", "attempts.jsonl", "status.json"))
    slug = B.MODELS[s.model]["slug"]
    temperature = 0.0 if B.MODELS[s.model]["send_temperature"] else None
    sys_prompt = system_prompt(s.belief)
    meta = {"experiment": B.EXPERIMENT_TAG, "session_id": s.session_id, "model": s.model, "model_slug": slug,
            "provider_pin": B.MODELS[s.model]["provider"], "actual_generator": s.generator, "believed_generator": s.belief,
            "condition": s.code, "session_index": s.session_index, "master_seed": B.MASTER_SEED, "session_seed": s.seed,
            "temperature_sent": temperature, "max_tokens": B.MAX_TOKENS, "max_tokens_ceiling": B.MAX_TOKENS_CEILING,
            "desc_window": B.DESC_WINDOW, "compact_window": B.COMPACT_WINDOW, "prompt_version": PROMPT_VERSION,
            "parser_version": PARSER_VERSION, "client_version": CLIENT_VERSION, "runner_version": RUNNER_VERSION,
            "system_prompt": sys_prompt, "system_prompt_sha256": B.sha256(sys_prompt), "live": live}
    with open(os.path.join(sd, "session_meta.json"), "w") as f:
        json.dump(meta, f, indent=1)

    # --- resume: replay the opponent's RNG over logged trials and verify it reproduces every landing
    done = _jsonl(trials_path)
    rng = random.Random(s.seed)
    history, past_choices, past_cr, circles = [], "", "", ""
    for row in done:
        cpu, _, _, ranval = choose_opponent_move(s.generator, past_choices, past_cr, rng)
        assert cpu == row["circle"] and f"{ranval:.6f}" == row["opp_ranval"], f"{s.session_id}: replay mismatch at trial {row['trial']}"
        history.append({"you": row["forecast"], "cpu": cpu, "win": bool(row["correct"])})
        past_choices += row["forecast"]; past_cr += row["forecast"] + ("1" if row["correct"] else "0"); circles += cpu
    if done:
        log(f"  {s.session_id}: resuming after trial {len(done)} (opponent state replayed and verified)")
    status = {"session_id": s.session_id, "status": "running", "completed_trials": len(done), "note": ""}

    throwaway = random.Random(f"callmodel-fallback-{s.seed}")   # call_model's coin fallback draws never touch the opponent RNG
    for t in range(len(done) + 1, B.N_TRIALS + 1):
        # 1. opponent commits from trials 1..t-1
        assert len(past_choices) == t - 1
        cpu, results, pred, ranval = choose_opponent_move(s.generator, past_choices, past_cr, rng)
        # 2. model forecast
        user_prompt = build_prompt(history, B.DESC_WINDOW, B.COMPACT_WINDOW)
        res, accepted, attempt_costs = None, False, 0.0
        for a in range(1, B.MAX_TRIAL_ATTEMPTS + 1):
            p = prices[slug]
            reserve = (len(sys_prompt) + len(user_prompt)) / 3 * p["prompt"] + B.MAX_TOKENS * p["completion"]
            if not budget.reserve(reserve):
                status.update(status="stopped_budget", note=f"budget cap ${budget.cap:.2f} reached before trial {t}")
                break
            t0 = utc_now()
            res = call_model(client, slug, sys_prompt, user_prompt, temperature=temperature, max_tokens=B.MAX_TOKENS,
                             rng=throwaway, escalate_on_truncation=True, max_tokens_ceiling=B.MAX_TOKENS_CEILING,
                             parse_fn=parse_choice)
            cost = response_cost(client, prices, slug, res) if res.choice_source != "fallback_api_fail" else 0.0
            budget.settle(reserve, cost)
            attempt_costs += cost
            ok = res.choice_source == "model"
            with open(attempts_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"session_id": s.session_id, "trial": t, "attempt": a, "dispatch_utc": t0, "accepted": ok,
                                    "choice_source": res.choice_source, "parsed": res.choice if ok else "",
                                    "finish_reason": res.finish_reason, "error_message": res.error_message,
                                    "response_text": res.response_text, "served_model": res.served_model,
                                    "provider": res.provider, "generation_id": res.generation_id,
                                    "prompt_tokens": res.prompt_tokens, "completion_tokens": res.completion_tokens,
                                    "reasoning_tokens": res.reasoning_tokens, "max_tokens_used": res.max_tokens_used,
                                    "retries_used": res.retries_used, "latency_ms": res.latency_ms, "cost_usd": cost,
                                    "user_prompt": user_prompt}) + "\n")
            if ok:
                accepted = True
                break
        if not accepted:
            if status["status"] == "running":
                status.update(status="stopped_no_valid_choice",
                              note=f"trial {t}: no parsed choice after {B.MAX_TRIAL_ATTEMPTS} attempts "
                                   f"(last: {res.choice_source}, finish={res.finish_reason})")
            break
        # 3. score and record
        choice = res.choice
        correct = int(choice == cpu)
        n_active = sum(1 for r in results if r.sig)
        pred_side = "" if pred is None else ("T" if pred.bside == "Triangle" else "S")
        row = {"session_id": s.session_id, "model": s.model, "model_slug": slug, "actual_generator": s.generator,
               "believed_generator": s.belief, "condition": s.code, "trial": t, "forecast": choice, "circle": cpu,
               "correct": correct, "prior_forecasts": past_choices, "prior_circles": circles, "history_cr": past_cr,
               "opp_ranval": f"{ranval:.6f}", "n_channels_active": n_active, "proteus_active": int(n_active > 0),
               "winning_channel": pred.n if pred is not None else -1,
               "winning_channel_bias": round(pred.bsideprob, 4) if pred is not None else "",
               "predicted_forecast": pred_side,
               "opp_action_type": ("random_no_detection" if pred is None else ("exploit" if cpu != pred_side else "mercy"))
               if s.generator == "proteus" else "iid_coin",
               **{f"n{i}_sign": int(results[i].sig) for i in range(9)},
               "attempts": a, "parse_status": res.choice_source, "final_line_exact": int(final_line_exact(res.response_text, choice)),
               "finish_reason": res.finish_reason, "served_model": res.served_model, "provider": res.provider,
               "prompt_tokens": res.prompt_tokens, "completion_tokens": res.completion_tokens,
               "reasoning_tokens": res.reasoning_tokens, "cost_usd": round(attempt_costs, 8), "latency_ms": res.latency_ms,
               "session_seed": s.seed, "trial_utc": utc_now(), "user_prompt": user_prompt,
               "user_prompt_sha256": B.sha256(user_prompt), "system_prompt_sha256": B.sha256(sys_prompt),
               "response_text": res.response_text}
        with open(trials_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        history.append({"you": choice, "cpu": cpu, "win": bool(correct)})
        past_choices += choice; past_cr += choice + ("1" if correct else "0"); circles += cpu
        status["completed_trials"] = t
        if t % 50 == 0:
            log(f"  {s.session_id}: {t}/{B.N_TRIALS} trials; accuracy so far {sum(1 for h in history if h['win']) / t:.3f}; "
                f"spent ${budget.spent:.2f}")
    if status["status"] == "running":
        status["status"] = "complete" if status["completed_trials"] == B.N_TRIALS else "incomplete"
    status["accuracy"] = (sum(1 for h in history if h["win"]) / len(history)) if history else None
    with open(status_path, "w") as f:
        json.dump(status, f, indent=1)
    return status


# ---------------------------------------------------------------------------
# Plan / validate / preflight / run
# ---------------------------------------------------------------------------

def fetch_prices():
    snap = {"fetched_utc": utc_now(), "endpoints": {}}
    for m in B.MODELS.values():
        with urllib.request.urlopen(f"https://openrouter.ai/api/v1/models/{m['slug']}/endpoints", timeout=60) as r:
            d = json.load(r)["data"]
        snap["endpoints"][m["slug"]] = [{"tag": e["tag"], "status": e.get("status"), "pricing": e["pricing"],
                                         "supported_parameters": e.get("supported_parameters")}
                                        for e in d["endpoints"] if e["tag"] == m["provider"]]
    return snap


def prices_from(snap):
    out = {}
    for m in B.MODELS.values():
        (e,) = snap["endpoints"][m["slug"]]
        out[m["slug"]] = {"prompt": float(e["pricing"]["prompt"]), "completion": float(e["pricing"]["completion"])}
    return out


def approved(out_dir) -> bool:
    p = os.path.join(out_dir, "APPROVAL.md")
    return os.path.exists(p) and any(l.strip() == "LIVE RUN APPROVED BY CHRIS: yes" for l in open(p))


def cmd_plan(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    snap = fetch_prices()
    for m in B.MODELS.values():
        (e,) = snap["endpoints"][m["slug"]]
        assert ("temperature" in (e["supported_parameters"] or [])) == m["send_temperature"], f"temperature support changed for {m['slug']}"
    with open(os.path.join(out_dir, "endpoint_and_price_snapshot.json"), "w") as f:
        json.dump(snap, f, indent=1)
    pr = prices_from(snap)
    # per-call usage from earlier PACA minimalist runs on this harness (data/**, Fable n=2259, Astra n=1918); Qwen assumed
    usage = {"fable": (358, 347, 818), "astra": (205, 62, 148), "qwen": (300, 1200, 4000)}
    est, rows = {}, []
    for m in B.MODEL_ORDER:
        p = pr[B.MODELS[m]["slug"]]
        pt, ct, ct95 = usage[m]
        n = 4 * B.N_TRIALS
        e, w = n * (pt * p["prompt"] + ct * p["completion"]), n * (pt * p["prompt"] + ct95 * p["completion"])
        est[m] = {"calls": n, "mean_prompt_tokens": pt, "mean_completion_tokens": ct, "p95_completion_tokens": ct95,
                  "expected_usd": e, "pessimistic_usd": w}
        rows.append(f"| {m} | {B.MODELS[m]['slug']} ({B.MODELS[m]['provider']}) | {n} | {pt} / {ct} / {ct95} | ${e:.2f} | ${w:.2f} |")
    tot_e, tot_w = sum(v["expected_usd"] for v in est.values()), sum(v["pessimistic_usd"] for v in est.values())
    pre = 12 * 0.05
    with open(os.path.join(out_dir, "cost_estimate.json"), "w") as f:
        json.dump({"per_model": est, "expected_total_usd": tot_e, "pessimistic_total_usd": tot_w,
                   "preflight_usd_upper": pre, "retry_allowance": "3% of pessimistic", "cap_usd": B.BUDGET_CAP_USD}, f, indent=1)
    sessions = B.sessions()
    manifest = {"created_utc": utc_now(), "experiment": B.EXPERIMENT_TAG, "runner_version": RUNNER_VERSION,
                "prompt_version": PROMPT_VERSION, "parser_version": PARSER_VERSION, "client_version": CLIENT_VERSION,
                "master_seed": B.MASTER_SEED, "n_trials": B.N_TRIALS, "desc_window": B.DESC_WINDOW,
                "compact_window": B.COMPACT_WINDOW, "max_tokens": B.MAX_TOKENS, "max_tokens_ceiling": B.MAX_TOKENS_CEILING,
                "max_trial_attempts": B.MAX_TRIAL_ATTEMPTS, "budget_cap_usd": B.BUDGET_CAP_USD, "model_order": B.MODEL_ORDER,
                "models": B.MODELS, "system_prompts": {b: system_prompt(b) for b in B.BELIEF_SENTENCE},
                "system_prompt_sha256": {b: B.sha256(system_prompt(b)) for b in B.BELIEF_SENTENCE},
                "sessions": [{"session_id": s.session_id, "model": s.model, "actual_generator": s.generator,
                              "believed_generator": s.belief, "condition": s.code, "session_index": s.session_index,
                              "session_seed": s.seed} for s in sessions]}
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    ex_hist = [{"you": a, "cpu": b, "win": a == b} for a, b in zip("TSSTTSTTSSTSTTTSSTSTSSTTSTT", "STSTTTSSTSTTSSTSTTSSTTSTSST")]
    L = ["# APPROVAL: PACA believed-self generator pilot", "",
         f"Experiment `{B.EXPERIMENT_TAG}`. 3 models x 4 conditions x 1 session x {B.N_TRIALS} trials = 2,400 model calls "
         f"(plus re-requests of failed trials). Hard cap ${B.BUDGET_CAP_USD:.0f}.", "",
         "## Cost estimate (pinned endpoints; usage from earlier PACA minimalist runs on this harness; Qwen assumed)", "",
         "| model | slug (provider) | calls | tokens in / out mean / out p95 | expected | pessimistic |", "|---|---|---:|---|---:|---:|", *rows,
         "", f"Expected ${tot_e:.2f}; pessimistic ${tot_w:.2f}; preflight about ${pre:.2f}.", "",
         "## Exact system prompts", "", "Believed self:", "", "```", system_prompt("self"), "```", "", "Believed other:", "",
         "```", system_prompt("other"), "```", "", "## Example user prompt (trial 28)", "", "```",
         build_prompt(ex_hist, B.DESC_WINDOW, B.COMPACT_WINDOW), "```", "", "## Status", "", "LIVE RUN APPROVED BY CHRIS: no", ""]
    with open(os.path.join(out_dir, "APPROVAL.md"), "w") as f:
        f.write("\n".join(L))
    print(f"PLAN written to {out_dir}: expected ${tot_e:.2f}, pessimistic ${tot_w:.2f}")


def run_model(model, out_dir, live, prices, budget, client_factory, log=print):
    ss = [s for s in B.sessions() if s.model == model]
    results = [None] * len(ss)

    def go(i):
        results[i] = run_session(ss[i], out_dir, client_factory(model), prices, budget, live, log)
    th = [threading.Thread(target=go, args=(i,)) for i in range(len(ss))]
    for t in th:
        t.start()
    for t in th:
        t.join()
    return results


def spent_so_far(out_dir):
    tot = 0.0
    for root, _, files in os.walk(out_dir):
        for fn in files:
            if fn in ("attempts.jsonl", "preflight_calls.jsonl"):
                tot += sum(float(r.get("cost_usd") or 0) for r in _jsonl(os.path.join(root, fn)))
    return tot


def cmd_preflight(out_dir):
    if not approved(out_dir):
        raise SystemExit("not approved (APPROVAL.md); no calls made")
    prices = prices_from(json.load(open(os.path.join(out_dir, "endpoint_and_price_snapshot.json"))))
    hist = [{"you": a, "cpu": b, "win": a == b} for a, b in zip("TSSTTSTTSSTSTTTSSTSTSSTTSTT", "STSTTTSSTSTTSSTSTTSSTTSTSST")]
    path = os.path.join(out_dir, "preflight_calls.jsonl")
    ok_all = True
    for m in B.MODEL_ORDER:
        client = PinnedClient(m)
        slug = B.MODELS[m]["slug"]
        temperature = 0.0 if B.MODELS[m]["send_temperature"] else None
        for belief in ("self", "other"):
            for h in ([], hist):
                up = build_prompt(h, B.DESC_WINDOW, B.COMPACT_WINDOW)
                res = call_model(client, slug, system_prompt(belief), up, temperature=temperature, max_tokens=B.MAX_TOKENS,
                                 rng=random.Random(0), max_tokens_ceiling=B.MAX_TOKENS_CEILING, parse_fn=parse_choice)
                cost = response_cost(client, prices, slug, res)
                rec = {"model": m, "belief": belief, "history_len": len(h), "choice_source": res.choice_source,
                       "parsed": res.choice if res.choice_source == "model" else "", "final_line_exact":
                       final_line_exact(res.response_text, res.choice) if res.choice_source == "model" else False,
                       "provider": res.provider, "served_model": res.served_model, "finish_reason": res.finish_reason,
                       "prompt_tokens": res.prompt_tokens, "completion_tokens": res.completion_tokens,
                       "reasoning_tokens": res.reasoning_tokens, "cost_usd": cost, "response_text": res.response_text}
                with open(path, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                ok_all &= res.choice_source == "model"
                print(f"  preflight {m:5s} {belief:5s} hist={len(h):2d}: {res.choice_source} {rec['parsed']} "
                      f"exact_final_line={rec['final_line_exact']} out_tokens={res.completion_tokens} ${cost:.4f} [{res.provider}]")
    print("PREFLIGHT", "PASS" if ok_all else "FAIL")
    return ok_all


def cmd_run(out_dir, only_model=None):
    if not approved(out_dir):
        raise SystemExit("not approved (APPROVAL.md); no calls made")
    prices = prices_from(json.load(open(os.path.join(out_dir, "endpoint_and_price_snapshot.json"))))
    budget = Budget(B.BUDGET_CAP_USD, spent_so_far(out_dir))
    for m in B.MODEL_ORDER:
        if only_model and m != only_model:
            continue
        print(f"[{utc_now()}] MODEL {m}: 4 sessions concurrently (spent so far ${budget.spent:.2f}, cap ${budget.cap:.0f})", flush=True)
        res = run_model(m, out_dir, True, prices, budget, PinnedClient, log=lambda x: print(x, flush=True))
        for r in res:
            print(f"  {r['session_id']}: {r['status']} {r['completed_trials']}/{B.N_TRIALS} accuracy={r['accuracy']} {r['note']}", flush=True)
        if any(r["status"] == "stopped_budget" for r in res):
            print("STOP: budget cap reached; later models not started", flush=True)
            return
    print(f"[{utc_now()}] RUN finished; spent ${budget.spent:.2f}", flush=True)


def cmd_validate(out_dir):
    """Offline full dry run of all 12 sessions with fake models, interruption + resume, then the unit tests."""
    import shutil
    import subprocess
    fake_dir = os.path.join(out_dir, "_validation_fake_run")
    shutil.rmtree(fake_dir, ignore_errors=True)
    prices = {m["slug"]: {"prompt": 1e-5, "completion": 5e-5} for m in B.MODELS.values()}
    # interrupt Fable after its sessions reach trial 120 by capping the budget, then resume with a fresh budget
    b1 = Budget(cap=0.0, spent=0.0)
    b1.cap = 4 * 120 * 0.001 + (0.003 + B.MAX_TOKENS * 5e-5)   # fake calls cost $0.001; stops near trial 120
    first = run_model("fable", fake_dir, False, prices, b1, lambda m: FakeClient(m, fail_rate=0.01), log=lambda x: None)
    resumed = run_model("fable", fake_dir, False, prices, Budget(1e9, 0.0), lambda m: FakeClient(m, fail_rate=0.01), log=lambda x: None)
    for m in ("astra", "qwen"):
        run_model(m, fake_dir, False, prices, Budget(1e9, 0.0), lambda mm: FakeClient(mm, fail_rate=0.01), log=lambda x: None)
    statuses = [json.load(open(os.path.join(fake_dir, s.model, s.session_id, "status.json"))) for s in B.sessions()]
    t = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_believed_self.py"], cwd=B.ROOT, capture_output=True, text=True)
    L = ["# VALIDATION REPORT: PACA believed-self pilot", "", f"Generated {utc_now()}.", "",
         "## Offline full run (fake model, 1% empty content_filter responses)", "",
         f"- Fable interrupted by a budget stop: {[r['status'] + '@' + str(r['completed_trials']) for r in first]}; "
         f"resumed: {[r['status'] + '@' + str(r['completed_trials']) for r in resumed]} (opponent RNG replay verified on resume).",
         f"- All sessions: {[(x['session_id'], x['status'], x['completed_trials']) for x in statuses]}", "",
         "## Unit tests", "", "```", t.stdout.strip()[-3000:], "```", "",
         f"Result: {'PASS' if t.returncode == 0 and all(x['status'] == 'complete' for x in statuses) and all(r['status'] == 'stopped_budget' for r in first) else 'FAIL'}", ""]
    with open(os.path.join(out_dir, "VALIDATION_REPORT.md"), "w") as f:
        f.write("\n".join(L))
    print(L[-2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "validate", "preflight", "run"])
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--model", choices=list(B.MODEL_ORDER))
    ap.add_argument("--out", default=B.DATA_DIR)
    a = ap.parse_args()
    if a.cmd == "plan":
        cmd_plan(a.out); return
    if a.cmd == "validate":
        cmd_validate(a.out); return
    if not a.live:
        raise SystemExit("--live required for paid calls")
    if a.cmd == "preflight":
        sys.exit(0 if cmd_preflight(a.out) else 1)
    cmd_run(a.out, a.model)


if __name__ == "__main__":
    main()
