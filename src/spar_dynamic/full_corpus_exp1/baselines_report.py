"""Brief combined report for the two phenotype-prediction baselines.

Writes a short markdown that answers the organizing questions from the task
spec and references both p_H and switch_rate baseline directories.
"""

import argparse, csv, os
from typing import Dict, List, Optional


def _read_csv(path: str) -> List[Dict]:
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return list(csv.DictReader(f))


def _fmt(v, places=3):
    if v in (None, "", "None"): return "—"
    try: return f"{float(v):.{places}f}"
    except Exception: return str(v)


def _row(rows, **kw):
    for r in rows:
        if all(str(r.get(k)) == str(v) for k, v in kw.items()):
            return r
    return None


def build(p_H_dir: str, switch_dir: str, out_path: str):
    obs_pH = _read_csv(os.path.join(p_H_dir, "observed_from_corpus.csv"))
    obs_sw = _read_csv(os.path.join(switch_dir, "observed_from_corpus.csv"))
    cs_pH = _read_csv(os.path.join(p_H_dir, "cell_summary.csv"))
    cs_sw = _read_csv(os.path.join(switch_dir, "cell_summary.csv"))
    ct_pH = _read_csv(os.path.join(p_H_dir, "contrasts_loose.csv"))
    ct_sw = _read_csv(os.path.join(switch_dir, "contrasts_loose.csv"))

    lines = []
    lines.append("# Phenotype-prediction baselines — brief combined report")
    lines.append("")
    lines.append("Two baselines, same framework (3 judges × 2 wordings × 3 targets × 3 procedures × "
                 "10 replicates = 340-360 forecasts; strict parser primary, loose "
                 "last-line parser secondary for abandoned trials).")
    lines.append("")
    lines.append(f"- Heads-frequency baseline:     `{p_H_dir}`")
    lines.append(f"- Switching-rate baseline:      `{switch_dir}`")
    lines.append("")

    # Observed table (both features side-by-side)
    lines.append("## Observed phenotypes (canonical corpus, mean over 20 sequences)")
    lines.append("")
    lines.append("| model | procedure | p(H) | switch_rate |")
    lines.append("|---|---|---:|---:|")
    for m in ("astra","fable","mimo"):
        for p in ("batch","history_conditioned","independent_calls"):
            r1 = _row(obs_pH, model=m, procedure=p)
            r2 = _row(obs_sw, model=m, procedure=p)
            lines.append(f"| {m} | {p} | "
                         f"{_fmt(r1['mean_over_sequences'] if r1 else None, 4)} | "
                         f"{_fmt(r2['mean_over_sequences'] if r2 else None, 4)} |")
    lines.append("")
    lines.append("Hand checks: `HHHH` → p(H)=1.0, switch=0.0;  `HTHT` → p(H)=0.5, switch=1.0.")
    lines.append("")

    # SELF vs observer MAE per feature
    lines.append("## Self vs observer MAE (loose parser)")
    lines.append("")
    lines.append("`SELF_mae` is the judge's MAE at predicting its own feature under SELF wording. "
                 "`OWN_NAMED_mae` is the same under NAMED wording. `OBS_mae` is the mean MAE of the "
                 "two other judges predicting that target under NAMED wording.")
    lines.append("")
    for label, ct in (("p(H)", ct_pH), ("switch_rate", ct_sw)):
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| target | procedure | SELF | OWN_NAMED | OBS | self_adv | own_adv | SELF-wording_adv |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
        for t in ("astra","fable","mimo"):
            for p in ("batch","history_conditioned","independent_calls"):
                r = _row(ct, target=t, procedure=p)
                if r:
                    lines.append(f"| {t} | {p} | {_fmt(r['SELF_mae'])} | {_fmt(r['OWN_NAMED_mae'])} | "
                                 f"{_fmt(r['OBS_mae'])} | {_fmt(r['self_advantage'])} | "
                                 f"{_fmt(r['own_model_advantage'])} | {_fmt(r['SELF_wording_advantage'])} |")
        lines.append("")

    # Scientific questions
    lines.append("## Organizing questions")
    lines.append("")
    lines.append("### 1. Which models accurately predict their own biases?")
    lines.append("")
    def _mae(ct, judge, wording, target, procedure):
        for r in ct:
            if (r["target"] == target and r["procedure"] == procedure):
                return float(r["SELF_mae"]) if wording == "SELF" else float(r["OWN_NAMED_mae"])
        return None
    lines.append("Smaller SELF MAE = more accurate about own bias. Loose parser, SELF wording:")
    lines.append("")
    lines.append("| judge | p(H) batch | p(H) hist | p(H) indep | switch batch | switch hist | switch indep |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for judge in ("astra","fable","mimo"):
        row = [judge]
        for proc in ("batch","history_conditioned","independent_calls"):
            v = _mae(ct_pH, judge, "SELF", judge, proc)
            row.append(_fmt(v))
        for proc in ("batch","history_conditioned","independent_calls"):
            v = _mae(ct_sw, judge, "SELF", judge, proc)
            row.append(_fmt(v))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("Fable's SELF predictions are strikingly accurate on both features under "
                 "independent_calls (own p(H) MAE 0.013, own switch_rate MAE 0.026) and roughly "
                 "right on batch too, but it is off on its own history_conditioned behavior "
                 "(predicts both features ≈ 0.5 when observed p(H) = 0.74 and switch_rate = 0.48). "
                 "Mimo is near-perfectly calibrated on its own history_conditioned switch_rate "
                 "(predicts 0.5; observed 0.497) but otherwise predicts 0.5 for everything "
                 "regardless of procedure. Astra is accurate on batch and history, but far off "
                 "on its own independent_calls behavior (predicts p(H) = 1.0 when actual = 0.39; "
                 "predicts switch_rate = 0.0 when actual = 0.47).")
    lines.append("")

    lines.append("### 2. Does accuracy depend on generation procedure?")
    lines.append("")
    lines.append("Yes. SELF MAE for every judge is lowest on batch (where observed is close to "
                 "the universal 0.5 prior all three judges give), near-chance on "
                 "history_conditioned (which fable and mimo diverge from), and most extreme on "
                 "independent_calls, where fable is accurate (actual phenotype near-saturated "
                 "and matches its own \"indep → p(H)≈1\" prior) while astra and mimo are badly "
                 "miscalibrated.")
    lines.append("")

    lines.append("### 3. Are self-predictions more accurate than equally informed observer predictions?")
    lines.append("")
    lines.append("Only for fable under independent_calls (self_advantage p(H) +0.237; switch_rate +0.167). "
                 "Astra and mimo under independent_calls show a strong NEGATIVE self-advantage: "
                 "they predict their own output worse than other judges predict it. On batch and "
                 "history_conditioned the contrasts are small or mixed. The observer baseline is "
                 "very low on batch (judges predict ~0.5 for everyone and observed is near 0.5), "
                 "so there is little room to differ.")
    lines.append("")

    lines.append("### 4. Does SELF wording improve accuracy relative to naming the same model?")
    lines.append("")
    lines.append("No consistent effect. Across the 18 (target × procedure × feature) cells, "
                 "SELF-vs-OWN_NAMED differences cluster near zero on both features. Where they "
                 "exist they are small (|≤ 0.03|). The large self_advantages reported above are "
                 "driven by target-vs-observer differences, not by the word \"SELF\". That is "
                 "consistent with the earlier source-attribution finding that SELF wording "
                 "alone does not elicit a privileged channel.")
    lines.append("")

    lines.append("### 5. Do nearly balanced heads frequencies coexist with unusual switching?")
    lines.append("")
    lines.append("Yes. Astra batch has observed p(H) = 0.495 but switch_rate = 0.62 — nearly "
                 "fair heads frequency, excess alternation. Astra history_conditioned similarly: "
                 "p(H) = 0.46, switch = 0.63. Mimo batch: p(H) = 0.49, switch = 0.62. In contrast, "
                 "fable independent_calls has p(H) = 0.99 and switch = 0.03 — both extreme and "
                 "mutually consistent. The two features carry non-redundant information about "
                 "LLM coin-simulation behavior.")
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append("- Ten replicates per cell measures variability in elicited estimates, not "
                 "replication across new source corpora. The source corpus is a fixed reference.")
    lines.append("- Fable produced reasoning before the final numeric answer on all 40 of its "
                 "NAMED-on-other-target|independent_calls cells across both baselines (p_H and "
                 "switch_rate). The strict parser rejects those; the loose last-line parser "
                 "recovers them. The two parsings are reported side-by-side.")
    lines.append("- Accurate self-prediction (fable on indep) does not establish privileged "
                 "self-access: fable predicts the same values for other targets under indep, "
                 "so what it has is a general procedure-level theory that happens to be "
                 "approximately correct for fable itself.")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p-h-dir", required=True)
    ap.add_argument("--switch-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build(args.p_h_dir, args.switch_dir, args.out)
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
