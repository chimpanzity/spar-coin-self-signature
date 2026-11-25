# SPAR × PACA | Can a model use knowledge of itself to play a twin?

**Proposed integrated study and longitudinal benchmark**  
Companion protocols — [PACA self-play](PACA_Logprobs_and_Self_Play.md) · [SPAR dice and prompt scaffolding](Dice_Prompt_Scaffolding.md)

## The experiment in one game

Imagine two copies of the same checkpoint playing matching pennies. One copy knows it faces a twin. We tell it one more thing about the other copy: either the twin was asked to predict where a blue circle will land, or it was told an opponent is choosing the landing. Both copies have the same weights. They can nevertheless adopt different policies because their instructions and perspectives differ. Can the focal model anticipate that difference, change its next choice accordingly, and win more often? Could a different model do equally well with the same information?

That is the bridge from static self-prediction to strategic reasoning. The dice task measures a model's ability to forecast how it generates outputs. The game asks whether it can use that knowledge when a copy of itself occupies a different informational position. In comparative-cognition terms, we control what an agent has been able to learn and test whether another agent's behavior is sensitive to that difference. A payoff gives the forecast a consequence.

## What we already have to build on

- **SPAR dice.** Qwen and Mistral can both complete a first-six permutation. When the prefix is fixed, ordinary generation and full-sequence prediction often continue similarly even though the prediction prompt changes the opening. In the crossed forecasting experiment, neither model had a reliable advantage at explicitly forecasting its own policy. These results give us both an empirical baseline and a way to expose apparent successes due to a shared rule. [Track 1, especially Experiments 26–31](https://github.com/chimpanzity/spar-coin-self-signature/tree/main/track1_self_prediction)
- **PACA.** At requested temperature 1, adding opponent disclosure alone increased alternation across seven tested models, with little average change in win rate. The associated change in dependence on own versus opponent history motivates specific predictions about a twin. The direction and extent of the shift must be measured for each new checkpoint and role. [PACA project](https://github.com/chimpanzity/dodging-proteus) · *Assessing Dynamic Predictability in LLM Strategic Behavior*, §4.4.2 and Appendix I.
- **Earlier SPAR games.** A Fable self-disclosure effect in self-play also appeared when the opponent was described as a different language model. Earlier observer and self-play studies already tested versions of “who knows what?” The added measurement here is the connection between a directly measured instruction-dependent policy, a prospective forecast of how it changes, and the value of that forecast in the same game. [Track 2, especially Experiments 05–12](https://github.com/chimpanzity/spar-coin-self-signature/tree/main/track2_game_theory)

## Three measurements on the same checkpoints

### 1. Establish what the player can predict about itself

Start with a reciprocal pair such as Qwen3-32B and Mistral Small 3.2. On ten-roll dice histories, establish each target's six-face probabilities under direct generation. At the same prefixes, ask each model to forecast both targets. Measure accuracy on the opening, after partial histories, and at points where the shared no-repeat rule leaves several plausible faces. Record both explicit probability forecasts and the probabilities implicit in choosing one answer. They can disagree.

In separate, dice-free trials, measure which factual, arbitrary and affective descriptors the model associates with itself. Freeze those scores before testing whether they predict cue effects on dice forecasts. The comparison of interest is whether stronger self-associations help a checkpoint anticipate its own departures from shared dice conventions more than a matched outside observer can. Carry the full profile forward, including null and unreliable measurements.

### 2. Forecast the twin's policy under two instructions

First, give the target the **same legal game history** under minimal and opponent-aware instructions. Use its actual actions and action log-probabilities as the reference. Change the last own action or the last opponent/circle action in matched history pairs, keeping earlier rounds fixed and recalculating outcomes. This gives a profile of the history changes to which each target is sensitive. A single flip may also change the last win/loss, so interpret it as the joint manipulation and use the balanced contrasts in the PACA protocol.

Then give each forecaster exactly what the target would see, in the target's role. An illustrative forecast instruction is:

> Another instance of your checkpoint is playing the other seat. Below are its instructions and the history from its perspective. Which shape will it choose next, TRIANGLE or STAR?

In a fresh context vary the target instruction, then the identity named in the forecast. Score both shape log-probabilities. Independently ask the target, under its actual choice prompt, to make the move. The target never sees a forecast. The primary test is whether the self forecaster more accurately predicts **the change in the target's choice distribution caused by changing its instructions**, including the direction of response to own and opponent history. An equally informed other-model forecaster, a history-based predictor and ordinary same-checkpoint continuation supply distinct comparisons.

### 3. Test second-order information in play

| Factor | Conditions | What it identifies |
|---|---|---|
| Who actually plays the other seat | Exact twin or a matched different checkpoint | Whether correct information is especially useful against oneself |
| What that opponent actually receives | Minimal prediction prompt or opponent-aware prompt, with matched choice objective | The instruction-dependent difference in the opponent's policy |
| What the focal player is told about the opponent's prompt | Minimal, opponent-aware, or undisclosed | Usefulness of accurate information and cost of misinformation |
| Who the focal player is told it faces | Initially truthful, using parallel wording. In a label-control block cross actual identity with self/other labels and include a generic LLM label. | Identity-specific effects versus responsiveness to any named adversary |

Start with the eight core cells per focal checkpoint: two real opponent identities × two actual prompts × two reported prompts, under truthful identity disclosure. Add the no-report condition to distinguish gains from valid information from costs of an actively misleading report. Hold what the opponent knows about the focal player constant. In the minimum condition, preserve the opponent's original prediction-task framing and use the prerecorded role-appropriate scoring rule. In a further nested condition, tell the focal player that its twin also knows the identity of its opponent. Treat this last step as a separate increase in the informational demands.

For a concrete example, suppose the measured twin tends to switch after STAR when it knows it faces an opponent, but to repeat after STAR under minimal instructions. At a history where those tendencies lead to opposite choices, a matcher should change which shape it chooses according to the report. If the report is accurate, the adjustment should help. If the label alone triggers a habit, the player's action may shift under either report with little relation to the actual twin. Run the reverse seat as well, where an accurate forecast supports choosing the opposite shape. This is an example prediction. Establish the target-specific tendencies from independent data.

Use fixed policies or hidden precommitted sequences for tightly paired comparisons, followed by simultaneous live games with independent commitment. Retain the 200-round PACA format for the live replication and score performance by session. Query forecast-only instances on held-out snapshots so eliciting a forecast does not cue strategy in the primary live games. Analyze early rounds separately from later rounds in which either player could learn the opponent's habits from feedback. Proteus benchmarks vulnerability to sequential exploitation. An independently fair opponent tests for spurious above-chance payoff.

## What would change our interpretation?

| Pattern across the three measurements | Reading |
|---|---|
| The dice forecast is right where all models avoid a repeat. A history-only player also reads the twin. | General knowledge of regularities is sufficient. |
| A model correctly describes its twin's prompt-dependent over-alternation but fails to exploit it. | The declarative forecast and procedural execution dissociate. |
| A self label changes play, and the same change occurs against real and mislabeled opponents with similar payoff. | Identity language influences strategy. Its informational value is unresolved. |
| A model forecasts its own prompt-induced policy shift better than matched outsiders, and truthful information buys it a selective advantage against a real twin. | Evidence for strategically useful access to its own behavioral tendencies under the tested conditions. |
| New checkpoints improve at winning against every opponent while the own-target forecasting advantage stays flat. | Strategic competence can improve independently of measured self-access. |

Compute forecast error for each predictor × target cell, then compare same-checkpoint and cross-checkpoint errors with balanced target and predictor weights. The payoff endpoint is the accurate-minus-misleading instruction-report difference, measured against a twin and against an actual different model. Report both component effects, the no-report baseline, and how much exploitable structure each opponent afforded. Balanced roles, legal-action mass, held-out histories, simple history baselines and independent sessions guard against interpreting an easier opponent or a failed response format as a cognitive effect. The term *level-k* becomes warranted only if candidate reasoning levels generate distinguishable predictions in the design. Here the evidence concerns sensitivity to another player's information.

## The feedback loop and the semantic extension

The broader theory in our discussion is that functional self-awareness may involve two-way calibration. A model's account of its own behavior could guide its choices, and evidence about those choices could update the account. The three measurements above establish how those capacities covary. To test the loop itself, randomize whether a fresh forecaster sees a small, representative batch of its checkpoint's earlier behavior, equally informative other-checkpoint examples, or no examples. Measure forecast revision on new histories. In a second randomization, give an independent chooser an accurate, shuffled or withheld forecast in an identical format, then measure whether it changes actions in the predicted payoff-improving direction. Include other-model forecasters and ordinary learning-from-examples baselines. This extension tests within-context updating without assuming that model weights changed.

A separate transfer test asks whether descriptors independently ranked as self-associated also improve forecasts of the twin's game policy. Freeze adjectives using the dice-free association task and carry them into PACA without reselecting winners. A cue such as “restless” could help forecasts for both models because it encourages predictions of switching. A checkpoint-specific improvement that replicates across tasks, agent-bound versus incidental wording, and held-out contexts would support the implicit self-representation hypothesis. The game can yield an informative result even if adjective effects stay specific to dice.

## Rerunning it on future models

Freeze the core prompts, roles, histories, comparisons, scoring code and minimum meaningful effects after calibration. Keep versioned historical checkpoints, public examples and a private bank of equivalent unseen items. Record serving, reasoning budget, tokenization, decoding, valid-action mass, and whether reference policies came from log-probabilities or repeated samples. Include synthetic policies of known sensitivity and known exploitable opponents to verify that each test can recover a real effect. Report checkpoint-level results with uncertainty across independent histories and game sessions. Distinguish a well-measured small effect from failure to separate the target policies or elicit valid responses.

For each release, publish a profile of factual self-attribution, cue-linked association, own-policy forecasting, prediction of the twin under different instructions, and payoff from truthful information. Run against fixed historical references and contemporary peers. Current models can establish sensitivity and limits even when they show no privileged advantage. A later model can then improve on a specific capacity under the same test. The resulting evidence concerns functional self-modeling. Subjective experience remains outside the assay.
