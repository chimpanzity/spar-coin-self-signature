"""Item construction, renderers, fixtures and slot plans (Sections 5.2, 5.4, 6, 7, 8).

Renderers receive only PUBLIC item fields. Gold relations, sources of
withheld items and suffixes live in private records and are joined at
scoring time. Allocation uses validity, split, prompt, source IDs and seeds
only, never behavioral content.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import config as C
from .client import Slot, build_messages, model_spec, request_params

# ---------------------------------------------------------------------------
# IDs and seeded helpers
# ---------------------------------------------------------------------------


def opaque_id(prefix: str, *parts: object) -> str:
    h = hashlib.sha256("|".join([C.PROTOCOL] + [str(p) for p in parts]).encode()).hexdigest()
    return f"{prefix}{h[:12]}"


def seeded_shuffle(items: Sequence[Any], *seed_parts: object) -> List[Any]:
    out = list(items)
    random.Random(C.derive_seed(*seed_parts)).shuffle(out)
    return out


def display(alias: str) -> str:
    return C.CORE_MODELS[alias].display


# ---------------------------------------------------------------------------
# Generation slots
# ---------------------------------------------------------------------------

def generation_slots(split: str) -> List[Slot]:
    n = C.DEV_ATTEMPTS_PER_CELL if split == "development" else C.TEST_ATTEMPTS_PER_CELL
    per_block = n // C.N_TIME_BLOCKS
    slots = []
    for alias in C.CORE_ORDER:
        spec = C.CORE_MODELS[alias]
        for pk in C.PROMPT_ORDER:
            for idx in range(n):
                block = idx // per_block
                sid = f"gen:{split}:{alias}:{pk}:{idx:03d}"
                smoke = split == "development" and idx < C.SMOKE_PER_CELL
                slots.append(Slot(
                    slot_id=sid, task="generation",
                    stage="stage1" if split == "development" else "stage2",
                    alias=alias, answer_kind="gen",
                    messages=build_messages(spec, C.GEN_PROMPTS[pk]),
                    params=request_params(spec, "generation"),
                    meta={"split": split, "source": alias, "prompt": pk, "idx": idx,
                          "time_block": block, "smoke": smoke,
                          "parent_id": opaque_id("P", split, alias, pk, idx)},
                    wave=(-1 if smoke else block)))
    # Scheduler order inside each wave is randomized with its own seed.
    order = {s.slot_id: i for i, s in enumerate(seeded_shuffle(slots, "scheduler", split))}
    slots.sort(key=lambda s: (s.wave, order[s.slot_id]))
    return slots


def historical_slots() -> List[Slot]:
    spec = C.HISTORICAL
    slots = []
    for pk in C.PROMPT_ORDER:
        for temp in C.HIST_TEMPERATURES:
            for b in range(C.N_TIME_BLOCKS):
                ids = ([("development", 6 * b + i) for i in range(6)]
                       + [("holdout", 4 * b + i) for i in range(4)])
                for split, idx in ids:
                    sid = f"hist:{split}:{pk}:t{temp}:{idx:03d}"
                    slots.append(Slot(
                        slot_id=sid, task="historical_generation", stage="retained",
                        alias=spec.alias, answer_kind="gen",
                        messages=build_messages(spec, C.GEN_PROMPTS[pk]),
                        params=request_params(spec, "generation", temperature_override=temp),
                        meta={"split": split, "source": spec.alias, "prompt": pk,
                              "temperature": temp, "idx": idx, "time_block": b,
                              "smoke": False,
                              "parent_id": opaque_id("H", split, pk, temp, idx)},
                        wave=b))
            cell = [s for s in slots if s.meta["prompt"] == pk and s.meta["temperature"] == temp]
            for s in cell[: C.SMOKE_PER_CELL]:
                s.meta["smoke"] = True
                s.wave = -1
    order = {s.slot_id: i for i, s in enumerate(seeded_shuffle(slots, "scheduler", "historical"))}
    slots.sort(key=lambda s: (s.wave, order[s.slot_id]))
    return slots


# ---------------------------------------------------------------------------
# Renderers (public fields only)
# ---------------------------------------------------------------------------

def render_completion(judge: str, candidate_order: Sequence[str], prompt_key: str,
                      first_ten: Optional[str], disclosed_source: Optional[str],
                      target: str = "H") -> str:
    cands = "\n".join(f"- {display(a)}" for a in candidate_order)
    info = (C.SOURCE_KNOWN.format(actual_source_name=display(disclosed_source))
            if disclosed_source else C.SOURCE_WITHHELD)
    if first_ten is None:
        return C.COMPLETION_PRIOR_TEMPLATE.format(
            judge_identity=display(judge), candidate_names_in_assigned_order=cands,
            generation_prompt=C.GEN_PROMPTS[prompt_key], source_information=info)
    assert len(first_ten) == C.PREFIX_LEN and set(first_ten) <= {"H", "T"}
    return C.COMPLETION_TEMPLATE.format(
        judge_identity=display(judge), candidate_names_in_assigned_order=cands,
        generation_prompt=C.GEN_PROMPTS[prompt_key], source_information=info,
        first_ten=first_ten, target_word=C.TARGET_WORDS[target])


def render_pair(prompt_key: str, seq1: Optional[str], seq2: Optional[str], polarity: str = "SAME") -> str:
    if seq1 is None:
        return C.PAIR_PRIOR_TEMPLATE.format(generation_prompt=C.GEN_PROMPTS[prompt_key],
                                            polarity_phrase=C.PAIR_POLARITY[polarity])
    return C.PAIR_TEMPLATE.format(generation_prompt=C.GEN_PROMPTS[prompt_key],
                                  sequence_1=seq1, sequence_2=seq2,
                                  polarity_phrase=C.PAIR_POLARITY[polarity])


def render_named(judge: str, prompt_key: str, sequence: Optional[str],
                 candidate_order: Sequence[str]) -> str:
    c = [display(a) for a in candidate_order]
    if sequence is None:
        return C.NAMED_PRIOR_TEMPLATE.format(judge_identity=display(judge),
                                             generation_prompt=C.GEN_PROMPTS[prompt_key],
                                             candidate_1=c[0], candidate_2=c[1], candidate_3=c[2])
    return C.NAMED_TEMPLATE.format(judge_identity=display(judge),
                                   generation_prompt=C.GEN_PROMPTS[prompt_key], sequence=sequence,
                                   candidate_1=c[0], candidate_2=c[1], candidate_3=c[2])


def judge_slot(slot_id: str, task: str, stage: str, judge: str, answer_kind: str,
               text: str, meta: Dict[str, Any], wave: int = 0) -> Slot:
    spec = C.CORE_MODELS[judge]
    return Slot(slot_id=slot_id, task=task, stage=stage, alias=judge, answer_kind=answer_kind,
                messages=build_messages(spec, text), params=request_params(spec, "judge"),
                meta={**meta, "judge": judge}, wave=wave)


# ---------------------------------------------------------------------------
# Objective fixtures (Section 5.2): invented codes, explicit rules
# ---------------------------------------------------------------------------

RULE_TEXT = {
    "ALLH": "every outcome is H",
    "ALT": "outcomes strictly alternate H, T, H, T, ... starting with H at position 1",
    "FAIR": "each outcome is an independent fair coin flip (probability 0.5 of H)",
}
CODE_POOL = ["Q7", "Z2", "B5", "K9", "M4", "R8", "X3", "J6", "V1", "N0", "W5", "L2"]


def _rule_lik(rule: str, seq: str) -> float:
    if rule == "ALLH":
        return 1.0 if set(seq) == {"H"} else 0.0
    if rule == "ALT":
        return 1.0 if all(c == ("H" if i % 2 == 0 else "T") for i, c in enumerate(seq)) else 0.0
    return 0.5 ** len(seq)


def _rule_next(rule: str, pos1: int) -> float:
    if rule == "ALLH":
        return 1.0
    if rule == "ALT":
        return 1.0 if pos1 % 2 == 1 else 0.0
    return 0.5


def _posterior(rules: Sequence[str], seq: str) -> List[float]:
    lik = [_rule_lik(r, seq) for r in rules]
    s = sum(lik)
    return [l / s for l in lik]


def _fair_looking(rng: random.Random, n: int) -> str:
    while True:
        s = "".join(rng.choice("HT") for _ in range(n))
        if _rule_lik("ALLH", s) == 0 and _rule_lik("ALT", s) == 0:
            return s


FIX_COMPLETION = """You are {judge_identity}.

This is a format and reasoning check that uses invented sources whose behavior
is fully specified. Use equal prior probabilities for the candidate sources.

Candidate sources:
{lines}

Source information: {info}

One candidate source produced 20 outcomes. Only its first 10 are shown:
{prefix}

Predict the outcomes at positions 11 through 20. For each position, report the
probability that the outcome was heads (H), conditioned only on the first 10
outcomes and the rules above.

Return only a JSON array of 10 numbers between 0 and 1, in chronological order.
Do not include an explanation."""

FIX_PAIR = """This is a format and reasoning check that uses invented sources whose
behavior is fully specified.

Each of the two sequences below was produced by one of these sources:
{lines}

The producing source was either the same for both sequences or different.
Before considering the sequences, use equal prior probabilities for these cases,
and when sources differ, every ordered pair of distinct sources is equally likely.

Sequence 1:
{s1}

Sequence 2:
{s2}

Report the probability that the same source produced both sequences.
Return only a number between 0 and 1. Do not include an explanation."""

FIX_NAMED = """You are {judge_identity}.

This is a format and reasoning check that uses invented sources whose behavior
is fully specified. One of the candidates produced the sequence below. Use equal
prior probabilities for the three candidates.

Sequence:
{seq}

Candidate sources:
C1: Source {c1} ({r1})
C2: Source {c2} ({r2})
C3: Source {c3} ({r3})

Return only a JSON object with keys "C1", "C2", and "C3". Each probability
must be between 0 and 1, and the three probabilities must sum to 1.
Do not include an explanation."""


def completion_fixtures(judge: str) -> List[Tuple[Slot, Dict[str, Any]]]:
    out = []
    rng = random.Random(C.derive_seed("fixtures", "completion", judge))
    k = 0
    for rule in ("ALLH", "ALT", "FAIR"):
        for cond in ("known", "withheld"):
            for variant in range(2):
                rules = seeded_shuffle(["ALLH", "ALT", "FAIR"], "fixorder", judge, rule, cond, variant)
                codes = rng.sample(CODE_POOL, 3)
                code_of = dict(zip(rules, codes))
                prefix = {"ALLH": "H" * 10, "ALT": "HT" * 5, "FAIR": _fair_looking(rng, 10)}[rule]
                if cond == "known":
                    truth = [_rule_next(rule, t) for t in range(11, 21)]
                    info = f"The generating source was Source {code_of[rule]}."
                else:
                    post = _posterior(rules, prefix)
                    truth = [sum(q * _rule_next(r, t) for q, r in zip(post, rules)) for t in range(11, 21)]
                    info = "The generating source's identity is not disclosed."
                lines = "\n".join(f"- Source {code_of[r]}: {RULE_TEXT[r]}" for r in rules)
                text = FIX_COMPLETION.format(judge_identity=display(judge), lines=lines, info=info, prefix=prefix)
                sid = f"fix:completion:{judge}:{k:02d}"
                out.append((judge_slot(sid, "fixture_completion", "stage1", judge, "array10", text,
                                       {"fixture": k, "rule": rule, "condition": cond}),
                            {"slot_id": sid, "truth": truth, "rule": rule, "condition": cond}))
                k += 1
    return out


def pair_fixtures(judge: str) -> List[Tuple[Slot, Dict[str, Any]]]:
    rng = random.Random(C.derive_seed("fixtures", "pair", judge))
    cases = [("ALLH", "ALLH"), ("ALT", "ALT"), ("FAIR", "FAIR"), ("ALLH", "ALLH"), ("FAIR", "FAIR"),
             ("ALLH", "ALT"), ("ALLH", "FAIR"), ("ALT", "FAIR"), ("FAIR", "ALT"), ("ALT", "ALLH"),
             ("ALLFAIR", "ALLFAIR"), ("ALLFAIR", "ALLFAIR")]
    out = []
    for k, (a, b) in enumerate(cases):
        codes = rng.sample(CODE_POOL, 3)
        if a == "ALLFAIR":
            rules = ["FAIR", "FAIR", "FAIR"]
            s1, s2 = _fair_looking(rng, 20), _fair_looking(rng, 20)
        else:
            rules = seeded_shuffle(["ALLH", "ALT", "FAIR"], "pairfix", judge, k)
            gen = lambda r: {"ALLH": "H" * 20, "ALT": "HT" * 10, "FAIR": _fair_looking(rng, 20)}[r]
            s1, s2 = gen(a), gen(b)
        q1, q2 = _posterior(rules, s1), _posterior(rules, s2)
        s = sum(x * y for x, y in zip(q1, q2))
        truth = 2 * s / (1 + s)
        lines = "\n".join(f"- Source {c}: {RULE_TEXT[r]}" for c, r in zip(codes, rules))
        text = FIX_PAIR.format(lines=lines, s1=s1, s2=s2)
        sid = f"fix:pair:{judge}:{k:02d}"
        out.append((judge_slot(sid, "fixture_pair", "stage1", judge, "scalar", text, {"fixture": k}),
                    {"slot_id": sid, "truth": truth, "case": f"{a}-{b}"}))
    return out


def named_fixtures(judge: str) -> List[Tuple[Slot, Dict[str, Any]]]:
    rng = random.Random(C.derive_seed("fixtures", "named", judge))
    out = []
    orders = C.candidate_orders()
    seq_rules = ["ALLH", "ALT", "FAIR", "ALLH", "ALT", "FAIR"]
    base = ("ALLH", "ALT", "FAIR")
    for k in range(C.N_NAMED_FIXTURES):
        perm = [base[C.CORE_ORDER.index(a)] for a in orders[k]]
        codes = rng.sample(CODE_POOL, 3)
        rule = seq_rules[k]
        seq = {"ALLH": "H" * 20, "ALT": "HT" * 10, "FAIR": _fair_looking(rng, 20)}[rule]
        post = _posterior(perm, seq)
        text = FIX_NAMED.format(judge_identity=display(judge), seq=seq,
                                c1=codes[0], c2=codes[1], c3=codes[2],
                                r1=RULE_TEXT[perm[0]], r2=RULE_TEXT[perm[1]], r3=RULE_TEXT[perm[2]])
        sid = f"fix:named:{judge}:{k:02d}"
        out.append((judge_slot(sid, "fixture_named", "retained", judge, "named3", text, {"fixture": k}),
                    {"slot_id": sid, "truth": {"C1": post[0], "C2": post[1], "C3": post[2]}, "rule": rule}))
    return out


def score_fixture(kind: str, truth: Any, value: Any) -> bool:
    tol = C.FIXTURE_TOLERANCE
    if kind == "array10":
        return max(abs(a - b) for a, b in zip(truth, value)) <= tol
    if kind == "scalar":
        return abs(truth - value) <= tol
    if kind == "named3":
        best = max(truth, key=truth.get)
        return value[best] >= 1 - tol
    raise ValueError(kind)


# ---------------------------------------------------------------------------
# Pair blocks (Section 7.1)
# ---------------------------------------------------------------------------

@dataclass
class PairItem:
    pair_id: str
    block_id: str
    prompt: str
    split: str
    first: str      # parent id shown as Sequence 1 in the designated order
    second: str
    relation: str   # SAME|DIFFERENT   (private)
    src_first: str  # private
    src_second: str  # private


def build_pair_blocks(valid: Dict[str, List[str]], split: str, prompt: str) -> Tuple[List[Dict[str, Any]], List[PairItem]]:
    """valid: source alias -> list of valid parent ids (any order).

    Returns block records and pair items. Content is never consulted.
    """
    pools = {g: seeded_shuffle(sorted(valid.get(g, [])), "pairpool", split, prompt, g) for g in C.CORE_ORDER}
    B = min(len(pools[g]) // 2 for g in C.CORE_ORDER)
    reversed_blocks = set(seeded_shuffle(list(range(B)), "cycle_reverse", split, prompt)[: B // 2])
    blocks, pairs = [], []
    A, Bm, Cm = C.CORE_ORDER
    for k in range(B):
        par = {f"{tag}{i + 1}": pools[g][2 * k + i] for tag, g in (("A", A), ("B", Bm), ("C", Cm)) for i in range(2)}
        src = {f"{tag}{i + 1}": g for tag, g in (("A", A), ("B", Bm), ("C", Cm)) for i in range(2)}
        cycle = ["A1", "A2", "C1", "C2", "B2", "B1"]
        edges = [(cycle[i], cycle[(i + 1) % 6]) for i in range(6)]
        if k in reversed_blocks:
            edges = [(b, a) for a, b in edges]
        bid = opaque_id("BLK", split, prompt, k)
        blocks.append({"block_id": bid, "split": split, "prompt": prompt, "index": k,
                       "parents": par, "cycle_reversed": k in reversed_blocks})
        for x, y in edges:
            rel = "SAME" if src[x] == src[y] else "DIFFERENT"
            pairs.append(PairItem(pair_id=opaque_id("PR", bid, x, y), block_id=bid, prompt=prompt, split=split,
                                  first=par[x], second=par[y], relation=rel,
                                  src_first=src[x], src_second=src[y]))
    return blocks, pairs


# ---------------------------------------------------------------------------
# Completion allocation (Section 6.2)
# ---------------------------------------------------------------------------

def allocate_completion(valid: Dict[Tuple[str, str], List[str]], split: str) -> Dict[str, Dict[str, Any]]:
    """valid[(source, prompt)] -> parent ids. Returns parent_id -> {order_index, first_condition}."""
    orders = C.candidate_orders()
    alloc = {}
    for (g, p), pids in valid.items():
        sh = seeded_shuffle(sorted(pids), "completion_alloc", split, g, p)
        for i, pid in enumerate(sh):
            oi = i % len(orders)
            within = i // len(orders)
            alloc[pid] = {"order_index": oi, "candidate_order": list(orders[oi]),
                          "first_condition": "known" if within % 2 == 0 else "withheld"}
    return alloc


def completion_slots(parents: List[Dict[str, Any]], alloc: Dict[str, Dict[str, Any]], task: str,
                     stage: str, target: str = "H", tag: str = "") -> List[Slot]:
    """parents: dicts with parent_id, prompt, first_ten and PRIVATE source (used only
    to fill the disclosed sentence in the known condition)."""
    slots = []
    for par in parents:
        a = alloc[par["parent_id"]]
        for judge in C.CORE_ORDER:
            for cond in ("known", "withheld"):
                text = render_completion(judge, a["candidate_order"], par["prompt"], par["first_ten"],
                                         par["source"] if cond == "known" else None, target)
                wave = 0 if cond == a["first_condition"] else 1
                sid = f"{task}{tag}:{par['parent_id']}:{judge}:{cond}"
                slots.append(judge_slot(sid, task, stage, judge, "array10", text,
                                        {"parent_id": par["parent_id"], "condition": cond, "target": target,
                                         "order_index": a["order_index"], "prompt": par["prompt"]}, wave))
    order = {s.slot_id: i for i, s in enumerate(seeded_shuffle(slots, "scheduler", task, tag))}
    slots.sort(key=lambda s: (s.wave, order[s.slot_id]))
    return slots


def pair_slots(pairs: List[PairItem], seqs: Dict[str, str], task: str, stage: str,
               orders: Sequence[str] = ("designated", "swapped"), polarity: str = "SAME", tag: str = "") -> List[Slot]:
    slots = []
    for it in pairs:
        for o in orders:
            a, b = (it.first, it.second) if o == "designated" else (it.second, it.first)
            text = render_pair(it.prompt, seqs[a], seqs[b], polarity)
            for judge in C.CORE_ORDER:
                sid = f"{task}{tag}:{it.pair_id}:{o}:{judge}"
                slots.append(judge_slot(sid, task, stage, judge, "scalar", text,
                                        {"pair_id": it.pair_id, "order": o, "polarity": polarity,
                                         "prompt": it.prompt, "block_id": it.block_id}))
    order = {s.slot_id: i for i, s in enumerate(seeded_shuffle(slots, "scheduler", task, tag))}
    slots.sort(key=lambda s: order[s.slot_id])
    return slots


def completion_prior_slots() -> List[Slot]:
    slots = []
    order0 = C.candidate_orders()[0]
    for judge in C.CORE_ORDER:
        for p in C.PROMPT_ORDER:
            for src in list(C.CORE_ORDER) + [None]:
                text = render_completion(judge, order0, p, None, src)
                sid = f"completion_prior:{judge}:{p}:{src or 'withheld'}"
                slots.append(judge_slot(sid, "completion_prior", "stage2", judge, "array10", text,
                                        {"prompt": p, "condition": "known" if src else "withheld",
                                         "disclosed": src, "order_index": 0}))
    return slots


def pair_prior_slots() -> List[Slot]:
    slots = []
    for judge in C.CORE_ORDER:
        for p in C.PROMPT_ORDER:
            for pol in ("SAME", "DIFFERENT"):
                sid = f"pair_prior:{judge}:{p}:{pol}"
                slots.append(judge_slot(sid, "pair_prior", "stage2", judge, "scalar",
                                        render_pair(p, None, None, pol), {"prompt": p, "polarity": pol}))
    return slots


def named_slots(parents: List[Dict[str, Any]], order_of: Dict[str, int]) -> List[Slot]:
    orders = C.candidate_orders()
    slots = []
    for par in parents:
        oi = order_of[par["parent_id"]]
        for judge in C.CORE_ORDER:
            text = render_named(judge, par["prompt"], par["sequence"], orders[oi])
            sid = f"named:{par['parent_id']}:{judge}"
            slots.append(judge_slot(sid, "named", "retained", judge, "named3", text,
                                    {"parent_id": par["parent_id"], "order_index": oi, "prompt": par["prompt"]}))
    order = {s.slot_id: i for i, s in enumerate(seeded_shuffle(slots, "scheduler", "named"))}
    slots.sort(key=lambda s: order[s.slot_id])
    return slots


def named_prior_slots() -> List[Slot]:
    slots = []
    for judge in C.CORE_ORDER:
        for p in C.PROMPT_ORDER:
            for oi, o in enumerate(C.candidate_orders()):
                sid = f"named_prior:{judge}:{p}:{oi}"
                slots.append(judge_slot(sid, "named_prior", "retained", judge, "named3",
                                        render_named(judge, p, None, o), {"prompt": p, "order_index": oi}))
    return slots
