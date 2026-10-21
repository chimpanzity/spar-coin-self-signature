# 05 · Pilot 4: Astra provenance replication with a no-provenance control (2026-09-29)

| | |
|---|---|
| Track | 1 — static self-prediction and self-modelling |
| Run IDs | `spar-astra-followup-20260929T190938Z` (this folder is the run root) |
| Models | judge: Astra (`openai/gpt-6-astra`); sources: Astra, Fable (`anthropic/claude-fable-5.1`), attempted Qwen3.8 27B |
| Size and cost | 120 judgments on 40 fresh trajectories; cost not reliably recorded (the report shows $0.0000) |
| Previous / next | [← 04 Pilot 3: provenance](../04_2026-09-29_pilot3_provenance/) · [06 Stimulus corpus →](../06_2026-09-30_stimulus_corpus/) |

## What was done
Astra-only replication of the Pilot 3 pattern ("told online" raised Astra's SELF rate on its own
strings only). Fresh 50-flip trajectories were generated, and each was judged three times in fresh
calls: told batch, told online, and with no provenance sentence. Primary contrast: the "selective
online SELF effect" = (SELF-source online shift) − (OTHER-source online shift); positive would replicate Pilot 3.

## Questions
- Does "told online" selectively raise Astra's SELF attributions for its own strings?
- What is Astra's SELF rate without any provenance cue?

## Results
From [`results/ASTRA_PROVENANCE_REPLICATION_REPORT.md`](results/ASTRA_PROVENANCE_REPLICATION_REPORT.md):

| P(SELF) | told batch | told online | no provenance |
|---|---:|---:|---:|
| Astra-source strings | 0.000 | 0.150 | 0.000 |
| other-source strings | 0.100 | 0.450 | 0.000 |

- Selective online SELF effect = **−0.200** (SELF shift +0.150, OTHER shift +0.350). The Pilot 3 pattern did not replicate.
- "Told online" raised SELF answers for other models' strings more than for Astra's own
  (McNemar exact p = 0.0391 for OTHER, 0.2500 for SELF).
- With no provenance sentence Astra never answered SELF (0 of 40 trajectories).
- So "told online" works as a general cue to answer SELF, not as a self-specific one.

## Open questions
- Why does a stated generation procedure move self-attribution at all? This became the
  procedure-belief question tested directly in [10 Story swap](../10_2026-10-01_story_swap/).

## What it led to
The 50-flip pilots showed that signatures exist but gave no self advantage, with small, uneven
stimulus sets. The next step was a larger, cleaner stimulus bank:
[06 Stimulus corpus](../06_2026-09-30_stimulus_corpus/).

**Notes.**
- The report's design says the OTHER sources were 5 Fable + 5 Qwen per architecture. Qwen batch
  generation mostly failed ("too many invalids (200); aborting" in [`logs/`](logs/)), and the source
  validation in the log shows 0 online Qwen strings. All 60 OTHER judgments are on Fable strings
  (the report's OTHER-source table shows Fable n = 20 per condition and Qwen n = 0).
- Cost accounting is broken in this run ($0.0000 reported); the true cost is unknown.
- Some older documents number the pilots differently (see [03](../03_2026-09-29_pilot2_self_vs_other/)); this folder is Pilot 4.

## Files
- Report: [`results/ASTRA_PROVENANCE_REPLICATION_REPORT.md`](results/ASTRA_PROVENANCE_REPLICATION_REPORT.md); CSV tables in [`results/`](results/)
  (`primary_interaction.csv`, `mcnemar.csv`, `condition_summary.csv`, ...).
- Raw data: [`source/`](source/), [`smoke/`](smoke/), [`trials/`](trials/), [`judgment/`](judgment/), `manifest.json`, [`logs/`](logs/).
- Code: [`src/spar_dynamic/astra_followup.py`](../../src/spar_dynamic/astra_followup.py),
  [`src/spar_dynamic/orchestrator_astra_followup.py`](../../src/spar_dynamic/orchestrator_astra_followup.py).
- Tests: [`tests/test_spar_astra_followup.py`](../../tests/test_spar_astra_followup.py).

## Re-running
From the repo root (needs `OPENROUTER_API_KEY`):

```
PYTHONPATH=src python -m spar_dynamic.orchestrator_astra_followup --live --yes
```
