# Key references and how they relate to this project

Notes on the four papers this project builds on. For each paper: what it did,
what it found, and what it means for the design and interpretation of the
coin-flip studies. The PDFs are not stored here because they are copyrighted.

---

## Loula, Prasad, Harber & Shiffrar (2005)

Loula, F., Prasad, S., Harber, K., & Shiffrar, M. (2005). Recognizing people
from their movement. *Journal of Experimental Psychology: Human Perception and
Performance, 31*(1), 210–220. https://doi.org/10.1037/0096-1523.31.1.210

**Design.** Six observers (three same-gender friend pairs) were filmed as
point-light actors performing 10 actions. They were tested 2–3 months later
under a cover story that the study was about *action* identification. Each
observer judged displays of themselves, their friend and an assigned stranger.

| exp | task | self | friend | stranger | chance |
|---|---|---:|---:|---:|---:|
| 1 | Identify the actor: self, friend or stranger (3 choices) | 69% | 47% | 38% (n.s.) | 33% |
| 2 | Same or different actor across two *different* actions (2 choices; same-actor trials) | 73% | 58% | 47% (n.s.) | 50% |
| 3 | Exp 2 with inverted displays (n = 4) | chance | chance | chance | 50% |
| 4 | Exp 1 with static frames (n = 4) | chance | chance | chance | 33% |

**Conclusions.** Motor experience explains self > friend, and visual
experience explains friend > stranger. Identification was best for
unconstrained actions (dancing, boxing) and worst for treadmill walking and
running. Errors were spread evenly over the wrong alternatives, with no
response bias. The authors argue that the self advantage comes from the action
system, *not* from conscious awareness of one's own movement style.

**Relevance here:**
- **The gradient is the evidence.** Loula's claim rests on self > friend >
  stranger. The phenotype-prediction studies here find a flat gradient: judges
  predict the same p(H) and switch rate for every target model. That pattern
  fits general knowledge about LLMs (the "friend" or visual-experience route)
  with no self-specific component.
- **Constrained versus unconstrained actions** maps onto the procedures. Batch
  behaves like treadmill walking, where every model looks like a fair coin and
  little identity information is available. Independent calls behave like
  dancing, with strong signatures.
- **The controls point the opposite way.** Loula's inverted and static
  controls fell to chance, ruling out low-level cues. Here, a centroid
  classifier on p(H) and switch rate already identifies the source almost
  perfectly (97–100% for history_conditioned and independent_calls), so any
  LLM success could be ordinary statistics-reading. A closer analogue of the
  static control would be shuffled sequences, which keep p(H) and destroy
  sequential structure.
- **Why Exp 2 exists.** Loula moved to same/different judgments because
  naming oneself can bias responses. That bears directly on SELF versus NAMED
  wording here, and it is why the preregistration adopted the Exp 2 paradigm.
- **Response bias.** Loula's errors were unbiased. The LLM judges here showed
  strong A-bias in source attribution, which is why the task-validation study
  was run.

---

## Couchman (2012)

Couchman, J. J. (2012). Self-agency in rhesus monkeys. *Biology Letters, 8*,
39–41. https://doi.org/10.1098/rsbl.2011.0536

**Design.** Forty humans and four rhesus monkeys moved a joystick-controlled
cursor around an obstacle to a goal, then selected the cursor they had been
controlling. At test, a distractor cursor mirrored the controlled one,
reversed left–right or up–down, and otherwise matched it in timing, area and
goal. Selection was among four letter icons.

**Findings.** Humans and all four monkeys chose the self-controlled cursor
above chance (monkeys individually about 0.38–0.72 against 0.25 chance, read
from the figure; humans much higher). When they erred, they picked the
partially matching distractor more often than the unrelated icons. Couchman
attributes this to comparing intention, sensorimotor signals and perceived
outcomes, a metacognitive judgment of agency, in a species that fails the
mirror test.

**Relevance here:**
- **Agency is a different construct from Loula's.** Couchman tests online
  self-agency: does the outcome match what I am doing right now? Loula, and
  every study here, tests offline recognition of one's own *style*. The LLM
  judges never generate while they judge, so the coin-flip studies test
  style recognition, not agency. That boundary should be stated in any
  writeup.
- **Error structure as evidence.** Choosing the partially matched distractor
  shows the judgment uses the match signal. An LLM analogue is to check
  whether wrong answers favour the sequence statistically closest to the
  target model's phenotype.

---

## Kaneko & Tomonaga (2011)

Kaneko, T., & Tomonaga, M. (2011). The perception of self-agency in
chimpanzees (*Pan troglodytes*). *Proceedings of the Royal Society B, 278*,
3694–3702. https://doi.org/10.1098/rspb.2011.0611

**Design.** Three chimpanzees moved one of two identical cursors with a
trackball and then touched the cursor they had controlled. The distractor
replayed the chimpanzee's own recorded movement from at least a day earlier,
so the two cursors could not be told apart by movement style.

**Findings:**
- **Exp 1:** 73.3% correct on the critical probe trials (24/35, 25/35 and
  28/35 by individual; chance 50%).
- **Exp 2:** an *offline* condition replayed both cursors from an earlier
  online trial, so the display was identical but nothing was under control.
  Accuracy was higher online than offline, but offline accuracy stayed above
  chance (65.6%). The authors trace this to residual visual cues: the
  self-cursor looked more goal-directed and avoided collisions.
- **Exp 3** (one chimpanzee): a 300 ms delay lowered accuracy, which stayed
  above chance (93/128). A 135° rotation pushed accuracy *below* chance
  (41/128 and 39/128), which the authors attribute to avoiding unfamiliar
  motion.

**Relevance here:**
- **The own-past-behaviour distractor** is the cleanest way to separate agency
  from style. It has no analogue in the current design, where pairs always
  come from different models.
- **The offline replay control** is the template for separating privileged
  access from trace-reading: same display, no privileged channel. The OBS
  contrast here (same pair shown to non-producing judges) does this job, so
  S = SELF − OBS plays the role of the online-minus-offline difference.
- **Above-chance offline performance** is a reminder that residual cues can
  carry identification with no self-knowledge. That parallels the centroid
  baseline here.
- **Systematic below-chance responding** under distortion parallels the
  below-chance LLM results (for example fable NAMED-on-fable = 0.15 on
  history_conditioned, and astra NAMED-on-astra = 0.00 under a truthful
  independent-calls story). Below chance means a consistent wrong belief, not
  noise, which supports the procedure-belief interpretation.
- **The comparator model** (agency = prediction matched against outcome)
  links to the phenotype-prediction studies. The judges' predictions are the
  same for every model, so there is no self-specific prediction to compare
  against.

---

## Van Koevering & Kleinberg (2024)

Van Koevering, K., & Kleinberg, J. (2024). How random is random? Evaluating the
randomness and humanness of LLMs' coin flips. *arXiv:2406.00092*.
https://arxiv.org/abs/2406.00092

**Design.** GPT-3.5, GPT-4 and Llama 3 at temperatures 0–1.5, asked to "Flip a
coin" or "Flip 20 (fair) coins" in a single completion. Analysis used 8-flip
windows for comparison with human data.

**Findings:**
- **Single flips** are heavily biased toward heads. Llama 3 gave no tails in
  660 flips at temperatures 0–1.0.
- **First flips** of a sequence are heads in over 88% of sequences, more than
  in humans. Unlike humans, models showed no effect of naming heads or tails
  first in the prompt.
- **Head counts** are too balanced: too many 4-of-8 windows, which exaggerates
  a human bias.
- **Over-alternation:** about 5 alternations per 8 flips for GPT-4 and Llama
  3, against 3.5 expected and roughly 60% alternation in humans. Long runs are
  rare, and (1,1,1) almost never occurs.
- **Predictability:** a LASSO model predicting the 8th flip from the previous
  7 reaches mean squared error of about 0.22 (GPT-4) and below 0.15 (Llama 3)
  at the highest temperature. GPT-3.5 is close to 0.25, the random baseline.
  Humans are above 0.24, so LLMs are less random than people.

**Relevance here:**
- **Batch matches their regime** (a whole sequence in one completion). The
  batch switch rates here (0.62–0.64) show the same over-alternation, close to
  the human level.
- **Independent calls match their single-flip regime.** Their heads bias
  predicts the collapse seen here (fable 98.7% H under independent calls).
- **Temperature caveat.** Every corpus call here requested temperature 0.0
  (`corpus/README.md`; whether each provider honoured it was not separately
  verified). Under independent calls an identical prompt at temperature 0
  should give an almost deterministic answer, so near-constant output is
  expected. A judge that predicts p(H) ≈ 1 for any model under that procedure
  may be reasoning correctly about sampling, not drawing on self-knowledge.
  This supports the procedure-belief interpretation and should be stated
  explicitly. The phenotypes in this corpus are temperature-0 phenotypes.
- **A ready-made predictability metric.** Their LASSO next-flip MSE could be
  added to the corpus phenotype alongside p(H), switch rate and longest run.
