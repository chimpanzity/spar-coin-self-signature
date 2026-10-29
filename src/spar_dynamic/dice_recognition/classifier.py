"""External source discriminability (handoff section 6): development data only.

Primary: L2 logistic regression (C=1) on the prespecified features, standardized inside each training fold,
grouped stratified 5-fold CV with identical strings kept in one fold (labels Qwen=1, Mistral=0). Pooled
out-of-fold ROC AUC is the gate statistic (>= 0.65). Also: balanced accuracy and confusion at 0.5,
nearest-centroid and single-feature (switch fraction) benchmarks under the same CV, a 1,000-permutation label
reference with the same grouped CV, and a bootstrap over unique-sequence groups.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from spar_dynamic.dice_recognition import config as C


def make_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))


def oof_scores(X, y, groups, kind="logreg", seed=C.PERMUTATION_SEED):
    cv = StratifiedGroupKFold(n_splits=C.CV_FOLDS, shuffle=True, random_state=seed)
    s = np.full(len(y), np.nan)
    for tr, te in cv.split(X, y, groups):
        if kind == "logreg":
            m = make_model().fit(X[tr], y[tr])
            s[te] = m.predict_proba(X[te])[:, 1]
        elif kind == "centroid":
            sc = StandardScaler().fit(X[tr])
            Z, Zt = sc.transform(X[tr]), sc.transform(X[te])
            c1, c0 = Z[y[tr] == 1].mean(0), Z[y[tr] == 0].mean(0)
            s[te] = np.linalg.norm(Zt - c0, axis=1) - np.linalg.norm(Zt - c1, axis=1)
        else:                                            # single feature column index `kind`
            m = make_model().fit(X[tr][:, [kind]], y[tr])
            s[te] = m.predict_proba(X[te][:, [kind]])[:, 1]
    return s


def evaluate(X, y, groups, switch_col):
    s = oof_scores(X, y, groups)
    auc = roc_auc_score(y, s)
    pred = (s >= 0.5).astype(int)
    rng = np.random.default_rng(C.PERMUTATION_SEED)
    perm = []
    for _ in range(C.N_PERMUTATIONS):
        yp = rng.permutation(y)
        perm.append(roc_auc_score(yp, oof_scores(X, yp, groups)))
    perm = np.array(perm)
    ug = np.unique(groups)
    brng = np.random.default_rng(C.BOOTSTRAP_SEED)
    boots = []
    for _ in range(2000):
        pick = brng.choice(ug, size=len(ug), replace=True)
        idx = np.concatenate([np.where(groups == g)[0] for g in pick])
        if len(np.unique(y[idx])) == 2:
            boots.append(roc_auc_score(y[idx], s[idx]))
    return dict(
        cv_auc=float(auc), balanced_accuracy=float(balanced_accuracy_score(y, pred)),
        confusion=confusion_matrix(y, pred, labels=[1, 0]).tolist(),
        auc_bootstrap_ci95_by_group=[float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        permutation=dict(n=len(perm), mean=float(perm.mean()), p95=float(np.percentile(perm, 95)),
                         p_value_ge_observed=float((1 + (perm >= auc).sum()) / (1 + len(perm)))),
        benchmarks=dict(majority_auc=0.5, majority_balanced_accuracy=0.5,
                        nearest_centroid_cv_auc=float(roc_auc_score(y, oof_scores(X, y, groups, "centroid"))),
                        switch_fraction_only_cv_auc=float(roc_auc_score(y, oof_scores(X, y, groups, switch_col)))),
        n=len(y), n_unique_groups=int(len(ug)), gate_threshold=C.AUC_GATE, gate_pass=bool(auc >= C.AUC_GATE),
        oof_scores=s.tolist())
