"""Pilot 3 — Provenance-manipulation SELF/OTHER (2 x 2 x 2 design).

For every judge:
  * pick 20 SELF trajectories = all 10 SELF batch + all 10 SELF online
  * pick 20 OTHER trajectories = 5 from each non-self model per architecture
  * present each of those 40 trajectories twice, once told-batch, once told-online
  * total: 80 trials per judge = 8 cells x 10

Each judgment call is stateless; the two versions of a trajectory are never
adjacent in trial order (min separation = PROVENANCE_MIN_PAIR_SEPARATION).
"""

import os, random, uuid
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from . import config as C
from .api import (APIResult, CostAccountant, call_model, parse_self_other)
from .self_other import load_source_trajectories
from .state import RunPaths, read_json, write_json


@dataclass
class ProvenanceTrial:
    trial_id: str
    judge_label: str
    true_source_identity: str        # SELF | OTHER
    actual_architecture: str         # batch | online
    stated_architecture: str         # batch | online
    provenance_congruent: bool
    source_model_label: str
    source_trajectory_id: str
    display_sequence: str
    trial_position: int              # 0..79 within block after shuffle
    construction_seed: int
    pair_key: str                    # groups the two versions of the same trajectory


@dataclass
class ProvenanceJudgmentRecord:
    trial_id: str
    judge_label: str
    true_source_identity: str
    actual_architecture: str
    stated_architecture: str
    provenance_congruent: bool
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
    parsed_judgment: str             # SELF | OTHER | ""
    self_response: Optional[int]     # 1 if SELF, 0 if OTHER, None if abandoned
    valid: bool
    correct: Optional[bool]          # None if abandoned; True/False for SELF-vs-OTHER match
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
    response_mode: str = "chat"


def _debunch(trials: List[ProvenanceTrial], rng: random.Random,
             min_pair_sep: int = C.PROVENANCE_MIN_PAIR_SEPARATION,
             max_iter: int = 5000) -> List[ProvenanceTrial]:
    """Enforce:
       * two members of the same pair_key are not adjacent (and separated by
         at least min_pair_sep positions where possible)
       * no >3 consecutive identical stated_architecture or correct-answer runs
    """
    def offense(seq):
        n = 0
        # pair-separation offense
        pos: Dict[str, List[int]] = {}
        for i, t in enumerate(seq):
            pos.setdefault(t.pair_key, []).append(i)
        for k, ps in pos.items():
            if len(ps) >= 2:
                # penalty when the two are too close
                sep = ps[1] - ps[0]
                if sep < min_pair_sep:
                    n += (min_pair_sep - sep)
        # long-run offense (>3 same stated / same correct)
        for i in range(3, len(seq)):
            if all(seq[j].stated_architecture == seq[i].stated_architecture
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


def build_provenance_trials(source_trajectories: Dict[Tuple[str, str], List[Tuple[str, str, str]]],
                            construction_seed: int = C.PROVENANCE_CONSTRUCTION_SEED) -> List[ProvenanceTrial]:
    """Return 240 trials (80 per judge x 3 judges) covering the full 2x2x2 design."""
    trials: List[ProvenanceTrial] = []
    for judge in C.MODEL_LABELS:
        others = [m for m in C.MODEL_LABELS if m != judge]
        block_seed = (construction_seed + hash((judge, "provenance")) & 0xffffff)
        rng = random.Random(block_seed)

        # Assemble 40 unique trajectories per judge:
        #   10 SELF batch + 10 SELF online = 20 SELF (use all judge's own)
        #   5 from each non-self per architecture = 20 OTHER
        unique_trajectories: List[Tuple[str, str, str, str, str]] = []   # (identity, actual_arch, model_label, traj_id, seq)

        # SELF: use all 10 of judge's own per architecture
        for arch in C.ARCHITECTURES:
            self_pool = source_trajectories[(arch, judge)]
            assert len(self_pool) >= C.PROVENANCE_UNIQUE_TRAJECTORIES_PER_CELL, \
                f"insufficient SELF trajectories for {judge}/{arch}: {len(self_pool)}"
            for (m_label, tid, seq) in self_pool[:C.PROVENANCE_UNIQUE_TRAJECTORIES_PER_CELL]:
                unique_trajectories.append(("SELF", arch, m_label, tid, seq))

        # OTHER: 5 per non-self model per architecture (deterministic sample without replacement)
        for arch in C.ARCHITECTURES:
            for other_label in others:
                other_pool = source_trajectories[(arch, other_label)]
                assert len(other_pool) >= C.PROVENANCE_OTHER_FROM_EACH_NON_SELF_PER_ARCH, \
                    f"insufficient OTHER trajectories for {other_label}/{arch}: {len(other_pool)}"
                idx = rng.sample(range(len(other_pool)), C.PROVENANCE_OTHER_FROM_EACH_NON_SELF_PER_ARCH)
                for i in idx:
                    m_label, tid, seq = other_pool[i]
                    unique_trajectories.append(("OTHER", arch, m_label, tid, seq))

        # Duplicate each with told-batch AND told-online -> 80 trials
        block: List[ProvenanceTrial] = []
        for (identity, actual_arch, m_label, tid, seq) in unique_trajectories:
            pair_key = f"{judge}::{tid}"
            for stated in ("batch", "online"):
                block.append(ProvenanceTrial(
                    trial_id=str(uuid.uuid4()), judge_label=judge,
                    true_source_identity=identity,
                    actual_architecture=actual_arch,
                    stated_architecture=stated,
                    provenance_congruent=(actual_arch == stated),
                    source_model_label=m_label,
                    source_trajectory_id=tid,
                    display_sequence=seq,
                    trial_position=-1,
                    construction_seed=block_seed,
                    pair_key=pair_key,
                ))
        rng.shuffle(block)
        block = _debunch(block, rng)
        for pos, t in enumerate(block):
            t.trial_position = pos
        trials.extend(block)
    return trials


def judge_one_trial(client: OpenAI, accountant: CostAccountant,
                    trial: ProvenanceTrial, judge_slug: str) -> ProvenanceJudgmentRecord:
    prompt = C.provenance_prompt(trial.display_sequence, trial.stated_architecture)
    attempts_meta = []
    parsed = None
    total_cost = 0.0
    last_res: Optional[APIResult] = None
    attempts = 0
    for attempt in range(1, C.PROVENANCE_MAX_JUDGMENT_ATTEMPTS + 1):
        res = call_model(client, accountant,
                         kind="judgment_provenance", slug=judge_slug,
                         prompt_text=prompt,
                         max_tokens=C.PROVENANCE_MAX_TOKENS,
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
    return ProvenanceJudgmentRecord(
        trial_id=trial.trial_id, judge_label=trial.judge_label,
        true_source_identity=trial.true_source_identity,
        actual_architecture=trial.actual_architecture,
        stated_architecture=trial.stated_architecture,
        provenance_congruent=trial.provenance_congruent,
        source_model_label=trial.source_model_label,
        source_trajectory_id=trial.source_trajectory_id,
        sequence_display=trial.display_sequence,
        trial_position=trial.trial_position,
        construction_seed=trial.construction_seed,
        pair_key=trial.pair_key,
        prompt_text=prompt,
        prompt_hash=last_res.prompt_hash if last_res else "",
        request_id=last_res.request_id if last_res else "",
        requested_model=judge_slug,
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
        response_mode="chat",
    )
