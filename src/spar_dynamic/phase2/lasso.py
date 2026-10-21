"""Seven-to-one LASSO reconstruction `history7_runs14_v1` (Section 10.3).

Fourteen features: seven history indicators (H=1), the adjacent-switch rate
over the seven, and counts of maximal within-history runs of exact lengths
2..7. Thirteen windows per 20-flip parent (targets at zero-indexed 7..19).
Offline only; predicts flips, not identity.
"""
from __future__ import annotations

import random
import warnings
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config as C
from .baselines import fold_of
from .corpus import runs

RECIPE = "history7_runs14_v1"


def window_features(history: str) -> List[float]:
    assert len(history) == 7
    ind = [1.0 if c == "H" else 0.0 for c in history]
    sw = sum(1 for a, b in zip(history, history[1:]) if a != b) / 6.0
    r = runs(history)
    counts = [float(sum(1 for x in r if x == L)) for L in range(2, 8)]
    return ind + [sw] + counts


def windows(seq: str) -> List[Tuple[List[float], float, int]]:
    out = []
    for t in range(7, len(seq)):
        hist = seq[t - 7:t]
        out.append((window_features(hist), 1.0 if seq[t] == "H" else 0.0, t))
    return out


def _design(seqs: Dict[str, str]):
    X, y, g, pos = [], [], [], []
    for pid, s in seqs.items():
        for f, target, t in windows(s):
            X.append(f); y.append(target); g.append(pid); pos.append(t)
    return np.array(X, float), np.array(y, float), g, np.array(pos)


def fit_cell(dev: Dict[str, str], tag: str) -> Dict[str, Any]:
    """Grouped five-fold alpha selection on development parents, refit on all."""
    if len(dev) < 10:
        return {"status": "insufficient", "n_dev_parents": len(dev)}
    X, y, groups, pos = _design(dev)
    fmap = fold_of(sorted(dev.keys()), C.CV_FOLDS, "lasso", tag)
    folds = np.array([fmap[gid] for gid in groups])
    lo, hi, n = C.LASSO_ALPHAS_LOG10
    alphas = list(np.logspace(lo, hi, int(n)))
    tuning = []
    for a in alphas:
        mses = []
        for f in range(C.CV_FOLDS):
            tr, va = folds != f, folds == f
            if va.sum() == 0:
                continue
            if np.var(y[tr]) == 0:
                pred = np.full(va.sum(), y[tr].mean())
            else:
                m = make_pipeline(StandardScaler(), Lasso(alpha=a, max_iter=C.LASSO_MAX_ITER, tol=C.LASSO_TOL, selection="cyclic"))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m.fit(X[tr], y[tr])
                pred = m.predict(X[va])
            mses.append(float(np.mean((pred - y[va]) ** 2)))
        tuning.append({"alpha": a, "cv_mse": float(np.mean(mses))})
    best_mse = min(r["cv_mse"] for r in tuning)
    best_alpha = max(r["alpha"] for r in tuning if r["cv_mse"] <= best_mse + 1e-12)
    out = {"status": "ok", "recipe": RECIPE, "n_dev_parents": len(dev), "n_dev_windows": int(len(y)),
           "alpha": best_alpha, "tuning": tuning, "train_mean": float(y.mean()),
           "train_pos_mean": {int(t): float(y[pos == t].mean()) for t in sorted(set(pos.tolist()))}}
    if np.var(y) == 0:
        out["status"] = "degenerate_constant_target"
        out["model"] = None
    else:
        m = make_pipeline(StandardScaler(), Lasso(alpha=best_alpha, max_iter=C.LASSO_MAX_ITER, tol=C.LASSO_TOL, selection="cyclic"))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            m.fit(X, y)
            out["convergence_warnings"] = [str(x.message)[:200] for x in w]
        out["model"] = m
        out["coefficients"] = [float(c) for c in m[-1].coef_]
        out["intercept"] = float(m[-1].intercept_)
    return out


def evaluate(fit: Dict[str, Any], test: Dict[str, str], tag: str) -> Dict[str, Any]:
    if fit.get("status") not in ("ok", "degenerate_constant_target") or not test:
        return {"status": fit.get("status", "no_test"), "n_test_parents": len(test)}
    per_parent = []
    for pid, s in test.items():
        W = windows(s)
        X = np.array([w[0] for w in W]); y = np.array([w[1] for w in W]); t = [w[2] for w in W]
        raw = fit["model"].predict(X) if fit["model"] is not None else np.full(len(y), fit["train_mean"])
        clip = np.clip(raw, 0, 1)
        posm = np.array([fit["train_pos_mean"].get(int(ti), fit["train_mean"]) for ti in t])
        per_parent.append({
            "parent_id": pid,
            "mse_lasso_raw": float(np.mean((raw - y) ** 2)),
            "brier_lasso_clipped": float(np.mean((clip - y) ** 2)),
            "mse_half": float(np.mean((0.5 - y) ** 2)),
            "mse_train_mean": float(np.mean((fit["train_mean"] - y) ** 2)),
            "mse_position_mean": float(np.mean((posm - y) ** 2)),
            "n_out_of_range": int(np.sum((raw < 0) | (raw > 1))),
        })
    keys = ["mse_lasso_raw", "brier_lasso_clipped", "mse_half", "mse_train_mean", "mse_position_mean"]
    summary = {k: float(np.mean([r[k] for r in per_parent])) for k in keys}
    rng = random.Random(C.derive_seed("bootstrap", "lasso", tag))
    imp = {"vs_half": [], "vs_train_mean": [], "vs_position_mean": []}
    n = len(per_parent)
    for _ in range(C.N_BOOT):
        sm = [per_parent[rng.randrange(n)] for _ in range(n)]
        L = np.mean([r["mse_lasso_raw"] for r in sm])
        imp["vs_half"].append(np.mean([r["mse_half"] for r in sm]) - L)
        imp["vs_train_mean"].append(np.mean([r["mse_train_mean"] for r in sm]) - L)
        imp["vs_position_mean"].append(np.mean([r["mse_position_mean"] for r in sm]) - L)
    ci = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in imp.items()}
    point = {"vs_half": summary["mse_half"] - summary["mse_lasso_raw"],
             "vs_train_mean": summary["mse_train_mean"] - summary["mse_lasso_raw"],
             "vs_position_mean": summary["mse_position_mean"] - summary["mse_lasso_raw"]}
    return {"status": "ok", "n_test_parents": n, "n_unique_test_strings": len(set(test.values())),
            "summary": summary, "improvement": point, "improvement_ci95": ci,
            "out_of_range_predictions": int(sum(r["n_out_of_range"] for r in per_parent)),
            "per_parent": per_parent}
