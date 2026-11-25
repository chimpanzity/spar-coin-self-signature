"""Frozen readouts for Experiment 37: primal (explicit-coefficient) copies of Experiment 36's fitted outer-fold models for Qwen's target.

A held-out history of fold k uses only the models fitted with fold k left out (Experiment 36 hyperparameters, same training rows).
Because pairs are differenced and paired changes are taken, history blocks cancel: only activation, output and logit blocks matter.
Readouts (candidate-level score s(x, i); a pair's readout is s(x, i) - s(x, j)):
  agent_probe    face bias + PCA32 of the agent forecast state (b75)
  direct_probe   face bias + PCA32 of the direct state (b75): generation-state portability control
  calibrated     face bias + forecast-output block
  hist_output    history + forecast-output block (its output part)
  hist_logits    history + PCA32 of the full logits (its logit part; needs the head Gram matrix)
  hist_output_act  history + output + activation (its output and activation parts), secondary
"""

from __future__ import annotations

import json

import numpy as np

from spar_dynamic.hidden_policy import analysis as A
from spar_dynamic.hidden_policy import design as D36
from spar_dynamic.policy_swap import design as D

SLOT = D.PRIMARY_SLOT


def face_weights(bk, tr_pairs, a):
    """Dual coefficients -> matrix C (prefixes x 6) with C[n, f] = sum of signed dual weights of candidate (n, f)."""
    C = np.zeros((len(bk.x), 6))
    for p, v in zip(tr_pairs, a):
        n, i, j = bk.pairs[p]
        C[n, i - 1] += v
        C[n, j - 1] -= v
    return C


def act_primal(data, sp, mode, C, weight, rank=A.RANK):
    """(W 6 x d, mean, sd) of the activation block: s(x, i) = W[i] . ((h - mu) / sd)."""
    H = data.S["qwen", mode, SLOT].astype(np.float64)
    tr = sp.trx
    mu, sd = H[tr].mean(0), H[tr].std(0)
    sd = np.where(sd > 1e-6, sd, np.inf)
    Z = (H - mu) / sd
    vt = np.linalg.svd(Z[tr], full_matrices=False)[2][:rank]
    P = Z @ vt.T
    scale = data.bk.faced(P @ P.T)[sp.trp, sp.trp].mean()
    return dict(W=weight / scale * (C.T @ P) @ vt, mu=mu, sd=sd)


def out_primal(data, sp, C, weight):
    """Output block: slope on the candidate log-probability and 6 x 7 face-indexed linear terms."""
    bk, L, mass = data.bk, data.L["qwen", "agent"], data.mass["qwen", "agent"]
    tr = sp.trx
    c = np.array([L[n, f - 1] for n, f in bk.cand])
    cs = max(c[np.isin(bk.cx, tr)].std(), 1e-6)
    z = np.concatenate([L, np.log(np.maximum(mass, 1e-30))[:, None]], 1)
    zm, zs = z[tr].mean(0), np.maximum(z[tr].std(0), 1e-6)
    Z = (z - zm) / zs
    ka, kb = data.out_kernel("qwen", "agent", tr)
    da, db = ka[sp.trp, sp.trp].mean(), kb[sp.trp, sp.trp].mean()
    slope = weight * 0.5 / da * (C * (L / cs)).sum() / cs
    return dict(slope=float(slope), V=weight * 0.5 / db * (C.T @ Z) / 7, zm=zm, zs=zs)


def logit_primal(data, sp, C, weight, rank=A.RANK):
    """Coefficients on training rows' centred final-normalised states: s(x, i) = sum_n B[i, n] k(x, n), kept as a 6 x n_train matrix."""
    K = data.Glogit["qwen"]
    tr = sp.trx
    m = K[:, tr].mean(1)
    Kc = K - m[:, None] - m[None, :] + m[tr].mean()
    w, v = np.linalg.eigh(Kc[np.ix_(tr, tr)])
    o = np.argsort(w)[::-1][:rank]
    U = v[:, o] / np.sqrt(np.maximum(w[o], 1e-9))
    P = Kc[:, tr] @ U
    scale = data.bk.faced(P @ P.T)[sp.trp, sp.trp].mean()
    return dict(B=weight / scale * (C.T @ P) @ U.T, tr=tr)


def bias_primal(data, sp, C):
    kb = data.bk.pairk(data.bk.same_face)
    return C.sum(0) / kb[sp.trp, sp.trp].mean()


def fit_fold(cv, k, kind, spec, lam):
    """Refit one outer-fold model and return its primal blocks; predictions on the held-out fold are returned for verification."""
    d = cv.data
    sp = cv.outer[k]["full"]
    Kf = A.block(sp, spec)
    y = d.y["qwen"]
    a = A.solve(Kf, y, sp.w, sp.trp, lam)
    C = face_weights(d.bk, sp.trp, a)
    te = np.where(np.isin(d.bk.pfam, cv.outer[k]["test"]))[0]
    r = dict(kind=kind, fold=k, spec=str(spec), lam=float(lam), bias=bias_primal(d, sp, C), dual_pred=Kf[np.ix_(te, sp.trp)] @ a, test_pairs=te)
    for s in spec:
        if s[-1] == 0:
            continue
        if s[0] == "act":
            r["act"] = act_primal(d, sp, s[2], C, s[-1], s[4])
        elif s[0] == "out":
            r["out"] = out_primal(d, sp, C, s[-1])
        elif s[0] == "logit":
            r["logit"] = logit_primal(d, sp, C, s[-1])
    return r


def score(r, states=None, L=None, mass=None, Kx=None):
    """Candidate scores (rows x 6) from primal blocks (no history part). Kx: rows x training-row raw logit inner products."""
    n = len(states if states is not None else L if L is not None else Kx)
    s = np.tile(r["bias"], (n, 1)).astype(float)
    if "act" in r:
        s += ((np.asarray(states, np.float64) - r["act"]["mu"]) / r["act"]["sd"]) @ r["act"]["W"].T
    if "out" in r:
        z = (np.concatenate([L, np.log(np.maximum(mass, 1e-30))[:, None]], 1) - r["out"]["zm"]) / r["out"]["zs"]
        s += r["out"]["slope"] * L + z @ r["out"]["V"].T
    if "logit" in r:
        s += Kx @ r["logit"]["B"].T                      # centring constants cancel in paired changes (see analysis)
    return s


KINDS = {"agent_probe": ("actonly", "qwen", "qwen", "agent", SLOT, A.RANK), "direct_probe": ("actonly", "qwen", "qwen", "direct", SLOT, A.RANK),
         "calibrated": ("outcal", "qwen", "qwen", "agent"), "hist_output": ("chain", "qwen", "qwen", "agent", SLOT, A.RANK),
         "hist_output_act": ("chain", "qwen", "qwen", "agent", SLOT, A.RANK), "hist_logits": ("logitchain", "qwen", "qwen")}
PART = {"hist_output": "io", "hist_output_act": "ioact", "hist_logits": "histlogit"}


def freeze(data=None):
    """Refit on base Qwen (Experiment 36 arrays), verify primal == dual, write arrays/probes.npz and probes_manifest.json."""
    data = data or A.Data()
    A._W["cv"] = cv = A.CV(data)
    bk = data.bk
    out, man = {}, {}
    cache = {}
    for kind, t in KINDS.items():
        if t not in cache:
            cache[t] = A.task(t)
        res = cache[t][PART[kind]] if kind in PART else cache[t]
        oof, chosen = res
        for k in D.HOLDOUT_FOLDS:
            spec, lam = chosen[k]
            r = fit_fold(cv, k, kind, spec, lam)
            te = r.pop("test_pairs")
            dp = r.pop("dual_pred")
            assert np.allclose(dp, oof[te], atol=1e-6), (kind, k)
            if not any(s[0] == "hist" for s in spec):          # no history block: the primal readout must reproduce the model exactly
                n = bk.px[te]
                st = data.S["qwen", "direct" if kind == "direct_probe" else "agent", SLOT]
                s = score(r, states=st, L=data.L["qwen", "agent"], mass=data.mass["qwen", "agent"])
                i, j = np.array([bk.pairs[p][1] for p in te]), np.array([bk.pairs[p][2] for p in te])
                err = float(np.abs((s[n, i - 1] - s[n, j - 1]) - dp).max())
                assert err < 1e-4, (kind, k, err)
            else:
                err = None
            for b in ("act", "out", "logit"):
                for q, v in r.get(b, {}).items():
                    out[f"{kind}.{k}.{b}.{q}"] = np.asarray(v)
            out[f"{kind}.{k}.bias"] = r["bias"]
            man[f"{kind}.{k}"] = dict(spec=str(spec), lam=float(lam), primal_vs_dual_max_abs=err,
                                      base_heldout_mse_pair_mean=float(((dp - data.y["qwen"][te]) ** 2).mean()), base_target_ms=float((data.y["qwen"][te] ** 2).mean()))
    (D.EXP / "arrays").mkdir(exist_ok=True)
    p = D.EXP / "arrays" / "probes.npz"
    np.savez(p, **out)
    from spar_dynamic.hidden_policy.gpu import file_sha
    rec = dict(tag=D.TAG, probes_sha256=file_sha(p), bytes=p.stat().st_size, slot=SLOT, folds=list(D.HOLDOUT_FOLDS),
               exp36_states_sha256=file_sha(D36.EXP / "arrays" / "qwen" / "states_bf16_uint16.npy") if (D36.EXP / "arrays" / "qwen").exists() else None, readouts=man)
    (D.EXP / "probes_manifest.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8", newline="\n")
    return rec


def load_probes():
    z = np.load(D.EXP / "arrays" / "probes.npz")
    out = {}
    for key in z.files:
        kind, k, *rest = key.split(".")
        r = out.setdefault((kind, int(k)), {})
        if rest == ["bias"]:
            r["bias"] = z[key]
        else:
            r.setdefault(rest[0], {})[rest[1]] = z[key]
    return out
