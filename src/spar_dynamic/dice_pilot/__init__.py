"""SPAR Dice-Rolling Hypothetical Self-Prediction Pilot — v3.1.

Two-phase paradigm: Phase 1 establishes a model's object-level 10-die-roll
sequence; Phase 2 asks the same model in a fresh stateless context to
predict a specific position of that sequence without emitting the preceding
rolls. Reasoning-on vs reasoning-off is the critical control. See the
spec at `data/spar_dynamic/dice_pilot/SPEC_v3.1.md` (copied from the
2026-10-15 handoff).
"""

SPECIFICATION_VERSION = "DICE_PILOT_v3.1"
EXPERIMENT_NAME = "dice_pilot"
