"""Frozen v2.1 prompts (handoff 4.1).

The question bodies are Experiment 23's frozen templates, imported unchanged from dice_recognition_v2.prompts. Each
v2.0 template ends with "\\n{answer_instruction}"; v2.1 fills that slot with the one-letter ENDING instead of the v2.0
bare or brief instruction. So every rendered prompt is the v2.0 question body, a newline, then ENDING, with no
trailing newline. Nothing else changes; the two orientations of an item differ only in which sequence fills A.
"""

from __future__ import annotations

from spar_dynamic.dice_recognition_v2 import prompts as V2

ENDING = "Reply with exactly one capital letter: A or B."

# Technical preflight only (handoff 5.4): a content-free A/B check, never scored scientifically.
GENERIC = ("Option A: 2 + 2 = 4\nOption B: 2 + 2 = 5\n\n"
           "Which option is arithmetically correct?\n" + ENDING)

sha256 = V2.sha256


def calibration(task: str, a: str, b: str) -> str:
    return V2._fill(V2.CAL[task], A=a, B=b, answer_instruction=ENDING)


def frame(name: str, a: str, b: str) -> str:
    """AUTH or TYP with one ten-roll sequence per sample (K = 1, no examples)."""
    return V2._fill(V2.AUTH if name == "AUTH" else V2.TYP, blocks_A=V2.blocks([a]), blocks_B=V2.blocks([b]),
                    answer_instruction=ENDING)


def named(a: str, b: str, name_order: str) -> str:
    """v2.0 NAMED, target Qwen3-32B; name_order QM lists Qwen first, MQ lists Mistral first."""
    order = ("qwen", "mistral") if name_order == "QM" else ("mistral", "qwen")
    return V2._fill(V2.NAMED, NAME_1=V2.NAMES[order[0]], NAME_2=V2.NAMES[order[1]], TARGET_MODEL=V2.NAMES["qwen"],
                    blocks_A=V2.blocks([a]), blocks_B=V2.blocks([b]), answer_instruction=ENDING)


def templates() -> dict:
    t = {"ENDING": ENDING, "GENERIC_preflight": GENERIC, "AUTH": V2.AUTH, "TYP": V2.TYP, "NAMED": V2.NAMED}
    t.update({f"CAL_{k}": v for k, v in V2.CAL.items()})
    return t
