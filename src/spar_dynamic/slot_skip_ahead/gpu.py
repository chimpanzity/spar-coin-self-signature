"""Collection for Experiment 38 (one model per process). Experiment 27-35 engine, arithmetic and scoring, unchanged and imported.

Order, stopping at the first failure:
  1. vocabulary scan; Experiment 28 archival G/F replay (Experiment 31/32 stop rule);
  2. anchors: Experiment 35 SLOT and Experiment 32 B and C prompts at k = 5 (same prompt ids, same output, six-face |dp| <= 0.01);
  3. teacher-forced G policy of this model on every prefix and each of its six one-roll extensions, then the Experiment 31 replay
     (own G policy along both greedy G paths, one-step and two-step-branch rows, six-face |dp| <= 0.01);
  4. the 548 prediction prompts: free greedy generation (128 tokens) and the first-answer distribution x2 (+ full pass once).
Usage: python -m spar_dynamic.slot_skip_ahead.gpu --model {qwen,mistral}
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from pathlib import Path

from spar_dynamic.dice_31_32 import config as C32
from spar_dynamic.dice_31_32 import gpu as G
from spar_dynamic.dice_31_32 import stimuli as S32
from spar_dynamic.slot_skip_ahead import design as D

PKG = Path(__file__).resolve().parent
STRICT = re.compile(r"[1-6]")


def guard_out(root):
    for part in os.path.abspath(str(root)).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= D.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x]


def max_dp(a, b):
    return max(abs(math.exp(a[f]) - math.exp(b[f])) for f in a)


def code_sha():
    return {**G.code_sha(), **{f"{p.parent.name}/{p.name}": G.canonical_sha(p) for p in sorted(PKG.glob("*.py"))}}


def meta(eng):
    return dict(study=D.TAG, predictor=eng.key, model_id=eng.model_id, model_commit=eng.commit, timestamp=G.now())


# ---------- prediction prompts ----------

def prompt_rec(eng, item, full_pass=True):
    p = item["prompt"]
    g = eng.generate(p)
    d1 = G.forced_dists(eng, p, [], "incremental")[0]
    d2 = G.forced_dists(eng, p, [], "incremental")[0]
    return dict(meta(eng), **item, prompt_ids=eng.prompt_ids(p), rendered_prompt=eng.rendered_text(p), free=g, content=g["content"],
                finish_reason=g["finish_reason"], completion_tokens=g["completion_tokens"],
                final_valid=bool(STRICT.fullmatch(g["content"])) and g["finish_reason"] == "stop",
                answer=d1, answer_rep2_identical=d1["face_logprobs"] == d2["face_logprobs"],
                answer_full_pass=G.forced_dists(eng, p, [], "full_pass")[0] if full_pass else None,
                answer_matches_generation=d1["face_logprobs"] == g["steps"][0]["face_logprobs"])


def anchor_check(eng):
    """Experiment 35 SLOT and Experiment 32 B/C at k = 5: prompt bytes and ids, free output and first-answer scores reproduce."""
    e35 = read_jsonl(D.EXP35 / "raw" / eng.key / "cells_standard.jsonl")
    e32 = read_jsonl(C32.EXP32 / "raw" / eng.key / "cells.jsonl")
    res = {}
    for a in D.anchors():
        src, g, cond = a["anchor"].split("-")[0], a["anchor"].split("-")[1], a["anchor"].split("-")[-1]
        if src == "exp35":
            r = next(x for x in e35 if x["cell_id"] == f"{eng.key}/standard<-{g}-SLOT" and x["replicate"] == 1)
            ref_fl, ref_content = r["answer"]["face_logprobs"], r["content"]
        else:
            r = next(x for x in e32 if x["prompt_id"] == f"{g}-G-{cond}" and x["replicate"] == 1)
            ref_fl, ref_content = r["first_boundary"]["face_logprobs"], r["free"]["content"]
        p = a["prompt"]
        gen, d = eng.generate(p), G.forced_dists(eng, p, [], "incremental")[0]
        res[a["anchor"]] = dict(prompt_equal=r["prompt"] == p and S32.sha256(p) == a["sha"], ids_equal=r["prompt_ids"] == eng.prompt_ids(p),
                                content=gen["content"], content_equal=gen["content"] == ref_content,
                                bit_identical=d["face_logprobs"] == ref_fl, max_dp=max_dp(d["face_logprobs"], ref_fl))
    ok = all(v["prompt_equal"] and v["ids_equal"] and v["content_equal"] and v["max_dp"] <= D.REPRO_TOL_P for v in res.values())
    return dict(ok=ok, per_anchor=res)


# ---------- teacher-forced G policy ----------

def policy_rec(eng, item):
    """One-step distribution after the prefix, and for each face x the distribution after prefix + x (two-step branches).
    Every branch recomputes the one-step row from scratch; the six copies must be bit-identical."""
    G_PROMPT = S32.SOURCE_INSTRUCTION["G"]
    sep = C32.SEPARATOR_ID[eng.key]
    pre = tuple(int(v) for v in item["prefix"].split(" "))
    n0 = len(G.history_ids(eng, pre)) + 1
    branches, one = {}, []
    for x in D.FACES:
        forced = G.history_ids(eng, pre + (x,)) + [sep]
        d0, d1 = G.forced_dists(eng, G_PROMPT, forced, "incremental", at=[n0, len(forced)])
        assert forced[n0 - 1] == sep and forced[n0] == eng.face_ids[x]
        one.append(d0["face_logprobs"])
        branches[str(x)] = d1
    base = G.history_ids(eng, pre) + [sep]
    d = G.forced_dists(eng, G_PROMPT, base, "incremental", at=[n0])[0]
    fp = G.forced_dists(eng, G_PROMPT, base, "full_pass", at=[n0])[0]
    return dict(meta(eng), **item, prompt_sha256=S32.G_SHA256, one_step=d, one_step_full_pass=fp, two_step=branches,
                one_step_copies_identical=all(o == d["face_logprobs"] for o in one))


def exp31_check(eng, pol):
    """Own G policy along both greedy G paths vs Experiment 31 streams `<eng>|G|<g>-G` (incremental, replicate 1).
    Prefix length k one-step = Exp 31 position k+1; branch x = true roll k+1 = Exp 31 position k+2."""
    ref = {r["stream_id"]: r for r in read_jsonl(C32.EXP31 / "raw" / eng.key / "streams.jsonl") if r["method"] == "incremental" and r["replicate"] == 1}
    by = {r["prefix"]: r for r in pol}
    rows = []
    for g in D.MODELS:
        x = C32.REFERENCES[(g, "G")]
        pos = {p["position"]: p["face_logprobs"] for p in ref[f"{eng.key}|G|{g}-G"]["positions"]}
        for k in D.KS:
            r = by[S32.seq(x[:k])]
            rows.append(dict(path=f"{g}-G", k=k, row="one_step", exp31_position=k + 1, bit_identical=r["one_step"]["face_logprobs"] == pos[k + 1],
                             max_dp=max_dp(r["one_step"]["face_logprobs"], pos[k + 1])))
            if k + 2 <= 10:
                b = r["two_step"][str(x[k])]["face_logprobs"]
                rows.append(dict(path=f"{g}-G", k=k, row="branch_true", exp31_position=k + 2, bit_identical=b == pos[k + 2], max_dp=max_dp(b, pos[k + 2])))
    return dict(ok=all(r["max_dp"] <= D.REPRO_TOL_P for r in rows), rows=rows, n_bit_identical=sum(r["bit_identical"] for r in rows))


# ---------- driver ----------

def run(eng, root):
    guard_out(root)
    raw = Path(root) / "raw" / eng.key
    if raw.exists():
        raise SystemExit(f"{raw} exists; refusing")
    raw.mkdir(parents=True)
    env = dict(G.env_record(eng, {}), study=D.TAG, code_sha256=code_sha())

    def save():
        json.dump(env, open(raw / "env.json", "w", encoding="utf-8", newline="\n"), indent=1)
    if env["vocab_scan"]["variant_face_tokens"]:
        save()
        raise SystemExit("STOP: variant face tokens")
    t0 = time.time()
    arch = G.archival(eng)
    G.write_jsonl(raw / "archival.jsonl", arch)
    env.update(archival_check=G.archival_check(eng, arch, C32.EXP28_MAIN), anchor_check=anchor_check(eng), preflight_seconds=round(time.time() - t0, 1))
    save()
    print("archival", env["archival_check"]["ok"], "anchors", env["anchor_check"]["ok"], flush=True)
    if not (env["archival_check"]["ok"] and env["anchor_check"]["ok"]):
        raise SystemExit("STOP: preflight failed " + json.dumps(env["anchor_check"]))
    t0 = time.time()
    pol = []
    for n, it in enumerate(D.policy_items(), 1):
        pol.append(policy_rec(eng, it))
        if n % 20 == 0:
            print(f"policy {n}/{len(D.policy_items())} {time.time() - t0:.0f} s", flush=True)
    G.write_jsonl(raw / "policy.jsonl", pol)
    env.update(exp31_check=exp31_check(eng, pol), policy_seconds=round(time.time() - t0, 1))
    save()
    print("exp31", env["exp31_check"]["ok"], env["exp31_check"]["n_bit_identical"], "bit-identical", flush=True)
    if not env["exp31_check"]["ok"] or not all(r["one_step_copies_identical"] for r in pol):
        raise SystemExit("STOP: policy replay failed")
    t0 = time.time()
    out = []
    items = D.prompt_items()
    for n, it in enumerate(items, 1):
        out.append(prompt_rec(eng, it))
        if n % 25 == 0:
            print(f"prompts {n}/{len(items)} {time.time() - t0:.0f} s; last {it['prompt_id']} {out[-1]['content'][:40]!r}", flush=True)
    G.write_jsonl(raw / "prompts.jsonl", out)
    env.update(prompts_seconds=round(time.time() - t0, 1), finished_utc=G.now(),
               max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"],
               files={p.name: G.canonical_sha(p) for p in sorted(raw.glob("*.jsonl"))})
    save()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=D.MODELS)
    a = ap.parse_args()
    from spar_dynamic.slot_skip_ahead.__main__ import validate
    validate()
    from spar_dynamic.dice_crossed_guidance.models import load
    t0 = time.time()
    eng = load(a.model)
    print(f"loaded {a.model} in {time.time() - t0:.1f} s", flush=True)
    run(eng, D.EXP)
    print("DONE", a.model, round(time.time() - t0, 1), flush=True)
