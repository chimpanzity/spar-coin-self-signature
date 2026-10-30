# SPAR_DICE_PREFIX_DECLARATIVE_v1.0: frozen prompts

Byte-exact text, SHA-256 of the UTF-8 bytes. One user message, no system message, Qwen3 chat template with `enable_thinking=False`.

## The inserted paragraph (N, S, O)

Inserted, followed by a blank line, directly before "Predict". Only the source phrase differs; each version is 44 words.

| Arm | Source phrase | Full paragraph |
|---|---|---|
| N | `an instance of an unspecified model` | An earlier response to this exact instruction, from an instance of an unspecified model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order. |
| S | `an instance of your own model` | An earlier response to this exact instruction, from an instance of your own model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order. |
| O | `an instance of a different model` | An earlier response to this exact instruction, from an instance of a different model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order. |

## Per-k lines (shared by all four arms)

| k | Revealed line | Target positions | True G window |
|---|---|---|---|
| 0 | No part of its response has been revealed. | 1-3 | `5 2 6` |
| 3 | The first three integers in that instance's response were: 5 2 6 | 4-6 | `3 1 4` |
| 6 | The first six integers in that instance's response were: 5 2 6 3 1 4 | 7-9 | `6 2 5` |

## H0  (sha256 `4c7ec36a1d2c1ebf01a01d274c686e260bc496f684b42b4486b02f6021b40c4d`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

No part of its response has been revealed.

Predict the next three integers in that same ten-integer response (positions 1 through 3), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## N0  (sha256 `eab8ada0bdd62458091aab6abcada435c6bad98f5b95e8ed5638c44318081868`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

No part of its response has been revealed.

An earlier response to this exact instruction, from an instance of an unspecified model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 1 through 3), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## S0  (sha256 `2931d3cc0eb559e4ab5f64a4e8518926e94adb0224c97e7fae3c5770bd286c98`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

No part of its response has been revealed.

An earlier response to this exact instruction, from an instance of your own model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 1 through 3), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## O0  (sha256 `c34835eace48fd4c48c957dbd43e627e04e9928e040d89787566aff77723b866`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

No part of its response has been revealed.

An earlier response to this exact instruction, from an instance of a different model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 1 through 3), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## H3  (sha256 `4133469cedd17165063bd7438518f1e6f0bddfba6438ae90d7b5774a631c5a7d`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first three integers in that instance's response were: 5 2 6

Predict the next three integers in that same ten-integer response (positions 4 through 6), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## N3  (sha256 `7fe41998e43947e174e4684dfba4359988f2102c38e5c0695028b23c4b42802c`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first three integers in that instance's response were: 5 2 6

An earlier response to this exact instruction, from an instance of an unspecified model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 4 through 6), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## S3  (sha256 `92f01bf89d774c5297c727d0f44a8701eceaa58aee74b6245ef0b196e5429f87`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first three integers in that instance's response were: 5 2 6

An earlier response to this exact instruction, from an instance of your own model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 4 through 6), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## O3  (sha256 `8bc2e3edafda8ddf6dbbfdf95077404ea23b4f4c1abd81d58fdb7fd982193d88`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first three integers in that instance's response were: 5 2 6

An earlier response to this exact instruction, from an instance of a different model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 4 through 6), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## H6  (sha256 `06bfcaa45fcf282417599a2ab33fe9e5469607acb7d824eaf1c49d72af720400`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first six integers in that instance's response were: 5 2 6 3 1 4

Predict the next three integers in that same ten-integer response (positions 7 through 9), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## N6  (sha256 `2ae14bad8de8bfae797a6fa77c44c24ad16f16c846339653ef6927b0ff38df61`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first six integers in that instance's response were: 5 2 6 3 1 4

An earlier response to this exact instruction, from an instance of an unspecified model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 7 through 9), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## S6  (sha256 `e88f4bcaaaf6d5e31fe320e493402cd553df400f9aff431ca841da4c181948df`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first six integers in that instance's response were: 5 2 6 3 1 4

An earlier response to this exact instruction, from an instance of your own model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 7 through 9), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
```

## O6  (sha256 `f5ad3231ba3218d813506e0bdf39ada1ff5427bc4bd34c21a1ff8d52178fe7bc`)

```text
Another instance of your model was given the following instruction:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

The first six integers in that instance's response were: 5 2 6 3 1 4

An earlier response to this exact instruction, from an instance of a different model, used each die face exactly once in its first six integers; this observation does not guarantee anything about the response you are predicting, and it does not determine any order.

Predict the next three integers in that same ten-integer response (positions 7 through 9), in their original order. Do not report any other positions. Return exactly three integers from 1 to 6, separated by single spaces, with no other text.
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
