"""Open-weight A/B next-token scoring for LOULA_DICE_AB_LOGPROB v2.1 (runs on the rented GPU).

Serving is Experiment 21's validated loader, imported unchanged (dice_logprob.gpu_runner.Qwen): Qwen/Qwen3-32B at a
pinned commit, bf16 weights and activations, a separate fp32 output layer, batch size 1, deterministic flags, chat
template with enable_thinking=False (the assistant prefix ends with a fixed empty think block), one user message,
no system message, no tools.

Scored position: directly after the complete rendered assistant prefix, i.e. where the first visible answer token
would be generated. Primary arithmetic ("prefill"): one cached forward pass over the rendered prompt, the same
first step greedy generation takes and Experiment 21's incremental path with an empty history. Diagnostic
("tokenwise"): prefill only `<|im_start|>user\\n`, then feed every remaining prompt token one at a time through the
KV cache; its gap to prefill estimates the bf16 floor (handoff 5.5) and is never used in primary comparisons.

Modes (each reads a frozen trial-list JSON written locally by `freeze`):
  preflight    5 technical prompts: both methods, greedy completions, determinism repeats, label-token checks.
  calibration  72 orientations, primary method. Needs --gate pointing at a preflight diagnostics.json with PASS.
  screen       recognition screen, primary method. Needs --gate pointing at calibration_gate.json with PASS.

Usage: python -m spar_dynamic.dice_recognition_logprob.gpu <mode> --trials <json> --out <dir> [--gate <json>]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import time

from spar_dynamic.dice_recognition_logprob import config as C

RAW = {"preflight": "raw_preflight.jsonl", "calibration": "scored_orientations.jsonl", "screen": "scored_orientations.jsonl"}
USER_PREFIX = "<|im_start|>user\n"


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def check_gate(mode: str, gate_path: str | None) -> dict | None:
    """Stage transitions: calibration needs a passed preflight, screen a passed calibration gate."""
    if mode == "preflight":
        return None
    if not gate_path or not os.path.exists(gate_path):
        raise SystemExit(f"{mode} needs --gate <passed {'preflight diagnostics' if mode == 'calibration' else 'calibration gate'}>")
    g = json.load(open(gate_path, encoding="utf-8"))
    want = "preflight" if mode == "calibration" else "calibration"
    if g.get("stage") != want or g.get("overall") != "PASS":
        raise SystemExit(f"{mode} refused: {want} gate is {g.get('overall')!r} (stage {g.get('stage')!r})")
    return g


def guard_out(out_dir: str):
    """Never write into the frozen Experiment 21-23 folders."""
    p = os.path.abspath(out_dir).replace("\\", "/")
    for frozen in ("21_2026-10-29_dice_logprob", "22_2026-10-29_loula_dice_recognition_pilot",
                   "23_2026-10-29_loula_recognition_redesign"):
        if f"/{frozen}" in p:
            raise SystemExit(f"refusing to write into frozen experiment folder {frozen}")


def load_trials(path: str) -> list:
    trials = json.load(open(path, encoding="utf-8"))
    for t in trials:
        if sha(t["prompt"]) != t["prompt_sha256"]:
            raise SystemExit(f"{t['trial_id']}: prompt hash mismatch")
    return trials


def done_ids(raw_path: str, trials: list) -> set:
    """Resume: completed trial ids, refusing drift between the archive and the frozen trial list."""
    if not os.path.exists(raw_path):
        return set()
    want = {t["trial_id"]: t["prompt_sha256"] for t in trials}
    done = set()
    for line in open(raw_path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if want.get(r["trial_id"]) != r["prompt_sha256"]:
            raise SystemExit(f"resume refused: {r['trial_id']} not in the frozen trial list or prompt changed")
        if r["trial_id"] in done:
            raise SystemExit(f"resume refused: duplicate {r['trial_id']} in {raw_path}")
        done.add(r["trial_id"])
    return done


def label_ids(tok) -> dict:
    out = {}
    for lab in C.LABELS:
        ids = tok.encode(lab, add_special_tokens=False)
        sp = tok.encode(" " + lab, add_special_tokens=False)
        if len(ids) != 1:
            raise SystemExit(f"label {lab!r} is not a single token: {ids}")
        out[lab] = dict(id=ids[0], bytes=list(tok.decode(ids).encode("utf-8")),
                        space_id=sp[0] if len(sp) == 1 else None)
    return out


def scores_from_logits(logits, labels: dict, tok, top_n: int = C.TOP_N) -> dict:
    """Raw logits z_A, z_B, full-vocabulary log-probabilities, A+B mass and d = log P(A) - log P(B)."""
    import torch
    lp = torch.log_softmax(logits.float(), dim=-1)
    a, b = labels["A"]["id"], labels["B"]["id"]
    top = torch.topk(lp, top_n)
    arg = int(top.indices[0])
    return dict(z_A=float(logits[a]), z_B=float(logits[b]), logp_A=float(lp[a]), logp_B=float(lp[b]),
                mass_AB=float(lp[a].exp() + lp[b].exp()), d=float(lp[a] - lp[b]),
                logp_space_A=float(lp[labels["A"]["space_id"]]) if labels["A"]["space_id"] is not None else None,
                logp_space_B=float(lp[labels["B"]["space_id"]]) if labels["B"]["space_id"] is not None else None,
                argmax_token=tok.decode([arg]), argmax_id=arg, argmax_logprob=float(lp[arg]),
                entropy_nats=float(-(lp.exp() * lp).sum()),
                top=[dict(token=tok.decode([int(i)]), id=int(i), logprob=float(v))
                     for v, i in zip(top.values.tolist(), top.indices.tolist())])


class Scorer:
    def __init__(self, model_id=C.MODEL_ID, revision=C.REVISION):
        from spar_dynamic.dice_logprob.gpu_runner import Qwen
        self.q = Qwen(model_id, revision)
        self.tok = self.q.tok
        self.labels = label_ids(self.tok)
        self.user_prefix_ids = self.tok.encode(USER_PREFIX, add_special_tokens=False)

    def render(self, prompt: str) -> str:
        return self.q.render(prompt)

    def ids(self, prompt: str):
        text = self.render(prompt)
        return text, self.tok(text, return_tensors="pt", add_special_tokens=False).input_ids.to("cuda")

    def next_logits(self, prompt: str, method: str = C.PRIMARY_METHOD):
        import torch
        text, ids = self.ids(prompt)
        with torch.no_grad():
            if method == "prefill":
                logits = self.q.model(ids, use_cache=True).logits[0, -1]
            elif method == "tokenwise":
                k = len(self.user_prefix_ids)
                assert ids[0, :k].tolist() == self.user_prefix_ids, "rendered prompt does not start with the user turn"
                out = self.q.model(ids[:, :k], use_cache=True)
                for j in range(k, ids.shape[1]):
                    out = self.q.model(ids[:, j:j + 1], past_key_values=out.past_key_values, use_cache=True)
                logits = out.logits[0, -1]
            else:
                raise ValueError(method)
        return text, ids.shape[1], logits.float()

    def score(self, prompt: str, method: str = C.PRIMARY_METHOD) -> dict:
        t0 = time.time()
        text, n, logits = self.next_logits(prompt, method)
        return dict(method=method, rendered_sha256=sha(text), prompt_tokens=n, latency_ms=int(1000 * (time.time() - t0)),
                    **scores_from_logits(logits, self.labels, self.tok))

    def greedy(self, prompt: str, max_new: int = C.GREEDY_MAX_NEW_TOKENS) -> dict:
        import torch
        _, ids = self.ids(prompt)
        gen = []
        with torch.no_grad():
            out = self.q.model(ids, use_cache=True)
            for _ in range(max_new):
                nxt = int(out.logits[0, -1].float().argmax())
                if nxt in self.q.eos:
                    break
                gen.append(nxt)
                out = self.q.model(torch.tensor([[nxt]], device="cuda"), past_key_values=out.past_key_values, use_cache=True)
        return dict(greedy_ids=gen, greedy_text=self.tok.decode(gen),
                    greedy_first_token=self.tok.decode(gen[:1]) if gen else "", greedy_first_id=gen[0] if gen else None)

    def template_checks(self, prompt: str) -> dict:
        text = self.render(prompt)
        base = self.tok(text, add_special_tokens=False).input_ids
        ctx = {lab: self.tok(text + lab, add_special_tokens=False).input_ids == base + [v["id"]]
               for lab, v in self.labels.items()}
        return dict(ends_with_empty_think=text.endswith(C.THINK_SUFFIX), has_system_turn="<|im_start|>system" in text,
                    n_user_turns=text.count("<|im_start|>user"), label_appends_single_token=ctx,
                    assistant_prefix_tail=text[-40:])


def run(mode: str, trials_path: str, out_dir: str, gate_path: str | None = None, model_id=C.MODEL_ID, revision=C.REVISION):
    guard_out(out_dir)
    gate = check_gate(mode, gate_path)
    os.makedirs(out_dir, exist_ok=True)
    trials = load_trials(trials_path)
    raw_path = os.path.join(out_dir, RAW[mode])
    done = done_ids(raw_path, trials)
    t_load = time.time()
    sc = Scorer(model_id, revision)
    env = dict(sc.q.env(), load_seconds=round(time.time() - t_load, 1), mode=mode, tag=C.TAG,
               expected_revision=revision, revision_match=sc.q.commit == revision,
               chat_template_sha256=sha(sc.tok.chat_template or ""), label_tokens=sc.labels,
               user_prefix_ids=sc.user_prefix_ids, primary_method=C.PRIMARY_METHOD,
               trials_file_sha256=hashlib.sha256(open(trials_path, "rb").read()).hexdigest(), n_trials=len(trials),
               resumed_completed=len(done), gate_file=gate_path, epsilon=(gate or {}).get("epsilon"),
               started_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    if mode == "preflight":
        env["template_checks"] = sc.template_checks(trials[0]["prompt"])
    with open(os.path.join(out_dir, f"env_{mode}.json"), "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)
    for n, t in enumerate(trials, 1):
        if t["trial_id"] in done:
            continue
        rec = dict({k: v for k, v in t.items()}, order_index=n, model_id=model_id, model_commit=sc.q.commit,
                   served="local-transformers", reasoning_mode="enable_thinking=False", **sc.score(t["prompt"]))
        if mode == "preflight":
            rec["diagnostic"] = sc.score(t["prompt"], C.DIAGNOSTIC_METHOD)
            rec.update(sc.greedy(t["prompt"]))
            rec["template_checks"] = sc.template_checks(t["prompt"])
            if n == 1:
                rec["determinism_repeats"] = [sc.score(t["prompt"])["d"] for _ in range(C.DETERMINISM_REPEATS)]
        rec["timestamp"] = dt.datetime.now(dt.timezone.utc).isoformat()
        with open(raw_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{n}/{len(trials)}] {t['trial_id']}: d={rec['d']:+.4f} mass={rec['mass_AB']:.4f} argmax={rec['argmax_token']!r}"
              + (f" greedy={rec['greedy_text']!r}" if mode == "preflight" else ""), flush=True)
    with open(os.path.join(out_dir, f"env_{mode}.json"), "w", encoding="utf-8") as f:
        json.dump(dict(env, finished_utc=dt.datetime.now(dt.timezone.utc).isoformat()), f, indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preflight", "calibration", "screen"])
    ap.add_argument("--trials", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gate", default=None)
    ap.add_argument("--model", default=C.MODEL_ID)
    ap.add_argument("--revision", default=C.REVISION)
    a = ap.parse_args()
    run(a.mode, a.trials, a.out, a.gate, a.model, a.revision)
