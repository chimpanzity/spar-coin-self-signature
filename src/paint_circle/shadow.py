"""Shadow Proteus: Lee et al. (2004) Algorithm 2 on a rolling W-trial window.

Wraps the PACA implementation (paca_believed_self/task/protean_committed.py,
byte-identical to dodging-proteus/task/protean_committed.py) without changing
its channel logic. The only modification is the window: at trial t the nine
channels see only trials t-W..t-1 (W=None means the full history, as in PACA).

The outcome bit fed to the choice+outcome channels is "the focal player won
this round" (for Player A: paint == circle; for Player B: paint != circle).
In PACA the subject was always the matcher, so the bit meant "matched".

Forecast convention: with a significant channel, the forecast probability of
the predicted choice is that channel's estimated bias (bsideprob / 100); with
no significant channel the forecast is 0.5 / 0.5.
"""

from __future__ import annotations

import functools
import importlib.util
import math
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

_PATH = str(repo_paths.legacy("paca_believed_self/task/protean_committed.py"))
_spec = importlib.util.spec_from_file_location("protean_committed", os.path.abspath(_PATH))
protean = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protean)

# Same function, memoized (as in dodging-proteus/code/verify_calibration.py).
protean.two_tailed_binomial_p = functools.lru_cache(maxsize=None)(protean.two_tailed_binomial_p)


@dataclass(frozen=True)
class Forecast:
    p_triangle: float          # forecast P(next choice == "T")
    active: bool               # any channel significant
    n_active: int
    channel: Optional[int]     # index of the strongest significant channel


def forecast(choices: str, wins: str, window: Optional[int]) -> Forecast:
    """Forecast the next choice from completed rounds only.

    choices: "T"/"S" per completed round; wins: "1"/"0" per completed round
    (focal player won). Both cover rounds 1..t-1.
    """
    assert len(choices) == len(wins)
    if window is not None:
        choices, wins = choices[-window:], wins[-window:]
    cr = "".join(c + w for c, w in zip(choices, wins))
    results = protean.compute_all_channels(choices, cr)
    best = protean.best_prediction(results)
    n_active = sum(r.sig for r in results)
    if best is None:
        return Forecast(0.5, False, n_active, None)
    p = best.bsideprob / 100.0
    return Forecast(p if best.bside == "Triangle" else 1.0 - p, True, n_active, best.n)


@dataclass(frozen=True)
class Predictability:
    p_shadow: float            # mean forecast probability of the actual choice
    pi: float                  # 2 * (p_shadow - 0.5)
    activation: float          # fraction of scored rounds with an active channel
    logloss: float             # mean -log2 forecast prob of actual choice
    logloss_marginal: float    # same for a rolling-window Laplace marginal baseline
    n_scored: int


def _clip(p: float) -> float:
    return min(max(p, 1e-3), 1 - 1e-3)


def predictability(choices: str, wins: str, window: Optional[int], start: int = 1) -> Predictability:
    """Prequential shadow forecasts of a completed sequence (0-based round index >= start)."""
    probs, active, ll, llm = [], [], [], []
    for t in range(start, len(choices)):
        f = forecast(choices[:t], wins[:t], window)
        actual = choices[t]
        p = f.p_triangle if actual == "T" else 1 - f.p_triangle
        probs.append(p)
        active.append(f.active)
        ll.append(-math.log2(_clip(p)))
        past = choices[:t] if window is None else choices[max(0, t - window):t]
        pm = (past.count(actual) + 1) / (len(past) + 2)
        llm.append(-math.log2(pm))
    n = len(probs)
    ps = sum(probs) / n
    return Predictability(ps, 2 * (ps - 0.5), sum(active) / n, sum(ll) / n, sum(llm) / n, n)


def forecasts_for(choices: str, wins: str, window: Optional[int]) -> List[Forecast]:
    """Forecast for every round t (round 0 gets the no-history forecast)."""
    return [forecast(choices[:t], wins[:t], window) for t in range(len(choices))]


def recommended_win_prob(opp_choices: str, opp_wins: str, window: Optional[int]) -> List[float]:
    """Information-matched shadow benchmark (handoff §7.3).

    For each round, the probability that a Proteus-style recommendation built
    from the opponent's past choices/outcomes beats the opponent's actual
    choice. A (matcher) plays the predicted opponent shape with prob = bias;
    B (mismatcher) plays the opposite of the predicted shape with prob = bias.
    Both reduce to the forecast probability of the opponent's actual choice.
    """
    out = []
    for t, f in enumerate(forecasts_for(opp_choices, opp_wins, window)):
        actual = opp_choices[t]
        out.append(f.p_triangle if actual == "T" else 1 - f.p_triangle)
    return out


def wins_string(own: Sequence[str], other: Sequence[str], matcher: bool) -> str:
    return "".join(("1" if (a == b) == matcher else "0") for a, b in zip(own, other))
