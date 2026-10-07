# SPAR coin-string SAME/DIFFERENT pilot: software build notes (2026-09-21, rev. 4)

Copy of the Claude Project doc `claude/SPAR_Coin_String_Pilot_Build_Notes_2026-09-21.md`, included so the laptop copy is self-contained.

Implements `SPAR_Coin_String_Pilot_Claude_Handoff_2026-09-21.md` as a Python project, with Chris's four corrections from the review of the first build applied (rev. 2), PACA-style flat per-call CSVs (rev. 3), and the preregistration's baselines and decision rules built into `summarize` (rev. 4).

## Where it lives

`C:\Users\chris\Claude\Projects\SPAR_Experiment1` on the home desktop (project root; README.md has setup and the full workflow). The laptop copy (this folder) is the same code as of 2026-09-21.
Package `spar_coin_pilot` under `src/`; run with `python -m spar_coin_pilot <command>`.

## Preregistration (rev. 4)

"Coin-String Pilot Preregistration" (Claude Doc in the Project, v1.0, 2026-09-21; markdown export in `docs/preregistration_v1.0_2026-09-21.md`) fixes hypotheses H0 (source signal), H1 (above-chance discrimination), H2a-d (own-model advantage per judge, its SAME and DIFFERENT components, reciprocal selectivity) and H3 (feasibility), the frozen design and materials (prompt and schema sha256, config hash 1379abbe..., seed 20260921), numeric decision rules (R0 LOO classifier >= 15/30 plus a statistic spread; R1 >= 44/72 pooled or >= 17/24 per judge; R2 own-other >= +0.25 per judge with both contrasts >= 0; R2' pooled >= +0.20 with exploratory Fisher p; R2d reciprocal/partial/absent/reversed; R3 feasibility; RB baselines), an outcome table O0-O7 with committed interpretations, stopping rules, deviations policy, interpretation boundaries and outcomes-to-next-steps. Registered before any paid call. Chris was asked in a doc comment whether the R2 threshold should stay at +0.25 or tighten to +0.33 (unanswered as of 2026-09-29; +0.25 stands).

`summarize` computes both external baselines (leave-one-out nearest-centroid source classifier on standardized string statistics; a median-split distance-rule judge scored on the same 72 trials) and evaluates every preregistered rule, writing `results/<run_id>/decision_rules.csv`, `baseline_loo_classifier.csv`, `baseline_distance_judge.csv` and a section in `summary.md`.

## Status

- All handoff section 16 deliverables built: scaffold, YAML config, prompts, OpenRouter client (catalog validation, retries, resume, budget guard), strict source generation, balanced four-cell trial builder with balance report, judgment runner (structured output with global one-word fallback after preflight), validate + summarize + export, 90 tests (fake-client end-to-end, mock-transport tests of the real client, resume/crash cases, provider pins, config locking, flat export, baselines and rules), dry-run report in `results/dryrun_20260921_045216/` showing 30 source + 72 judgment calls (+3 optional preflight calls).
- No paid calls have been made. `run.dry_run: true`; paid calls need `--live` plus an interactive confirmation.
- Live OpenRouter catalog (2026-09-21): all three IDs exist. `openai/gpt-6-astra` and `anthropic/claude-fable-5.1` at $10/$50 per Mtok (no temperature parameter); `qwen/qwen3.8-27b` at $0.42/$3. All advertise reasoning, response_format, structured_outputs.
- Cost: about $1.53 for the whole pilot at those prices under placeholder token assumptions. Provisional: hidden reasoning tokens will dominate for Astra and Fable. `estimate --run-id RUN_ID` re-projects from the observed token usage after the smoke test. Ceiling in config is $25.

## Design decisions discussed with Chris (Sept 21, 2026)

- Source strings: one stateless call per string, the whole 50-flip string in one completion (the Van Koevering & Kleinberg 2024 regime; their "Flip 20 coins" prompts produced whole sequences, and their single-flip prompts with no history were nearly 100% heads). A sequential variant (50 fresh calls per string with the history in the prompt) is a distinct later condition, closer to PACA and the STAY/SWITCH representation, ~1,500 calls.
- Judges: a new stateless instance for every trial (no session, no feedback, no history); the "session" is researcher-side bookkeeping. This departs from Loula et al.'s within-session human design deliberately, and it is what makes the string-reuse schedule safe. A within-conversation judge variant is a possible follow-up needing 48 unique strings per judge. Chris confirmed he likes it as is.

## Data files (rev. 3, Chris's "kitchen sink" convention from PACA)

`data/derived/<run_id>/calls_all.csv`: one self-contained row per API call (source, preflight, judgment), about 130 columns: run context and seeds (run_seed, config_hash, package version, git commit, python, platform, hostname, prompt hashes, effective response mode), call metadata (ids, models, provider served and pinned, attempts, replacement link, validity, timestamps, latency, HTTP attempts, finish reason, costs), the exact request (prompt text, max_tokens, reasoning settings, temperature/seed if sent, provider routing, response_format, full request body JSON), the response (raw completion verbatim, parsed value, correctness, response id, system_fingerprint, reasoning text/details if not excluded, headers), token usage broken out (incl. reasoning_tokens), the catalog snapshot for the model (name, created, canonical_slug, prices, supported parameters, endpoint providers), and for judgment rows the full trial design (cell, sub-cell, correct answer, source pair, sample ids, display order, construction_seed, build attempts, ordering run lengths, stimulus hash, both displayed and both canonical strings, provenance of each source string). Split views: `sources.csv` (+ per-string diagnostics), `judgments.csv`, `preflight.csv`, `trials.csv`; `columns.md` is the column dictionary. `results/<run_id>/trial_level.csv` is one row per trial with the latest attempt's full row. Rebuilt from the raw JSONL/JSON any time with `export --run-id`.

Seeds: `run_seed` (trial construction), `construction_seed` per judge, `build_attempts`. API sampling seeds are not sent by default (handoff did not ask); `openrouter.send_seed: true` sends a deterministic per-call seed to models advertising `seed`, recorded as `api_seed`/`api_seed_sent` (design-locked).

## Corrections applied after Chris's review (rev. 2)

1. Loula et al. (2005) citation: Journal of Experimental Psychology: Human Perception and Performance, 31(1), 210-220 (README and these notes; the JESP citation in the original handoff was wrong).
2. Judge prompt now opens: "Each of the two strings below was generated by an LLM asked to simulate 50 flips of a fair coin. The strings may have been generated by the same underlying model or by two different models." (both the structured and one-word variants; the closing instruction sentences are unchanged).
3. Provider pinning: `models.<label>.provider` in the YAML sends `provider.order: [<name>]` with fallbacks off. Checked before spending against the model's endpoints (from the manifest's catalog snapshot) and against the provider of every call already recorded in the run; validation adds `provider_pins_honored`. Intended use: run `generate --live --limit 3`, read `provider` in the three records, pin, resume the same run id.
4. `estimate --run-id` for usage-based re-projection (see Status).

Procedural check: source calls are dispatched strict round-robin across models with at most one call in flight per model, so `--limit 3` is exactly one call per model regardless of provider latency; judgment calls are round-robin across judges by trial position.

## Key implementation decisions

- Reasoning sent as OpenRouter's unified `reasoning: {effort: low, exclude: true}`; no temperature; `provider: {allow_fallbacks: false, require_parameters: true}`; `usage: {include: true}` for per-call cost.
- `max_tokens` 6000 for both phases so reasoning tokens (and Anthropic's minimum 1024-token reasoning budget) fit; the strict parser rejects bad output. `max_tokens` is design-locked: changing it after the smoke test means a new run, because it sets the reasoning budget on Anthropic routes.
- Config change policy: design parameters (seed, model ids/order, string length/alphabet, strings per model, reasoning settings, max_tokens, system prompts, temperature, trials per cell, response mode, display alphabet, lenient parsing, send_seed) cannot change within a run; operational ones (provider pins, budget ceiling, timeouts, retries, concurrency, attempt ceilings, estimate assumptions) can, with the previous config kept in `config_history`. `build-trials`, `validate`, `summarize`, `export` use the manifest's config.
- Trial builder addresses strings by pool index, so the dry run's placeholder trials have the same pairing structure as the real run. Reuse: judge strings fill 18 slots (8x2, 2x1), each other model's 15 (5x2, 5x1).
- Invalid completions are never repaired: recorded as invalid, replaced by the model's next call linked via `replacement_for` (one-to-one, checked by validation). API/transport failures are recorded as `api_error`, stop the phase cleanly, and do not count toward the malformed-output ceilings.
- Response mode decided once per run (catalog check + 3 tiny live preflight calls) and fixed on resume.
- Returned model id must equal the requested id or the catalog `canonical_slug`. Raw data is append-only; CSVs and results are rebuilt from it.

## Next steps for the pilot run

See `HANDOFF.md` in the project root (2026-09-29) for the laptop run procedure with its stop points.

1. venv, `pip install -e ".[dev]"`, key into `.env`, `python -m pytest`, `python -m spar_coin_pilot demo-fake`.
2. `snapshot-models`, `estimate`, `dry-run` against the live catalog; review `dry_run_report.md` and `balance_report.md`.
3. `generate --live --limit 3` (one call per model); inspect provider, token_usage, finish_reason; `estimate --run-id RUN_ID`; pin providers if wanted; then `generate --live --run-id RUN_ID`, `build-trials`, `run-judgments --live`, `validate`, `summarize`; read `decision_rules.csv` against section 8 of the preregistration.

## Notes

- Switching `display_alphabet` to AB requires revising the judge prompt (it still says "flips of a fair coin").
