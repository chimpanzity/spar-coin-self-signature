"""External comparators (Section 10.1-10.2). All fits use development data only.

EmpiricalPrefixObserver is a bounded external comparator, not an ideal
observer or an upper bound on external knowledge.
"""
from __future__ import annotations

import math
import random
import warnings
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config as C
from .corpus import describe, runs

# ---------------------------------------------------------------------------
# Empirical-prefix observer
# ---------------------------------------------------------------------------


class PrefixModel:
    """One source x prompt cell."""

    def __init__(self, seqs: Sequence[str]):
        self.n = len(seqs)
        L = C.SEQ_LEN
        self.heads_at = [sum(1 for s in seqs if s[t] == "H") for t in range(L)]
        self.pos = [(self.heads_at[t] + 0.5) / (self.n + 1) for t in range(L)]
        self.n_pref: Dict[str, int] = defaultdict(int)
        self.h_next: Dict[str, int] = defaultdict(int)
        for s in seqs:
            for t in range(L):
                u = s[:t]
                self.n_pref[u] += 1
                if s[t] == "H":
                    self.h_next[u] += 1
        k = C.PREFIX_LEN
        self.n10: Dict[str, int] = defaultdict(int)
        self.h10: Dict[Tuple[str, int], int] = defaultdict(int)
        for s in seqs:
            u = s[:k]
            self.n10[u] += 1
            for t in range(k, L):
                if s[t] == "H":
                    self.h10[(u, t)] += 1

    def one_step(self, u: str) -> float:
        t = len(u)
        return (self.h_next.get(u, 0) + 2 * self.pos[t]) / (self.n_pref.get(u, 0) + 2)

    def loglik(self, x: str) -> float:
        ll = 0.0
        for t in range(len(x)):
            f = self.one_step(x[:t])
            ll += math.log(f if x[t] == "H" else 1 - f)
        return ll

    def direct(self, u10: str) -> List[float]:
        k = C.PREFIX_LEN
        n = self.n10.get(u10, 0)
        return [(self.h10.get((u10, t), 0) + 2 * self.pos[t]) / (n + 2) for t in range(k, C.SEQ_LEN)]

    def position(self) -> List[float]:
        return self.pos[C.PREFIX_LEN:]


class Observer:
    """Three-source observer within one prompt."""

    def __init__(self, train: Dict[str, Sequence[str]]):
        self.models = {g: PrefixModel(s) for g, s in train.items() if len(s) > 0}

    def ready(self) -> bool:
        return all(g in self.models for g in C.CORE_ORDER)

    def posterior(self, x: str) -> Dict[str, float]:
        lls = {g: m.loglik(x) for g, m in self.models.items()}
        mx = max(lls.values())
        w = {g: math.exp(v - mx) for g, v in lls.items()}
        s = sum(w.values())
        return {g: v / s for g, v in w.items()}

    def forecast_known(self, g: str, u10: str) -> List[float]:
        return self.models[g].direct(u10)

    def forecast_withheld(self, u10: str) -> List[float]:
        q = self.posterior(u10)
        fc = {g: self.models[g].direct(u10) for g in self.models}
        return [sum(q[g] * fc[g][i] for g in self.models) for i in range(C.SEQ_LEN - C.PREFIX_LEN)]

    def p_same(self, x: str, y: str) -> float:
        qx, qy = self.posterior(x), self.posterior(y)
        s = sum(qx[g] * qy[g] for g in self.models)
        return 2 * s / (1 + s)


def brier(p: Sequence[float], suffix: str) -> float:
    return sum((pi - (1.0 if c == "H" else 0.0)) ** 2 for pi, c in zip(p, suffix)) / len(suffix)


def fold_of(ids: Sequence[str], k: int, *seed_parts) -> Dict[str, int]:
    sh = list(ids)
    random.Random(C.derive_seed("folds", *seed_parts)).shuffle(sh)
    return {pid: i % k for i, pid in enumerate(sh)}


def headroom_oof(dev: Dict[Tuple[str, str], Dict[str, str]]) -> Dict[str, any]:
    """dev[(source,prompt)] -> {parent_id: seq}. Five-fold out-of-fold observer losses.

    Returns per-parent known/withheld/position losses and the I[g,p], I[g]
    summaries defined in Section 5.5.
    """
    k = C.CV_FOLDS
    folds = {cell: fold_of(sorted(d.keys()), k, "headroom", *cell) for cell, d in dev.items()}
    per_parent = []
    for p in C.PROMPT_ORDER:
        for f in range(k):
            train = {g: [s for pid, s in dev.get((g, p), {}).items() if folds[(g, p)][pid] != f] for g in C.CORE_ORDER}
            if any(len(v) == 0 for v in train.values()):
                continue
            obs = Observer(train)
            pooled_pos = [sum(obs.models[g].position()[i] for g in C.CORE_ORDER) / 3 for i in range(10)]
            for g in C.CORE_ORDER:
                for pid, s in dev.get((g, p), {}).items():
                    if folds[(g, p)][pid] != f:
                        continue
                    u, y = s[:10], s[10:]
                    q = obs.posterior(u)
                    per_parent.append({
                        "parent_id": pid, "source": g, "prompt": p, "fold": f,
                        "B_known": brier(obs.forecast_known(g, u), y),
                        "B_withheld": brier(obs.forecast_withheld(u), y),
                        "B_source_position": brier(obs.models[g].position(), y),
                        "B_pooled_position": brier(pooled_pos, y),
                        "B_fair": brier([0.5] * 10, y),
                        "posterior_true_source": q[g],
                        "exact_prefix_support": obs.models[g].n10.get(u, 0),
                    })
    I_gp, prefix_value = {}, {}
    for g in C.CORE_ORDER:
        for p in C.PROMPT_ORDER:
            rs = [r for r in per_parent if r["source"] == g and r["prompt"] == p]
            if rs:
                I_gp[f"{g}|{p}"] = sum(r["B_withheld"] - r["B_known"] for r in rs) / len(rs)
                prefix_value[f"{g}|{p}"] = sum(r["B_source_position"] - r["B_known"] for r in rs) / len(rs)
            else:
                I_gp[f"{g}|{p}"] = None
                prefix_value[f"{g}|{p}"] = None
    I_g = {}
    for g in C.CORE_ORDER:
        vals = [I_gp[f"{g}|{p}"] for p in C.PROMPT_ORDER]
        I_g[g] = sum(vals) / 2 if all(v is not None for v in vals) else None
    finite = [v for v in I_g.values() if v is not None]
    review = (len(finite) < 3) or all(v < C.HEADROOM_THRESHOLD for v in finite)
    return {"per_parent": per_parent, "I_gp": I_gp, "I_g": I_g, "prefix_value": prefix_value,
            "headroom_review_required": review, "threshold": C.HEADROOM_THRESHOLD}


# ---------------------------------------------------------------------------
# Heads-count classifier and pair rankings
# ---------------------------------------------------------------------------

class HeadsCountClassifier:
    def __init__(self, train: Dict[str, Sequence[str]]):
        self.hist = {}
        for g, seqs in train.items():
            h = [0.5] * 21
            for s in seqs:
                h[s.count("H")] += 1
            tot = sum(h)
            self.hist[g] = [v / tot for v in h]

    def posterior(self, x: str) -> Dict[str, float]:
        w = {g: h[x.count("H")] for g, h in self.hist.items()}
        s = sum(w.values())
        return {g: v / s for g, v in w.items()}

    def p_same(self, x: str, y: str) -> float:
        qx, qy = self.posterior(x), self.posterior(y)
        s = sum(qx[g] * qy[g] for g in self.hist)
        return 2 * s / (1 + s)


def rank_scores(x: str, y: str) -> Dict[str, float]:
    return {"equality": float(x == y),
            "positional_agreement": sum(a == b for a, b in zip(x, y)) / len(x),
            "neg_heads_diff": -abs(x.count("H") - y.count("H"))}


# ---------------------------------------------------------------------------
# Regularized comparators
# ---------------------------------------------------------------------------

def _desc4(s: str) -> List[float]:
    d = describe(s)
    return [d["heads"], d["switches"], d["longest_run"], d["terminal_run"]]


def pair_features(x: str, y: str) -> List[float]:
    a, b = _desc4(x), _desc4(y)
    feats = []
    for u, v in zip(a, b):
        feats += [u + v, abs(u - v)]
    feats += [sum(c1 != c2 for c1, c2 in zip(x, y)), float(x == y)]
    return feats


def _fit_logit(X, y, C_val, w=None):
    model = make_pipeline(StandardScaler(), LogisticRegression(C=C_val, max_iter=5000))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(X, y, logisticregression__sample_weight=w)
    return model


class PairL2:
    """L2 logistic pair classifier; block-grouped five-fold selection of C."""

    def __init__(self, X: List[List[float]], y: List[int], groups: List[str], seed_tag: str):
        X, y = np.array(X, float), np.array(y, int)
        ug = sorted(set(groups))
        fmap = fold_of(ug, C.CV_FOLDS, "pairl2", seed_tag)
        folds = np.array([fmap[g] for g in groups])
        scores = {}
        for c in C.L2_C_GRID:
            losses = []
            for f in range(C.CV_FOLDS):
                tr, va = folds != f, folds == f
                if va.sum() == 0 or len(set(y[tr])) < 2:
                    continue
                m = _fit_logit(X[tr], y[tr], c)
                p = m.predict_proba(X[va])[:, 1]
                losses.append(float(np.mean((p - y[va]) ** 2)))
            scores[c] = float(np.mean(losses)) if losses else float("inf")
        best = min(sorted(scores), key=lambda c: (scores[c], c))
        self.cv_scores, self.C = scores, best
        self.model = _fit_logit(X, y, best) if len(set(y)) == 2 else None
        self.const = float(np.mean(y))

    def predict(self, X: List[List[float]]) -> List[float]:
        if self.model is None:
            return [self.const] * len(X)
        return list(self.model.predict_proba(np.array(X, float))[:, 1])


def prefix_features(u10: str) -> List[float]:
    r = runs(u10)
    return ([1.0 if c == "H" else 0.0 for c in u10]
            + [sum(1 for a, b in zip(u10, u10[1:]) if a != b) / 9.0, float(max(r)), float(r[-1])])


class CompletionL2:
    """Ten per-horizon L2 logistic regressions on first-ten features."""

    def __init__(self, seqs: List[str], ids: List[str], weights: Optional[List[float]], seed_tag: str):
        X = np.array([prefix_features(s[:10]) for s in seqs], float)
        Y = np.array([[1 if c == "H" else 0 for c in s[10:]] for s in seqs], int)
        w = np.array(weights if weights is not None else [1.0] * len(seqs), float)
        fmap = fold_of(sorted(ids), C.CV_FOLDS, "complL2", seed_tag)
        folds = np.array([fmap[i] for i in ids])
        n = len(seqs)
        scores = {}
        for c in C.L2_C_GRID:
            losses = []
            for f in range(C.CV_FOLDS):
                tr, va = folds != f, folds == f
                if va.sum() == 0 or tr.sum() == 0:
                    continue
                P = np.column_stack([self._fit_one(X[tr], Y[tr, h], w[tr], c).predict(X[va]) for h in range(10)])
                losses.append(float(np.mean((P - Y[va]) ** 2)))
            scores[c] = float(np.mean(losses)) if losses else float("inf")
        self.cv_scores = scores
        self.C = min(sorted(scores), key=lambda c: (scores[c], c))
        self.models = [self._fit_one(X, Y[:, h], w, self.C) for h in range(10)]

    class _Const:
        def __init__(self, p):
            self.p = p

        def predict(self, X):
            return np.full(len(X), self.p)

    class _Wrap:
        def __init__(self, m):
            self.m = m

        def predict(self, X):
            return self.m.predict_proba(X)[:, 1]

    def _fit_one(self, X, y, w, c):
        if len(set(y.tolist())) < 2:
            h = float(np.sum(w * y)); n = float(np.sum(w))
            return self._Const((h + 0.5) / (n + 1))
        return self._Wrap(_fit_logit(X, y, c, w))

    def predict(self, u10: str) -> List[float]:
        X = np.array([prefix_features(u10)], float)
        return [float(m.predict(X)[0]) for m in self.models]
