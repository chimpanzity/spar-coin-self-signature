"""
Proteus: the adaptive matching-pennies opponent used in PACA.

On each trial Proteus predicts the subject's upcoming choice from the accumulated
choice history and plays to mismatch it. Nine detection channels run in parallel
over the full session history:
    channel 0     marginal side bias
    channels 1-4  the next choice conditional on the last 1-4 choices
    channels 5-8  the next choice conditional on the last 1-4 choice+outcome pairs
Each channel uses an exact two-tailed binomial test at p < .05. Proteus takes the
strongest significant bias, predicts the subject's next choice, and plays the
opposite side with probability equal to the detected bias strength; if no channel
is significant it plays randomly.

Proteus commits before the subject moves: every channel conditions only on trials
1..t-1. The game is therefore a true simultaneous matching-pennies contest, with a
0.500 win-rate ceiling for an unexploitable (i.i.d. fair-coin) player.

Implements Algorithm 2 of Lee, Conroy, McGreevy, & Barraclough (2004).
"""

import math, random
from dataclasses import dataclass
from typing import Optional


def log_binomial_coeff(n, k):
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)

def binomial_pmf(n, k, p=0.5):
    if k < 0 or k > n:
        return 0.0
    return math.exp(log_binomial_coeff(n, k) + k*math.log(p) + (n-k)*math.log(1-p))

def two_tailed_binomial_p(n, k, p=0.5):
    if n == 0:
        return 1.0
    obs = binomial_pmf(n, k, p)
    return min(sum(binomial_pmf(n, i, p) for i in range(n+1)
                   if binomial_pmf(n, i, p) <= obs + 1e-12), 1.0)


@dataclass
class ChannelResult:
    n: int
    sig: bool
    bside: Optional[str]   # "Triangle" / "Star" = predicted SUBJECT choice
    bsideprob: float       # detected bias strength, percent (50-100)


def _majority_stat(n, nT, nS):
    """Predict the majority follower; two-tailed binomial significance."""
    total = nT + nS
    if total < 1:
        return ChannelResult(n, False, None, 0.0)
    majority = max(nT, nS)
    if two_tailed_binomial_p(total, majority) >= 0.05:
        return ChannelResult(n, False, None, 0.0)
    if nT >= nS:
        return ChannelResult(n, True, "Triangle", nT / total * 100)
    return ChannelResult(n, True, "Star", nS / total * 100)


def detect_channel(channel_n, past_choices, past_cr):
    """
    past_choices : choices for trials 1..t-1 (current choice NOT included).
    past_cr      : choice+reward string for trials 1..t-1.
    Predicts the subject's choice at trial t from history through t-1 only.
    """
    M = len(past_choices)

    if channel_n == 0:  # side bias over completed choices
        if M < 1:
            return ChannelResult(0, False, None, 0.0)
        return _majority_stat(0, past_choices.count("T"), past_choices.count("S"))

    if 1 <= channel_n <= 4:  # choice-history context of length n predicting the next choice
        n = channel_n
        if M < n + 1:
            return ChannelResult(n, False, None, 0.0)
        ctx = past_choices[M - n:]          # the n most recent completed choices
        nT = nS = 0
        for i in range(M - n):
            if past_choices[i:i + n] == ctx:
                nxt = past_choices[i + n]
                if nxt == "T": nT += 1
                elif nxt == "S": nS += 1
        return _majority_stat(n, nT, nS)

    if 5 <= channel_n <= 8:  # choice+reward context predicting the next choice
        k = channel_n - 4
        ctx_len = 2 * k
        L = len(past_cr)
        if M < k + 1 or L < ctx_len + 1:
            return ChannelResult(channel_n, False, None, 0.0)
        ctx = past_cr[L - ctx_len:]
        nT = nS = 0
        for i in range(L - ctx_len):
            if past_cr[i:i + ctx_len] == ctx:
                nxt = past_cr[i + ctx_len]   # the choice char that followed
                if nxt == "T": nT += 1
                elif nxt == "S": nS += 1
        return _majority_stat(channel_n, nT, nS)

    raise ValueError(f"Invalid channel index: {channel_n}")


def compute_all_channels(past_choices, past_cr):
    return [detect_channel(n, past_choices, past_cr) for n in range(9)]


def best_prediction(results):
    best = None
    for r in results:
        if r.sig and (best is None or r.bsideprob > best.bsideprob):
            best = r
    return best


def choose_opponent_move(opponent_type, past_choices, past_cr, rng=None):
    """
    Decide the opponent's move for trial t using only trials 1..t-1
    (past_choices / past_cr), before the subject's trial-t choice is known.
    Returns (cpu_choice, channel_results, winning_channel_or_None, ranval).
    """
    if rng is None:
        rng = random
    results = compute_all_channels(past_choices, past_cr)
    ranval = rng.random()

    if opponent_type == "random":
        return ("T" if ranval < 0.5 else "S"), results, None, ranval

    if opponent_type == "proteus":
        pred = best_prediction(results)
        if pred is None:
            return ("T" if ranval < 0.5 else "S"), results, None, ranval
        predicted = "T" if pred.bside == "Triangle" else "S"
        opposite = "S" if predicted == "T" else "T"
        prob = pred.bsideprob / 100.0
        cpu = opposite if ranval <= prob else predicted
        return cpu, results, pred, ranval

    raise ValueError(f"Unknown opponent_type: {opponent_type!r}")
