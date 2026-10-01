# Phenotype-prediction baselines — brief combined report

Two baselines, same framework (3 judges × 2 wordings × 3 targets × 3 procedures × 10 replicates = 340-360 forecasts; strict parser primary, loose last-line parser secondary for abandoned trials).

- Heads-frequency baseline:     `data/spar_dynamic/full_corpus_phenotype_prediction/phenotype-20261001T165443Z/baseline_p_H`
- Switching-rate baseline:      `data/spar_dynamic/full_corpus_phenotype_prediction_switch_rate/switchrate-20261001T175124Z/baseline_switch_rate`

## Observed phenotypes (canonical corpus, mean over 20 sequences)

| model | procedure | p(H) | switch_rate |
|---|---|---:|---:|
| astra | batch | 0.4950 | 0.6202 |
| astra | history_conditioned | 0.4600 | 0.6323 |
| astra | independent_calls | 0.3890 | 0.4732 |
| fable | batch | 0.5065 | 0.6434 |
| fable | history_conditioned | 0.7440 | 0.4758 |
| fable | independent_calls | 0.9870 | 0.0263 |
| mimo | batch | 0.4875 | 0.6237 |
| mimo | history_conditioned | 0.6330 | 0.4975 |
| mimo | independent_calls | 0.8600 | 0.2333 |

Hand checks: `HHHH` → p(H)=1.0, switch=0.0;  `HTHT` → p(H)=0.5, switch=1.0.

## Self vs observer MAE (loose parser)

`SELF_mae` is the judge's MAE at predicting its own feature under SELF wording. `OWN_NAMED_mae` is the same under NAMED wording. `OBS_mae` is the mean MAE of the two other judges predicting that target under NAMED wording.

### p(H)

| target | procedure | SELF | OWN_NAMED | OBS | self_adv | own_adv | SELF-wording_adv |
|---|---|---:|---:|---:|---:|---:|---:|
| astra | batch | 0.005 | 0.005 | 0.008 | 0.003 | 0.003 | 0.000 |
| astra | history_conditioned | 0.040 | 0.040 | 0.044 | 0.004 | 0.004 | 0.000 |
| astra | independent_calls | 0.611 | 0.461 | 0.361 | -0.250 | -0.100 | -0.150 |
| fable | batch | 0.010 | 0.009 | 0.006 | -0.004 | -0.002 | -0.001 |
| fable | history_conditioned | 0.244 | 0.237 | 0.244 | 0.000 | 0.007 | -0.007 |
| fable | independent_calls | 0.013 | 0.013 | 0.250 | 0.237 | 0.237 | 0.000 |
| mimo | batch | 0.013 | 0.013 | 0.022 | 0.010 | 0.010 | 0.000 |
| mimo | history_conditioned | 0.133 | 0.133 | 0.128 | -0.005 | -0.005 | 0.000 |
| mimo | independent_calls | 0.360 | 0.360 | 0.138 | -0.223 | -0.223 | 0.000 |

### switch_rate

| target | procedure | SELF | OWN_NAMED | OBS | self_adv | own_adv | SELF-wording_adv |
|---|---|---:|---:|---:|---:|---:|---:|
| astra | batch | 0.057 | 0.084 | 0.065 | 0.008 | -0.019 | 0.027 |
| astra | history_conditioned | 0.088 | 0.088 | 0.132 | 0.044 | 0.044 | 0.000 |
| astra | independent_calls | 0.473 | 0.473 | 0.272 | -0.201 | -0.201 | 0.000 |
| fable | batch | 0.026 | 0.023 | 0.075 | 0.049 | 0.052 | -0.003 |
| fable | history_conditioned | 0.272 | 0.247 | 0.153 | -0.120 | -0.095 | -0.025 |
| fable | independent_calls | 0.026 | 0.026 | 0.193 | 0.167 | 0.167 | 0.000 |
| mimo | batch | 0.128 | 0.129 | 0.032 | -0.096 | -0.097 | 0.001 |
| mimo | history_conditioned | 0.003 | 0.003 | 0.280 | 0.278 | 0.278 | 0.000 |
| mimo | independent_calls | 0.237 | 0.267 | 0.233 | -0.004 | -0.033 | 0.029 |

## Organizing questions

### 1. Which models accurately predict their own biases?

Smaller SELF MAE = more accurate about own bias. Loose parser, SELF wording:

| judge | p(H) batch | p(H) hist | p(H) indep | switch batch | switch hist | switch indep |
|---|---:|---:|---:|---:|---:|---:|
| astra | 0.005 | 0.040 | 0.611 | 0.057 | 0.088 | 0.473 |
| fable | 0.010 | 0.244 | 0.013 | 0.026 | 0.272 | 0.026 |
| mimo | 0.013 | 0.133 | 0.360 | 0.128 | 0.003 | 0.237 |

Fable's SELF predictions are strikingly accurate on both features under independent_calls (own p(H) MAE 0.013, own switch_rate MAE 0.026) and roughly right on batch too, but it is off on its own history_conditioned behavior (predicts both features ≈ 0.5 when observed p(H) = 0.74 and switch_rate = 0.48). Mimo is near-perfectly calibrated on its own history_conditioned switch_rate (predicts 0.5; observed 0.497) but otherwise predicts 0.5 for everything regardless of procedure. Astra is accurate on batch and history, but far off on its own independent_calls behavior (predicts p(H) = 1.0 when actual = 0.39; predicts switch_rate = 0.0 when actual = 0.47).

### 2. Does accuracy depend on generation procedure?

Yes. SELF MAE for every judge is lowest on batch (where observed is close to the universal 0.5 prior all three judges give), near-chance on history_conditioned (which fable and mimo diverge from), and most extreme on independent_calls, where fable is accurate (actual phenotype near-saturated and matches its own "indep → p(H)≈1" prior) while astra and mimo are badly miscalibrated.

### 3. Are self-predictions more accurate than equally informed observer predictions?

Only for fable under independent_calls (self_advantage p(H) +0.237; switch_rate +0.167). Astra and mimo under independent_calls show a strong NEGATIVE self-advantage: they predict their own output worse than other judges predict it. On batch and history_conditioned the contrasts are small or mixed. The observer baseline is very low on batch (judges predict ~0.5 for everyone and observed is near 0.5), so there is little room to differ.

### 4. Does SELF wording improve accuracy relative to naming the same model?

No consistent effect. Across the 18 (target × procedure × feature) cells, SELF-vs-OWN_NAMED differences cluster near zero on both features. Where they exist they are small (|≤ 0.03|). The large self_advantages reported above are driven by target-vs-observer differences, not by the word "SELF". That is consistent with the earlier source-attribution finding that SELF wording alone does not elicit a privileged channel.

### 5. Do nearly balanced heads frequencies coexist with unusual switching?

Yes. Astra batch has observed p(H) = 0.495 but switch_rate = 0.62 — nearly fair heads frequency, excess alternation. Astra history_conditioned similarly: p(H) = 0.46, switch = 0.63. Mimo batch: p(H) = 0.49, switch = 0.62. In contrast, fable independent_calls has p(H) = 0.99 and switch = 0.03 — both extreme and mutually consistent. The two features carry non-redundant information about LLM coin-simulation behavior.

## Caveats

- Ten replicates per cell measures variability in elicited estimates, not replication across new source corpora. The source corpus is a fixed reference.
- Fable produced reasoning before the final numeric answer on all 40 of its NAMED-on-other-target|independent_calls cells across both baselines (p_H and switch_rate). The strict parser rejects those; the loose last-line parser recovers them. The two parsings are reported side-by-side.
- Accurate self-prediction (fable on indep) does not establish privileged self-access: fable predicts the same values for other targets under indep, so what it has is a general procedure-level theory that happens to be approximately correct for fable itself.
