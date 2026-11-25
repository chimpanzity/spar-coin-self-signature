"""Prespecified analysis for Experiment 36. Pairwise log odds of the direct-generation policy over unused faces; nested grouped CV.

Every fitted model is a weighted kernel ridge on canonical pairs (i < j) whose kernel is antisymmetric in the pair: for candidate kernel
k((x,i),(x',i')), K = k(i,i') - k(i,j') - k(j,i') + k(j,j'). A face-indexed coefficient block on features z(x) is k = delta(i,i') z.z', so the
activation probe is the handoff's signed difference of face-indexed linear coefficients (on train-only standardised, train-only PCA scores).
Pair weights give equal weight to prefixes within family and to families. Every block kernel is scaled to mean diagonal 1 on training pairs.
"""

from __future__ import annotations

import csv
import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np  # noqa: E402

from spar_dynamic.dice_scaffolding.design import faces_of  # noqa: E402
from spar_dynamic.hidden_policy import design as D  # noqa: E402

LAMBDAS = tuple(10.0 ** e for e in np.arange(-3, 2.01, 0.5))
HIST = ("linear", "rbf1", "rbf2", "relational", "rbf2+relational")
OMEGAS = (0.1, 1.0, 10.0)                    # weight of the forecast-output block
ALPHAS = (0.0, 0.1, 1.0, 10.0)               # weight of the activation block (0 = not used)
RANK = 32                                    # matched train-only PCA rank, every activation and logit block
RANK_SENS = (8, 16, 64)
BOOT_B, BOOT_SEED = 10_000, 361125
N_PERM, PERM_SEED = 100, 361126
OTHER = {"qwen": "mistral", "mistral": "qwen"}


# ---------- design matrices ----------

class Bank:
    """Eligible prefixes, candidates (prefix, unused face) and canonical pairs."""

    def __init__(self, prefixes=None):
        rows = [b for b in D.bank() if b["eligible"]] if prefixes is None else prefixes
        self.prefix = [b["prefix"] for b in rows]
        self.x = [faces_of(p) for p in self.prefix]
        self.family = np.array([b["family"] for b in rows])
        self.fold = np.array([b["fold"] for b in rows])
        self.roll = np.array([b["roll"] for b in rows])
        self.cand = [(n, f) for n, x in enumerate(self.x) for f in D.FACES if f not in x]
        ci = {c: k for k, c in enumerate(self.cand)}
        self.cx, self.cf = np.array([c[0] for c in self.cand]), np.array([c[1] for c in self.cand])
        self.pairs = [(n, i, j) for n, x in enumerate(self.x) for i, j in itertools.combinations([f for f in D.FACES if f not in x], 2)]
        self.px = np.array([p[0] for p in self.pairs])
        self.a = np.array([ci[(n, i)] for n, i, j in self.pairs])
        self.b = np.array([ci[(n, j)] for n, i, j in self.pairs])
        self.pfam = self.family[self.px]
        self.same_face = (self.cf[:, None] == self.cf[None, :]).astype(float)

    def weights(self, pidx):
        """1 / (pairs in prefix x prefixes in family), mean 1 over the given pairs."""
        px = self.px[pidx]
        fam = self.family[px]
        npair = {n: (px == n).sum() for n in set(px)}
        npre = {f: len(set(px[fam == f])) for f in set(fam)}
        w = np.array([1 / (npair[n] * npre[f]) for n, f in zip(px, fam)])
        return w / w.mean()

    def pairk(self, kc):
        a, b = self.a, self.b
        return kc[np.ix_(a, a)] - kc[np.ix_(a, b)] - kc[np.ix_(b, a)] + kc[np.ix_(b, b)]

    def faced(self, kx):
        """Face-indexed blocks on a prefix kernel."""
        return self.pairk(kx[np.ix_(self.cx, self.cx)] * self.same_face)


def history_kernels(bk):
    n = len(bk.x)
    oh = np.zeros((n, 8, 6))
    for r, x in enumerate(bk.x):
        for k, f in enumerate(x):
            oh[r, k, f - 1] = 1                              # position from the start
        for k, f in enumerate(reversed(x)):
            oh[r, 4 + k, f - 1] = 1                          # position from the end
    z = np.concatenate([oh.reshape(n, -1), (bk.roll[:, None] == 5).astype(float)], 1)
    lin = z @ z.T
    d2 = ((z[:, None] - z[None]) ** 2).sum(-1)
    c = []
    for (r, f) in bk.cand:
        x = bk.x[r]
        last = [f - x[-k] for k in (1, 2, 3)]
        oneh = [0.7 * (f == v) for v in D.FACES]
        c.append(oneh + [v / 2.5 for v in last] + [abs(v) / 2.5 for v in last] + [float(len(x) == 4)])
    c = np.array(c)
    rel = np.exp(-((c[:, None] - c[None]) ** 2).sum(-1) / 2)
    return {"linear": bk.faced(lin), "rbf1": bk.faced(np.exp(-d2 / 4)), "rbf2": bk.faced(np.exp(-d2 / 16)), "relational": bk.pairk(rel)}


def pca_kernel(H, tr, rank):
    """Linear kernel of train-only standardised, train-only PCA scores (H: prefixes x d). Returns kernel over all rows of H."""
    mu, sd = H[tr].mean(0), H[tr].std(0)
    Z = (H - mu) / np.where(sd > 1e-6, sd, np.inf)
    u, s, vt = np.linalg.svd(Z[tr], full_matrices=False)
    P = Z @ vt[:rank].T
    return P @ P.T


def gram_pca_kernel(Kfull, tr, rank):
    """PCA (train-centred, rank) on rows known only through their inner products."""
    m = Kfull[:, tr].mean(1)
    Kc = Kfull - m[:, None] - m[None, :] + m[tr].mean()
    w, v = np.linalg.eigh(Kc[np.ix_(tr, tr)])
    o = np.argsort(w)[::-1][:rank]
    P = Kc[:, tr] @ (v[:, o] / np.sqrt(np.maximum(w[o], 1e-9)))
    return P @ P.T


def scaled(K, tr):
    d = K[tr, tr].mean()
    return K / d if d > 0 else K


def solve(K, y, w, tr, lam):
    return np.linalg.solve(K[np.ix_(tr, tr)] + lam * np.diag(1 / w), y[tr])


# ---------- data ----------

class Data:
    def __init__(self, root=None, rows=None, states=None, gram=None):
        root = Path(root or D.EXP)
        self.bk = bk = Bank()
        pos = {p: n for n, p in enumerate(bk.prefix)}
        self.L, self.mass, self.argmax, self.S, self.Glogit = {}, {}, {}, {}, {}
        for m in D.MODELS:
            rs = rows[m] if rows else [json.loads(x) for x in (root / "raw" / m / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
            st = states[m] if states is not None else np.load(root / "arrays" / m / "states_bf16_uint16.npy", mmap_mode="r")
            M = gram[m] if gram is not None else np.load(root / "arrays" / m / "head_gram_centered_f32.npy")
            for mode in D.MODES:
                sel = {pos[r["prefix"]]: r for r in rs if r["mode"] == mode and r["prefix"] in pos}
                assert len(sel) == len(bk.prefix), (m, mode, len(sel))
                o = [sel[n] for n in range(len(bk.prefix))]
                self.L[m, mode] = np.array([r["l"] for r in o])
                self.mass[m, mode] = np.array([r["mass"] for r in o])
                self.argmax[m, mode] = [r["argmax_token"] for r in o]
                A = st[[r["row"] for r in o]]
                A = (A.astype(np.uint32) << 16).view(np.float32) if A.dtype == np.uint16 else np.asarray(A, np.float32)
                for k, s in enumerate(D.SLOTS[:4]):
                    self.S[m, mode, s] = A[:, k].astype(np.float32)
                if mode == "agent":
                    F = A[:, 4].astype(np.float64)
                    self.Glogit[m] = (F @ M.astype(np.float64)) @ F.T
        f = np.array(D.FACES)
        self.y = {t: self.pairdiff(self.L[t, "direct"]) for t in D.MODELS}
        self.unused = np.array([[v not in x for v in f] for x in bk.x])

    def pairdiff(self, L):
        return np.array([L[n, i - 1] - L[n, j - 1] for n, i, j in self.bk.pairs])

    def out_kernel(self, m, mode, tr_x):
        """Forecast-output block: face-shared slope on candidate log-probability, and face-indexed linear terms in the six
        log-probabilities and the log digit mass (train-only standardised)."""
        bk = self.bk
        c = np.array([self.L[m, mode][n, f - 1] for n, f in bk.cand])
        c = c / max(c[np.isin(bk.cx, tr_x)].std(), 1e-6)
        z = np.concatenate([self.L[m, mode], np.log(np.maximum(self.mass[m, mode], 1e-30))[:, None]], 1)
        z = (z - z[tr_x].mean(0)) / np.maximum(z[tr_x].std(0), 1e-6)
        return bk.pairk(np.outer(c, c)), bk.faced(z @ z.T / z.shape[1])


_CACHE = {}


class Split:
    """Kernels for one training set of prefixes, scaled on its training pairs."""

    def __init__(self, data, hk, train_fams):
        self.d, bk = data, data.bk
        self.trx = np.where(np.isin(bk.family, list(train_fams)))[0]
        self.trp = np.where(np.isin(bk.pfam, list(train_fams)))[0]
        self.w = bk.weights(self.trp)
        self.hist = {k: scaled(v, self.trp) for k, v in hk.items()}
        self.hist["rbf2+relational"] = (self.hist["rbf2"] + self.hist["relational"]) / 2
        self.bias = scaled(bk.pairk(bk.same_face), self.trp)
        self._c = {}

    def memo(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    def out(self, m, mode):
        def f():
            a, b = self.d.out_kernel(m, mode, self.trx)
            return (scaled(a, self.trp) + scaled(b, self.trp)) / 2
        return self.memo(("out", m, mode), f)

    def act(self, m, mode, slot, rank=RANK):
        return self.memo(("act", m, mode, slot, rank), lambda: scaled(self.d.bk.faced(pca_kernel(self.d.S[m, mode, slot], self.trx, rank)), self.trp))

    def logit(self, m, rank=RANK):
        return self.memo(("logit", m, rank), lambda: scaled(self.d.bk.faced(gram_pca_kernel(self.d.Glogit[m], self.trx, rank)), self.trp))


def block(split, spec):
    """spec: tuple of (name, args..., weight)."""
    K = split.bias.copy()
    for s in spec:
        name, w = s[0], s[-1]
        if w == 0:
            continue
        K += w * (split.hist[s[1]] if name == "hist" else split.out(*s[1:-1]) if name == "out" else split.act(*s[1:-1]) if name == "act"
                  else split.logit(*s[1:-1]))
    return K


class CV:
    def __init__(self, data):
        self.data, self.bk = data, data.bk
        self.hk = history_kernels(self.bk)
        fams = sorted(set(self.bk.family))
        self.outer = []
        for k in range(D.N_OUTER):
            tr = [f for f in fams if D.folds()[f] != k]
            inn = D.inner_folds(tr)
            self.outer.append(dict(test=[f for f in fams if D.folds()[f] == k], full=Split(data, self.hk, tr),
                                   inner=[(Split(data, self.hk, [f for f in tr if inn[f] != q]), [f for f in tr if inn[f] == q]) for q in range(D.N_INNER)]))

    def famloss(self, pidx, e2):
        """Equal weight per pair within prefix, prefix within family, family."""
        w = self.bk.weights(pidx)
        return float((w * e2).sum() / w.sum())

    def inner_loss(self, o, spec, y):
        """Inner CV loss for every lambda."""
        tot = np.zeros(len(LAMBDAS))
        for sp, val in o["inner"]:
            K = block(sp, spec)
            va = np.where(np.isin(self.bk.pfam, val))[0]
            for n, lam in enumerate(LAMBDAS):
                a = solve(K, y, sp.w, sp.trp, lam)
                tot[n] += self.famloss(va, (K[np.ix_(va, sp.trp)] @ a - y[va]) ** 2) * len(val)
        return tot / sum(len(v) for _, v in o["inner"])

    def fit(self, specs, y, cross=None):
        """Nested CV over candidate specs x lambda. specs: list, or function(outer index) -> list.
        Returns out-of-fold predictions, chosen (spec, lambda) per fold. cross: optional function(Split) -> (test x train pair kernel)."""
        oof, chosen = np.full(len(y), np.nan), []
        for k, o in enumerate(self.outer):
            cand = specs(k) if callable(specs) else specs
            best = min(((l, s, lam) for s in cand for l, lam in zip(self.inner_loss(o, s, y), LAMBDAS)), key=lambda t: t[0])
            _, s, lam = best
            sp = o["full"]
            te = np.where(np.isin(self.bk.pfam, o["test"]))[0]
            K = block(sp, s)
            a = solve(K, y, sp.w, sp.trp, lam)
            Kc = K if cross is None else cross(sp, s)
            oof[te] = Kc[np.ix_(te, sp.trp)] @ a
            chosen.append((s, lam))
        return oof, chosen


# ---------- model families ----------

def spec_hist():
    return [(("hist", h, 1.0),) for h in HIST]


def spec_io(m, mode):
    return [(("hist", h, 1.0), ("out", m, mode, w)) for h in HIST for w in OMEGAS]


def add(base_chosen, extra):
    """Base spec chosen in each outer fold, plus a block with a tuned weight."""
    return lambda k: [base_chosen[k][0] + (extra + (a,),) for a in ALPHAS]


def transfer_kernel(data, m, mode_to, slot):
    """Test rows use mode_to activations, training rows agent activations; standardisation and PCA from agent training rows."""
    def f(sp, spec):
        H, T = data.S[m, "agent", slot], data.S[m, mode_to, slot]
        tr = sp.trx
        mu, sd = H[tr].mean(0), H[tr].std(0)
        q = np.where(sd > 1e-6, sd, np.inf)
        Z, Y = (H - mu) / q, (T - mu) / q
        vt = np.linalg.svd(Z[tr], full_matrices=False)[2][:RANK]
        P, R = Z @ vt.T, Y @ vt.T
        bk = data.bk
        raw = bk.faced(P @ P.T)
        c = (R @ P.T)[np.ix_(bk.cx, bk.cx)] * bk.same_face
        K = c[np.ix_(bk.a, bk.a)] - c[np.ix_(bk.a, bk.b)] - c[np.ix_(bk.b, bk.a)] + c[np.ix_(bk.b, bk.b)]
        return sp.bias + K / raw[sp.trp, sp.trp].mean()
    return f


def fam_losses(bk, e2, mask=None):
    """Per-family loss (pairs within prefix, prefixes within family), over prefixes in mask."""
    out = {}
    for f in sorted(set(bk.family)):
        pr = [n for n in np.where(bk.family == f)[0] if mask is None or mask[n]]
        v = [e2[bk.px == n].mean() for n in pr]
        if v:
            out[f] = float(np.mean(v))
    return out


def boot(stat, fams, B=BOOT_B):
    """Percentile interval of stat(index array into fams), resampling families."""
    rng = np.random.Generator(np.random.PCG64(BOOT_SEED))
    idx = rng.integers(0, len(fams), size=(B, len(fams)))
    v = stat(idx)
    return [float(q) for q in np.percentile(v, [2.5, 97.5])]


def summ(d):
    """dict family -> value: mean, bootstrap CI, positives, leave-one-family-out range."""
    f = sorted(d)
    x = np.array([d[k] for k in f])
    loo = [np.delete(x, k).mean() for k in range(len(x))]
    return dict(mean=float(x.mean()), ci95=boot(lambda i: x[i].mean(1), f), positive=int((x > 0).sum()), families=len(f),
                loo=[float(min(loo)), float(max(loo))])


# ---------- driver (tasks run in worker processes) ----------

_W = {}


def _init(loader, args):
    _W["cv"] = CV(loader(*args))


def task(name):
    cv = _W["cv"]
    d = cv.data
    for o in cv.outer:                                     # bound worker memory: block kernels are cached within a task only
        for sp in [o["full"], *(q for q, _ in o["inner"])]:
            sp._c.clear()
    kind, *r = name
    if kind == "bias":
        return cv.fit([()], d.y[r[0]])
    if kind == "hist":
        return cv.fit(spec_hist(), d.y[r[0]])
    if kind == "outcal":                                   # output-only calibration: face bias + output block
        t, m, mode = r
        return cv.fit([(("out", m, mode, w),) for w in OMEGAS], d.y[t])
    if kind == "actonly":
        t, m, mode, slot, rank = r
        return cv.fit([(("act", m, mode, slot, rank, 1.0),)], d.y[t])
    if kind == "transfer":
        t, m, to, slot = r
        return cv.fit([(("act", m, "agent", slot, RANK, 1.0),)], d.y[t], cross=transfer_kernel(d, m, to, slot))
    if kind in ("chain", "directchain"):                   # io -> io + act
        t, m, mode, slot, rank = r
        base = cv.fit(spec_io(m, mode), d.y[t])
        am = mode if kind == "chain" else "direct"
        return dict(io=base, ioact=cv.fit(add(base[1], ("act", m, am, slot, rank)), d.y[t]))
    if kind == "logitchain":
        t, m = r
        base = cv.fit(spec_hist(), d.y[t])
        L = cv.fit(lambda k: [base[1][k][0] + (("logit", m, RANK, a),) for a in ALPHAS], d.y[t])
        return dict(histlogit=L, histlogitact=cv.fit(add(L[1], ("act", m, "agent", D.PRIMARY_SLOT, RANK)), d.y[t]))
    if kind == "stack":                                    # history + both outputs + other model's act, then + own act
        t, m, slot = r
        io = cv.fit([(("hist", h, 1.0), ("out", m, "agent", w), ("out", OTHER[m], "agent", w)) for h in HIST for w in OMEGAS], d.y[t])
        o = cv.fit(add(io[1], ("act", OTHER[m], "agent", slot, RANK)), d.y[t])
        return dict(io2=io, io2other=o, io2both=cv.fit(add(o[1], ("act", m, "agent", slot, RANK)), d.y[t]))
    if kind == "perm":                                     # permute whole target profiles within (family, unused set)
        t, m, seed = r
        rng = np.random.Generator(np.random.PCG64([PERM_SEED, seed]))
        bk = d.bk
        L = d.L[t, "direct"].copy()
        groups = {}
        for n, x in enumerate(bk.x):
            groups.setdefault((bk.family[n], tuple(sorted(x))), []).append(n)
        for g in groups.values():
            assert len(g) == 6
            L[g] = d.L[t, "direct"][np.array(g)[rng.permutation(6)]]
        y = d.pairdiff(L)
        base = cv.fit(spec_io(m, "agent"), y)
        ex = cv.fit(add(base[1], ("act", m, "agent", D.PRIMARY_SLOT, RANK)), y)
        lb, le = fam_losses(bk, (base[0] - y) ** 2), fam_losses(bk, (ex[0] - y) ** 2)
        return float(np.mean([lb[f] - le[f] for f in lb]))
    raise ValueError(name)


def task_list():
    P = D.PRIMARY_SLOT
    T = [(k, t) for k in ("bias", "hist") for t in D.MODELS]
    for t in D.MODELS:
        for m in D.MODELS:
            T += [("outcal", t, m, "agent"), ("logitchain", t, m), ("directchain", t, m, "agent", P, RANK)]
            T += [("chain", t, m, "agent", s, RANK) for s in D.SLOTS[:4]] + [("chain", t, m, "agent", P, r) for r in RANK_SENS]
            T += [("chain", t, m, p, P, RANK) for p in D.PROMPTS[1:]]
            T += [("actonly", t, m, mode, P, RANK) for mode in D.MODES]
            T += [("actonly", t, m, mode, s, RANK) for mode in ("agent", "direct") for s in D.SLOTS[:4] if s != P]
            T += [("transfer", t, m, p, P) for p in D.PROMPTS]
        T += [("stack", t, t, P), ("stack", t, OTHER[t], P)]
    T += [("perm", "qwen", "qwen", s) for s in range(N_PERM)]
    return T


def run_tasks(loader, args, tasks, workers):
    if workers <= 1:
        _init(loader, args)
        return {t: task(t) for t in tasks}
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(loader, args)) as ex:
        return dict(zip(tasks, ex.map(task, tasks)))


# ---------- reporting ----------

def pref(scores, unused):
    """Preferred unused face index per prefix."""
    return np.where(unused, scores, -np.inf).argmax(1)


def cand_scores(bk, pred):
    """Candidate scores implied by pair predictions (least squares; centred) -> prefixes x 6 (nan for used faces)."""
    out = np.full((len(bk.x), 6), np.nan)
    for n, x in enumerate(bk.x):
        fs = [f for f in D.FACES if f not in x]
        s = {f: 0.0 for f in fs}
        for p in np.where(bk.px == n)[0]:
            _, i, j = bk.pairs[p]
            s[i] += pred[p] / len(fs)
            s[j] -= pred[p] / len(fs)
        for f in fs:
            out[n, f - 1] = s[f]
    return out


def collect(data, R):
    """Named out-of-fold pair predictions per target."""
    bk, P = data.bk, {}
    for t in D.MODELS:
        Q = {"equal odds": np.zeros(len(bk.pairs)), "face bias": R["bias", t][0], "history": R["hist", t][0]}
        for m in D.MODELS:
            Q[f"raw forecast {m}"] = data.pairdiff(data.L[m, "agent"])
            Q[f"calibrated output {m}"] = R["outcal", t, m, "agent"][0]
            for s in D.SLOTS[:4]:
                c = R["chain", t, m, "agent", s, RANK]
                Q[f"history+output {m}"] = c["io"][0]
                Q[f"history+output+act {m} {s}"] = c["ioact"][0]
                for mode in ("agent", "direct"):
                    Q[f"act only {m} {mode} {s}"] = R["actonly", t, m, mode, s, RANK][0]
            for r in RANK_SENS:
                Q[f"history+output+act {m} {D.PRIMARY_SLOT} rank{r}"] = R["chain", t, m, "agent", D.PRIMARY_SLOT, r]["ioact"][0]
            for p in D.PROMPTS[1:]:
                c = R["chain", t, m, p, D.PRIMARY_SLOT, RANK]
                Q[f"history+output {m} [{p}]"], Q[f"history+output+act {m} [{p}]"] = c["io"][0], c["ioact"][0]
                Q[f"raw forecast {m} [{p}]"] = data.pairdiff(data.L[m, p])
                Q[f"act only {m} {p} {D.PRIMARY_SLOT}"] = R["actonly", t, m, p, D.PRIMARY_SLOT, RANK][0]
            for p in D.PROMPTS:
                Q[f"transfer agent->{p} {m}"] = R["transfer", t, m, p, D.PRIMARY_SLOT][0]
            Q[f"history+output+direct act {m}"] = R["directchain", t, m, "agent", D.PRIMARY_SLOT, RANK]["ioact"][0]
            Q[f"history+logits {m}"], Q[f"history+logits+act {m}"] = (R["logitchain", t, m][k][0] for k in ("histlogit", "histlogitact"))
            s = R["stack", t, m, D.PRIMARY_SLOT]
            for k, lab in (("io2", "history+both outputs"), ("io2other", f"history+both outputs+act {OTHER[m]}"),
                           ("io2both", f"history+both outputs+act {OTHER[m]}+act {m}")):
                Q[lab] = s[k][0]
        P[t] = Q
    return P


def specificity(Lf, fams):
    """Four normalised gains (act checkpoint x target) and the balanced own-minus-cross contrast, family bootstrap (ratios recomputed)."""
    A = {}
    for t in D.MODELS:
        A[t, "hist"] = np.array([Lf[t]["history"][f] for f in fams])
        for m in D.MODELS:
            A[t, m, "io"] = np.array([Lf[t][f"history+output {m}"][f] for f in fams])
            A[t, m, "act"] = np.array([Lf[t][f"history+output+act {m} {D.PRIMARY_SLOT}"][f] for f in fams])

    def cell(t, m, i):
        return (A[t, m, "io"][i] - A[t, m, "act"][i]).mean(-1) / A[t, "hist"][i].mean(-1)

    def contrast(i):
        return 0.5 * (cell("qwen", "qwen", i) + cell("mistral", "mistral", i) - cell("qwen", "mistral", i) - cell("mistral", "qwen", i))
    al = np.arange(len(fams))
    out = {f"act {m} -> target {t}": dict(gain=float(cell(t, m, al)), ci95=boot(lambda i: cell(t, m, i), fams)) for t in D.MODELS for m in D.MODELS}
    out["own minus cross (balanced)"] = dict(gain=float(contrast(al)), ci95=boot(contrast, fams))
    out["qwen target: own minus cross"] = dict(gain=float(cell("qwen", "qwen", al) - cell("qwen", "mistral", al)),
                                               ci95=boot(lambda i: cell("qwen", "qwen", i) - cell("qwen", "mistral", i), fams))
    return out


def wcsv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def policy_table(data):
    """(a) unused mass and (b) raw forecast ranking, by checkpoint, prompt and roll (families equally weighted)."""
    bk, rows = data.bk, []
    fam = lambda v, mask: float(np.mean([v[(bk.family == f) & mask].mean() for f in sorted(set(bk.family))]))
    for m in D.MODELS:
        for mode in D.MODES:
            L = data.L[m, mode]
            p = np.exp(L) / np.exp(L).sum(1, keepdims=True)
            um = (p * data.unused).sum(1)
            fp = pref(L, data.unused)
            for roll in ("all", 4, 5):
                k = np.ones(len(bk.x), bool) if roll == "all" else bk.roll == roll
                rows.append(dict(model=m, mode=mode, roll=roll, digit_mass=fam(data.mass[m, mode], k), unused_mass=fam(um, k),
                                 argmax_is_digit=fam(np.array([a in list("123456") for a in data.argmax[m, mode]], float), k),
                                 **{f"top_unused_matches_{t}_direct": fam((fp == pref(data.L[t, "direct"], data.unused)).astype(float), k) for t in D.MODELS}))
    return rows


def checks(root):
    out = {}
    for m in D.MODELS:
        raw = root / "raw" / m
        pg, fg, env = (json.load(open(raw / n, encoding="utf-8")) for n in ("pilot_gates.json", "full_gates.json", "env.json"))
        rows = [json.loads(x) for x in (raw / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
        want = [(x["mode"], x["prefix"], x["prompt_sha256"]) for x in D.prompt_rows()]
        from spar_dynamic.hidden_policy.gpu import file_sha
        st = np.load(root / "arrays" / m / "states_bf16_uint16.npy", mmap_mode="r")
        out[m] = {"pilot gates": pg["ok"], "full gates (replay, repeat, hooks off, projection, finite)": fg["ok"], "archival G/F replay": env["archival_check"]["ok"],
                  "2,400 rows, frozen order and prompt hashes": [(r["mode"], r["prefix"], r["prompt_sha256"]) for r in rows] == want,
                  "array rows match metadata": st.shape[0] == len(rows) and [r["row"] for r in rows] == list(range(len(rows))),
                  "pinned revision": {r["revision"] for r in rows} == {D.MODEL[m]["revision"]},
                  "array hashes": all(file_sha(root / "arrays" / m / n) == v["sha256"] for n, v in env["arrays"].items()),
                  "replay detail": fg["replay"]["by_mode"], "projection_max_abs": fg["projection_max_abs"]}
    return out


def report(data, R, out):
    bk = data.bk
    fams = sorted(set(bk.family))
    P = collect(data, R)
    Lf, rows, perfam = {}, [], []
    tf = {t: pref(data.L[t, "direct"], data.unused) for t in D.MODELS}
    dis = tf["qwen"] != tf["mistral"]
    for t in D.MODELS:
        Lf[t] = {}
        for k, v in P[t].items():
            e2 = (v - data.y[t]) ** 2
            Lf[t][k] = fam_losses(bk, e2)
            sc = np.nan_to_num(cand_scores(bk, v), nan=-np.inf)
            fv = sc.argmax(1)
            r = dict(target=t, model=k, loss=float(np.mean(list(Lf[t][k].values()))), loss_roll4=float(np.mean(list(fam_losses(bk, e2, bk.roll == 4).values()))),
                     loss_roll5=float(np.mean(list(fam_losses(bk, e2, bk.roll == 5).values()))),
                     sign_agreement=float(np.mean(list(fam_losses(bk, (np.sign(v) == np.sign(data.y[t])).astype(float)).values()))))
            if dis.any():
                r.update(disagree_loss=float(np.mean(list(fam_losses(bk, e2, dis).values()))), disagree_favours_qwen=float((fv[dis] == tf["qwen"][dis]).mean()),
                         disagree_favours_mistral=float((fv[dis] == tf["mistral"][dis]).mean()))
            rows.append(r)
            perfam += [dict(target=t, model=k, family=f, fold=D.folds()[f], loss=x) for f, x in Lf[t][k].items()]
    wcsv(out / "losses.csv", rows)
    wcsv(out / "losses_by_family.csv", perfam)

    def cmp(t, a, b):
        return summ({f: Lf[t][a][f] - Lf[t][b][f] for f in fams})
    S = {}
    ps = D.PRIMARY_SLOT
    for t in D.MODELS:
        H = {"history vs face bias": ("face bias", "history")}
        for m in D.MODELS:
            io, ac = f"history+output {m}", f"history+output+act {m} {ps}"
            H.update({f"{m}: output beyond history": ("history", io), f"{m}: act beyond history+output": (io, ac),
                      f"{m}: act only vs face bias": ("face bias", f"act only {m} agent {ps}"), f"{m}: act only vs history": ("history", f"act only {m} agent {ps}"),
                      f"{m}: direct act only vs face bias": ("face bias", f"act only {m} direct {ps}"), f"{m}: direct act only vs history": ("history", f"act only {m} direct {ps}"),
                      f"{m}: direct act beyond history+output": (io, f"history+output+direct act {m}"),
                      f"{m}: direct act only vs forecast act only": (f"act only {m} agent {ps}", f"act only {m} direct {ps}"),
                      f"{m}: raw forecast vs equal odds": ("equal odds", f"raw forecast {m}"), f"{m}: calibrated output vs face bias": ("face bias", f"calibrated output {m}"),
                      f"{m}: logits beyond history": ("history", f"history+logits {m}"), f"{m}: act beyond history+logits": (f"history+logits {m}", f"history+logits+act {m}"),
                      f"{m}: act beyond history+both outputs+act {OTHER[m]}": (f"history+both outputs+act {OTHER[m]}", f"history+both outputs+act {OTHER[m]}+act {m}")})
            H.update({f"{m}: act beyond history+output, {s}": (io, f"history+output+act {m} {s}") for s in D.SLOTS[:4] if s != ps})
            H.update({f"{m}: act beyond history+output, rank {r}": (io, f"history+output+act {m} {ps} rank{r}") for r in RANK_SENS})
            for p in D.PROMPTS[1:]:
                H.update({f"{m} [{p}]: act beyond history+output": (f"history+output {m} [{p}]", f"history+output+act {m} [{p}]"),
                          f"{m} [{p}]: refit act only vs agent act only": (f"act only {m} agent {ps}", f"act only {m} {p} {ps}"),
                          f"{m} [{p}]: transferred agent probe vs face bias": ("face bias", f"transfer agent->{p} {m}"),
                          f"{m} [{p}]: raw forecast vs agent raw forecast": (f"raw forecast {m}", f"raw forecast {m} [{p}]")})
        H["qwen act+base vs mistral act+base"] = (f"history+output+act mistral {ps}", f"history+output+act qwen {ps}")
        S[t] = {k: cmp(t, *v) for k, v in H.items()}
    perm = [R["perm", "qwen", "qwen", s] for s in range(N_PERM) if ("perm", "qwen", "qwen", s) in R]
    obs = S["qwen"]["qwen: act beyond history+output"]["mean"]
    counts = dict(prefixes=len(bk.x), pairs=len(bk.pairs), families=len(fams), roll4=int((bk.roll == 4).sum()), roll5=int((bk.roll == 5).sum()),
                  disagree=int(dis.sum()), disagree_roll4=int((dis & (bk.roll == 4)).sum()), disagree_roll5=int((dis & (bk.roll == 5)).sum()),
                  disagree_families=len(set(bk.family[dis])), favoured={t: {str(f): int((tf[t] == f - 1).sum()) for f in D.FACES} for t in D.MODELS},
                  target_variance_about_zero={t: float(np.mean(list(Lf[t]["equal odds"].values()))) for t in D.MODELS},
                  target_unused_mass_min={t: float(np.where(data.unused, np.exp(data.L[t, "direct"]), 0).sum(1).min()) for t in D.MODELS})
    by_digit = []
    for t in D.MODELS:
        for k in ("raw forecast qwen", "history", "history+output qwen", f"history+output+act qwen {ps}", f"history+output+act mistral {ps}", f"act only qwen direct {ps}"):
            e2 = (P[t][k] - data.y[t]) ** 2
            for f in D.FACES:
                q = np.isin(bk.px, np.where(tf[t] == f - 1)[0])
                if q.any():
                    by_digit.append(dict(target=t, model=k, favoured_face=f, pairs=int(q.sum()), mean_sq_error=float(e2[q].mean())))
    wcsv(out / "losses_by_favoured_face.csv", by_digit)
    folds = [dict(target=t, act=m, fold=k, gain=float(np.mean([Lf[t][f"history+output {m}"][f] - Lf[t][f"history+output+act {m} {ps}"][f] for f in fams if D.folds()[f] == k])))
             for t in D.MODELS for m in D.MODELS for k in range(D.N_OUTER)]
    wcsv(out / "gain_by_fold.csv", folds)
    pol = policy_table(data)
    wcsv(out / "policy_and_ranking.csv", pol)
    oof = []
    for t in D.MODELS:
        for p, (n, i, j) in enumerate(bk.pairs):
            oof.append(dict(target=t, prefix=bk.prefix[n], family=bk.family[n], fold=int(bk.fold[n]), roll=int(bk.roll[n]), i=i, j=j, y=data.y[t][p], disagree=bool(dis[n]),
                            **{k: float(P[t][k][p]) for k in ("face bias", "history", "raw forecast qwen", "raw forecast mistral", "history+output qwen", "history+output mistral",
                                                              f"history+output+act qwen {ps}", f"history+output+act mistral {ps}", f"act only qwen agent {ps}",
                                                              f"act only mistral agent {ps}", f"act only qwen direct {ps}", f"act only mistral direct {ps}")}))
    wcsv(out / "oof_predictions.csv", oof)
    chosen = {str(k): [[str(s), float(l)] for s, l in (v["ioact"][1] if isinstance(v, dict) and "ioact" in v else v[1])]
              for k, v in R.items() if k[0] in ("chain", "hist", "bias", "actonly")}
    json.dump(chosen, open(out / "chosen_hyperparameters.json", "w", encoding="utf-8", newline="\n"), indent=0)
    summ_all = dict(counts=counts, comparisons=S, specificity=specificity(Lf, fams),
                    permutation=dict(n=len(perm), observed_gain=obs, null_mean=float(np.mean(perm)) if perm else None,
                                     null_q975=float(np.percentile(perm, 97.5)) if perm else None,
                                     p=(1 + sum(x >= obs for x in perm)) / (1 + len(perm)) if perm else None))
    json.dump(summ_all, open(out / "summary.json", "w", encoding="utf-8", newline="\n"), indent=1)
    flat = [dict(target=t, comparison=k, gain=v["mean"], ci_lo=v["ci95"][0], ci_hi=v["ci95"][1], families_positive=v["positive"], families=v["families"],
                 loo_lo=v["loo"][0], loo_hi=v["loo"][1]) for t in S for k, v in S[t].items()]
    wcsv(out / "comparisons.csv", flat)
    return summ_all, rows, pol


def main():
    out = D.EXP / "results"
    out.mkdir(exist_ok=True)
    ck = checks(D.EXP)
    (out / "checks.json").write_text(json.dumps(ck, indent=1) + "\n", encoding="utf-8", newline="\n")
    (out / "CHECKS.md").write_text("# Experiment 36 checks\n\n" + "".join(f"- {m}: {'PASS' if v is True else 'FAIL' if v is False else json.dumps(v)}: {k}\n"
                                                                        for m, c in ck.items() for k, v in c.items()), encoding="utf-8", newline="\n")
    R = run_tasks(Data, (), task_list(), int(os.environ.get("SPAR_WORKERS", "12")))
    s, rows, pol = report(Data(), R, out)
    print(json.dumps(ck, indent=1))
    print(json.dumps(s["counts"]), json.dumps(s["permutation"]), json.dumps(s["specificity"], indent=1), sep="\n")
    for t in s["comparisons"]:
        for k, v in s["comparisons"][t].items():
            print(f"{t:8s} {k:62s} {v['mean']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] {v['positive']}/{v['families']}")
    for r in rows:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    for r in pol:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
