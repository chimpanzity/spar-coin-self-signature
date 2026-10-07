# SPAR — Behavioral Self-Signatures in LLMs

## Summary of the work so far (updated 2026-10-07)

> **Evaluating this project (human or LLM)?** Start with
> [`REVIEW_GUIDE.md`](REVIEW_GUIDE.md): reading order with raw-text links,
> a claim-to-evidence map, which runs are canonical, and known caveats.

**Question.** Ask an LLM to simulate fair coin flips. Can it recognize its own
100-flip sequences, and predict their statistics, better than other models can?
This is an LLM version of Loula et al.'s point-light self-recognition paradigm.

**Main result.** No model showed a clean privileged self-recognition ability.
What decides a model's attribution is the story it is told about how the
sequence was generated, not the sequence itself. Models hold clear beliefs
about how LLMs behave under each generation procedure, and they apply those
beliefs the same way to every model, themselves included. Fable's beliefs
happen to match its own behavior; Astra's do not.

| # | study | what it showed |
|---|---|---|
| 1–4 | [Pilots](pilots/) (50 flips) | Source phenotypes exist (classifier 70% batch / 93% online); no selective own-model advantage; SELF/OTHER attribution is poor |
| 5 | [SPAR Stimulus Corpus](corpus/) | 180 frozen trajectories (3 models × 3 procedures × 20 × 100 flips) with a 10/10 dev/holdout split. The procedure changes the phenotype sharply: Fable under independent calls gives 98.7% H |
| FCE1 | Producer vs. observer identification, history-conditioned | Holdout mean self-advantage S = +0.008, essentially zero. A centroid classifier on p(H) alone reaches 96.7% |
| FCE2 | Same design on batch / independent calls | S = −0.008 (batch), +0.100 (indep); the indep result comes almost entirely from Fable |
| — | Task validation (objective A/B questions) | Astra and Fable answer 100% correctly with balanced A/B use, so their A-bias in source attribution is specific to that task, not a broken format |
| — | Story swap (same stimuli, three stories) | Changing only the stated procedure flips Fable's SELF answer on 85% of identical items. **Attribution follows the story, not the trace** |
| — | Phenotype prediction, p(H) and switch rate | Judges forecast the statistics before seeing any sequence and predict the **same values for every target model**. What looks like a self-model is a procedure-level task model |

**What we can defend:** the within-stimulus story-swap effect; the
procedure-belief finding from phenotype prediction; the task-specificity of
the position bias; the overall null for self-recognition.
**What we cannot claim:** privileged introspection, a special SELF channel, or
broad generalization from only three models.

**Read more:**
- 📓 [Weekly handoff notes, 2026-09-29 → 10-03](docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md): the full narrative, with designs, numbers, bugs fixed, costs, limitations and next steps
- [FCE1/FCE2 cross-method report](data/spar_dynamic/FCE1_FCE2_CROSS_METHOD_REPORT.md)
- [Phenotype baselines report](data/spar_dynamic/PHENOTYPE_BASELINES_REPORT.md)
- [Corpus source report](corpus/THREE_ARCHITECTURE_SOURCE_REPORT.md)
- [Original preregistration (v1.0, 2026-09-21)](docs/preregistration/preregistration_v1.0_2026-09-21.md) and [build notes](docs/preregistration/build_notes_2026-09-21_rev4.md)
- [All handoff notes](docs/handoffs/)
- [Key references, with notes on how each relates to this project](docs/references.md) (Loula 2005; Couchman 2012; Kaneko & Tomonaga 2011; Van Koevering & Kleinberg 2024)

**Related work.** Martin, C. F. (2026). *Dodging Proteus: Prescribing
unexploitable play made language models more exploitable in a closed-loop
matching pennies assay.* Preprint, not peer reviewed.
[doi:10.5281/zenodo.21781962](https://doi.org/10.5281/zenodo.21781962) ·
[code](https://github.com/chimpanzity/dodging-proteus). The same LLM
behavioral signatures (over-alternation, persistent action bias) appear in an
adaptive matching-pennies setting.

Total OpenRouter spend across all studies: about **$38** (about $11 for the
pilots and corpus generation, plus about $27 for this week's experiments and
model-selection preflights; the itemized table is in the handoff).

---

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

All work in this repository builds on this corpus. The four earlier
pilots are archived in [`pilots/`](pilots/) for provenance.

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
pilots/                             preregistered harness (0) + prior pilots 1-4, archived
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
  full_corpus_exp1/                   FCE1/FCE2, validation, story-swap, phenotype prediction
    pairs.py / runner.py / analysis.py  pair construction, live runs, S/O/F contrasts
    validation.py                       objective A/B task-validation study
    cross_story.py                      within-stimulus three-story analysis
    phenotype_prediction.py             forecast elicitation (p_H or switch_rate)
    baselines_analysis.py / baselines_report.py  forecast MAE + self/observer contrasts
docs/handoffs/                      handoff notes (full narrative of each work session)
docs/preregistration/               original pilot preregistration v1.0 + build notes
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

The four pilots plus the canonical corpus generation came to about $11.
The corpus experiments (FCE1, FCE2, validation, story swap, phenotype
prediction) and model-selection preflights added about $27, so the total is
roughly **$38 USD** in
OpenRouter spend. Itemized costs are in the
[handoff notes](docs/handoffs/HANDOFF_SPAR_WEEK_2026-09-29_to_2026-10-03.md#cost-accounting).
