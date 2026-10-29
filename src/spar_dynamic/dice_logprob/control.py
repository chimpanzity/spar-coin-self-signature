"""Generic-model framing control for DICE_LOGPROB (amendment v1.1, handoff 2026-10-29). Offline; no GPU.

Conditions: G and F (byte-identical to Experiment 21) and N (F with "another instance of your model"
replaced by "another language model"). Reads a gpu_runner control run folder (control_preflight or
control_main) and the archived Experiment 21 main run for the compatibility check.

  gates    preflight gates (handoff 4.2) -> control_preflight_report.md, control_preflight_summary.json
  analyse  primary position-1 comparison and matched-prefix comparison (handoff 5) ->
           responses.csv, position_probabilities.csv, matched_prefix.csv, first_roll_comparison.csv,
           matched_prefix_comparison.csv, analysis_summary.json, figures/*.png

Position 1 is computed once per instruction (the empty prefix is shared by all histories). Identical greedy
repeats are reproducibility checks of one deterministic path, never independent observations.

Usage: python -m spar_dynamic.dice_logprob.control {gates|analyse} --run <dir> [--archived <exp21 main dir>]
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re

import repo_paths
from spar_dynamic.dice_logprob import analysis as A, extract, prompts

FACES = extract.FACES
REFS = ("G", "F", "N")
ARCHIVED = {"G": [5, 2, 6, 3, 1, 4, 6, 2, 5, 3], "F": [3, 1, 4, 6, 2, 5, 3, 2, 6, 4]}
THINK_SUFFIX = "<think>\n\n</think>\n\n"
TF_TOL_P6 = 1e-4
COL = {"G": "#2a78d6", "F": "#eb6834", "N": "#1baf7a"}


def default_archived() -> str:
    return str(repo_paths.T1_EXP["dice_logprob"] / "main-qwen3-32b-a100")


def _load(run_dir):
    rows = [json.loads(l) for l in open(os.path.join(run_dir, "raw_attempts.jsonl"), encoding="utf-8")]
    mp_path = os.path.join(run_dir, "matched_prefix.jsonl")
    mp = [json.loads(l) for l in open(mp_path, encoding="utf-8")] if os.path.exists(mp_path) else []
    env_file = next(f for f in sorted(os.listdir(run_dir)) if f.startswith("env_"))
    return rows, mp, json.load(open(os.path.join(run_dir, env_file), encoding="utf-8"))


def _face_steps(r):
    return [t for t in r["raw_logprobs_content"] if re.fullmatch(r" ?[1-6]", t["token"])]


def _p6(bare):
    return extract.p6_from_logp([A._g(bare, f) for f in FACES])


def _mass(bare):
    return sum(math.exp(A._g(bare, f)) for f in FACES)


def _margin(p):
    s = sorted(p.values(), reverse=True)
    return s[0] - s[1]


def _js(p, q):
    return extract.js_bits([p[f] for f in FACES], [q[f] for f in FACES])


def modal_records(rows):
    out = {}
    for k in REFS:
        rs = [r for r in rows if r["condition"] == k]
        if rs:
            c = collections.Counter(r["raw_choice_content"] for r in rs)
            m = c.most_common(1)[0][0]
            out[k] = next(r for r in rs if r["raw_choice_content"] == m)
    return out


def precision_floor(mp):
    floor = 0.0
    inc = {(m["instruction"], m["history"], m["position"]): m for m in mp if m.get("method") == "incremental"}
    for m in mp:
        if m.get("method") == "full_pass":
            i = inc.get((m["instruction"], m["history"], m["position"]))
            if i:
                a, b = _p6(i["face_logprobs_exact"]["bare"]), _p6(m["face_logprobs_exact"]["bare"])
                floor = max(floor, max(abs(a[f] - b[f]) for f in FACES))
    return floor


# ------------------------------------------------------------------------------------------- gates --
def gates(run_dir, archived_dir=None):
    rows, mp, env = _load(run_dir)
    archived_dir = archived_dir or default_archived()
    arch_rows = [json.loads(l) for l in open(os.path.join(archived_dir, "raw_attempts.jsonl"), encoding="utf-8")]
    frozen = {c["condition"]: c["prompt_sha256"] for c in prompts.control_conditions()}
    per = []
    for r in rows:
        p = extract.parse(r["raw_choice_content"], 10, r["finish_reason"])
        faces = extract.align_faces(r["raw_choice_content"], r["raw_logprobs_content"]) if p["verdict"] == "valid" else []
        per.append(dict(trial_id=r["trial_id"], condition=r["condition"], verdict=p["verdict"], content=r["raw_choice_content"],
                        complete=sum(f["candidate_coverage_complete"] for f in faces), comparable=sum(f["comparable_flag"] for f in faces),
                        min_mass=min((f["six_face_mass"] for f in faces if f["six_face_mass"]), default=None),
                        think_ok=r["rendered_prompt"].endswith(THINK_SUFFIX) and "<think" not in r["raw_choice_content"].lower(),
                        hash_ok=r["prompt_sha256"] == frozen[r["condition"]]))
    repro, compat = {}, {}
    for k in REFS:
        rs = [r for r in rows if r["condition"] == k]
        c = collections.Counter(r["raw_choice_content"] for r in rs)
        spread = 0.0
        if rs:
            base = [_p6(t["face_logprobs_exact"]["bare"]) for t in _face_steps(rs[0])]
            for r in rs[1:]:
                for a, b in zip(base, [_p6(t["face_logprobs_exact"]["bare"]) for t in _face_steps(r)]):
                    spread = max(spread, max(abs(a[f] - b[f]) for f in FACES))
        repro[k] = dict(n=len(rs), distinct=len(c), modal=c.most_common(1)[0][0] if c else None,
                        modal_count=c.most_common(1)[0][1] if c else 0, max_abs_p6_spread=spread)
    modal = modal_records(rows)
    for k in ("G", "F"):
        arch = next(r for r in arch_rows if r["condition"] == k)
        new_seq = [int(x) for x in modal[k]["raw_choice_content"].split()]
        d = 0.0
        if new_seq == ARCHIVED[k]:
            for a, b in zip(_face_steps(arch), _face_steps(modal[k])):
                pa, pb = _p6(a["face_logprobs_exact"]["bare"]), _p6(b["face_logprobs_exact"]["bare"])
                d = max(d, max(abs(pa[f] - pb[f]) for f in FACES))
        compat[k] = dict(archived=ARCHIVED[k], new=new_seq, sequence_identical=new_seq == ARCHIVED[k],
                         max_abs_p6_diff_vs_archived=d if new_seq == ARCHIVED[k] else None)
    tf = {}
    for k in REFS:
        gen = [_p6(t["face_logprobs_exact"]["bare"]) for t in _face_steps(modal[k])]
        sc = sorted([m for m in mp if m["instruction"] == k and m["history"] == k and m.get("method") == "incremental"],
                    key=lambda m: m["position"])
        diffs = [abs(g[f] - _p6(s["face_logprobs_exact"]["bare"])[f]) for g, s in zip(gen, sc) for f in FACES]
        tf[k] = dict(n_positions=len(sc), max_abs_p6_diff=max(diffs, default=None))
    G = collections.OrderedDict()
    G["prompt_hashes_frozen"] = all(x["hash_ok"] for x in per)
    G["valid_ten_face_outputs"] = all(x["verdict"] == "valid" for x in per)
    G["non_thinking"] = all(x["think_ok"] for x in per)
    G["complete_six_face_vectors_all_positions"] = all(x["complete"] == 10 and x["comparable"] == 10 for x in per)
    G["reproducible_within_condition"] = all(v["distinct"] == 1 for v in repro.values())
    G["G_F_reproduce_experiment_21"] = all(v["sequence_identical"] for v in compat.values())
    G["teacher_forcing_reproduces_generation"] = all(v["n_positions"] == 10 and v["max_abs_p6_diff"] is not None
                                                     and v["max_abs_p6_diff"] < TF_TOL_P6 for v in tf.values())
    s = dict(gates=G, overall="PASS" if all(G.values()) else "FAIL", env=env, responses=per, reproducibility=repro,
             compatibility=compat, teacher_forcing=tf, precision_floor_p6=precision_floor(mp),
             prompt_sha256=frozen)
    with open(os.path.join(run_dir, "control_preflight_summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, default=str)
    with open(os.path.join(run_dir, "control_preflight_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(_gate_report(s, run_dir))
    return s


def _gate_report(s, run_dir):
    e = s["env"]
    L = [f"# Generic-model control: preflight report\n\nRun `{os.path.basename(run_dir.rstrip('/'))}`. Overall: **{s['overall']}**.\n\n",
         f"Serving: `{e['model_id']}` @ `{e['model_commit']}`, {e['dtype']}, {e['gpu']}, driver {e['driver']}, CUDA {e['cuda']}, "
         f"torch {e['torch']}, transformers {e['transformers']}. Greedy, batch 1, `enable_thinking=False`.\n\n"
         "| Gate | Result |\n|---|---|\n"]
    L += [f"| {g} | {'PASS' if v else 'FAIL'} |\n" for g, v in s["gates"].items()]
    L.append("\n## Reproducibility\n\n")
    L += [f"- **{k}**: `{v['modal']}` in {v['modal_count']}/{v['n']}; max p6 spread {v['max_abs_p6_spread']:.2e}\n" for k, v in s["reproducibility"].items()]
    L.append("\n## Compatibility with Experiment 21 (archived main run)\n\n")
    for k, v in s["compatibility"].items():
        d = f"{v['max_abs_p6_diff_vs_archived']:.2e}" if v["max_abs_p6_diff_vs_archived"] is not None else "n/a (sequence differs)"
        L.append(f"- **{k}**: archived `{' '.join(map(str, v['archived']))}`, new `{' '.join(map(str, v['new']))}`; "
                 f"identical: {v['sequence_identical']}; max |Δ p6| vs archived {d}\n")
    L.append("\n## Teacher forcing (incremental) vs own generation\n\n")
    L += [f"- **{k}|{k}**: {v['n_positions']} positions, max |Δ p6| {v['max_abs_p6_diff']:.2e} (gate < {TF_TOL_P6})\n" for k, v in s["teacher_forcing"].items()]
    L.append(f"\nNumerical precision floor (incremental vs full-pass, max |Δ p6|): {s['precision_floor_p6']:.3f}.\n")
    L.append("\n## Prompt hashes\n\n" + "".join(f"- {k}: `{h}`\n" for k, h in s["prompt_sha256"].items()))
    return "".join(L)


# ----------------------------------------------------------------------------------------- analysis --
def analyse(run_dir):
    rows, mp, env = _load(run_dir)
    pos, resp = A.position_table(rows)
    A._csv(os.path.join(run_dir, "responses.csv"), resp)
    A._csv(os.path.join(run_dir, "position_probabilities.csv"), pos)
    modal = modal_records(rows)
    floor = precision_floor(mp)
    seqs = {k: [int(x) for x in modal[k]["raw_choice_content"].split()] for k in REFS}

    # primary: position 1 (from generation; identical to matched-prefix position 1, computed once per instruction)
    p1 = {k: _p6(_face_steps(modal[k])[0]["face_logprobs_exact"]["bare"]) for k in REFS}
    m1 = {k: _mass(_face_steps(modal[k])[0]["face_logprobs_exact"]["bare"]) for k in REFS}
    first = []
    for k in REFS:
        p = p1[k]
        first.append(dict(condition=k, selected_face=seqs[k][0], six_face_mass_raw=m1[k], top2_gap=_margin(p),
                          near_tie=_margin(p) < floor, p_face5=p[5], rank_face5=extract.rank_of(5, p),
                          **{f"p6_{f}": p[f] for f in FACES}))
    pairs = {f"JS_{a}_{b}": _js(p1[a], p1[b]) for a, b in (("F", "N"), ("G", "F"), ("G", "N"))}
    A._csv(os.path.join(run_dir, "first_roll_comparison.csv"), first + [dict(condition=k, JS_bits=v) for k, v in pairs.items()])

    # matched prefix: instruction x history x position (incremental = primary)
    inc = {(m["instruction"], m["history"], m["position"]): m for m in mp if m.get("method") == "incremental"}
    long, comp = [], []
    for h in REFS:
        for k in range(1, 11):
            ps = {}
            for x in REFS:
                m = inc[(x, h, k)]
                bare = m["face_logprobs_exact"]["bare"]
                p = _p6(bare)
                ps[x] = p
                long.append(dict(instruction=x, history_source=h, position=k, prefix=" ".join(map(str, seqs[h][:k - 1])),
                                 history_next_face=seqs[h][k - 1], selected_face=max(FACES, key=lambda f: p[f]),
                                 margin=_margin(p), near_tie=_margin(p) < floor, six_face_mass_raw=_mass(bare),
                                 **{f"logprob_{f}": A._g(bare, f) for f in FACES}, **{f"p6_{f}": p[f] for f in FACES}))
            am = {x: max(FACES, key=lambda f: ps[x][f]) for x in REFS}
            comp.append(dict(history_source=h, position=k, history_next_face=seqs[h][k - 1],
                             top_G=am["G"], top_F=am["F"], top_N=am["N"], F_N_same_top=am["F"] == am["N"],
                             F_follows_history=am["F"] == seqs[h][k - 1], N_follows_history=am["N"] == seqs[h][k - 1],
                             G_follows_history=am["G"] == seqs[h][k - 1],
                             JS_F_N=_js(ps["F"], ps["N"]), JS_G_F=_js(ps["G"], ps["F"]), JS_G_N=_js(ps["G"], ps["N"])))
    A._csv(os.path.join(run_dir, "matched_prefix.csv"), long)
    A._csv(os.path.join(run_dir, "matched_prefix_comparison.csv"), comp)

    later = [c for c in comp if c["position"] >= 2]
    summary = dict(run=os.path.basename(run_dir.rstrip("/\\")), env=env, sequences=seqs, precision_floor_p6=floor,
                   position1=dict(distributions={k: p1[k] for k in REFS}, raw_mass=m1, **pairs,
                                  self_specific_increment_JS_GF_minus_JS_GN=pairs["JS_G_F"] - pairs["JS_G_N"],
                                  first_faces={k: seqs[k][0] for k in REFS}),
                   matched_prefix=dict(
                       by_history={h: dict(max_JS_F_N_pos2_10=max(c["JS_F_N"] for c in later if c["history_source"] == h),
                                           F_N_same_top_pos2_10=sum(c["F_N_same_top"] for c in later if c["history_source"] == h),
                                           F_follows_pos2_10=sum(c["F_follows_history"] for c in later if c["history_source"] == h),
                                           N_follows_pos2_10=sum(c["N_follows_history"] for c in later if c["history_source"] == h),
                                           G_follows_pos2_10=sum(c["G_follows_history"] for c in later if c["history_source"] == h))
                                   for h in REFS}),
                   repeats_note="identical greedy repeats are reproducibility checks of one deterministic path, not independent samples")
    with open(os.path.join(run_dir, "analysis_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    _figures(run_dir, p1, seqs, comp, pairs)
    return summary


def _figures(run_dir, p1, seqs, comp, pairs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.edgecolor": A.INK2, "axes.labelcolor": A.INK, "xtick.color": A.INK2, "ytick.color": A.INK2,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
    fd = os.path.join(run_dir, "figures")
    os.makedirs(fd, exist_ok=True)
    names = {"G": "G: direct generation", "F": "F: another instance of your model", "N": "N: another language model"}

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    for j, k in enumerate(REFS):
        ax.bar([f - 0.27 + 0.27 * j for f in FACES], [p1[k][f] for f in FACES], width=0.25, color=COL[k],
               label=f"{names[k]} (picks {seqs[k][0]})")
    ax.set_xticks(list(FACES)); ax.set_xlabel("face at roll 1"); ax.set_ylabel("p among faces 1-6"); ax.set_ylim(0, 1)
    ax.grid(axis="y", color="#e4e3df", lw=0.6); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=8)
    ax.set_title(f"Roll 1 (empty prefix): JS(F,N) = {pairs['JS_F_N']:.2f}, JS(G,F) = {pairs['JS_G_F']:.2f}, "
                 f"JS(G,N) = {pairs['JS_G_N']:.2f} bits", fontsize=9, color=A.INK)
    fig.tight_layout(); fig.savefig(os.path.join(fd, "first_roll_G_F_N.png"), dpi=160); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4), sharey=True)
    for ax, h in zip(axes, REFS):
        c = sorted([x for x in comp if x["history_source"] == h], key=lambda x: x["position"])
        ks = [x["position"] for x in c]
        ax.plot(ks, [x["JS_F_N"] for x in c], "o-", color=A.INK, lw=2, ms=6, label="F vs N (primary)")
        ax.plot(ks, [x["JS_G_F"] for x in c], "s--", color=COL["F"], lw=1.6, ms=5, label="G vs F")
        ax.plot(ks, [x["JS_G_N"] for x in c], "^--", color=COL["N"], lw=1.6, ms=5, label="G vs N")
        ax.set_title(f"shared prefix = {h}'s sequence", fontsize=9, color=A.INK); ax.set_xticks(range(1, 11))
        ax.set_xlabel("position"); ax.set_ylim(-0.03, 1.03); ax.grid(axis="y", color="#e4e3df", lw=0.6)
    axes[0].set_ylabel("JS divergence between instructions (bits)")
    axes[1].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    fig.tight_layout(); fig.savefig(os.path.join(fd, "matched_prefix_js.png"), dpi=160); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gates", "analyse"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--archived", default=None)
    a = ap.parse_args()
    if a.cmd == "gates":
        s = gates(a.run, a.archived)
        print(json.dumps(dict(overall=s["overall"], gates=s["gates"], compatibility=s["compatibility"],
                              teacher_forcing=s["teacher_forcing"], precision_floor_p6=s["precision_floor_p6"]), indent=1, default=str))
    else:
        s = analyse(a.run)
        print(json.dumps(dict(sequences=s["sequences"], position1={k: v for k, v in s["position1"].items() if k != "distributions"},
                              matched_prefix=s["matched_prefix"]), indent=1, default=str))
