"""GPU stages for SPAR_CROSSED_GUIDED_SELFPRED_v1.0 (one model per process; run on the rented GPU).

  preflight --model M   env, tokenisation, G x3, F x3, Fanon x1 (greedy), Qwen only: Experiment 26's twelve prompts and an
                        engine-vs-Experiment-21-class bit check; feasibility sampling (N_FEASIBILITY draws, discarded);
                        scorer-vs-generation on every output; matched-prefix G|G, F|G, F|F by both arithmetic paths;
                        three crossed prompts as a rendering/format check; timings.
  corpus --model M      reference corpus (N_REFERENCE) then targets (N_TARGETS) sampled at TEMPERATURE with the seed table,
                        each sampled sequence rescored under G (scorer check). Needs --gate (passed preflight).
  predict --model M     every frozen trial with predictor M: free greedy output + teacher-forced six-face distribution at
                        each scored position (incremental), full-pass floor on a seeded subset, own-output rescoring on the
                        same subset; then G, F and Fanon scored on every target item's full sequence (both models'
                        items: oracle for its own, native policy for the other's). Needs --trials and --gate. Resumable.

Usage: python -m spar_dynamic.dice_crossed_guidance.gpu <stage> --model {qwen,mistral} --out <dir> [...]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
import time

from spar_dynamic.dice_crossed_guidance import config as C
from spar_dynamic.dice_crossed_guidance import prompts as P

VALID10 = re.compile(r"[1-6]( [1-6]){9}")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def guard_out(out_dir: str):
    for part in os.path.abspath(out_dir).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= C.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def append(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def file_sha(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def check_gate(path, model):
    g = json.load(open(path, encoding="utf-8"))
    if g.get("overall") != "PASS" or model not in g.get("models", [model]):
        raise SystemExit(f"gate {path} is {g.get('overall')}; refusing")
    return g


def seeds(kind: str, model: str, n: int) -> list:
    return [C.SEED_BASE[kind] + C.MODEL_SEED_OFFSET[model] + i for i in range(n)]


def gen_record(eng, stage, cid, prompt, rep=1, temperature=None, seed=None, rescore=True, full=False):
    g = eng.generate(prompt, temperature, seed)
    rec = dict(stage=stage, model=eng.key, condition=cid, replicate=rep, prompt=prompt, prompt_sha256=P.sha256(prompt),
               timestamp=now(), **g)
    if rescore and g["content"].strip():
        rec["own_rescored"] = eng.score(prompt, g["content"], "incremental")
        if full:
            rec["own_rescored_full_pass"] = eng.score(prompt, g["content"], "full_pass")
    return rec


def preflight(eng, out):
    raw = os.path.join(out, "raw_attempts.jsonl")
    if os.path.exists(raw):
        raise SystemExit(f"{raw} exists; preflight is never appended to")
    refs = P.references()
    jobs = [(r, i) for r in ("G", "F") for i in (1, 2, 3)] + [("Fanon", 1)]
    if eng.key == "qwen":
        jobs += [(c["condition"], 1) for c in P.archival26()]
    random.Random(C.ORDER_SEED + 1).shuffle(jobs)
    x26 = {c["condition"]: c for c in P.archival26()}
    allp = {**{k: v["prompt"] for k, v in refs.items()}, **{k: v["prompt"] for k, v in x26.items()}}
    g10 = " ".join(map(str, C.QWEN_G_REF))
    env = dict(eng.env(), stage="preflight", started_utc=now(), job_order=jobs,
               prompt_sha256={k: P.sha256(v) for k, v in allp.items()},
               rendered_sha256={k: P.sha256(eng.rendered_text(v)) for k, v in allp.items()},
               rendered_G=eng.rendered_text(refs["G"]["prompt"]), g10_history_ids=eng.hist_ids(g10),
               face_single_tokens={str(f): eng.hist_ids(str(f)) for f in C.FACES})
    json.dump(env, open(os.path.join(out, "env_preflight.json"), "w", encoding="utf-8"), indent=2)
    timing = []
    for n, (cid, rep) in enumerate(jobs, 1):
        t0 = time.time()
        rec = gen_record(eng, "preflight", cid, allp[cid], rep, full=(rep == 1))
        if cid in x26:
            c = x26[cid]
            rec["teacher_forced"] = eng.score(c["prompt"], " ".join(map(str, c["target"])), "incremental")
            rec["teacher_forced_full_pass"] = eng.score(c["prompt"], " ".join(map(str, c["target"])), "full_pass")
            rec.update(k=c["k"], arm=c["arm"], target=c["target"])
        append(raw, rec)
        timing.append(time.time() - t0)
        print(f"[{n}/{len(jobs)}] {cid}-{rep}: {rec['content']!r} ({rec['finish_reason']}, {rec['latency_ms']} ms)", flush=True)
    # feasibility sampling (discarded)
    for i, s in enumerate(seeds("feasibility", eng.key, C.N_FEASIBILITY)):
        rec = gen_record(eng, "preflight", "feasibility", refs["G"]["prompt"], i + 1, C.TEMPERATURE, s)
        append(raw, rec)
        print(f"[feasibility {i + 1}] seed {s}: {rec['content']!r}", flush=True)
    # crossed prompt format check: three trials on this model's own greedy G
    own_g = next(json.loads(l) for l in open(raw, encoding="utf-8") if json.loads(l)["condition"] == "G")["content"]
    seq = [int(x) for x in own_g.split()] if VALID10.fullmatch(own_g) else list(C.QWEN_G_REF)
    other = "mistral" if eng.key == "qwen" else "qwen"
    xc = [("A", "H", "k3", eng.key), ("T", "D", "m3", other), ("R", "I", "k8", eng.key)]
    for fr, ev, cond, tgt in xc:
        p = P.prompt(fr, ev, cond, eng.key, tgt, seq, [3, 1, 5, 6, 2, 4, 1, 3, 6, 2])
        t0 = time.time()
        rec = gen_record(eng, "preflight", f"crossed_{fr}{ev}_{cond}", p)
        rec["teacher_forced"] = eng.score(p, " ".join(str(seq[j - 1]) for j in C.CONDITIONS[cond]["positions"]), "incremental")
        rec["teacher_forced_full_pass"] = eng.score(p, " ".join(str(seq[j - 1]) for j in C.CONDITIONS[cond]["positions"]), "full_pass")
        rec["target_model_label"] = tgt
        append(raw, rec)
        timing.append(time.time() - t0)
        print(f"[crossed {fr}{ev} {cond}] {rec['content']!r}", flush=True)
    # matched prefix: G|G, F|G, F|F on this model's own greedy outputs (RQ1), both arithmetic paths
    recs = [json.loads(l) for l in open(raw, encoding="utf-8")]
    modal = {k: next(r["content"] for r in recs if r["condition"] == k) for k in ("G", "F")}
    with open(os.path.join(out, "matched_prefix.jsonl"), "w", encoding="utf-8") as f:
        for x, h in (("G", "G"), ("F", "G"), ("F", "F"), ("Fanon", "G")):
            for method in ("incremental", "full_pass"):
                for s in eng.score(refs[x]["prompt"], modal[h], method):
                    f.write(json.dumps(dict(instruction=x, history=h, history_sequence=modal[h], **s)) + "\n")
    # Qwen: this engine vs Experiment 21's class, same prompts (must be bit-identical)
    if eng.key == "qwen":
        eq = []
        for k in ("G", "F"):
            a = eng.q.generate(refs[k]["prompt"])
            b = next(r for r in recs if r["condition"] == k)
            eq.append(dict(prompt=k, content_equal=a["raw_choice_content"] == b["content"],
                           max_abs_face_logprob_diff=max(abs(x["face_logprobs_exact"]["bare"][f] - y["face_logprobs"][str(f)])
                                                         for x, y in zip(a["raw_logprobs_content"], b["steps"]) for f in C.FACES)))
            sa = eng.q.score_prefix(refs[k]["prompt"], modal["G"], "incremental")
            sb = eng.score(refs[k]["prompt"], modal["G"], "incremental")
            eq.append(dict(prompt=f"{k}|G score", max_abs_face_logprob_diff=max(abs(x["face_logprobs_exact"]["bare"][f] - y["face_logprobs"][str(f)])
                                                                                 for x, y in zip(sa, sb) for f in C.FACES)))
        json.dump(eq, open(os.path.join(out, "engine_equivalence.json"), "w", encoding="utf-8"), indent=2)
    env.update(finished_utc=now(), sec_per_job_mean=sum(timing) / len(timing), sec_per_crossed_trial=timing[-3:],
               max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"])
    json.dump(env, open(os.path.join(out, "env_preflight.json"), "w", encoding="utf-8"), indent=2)


def corpus(eng, out):
    path = os.path.join(out, "sampled.jsonl")
    if os.path.exists(path):
        raise SystemExit(f"{path} exists; the corpus is collected once")
    g = P.references()["G"]["prompt"]
    env = dict(eng.env(), stage="corpus", started_utc=now(), temperature=C.TEMPERATURE, top_p=1.0, top_k=None)
    for kind, n in (("reference", C.N_REFERENCE), ("target", C.N_TARGETS)):
        valid, drawn = 0, 0
        for s in seeds(kind, eng.key, n * C.MAX_DRAW_FACTOR):
            if valid == n:
                break
            rec = gen_record(eng, "corpus", kind, g, drawn + 1, C.TEMPERATURE, s)
            rec["valid"] = bool(VALID10.fullmatch(rec["content"])) and rec["finish_reason"] == "stop"
            if rec["valid"]:
                rec["full_pass"] = eng.score(g, rec["content"], "full_pass")
            append(path, rec)
            drawn += 1
            valid += rec["valid"]
            print(f"[{kind} {drawn}] seed {s}: {rec['content']!r} valid={rec['valid']}", flush=True)
        env[f"{kind}_drawn"], env[f"{kind}_valid"] = drawn, valid
        if valid < n:
            env["stop"] = f"{kind}: only {valid} valid of {drawn} draws"
            json.dump(env, open(os.path.join(out, "env_corpus.json"), "w", encoding="utf-8"), indent=2)
            raise SystemExit(env["stop"])
    env["finished_utc"] = now()
    json.dump(env, open(os.path.join(out, "env_corpus.json"), "w", encoding="utf-8"), indent=2)


def predict(eng, out, trials_path, items_path):
    trials = [json.loads(l) for l in open(trials_path, encoding="utf-8")]
    items = json.load(open(items_path, encoding="utf-8"))
    mine = [t for t in trials if t["predictor"] == eng.key]
    random.Random(C.ORDER_SEED + (0 if eng.key == "qwen" else 7)).shuffle(mine)
    rng = random.Random(C.ORDER_SEED + 2)
    fp_ids = {t["trial_id"] for t in sorted(trials, key=lambda t: t["trial_id"])
              if t["tier"] == "A" or rng.random() < C.FULL_PASS_FRACTION_B}
    path = os.path.join(out, "predictions.jsonl")
    done = {}
    if os.path.exists(path):                       # resume: refuse drift, skip completed trials
        for l in open(path, encoding="utf-8"):
            r = json.loads(l)
            done[r["trial_id"]] = r["prompt_sha256"]
    want = {t["trial_id"]: t["prompt_sha256"] for t in mine}
    assert all(want[k] == v for k, v in done.items()), "prompt drift against an earlier partial run"
    env = dict(eng.env(), stage="predict", started_utc=now(), trials_sha256=file_sha(trials_path),
               items_sha256=file_sha(items_path), n_trials=len(mine), resumed_with=len(done))
    json.dump(env, open(os.path.join(out, f"env_predict_{eng.key}.json"), "w", encoding="utf-8"), indent=2)
    t_start = time.time()
    todo = [t for t in mine if t["trial_id"] not in done]
    for n, t in enumerate(todo, 1):
        sub = t["trial_id"] in fp_ids
        rec = gen_record(eng, "predict", t["arm"], t["prompt"], rescore=sub)
        hist = " ".join(map(str, t["target"]))
        rec.update(trial_id=t["trial_id"], predictor=eng.key, item_id=t["item_id"], cond=t["cond"],
                   teacher_forced=eng.score(t["prompt"], hist, "incremental"))
        if sub:
            rec["teacher_forced_full_pass"] = eng.score(t["prompt"], hist, "full_pass")
        steps = rec.pop("steps")                   # keep the digit steps (digit_steps) and the final step only
        rec["final_step"] = steps[-1] if steps else None
        append(path, rec)
        if n % 100 == 0 or n == len(todo):
            el = time.time() - t_start
            print(f"[{n}/{len(todo)}] {t['trial_id']}: {rec['content']!r} | {el / n:.2f} s/trial, eta {(len(todo) - n) * el / n / 60:.1f} min", flush=True)
    # policy references on every item's full sequence
    refs = P.references()
    with open(os.path.join(out, f"policy_{eng.key}.jsonl"), "w", encoding="utf-8") as f:
        for it in items:
            h = " ".join(map(str, it["sequence"]))
            for instr in ("G", "F", "Fanon"):
                for method in ("incremental", "full_pass"):
                    for s in eng.score(refs[instr]["prompt"], h, method):
                        f.write(json.dumps(dict(scorer=eng.key, item_id=it["item_id"], generator=it["generator"],
                                                instruction=instr, history_sequence=h, **s)) + "\n")
    env.update(finished_utc=now(), seconds=round(time.time() - t_start, 1))
    json.dump(env, open(os.path.join(out, f"env_predict_{eng.key}.json"), "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["preflight", "corpus", "predict"])
    ap.add_argument("--model", required=True, choices=C.MODELS)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gate", default=None)
    ap.add_argument("--trials", default=None)
    ap.add_argument("--items", default=None)
    a = ap.parse_args()
    guard_out(a.out)
    os.makedirs(a.out, exist_ok=True)
    if a.stage != "preflight":
        if not a.gate:
            raise SystemExit("corpus and predict need --gate <passed gate json>")
        check_gate(a.gate, a.model)
    if a.stage == "predict" and not (a.trials and a.items):
        raise SystemExit("predict needs --trials and --items")
    from spar_dynamic.dice_crossed_guidance.models import load
    t0 = time.time()
    eng = load(a.model)
    print(f"loaded {a.model} in {time.time() - t0:.1f} s", flush=True)
    {"preflight": lambda: preflight(eng, a.out), "corpus": lambda: corpus(eng, a.out),
     "predict": lambda: predict(eng, a.out, a.trials, a.items)}[a.stage]()
    print(json.dumps(dict(stage=a.stage, model=a.model, seconds=round(time.time() - t0, 1))), flush=True)
