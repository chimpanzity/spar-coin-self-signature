"""Offline analysis and checks for Experiment 35 (descriptive, two fixed sequences; no p-values, no intervals)."""

from __future__ import annotations

import csv
import json
import math
from statistics import mean

from spar_dynamic.dice_31_32 import config as C32
from spar_dynamic.dice_31_32.gpu import canonical_sha
from spar_dynamic.roll7_scaffolding import design as D
from spar_dynamic.roll7_scaffolding.gpu import read_jsonl

F = [str(f) for f in D.FACES]
ORDER = list(D.ENDINGS)


def probs(fl):
    m = sum(math.exp(fl[f]) for f in F)
    return m, {f: math.exp(fl[f]) / m for f in F}


def classify(r):
    if not r["final_valid"]:
        return "invalid"
    f = int(r["final_text"])
    return "true seventh" if f == r["true7"] else "true sixth" if f == r["true6"] else "another face"


def readout(r):
    """One record -> flat row. Distribution fields are None when there is no answer boundary."""
    o = {k: r.get(k) for k in ("cell_id", "predictor", "mode", "source_model", "own_source", "condition", "prefix5", "true6", "true7", "replicate",
                               "prompt_sha256", "final_text", "final_valid", "finish_reason", "completion_tokens", "truncated", "status",
                               "think_opened", "think_closed", "whitespace_is_template")}
    if o["mode"] == "standard":
        o["final_text"] = (r["final_text"] or "")[:200]
    o["outcome"] = classify(r)
    a = r["answer"]
    o["boundary"] = "first assistant token" if o["mode"] == "standard" else "none" if a is None else \
        "first non-whitespace token after </think>" + ("" if r["whitespace_is_template"] else " (non-template whitespace)")
    keys = ["argmax_token", "digit_mass", "p_true7", "p_true6", "raw_p_true7", "logp7_minus_logp6", "rank_true7", "top_face", "entropy_bits",
            *[f"p{f}" for f in F], *[f"logp{f}" for f in F]]
    o.update({k: None for k in keys})
    if a is not None:
        fl = a["face_logprobs"]
        m, p = probs(fl)
        s7, s6 = str(r["true7"]), str(r["true6"])
        o.update(argmax_token=a["argmax_token"], digit_mass=m, p_true7=p[s7], p_true6=p[s6], raw_p_true7=math.exp(fl[s7]),
                 logp7_minus_logp6=fl[s7] - fl[s6], rank_true7=1 + sum(p[f] > p[s7] for f in F), top_face=int(max(F, key=lambda f: p[f])),
                 entropy_bits=a["entropy_bits"], **{f"p{f}": p[f] for f in F}, **{f"logp{f}": fl[f] for f in F})
    return o


def same_rep(a, b):
    """Generated ids and the answer distribution are bit-identical."""
    return a["generated_ids"] == b["generated_ids"] and (a["answer"] or {}).get("face_logprobs") == (b["answer"] or {}).get("face_logprobs")


def load(root=None):
    root = root or D.EXP
    raw = [r for m in D.MODELS for n in ("cells_standard", "cells_thinking") if (root / "raw" / m / f"{n}.jsonl").exists()
           for r in read_jsonl(root / "raw" / m / f"{n}.jsonl")]
    sp = root / "raw" / "qwen" / "cells_thinking_supplementary.jsonl"
    return raw, read_jsonl(sp) if sp.exists() else []


def contrasts(rows):
    """Each variant minus B within predictor x source x mode; and Qwen thinking minus standard within ending."""
    by = {r["cell_id"]: r for r in rows}
    K = ("p_true7", "p_true6", "logp7_minus_logp6", "digit_mass")

    def diff(a, b, label):
        return dict(contrast=label, predictor=a["predictor"], source_model=a["source_model"], mode=a["mode"], condition=a["condition"],
                    outcome=a["outcome"], outcome_ref=b["outcome"], rank=a["rank_true7"], rank_ref=b["rank_true7"],
                    **{f"d_{k}": None if a[k] is None or b[k] is None else a[k] - b[k] for k in K})
    out = [diff(r, by[r["cell_id"].rsplit("-", 1)[0] + "-B"], "variant - B") for r in rows if r["condition"] != "B"]
    out += [diff(r, by[r["cell_id"].replace("/thinking", "/standard")], "thinking - standard") for r in rows if r["mode"] == "thinking"]
    return out


def recurrence(cons):
    out = []
    for mode in ("standard", "thinking"):
        for c in ORDER[1:]:
            q = [x for x in cons if x["contrast"] == "variant - B" and x["condition"] == c and x["mode"] == mode]
            d = [x["d_p_true7"] for x in q if x["d_p_true7"] is not None]
            mg = [x["d_logp7_minus_logp6"] for x in q if x["d_logp7_minus_logp6"] is not None]
            if q:
                out.append(dict(mode=mode, condition=c, cells=len(q), scored=len(d), p7_up=sum(x > 0 for x in d), mean_d_p7=mean(d) if d else None,
                                min_d_p7=min(d) if d else None, max_d_p7=max(d) if d else None, margin_up=sum(x > 0 for x in mg),
                                n_true7=sum(x["outcome"] == "true seventh" for x in q), n_true6=sum(x["outcome"] == "true sixth" for x in q),
                                n_other=sum(x["outcome"] == "another face" for x in q), n_invalid=sum(x["outcome"] == "invalid" for x in q)))
    return out


def checks(raw, sup, rows):
    root = D.EXP
    env = {m: json.load(open(root / "raw" / m / "env.json", encoding="utf-8")) for m in D.MODELS}
    design = {c["cell_id"]: c for c in D.cells()}
    pair = {}
    for r in raw:
        pair.setdefault(r["cell_id"], []).append(r)
    res = {
        "36 cells x 2 replicates": set(pair) == set(design) and all(sorted(r["replicate"] for r in v) == [1, 2] for v in pair.values()) and len(raw) == 72,
        "prompt bytes and hashes equal the frozen design": all(r["prompt"] == design[r["cell_id"]]["prompt"] and
                                                               r["prompt_sha256"] == design[r["cell_id"]]["prompt_sha256"] for r in raw + sup),
        "baseline hashes equal Experiment 32 prompts_frozen.md": all(
            f"### {s}-G-B (sha256 `{design[f'qwen/standard<-{s}-B']['prompt_sha256']}`)" in (C32.EXP32 / "prompts_frozen.md").read_text(encoding="utf-8")
            for s, _ in D.SOURCES),
        "archival G/F replay (Experiment 28)": all(e["archival_check"]["ok"] for e in env.values()),
        "Experiment 32 B replay": all(e["b_check"]["ok"] for e in env.values()),
        "Experiment 32 B replay bit-identical": all(v["bit_identical"] for e in env.values() for v in e["b_check"]["per_source"].values()),
        "pinned revisions": all(r["model_commit"] == D.MODEL[r["predictor"]]["revision"] for r in raw + sup),
        "replicates bit-identical": all(same_rep(*v) for v in pair.values()),
        "standard answer scores equal the generation step": all(r["answer_matches_generation"] for r in raw if r["mode"] == "standard"),
        "standard boundary: rendered prompt ends with the empty think block (Qwen)": all(
            r["rendered_prompt"].endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n") for r in raw if r["predictor"] == "qwen" and r["mode"] == "standard"),
        "thinking prompt ends at the assistant header": all(r["rendered_prompt"].endswith("<|im_start|>assistant\n") for r in raw + sup if r["mode"] == "thinking"),
        "thinking boundary follows </think> and whitespace only": all(
            r["generated_ids"][r["boundary"] - len(r["whitespace_ids"]) - 1] == D.THINK_CLOSE and
            r["answer"]["argmax_token_id"] == r["generated_ids"][r["boundary"]] for r in raw + sup if r["mode"] == "thinking" and r["answer"]),
        "thinking without a boundary has no scores": all(r["answer"] is None for r in raw + sup if r["mode"] == "thinking" and r["boundary"] is None),
        "supplementary runs extend the primary greedy path": all(r["extends_primary"] for r in sup),
        "face token ids": all({int(k): v for k, v in r["answer"]["face_token_ids"].items()} == dict(D.MODEL[r["predictor"]]["face_ids"])
                              for r in raw + sup if r["answer"]),
        "six-face probabilities sum to one, mass <= 1": all(abs(sum(r[f"p{f}"] for f in F) - 1) < 1e-9 and r["digit_mass"] <= 1 + 1e-5
                                                            for r in rows if r["p_true7"] is not None),
        "raw file hashes": all(canonical_sha(root / "raw" / m / n) == h for m, e in env.items() for n, h in e["files"].items()),
    }
    floor = max(abs(math.exp(r["answer"]["face_logprobs"][f]) - math.exp(r["answer_full_pass"]["face_logprobs"][f]))
                for r in raw if r.get("answer_full_pass") for f in F)
    return res, dict(full_pass_floor_max_dp=floor, b_replay={m: e["b_check"]["per_source"] for m, e in env.items()},
                     replicate_mismatches=[k for k, v in pair.items() if not same_rep(*v)])


def wcsv(path, rows):
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def anchors():
    out = []
    for r in csv.DictReader(open(C32.EXP32 / "results" / "cells_12.csv", encoding="utf-8")):
        out.append(dict(predictor=r["predictor"], source_model=r["source_model"], condition32=r["condition"], free_text=r["free_text"],
                        p_true7=float(r["p_true7"]), rank_true7=int(r["rank_true7"]), top7=int(r["top7"]), digit_mass7=float(r["digit_mass7"])))
    return out


def figure(rows, sup_rows, anc):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, mut, blue, orange = "#222222", "#777777", "#2a78d6", "#c8571b"
    fig, axes = plt.subplots(3, 2, figsize=(9.2, 9.0), sharex=True, sharey=True)
    supd = {r["cell_id"]: r for r in sup_rows}
    for ax, (p, mode) in zip(axes, (("qwen", "standard"), ("qwen", "thinking"), ("mistral", "standard"))):
        for a, (s, _) in zip(ax, D.SOURCES):
            for n, c in enumerate(ORDER):
                r = next(x for x in rows if x["cell_id"] == f"{p}/{mode}<-{s}-{c}")
                lab = {"true seventh": "7th", "true sixth": "6th", "another face": "other", "invalid": "invalid"}[r["outcome"]]
                hollow = False
                if r["p_true7"] is None and r["cell_id"] in supd:
                    r, hollow = supd[r["cell_id"]], True
                    lab = "long: " + {"true seventh": "7th", "true sixth": "6th", "another face": "other", "invalid": "invalid"}[r["outcome"]]
                if r["p_true7"] is None:
                    a.text(n, 0.03, "no answer", ha="center", fontsize=7.5, color=mut, rotation=90, va="bottom")
                    continue
                for d, k, col in ((-0.17, "p_true7", blue), (0.17, "p_true6", orange)):
                    a.bar(n + d, r[k], 0.3, color="white" if hollow else col, edgecolor=col, linewidth=1.2)
                a.text(n, min(max(r["p_true7"], r["p_true6"]) + 0.02, 1.02), lab, ha="center", fontsize=7.5, color=ink)
            if mode == "standard":
                for k, ls in (("A", "--"), ("C", ":")):
                    v = next(x["p_true7"] for x in anc if (x["predictor"], x["source_model"], x["condition32"]) == (p, s, k))
                    a.axhline(v, color=mut, lw=1, ls=ls)
                    a.text(5.55, v, f"{k}", fontsize=8, color=mut, va="center")
            a.set_title(f"{p.capitalize()}, {mode}; {s.capitalize()} sequence", fontsize=9.5, color=ink, loc="left")
            a.set_ylim(0, 1.12)
            a.set_xlim(-0.6, 5.8)
            a.set_xticks(range(6), ORDER, fontsize=8.5)
            a.tick_params(labelbottom=True)
            for sp in ("top", "right"):
                a.spines[sp].set_visible(False)
    for a in axes[:, 0]:
        a.set_ylabel("Probability at final answer", fontsize=8.5)
    fig.legend([plt.Rectangle((0, 0), 1, 1, color=blue), plt.Rectangle((0, 0), 1, 1, color=orange)],
               ["true roll 7", "true roll 6 (missing)"], loc="upper center", ncol=2, frameon=False, fontsize=9)
    fig.text(0.5, 0.004, "Six-face-normalised. Labels: free answer. Dashed/dotted: Exp. 32 p(true 7) when the sixth was emitted (A) or supplied (C). "
             "Hollow: longer-budget supplementary run.", ha="center", fontsize=7.5, color=mut)
    fig.tight_layout(rect=(0, 0.015, 1, 0.965))
    (D.EXP / "figures").mkdir(exist_ok=True)
    fig.savefig(D.EXP / "figures" / "fig35_roll7_scaffolding.png", dpi=170)
    fig.savefig(D.EXP / "figures" / "fig35_roll7_scaffolding.pdf")


def main():
    raw, sup = load()
    allrows = [readout(r) for r in raw]
    rows = [r for r in allrows if r["replicate"] == 1]
    sup_rows = [readout(r) for r in sup]
    chk, info = checks(raw, sup, allrows + sup_rows)
    out = D.EXP / "results"
    out.mkdir(exist_ok=True)
    pair = {}
    for r in raw:
        pair.setdefault(r["cell_id"], []).append(r)
    for r in rows:
        r["replicates_identical"] = same_rep(*pair[r["cell_id"]])
    cons, anc = contrasts(rows), anchors()
    rec = recurrence(cons)
    wcsv(out / "cells_36.csv", rows)
    wcsv(out / "supplementary_long_budget.csv", sup_rows)
    wcsv(out / "contrasts.csv", cons)
    wcsv(out / "recurrence.csv", rec)
    wcsv(out / "exp32_anchors.csv", anc)
    json.dump(dict(checks=chk, info=info, recurrence=rec), open(out / "summary.json", "w", encoding="utf-8", newline="\n"), indent=1)
    (out / "CHECKS.md").write_text("# Experiment 35 checks\n\n" + "".join(f"- {'PASS' if v else 'FAIL'}: {k}\n" for k, v in chk.items())
                                   + f"\nFull-pass floor (standard cells): max |dp| = {info['full_pass_floor_max_dp']:.4f}\n", encoding="utf-8", newline="\n")
    figure(rows, sup_rows, anc)
    for k, v in chk.items():
        print("PASS" if v else "FAIL", k)
    print(info)
    for r in rows + [dict(r, cell_id="SUPP " + r["cell_id"]) for r in sup_rows]:
        g = lambda k: "  -  " if r[k] is None else f"{r[k]:.3f}"
        print(f"{r['cell_id']:38s} {r['outcome']:13s} {str(r['final_text'])[:22]!r:26s} tok {r['completion_tokens']:4d} mass {g('digit_mass')} "
              f"p7 {g('p_true7')} p6 {g('p_true6')} margin {g('logp7_minus_logp6')} rank {r['rank_true7']} argmax {r['argmax_token']!r} {r['status']}")
    for r in rec:
        print(r)
