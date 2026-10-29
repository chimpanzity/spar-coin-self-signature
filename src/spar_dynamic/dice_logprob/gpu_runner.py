"""Open-weight runner for DICE_LOGPROB_v1.0 (amendment 2026-10-29: SiliconFlow exposes no logprobs and is
not deterministic at temperature 0, so Qwen3-32B is served from its open weights on a rented GPU).

Serving: transformers, bf16 (output layer fp32), batch size 1, greedy decoding (argmax of the full next-token distribution,
no sampling, no repetition penalty or other logit processors), max 128 new tokens, stop at the chat
template's end-of-turn token. Non-thinking mode is Qwen3's documented switch: the chat template with
enable_thinking=False, which ends the assistant prefix with an empty think block. One user message, no
system message, no tools.

Probabilities are exact: every step stores the log-softmax of the full vocabulary for all six face
tokens (bare digit and, where it is a single token, space+digit), the chosen token and the top 20.
`raw_logprobs_content` mimics the OpenAI logprobs structure so extract.align_faces can read it: each
token's `top_logprobs` is the true top 20 plus the six same-shape face tokens with their exact values.

Matched-prefix scoring (handoff 6.4): for instruction X in {G, F} and history H in {modal G, modal F},
one teacher-forced forward pass over template(X) + H gives the exact six-face distribution at every
position k given the identical assistant prefix h_1 .. h_{k-1}.

Modes:
  preflight  10 G + 10 F + each S/W condition once (seeded shuffle), then matched-prefix scoring.
  main       --replicates N of all 15 conditions (seeded shuffle), then matched-prefix scoring.
             Requires --execute and --confirm-preflight-id.
  control_preflight  generic-model control (amendment v1.1): 3 each of G, F, N (seeded shuffle), then
                     matched-prefix scoring of every instruction x every modal history (G, F, N).
  control_main       --replicates N each of G, F, N, then the same matched-prefix scoring.
                     Requires --execute and --confirm-preflight-id.

Usage: python -m spar_dynamic.dice_logprob.gpu_runner preflight --model Qwen/Qwen3-32B --out <dir>
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import platform
import random
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch  # noqa: E402

from spar_dynamic.dice_logprob import prompts  # noqa: E402

ORDER_SEED = 20261029
CONTROL_ORDER_SEED = 20261030      # generic-model control (amendment v1.1)
CONTROL_PREFLIGHT_N = 3
MAX_NEW_TOKENS = 128
TOP_N = 20
FACES = (1, 2, 3, 4, 5, 6)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Qwen:
    def __init__(self, model_id: str, revision: str | None = None):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.manual_seed(0)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.use_deterministic_algorithms(True, warn_only=True)
        self.tok = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, dtype=torch.bfloat16,
                                                          device_map="cuda", attn_implementation="sdpa")
        self.model.eval()
        # Output layer in fp32 so logits are not rounded to bf16 (bf16 logits step ~0.06-0.125 nats in the tail).
        # A separate fp32 copy, so tied input embeddings (small Qwen3 models) stay bf16.
        w = self.model.lm_head.weight.detach().float().clone()
        head = torch.nn.Linear(w.shape[1], w.shape[0], bias=False, device=w.device, dtype=torch.float32)
        head.weight.data = w
        head.register_forward_pre_hook(lambda mod, args: (args[0].float(),))
        self.model.lm_head = head
        from huggingface_hub import hf_hub_download
        self.commit = os.path.basename(os.path.dirname(hf_hub_download(model_id, "config.json", revision=revision)))
        self.model_id = model_id
        gc_eos = self.model.generation_config.eos_token_id
        self.eos = set(gc_eos if isinstance(gc_eos, list) else [gc_eos]) | {self.tok.eos_token_id}
        self.face_bare, self.face_space = {}, {}
        for f in FACES:
            b = self.tok.encode(str(f), add_special_tokens=False)
            s = self.tok.encode(" " + str(f), add_special_tokens=False)
            assert len(b) == 1, f"face {f} is not one token"
            self.face_bare[f] = b[0]
            self.face_space[f] = s[0] if len(s) == 1 else None

    def env(self) -> dict:
        import transformers
        p = torch.cuda.get_device_properties(0)
        return dict(model_id=self.model_id, model_commit=self.commit,
                    dtype="bfloat16 weights and activations; lm_head and logits fp32", gpu=p.name, gpu_mem_gb=round(p.total_memory / 2**30, 1),
                    cuda=torch.version.cuda, torch=torch.__version__, transformers=transformers.__version__,
                    python=platform.python_version(), driver=_driver(), eos_ids=sorted(self.eos),
                    face_bare_ids=self.face_bare, face_space_ids=self.face_space,
                    deterministic=dict(cudnn_deterministic=True, tf32=False, use_deterministic_algorithms="warn_only",
                                       CUBLAS_WORKSPACE_CONFIG=os.environ.get("CUBLAS_WORKSPACE_CONFIG")))

    def render(self, prompt: str) -> str:
        return self.tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)

    def _faces(self, lp: torch.Tensor) -> dict:
        return dict(bare={f: lp[i].item() for f, i in self.face_bare.items()},
                    space={f: (lp[i].item() if i is not None else None) for f, i in self.face_space.items()})

    def _step(self, lp: torch.Tensor, chosen: int) -> dict:
        top = torch.topk(lp, TOP_N)
        top_list = [(int(i), float(v)) for v, i in zip(top.values.tolist(), top.indices.tolist())]
        txt = self.tok.decode([chosen])
        shape_ids = self.face_space if txt.startswith(" ") and len(txt) == 2 else self.face_bare
        ids = {i for i, _ in top_list} | {i for i in shape_ids.values() if i is not None}
        alts = sorted(((i, lp[i].item()) for i in ids), key=lambda x: -x[1])
        return dict(token=txt, token_id=chosen, logprob=lp[chosen].item(), bytes=list(txt.encode("utf-8")),
                    top_logprobs=[dict(token=self.tok.decode([i]), token_id=i, logprob=v,
                                       bytes=list(self.tok.decode([i]).encode("utf-8")), in_true_top20=i in {j for j, _ in top_list})
                                  for i, v in alts],
                    face_logprobs_exact=self._faces(lp),
                    entropy_bits=float(-(lp.exp() * lp).sum().item() / 0.6931471805599453))

    @torch.no_grad()
    def generate(self, prompt: str) -> dict:
        text = self.render(prompt)
        ids = self.tok(text, return_tensors="pt", add_special_tokens=False).input_ids.to("cuda")
        t0 = time.time()
        out = self.model(ids, use_cache=True)
        steps, gen, finish = [], [], "length"
        for _ in range(MAX_NEW_TOKENS):
            lp = torch.log_softmax(out.logits[0, -1].float(), dim=-1)
            nxt = int(torch.argmax(lp).item())
            if nxt in self.eos:
                finish = "stop"
                steps.append(dict(eos=True, token_id=nxt, logprob=lp[nxt].item()))
                break
            steps.append(self._step(lp, nxt))
            gen.append(nxt)
            out = self.model(torch.tensor([[nxt]], device="cuda"), past_key_values=out.past_key_values, use_cache=True)
        content = self.tok.decode(gen)
        tokens = [s for s in steps if not s.get("eos")]
        return dict(rendered_prompt=text, rendered_prompt_sha256=sha(text), prompt_tokens=ids.shape[1],
                    completion_tokens=len(gen), generated_ids=gen, raw_choice_content=content, finish_reason=finish,
                    eos_step=steps[-1] if steps and steps[-1].get("eos") else None,
                    raw_logprobs_content=tokens, latency_ms=int(1000 * (time.time() - t0)))

    @torch.no_grad()
    def score_prefix(self, prompt: str, history: str, method: str = "incremental") -> list:
        """Exact six-face distribution at each face position of `history`, teacher-forced after template(prompt).

        incremental: the history is fed one token at a time through the KV cache, the same arithmetic path as
        generate(), so scoring a model's own output reproduces its generation exactly (primary method).
        full_pass: one forward pass over prompt + history; differs from incremental only by bf16 summation
        order, so the gap between the two estimates the numerical precision floor (reported, not used).
        """
        pre = self.tok(self.render(prompt), return_tensors="pt", add_special_tokens=False).input_ids.to("cuda")
        hist = self.tok(history, add_special_tokens=False).input_ids
        rows = []
        if method == "incremental":
            out = self.model(pre, use_cache=True)
            for t in hist:
                rows.append(torch.log_softmax(out.logits[0, -1].float(), dim=-1))
                out = self.model(torch.tensor([[t]], device="cuda"), past_key_values=out.past_key_values, use_cache=True)
        else:
            ids = torch.cat([pre[0], torch.tensor(hist, device="cuda")]).unsqueeze(0)
            lp = torch.log_softmax(self.model(ids).logits[0].float(), dim=-1)
            rows = [lp[pre.shape[1] + j - 1] for j in range(len(hist))]
        face_ids = set(self.face_bare.values()) | {v for v in self.face_space.values() if v is not None}
        out_rows, k = [], 0
        for t, row in zip(hist, rows):
            if t in face_ids:
                k += 1
                out_rows.append(dict(method=method, position=k, history_face=int(self.tok.decode([t]).strip()),
                                     history_token_id=t, face_logprobs_exact=self._faces(row),
                                     argmax_token=self.tok.decode([int(row.argmax())]), argmax_logprob=row.max().item()))
        return out_rows


def _driver() -> str:
    try:
        import subprocess
        return subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True).strip()
    except Exception:
        return "unknown"


def run(mode: str, model_id: str, out_dir: str, replicates: int, revision: str | None = None):
    os.makedirs(out_dir, exist_ok=True)
    control = mode.startswith("control_")
    conds = {c["condition"]: c for c in (prompts.control_conditions() if control else prompts.conditions())}
    refs = ("G", "F", "N") if control else ("G", "F")
    if mode == "preflight":
        jobs = [("G", i) for i in range(1, 11)] + [("F", i) for i in range(1, 11)] + \
               [(k, 1) for k in conds if k not in ("G", "F")]
    elif mode == "control_preflight":
        jobs = [(k, i) for k in refs for i in range(1, CONTROL_PREFLIGHT_N + 1)]
    else:
        jobs = [(k, i) for k in conds for i in range(1, replicates + 1)]
    random.Random(CONTROL_ORDER_SEED if control else ORDER_SEED).shuffle(jobs)
    raw_path = os.path.join(out_dir, "raw_attempts.jsonl")
    done = set()
    if os.path.exists(raw_path):                      # resume: refuse drift, skip completed trials
        for l in open(raw_path, encoding="utf-8"):
            r = json.loads(l)
            assert r["prompt_sha256"] == conds[r["condition"]]["prompt_sha256"] and r["model_id"] == model_id
            done.add((r["condition"], r["replicate"]))
    t_load = time.time()
    q = Qwen(model_id, revision)
    env = dict(q.env(), load_seconds=round(time.time() - t_load, 1), mode=mode,
               order_seed=CONTROL_ORDER_SEED if control else ORDER_SEED,
               prompt_sha256={k: c["prompt_sha256"] for k, c in conds.items()},
               max_new_tokens=MAX_NEW_TOKENS, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
               n_jobs=len(jobs), job_order=jobs, chat_template_sha256=sha(q.tok.chat_template or ""))
    with open(os.path.join(out_dir, f"env_{mode}.json"), "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)
    for n, (k, i) in enumerate(jobs, 1):
        if (k, i) in done:
            continue
        c = conds[k]
        g = q.generate(c["prompt"])
        rec = dict(run_id=os.path.basename(out_dir.rstrip("/")), mode=mode, trial_id=f"{k}-{i}", condition=k,
                   condition_type=c["condition_type"], target_positions=c["positions"], replicate=i, order_index=n,
                   prompt_text=c["prompt"], prompt_sha256=c["prompt_sha256"], model_id=model_id,
                   model_commit=env["model_commit"], served_provider="local-transformers", reasoning_mode="enable_thinking=False",
                   temperature="greedy", cost_usd=0.0, timestamp=dt.datetime.now(dt.timezone.utc).isoformat(), **g)
        with open(raw_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{n}/{len(jobs)}] {k}-{i}: {g['raw_choice_content']!r} ({g['finish_reason']}, {g['latency_ms']} ms)", flush=True)

    # matched-prefix scoring on the modal outputs (G, F; plus N in the control)
    rows = [json.loads(l) for l in open(raw_path, encoding="utf-8")]
    modal = {}
    for k in refs:
        c = collections.Counter(r["raw_choice_content"] for r in rows if r["condition"] == k)
        modal[k] = c.most_common(1)[0][0]
    mp = []
    for x in refs:
        for h in refs:
            for method in ("incremental", "full_pass"):
                for s in q.score_prefix(conds[x]["prompt"], modal[h], method):
                    mp.append(dict(instruction=x, history=h, history_sequence=modal[h], **s))
    with open(os.path.join(out_dir, "matched_prefix.jsonl"), "w", encoding="utf-8") as f:
        for r in mp:
            f.write(json.dumps(r) + "\n")
    print(json.dumps(dict(modal=modal, n_records=len(rows), n_matched_prefix=len(mp))), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preflight", "main", "control_preflight", "control_main"])
    ap.add_argument("--model", default="Qwen/Qwen3-32B")
    ap.add_argument("--revision", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--replicates", type=int, default=10)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--confirm-preflight-id", default=None)
    a = ap.parse_args()
    if a.mode in ("main", "control_main") and not (a.execute and a.confirm_preflight_id):
        raise SystemExit("main collection needs --execute and --confirm-preflight-id <passed preflight run id>")
    run(a.mode, a.model, a.out, a.replicates, a.revision)
