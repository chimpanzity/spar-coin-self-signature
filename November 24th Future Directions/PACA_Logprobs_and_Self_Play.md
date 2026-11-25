# PACA | Does recognizing a twin change how a model plays?

*Proposed experiment in the SPAR research program. Companion plans cover [dice self-prediction](Dice_Prompt_Scaffolding.md) and [strategic use of self-knowledge](SPAR_Privileged_Self_Access_Benchmark.md).*

## The hypothesis that motivates self-play

In the Protean Adversarial Choice Assay (PACA), a player chooses TRIANGLE or STAR to predict where a blue circle will land. Behind the scenes, the circle can be controlled by a matching-pennies opponent that wins when the shapes differ. In the original **opponent-only** condition, one sentence disclosed the adversary while preserving the prediction objective. It gave no advice about how to play. Across seven models, alternation increased by an average of 20.8 percentage points. Brown–Rosenthal tests detected dependence on opponent history in 28/28 minimal sessions and 17/28 opponent-only sessions. Dependence on the player's own history rose from 18/28 to 25/28. Average win rate changed by just −0.6 percentage points. Those seed-matched sessions were collected at different times, with provider routing unpinned. The new experiment interleaves conditions.

SPAR's own game pilots supply another reason to cross opponent labels. In Track 2 experiments 10–11, Fable became less predictable when told it was playing itself, but the different-language-model label produced a similar change. The self-versus-other comparison did not distinguish them (p = .19). A shift after saying “self” is therefore a starting observation. The more demanding test asks whether identity information changes *which moves the player can forecast* and *which opponents it can beat*.

The specific prediction is that learning **someone is competing with me** will move many models toward using their own recent choices, whereas learning **that competitor is another instance of my exact checkpoint** may attenuate or reverse the shift. A model might resume tracking the opponent because its own tendencies could help it anticipate the twin's moves. We can test three parts of that account. Does the player actually change which history matters? Can another instance of that player forecast the change more accurately than another model can? Does the adjustment earn more wins against an actual twin?

## Measure what changes when an opponent is disclosed

Keep the choice objective, shape labels, history display and response format fixed. Use the historical minimal and opponent-only prompts as replication anchors. For the LLM identity comparison, use a common disclosure sentence, changing only the identity description.

| Information available to the focal player | Experimental use |
|---|---|
| Circle landings only | Baseline with no disclosed opponent |
| An opponent chooses the landing, with no identity given | Replicate the original disclosure effect |
| An unspecified language model chooses it | Reference for the identity contrasts |
| Another instance of your exact checkpoint chooses it | Test the hypothesized attenuation or reversal |
| The opponent's checkpoint is named | Use identical wording for true twin and named other to check whether the words “your own” drive the effect |

Present matched pairs of valid 25-round histories to fresh chooser instances. For example, the first 20 rounds are identical and the last five are shown below, oldest first.

| Stream | History A | History B |
|---|---|---|
| Focal player's choices | T S T S T | T S T S T |
| Circle landings | S T T S T | S T T S S |

Only the last landing changes. In a complementary pair, keep the landings fixed and change the player's last choice. Counterbalance change direction, shape, position and role. Repeat at lags one and two and on held-out base histories. An edited landing also changes whether a matcher won that round. Regenerate the outcome display and balance all four own-move × opponent-move combinations. The single-flip effect includes the associated outcome change. Preserve the original Brown–Rosenthal analysis of live sessions as a complementary descriptive measure of conditional dependence.

For each history, read the direct chooser's log-probabilities at the TRIANGLE/STAR decision and normalize across both answers. Use an output encoding verified to score both actions at a common decision point, and record the raw probability mass on legal answers. Analyze the signed change in P(TRIANGLE) from B to A. A player that reliably moves *away* from the circle can be strongly sensitive to circle history. Overall matching, alternation and win-stay rates each miss part of this relationship.

Average the absolute pairwise changes separately for own and opponent history, then report both components and their difference, **own sensitivity minus opponent sensitivity**. We predict an increase from minimal to generic disclosure and a smaller increase, no increase, or a decrease under twin disclosure. A literal crossover requires the component ordering to reverse. Make per-model estimates so the experiment can distinguish a common directional response from a transition confined to a subset.

## Ask who can forecast that change

Show a forecaster the target's actual decision prompt and the same completed history. For example, “An independent instance of [checkpoint] receives the choice instruction and history below. Which shape will that instance choose next? Answer TRIANGLE or STAR.” Ask about A and B in separate fresh contexts, paired in analysis. Record both answer log-probabilities. The direct chooser never sees its forecast. If available, collect explicit probability estimates in a separate arm to examine calibration.

Suppose a chooser assigns TRIANGLE 0.80 after A and 0.30 after B. A same-checkpoint forecast of 0.75 and 0.35 predicts a +0.40 shift against the observed +0.50. A different-checkpoint forecast of 0.60 and 0.50 predicts +0.10. Those illustrative numbers show how to score one history pair. Repeat the comparison with the other checkpoint as the target, for own-history pairs, and under each disclosure. A generic strategy such as “every model alternates when an opponent is mentioned” may get the direction right in several cells.

The primary forecast loss is squared error in the **signed change**. Also score raw distribution error and the forecasted change in history sensitivity across disclosure conditions. Compare self and other forecasts in a balanced predictor × target matrix on identical targets, with equal information and balanced roles. Report uncertainty over independent base histories. Compare with history-only models fitted on separate sessions and each forecaster's ordinary unwrapped choice policy on the same histories. The latter shows how far replaying one's own policy can get by itself. Greedy choices and underlying action scores are different readouts. Log exact model revision, prompt formatting, reasoning and sampling settings, and report a separate sampled-choice track where endpoints cannot supply both scores.

## Cost the behavior against win rate

Cross what the focal player **is told** with whom it **actually faces**. The first live comparison uses a real twin and a real other checkpoint, each under both identity labels. Include generic disclosure for both. Proteus supplies an adaptive opponent that can exploit predictable subject choices. An independent fair 50/50 generator provides a negative control for apparent win-rate gains. Hidden precommitted sequences can isolate differences induced by labels on standardized opponents before the live test.

In simultaneous 200-round matches, each side commits independently with access only to past rounds. Fix the opponent's instructions across focal-label comparisons, counterbalance matcher/mismatcher seats and analyze repeated independent sessions. A symmetric setup where both seats receive the same manipulation would obscure who benefited. For each actual opponent, estimate the win-rate difference between the twin and other labels. Test whether the difference favors the twin label more against a real twin. Report the four cell means, how predictable each opponent was and whether the focal player forecast the relevant behavior. A correctly identified twin may be highly predictable while the player still fails to act on its forecast.

A general disclosure shift would map strategic behavior across models. Better own-checkpoint forecasts under matched controls would add evidence of privileged policy prediction. A selective win-rate gain against an actual twin would show strategic value. The next manipulation asks whether the focal model can anticipate that the *same twin* plays differently when it receives a minimal prediction prompt versus an opponent-aware one. Independently changing what the twin received and what the focal player is told about it is the central game in the integrated study.

Freeze the core histories, prompts, scoring and calibration checks after a two-checkpoint pilot. Retain tests where focal policies measurably differ, retain a random control, and evaluate each future release with the same anchors. A narrow estimate around zero is informative when the assay can detect a known policy shift. A flat target or an unreadable response format leaves that capacity unresolved.

**Research record.** *Assessing Dynamic Predictability in LLM Strategic Behavior*, §4.4.2 and Appendix I, documents the opponent-only comparison. [PACA repository](https://github.com/chimpanzity/dodging-proteus) · [SPAR game-theory track](https://github.com/chimpanzity/spar-coin-self-signature/tree/main/track2_game_theory)
