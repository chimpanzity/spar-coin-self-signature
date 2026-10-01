"""Section 10-15: judge client config, durable ledger, preflight, scored collection.

Design:
  - raw_attempts.jsonl   append-only log of every API attempt (incl retries, failures)
  - trial_outcomes.json  { trial_id -> {status, correct, visible_answer, attempts, total_cost, request_ids...} }
  - cost_ledger.json     { spent, reserved, cap }
  - lockfile             prevents two runners sharing a run_dir

A valid completed trial yields exactly one `visible_answer in {A, B}` from the
first valid response. On abandonment, status="abandoned" and correct=None.
"""

import contextlib, hashlib, json, os, random, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI

from . import config as F
from .pairs import Trial, build_prompt, prompt_hash


# -- Pricing helpers ---------------------------------------------------------
def _cost_usd(prompt_tokens: int, completion_tokens: int,
              reasoning_tokens: int, price: Dict[str, float]) -> float:
    p = price.get("prompt", 0.0) * (prompt_tokens or 0)
    c = price.get("completion", 0.0) * ((completion_tokens or 0) + (reasoning_tokens or 0))
    return float(p + c)


def worst_case_cost(prompt_text: str, max_tokens: int, price: Dict[str, float]) -> float:
    """Upper bound on a single attempt's cost. 4 chars/token is a conservative
    estimate for English/ASCII; H/T sequences are 1 byte each so the per-char
    bound stays safe."""
    prompt_tokens = max(1, len(prompt_text) // 4 + 1)
    completion_tokens = max_tokens
    reasoning_tokens = max_tokens  # worst case: all tokens burned on reasoning
    # Both prompt + max completion ceilings
    return _cost_usd(prompt_tokens, completion_tokens, reasoning_tokens, price)


# -- Ledger ------------------------------------------------------------------

@dataclass
class CostLedger:
    cap_usd: float
    spent_usd: float = 0.0
    reserved_usd: float = 0.0  # worst-case holds for in-flight requests

    def commit(self, actual: float, reservation: float):
        self.spent_usd += float(actual)
        self.reserved_usd -= float(reservation)
        if self.reserved_usd < 0: self.reserved_usd = 0.0

    def can_reserve(self, reservation: float) -> bool:
        return (self.spent_usd + self.reserved_usd + reservation) <= self.cap_usd

    def reserve(self, reservation: float) -> bool:
        if not self.can_reserve(reservation):
            return False
        self.reserved_usd += float(reservation)
        return True

    def release(self, reservation: float):
        self.reserved_usd -= float(reservation)
        if self.reserved_usd < 0: self.reserved_usd = 0.0

    def to_dict(self) -> Dict:
        return {"cap_usd": self.cap_usd, "spent_usd": self.spent_usd,
                "reserved_usd": self.reserved_usd}


def _append_jsonl(path: str, rec: Dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def _write_json_atomic(path: str, obj: Any):
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def _read_json(path: str, default):
    if not os.path.exists(path): return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -- Judge client ------------------------------------------------------------

def make_openrouter_client(api_key: str, timeout_s: float = 120.0) -> OpenAI:
    return OpenAI(base_url="https://openrouter.ai/api/v1",
                  api_key=api_key, timeout=timeout_s)


def _call_judge(client: OpenAI, judge: F.JudgeSpec, prompt_text: str,
                max_tokens: int, provider_pin: Optional[str]) -> Dict[str, Any]:
    """One API call. Returns {raw_text, finish_reason, usage, provider, served_model,
    reasoning_tokens, request_id, generation_id, latency_ms, error}."""
    reasoning_cfg = F.REASONING_PER_JUDGE.get(judge.label, {"effort": "low", "exclude": True})
    extra_body: Dict[str, Any] = {
        "reasoning": dict(reasoning_cfg),
    }
    if provider_pin:
        # NOTE: `require_parameters: True` makes OpenRouter 404 whenever the
        # pinned provider's declared parameter schema doesn't include the
        # reasoning fields, even though those providers do accept and apply
        # the parameters. Pin + disable fallbacks is enough to lock routing;
        # the returned `provider` field is verified on every attempt.
        extra_body["provider"] = {
            "order": [provider_pin],
            "allow_fallbacks": False,
        }
    t0 = time.time()
    try:
        r = client.chat.completions.create(
            model=judge.slug,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=F.TEMPERATURE,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
    except Exception as e:
        return {"raw_text": "", "finish_reason": "error", "error": str(e)[:400],
                "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0,
                "provider": "", "served_model": "", "request_id": "", "generation_id": "",
                "latency_ms": int(1000 * (time.time() - t0))}
    choice = r.choices[0]
    msg = getattr(choice, "message", None)
    raw_text = (getattr(msg, "content", None) or "") if msg is not None else ""
    usage = getattr(r, "usage", None)
    pt = ct = rt = 0
    if usage is not None:
        pt = getattr(usage, "prompt_tokens", 0) or 0
        ct = getattr(usage, "completion_tokens", 0) or 0
        details = getattr(usage, "completion_tokens_details", None)
        if details is not None:
            rt = getattr(details, "reasoning_tokens", 0) or 0
    gen_id = getattr(r, "id", "") or ""
    req_id = ""
    try:
        req_id = r._request_id or ""
    except Exception:
        pass
    return {
        "raw_text": raw_text,
        "finish_reason": getattr(choice, "finish_reason", "") or "",
        "error": "",
        "prompt_tokens": pt, "completion_tokens": ct, "reasoning_tokens": rt,
        "provider": getattr(r, "provider", "") or "",
        "served_model": getattr(r, "model", "") or "",
        "request_id": req_id, "generation_id": gen_id,
        "latency_ms": int(1000 * (time.time() - t0)),
    }


# -- Section 13: parse A/B -----------------------------------------------------
def parse_ab(text: str) -> Optional[str]:
    s = (text or "").strip().upper()
    if s == "A": return "A"
    if s == "B": return "B"
    return None


# -- Trial execution ---------------------------------------------------------

@dataclass
class TrialOutcome:
    trial_id: str
    status: str                       # "ok" | "abandoned" | "pending"
    visible_answer: Optional[str]     # "A" | "B" | None
    correct: Optional[bool]           # vs correct_answer
    attempts: int                     # total response attempts (not transport retries)
    first_attempt_valid: Optional[bool]
    total_cost_usd: float
    returned_model_id: str
    provider: str
    request_ids: List[str] = field(default_factory=list)
    reasoning_tokens_total: int = 0
    completion_tokens_total: int = 0
    latency_ms_total: int = 0
    missing_reason: str = ""


def _run_one_trial(trial: Trial, judge: F.JudgeSpec, provider_pin: Optional[str],
                   client: OpenAI, max_tokens: int, run_dir: str,
                   ledger: CostLedger, price: Dict[str, float],
                   kind: str,
                   request_config_hash: str) -> TrialOutcome:
    """Run a single trial with retry policy; append each attempt to raw_attempts.jsonl.
    `kind` is "preflight" or "scored"."""
    raw_path = os.path.join(run_dir, "raw_attempts.jsonl")
    prompt_text = build_prompt(trial)
    phash = prompt_hash(prompt_text)
    outcome = TrialOutcome(
        trial_id=trial.trial_id, status="pending", visible_answer=None,
        correct=None, attempts=0, first_attempt_valid=None, total_cost_usd=0.0,
        returned_model_id="", provider="",
    )
    for attempt_i in range(1, F.RESPONSE_ATTEMPT_CAP + 1):
        # Transport retries wrapped
        last_result = None
        for tries in range(1, F.TRANSPORT_RETRY_CAP + 1):
            reservation = worst_case_cost(prompt_text, max_tokens, price)
            if not ledger.reserve(reservation):
                outcome.status = "abandoned"
                outcome.missing_reason = "budget_cap_prevents_dispatch"
                _append_jsonl(raw_path, {
                    "experiment_name": "full_corpus_experiment_1",
                    "specification_version": "FCE1_v1.0",
                    "kind": kind, "trial_id": trial.trial_id,
                    "attempt_number": attempt_i, "transport_try": tries,
                    "status": "budget_cap", "cost_usd": 0.0,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
                return outcome
            r = _call_judge(client, judge, prompt_text, max_tokens, provider_pin)
            cost = _cost_usd(r["prompt_tokens"], r["completion_tokens"],
                             r["reasoning_tokens"], price)
            ledger.commit(cost, reservation)
            last_result = r
            # Transport-level success: no error OR error is permanent (we don't retry those)
            if r["error"] == "" or _is_permanent_error(r["error"]):
                break
            # transient: back off
            time.sleep(min(2 ** tries, 10) + random.random())

        # One response attempt now has a last_result. Log it.
        parsed = parse_ab(last_result["raw_text"]) if last_result["error"] == "" else None
        rec = {
            "experiment_name": "full_corpus_experiment_1",
            "specification_version": "FCE1_v1.0",
            "kind": kind, "trial_id": trial.trial_id,
            "attempt_number": attempt_i,
            "prompt_hash": phash,
            "requested_judge_model_id": judge.slug,
            "returned_model_id": last_result["served_model"],
            "provider": last_result["provider"],
            "request_id": last_result["request_id"],
            "generation_id": last_result["generation_id"],
            "raw_visible_content": last_result["raw_text"],
            "finish_reason": last_result["finish_reason"],
            "parsed_answer": parsed,
            "valid": parsed is not None,
            "error": last_result["error"],
            "input_tokens": last_result["prompt_tokens"],
            "output_tokens": last_result["completion_tokens"],
            "reasoning_tokens": last_result["reasoning_tokens"],
            "latency_ms": last_result["latency_ms"],
            "cost_usd": cost if last_result["error"] == "" else cost,  # count uncertain-billing conservatively
            "cost_status": "billed" if last_result["error"] == "" else "uncertain",
            "judge_request_config_hash": request_config_hash,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _append_jsonl(raw_path, rec)
        outcome.attempts = attempt_i
        outcome.total_cost_usd += cost
        outcome.reasoning_tokens_total += last_result["reasoning_tokens"]
        outcome.completion_tokens_total += last_result["completion_tokens"]
        outcome.latency_ms_total += last_result["latency_ms"]
        if last_result["request_id"]:
            outcome.request_ids.append(last_result["request_id"])
        if not outcome.returned_model_id:
            outcome.returned_model_id = last_result["served_model"]
            outcome.provider = last_result["provider"]
        if attempt_i == 1:
            outcome.first_attempt_valid = (parsed is not None)
        if parsed is not None:
            outcome.visible_answer = parsed
            outcome.correct = (parsed == trial.correct_answer)
            outcome.status = "ok"
            return outcome
    outcome.status = "abandoned"
    outcome.missing_reason = "exhausted_response_attempts"
    return outcome


def _is_permanent_error(err: str) -> bool:
    s = err.lower()
    for marker in ("401", "403", "invalid api key", "authentication", "quota",
                    "model_not_found", "not available", "invalid model"):
        if marker in s: return True
    return False


# -- Catalog + price snapshot -------------------------------------------------
def snapshot_prices(client: OpenAI) -> Dict[str, Dict[str, float]]:
    """Return { slug -> {prompt, completion} } floats USD/token."""
    out: Dict[str, Dict[str, float]] = {}
    try:
        models = client.models.list()
        for m in models.data:
            slug = getattr(m, "id", None)
            pricing = getattr(m, "pricing", None) or {}
            if slug and pricing:
                out[slug] = {
                    "prompt": float(pricing.get("prompt", 0.0) or 0.0),
                    "completion": float(pricing.get("completion", 0.0) or 0.0),
                }
    except Exception:
        pass
    return out


# -- Section 14: process lock ------------------------------------------------
@contextlib.contextmanager
def process_lock(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        raise RuntimeError(f"lockfile exists: {path} — another runner may be active")
    with open(path, "w") as f:
        f.write(f"{os.getpid()} {time.time()}\n")
    try:
        yield
    finally:
        try: os.remove(path)
        except OSError: pass


# -- Request config hash -----------------------------------------------------
def judge_request_config_hash(max_tokens: int, provider_pin: Optional[str],
                               judge_label: Optional[str] = None) -> str:
    reasoning_cfg = (F.REASONING_PER_JUDGE.get(judge_label or "", {"effort": "low", "exclude": True}))
    h = hashlib.sha256()
    h.update(json.dumps({
        "temperature": F.TEMPERATURE,
        "max_tokens": max_tokens,
        "reasoning": reasoning_cfg,
        "provider_pin": provider_pin or "",
    }, sort_keys=True).encode())
    return h.hexdigest()
