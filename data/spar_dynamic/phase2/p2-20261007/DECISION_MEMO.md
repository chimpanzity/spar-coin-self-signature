# Decision memo (Stage 1 -> Stage 2)

- Apparatus and generation parser valid? Yes, after amendments A1 (Qwen seeds) and A2 (parser gen_v2), both recorded in amendments.jsonl before any judge data.
- Completion and pair fixtures valid? One or more valid-response gates FAILED (see STAGE1_REPORT.md); per Chris, the run continues and failures are reported.
- Rehearsal valid? See STAGE1_REPORT.md rehearsal table; flat judgments are reported, not rejected.
- Minimal observer diagnostics and headroom decision recorded? Yes; review_required=False.
- Prefix k=10 and probability-response policy retained? Yes.
- Two-sided H4 and common-set rules fixed? Yes (analysis.py at the frozen hash).
- Precision plan acknowledged? PRECISION_PLAN.md written before test generation.
- Cost ceiling: hard cap $100 (Chris).
- Arm status: core completion and anonymous arms ready; named fixtures, named calls and historical generation run after the protected core calls; LASSO/regularized code exists before the freeze.
- Low-validity cells (Qwen x fair) are not paused, per Chris's instruction.

