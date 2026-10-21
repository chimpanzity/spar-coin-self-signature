# APPROVAL: PACA believed-self generator pilot

Experiment `paca_believed_self_pilot_v1`. 3 models x 4 conditions x 1 session x 200 trials = 2,400 model calls (plus re-requests of failed trials). Hard cap $60.

## Cost estimate (pinned endpoints; usage from earlier PACA minimalist runs on this harness; Qwen assumed)

| model | slug (provider) | calls | tokens in / out mean / out p95 | expected | pessimistic |
|---|---|---:|---|---:|---:|
| fable | anthropic/claude-fable-5.1 (anthropic) | 800 | 358 / 347 / 818 | $16.74 | $35.58 |
| astra | openai/gpt-6-astra (openai) | 800 | 205 / 62 / 148 | $4.12 | $7.56 |
| qwen | qwen/qwen3.8-27b (alibaba) | 800 | 300 / 1200 / 4000 | $2.55 | $8.26 |

Expected $23.41; pessimistic $51.41; preflight about $0.60.

## Exact system prompts

Believed self:

```
Another instance of your model is generating the sequence of blue circle landings.

Choose the shape that the blue circle will land on.

Available actions:
  TRIANGLE
  STAR

You may briefly think through your choice. End your response with the chosen action on its own line.
```

Believed other:

```
An instance of a different language model is generating the sequence of blue circle landings.

Choose the shape that the blue circle will land on.

Available actions:
  TRIANGLE
  STAR

You may briefly think through your choice. End your response with the chosen action on its own line.
```

## Example user prompt (trial 28)

```
Previous rounds (oldest → most recent):
  You chose TRIANGLE - blue circle landed on STAR
  You chose TRIANGLE - blue circle landed on TRIANGLE
  You chose STAR - blue circle landed on STAR
  You chose TRIANGLE - blue circle landed on STAR
  You chose TRIANGLE - blue circle landed on TRIANGLE  (most recent)

(grid reads left to right, oldest → most recent)
Your last 25 choices:   S T T S T T S S T S T T T S S T S T S S T T S T T
Blue circle landed on:  S T T T S S T S T T S S T S T T S S T T S T S S T

Your action:
```

## Status

LIVE RUN APPROVED BY CHRIS: yes
Approved by Chris in chat 2026-10-11 ("excellent, lets proceed") after reviewing the exact prompts (belief sentence revised to "...generating the sequence of blue circle landings."), the $23 expected / $51 pessimistic estimate and the $60 hard cap.

## Decision 2026-10-11: Qwen dropped

Preflight showed Qwen3.8-27B, at PACA's default reasoning, spending 28,000-31,000 output tokens (about $0.075 and ~10
minutes) per forecast once history is present. That projects to roughly $60 and ~30 hours per sequential 200-trial
session set, which is infeasible within the cap. Chris decided ("lets not do qwen then") not to run Qwen rather than
change its reasoning setting. The pilot is therefore Fable and Astra only: 8 sessions, 1,600 calls. Qwen preflight calls
($0.15) remain in preflight_calls.jsonl.
