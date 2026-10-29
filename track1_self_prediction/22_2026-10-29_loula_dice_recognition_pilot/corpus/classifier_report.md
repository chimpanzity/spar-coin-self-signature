# Development-only source discriminability (gate)

Logistic regression (L2, C=1) on p1, p2, p3, p4, p5, p6, switch_frac, max_run, n_distinct; standardized within each training fold; grouped stratified 5-fold CV (identical strings share a fold). n = 60 development sequences, 33 unique strings.

| Measure | Value |
|---|---|
| **CV ROC AUC (gate statistic)** | **0.758** |
| 95% bootstrap over unique-string groups | 0.537–0.922 |
| Balanced accuracy (threshold 0.5) | 0.750 |
| Confusion [[Qwen→Qwen, Qwen→Mistral], [Mistral→Qwen, Mistral→Mistral]] | [[20, 10], [5, 25]] |
| Majority / chance | AUC 0.5, balanced accuracy 0.5 |
| Nearest-centroid CV AUC | 0.789 |
| Switch-fraction-only CV AUC | 0.477 |
| Label permutations (1000): mean / 95th percentile AUC | 0.487 / 0.639 |
| Permutation p (AUC ≥ observed) | 0.0020 |

**Gate (AUC ≥ 0.65): PASS: recognition judgments may run.** The threshold is an operational feasibility screen, not a significance test.
