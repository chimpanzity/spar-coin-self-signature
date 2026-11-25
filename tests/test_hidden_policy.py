"""Offline tests for Experiment 36: prompts, split, capture hooks, kernel identities and a planted-signal analysis."""

from __future__ import annotations

import types

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from spar_dynamic.hidden_policy import analysis as A  # noqa: E402
from spar_dynamic.hidden_policy import design as D  # noqa: E402
from spar_dynamic.hidden_policy import gpu as R  # noqa: E402
from spar_dynamic.hidden_policy.__main__ import preconditions  # noqa: E402


def test_design():
    preconditions()
    b = D.bank()
    assert len({x["family"] for x in b}) == 20 and all(x["family"] == D.family(tuple(map(int, x["prefix"].split()))) for x in b)
    assert {x["fold"] for x in b if not x["eligible"]} == {None}
    assert sorted(np.bincount(list(D.folds().values())).tolist()) == [3, 3, 4, 4, 4]
    assert not any(x["pilot_prefix"] and x["eligible"] for x in b)
    text = (D.EXP.parents[1] / "docs/handoffs/GPT_SPAR_Hidden_Activation_Dice_Policy_Claude_Code_Handoff.md").read_text(encoding="utf-8")
    for m in D.PROMPTS:
        assert f"| {m} | The roller is {D.SUBJECT[m]}. |" in text
        for line in D.forecast(m, "5 2 6").split("\n"):
            assert line in text or line.startswith(("The roller is", "Earlier rolls"))
    assert [D.block_index(64, d) for d in D.DEPTHS] == [15, 31, 47, 63] and [D.block_index(40, d) for d in D.DEPTHS] == [9, 19, 29, 39]
    assert len(D.prompt_rows()) == 2400


def test_pair_kernel_is_face_indexed_signed_difference():
    bk = A.Bank()
    rng = np.random.default_rng(0)
    z = rng.normal(size=(len(bk.x), 5))
    K = bk.faced(z @ z.T)
    phi = np.zeros((len(bk.pairs), 30))
    for p, (n, i, j) in enumerate(bk.pairs):
        phi[p, 5 * (i - 1):5 * i] += z[n]
        phi[p, 5 * (j - 1):5 * j] -= z[n]
    assert np.allclose(K, phi @ phi.T)
    w = bk.weights(np.arange(len(bk.pairs)))
    s = {f: w[bk.pfam == f].sum() for f in set(bk.pfam)}
    assert np.allclose(list(s.values()), s["123"]) and len(bk.pairs) == 648 and len(bk.x) == 432


def test_gram_pca_matches_explicit():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(40, 12))
    tr = np.arange(30)
    k = A.gram_pca_kernel(X @ X.T, tr, 4)
    Z = X - X[tr].mean(0)
    v = np.linalg.svd(Z[tr], full_matrices=False)[2][:4]
    assert np.allclose(k, Z @ v.T @ v @ Z.T)


def synth(signal_in_qwen_act=True, d=24, seed=0):
    """Qwen's target = face bias + idiosyncratic prefix part; the idiosyncratic part is (optionally) linear in Qwen's b75 forecast state."""
    rng = np.random.default_rng(seed)
    b = D.bank()
    W = rng.normal(size=(6, 5))
    rows, states, gram = {}, {}, {}
    latent = {m: rng.normal(size=(480, 5)) for m in D.MODELS}
    for m in D.MODELS:
        rows[m], st = [], []
        for mode in D.MODES:
            for n, x in enumerate(b):
                s = rng.normal(size=(5, d))
                if mode == "direct" or signal_in_qwen_act:
                    s[:, :5] = latent[m][n] * 2 + 0.1 * rng.normal(size=(5, 5))
                l = np.linspace(-2, -1, 6) + (latent[m][n] @ W.T if mode == "direct" else 0.1 * rng.normal(size=6))
                rows[m].append(dict(row=len(rows[m]), mode=mode, prefix=x["prefix"], l=list(l), mass=0.9, argmax_token="1"))
                st.append(s)
        states[m] = np.array(st, np.float32)
        M = rng.normal(size=(d, d))
        gram[m] = (M @ M.T).astype(np.float32)
    return rows, states, gram


def loader(*a):
    return A.Data(rows=a[0], states=a[1], gram=a[2])


def test_planted_signal_recovered_and_specific():
    a = synth(True)
    P = D.PRIMARY_SLOT
    T = [("hist", "qwen"), ("bias", "qwen"), ("chain", "qwen", "qwen", "agent", P, A.RANK), ("chain", "qwen", "mistral", "agent", P, A.RANK),
         ("actonly", "qwen", "qwen", "agent", P, A.RANK), ("transfer", "qwen", "qwen", "agent", P), ("stack", "qwen", "qwen", P)]
    r = A.run_tasks(loader, a, T, 1)
    d = loader(*a)
    L = lambda v: np.mean(list(A.fam_losses(d.bk, (v[0] - d.y["qwen"]) ** 2).values()))
    q, m = r[T[2]], r[T[3]]
    assert L(q["ioact"]) < 0.3 * L(q["io"])
    assert L(m["ioact"]) > 0.85 * L(m["io"])
    assert L(r[T[4]]) < 0.4 * L(r[T[1]])
    assert np.allclose(r[T[4]][0], r[T[5]][0], atol=1e-5)          # transfer to agent itself reproduces the agent probe
    s = r[T[6]]
    assert L(s["io2both"]) < 0.4 * L(s["io2other"])


def test_null_signal_adds_nothing():
    a = synth(False, seed=3)
    t = ("chain", "qwen", "qwen", "agent", D.PRIMARY_SLOT, A.RANK)
    r = A.run_tasks(loader, a, [t], 1)[t]
    d = loader(*a)
    L = lambda v: np.mean(list(A.fam_losses(d.bk, (v[0] - d.y["qwen"]) ** 2).values()))
    assert L(r["ioact"]) > 0.9 * L(r["io"])


def test_no_test_targets_used():
    """Changing a test fold's targets leaves that fold's predictions unchanged."""
    a = synth(True)
    cv = A.CV(loader(*a))
    y = cv.data.y["qwen"].copy()
    spec = [(("act", "qwen", "agent", "b75", 8, 1.0),)]
    p1 = cv.fit(spec, y)[0]
    te = np.isin(cv.bk.pfam, cv.outer[0]["test"])
    y2 = y.copy()
    y2[te] += 5
    p2 = cv.fit(spec, y2)[0]
    assert np.array_equal(p1[te], p2[te]) and not np.array_equal(p1[~te], p2[~te])


def test_capture_hooks_tiny():
    class Block(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.f = torch.nn.Linear(8, 8, dtype=torch.bfloat16)

        def forward(self, x):
            return x + self.f(x)

    class M(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = torch.nn.Module()
            self.model.layers = torch.nn.ModuleList([Block() for _ in range(8)])
            self.model.norm = torch.nn.LayerNorm(8, dtype=torch.bfloat16)
            self.emb = torch.nn.Embedding(2000, 8, dtype=torch.bfloat16)
            self.lm_head = torch.nn.Linear(8, 2000, bias=False)
            self.lm_head.register_forward_pre_hook(lambda mod, args: (args[0].float(),))

        def forward(self, ids):
            x = self.emb(ids)
            for b in self.model.layers:
                x = b(x)
            return self.lm_head(self.model.norm(x))
    torch.manual_seed(0)
    m = M()
    eng = types.SimpleNamespace(key="qwen", commit="c", model=m, eos={1}, face_ids=dict(D.MODEL["qwen"]["face_ids"]),
                                prompt_ids=lambda p: [5, 6, 7 + len(p) % 9], hist_ids=lambda s: [220 if c == " " else D.MODEL["qwen"]["face_ids"][int(c)] for c in s],
                                decode=lambda ids: "x", rendered_text=lambda p: p)
    eng._fwd = lambda ids, past=None: types.SimpleNamespace(logits=m(torch.tensor([ids])), past_key_values=0)
    with R.Capture(eng) as cap:
        assert cap.blocks == [1, 3, 5, 7]
        r, a = R.capture_row(eng, cap, "agent", "5 2 6", emit=3)
        r2, a2 = R.capture_row(eng, cap, "direct", "5 2 6")
    assert a.shape == (5, 8) and r["projection_max_abs"] < 1e-5 and r2["token_id"] == 220 and r["emitted"] == "x"
    assert np.allclose(R.to_f32(a)[4], m.model.norm(torch.tensor(R.to_f32(a)[3]).to(torch.bfloat16)).detach().float().numpy(), atol=1e-2)
    assert R.hook_off_check(eng, [r, r2])["ok"]


def test_guard():
    with pytest.raises(SystemExit):
        R.guard_out(D.EXP.parent / "35_2026-11-25_roll7_prompt_scaffolding")
