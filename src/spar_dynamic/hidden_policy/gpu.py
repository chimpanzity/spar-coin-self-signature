"""Activation capture for Experiment 36 (one model per process; rented GPU). Experiment 27-35 engine and arithmetic, unchanged.

Forecast rows: prompt prefill, state at the last rendered prompt token. Direct rows: prompt prefill, then forced prefix and separator one
token at a time through the KV cache (Experiment 33), state at the last forced separator. Hooks keep the last position only.
pilot -> gates -> full bank. Usage: python -m spar_dynamic.hidden_policy.gpu --model {qwen,mistral}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path

import numpy as np

from spar_dynamic.dice_31_32 import config as C31
from spar_dynamic.dice_31_32 import gpu as G31
from spar_dynamic.dice_scaffolding import config as C33
from spar_dynamic.dice_scaffolding import design as D33
from spar_dynamic.hidden_policy import design as D

PKG = Path(__file__).resolve().parent


def guard_out(root):
    for part in os.path.abspath(str(root)).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= D.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x]


class Capture:
    """Last-position post-block states at the four depths and the final-normalised state (the head's input)."""

    def __init__(self, eng):
        m = eng.model.model
        self.stack = m.language_model if hasattr(m, "language_model") else m
        self.layers, self.norm = self.stack.layers, self.stack.norm
        self.blocks = [D.block_index(len(self.layers), d) for d in D.DEPTHS]
        self.state, self.handles = {}, []

    def __enter__(self):
        def hook(name):
            def f(mod, args, out):
                t = out[0] if isinstance(out, tuple) else out
                self.state[name] = t[0, -1].detach().clone()
            return f
        for s, b in zip(D.SLOTS, self.blocks):
            self.handles.append(self.layers[b].register_forward_hook(hook(s)))
        self.handles.append(self.norm.register_forward_hook(hook("final_norm")))
        return self

    def __exit__(self, *a):
        for h in self.handles:
            h.remove()
        self.handles = []


def bits(t):
    """bf16 tensor -> raw uint16 bits (lossless)."""
    import torch
    assert t.dtype == torch.bfloat16
    return t.cpu().view(torch.int16).numpy().astype(np.int16).view(np.uint16)


def ids_for(eng, mode, prefix):
    if mode == "direct":
        return eng.prompt_ids(D.G), G31.history_ids(eng, D33.faces_of(prefix)) + [D.SEPARATOR_ID[eng.key]]
    return eng.prompt_ids(D.forecast(mode, prefix)), []


def logits_at(eng, pre, forced):
    out = eng._fwd(pre)
    for t in forced:
        out = eng._fwd([t], out.past_key_values)
    return out.logits[0, -1].float(), out


def capture_row(eng, cap, mode, prefix, emit=0):
    """One row: metadata dict and uint16 array (slots, d)."""
    import torch
    pre, forced = ids_for(eng, mode, prefix)
    ptext = D.G if mode == "direct" else D.forecast(mode, prefix)
    with torch.no_grad():
        lg, out = logits_at(eng, pre, forced)
        st = torch.stack([cap.state[s] for s in D.SLOTS])
        proj = eng.model.lm_head(st[-1].unsqueeze(0))[0].float()
        lp = torch.log_softmax(lg, dim=-1)
        det = G31.detail(eng, lp)
        gen = []
        if emit:
            for _ in range(emit):
                n = int(torch.argmax(torch.log_softmax(out.logits[0, -1].float(), dim=-1)))
                if n in eng.eos:
                    break
                gen.append(n)
                out = eng._fwd([n], out.past_key_values)
    seq = pre + forced
    ls = [det["face_logprobs"][str(f)] for f in D.FACES]
    row = dict(mode=mode, prefix=prefix, model=eng.key, revision=eng.commit, prompt_sha256=D.sha256(ptext),
               rendered_sha256=D.sha256(eng.rendered_text(ptext)), token_sha256=hashlib.sha256(json.dumps(seq).encode()).hexdigest(),
               token_position=len(seq) - 1, token_id=seq[-1], n_prompt_tokens=len(pre), l=ls, mass=sum(math.exp(v) for v in ls),
               argmax_token=det["argmax_token"], argmax_token_id=det["argmax_token_id"], entropy_bits=det["entropy_bits"], top=det["top"][:5],
               projection_max_abs=float((proj - lg).abs().max()), emitted=eng.decode(gen) if emit else None)
    return row, bits(st)


def replay(rows, model):
    """Experiment 33: shape forecasts and direct G rows with the same prompt and prefix."""
    raw = C33.EXP / "raw" / model
    f33 = {r["prompt_sha256"]: r for n in ("core", "extensions") for r in read_jsonl(raw / f"forecasts_{n}.jsonl")}
    g33 = {r["history"]: r for n in ("core", "extensions") for r in read_jsonl(raw / f"direct_{n}.jsonl") if r["assay"] == "direct_G"}
    res = {}
    for r in rows:
        ref = g33.get(r["prefix"]) if r["mode"] == "direct" else f33.get(r["prompt_sha256"])
        if ref is None or ref["prompt_sha256"] != r["prompt_sha256"]:
            continue
        x = res.setdefault(r["mode"], dict(n=0, max_dp=0.0, bit_identical=0))
        x["n"] += 1
        x["max_dp"] = max(x["max_dp"], max(abs(math.exp(a) - math.exp(b)) for a, b in zip(r["l"], ref["l"])))
        x["bit_identical"] += r["l"] == ref["l"]
    ok = all(v["max_dp"] <= D.REPRO_TOL_P for v in res.values()) and "shape" in res and "direct" in res
    return dict(ok=ok, by_mode=res)


def hook_off_check(eng, rows):
    """Re-score without hooks: six-face scores must be bit-identical."""
    import torch
    bad = 0
    with torch.no_grad():
        for r in rows:
            lp = torch.log_softmax(logits_at(eng, *ids_for(eng, r["mode"], r["prefix"]))[0], dim=-1)
            bad += [float(lp[eng.face_ids[f]]) for f in D.FACES] != r["l"]
    return dict(n=len(rows), mismatches=bad, ok=bad == 0)


def sweep(eng, jobs, emit_agent, label):
    rows, arr = [], []
    t0 = time.time()
    with Capture(eng) as cap:
        for n, (mode, p) in enumerate(jobs, 1):
            r, a = capture_row(eng, cap, mode, p, D.EMIT_TOKENS if emit_agent and mode == "agent" else 0)
            rows.append(dict(row=len(rows), **r))
            arr.append(a)
            if n % 400 == 0:
                print(f"[{label}] {n}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    return rows, np.stack(arr)


def gates(eng, rows, arr, jobs):
    again, arr2 = sweep(eng, jobs, False, "repeat")
    rep = dict(n=len(jobs), score_mismatches=sum(a["l"] != b["l"] for a, b in zip(rows, again)), state_mismatches=int((arr != arr2).any((1, 2)).sum()))
    rep["ok"] = rep["score_mismatches"] == 0 and rep["state_mismatches"] == 0
    g = dict(replay=replay(rows, eng.key), repeat=rep, hook_off=hook_off_check(eng, rows), finite=bool(np.isfinite(to_f32(arr)).all()),
             projection_max_abs=max(r["projection_max_abs"] for r in rows),
             last_token=sorted({(r["mode"] == "direct", r["token_id"]) for r in rows}))
    g["ok"] = g["replay"]["ok"] and rep["ok"] and g["hook_off"]["ok"] and g["finite"] and g["projection_max_abs"] <= D.PROJ_TOL and len(g["last_token"]) == 2
    return g


def to_f32(u16):
    return (u16.astype(np.uint32) << 16).view(np.float32)


def code_sha():
    return {**G31.code_sha(), **{f"{p.parent.name}/{p.name}": G31.canonical_sha(p) for p in sorted(PKG.glob("*.py"))}}


def file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def run(eng, root):
    import torch
    guard_out(root)
    raw, arrd = Path(root) / "raw" / eng.key, Path(root) / "arrays" / eng.key
    if raw.exists():
        raise SystemExit(f"{raw} exists; refusing")
    raw.mkdir(parents=True)
    arrd.mkdir(parents=True, exist_ok=True)

    def dump(name, o):
        json.dump(o, open(raw / name, "w", encoding="utf-8", newline="\n"), indent=1)
    cap = Capture(eng)
    env = dict(G31.env_record(eng, {}), study=D.TAG, code_sha256=code_sha(), n_layers=len(cap.layers), blocks=dict(zip(D.SLOTS, cap.blocks)),
               d_model=int(eng.model.lm_head.weight.shape[1]),
               slot_note="b25..b100: post-block residual before final normalisation; final_norm: head input")
    arch = G31.archival(eng)
    G31.write_jsonl(raw / "archival.jsonl", arch)
    env["archival_check"] = G31.archival_check(eng, arch, C31.EXP28_MAIN)
    dump("env.json", env)
    if not env["archival_check"]["ok"] or env["vocab_scan"]["variant_face_tokens"]:
        raise SystemExit("STOP: archival or vocabulary check failed")
    jobs = [(m, p) for m in D.MODES for p in D.pilot_prefixes()]
    rows, arr = sweep(eng, jobs, True, "pilot")
    G31.write_jsonl(raw / "pilot_rows.jsonl", rows)
    pg = gates(eng, rows, arr, jobs)
    dump("pilot_gates.json", pg)
    print("pilot gates", json.dumps(pg), flush=True)
    if not pg["ok"]:
        raise SystemExit("STOP: pilot gates failed")
    jobs = [(m, b["prefix"]) for m in D.MODES for b in D.bank()]
    rows, arr = sweep(eng, jobs, True, "full")
    G31.write_jsonl(raw / "rows.jsonl", rows)
    np.save(arrd / "states_bf16_uint16.npy", arr)
    fg = gates(eng, rows, arr, jobs)
    dump("full_gates.json", fg)
    print("full gates", json.dumps(fg), flush=True)
    w = eng.model.lm_head.weight.detach().double()
    w = w - w.mean(0, keepdim=True)                        # row-wise logit mean removed (softmax-invariant)
    np.save(arrd / "head_gram_centered_f32.npy", (w.T @ w).float().cpu().numpy())
    env.update(finished_utc=G31.now(), files={p.name: G31.canonical_sha(p) for p in sorted(raw.glob("*.json*")) if p.name != "env.json"},
               arrays={p.name: dict(sha256=file_sha(p), shape=list(np.load(p, mmap_mode="r").shape), bytes=p.stat().st_size) for p in sorted(arrd.glob("*.npy"))},
               max_memory_allocated_gb=round(torch.cuda.max_memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None)
    dump("env.json", env)
    if not fg["ok"]:
        raise SystemExit("STOP: full gates failed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=D.MODELS)
    a = ap.parse_args()
    from spar_dynamic.hidden_policy.__main__ import validate
    validate()
    from spar_dynamic.dice_crossed_guidance.models import load
    run(load(a.model), D.EXP)
    print("DONE", a.model, flush=True)
