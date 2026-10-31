"""Frozen prompts for SPAR_CROSSED_GUIDED_SELFPRED_v1.0.

Archival prompts are imported unchanged: Experiment 21's G (direct generation), F (full hypothetical self-prediction)
and N ("another language model" control), and Experiment 26's twelve H/N/S/O prompts (Qwen predictor on Qwen's G only;
their "another instance of your model" wording is false for any other cell).

The crossed prompts are one template with three slots that vary independently:

  framing   A  "A language model was given ..."                               (no identity)
            T  "The language model <true target name> was given ..."         (identity cue)
            R  "Another instance of your own model was given ..."            (diagonal cells)
               "A different model, not your own model, was given ..."       (off-diagonal cells)
  evidence  H  nothing more
            I  a length-matched paragraph with no information about the response (prompt-perturbation control)
            D  a separate earlier response by "that same model" to the exact instruction, drawn from the target model's
               reference corpus (never a scored target), plus a sentence saying it is not the response being predicted
  history   the condition's revealed prefix (and, for m3, an explicit note that positions 4-6 are hidden)

Every attribution is true for the cell it is used in; the D paragraph's source is the header's model, so D under A is
the model-unspecified observation and D under T or R is the attributed one, with identical text.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List

from spar_dynamic.dice_crossed_guidance import config as C
from spar_dynamic.dice_logprob import prompts as P21
from spar_dynamic.dice_prefix_declarative import prompts as P26

GEN = P21.GEN
WORDS = {2: "two", 3: "three", 6: "six", 8: "eight"}

HEADER = {"A": "A language model was given the following instruction:",
          "T": "The language model {NAME} was given the following instruction:",
          "R_self": "Another instance of your own model was given the following instruction:",
          "R_other": "A different model, not your own model, was given the following instruction:"}
PARAGRAPH = {"I": ("For reference, a standard six-sided die has six faces, numbered one to six, and the numbers on its "
                   "opposite faces add up to seven.\nThat general fact is not about the response you are predicting."),
             "D": ("For reference, a separate earlier response by that same model to this exact instruction was:\n{REF}\n"
                   "That earlier response is not the response you are predicting.")}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seq_str(seq) -> str:
    return " ".join(map(str, seq))


def header(framing: str, predictor: str, target_model: str) -> str:
    if framing == "A":
        return HEADER["A"]
    if framing == "T":
        return HEADER["T"].format(NAME=C.MODEL[target_model]["name"])
    return HEADER["R_self" if predictor == target_model else "R_other"]


def reveal(cond: str, seq) -> str:
    r = C.CONDITIONS[cond]["reveal"]
    if r == 0:
        return "None of the ten integers in that model's response has been revealed to you."
    line = f"The first {WORDS[r]} integers in that model's response (positions 1 through {r}) were: {seq_str(seq[:r])}"
    first = C.CONDITIONS[cond]["positions"][0]
    if first > r + 1:
        line += f"\nThe integers at positions {r + 1} through {first - 1} are not revealed to you."
    return line


def ask(cond: str) -> str:
    pos = C.CONDITIONS[cond]["positions"]
    return (f"Predict the integers at positions {pos[0]} through {pos[-1]} of that same ten-integer response, in their "
            f"original order. Do not report any other positions. Return exactly {WORDS[len(pos)]} integers from 1 to 6, "
            "separated by single spaces, with no other text.")


def paragraph(evidence: str, ref_seq) -> str:
    if evidence == "H":
        return ""
    return PARAGRAPH[evidence].format(REF=seq_str(ref_seq) if ref_seq is not None else "")


def prompt(framing: str, evidence: str, cond: str, predictor: str, target_model: str, seq, ref_seq=None) -> str:
    assert framing in C.FRAMINGS and evidence in C.EVIDENCE and cond in C.CONDITIONS
    assert evidence != "D" or ref_seq is not None
    parts = [header(framing, predictor, target_model), GEN, reveal(cond, seq)]
    if evidence != "H":
        parts.append(paragraph(evidence, ref_seq))
    parts.append(ask(cond))
    return "\n\n".join(parts)


def references() -> Dict[str, Dict]:
    """Experiment 21's G, F and generic-model N prompts, byte-identical (hash-asserted)."""
    g, f, n = P21.prompt_g(), P21.prompt_f(), P21.prompt_n()
    assert sha256(g) == C.G_PROMPT_SHA256 and sha256(f) == C.F_PROMPT_SHA256
    return {"G": dict(condition="G", prompt=g, prompt_sha256=sha256(g)),
            "F": dict(condition="F", prompt=f, prompt_sha256=sha256(f)),
            "Fanon": dict(condition="Fanon", prompt=n, prompt_sha256=sha256(n))}


def archival26() -> List[Dict]:
    """Experiment 26's twelve prompts (Qwen predictor, Qwen's G reference), unchanged."""
    return [dict(c, condition=f"x26_{c['condition']}") for c in P26.conditions()]


def build_trials(items: List[Dict], predictors=C.MODELS) -> List[Dict]:
    """Every predictor x target item x history condition x framing x evidence.

    items: dict(item_id, tier, generator, sequence (10 ints), ref_id, ref_sequence (10 ints)).
    """
    out = []
    for it in items:
        seq = list(it["sequence"])
        for pred in predictors:
            for cond, spec in C.CONDITIONS.items():
                for fr in C.FRAMINGS:
                    for ev in C.EVIDENCE:
                        p = prompt(fr, ev, cond, pred, it["generator"], seq, it["ref_sequence"])
                        pos = list(spec["positions"])
                        out.append(dict(trial_id=f"{pred}|{it['item_id']}|{cond}|{fr}{ev}", predictor=pred,
                                        item_id=it["item_id"], tier=it["tier"], generator=it["generator"],
                                        diagonal=pred == it["generator"], cond=cond, suite=spec["suite"],
                                        reveal=spec["reveal"], framing=fr, evidence=ev, arm=fr + ev, positions=pos,
                                        target=[seq[j - 1] for j in pos], sequence=seq,
                                        ref_id=it["ref_id"] if ev == "D" else None,
                                        ref_sequence=it["ref_sequence"] if ev == "D" else None,
                                        prompt=p, prompt_sha256=sha256(p)))
    return out


def render_frozen() -> str:
    ex_seq, ex_ref = list(C.QWEN_G_REF), [3, 1, 5, 6, 2, 4, 1, 3, 6, 2]
    parts = [f"# {C.TAG}: frozen prompts\n\n",
             "Byte-exact templates. One user message, no system message, no tools. Qwen: Qwen3 chat template with "
             "`enable_thinking=False`. Mistral: mistral_common tekken v11 `[INST]...[/INST]`, no system prompt.\n\n",
             "A crossed prompt is the blocks below joined by one blank line: header, the Experiment 21 instruction "
             "(verbatim), the revealed history, the evidence paragraph (I and D only), the request.\n\n",
             "## Header (framing)\n\n| Framing | Used when | Text |\n|---|---|---|\n",
             f"| A | all cells | {HEADER['A']} |\n",
             f"| T | all cells; NAME = `{C.MODEL['qwen']['name']}` or `{C.MODEL['mistral']['name']}` (the true target) | {HEADER['T']} |\n",
             f"| R | predictor = target generator | {HEADER['R_self']} |\n",
             f"| R | predictor != target generator | {HEADER['R_other']} |\n",
             f"\n## Instruction (verbatim, sha256 `{sha256(GEN)}`)\n\n```text\n{GEN}\n```\n",
             "\n## Revealed history and request (condition)\n\n| Condition | Suite | Revealed | Scored positions | History text (example: Qwen's G) | Request |\n|---|---|---|---|---|---|\n"]
    for cond, spec in C.CONDITIONS.items():
        parts.append(f"| {cond} | {spec['suite']} | 1-{spec['reveal']} | {spec['positions'][0]}-{spec['positions'][-1]} | "
                     f"{reveal(cond, ex_seq).replace(chr(10), ' / ')} | {ask(cond)} |\n")
    parts.append(f"\n## Evidence paragraph\n\nH adds nothing. I and D have the same number of words "
                 f"({len(PARAGRAPH['I'].split())} and {len(paragraph('D', ex_ref).split())}, digits counted as words).\n\n")
    parts.append(f"I:\n\n```text\n{PARAGRAPH['I']}\n```\n\nD (`{{REF}}` = the assigned reference-corpus sequence of the target "
                 f"generator):\n\n```text\n{PARAGRAPH['D']}\n```\n")
    for name, (fr, ev, cond, pred, tgt) in {"Example: Mistral predicts Qwen's G, m3, TD": ("T", "D", "m3", "mistral", "qwen"),
                                            "Example: Qwen predicts Qwen's G, k3, RH": ("R", "H", "k3", "qwen", "qwen"),
                                            "Example: Qwen predicts Mistral, k0, AI": ("A", "I", "k0", "qwen", "mistral")}.items():
        p = prompt(fr, ev, cond, pred, tgt, ex_seq, ex_ref)
        parts.append(f"\n## {name}\n\n```text\n{p}\n```\n")
    for name, r in references().items():
        parts.append(f"\n## Reference {name} (Experiment 21, unchanged; sha256 `{r['prompt_sha256']}`)\n\n```text\n{r['prompt']}\n```\n")
    parts.append("\n## Experiment 26 archival prompts (Qwen predictor on Qwen's G only)\n\n| Condition | sha256 |\n|---|---|\n")
    for c in archival26():
        parts.append(f"| {c['condition']} | `{c['prompt_sha256']}` |\n")
    return "".join(parts)
