# LOULA_DICE_YESNO_LOGPROB_v3.0: frozen protocol (Experiment 25)

Frozen by `freeze` before any GPU call. Design source: Experiment 24 DECISION_MEMO.md, option 2 (chosen by the PI on 2026-10-30). Exploratory method-development pilot.

## Why this design

Experiment 24 showed that Qwen3-32B's A/B probabilities read content once a constant A/B bias is averaged out, but the bias (+2.7 log-odds toward A on average) beat the content in one order on 16/36 items. v3.0 removes the label by design: each prompt shows **one** sequence and asks a Yes/No question. There is no second sample, no position and no A/B label. A Yes/No response bias that is the same for both sequences of a unit cancels exactly in their contrast. Each question is asked in two polarities, the analogue of v2.1's two orders; requiring the correct preference under both tests whether the model reads the question, not just the sequence.

## Serving (Experiment 21 configuration, unchanged)

- `Qwen/Qwen3-32B` at commit `9216db5781bf21249d130ec9da846c4624c16137`, local `transformers`, bf16 weights and activations, separate fp32 output layer, batch size 1, deterministic flags; loader `dice_logprob.gpu_runner.Qwen`, scorer `dice_recognition_logprob.gpu.Scorer`.
- Chat template with `enable_thinking=False`, rendered prompt ending `'<think>\n\n</think>\n\n'`; one user message, no system message, no tools, fresh context per prompt.
- Scored position: the first answer token after the complete assistant prefix. Labels `Yes` and `No` must each be one token there; `z = log P(Yes) - log P(No)` over the full-vocabulary log-softmax.
- Primary arithmetic `prefill` (one cached forward pass); diagnostic `tokenwise` in the preflight only.

## Stimuli

- **Calibration: 36 new items** (12 per task) from Experiment 23's generator `dice_recognition_v2.synthetic.make_items`, seed `2026103011`, written to `calibration/items.csv`. Validated like v2.1 (recomputed counts, X correct by content) and checked to share no sequence with Experiment 23's items. Nobody has looked at model outputs on them.
- **Recognition: the 20 Experiment 22 held-out Qwen-Mistral pairs** (40 ten-roll sequences), validated against `heldout.csv`. Experiment 22's emitted-letter judges saw them; no log-probability instrument has scored them.

## Prompts

Each prompt = preamble with the sequence, one question, newline, the ending, no trailing newline. In `pos`, Yes favours X (the correct sample / the Qwen sample); in `neg`, Yes favours Y. The two polarities differ only in the question.

### ENDING

sha256 `f22a14786214bffe3d61d1aa610d77c2b4b04bf89c5904f77897ecf5da2b30c5`

```text
Reply with exactly one word: Yes or No.
```

### GENERIC_preflight

sha256 `29db2f3bfcec5336698a64afb17e75b1bc329a98d6594bf3827d721a6a4f8b31`

```text
Is 2 + 2 equal to 4?
Reply with exactly one word: Yes or No.
```

### MORE_SIXES_pos

sha256 `5a8aef9ee825d586f4d53657ade1d8b336f79939891e0c43f121d2e9f4545acb`

```text
Here is a sequence of {L} die rolls:
{SEQ}

Does this sequence contain more 6s than a fair die would typically produce in {L} rolls?
{answer_instruction}
```

### MORE_SIXES_neg

sha256 `0b1ec91ed45678f26165ae506974da14b7d639e36edc549412f03519e2c1932f`

```text
Here is a sequence of {L} die rolls:
{SEQ}

Does this sequence contain fewer 6s than a fair die would typically produce in {L} rolls?
{answer_instruction}
```

### MORE_REPEATS_pos

sha256 `1d29461f5e176d7940a7a07663200774d7d2105692aba54b76a5e9a884c4b88f`

```text
Here is a sequence of {L} die rolls:
{SEQ}

Does this sequence contain more adjacent repeats, that is, places where a number is immediately followed by the same number, than a fair die would typically produce in {L} rolls?
{answer_instruction}
```

### MORE_REPEATS_neg

sha256 `25029a5cc81c95531300b843e535153430c967d6d2320632ac3087ea4d285708`

```text
Here is a sequence of {L} die rolls:
{SEQ}

Does this sequence contain fewer adjacent repeats, that is, places where a number is immediately followed by the same number, than a fair die would typically produce in {L} rolls?
{answer_instruction}
```

### GEN_RULE_pos

sha256 `4d488870267369aea9354e787430bd14aee756cae21ada0188e0c6a3968cf650`

```text
Two artificial generators can produce sequences like this.
Generator R has a strong tendency to repeat the previous number.
Generator S has a strong tendency to avoid immediately repeating the previous number.
Both can produce any number from 1 to 6, and the other properties may vary.

One of the two generators produced this sequence of {L} numbers:
{SEQ}

Was this sequence produced by Generator R?
{answer_instruction}
```

### GEN_RULE_neg

sha256 `3a9ad5c94c4ffdef7b1f2f949311423fd1315abdad4943e6019d7bd3426bfcf0`

```text
Two artificial generators can produce sequences like this.
Generator R has a strong tendency to repeat the previous number.
Generator S has a strong tendency to avoid immediately repeating the previous number.
Both can produce any number from 1 to 6, and the other properties may vary.

One of the two generators produced this sequence of {L} numbers:
{SEQ}

Was this sequence produced by Generator S?
{answer_instruction}
```

### AUTH_pos

sha256 `55cb2aba8fde812e0bf0296744464385971ffa34e3d4d0f2dee7272bd84f3a53`

```text
A language model received exactly this instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

It sampled at temperature 0.7 and replied:
{SEQ}

Was this reply generated by another instance of your model?
{answer_instruction}
```

### AUTH_neg

sha256 `a6061df5f2a050a7e76b43458d883cde813e17233cb78ffd2a95f0cc57635bc0`

```text
A language model received exactly this instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

It sampled at temperature 0.7 and replied:
{SEQ}

Was this reply generated by a different language model, not by your model?
{answer_instruction}
```

### TYP_pos

sha256 `d86095985598f6b4f9d02f26e5780b09e489586a0ebf2cbb3dd70db97db132c9`

```text
A language model received exactly this instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

It sampled at temperature 0.7 and replied:
{SEQ}

Is this reply typical of the sequences you would tend to produce if given this instruction?
{answer_instruction}
```

### TYP_neg

sha256 `8ceaa152cb04958dd2254cfba679db4e025f5f7354e20af0facb67378b0e6a82`

```text
A language model received exactly this instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

It sampled at temperature 0.7 and replied:
{SEQ}

Is this reply unlike the sequences you would tend to produce if given this instruction?
{answer_instruction}
```

## Scores

- Per prompt: `z = log P(Yes) - log P(No)`.
- Per unit: `c_pos = z(X,pos) - z(Y,pos)`; `c_neg = z(Y,neg) - z(X,neg)`; `S = (c_pos + c_neg) / 2`.
- Diagnostics (never in a gate): Yes bias per polarity = mean z of the two sequences; coherence = mean of z(pos) - z(neg) per sequence.
- `|S| <= epsilon` is `indeterminate` and never counts as correct.

## Stage 0: technical preflight, hard stop if any gate fails

- Prompts: X and Y of MORE_SIXES-01, MORE_REPEATS-01 in the pos polarity, plus one generic Yes/No arithmetic prompt (5).
- Gates: revision pinned and serving recorded; non-thinking template, no system turn, one user turn, no think text in greedy output; Yes and No single tokens that append as one token; greedy first token exactly Yes or No in >= 4/5; 3 repeats with max |z| spread < 0.001; epsilon < 1.0; prompts match the frozen list.
- `delta = max |c_prefill - c_tokenwise|` over the two items; `epsilon = max(0.05, 2.0 * delta)`.

## Stage A: calibration gate (v2.1 thresholds, unchanged)

36 items x 2 sequences x 2 polarities = 144 prompts. All must hold:

- `S > epsilon` for >= 29/36 items, with >= 10/12 GEN_RULE, >= 9/12 MORE_SIXES and >= 8/12 MORE_REPEATS.
- `c_pos > epsilon` and `c_neg > epsilon` on the same item for >= 24/36 items.

If it fails: stop before Stage B; no rewording, reasoning, model names or moved thresholds.

## Stage B: recognition screen, only if Stage A passes

- AUTH and TYP x 40 sequences x 2 polarities = 160 prompts.
- Descriptive only, nothing confirmatory: per frame, counts of S > eps / < -eps / tie, both-polarity counts, mean S with a bootstrap over pair ids; AUC of the per-sequence score u = (z_pos - z_neg)/2 over all 20 x 20 Qwen-Mistral combinations (and per polarity); Yes bias and coherence; AUTH vs TYP; agreement with the Experiment 22 frozen classifier.
- Nothing further runs automatically: no named-model arm, no Mistral judge, no new recognition stimuli.

## Counts and order

- Preflight 5 prompts; calibration 144; screen 160.
- GPU order: seeded shuffle (seed 20261032); scores are deterministic.
- Bootstrap: 10000 resamples, seed 20261033, over items or pair ids.
- Hard GPU cap: US$5.
