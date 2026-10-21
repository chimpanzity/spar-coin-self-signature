"""Trial-by-trial cross-story analysis: same stimulus × three alleged generative histories.

For a given stimulus method (default independent_calls) we align three runs by
(pair_id, target_label, wording_condition, judge_label) and build a wide table
with per-trial correctness and visible_answer under each story condition.

Produces:
  cross_story_trials.csv    one row per matched trial key, with
                              correct_{story}, answer_{story},
                              consistent_across_stories, flip_count
  cross_story_summary.csv   per (judge, target, wording, split) accuracy
                              under each story + joint SELF-rate across stories
"""

import argparse, csv, json, os
from collections import defaultdict
from typing import Dict, List, Optional


def _read_trial_level(run_dir: str) -> List[Dict]:
    path = os.path.join(run_dir, "trial_level.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no trial_level.csv in {run_dir}")
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _key(row: Dict) -> tuple:
    """Alignment key for a trial across story conditions."""
    return (row["pair_id"], row["target_label"], row["wording_condition"], row["judge_label"])


def build_cross_story(run_by_story: Dict[str, str], out_dir: str):
    rows_by_story: Dict[str, Dict[tuple, Dict]] = {}
    for story, run_dir in run_by_story.items():
        rows = _read_trial_level(run_dir)
        rows_by_story[story] = {_key(r): r for r in rows}

    # Keys present in ALL stories
    all_keys = set.intersection(*[set(d.keys()) for d in rows_by_story.values()])
    stories = list(run_by_story.keys())

    # Wide per-trial table
    wide_rows: List[Dict] = []
    for key in sorted(all_keys):
        pair_id, target, wording, judge = key
        base = rows_by_story[stories[0]][key]
        row: Dict = {
            "pair_id": pair_id, "triplet_id": base["triplet_id"],
            "split": base["split"],
            "target_label": target, "wording_condition": wording,
            "judge_label": judge,
            "source_label_A": base["source_label_A"],
            "source_label_B": base["source_label_B"],
            "sequence_A_id": base["sequence_A_id"],
            "sequence_B_id": base["sequence_B_id"],
            "correct_answer": base["correct_answer"],
        }
        answers = []
        corrects = []
        for s in stories:
            r = rows_by_story[s][key]
            row[f"status_{s}"] = r["status"]
            row[f"answer_{s}"] = r["visible_answer"]
            row[f"correct_{s}"] = r["correct"]
            answers.append(r["visible_answer"])
            corrects.append(str(r["correct"]) == "True")
        # Flip metrics (ignore None answers)
        clean = [a for a in answers if a in ("A", "B")]
        row["answers_distinct"] = len(set(clean))
        row["consistent_across_stories"] = int(len(set(clean)) == 1 and len(clean) == len(stories))
        row["n_correct_across_stories"] = sum(corrects)
        wide_rows.append(row)

    os.makedirs(out_dir, exist_ok=True)
    wide_path = os.path.join(out_dir, "cross_story_trials.csv")
    with open(wide_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(wide_rows[0].keys()))
        w.writeheader()
        for r in wide_rows: w.writerow(r)
    print(f"wrote {wide_path} ({len(wide_rows)} rows across {len(stories)} stories)", flush=True)

    # Per (judge, target, wording, split) accuracy under each story
    summary_rows: List[Dict] = []
    for split in ("development", "holdout"):
        for wording in ("NAMED", "SELF"):
            for judge in ("astra", "fable", "mimo"):
                for target in ("astra", "fable", "mimo"):
                    if wording == "SELF" and judge != target: continue
                    subset = [r for r in wide_rows if r["split"] == split
                              and r["wording_condition"] == wording
                              and r["judge_label"] == judge
                              and r["target_label"] == target]
                    out: Dict = {"split": split, "wording": wording,
                                 "judge": judge, "target": target,
                                 "n": len(subset)}
                    for s in stories:
                        scorable = [r for r in subset if r[f"status_{s}"] == "ok"
                                     and r[f"correct_{s}"] in ("True", "False")]
                        correct = sum(1 for r in scorable if r[f"correct_{s}"] == "True")
                        out[f"n_scored_{s}"] = len(scorable)
                        out[f"accuracy_{s}"] = round(correct / len(scorable), 4) if scorable else None
                        a_rate = [r[f"answer_{s}"] for r in subset if r[f"answer_{s}"] in ("A","B")]
                        out[f"a_rate_{s}"] = round(sum(1 for a in a_rate if a == "A") / len(a_rate), 4) if a_rate else None
                    # Consistency: fraction of items where answer identical across all stories
                    valid = [r for r in subset if all(r[f"answer_{s}"] in ("A","B") for s in stories)]
                    if valid:
                        same = sum(1 for r in valid if len(set(r[f"answer_{s}"] for s in stories)) == 1)
                        out["pct_consistent_across_stories"] = round(same / len(valid), 4)
                        out["n_consistent_valid"] = len(valid)
                    else:
                        out["pct_consistent_across_stories"] = None
                        out["n_consistent_valid"] = 0
                    summary_rows.append(out)

    sum_path = os.path.join(out_dir, "cross_story_summary.csv")
    with open(sum_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        for r in summary_rows: w.writerow(r)
    print(f"wrote {sum_path} ({len(summary_rows)} rows)", flush=True)
    return wide_rows, summary_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truthful-run", required=True,
                     help="run_dir of indep stimuli × truthful indep story")
    ap.add_argument("--false-history-run", required=True,
                     help="run_dir of indep stimuli × false history_conditioned story")
    ap.add_argument("--false-batch-run", required=True,
                     help="run_dir of indep stimuli × false batch story")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    run_by_story = {
        "truthful":      args.truthful_run,
        "false_history": args.false_history_run,
        "false_batch":   args.false_batch_run,
    }
    build_cross_story(run_by_story, args.out_dir)


if __name__ == "__main__":
    main()
