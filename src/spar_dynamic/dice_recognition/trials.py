"""Held-out A/B recognition trials (handoff section 7). Runs only after the classifier gate passes.

Pairs: held-out Qwen and Mistral stimuli, each list sorted by id and shuffled with PAIR_SEED, zipped one to one
(no difficulty optimisation). Each pair is shown in both orientations (QA: Qwen as A; MA: Mistral as A) to both
judges under three conditions (self, named_qwen, named_mistral): 20 x 2 x 2 x 3 = 240 stateless calls. Truth: the
target source is the judge itself for `self`, otherwise the named model; the correct letter is the side holding
the target's sequence. Trial order is shuffled per judge with TRIAL_ORDER_SEED.
"""

from __future__ import annotations

import json
import os
import random

from spar_dynamic.dice_recognition import client as CL, config as C, prompts as P


def make_pairs(heldout):
    q = sorted([s for s in heldout if s["source"] == "qwen"], key=lambda s: s["stimulus_id"])
    m = sorted([s for s in heldout if s["source"] == "mistral"], key=lambda s: s["stimulus_id"])
    assert len(q) == len(m) == C.N_HOLDOUT
    rng = random.Random(C.PAIR_SEED)
    rng.shuffle(q)
    rng.shuffle(m)
    pairs = []
    for k, (a, b) in enumerate(zip(q, m), 1):
        assert a["sequence"] != b["sequence"]
        pairs.append(dict(pair_id=f"P{k:02d}", qwen_id=a["stimulus_id"], qwen_seq=a["sequence"],
                          mistral_id=b["stimulus_id"], mistral_seq=b["sequence"]))
    return pairs


def make_trials(pairs):
    trials = []
    for j_idx, judge in enumerate(C.SOURCES):
        rows = []
        for p in pairs:
            for orient in ("QA", "MA"):
                a_src, b_src = ("qwen", "mistral") if orient == "QA" else ("mistral", "qwen")
                seq = {"qwen": p["qwen_seq"], "mistral": p["mistral_seq"]}
                for cond in P.CONDITIONS:
                    target = judge if cond == "self" else cond.split("_", 1)[1]
                    rows.append(dict(trial_id=f"{judge}|{cond}|{p['pair_id']}|{orient}", judge=judge, condition=cond,
                                     pair_id=p["pair_id"], orientation=orient, A_source=a_src, B_source=b_src,
                                     sequence_A=seq[a_src], sequence_B=seq[b_src], target_source=target,
                                     correct="A" if a_src == target else "B",
                                     prompt=P.judgment_prompt(cond, seq[a_src], seq[b_src])))
        random.Random(C.TRIAL_ORDER_SEED + j_idx).shuffle(rows)
        for n, r in enumerate(rows, 1):
            r["order_index"] = n
        trials += rows
    return trials


def run(oai, ledger, trials, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "raw_attempts.jsonl")
    done = set()
    if os.path.exists(path):
        done = {json.loads(l)["trial_id"] for l in open(path, encoding="utf-8")}
    for t in trials:
        if t["trial_id"] in done:
            continue
        rec = CL.call(oai, ledger, t["judge"], t["prompt"], "judgment")
        choice = P.parse_choice(rec.get("content")) if rec.get("ok") and CL.thinking_clean(rec) and CL.provider_ok(rec) else None
        rec.update({k: v for k, v in t.items() if k != "prompt"}, prompt_text=t["prompt"], prompt_sha256=P.sha256(t["prompt"]),
                   choice=choice, valid=choice is not None, is_correct=(choice == t["correct"]) if choice else None)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        if rec.get("ok") and not CL.provider_ok(rec):
            raise SystemExit(f"STOP: judge {t['judge']} served by {rec.get('served_provider')}")
        print(f"[{t['judge']} {t['order_index']}/120] {t['trial_id']}: {rec.get('content')!r} -> {choice} "
              f"(correct {t['correct']}; spent ${ledger.spent:.4f})", flush=True)
