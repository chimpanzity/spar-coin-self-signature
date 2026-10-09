# Opponent self-identity disclosure (OpponentDisclosure_v1)

Implements "SPAR Blind Twin Follow-Up: Opponent Self-Identity Disclosure in Repeated Matching Pennies"
(pasted by Chris, 2026-10-09). Sections 1-4 and the visible part of Section 5 are implemented verbatim:
Astra vs Astra; Player 1 always Matcher, Player 2 always Mismatcher; 2x2 disclosure (00, 10, 01, 11);
8 games per condition x 20 rounds (1,280 player calls); exact prompts, identity sentences, history
format and empty-history text; fresh context per request; both players see the same completed history.

**The handoff text ended mid-sentence in the parsing section.** The following are Claude's prespecified
defaults, fixed in code before any data:

- **Model/decoding:** `openai/gpt-6-astra` via OpenAI, pinned, fallbacks off; temperature, top_p and seed
  omitted (temperature unsupported); reasoning effort=low, exclude=true; max_tokens 4000 (as in all
  Blind Twin runs). No system message.
- **Parser (od_v1_final_line_exact):** the final non-empty line, after trimming whitespace and ignoring
  case, must be exactly STAR or TRIANGLE (so `**STAR**` or `STAR.` are invalid). Earlier lines are free
  text and are never searched for a choice.
- **Invalid answers:** a completed answer that fails the parser makes the round invalid and the game is
  marked incomplete at that round; no resampling or repair. Transport errors (429/5xx/timeouts) are retried
  with the same payload at most 3 times.
- **Scheduling:** 32 games; replicate k of all four conditions is scheduled together in a seeded order;
  up to 16 games run concurrently; both seats' requests dispatched from the identical prior history.
- **Primary outcome:** Matcher win rate per game. Factorial contrasts in percentage points:
  informing the Matcher = mean(10,11) - mean(00,01); informing the Mismatcher = mean(01,11) - mean(00,10);
  interaction = (11-01) - (10-00); plus 10 vs 11, 01 vs 11 and 11 vs 00.
- **Secondary outcomes (per player):** %STAR, switch rate, longest run, and predictability by five
  history-only rules (frequency, repeat last, alternate last, win-stay/lose-shift, one-step Markov; round 1
  and ties = half credit) and their per-game maximum. Reported with own-informed and opponent-informed
  factorial effects.
- **Uncertainty:** 5,000 bootstrap resamples of games within each condition; percentile 95% intervals;
  exploratory, no multiplicity correction.
- **Manipulation check (descriptive):** share of responses mentioning a prespecified list of terms
  (same model, instance, Astra, myself, mirror, ...), and share with reasoning lines, by role x informed.
- **Budget:** hard ceiling $25 enforced per call; a 2-game technical smoke test (conditions 00 and 11) is
  logged separately and excluded from the data.
