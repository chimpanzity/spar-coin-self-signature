"""Exploratory offline reanalysis of Experiment 33: does "angry" help Qwen on unused faces? No model calls.
Run from the repo root:  PYTHONPATH=src python track1_self_prediction/34_2026-11-25_dice_unused_faces/analyse.py
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spar_dynamic.dice_scaffolding import config as C
from spar_dynamic.dice_scaffolding import design as D
from spar_dynamic.dice_scaffolding.analysis import Data, bank, js, unused_faces

OUT = Path(__file__).resolve().parent
NEU, ANG = D.cond_key(C.NEUTRAL), D.cond_key(D.subject_word("angry"))
B, SEED = 10_000, 241125
data = Data(phases=("core", "extensions"))


def fav(v, u):
    """Unique favourite unused face of a target vector, or None on a tie."""
    p = [v[f - 1] for f in u]
    best = [f for f, x in zip(u, p) if x == max(p)]
    return best[0] if len(best) == 1 else None


def cond(v, u):
    s = sum(v[f - 1] for f in u)
    return None if s <= 0 else np.array([v[f - 1] / s for f in u])


def row(r):
    h, u = r["history"], unused_faces(r["history"])
    vec = {"neutral": data.F[("qwen", NEU, h)], "angry": data.F[("qwen", ANG, h)],
           "qwen": data.GT[("qwen", h)], "mistral": data.GT[("mistral", h)]}
    M = {k: float(sum(v[f - 1] for f in u)) for k, v in vec.items()}
    c = {k: cond(v, u) for k, v in vec.items()}
    o = dict(family=r["family"], roll=r["k"], history=h, unused=" ".join(map(str, u)), mass_neutral=M["neutral"],
             mass_angry=M["angry"], d_mass_pp=100 * (M["angry"] - M["neutral"]))
    for t in C.MODELS:
        o[f"mass_target_{t}"] = M[t]
        o[f"abs_err_reduction_pp_{t}"] = 100 * (abs(M["neutral"] - M[t]) - abs(M["angry"] - M[t]))
        o[f"full_gain_{t}"] = js(vec["neutral"], vec[t]) - js(vec["angry"], vec[t])
        ok = all(c[k] is not None for k in ("neutral", "angry", t))
        o[f"cond_D_neutral_{t}"] = js(c["neutral"], c[t]) if ok else ""
        o[f"cond_D_angry_{t}"] = js(c["angry"], c[t]) if ok else ""
        o[f"cond_D_uniform_{t}"] = js(np.full(len(u), 1 / len(u)), c[t]) if c[t] is not None else ""
        o[f"cond_gain_{t}"] = o[f"cond_D_neutral_{t}"] - o[f"cond_D_angry_{t}"] if ok else ""
        o[f"fav_{t}"] = fav(vec[t], u)
        s = sorted(c[t])[::-1]
        o[f"fav_margin_{t}"] = float(s[0] - s[1]) if len(s) > 1 else ""
    both = "" not in (o["cond_gain_qwen"], o["cond_gain_mistral"])
    o["cond_gain_diff"] = o["cond_gain_qwen"] - o["cond_gain_mistral"] if both else ""
    q, m = o["fav_qwen"], o["fav_mistral"]
    o["disagree"] = bool(len(u) > 1 and q is not None and m is not None and q != m)
    for name, f in (("qwenfav", q), ("mistralfav", m)):
        for k in ("neutral", "angry"):
            o[f"p_{k}_{name}"] = float(c[k][u.index(f)]) if f is not None else ""
        o[f"d_{name}_pp"] = 100 * (o[f"p_angry_{name}"] - o[f"p_neutral_{name}"]) if f is not None else ""
    o["d_qwenfav_minus_mistralfav_pp"] = o["d_qwenfav_pp"] - o["d_mistralfav_pp"] if o["disagree"] else ""
    return o


def est(rows, key):
    """Family means, then mean over contributing families; percentile bootstrap over whole families (same draw for every key)."""
    fam = {}
    for r in rows:
        if r[key] != "":
            fam.setdefault(r["family"], []).append(r[key])
    x = np.array([np.mean(v) for _, v in sorted(fam.items())])
    e = dict(mean=float(x.mean()) if len(x) else None, families=len(x), histories=sum(map(len, fam.values())),
             families_positive=int((x > 0).sum()), by_family={f: float(np.mean(v)) for f, v in sorted(fam.items())}, ci95=None)
    if len(x) > 1:
        i = np.random.Generator(np.random.PCG64(SEED)).integers(0, len(x), size=(B, len(x)))
        e["ci95"] = [float(v) for v in np.percentile(x[i].mean(1), [2.5, 97.5])]
        loo = [np.delete(x, j).mean() for j in range(len(x))]
        e["leave_one_family_out"] = [float(min(loo)), float(max(loo))]
    return e


allrows = [row(r) for r in bank("confirmation")]
chk = {t: est(allrows, f"full_gain_{t}")["mean"] for t in C.MODELS}
assert len(allrows) == 84 and round(chk["qwen"], 3) == 0.088 and round(chk["mistral"], 3) == 0.086, chk
prim, r6 = [r for r in allrows if r["roll"] in (4, 5)], [r for r in allrows if r["roll"] == 6]
assert len(prim) == 24 and len({r["family"] for r in prim}) == 12
dis = [r for r in prim if r["disagree"]]

K_MASS = ["mass_neutral", "mass_angry", "d_mass_pp", "mass_target_qwen", "mass_target_mistral", "abs_err_reduction_pp_qwen",
          "abs_err_reduction_pp_mistral"]
K_COND = ["cond_D_neutral_qwen", "cond_D_angry_qwen", "cond_D_uniform_qwen", "cond_gain_qwen", "cond_D_neutral_mistral",
          "cond_D_angry_mistral", "cond_D_uniform_mistral", "cond_gain_mistral", "cond_gain_diff", "full_gain_qwen", "full_gain_mistral"]
K_FAV = ["p_neutral_qwenfav", "p_angry_qwenfav", "d_qwenfav_pp", "p_neutral_mistralfav", "p_angry_mistralfav", "d_mistralfav_pp",
         "d_qwenfav_minus_mistralfav_pp"]
S = dict(check_full_gain_84=chk, bootstrap=dict(B=B, seed=SEED),
         n=dict(primary=len(prim), disagreement=len(dis), disagreement_families=len({r["family"] for r in dis}),
                target_ties=sum(r["fav_qwen"] is None or r["fav_mistral"] is None for r in prim),
                omitted_zero_denominator={k: sum(r[k] == "" for r in prim) for k in ("cond_gain_qwen", "cond_gain_mistral")}))
for name, rs, keys in (("rolls_4_5", prim, K_MASS + K_COND), ("roll_4", [r for r in prim if r["roll"] == 4], K_MASS + K_COND),
                       ("roll_5", [r for r in prim if r["roll"] == 5], K_MASS + K_COND), ("roll_6", r6, K_MASS),
                       ("disagreement", dis, K_MASS + K_COND + K_FAV)):
    S[name] = {k: est(rs, k) for k in keys}

w = "5 2 6"
ex = {"available": all(k in data.F for k in (("qwen", NEU, w), ("qwen", ANG, w))) and all((t, w) in data.GT for t in C.MODELS)}
if ex["available"]:
    u = unused_faces(w)
    vs = (("Qwen forecast, a shape", data.F[("qwen", NEU, w)]), ("Qwen forecast, angry", data.F[("qwen", ANG, w)]),
          ("Qwen direct", data.GT[("qwen", w)]), ("Mistral direct", data.GT[("mistral", w)]))
    tot = lambda v: float(sum(v[f - 1] for f in u))
    ex.update(unused=u, rows={lab: {**{str(f): float(v[f - 1]) for f in u}, "unused_total": tot(v), "share_of_3": float(v[2] / tot(v))}
                              for lab, v in vs},
              favourites={t: fav(data.GT[(t, w)], u) for t in C.MODELS},
              in_confirmation_bank=[r["family"] for r in allrows if r["history"] == w])
S["example_5_2_6"] = ex
with open(OUT / "summary.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(S, f, indent=1)
with open(OUT / "per_history.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=["bank"] + list(prim[0]), lineterminator="\n")
    wr.writeheader()
    for r in prim + r6:
        wr.writerow({"bank": "primary" if r["roll"] != 6 else "roll 6 check", **r})
for n in ("rolls_4_5", "roll_4", "roll_5", "roll_6", "disagreement"):
    print("##", n)
    for k, e in S[n].items():
        ci = np.round(e["ci95"], 4).tolist() if e["ci95"] else None
        print(f"  {k:30s} {e['mean']:+.4f} {ci} fam {e['families']} hist {e['histories']} pos {e['families_positive']} "
              f"loo {np.round(e.get('leave_one_family_out', []), 4).tolist()}")
print(S["n"], chk)
print(json.dumps(ex, indent=1))
for r in dis:
    print(r["family"], r["roll"], r["history"], "unused", r["unused"], "fav", r["fav_qwen"], r["fav_mistral"],
          *[f"{k}={r[k]:+.3f}" for k in ("fav_margin_qwen", "fav_margin_mistral", "cond_gain_qwen", "cond_gain_mistral",
                                         "p_neutral_qwenfav", "p_angry_qwenfav", "p_neutral_mistralfav", "p_angry_mistralfav")])
