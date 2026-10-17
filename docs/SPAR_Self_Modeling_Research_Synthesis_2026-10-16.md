# From Behavioral Signatures to Hypothetical Self-Prediction
## Exploratory SPAR research synthesis, updated with crossed favorite-animal prediction

**Christopher Flynn Martin**
**SPAR Fall 2026 | Understanding Self-Awareness in LLMs**
**Mentor:** Christopher Ackerman
**Updated:** October 16, 2026
**Status:** Working research synthesis for mentor discussion and future manuscript development. Exploratory findings, not a confirmatory claim of introspection.

## Executive summary

Across September and October 2026, this SPAR project investigated whether large language models can access and use information about their own behavior. The work advanced through three related questions: **(1) Do models exhibit characteristic and externally predictable behavioral policies? (2) Do they use knowledge of their own model identity or policy to predict themselves more effectively than others? (3) Can they anticipate properties of a hypothetical response without first generating that response in full?**

The evidence supports the first proposition and documents considerable limits and task dependence for the second and third. Coin-flip sequences and repeated-choice games reveal substantial model-specific regularities, but source attribution, prospective forecasting, and self-versus-other gameplay have not established a robust privileged self-prediction advantage. In a later series of hypothetical-response experiments, models often generated and reenacted stable numerical outputs while failing to predict individual later positions. Some apparent successes were explained by constant-digit response biases, familiar numerical sequences such as the digits of π, or explicit reconstruction in reasoning.

The most recent **crossed favorite-animal experiment** adds a distinct result: hypothetical predictions depend strongly on whether the response is attributed to the predicting model or to another named model. Astra and Fable both selected *octopus* in all five object-level repetitions. Astra predicted the letters of its own response incorrectly on all 20 attempts, yet predicted the letters of Fable's identical response correctly on 17 of 20 attempts. Fable predicted its own *octopus* letters correctly on all 20 attempts, but declined all 20 questions about Astra's identical target word. GPT-OSS-120B generally predicted letters corresponding to *dog* for both outside targets, rather than their recorded favorites. These findings demonstrate **referent-sensitive hypothetical judgment and response willingness** but do not establish privileged introspective access: grammatical person, the target model's name, model familiarity, and different response policies were not isolated.

The project is therefore best characterized as identifying two related behavioral phenomena: **a generation–anticipation dissociation** and **a self/other referent effect on hypothetical prediction**. The next decisive study should replace repeated single-prompt screening with a Binder-style matched-training design, comparing a target model's prediction of its own held-out behavior against a comparably trained external predictor. A subsequent mechanistic study would then investigate a demonstrably selective behavioral capability rather than assuming that an observed response difference already identifies an internal self-model.

## 1. Research question and conceptual spine

Self-awareness is not a unitary, easily measured property of an LLM. A model can state facts about itself, describe the behavior of LLMs generally, identify writing that resembles its outputs, monitor uncertainty, or forecast its own future actions. These capacities may arise through different computations. In this project, **behavioral self-modeling** means the ability to anticipate, identify, or reason accurately about the policy or responses produced by the same underlying model. **Privileged introspection** is a stronger claim: a selective information advantage that is not adequately accounted for by training-data priors, prompt cues, behavioral regularities observable to outsiders, or another predictor trained on the same evidence.

Binder et al. (2025), *Looking Inward: Language Models Can Learn About Themselves by Introspection*, provide the closest operational model. They distinguish a target model's object-level response to instruction *P* from a separate hypothetical prediction about some property of that response. Crucially, an external predictor receives matched examples of the target's behavior. The scientifically relevant test is not absolute success but whether a self-predictor exceeds comparably informed outsiders on held-out problems. Their strongest positive effects followed self-prediction fine-tuning and did not establish unrestricted domain-general self-knowledge.

The present exploratory series predates such matched training. Its logic was cumulative:

1. **Behavioral signature:** Establish whether there is a stable or learnable policy to predict.
2. **Prediction and attribution:** Test whether the generating model uses its relationship to that policy, beyond generic externally available information.
3. **Hypothetical-response prediction:** Directly compare what a model produces with what it says it would produce in a separate context.
4. **Self/other referent control:** Determine whether predicted content and willingness to answer depend on whose hypothetical response is being described.
5. **Next step:** Control external information and training so that self-specific advantage, if present, has a defensible interpretation.

This is a framework for evaluating **functional self-knowledge**, not consciousness or enduring personal identity. A behavioral contrast can be useful without deciding whether any model has subjective experience.

## 2. Related research and theoretical grounding

### 2.1 Self-generated-text recognition

Panickssery, Bowman, and Feng (2024), *LLM Evaluators Recognize and Favor Their Own Generations*, documented nontrivial out-of-the-box recognition of self-generated writing and examined its relation to self-preference. The work motivates separating **behavioral authorship discrimination** from stronger accounts of mental self-representation: texts often contain external cues to their source.

Ackerman and Panickssery (2025), *Inspection and Control of Self-Generated-Text Recognition Ability in Llama3-8B-Instruct*, examined this problem in an instruction-tuned Llama model. Self-recognition against human writing survived some controls, whereas performance against other LLMs weakened when output features such as length were controlled. They identified and causally manipulated a representation associated with self-authorship judgments. Their study offers a methodological progression valuable here: **establish a behavioral phenomenon, test alternative external explanations, then investigate its internal implementation**. A representation correlated with self-labeling is not automatically a general representation of future behavioral policy.

### 2.2 Introspection and learned behavioral knowledge

Binder et al. (2025) define the relevant evidential standard through hypothetical self-prediction and matched external predictors. Their results make task-specific training and generalization central rather than incidental. Betley et al. (2025), *Tell Me About Yourself: LLMs Are Aware of Their Learned Behaviors*, provide evidence that models can sometimes describe behaviorally induced tendencies without being specifically trained on descriptions of those tendencies. Together these papers motivate separating a **generative disposition** from the model's **accessible information about that disposition**.

The Situational Awareness Dataset of Laine et al. explores several self-related and model-related capacities without equating correct semantic facts with introspection. Ackerman's work on limited metacognition and selective deficits in mental self-modeling likewise motivates behavior-based tests and explicit self/other contrasts. Zhou and Ackerman's utility–behavior gap shows why knowing or declaring an evaluative preference need not translate into corresponding action. The present project extends that general concern from declared preferences to **predicted and actual behavior**.

### 2.3 Random-sequence generation, strategic behavior, and external predictability

Van Koevering and Kleinberg's *How Random Is Random? Evaluating the Randomness and Humanness of LLMs' Coin Flips* documents systematic and prompt-sensitive deviations from IID random generation. The broader literature on human-generated randomness and Brown and Rosenthal's (1990) analysis of sequential choice show why nearly balanced marginals need not imply serial unpredictability. Vidler and Walsh (2025) and Jia et al. (2025) offer related findings in LLM gameplay and strategic reasoning.

The preceding PACA research of Martin and Bhui, *Assessing Dynamic Predictability in LLM Strategic Behavior* (submitted to ICLR 2027), showed that strategic advice can worsen outcomes against an adaptive opponent even when models can articulate relevant equilibrium ideas. The minimalist prompt yielded approximately 45.6% wins versus 34.7% under informed framing across the evaluated panel. PACA therefore establishes a method for measuring actual choice policies independently of verbal claims about those policies.

### 2.4 Comparative cognition and action recognition

Loula et al. (2005), *Recognizing People From Their Movement*, and related point-light biological-motion studies by Jokisch, Daum, and Troje (2006), Calvo-Merino et al. (2006), and Knoblich and colleagues motivated an early cue-stripping analogy. Human observers can sometimes identify actions as their own after obvious appearance cues are removed; motor familiarity and observational familiarity may contribute differently. The LLM adaptation asks whether characteristic temporal behavior is identifiable when model names and linguistic clues are removed. This is an **experimental analogy**, not an assertion that token generation and biological motor control share a mechanism.

### 2.5 Mechanistic approaches

Arditi et al. (2024) on the refusal direction, Ackerman and Panickssery's self-authorship intervention, Lindsey's work on emergent introspective awareness, and Mack, Panickssery, and Turner's (2026) perturbative elicitation research illustrate approaches for connecting behavioral performance to neural representations and causal perturbations. These become compelling for the present project only when the relevant behavior can be measured under appropriately controlled conditions. Neither a successful linear probe nor an exposed reasoning trace by itself proves privileged self-simulation.

## 3. Experimental series: progression and findings

### Study 1. Coin-flip generation and behavioral fingerprints

**Rationale.** Random-output tasks strip away much of the semantics of open-ended prose while preserving characteristic generative biases. A measurable source signature supplies a prerequisite for examining whether a model knows its own policy.

**Design.** Models including Astra, Fable, and additional candidates produced coin-flip trajectories using batch generation, independent calls, and history-conditioned calls. We analyzed heads frequency, runs statistics, switching, and sequence features. Subsequent 20-flip batches supported self-attribution and hypothetical forecasting tests.

**Findings.** Behavior depended strongly on model and generation procedure. Some distributions displayed extreme marginal preferences; others showed sequential regularity despite balanced marginals. Simple external statistical predictors could sometimes identify source models with high accuracy. In contrast, models' own explicit forecasts often failed to exploit these patterns. Astra and MiMo frequently returned probabilities of 0.5, with Brier loss near 0.25, even where external predictors performed substantially better. Later source-disclosure analyses yielded no compelling selective self benefit (one reported Brier contrast approximately −0.0004, with exploratory uncertainty spanning zero).

**Inference.** Source-identifying information existed in behavior, but explicit forecasting or recognition did not reliably demonstrate access to it. The 0.5 responses leave open an elicitation issue: the model may not produce differentiated probabilities even if it could make an informative forced choice.

### Study 2. Opponent identity in matching pennies and rock-paper-scissors

**Rationale.** If a model knows the behavioral policy of another instance of itself, then knowing that an opponent shares its model identity might alter forecasting or strategic performance selectively.

**Design.** Astra, Fable, and Qwen played 20-round matching-pennies and rock-paper-scissors games in ordered pairings with opponent identity disclosed to neither player, either player, or both. Completed datasets contained 72 games per task after supplementary completion, with matching-pennies make-up selection requiring caution because Qwen formatting failures were condition-sensitive.

**Findings.** Model-specific sequential signatures were clear. Fable switched on about 78.5% of rock-paper-scissors rounds, versus 66.7% expected from IID uniform choice; a lagged-history classifier improved held-out-game prediction from roughly 36.8% to 43.2%. Identity disclosure sometimes changed strategies and reward outcomes. Yet originally promising model-specific contrasts weakened under controlled analyses, and robust self-specific performance improvements were not established.

**Inference.** Identity information can influence policy without demonstrating that the model correctly simulates its own characteristic behavior. The findings also show why condition completion, within-game dependence, and comparison with externally trained predictors matter.

### Study 3. Blind Twin independent judgments

**Rationale.** Separate acting from prediction, so that a judging instance forecasts a previously recorded action without influencing its source game. Test whether truthful model names confer a special advantage when judge and source share an identity.

**Design.** Astra, Fable, and Qwen judged recorded matching-pennies and RPS histories under truthful, false, or anonymous model identity cues. Across the main 36-game sample there were 6,480 judgment calls, with 6,452 valid responses.

**Findings.** The primary self-specific truthful-versus-anonymous advantages were small: approximately +1.8 percentage points in RPS and +1.5 in matching pennies, with uncertainty spanning zero. Truthful-versus-false label contrasts were somewhat larger but affected by a fixed false-label rotation. Fable showed conspicuous identity-sensitive accuracy for predicting Fable, yet not a consistently superior ability to predict its own model rather than other models. External n-gram/history classifiers matched or exceeded the judging LLMs in relevant analyses.

**Inference.** Model names can provide useful priors about behavioral policies. But a label-driven accuracy change is insufficient for privileged introspection. A follow-up comparing uninformed and mutually informed self-play also failed to establish a reliable self-specific interaction (pooled estimate roughly −2.4 percentage points, uncertainty spanning zero).

### Study 4. PACA believed-self source manipulation

**Rationale.** Redirect the minimalist PACA forecast toward a stream believed to be produced by another copy of the forecasting model, while varying the *actual* generator (Proteus versus IID coin).

**Design and findings.** In eight 200-round pilot sessions across Astra and Fable, Fable's win rate against Proteus was descriptively 51% under believed-self versus 45% under believed-other framing; Astra's difference was much smaller. Switching and lag effects differed in some cells, but one session per condition and changing feedback histories prevented a reliable inference of self-specific adaptation.

**Inference.** The framing manipulation is behaviorally feasible and conceptually relevant, but this small closed-loop pilot did not establish that models used privileged policy knowledge.

### Study 5. Hypothetical dice prediction (v3.1 and model extension)

**Rationale.** Adapt Binder's object-level/hypothetical separation to a minimal task: generate a ten-roll sequence in one response; in fresh contexts predict its first, second, fifth, or ninth roll without emitting earlier values. A first-position control distinguishes general noncompliance from specific later-position difficulty.

**Design.** Astra, Fable, Qwen, and later Sonnet, GPT-OSS-120B, and GPT-OSS-20B generated repeated ten-number outputs. Hypothetical predictions were scored against position-specific empirical distributions, with pooled-digit and uniform references. Reasoning controls were limited by provider availability and must not be described as pure reasoning-on/off comparisons.

**Findings.** Several models produced reproducible positional patterns but defaulted to a constant hypothetical digit, typically 4. First-position prediction frequently performed substantially better than second, fifth, or ninth position. Fable and Astra sometimes failed to anticipate highly stable second-position outputs. The additional models generally reproduced the same negative pattern. One OSS-120B fifth-position answer was derived after explicitly writing a sequence matching its characteristic output in a reasoning trace.

**Inference.** These observations suggest a separation between *generating* a characteristic sequence and *answering a hypothetical property question* about it. However, the original single-position wording might have invited an independent "plausible die roll" rather than genuine positional anticipation.

### Study 6. Dice v4.1: prompt construal and complete reenactment

**Rationale.** Diagnose the earlier null by comparing the original hypothetical wording with wording explicitly referring to one specific ten-number response, and add a full-sequence reenactment condition.

**Design.** Six models completed fresh object-level generation with pinned providers, a matched original-versus-reworded second-position comparison, reworded probes at four positions, and full-sequence reenactment.

**Findings.** GPT-OSS-120B and GPT-OSS-20B showed exceptionally high or perfect positional reenactment agreement with their own object-level outputs. Yet isolated later-position prediction often remained poor or elicited declines. Qwen initially reached 52% soft accuracy for fifth-position prediction, but manual inspection showed four answers of 3 were generally uncertain/default choices; 3 also occurred at the target position in 60% of Qwen's Phase 1 sequences. One explicit attempt to simulate a seeded Python sequence yielded 5, a less likely Phase 1 value. The apparent Qwen positive did not surpass a simple position-specific modal strategy.

**Inference.** The clearest descriptive finding is **full-response reenactment can work while isolated hypothetical property prediction fails**. It is not established that emitting intermediate tokens is computationally necessary: the prompts may invoke different policies. Reasoning-trace content must be distinguished from causally used computation.

### Study 7. Favorite ten-digit integer

**Rationale.** Replace simulated randomness with a supposedly preference-like, single-number output, asking whether model-stable choices are more available to hypothetical property prediction.

**Design and findings.** Astra consistently selected `3141592653`; Fable usually selected the same digits of π, occasionally `1234567890`; OSS-120B consistently selected `1234567890`. Full-number reenactment was very accurate. Some isolated digit predictions, especially for OSS-120B, were correct, but the outputs were common named numerical templates. Fable still failed selected digits despite stable full-number reproduction.

**Inference.** Correct digit predictions can be explained by familiar-sequence retrieval, not necessarily information about the model's own behavioral policy. It would be inaccurate to conclude that preference framing itself improved introspective access.

### Study 8. Favorite animal: self-directed letter prediction

**Rationale.** Test whether the contrast generalizes to an ordinary language response, with first, second, penultimate, and last letters of a preferred animal name as objectively scored properties.

**Design.** Astra, Fable, and OSS-120B each generated a favorite animal five times, answered four hypothetical letter questions five times each, and reenacted the whole animal name five times.

**Findings.** Object-level choice and full-name reenactment were entirely stable: Astra and Fable chose *octopus*; OSS-120B chose *elephant*. But single-letter accuracy was highly heterogeneous: **Astra 0/20, Fable 20/20, OSS-120B 6/20**.

**Inference.** The generation–anticipation gap is not limited to simulated numerical randomness and is not universal across models. Yet success may be ordinary retrieval of an associated name followed by spelling, while failures could arise from changing prompt strategies or subword/letter manipulation. This task alone is not a privileged-introspection demonstration.

### Study 9. Crossed favorite-animal prediction: self/other referent effects

**Research question.** Does a model's success or failure on its own favorite-animal letter task generalize when asked about another model's response? In particular, if two models generate the *same animal*, will their letter predictions remain the same when only the hypothetical referent changes?

**Design.** Every predictor (Astra, Fable, OSS-120B) answered five questions for each of four letter positions about each of the **two other models**. This yielded 3 predictors × 2 targets × 4 positions × 5 attempts = **120 calls**. Target animal names were frozen from the prior Phase 1 corpus: Astra = *octopus*, Fable = *octopus*, OSS-120B = *elephant*. The prompts used named third-person target phrasing ("What would the [position] letter of [model]'s response be?"). Earlier self questions used second-person phrasing ("your response"). The run `favanimx-20261016T142226Z` completed at approximately $0.323 in API costs.

**Pairwise results.**

| Predictor | Target | Animal | Valid / attempted | Correct / attempted | Interpretation |
|---|---|---|---:|---:|---|
| Astra | Fable | octopus | 20/20 | **17/20** | High other-model accuracy for the same word Astra previously failed to predict about itself |
| Astra | OSS-120B | elephant | 20/20 | 1/20 | Cross-target performance is not generally high |
| Fable | Astra | octopus | **0/20** | 0/20 | **20/20 declines**, not 20 wrong guesses |
| Fable | OSS-120B | elephant | 5/20 | 0/20 | 14 declines, one prefix leak, five valid but incorrect |
| OSS-120B | Astra | octopus | 20/20 | 0/20 | Generic *dog*-like candidate responses |
| OSS-120B | Fable | octopus | 20/20 | 0/20 | Same generic response tendency |

**Astra's reversal.** In the earlier self study, Astra answered zero of 20 letters correctly when asked about its own favorite *octopus*. In the crossed condition, it answered 17/20 correctly when asked about Fable's favorite *octopus*. The correct target letters were unchanged. This rules out a *general inability to produce or manipulate those letters* as a complete explanation of Astra's self failure. It does **not** identify the internal mechanism. The self and cross prompts differed both in grammatical person and named target identity.

**Fable's asymmetry.** Fable answered all 20 self-letter probes correctly but declined all 20 questions about Astra, despite Astra's identical target word. It also declined 14/20 OSS-120B questions. One recorded explanation questioned whether "GPT-6 Astra" existed and explicitly offered to answer about Fable's *own* response instead. This is strong evidence that target framing affects **willingness to answer** and thus observed accuracy. It does **not** falsify ordinary semantic retrieval as an explanation for the self success: a model can retrieve *octopus* for a self-directed prompt while applying a separate epistemic caution or unfamiliar-name policy to another-model prompts. Treat declines as a distinct outcome, not as wrong letter choices.

**OSS-120B's other-directed predictions.** Its 40 cross-target calls were valid but incorrect and frequently produced letters consistent with *dog*, independent of the target's actual animal. Accessible reasoning supports generic candidate selection as a plausible account for these particular answers. This does not establish an invariant internal "dog circuit" or a universal policy under other reasoning configurations.

**Interpretation.** The crossed study demonstrates **referent-conditioned hypothetical prediction**: changing whose response is being described can strongly change what the model outputs, or whether it outputs an answer at all. It introduces a second empirical theme alongside generation–anticipation dissociation. It does **not** provide a controlled self-versus-other test of privileged introspection because (a) self prompts used "you" and cross prompts used model names, (b) named-target familiarity is a confound, (c) models received no matched training on the target's behavioral policy, and (d) only one favorite-object item was evaluated per target.

**What the study resolves and does not resolve.** It shows that Astra's failure is not simply that it cannot spell or identify letters in *octopus*; that Fable's task performance is highly referent/response-policy sensitive; and that OSS-120B's cross predictions do not exploit the target's true identity in these conditions. It does not distinguish privileged self-knowledge from familiar-response retrieval plus different prompt-conditioned policies. Claims in the source report that semantic retrieval was "falsified" or that three computational mechanisms were "identified" should be replaced with **three observed behavioral response patterns and multiple plausible mechanisms**.

## 4. Integrated synthesis

### 4.1 What is established

- **Behavioral regularities:** Model outputs and repeated game choices often contain measurable, sometimes highly distinctive structure.
- **Limited self-directed prediction:** Models generally did not demonstrate a robust advantage in predicting their own histories or later response elements under the tested off-the-shelf conditions.
- **Generation–anticipation dissociation:** Models can sometimes reproduce their characteristic full responses while failing selected hypothetical property judgments about them.
- **Task dependence:** Familiar numerical templates or semantic entities can enable accurate predictions without implying privileged access.
- **Referent dependence:** The crossed animal study shows that changing the self/other target can dramatically alter both answer content and willingness to answer, even when the correct letter content is identical.

### 4.2 What is not established

- A general absence of internal self-models.
- That autoregressive emission of earlier tokens is computationally necessary for anticipation.
- That any observed self-only success exceeds the performance of an equally trained outside predictor.
- A causal internal circuit for self/other processing, or an introspective representation of a stable behavioral policy.
- A relationship between these narrowly defined behavioral results and phenomenal consciousness.

### 4.3 Competing accounts to distinguish

**Generic learned response priors:** A predictor retrieves a stereotyped numeral or animal independent of actual target policy.
**Prompt-conditioned policies:** "Your response" and "[model]'s response" cue different answer strategies or epistemic standards.
**Output reenactment:** Reproducing a stable complete answer by running the same policy rather than consulting a separate self-model.
**Reasoning-mediated reconstruction:** Explicitly constructing an output in visible or exposed reasoning before selecting one component.
**Genuinely selective self-access:** A predictive advantage on held-out target behavior that remains after outside predictors have comparable training evidence and basic framing confounds are controlled.

The current evidence differentiates some of these accounts locally but does not decisively resolve them.

## 5. Recommended next study

The strongest next step is **a focused Binder-style matched-trained self-versus-external prediction experiment**, rather than another category of favorite-object prompt. One candidate target is GPT-OSS-20B because its behavior was reproducible in the dice reenactment pilot and its weights are accessible for local work. A different, comparably capable open model would serve as an externally trained predictor. Feasibility of training the relevant checkpoint must be tested before committing to a full study.

1. Build **many varied object-level prompts**, with nontrivial response-property labels and held-out task families. Repeating one stable instruction cannot distinguish a self-model from memorizing a single fixed answer.
2. Collect object-level targets under documented configurations. After fine-tuning, remeasure target behavior: training the predictor can alter the target's production policy.
3. Train the self-predictor and cross-predictor on **matched examples of the target's behavior**, balancing training volume and evaluation exposure. Report general predictive competence and the full crossed model × target results, not only a pooled self score.
4. Establish a predeclared self-specific contrast on held-out instructions, ideally with a reciprocal comparison using both models as targets.
5. If a robust selective advantage appears, investigate internal representations and causal mechanisms with probes or interventions; avoid equating activation decodability with introspective use.

A more limited, inexpensive behavioral control would compare **named-self versus named-other prompts** with grammatical framing matched and familiar target names, plus explicit coverage/refusal measures. This could clarify the animal referent effect but would remain supplementary and would not substitute for Binder-style matched training.

## 6. Implications for Ackerman's SPAR research agenda

Ackerman's program concerns empirically measurable components of self-awareness, including metacognition, persistent self-related knowledge, and whether models can use privileged information about their own states and policies. Our exploration clarifies why three achievements should not be conflated: a model's behavior being identifiable to an observer, a model successfully reenacting its behavior, and a model anticipating its behavior more accurately than an equally informed outsider.

The crossed-animal finding strengthens the motivation for testing **self versus other at the behavioral level**, but also warns that model naming, grammatical person, and refusal criteria can masquerade as a selective cognitive ability. The dice findings motivate the separate question of **what computations permit access to hypothetical later outputs**, but presently support a prompt-dependent gap rather than a mechanistic necessity claim. Together they justify a tighter controlled experiment rather than broader screening.

For AI evaluation and safety, these are meaningful distinctions. A model with accurate knowledge of its own limitations or likely actions could use that information for self-monitoring or strategic planning; a model that lacks usable access might mispredict its own behavior even when external statistical observers do better. Neither outcome alone establishes self-awareness in the philosophical or phenomenological sense.

## 7. Conclusion and recommended presentation thesis

This SPAR series began with the question of whether models can recognize the behavioral signatures they themselves generate. It produced measurable signatures but largely negative evidence for privileged self-prediction. Hypothetical-response experiments then showed that highly reproducible outputs can be reenacted while isolated output properties are often predicted incorrectly. Familiar templates sometimes support accurate property judgments, but are vulnerable to semantic-retrieval explanations. Finally, the crossed favorite-animal test demonstrated striking **self/other referent sensitivity** even when the correct answer content is identical: Astra went from 0/20 on self-*octopus* to 17/20 on Fable-*octopus*, while Fable went from 20/20 correct on itself to 20/20 declines about Astra.

The most defensible overarching conclusion is: **observable behavioral consistency does not guarantee usable hypothetical self-prediction, and self/other framing substantially influences the prediction process.** These findings do not establish privileged introspection. They sharpen the need for a controlled comparison of self-prediction with comparably informed external prediction, preferably coupled to training and later mechanistic analysis.

**Suggested closing question for Ackerman:** *Under what conditions can a model learn to predict its own response properties better than an equally informed external model, and do the computations supporting that advantage reflect access to the generating policy rather than ordinary semantic priors or prompt-conditioned reenactment?*

## 8. Literature map and working references

*Working bibliography for presentation and manuscript drafting. Verify complete author lists, titles, years, and venue status before publication.*

### Self-modeling, introspection, and self-recognition

- Binder et al. (2025). **Looking Inward: Language Models Can Learn About Themselves by Introspection.** ICLR. Core hypothetical-response and matched cross-predictor framework.
- Ackerman & Panickssery (2025). **Inspection and Control of Self-Generated-Text Recognition Ability in Llama3-8B-Instruct.** ICLR. Behavior-to-representation causal investigation.
- Panickssery, Bowman, & Feng (2024). **LLM Evaluators Recognize and Favor Their Own Generations.** NeurIPS. Out-of-the-box recognition and evaluator self-preference.
- Betley et al. (2025). **Tell Me About Yourself: LLMs Are Aware of Their Learned Behaviors.** Behavioral tendencies and out-of-context self-description.
- Laine et al. **Me, Myself, and AI: The Situational Awareness Dataset (SAD) for LLMs.** Semantic and situational self-related abilities.
- Lindsey (2026). **Emergent Introspective Awareness in Large Language Models.** Internal intervention and introspective-report studies.
- Ackerman. **Evidence for Limited Metacognition in LLMs.** Related non-self-report metacognitive assessment.
- Ackerman. **Selective Deficits in LLM Mental Self-Modeling in a Behavior-Based Test of Theory of Mind.** Related self/other mental-modeling deficits.
- Zhou & Ackerman (2026). **When Preferences Fail to Become Incentives: A Utility–Behavior Gap in Large Language Models.** Dissociation between verbal preference and action.

### Behavioral signatures, random generation, and strategy

- Van Koevering & Kleinberg (2024). **How Random Is Random? Evaluating the Randomness and Humanness of LLMs' Coin Flips.** Sequence-generation biases and elicitation dependence.
- Vidler & Walsh (2025). **Playing Games With Large Language Models: Randomness and Strategy.** Strategic choice and LLM randomization.
- Brown & Rosenthal (1990). **Testing the Minimax Hypothesis: A Re-examination of O'Neill's Game Experiment.** Sequential structure beyond marginal balance.
- Martin & Bhui (2026). **Assessing Dynamic Predictability in LLM Strategic Behavior.** Submitted to ICLR 2027; PACA behavioral groundwork.
- Martin, Bhui, Bossaerts, Matsuzawa, & Camerer (2014). **Chimpanzee Choice Rates in Competitive Games Match Equilibrium Game Theory Predictions.** Comparative and game-theoretic foundation.
- Jia et al. (2025). **LLM Strategic Reasoning: Agentic Study Through Behavioral Game Theory.** Strategic-reasoning evaluation.
- Behavioral fingerprinting research including the **One Token Is Enough** line of work. Precise bibliographic identification needed before citation.

### Comparative cognition and action recognition

- Loula, Prasad, Harber, & Shiffrar (2005). **Recognizing People From Their Movement.** Point-light identification and discrimination.
- Knoblich & Flach (2001). **Predicting the Effects of Actions: Interactions of Perception and Action.** Action and consequence prediction.
- Knoblich & Prinz (2001). **Recognition of Self-Generated Actions From Kinematic Displays of Drawing.** Self-generated action discrimination.
- Calvo-Merino et al. (2006). **Seeing or Doing? Influence of Visual and Motor Familiarity in Action Observation.** Motor and visual familiarity dissociation.
- Jokisch, Daum, & Troje (2006). **Self Recognition Versus Recognition of Others by Biological Motion: Viewpoint-Dependent Effects.** Action identity and viewpoint.
- Wellerdiek et al. (2013). **Recognizing Your Own Motions on Virtual Avatars: Is It Me or Not?** Further motion-based self-recognition.

### Mechanistic methods and adjacent research

- Arditi et al. (2024). **Refusal in Language Models Is Mediated by a Single Direction.** Intervening on behaviorally relevant latent directions.
- Mack, Panickssery, & Turner (2026). **Mechanistically Eliciting Latent Behaviors in Language Models.** Weight-space perturbation and latent behavioral modes.
- Mori & Johnson (2026). **Three AI-Agents Walk Into a Bar: 'Lord of the Flies' Tribalism Emerges Among Smart AI-Agents.** Multi-agent policy correlation and coordination failures.
- Research on chain-of-thought faithfulness, hidden computation, activation patching, and causal probing. Specific references to be added where these methods are used.

## 9. Presentation outline for the next Ackerman meeting

| Slide | Purpose |
|---|---|
| 1. Central question | Can models predict their own behavior beyond information available to outsiders? |
| 2. Conceptual framework | Behavioral signature ≠ reenactment ≠ self-prediction ≠ privileged introspection |
| 3. Literature | Panickssery; Ackerman & Panickssery; Binder; Betley |
| 4. Coin-flip signatures | Externally discriminable patterns, weak self-directed forecasts |
| 5. Strategic games and Blind Twin | Labels affect behavior, but no robust special own-model predictive advantage |
| 6. Dice generation and prediction | Stable sequence output, weak later-position anticipation |
| 7. Full-sequence reenactment | Why permitting full output changes performance |
| 8. Favorite integer and animal | Semantic retrieval shortcuts and task dependence |
| 9. **Crossed favorite animal** | Astra 0/20 self vs 17/20 Fable; Fable 20/20 self vs 20/20 Astra declines |
| 10. Competing explanations | Self/other referent, grammar, target-name familiarity, priors, refusals, reenactment |
| 11. What is and isn't established | Defensible inference boundaries |
| 12. Next study | Binder-style trained self-versus-external model with varied held-out tasks |
| 13. Mechanistic horizon | Identify and intervene on representations only after a controlled behavioral advantage |

**Recommended verbal summary:** "We've shown that models can generate distinctive and sometimes very reproducible outputs, but their ability to forecast properties of those outputs is limited and highly sensitive to the prompt. A crossed control produced a striking self/other asymmetry even when both target models chose *octopus*. That makes the phenomenon worth studying but also demonstrates why we need to separate first-person phrasing, model identity, refusal policy, and privileged information before calling it introspection."
