# 01 · Preregistered SAME/DIFFERENT harness, "Pilot 0" (2026-09-21)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | none live; one no-cost dry run, `results/dryrun_20260921_045216` |
| Models | planned: Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen3.8 27B (`qwen/qwen3.8-27b`) |
| Size and cost | planned 30 source calls + 72 judgment calls + 3 preflight calls; no paid calls made, $0 |
| Previous / next | (first experiment) · [02 Pilot 1: source signatures →](../02_2026-09-29_pilot1_source_signature/) |

## What was done
A self-contained harness (`spar-coin-pilot` 0.1.0) for a preregistered LLM analogue of the
Loula et al. (2005) actor-discrimination task. Each model would write ten 50-flip "fair coin"
strings; the same models would then judge, one stateless call per trial, whether two anonymous
strings came from the SAME model or DIFFERENT models. Four cells per judge (own+own, own+other,
other+same other, other1+other2) separate an own-model advantage from general skill.
The preregistration was fixed before any paid call. The harness was tested and dry-run against
a fake catalog, but never run live: the pilots that were run (folders 02–05) used a
re-implementation, the `spar_dynamic` package.

## Questions
- Do coin-flip strings carry a model-specific signature that judges can see?
- Is a judge selectively better at SAME/DIFFERENT discrimination when its own model's strings are involved?

## Results
- No data: no live calls were made with this harness.
- The dry run ([`dry_run_report.md`](results/dryrun_20260921_045216/dry_run_report.md)) used a fake
  catalog; it estimated $0.4464 for the planned calls, with a $25.0 cost ceiling.

## Open questions
- The preregistered contrasts (A vs C on SAME trials, B vs D on DIFFERENT trials) were never tested
  in this exact form; Pilot 1 used a different implementation and added an "online" generation arm.

## What it led to
The design was re-implemented as `spar_dynamic` and run as
[02 Pilot 1](../02_2026-09-29_pilot1_source_signature/), which compared single-call ("batch") and
one-flip-per-call ("online") generation.

## Files
- Preregistration and build notes: [`docs/preregistration/`](../../docs/preregistration/)
  (`preregistration_v1.0_2026-09-21.md`, `build_notes_2026-09-21_rev4.md`).
- Laptop setup handoff: [`docs/handoffs/HANDOFF_2026-09-29_pilot1_laptop_setup.md`](../../docs/handoffs/HANDOFF_2026-09-29_pilot1_laptop_setup.md).
- Harness code (its own package, not under the repo's `src/`): [`src/spar_coin_pilot/`](src/spar_coin_pilot/),
  config [`config/pilot_coin.yaml`](config/pilot_coin.yaml), frozen prompts [`prompts/`](prompts/),
  output schema [`schemas/`](schemas/), its own tests [`tests/`](tests/), `pyproject.toml`, `pack_for_transfer.py`.
- Dry run: [`results/dryrun_20260921_045216/`](results/dryrun_20260921_045216/) (report, balance report, payloads, placeholder trials).
- [`HARNESS_MANUAL.md`](HARNESS_MANUAL.md): the harness's original README, unchanged (setup, workflow and paid-call rules).
  - Its commands are run from inside this folder, because it is a separate installable package.
  - Paths such as `C:\Users\chris\...` refer to the original development machine.
