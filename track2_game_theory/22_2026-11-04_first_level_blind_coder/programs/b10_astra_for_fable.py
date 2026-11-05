import math


def predict(history, seat):
    """Heuristic probability estimate; no model-specific calibration data."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if not n:
        return 0.60 if seat == "p1" else 0.45

    other = "p2" if seat == "p1" else "p1"
    own = [int(row[seat] == "STAR") for row in history]
    opp = [int(row[other] == "STAR") for row in history]

    def estimate(kind, t):
        if t == 0:
            return 0.5

        if kind == "frequency":
            return (sum(opp[:t]) + 2.0) / (t + 4.0)

        if kind == "recent":
            weights = [0.78 ** (t - 1 - i) for i in range(t)]
            return (
                1.5 + sum(w * opp[i] for i, w in enumerate(weights))
            ) / (3.0 + sum(weights))

        if kind == "repeat":
            return 0.85 if opp[t - 1] else 0.15

        if kind == "alternate":
            return 0.15 if opp[t - 1] else 0.85

        if kind == "copy":
            return 0.85 if own[t - 1] else 0.15

        if kind == "invert":
            return 0.15 if own[t - 1] else 0.85

        if kind == "transition":
            indices = [
                i for i in range(1, t)
                if opp[i - 1] == opp[t - 1]
            ]
        elif kind == "context":
            if t < 2:
                return 0.5
            indices = [
                i for i in range(2, t)
                if opp[i - 2:i] == opp[t - 2:t]
            ]
        else:
            # Conditional response to the previous pair of choices.
            indices = [
                i for i in range(1, t)
                if (own[i - 1], opp[i - 1])
                == (own[t - 1], opp[t - 1])
            ]

        weights = [0.94 ** (t - 1 - i) for i in indices]
        return (
            1.25 + sum(w * opp[i] for w, i in zip(weights, indices))
        ) / (2.5 + sum(weights))

    experts = [
        ("frequency", 2.0),
        ("recent", 2.0),
        ("repeat", 0.6),
        ("alternate", 0.8),
        ("copy", 0.4),
        ("invert", 0.4),
        ("transition", 1.5),
        ("context", 0.8),
        ("response", 0.8),
    ]

    forecasts = []
    for kind, prior in experts:
        score = math.log(prior)
        for t in range(1, n):
            p = estimate(kind, t)
            likelihood = p if opp[t] else 1.0 - p
            score += 0.90 ** (n - 1 - t) * math.log(likelihood)
        forecasts.append((score, estimate(kind, n)))

    top = max(score for score, _ in forecasts)
    weights = [math.exp(0.85 * (score - top))
               for score, _ in forecasts]
    opponent_star = sum(
        w * p for w, (_, p) in zip(weights, forecasts)
    ) / sum(weights)

    target_star = opponent_star if seat == "p1" else 1.0 - opponent_star

    # Allow substantial mass for deliberate mixing and unmodeled reasoning.
    probability = 0.5 + 0.70 * (target_star - 0.5)
    probability += 0.025 * math.exp(-n / 5.0)

    return max(0.12, min(0.88, probability))
