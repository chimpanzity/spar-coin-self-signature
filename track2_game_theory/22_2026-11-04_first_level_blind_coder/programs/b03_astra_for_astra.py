import math


def predict(history, seat):
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    if not history:
        return 0.58 if seat == "p1" else 0.46

    other = "p2" if seat == "p1" else "p1"
    opponent = [int(row[other] == "STAR") for row in history]
    own = [int(row[seat] == "STAR") for row in history]
    n = len(history)

    def forecasts(t):
        if t == 0:
            return [0.5] * 7

        xs = opponent[:t]
        frequency = (sum(xs) + 2.0) / (t + 4.0)

        total = 0.0
        stars = 0.0
        for i, x in enumerate(xs):
            weight = 0.82 ** (t - 1 - i)
            total += weight
            stars += weight * x
        recent = (stars + 1.5) / (total + 3.0)

        last = xs[-1]
        transitions = [
            xs[i] for i in range(1, t) if xs[i - 1] == last
        ]
        conditional = (sum(transitions) + 1.5) / (
            len(transitions) + 3.0
        )

        # The opponent may respond to this player's preceding move.
        response = own[t - 1] if other == "p1" else 1 - own[t - 1]
        return [
            0.5,
            frequency,
            recent,
            conditional,
            0.2 + 0.6 * last,
            0.8 - 0.6 * last,
            0.2 + 0.6 * response,
        ]

    weights = [3.0, 1.5, 1.0, 1.0, 0.6, 0.6, 0.5]
    for t in range(n):
        observed = opponent[t]
        for j, p in enumerate(forecasts(t)):
            likelihood = p if observed else 1.0 - p
            weights[j] *= likelihood ** 0.65
        normalizer = sum(weights)
        weights = [w / normalizer for w in weights]

    opponent_star = sum(
        w * p for w, p in zip(weights, forecasts(n))
    ) / sum(weights)

    advantage = 2.0 * opponent_star - 1.0
    if seat == "p2":
        advantage = -advantage

    opening_bias = (0.04 if seat == "p1" else -0.02) * math.exp(-n / 4.0)
    return 0.5 + 0.24 * math.tanh(2.5 * advantage) + opening_bias
