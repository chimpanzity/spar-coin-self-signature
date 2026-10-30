"""Stage A synthetic calibration items (handoff section 4). Deterministic under SEEDS['calibration_items'].

MORE_SIXES: two uniform 10-roll sequences whose counts of 6 differ by 1-3, neither with more than five 6s.
MORE_REPEATS: two 10-roll Markov sequences (repeat probability drawn per sequence from U(0.1, 0.5)) whose
    adjacent-repeat counts differ by 1-3, longest run at most 4 (no caricatures).
GEN_RULE: one sequence from Generator R (repeat previous face with p=0.70, otherwise a uniform different face)
    and one from Generator S (p=0.05); same length L ~ U{10..20} within a pair. Kept only if R shows at least one
    switch (an exception), and R has strictly more adjacent repeats than S, so the provenance answer is also the
    content answer.
Each item stores sequence X (the correct one: more 6s / more repeats / from R) and Y. Duplicates are rejected.
"""

from __future__ import annotations

import random

from spar_dynamic.dice_recognition_v2 import config as C


def n_sixes(seq):
    return sum(f == 6 for f in seq)


def n_repeats(seq):
    return sum(a == b for a, b in zip(seq, seq[1:]))


def max_run(seq):
    run = best = 1
    for a, b in zip(seq, seq[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


def markov(rng, n, p_repeat):
    s = [rng.randint(1, 6)]
    while len(s) < n:
        s.append(s[-1] if rng.random() < p_repeat else rng.choice([f for f in range(1, 7) if f != s[-1]]))
    return s


def _fmt(seq):
    return " ".join(map(str, seq))


def make_items(seed=C.SEEDS["calibration_items"], n=C.N_CAL_ITEMS):
    rng = random.Random(seed)
    items, seen = [], set()

    def add(task, x, y, **meta):
        key = (_fmt(x), _fmt(y))
        if key[0] == key[1] or key in seen:
            return False
        seen.add(key)
        k = sum(i["task"] == task for i in items) + 1
        items.append(dict(item_id=f"{task}-{k:02d}", task=task, X=_fmt(x), Y=_fmt(y), length=len(x), **meta))
        return True

    while sum(i["task"] == "MORE_SIXES" for i in items) < n:
        x, y = [rng.randint(1, 6) for _ in range(10)], [rng.randint(1, 6) for _ in range(10)]
        if n_sixes(x) < n_sixes(y):
            x, y = y, x
        if 1 <= n_sixes(x) - n_sixes(y) <= 3 and n_sixes(x) <= 5:
            add("MORE_SIXES", x, y, X_value=n_sixes(x), Y_value=n_sixes(y))
    while sum(i["task"] == "MORE_REPEATS" for i in items) < n:
        x, y = markov(rng, 10, rng.uniform(0.1, 0.5)), markov(rng, 10, rng.uniform(0.1, 0.5))
        if n_repeats(x) < n_repeats(y):
            x, y = y, x
        if 1 <= n_repeats(x) - n_repeats(y) <= 3 and max(max_run(x), max_run(y)) <= 4:
            add("MORE_REPEATS", x, y, X_value=n_repeats(x), Y_value=n_repeats(y))
    while sum(i["task"] == "GEN_RULE" for i in items) < n:
        L = rng.randint(*C.RULE_LEN)
        r, s = markov(rng, L, C.RULE_R_REPEAT), markov(rng, L, C.RULE_S_REPEAT)
        if n_repeats(r) > n_repeats(s) and n_repeats(r) < L - 1:
            add("GEN_RULE", r, s, X_value=n_repeats(r), Y_value=n_repeats(s))
    return items


def correct_side(item):
    """Recompute the correct candidate from content alone (X or Y), independent of how the item was built."""
    x, y = [int(v) for v in item["X"].split()], [int(v) for v in item["Y"].split()]
    f = n_sixes if item["task"] == "MORE_SIXES" else n_repeats
    return "X" if f(x) > f(y) else "Y" if f(y) > f(x) else None
