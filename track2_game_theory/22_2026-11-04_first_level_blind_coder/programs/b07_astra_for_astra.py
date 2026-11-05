import math


def predict(history, seat):
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    if not history:
        return 0.56 if seat == "p1" else 0.46

    own_key = seat
    opp_key = "p2" if seat == "p1" else "p1"
    own = [1.0 if r[own_key] == "STAR" else 0.0 for r in history]
    opp = [1.0 if r[opp_key] == "STAR" else 0.0 for r in history]
    n = len(opp)

    def forecasts(t):
        if t == 0:
            return [0.5] * 9

        past = opp[:t]
        frequency = (sum(past) + 2.0) / (t + 4.0)

        total = 0.0
        mass = 0.0
        for i, x in enumerate(past):
            w = 0.8 ** (t - 1 - i)
            total += w * x
            mass += w
        recent = (total + 1.5) / (mass + 3.0)

        last = past[-1]
        following = [
            past[i] for i in range(1, t) if past[i - 1] == last
        ]
        transition = (sum(following) + 1.5) / (len(following) + 3.0)

        return [
            0.5,
            0.85,
            0.15,
            frequency,
            recent,
            0.15 + 0.70 * last,
            0.85 - 0.70 * last,
            transition,
            0.15 + 0.70 * (
                own[t - 1] if opp_key == "p1" else 1.0 - own[t - 1]
            ),
        ]

    weights = [2.5, 0.5, 0.5, 1.5, 1.0, 0.8, 0.8, 1.2, 0.6]
    losses = [0.0] * len(weights)

    for t, actual in enumerate(opp):
        estimates = forecasts(t)
        for j, estimate in enumerate(estimates):
            losses[j] = 0.94 * losses[j] + (estimate - actual) ** 2

    estimates = forecasts(n)
    posterior = [
        prior * math.exp(-2.5 * loss)
        for prior, loss in zip(weights, losses)
    ]
    opponent_star = sum(
        w * p for w, p in zip(posterior, estimates)
    ) / sum(posterior)

    direction = 1.0 if seat == "p1" else -1.0
    strategic_signal = direction * (opponent_star - 0.5)
    probability = 0.5 + 0.34 * math.tanh(4.0 * strategic_signal)

    # Small, rapidly decaying prior for the first-listed action.
    probability += 0.025 * math.exp(-n / 4.0)

    return max(0.05, min(0.95, probability))
