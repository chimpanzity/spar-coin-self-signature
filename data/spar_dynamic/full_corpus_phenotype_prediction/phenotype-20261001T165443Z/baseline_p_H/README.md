# Baseline analysis — feature=p_H

- Forecast run: `data/spar_dynamic/full_corpus_phenotype_prediction/phenotype-20261001T165443Z`
- Canonical corpus: `data/spar_dynamic/spar-stimulus-corpus-20260930T012044Z/results/corpus`
- Trials attempted: 360
- Strict-valid: 340
- Loose-recovered from abandoned trials: 20

## Observed feature values (per model × procedure, mean over 20 sequences)

| model | batch | history_conditioned | independent_calls |
|---|---:|---:|---:|
| astra | 0.4950 | 0.4600 | 0.3890 |
| fable | 0.5065 | 0.7440 | 0.9870 |
| mimo | 0.4875 | 0.6330 | 0.8600 |

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
