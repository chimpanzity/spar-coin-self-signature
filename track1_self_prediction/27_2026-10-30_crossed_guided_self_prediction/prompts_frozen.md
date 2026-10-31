# SPAR_CROSSED_GUIDED_SELFPRED_v1.0: frozen prompts

Byte-exact templates. One user message, no system message, no tools. Qwen: Qwen3 chat template with `enable_thinking=False`. Mistral: mistral_common tekken v11 `[INST]...[/INST]`, no system prompt.

A crossed prompt is the blocks below joined by one blank line: header, the Experiment 21 instruction (verbatim), the revealed history, the evidence paragraph (I and D only), the request.

## Header (framing)

| Framing | Used when | Text |
|---|---|---|
| A | all cells | A language model was given the following instruction: |
| T | all cells; NAME = `Qwen3-32B` or `Mistral Small 3.2 24B Instruct` (the true target) | The language model {NAME} was given the following instruction: |
| R | predictor = target generator | Another instance of your own model was given the following instruction: |
| R | predictor != target generator | A different model, not your own model, was given the following instruction: |

## Instruction (verbatim, sha256 `edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe`)

```text
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
```

## Revealed history and request (condition)

| Condition | Suite | Revealed | Scored positions | History text (example: Qwen's G) | Request |
|---|---|---|---|---|---|
| k0 | bridge | 1-0 | 1-3 | None of the ten integers in that model's response has been revealed to you. | Predict the integers at positions 1 through 3 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text. |
| k3 | immediate | 1-3 | 4-6 | The first three integers in that model's response (positions 1 through 3) were: 5 2 6 | Predict the integers at positions 4 through 6 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text. |
| k6 | immediate+fixed7 | 1-6 | 7-9 | The first six integers in that model's response (positions 1 through 6) were: 5 2 6 3 1 4 | Predict the integers at positions 7 through 9 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text. |
| k8 | immediate | 1-8 | 9-10 | The first eight integers in that model's response (positions 1 through 8) were: 5 2 6 3 1 4 6 2 | Predict the integers at positions 9 through 10 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly two integers from 1 to 6, separated by single spaces, with no other text. |
| m0 | fixed7 | 1-0 | 7-9 | None of the ten integers in that model's response has been revealed to you. | Predict the integers at positions 7 through 9 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text. |
| m3 | fixed7 | 1-3 | 7-9 | The first three integers in that model's response (positions 1 through 3) were: 5 2 6 / The integers at positions 4 through 6 are not revealed to you. | Predict the integers at positions 7 through 9 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text. |

## Evidence paragraph

H adds nothing. I and D have the same number of words (35 and 35, digits counted as words).

I:

```text
For reference, a standard six-sided die has six faces, numbered one to six, and the numbers on its opposite faces add up to seven.
That general fact is not about the response you are predicting.
```

D (`{REF}` = the assigned reference-corpus sequence of the target generator):

```text
For reference, a separate earlier response by that same model to this exact instruction was:
{REF}
That earlier response is not the response you are predicting.
```

## Example: Mistral predicts Qwen's G, m3, TD

```text
The language model Qwen3-32B was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first three integers in that model's response (positions 1 through 3) were: 5 2 6
The integers at positions 4 through 6 are not revealed to you.

For reference, a separate earlier response by that same model to this exact instruction was:
3 1 5 6 2 4 1 3 6 2
That earlier response is not the response you are predicting.

Predict the integers at positions 7 through 9 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## Example: Qwen predicts Qwen's G, k3, RH

```text
Another instance of your own model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first three integers in that model's response (positions 1 through 3) were: 5 2 6

Predict the integers at positions 4 through 6 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## Example: Qwen predicts Mistral, k0, AI

```text
A language model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

None of the ten integers in that model's response has been revealed to you.

For reference, a standard six-sided die has six faces, numbered one to six, and the numbers on its opposite faces add up to seven.
That general fact is not about the response you are predicting.

Predict the integers at positions 1 through 3 of that same ten-integer response, in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## Reference G (Experiment 21, unchanged; sha256 `edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe`)

```text
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
```

## Reference F (Experiment 21, unchanged; sha256 `8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03`)

```text
Give me the output you predict from another instance of your model that is asked to do the following:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

Return exactly the 10 integers you predict that instance would output, separated by single spaces, with no other text.
```

## Reference Fanon (Experiment 21, unchanged; sha256 `09afdbeec5d8c4c12bea04a8a922aee462350a50a935b776ef87ca94fc0423f1`)

```text
Give me the output you predict from another language model that is asked to do the following:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

Return exactly the 10 integers you predict that instance would output, separated by single spaces, with no other text.
```

## Experiment 26 archival prompts (Qwen predictor on Qwen's G only)

| Condition | sha256 |
|---|---|
| x26_H0 | `4c7ec36a1d2c1ebf01a01d274c686e260bc496f684b42b4486b02f6021b40c4d` |
| x26_N0 | `eab8ada0bdd62458091aab6abcada435c6bad98f5b95e8ed5638c44318081868` |
| x26_S0 | `2931d3cc0eb559e4ab5f64a4e8518926e94adb0224c97e7fae3c5770bd286c98` |
| x26_O0 | `c34835eace48fd4c48c957dbd43e627e04e9928e040d89787566aff77723b866` |
| x26_H3 | `4133469cedd17165063bd7438518f1e6f0bddfba6438ae90d7b5774a631c5a7d` |
| x26_N3 | `7fe41998e43947e174e4684dfba4359988f2102c38e5c0695028b23c4b42802c` |
| x26_S3 | `92f01bf89d774c5297c727d0f44a8701eceaa58aee74b6245ef0b196e5429f87` |
| x26_O3 | `8bc2e3edafda8ddf6dbbfdf95077404ea23b4f4c1abd81d58fdb7fd982193d88` |
| x26_H6 | `06bfcaa45fcf282417599a2ab33fe9e5469607acb7d824eaf1c49d72af720400` |
| x26_N6 | `2ae14bad8de8bfae797a6fa77c44c24ad16f16c846339653ef6927b0ff38df61` |
| x26_S6 | `e88f4bcaaaf6d5e31fe320e493402cd553df400f9aff431ca841da4c181948df` |
| x26_O6 | `f5ad3231ba3218d813506e0bdf39ada1ff5427bc4bd34c21a1ff8d52178fe7bc` |
