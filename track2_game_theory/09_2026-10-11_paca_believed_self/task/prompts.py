"""
prompts.py — system prompts and per-trial user message builder.

Do not edit the prompt strings without bumping PROMPT_VERSION; the version is
logged with every trial so prompt wording stays tied to the recorded data.
"""

PROMPT_VERSION = "paper1-v1"  # logged with every trial; bump if any prompt string changes

SYS_MINIMALIST = """Choose the shape that the blue circle will land on.

Available actions:
  TRIANGLE
  STAR

You may briefly think through your choice. End your response with the chosen action on its own line."""

SYS_INFORMED = """You are playing matching pennies against an exploitative opponent. Each round you and the opponent choose TRIANGLE or STAR. The blue circle lands on the opponent's chosen shape. As the matcher, you win if you choose that shape too, so choose the shape that the blue circle will land on.

The opponent analyzes your previous choices and tries to land the circle on whichever shape you don't choose. To prevent exploitation, you must choose TRIANGLE and STAR with equal probability (50/50) on each trial, with each choice independent of all previous choices, like flipping a fair coin. Patterns in your choices, such as alternation or repetition, can be detected and exploited.

Available actions:
  TRIANGLE
  STAR

You may briefly think through your choice. End your response with the chosen action on its own line."""


def get_system_prompt(prompt_mode: str) -> str:
    if prompt_mode == "minimalist":
        return SYS_MINIMALIST
    if prompt_mode == "informed":
        return SYS_INFORMED
    raise ValueError(f"Unknown prompt_mode: {prompt_mode!r} (use minimalist|informed)")


def build_prompt(history: list, desc_window: int, compact_window: int) -> str:
    """history: list of {'you','cpu'} in chronological order (completed trials)."""
    if len(history) == 0:
        return "No previous rounds yet.\n\nYour action:"

    desc_rounds = history[-desc_window:] if desc_window > 0 else []
    compact_rounds = history[-compact_window:] if compact_window > 0 else []

    parts = ["Previous rounds (oldest → most recent):"]
    for i, h in enumerate(desc_rounds):
        shape_word = "TRIANGLE" if h["you"] == "T" else "STAR"
        landed_word = "TRIANGLE" if h["cpu"] == "T" else "STAR"
        suffix = "  (most recent)" if i == len(desc_rounds) - 1 else ""
        parts.append(f"  You chose {shape_word} - blue circle landed on {landed_word}{suffix}")

    n = len(compact_rounds)
    choices_row = " ".join(h["you"] for h in compact_rounds)
    landed_row = " ".join(h["cpu"] for h in compact_rounds)
    choices_label = f"Your last {n} choice{'' if n == 1 else 's'}:"
    landed_label = "Blue circle landed on:"
    label_width = max(len(choices_label), len(landed_label)) + 2

    parts.append("")
    parts.append("(grid reads left to right, oldest → most recent)")
    parts.append(f"{choices_label.ljust(label_width)}{choices_row}")
    parts.append(f"{landed_label.ljust(label_width)}{landed_row}")
    parts.append("")
    parts.append("Your action:")
    return "\n".join(parts)
