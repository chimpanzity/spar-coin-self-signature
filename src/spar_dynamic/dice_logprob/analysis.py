"""Offline analysis for DICE_LOGPROB_v1.0 (handoff sections 6.2, 6.3, 7). No model calls.

Input: a gpu_runner run folder (raw_attempts.jsonl, matched_prefix.jsonl, env_<mode>.json).
Writes into the run folder: responses.csv, position_probabilities.csv, probability_coverage.csv, and
analysis/{summary.json, reference_sequences.csv, condition_by_position.csv, divergence.csv,
cross_window.csv, matched_prefix.csv, figures/*.png}.

References: G_k and F_k are the modal full sequences of G and F; the run must show them identical in every
replicate (temperature-0 reliability, not independent draws). F is a hypothetical reference, not ground
truth. Six-face vectors p6 are conditional on the die-face subset; raw face mass is kept alongside.
Near-tie rule: two faces whose six-face probabilities differ by less than the run's measured numerical
precision floor (max |delta p6| between incremental and full-pass scoring) are treated as tied.

Usage: python -m spar_dynamic.dice_logprob.analysis --run <run_dir>
"""

from __future__ import annotations

import argparse
import collections
import csv
import itertools
import json
import math
import os
import re

from spar_dynamic.dice_logprob import extract, prompts

FACES = extract.FACES
COL_G, COL_F, COL_BOTH, COL_NONE = "#2a78d6", "#eb6834", "#1baf7a", "#e4e3df"
INK, INK2 = "#0b0b0b", "#52514e"


def _g(d, f):
    return d[str(f)] if str(f) in d else d[f]


def _csv(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})


def load(run_dir):
    rows = [json.loads(l) for l in open(os.path.join(run_dir, "raw_attempts.jsonl"), encoding="utf-8")]
    mp_path = os.path.join(run_dir, "matched_prefix.jsonl")
    mp = [json.loads(l) for l in open(mp_path, encoding="utf-8")] if os.path.exists(mp_path) else []
    env_file = next(f for f in sorted(os.listdir(run_dir)) if f.startswith("env_"))
    env = json.load(open(os.path.join(run_dir, env_file), encoding="utf-8"))
    return rows, mp, env


def position_table(rows):
    """One row per reported original position per response (handoff 6.2)."""
    out, resp = [], []
    for r in rows:
        n = len(r["target_positions"])
        p = extract.parse(r["raw_choice_content"], n, r["finish_reason"])
        faces = extract.align_faces(r["raw_choice_content"], r["raw_logprobs_content"]) if p["verdict"] == "valid" else []
        resp.append(dict(trial_id=r["trial_id"], condition=r["condition"], replicate=r["replicate"], order_index=r.get("order_index"),
                         content=r["raw_choice_content"], parser_verdict=p["verdict"], finish_reason=r["finish_reason"],
                         prompt_sha256=r["prompt_sha256"], completion_tokens=r["completion_tokens"], latency_ms=r["latency_ms"]))
        for f in faces:
            k = r["target_positions"][f["local_output_index"] - 1]
            row = dict(trial_id=r["trial_id"], condition=r["condition"], replicate=r["replicate"], original_position=k,
                       local_output_index=f["local_output_index"], reported_face=f["reported_face"],
                       token_index=f["token_indices"][0] if f["token_indices"] else None,
                       token_text=f["token_texts"][0] if f["token_texts"] else None,
                       six_face_mass=f["six_face_mass"], candidate_coverage_complete=f["candidate_coverage_complete"],
                       tokenization_ambiguity_flag=f["tokenization_ambiguity_flag"], comparable_flag=f["comparable_flag"],
                       reason_if_not_comparable=f["reason_if_not_comparable"])
            for x in FACES:
                row[f"p_face_{x}_raw"] = f["p_raw"][x] if f["p_raw"] else None
            for x in FACES:
                row[f"p6_{x}"] = f["p6"][x] if f["p6"] else None
            out.append(row)
    return out, resp


def _vec(row):
    return [row[f"p6_{x}"] for x in FACES]


def _margin(p):
    s = sorted(p, reverse=True)
    return s[0] - s[1]


def analyse(run_dir):
    rows, mp, env = load(run_dir)
    pos, resp = position_table(rows)
    _csv(os.path.join(run_dir, "responses.csv"), resp)
    _csv(os.path.join(run_dir, "position_probabilities.csv"), pos)
    cov = collections.defaultdict(lambda: collections.Counter())
    for r in pos:
        c = cov[r["condition"]]
        c["positions"] += 1
        c["complete"] += r["candidate_coverage_complete"]
        c["comparable"] += r["comparable_flag"]
        c["ambiguity"] += r["tokenization_ambiguity_flag"]
    cov_rows = [dict(condition=k, positions=v["positions"], complete=v["complete"], comparable=v["comparable"],
                     ambiguity_flags=v["ambiguity"],
                     min_six_face_mass=min(r["six_face_mass"] for r in pos if r["condition"] == k and r["six_face_mass"] is not None))
                for k, v in cov.items()]
    _csv(os.path.join(run_dir, "probability_coverage.csv"), cov_rows)

    out = os.path.join(run_dir, "analysis")
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    conds = {c["condition"]: c for c in prompts.conditions()}

    # stability per condition: every replicate identical (content and probabilities)?
    stability = {}
    for k in conds:
        rs = [r for r in resp if r["condition"] == k]
        cnt = collections.Counter(r["content"] for r in rs)
        prs = [r for r in pos if r["condition"] == k]
        spread = 0.0
        for kpos in conds[k]["positions"]:
            vs = [_vec(r) for r in prs if r["original_position"] == kpos]
            spread = max([spread] + [abs(a - b) for v in vs for a, b in zip(v, vs[0])])
        stability[k] = dict(n=len(rs), n_valid=sum(r["parser_verdict"] == "valid" for r in rs),
                            modal=cnt.most_common(1)[0][0] if cnt else None, modal_count=cnt.most_common(1)[0][1] if cnt else 0,
                            distinct=len(cnt), max_abs_p6_spread_across_replicates=spread)

    # one representative row per (condition, original position): the modal output's first replicate
    rep = {}
    for k, s in stability.items():
        trial = next(r["trial_id"] for r in resp if r["condition"] == k and r["content"] == s["modal"])
        for r in pos:
            if r["trial_id"] == trial:
                rep[(k, r["original_position"])] = r
    Gk = {k: rep[("G", k)]["reported_face"] for k in range(1, 11)}
    Fk = {k: rep[("F", k)]["reported_face"] for k in range(1, 11)}
    _csv(os.path.join(out, "reference_sequences.csv"),
         [dict(position=k, G=Gk[k], F=Fk[k], match=Gk[k] == Fk[k],
               G_modal_count=stability["G"]["modal_count"], F_modal_count=stability["F"]["modal_count"]) for k in range(1, 11)])

    # precision floor from matched-prefix incremental vs full-pass
    floor = 0.0
    for x, h in itertools.product("GF", "GF"):
        inc = {m["position"]: m for m in mp if m["instruction"] == x and m["history"] == h and m.get("method") == "incremental"}
        fp = {m["position"]: m for m in mp if m["instruction"] == x and m["history"] == h and m.get("method") == "full_pass"}
        for k in inc:
            if k in fp:
                a = extract.p6_from_logp([_g(inc[k]["face_logprobs_exact"]["bare"], f) for f in FACES])
                b = extract.p6_from_logp([_g(fp[k]["face_logprobs_exact"]["bare"], f) for f in FACES])
                floor = max(floor, max(abs(a[f] - b[f]) for f in FACES))

    # G vs F natural trajectories (primary)
    div = []
    for k in range(1, 11):
        pg, pf = _vec(rep[("G", k)]), _vec(rep[("F", k)])
        div.append(dict(position=k, G_face=Gk[k], F_face=Fk[k], match=Gk[k] == Fk[k],
                        pG_of_G=pg[Gk[k] - 1], pG_of_F=pg[Fk[k] - 1], rank_F_under_G=extract.rank_of(Fk[k], dict(zip(FACES, pg))),
                        pF_of_F=pf[Fk[k] - 1], pF_of_G=pf[Gk[k] - 1], rank_G_under_F=extract.rank_of(Gk[k], dict(zip(FACES, pf))),
                        logp_diff_G_selected_minus_F_face_under_G=math.log(pg[Gk[k] - 1]) - math.log(max(pg[Fk[k] - 1], 1e-300)),
                        logp_diff_F_selected_minus_G_face_under_F=math.log(pf[Fk[k] - 1]) - math.log(max(pf[Gk[k] - 1], 1e-300)),
                        margin_G=_margin(pg), margin_F=_margin(pf), near_tie_G=_margin(pg) < floor, near_tie_F=_margin(pf) < floor,
                        JS_bits_G_vs_F=extract.js_bits(pg, pf),
                        six_face_mass_G=rep[("G", k)]["six_face_mass"], six_face_mass_F=rep[("F", k)]["six_face_mass"],
                        **{f"pG6_{x}": pg[x - 1] for x in FACES}, **{f"pF6_{x}": pf[x - 1] for x in FACES}))
    _csv(os.path.join(out, "divergence.csv"), div)

    # every prediction condition at every original position
    cbp = []
    for c in conds:
        if c == "G":
            continue
        for k in conds[c]["positions"]:
            r = rep[(c, k)]
            p = dict(zip(FACES, _vec(r)))
            x = r["reported_face"]
            cbp.append(dict(condition=c, original_position=k, local_output_index=r["local_output_index"], reported_face=x,
                            replicates_identical=stability[c]["distinct"] == 1, G_k=Gk[k], F_k=Fk[k],
                            hit_G=x == Gk[k], hit_F=x == Fk[k], p_of_G_k=p[Gk[k]], rank_G_k=extract.rank_of(Gk[k], p),
                            p_of_F_k=p[Fk[k]], rank_F_k=extract.rank_of(Fk[k], p), margin=_margin(list(p.values())),
                            near_tie=_margin(list(p.values())) < floor,
                            JS_bits_vs_G_k=extract.js_bits(list(p.values()), _vec(rep[("G", k)])),
                            JS_bits_vs_F_k=extract.js_bits(list(p.values()), _vec(rep[("F", k)])) if c != "F" else 0.0,
                            six_face_mass=r["six_face_mass"], **{f"p6_{f}": p[f] for f in FACES}))
    _csv(os.path.join(out, "condition_by_position.csv"), cbp)

    # cross-window agreement at positions reported in several prediction contexts
    cw = []
    for k in range(1, 11):
        ctx = [c for c in conds if c not in ("G",) and k in conds[c]["positions"]]
        for a, b in itertools.combinations(ctx, 2):
            ra, rb = rep[(a, k)], rep[(b, k)]
            cw.append(dict(original_position=k, context_a=a, context_b=b, face_a=ra["reported_face"], face_b=rb["reported_face"],
                           agree=ra["reported_face"] == rb["reported_face"], JS_bits=extract.js_bits(_vec(ra), _vec(rb))))
    _csv(os.path.join(out, "cross_window.csv"), cw)

    # matched prefix (incremental = primary)
    mpr = []
    for h in "GF":
        hist = {m["position"]: m for m in mp if m["history"] == h and m["instruction"] == "G" and m.get("method") == "incremental"}
        for k in sorted(hist):
            pgx = extract.p6_from_logp([_g(hist[k]["face_logprobs_exact"]["bare"], f) for f in FACES])
            m_f = next(m for m in mp if m["history"] == h and m["instruction"] == "F" and m.get("method") == "incremental" and m["position"] == k)
            pfx = extract.p6_from_logp([_g(m_f["face_logprobs_exact"]["bare"], f) for f in FACES])
            hf = hist[k]["history_face"]
            mpr.append(dict(history=h, position=k, history_face=hf, prefix=" ".join(hist[k]["history_sequence"].split()[:k - 1]),
                            argmax_under_G=max(FACES, key=lambda f: pgx[f]), argmax_under_F=max(FACES, key=lambda f: pfx[f]),
                            pG_history_face=pgx[hf], pF_history_face=pfx[hf], JS_bits_G_vs_F=extract.js_bits(list(pgx.values()), list(pfx.values())),
                            margin_G=_margin(list(pgx.values())), margin_F=_margin(list(pfx.values())),
                            **{f"pG6_{f}": pgx[f] for f in FACES}, **{f"pF6_{f}": pfx[f] for f in FACES}))
    _csv(os.path.join(out, "matched_prefix.csv"), mpr)

    def bigrams(s):
        return collections.Counter(zip(s, s[1:]))
    gs, fs = [Gk[k] for k in range(1, 11)], [Fk[k] for k in range(1, 11)]
    summary = dict(run=os.path.basename(run_dir.rstrip("/\\")), env=env, n_responses=len(resp),
                   n_valid=sum(r["parser_verdict"] == "valid" for r in resp), stability=stability,
                   references=dict(G=gs, F=fs, positions_matching=[k for k in range(1, 11) if Gk[k] == Fk[k]]),
                   precision_floor_p6=floor, coverage=cov_rows,
                   bigrams=dict(G=[list(b) for b in bigrams(gs)], F=[list(b) for b in bigrams(fs)],
                                shared=[list(b) for b in set(bigrams(gs)) & set(bigrams(fs))],
                                face_counts_G=dict(collections.Counter(gs)), face_counts_F=dict(collections.Counter(fs))),
                   divergence=div, matched_prefix=mpr)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    figures(out, div, cbp, rep, conds, Gk, Fk, mpr, floor)
    return summary


def figures(out, div, cbp, rep, conds, Gk, Fk, mpr, floor):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
    fd = os.path.join(out, "figures")

    # 1. reference sequences
    fig, ax = plt.subplots(figsize=(7, 1.9))
    for row, (lab, seq, col) in enumerate([("G (direct generation)", Gk, COL_G), ("F (full self-prediction)", Fk, COL_F)]):
        for k in range(1, 11):
            m = Gk[k] == Fk[k]
            ax.add_patch(plt.Rectangle((k - 0.45, 1 - row - 0.4), 0.9, 0.8, color=COL_BOTH if m else col, alpha=0.18 if not m else 0.35, lw=0))
            ax.text(k, 1 - row, str(seq[k]), ha="center", va="center", fontsize=13, color=INK)
        ax.text(0.3, 1 - row, lab, ha="right", va="center", color=INK)
    ax.set_xlim(-2.6, 10.6); ax.set_ylim(-0.6, 1.6); ax.set_xticks(range(1, 11)); ax.set_yticks([])
    ax.spines["left"].set_visible(False); ax.set_xlabel("roll position (aqua = G and F agree)")
    fig.tight_layout(); fig.savefig(os.path.join(fd, "reference_sequences.png"), dpi=160); plt.close(fig)

    # 2. main logprob figure: six-face distributions, G vs F, per position
    fig, axes = plt.subplots(2, 5, figsize=(12, 5), sharey=True)
    for k, ax in zip(range(1, 11), axes.flat):
        d = div[k - 1]
        xs = list(FACES)
        ax.bar([x - 0.2 for x in xs], [d[f"pG6_{x}"] for x in xs], width=0.38, color=COL_G, label="G")
        ax.bar([x + 0.2 for x in xs], [d[f"pF6_{x}"] for x in xs], width=0.38, color=COL_F, label="F")
        ax.set_title(f"position {k}: G={d['G_face']}  F={d['F_face']}  JS={d['JS_bits_G_vs_F']:.2f}", fontsize=8.5, color=INK)
        ax.set_xticks(xs); ax.set_ylim(0, 1.05); ax.grid(axis="y", color="#e4e3df", lw=0.6); ax.set_axisbelow(True)
    axes[0, 0].legend(frameon=False, fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("p among faces 1-6")
    for ax in axes[1]:
        ax.set_xlabel("face")
    fig.suptitle("Six-face distributions in the natural G and F trajectories (normalised over faces 1-6; later positions follow different histories)", fontsize=9.5, color=INK)
    fig.tight_layout(); fig.savefig(os.path.join(fd, "g_vs_f_face_distributions.png"), dpi=160); plt.close(fig)

    # 3. divergence and rank: natural vs matched prefix
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6))
    ks = list(range(1, 11))
    a1.plot(ks, [d["JS_bits_G_vs_F"] for d in div], "o-", color=INK, lw=2, ms=6, label="natural trajectories")
    for h, col, mk in (("G", COL_G, "s"), ("F", COL_F, "^")):
        r = [m for m in mpr if m["history"] == h]
        a1.plot([m["position"] for m in r], [m["JS_bits_G_vs_F"] for m in r], mk + "--", color=col, lw=2, ms=6,
                label=f"matched prefix: {h}'s history")
    a1.set_ylim(-0.03, 1.03); a1.set_xticks(ks); a1.set_xlabel("position"); a1.set_ylabel("JS divergence, G vs F instruction (bits)")
    a1.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    a1.grid(axis="y", color="#e4e3df", lw=0.6)
    a2.plot(ks, [d["rank_G_under_F"] for d in div], "o-", color=COL_F, lw=2, ms=6, label="rank of G's face under F")
    a2.plot(ks, [d["rank_F_under_G"] for d in div], "s-", color=COL_G, lw=2, ms=6, label="rank of F's face under G")
    a2.set_ylim(6.3, 0.7); a2.set_yticks(range(1, 7)); a2.set_xticks(ks); a2.set_xlabel("position"); a2.set_ylabel("rank (1 = top)")
    a2.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    a2.grid(axis="y", color="#e4e3df", lw=0.6)
    fig.set_size_inches(11, 4.2)
    fig.tight_layout(); fig.savefig(os.path.join(fd, "divergence_and_rank.png"), dpi=160); plt.close(fig)

    # 4. serial-position / window heatmap aligned to original positions
    rows = ["F"] + [f"S{k}" for k in range(1, 11)] + [f"W{a}-{b}" for a, b in prompts.WINDOWS]
    labels = ["F (full)", "S(k) (single)"] + [f"W{a}-{b}" for a, b in prompts.WINDOWS]
    grid = {"F (full)": {k: rep[("F", k)]["reported_face"] for k in range(1, 11)},
            "S(k) (single)": {k: rep[(f"S{k}", k)]["reported_face"] for k in range(1, 11)}}
    for a, b in prompts.WINDOWS:
        grid[f"W{a}-{b}"] = {k: rep[(f"W{a}-{b}", k)]["reported_face"] for k in range(a, b + 1)}
    fig, ax = plt.subplots(figsize=(8, 3.2))
    allrows = ["G (truth)"] + labels
    for i, lab in enumerate(allrows):
        for k in range(1, 11):
            if lab == "G (truth)":
                v, col = Gk[k], "#ffffff"
            elif k in grid[lab]:
                v = grid[lab][k]
                col = COL_BOTH if (v == Gk[k] and v == Fk[k]) else COL_G if v == Gk[k] else COL_F if v == Fk[k] else COL_NONE
            else:
                continue
            ax.add_patch(plt.Rectangle((k - 0.46, -i - 0.42), 0.92, 0.84, color=col, lw=0.5, ec="#c3c2b7"))
            ax.text(k, -i, str(v), ha="center", va="center", color=INK, fontsize=10)
    ax.set_yticks([-i for i in range(len(allrows))], allrows); ax.set_xticks(range(1, 11)); ax.set_xlim(0.4, 10.6)
    ax.set_ylim(-len(allrows) + 0.4, 0.6); ax.set_xlabel("original position in the 10-roll sequence")
    ax.legend(handles=[Patch(color=COL_G, label="matches G"), Patch(color=COL_F, label="matches F"),
                       Patch(color=COL_BOTH, label="matches both"), Patch(color=COL_NONE, label="neither")],
              frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4)
    ax.spines["left"].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(fd, "serial_window_heatmap.png"), dpi=160); plt.close(fig)

    # 5. cross-window distributions at multiply represented positions (3-8)
    shared = [k for k in range(1, 11) if sum(k in conds[c]["positions"] for c in conds if c[0] == "W") >= 2]
    fig, axes = plt.subplots(1, len(shared), figsize=(2.3 * len(shared), 3), sharey=True)
    ctx_cols = {"G": COL_G, "F": COL_F, "S": COL_BOTH, "W1-5": "#eda100", "W3-8": "#e87ba4", "W5-10": "#6250d6"}
    for ax, k in zip(axes, shared):
        ctx = [("G", rep[("G", k)]), ("F", rep[("F", k)]), ("S", rep[(f"S{k}", k)])] + \
              [(f"W{a}-{b}", rep[(f"W{a}-{b}", k)]) for a, b in prompts.WINDOWS if a <= k <= b]
        w = 0.8 / len(ctx)
        for j, (name, r) in enumerate(ctx):
            ax.bar([x - 0.4 + w * (j + 0.5) for x in FACES], _vec(r), width=w * 0.9, color=ctx_cols[name], label=name)
        ax.set_title(f"position {k}", fontsize=9, color=INK); ax.set_xticks(list(FACES)); ax.set_xlabel("face")
        ax.grid(axis="y", color="#e4e3df", lw=0.6); ax.set_axisbelow(True)
    axes[0].set_ylabel("p among faces 1-6")
    handles = [Patch(color=c, label=n) for n, c in ctx_cols.items()]
    fig.legend(handles=handles, frameon=False, fontsize=8, ncol=6, loc="lower center")
    fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(os.path.join(fd, "cross_window_distributions.png"), dpi=160); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    s = analyse(ap.parse_args().run)
    print(json.dumps(dict(run=s["run"], n_responses=s["n_responses"], n_valid=s["n_valid"], references=s["references"],
                          precision_floor_p6=round(s["precision_floor_p6"], 4),
                          stability={k: (v["modal_count"], v["n"], v["distinct"]) for k, v in s["stability"].items()}), indent=1))
