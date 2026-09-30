# Data dictionary — SPAR Stimulus Corpus

## trajectories.csv (180 rows — one per trajectory)

| field | type | description |
|---|---|---|
| trajectory_id | string | Unique ID from source run (e.g. `astra_batch_00`). Stable across recompilations. |
| model | string | One of `astra`, `fable`, `mimo`. |
| method | string | One of `batch`, `history_conditioned`, `independent_calls`. |
| split | string | `development` or `holdout` (frozen at compilation). |
| replicate | int | 1..10, numbered within (cell, split). Replicate 1 in dev ≠ replicate 1 in holdout. |
| sequence | string | The 100-character H/T sequence. |
| n_flips | int | Sequence length (always 100). |
| requested_model_id | string | The OpenRouter slug that was requested (e.g. `openai/gpt-6-astra`). |
| returned_model_id | string | The model_id OpenRouter served (usually equal to requested). |
| provider | string | Serving provider reported by OpenRouter. |
| run_id | string | Source run ID. |
| first_call_utc | ISO 8601 | Timestamp of the first API attempt for this trajectory. |
| finished_utc | ISO 8601 | Timestamp when the trajectory was closed (success). |
| temperature | float | Sampling temperature (0.0 for all pilot 5 calls). |
| prompt_version | string | Prompt-set identifier (`pilot5_v1`). |
| total_api_calls_recorded | int | Every attempt made for this trajectory (including retries and failed parses). |
| trajectory_cost_usd | float | Sum of per-attempt costs for this trajectory. |
| original_replicate_index | int | Source-run replicate index (0-based). Backfill trajectories have index ≥ 20. |

## flips.csv (18,000 rows — one per flip)

| field | type | description |
|---|---|---|
| trajectory_id | string | Foreign key to `trajectories.csv`. |
| model | string | Redundant with trajectories.csv, kept for convenience in analyses. |
| method | string | Same. |
| split | string | Same. |
| replicate | int | Same. |
| trial | int | 1..100, position of the flip within the trajectory. |
| choice | char | `H` or `T`. |
| history_before | string | For `history_conditioned` only: the exact H/T history the model saw when producing this flip (empty for the other two methods). |

## metrics.csv (540 rows — one per (trajectory, prefix))

| field | type | description |
|---|---|---|
| trajectory_id | string | Foreign key to `trajectories.csv`. |
| model / method / split / replicate | | Same as trajectories.csv. |
| prefix_n | int | Prefix length the metrics are computed over (20, 50, or 100). |
| p_H | float | Proportion of H in the prefix. |
| switch_rate | float | Fraction of consecutive positions where the choice changes. |
| runs_z | float | Wald–Wolfowitz runs Z (positive = too many alternations; negative = too many runs). |
| longest_run | int | Longest consecutive run of a single symbol in the prefix. |
| HH / HT / TH / TT | float | Fractions of the four bigrams over the (prefix_n − 1) bigrams. |
| entropy_binary | float | Binary entropy of p_H (bits). |

## Related files (outside `corpus/`)

- `../../raw_attempts.jsonl` — every API attempt for the source run (immutable provenance).
- `../../trajectories/trajectory-*.json` — per-trajectory result and metadata (source of truth for this compilation).
- `../THREE_ARCHITECTURE_SOURCE_REPORT.md` — narrative analysis and headline results.
