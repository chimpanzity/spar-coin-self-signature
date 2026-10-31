"""Model adapters for SPAR_CROSSED_GUIDED_SELFPRED_v1.0 (runs on the rented GPU).

Both models share one engine with Experiment 21's arithmetic: bf16 weights, a separate fp32 copy of the output layer
(logits fp32), batch 1, the prompt prefilled once and every further token fed one at a time through the KV cache, exact
full-vocabulary log-softmax at every step. Deterministic flags as in Experiment 21.

  Qwen     loaded by Experiment 21's `Qwen` class, unchanged (Qwen3 chat template, enable_thinking=False).
  Mistral  the transformers conditional-generation class for Mistral 3 (text path only: input_ids, no pixel_values) at the pinned revision;
           prompts tokenised by mistral_common's tekken v11 instruct tokenizer from the same revision
           (<s>[INST]prompt[/INST], one user message, no system prompt), the path the model card documents.

The engine stores, at every step, the log-probabilities of the six bare face tokens (digits and spaces are separate
tokens in both tokenizers; checked at load), their raw mass, the chosen token and its raw (T=1) log-probability.
Sampling draws from softmax(logits / T) with a per-call seeded CUDA generator (top_p = 1, no top_k).
"""

from __future__ import annotations

import hashlib
import os
import platform
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch  # noqa: E402

from spar_dynamic.dice_crossed_guidance import config as C  # noqa: E402

LN2 = 0.6931471805599453


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _determinism():
    torch.manual_seed(0)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.use_deterministic_algorithms(True, warn_only=True)


def fp32_head(model):
    """Experiment 21's output layer: a separate fp32 copy of lm_head with an input cast."""
    w = model.lm_head.weight.detach().float().clone()
    head = torch.nn.Linear(w.shape[1], w.shape[0], bias=False, device=w.device, dtype=torch.float32)
    head.weight.data = w
    head.register_forward_pre_hook(lambda mod, args: (args[0].float(),))
    model.lm_head = head


def _driver() -> str:
    try:
        import subprocess
        return subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True).strip()
    except Exception:
        return "unknown"


class Engine:
    key: str
    model = None
    eos: set
    face_ids: dict
    device = "cuda"

    # tokenizer-specific
    def prompt_ids(self, prompt: str) -> list:
        raise NotImplementedError

    def hist_ids(self, text: str) -> list:
        raise NotImplementedError

    def decode(self, ids: list) -> str:
        raise NotImplementedError

    def rendered_text(self, prompt: str) -> str:
        raise NotImplementedError

    # shared arithmetic
    def _fwd(self, ids, past=None):
        return self.model(input_ids=torch.tensor([ids], device=self.device), past_key_values=past, use_cache=True)

    def _faces(self, lp: torch.Tensor) -> dict:
        return {str(f): lp[i].item() for f, i in self.face_ids.items()}

    @torch.no_grad()
    def generate(self, prompt: str, temperature: float | None = None, seed: int | None = None) -> dict:
        """Greedy (temperature None) or sampled generation; every step's exact face log-probabilities."""
        ids = self.prompt_ids(prompt)
        gen_rng = None
        if temperature is not None:
            gen_rng = torch.Generator(device=self.device)
            gen_rng.manual_seed(int(seed))
        t0 = time.time()
        out = self._fwd(ids)
        steps, gen, finish = [], [], "length"
        for _ in range(C.MAX_NEW_TOKENS):
            logits = out.logits[0, -1].float()
            lp = torch.log_softmax(logits, dim=-1)
            if temperature is None:
                nxt = int(torch.argmax(lp).item())
                lp_t = None
            else:
                lpt = torch.log_softmax(logits / temperature, dim=-1)
                nxt = int(torch.multinomial(lpt.exp(), 1, generator=gen_rng).item())
                lp_t = lpt[nxt].item()
            top = torch.topk(lp, 5)
            step = dict(token=self.decode([nxt]), token_id=nxt, logprob=lp[nxt].item(), logprob_tempered=lp_t,
                        face_logprobs=self._faces(lp), top5=[[int(i), float(v)] for v, i in zip(top.values.tolist(), top.indices.tolist())],
                        entropy_bits=float(-(lp.exp() * lp).sum().item() / LN2))
            steps.append(step)
            if nxt in self.eos:
                finish = "stop"
                break
            gen.append(nxt)
            out = self._fwd([nxt], out.past_key_values)
        content = self.decode(gen)
        return dict(prompt_tokens=len(ids), rendered_prompt_sha256=sha(self.rendered_text(prompt)), completion_tokens=len(gen),
                    generated_ids=gen, content=content, finish_reason=finish, steps=steps,
                    digit_steps=[s for s in steps if s["token_id"] in self.face_ids.values()],
                    temperature=temperature, seed=seed, latency_ms=int(1000 * (time.time() - t0)))

    @torch.no_grad()
    def score(self, prompt: str, history: str, method: str = "incremental") -> list:
        """Six-face log-probabilities before every face token of `history`, teacher-forced as the assistant turn.

        incremental: prompt prefilled once, then one token at a time through the KV cache (generation arithmetic; primary).
        full_pass:   one forward pass over prompt + history (numerical floor only).
        """
        pre = self.prompt_ids(prompt)
        hist = self.hist_ids(history)
        if method == "incremental":
            rows = []
            out = self._fwd(pre)
            for t in hist:
                rows.append(torch.log_softmax(out.logits[0, -1].float(), dim=-1))
                out = self._fwd([t], out.past_key_values)
        else:
            lp = torch.log_softmax(self.model(input_ids=torch.tensor([pre + hist], device=self.device)).logits[0].float(), dim=-1)
            rows = [lp[len(pre) + j - 1] for j in range(len(hist))]
        inv = {v: k for k, v in self.face_ids.items()}
        res, k = [], 0
        for t, row in zip(hist, rows):
            if t in inv:
                k += 1
                res.append(dict(method=method, position=k, history_face=inv[t], face_logprobs=self._faces(row),
                                argmax_token_id=int(row.argmax()), argmax_logprob=row.max().item()))
        return res

    def env_common(self) -> dict:
        import transformers
        p = torch.cuda.get_device_properties(0)
        return dict(key=self.key, model_id=self.model_id, model_commit=self.commit,
                    dtype="bfloat16 weights and activations; lm_head and logits fp32", gpu=p.name,
                    gpu_mem_gb=round(p.total_memory / 2**30, 1), cuda=torch.version.cuda, torch=torch.__version__,
                    transformers=transformers.__version__, python=platform.python_version(), driver=_driver(),
                    eos_ids=sorted(self.eos), face_ids=self.face_ids,
                    max_memory_allocated_gb=round(torch.cuda.max_memory_allocated() / 2**30, 2),
                    deterministic=dict(cudnn_deterministic=True, tf32=False, use_deterministic_algorithms="warn_only",
                                       CUBLAS_WORKSPACE_CONFIG=os.environ.get("CUBLAS_WORKSPACE_CONFIG")))


class QwenEngine(Engine):
    key = "qwen"

    def __init__(self, model_id=None, revision=None):
        from spar_dynamic.dice_logprob.gpu_runner import Qwen
        spec = C.MODEL["qwen"]
        self.model_id = model_id or spec["model_id"]
        self.q = Qwen(self.model_id, revision if revision is not None else spec["revision"])   # Experiment 21, unchanged
        self.model, self.tok, self.commit, self.eos = self.q.model, self.q.tok, self.q.commit, self.q.eos
        self.face_ids = dict(self.q.face_bare)

    def rendered_text(self, prompt):
        return self.q.render(prompt)

    def prompt_ids(self, prompt):
        return self.tok(self.q.render(prompt), add_special_tokens=False).input_ids

    def hist_ids(self, text):
        return self.tok(text, add_special_tokens=False).input_ids

    def decode(self, ids):
        return self.tok.decode(ids)

    def env(self):
        return dict(self.env_common(), chat_template_sha256=sha(self.tok.chat_template or ""), serving="Experiment 21 Qwen class")


class MistralEngine(Engine):
    key = "mistral"

    def __init__(self, model_id=None, revision=None, model=None, tekken_path=None, device="cuda"):
        from huggingface_hub import hf_hub_download
        from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
        spec = C.MODEL["mistral"]
        self.model_id = model_id or spec["model_id"]
        rev = revision if revision is not None else spec["revision"]
        self.device = device
        _determinism()
        tekken_path = tekken_path or hf_hub_download(self.model_id, "tekken.json", revision=rev)
        self.tekken_sha256 = hashlib.sha256(open(tekken_path, "rb").read()).hexdigest()
        self.mt = MistralTokenizer.from_file(tekken_path)
        self.t = self.mt.instruct_tokenizer.tokenizer
        if model is None:
            from transformers import Mistral3ForConditionalGeneration
            model = Mistral3ForConditionalGeneration.from_pretrained(self.model_id, revision=rev, dtype=torch.bfloat16,
                                                                     device_map=device, attn_implementation="sdpa")
            self.commit = os.path.basename(os.path.dirname(hf_hub_download(self.model_id, "config.json", revision=rev)))
        else:
            self.commit = "injected-test-model"
        model.eval()
        fp32_head(model)
        self.model = model
        self.eos = {self.t.eos_id}
        self.face_ids = {}
        for f in C.FACES:
            ids = self.t.encode(str(f), bos=False, eos=False)
            assert len(ids) == 1, f"face {f} is not one tekken token"
            self.face_ids[f] = ids[0]

    def _request(self, prompt):
        from mistral_common.protocol.instruct.messages import UserMessage
        from mistral_common.protocol.instruct.request import ChatCompletionRequest
        return self.mt.encode_chat_completion(ChatCompletionRequest(messages=[UserMessage(content=prompt)]))

    def rendered_text(self, prompt):
        return self._request(prompt).text

    def prompt_ids(self, prompt):
        return list(self._request(prompt).tokens)

    def hist_ids(self, text):
        return self.t.encode(text, bos=False, eos=False)

    def decode(self, ids):
        return self.t.decode(ids)

    def env(self):
        import mistral_common
        return dict(self.env_common(), mistral_common=mistral_common.__version__, tekken_sha256=self.tekken_sha256,
                    tokenizer_version=str(self.t.version), bos_id=self.t.bos_id, serving="transformers Mistral3ForConditionalGeneration, text-only input_ids")


def load(key: str, **kw) -> Engine:
    return {"qwen": QwenEngine, "mistral": MistralEngine}[key](**kw)
