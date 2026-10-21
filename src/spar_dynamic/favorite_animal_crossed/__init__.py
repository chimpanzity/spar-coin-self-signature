"""FAVORITE_ANIMAL_CROSSED_v1.0 — Crossed-prediction control for the
favorite-animal pilot.

Each of three models predicts the four queried letters of each OTHER
model's canonical favorite animal (as determined in the prior
favorite_animal pilot: astra=octopus, fable=octopus, oss120=elephant).

Six predictor × non-self-target pairs × 4 positions × 5 reps = 120 calls.

The critical disambiguating cell is **Fable → OSS-120 (elephant)**:
- If Fable predicts elephant's letters accurately, Fable's prior
  single-letter success was semantic reasoning, not introspection.
- If Fable fails on elephant but succeeded on octopus, there is something
  self-specific about retrieving its own canonical response.
"""

SPECIFICATION_VERSION = "FAVORITE_ANIMAL_CROSSED_v1.0"
EXPERIMENT_NAME = "favorite_animal_crossed"
