"""RPS renderers. They accept PUBLIC history rows only (completed rounds)."""
from __future__ import annotations

from typing import Dict, Sequence

from . import config as C


def winner(a: str, b: str) -> str:
    if a == b:
        return "Tie"
    return "Player A" if C.BEATS[a] == b else "Player B"


def history_table(rows: Sequence[Dict]) -> str:
    if not rows:
        return C.EMPTY_HISTORY
    lines = ["| Round | Player A | Player B | Result |", "|---|---|---|---|"]
    for r in rows:
        res = "Tie" if r["winner"] == "Tie" else f"{r['winner']} wins"
        lines.append(f"| {r['round']} | {r['player_a']} | {r['player_b']} | {res} |")
    return "\n".join(lines)


def _check_prefix(rows: Sequence[Dict], t: int) -> None:
    assert len(rows) == t - 1, "history must contain exactly the rounds before round t"
    for i, r in enumerate(rows, 1):
        assert r["round"] == i and set(r) == {"round", "player_a", "player_b", "winner"}, "public rows only"


def player_prompt(role: str, rows: Sequence[Dict], t: int) -> str:
    _check_prefix(rows, t)
    tpl = C.PLAYER_A_TEMPLATE if role == "player_a" else C.PLAYER_B_TEMPLATE
    return tpl.format(SHARED_GAME_EXPLANATION=C.SHARED_GAME_EXPLANATION, PUBLIC_HISTORY=history_table(rows), T=t)


def identity_sentence(condition: str, a_model: str, b_model: str) -> str:
    if condition == "ANONYMOUS":
        return C.IDENTITY_ANONYMOUS
    if condition == "FALSE":
        a_model, b_model = C.other_model(a_model), C.other_model(b_model)
    return C.IDENTITY_KNOWN.format(player_a=C.MODELS[a_model]["display"], player_b=C.MODELS[b_model]["display"])


def judge_prompt(judge: str, condition: str, a_model: str, b_model: str, rows: Sequence[Dict], t: int) -> str:
    _check_prefix(rows, t)
    return C.JUDGE_TEMPLATE.format(SHARED_GAME_EXPLANATION=C.SHARED_GAME_EXPLANATION,
                                   JUDGE_IDENTITY=C.MODELS[judge]["display"],
                                   IDENTITY_SENTENCE=identity_sentence(condition, a_model, b_model),
                                   PUBLIC_HISTORY=history_table(rows), T=t)
