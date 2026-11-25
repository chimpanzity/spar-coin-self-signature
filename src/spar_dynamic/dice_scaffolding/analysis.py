"""Prespecified analysis for Experiment 33. Distances are Jensen-Shannon divergences in bits between six-face-normalised vectors.

Core objects: `F[(p, cond, h)]` forecast vectors, `GT[(t, h)]` direct references, `A[p][word]` independent associations. Everything
below the loader works on these dictionaries, so the synthetic fixture in the tests exercises the same code as the real data.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np

from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl
from spar_dynamic.dice_scaffolding import config as C
from spar_dynamic.dice_scaffolding import design as D

OTHER = {"qwen": "mistral", "mistral": "qwen"}
CK = D.cond_key
NEU = CK(C.NEUTRAL)


def js(q, g) -> float:
    q, g = np.asarray(q, float), np.asarray(g, float)
    m = (q + g) / 2
    def kl(a):
        z = a > 0
        return float((a[z] * np.log2(a[z] / m[z])).sum())
    return max(0.0, (kl(q) + kl(g)) / 2)


# ---------- loading ----------

class Data:
    def __init__(self, root=None, phases=("core",)):
        root = Path(root or C.EXP)
        self.root, self.F, self.GT, self.mass, self.cued, self.gmass, self.top = root, {}, {}, {}, {}, {}, {}
        self.A, self.envs, self.facts, self.gens, self.frow, self.grow, self.assoc_rows = {}, {}, [], {}, {}, {}, {}
        self.tokens = {}
        for m in C.MODELS:
            raw = root / "raw" / m
            frows, grows = {}, []
            for ph in phases:
                for r in read_jsonl(raw / f"forecasts_{ph}.jsonl"):
                    frows[r["prompt_sha256"]] = r
                grows += read_jsonl(raw / f"direct_{ph}.jsonl")
            for d in D.design():
                if d["phase"] in phases:
                    r = frows.get(d["prompt_sha256"])
                    if r is None:
                        raise SystemExit(f"incomplete block: {m} {d['design_id']}")
                    key = (m, d["cond"], d["history"])
                    self.F[key], self.mass[key], self.frow[key] = np.array(r["q"]), r["mass"], r["row_id"]
                    self.top[key], self.tokens[key] = r["argmax_token"], (r["n_chars"], r["n_prompt_tokens"])
            for r in grows:
                if r["assay"] == "direct_G":
                    self.GT[(m, r["history"])], self.gmass[(m, r["history"])] = np.array(r["q"]), r["mass"]
                    self.grow[(m, r["history"])] = r["row_id"]
                else:
                    self.cued[(m, r["subject"], r["history"])] = np.array(r["q"])
            self.assoc_rows[m] = read_jsonl(raw / "associations.jsonl")
            sc = json.load(open(raw / "association_scores.json", encoding="utf-8"))
            self.A[m] = {w: v["A"] for w, v in sc["self_other"].items()}
            setattr(self, f"scores_{m}", sc)
            if "extensions" in phases:
                self.facts += read_jsonl(raw / "facts.jsonl")
                self.gens[m] = read_jsonl(raw / "generations.jsonl")


# ---------- elementary quantities ----------

def dist(F, GT, p, cond, t, h):
    return js(F[(p, cond, h)], GT[(t, h)])


def gain(F, GT, p, t, cond, h, neutral=NEU):
    return dist(F, GT, p, neutral, t, h) - dist(F, GT, p, cond, t, h)


def selective(F, GT, p, cond, h, neutral=NEU):
    return gain(F, GT, p, p, cond, h, neutral) - gain(F, GT, p, OTHER[p], cond, h, neutral)


def by_family(rows) -> dict:
    out = {}
    for r in rows:
        out.setdefault(r["family"], []).append(r["history"])
    return out


def primary_cells(F, GT, A, pairs, fams, wordcond=lambda w: CK(D.subject_word(w)), neutral=NEU, keep=None) -> dict:
    """Per checkpoint: arrays [pair, family] of the directional association test T and own improvement O (bits), family = mean over its
    histories. `keep(p, cond_list, h)` optionally restricts histories (mass sensitivity); empty cells are nan."""
    res = {}
    for p in C.MODELS:
        T = np.full((len(pairs), len(fams)), np.nan)
        O, dS = T.copy(), T.copy()
        n = np.zeros_like(T)
        for i, (l, r) in enumerate(pairs):
            a = A[p][l] - A[p][r]
            cl, cr = wordcond(l), wordcond(r)
            for j, hs in enumerate(fams.values()):
                use = [h for h in hs if keep is None or keep(p, [neutral, cl, cr], h)]
                n[i, j] = len(use)
                if not use:
                    continue
                d = np.mean([selective(F, GT, p, cl, h, neutral) - selective(F, GT, p, cr, h, neutral) for h in use])
                gl = np.mean([gain(F, GT, p, p, cl, h, neutral) for h in use])
                gr = np.mean([gain(F, GT, p, p, cr, h, neutral) for h in use])
                dS[i, j], T[i, j] = d, np.sign(a) * d
                O[i, j] = gl if a > 0 else gr if a < 0 else (gl + gr) / 2
        res[p] = dict(T=T, O=O, dS=dS, n=n, a=[A[p][l] - A[p][r] for l, r in pairs])
    return res


def boot_summary(cells, seed=C.BOOT_SEED, B=C.BOOT_B) -> dict:
    """Two-way percentile bootstrap over families and pairs with shared indices; leave-one-out ranges."""
    M = {(p, e): cells[p][e] for p in C.MODELS for e in ("T", "O")}
    for e in ("T", "O"):
        M[("joint", e)] = (M[("qwen", e)] + M[("mistral", e)]) / 2
    np_, nf = M[("qwen", "T")].shape
    rng = np.random.Generator(np.random.PCG64(seed))
    fi = rng.integers(0, nf, size=(B, nf))
    pi = rng.integers(0, np_, size=(B, np_))
    out = {}
    for (p, e), X in M.items():
        if np.isnan(X).any():
            out[f"{p}_{e}"] = dict(mean=float(np.nanmean(X)), incomplete=True, n_missing=int(np.isnan(X).sum()))
            continue
        b = np.array([X[np.ix_(pi[k], fi[k])].mean() for k in range(B)])
        lop = [float(np.delete(X, i, 0).mean()) for i in range(np_)]
        lof = [float(np.delete(X, j, 1).mean()) for j in range(nf)]
        out[f"{p}_{e}"] = dict(mean=float(X.mean()), ci95=[float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
                               leave_one_pair_out=[min(lop), max(lop)], leave_one_family_out=[min(lof), max(lof)],
                               pairs_positive=int((X.mean(1) > 0).sum()), n_pairs=np_, n_families=nf)
    return out


def classify(summary, name) -> str:
    """Descriptive label used in tests and the report: is selective gain accompanied by absolute own improvement?"""
    t, o = summary[f"{name}_T"]["mean"], summary[f"{name}_O"]["mean"]
    tol = 1e-9
    if t > tol and o > tol:
        return "selective_with_own_improvement"
    if t > tol:
        return "selective_without_own_improvement"
    return "no_positive_selectivity"


# ---------- associations ----------

def association_table(data: Data) -> list:
    out = []
    for p in C.MODELS:
        sc = getattr(data, f"scores_{p}")
        rows = data.assoc_rows[p]
        for split, pairs in (("development", C.DEV_PAIRS), ("confirmation", C.CONF_PAIRS)):
            for l, r in pairs:
                for kind in ("self_other", "anonymous"):
                    L, R = sc[kind][l], sc[kind][r]
                    rr = [x for x in rows if x["kind"] == kind and x["word"] in (l, r)]
                    out.append(dict(checkpoint=p, kind=kind, split=split, left=l, right=r, A_left=L["A"], A_right=R["A"], a=L["A"] - R["A"],
                                    a_wording1=L["by_wording"][0] - R["by_wording"][0], a_wording2=L["by_wording"][1] - R["by_wording"][1],
                                    wording_sign_agree=(L["by_wording"][0] - R["by_wording"][0]) * (L["by_wording"][1] - R["by_wording"][1]) > 0,
                                    min_letter_mass=min(x["mass"] for x in rr), max_variant_mass=max(x["variant_mass"] for x in rr)))
    return out


def association_effects(data: Data) -> list:
    """Label (A vs B) and presentation-order effects on log p(first agent) - log p(second agent)."""
    out = []
    for p in C.MODELS:
        for kind in ("self_other", "anonymous"):
            rr = [x for x in data.assoc_rows[p] if x["kind"] == kind]
            d = [x["l"][x["letters"].index(x["first_letter"])] - x["l"][x["letters"].index(x["second_letter"])] for x in rr]
            m = lambda f: float(np.mean([v for v, x in zip(d, rr) if f(x)]))
            words = {}
            for v, x in zip(d, rr):
                words.setdefault(x["word"], []).append(v)
            out.append(dict(checkpoint=p, kind=kind, mean_first_minus_second=float(np.mean(d)), label_effect_A_minus_B=m(lambda x: x["label"] == 0) - m(lambda x: x["label"] == 1),
                            order_effect_first_minus_last=m(lambda x: x["order"] == 0) - m(lambda x: x["order"] == 1),
                            word_sd=float(np.std([np.mean(v) for v in words.values()], ddof=1)),
                            mean_letter_mass=float(np.mean([x["mass"] for x in rr])), max_variant_mass=max(x["variant_mass"] for x in rr)))
    return out


# ---------- core tables ----------

def bank(split=None, subset=False):
    return [r for r in D.constructed() if (split is None or r["split"] == split) and (not subset or r["subset"])]


def stratum(k):
    return next(s for s, ks in C.STRATA.items() if k in ks)


def separability(data: Data, rows, label) -> list:
    out = []
    for s, ks in C.STRATA.items():
        hs = sorted({r["history"] for r in rows if r["k"] in ks})
        if not hs:
            continue
        d = [js(data.GT[("qwen", h)], data.GT[("mistral", h)]) for h in hs]
        out.append(dict(bank=label, rolls=s, n=len(hs), mean_js=float(np.mean(d)), median_js=float(np.median(d)), max_js=float(max(d)),
                        top_face_differs=int(sum(data.GT[("qwen", h)].argmax() != data.GT[("mistral", h)].argmax() for h in hs))))
    return out


def word_table(data: Data, words, rows, label, template="T1", neutral_subject=C.NEUTRAL) -> list:
    """Own / other / selective gain per checkpoint and word (family-balanced means) plus the outsider's gain for the same target."""
    fams, neutral = by_family(rows), CK(neutral_subject, template)
    fm = lambda f: float(np.mean([np.mean([f(h) for h in hs]) for hs in fams.values()]))
    out = []
    for p, w in itertools.product(C.MODELS, words):
        c = CK(D.subject_word(w), template)
        g = lambda q, t: fm(lambda h: gain(data.F, data.GT, q, t, c, h, neutral))
        own, oth = g(p, p), g(p, OTHER[p])
        out.append(dict(bank=label, template=template, checkpoint=p, word=w, association=data.A[p][w], own_gain=own, other_gain=oth, selective=own - oth,
                        outsider_gain_same_target=g(OTHER[p], p), D_own_neutral=fm(lambda h: dist(data.F, data.GT, p, neutral, p, h)),
                        D_own_cue=fm(lambda h: dist(data.F, data.GT, p, c, p, h))))
    return out


def pair_table(cells, pairs, label) -> list:
    out = []
    for p in C.MODELS:
        for i, (l, r) in enumerate(pairs):
            out.append(dict(bank=label, checkpoint=p, left=l, right=r, a=cells[p]["a"][i], S_left_minus_S_right=float(np.nanmean(cells[p]["dS"][i])),
                            directional_test=float(np.nanmean(cells[p]["T"][i])), own_improvement=float(np.nanmean(cells[p]["O"][i])),
                            families_positive=int((cells[p]["T"][i] > 0).sum()), n_families=int(cells[p]["T"].shape[1])))
    return out


def unused_faces(h):
    x = D.faces_of(h)
    blk = x if len(x) < 6 else x[6:]
    u = [f for f in C.FACES if f not in blk]
    return u or list(C.FACES)


def baselines(data: Data, rows, label) -> list:
    out = []
    for t, (s, ks) in itertools.product(C.MODELS, list(C.STRATA.items()) + [("all", C.KS)]):
        hs = [r["history"] for r in rows if r["k"] in ks]
        if not hs:
            continue
        uni = np.full(6, 1 / 6)
        uu = lambda h: np.array([1 / len(unused_faces(h)) if f in unused_faces(h) else 0.0 for f in C.FACES])
        mix = lambda h: (data.GT[("qwen", h)] + data.GT[("mistral", h)]) / 2
        mean = lambda f: float(np.mean([js(f(h), data.GT[(t, h)]) for h in hs]))
        row = dict(bank=label, target=t, rolls=s, n=len(hs), uniform=mean(lambda h: uni), uniform_unused=mean(uu), policy_mixture=mean(mix),
                   other_policy=mean(lambda h: data.GT[(OTHER[t], h)]))
        for p in C.MODELS:
            row[f"forecast_neutral_{p}"] = mean(lambda h: data.F[(p, NEU, h)])
        out.append(row)
    return out


def diagnostics(data: Data, rows, label) -> list:
    """Mass, compliance, residuals, top-face agreement and unused-set decomposition for neutral forecasts, by roll stratum."""
    out = []
    for p, (s, ks) in itertools.product(C.MODELS, C.STRATA.items()):
        hs = [r["history"] for r in rows if r["k"] in ks]
        q, g = np.array([data.F[(p, NEU, h)] for h in hs]), np.array([data.GT[(p, h)] for h in hs])
        un = [[f - 1 for f in unused_faces(h)] for h in hs]
        wi = []
        for a, b, u in zip(q, g, un):
            if len(u) > 1 and a[u].sum() > 0 and b[u].sum() > 0:
                wi.append(js(a[u] / a[u].sum(), b[u] / b[u].sum()))
        out.append(dict(bank=label, checkpoint=p, rolls=s, n=len(hs), median_face_mass=float(np.median([data.mass[(p, NEU, h)] for h in hs])),
                        greedy_is_face=float(np.mean([data.top[(p, NEU, h)] in "123456" for h in hs])), mean_js_own=float(np.mean([js(a, b) for a, b in zip(q, g)])),
                        top_face_agree_own=float(np.mean(q.argmax(1) == g.argmax(1))), forecast_mass_on_unused=float(np.mean([a[u].sum() for a, u in zip(q, un)])),
                        target_mass_on_unused=float(np.mean([b[u].sum() for b, u in zip(g, un)])), js_within_unused=float(np.mean(wi)) if wi else None,
                        median_direct_mass=float(np.median([data.gmass[(p, h)] for h in hs])),
                        **{f"residual_face{f}": float((q - g)[:, f - 1].mean()) for f in C.FACES}))
    return out


def coverage(data: Data, phases=("core",)) -> list:
    """Valid-face mass by arm/condition/model; flag core conditions with median mass below LOW_MASS."""
    grp = {}
    for d in D.design():
        if d["phase"] in phases:
            grp.setdefault((d["phase"], d["arm"], d["cond"]), set()).add(d["history"])
    out = []
    for (ph, arm, cond), hs in grp.items():
        for p in C.MODELS:
            m = [data.mass[(p, cond, h)] for h in hs]
            tc = [data.tokens[(p, cond, h)] for h in hs]
            out.append(dict(phase=ph, arm=arm, condition=cond, checkpoint=p, n=len(m), median_mass=float(np.median(m)), min_mass=min(m),
                            greedy_is_face=float(np.mean([data.top[(p, cond, h)] in "123456" for h in hs])), low_mass_flag=float(np.median(m)) < C.LOW_MASS,
                            mean_chars=float(np.mean([x[0] for x in tc])), mean_tokens=float(np.mean([x[1] for x in tc]))))
    return out


def named_matrix(data: Data) -> list:
    """Forecaster x named target on the subset bank, with 'a language model' as the within-target control."""
    hs = by_family(bank(subset=True))
    fm = lambda f: float(np.mean([np.mean([f(h) for h in v]) for v in hs.values()]))
    out = []
    for p, t in itertools.product(C.MODELS, C.MODELS):
        c = CK(C.NAME[t])
        Dn, Dg = fm(lambda h: dist(data.F, data.GT, p, c, t, h)), fm(lambda h: dist(data.F, data.GT, p, CK(C.GENERIC_LM), t, h))
        Ds = fm(lambda h: dist(data.F, data.GT, p, NEU, t, h))
        out.append(dict(forecaster=p, named_target=t, owner=p == t, D_named=Dn, D_generic_lm=Dg, D_neutral_shape=Ds, improvement_vs_generic=Dg - Dn,
                        improvement_vs_neutral=Ds - Dn))
    return out


def subject_table(data: Data, subjects: dict, control, label) -> list:
    hs = by_family(bank(subset=True))
    fm = lambda f: float(np.mean([np.mean([f(h) for h in v]) for v in hs.values()]))
    out = []
    for p, (k, s) in itertools.product(C.MODELS, subjects.items()):
        g = {t: fm(lambda h: gain(data.F, data.GT, p, t, CK(s), h, CK(control))) for t in C.MODELS}
        out.append(dict(panel=label, checkpoint=p, subject=k, control=control, n_histories=28, D_own=fm(lambda h: dist(data.F, data.GT, p, CK(s), p, h)),
                        D_other=fm(lambda h: dist(data.F, data.GT, p, CK(s), OTHER[p], h)), own_gain=g[p], other_gain=g[OTHER[p]], selective=g[p] - g[OTHER[p]]))
    return out


def scaffold_table(data: Data) -> tuple:
    hs = by_family(bank(subset=True))
    fm = lambda f: float(np.mean([np.mean([f(h) for h in v]) for v in hs.values()]))
    subj = {"neutral": C.NEUTRAL, **{w: D.subject_word(w) for w in C.SUBSET_WORDS}}
    levels, shift = [], []
    for p, t, (k, s) in itertools.product(C.MODELS, C.MODELS, subj.items()):
        d = {sc: fm(lambda h: dist(data.F, data.GT, p, CK(s, scaffold=sc), t, h)) for sc in C.SCAFFOLDS}
        levels.append(dict(forecaster=p, target=t, own=p == t, subject=k, **{f"D_{x}": v for x, v in d.items()},
                           **{f"plain_minus_{x}": d["plain"] - d[x] for x in ("physical", "textual", "preamble")},
                           **{f"preamble_minus_{x}": d["preamble"] - d[x] for x in ("physical", "textual")}))
        if k != "neutral":
            g = {sc: fm(lambda h: gain(data.F, data.GT, p, t, CK(s, scaffold=sc), h, CK(C.NEUTRAL, scaffold=sc))) for sc in C.SCAFFOLDS}
            shift.append(dict(forecaster=p, target=t, own=p == t, word=k, **{f"gain_{x}": v for x, v in g.items()},
                              **{f"{x}_minus_plain": g[x] - g["plain"] for x in ("physical", "textual", "preamble")}))
    return levels, shift


def roll_table(data: Data, pairs, rows) -> list:
    out = []
    for p, k in itertools.product(C.MODELS, C.KS):
        hs = [r["history"] for r in rows if r["k"] == k]
        T, O = [], []
        for l, r in pairs:
            a = data.A[p][l] - data.A[p][r]
            cl, cr = CK(D.subject_word(l)), CK(D.subject_word(r))
            T.append(np.sign(a) * np.mean([selective(data.F, data.GT, p, cl, h) - selective(data.F, data.GT, p, cr, h) for h in hs]))
            gl, gr = (np.mean([gain(data.F, data.GT, p, p, c, h) for h in hs]) for c in (cl, cr))
            O.append(gl if a > 0 else gr if a < 0 else (gl + gr) / 2)
        out.append(dict(checkpoint=p, roll=k, n_histories=len(hs), directional_test=float(np.mean(T)), own_improvement=float(np.mean(O)),
                        separability_js=float(np.mean([js(data.GT[("qwen", h)], data.GT[("mistral", h)]) for h in hs])),
                        D_own_neutral=float(np.mean([dist(data.F, data.GT, p, NEU, p, h) for h in hs]))))
    return out


def correlations(words_rows, pair_rows) -> list:
    out = []
    for p in C.MODELS:
        w = [r for r in words_rows if r["checkpoint"] == p]
        out.append(dict(checkpoint=p, level="word", n=len(w), pearson_association_vs_selective=_corr([r["association"] for r in w], [r["selective"] for r in w]),
                        pearson_association_vs_own_gain=_corr([r["association"] for r in w], [r["own_gain"] for r in w])))
        q = [r for r in pair_rows if r["checkpoint"] == p]
        out.append(dict(checkpoint=p, level="pair", n=len(q), pearson_association_vs_selective=_corr([r["a"] for r in q], [r["S_left_minus_S_right"] for r in q]),
                        pearson_association_vs_own_gain=None))
    return out


def _corr(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else None


def core(data: Data) -> dict:
    conf, dev, sub = bank("confirmation"), bank("development"), bank(subset=True)
    res = {}
    cells = primary_cells(data.F, data.GT, data.A, C.CONF_PAIRS, by_family(conf))
    res["primary"] = boot_summary(cells)
    res["primary_labels"] = {n: classify(res["primary"], n) for n in ("qwen", "mistral", "joint")}
    res["pairs_primary"] = pair_table(cells, C.CONF_PAIRS, "primary: confirmatory pairs x confirmatory histories")
    variants = {}
    def variant(name, pairs, rows, **kw):
        c = primary_cells(data.F, data.GT, data.A, pairs, by_family(rows), **kw)
        variants[name] = dict(summary=boot_summary(c), n_pairs=len(pairs), n_families=len(by_family(rows)))
        return pair_table(c, pairs, name)
    extra = variant("development pairs x development histories", C.DEV_PAIRS, dev)
    extra += variant("development pairs x confirmatory histories", C.DEV_PAIRS, conf)
    extra += variant("confirmatory pairs x development histories", C.CONF_PAIRS, dev)
    extra += variant("longer neutral: confirmatory pairs x confirmatory histories", C.CONF_PAIRS, conf, neutral=CK(C.LONG_NEUTRAL))
    extra += variant("T1 on the 28-history subset", C.CONF_PAIRS, sub)
    t2 = lambda w: CK(D.subject_word(w), "T2")
    extra += variant("T2 on the 28-history subset", C.CONF_PAIRS, sub, wordcond=t2, neutral=CK(C.NEUTRAL, "T2"))
    extra += variant("T2, longer neutral", C.CONF_PAIRS, sub, wordcond=t2, neutral=CK(C.LONG_NEUTRAL, "T2"))
    keep = lambda p, conds, h: all(data.mass[(p, c, h)] >= C.LOW_MASS for c in conds)
    hm = primary_cells(data.F, data.GT, data.A, C.CONF_PAIRS, by_family(conf), keep=keep)
    variants["high-mass sensitivity (all three arms >= 0.50)"] = dict(summary=boot_summary(hm), retained_histories={
        p: [int(hm[p]["n"].sum()), int(len(C.CONF_PAIRS) * len(conf))] for p in C.MODELS})
    res["variants"], res["pairs_variants"] = variants, extra
    res["associations"], res["association_effects"] = association_table(data), association_effects(data)
    res["words"] = word_table(data, C.CONF_WORDS, conf, "confirmatory words x confirmatory histories") + \
        word_table(data, [w for x in C.DEV_PAIRS for w in x], dev, "development words x development histories") + \
        word_table(data, C.CONF_WORDS, sub, "subset T2", "T2")
    res["correlations"] = correlations([r for r in res["words"] if r["bank"].startswith("confirmatory")], res["pairs_primary"])
    res["separability"] = separability(data, conf, "confirmation") + separability(data, dev, "development")
    res["baselines"] = baselines(data, conf, "confirmation")
    res["diagnostics"] = diagnostics(data, conf, "confirmation")
    res["coverage"] = coverage(data)
    res["named_matrix"] = named_matrix(data)
    res["identity"] = subject_table(data, C.IDENTITY_SUBJECTS, C.GENERIC_LM, "identity vs 'a language model'") + \
        subject_table(data, C.IDENTITY_SUBJECTS, C.NEUTRAL, "identity vs 'a shape'")
    res["scaffold_levels"], res["scaffold_gain"] = scaffold_table(data)
    res["rolls"] = roll_table(data, C.CONF_PAIRS, conf)
    ln = [dict(checkpoint=p, D_own_neutral=float(np.mean([dist(data.F, data.GT, p, NEU, p, r["history"]) for r in conf])),
               D_own_long_neutral=float(np.mean([dist(data.F, data.GT, p, CK(C.LONG_NEUTRAL), p, r["history"]) for r in conf]))) for p in C.MODELS]
    res["neutral_wording"] = ln
    h = D.seq(C.WORKED[0])
    res["worked"] = [dict(history=D.seq(x), checkpoint=p, **{f"G{f}": float(data.GT[(p, D.seq(x))][f - 1]) for f in C.FACES},
                          **{f"F_{n}_{f}": float(data.F[(p, CK(s), D.seq(x))][f - 1]) for n, s in (("neutral", C.NEUTRAL), ("blue", D.subject_word("blue")), ("orange", D.subject_word("orange")))
                             for f in C.FACES}) for x in C.WORKED for p in C.MODELS]
    res["worked_history_in_primary"] = h in {r["history"] for r in conf}
    return res


# ---------- extensions ----------

def incidental(data: Data) -> list:
    hs = by_family(bank(subset=True))
    fm = lambda f: float(np.mean([np.mean([f(h) for h in v]) for v in hs.values()]))
    out = []
    for p, w in itertools.product(C.MODELS, C.SUBSET_WORDS):
        r, c = {}, {}
        for t in C.MODELS:
            r[t] = fm(lambda h: gain(data.F, data.GT, p, t, CK(D.subject_word(w)), h))
            c[t] = fm(lambda h: gain(data.F, data.GT, p, t, CK(C.NEUTRAL, card=w), h, CK(C.NEUTRAL, card="")))
        out.append(dict(checkpoint=p, word=w, roller_own=r[p], card_own=c[p], roller_selective=r[p] - r[OTHER[p]], card_selective=c[p] - c[OTHER[p]],
                        roller_minus_card_own=r[p] - c[p], roller_minus_card_selective=(r[p] - r[OTHER[p]]) - (c[p] - c[OTHER[p]])))
    return out


def objects(data: Data) -> list:
    hs = by_family(bank(subset=True))
    fm = lambda f: float(np.mean([np.mean([f(h) for h in v]) for v in hs.values()]))
    out = []
    for p, t in itertools.product(C.MODELS, C.MODELS):
        Dv = lambda k: fm(lambda h: dist(data.F, data.GT, p, CK(C.OBJECT_SUBJECTS[k]), t, h))
        for name, (x1, x2), (y1, y2) in (("color x form", ("blue", "orange"), ("pointy", "round")), ("affect x object", ("angry", "sad"), ("square", "circle"))):
            d = {(a, b): Dv(f"{a}_{b}") for a in (x1, x2) for b in (y1, y2)}
            out.append(dict(forecaster=p, target=t, own=p == t, cross=name, **{f"D_{a}_{b}": v for (a, b), v in d.items()},
                            effect_first=((d[(x2, y1)] - d[(x1, y1)]) + (d[(x2, y2)] - d[(x1, y2)])) / 2,
                            effect_second=((d[(x1, y2)] - d[(x1, y1)]) + (d[(x2, y2)] - d[(x2, y1)])) / 2,
                            interaction=(d[(x2, y2)] - d[(x1, y2)]) - (d[(x2, y1)] - d[(x1, y1)]), n_histories=28))
    return out


def cued(data: Data) -> list:
    """Facewise shifts from neutral in direct generation vs forecasting, same histories."""
    hs = [r["history"] for r in bank(subset=True)]
    out = []
    for p, w in itertools.product(C.MODELS, C.SUBSET_WORDS):
        gs = np.array([data.cued[(p, D.subject_word(w), h)] - data.cued[(p, C.NEUTRAL, h)] for h in hs])
        fs = np.array([data.F[(p, CK(D.subject_word(w)), h)] - data.F[(p, NEU, h)] for h in hs])
        jd = float(np.mean([js(data.cued[(p, D.subject_word(w), h)], data.cued[(p, C.NEUTRAL, h)]) for h in hs]))
        jf = float(np.mean([js(data.F[(p, CK(D.subject_word(w)), h)], data.F[(p, NEU, h)]) for h in hs]))
        out.append(dict(checkpoint=p, word=w, js_shift_direct=jd, js_shift_forecast=jf, pearson_facewise_shifts=_corr(gs.ravel(), fs.ravel()),
                        **{f"direct_shift_{f}": float(gs[:, f - 1].mean()) for f in C.FACES}, **{f"forecast_shift_{f}": float(fs[:, f - 1].mean()) for f in C.FACES}))
    for p in C.MODELS:
        out.append(dict(checkpoint=p, word="[neutral cue vs unmodified G]", js_shift_direct=float(np.mean([js(data.cued[(p, C.NEUTRAL, h)], data.GT[(p, h)]) for h in hs]))))
    return out


def natural_tables(data: Data) -> dict:
    sel = [r for r in D.natural() if r["selected"]]
    uniq = {}
    for r in sel:
        uniq.setdefault(r["history"], dict(history=r["history"], k=r["k"], sources=set(), overlap=r["overlaps_constructed"]))["sources"].add(r["source"])
    out = []
    for p, w in itertools.product(C.MODELS, C.SUBSET_WORDS):
        for lab, hs in (("all selected", list(uniq)), ("previously unseen", [h for h, u in uniq.items() if not u["overlap"]]),
                        ("own-source", [h for h, u in uniq.items() if u["sources"] == {p}]), ("other-source", [h for h, u in uniq.items() if u["sources"] == {OTHER[p]}])):
            c = CK(D.subject_word(w))
            g = {t: float(np.mean([gain(data.F, data.GT, p, t, c, h) for h in hs])) for t in C.MODELS}
            out.append(dict(checkpoint=p, word=w, histories=lab, n=len(hs), own_gain=g[p], other_gain=g[OTHER[p]], selective=g[p] - g[OTHER[p]]))
    pairs = [("blue", "orange"), ("pointy", "round"), ("angry", "calm")]
    tests = []
    for p, lab in itertools.product(C.MODELS, ("all selected", "previously unseen")):
        rr = {r["word"]: r for r in out if r["checkpoint"] == p and r["histories"] == lab}
        T = [float(np.sign(data.A[p][l] - data.A[p][r]) * (rr[l]["selective"] - rr[r]["selective"])) for l, r in pairs]
        O = [rr[l if data.A[p][l] > data.A[p][r] else r]["own_gain"] for l, r in pairs]
        tests.append(dict(checkpoint=p, histories=lab, directional_test_mean=float(np.mean(T)), own_improvement_mean=float(np.mean(O)), by_pair=[f"{l}/{r}: {t:+.5f}" for (l, r), t in zip(pairs, T)]))
    return dict(words=out, tests=tests, separability=separability(data, D.natural(), "natural (all)"),
                unique_selected=len(uniq), overlapping_constructed=sum(u["overlap"] for u in uniq.values()))


def opening_table(data: Data) -> list:
    out = []
    for p, L in itertools.product(C.MODELS, (0, 1, 2)):
        hs = [h for h in D.opening() if len(D.faces_of(h)) == L]
        row = dict(checkpoint=p, prefix_length=L, n=len(hs), separability_js=float(np.mean([js(data.GT[("qwen", h)], data.GT[("mistral", h)]) for h in hs])))
        for n, s in (("neutral", C.NEUTRAL), ("identical", C.IDENTICAL)):
            row[f"D_own_{n}"] = float(np.mean([dist(data.F, data.GT, p, CK(s), p, h) for h in hs]))
            row[f"D_other_{n}"] = float(np.mean([dist(data.F, data.GT, p, CK(s), OTHER[p], h) for h in hs]))
        out.append(row)
    return out


def verbal_tables(data: Data) -> tuple:
    from spar_dynamic.dice_scaffolding.gpu import parse_verbal
    rows, summ = [], []
    for p in C.MODELS:
        for r in data.gens[p]:
            if r["assay"] != "verbal":
                continue
            v, why = parse_verbal(r["content"])
            rows.append(dict(checkpoint=p, subject_key=r["subject_key"], history=r["history"], valid=v is not None, reason=why, finish=r["finish_reason"],
                             D_own=js(v, data.GT[(p, r["history"])]) if v else None, D_other=js(v, data.GT[(OTHER[p], r["history"])]) if v else None,
                             D_own_token_forecast=dist(data.F, data.GT, p, CK(r["subject"]), p, r["history"]), report=v, text=r["content"][:200]))
        for k in D.readout_subjects():
            a = [x for x in rows if x["checkpoint"] == p and x["subject_key"] == k]
            ok = [x for x in a if x["valid"]]
            summ.append(dict(checkpoint=p, subject=k, n=len(a), n_valid=len(ok), D_own=float(np.mean([x["D_own"] for x in ok])) if ok else None,
                             D_other=float(np.mean([x["D_other"] for x in ok])) if ok else None,
                             D_own_token_same_rows=float(np.mean([x["D_own_token_forecast"] for x in ok])) if ok else None,
                             distinct_reports=len({json.dumps(x["report"]) for x in ok})))
    return rows, summ


def free_table(data: Data) -> list:
    from spar_dynamic.dice_scaffolding.gpu import parse_free
    out = []
    for p in C.MODELS:
        for r in data.gens[p]:
            if r["assay"] != "free":
                continue
            x = parse_free(r["content"])
            row = dict(checkpoint=p, subject=r["subject_key"], valid=x is not None, content=r["content"][:120])
            if x:
                row.update(repeated_faces_first_six=6 - len(set(x[:6])), first_six_permutation=len(set(x[:6])) == 6)
                for t in C.MODELS:
                    g = C.REFERENCES[(t, "G")]
                    div = next((i + 1 for i in range(10) if x[i] != g[i]), None)
                    row.update({f"matches_{t}": sum(a == b for a, b in zip(x, g)), f"first_divergence_{t}": div})
            out.append(row)
    return out


def facts_table(data: Data) -> list:
    grp = {}
    for r in data.facts:
        q = np.exp(np.array(r["l"]))
        grp.setdefault((r["model"], r["item"], r["subject_key"]), []).append((r, q / q.sum()))
    out = []
    for (m, item, sk), v in grp.items():
        acc = {}
        for r, q in v:
            for x, pr in zip(r["letters"], q):
                acc.setdefault(r["meaning"][x], []).append(float(pr))
        mean = {k: float(np.mean(x)) for k, x in acc.items()}
        true = ("both" if item == "both_true" else "neither" if item == "neither_true"
                else f"{m if sk == 'self' else sk}_value")
        out.append(dict(checkpoint=m, item=item, subject=sk, correct_option=true, p_correct=mean[true], correct_argmax=int(sum(q.argmax() == r["letters"].index(next(x for x in r["letters"] if r["meaning"][x] == true)) for r, q in v)),
                        n_prompts=len(v), mean_letter_mass=float(np.mean([r["mass"] for r, _ in v])), probabilities=json.dumps({k: round(x, 4) for k, x in mean.items()})))
    return out


def factual(data: Data) -> list:
    return subject_table(data, C.FACTUAL_SUBJECTS, C.GENERIC_LM, "factual vs 'a language model'")


def extensions(data: Data) -> dict:
    vrows, vs = verbal_tables(data)
    return dict(incidental=incidental(data), objects=objects(data), object_subjects=subject_table(data, C.OBJECT_SUBJECTS, C.NEUTRAL, "objects vs 'a shape'"),
                cued=cued(data), natural=natural_tables(data), opening=opening_table(data), verbal_rows=vrows, verbal=vs, free=free_table(data),
                facts=facts_table(data), factual=factual(data), coverage=coverage(data, ("extensions",)))


def analysis_rows(data: Data, phases) -> list:
    """Every forecast-target distance with row provenance (handoff section 7 minimum schema)."""
    meta = {r["history"]: r for r in D.constructed()}
    out = []
    for d in D.design():
        if d["phase"] not in phases:
            continue
        h = d["history"]
        neutral = CK(C.NEUTRAL, d["template"], d["scaffold"], "" if d["card"] is not None else None)
        for p, t in itertools.product(C.MODELS, C.MODELS):
            key = (p, d["cond"], h)
            out.append(dict(phase=d["phase"], arm=d["arm"], template=d["template"], scaffold=d["scaffold"], card=d["card"], subject=d["subject"], history=h,
                            k=len(D.faces_of(h)) + 1, family=meta.get(h, {}).get("family"), split=meta.get(h, {}).get("split"), forecaster=p, target=t,
                            target_revision=C.MODEL[t]["revision"], forecast_row=data.frow[key], target_row=data.grow[(t, h)],
                            neutral_row=data.frow.get((p, neutral, h)), js_bits=round(js(data.F[key], data.GT[(t, h)]), 10), face_mass=data.mass[key],
                            low_mass=data.mass[key] < C.LOW_MASS, top_token=data.top[key]))
    return out
