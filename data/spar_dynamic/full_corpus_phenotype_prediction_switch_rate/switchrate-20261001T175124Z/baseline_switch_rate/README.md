# Baseline analysis — feature=switch_rate

- Forecast run: `data/spar_dynamic/full_corpus_phenotype_prediction_switch_rate/switchrate-20261001T175124Z`
- Canonical corpus: `data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/results/corpus`
- Trials attempted: 360
- Strict-valid: 329
- Loose-recovered from abandoned trials: 31

## Observed feature values (per model × procedure, mean over 20 sequences)

| model | batch | history_conditioned | independent_calls |
|---|---:|---:|---:|
| astra | 0.6202 | 0.6323 | 0.4732 |
| fable | 0.6434 | 0.4758 | 0.0263 |
| mimo | 0.6237 | 0.4975 | 0.2333 |

## Parsers

- **Strict (primary)**: response must be a bare numeric literal in [0,1] after whitespace strip. No newlines in the stripped content.
- **Loose (secondary)**: strict first; if that fails and the response has a last non-empty line that is a bare numeric literal in [0,1], use it. Applied only to the first-attempt raw response for abandoned trials.

## Contrast definitions (per target × procedure)

- `SELF_mae`: MAE when the judge is the target under SELF wording.
- `OWN_NAMED_mae`: MAE when the judge is the target under NAMED wording.
- `OBS_mae`: mean of the two other judges' MAE for this target under NAMED wording.
- `self_advantage` = OBS_mae − SELF_mae (positive = target better than observers)
- `own_model_advantage` = OBS_mae − OWN_NAMED_mae
- `SELF_wording_advantage` = OWN_NAMED_mae − SELF_mae

## Hand checks

- `HHHH`: p(H) = 1.0, switch_rate = 0.0.
- `HTHT`: p(H) = 0.5, switch_rate = 1.0.
