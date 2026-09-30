# SPAR — Behavioral Self-Signatures in LLMs

> **New canonical dataset (2026-09-30).** All future work in this repository
> builds on the **SPAR Stimulus Corpus** at [`corpus/`](corpus/):
> 180 valid 100-flip trajectories, 3 models × 3 production architectures,
> with a frozen 10/10 development/evaluation split within every cell.
>
> The four earlier pilots that led to this corpus have been moved to
> [`pilots/`](pilots/). They are preserved as historical provenance and
> should not be used as the reference dataset going forward.

## Question and motivation

When a fair coin is flipped, the resulting binary sequence has two defining
statistical properties: heads and tails each have an expected marginal
frequency of 50%, and successive flips are independent.

Prior work has shown that LLMs asked to simulate sequences of coin flips
systematically fail to reproduce one or both of these properties. Even when
the overall proportion of heads and tails is close to 50/50, models often
produce excess alternation, avoid long runs, or exhibit other sequential
dependencies (e.g., Van Koevering & Kleinberg; Bigelow et al.; West & Potts).
Where true randomness contains no stable sequential signature, LLMs
introduce structure.

That raises the possibility that this structure carries a behavioral
phenotype characteristic of the model that produced it. The first question
is therefore whether different models leave identifiable signatures in
otherwise minimal binary behavior. The more interesting question for the
SPAR project is whether models can recognize their own phenotype, and
whether they are better at doing so than other models or statistical
classifiers. A selective own-model advantage would be difficult to explain
as ordinary pattern classification alone and would be consistent with some
form of privileged access to information about the processes that generated
the behavior, although it would not by itself establish introspection or
self-awareness.

## Behavioral-psychology inspiration

The experimental logic is adapted from Loula et al.'s work on human
self-recognition from point-light motion. Participants were filmed
performing actions with reflective markers on their joints, removing most
ordinary visual identity information while retaining the dynamics of
movement. In subsequent tests they either identified an individual actor as
self, friend, or stranger, or judged whether two different displays had been
produced by the same or different person. Performance was especially good
for one's own movements, suggesting that behavioral dynamics can contain
recognizable identity information even after surface features have been
stripped away.

The LLM analogue here replaces the point-light movement trajectory with an
anonymous sequence of H and T flips. The aim is to ask whether model
identity — and potentially self-identity — survives in this deliberately
impoverished behavioral trace.

## The canonical stimulus corpus (`corpus/`)

The corpus is the reference stimulus bank for every future analysis in this
repository. It contains:

- **180 trajectories** (3 models × 3 methods × 20 replicates × 100 flips)
- **3 models**: `astra` (`openai/gpt-6-astra`), `fable`
  (`anthropic/claude-fable-5.1`), `mimo` (`xiaomi/mimo-v2.6-pro`)
- **3 production methods**:
  - `batch` — a single API call produces all 100 flips
  - `history_conditioned` — 100 sequential calls, each receives the full prior history
  - `independent_calls` — 100 sequential calls, each sees an identical fixed prompt (no history)
- **Frozen split**: stratified random 10 development / 10 evaluation within
  every (model, method) cell, seeded once at compilation time
  (`CORPUS_SPLIT_SEED = 20260930`). Recognition experiments should develop
  matching procedures on the development half and apply the frozen procedure
  to the evaluation half.

### Headline finding

The three architectures produce sharply different behavioral phenotypes for
the same nominal task (mean values at 100 flips):

| model | method | p(H) | switch rate | longest run |
|---|---|---:|---:|---:|
| astra | batch | .495 | .620 | 3.6 |
| astra | history_conditioned | .460 | .632 | 4.6 |
| astra | independent_calls | .389 | .473 | 7.7 |
| fable | batch | .507 | .643 | 3.0 |
| fable | history_conditioned | .744 | .476 | 24.3 |
| fable | **independent_calls** | **.987** | **.026** | **78.0** |
| mimo | batch | .487 | .624 | 3.5 |
| mimo | history_conditioned | .633 | .497 | 7.3 |
| mimo | independent_calls | .860 | .233 | 22.2 |

Batch produces near-fair coins for all three models. Independent fresh
calls collapse into strongly biased same-flip behavior — most dramatically
for fable, which becomes an H machine (98.7% heads, mean longest run 78 out
of 100). History-conditioned generation sits in between and produces the
most reliably model-identifying trajectories: a simple nearest-centroid
classifier reaches 90.0% source-model accuracy at 100 flips
(chance = 33.3%), up from 68.3% at 20 flips.

See [`corpus/THREE_ARCHITECTURE_SOURCE_REPORT.md`](corpus/THREE_ARCHITECTURE_SOURCE_REPORT.md)
for the full analysis.

### Corpus layout

```
corpus/
  trajectories.csv         # 180 rows, canonical stimulus bank
  flips.csv                # 18,000 rows, long-format trial-level view
  metrics.csv              # 540 rows, phenotype at prefix 20/50/100
  manifest.json            # split seeds, cell counts, verbatim prompts
  README.md                # detailed corpus documentation
  data_dictionary.md       # field-by-field definitions
  stimulus_corpus.xlsx     # human-browsable Excel workbook (generated from CSVs)
  THREE_ARCHITECTURE_SOURCE_REPORT.md   # narrative analysis + headline results
```

The raw source run (every API attempt including retries and failures) lives
at [`data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/`](data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/).
The corpus is regenerable from that source via
`python -m spar_dynamic.compile_corpus --run-id spar-stimulus-corpus-20260930T012044Z`.

## Prior pilots (see [`pilots/`](pilots/))

Four pilots (Sept 2026) established the setup that led to the corpus:

1. Batch vs online sequence production; source-model classifier reached 70%
   accuracy on 50-flip batch trajectories and 93.3% on online trajectories.
2. Models running Loula's SAME/DIFFERENT paradigm reached ~92% (Astra) and
   ~83% (Fable) on online trajectories, but showed no selective own-model
   advantage.
3. Explicit SELF/OTHER attribution was poor: Astra classified nearly every
   sequence as OTHER, including its own.
4. A follow-up with a no-provenance control found that a "generated online"
   description increased SELF responses generally rather than selectively
   unlocking Astra's own phenotype.

These are preserved as historical context. New analyses should build on the
corpus, not on the pilot data.

## Repository layout

```
corpus/                             CANONICAL stimulus bank (start here)
pilots/                             prior pilots 1-4, archived (historical only)
data/spar_dynamic/                  raw run data for the canonical corpus
spar_dynamic/                       Python package (all pilots + corpus code)
  config.py                           frozen prompts, models, retry, budgets, split seed
  api.py                              OpenRouter client + cost accountant + parsers
  analyze.py                          feature engineering + all analyses
  stimulus_corpus.py                  three production methods for the corpus
  orchestrator_stimulus_corpus.py     end-to-end corpus generation
  backfill_mimo_history.py            per-cell top-up for low-yield methods
  finalize_report.py                  regenerates validation + analysis reports
  compile_corpus.py                   builds corpus/ CSVs + XLSX from a source run
  source.py + orchestrator.py         (pilot 1 code)
  self_other.py + orchestrator_self_other.py       (pilot 2)
  provenance.py + orchestrator_provenance.py       (pilot 3)
  astra_followup.py + orchestrator_astra_followup.py (pilot 4)
tests/                              unit + integration tests for all of the above
```

## Regenerating the corpus

```bash
pip install -r requirements.txt openpyxl
export OPENROUTER_API_KEY=sk-or-v1-...

# Recompile CSVs, XLSX, README, and data dictionary from the raw source run:
python -m spar_dynamic.compile_corpus \
  --run-id spar-stimulus-corpus-20260930T012044Z

# Rerun the analysis and narrative report:
python -m spar_dynamic.finalize_report \
  --run-id spar-stimulus-corpus-20260930T012044Z
```

To generate a fresh source run from scratch (about $7 of OpenRouter spend at
$60 budget cap):

```bash
python -m spar_dynamic.orchestrator_stimulus_corpus --live --yes
```

## Total cost so far

All five studies combined (four prior pilots + the canonical corpus generation)
came to approximately **$11 USD** in OpenRouter spend.
