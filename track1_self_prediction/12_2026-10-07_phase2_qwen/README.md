# 12 · Phase 2 coin-flip pilot (v7.1), run 1 with Qwen3-8B (2026-10-07 to 10-08)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `p2-20261007`; connectivity and model diagnostics in `phase2/_preflight/` |
| Models | Astra (`openai/gpt-6-astra`, OpenAI), Fable (`anthropic/claude-fable-5.1`, Anthropic), Qwen3-8B (`qwen/qwen3-8b`, Alibaba); historical check GPT-3.5-turbo-0613 (Azure) |
| Size and cost | 2,514 calls (planned envelope 3,186), $8.39 |
| Previous / next | [← 11 Phenotype prediction](../11_2026-10-01_phenotype_prediction/) · [13 Phase 2, run 2 (MiMo) →](../13_2026-10-08_phase2_mimo/) |

## What was done
A redesigned, pre-registered coin-flip study (protocol `SPAR_Phase2_v7.1`) with recorded approvals,
a freeze before test data, and logged amendments. Three models generate 20-flip strings under a
"plain" and a "fair" prompt ("Flip 20 fair coins."). Judges then (1) forecast continuations of
prefixes, Brier-scored, with the source disclosed or withheld; the key contrast **H4** = gain from
disclosure on own-model sequences minus gain on other-model sequences, with a ±0.02 Brier margin;
(2) give a probability that two anonymous strings share a source (recognition contrast R);
(3) attribute a string to a named model. External observers (prefix lookup, pair classifier, LASSO)
score the same items.

## Questions
- Does knowing that a sequence is its own help a model forecast it more than knowing another model's source helps (H4 > 0)?
- Do judges show an own-model advantage in anonymous SAME/DIFFERENT or named attribution?

## Results
From [`PHASE2_PILOT_RESULTS_2026-10-08.md`](PHASE2_PILOT_RESULTS_2026-10-08.md) and [`CORE_REPORT.md`](phase2/p2-20261007/CORE_REPORT.md):
- **H4 = −0.0026 [−0.0040, −0.0013]**: negative and well inside the ±0.02 margin. Disclosure helped
  other-source forecasts slightly (+0.0024) and own forecasts not at all (−0.0002).
- **The judges mostly did not forecast.** Astra returned 0.5 at every position for 100% of Astra- and
  Fable-source prefixes; Fable did so on 52–62% of prefixes and Qwen on 80–94%. The prefix observer
  scored Brier 0.064 on Fable/plain when told the source, against 0.250 for the judges.
- Qwen produced a usable "fair" sequence in 7 of 84 calls (6/60 development, 1/24 test), so the
  two-prompt anonymous and named panels were not estimable.
- Plain prompt only (secondary): R = +0.076 [+0.011, +0.130], inconsistent across judge pairs and
  driven by Qwen scoring below chance as the uninvolved judge (AUC 0.11). Named attribution R = −0.04 [−0.17, +0.09].
- No evidence of a self-specific forecasting advantage.

## Open questions
- Is the 0.5 answer a response policy (task framing) rather than inability? Fixtures showed Astra
  and Fable can use stated rules (12/12 correct).
- Which third model can follow the "fair" prompt? (run 2)

## What it led to
The same protocol was rerun with MiMo as the third model: [13 Phase 2, run 2](../13_2026-10-08_phase2_mimo/).

## Files
- Summary: [`PHASE2_PILOT_RESULTS_2026-10-08.md`](PHASE2_PILOT_RESULTS_2026-10-08.md).
- Run folder [`phase2/p2-20261007/`](phase2/p2-20261007/): start with `CORE_REPORT.md`, then `RETAINED_ARMS_REPORT.md`,
  `STAGE1_REPORT.md`, `STAGE2_REPORT.md`, `DECISION_MEMO.md`; records `amendments.jsonl`, `approvals.jsonl`,
  `freeze.json`, `calls.jsonl` (all calls), `sequences.csv`, `scores.csv`, `checksums.sha256`.
- Preflight diagnostics: [`phase2/_preflight/`](phase2/_preflight/) (also holds the MiMo smoke test used for run 2).
- Background: [week handoff 10-05 to 10-11, §2](../../docs/handoffs/HANDOFF_SPAR_WEEK_2026-10-05_to_2026-10-11.md).
- Code: [`src/spar_dynamic/phase2/`](../../src/spar_dynamic/phase2/) (`rescore.py` independently reproduces H4).
- Tests: [`tests/test_phase2.py`](../../tests/test_phase2.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY` with `--live`; without `--live` a fake transport is used
and nothing is sent). Stages, in order, as listed in `src/spar_dynamic/phase2/__main__.py`:

```
PYTHONPATH=src python -m spar_dynamic.phase2 init     --run <run id>
PYTHONPATH=src python -m spar_dynamic.phase2 generate --run <run id> --split development --live
PYTHONPATH=src python -m spar_dynamic.phase2 stage1   --run <run id> --live   # fixtures, report, rehearsal, headroom
PYTHONPATH=src python -m spar_dynamic.phase2 freeze   --run <run id>
PYTHONPATH=src python -m spar_dynamic.phase2 stage2   --run <run id> --live   # test generation + core tasks
PYTHONPATH=src python -m spar_dynamic.phase2 retained --run <run id> --live   # named + historical
PYTHONPATH=src python -m spar_dynamic.phase2 analyze  --run <run id>
PYTHONPATH=src python -m spar_dynamic.phase2 verify   --run <run id> --fake   # full fake end-to-end
```

The third model is chosen by the environment variable `PHASE2_THIRD_MODEL` (default `qwen`).
