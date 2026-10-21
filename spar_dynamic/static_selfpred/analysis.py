"""Analysis for STATIC_SELFPRED_v1.0 (handoff Part I §4).

For every model configuration x task x position, compares answer
distributions (not single draws):

  object    property of the object-level answers (letter of the animal name,
            or the kth die value)
  self      hypothetical self-prediction ("your response")
  generic   same question about "a typical large language model"
  gname     animal only: letter derived from the generic full-name answers
  neutral   animal only: agentless phrasing
  single    dice only: a single simulated die roll (position-invariant default)

Metrics per comparator C against the object distribution O:
  match    P(a C draw equals an independent O draw) = sum_x C(x) O(x)
  tvd      total variation distance between C and O
  mode_ok  modal C answer equals modal O answer
The key contrast is match(self) - match(generic): does asking about "you"
track the model's own behaviour better than asking about a typical model?
Uncertainty: 95% percentile bootstrap, resampling calls within each cell
(independent fresh-context calls), 4,000 replicates, seed 20261022.

Supplied-answer check: accuracy of the letter of the supplied name.
Non-valid responses are counted per cell and excluded from distributions.

Usage:
    python -m spar_dynamic.static_selfpred.analysis <run_dir>
"""

from __future__ import annotations

import collections
import csv
import json
import os
import sys
from typing import Dict, List, Optional

import numpy as np

from spar_dynamic.favorite_animal.parsers import letter_at
from spar_dynamic.static_selfpred import prompts

N_BOOT = 4000
SEED = 20261022


def load(run_dir: str) -> List[Dict]:
    rows = {}
    for line in open(os.path.join(run_dir, "raw_attempts.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        tid = r.get("trial_id") or f"{r['model_label']}|{r['config']}|{r['cell']}|{r['position']}|{r['replicate']}"
        if r["category"] != "transport_error":
            rows[tid] = r
    return list(rows.values())


def dist(values: List[str]) -> Dict[str, float]:
    c = collections.Counter(values)
    n = sum(c.values())
    return {k: v / n for k, v in c.items()} if n else {}


def match(p: Dict[str, float], q: Dict[str, float]) -> float:
    return sum(p.get(k, 0.0) * q.get(k, 0.0) for k in set(p) | set(q))


def tvd(p: Dict[str, float], q: Dict[str, float]) -> float:
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in set(p) | set(q))


def mode(values: List[str]) -> Optional[str]:
    c = collections.Counter(values).most_common()
    if not c:
        return None
    top = [k for k, n in c if n == c[0][1]]
    return "/".join(sorted(top))


def boot_ci(stat, samples: List[List[str]], rng) -> List[float]:
    """Percentile CI of stat(*resampled lists), resampling each list independently."""
    if any(len(s) == 0 for s in samples):
        return [float("nan"), float("nan")]
    arrs = [np.array(s, dtype=object) for s in samples]
    vals = []
    for _ in range(N_BOOT):
        res = [list(a[rng.integers(0, len(a), len(a))]) for a in arrs]
        vals.append(stat(*res))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def cell_values(rows, label, config, cell, position=None) -> List[str]:
    return [str(r["value"]) for r in rows
            if r["model_label"] == label and r["config"] == config and r["cell"] == cell
            and r["category"] == "valid" and (position is None or str(r["position"]) == str(position))]


def object_property(rows, label, config, task, position) -> List[str]:
    if task == "animal":
        names = cell_values(rows, label, config, "animal_object")
        return [x for x in (letter_at(n, position) for n in names) if x]
    seqs = cell_values(rows, label, config, "dice_object")
    return [s.split()[int(position) - 1] for s in seqs]


def analyse(rows: List[Dict]) -> Dict:
    rng = np.random.default_rng(SEED)
    configs = sorted({(r["model_label"], r["config"]) for r in rows})
    out = {"cells": [], "categories": {}, "supplied": []}

    cats = collections.defaultdict(collections.Counter)
    for r in rows:
        cats[f"{r['model_label']}|{r['config']}|{r['cell']}"][r["category"]] += 1
    out["categories"] = {k: dict(v) for k, v in sorted(cats.items())}

    for label, config in configs:
        for task, positions in (("animal", prompts.ANIMAL_POSITIONS), ("dice", tuple(prompts.DICE_ORDINALS))):
            for pos in positions:
                obj = object_property(rows, label, config, task, pos)
                comps = {"self": cell_values(rows, label, config, f"{task}_self", pos),
                         "generic": cell_values(rows, label, config, f"{task}_generic", pos)}
                if task == "animal":
                    comps["neutral"] = cell_values(rows, label, config, "animal_neutral", pos)
                    gnames = cell_values(rows, label, config, "animal_generic_name")
                    comps["gname"] = [x for x in (letter_at(n, pos) for n in gnames) if x]
                else:
                    comps["single"] = cell_values(rows, label, config, "dice_single_roll")
                if not obj:
                    continue
                O = dist(obj)
                rec = dict(model=label, config=config, task=task, position=pos, n_object=len(obj),
                           object_mode=mode(obj), object_dist=O)
                for name, vals in comps.items():
                    if not vals:
                        continue
                    C = dist(vals)
                    rec[name] = dict(n=len(vals), mode=mode(vals), dist=C,
                                     match=match(C, O), tvd=tvd(C, O),
                                     mode_ok=mode(vals) == mode(obj),
                                     match_ci=boot_ci(lambda c, o: match(dist(c), dist(o)), [vals, obj], rng))
                if comps["self"] and comps["generic"]:
                    rec["self_minus_generic"] = dict(
                        diff=rec["self"]["match"] - rec["generic"]["match"],
                        ci=boot_ci(lambda s, g, o: match(dist(s), dist(o)) - match(dist(g), dist(o)),
                                   [comps["self"], comps["generic"], obj], rng))
                out["cells"].append(rec)

        # supplied-answer competence
        name_rows = [r for r in rows if r["model_label"] == label and r["config"] == config
                     and r["cell"] == "animal_supplied"]
        if name_rows:
            supplied = _supplied_name(name_rows[0]["prompt"])
            for pos in prompts.ANIMAL_POSITIONS:
                pr = [r for r in name_rows if r["position"] == pos]
                ok = sum(r["category"] == "valid" and r["value"] == letter_at(supplied, pos) for r in pr)
                out["supplied"].append(dict(model=label, config=config, name=supplied, position=pos,
                                            correct=ok, n=len(pr)))
    return out


def _supplied_name(prompt_text: str) -> str:
    return prompt_text.split('"')[1]


def write_tables(res: Dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    comps = ("self", "generic", "gname", "neutral", "single")
    with open(os.path.join(out_dir, "comparison_table.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "config", "task", "position", "n_object", "object_mode"]
                   + [f"{c}_{m}" for c in comps for m in ("n", "mode", "match", "match_lo", "match_hi", "tvd")]
                   + ["self_minus_generic", "smg_lo", "smg_hi"])
        for r in res["cells"]:
            row = [r["model"], r["config"], r["task"], r["position"], r["n_object"], r["object_mode"]]
            for c in comps:
                x = r.get(c)
                row += ([x["n"], x["mode"], round(x["match"], 3), round(x["match_ci"][0], 3),
                         round(x["match_ci"][1], 3), round(x["tvd"], 3)] if x else [""] * 6)
            smg = r.get("self_minus_generic")
            row += ([round(smg["diff"], 3), round(smg["ci"][0], 3), round(smg["ci"][1], 3)] if smg else [""] * 3)
            w.writerow(row)
    with open(os.path.join(out_dir, "supplied_answer_check.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model", "config", "name", "position", "correct", "n"])
        w.writeheader()
        w.writerows(res["supplied"])
    with open(os.path.join(out_dir, "response_categories.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        allcats = sorted({c for v in res["categories"].values() for c in v})
        w.writerow(["model|config|cell"] + allcats)
        for k, v in res["categories"].items():
            w.writerow([k] + [v.get(c, 0) for c in allcats])


def plot(res: Dict, out_dir: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cells = res["cells"]
    configs = sorted({(c["model"], c["config"]) for c in cells})
    comps = [("self", "#d1495b"), ("generic", "#00798c"), ("gname", "#66a182"),
             ("neutral", "#edae49"), ("single", "#8d6a9f")]
    for task in ("animal", "dice"):
        fig, axes = plt.subplots(1, len(configs), figsize=(4.2 * len(configs), 3.8), sharey=True, squeeze=False)
        for ax, (label, config) in zip(axes[0], configs):
            sub = [c for c in cells if c["model"] == label and c["config"] == config and c["task"] == task]
            xs = np.arange(len(sub))
            present = [(n, col) for n, col in comps if any(n in c for c in sub)]
            width = 0.8 / max(1, len(present))
            for i, (name, col) in enumerate(present):
                m = [c[name]["match"] if name in c else np.nan for c in sub]
                lo = [c[name]["match"] - c[name]["match_ci"][0] if name in c else 0 for c in sub]
                hi = [c[name]["match_ci"][1] - c[name]["match"] if name in c else 0 for c in sub]
                ax.bar(xs + (i - (len(present) - 1) / 2) * width, m, width, yerr=[lo, hi],
                       color=col, label=name, capsize=2)
            ax.set_xticks(xs, [str(c["position"]) for c in sub])
            ax.set_title(f"{label} {config}")
            ax.set_ylim(0, 1.05)
        axes[0][0].set_ylabel("P(prediction matches own object-level answer)")
        axes[0][-1].legend(fontsize=8)
        fig.suptitle(f"{task}: agreement with object-level behaviour (95% bootstrap CI)")
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"match_{task}.png"), dpi=150)
        plt.close(fig)


def main(run_dir: str):
    res = analyse(load(run_dir))
    out_dir = os.path.join(run_dir, "analysis")
    write_tables(res, out_dir)
    plot(res, out_dir)
    print(f"wrote {out_dir}: {len(res['cells'])} cells")


if __name__ == "__main__":
    main(sys.argv[1])
