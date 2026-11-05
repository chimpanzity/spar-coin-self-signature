"""Author messages (handoff section 2), verbatim, with TARGET_NAME and OBSERVER_PROMPT filled.

OBSERVER_PROMPT is the archived matching-pennies judge template rendered for the target judge with the anonymous identity
line and the condition-00 information line, exactly as in run btss-20261011, except that the completed-round history and the
upcoming round number are neutral placeholders. The history placeholder states the original rendering, including the
empty-history line, so the input contract matches what the observer saw. For a fixed target, both authors receive the same
bytes; across targets only the judge name (in TARGET_NAME and inside the observer prompt) differs.
"""
from __future__ import annotations

from typing import Dict

from blind_twin_forecast_prediction import config as C
from blind_twin_selfself import config as BT

HISTORY_PLACEHOLDER = ("[COMPLETED-ROUND HISTORY: the line \"None. This is the first round.\" if no round has been completed; "
                       "otherwise the line \"Round | Matcher (Player 1) | Mismatcher (Player 2) | Winner\" followed by one line per "
                       "completed round, oldest first, of the form \"<round> | <Player 1 choice> | <Player 2 choice> | <winner>\"]")
ROUND_PLACEHOLDER = "[UPCOMING ROUND]"

AUTHOR_TEMPLATE = """Write one deterministic Python function that predicts the forecasts made by TARGET_NAME when it serves as an independent observer of a 20-round matching-pennies game. The observer receives the instructions below. Its task is to predict both players’ next moves. Your task is to estimate the probability that this particular observer will answer STAR for each player. Its forecasts may be mistaken about the players.

BEGIN OBSERVER PROMPT
OBSERVER_PROMPT
END OBSERVER PROMPT

Implement predict(history). The input is a list of completed rounds, oldest first, with keys "round" (integer starting at 1), "p1" and "p2" ("STAR" or "TRIANGLE"), and "result" ("Matcher" or "Mismatcher"). An empty list is valid. The upcoming round is len(history) + 1. Return a pair (p_star_player_1, p_star_player_2) of finite numbers in [0, 1], in that order. Each answer will be scored by squared probability error against the observer’s reported choice.

Use pure Python and built-in arithmetic. Only the math module is available. Use only the supplied history. Write a single self-contained program, with no external calls, files, randomness, or persistent state. Return only the Python source."""


def observer_prompt(target: str) -> str:
    """The archived judge template (BT.JUDGE_TEMPLATE) for this judge, anonymous identities, condition-00 information."""
    return BT.JUDGE_TEMPLATE.format(RULES=BT.RULES["mp"], JUDGE_NAME=BT.MODELS[target]["name"], IDENTITY_SENTENCE=BT.IDENTITY_ANONYMOUS,
                                    INFO_SENTENCE=BT.INFO["00"], PUBLIC_HISTORY=HISTORY_PLACEHOLDER, T=ROUND_PLACEHOLDER,
                                    EXAMPLE=BT.EXAMPLE["mp"].format(), VALUES=BT.VALUES["mp"])


def author_message(target: str) -> str:
    return AUTHOR_TEMPLATE.replace("TARGET_NAME", BT.MODELS[target]["name"]).replace("OBSERVER_PROMPT", observer_prompt(target))


def messages() -> Dict[str, str]:
    """One message per target (sent identically to both authors)."""
    return {j: author_message(j) for j in C.TARGETS}


def request_body(author: str, target: str) -> dict:
    m = C.MODELS[author]
    return {"model": m["slug"], "messages": [{"role": "user", "content": author_message(target)}], "reasoning": dict(C.REASONING),
            "max_tokens": C.MAX_TOKENS, "provider": {"order": [m["provider"]], "allow_fallbacks": False}, "usage": {"include": True}}
