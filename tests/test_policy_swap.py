"""Offline tests for Experiment 37: target rule, adapter hooks and training on a tiny model, primal probes, metrics."""

from __future__ import annotations

import types

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from spar_dynamic.hidden_policy import analysis as A36  # noqa: E402
from spar_dynamic.hidden_policy import design as D36  # noqa: E402
from spar_dynamic.policy_swap import analysis as A  # noqa: E402
from spar_dynamic.policy_swap import design as D  # noqa: E402
from spar_dynamic.policy_swap import gpu as R  # noqa: E402
from spar_dynamic.policy_swap import probes as PR  # noqa: E402
from spar_dynamic.policy_swap.__main__ import preconditions  # noqa: E402
from tests.test_hidden_policy import loader, synth  # noqa: E402


def test_split_and_rule():
    preconditions()
    assert D.source_map((1, 2, 3), "A") == {4: 6, 5: 4, 6: 5} and D.source_map((1, 2, 3), "B") == {4: 5, 5: 6, 6: 4}      # first<last: A forward
    assert D.source_map((3, 2, 1), "A") == D.source_map((1, 2, 3), "B")
    assert D.source_map((1, 2, 3, 4), "A") == {5: 6, 6: 5} and D.source_map((1, 2, 3, 4), "B") == {5: 5, 6: 6}
    assert D.source_map((4, 2, 3, 1), "B") == {5: 6, 6: 5}
    lp = np.log([.1, .1, .1, .4, .2, .1])
    for arm in ("A", "B", "neutral"):
        q = np.exp(D.permuted_logp(lp, (1, 2, 3), arm))
        assert np.isclose(q[3:].sum(), .7) and np.allclose(q[:3], .1)
    assert np.allclose(np.exp(D.permuted_logp(lp, (1, 2, 3), "A"))[3:], [.1, .4, .2])


def test_gate_stats():
    b = np.log(np.array([[.05, .05, .05, .5, .2, .1]]))
    n = np.log(np.array([[.05, .05, .05, .1, .5, .2]]))
    g = D.gate_stats(b, n, [(1, 2, 3)])
    assert g["pass"] and g["switch_rate"] == 1 and g["median_abs_dmass_pp"] < 1e-9
    assert not D.gate_stats(b, b, [(1, 2, 3)])["pass"]


class TinyBlock(torch.nn.Module):
    def __init__(self, d):
        super().__init__()
        self.self_attn, self.mlp = torch.nn.Module(), torch.nn.Module()
        for s in ("q_proj", "v_proj", "o_proj"):
            setattr(self.self_attn, s, torch.nn.Linear(d, d))
        self.mlp.down_proj = torch.nn.Linear(d, d)

    def forward(self, x):
        a = self.self_attn
        h = torch.cumsum(a.v_proj(x) * torch.sigmoid(a.q_proj(x)), 1) / 8
        return x + self.mlp.down_proj(torch.tanh(a.o_proj(h)))


class TinyLM(torch.nn.Module):
    def __init__(self, d=32, n=3):
        super().__init__()
        self.emb = torch.nn.Embedding(300, d)
        self.layers, self.norm = torch.nn.ModuleList([TinyBlock(d) for _ in range(n)]), torch.nn.LayerNorm(d)

    def forward(self, input_ids, use_cache=False):
        x = self.emb(input_ids) + 0.1 * torch.arange(input_ids.shape[1])[None, :, None]
        for b in self.layers:
            x = b(x)
        return types.SimpleNamespace(last_hidden_state=self.norm(x))


def tiny_engine():
    torch.manual_seed(0)
    m = torch.nn.Module()
    m.model, m.lm_head = TinyLM(), torch.nn.Linear(32, 300, bias=False)
    fid = dict(D36.MODEL["qwen"]["face_ids"])
    e = types.SimpleNamespace(key="qwen", model=m, device="cpu", face_ids=fid, eos={1}, prompt_ids=lambda p: [5, 6, 7],
                              hist_ids=lambda s: [220 if c == " " else fid[int(c)] for c in s])
    e._fwd = lambda ids, past=None: types.SimpleNamespace(logits=m.lm_head(m.model(torch.tensor([ids])).last_hidden_state))
    return e


def test_lora_disabled_identity_training_and_frozen_base():
    e = tiny_engine()
    for p in e.model.parameters():
        p.requires_grad_(False)
    tr, dev = D.prefixes("train")[::2], D.prefixes("dev")
    base, bdev = R.base_table(e, tr + dev, 20), R.base_table(e, dev, 20)          # same batches for the bit-identity check
    w0 = {k: v.clone() for k, v in e.model.state_dict().items()}
    old = D.BLOCKS
    log = []
    R.Lora.__init__.__defaults__ = ((0, 1), *R.Lora.__init__.__defaults__[1:])
    try:
        cfg = dict(name="t", rank=8, lr=1e-2, epochs=12, batch=20)
        a = R.train_arm(e, e.model.model.layers, "A", cfg, tr, dev, base, log)
        assert log[-1]["train_loss"] < 0.6 * log[0]["dev_loss"]
        assert all(torch.equal(w0[k], v) for k, v in e.model.state_dict().items())
        lora = R.Lora(e.model.model.layers, 8, 0, device="cpu")
        lora.load(a["state"])
        on = R.base_table(e, dev, 20)
        lora.scale = 0.0
        off = R.base_table(e, dev, 20)
        assert all(torch.equal(off[p], bdev[p]) for p in off) and any(not torch.equal(on[p], bdev[p]) for p in on)
        lora.remove()
        n = R.train_arm(e, e.model.model.layers, "neutral", cfg, tr, dev, base, log, init=a["state"])
        assert n["gate"]["median_abs_dlogodds"] < max(a["gate"]["median_abs_dlogodds"], 0.05)
    finally:
        R.Lora.__init__.__defaults__ = (old, *R.Lora.__init__.__defaults__[1:])
    t = R.target_logp(e, base[dev[0]["prefix"]], dev[0]["prefix"], "A")
    assert abs(float(t.exp().sum()) - 1) < 1e-4


def test_primal_probes_and_pipeline(tmp_path, monkeypatch):
    """Primal == dual (asserted inside freeze); a planted policy change carried by the states is tracked, outputs do not move."""
    a = synth(True)
    data = loader(*a)
    monkeypatch.setattr(D, "EXP", tmp_path)
    monkeypatch.setattr(A36, "HIST", ("linear",))
    monkeypatch.setattr(A36, "LAMBDAS", (0.01, 0.1))
    PR.freeze(data)
    rows36, st36 = a[0]["qwen"], a[1]["qwen"]
    by = {(r["mode"], r["prefix"]): r for r in rows36}
    rng = np.random.default_rng(5)
    W = np.random.default_rng(0).normal(size=(6, 5))          # synth's readout matrix
    rows, states = [], []
    for arm in D.ARMS:
        for mode in D.MODES:
            for r in D.prefixes("holdout"):
                b = by[mode, r["prefix"]]
                dz = {"A": 1, "B": -1}.get(arm, 0) * np.random.default_rng(abs(hash(r["prefix"])) % 2**32).normal(size=5)
                s = st36[b["row"]].copy()
                s[:, :5] += 2 * dz
                l = np.array(b["l"]) + (dz @ W.T if mode == "direct" else 0)
                rows.append(dict(arm=arm, mode=mode, prefix=r["prefix"], row=len(rows), l=list(l), mass=0.9))
                states.append(s)
    pos = {b["prefix"]: by["agent", b["prefix"]]["row"] for b in D36.bank()}
    F36 = np.array([st36[pos[b["prefix"]]][4] for b in D36.bank() if b["eligible"]], float)
    monkeypatch.setattr(A, "BOOT_B", 200)
    monkeypatch.setattr(A, "N_SHUFFLE", 20)
    d = A.Data(rows=rows, states=np.array(states, np.float32), gram=a[2]["qwen"].astype(float), base36=F36)
    S = A.analyse(d)
    assert S["A+B|agent|agent_probe"]["corr"] > 0.8 and S["A+B|agent|agent_probe"]["skill"] > 0.5
    assert S["A+B|agent|direct_probe"]["corr"] > 0.8 and S["A-minus-B|agent|agent_probe"]["corr"] > 0.8
    assert abs(S["A+B|agent|raw_output"]["skill"]) < 1e-9 and abs(S["A+B|agent|agent_probe"]["wrong_history"]["mean"]) < 0.2
    assert S["disabled|agent|agent_probe"]["mse"] == 0
    assert A.gates(d)["A"]["all"]["switch_rate"] > 0.2 and A.examples(A.favourites(d))["tracked"]
    assert rng is not None
