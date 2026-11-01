"""GPU stages for SPAR_EXP30_SIX_ROLL_RECOGNITION_v1.0 (one judge per process; run on the rented GPU).

Serving is Experiment 27-29's engine (`dice_crossed_guidance.models`), unchanged: bf16 weights and activations, fp32 output
layer and logits, batch 1, KV-cache decoding, full-vocabulary log-softmax, greedy argmax, no sampling, no logit processors.

Answer scoring (`Judge.ask`): the scored position is directly after the complete rendered assistant prefix, i.e. the first
answer token of the frozen question. Primary arithmetic `prefill`: one cached forward pass over the rendered prompt (the first
step greedy generation takes), then a bounded greedy completion from the same cache. Floor arithmetic `tokenwise`: the first
prompt token prefilled, every remaining prompt token fed one at a time through the KV cache (first replicate of each prompt).

Stages (each writes under <root>/<stage>/<model>/):
  preflight    vocabulary scan and label-token checks; archival G and F (Experiment 28 prompts) x2; 4 technical prompts x3;
               the generative-policy benchmark (4 sources x authentic/swap/repeat six-roll histories teacher-forced under the
               source instruction, both arithmetic paths) -> <root>/policy_benchmark/<model>/.
  calibration  36 calibration prompts once each. Needs a PASS preflight gate.
  main         32 recognition prompts x 3 identical calls (seeded shuffle; resumable, append-only). Needs a PASS calibration gate.
  chain        preflight -> gate -> calibration -> gate -> main -> checks, stopping at the first FAIL (judge-level gating).

Usage: python -m spar_dynamic.dice_six_roll_recognition.gpu <stage> --model {qwen,mistral} [--root <dir>]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import time
from pathlib import Path

from spar_dynamic.dice_logprob_crossmodel.gpu import append, vocab_scan
from spar_dynamic.dice_six_roll_recognition import config as C
from spar_dynamic.dice_six_roll_recognition import stimuli as S

PKG = Path(__file__).resolve().parent
RAW = "presentations.jsonl"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def guard_out(out_dir):
    for part in os.path.abspath(str(out_dir)).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= C.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


def stage_dir(root, stage, model) -> Path:
    return Path(root) / stage / model


def code_sha() -> dict:
    from spar_dynamic.dice_six_roll_recognition.gates import canonical_sha
    files = sorted(PKG.glob("*.py")) + [PKG.parent / "dice_crossed_guidance" / "models.py", PKG.parent / "dice_logprob_crossmodel" / "gpu.py",
                                        PKG.parent / "dice_logprob" / "gpu_runner.py"]
    return {f"{p.parent.name}/{p.name}": canonical_sha(p) for p in files}


def check_gate(path, model, stage):
    if not os.path.exists(path):
        raise SystemExit(f"{path} missing; {stage} refused")
    g = json.load(open(path, encoding="utf-8"))
    if g.get("overall") != "PASS" or g.get("model") != model or g.get("stage") != stage:
        raise SystemExit(f"gate {path} is {g.get('overall')} for {g.get('model')} ({g.get('stage')}); refusing")
    if g.get("prompt_sha256") != S.all_prompt_sha():
        raise SystemExit("gate prompt hashes differ from the frozen prompts; refusing")
    return g


# ---------- answer-token scoring ----------

def label_info(eng) -> dict:
    out = {}
    for lab in C.LABELS:
        ids, sp = eng.hist_ids(lab), eng.hist_ids(" " + lab)
        out[lab] = dict(id=ids[0] if len(ids) == 1 else None, n_tokens=len(ids), text=eng.decode(ids), space_id=sp[0] if len(sp) == 1 else None)
    return out


class Judge:
    """First-answer-token scores and a bounded greedy answer on the engine's model (torch imported lazily)."""

    def __init__(self, eng):
        self.eng = eng
        self.labels = label_info(eng)

    def context_check(self, prompt) -> dict:
        """Each label appends as exactly one token after the assistant prefix."""
        if self.eng.key == "qwen":
            base = self.eng.prompt_ids(prompt)
            text = self.eng.rendered_text(prompt)
            ok = {lab: self.eng.tok(text + lab, add_special_tokens=False).input_ids == base + [v["id"]] for lab, v in self.labels.items()}
            return dict(label_appends_single_token=ok, assistant_prefix_tail=text[-40:])
        return dict(label_appends_single_token={lab: v["id"] is not None for lab, v in self.labels.items()},
                    note="mistral_common encodes the prompt at token level; the answer token is appended as an id",
                    assistant_prefix_tail=self.eng.rendered_text(prompt)[-40:])

    def _first(self, ids, method):
        import torch
        if method == "prefill":
            out = self.eng._fwd(ids)
        else:
            out = self.eng._fwd(ids[:1])
            for t in ids[1:]:
                out = self.eng._fwd([t], out.past_key_values)
        return out, torch.log_softmax(out.logits[0, -1].float(), dim=-1)

    def _scores(self, lp, suffix="") -> dict:
        a, b = self.labels["A"], self.labels["B"]
        d = {f"logp_A{suffix}": float(lp[a["id"]]), f"logp_B{suffix}": float(lp[b["id"]])}
        if not suffix:
            import torch
            top = torch.topk(lp, C.TOP_N)
            arg = int(top.indices[0])
            d.update(logp_space_A=float(lp[a["space_id"]]) if a["space_id"] is not None else None,
                     logp_space_B=float(lp[b["space_id"]]) if b["space_id"] is not None else None,
                     argmax_id=arg, argmax_token=self.eng.decode([arg]), argmax_logprob=float(lp[arg]),
                     entropy_nats=float(-(lp.exp() * lp).sum()),
                     top=[[int(i), self.eng.decode([int(i)]), float(v)] for v, i in zip(top.values.tolist(), top.indices.tolist())])
        return d

    def ask(self, prompt, tokenwise=False) -> dict:
        import torch
        with torch.no_grad():
            t0 = time.time()
            ids = self.eng.prompt_ids(prompt)
            out, lp = self._first(ids, "prefill")
            rec = dict(prompt_tokens=len(ids), rendered_prompt_sha256=S.sha256(self.eng.rendered_text(prompt)), **self._scores(lp))
            gen, finish, cur = [], "length", lp
            for _ in range(C.ANSWER_MAX_NEW_TOKENS):
                nxt = int(torch.argmax(cur).item())
                if nxt in self.eng.eos:
                    finish = "stop"
                    break
                gen.append(nxt)
                out = self.eng._fwd([nxt], out.past_key_values)
                cur = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
            rec.update(greedy_ids=gen, greedy_text=self.eng.decode(gen), finish_reason=finish, latency_ms=int(1000 * (time.time() - t0)))
            if tokenwise:
                rec.update(self._scores(self._first(ids, "tokenwise")[1], "_tokenwise"))
        return rec


def derive(rec: dict) -> dict:
    """d = log P(A) - log P(B), A+B mass, label-conditional pA, strict format, the tokenwise gap."""
    import math
    a, b = rec["logp_A"], rec["logp_B"]
    rec.update(d=a - b, mass_AB=math.exp(a) + math.exp(b), pA=1.0 / (1.0 + math.exp(b - a)),
               greedy_letter=rec["greedy_text"] if rec["greedy_text"] in C.LABELS else None,
               strict_valid=rec["greedy_text"] in C.LABELS and rec["finish_reason"] == "stop")
    if "logp_A_tokenwise" in rec:
        rec.update(d_tokenwise=rec["logp_A_tokenwise"] - rec["logp_B_tokenwise"])
        rec["abs_delta_d"] = abs(rec["d"] - rec["d_tokenwise"])
    return rec


# ---------- records ----------

def env_record(eng, judge, stage, jobs, seed) -> dict:
    import accelerate
    import huggingface_hub
    g10 = S.seq(C.REFERENCES[("qwen", "G")])
    return dict(eng.env(), study=C.TAG, stage=stage, started_utc=now(), order_seed=seed, job_order=jobs, n_jobs=len(jobs),
                prompt_sha256=S.all_prompt_sha(), archival_prompt_sha256={k: S.sha256(v) for k, v in S.SOURCE_INSTRUCTION.items()},
                rendered_G=eng.rendered_text(S.SOURCE_INSTRUCTION["G"]), g10_history_ids=eng.hist_ids(g10),
                face_single_tokens={str(f): eng.hist_ids(str(f)) for f in C.FACES}, label_tokens=judge.labels,
                label_context=judge.context_check(S.tech_cells()[0]["prompt"]), answer_max_new_tokens=C.ANSWER_MAX_NEW_TOKENS,
                accelerate=accelerate.__version__, huggingface_hub=huggingface_hub.__version__, code_sha256=code_sha(),
                code_commit=os.environ.get("SPAR_CODE_COMMIT", "unknown"), hourly_usd=os.environ.get("SPAR_HOURLY_USD"))


def presentation_record(eng, judge, stage, cell, rep, order_index, tokenwise) -> dict:
    r = judge.ask(cell["prompt"], tokenwise=tokenwise)
    rec = dict(study=C.TAG, stage=stage, judge=eng.key, model_id=eng.model_id, model_commit=eng.commit, replicate=rep,
               order_index=order_index, trial_id=f"{eng.key}<-{cell['prompt_id']}-{rep}", timestamp=now(),
               decoding="first answer token scored by prefill; greedy argmax completion, no sampling, no logit processors",
               **{k: v for k, v in cell.items() if k != "prompt"}, prompt=cell["prompt"], **r)
    rec["prompt_sha256_check"] = S.sha256(rec["prompt"]) == cell["prompt_sha256"]
    return derive(rec)


def archival_record(eng, job, rep) -> dict:
    prompt = S.SOURCE_INSTRUCTION[job]
    g = eng.generate(prompt)
    return dict(study=C.TAG, stage="preflight", kind="archival", model=eng.key, job=job, condition=job, replicate=rep,
                trial_id=f"{eng.key}-archival-{job}-{rep}", prompt=prompt, prompt_sha256=S.sha256(prompt), timestamp=now(), **g)


def policy_rows(eng) -> list:
    """Every source's authentic, swap and repeat six-roll history teacher-forced under the source instruction (G or F), by this
    model, with both arithmetic paths: the six-face vectors before each of the six faces."""
    rows = []
    for (s, i), fx in S.fixtures().items():
        prompt = S.SOURCE_INSTRUCTION[i]
        for cand in ("authentic", "swap", "repeat"):
            hist = S.seq(fx[cand])
            for method in ("incremental", "full_pass"):
                for r in eng.score(prompt, hist, method):
                    assert r["history_face"] == fx[cand][r["position"] - 1]
                    rows.append(dict(scorer=eng.key, source=s, source_instruction=i, source_id=S.source_id(s, i), candidate=cand,
                                     history=hist, prompt_sha256=S.sha256(prompt), diagonal=s == eng.key, **r))
    return rows


# ---------- stages ----------

def _seed(model, stage):
    return C.ORDER_SEED[model] + {"main": 0, "calibration": 50, "preflight": 100}[stage]


def jobs_for(model, stage) -> list:
    cells = {"preflight": S.tech_cells, "calibration": S.calibration_cells, "main": S.prompt_cells}[stage]()
    reps = {"preflight": C.PREFLIGHT_REPEATS, "calibration": 1, "main": C.N_REPLICATES}[stage]
    jobs = [[c["prompt_id"], i] for c in cells for i in range(1, reps + 1)]
    random.Random(_seed(model, stage)).shuffle(jobs)
    return jobs


def _cells(stage) -> dict:
    return {c["prompt_id"]: c for c in {"preflight": S.tech_cells, "calibration": S.calibration_cells, "main": S.prompt_cells}[stage]()}


def _present(eng, judge, out: Path, stage, gate_path=None, extra_env=None):
    from spar_dynamic.dice_six_roll_recognition.gates import canonical_sha
    out.mkdir(parents=True, exist_ok=True)
    raw = out / RAW
    cells, jobs = _cells(stage), jobs_for(eng.key, stage)
    done = set()
    if raw.exists():
        if stage != "main":
            raise SystemExit(f"{raw} exists; {stage} is never appended to")
        for l in open(raw, encoding="utf-8"):                       # resume: refuse drift, skip completed jobs
            r = json.loads(l)
            if r["prompt_id"] not in cells or r["prompt_sha256"] != cells[r["prompt_id"]]["prompt_sha256"] or r["judge"] != eng.key:
                raise SystemExit(f"prompt or judge drift in {raw} at {r['trial_id']}; refusing to resume")
            if (r["prompt_id"], r["replicate"]) in done:
                raise SystemExit(f"duplicate {r['trial_id']} in {raw}; refusing to resume")
            done.add((r["prompt_id"], r["replicate"]))
    env = env_record(eng, judge, stage, jobs, _seed(eng.key, stage))
    env.update(extra_env or {}, resumed_with=len(done))
    if gate_path:
        env["gate_sha256"] = canonical_sha(gate_path)
    env_path = out / (f"env_{stage}.json" if not done else f"env_{stage}_resume{len(done)}.json")
    json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2)
    t0 = time.time()
    todo = [(n, pid, rep) for n, (pid, rep) in enumerate(jobs, 1) if (pid, rep) not in done]
    for j, (n, pid, rep) in enumerate(todo, 1):
        rec = presentation_record(eng, judge, stage, cells[pid], rep, n, tokenwise=rep == 1)
        append(raw, rec)
        el = time.time() - t0
        print(f"[{stage} {n}/{len(jobs)}] {pid}-{rep}: d={rec['d']:+.3f} mass={rec['mass_AB']:.3f} {rec['greedy_text'][:30]!r} | "
              f"{el / j:.2f} s/call", flush=True)
    env.update(finished_utc=now(), seconds=round(time.time() - t0, 1), presentations_sha256=canonical_sha(raw),
               max_memory_allocated_gb=eng.env_common()["max_memory_allocated_gb"])
    json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2)
    return env


def preflight(eng, judge, root):
    from spar_dynamic.dice_six_roll_recognition.gates import canonical_sha
    out = stage_dir(root, "preflight", eng.key)
    if (out / "archival.jsonl").exists():
        raise SystemExit(f"{out} already holds a preflight; never appended to")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    vs = vocab_scan(eng)
    vs_sec = round(time.time() - t0, 1)
    t0 = time.time()
    arch = out / "archival.jsonl"
    for k in C.INSTRUCTIONS:
        for i in range(1, C.ARCHIVAL_REPEATS + 1):
            append(arch, archival_record(eng, k, i))
    arch_sec = round(time.time() - t0, 1)
    t0 = time.time()
    pol = stage_dir(root, "policy_benchmark", eng.key)
    pol.mkdir(parents=True, exist_ok=True)
    with open(pol / "policy_teacher_forced.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for row in policy_rows(eng):
            f.write(json.dumps(row) + "\n")
    pol_sec = round(time.time() - t0, 1)
    _present(eng, judge, out, "preflight", extra_env=dict(vocab_scan=vs, vocab_scan_seconds=vs_sec, archival_seconds=arch_sec,
                                                            policy_seconds=pol_sec, archival_sha256=canonical_sha(arch),
                                                            policy_sha256=canonical_sha(pol / "policy_teacher_forced.jsonl")))


def calibration(eng, judge, root):
    gate = stage_dir(root, "preflight", eng.key) / "preflight_gates.json"
    check_gate(gate, eng.key, "preflight")
    _present(eng, judge, stage_dir(root, "calibration", eng.key), "calibration", gate_path=gate)


def main(eng, judge, root):
    gate = stage_dir(root, "calibration", eng.key) / "calibration_gate.json"
    g = check_gate(gate, eng.key, "calibration")
    _present(eng, judge, stage_dir(root, "main", eng.key), "main", gate_path=gate, extra_env=dict(epsilon=g["epsilon"]))


def chain(eng, judge, root, verify=None) -> str:
    """preflight -> gate -> calibration -> gate -> main -> checks for one judge; returns the last stage reached."""
    from spar_dynamic.dice_six_roll_recognition import gates as Gt
    status = Path(root) / f"stage_status_{eng.key}.txt"

    def log(msg):
        with open(status, "a", encoding="utf-8") as f:
            f.write(f"{now()} {msg}\n")
        print(msg, flush=True)
    for stage, run, gate_fn in (("preflight", preflight, Gt.write_preflight_gate), ("calibration", calibration, Gt.write_calibration_gate),
                                ("main", main, Gt.write_main_checks)):
        if verify:
            verify()
        run(eng, judge, root)
        res = gate_fn(eng.key, root)
        log(f"{stage} {eng.key} {res['overall']}")
        if res["overall"] != "PASS":
            log(f"STOP {eng.key} after {stage}")
            return stage
    log(f"DONE {eng.key}")
    return "main"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["preflight", "calibration", "main", "chain"])
    ap.add_argument("--model", required=True, choices=C.MODELS)
    ap.add_argument("--root", default=str(C.EXP))
    a = ap.parse_args()
    guard_out(a.root)
    from spar_dynamic.dice_crossed_guidance.models import load
    t0 = time.time()
    eng = load(a.model)
    judge = Judge(eng)
    print(f"loaded {a.model} in {time.time() - t0:.1f} s; labels {judge.labels}", flush=True)
    if a.stage == "chain":
        from spar_dynamic.dice_six_roll_recognition.__main__ import verify_frozen
        chain(eng, judge, a.root, verify=verify_frozen if Path(a.root).resolve() == C.EXP.resolve() else None)
    else:
        {"preflight": preflight, "calibration": calibration, "main": main}[a.stage](eng, judge, a.root)
    print(json.dumps(dict(stage=a.stage, model=a.model, seconds=round(time.time() - t0, 1))), flush=True)
