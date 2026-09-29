"""Pilot 4 — Astra-only provenance replication with a no-provenance control.

Design (Astra as judge):
  * 20 fresh Astra SELF trajectories (10 batch + 10 online)
  * 20 fresh OTHER trajectories (5 fable batch + 5 fable online + 5 qwen batch + 5 qwen online)
  * every trajectory judged 3x: told-batch, told-online, no-provenance
  * 40 x 3 = 120 judgment trials

Trial ordering: reproducible shuffle with soft-constraint debunching so that
  * the three versions of the same trajectory are never adjacent
  * long runs of same stated condition / identity are avoided
"""

import os, random, uuid
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from . import config as C
from .api import (APIResult, CostAccountant, call_model, parse_self_other)
from .state import RunPaths, read_json, write_json


ASTRA_LABEL = "astra"
JUDGE_SLUG = "openai/gpt-6-astra"


@dataclass
class AstraFollowupTrial:
    trial_id: str
    true_source_identity: str        # SELF | OTHER
    actual_architecture: str         # batch | online
    stated_condition: str            # told_batch | told_online | no_provenance
    source_model_label: str          # astra | fable | qwen
    source_trajectory_id: str
    display_sequence: str
    trial_position: int              # 0..119
    construction_seed: int
    pair_key: str                    # groups the 3 versions of one trajectory


@dataclass
class AstraFollowupJudgmentRecord:
    trial_id: str
    true_source_identity: str
    actual_architecture: str
    stated_condition: str
    source_model_label: str
    source_trajectory_id: str
    sequence_display: str
    trial_position: int
    construction_seed: int
    pair_key: str
    prompt_text: str
    prompt_hash: str
    request_id: str
    requested_model: str
    served_model: str
    provider: str
    raw_completion: str
    parsed_judgment: str
    self_response: Optional[int]
    valid: bool
    correct: Optional[bool]
    attempts: int
    attempt_records: List[Dict] = field(default_factory=list)
    trial_status: str = "ok"
    total_cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    finish_reason: str = ""
    latency_ms: int = 0
    error_message: str = ""
    call_utc: str = ""


# --- source loading ------------------------------------------------------

def load_pilot4_sources(run_root: str) -> List[Tuple[str, str, str, str]]:
    """Load all valid pilot-4 source trajectories from disk.

    Returns list of (source_model_label, actual_architecture, trajectory_id, sequence).
    """
    out = []
    for arch in C.ARCHITECTURES:
        base = os.path.join(run_root, "source", arch)
        for m in C.MODELS:
            model_dir = os.path.join(base, m.label)
            if not os.path.isdir(model_dir):
                continue
            for fn in sorted(os.listdir(model_dir)):
                if not fn.endswith(".json") or ".steps." in fn:
                    continue
                rec = read_json(os.path.join(model_dir, fn))
                if rec and rec.get("valid"):
                    out.append((m.label, arch, rec["trajectory_id"], rec["parsed_sequence"]))
    return sorted(out, key=lambda x: (x[1], x[0], x[2]))


# --- trial construction ---------------------------------------------------

def _debunch(trials: List[AstraFollowupTrial], rng: random.Random,
             min_pair_sep: int = C.ASTRA_FOLLOWUP_MIN_REPEAT_SEPARATION,
             max_iter: int = 8000) -> List[AstraFollowupTrial]:
    """Enforce pair separation (each trajectory has 3 versions) + avoid long
    runs of same stated_condition / same identity (>3)."""
    def offense(seq):
        n = 0
        # each pair_key has 3 positions; penalize small gaps
        pos: Dict[str, List[int]] = {}
        for i, t in enumerate(seq):
            pos.setdefault(t.pair_key, []).append(i)
        for k, ps in pos.items():
            ps_sorted = sorted(ps)
            for a, b in zip(ps_sorted, ps_sorted[1:]):
                gap = b - a
                if gap < min_pair_sep:
                    n += (min_pair_sep - gap)
        # long-run offense
        for i in range(3, len(seq)):
            if all(seq[j].stated_condition == seq[i].stated_condition
                   for j in range(i - 3, i + 1)):
                n += 1
            if all(seq[j].true_source_identity == seq[i].true_source_identity
                   for j in range(i - 3, i + 1)):
                n += 1
        return n
    best = list(trials); best_off = offense(best)
    for _ in range(max_iter):
        if best_off == 0:
            break
        cand = list(best)
        i, j = rng.sample(range(len(cand)), 2)
        cand[i], cand[j] = cand[j], cand[i]
        o = offense(cand)
        if o < best_off:
            best, best_off = cand, o
    return best


def build_trials(sources: List[Tuple[str, str, str, str]],
                 construction_seed: int = C.ASTRA_FOLLOWUP_CONSTRUCTION_SEED
                 ) -> List[AstraFollowupTrial]:
    """Build 120 trials for Astra: 40 unique trajectories x 3 stated conditions."""
    # sanity: expect 20 astra + 20 non-astra
    n_astra = sum(1 for (ml, _, _, _) in sources if ml == ASTRA_LABEL)
    n_other = len(sources) - n_astra
    assert n_astra == 20, f"expected 20 astra sources, got {n_astra}"
    assert n_other == 20, f"expected 20 non-astra sources, got {n_other}"

    rng = random.Random(construction_seed)
    trials: List[AstraFollowupTrial] = []
    for (ml, arch, tid, seq) in sources:
        identity = "SELF" if ml == ASTRA_LABEL else "OTHER"
        pair_key = f"pilot4::{tid}"
        for stated in C.STATED_CONDITIONS:
            trials.append(AstraFollowupTrial(
                trial_id=str(uuid.uuid4()),
                true_source_identity=identity,
                actual_architecture=arch,
                stated_condition=stated,
                source_model_label=ml,
                source_trajectory_id=tid,
                display_sequence=seq,
                trial_position=-1,
                construction_seed=construction_seed,
                pair_key=pair_key,
            ))
    rng.shuffle(trials)
    trials = _debunch(trials, rng)
    for pos, t in enumerate(trials):
        t.trial_position = pos
    return trials


def judge_one_trial(client: OpenAI, accountant: CostAccountant,
                    trial: AstraFollowupTrial) -> AstraFollowupJudgmentRecord:
    prompt = C.astra_followup_prompt(trial.display_sequence, trial.stated_condition)
    attempts_meta = []
    parsed = None
    total_cost = 0.0
    last_res: Optional[APIResult] = None
    attempts = 0
    for attempt in range(1, C.ASTRA_FOLLOWUP_MAX_JUDGMENT_ATTEMPTS + 1):
        res = call_model(client, accountant,
                         kind="judgment_astra_followup", slug=JUDGE_SLUG,
                         prompt_text=prompt,
                         max_tokens=C.ASTRA_FOLLOWUP_MAX_TOKENS,
                         response_format=None)
        total_cost += res.cost_usd
        last_res = res
        attempts = attempt
        parsed = parse_self_other(res.response_text)
        attempts_meta.append({
            "attempt_no": attempt, "raw_completion": res.response_text,
            "parsed": parsed, "served_model": res.served_model, "provider": res.provider,
            "prompt_tokens": res.prompt_tokens, "completion_tokens": res.completion_tokens,
            "reasoning_tokens": res.reasoning_tokens, "finish_reason": res.finish_reason,
            "cost_usd": res.cost_usd, "latency_ms": res.latency_ms,
            "error_message": res.error_message,
            "call_utc": res.call_utc, "request_id": res.request_id,
        })
        if parsed is not None:
            break
    trial_status = "ok" if parsed is not None else "abandoned"
    self_response = None
    correct = None
    if parsed is not None:
        self_response = 1 if parsed == "SELF" else 0
        correct = (parsed == trial.true_source_identity)
    return AstraFollowupJudgmentRecord(
        trial_id=trial.trial_id, true_source_identity=trial.true_source_identity,
        actual_architecture=trial.actual_architecture,
        stated_condition=trial.stated_condition,
        source_model_label=trial.source_model_label,
        source_trajectory_id=trial.source_trajectory_id,
        sequence_display=trial.display_sequence,
        trial_position=trial.trial_position,
        construction_seed=trial.construction_seed,
        pair_key=trial.pair_key,
        prompt_text=prompt,
        prompt_hash=last_res.prompt_hash if last_res else "",
        request_id=last_res.request_id if last_res else "",
        requested_model=JUDGE_SLUG,
        served_model=last_res.served_model if last_res else "",
        provider=last_res.provider if last_res else "",
        raw_completion=last_res.response_text if last_res else "",
        parsed_judgment=parsed or "",
        self_response=self_response,
        valid=parsed is not None,
        correct=correct,
        attempts=attempts,
        attempt_records=attempts_meta,
        trial_status=trial_status,
        total_cost_usd=total_cost,
        prompt_tokens=last_res.prompt_tokens if last_res else 0,
        completion_tokens=last_res.completion_tokens if last_res else 0,
        reasoning_tokens=last_res.reasoning_tokens if last_res else 0,
        finish_reason=last_res.finish_reason if last_res else "",
        latency_ms=last_res.latency_ms if last_res else 0,
        error_message=last_res.error_message if last_res else "",
        call_utc=last_res.call_utc if last_res else "",
    )
