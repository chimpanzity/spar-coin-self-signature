"""Build paint-and-circle batch plans.

Usage:
    python -m paint_circle.plan pilot <batch_dir> <cost_cap_usd>
    python -m paint_circle.plan main  <batch_dir> <cost_cap_usd>
"""

from __future__ import annotations

import json
import os
import sys

from paint_circle import game, run

WINDOW = 50          # fixed by paint_circle/results/shadow_calibration.json
ROUNDS = 200


def session(model_a, model_b, d_a, d_b, k):
    return dict(session_id=f"{model_a}-{model_b}__A-{d_a or 'none'}__B-{d_b or 'none'}__s{k}",
                model_A=model_a, model_B=model_b, disclosure_A=d_a, disclosure_B=d_b,
                window=WINDOW, rounds=ROUNDS)


def pilot():
    return [session(m, m, None, None, 0) for m in ("qwen", "astra", "fable")]


# Same-model conditions: (A disclosure, B disclosure)
FACTORIAL = [(None, None), ("self", None), (None, "self"), ("self", "self")]
SPECIFICITY = [("other", None), ("agent", None)]          # false "other" label; existence only
NEGATIVE = [("salmon", None), ("program", None)]


def main_plan():
    """Priority order (sessions start in this order; the batch cost cap stops
    whatever is still running). Pilot cost per 200-round session, 2026-10-20:
    Astra ~$1.8, Fable ~$3.0, Qwen ~$0.01; planned total ~$90."""
    s = []
    # 1. Qwen: everything (cheap)
    for d_a, d_b in FACTORIAL + SPECIFICITY + NEGATIVE:
        s += [session("qwen", "qwen", d_a, d_b, k) for k in range(1, 7)]
    # 2. Astra factorial
    for d_a, d_b in FACTORIAL:
        s += [session("astra", "astra", d_a, d_b, k) for k in range(1, 5)]
    # 3. Fable core contrast (00 vs unilateral self)
    for d_a, d_b in [(None, None), ("self", None)]:
        s += [session("fable", "fable", d_a, d_b, k) for k in range(1, 4)]
    # 4. Cross-model Astra/Qwen: actual other x believed none / self / other
    for d in (None, "self", "other"):
        s += [session("astra", "qwen", d, None, k) for k in range(1, 4)]
        s += [session("qwen", "astra", d, None, k) for k in range(1, 4)]
    # 5. Astra specificity and negative control
    for d_a, d_b in SPECIFICITY:
        s += [session("astra", "astra", d_a, d_b, k) for k in range(1, 4)]
    s += [session("astra", "astra", "salmon", None, k) for k in range(1, 3)]
    # 6. Fable reciprocal and mutual disclosure
    for d_a, d_b in [(None, "self"), ("self", "self")]:
        s += [session("fable", "fable", d_a, d_b, k) for k in range(1, 3)]
    return s


def write(batch_dir, sessions, cap):
    os.makedirs(batch_dir, exist_ok=True)
    plan = dict(prompt_version=game.PROMPT_VERSION, window=WINDOW, rounds=ROUNDS,
                cost_cap_usd=cap, models=run.MODELS,
                system_prompts={f"{seat}|{d}": game.system_prompt(seat, d)
                                for seat in "AB" for d in game.DISCLOSURES},
                sessions=sessions)
    with open(os.path.join(batch_dir, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    print(f"{len(sessions)} sessions -> {batch_dir}")


if __name__ == "__main__":
    kind, batch_dir, cap = sys.argv[1], sys.argv[2], float(sys.argv[3])
    write(batch_dir, pilot() if kind == "pilot" else main_plan(), cap)
