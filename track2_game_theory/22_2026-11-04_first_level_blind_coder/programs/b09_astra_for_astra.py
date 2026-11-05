import math


def predict(history, seat):
    """Heuristic estimate; no model-specific behavioral data is assumed."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if n == 0:
        return 0.58 if seat == "p1" else 0.47

    other = "p2" if seat == "p1" else "p1"
    opponent = [int(row[other] == "STAR") for row in history]
    own = [int(row[seat] == "STAR") for row in history]

    def forecasts(t):
        if t == 0:
            return [0.5] * 7

        past = opponent[:t]
        frequency = (sum(past) + 2.0) / (t + 4.0)

        weights = [0.78 ** (t - 1 - i) for i in range(t)]
        recent = (
            1.5 + sum(w * x for w, x in zip(weights, past))
        ) / (3.0 + sum(weights))

        last = past[-1]
        repeat = 0.15 + 0.70 * last
        alternate = 1.0 - repeat

        following = [
            past[i] for i in range(1, t) if past[i - 1] == last
        ]
        conditional = (sum(following) + 1.5) / (len(following) + 3.0)

        copy = 0.20 + 0.60 * own[t - 1]
        oppose = 1.0 - copy
        return [
            frequency, recent, repeat, alternate,
            conditional, copy, oppose,
        ]

    # Estimate which elementary opponent patterns the player might notice.
    losses = [0.0] * 7
    for t in range(1, n):
        guesses = forecasts(t)
        for j, guess in enumerate(guesses):
            losses[j] = (
                0.88 * losses[j] + (guess - opponent[t]) ** 2
            )

    priors = [2.0, 2.0, 0.8, 0.8, 1.4, 0.5, 0.5]
    weights = [
        prior * math.exp(-2.5 * loss)
        for prior, loss in zip(priors, losses)
    ]
    guesses = forecasts(n)
    expected_star = sum(
        weight * guess for weight, guess in zip(weights, guesses)
    ) / sum(weights)

    # Blend pattern-aware play with deliberate randomization and uncertainty
    # about the player's actual strategy.
    advantage = 2.0 * expected_star - 1.0
    if seat == "p2":
        advantage = -advantage
    response = math.tanh(2.0 * advantage)
    probability = 0.5 + 0.27 * response

    # Small residual preference for the first-listed action.
    probability += 0.025 * math.exp(-n / 6.0)
    return max(0.05, min(0.95, probability))
