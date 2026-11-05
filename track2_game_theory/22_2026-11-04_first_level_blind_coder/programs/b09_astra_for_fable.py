import math


def predict(history, seat):
    """Heuristic probability estimate; does not assume access to model internals."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if n == 0:
        return 0.62 if seat == "p1" else 0.46

    other = "p2" if seat == "p1" else "p1"
    own = [int(row[seat] == "STAR") for row in history]
    opp = [int(row[other] == "STAR") for row in history]

    def experts(t):
        if t == 0:
            return [0.5] * 10

        past = opp[:t]
        frequency = (sum(past) + 1.5) / (t + 3.0)

        weights = [0.78 ** (t - 1 - i) for i in range(t)]
        recent = (
            1.0 + sum(w * x for w, x in zip(weights, past))
        ) / (2.0 + sum(weights))

        last = past[-1]
        transitions = [
            past[i] for i in range(1, t) if past[i - 1] == last
        ]
        markov = (sum(transitions) + 1.0) / (len(transitions) + 2.0)

        periodic = past[-2] if t >= 2 else last
        matched = own[t - 1] == past[-1]
        opponent_won = matched if other == "p1" else not matched
        stay_shift = last if opponent_won else 1 - last

        def soften(x):
            return 0.15 + 0.70 * x

        return [
            0.5,
            frequency,
            recent,
            markov,
            soften(last),
            soften(1 - last),
            soften(periodic),
            soften(own[t - 1]),
            soften(1 - own[t - 1]),
            soften(stay_shift),
        ]

    priors = [0.24, 0.18, 0.14, 0.12, 0.07,
              0.08, 0.05, 0.04, 0.04, 0.04]
    log_weights = [math.log(w) for w in priors]

    for t in range(n):
        forecasts = experts(t)
        for j, probability in enumerate(forecasts):
            likelihood = probability if opp[t] else 1.0 - probability
            log_weights[j] += (
                0.85 * (0.96 ** (n - 1 - t)) * math.log(likelihood)
            )

    maximum = max(log_weights)
    weights = [math.exp(w - maximum) for w in log_weights]
    forecasts = experts(n)
    opponent_star = sum(
        w * p for w, p in zip(weights, forecasts)
    ) / sum(weights)

    # Blend inferred exploitation with substantial unpredictable mixing.
    advantage = opponent_star - 0.5
    if seat == "p2":
        advantage = -advantage
    probability = 0.5 + 0.34 * math.tanh(4.0 * advantage)

    # Small, rapidly fading opening preference.
    probability += (0.06 if seat == "p1" else -0.025) * math.exp(-n / 3.0)

    return max(0.12, min(0.88, probability))
