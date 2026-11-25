"""Frozen design of Experiment 37: holdout, target rule, adapter schedule, gates. Pure Python/numpy."""

from __future__ import annotations

import json

import numpy as np

from repo_paths import T1
from spar_dynamic.hidden_policy import design as D36

TAG = "SPAR_EXP37_FROZEN_PROBE_POLICY_SWAP_v1.0"
EXP = T1 / "37_2026-11-25_frozen_probe_policy_swap"
EXP36 = D36.EXP
LAST_FROZEN_INDEX = 36
MODEL = D36.MODEL["qwen"]
HOLDOUT_FOLDS = (0, 1)                      # Experiment 36 outer folds; 8 families, never seen by adapter training or tuning
TRAIN_FOLDS = (2, 3, 4)                     # 10 families, adapter training
DEV_FAMILIES = D36.PILOT_FAMILIES           # adapter development; excluded from every probe and from evaluation
MODES = ("agent", "shape", "direct")
ARMS = ("base", "disabled", "A", "B", "neutral")
ACTIVE = ("A", "B")
PRIMARY_SLOT = D36.PRIMARY_SLOT             # block 47; adapters end upstream of it
BLOCKS = tuple(range(24, 40))
SITES = ("self_attn.q_proj", "self_attn.v_proj", "self_attn.o_proj", "mlp.down_proj")
# Two schedules, tried in order on development data only; the first whose A and B both pass the gates is used (else the second).
CONFIGS = (dict(name="c1", rank=8, lr=5e-4, epochs=24, batch=10), dict(name="c2", rank=16, lr=1e-3, epochs=40, batch=10))
EVAL_EVERY = 4                              # epochs between development evaluations; the epoch with the lowest development loss is kept
LORA_SCALE = 1.0
SEED = {"A": 370001, "B": 370002, "neutral": 370003}
W_FULL = 1.0                                # weight of the full-vocabulary preservation KL added to the conditional KL
GATE = dict(median_abs_dlogodds=0.5, switch_rate=0.20, median_abs_dmass_pp=3.0)
GPU_CAP_USD = 10.0


def prefixes(which):
    b = D36.bank()
    f = {"train": lambda r: r["fold"] in TRAIN_FOLDS, "dev": lambda r: r["family"] in DEV_FAMILIES, "holdout": lambda r: r["fold"] in HOLDOUT_FOLDS}[which]
    return [r for r in b if f(r)]


def faces(p):
    return tuple(int(v) for v in p.split())


def source_map(x, arm):
    """For each unused face u (ascending), the unused face whose base logit it receives. first < last: A rotates one step forward
    (face u_m's logit moves to u_{m+1}), else backward; B reversed. Two unused faces: A swaps when first < last and B when not."""
    U = [f for f in D36.FACES if f not in x]
    k, pred = len(U), x[0] < x[-1]
    if arm == "neutral":
        step = 0
    elif k == 2:
        step = int(pred if arm == "A" else not pred)
    else:
        step = 1 if (pred if arm == "A" else not pred) else -1
    return {U[m]: U[(m - step) % k] for m in range(k)}


def permuted_logp(lp6, x, arm):
    """Six face log-probabilities with the conditional profile over unused faces permuted (unused mass preserved exactly)."""
    out = np.array(lp6, float)
    for u, s in source_map(x, arm).items():
        out[u - 1] = lp6[s - 1]
    return out


def gate_stats(base6, new6, xs):
    """Manipulation statistics for one arm (arrays prefixes x 6 of raw face log-probabilities)."""
    d, sw, dm = [], [], []
    for b, n, x in zip(np.asarray(base6), np.asarray(new6), xs):
        U = [f - 1 for f in D36.FACES if f not in x]
        for a in range(len(U)):
            for c in range(a + 1, len(U)):
                d.append(abs((n[U[a]] - n[U[c]]) - (b[U[a]] - b[U[c]])))
        sw.append(max(U, key=lambda u: b[u]) != max(U, key=lambda u: n[u]))
        pb, pn = np.exp(b) / np.exp(b).sum(), np.exp(n) / np.exp(n).sum()
        dm.append(100 * abs(pn[U].sum() - pb[U].sum()))
    r = dict(median_abs_dlogodds=float(np.median(d)), switch_rate=float(np.mean(sw)), median_abs_dmass_pp=float(np.median(dm)),
             mean_abs_dmass_pp=float(np.mean(dm)), median_digit_mass=float(np.median(np.exp(np.asarray(new6)).sum(1))), n=len(xs))
    r["pass"] = bool(r["median_abs_dlogodds"] >= GATE["median_abs_dlogodds"] and r["switch_rate"] >= GATE["switch_rate"]
                     and r["median_abs_dmass_pp"] <= GATE["median_abs_dmass_pp"])
    return r


def manifest():
    return json.dumps(dict(tag=TAG, model=dict(model_id=MODEL["model_id"], revision=MODEL["revision"]),
                           holdout=sorted({r["family"] for r in prefixes("holdout")}), train=sorted({r["family"] for r in prefixes("train")}),
                           dev=list(DEV_FAMILIES), n={k: len(prefixes(k)) for k in ("train", "dev", "holdout")}, modes=MODES, arms=ARMS,
                           blocks=BLOCKS, sites=SITES, configs=CONFIGS, eval_every=EVAL_EVERY, seed=SEED, w_full=W_FULL, gate=GATE,
                           gpu_cap_usd=GPU_CAP_USD), indent=1) + "\n"


def split_csv():
    rows = ["prefix,family,fold,roll,use,source_map_A,source_map_B"]
    for w in ("train", "dev", "holdout"):
        for r in prefixes(w):
            m = [" ".join(f"{u}<-{s}" for u, s in source_map(faces(r["prefix"]), a).items()) for a in ACTIVE]
            rows.append(f"{r['prefix']},{r['family']},{'' if r['fold'] is None else r['fold']},{r['roll']},{w},{m[0]},{m[1]}")
    return "\n".join(rows) + "\n"


def hashes_csv():
    rows = ["mode,prefix,prompt_sha256"]
    for m in MODES:
        for w in ("train", "dev", "holdout"):
            for r in prefixes(w):
                rows.append(f"{m},{r['prefix']},{D36.sha256(D36.G if m == 'direct' else D36.forecast(m, r['prefix']))}")
    return "\n".join(rows) + "\n"


def built():
    return {"manifest.json": manifest(), "split.csv": split_csv(), "prompt_hashes.csv": hashes_csv()}
