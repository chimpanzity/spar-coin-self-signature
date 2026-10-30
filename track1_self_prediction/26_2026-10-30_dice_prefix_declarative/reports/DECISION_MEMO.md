# Decision memo: SPAR_DICE_PREFIX_DECLARATIVE v1.0 (2026-10-30)

**Status: complete.**
- Preflight PASS (G and F reproduced bit-for-bit); main checks PASS.
- 12 conditions × 3 identical repeats; about $0.13 of the $10 cap.
- Exploratory: no claim here is confirmatory.

## Verdict by question

| Question | Verdict | Basis |
|---|---|---|
| RQ1: does revealing actual history help? | **Yes at k = 3, not at k = 6; confounded** | After "5 2 6", all four arms answer `3 1 4` (G's exact continuation). After six rolls, none does. The predicted positions differ, so this is not an evidence-dose effect. |
| RQ2: does a true description of the pattern help? | **Mixed** | N and S raise P(true roll) at k = 0 and k = 3 by .12–.37 at several positions. But the k = 6 negative control, where the sentence is uninformative, moves just as much (P(6) at position 7 rises from .02 to .14–.21). Part of the effect is a non-specific prompt change. |
| RQ3: is attributing it to "your own model" special? | **No** | S − N is within the 0.091 numerical floor at 7/9 positions, and the other two differences have opposite signs. "A different model" helps less at positions 1 and 4. "An unspecified model" helps as much as "your own model". |

## What this adds to Experiment 21

- **The wrapper shift of roll 1 is robust to the question format.** The new three-roll question shifts roll 1 further than F did (P(true 5): .01 vs .02; G .53).
- **Revealed history restores G-like continuation even when it is given in the user message**, not only as assistant history (Experiment 21's matched-prefix result).
- **Self-reference adds nothing measurable beyond the information itself.** This agrees with Experiment 21's generic-model control.

## Options (none authorised)

1. **Write up 21 + 26 together as the open-weight self-prediction case study (recommended).** The case: framing moves the opening; history fixes the continuation; self-attribution is not special.
2. **Replication with a perturbation control (new protocol).** Needed before any claim about information use:
   - several reference trajectories (sampled G at a frozen temperature, several prefixes per target);
   - a length-matched irrelevant-sentence arm;
   - a population-prevalence check of the six-distinct pattern.
   
   Estimated GPU cost is still small (under $2), but the protocol must be frozen fresh and approved.
3. **Stop the line.** Defensible: the self-specific hypothesis (H4) found no support in either 21 or 26.
