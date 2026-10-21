# 04 · Pilot 3: stated provenance and self-attribution (2026-09-29)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `spar-provenance-20260929T181702Z` (this folder is the run root) |
| Models | Astra (`openai/gpt-6-astra`), Fable (`anthropic/claude-fable-5.1`), Qwen3.8 27B (`qwen/qwen3.8-27b`) as judges |
| Size and cost | 240 trials; cost not reliably recorded (the report shows $0.0194 from "2 calls") |
| Previous / next | [← 03 Pilot 2: SELF/OTHER](../03_2026-09-29_pilot2_self_vs_other/) · [05 Pilot 4: Astra follow-up →](../05_2026-09-29_pilot4_astra_followup/) |

## What was done
The Pilot 2 SELF/OTHER task, with one sentence added that states how the string was produced:
"told batch" (one call simulated all 50 flips) or "told online" (50 calls, one flip each, with
history). Design per judge: 2 (source SELF/OTHER) × 2 (actual architecture) × 2 (stated
architecture) × 10 trials = 80; each trajectory shown twice in fresh calls, once per stated
architecture. Strings are Pilot 1's.

## Questions
- Does accurate provenance help self-attribution more than other-attribution (a positive
  "self-specific provenance effect")?
- Does the stated architecture shift SELF answers regardless of the true source?

## Results
From [`results/PROVENANCE_SELF_ATTRIBUTION_REPORT.md`](results/PROVENANCE_SELF_ATTRIBUTION_REPORT.md):

| judge | Δ congruent − incongruent, SELF | same, OTHER | self-specific effect |
|---|---:|---:|---:|
| Astra | −0.150 | +0.000 | −0.150 |
| Fable | −0.250 | +0.300 | −0.550 |
| Qwen | +0.000 | +0.150 | −0.150 |

- The self-specific provenance effect was negative for all three judges.
- "Told online" raised Astra's SELF rate on its own strings (actual batch: 0.000 → 0.600; actual
  online: 0.300 → 0.600) while its SELF rate on other models' strings stayed at 0.100 in every cell.
  This was the pattern taken forward to Pilot 4.
- Fable's SELF rate also rose when told online, but for other models' batch strings as well (0.400 → 0.900 on OTHER batch strings).
- 10 trials per cell; granularity 0.10. The report's automatic outcome label is "Outcome C" (generic congruence).

## Open questions
- Was Astra's selective "told online" shift real, or noise at n = 10 per cell?
- What is each judge's SELF rate with no provenance sentence at all?

## What it led to
[05 Pilot 4](../05_2026-09-29_pilot4_astra_followup/) tested the Astra pattern on fresh strings with
a no-provenance control.

**Notes.** Cost accounting is broken in this run: the report lists 240 valid trials but only
"2 calls, $0.0194", so the true cost is unknown. Some older documents number the pilots
differently (see the correction in [03](../03_2026-09-29_pilot2_self_vs_other/)); this folder is Pilot 3.

## Files
- Report: [`results/PROVENANCE_SELF_ATTRIBUTION_REPORT.md`](results/PROVENANCE_SELF_ATTRIBUTION_REPORT.md); CSV tables in [`results/`](results/).
- Raw data: [`trials/`](trials/), [`judgment/`](judgment/), `manifest.json`, `catalog_snapshot.json`, [`logs/`](logs/).
- Code: [`src/spar_dynamic/provenance.py`](../../src/spar_dynamic/provenance.py),
  [`src/spar_dynamic/orchestrator_provenance.py`](../../src/spar_dynamic/orchestrator_provenance.py).
- Tests: [`tests/test_spar_provenance.py`](../../tests/test_spar_provenance.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.orchestrator_provenance --live --yes \
    --source-run-root track1_self_prediction/02_2026-09-29_pilot1_source_signature
```
