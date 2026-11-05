"""Author message (handoff section 2), verbatim, with TARGET_NAME, PLAYER_1_TEMPLATE and PLAYER_2_TEMPLATE filled.

The player templates are the original Study 1 matching-pennies prompt (`opponent_disclosure_mp_3models.config.GAME_TEMPLATE`)
for condition 00: the seat and role filled, the target's archived display name as the player's own model identity, the
uninformed opponent sentence, and the original response-format line. Only the completed-round history and the round number
are neutral slots; the history slot documents the original public rendering (EMPTY_HISTORY, HISTORY_HEADER, one row per
round). Substituting an actual rendered history and round reproduces game.player_prompt() byte for byte (tested).
For a fixed target the message is byte-identical across authors and generations.
"""
from __future__ import annotations

from typing import Dict

from blind_coder_player_choices import config as C
from opponent_disclosure_mp_3models import config as G

HISTORY_SLOT = (f"[COMPLETED-ROUND HISTORY: the line \"{G.EMPTY_HISTORY}\" if no round has been completed; otherwise the line "
                f"\"{G.HISTORY_HEADER}\" followed by one line per completed round, oldest first, of the form "
                "\"<round> | <Player 1 choice> | <Player 2 choice> | <winner>\"]")
ROUND_SLOT = "[UPCOMING ROUND]"
SEAT_NAME = {"p1": "Player 1", "p2": "Player 2"}

AUTHOR_TEMPLATE = """Write a Python function to predict the actual choices of TARGET_NAME when it plays the game described below. This player may occupy either seat. Here are the instructions it receives in each seat.

PLAYER_1_TEMPLATE

PLAYER_2_TEMPLATE

Implement predict(history, seat). The input history is a list of completed rounds, oldest first. Each row has "round" (integer starting at 1), "p1" and "p2" ("STAR" or "TRIANGLE"), and "result" ("Matcher" or "Mismatcher"). At round one the list is empty. The upcoming round is len(history) + 1. The seat argument is "p1" for the Matcher or "p2" for the Mismatcher.

Return one number between 0 and 1: the probability that TARGET_NAME, in the specified seat, will actually choose STAR on the upcoming round. Your prediction will be scored by squared error against the recorded choice.

Use deterministic, self-contained Python. Built-ins and the math module are available. Use only the supplied history and seat. No external calls, files, randomness or persistent state. Return only Python source."""


def player_template(seat: str, target: str) -> str:
    s = SEAT_NAME[seat]
    return G.GAME_TEMPLATE.format(SEAT=s, ROLE=G.ROLES[s], OWN_MODEL_NAME=G.MODELS[target]["name"], OPPONENT_IDENTITY_SENTENCE=G.UNINFORMED,
                                  PUBLIC_HISTORY=HISTORY_SLOT, T=ROUND_SLOT)


def author_message(target: str) -> str:
    return (AUTHOR_TEMPLATE.replace("PLAYER_1_TEMPLATE", player_template("p1", target))
            .replace("PLAYER_2_TEMPLATE", player_template("p2", target)).replace("TARGET_NAME", G.MODELS[target]["name"]))


def messages() -> Dict[str, str]:
    return {j: author_message(j) for j in C.TARGETS}


def request_body(author: str, target: str) -> dict:
    """Isolated request: no temperature, top_p or seed; no tools; pinned provider, no fallbacks; no cache directives."""
    m = C.MODELS[author]
    return {"model": m["slug"], "messages": [{"role": "user", "content": author_message(target)}], "reasoning": dict(C.REASONING),
            "max_tokens": C.MAX_TOKENS, "provider": {"order": [m["provider"]], "allow_fallbacks": False}, "usage": {"include": True}}
