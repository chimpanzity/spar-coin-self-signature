# SPAR: self-modelling in language models

Do language models know their own behaviour? This repository holds every experiment run for the SPAR project, from September 21 to October 21, 2026. The work runs in two parallel, complementary tracks:

| Track | Question | Folder |
|---|---|---|
| **1. Static self-prediction and self-modelling** (focus of the mid-term report) | Can a model recognise or predict its own outputs (coin-flip sequences, dice rolls, favourite answers) better than another model's, and is any success knowledge of *itself*? | [`track1_self_prediction/`](track1_self_prediction/) |
| **2. Game theory** | Does knowing that another player is *the same model* change how a model reads or plays against it? | [`track2_game_theory/`](track2_game_theory/) |

Each track has a README that tells its story in order. Each experiment has its own dated folder holding its data, results and reports, with a README covering what was run, the questions, the results, the open questions and what came next.

## Main findings so far

1. **Models have behavioural signatures but do not show self-specific knowledge of them.** Their coin-flip statistics and favourite answers identify them, yet across attribution (track 1, 02–11), forecasting (12–13) and hypothetical self-prediction (14–20), no model reliably does better about itself than about "a language model" in general.
2. **Apparent self-knowledge turns out to be knowledge of procedures, defaults or framing.**
   - Fable's strongest track 1 results are explained by the stated generation procedure (track 1, 10) and by a default answer it shares with "a typical model" (track 1, 20).
   - Its strongest track 2 result, becoming unpredictable when told it faces itself, is matched by telling it the opponent is a *different* language model (track 2, 11).
3. **Models can reproduce their outputs but not predict their properties.** They replay sequences they would generate, but single-position questions fall back on defaults (track 1, 16–20).

## Timeline (both tracks)

| Date | Track | Experiment | Key result |
|---|---|---|---|
| Sep 21 | 1 | [01 Preregistered SAME/DIFFERENT harness](track1_self_prediction/01_2026-09-21_preregistered_harness/) | Built and dry-run only |
| Sep 29 | 1 | [02 Pilot 1: source signatures](track1_self_prediction/02_2026-09-29_pilot1_source_signature/) | Signatures exist; no self advantage |
| Sep 29 | 1 | [03 Pilot 2: SELF vs OTHER](track1_self_prediction/03_2026-09-29_pilot2_self_vs_other/) | Models almost never answer SELF |
| Sep 29 | 1 | [04 Pilot 3: provenance](track1_self_prediction/04_2026-09-29_pilot3_provenance/) | No self-specific provenance effect |
| Sep 29 | 1 | [05 Pilot 4: Astra follow-up](track1_self_prediction/05_2026-09-29_pilot4_astra_followup/) | Did not replicate |
| Sep 30 | 1 | [06 Stimulus corpus](track1_self_prediction/06_2026-09-30_stimulus_corpus/) | 180 sequences of 100 flips; 3 models × 3 generation methods |
| Oct 1 | 1 | [07 FCE1](track1_self_prediction/07_2026-10-01_fce1_history_conditioned/) | No self advantage |
| Oct 1 | 1 | [08 FCE2](track1_self_prediction/08_2026-10-01_fce2_batch_and_independent/) | Self advantage only for Fable under independent calls |
| Oct 1 | 1 | [09 A/B task validation](track1_self_prediction/09_2026-10-01_ab_task_validation/) | Answer format works |
| Oct 1 | 1 | [10 Story swap](track1_self_prediction/10_2026-10-01_story_swap/) | Fable's "self-recognition" follows the stated procedure |
| Oct 1 | 1 | [11 Phenotype prediction](track1_self_prediction/11_2026-10-01_phenotype_prediction/) | Same forecast for every target |
| Oct 7 | 1 | [12 Phase 2 (Qwen)](track1_self_prediction/12_2026-10-07_phase2_qwen/) | Judges default to 0.5 |
| Oct 8 | 1 | [13 Phase 2 (MiMo)](track1_self_prediction/13_2026-10-08_phase2_mimo/) | Same floor; coin-flip line parked |
| Oct 9 | 2 | [01 Blind Twin v1 (MP)](track2_game_theory/01_2026-10-09_blind_twin_v1_mp/) | Parser failure |
| Oct 9 | 2 | [02 Blind Twin v2 (MP)](track2_game_theory/02_2026-10-09_blind_twin_v2_mp/) | Small self-label effect |
| Oct 9 | 2 | [03 Blind Twin RPS](track2_game_theory/03_2026-10-09_blind_twin_rps/) | True label beats false in every run; Fable-driven |
| Oct 9 | 2 | [04 Opponent disclosure pilot](track2_game_theory/04_2026-10-09_opponent_disclosure_pilot/) | Told Matcher +5 pp |
| Oct 10 | 2 | [05 Study 1 Exp. 1: disclosure, 3 models](track2_game_theory/05_2026-10-10_study1_exp1_disclosure/) | No overall self-specific effect |
| Oct 10 | 2 | [06 Exp. 2: Blind Twin judges](track2_game_theory/06_2026-10-10_exp2_blind_twin_judges/) | Small, Fable-driven label effects |
| Oct 11 | 2 | [07 Self-self judges + retest](track2_game_theory/07_2026-10-11_selfself_judges_and_retest/) | No twin advantage; 80% judge reproducibility |
| Oct 11 | 2 | [08 Post-hoc analyses](track2_game_theory/08_2026-10-11_post_hoc_analyses/) | Fable's label effect ≈ 24–32 games of observation |
| Oct 11 | 2 | [09 PACA believed-self](track2_game_theory/09_2026-10-11_paca_believed_self/) | No consistent framing effect |
| Oct 15 | 1 | [14 Dice v3.1](track1_self_prediction/14_2026-10-15_dice_v31/) | Predictions collapse to a default |
| Oct 15 | 1 | [15 Dice: more models](track1_self_prediction/15_2026-10-15_dice_model_extension/) | No model passes |
| Oct 16 | 1 | [16 Dice v4.1](track1_self_prediction/16_2026-10-16_dice_v41/) | Can replay sequences, cannot predict positions |
| Oct 16 | 1 | [17 Favourite integer](track1_self_prediction/17_2026-10-16_favorite_integer/) | Famous strings (π) |
| Oct 16 | 1 | [18 Favourite animal](track1_self_prediction/18_2026-10-16_favorite_animal/) | Fable 20/20 letters, Astra 0/20 |
| Oct 16 | 1 | [19 Favourite animal, crossed](track1_self_prediction/19_2026-10-16_favorite_animal_crossed/) | Astra predicts Fable's letters, not its own |
| Oct 20–21 | 1 | [20 Static self-prediction replication](track1_self_prediction/20_2026-10-20_static_selfpred_replication/) | No self-over-generic advantage (9,920 calls) |
| Oct 20–21 | 2 | [10 Paint-and-circle self-play](track2_game_theory/10_2026-10-20_paint_circle_selfplay/) | Told "self", Fable became unpredictable |
| Oct 21 | 2 | [11 Fable specificity](track2_game_theory/11_2026-10-21_paint_circle_fable_specificity/) | Not specific to "self" |
| Oct 21 | 2 | [12 Fable perspective-taking](track2_game_theory/12_2026-10-21_paint_circle_fable_perspective/) | Guidance works under both labels |
| Oct 21 | 2 | [13 Scripted-opponent pilot](track2_game_theory/13_2026-10-21_paint_circle_scripted_opponent_pilot/) | Fable exploits simple scripted patterns almost immediately; the measures behave as intended |
| Oct 21 | 2 | [14 Identity framing vs scripted opponent](track2_game_theory/14_2026-10-21_paint_circle_scripted_identity_framing/) | The pattern beats the framing: no label stops exploitation; residual effects are not self-specific |

The two tracks also connect directly:
- **Oct 8–9:** track 1's forecasting floor (13) motivated the move to games (track 2).
- **Oct 15:** the Oct 9–11 games led back to simpler self-prediction tests (track 1, 14).
- **Oct 20–21:** the paint-and-circle self-play (track 2, 10) ran alongside the static replication (track 1, 20).

## Repository layout

| Path | Contents |
|---|---|
| `track1_self_prediction/` | 20 dated experiment folders: data, results, reports, README each |
| `track2_game_theory/` | 14 dated experiment folders |
| `src/` | All Python code (packages keep their original names); `src/repo_paths.py` maps old paths to new ones |
| `tests/` | Test suite (`python -m pytest`) |
| `docs/` | Cross-cutting documents. `reports/` holds combined write-ups. Also preregistration, weekly handoffs, references, the research synthesis, `REORGANISATION_2026-10-21.md`, `PATH_MAP.md`, and `archive/` (earlier README, review guide, llms.txt) |
| `exports/` | Flat CSV upload packs for analysis elsewhere |

The repository was reorganised into this layout on 2026-10-21, and no data changed. Older reports refer to the previous paths; see [`docs/PATH_MAP.md`](docs/PATH_MAP.md) and [`docs/REORGANISATION_2026-10-21.md`](docs/REORGANISATION_2026-10-21.md). The pre-reorganisation state is git tag `pre-reorg-2026-10-21`.

## Running the code

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt pytest   # Windows paths shown
export PYTHONPATH=src           # PowerShell: $env:PYTHONPATH = "src"
python -m pytest                 # full test suite
```

Live runs call models through OpenRouter and need `OPENROUTER_API_KEY` in `.env` at the repository root (git-ignored). Each experiment README gives the exact commands for that experiment.

## Models

| Name used here | Model |
|---|---|
| Astra | `openai/gpt-6-astra` |
| Fable | `anthropic/claude-fable-5.1` |
| Qwen | `qwen/qwen3.8-27b` in the Sep 29 pilots and the Oct 9–11 games; `qwen/qwen3-8b` in Phase 2 (Oct 7); `qwen/qwen3-32b` from Oct 15 (SiliconFlow from Oct 20) |
| MiMo | MiMo-v2.6-pro (Sep 30–Oct 8) |
| Others | GPT-OSS-120B/20B and Sonnet 5.5 in the Oct 15–16 dice pilots |

Settings and costs are in each experiment's README.
