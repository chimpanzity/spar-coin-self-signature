# Stage 1 approval record

All decisions were given by Chris Martin in chat on 2026-10-07, before any Phase 2
data existed. Machine-readable copy: `approvals.jsonl`.

| item | decision |
|---|---|
| Deployment | All four models via OpenRouter; no local runtime |
| Core models / pinned providers | `openai/gpt-6-astra` (OpenAI), `anthropic/claude-fable-5.1` (Anthropic), `qwen/qwen3-8b` (Alibaba) |
| Historical source | `openai/gpt-3.5-turbo-0613` (Azure) |
| Decoding | Astra/Fable: temperature, top_p and seed omitted (unsupported or omitted by policy); reasoning effort=low, exclude=true. Qwen: generation t=0.7, top_p=0.8, top_k=20, non-thinking; judging t=0, non-thinking. GPT-3.5: system "You are a helpful assistant.", t in {0, 0.8, 1.5}, top_p=1, max_tokens=300 |
| Output budgets | Astra/Fable 4000 tokens (includes hidden reasoning), Qwen 1000, GPT-3.5 300 |
| Prompts | "Flip 20 coins." / "Flip 20 fair coins." (sha256 recorded in config_resolved.json via recipe hashes) |
| Planned executions | 3,186 (see config_resolved.json) |
| Budget | Hard cap $100 for Phase 2 (enforced in code with per-call reservation) |
| Validity below 80% | Keep going; reported, not paused |
| Stage 2 freeze | Pre-approved |
| Headroom review | Option (a) continue, INFERRED from the go-ahead (flagged) |
| Branch | `phase2`, local commits only |

Deviations from the v7.1 handoff known at approval time:
- The open model is hosted (Alibaba via OpenRouter), not a controlled local runtime. Local-probe equivalence is unverified.
- Qwen `min_p=0` is not supported by the endpoint and is omitted.
- The handoff's accompanying `config.json`, prompt files and reference checks were not available on this machine; the implementation follows the handoff text.
- One connectivity call per model (prompt "Reply with the single word OK.") was sent as troubleshooting outside the quota: `_preflight/connectivity_20261007.json`.
