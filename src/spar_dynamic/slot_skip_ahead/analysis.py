"""Offline checks and analysis for Experiment 38. Frozen with the protocol; reads raw files only.

Distributions are six-face-normalised; distances are Jensen-Shannon divergence in bits. For generator g and prefix P (k rolls):
  T1_g(P)    one-step G policy (roll k+1);
  B_g(P, x)  G policy for roll k+2 after P and x (teacher-forced);
  T2_g(P)    two-step target for roll k+2: sum_x T1_g(P)[x] * B_g(P, x).
A forecast f is the predictor's first-answer distribution. SLOT and B forecasts are scored against T2 (correct target) and T1
(the next roll, i.e. mis-indexing); C forecasts (roll k+1 supplied) against B_g(P, x_true).
"""

from __future__ import annotations

import csv
import json
import math
import random
from statistics import mean

from spar_dynamic.dice_31_32 import stimuli as S32
from spar_dynamic.dice_31_32.gpu import canonical_sha
from spar_dynamic.slot_skip_ahead import design as D

F = [str(f) for f in D.FACES]
LOW_MASS = 0.5


def read_jsonl(p):
    return [json.loads(x) for x in open(p, encoding="utf-8").read().splitlines() if x]


def norm(fl):
    m = sum(math.exp(fl[f]) for f in F)
    return m, {f: math.exp(fl[f]) / m for f in F}


def js(p, q):
    def kl(a, b):
        return sum(a[f] * math.log2(a[f] / b[f]) for f in F if a[f] > 0)
    m = {f: (p[f] + q[f]) / 2 for f in F}
    return max(0.0, (kl(p, m) + kl(q, m)) / 2)


def uniform(faces=F):
    return {f: (1 / len(faces) if f in faces else 0.0) for f in F}


def unused(seq, pos):
    """Faces not yet used in the six-roll block containing 1-based position `pos` (blocks 1-6, 7-12)."""
    start = 6 * ((pos - 1) // 6)
    return [f for f in F if int(f) not in seq[start:pos - 1]]


def rule2(prefix):
    """Model-free two-step exhaustion rule: roll k+1 uniform over unused faces in its block, then roll k+2 likewise."""
    k = len(prefix)
    out = {f: 0.0 for f in F}
    first = unused(prefix, k + 1)
    for x in first:
        second = unused(tuple(prefix) + (int(x),), k + 2)
        for f in second:
            out[f] += 1 / len(first) / len(second)
    return out


# ---------- targets ----------

def targets(pol_by_model):
    """{(g, prefix): dict(T1, T2, B={x: dist})} from the policy records."""
    out = {}
    for g, rows in pol_by_model.items():
        for r in rows:
            p = tuple(int(v) for v in r["prefix"].split(" "))
            _, t1 = norm(r["one_step"]["face_logprobs"])
            b = {x: norm(r["two_step"][x]["face_logprobs"])[1] for x in F}
            t2 = {f: sum(t1[x] * b[x][f] for x in F) for f in F}
            out[(g, p)] = dict(T1=t1, T2=t2, B=b, mass1=norm(r["one_step"]["face_logprobs"])[0],
                               mass2=min(norm(r["two_step"][x]["face_logprobs"])[0] for x in F))
    return out


def other(m):
    return [g for g in D.MODELS if g != m][0]


def rows_prompts(prm_by_model, T):
    """One row per predictor x prompt with forecast distances to both generators' targets and the baselines."""
    out = []
    for m, rows in prm_by_model.items():
        for r in rows:
            shown = tuple(int(v) for v in r["rolls_shown"].split(" "))
            mass, f = norm(r["answer"]["face_logprobs"])
            o = dict(predictor=m, prompt_id=r["prompt_id"], condition=r["condition"], k=r["k"], target_roll=r["target_roll"],
                     rolls_shown=r["rolls_shown"], cluster=S32.seq(shown[:D.CLUSTER_LEN]),
                     block=("first" if r["target_roll"] <= 6 else "second"), digit_mass=mass, low_mass=mass < LOW_MASS,
                     content=r["content"][:80], final_valid=r["final_valid"], top_face=int(max(F, key=lambda x: f[x])),
                     **{f"p{x}": f[x] for x in F})
            if r["condition"] in ("SLOT", "B"):
                own, oth = T[(m, shown)], T[(other(m), shown)]
                rl = rule2(shown)
                o.update(d2_own=js(f, own["T2"]), d2_other=js(f, oth["T2"]), d1_own=js(f, own["T1"]), d1_other=js(f, oth["T1"]),
                         base_uniform=js(uniform(), own["T2"]), base_rule2=js(rl, own["T2"]), base_T1_own=js(own["T1"], own["T2"]),
                         base_T2_other=js(oth["T2"], own["T2"]), target_sep=js(own["T2"], oth["T2"]),
                         answer_top_next_own=int(max(F, key=lambda x: own["T1"][x])), answer_top_two_own=int(max(F, key=lambda x: own["T2"][x])))
                o["index"] = o["d1_own"] - o["d2_own"]
                o["free_is_top_next_own"] = r["final_valid"] and int(r["content"]) == o["answer_top_next_own"]
                o["free_is_top_two_own"] = r["final_valid"] and int(r["content"]) == o["answer_top_two_own"]
            else:
                pre, x = shown[:-1], str(shown[-1])
                own, oth = T[(m, pre)]["B"][x], T[(other(m), pre)]["B"][x]
                o.update(dc_own=js(f, own), dc_other=js(f, oth), base_uniform=js(uniform(), own), base_rule1=js(uniform(unused(shown, len(shown) + 1)), own),
                         target_sep=js(own, oth))
            out.append(o)
    return out


def rows_realised(prm_by_model):
    """Per predictor x source sequence x k: forecast probability of the realised roll k+2 (and k+1), free-answer category."""
    by = {(m, r["prompt_id"]): r for m, rows in prm_by_model.items() for r in rows}
    out = []
    for s in D.sources():
        x = s["rolls"]
        for m in D.MODELS:
            for k in D.KS:
                for cond in ("SLOT", "B", "C"):
                    shown = x[:k + 1] if cond == "C" else x[:k]
                    r = by[(m, f"{cond}-{''.join(map(str, shown))}")]
                    _, f = norm(r["answer"]["face_logprobs"])
                    t2, t1 = x[k + 1], x[k]
                    cat = "invalid"
                    if r["final_valid"]:
                        a = int(r["content"])
                        cat = "target roll" if a == t2 else ("roll k+1" if a == t1 and cond != "C" else "other face")
                    out.append(dict(predictor=m, source_id=s["source_id"], generator=s["generator"], own_source=m == s["generator"], kind=s["kind"],
                                    condition=cond, k=k, true_k1=t1, true_k2=t2, p_true_k2=f[str(t2)], p_true_k1=f[str(t1)], free=r["content"][:20],
                                    category=cat))
    return out


# ---------- statistics ----------

def boot_mean(vals, clusters, seed=D.BOOT_SEED, n=D.N_BOOT):
    """Mean and 95% percentile CI, resampling clusters with replacement."""
    by = {}
    for v, c in zip(vals, clusters):
        by.setdefault(c, []).append(v)
    keys = sorted(by)
    rng = random.Random(seed)
    est = mean(vals)
    bs = []
    for _ in range(n):
        pick = [by[keys[rng.randrange(len(keys))]] for _ in keys]
        flat = [v for g in pick for v in g]
        bs.append(mean(flat))
    bs.sort()
    return dict(mean=est, lo=bs[int(0.025 * n)], hi=bs[int(0.975 * n) - 1], n=len(vals), clusters=len(keys))


def primary(rows):
    """Q1 SLOT vs B (index and distance), Q2 index under SLOT, Q3 crossed own-vs-other interaction. Pooled and by k and block."""
    by = {(r["predictor"], r["prompt_id"]): r for r in rows}
    out = []
    sel = {"all": lambda r: True, **{f"k={k}": (lambda k: lambda r: r["k"] == k)(k) for k in D.KS},
           "first block": lambda r: r["block"] == "first", "second block": lambda r: r["block"] == "second"}
    for m in D.MODELS:
        slot = [r for r in rows if r["predictor"] == m and r["condition"] == "SLOT"]
        for name, f in sel.items():
            s = [r for r in slot if f(r)]
            if not s:
                continue
            b = [by[(m, "B-" + r["prompt_id"][5:])] for r in s]
            cl = [r["cluster"] for r in s]
            out.append(dict(measure="Q1 index SLOT - B", predictor=m, subset=name, **boot_mean([a["index"] - c["index"] for a, c in zip(s, b)], cl)))
            out.append(dict(measure="Q1 d2_own B - SLOT", predictor=m, subset=name, **boot_mean([c["d2_own"] - a["d2_own"] for a, c in zip(s, b)], cl)))
            out.append(dict(measure="Q2 index SLOT", predictor=m, subset=name, **boot_mean([a["index"] for a in s], cl)))
            out.append(dict(measure="Q2 index B", predictor=m, subset=name, **boot_mean([c["index"] for c in b], cl)))
    for cond in ("SLOT", "B", "C"):
        dk = ("d2_own", "d2_other") if cond != "C" else ("dc_own", "dc_other")
        qs = [r for r in rows if r["predictor"] == "qwen" and r["condition"] == cond]
        for name, f in sel.items():
            s = [r for r in qs if f(r)]
            if not s:
                continue
            v = [((q[dk[1]] - q[dk[0]]) + (by[("mistral", q["prompt_id"])][dk[1]] - by[("mistral", q["prompt_id"])][dk[0]])) / 2 for q in s]
            out.append(dict(measure=f"Q3 crossed own advantage {cond}", predictor="both", subset=name, **boot_mean(v, [r["cluster"] for r in s])))
    return out


def descriptives(rows, real):
    out = []
    for m in D.MODELS:
        for cond in ("SLOT", "B", "C"):
            for k in D.KS:
                s = [r for r in rows if r["predictor"] == m and r["condition"] == cond and r["k"] == k]
                d = dict(predictor=m, condition=cond, k=k, target_roll=k + 2, prompts=len(s), median_digit_mass=sorted(r["digit_mass"] for r in s)[len(s) // 2],
                         low_mass=sum(r["low_mass"] for r in s), valid=sum(r["final_valid"] for r in s))
                if cond != "C":
                    d.update({c: mean(r[c] for r in s) for c in ("d2_own", "d2_other", "d1_own", "index", "base_uniform", "base_rule2", "base_T1_own",
                                                                  "base_T2_other", "target_sep")},
                             free_top_next=sum(r["free_is_top_next_own"] for r in s), free_top_two=sum(r["free_is_top_two_own"] for r in s))
                else:
                    d.update({c: mean(r[c] for r in s) for c in ("dc_own", "dc_other", "base_uniform", "base_rule1", "target_sep")})
                rr = [r for r in real if r["predictor"] == m and r["condition"] == cond and r["k"] == k]
                for own in (True, False):
                    q = [r for r in rr if r["own_source"] == own]
                    tag = "own" if own else "other"
                    d.update({f"p_true_k2_{tag}": mean(r["p_true_k2"] for r in q), f"p_true_k1_{tag}": mean(r["p_true_k1"] for r in q),
                              f"hits_{tag}": sum(r["category"] == "target roll" for r in q), f"k1_answers_{tag}": sum(r["category"] == "roll k+1" for r in q),
                              f"invalid_{tag}": sum(r["category"] == "invalid" for r in q), f"n_{tag}": len(q)})
                out.append(d)
    return out


# ---------- checks ----------

def checks(prm, pol):
    env = {m: json.load(open(D.EXP / "raw" / m / "env.json", encoding="utf-8")) for m in D.MODELS}
    items = {r["prompt_id"]: r for r in D.prompt_items()}
    pitems = {r["policy_id"] for r in D.policy_items()}
    res = {
        "548 prompts per predictor, prompt bytes and hashes equal the frozen design": all(
            len(prm[m]) == len(items) and {r["prompt_id"] for r in prm[m]} == set(items) and
            all(r["prompt"] == items[r["prompt_id"]]["prompt"] and r["prompt_sha256"] == items[r["prompt_id"]]["prompt_sha256"] for r in prm[m]) for m in D.MODELS),
        "170 policy prefixes per generator": all(len(pol[m]) == len(pitems) and {r["policy_id"] for r in pol[m]} == pitems for m in D.MODELS),
        "archival G/F replay (Experiment 28)": all(e["archival_check"]["ok"] for e in env.values()),
        "anchors reproduce (Experiment 35 SLOT, Experiment 32 B and C)": all(e["anchor_check"]["ok"] for e in env.values()),
        "policy reproduces Experiment 31 (|dp| <= 0.01)": all(e["exp31_check"]["ok"] for e in env.values()),
        "pinned revisions": all(r["model_commit"] == D.MODEL[m]["revision"] for m in D.MODELS for r in prm[m] + pol[m]),
        "first-answer replicate bit-identical": all(r["answer_rep2_identical"] for m in D.MODELS for r in prm[m]),
        "first-answer scores equal the generation step": all(r["answer_matches_generation"] for m in D.MODELS for r in prm[m]),
        "one-step copies across the six branches bit-identical": all(r["one_step_copies_identical"] for m in D.MODELS for r in pol[m]),
        "Qwen standard boundary: rendered prompt ends with the empty think block": all(
            r["rendered_prompt"].endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n") for r in prm["qwen"]),
        "face token ids": all({int(k): v for k, v in r["answer"]["face_token_ids"].items()} == dict(D.MODEL[m]["face_ids"]) for m in D.MODELS for r in prm[m]),
        "anchor prompts in the grid give the anchor outputs": all(
            next(r for r in prm[m] if r["prompt_sha256"] == a["sha"])["content"] == env[m]["anchor_check"]["per_anchor"][a["anchor"]]["content"]
            for m in D.MODELS for a in D.anchors()),
        "raw file hashes": all(canonical_sha(D.EXP / "raw" / m / n) == h for m, e in env.items() for n, h in e["files"].items()),
    }
    floor_p = max(abs(math.exp(r["answer"]["face_logprobs"][f]) - math.exp(r["answer_full_pass"]["face_logprobs"][f])) for m in D.MODELS for r in prm[m] for f in F)
    floor_t = max(abs(math.exp(r["one_step"]["face_logprobs"][f]) - math.exp(r["one_step_full_pass"]["face_logprobs"][f])) for m in D.MODELS for r in pol[m] for f in F)
    info = dict(full_pass_floor_prompts=floor_p, full_pass_floor_policy=floor_t,
                exp31_bit_identical={m: f"{e['exp31_check']['n_bit_identical']}/{len(e['exp31_check']['rows'])}" for m, e in env.items()},
                anchors={m: e["anchor_check"]["per_anchor"] for m, e in env.items()})
    return res, info


def wcsv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))      # SLOT/B and C rows carry different distance columns
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def load():
    prm = {m: read_jsonl(D.EXP / "raw" / m / "prompts.jsonl") for m in D.MODELS}
    pol = {m: read_jsonl(D.EXP / "raw" / m / "policy.jsonl") for m in D.MODELS}
    return prm, pol


def main():
    prm, pol = load()
    chk, info = checks(prm, pol)
    T = targets(pol)
    rows = rows_prompts(prm, T)
    real = rows_realised(prm)
    pri = primary(rows)
    desc = descriptives(rows, real)
    out = D.EXP / "results"
    out.mkdir(exist_ok=True)
    wcsv(out / "prompts_scored.csv", rows)
    wcsv(out / "realised.csv", real)
    wcsv(out / "primary.csv", pri)
    wcsv(out / "by_k.csv", desc)
    json.dump(dict(checks=chk, info=info), open(out / "summary.json", "w", encoding="utf-8", newline="\n"), indent=1)
    (out / "CHECKS.md").write_text("# Experiment 38 checks\n\n" + "".join(f"- {'PASS' if v else 'FAIL'}: {k}\n" for k, v in chk.items())
                                   + f"\nFull-pass floor: prompts max |dp| = {info['full_pass_floor_prompts']:.4f}; policy max |dp| = "
                                   f"{info['full_pass_floor_policy']:.4f}. Experiment 31 rows bit-identical: {info['exp31_bit_identical']}.\n",
                                   encoding="utf-8", newline="\n")
    from spar_dynamic.slot_skip_ahead.figures import figure
    figure(desc, pri)
    for k, v in chk.items():
        print("PASS" if v else "FAIL", k)
    for r in pri:
        if r["subset"] in ("all", "first block", "second block"):
            print(f"{r['measure']:34s} {r['predictor']:8s} {r['subset']:13s} {r['mean']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}] n={r['n']} cl={r['clusters']}")
