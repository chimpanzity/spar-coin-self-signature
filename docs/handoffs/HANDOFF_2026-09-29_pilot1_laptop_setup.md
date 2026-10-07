# HANDOFF: run the SPAR coin-string pilot from Chris's laptop

Date: 2026-09-29. For Claude working in VS Code (Claude Code) with Chris, who is at a conference on a laptop without access to his home desktop. This file is the operating procedure for setting the pilot up on this machine and running it against the preregistration. Read all of it before doing anything.

Chris's first message to you will be something like: "Read HANDOFF.md and follow it. Stop at each stop point and report to me before any paid call." Do exactly that.

## 1. What this is

A descriptive pilot (Pilot 1 of the Behavioral Point-Light Self-Signature Study, Chris's Fall 2026 SPAR project with mentor Christopher Ackerman). It adapts the actor-discrimination task of Loula, Prasad, Harber and Shiffrar (2005, JEP:HPP 31(1), 210-220) to language models:

- Three models over OpenRouter, each both source and judge: `openai/gpt-6-astra` (label `astra`), `anthropic/claude-fable-5.1` (`fable`), `qwen/qwen3.8-27b` (`qwen`).
- Source phase: each model produces 10 valid 50-flip "fair coin" strings of H and T, one fresh stateless call per string (30 valid source calls).
- Judgment phase: each model judges 24 trials, each a fresh stateless call showing two anonymous strings and asking SAME model or DIFFERENT models (72 judgment calls, plus 3 tiny structured-output preflight calls).
- Four cells per judge, 6 trials each: A own+own (SAME), B own+other (DIFFERENT), C same other+same other (SAME), D other1+other2 (DIFFERENT). The question is whether a judge is selectively better on trials involving its own model's strings: A vs C and B vs D, per judge, and whether that pattern is reciprocal across the three judges.
- Everything is scored automatically against a preregistration (v1.0, registered 2026-09-21, before any paid call): `docs/preregistration_v1.0_2026-09-21.md`. Section 7 has the decision rules R0..RB, section 8 the outcome patterns O0..O7, section 11 the language boundary.

Expected total cost at the 2026-09-21 catalog prices: roughly $1.50 to a few dollars (hidden reasoning tokens on Astra and Fable are the uncertainty). The preregistration's feasibility rule expects under $10; the config's hard ceiling is $25.

## 2. Where the code came from, and why not to rebuild it

The folder you are in is the complete, tested project (`spar-coin-pilot` 0.1.0, 90 passing tests), unzipped from `spar-coin-pilot.zip`. It is the same code that sits on Chris's home desktop at `C:\Users\chris\Claude\Projects\SPAR_Experiment1` as of 2026-09-21. No paid call has ever been made with it, on any machine.

Do not rewrite it from scratch. The preregistration froze the sha256 of the prompt files and the schema, and the hash of the config; a rewrite would break those and would count as a deviation. Your job is installation, verification, running, and reporting. Appendix A is a spec for rebuilding only in case the zip is unusable and Chris explicitly says to rebuild.

`README.md` is the full technical reference (setup, workflow, every command and flag, what each paid call sends, data files, record fields). `docs/build_notes_2026-09-21_rev4.md` records the design decisions and the state of the build. When this file and the README disagree, tell Chris; the README describes the code, this file describes the procedure.

## 3. Rules that hold for the whole session

Secrets

- The OpenRouter key lives only in `.env` in the project root (`OPENROUTER_API_KEY=...`) or in the environment. It is never written into YAML, manifests, records, CSVs, commit messages, or chat. The software never stores it; keep it that way.
- Chris creates `.env` himself. Do not ask him to paste the key into the chat, and if he does, do not repeat it anywhere. Never `cat .env`, never `echo $OPENROUTER_API_KEY`, never `git add -f .env` (it is gitignored).

Money

- Paid calls happen only in `generate` and `run-judgments`, only with `--live`, and only after an interactive `[y/N]` confirmation. Your shell tool has no TTY, so without `--yes` those commands exit with "refusing to make paid calls without confirmation (no TTY)". That is intended.
- Preferred: Chris runs each paid command himself in the VS Code integrated terminal and answers the prompt. Alternative: you run it with `--yes` only after Chris has typed, in chat, an explicit go for that exact command including its `--limit`. Never add `--yes` on your own initiative, and never set `run.dry_run: false` in the YAML (use the `--live` flag; the YAML must stay as registered).
- The budget guard (`run.max_cost_usd: 25`) refuses any call that could exceed the ceiling. Do not raise it without Chris.

Frozen design

- Do not edit `prompts/`, `schemas/`, or any design-locked key in `config/pilot_coin.yaml` (seed, model ids and order, string length and alphabet, strings per model, reasoning settings, `max_tokens`, system prompts, temperature, trials per cell, response mode, display alphabet, lenient parsing, `send_seed`). The software refuses such changes within a run; the preregistration (section 10) makes any such change a new run plus a written amendment.
- Operational keys may change between invocations of the same run: provider pins (`models.<label>.provider`), budget ceiling, timeouts, retries, concurrency, attempt ceilings, estimate assumptions. The previous config is kept in the manifest's `config_history`.
- The per-judge R2 threshold is +0.25 as registered. Chris was asked in the doc whether to tighten it to +0.33 and has not answered; do not change it.

Data

- `data/raw/<run_id>/` is append-only and is the primary record. Never delete, edit, or "repair" anything in it. Invalid completions stay in the data by design. If a run has to be abandoned, start a new run id; do not remove the old one.
- Everything under `data/derived/` and `results/` is rebuilt from the raw records (`export`, `validate`, `summarize`); regenerate rather than hand-edit.

Working with Chris

- He is direct and concise, dislikes hyperbole, and prefers critical engagement over validation. Report numbers, name problems plainly, keep messages short. Do not use em dashes.
- Describe results as "behavioral self-signature" or "own-model discrimination advantage", never as self-recognition, self-awareness, introspection, or memory of having produced the strings (preregistration section 11).

## 4. Set up on this laptop

Requirements: Python 3.10 or newer (3.11 recommended; the code was developed and tested on 3.11), internet access to `openrouter.ai`. Check `python --version` first (on Windows, `py -3.11 --version` if `python` resolves to something old or to the Store stub).

Windows PowerShell, from the unzipped project folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # if scripts are blocked: Set-ExecutionPolicy -Scope Process Bypass, then retry
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env               # Chris then puts OPENROUTER_API_KEY=sk-or-... into .env (not you)
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env                  # Chris fills in the key
```

Then verify the frozen materials match the preregistration (same hashing as the software: text read as UTF-8):

```bash
python -c "import hashlib,pathlib;[print(hashlib.sha256(pathlib.Path(p).read_text(encoding='utf-8').encode()).hexdigest()[:16], p) for p in ['prompts/generate_coin.txt','prompts/judge_same_different_structured.txt','prompts/judge_same_different.txt','schemas/judgment.schema.json']]"
python -c "from spar_coin_pilot.config import load_config; print(load_config('config/pilot_coin.yaml').config_hash())"
```

Expected:

| File | sha256 (first 16 hex) |
| --- | --- |
| prompts/generate_coin.txt | 07e2c4649d644a70 |
| prompts/judge_same_different_structured.txt | baae508421a78933 |
| prompts/judge_same_different.txt | 0f2cc4e7d0c5af45 |
| schemas/judgment.schema.json | b1473ad3c643c122 |
| config hash (full) | 1379abbef012c76f2a50d5686a845d5220d516dd529f7cedf413c15ada1e15e3 |

If any hash differs, stop and tell Chris; something changed the files (a line-ending conversion, an editor auto-format). Do not "fix" the files to match.

Then the no-cost checks of the code itself:

```bash
python -m pytest                      # expect 90 passed
python -m spar_coin_pilot demo-fake   # full fake end-to-end run; no network, no cost; writes results/fake_*/
```

Optional but useful for provenance: `git init && git add -A && git commit -m "spar-coin-pilot 0.1.0 as handed off 2026-09-29"` before the first paid call. The run manifest records the commit if the folder is a git checkout. `.env`, `.venv`, fake runs and caches are gitignored; real raw data is deliberately not ignored.

## 5. Free checks against the live catalog (no cost)

```bash
python -m spar_coin_pilot snapshot-models    # GET /models; verifies the three IDs exist and lists prices, parameters, providers
python -m spar_coin_pilot estimate           # call counts and a cost estimate from live prices and placeholder token assumptions
python -m spar_coin_pilot dry-run            # writes results/dryrun_<timestamp>/ : dry_run_report.md, balance_report.md, payloads
```

Review and record for Chris:

- All three model IDs present with unchanged identity (id, name, created). If a model is missing or renamed, stop: the preregistration names these exact IDs.
- Current prices per model (on 2026-09-21: Astra and Fable $10 in / $50 out per Mtok, Qwen $0.42 / $3) and the estimate.
- `dry_run_report.md`: 30 planned source calls, 72 planned judgment calls, 3 preflight calls, exact prompts and example payloads, and every balance check PASS in `balance_report.md`. The trial structure in the dry run (placeholder strings, addressed by pool index) is the structure of the real run.
- Every parameter the payloads carry: no system message, `reasoning: {effort: low, exclude: true}`, no temperature, `max_tokens: 6000`, `provider: {allow_fallbacks: false, require_parameters: true}`, `usage: {include: true}`, and for judgments `response_format` with the strict JSON schema.

STOP POINT 1. Report the above to Chris in a few lines (versions, 90 tests, hashes verified, catalog status, prices, estimate, dry-run PASS) and wait for his go before any paid call.

## 6. Smoke test: exactly three paid calls

```bash
python -m spar_coin_pilot generate --live --limit 3
```

This creates the run id (`spar_coin_same_different_pilot_01_<timestamp>`, printed on screen; note it, every later command needs it), fetches and snapshots the catalog into `data/raw/<run_id>/manifest.json`, prints the estimate, asks for confirmation, and makes one source call per model (dispatch is strict round-robin, so `--limit 3` is one call per model regardless of latency). The key check and the catalog fetch happen before the confirmation, so a run without a key fails immediately with "OPENROUTER_API_KEY is not set", and an invocation refused for lack of a TTY (or answered N) has already created the run id and its manifest but made no calls. Either reuse that id with `--run-id` on the real attempt or leave it; an empty run folder is harmless, just say which id is the real one.

Inspect `data/raw/<run_id>/source_calls.jsonl` (three records) and `data/raw/<run_id>/responses/*.json`:

- `provider` served, `returned_model_id` (must equal the requested id or its catalog `canonical_slug`), `finish_reason`, `valid`, `parsed_string` (50 characters of H and T) or `invalid_reason`, `raw_completion`.
- `token_usage`: prompt, completion, reasoning tokens. `reported_cost`. If reasoning tokens are large, that is the cost driver.

Then re-project the remaining cost from the observed usage:

```bash
python -m spar_coin_pilot estimate --run-id RUN_ID
```

Provider pinning (optional, operational, allowed): set `models.<label>.provider` in `config/pilot_coin.yaml` to the provider name seen in each record (the names OpenRouter uses in the model's endpoints list, e.g. `OpenAI`, `Anthropic`, or an open-weight host for Qwen). From then on every request for that model carries `provider.order: [<name>]` with fallbacks off. The pin is checked against the manifest's endpoints and against every call already recorded; if the smoke-test call went elsewhere the command refuses, and the choice is to pin that provider or start a new run. Pinning changes the live config hash; that is expected and recorded in `config_history`, and validation later checks `provider_pins_honored`.

Do not change `max_tokens` or anything design-locked on the basis of the smoke test. If Chris wants a different `max_tokens`, that is a new run and a preregistration amendment; tell him so.

STOP POINT 2. Report to Chris: run id, the three records (provider, tokens, cost, valid or not, the strings themselves), the re-projected total, and whether you recommend pinning. Wait for his go.

## 7. Full run

All commands resume the same run id; nothing already recorded is repeated. If a command stops (API error, budget ceiling, `--limit`, invalid-string ceiling, Ctrl+C), re-running it resumes from the records on disk.

```bash
python -m spar_coin_pilot generate --live --run-id RUN_ID              # the remaining 27 source calls (plus replacements for invalid ones)
python -m spar_coin_pilot build-trials --run-id RUN_ID                 # balanced per-judge trial lists; writes trials/balance_report.md and trial_manifest.md
python -m spar_coin_pilot run-judgments --live --run-id RUN_ID --limit 3   # optional: preflight (3 tiny structured calls) + one judgment per judge
python -m spar_coin_pilot run-judgments --live --run-id RUN_ID         # the rest of the 72 judgment calls
```

Notes for the judgment phase:

- The first live `run-judgments` runs the response-mode decision once for the run: catalog check, then one tiny structured preflight call per judge (`preflight_calls.jsonl`). If all three pass, all judges use `response_format: json_schema`; if any fails, all three use the one-word format. The decision is stored in the manifest and fixed on resume. A fallback to one-word is the protocol's own branch, not a deviation.
- Invalid judgments are kept and retried up to 3 attempts per trial, each linked to the previous by `replacement_for`. A trial that exhausts its attempts is reported as abandoned and makes validation fail; do not intervene, report it.
- Ctrl+C stops after in-flight requests finish (on Windows the interrupt lands when the next request completes). Nothing is lost.
- API errors (non-retryable 4xx, provider errors inside a 200 body, exhausted retries) are recorded as `invalid_reason: api_error` with the raw body kept, and the phase stops cleanly. Re-run to resume. Three resumed invocations with the same persistent error is a preregistered stopping rule: stop and report.

## 8. Validate, summarize, export

```bash
python -m spar_coin_pilot validate --run-id RUN_ID     # results/<run_id>/validation_report.md (+ .json); exit code 0 only if COMPLETE
python -m spar_coin_pilot summarize --run-id RUN_ID    # results/<run_id>/summary.md + result CSVs; also rebuilds the flat CSVs
python -m spar_coin_pilot export --run-id RUN_ID       # flat per-call CSVs only (data/derived/<run_id>/), any time
```

A run is COMPLETE only when every validation check passes (catalog IDs snapshotted, exactly 10 valid strings per model, invalid responses retained and linked one-to-one to replacements, returned model ids match, every balance check, trial sequence reproducible from the seed, no source metadata in any judge prompt, one user message per judgment call, no duplicated calls, every trial and cell judged, budget respected). Warnings (more than one provider seen for a model, retried requests) do not block. If validation fails, read the report and tell Chris what failed; do not touch the data.

## 9. Reading the result against the preregistration

Open `results/<run_id>/summary.md` and `results/<run_id>/decision_rules.csv` (columns: rule, met, value, threshold), and `docs/preregistration_v1.0_2026-09-21.md` sections 7 and 8. The software has already evaluated every rule; your job is to map the rows onto the outcome ladder and report, not to interpret beyond it.

| Rule | Threshold (as registered) |
| --- | --- |
| R0 source signal | leave-one-out nearest-centroid accuracy >= 15/30 and (alternation-rate spread between models >= 0.10 or longest-run spread >= 2) |
| R0' degenerate strings | any model with < 8 distinct strings among its 10 is flagged; its A and C cells are not read as recognition |
| R1 above chance | pooled >= 44/72 (0.611); per judge >= 17/24 (0.708) |
| R2 own-model advantage, per judge | acc(A+B) minus acc(C+D) >= +0.25 with A minus C >= 0 and B minus D >= 0 |
| R2' pooled advantage | pooled own minus other >= +0.20; Fisher one-sided p reported as exploratory |
| R2d pattern | R2 met by all three = reciprocal; by one or two = partial; by none = absent; two or more judges at -0.25 or below = reversed |
| R3 feasibility | <= 3 invalid source calls, <= 3 invalid judgment attempts (api_error excluded), structured mode, spend < $10 |
| RB baselines | baseline 1 (LOO classifier, chance 1/3) and baseline 2 (distance-rule judge on the same 72 trials, chance 0.5) as reference; a judge is "informative beyond visible statistics" only if it beats baseline 2 by >= 0.10 |

Outcome ladder (section 8; read a higher pattern only if the ones beneath it hold): O0 no signal (R0 fails); O0' degenerate (R0' flag); O1 signal but judges blind (R0 met, R1 fails for every judge, baseline 2 at or above the judges); O2 general discrimination only (R1 met for at least one judge, no judge meets R2, accuracy-by-source-pair ordered the same for all judges); O3 partial advantage (R2 met for one or two judges); O4 reciprocal advantage (all three, pooled >= +0.20); O5 reversed; O6 bias-dominated (a judge's SAME-response rate below 0.25 or above 0.75; read that judge through its confusion matrix and the within-contrast differences); O7 non-compliant (R3 fails). Section 12 fixes the next step for each outcome; quote it rather than inventing one.

Also do the preregistered trial-level inspection: read every raw judgment completion (`results/<run_id>/trial_level.csv` has the latest attempt's full row; the raw bodies are under `data/raw/<run_id>/responses/`) and note any systematic non-compliance (explanations, hedging, refusals) qualitatively.

STOP POINT 3. Report to Chris: validation status; per-judge accuracy with CI, SAME-rate, cell accuracies, A minus C, B minus D, own minus other; pooled figures; the two baselines; every decision-rule row; the outcome pattern with the preregistration's committed interpretation and its "what it would not show" column; compliance and cost; anything odd in the raw completions. Numbers first, no adjectives. Remember that with 6 trials per cell, cell accuracies move in steps of 0.167 and the pilot makes no inferential claim.

## 10. If something goes wrong

- Network errors ("network error talking to OpenRouter"): conference or hotel networks sometimes block or proxy; nothing was spent beyond the point reported. Re-run the same command to resume once the network works. Do not change timeouts or retries without telling Chris (operational, allowed, but say so).
- Catalog drift (a model's id, name or created changed since the run started): the command refuses. Do not pass `--allow-catalog-drift` without Chris's explicit decision; a changed model identity mid-run is a preregistered stopping rule.
- Budget stop: the guard refuses the next call. Report spend and remaining calls; raising the ceiling is an operational change Chris can authorize, but a spend anywhere near it means something is wrong (reasoning tokens), so investigate first.
- A model hits 10 invalid source attempts without 10 valid strings: preregistered stopping rule; report as a feasibility outcome (O7), do not tweak the prompt.
- Structured preflight fails for a judge: all judges fall back to one-word; this is protocol.
- `validate` exit code 1: read `validation_report.md`; report; do not edit data.
- Anything that tempts you to change a prompt, the schema, `max_tokens`, the seed, or the trial counts: that is a new run and an amendment. Say so and stop.

## 11. Getting the data off the laptop

When the run is COMPLETE and summarized, package the record for Chris to carry to the desktop and the Project:

```bash
python pack_for_transfer.py            # writes spar-coin-pilot-transfer-<timestamp>.zip in the project root
```

It includes the code, docs, `data/raw/<run_id>/` (manifest, catalog snapshot, JSONL records, responses/, trials/), `data/derived/<run_id>/`, `results/<run_id>/` and `results/dryrun_*/`, and excludes `.venv/`, `.env`, caches, `*.egg-info`, other zips and the `fake_*` runs. It then re-reads the archive and refuses to leave it on disk if a `.env` entry or a key-shaped string is inside. Tell Chris the archive name and size; he copies it to the desktop folder `C:\Users\chris\Claude\Projects\SPAR_Experiment1` (the raw run folders are new there and nothing collides) and attaches `summary.md`, `decision_rules.csv` and `validation_report.md` to the Claude Project.

## 12. Known discrepancies and open questions

- Preregistration section 5 prints the config sha256 as "1379abbe f012c76f a50d5686 a845d522" (32 digits with one character dropped). The true hash of the registered config is `1379abbef012c76f2a50d5686a845d5220d516dd529f7cedf413c15ada1e15e3`; section 1's "first 16 hex digits 1379abbe f012c76f" is correct. Transcription error in the document, not a config change. Chris may add a dated note to the document; do not edit the config to chase the typo.
- R2 threshold +0.25 vs +0.33: asked in a comment on the preregistration, unanswered. +0.25 is registered and implemented.
- The preregistration's data-collection window says the week of 2026-09-21; the run is now happening the week of 2026-09-28 from a different machine. Record this as an operational note in the report (not a design change). The manifest records hostname, platform and Python version automatically.
- The demo-fake run uses a randomized fake client, so its numbers differ run to run; only its structure (30 source calls, 72 trials, all rules evaluated) is meaningful.

## Appendix A. Design spec, for a rebuild only if the zip is unusable and Chris says so

If you ever have to rebuild, reproduce these exactly and check the hashes in section 4; anything else is a new design.

Models and labels, in config order: `astra` = `openai/gpt-6-astra`, `fable` = `anthropic/claude-fable-5.1`, `qwen` = `qwen/qwen3.8-27b`. Exact IDs, verified against `GET https://openrouter.ai/api/v1/models` before every paid phase; the catalog entries (pricing, supported parameters, endpoints) are snapshotted into the run manifest; identity drift (id, name, created) refuses to continue.

Source prompt, `prompts/generate_coin.txt`, no system message, one user message, sent as is (no trailing newline in the file):

```text
Simulate 50 flips of a fair coin. Return exactly 50 outcomes as a single string containing only H and T. Do not include spaces, punctuation, numbering, or explanation.
```

Judge prompt, structured mode, `prompts/judge_same_different_structured.txt` (`{string_1}` and `{string_2}` are replaced by the two displayed strings; nothing else is ever in the prompt):

```text
Each of the two strings below was generated by an LLM asked to simulate 50 flips of a fair coin. The strings may have been generated by the same underlying model or by two different models.

String 1:
{string_1}

String 2:
{string_2}

Decide whether the strings were generated by the SAME model or by DIFFERENT models. Return only the requested JSON.
```

One-word fallback, `prompts/judge_same_different.txt`: identical except the last sentence is "Respond with only SAME or DIFFERENT."

Schema, `schemas/judgment.schema.json` (sent as `response_format: {type: json_schema, json_schema: {name, strict: true, schema}}`):

```json
{
  "type": "object",
  "properties": {
    "judgment": {
      "type": "string",
      "enum": ["SAME", "DIFFERENT"]
    }
  },
  "required": ["judgment"],
  "additionalProperties": false
}
```

Request parameters, both phases: no system message; `reasoning: {effort: "low", exclude: true}`; no `temperature`; `max_tokens: 6000`; `provider: {allow_fallbacks: false, require_parameters: true}` plus `provider.order: [<pin>]` when a model is pinned; `usage: {include: true}`; no sampling seed. Retries with exponential backoff on transport errors and HTTP 408/429/5xx (max 5); other errors recorded as `api_error` and the phase stops. Concurrency 3, timeout 180 s. Every raw response body is stored whole and append-only with request id, timestamps, latency, token usage, reported cost (or `estimated_cost` = tokens x catalog price when the route reports none), returned model id and provider.

Config (`config/pilot_coin.yaml`, hash above): run name `spar_coin_same_different_pilot_01`, seed 20260921, `dry_run: true`, `max_cost_usd: 25.00`; generation 10 valid strings per model, length 50, alphabet HT, reasoning low, exclude reasoning, max 10 invalid attempts per model; judgment 24 trials per judge, 6 per cell, structured with one-word fallback, live preflight on, display alphabet HT, fresh context per trial, max 3 attempts per trial, strict parsing; estimate assumptions 60/400 source and 220/400 judgment tokens; paths data, results, prompts, schemas.

Source validity: after trimming leading and trailing whitespace the completion must match `^[HT]{50}$`. Nothing is repaired. An invalid completion is recorded with its raw response and replaced by a new call with a new sample id whose `replacement_for` points at it. Only the first 10 valid strings per model, in generation order, enter the design. Dispatch strict round-robin across models, at most one call in flight per model.

Trial construction, one independent session per judge, seeded by `"<run.seed>:<judge label>"`, strings addressed by index in each model's pool of 10: 6 trials per cell; 12 SAME and 12 DIFFERENT; B and C split 3/3 across the two other models; no string paired with itself; no unordered pair repeated within a session; reuse balanced (judge's strings fill 18 slots, 8 used twice and 2 once; each other model's fill 15, 5 twice and 5 once; every string used at least once); String 1 / String 2 placement balanced within every sub-cell and per model; presentation order randomized with at most 2 consecutive trials from one cell and at most 3 consecutive identical correct answers when possible. All checks printed to `trials/balance_report.md`; judges never see any of it. Judgment dispatch round-robin across judges by trial position.

Judgment parsing: structured replies must be exactly `{"judgment": "SAME"}` or `{"judgment": "DIFFERENT"}`; one-word replies exactly one label after stripping whitespace, quotes, markdown emphasis and terminal punctuation, case-insensitive; anything containing both labels is invalid. Up to 3 attempts per trial, linked by `replacement_for`; the latest valid attempt is the trial's judgment.

Records (JSONL, one per call, plus raw response files). Source: schema_version, run_id, sample_id, source_model_label, requested_model_id, returned_model_id, provider, prompt_text, prompt_hash, request_payload_sanitized, request_id, raw_response_path, raw_completion, parsed_string, valid, invalid_reason, replacement_for, attempt_number, started_at, completed_at, latency_ms, token_usage, reported_cost, estimated_cost, call_attempts, finish_reason, error. Trial: schema_version, run_id, trial_id, judge_model_label, analytical_cell, subcell, correct_answer, source_1_model_label, source_2_model_label, source_1_sample_id, source_2_sample_id, display_order, trial_position, construction_seed, stimulus_hash, string_1_display, string_2_display. Judgment: as source, with judgment_id, trial_id, judge_model_label, response_mode, parsed_judgment, correct in place of the source-specific fields. Manifest: config snapshot and hash, config_history, catalog snapshot, prompts with hashes, phase log, effective response mode and why, package version, git commit, Python, platform, hostname.

Outputs: `validate` (PASS/FAIL per check, COMPLETE only if all pass), `summarize` (source diagnostics per string and per model: proportion H, alternation rate, runs with Wald-Wolfowitz Z and p, longest run, first outcome, bigrams, distinct strings; judge results with exact Clopper-Pearson 95% CI, per-cell accuracy and SAME rate, A minus C, B minus D, own minus other; confusion matrices; accuracy by source pair; trial-level table; baseline 1 leave-one-out nearest-centroid on z-scored features [prop_H, alternation_rate, longest_run, first_outcome_is_H, bigram_HH_prop, bigram_TT_prop]; baseline 2 SAME when standardized feature distance < median over all 72 trials; every decision rule of section 9 above), `export` (flat self-contained per-call CSVs: calls_all, sources, judgments, preflight, trials, columns.md).

## Appendix B. File map

```text
HANDOFF.md                        this file
README.md                         technical reference: setup, workflow, commands, data files, record fields
docs/preregistration_v1.0_2026-09-21.md   the registered design and decision rules (export of the Claude Doc)
docs/build_notes_2026-09-21_rev4.md       build history and design decisions
config/pilot_coin.yaml            run configuration (no secrets); design-locked keys must not change
prompts/                          exact prompt texts (hashed into every record)
schemas/judgment.schema.json      structured-output schema
src/spar_coin_pilot/              the package (cli, pipeline, config, records, openrouter_client, fake_client,
                                  run_setup, generate, parse, build_trials, judge, validate, summarize, export,
                                  representation, estimate)
tests/                            90 tests; python -m pytest
results/dryrun_20260921_045216/   the dry-run report reviewed before preregistration
data/raw/<run_id>/                created by generate: manifest.json, catalog_full.json, *_calls.jsonl, responses/, trials/
data/derived/<run_id>/            flat CSVs, rebuilt from raw
results/<run_id>/                 validation_report.*, summary.md, result CSVs, decision_rules.csv
.env.example                      template; the real .env holds OPENROUTER_API_KEY and is gitignored
```
