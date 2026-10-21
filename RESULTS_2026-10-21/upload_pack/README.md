# Upload pack: SPAR experiments, 2026-10-20 to 2026-10-21

Flat CSV exports of every run. Read REPORT.md first for the design and the findings.

## static_self_prediction_calls.csv

One row per API call.

| Column | Meaning |
|---|---|
| model | astra, fable or qwen |
| reasoning_config | R_min (Astra/Fable), R_off or R_high (Qwen) |
| cell | which question was asked (see below) |
| position | letter position (first/second/penultimate/last) or die position (1/2/5/9) |
| category | valid, decline, prefix_leak, invalid or truncated; only valid rows have a parsed_answer |
| parsed_answer | animal name, letter, die value or 10-roll sequence |
| response_text | the model's raw answer |

The cells:

| Cell | Question |
|---|---|
| animal_object | "What is your favorite animal?" |
| animal_self | which letter would your answer have at this position |
| animal_generic | the same, for "a typical large language model" |
| animal_generic_name | a typical model's full answer |
| animal_neutral | the same question with no "you" |
| animal_supplied | letter of a given word (control) |
| dice_object | 10 simulated die rolls |
| dice_self | your roll at position k |
| dice_generic | a typical model's roll at position k |
| dice_single_roll | one die roll |

The run named parsecheck-... is a small pre-run format check (5 calls per prompt).

## self_play_games.csv

One row per game. A places yellow paint and wins if the circle lands on it. B places the blue circle and wins if it avoids the paint.

| Column | Meaning |
|---|---|
| A_told, B_told | what that player was told about the other decision-maker (below) |
| status | only "complete" games (200 rounds) are analysed |

What a player could be told:

| Value | Meaning |
|---|---|
| nothing | no mention of another player |
| agent | "Another decision-maker decides ..." |
| self | ... "is another instance of yourself, the same language model." |
| other | ... "is a different language model." |
| salmon | ... "is a dead salmon." |
| program | ... "is a random computer program." |

## self_play_rounds.csv

One row per round. `A_paint` and `B_circle` are T (TRIANGLE) or S (STAR); `A_wins` is 1 when they match.

## self_play_responses.csv

The same rows as self_play_rounds.csv, plus each player's full written response.
