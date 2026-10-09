"""Renderers. They accept PUBLIC history rows only (completed rounds)."""
from __future__ import annotations

from typing import Dict, List, Sequence

from . import config as C


def winner(matcher_choice: str, mismatcher_choice: str) -> str:
    return "Matcher" if matcher_choice == mismatcher_choice else "Mismatcher"


def history_table(rows: Sequence[Dict]) -> str:
    """rows: completed rounds [{'round', 'matcher', 'mismatcher', 'winner'}], chronological."""
    if not rows:
        return C.EMPTY_HISTORY
    lines = ["| Round | Matcher | Mismatcher | Winner |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['round']} | {r['matcher']} | {r['mismatcher']} | {r['winner']} |")
    return "\n".join(lines)


def _check_prefix(rows: Sequence[Dict], t: int) -> None:
    assert len(rows) == t - 1, "history must contain exactly the rounds before round t"
    for i, r in enumerate(rows, 1):
        assert r["round"] == i and set(r) == {"round", "matcher", "mismatcher", "winner"}, "public rows only"


def player_prompt(role: str, rows: Sequence[Dict], t: int) -> str:
    _check_prefix(rows, t)
    tpl = C.MATCHER_TEMPLATE if role == "matcher" else C.MISMATCHER_TEMPLATE
    return tpl.format(SHARED_GAME_EXPLANATION=C.SHARED_GAME_EXPLANATION,
                      PUBLIC_HISTORY=history_table(rows), T=t)


def identity_sentence(condition: str, matcher_model: str, mismatcher_model: str) -> str:
    if condition == "ANONYMOUS":
        return C.IDENTITY_ANONYMOUS
    if condition == "FALSE":
        matcher_model, mismatcher_model = C.other_model(matcher_model), C.other_model(mismatcher_model)
    return C.IDENTITY_KNOWN.format(matcher=C.MODELS[matcher_model]["display"],
                                   mismatcher=C.MODELS[mismatcher_model]["display"])


def judge_prompt(judge: str, condition: str, matcher_model: str, mismatcher_model: str,
                 rows: Sequence[Dict], t: int) -> str:
    _check_prefix(rows, t)
    return C.JUDGE_TEMPLATE.format(SHARED_GAME_EXPLANATION=C.SHARED_GAME_EXPLANATION,
                                   JUDGE_IDENTITY=C.MODELS[judge]["display"],
                                   IDENTITY_SENTENCE=identity_sentence(condition, matcher_model, mismatcher_model),
                                   PUBLIC_HISTORY=history_table(rows), T=t)
