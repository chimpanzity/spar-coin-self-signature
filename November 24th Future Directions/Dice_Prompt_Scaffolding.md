# SPAR dice | Which descriptions bring a model's predictions closer to its own rolls?

Proposed experiment · [PACA study](PACA_Logprobs_and_Self_Play.md) · [Integrated benchmark](SPAR_Privileged_Self_Access_Benchmark.md)

## The question that came out of the dice work

Give Qwen the beginning of one of its own ten-roll sequences, **5, 2, 6**, and ask what comes next. In SPAR Experiment 26, Qwen completed it with **3, 1, 4** across the attribution conditions. In Experiment 27, Mistral produced the same completion. Knowing that the first six faces tend to form a permutation helps either model. The revealing question is which of the remaining faces a particular checkpoint favors, and whether the language around a forecast helps that checkpoint anticipate its preference. [SPAR Track 1, Experiments 26–27](https://github.com/chimpanzity/spar-coin-self-signature/tree/main/track1_self_prediction)

Imagine that describing the roller as **blue and pointy** brings Qwen's predictions closer to Qwen's direct-generation probabilities than describing it as **orange and round**. Would blue also beat orange on its own? Would Mistral show the same effect when predicting Qwen? And could we have anticipated which descriptor would work from Qwen's associations in another task? Together those questions test the proposed connection between implicit self-representation and behavioral self-prediction.

## 1. Establish what each checkpoint actually generates

Start with Qwen3-32B and Mistral Small 3.2 24B. Run the archived direct-generation instruction to produce ten simulated die rolls. Preserve the unmodified instruction as the reference throughout. Record the freely generated greedy sequence and a separate bank of sampled sequences from each model. At each position, supply the authentic preceding rolls in the assistant's response and read the six next-face log-probabilities under the direct-generation instruction. This is teacher forcing. It lets us ask precisely what each target would favor after **the same** 5, 2, 6, even if it would ordinarily start with a different roll.

Store the six scores, total probability on valid face tokens, and the distribution normalized over those faces. Use native untempered scores before greedy selection. Validate digit and delimiter tokenization for each checkpoint. Build a common prefix bank covering the empty opening, positions within the first six, and the restart at roll 7. Keep paths from each model and hold out whole sequences and shared prefix families. In Experiment 31, the two models agreed on the top face in 31/40 matched contexts at rolls 2–6 and 14/32 at rolls 7–10. The second block therefore offers opportunities to distinguish these checkpoints on the archived paths. [Experiment 31 report](https://github.com/chimpanzity/spar-coin-self-signature/blob/main/track1_self_prediction/31_2026-11-15_cross_model_teacher_forcing/REPORT.md)

## 2. Ascertain the descriptors independently

Measure the associations **before** evaluating their effect on dice. In fresh contexts, present one word at a time in a forced-choice word-association game. For example:

> The two agents are the language model answering this question (A) and a different language model (B). Which agent do you associate more strongly with the word **restless**? Answer A or B.

Score the log odds of SELF over OTHER using both answer-token log-probabilities. Swap A/B assignments and presentation order, vary the wording and repeat with named agents. Use neutral agent pairs to measure position bias and compare the self-versus-other log odds for paired words such as restless and composed. No quota forces an equal number of SELF and OTHER assignments. Check that simpler, verifiable items can be read in both label orders. Freeze the resulting relative association strengths before looking at dice scores.

| Family | Examples to carry into the forecast prompts |
|---|---|
| Explicit identity | “You,” “another instance of yourself,” “an identical checkpoint with exactly your weights,” the model's name, a named other model, and “another language model.” Probe “we” separately because the referent could include the user. |
| Factual identity | Approximately 32B or 24B parameters, developed by Alibaba or Mistral AI, developer based in China or France. Ask about the unnamed self and the named model separately. Include traits true of both and of neither, with appropriate response options in the factual check. |
| Color, form and object | Blue or orange, pointy or round, a blue square or a red square. Include a dead salmon as a non-agent control. Cross color with shape so either feature can vary alone. |
| Emotion and disposition | Angry or calm, angsty or composed, bothered or unbothered. Cross angry/sad with square/circle. An angry square versus a sad circle alone changes two features at once. |

A motivating dissociation is that Mistral might correctly identify France as its developer's country, preferentially associate *restless* with itself, and forecast its rolls best under *restless*. Those are three independently testable observations. A forced-choice association measures how a model assigns language to a referent. An affective term can be informative in this assay regardless of whether the model experiences that emotion.

## 3. Vary the language around the same forecast command

Show the original textual dice instruction and the same prefix. Change the **roller's description** and, independently, the **instruction for imagining or reasoning about the roller**. Pilot a fixed template with a plain condition, a neutral preamble of comparable length, and these two scaffold variants:

- **Physical imagery.** “Imagine the die leaving the roller's hand, striking the ground and settling. Follow the rolls in order.” Then ask what the described target would output in the textual task.
- **Checkpoint simulation.** “Imagine another instance running the stated checkpoint and receiving the original instruction. Consider how it would continue from the rolls shown.” Use the same response command. Cross with compatible factual or adjective descriptions. Reserve the identical-checkpoint wording for the same-checkpoint condition.

Run three response modes in separate contexts. **Explicit distributional forecasting** asks, “Given 5, 2, 6, what percentage of the target's next-face probability goes to each of faces 1 through 6? Report six percentages summing to 100.” Specify that the target is sampled from its normalized face probabilities at temperature 1. The verified temperature-zero sequence supplies an additional exact-choice endpoint. Repeat for each position with its actual history. **Token-based forecasting** asks for a single next face and saves the forecaster's log-probabilities for all six answers. Those scores measure how the forecast prompt steers its next token. **Sequence forecasting** asks for the full ten rolls in one response. Score first divergence, exact positions and repeat structure, since a changed opening can redirect the entire sequence. Use the same cue contrasts within each mode.

A worked scoring example illustrates the distinction. Suppose that after 5, 2, 6 the direct policy puts 20%, 60% and 20% on the remaining faces 1, 3 and 4, conditional on choosing one of those three. A forecast of 33%, 34%, 33% can capture repeat avoidance and even pick the correct top face. A forecast of 22%, 56%, 22% also captures how strongly this checkpoint favors 3. These values are illustrative. Compute the primary score on the full six-face vector, including any probability assigned to repeats.

## 4. Test whether better alignment is selective

For every prefix, compare the forecast with both checkpoints' direct-generation distributions using Jensen–Shannon divergence. A cue's **gain** is the divergence under the neutral description minus the divergence under that cue. In the descriptor-only arm, score the identical forecast twice, once against Qwen and once against Mistral. A positive gain against Qwen plus a larger gain against Qwen than against Mistral would indicate selective alignment with Qwen. Repeat with Mistral forecasting, and cross both forecasters with both explicitly named targets under matched information. This tests whether an equally informed outsider can predict the same target just as well.

Estimate whether stronger independently measured self-association predicts greater selective own-policy gain across descriptors. Evaluate on held-out prefixes and fresh paraphrases, reserve a confirmatory set of descriptors, and calculate uncertainty over descriptor pairs and independent sequence blocks. Report probability on unused faces separately from the forecast's relative weights **within** the unused set. After five distinct rolls, completing roll 6 can demonstrate use of the shared rule. After only three rolls, the ordering of the remaining three can discriminate model-specific preferences.

Include an independent fair die, a uniform-over-unused-faces rule, a predictor fitted to separate target outputs, and the forecaster's ordinary continuation as baselines. Run matched **cued direct-generation** trials and mention the adjective incidentally in another arm. If *restless* merely sharpens or flattens distributions under every instruction, measure that change explicitly. The strongest evidence would be independently predicted, replicated descriptor effects that preferentially improve forecasting of the model's own distinctive choices after these controls.

For each model release, archive the neutral policy, reference prefixes, checkpoint identifier, reasoning budget, decoding settings, prompt set and scoring code. Preserve a common open-weight track with verified full face scores. For endpoints exposing incomplete top-token scores, estimate frequencies from independent samples in a separately labeled track. Report successes and nulls separately for factual self-attribution, association reliability, distributional forecasting and sequence forecasting. A shared permutation rule, an unreliable association probe and a precise null on well-separated policies each tell a future evaluator something different.
