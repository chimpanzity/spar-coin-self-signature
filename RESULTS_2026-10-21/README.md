# Results: 2026-10-20 to 2026-10-21

Everything from the last 24 hours of testing is in this folder. Start with **REPORT.md**.

**To upload to another LLM, use `upload_pack_2026-10-21.zip`:** flat CSVs of all the data, plus the report and a data dictionary.

| File | What it is |
|---|---|
| `REPORT.md` | The full write-up of both studies: findings, tables, limitations |
| `pilot_audit.md` | Audit of the earlier pilot claims against their logs |

## 1_static_self_prediction/

Can a model predict a property of its own answer (a letter of its favourite animal, a dice roll at position k) without producing the answer?

| File | What it is |
|---|---|
| `match_animal.png`, `match_dice.png` | **Main figures.** How often each kind of prediction matches the model's real answers |
| `comparison_table.csv` | The numbers behind the figures: one row per model × task × position |
| `supplied_answer_check.csv` | Control: letter extraction from a given name (100% everywhere) |
| `response_categories.csv` | Valid, declined and unusable answers per cell |
| `run_summary.json` | Calls made (9,920), cost ($14.88), each model's own favourite animal |
| `qwen_parse_check_summary.json` | Pre-run check that Qwen answers in a usable format |
| `prompts_frozen.txt` | The exact prompts used |

## 2_self_play/

Two copies of a model play paint-and-circle (matching pennies). Does telling a player the other is itself change how it plays?

| File | What it is |
|---|---|
| `pi_vs_win.png` | **Main figure.** Each condition's predictability vs win rate |
| `cell_summary.csv` | One row per condition × seat: win rate, predictability (PI), Brown–Rosenthal etc. |
| `contrasts_vs_baseline.csv` | Each condition compared with its no-disclosure baseline |
| `seat_sessions.csv` | One row per game and seat (119 games, including the Fable follow-up) |
| `shadow_calibration.json` | Simulation that chose the 50-round history window |

## 3_fable_followup/

17 more Fable games (6 per condition), testing whether Fable's drop in predictability is specific to being told "another instance of yourself". **It is not.** Telling Fable that the opponent is "a different language model" works almost as well; only "another decision-maker exists" falls clearly short. See the update at the top of REPORT.md and Part III.

| File | What it is |
|---|---|
| `fable_specificity.json` | **The prespecified result:** primary contrasts (Holm-adjusted) and secondary contrasts |
| `fable_seatA_sessions.csv` | One row per Fable game (seat A): predictability, win rate, exploitation indices, etc. |
| `plan_and_prespecified_analysis.json` | The sessions and the analysis fixed before the data came in |

## Raw data (not copied, too large)

| What | Where |
|---|---|
| Static study, every call | `data/spar_dynamic/static_selfpred/main-20261021T021451Z/raw_attempts.jsonl` |
| Self-play, every round | `paint_circle/results/pilot-20261020/`, `main-20261020/`, `makeups-20261020/`, `fable-specificity-20261021/` (one subfolder per game) |
| Code | `spar_dynamic/static_selfpred/` and `paint_circle/` |
