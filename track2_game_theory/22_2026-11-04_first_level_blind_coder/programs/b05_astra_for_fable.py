import math


def predict(history, seat):
    """Heuristic forecast; no model-specific calibration data is available."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if not n:
        return 0.62 if seat == "p1" else 0.42

    other = "p2" if seat == "p1" else "p1"
    own = [int(row[seat] == "STAR") for row in history]
    opp = [int(row[other] == "STAR") for row in history]

    def forecasts(t):
        if t == 0:
            return [0.5] * 8

        xs = opp[:t]
        last = xs[-1]
        frequency = (sum(xs) + 2.0) / (t + 4.0)

        weights = [0.8 ** (t - 1 - i) for i in range(t)]
        recent = (sum(w * x for w, x in zip(weights, xs)) + 1.5)
        recent /= sum(weights) + 3.0

        successors = [xs[i] for i in range(1, t) if xs[i - 1] == last]
        markov = (sum(successors) + 1.5) / (len(successors) + 3.0)

        opponent_won = (
            (opp[t - 1] == own[t - 1]) if other == "p1"
            else (opp[t - 1] != own[t - 1])
        )
        win_stay = last if opponent_won else 1 - last

        # An opponent responding to our previous move.
        counter = own[t - 1] if other == "p1" else 1 - own[t - 1]
        return [
            0.5,
            frequency,
            recent,
            0.15 + 0.70 * last,
            0.15 + 0.70 * (1 - last),
            markov,
            0.15 + 0.70 * win_stay,
            0.15 + 0.70 * counter,
        ]

    priors = [2.5, 2.0, 1.5, 1.0, 1.0, 1.5, 0.7, 0.7]
    losses = [0.0] * len(priors)
    for t in range(1, n):
        predictions = forecasts(t)
        for j, p in enumerate(predictions):
            losses[j] = 0.92 * losses[j] + (p - opp[t]) ** 2

    weights = [
        prior * math.exp(-3.0 * loss)
        for prior, loss in zip(priors, losses)
    ]
    current = forecasts(n)
    expected_opponent = sum(w * p for w, p in zip(weights, current))
    expected_opponent /= sum(weights)

    desired = expected_opponent if seat == "p1" else 1.0 - expected_opponent
    strategic = 0.5 + 0.38 * math.tanh(4.0 * (desired - 0.5))

    # Weak inertia and an opening-symbol preference reflect plausible
    # nonrandom behavior without treating the heuristic as certain.
    won = (
        own[-1] == opp[-1] if seat == "p1"
        else own[-1] != opp[-1]
    )
    stay_or_switch = own[-1] if won else 1 - own[-1]
    opening_bias = (0.025 if seat == "p1" else -0.015) * math.exp(-n / 5.0)
    probability = (
        0.90 * strategic
        + 0.06 * (0.35 + 0.30 * stay_or_switch)
        + 0.04 * (0.35 + 0.30 * own[-1])
        + opening_bias
    )
    return max(0.12, min(0.88, probability))
