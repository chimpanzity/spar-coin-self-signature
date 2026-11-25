"""Experiment 37 GPU stages (Qwen only).

train     adapters A, B (config ladder on development gates), then neutral (A's weights retrained to the base policy on the same
          schedule). Direct-generation contexts of the training families only.
evaluate  held-out families: base, disabled, A, B, neutral x agent, shape, direct; the Experiment 36 capture code, unchanged.
Adapters are low-rank additions to fixed linear layers through one unconditional forward hook per layer.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

from spar_dynamic.dice_31_32 import config as C31
from spar_dynamic.dice_31_32 import gpu as G31
from spar_dynamic.hidden_policy import design as D36
from spar_dynamic.hidden_policy import gpu as R36
from spar_dynamic.policy_swap import design as D

PKG = Path(__file__).resolve().parent


class Lora:
    """Adapter on every (block, site); scale 0 runs the same path with a zero contribution."""

    def __init__(self, layers, rank, seed, blocks=D.BLOCKS, sites=D.SITES, device="cuda"):
        import torch
        g = torch.Generator().manual_seed(seed)
        self.scale, self.p, self.handles, self.rank = D.LORA_SCALE, {}, [], rank
        for b in blocks:
            for s in sites:
                mod = layers[b].get_submodule(s)
                a = torch.randn(rank, mod.in_features, generator=g) / mod.in_features ** 0.5
                self.p[f"{b}.{s}"] = (torch.nn.Parameter(a.to(device)), torch.nn.Parameter(torch.zeros(mod.out_features, rank, device=device)))
                self.handles.append(mod.register_forward_hook(self._hook(f"{b}.{s}")))

    def _hook(self, key):
        def f(mod, args, out):
            a, b = self.p[key]
            return out + (self.scale * ((args[0].float() @ a.T) @ b.T)).to(out.dtype)
        return f

    def params(self):
        return [t for ab in self.p.values() for t in ab]

    def state(self):
        return {f"{k}.{n}": t.detach().cpu().numpy().copy() for k, ab in self.p.items() for n, t in zip("AB", ab)}

    def load(self, st):
        import torch
        with torch.no_grad():
            for k, ab in self.p.items():
                for n, t in zip("AB", ab):
                    t.copy_(torch.as_tensor(np.asarray(st[f"{k}.{n}"])).to(t.device))

    def remove(self):
        for h in self.handles:
            h.remove()


def batch_logits(eng, rows):
    """Last-position logits (fp32) for equal-length direct contexts, one padding-free batch."""
    import torch
    ids = []
    for r in rows:
        pre, forced = R36.ids_for(eng, "direct", r["prefix"])
        ids.append(pre + forced)
    assert len({len(i) for i in ids}) == 1
    h = eng.model.model(input_ids=torch.tensor(ids, device=eng.device), use_cache=False).last_hidden_state[:, -1]
    return eng.model.lm_head(h).float()


def by_roll(rows, size, rng=None):
    out = []
    for roll in (4, 5):
        q = [r for r in rows if r["roll"] == roll]
        if rng is not None:
            q = [q[i] for i in rng.permutation(len(q))]
        out += [q[i:i + size] for i in range(0, len(q), size)]
    if rng is not None:
        out = [out[i] for i in rng.permutation(len(out))]
    return out


def base_table(eng, rows, size):
    """Base full-vocabulary log-probabilities per prefix (CPU), measured before any adapter is installed."""
    import torch
    t = {}
    with torch.no_grad():
        for bt in by_roll(rows, size):
            lp = torch.log_softmax(batch_logits(eng, bt), -1).cpu()
            t.update({r["prefix"]: lp[k] for k, r in enumerate(bt)})
    return t


def target_logp(eng, base_lp, prefix, arm):
    """Base distribution with the unused-face profile permuted; used faces and all other tokens keep their base probabilities."""
    t = base_lp.clone()
    for u, s in D.source_map(D.faces(prefix), arm).items():
        t[eng.face_ids[u]] = base_lp[eng.face_ids[s]]
    return t


def loss_fn(eng, logits, targets, rows):
    import torch
    lp = torch.log_softmax(logits, -1)
    tot = 0
    for k, r in enumerate(rows):
        u = [eng.face_ids[f] for f in D36.FACES if f not in D.faces(r["prefix"])]
        tc, mc = torch.log_softmax(targets[k][u], -1), torch.log_softmax(lp[k][u], -1)
        full = (targets[k].exp() * (targets[k] - lp[k])).sum()
        tot = tot + (tc.exp() * (tc - mc)).sum() + D.W_FULL * full
    return tot / len(rows)


def six(eng, t):
    return [float(t[eng.face_ids[f]]) for f in D36.FACES]


def dev_eval(eng, rows, base, arm, size):
    import torch
    tot, n, new = 0.0, 0, {}
    with torch.no_grad():
        for bt in by_roll(rows, size):
            lg = batch_logits(eng, bt)
            tg = [target_logp(eng, base[r["prefix"]], r["prefix"], arm).to(lg.device) for r in bt]
            tot += float(loss_fn(eng, lg, tg, bt)) * len(bt)
            n += len(bt)
            lp = torch.log_softmax(lg, -1)
            new.update({r["prefix"]: six(eng, lp[k]) for k, r in enumerate(bt)})
    b6, n6 = [six(eng, base[r["prefix"]]) for r in rows], [new[r["prefix"]] for r in rows]
    g = D.gate_stats(b6, n6, [D.faces(r["prefix"]) for r in rows])
    # Fixed-digit check: share of the change in unused log-odds explained by one mean shift per roll and face pair.
    d, key = [], []
    for b, q, r in zip(b6, n6, rows):
        U = [f for f in D36.FACES if f not in D.faces(r["prefix"])]
        for i in range(len(U)):
            for j in range(i + 1, len(U)):
                d.append((q[U[i] - 1] - q[U[j] - 1]) - (b[U[i] - 1] - b[U[j] - 1]))
                key.append((r["roll"], U[i], U[j]))
    d = np.array(d)
    fit = np.array([np.mean([v for v, kk in zip(d, key) if kk == k]) for k in key])
    g["fixed_digit_share"] = float(1 - ((d - fit) ** 2).sum() / max((d ** 2).sum(), 1e-12))
    g["gain_by_face"] = {str(f): int(sum(max((v for v in range(6) if v + 1 not in D.faces(r["prefix"])), key=lambda v: q[v]) == f - 1 for q, r in zip(n6, rows))) for f in D36.FACES}
    g["base_favourite_by_face"] = {str(f): int(sum(max((v for v in range(6) if v + 1 not in D.faces(r["prefix"])), key=lambda v: b[v]) == f - 1 for b, r in zip(b6, rows))) for f in D36.FACES}
    g["loss"] = tot / n
    return g


def train_arm(eng, layers, arm, cfg, tr, dev, base, log, init=None):
    import torch
    lora = Lora(layers, cfg["rank"], D.SEED[arm], device=eng.device)
    if init is not None:
        lora.load(init)
    opt = torch.optim.AdamW(lora.params(), lr=cfg["lr"], weight_decay=0.0)
    rng = np.random.Generator(np.random.PCG64(D.SEED[arm]))
    steps = cfg["epochs"] * len(by_roll(tr, cfg["batch"]))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 20) * 0.5 * (1 + np.cos(np.pi * min(1.0, s / steps))))
    best, t0 = None, time.time()

    def ev(epoch, trl):
        nonlocal best
        g = dev_eval(eng, dev, base, arm, cfg["batch"])
        log.append(dict(arm=arm, config=cfg["name"], epoch=epoch, train_loss=trl, seconds=round(time.time() - t0, 1), **{f"dev_{k}": v for k, v in g.items()}))
        print(json.dumps(log[-1]), flush=True)
        if epoch and (best is None or g["loss"] < best[0]):
            best = (g["loss"], epoch, lora.state(), g)
    ev(0, None)
    for ep in range(1, cfg["epochs"] + 1):
        tot, n = 0.0, 0
        for bt in by_roll(tr, cfg["batch"], rng):
            with torch.enable_grad():
                lg = batch_logits(eng, bt)
                tg = [target_logp(eng, base[r["prefix"]], r["prefix"], arm).to(lg.device) for r in bt]
                loss = loss_fn(eng, lg, tg, bt)
                opt.zero_grad()
                loss.backward()
            if not torch.isfinite(loss):
                raise SystemExit(f"STOP: nonfinite loss in {arm}")
            torch.nn.utils.clip_grad_norm_(lora.params(), 1.0)
            opt.step()
            sched.step()
            tot += float(loss.detach()) * len(bt)
            n += len(bt)
        if ep % D.EVAL_EVERY == 0:
            ev(ep, tot / n)
    lora.remove()
    return dict(state=best[2], epoch=best[1], gate=best[3], config=cfg["name"], rank=cfg["rank"])


def preflight(eng, raw, stage):
    env = dict(G31.env_record(eng, {}), study=D.TAG, stage=stage, code_sha256={**R36.code_sha(), **{f"{p.parent.name}/{p.name}": G31.canonical_sha(p) for p in sorted(PKG.glob("*.py"))}})
    arch = G31.archival(eng)
    env["archival_check"] = G31.archival_check(eng, arch, C31.EXP28_MAIN)
    json.dump(env, open(raw / f"env_{stage}.json", "w", encoding="utf-8", newline="\n"), indent=1)
    if not env["archival_check"]["ok"]:
        raise SystemExit("STOP: archival check failed")
    return env


def train(eng, root):
    import torch
    root = Path(root)
    R36.guard_out(root)
    raw, ad = root / "raw", root / "arrays" / "adapters"
    if (raw / "train_summary.json").exists():
        raise SystemExit("training already done; refusing")
    raw.mkdir(parents=True, exist_ok=True)
    ad.mkdir(parents=True, exist_ok=True)
    preflight(eng, raw, "train")
    for p in eng.model.parameters():
        p.requires_grad_(False)
    layers = R36.Capture(eng).layers
    tr, dev = D.prefixes("train"), D.prefixes("dev")
    base = base_table(eng, tr + dev, D.CONFIGS[0]["batch"])
    log, attempts, done = [], [], {}
    for cfg in D.CONFIGS:
        done = {a: train_arm(eng, layers, a, cfg, tr, dev, base, log) for a in D.ACTIVE}
        attempts.append({a: dict(config=cfg["name"], epoch=v["epoch"], gate=v["gate"]) for a, v in done.items()})
        if all(v["gate"]["pass"] for v in done.values()):
            break
    cfg = next(c for c in D.CONFIGS if c["name"] == done["A"]["config"])
    done["neutral"] = train_arm(eng, layers, "neutral", cfg, tr, dev, base, log, init=done["A"]["state"])
    G31.write_jsonl(raw / "train_log.jsonl", log)
    summ = dict(attempts=attempts, used_config=cfg, adapters={})
    for a, v in done.items():
        f = ad / f"{a}.npz"
        np.savez(f, **v["state"])
        summ["adapters"][a] = dict(epoch=v["epoch"], dev_gate=v["gate"], sha256=R36.file_sha(f), bytes=f.stat().st_size,
                                   b_norm=float(np.sqrt(sum((x ** 2).sum() for k, x in v["state"].items() if k.endswith(".B")))))
    summ.update(finished_utc=G31.now(), max_memory_allocated_gb=round(torch.cuda.max_memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None)
    json.dump(summ, open(raw / "train_summary.json", "w", encoding="utf-8", newline="\n"), indent=1)
    print("TRAIN DONE", json.dumps({a: v["dev_gate"] for a, v in summ["adapters"].items()}), flush=True)


def evaluate(eng, root, exp36_raw=None):
    root = Path(root)
    R36.guard_out(root)
    raw, arrd = root / "raw", root / "arrays"
    if (raw / "rows.jsonl").exists():
        raise SystemExit("evaluation already done; refusing")
    env = preflight(eng, raw, "evaluate")
    summ = json.load(open(raw / "train_summary.json", encoding="utf-8"))
    jobs = [(m, r["prefix"]) for m in D.MODES for r in D.prefixes("holdout")]
    cap = R36.Capture(eng)
    rows, arrs, free = [], [], {}

    def sweep(arm):
        rs, a = R36.sweep(eng, jobs, False, arm)
        for r in rs:
            r["arm"], r["row"] = arm, len(rows)
            rows.append(r)
        arrs.append(a)
        g = eng.generate(D36.G)
        free[arm] = dict(content=g["content"], finish_reason=g["finish_reason"])
        return rs, a
    base, abase = sweep("base")
    chk = dict(base_repeat=sum(x["l"] != y["l"] for x, y in zip(base, R36.sweep(eng, jobs, False, "rep")[0])), hook_off=R36.hook_off_check(eng, base))
    if exp36_raw:
        ref = {(r["mode"], r["prefix"]): r for r in R36.read_jsonl(exp36_raw)}
        chk["exp36_score_mismatches"] = sum(ref[r["mode"], r["prefix"]]["l"] != r["l"] for r in base)
    lora = Lora(cap.layers, summ["used_config"]["rank"], 0, device=eng.device)
    for arm in ("disabled", "A", "B", "neutral"):
        lora.load(np.load(arrd / "adapters" / f"{'A' if arm == 'disabled' else arm}.npz"))
        lora.scale = 0.0 if arm == "disabled" else D.LORA_SCALE
        rs, a = sweep(arm)
        if arm == "disabled":                                    # adapter A's weights installed, contribution zeroed
            chk["disabled_equals_base_scores"] = all(x["l"] == y["l"] for x, y in zip(rs, base))
            chk["disabled_equals_base_states"] = bool((a == abase).all())
        chk[f"{arm}_prompt_and_tokens_equal_base"] = all((x["prompt_sha256"], x["rendered_sha256"], x["token_sha256"]) == (y["prompt_sha256"], y["rendered_sha256"], y["token_sha256"])
                                                         for x, y in zip(rs, base))
        chk[f"{arm}_hook_off"] = R36.hook_off_check(eng, rs[::7])
    lora.remove()
    G31.write_jsonl(raw / "rows.jsonl", rows)
    np.save(arrd / "states_bf16_uint16.npy", np.concatenate(arrs))
    json.dump(dict(checks=chk, free_generation_G=free), open(raw / "eval_checks.json", "w", encoding="utf-8", newline="\n"), indent=1)
    env.update(finished_utc=G31.now(), arrays={p.relative_to(arrd).as_posix(): dict(sha256=R36.file_sha(p), bytes=p.stat().st_size) for p in sorted(arrd.rglob("*.np*"))},
               files={p.name: G31.canonical_sha(p) for p in sorted(raw.glob("*.json*")) if not p.name.startswith("env_")})
    json.dump(env, open(raw / "env_evaluate.json", "w", encoding="utf-8", newline="\n"), indent=1)
    print("EVAL DONE", json.dumps(chk), json.dumps(free), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["train", "evaluate"])
    a = ap.parse_args()
    from spar_dynamic.policy_swap.__main__ import validate
    validate(probes=a.stage == "evaluate")
    from spar_dynamic.dice_crossed_guidance.models import load
    eng = load("qwen")
    if a.stage == "train":
        train(eng, D.EXP)
    else:
        p = D.EXP36 / "raw" / "qwen" / "rows.jsonl"
        evaluate(eng, D.EXP, p if p.exists() else None)
    print("DONE", a.stage, os.getpid(), flush=True)
