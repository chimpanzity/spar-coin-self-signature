"""Paint-and-circle game: prompts, history rendering, parsing, scoring.

Player A places yellow paint (wins on match); Player B places the blue circle
(wins on mismatch). Both commit simultaneously each round. Both players
receive the SAME user message: a truthful record of past paint and circle
placements (no inverted histories, no seat-specific narration).

Prompts follow handoff 2026-10-20 §5.2 exactly. A disclosure, when present,
is one paragraph inserted after the instruction line:
    <existence sentence> <identity sentence>
or the existence sentence alone (the "agent" control).
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional

PROMPT_VERSION = "paint_circle-v1.0"

INSTRUCTION = {
    "A": "Place yellow paint on the shape where you think the blue circle will land.",
    "B": "Place the blue circle on the shape that will not receive yellow paint.",
}
TAIL = (
    "Available actions:\n"
    "TRIANGLE\n"
    "STAR\n"
    "\n"
    "You may briefly think through your choice. End your response with the chosen action on its own line."
)

EXISTENCE = {
    "A": "Another decision-maker decides where the blue circle lands.",
    "B": "Another decision-maker decides which shape receives the yellow paint.",
}
IDENTITY = {
    "self": "The other decision-maker is another instance of yourself, the same language model.",
    "other": "The other decision-maker is a different language model.",
    "salmon": "The other decision-maker is a dead salmon.",
    "program": "The other decision-maker is a random computer program.",
    # added 2026-10-22: separates "mindless" from "random" (experiment 16)
    "deterministic": "The other decision-maker is a deterministic computer program.",
}
DISCLOSURES = (None, "agent") + tuple(IDENTITY)

# Perspective-taking guidance for seat A (handoff 2026-10-21,
# "Fable perspective-taking"; version paint_circle-fable-perspective-v1.0).
# Inserted after the disclosure paragraph; identical in every guided cell.
GUIDANCE_VERSION = "paint_circle-fable-perspective-v1.0"
GUIDANCE_A = (
    "The other decision-maker is instructed: \"Place the blue circle on the shape that will not receive "
    "yellow paint.\" Before choosing your shape, consider what you would choose if you were in the other "
    "decision-maker's position, following that instruction and using the available history. Use that "
    "prediction to choose the shape where you expect the blue circle to land."
)


def system_prompt(seat: str, disclosure: Optional[str], guidance: bool = False) -> str:
    assert seat in INSTRUCTION and disclosure in DISCLOSURES
    assert not guidance or (seat == "A" and disclosure is not None), "guidance is defined for a disclosed seat A only"
    parts = [INSTRUCTION[seat]]
    if disclosure == "agent":
        parts.append(EXISTENCE[seat])
    elif disclosure is not None:
        parts.append(f"{EXISTENCE[seat]} {IDENTITY[disclosure]}")
    if guidance:
        parts.append(GUIDANCE_A)
    parts.append(TAIL)
    return "\n\n".join(parts)


def _name(c: str) -> str:
    return "TRIANGLE" if c == "T" else "STAR"


def render_history(paint: str, circle: str, window: int, n_verbal: int = 5) -> str:
    """User message for the next round. paint/circle: "T"/"S" per completed round."""
    assert len(paint) == len(circle)
    if not paint:
        return "No previous rounds yet.\n\nYour action:"
    lines = ["Previous rounds (oldest -> most recent):"]
    start = max(0, len(paint) - n_verbal)
    for i in range(start, len(paint)):
        row = f"Yellow paint placed on {_name(paint[i])} - blue circle landed on {_name(circle[i])}"
        if i == len(paint) - 1:
            row += " (most recent)"
        lines.append(row)
    p, c = paint[-window:], circle[-window:]
    lines += ["", "(grid reads left to right, oldest -> most recent)",
              "Yellow paint: " + " ".join(p),
              "Blue circle: " + " ".join(c),
              "", "Your action:"]
    return "\n".join(lines)


_CHOICE_RE = re.compile(r"\b(TRIANGLE|STAR)\b", re.I)


def _last_line(text: str) -> str:
    lines = [l.strip().strip("*`.\"'").upper() for l in (text or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


def parse_choice(text: str) -> Optional[str]:
    """PACA rule: the last TRIANGLE/STAR token anywhere in the response.

    Added 2026-10-20 after the pilot: a final line that is exactly the grid
    abbreviation "T" or "S" is also accepted (Qwen at temperature 0 answered
    "T" deterministically, so re-requesting could not recover). Flagged by
    abbreviated_choice().
    """
    m = _CHOICE_RE.findall(text or "")
    if m:
        return "T" if m[-1].upper() == "TRIANGLE" else "S"
    last = _last_line(text)
    return last if last in ("T", "S") else None


def abbreviated_choice(text: str) -> bool:
    return not _CHOICE_RE.search(text or "") and _last_line(text) in ("T", "S")


def strict_last_line(text: str) -> bool:
    lines = [l.strip().strip("*`.").upper() for l in (text or "").splitlines() if l.strip()]
    return bool(lines) and lines[-1] in ("TRIANGLE", "STAR")


def a_wins(paint: str, circle: str) -> bool:
    return paint == circle


def history_hash(paint: str, circle: str) -> str:
    return hashlib.sha256(f"{paint}|{circle}".encode()).hexdigest()[:16]
