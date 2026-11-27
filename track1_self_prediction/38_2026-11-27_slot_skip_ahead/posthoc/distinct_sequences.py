"""Post-hoc (added after the run; reads results/ and the design only, no model calls).

1. Free-answer counts per distinct sequence (the frozen realised table counts duplicated sampled sequences each time).
2. What each model answers under SLOT at k = 5 (the Experiment 35 position): the unused face (= roll 6 under the
   permutation rule), the last shown roll, another shown face, or invalid.
Usage (repo root): PYTHONPATH=src python track1_self_prediction/38_2026-11-27_slot_skip_ahead/posthoc/distinct_sequences.py
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
src = {r["source_id"]: r["rolls"] for r in csv.DictReader(open(EXP / "design_sources.csv", encoding="utf-8"))}
real = list(csv.DictReader(open(EXP / "results" / "realised.csv", encoding="utf-8")))
scored = list(csv.DictReader(open(EXP / "results" / "prompts_scored.csv", encoding="utf-8")))

rows = []
for m in ("qwen", "mistral"):
    for cond in ("SLOT", "B", "C"):
        for k in [str(k) for k in range(1, 9)]:
            cat = {}
            for r in real:
                if r["predictor"] == m and r["condition"] == cond and r["k"] == k:
                    cat[src[r["source_id"]]] = r["category"]
            n = len(cat)
            rows.append(dict(predictor=m, condition=cond, k=int(k), distinct_sequences=n, target_roll=sum(v == "target roll" for v in cat.values()),
                             roll_k1=sum(v == "roll k+1" for v in cat.values()), other_face=sum(v == "other face" for v in cat.values()),
                             invalid=sum(v == "invalid" for v in cat.values())))

k5 = []
for r in scored:
    if r["condition"] == "SLOT" and r["k"] == "5":
        shown = [int(v) for v in r["rolls_shown"].split()]
        unused = ({1, 2, 3, 4, 5, 6} - set(shown))
        a = r["content"].strip()
        kind = "invalid" if r["final_valid"] != "True" else ("unused face (roll 6 under the rule)" if int(a) in unused else
                                                              "last shown roll" if int(a) == shown[-1] else "another shown face")
        k5.append(dict(predictor=r["predictor"], rolls_shown=r["rolls_shown"], answer=a, kind=kind, own_top_next=r["answer_top_next_own"],
                       own_top_roll7=r["answer_top_two_own"]))

out = EXP / "posthoc"
for name, data in (("distinct_sequence_answers.csv", rows), ("slot_k5_answers.csv", k5)):
    with open(out / name, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(data)
summ = {}
for m in ("qwen", "mistral"):
    for cond in ("SLOT", "B", "C"):
        q = [r for r in rows if r["predictor"] == m and r["condition"] == cond]
        summ[f"{m} {cond}"] = {c: sum(r[c] for r in q) for c in ("distinct_sequences", "target_roll", "roll_k1", "other_face", "invalid")}
    q = [r for r in k5 if r["predictor"] == m]
    summ[f"{m} SLOT k=5"] = {kind: sum(r["kind"] == kind for r in q) for kind in sorted({r["kind"] for r in k5})}
    summ[f"{m} SLOT k=5"]["answer equals own top roll-7 face"] = sum(r["answer"] == r["own_top_roll7"] for r in q)
    summ[f"{m} SLOT k=5"]["prefixes"] = len(q)
json.dump(summ, open(out / "summary.json", "w", encoding="utf-8", newline="\n"), indent=1)
print(json.dumps(summ, indent=1))
