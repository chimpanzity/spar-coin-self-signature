# Loula-inspired dice-sequence self-recognition: pilot report (2026-10-29)

**Tag:** `LOULA_DICE_RECOGNITION_PILOT_v1.0`. **Handoff:** `GPT_SPAR_Loula_Dice_Self_Recognition_OpenRouter_Pilot_Claude_Code_Handoff_v1.0`. **Models (OpenRouter, one pinned provider each, no fallbacks):** Qwen3-32B on SiliconFlow (reasoning off) and Mistral Small 3.2 24B on DeepInfra. **Spend:** $0.0057 of the $5 cap, 355 calls. No GPU; Experiment 21 was not rerun.

## 1. What ran

| Phase | Outcome |
|---|---|
| Dry run | Frozen manifest and prompts, planned ids; 0 API calls |
| A. API preflight | **PASS.** 4 generations + 2 judgments per model. Providers pinned on every call, Qwen reasoning tokens 0, all outputs valid. |
| B. Stimulus corpus | **PASS.** 50 valid sequences per model (Qwen 50 of 50 attempts; Mistral 50 of 53, 3 rejected for a "Here is your sequence…" preamble). Exact 30/20 development/held-out split under the duplicate-group rule. |
| C. Discriminability gate | **PASS.** Development-only CV AUC 0.76 (gate 0.65). |
| D. Recognition pilot | Run: 240 / 240 judgments, all valid strict A/B answers |
| E. Analysis | This report; no main study launched |

## 2. Observations

### 2.1 The two models' 10-roll sequences (temperature 0.7)

- **Both models generate permutation-like, "too random" sequences.**
  - All 100 sequences use all six faces. A fair die gives that in about 27% of 10-roll sequences.
  - Mistral never repeats a face back to back (50 of 50), and Qwen almost never does (48 of 50). A fair die gives no adjacent repeat in about 19%.
  - Face 4 is under-used by both (mean share .11 Qwen, .13 Mistral, vs .17).
- **There are strong positional habits, some shared.**
  - Both put a 4 at position 6 in most sequences: Qwen 70%, Mistral 64%.
  - Qwen opens with 5 in 56% of sequences, consistent with its temperature-0 first roll in Experiment 21.
  - Figure: `analysis/figures/position_face_frequencies.png`.
- **Diversity is limited.**
  - The 100 sequences contain 64 distinct strings: Qwen 31, Mistral 34.
  - Within-source duplicate groups: Qwen 9, Mistral 7. Mistral's most common string (`1 3 5 2 6 4 1 3 2 5`) appears 7 times.
  - One string, `5 2 6 1 3 4 6 2 5 1`, was produced 4 times by **each** model. It is nondiagnostic, so it was kept in development, as prespecified.

### 2.2 External discriminability (development only, 60 sequences, 33 unique strings)

| Measure | Value |
|---|---|
| **Grouped 5-fold CV ROC AUC** (logistic regression on face proportions, switch fraction, longest run, distinct faces) | **0.758** |
| 95% bootstrap over unique-string groups | 0.54–0.92 |
| Balanced accuracy; confusion | 0.75; Qwen 20/30 correct, Mistral 25/30 correct |
| Nearest-centroid CV AUC | 0.789 |
| Switch-fraction-only CV AUC | 0.477 (switching is near-constant in both models) |
| 1,000 label permutations: mean / 95th percentile; p | 0.487 / 0.639; p = .002 |

**Gate passed.** The frozen development classifier, applied without tuning to the 40 held-out sequences (31 distinct strings), gives **AUC 0.72** and picks the Qwen member of **77.5%** of the 20 held-out pairs (95% pair bootstrap 0.60–0.93). The source information therefore exists in the held-out stimuli.

### 2.3 Recognition judgments (20 held-out pairs × 2 orders × 2 judges × 3 questions)

| Judge | Question | Answers given | Pair-averaged accuracy (95% pair bootstrap) | Same sequence chosen in both orders |
|---|---|---|---|---|
| Qwen3-32B | self ("an instance of your model") | A ×40 | 0.50 (0.50–0.50) | 0 / 20 |
| Qwen3-32B | named: Qwen3-32B | A ×40 | 0.50 | 0 / 20 |
| Qwen3-32B | named: Mistral Small 3.2 24B | **B ×40** | 0.50 | 0 / 20 |
| Mistral Small 3.2 | self | A ×40 | 0.50 | 0 / 20 |
| Mistral Small 3.2 | named: Qwen3-32B | A ×40 | 0.50 | 0 / 20 |
| Mistral Small 3.2 | named: Mistral Small 3.2 24B | A ×35, B ×5 | 0.525 (0.45–0.60) | 3 / 20 |

| Prespecified contrast | Value (95% pair bootstrap) |
|---|---|
| Own-model advantage, named = ½[(Q→Qwen − M→Qwen) + (M→Mistral − Q→Mistral)] | **+0.013** (−0.025 to +0.050) |
| Qwen: self − named own | 0.000 |
| Mistral: self − named own | −0.025 (−0.10 to +0.05) |
| External classifier, same pairs | 0.775 (0.60–0.93) |

**The judges' answers are essentially independent of the sequences.**
- Qwen answers "A" whenever the target is itself or Qwen3-32B, and "B" whenever it is Mistral. That matches the order the two models are named in the prompt ("Qwen3-32B and Mistral Small 3.2 24B"), so it looks like a name-order heuristic.
- Mistral answers "A" in 115 of 120 trials.
- Because each pair appears once in each order, a fixed letter scores exactly 0.5. In 5 of 6 cells no judge picked the same sequence in both orders.

## 3. Interpretation

This is **Outcome D** of the handoff (the classifier succeeds and both judges fail), in its most degenerate form. Under this prompt, at temperature 0 with an 8-token answer limit, neither judge used the stimuli at all, so the pilot measures a response default, not recognition.

Keeping the handoff's constructs separate:
- **Source discriminability:** present, but modest. The models differ in which permutation-like patterns they favour, not in how random they are. An external observer reaches about 0.72–0.76 AUC.
- **Correct self-labeling:** absent (0.50 for both judges).
- **Privileged self-recognition:** cannot be assessed here. The own-model advantage is +0.01 with an interval spanning zero, but with content-independent answers it is not interpretable either way.
- **Introspective self-knowledge:** not addressed by this design.

These results do **not** show that the models lack self-recognition capacity, only that this forced-choice elicitation did not engage the stimuli. They also do not show that the fingerprints are absent.

## 4. Comparison with earlier SPAR work (not a novel paradigm)

| Earlier SPAR result | How this pilot relates |
|---|---|
| **Coin-flip source signature (track 1, folder 02):** signatures existed (classifier 0.70 batch / 0.93 online), with no consistent own-source advantage | Same pattern with dice and two open-weight models: signatures exist, no self advantage |
| **A/B task validation (09):** Astra and Fable read the sequences (100% on verifiable questions); MiMo showed a strong "A" bias | Here both judges behave like MiMo did, but more extremely: no reading check was included, so we cannot tell whether they *can* read the stimuli in this format |
| **Probabilistic judgments collapsed to 0.5 (12–13)** | The forced-choice replacement also collapsed to a default, at temperature 0 with a short answer |

What may be new is the tightly matched two-open-weight dice implementation tied to Experiment 21. The binary self-recognition paradigm itself is not new.

## 5. Limitations

- **Small and exploratory:** 20 held-out pairs, 33 distinct development strings, and a wide AUC interval (0.54–0.92).
- **Duplicates:** held-out has 31 distinct strings in 40 sequences. Pairs are independent units, but some strings recur across pairs.
- **One prompt per condition, temperature 0, 8-token limit.** The degenerate answers may be specific to this elicitation.
- **Name order** in the named prompt was fixed (Qwen listed first), which Qwen's answers appear to track. The handoff's frozen wording did not counterbalance it.
- **Provider-served models:** SiliconFlow fp8 and DeepInfra fp8. Results may differ under other serving.

## 6. Recommendation

**Stop. Do not scale this design to a main study:** a larger version would only measure response defaults more precisely. Any follow-up needs a separately approved protocol. Candidate changes (proposed, not run):
1. **Add a reading check in the same format** (e.g. "Which sequence contains more 6s? Answer A or B only"), as in folder 09, to establish whether each judge processes the sequences at all.
2. **Counterbalance the order the two models are named in** inside the named prompt.
3. **Score the judgment instead of sampling it.** With open weights (the Experiment 21 pipeline), read P(A) vs P(B) for both orientations and average the log-odds. That cancels a fixed position bias and yields a graded preference even when the greedy answer is always "A".
4. Optionally allow brief reasoning or a longer answer, as a separate arm.

## 7. Files

| Path | Contents |
|---|---|
| `protocol_frozen.md`, `manifest.json` | Prompts, hashes, pins, settings, gates, analysis plan, seeds, deviations (none to the protocol) |
| `api_preflight/` | Raw preflight calls and `preflight_summary.json` |
| `corpus/raw_attempts.jsonl` | All 103 generation attempts with raw responses |
| `corpus/stimuli.csv`, `development.csv`, `heldout.csv`, `phenotype_features.csv` | The stimuli, the split and the features |
| `corpus/classifier_report.md`, `classifier_cv.csv`, `classifier_gate.json` | The gate |
| `judgments/raw_attempts.jsonl`, `pairs.csv`, `trials.csv`, `responses.csv` | All 240 judgments |
| `analysis/summary.json`, `paired_accuracy.csv`, `judge_by_target.csv` | Analysis tables |
| `analysis/figures/` | `face_histogram`, `position_face_frequencies`, `sequence_statistics`, `classifier_roc`, `recognition_accuracy`, `orientation_consistency` |
| `cost_ledger.json`, `corpus_run.log`, `judge_run.log` | Spend and run logs |
| Code and tests | `src/spar_dynamic/dice_recognition/`; `tests/test_dice_recognition.py` (34 offline tests) |

Re-run the offline phases:

```bash
PYTHONPATH=src python -m spar_dynamic.dice_recognition classify
PYTHONPATH=src python -m spar_dynamic.dice_recognition analyse
```
