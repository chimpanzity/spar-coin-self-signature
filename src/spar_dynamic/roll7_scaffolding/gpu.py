"""Collection for Experiment 35 (one model per process). Experiment 27-32 engine, arithmetic and scoring, unchanged and imported.

Order, stopping at the first failure: vocabulary scan; Experiment 28 archival G/F replay (Experiment 31/32 stop rule); Experiment 32
B prompts reproduced (same output, six-face |dp| <= 0.01); then the 12 standard cells x 2; for Qwen the 12 native-thinking cells x 2 at
1,024 tokens, and last the supplementary longer-budget continuation of cells that were truncated.
Usage: python -m spar_dynamic.roll7_scaffolding.gpu --model {qwen,mistral}
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
from spar_dynamic.roll7_scaffolding import design as D

PKG = Path(__file__).resolve().parent
STRICT = re.compile(r"[1-6]")


def guard_out(root):
    for part in os.path.abspath(str(root)).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= D.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x]


def thinking_ids(eng, prompt):
    """Normal Qwen template with native thinking enabled; returns (rendered text, ids)."""
    t = eng.tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True, enable_thinking=True)
    return t, eng.tok(t, add_special_tokens=False).input_ids


def split_thinking(gen, finish, decode):
    """Locate the thinking block and the final answer in generated ids. `boundary` is the index in gen of the first final-answer
    token: the first token after the first </think> that is not whitespace-only; None if there is no such token."""
    r = dict(think_opened=bool(gen) and gen[0] == D.THINK_OPEN, think_closed=D.THINK_CLOSE in gen, truncated=finish == "length", boundary=None,
             whitespace_ids=None, whitespace_is_template=None, thinking_text=None, final_text=None, final_valid=False, status="")
    if not r["think_closed"]:
        r["status"] = "truncated inside thinking block" if r["think_opened"] and r["truncated"] else "no closed thinking block"
        r["thinking_text"] = decode(gen)
        return r
    j = gen.index(D.THINK_CLOSE)
    r["thinking_text"] = decode(gen[:j])
    k = j + 1
    while k < len(gen) and decode([gen[k]]).strip() == "":
        k += 1
    tail = gen[j + 1:]
    r["whitespace_ids"] = gen[j + 1:k]
    r["whitespace_is_template"] = r["whitespace_ids"] == [D.THINK_SEP]
    r["final_text"] = decode(tail[1:] if tail[:1] == [D.THINK_SEP] else tail)      # only the template-defined "\n\n" is removed
    if k < len(gen):
        r["boundary"] = k
        r["final_valid"] = bool(STRICT.fullmatch(r["final_text"])) and finish == "stop"
        r["status"] = "answered" if finish == "stop" else "truncated after thinking closed"
    else:
        r["status"] = "no final answer after thinking"
    return r


def generate_thinking(eng, prompt, max_new):
    """Greedy, engine arithmetic. Full detail is kept for every step after </think>."""
    import torch
    text, ids = thinking_ids(eng, prompt)
    t0, gen, lps, after, finish = time.time(), [], [], {}, "length"
    with torch.no_grad():
        out = eng._fwd(ids)
        for _ in range(max_new):
            lp = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
            nxt = int(torch.argmax(lp))
            if D.THINK_CLOSE in gen:
                after[len(gen)] = G.detail(eng, lp)
            if nxt in eng.eos:
                finish = "stop"
                break
            gen.append(nxt)
            lps.append(float(lp[nxt]))
            out = eng._fwd([nxt], out.past_key_values)
    info = split_thinking(gen, finish, eng.decode)
    b = info["boundary"]
    return dict(rendered_prompt=text, rendered_prompt_sha256=S32.sha256(text), prompt_ids=ids, prompt_tokens=len(ids), max_new_tokens=max_new,
                generated_ids=gen, chosen_logprobs=lps, content=eng.decode(gen), finish_reason=finish, completion_tokens=len(gen),
                seconds=round(time.time() - t0, 2), answer=None if b is None else after[b], **info)


def meta(eng, c, rep):
    return dict(study=D.TAG, **c, replicate=rep, model_id=eng.model_id, model_commit=eng.commit, timestamp=G.now())


def standard_rec(eng, c, rep):
    g = eng.generate(c["prompt"])
    first = G.forced_dists(eng, c["prompt"], [], "incremental")[0]
    return dict(meta(eng, c, rep), rendered_prompt=eng.rendered_text(c["prompt"]), prompt_ids=eng.prompt_ids(c["prompt"]), free=g,
                generated_ids=g["generated_ids"], content=g["content"], finish_reason=g["finish_reason"], completion_tokens=g["completion_tokens"],
                truncated=g["finish_reason"] == "length", final_text=g["content"],
                final_valid=bool(STRICT.fullmatch(g["content"])) and g["finish_reason"] == "stop",
                status="answered" if g["finish_reason"] == "stop" else "truncated", answer=first,
                answer_full_pass=G.forced_dists(eng, c["prompt"], [], "full_pass")[0] if rep == 1 else None,
                answer_matches_generation=first["face_logprobs"] == g["steps"][0]["face_logprobs"])


def b_check(eng):
    """Experiment 32 B replay: same prompt bytes and ids, same output, six-face |dp| within the established tolerance."""
    ref = read_jsonl(C32.EXP32 / "raw" / eng.key / "cells.jsonl")
    res = {}
    for s, _ in D.SOURCES:
        r = next(x for x in ref if x["prompt_id"] == f"{s}-G-B" and x["replicate"] == 1)
        p = D.prompt(s, "B")
        g, d = eng.generate(p), G.forced_dists(eng, p, [], "incremental")[0]
        a, b = r["first_boundary"]["face_logprobs"], d["face_logprobs"]
        res[s] = dict(prompt_equal=r["prompt"] == p and r["prompt_sha256"] == D.B_SHA[s] == S32.sha256(p),
                      ids_equal=r["prompt_ids"] == eng.prompt_ids(p), content=g["content"], content_equal=g["content"] == r["free"]["content"],
                      bit_identical=a == b, max_dp=max(abs(math.exp(a[f]) - math.exp(b[f])) for f in a))
    ok = all(v["prompt_equal"] and v["ids_equal"] and v["content_equal"] and v["max_dp"] <= D.REPRO_TOL_P for v in res.values())
    return dict(ok=ok, per_source=res)


def code_sha():
    return {**G.code_sha(), **{f"{p.parent.name}/{p.name}": G.canonical_sha(p) for p in sorted(PKG.glob("*.py"))}}


def collect_thinking(eng, cells):
    """12 cells x 2 at the handoff budget, then (separately) one longer-budget run of the truncated cells."""
    out = []
    for c in cells:
        for rep in (1, 2):
            out.append(dict(meta(eng, c, rep), **generate_thinking(eng, c["prompt"], D.THINK_MAX_NEW)))
            r = out[-1]
            print(c["cell_id"], rep, r["status"], repr(r["final_text"]), r["completion_tokens"], r["seconds"], flush=True)
    return out


def collect_supplementary(eng, cells, primary):
    trunc = {r["cell_id"]: r for r in primary if r["replicate"] == 1 and r["truncated"]}
    sup = []
    for c in cells:
        if c["cell_id"] in trunc:
            r = dict(meta(eng, c, 1), supplementary=True, **generate_thinking(eng, c["prompt"], D.SUPP_MAX_NEW))
            n = len(trunc[c["cell_id"]]["generated_ids"])
            r["extends_primary"] = r["generated_ids"][:n] == trunc[c["cell_id"]]["generated_ids"]
            sup.append(r)
            print("SUPP", c["cell_id"], r["status"], repr(r["final_text"]), r["completion_tokens"], flush=True)
    return sup


def run(eng, root):
    guard_out(root)
    raw = Path(root) / "raw" / eng.key
    if raw.exists():
        raise SystemExit(f"{raw} exists; refusing")
    raw.mkdir(parents=True)
    env = dict(G.env_record(eng, {}), study=D.TAG, code_sha256=code_sha())
    if env["vocab_scan"]["variant_face_tokens"]:
        raise SystemExit("STOP: variant face tokens")
    if eng.key == "qwen" and (eng.tok.convert_tokens_to_ids(["<think>", "</think>"]) != [D.THINK_OPEN, D.THINK_CLOSE]
                              or eng.hist_ids("\n\n") != [D.THINK_SEP]):
        raise SystemExit("STOP: thinking token ids differ")
    arch = G.archival(eng)
    G.write_jsonl(raw / "archival.jsonl", arch)
    env.update(archival_check=G.archival_check(eng, arch, C32.EXP28_MAIN), b_check=b_check(eng))
    json.dump(env, open(raw / "env.json", "w", encoding="utf-8", newline="\n"), indent=1)
    print("archival", env["archival_check"]["ok"], "B", json.dumps(env["b_check"]), flush=True)
    if not (env["archival_check"]["ok"] and env["b_check"]["ok"]):
        raise SystemExit("STOP: preflight failed")
    mine = [c for c in D.cells() if c["predictor"] == eng.key]
    out = []
    for c in [c for c in mine if c["mode"] == "standard"]:
        for rep in (1, 2):
            out.append(standard_rec(eng, c, rep))
            print(c["cell_id"], rep, repr(out[-1]["content"][:60]), out[-1]["finish_reason"], flush=True)
    G.write_jsonl(raw / "cells_standard.jsonl", out)
    th = [c for c in mine if c["mode"] == "thinking"]
    if th:
        prim = collect_thinking(eng, th)
        G.write_jsonl(raw / "cells_thinking.jsonl", prim)
        G.write_jsonl(raw / "cells_thinking_supplementary.jsonl", collect_supplementary(eng, th, prim))
    env.update(finished_utc=G.now(), files={p.name: G.canonical_sha(p) for p in sorted(raw.glob("*.jsonl"))})
    json.dump(env, open(raw / "env.json", "w", encoding="utf-8", newline="\n"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=D.MODELS)
    a = ap.parse_args()
    from spar_dynamic.roll7_scaffolding.__main__ import validate
    validate()
    from spar_dynamic.dice_crossed_guidance.models import load
    run(load(a.model), D.EXP)
    print("DONE", a.model, flush=True)
