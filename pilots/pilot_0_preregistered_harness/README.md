> **Archive note (2026-10-07).** This is the original `spar-coin-pilot` 0.1.0
> harness, built for the coin-string SAME/DIFFERENT pilot preregistered on
> 2026-09-21. Its preregistration and build notes are now in
> [`docs/preregistration/`](../../docs/preregistration/), and the laptop setup
> procedure is in
> [`docs/handoffs/HANDOFF_2026-09-29_pilot1_laptop_setup.md`](../../docs/handoffs/HANDOFF_2026-09-29_pilot1_laptop_setup.md).
> As of that handoff no paid calls had been made with this harness. The
> pilots that were actually run (`pilot_1` to `pilot_4`) used the
> `spar_dynamic` package at the repository root. `results/dryrun_*` is a
> no-cost dry run. Paths below such as `C:\Users\chris\...` refer to the
> original development machine.

# SPAR coin-string SAME/DIFFERENT pilot

Behavioral self-signature pilot adapted from the actor-discrimination task in Loula et al.
(2005), run over OpenRouter. Three language models (Astra, Fable, Qwen3.8 27B) each produce
ten 50-flip "fair coin" strings in fresh contexts. The same models then judge, one stateless
call per trial, whether two anonymous strings came from the SAME model or DIFFERENT models.
The question is not raw accuracy but whether each judge is selectively better on trials
involving its own model's strings.

Four analytical cells per judge (6 trials each, 24 per judge, 72 judgment calls in total):

| Cell | Sources relative to judge         | Correct   |
|------|-----------------------------------|-----------|
| A    | own + own                         | SAME      |
| B    | own + other (3 per other model)   | DIFFERENT |
| C    | same other + same other (3 each)  | SAME      |
| D    | other 1 + other 2                 | DIFFERENT |

Contrasts of interest: A vs C (SAME trials) and B vs D (DIFFERENT trials).

Everything that can spend money is off by default (`run.dry_run: true`), asks for confirmation,
is capped by a hard cost ceiling, and can be resumed without duplicating calls.

## Setup (Windows, VS Code terminal)

```powershell
cd C:\Users\chris\Claude\Projects\SPAR_Experiment1
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env      # then put your key in .env:  OPENROUTER_API_KEY=sk-or-...
```

Python 3.10+ (3.11 recommended). On macOS/Linux use `source .venv/bin/activate`.

The key is read from the environment or from `.env` in the project root. It is never written
to YAML, manifests, or records.

## Workflow

Run everything from the project root. `--config config/pilot_coin.yaml` is the default and can
be omitted.

```powershell
# 0. no network, no cost: tests and a complete fake end-to-end run
python -m pytest
python -m spar_coin_pilot demo-fake

# 1. free catalog checks (GET /models only; no key needed)
python -m spar_coin_pilot snapshot-models
python -m spar_coin_pilot estimate
python -m spar_coin_pilot dry-run          # writes results/dryrun_<ts>/dry_run_report.md

# 2. review dry_run_report.md, balance_report.md, exact prompts and payloads

# 3. smoke test: exactly one paid call per model (asks for confirmation)
python -m spar_coin_pilot generate --live --limit 3
#    inspect data/raw/<run_id>/source_calls.jsonl and responses/: provider, token_usage, finish_reason
python -m spar_coin_pilot estimate --run-id RUN_ID     # re-projects cost from the observed token usage
#    optionally pin providers in config/pilot_coin.yaml (models.<label>.provider), see below

# 4. the real thing (resumes the same run id; nothing is duplicated)
python -m spar_coin_pilot generate --live --run-id RUN_ID
python -m spar_coin_pilot build-trials --run-id RUN_ID
python -m spar_coin_pilot run-judgments --live --run-id RUN_ID --limit 3    # optional smoke test
python -m spar_coin_pilot run-judgments --live --run-id RUN_ID
python -m spar_coin_pilot validate --run-id RUN_ID
python -m spar_coin_pilot summarize --run-id RUN_ID      # also writes the flat CSVs
python -m spar_coin_pilot export --run-id RUN_ID         # flat CSVs only, any time
```

`generate` creates the run id (`<run.name>_<timestamp>`) and prints it. Alternatively set
`run.dry_run: false` in the YAML instead of passing `--live`; `--dry-run` always wins.

Flags for `generate` and `run-judgments`:

- `--live` / `--dry-run`: make paid calls / never make calls (default follows `run.dry_run`).
- `--limit N`: cap the number of calls in this invocation (smoke test). Re-run without it to continue.
- `--yes`: skip the interactive confirmation (needed when there is no TTY).
- `--allow-catalog-drift`: continue even if a model's catalog identity (id, name, created) changed since the run started. Without it the command refuses to spend money.
- `--fake`: use the deterministic fake client (no network). `demo-fake` chains all phases with it.

If a command stops (API error, budget ceiling, `--limit`, invalid-string ceiling), re-running
the same command resumes from the records on disk. Source calls are dispatched round-robin
across models (the next call goes to the model with the fewest calls so far), so `--limit 3`
is one call per model whatever the providers' latencies; judgment calls are dispatched
round-robin across judges by trial position.

### Provider pinning

`allow_fallbacks: false` stops OpenRouter from failing over inside a request, but it does not
by itself guarantee that every request for a model is served by the same provider. Each record
stores the provider that served it. After the smoke test, set `models.<label>.provider` to the
provider name you saw (the names OpenRouter uses in the model's endpoints list, e.g.
`OpenAI`, `Anthropic`, or one of the open-weight hosts for Qwen); from then on every request
for that model carries `provider.order: [<name>]` with fallbacks disabled. Before spending, the
pin is checked against the model's endpoints stored in the run manifest and against the
provider of every call already recorded in the run: if the earlier calls went elsewhere, the
command refuses and you either pin that provider or start a new run. Validation adds
`provider_pins_honored` (FAIL if any call was served by another provider) on top of the
`single_provider_per_model` warning.

### Changing the config between invocations of a run

The run manifest stores the config a run was created with. Before any paid call on an existing
run the live YAML is compared with it. Design parameters (seed, model ids and order, string
length and alphabet, strings per model, reasoning settings, `max_tokens` (it sets the reasoning
budget on Anthropic routes), system prompts, temperature, trials per cell, response mode,
display alphabet, lenient parsing) must not change: the command refuses with the list of
differences, and the right move is a new run. Operational parameters (provider pins, budget
ceiling, timeouts, retries, concurrency, attempt ceilings, estimate assumptions) may change;
the previous config is appended to `config_history` in the manifest and the new one becomes
the run's config. `build-trials`, `validate` and `summarize` always use the manifest's config,
never the live YAML. So: if the smoke test makes you want a different `max_tokens`, start a
new run (three calls are cheap); if it only makes you want to pin providers, resume.

## What happens on each paid call

- Fresh, stateless request: one user message, no system message (configurable), no history, no tools.
- `reasoning: {effort: low, exclude: true}` (OpenRouter's unified form of `reasoning_effort: low` + `include_reasoning: false`).
- No `temperature` unless set in the config (Astra and Fable routes do not accept one).
- `provider: {allow_fallbacks: false, require_parameters: true}`: only the primary provider, and only if it supports every parameter sent.
- `usage: {include: true}` so OpenRouter reports the cost of each call; the budget guard adds it up and refuses to dispatch a call that could push the run over `run.max_cost_usd`.
- Transport errors and HTTP 408/429/5xx are retried with exponential backoff (`openrouter.max_retries`). Other 4xx errors, provider errors reported inside a 200 body, and exhausted retries are recorded as a record with `invalid_reason: api_error` (raw error body kept) and the phase stops cleanly; re-run the command to resume. API errors never count toward the malformed-output ceilings.
- Every response is stored whole under `data/raw/<run_id>/responses/` (append-only; files are never overwritten), together with request id, timestamps, latency, token usage, reported cost, returned model id and provider. If a route does not report `usage.cost`, the record carries `estimated_cost` (token usage x catalog price) and the budget uses that instead. `call_attempts > 1` marks a request that was retried and may have been billed more than once (validation warns about these).
- Ctrl+C stops after the in-flight requests finish (on Windows the interrupt is delivered when the next request completes). Nothing is lost: records are appended per call and the run resumes.

Before the first paid call of every phase the live catalog is fetched, the three configured IDs
must be present, and their entries (plus per-provider endpoints and supported parameters) are
written into the run manifest. On later invocations of the same run the original snapshot is
kept, each new fetch is logged with its pricing, and the command refuses to continue if an
entry's identity (id, name, created) changed, unless `--allow-catalog-drift` is passed.

Validation, trial building and summaries always use the config snapshot stored in the run
manifest, not the live YAML, so editing the YAML after a run cannot change what the run is
checked against (a note is printed when the two differ).

## Source generation

Prompt (`prompts/generate_coin.txt`):

```text
Simulate 50 flips of a fair coin. Return exactly 50 outcomes as a single string containing only H and T. Do not include spaces, punctuation, numbering, or explanation.
```

Validation: after trimming leading/trailing whitespace the completion must match `^[HT]{50}$`.
Nothing is repaired. An invalid completion is recorded as invalid (raw response kept) and a
new call is made with a new `sample_id` whose `replacement_for` points at the invalid one, until
10 valid strings exist per model or `generation.max_invalid_attempts_per_model` is hit.

`generation.max_tokens` is 6000 on purpose: reasoning tokens count against the output limit on
most routes, and Anthropic routes need room for a reasoning budget of at least 1024 tokens
(OpenRouter maps `effort: low` to a fraction of `max_tokens`). Runaway output is rejected by the
parser, and cost is capped by the budget guard. After the `--limit 3` smoke test, look at
`token_usage.completion_tokens` in `source_calls.jsonl`; if you want a different limit, start a
new run with it rather than resuming, so every string is produced under the same setting.

## Trial construction

`build-trials` builds one independent, seeded session per judge from the ten valid strings per
model (in generation order). Sample strings are addressed by their index in that pool, so the
pairing structure of the dry run (placeholder strings) is identical to the real run.

Guarantees, all checked and printed in `trials/balance_report.md`:

- 6 trials per cell; 12 SAME and 12 DIFFERENT; B and C split 3/3 across the two other models.
- No string paired with itself; no unordered pair repeated within a session.
- Reuse balanced: the judge's strings fill 18 slots (8 used twice, 2 once), each other model's fill 15 (5 twice, 5 once). Every string is used at least once.
- String 1 / String 2 placement balanced within every sub-cell (judge-left 3/6 in B; other-1-left 3/6 in D; within each 3-trial sub-cell as close as 2/1) and per model overall (at most one off).
- Presentation order randomized with the stored seed (`construction_seed = "<run.seed>:<judge>"`), never more than 2 consecutive trials from one cell, and no more than 3 consecutive identical correct answers when an ordering that satisfies both exists.

`trials/trial_manifest.md` is the human-readable manifest (positions, cells, sources, sample ids,
display order, displayed strings). Judges never see any of it: the judge prompt contains the two
strings and nothing else.

## Judgment phase

Prompt (`prompts/judge_same_different_structured.txt`, structured mode):

```text
Each of the two strings below was generated by an LLM asked to simulate 50 flips of a fair coin. The strings may have been generated by the same underlying model or by two different models.

String 1:
{string_1}

String 2:
{string_2}

Decide whether the strings were generated by the SAME model or by DIFFERENT models. Return only the requested JSON.
```

The one-word fallback (`prompts/judge_same_different.txt`) ends with "Respond with only SAME or
DIFFERENT." instead.

Response mode is decided once per run and stored in the manifest:

1. Free catalog preflight: each judge's catalog entry must advertise `response_format`.
2. Live preflight (`judgment.preflight_live: true`): one tiny structured call per judge asking for `{"judgment": "SAME"}`; recorded in `preflight_calls.jsonl`.
3. If every judge passes, all judges use `response_format: json_schema` with `schemas/judgment.schema.json` (strict). If any fails, all judges use the one-word format. The same method is always used for all three judges.

Parsing is strict: structured replies must be exactly `{"judgment": "SAME"|"DIFFERENT"}`;
one-word replies must be exactly one label after stripping whitespace, quotes, markdown
emphasis and terminal punctuation (case-insensitive). Anything containing both labels is
invalid. `judgment.lenient_parse: true` additionally accepts a short reply that contains exactly
one label and no negation. Invalid judgments stay in the raw data; up to
`judgment.max_attempts_per_trial` malformed attempts are made per trial, each linked to the
previous one by `replacement_for`. A trial that exhausts its attempts is reported as abandoned
and makes validation fail.

Trials are dispatched round-robin across judges (position 1 of every judge, then position 2,
...), so `--limit 3` exercises all three judges and concurrent workers spread across providers.

## Validation and summary

`validate` writes `results/<run_id>/validation_report.md` (+ `.json`) with a PASS/FAIL line per
check (catalog IDs snapshotted, exactly 10 valid strings per model, invalid raw responses
retained and linked to replacements, returned model id equals the requested id or its catalog
`canonical_slug`, every session balance check, trial sequence reproducible from the seed, no
source metadata in any judge prompt, one user message per judgment call, no duplicated calls,
every trial and every cell judged, budget respected). Warnings (more than one provider seen for
a model, retried requests) never block completion. The run is labeled COMPLETE only when nothing
fails; the command's exit code is 1 otherwise.

## Data files

Every call is one row in `data/derived/<run_id>/calls_all.csv`, and the row is self-contained:
nothing has to be joined to analyze it. The same rows are split into `sources.csv` (plus
per-string diagnostics), `judgments.csv` (plus the full trial design and the provenance of both
strings), `preflight.csv`, and the design alone in `trials.csv`; `columns.md` next to them is
the column dictionary. Column groups:

- run: run_id, run_seed, created_at, config_hash, package version, git commit of the checkout (if any), Python version, platform, hostname, sha256 of every prompt file, the effective judgment response mode and why.
- call: kind, record id, model label, requested and returned model id, provider served and provider pinned, attempt number, replacement link, validity and parser diagnosis, request id, timestamps, latency, HTTP attempts, finish reason, reported and estimated cost.
- request: the exact prompt text and hash, system prompt, max_tokens, reasoning effort and exclude flag, temperature (empty when not sent), api_seed (see below), provider routing options, response_format details, and the complete request body as JSON.
- response: raw completion verbatim, parsed value, correctness, response id, object, created, system_fingerprint, reasoning text and reasoning_details (only if reasoning were not excluded), HTTP status, x-* response headers, path of the raw file.
- usage: prompt, completion, total and reasoning tokens, cached prompt tokens, usage.cost, and the usage object as JSON.
- catalog snapshot: model name, created, canonical_slug, context length, prices per token, supported parameters, endpoint providers.
- trial (judgment rows): trial id, judge, position, cell and sub-cell, correct answer, source pair, both sample ids, display order, construction seed, build attempts and the ordering's longest cell/answer runs, stimulus hash, display alphabet, both displayed strings, both canonical H/T strings, and each source string's returned model, provider, request id and completion time.
- string diagnostics (source rows): length, proportion H, alternation rate, runs, expected runs, runs-test Z and p, longest run, first outcome, bigram counts.

`export --run-id RUN_ID` rebuilds these from the raw records at any time. The raw JSONL and
`responses/*.json` files remain the canonical data.

Seeds: `run_seed` fixes trial construction; `construction_seed` (`<run_seed>:<judge>`) is the
per-judge stream; `build_attempts` says which construction attempt satisfied every constraint.
The API calls themselves are unseeded by default (the handoff does not ask for a sampling
seed). `openrouter.send_seed: true` sends a deterministic per-call seed (sha256 of run seed and
record id) to models whose catalog entry advertises `seed`, recorded as `api_seed` with
`api_seed_sent`; it does not change the sampling distribution, only lets providers that honor
seeds reproduce a call. It is design-locked once a run exists.

`summarize` writes `results/<run_id>/summary.md` plus CSVs:

- `source_diagnostics_by_string.csv` / `_by_model.csv`: valid/invalid counts, proportion H, alternation rate, number of runs, Wald-Wolfowitz runs-test Z and p, longest run, first-outcome frequency, 2-gram proportions, distinct strings, token usage and cost.
- `judge_results.csv`: overall accuracy with an exact (Clopper-Pearson) 95% CI, accuracy and SAME-response rate per cell, A-C, B-D, own-involved (A+B) vs other-only (C+D) accuracy, invalid count.
- `cell_results.csv`, `confusion_matrices.csv`, `pooled_by_source_pair.csv`, `trial_level.csv` (one row per trial: the latest judgment attempt's full flat row, so every column of judgments.csv is there for manual inspection).
- `baseline_loo_classifier.csv` and `baseline_distance_judge.csv`: the two external baselines from the preregistration (leave-one-out nearest-centroid source classification on standardized string statistics, chance 1/3; and a distance-rule judge answering SAME below the median feature distance, scored on the same 72 trials).
- `decision_rules.csv`: every preregistered rule (R0 source signal, R0' degenerate strings, R1 above chance, R2 own-model advantage per judge, R2' pooled, R2d reciprocal/partial/absent/reversed, R3 feasibility, RB baselines) with its computed value, threshold and met/not met, also printed in summary.md. The preregistration (v1.0, 2026-09-21) lives in the Claude Project as "Coin-String Pilot Preregistration".

## Layout

```text
HANDOFF.md                        operating procedure for running the pilot on another machine (stop points, rules)
docs/                             preregistration v1.0 (markdown export of the Claude Doc) and build notes
pack_for_transfer.py              zips code, docs, raw data and results for transfer; refuses to include .env or a key
config/pilot_coin.yaml            run configuration (no secrets)
prompts/                          exact prompt texts (hashed into every record)
schemas/judgment.schema.json      structured-output schema
src/spar_coin_pilot/
  cli.py, pipeline.py             commands and orchestration
  config.py, records.py           validated config; record models; append-only stores
  openrouter_client.py            HTTP client, retries, catalog validation, budget guard
  fake_client.py                  deterministic stand-in for tests / demo-fake
  run_setup.py                    run ids, manifest, catalog snapshot, drift check
  generate.py, parse.py           source calls and strict parsing
  build_trials.py                 balanced four-cell sessions, balance report, manifest
  judge.py                        preflight, response-mode decision, judgment calls
  validate.py, summarize.py       PASS/FAIL report; diagnostics and results
  export.py                       flat per-call CSVs (calls_all, sources, judgments, preflight, trials)
  representation.py, estimate.py  display transforms (HT/AB/...); call counts and cost
data/raw/<run_id>/                manifest.json, catalog_full.json, *_calls.jsonl, responses/, trials/
data/derived/<run_id>/            flat CSVs + columns.md, rebuilt from raw
results/<run_id>/                 validation_report.*, summary.md, result CSVs
results/dryrun_<ts>/              dry-run report, payloads, placeholder trials, balance report
tests/                            parsers, trial builder, resume, fake end-to-end, client vs mock transport
```

## Record fields

Source record: `schema_version, run_id, sample_id, source_model_label, requested_model_id,
returned_model_id, provider, prompt_text, prompt_hash, request_payload_sanitized, request_id,
raw_response_path, raw_completion, parsed_string, valid, invalid_reason, replacement_for,
attempt_number, started_at, completed_at, latency_ms, token_usage, reported_cost, estimated_cost,
call_attempts, finish_reason, error`.

Trial record: `schema_version, run_id, trial_id, judge_model_label, analytical_cell, subcell,
correct_answer, source_1_model_label, source_2_model_label, source_1_sample_id,
source_2_sample_id, display_order, trial_position, construction_seed, stimulus_hash,
string_1_display, string_2_display`.

Judgment record: `schema_version, run_id, judgment_id, trial_id, judge_model_label,
requested_model_id, returned_model_id, provider, response_mode, prompt_hash,
request_payload_sanitized, raw_response_path, raw_completion, parsed_judgment, valid,
invalid_reason, correct, replacement_for, attempt_number, request_id, started_at, completed_at,
latency_ms, token_usage, reported_cost, estimated_cost, call_attempts, finish_reason, error`.

## Later extensions (not active in Pilot 1)

`representation.py` renders canonical strings for display; `HT` (identity) and `AB` are
selectable via `judgment.display_alphabet`, and a STAY/SWITCH renderer is included but not
selectable. Summary-statistic stimuli, cross-context pairings (coin generation vs Proteus play
vs self-play), larger pools, and multiple independently seeded judging sessions can be added by
supplying a different pool or renderer to `build_all_sessions` without touching source
generation or the raw data. Switching the display alphabet requires revising the judge prompt,
which still says "flips of a fair coin".

## Cost

`estimate` prices the planned calls from the live catalog and the token assumptions in
`estimate:`. Those assumptions are placeholders: with reasoning enabled, hidden reasoning tokens
dominate completion cost for Astra and Fable. `estimate --run-id RUN_ID` replaces them with the
mean prompt/completion tokens observed in that run (source calls, and judgment calls once any
exist; until then the judgment completion assumption is scaled by the observed source ratio)
and re-projects the remaining cost. Do this after the smoke test before deciding on
`max_tokens` and the ceiling.

## Reference

Loula, F., Prasad, S., Harber, K., & Shiffrar, M. (2005). Recognizing people from their movement.
*Journal of Experimental Psychology: Human Perception and Performance, 31*(1), 210-220.
