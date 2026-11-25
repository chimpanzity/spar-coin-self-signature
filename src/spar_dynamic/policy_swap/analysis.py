"""Prespecified analysis for Experiment 37: do frozen readouts' changes follow the measured changes in direct generation?"""

from __future__ import annotations

import csv
import itertools
import json

import numpy as np

from spar_dynamic.hidden_policy import design as D36
from spar_dynamic.hidden_policy.gpu import file_sha, read_jsonl
from spar_dynamic.policy_swap import design as D
from spar_dynamic.policy_swap import probes as PR

BOOT_B, BOOT_SEED = 10_000, 371125
N_SHUFFLE, SHUFFLE_SEED = 1000, 371126
READOUTS = ("agent_probe", "raw_output", "calibrated", "hist_output", "hist_logits", "hist_output_act", "direct_probe")
SLOT_I = D36.SLOTS.index(D.PRIMARY_SLOT)


def wcorr(x, y, w):
    mx, my = (w * x).sum() / w.sum(), (w * y).sum() / w.sum()
    c = (w * (x - mx) * (y - my)).sum()
    d = np.sqrt((w * (x - mx) ** 2).sum() * (w * (y - my) ** 2).sum())
    return float(c / d) if d > 0 else float("nan")


class Data:
    def __init__(self, rows=None, states=None, probes=None, gram=None, base36=None):
        self.hold = D.prefixes("holdout")
        self.x = [D.faces(r["prefix"]) for r in self.hold]
        self.fam = np.array([r["family"] for r in self.hold])
        self.fold = np.array([r["fold"] for r in self.hold])
        self.roll = np.array([r["roll"] for r in self.hold])
        self.pairs = [(n, i, j) for n, x in enumerate(self.x) for i, j in itertools.combinations([f for f in D36.FACES if f not in x], 2)]
        self.px = np.array([p[0] for p in self.pairs])
        self.I, self.J = np.array([p[1] - 1 for p in self.pairs]), np.array([p[2] - 1 for p in self.pairs])
        self.pf = self.fam[self.px]
        self.w = np.array([1 / ((self.px == n).sum() * (self.fam == f).sum()) for n, f in zip(self.px, self.pf)])
        rows = rows if rows is not None else read_jsonl(D.EXP / "raw" / "rows.jsonl")
        states = states if states is not None else np.load(D.EXP / "arrays" / "states_bf16_uint16.npy", mmap_mode="r")
        self.rows = {(r["arm"], r["mode"], r["prefix"]): r for r in rows}
        pr = probes if probes is not None else PR.load_probes()
        gram = gram if gram is not None else np.load(D36.EXP / "arrays" / "qwen" / "head_gram_centered_f32.npy").astype(np.float64)
        F36 = base36 if base36 is not None else self._base36()
        self.L, self.mass, self.R = {}, {}, {}
        for arm in D.ARMS:
            for mode in D.MODES:
                rs = [self.rows[arm, mode, r["prefix"]] for r in self.hold]
                L, mass = np.array([r["l"] for r in rs]), np.array([r["mass"] for r in rs])
                self.L[arm, mode], self.mass[arm, mode] = L, mass
                st = states[[r["row"] for r in rs]]
                st = (st.astype(np.uint32) << 16).view(np.float32) if st.dtype == np.uint16 else np.asarray(st)
                for ro in READOUTS:
                    if ro == "raw_output":
                        s = L
                    elif (ro == "direct_probe") != (mode == "direct"):
                        continue
                    else:
                        s = np.full((len(rs), 6), np.nan)
                        for k in D.HOLDOUT_FOLDS:
                            q, p = np.where(self.fold == k)[0], pr[ro, k]
                            Kx = None
                            if "logit" in p:
                                Kx = (st[q, 4].astype(np.float64) @ gram) @ F36[np.asarray(p["logit"]["tr"])].T
                            s[q] = PR.score(p, states=st[q, SLOT_I], L=L[q], mass=mass[q], Kx=Kx if "logit" in p else np.zeros((len(q), 1)))
                    self.R[arm, mode, ro] = s[self.px, self.I] - s[self.px, self.J]
        self.Y = {a: self.R[a, "direct", "raw_output"] for a in D.ARMS}

    @staticmethod
    def _base36():
        """Final-normalised agent states of Experiment 36's eligible prefixes, in its bank order."""
        rows = read_jsonl(D36.EXP / "raw" / "qwen" / "rows.jsonl")
        pos = {r["prefix"]: r["row"] for r in rows if r["mode"] == "agent"}
        st = np.load(D36.EXP / "arrays" / "qwen" / "states_bf16_uint16.npy", mmap_mode="r")
        A = st[[pos[b["prefix"]] for b in D36.bank() if b["eligible"]]][:, 4]
        return (A.astype(np.uint32) << 16).view(np.float32).astype(np.float64)

    def dy(self, arm):
        return self.Y[arm] - self.Y["base"]

    def dr(self, arm, mode, ro):
        return self.R[arm, mode, ro] - self.R["base", mode, ro]


def metric_block(d, act, dec, w, pf, mask=None):
    """Correlation, error versus zero change, slope; with family bootstrap. act/dec: lists of arrays (arms pooled with equal weight)."""
    fams = sorted(set(pf))
    m = np.ones(len(pf), bool) if mask is None else mask
    A = np.concatenate([a[m] for a in act])
    R = np.concatenate([r[m] for r in dec])
    W = np.concatenate([w[m]] * len(act))
    FX = np.concatenate([pf[m]] * len(act))
    # per-family sufficient statistics for the bootstrap
    T = np.array([[(W[q] * v[q]).sum() for v in (np.ones_like(A), A, R, A * A, R * R, A * R, (R - A) ** 2)] for f in fams for q in [FX == f]])

    def stats(i):
        s = T[i].sum(-2)
        n, a, r, aa, rr, ar, e = (s[..., k] for k in range(7))
        ca, cr, cc = aa / n - (a / n) ** 2, rr / n - (r / n) ** 2, ar / n - a * r / n ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            return dict(corr=cc / np.sqrt(ca * cr), mse=e / n, zero_mse=aa / n, skill=1 - (e / n) / (aa / n), slope_dec_on_act=ar / aa,
                        sign=np.zeros_like(n))
    s0 = stats(np.arange(len(fams)))
    rng = np.random.Generator(np.random.PCG64(BOOT_SEED))
    bs = stats(rng.integers(0, len(fams), size=(BOOT_B, len(fams))))
    out = {k: float(s0[k]) for k in ("corr", "mse", "zero_mse", "skill", "slope_dec_on_act")}
    nz = np.abs(A) > 1e-9
    out["sign_agreement"] = float((W[nz] * (np.sign(A[nz]) == np.sign(R[nz]))).sum() / W[nz].sum()) if nz.any() else None
    for k in ("corr", "skill", "slope_dec_on_act"):
        v = bs[k][np.isfinite(bs[k])]
        out[k + "_ci"] = [float(q) for q in np.percentile(v, [2.5, 97.5])] if len(v) else None
    out.update(n_pairs=int(m.sum()), n_families=len(set(pf[m])), n_arms=len(act))
    return out, bs


def demean(d, v):
    """Subtract the weighted mean per roll x face pair (fixed digit shift)."""
    out = v.copy()
    key = [(d.roll[n], i, j) for n, i, j in d.pairs]
    for k in set(key):
        q = np.array([kk == k for kk in key])
        out[q] -= (d.w[q] * v[q]).sum() / d.w[q].sum()
    return out


def shuffle_null(d, acts, decs):
    """Pair each decoded change with a different history's measured change, within arm, roll and face pair."""
    rng = np.random.Generator(np.random.PCG64(SHUFFLE_SEED))
    key = [(d.roll[n], i, j) for n, i, j in d.pairs]
    groups = [np.array([p for p, kk in enumerate(key) if kk == k]) for k in sorted(set(key))]
    W = np.concatenate([d.w] * len(acts))
    R = np.concatenate(decs)
    v = []
    for _ in range(N_SHUFFLE):
        sh = []
        for a in acts:
            b = a.copy()
            for g in groups:
                o = rng.permutation(len(g))                # a random cycle: nobody keeps its own history
                b[g[o]] = a[g[np.roll(o, 1)]]
            sh.append(b)
        v.append(wcorr(np.concatenate(sh), R, W))
    return dict(mean=float(np.nanmean(v)), q025=float(np.nanpercentile(v, 2.5)), q975=float(np.nanpercentile(v, 97.5)), min_stratum=int(min(map(len, groups))), strata=len(groups))


def gates(d):
    out = {}
    b = d.L["base", "direct"]
    for arm in D.ARMS[1:]:
        g = {"all": D.gate_stats(b, d.L[arm, "direct"], d.x)}
        for r in (4, 5):
            q = np.where(d.roll == r)[0]
            g[f"roll{r}"] = D.gate_stats(b[q], d.L[arm, "direct"][q], [d.x[n] for n in q])
        out[arm] = g
    q = np.where(d.roll > 0)[0]
    out["A_vs_B_direct"] = D.gate_stats(d.L["A", "direct"][q], d.L["B", "direct"][q], d.x)
    return out


def analyse(d):
    S = {}
    for name, arms in (("A", ["A"]), ("B", ["B"]), ("A+B", ["A", "B"]), ("neutral", ["neutral"]), ("disabled", ["disabled"])):
        for mode in ("agent", "shape"):
            base_bs = None
            for ro in READOUTS:
                rm = "direct" if ro == "direct_probe" else mode
                if ro == "direct_probe" and mode == "shape":
                    continue
                act, dec = [d.dy(a) for a in arms], [d.dr(a, rm, ro) for a in arms]
                r, bs = metric_block(d, act, dec, d.w, d.pf)
                if name in ("A", "B", "A+B"):
                    r["demeaned"] = {k: v for k, v in metric_block(d, [demean(d, a) for a in act], [demean(d, a) for a in dec], d.w, d.pf)[0].items() if k in ("corr", "corr_ci", "skill")}
                    for roll in (4, 5):
                        r[f"roll{roll}"] = {k: v for k, v in metric_block(d, act, dec, d.w, d.pf, d.roll[d.px] == roll)[0].items() if k in ("corr", "skill", "sign_agreement", "n_pairs")}
                    if mode == "agent":
                        r["wrong_history"] = shuffle_null(d, act, dec)
                if ro == "agent_probe":
                    base_bs, base_r = bs, r
                elif base_bs is not None:
                    for k in ("corr", "skill"):
                        v = base_bs[k] - bs[k]
                        v = v[np.isfinite(v)]
                        r[f"probe_minus_this_{k}"] = base_r[k] - r[k]
                        r[f"probe_minus_this_{k}_ci"] = [float(q) for q in np.percentile(v, [2.5, 97.5])] if len(v) else None
                S[f"{name}|{mode}|{ro}"] = r
    for mode in ("agent", "shape"):
        for ro in READOUTS:
            if ro == "direct_probe" and mode == "shape":
                continue
            rm = "direct" if ro == "direct_probe" else mode
            S[f"A-minus-B|{mode}|{ro}"] = metric_block(d, [d.dy("A") - d.dy("B")], [d.dr("A", rm, ro) - d.dr("B", rm, ro)], d.w, d.pf)[0]
    # base validity of the frozen readouts on held-out histories
    Yb = d.Y["base"]
    for ro in READOUTS:
        mode = "direct" if ro == "direct_probe" else "agent"
        if ro in ("hist_output", "hist_logits", "hist_output_act"):
            continue                                         # history part not stored; see Experiment 36
        S[f"base-levels|{mode}|{ro}"] = metric_block(d, [Yb], [d.R["base", mode, ro]], d.w, d.pf)[0]
    return S


def favourites(d):
    rows = []
    for arm in D.ACTIVE:
        for n, x in enumerate(d.x):
            U = [f - 1 for f in D36.FACES if f not in x]
            b, a = d.L["base", "direct"][n], d.L[arm, "direct"][n]
            fb, fa = max(U, key=lambda u: b[u]), max(U, key=lambda u: a[u])
            if fb == fa:
                continue
            i, j = sorted((fa, fb))
            p = next(k for k, q in enumerate(d.pairs) if q == (n, i + 1, j + 1))
            s = 1 if fa == i else -1                         # oriented: log odds of the new favourite over the old one
            pn = lambda L: float((np.exp(L) / np.exp(L).sum())[U].sum())
            r = dict(arm=arm, prefix=d.hold[n]["prefix"], family=d.fam[n], fold=int(d.fold[n]), roll=int(d.roll[n]), old_favourite=fb + 1, new_favourite=fa + 1,
                     actual_change=s * d.dy(arm)[p], base_unused_mass=pn(b), arm_unused_mass=pn(a), digit_mass=float(np.exp(a).sum()))
            for ro in READOUTS:
                m = "direct" if ro == "direct_probe" else "agent"
                r[f"{ro}_change"] = s * d.dr(arm, m, ro)[p]
                if ro in ("agent_probe", "raw_output", "direct_probe"):
                    r[f"{ro}_base"], r[f"{ro}_arm"] = s * d.R["base", m, ro][p], s * d.R[arm, m, ro][p]
            for ro in ("agent_probe", "raw_output"):
                r[f"shape_{ro}_change"] = s * d.dr(arm, "shape", ro)[p]
            rows.append(r)
    return rows


def examples(fv):
    def pick(q, key):
        return max(q, key=key) if q else None
    ap = lambda r: r["agent_probe_change"]
    return dict(tracked=pick([r for r in fv if ap(r) > 0 and r["agent_probe_base"] < 0 < r["agent_probe_arm"]], ap) or pick([r for r in fv if ap(r) > 0], ap),
                missed=pick([r for r in fv if ap(r) <= 0], lambda r: -ap(r)),
                forecast_tracks=pick([r for r in fv if r["raw_output_base"] < 0 < r["raw_output_arm"]], lambda r: r["raw_output_change"]))


def wcsv(path, rows):
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    out = D.EXP / "results"
    out.mkdir(exist_ok=True)
    d = Data()
    chk = json.load(open(D.EXP / "raw" / "eval_checks.json", encoding="utf-8"))
    man = json.load(open(D.EXP / "probes_manifest.json", encoding="utf-8"))
    env = json.load(open(D.EXP / "raw" / "env_evaluate.json", encoding="utf-8"))
    c = chk["checks"]
    ck = {"probes hash equals the frozen manifest": file_sha(D.EXP / "arrays" / "probes.npz") == man["probes_sha256"],
          "array and adapter hashes": all(file_sha(D.EXP / "arrays" / k) == v["sha256"] for k, v in env["arrays"].items()),
          "archival G/F replay": env["archival_check"]["ok"], "base repeat bit-identical": c["base_repeat"] == 0, "hooks on/off": c["hook_off"]["ok"],
          "base scores equal Experiment 36": c.get("exp36_score_mismatches") == 0,
          "disabled equals base (scores, states)": c["disabled_equals_base_scores"] and c["disabled_equals_base_states"],
          "prompts and tokens identical across arms": all(v for k, v in c.items() if k.endswith("prompt_and_tokens_equal_base")),
          "2,880 rows": len(d.rows) == len(D.ARMS) * len(D.MODES) * 192}
    (out / "CHECKS.md").write_text("# Experiment 37 checks\n\n" + "".join(f"- {'PASS' if v else 'FAIL'}: {k}\n" for k, v in ck.items()), encoding="utf-8", newline="\n")
    S, g, fv = analyse(d), gates(d), favourites(d)
    ex = examples(fv)
    json.dump(dict(checks=ck, gates=g, metrics=S, examples=ex, free_generation_G=chk["free_generation_G"]), open(out / "summary.json", "w", encoding="utf-8", newline="\n"),
              indent=1, default=float)
    wcsv(out / "favourite_reversals.csv", fv)
    flat = []
    for k, v in S.items():
        a, m, ro = k.split("|")
        flat.append(dict(arm=a, mode=m, readout=ro, **{q: (json.dumps(z) if isinstance(z, (dict, list)) else z) for q, z in v.items()}))
    wcsv(out / "metrics.csv", flat)
    pr = []
    for arm in D.ARMS[1:]:
        for p, (n, i, j) in enumerate(d.pairs):
            pr.append(dict(arm=arm, prefix=d.hold[n]["prefix"], family=d.fam[n], fold=int(d.fold[n]), roll=int(d.roll[n]), i=i, j=j, actual_change=d.dy(arm)[p],
                           **{f"{m}_{ro}_change": d.dr(arm, "direct" if ro == "direct_probe" else m, ro)[p] for m in ("agent", "shape") for ro in READOUTS if not (ro == "direct_probe" and m == "shape")}))
    wcsv(out / "paired_changes.csv", pr)
    for k, v in ck.items():
        print("PASS" if v else "FAIL", k)
    for a, v in g.items():
        print(a, json.dumps(v))
    print(json.dumps(chk["free_generation_G"]))
    for k, v in S.items():
        print(f"{k:38s} corr {v['corr']:+.3f} {v['corr_ci']} skill {v['skill']:+.3f} {v['skill_ci']} slope {v['slope_dec_on_act']:+.3f} sign {v['sign_agreement']} "
              f"dm {v.get('demeaned', {}).get('corr')} wrong {v.get('wrong_history', {}).get('mean')}/{v.get('wrong_history', {}).get('q975')} "
              f"d_corr {v.get('probe_minus_this_corr')} {v.get('probe_minus_this_corr_ci')}")
    for a in D.ACTIVE:
        q = [r for r in fv if r["arm"] == a]
        print(a, "reversals", len(q), "probe up", sum(r["agent_probe_change"] > 0 for r in q), "raw up", sum(r["raw_output_change"] > 0 for r in q),
              "direct probe up", sum(r["direct_probe_change"] > 0 for r in q))
    print(json.dumps(ex, indent=1, default=float))
