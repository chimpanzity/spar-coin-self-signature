# Blind Twin: overnight matching-pennies pilot

Does truthfully identifying a player as another instance of the observing model selectively improve the observer's predictions of that player's next move, compared with a false identity or no identity? This measures the functional value of identity information, not introspection.

- Players: Astra and Fable, four ordered matchups x 3 games x 20 rounds; fresh request per round with the full public history; neither player is told the opponent's identity.
- Judges: separate Astra and Fable instances predict both players' next choices at every round under TRUE / FALSE / ANONYMOUS identity lines on the identical frozen game log.
- Primary index S (truth vs anonymous, self-specific); key companion S_false (truth vs false).

Run:

```
python -m blind_twin fake  --run <id>          # offline end-to-end
python -m blind_twin smoke --run <id> --live   # 4 technical calls, stored in smoke_calls.jsonl
python -m blind_twin run   --run <id> --live   # games -> freeze -> judges -> analysis (resumable)
python -m blind_twin analyze --run <id>
```

Files: `config.py` (frozen prompts, design, budget), `render.py` (public-history renderers), `parse.py` (strict parsers), `runner.py` (games, freeze, judging; reuses the SPAR Phase 2 transport and budget guard), `score.py` (scoring, baselines, bootstrap, report), `templates/` (exact prompt text), `protocol.md`. Tests: `tests/test_blind_twin.py`. Outputs: `results/<run_id>/`.
