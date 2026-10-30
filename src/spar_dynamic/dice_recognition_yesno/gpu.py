"""Open-weight Yes/No next-token scoring for LOULA_DICE_YESNO_LOGPROB v3.0 (runs on the rented GPU).

Serving, scored position, primary ("prefill") and diagnostic ("tokenwise") arithmetic, greedy completion, template
checks, resume and hash checks are v2.1's (dice_recognition_logprob.gpu), which itself loads Experiment 21's
validated Qwen unchanged. Only the two scored labels change: `Yes` and `No`, z = log P(Yes) - log P(No).

Modes (each reads a frozen trial-list JSON written locally by `freeze`):
  preflight    5 technical prompts: both methods, greedy completions, determinism repeats, label-token checks.
  calibration  144 prompts, primary method. Needs --gate pointing at a preflight diagnostics.json with PASS.
  screen       160 prompts, primary method. Needs --gate pointing at calibration_gate.json with PASS.

Usage: python -m spar_dynamic.dice_recognition_yesno.gpu <mode> --trials <json> --out <dir> [--gate <json>]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import time

from spar_dynamic.dice_recognition_logprob import gpu as G24
from spar_dynamic.dice_recognition_yesno import config as C

RAW = G24.RAW
FROZEN = ("21_2026-10-29_dice_logprob", "22_2026-10-29_loula_dice_recognition_pilot",
          "23_2026-10-29_loula_recognition_redesign", "24_2026-10-29_loula_ab_logprob_pilot")
check_gate, load_trials, done_ids, sha = G24.check_gate, G24.load_trials, G24.done_ids, G24.sha


def guard_out(out_dir: str):
    """Never write into the frozen Experiment 21-24 folders."""
    p = os.path.abspath(out_dir).replace("\\", "/")
    for frozen in FROZEN:
        if f"/{frozen}" in p:
            raise SystemExit(f"refusing to write into frozen experiment folder {frozen}")


def label_ids(tok) -> dict:
    out = {}
    for lab in C.LABELS:
        ids = tok.encode(lab, add_special_tokens=False)
        sp = tok.encode(" " + lab, add_special_tokens=False)
        if len(ids) != 1:
            raise SystemExit(f"label {lab!r} is not a single token: {ids}")
        out[lab] = dict(id=ids[0], bytes=list(tok.decode(ids).encode("utf-8")), space_id=sp[0] if len(sp) == 1 else None)
    return out


def scores_from_logits(logits, labels: dict, tok, top_n: int = C.TOP_N) -> dict:
    """Raw logits, full-vocabulary log-probabilities of Yes and No, their mass and z = log P(Yes) - log P(No)."""
    import torch
    lp = torch.log_softmax(logits.float(), dim=-1)
    y, n = labels["Yes"]["id"], labels["No"]["id"]
    top = torch.topk(lp, top_n)
    arg = int(top.indices[0])
    lower = {w: tok.encode(w, add_special_tokens=False) for w in ("yes", "no")}
    return dict(z_logit_Yes=float(logits[y]), z_logit_No=float(logits[n]), logp_Yes=float(lp[y]), logp_No=float(lp[n]),
                mass_YN=float(lp[y].exp() + lp[n].exp()), z=float(lp[y] - lp[n]),
                logp_space_Yes=float(lp[labels["Yes"]["space_id"]]) if labels["Yes"]["space_id"] is not None else None,
                logp_space_No=float(lp[labels["No"]["space_id"]]) if labels["No"]["space_id"] is not None else None,
                logp_lower={w: float(lp[i[0]]) for w, i in lower.items() if len(i) == 1},
                argmax_token=tok.decode([arg]), argmax_id=arg, argmax_logprob=float(lp[arg]),
                entropy_nats=float(-(lp.exp() * lp).sum()),
                top=[dict(token=tok.decode([int(i)]), id=int(i), logprob=float(v))
                     for v, i in zip(top.values.tolist(), top.indices.tolist())])


class Scorer(G24.Scorer):
    def __init__(self, model_id=C.MODEL_ID, revision=C.REVISION):
        super().__init__(model_id, revision)
        self.labels = label_ids(self.tok)                # Yes/No replace v2.1's A/B everywhere below

    def score(self, prompt: str, method: str = C.PRIMARY_METHOD) -> dict:
        t0 = time.time()
        text, n, logits = self.next_logits(prompt, method)
        return dict(method=method, rendered_sha256=sha(text), prompt_tokens=n, latency_ms=int(1000 * (time.time() - t0)),
                    **scores_from_logits(logits, self.labels, self.tok))


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
        rec = dict(t, order_index=n, model_id=model_id, model_commit=sc.q.commit, served="local-transformers",
                   reasoning_mode="enable_thinking=False", **sc.score(t["prompt"]))
        if mode == "preflight":
            rec["diagnostic"] = sc.score(t["prompt"], C.DIAGNOSTIC_METHOD)
            rec.update(sc.greedy(t["prompt"]))
            rec["template_checks"] = sc.template_checks(t["prompt"])
            if n == 1:
                rec["determinism_repeats"] = [sc.score(t["prompt"])["z"] for _ in range(C.DETERMINISM_REPEATS)]
        rec["timestamp"] = dt.datetime.now(dt.timezone.utc).isoformat()
        with open(raw_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{n}/{len(trials)}] {t['trial_id']}: z={rec['z']:+.4f} mass={rec['mass_YN']:.4f} argmax={rec['argmax_token']!r}"
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
