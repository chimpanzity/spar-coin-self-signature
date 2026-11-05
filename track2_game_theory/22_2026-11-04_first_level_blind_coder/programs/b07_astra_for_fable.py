import math


def predict(history, seat):
    """Heuristic probability estimate; no model-specific calibration is assumed."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    if not history:
        return 0.62 if seat == "p1" else 0.42

    other = "p2" if seat == "p1" else "p1"
    opponent = [int(row[other] == "STAR") for row in history]
    own = [int(row[seat] == "STAR") for row in history]

    def forecasts(t):
        if t == 0:
            return [0.5] * 10

        past = opponent[:t]
        last = past[-1]
        frequency = (sum(past) + 2.0) / (t + 4.0)

        weights = [0.78 ** (t - 1 - i) for i in range(t)]
        recent = (
            1.0 + sum(w * x for w, x in zip(weights, past))
        ) / (2.0 + sum(weights))

        transitions = [
            opponent[i]
            for i in range(1, t)
            if opponent[i - 1] == last
        ]
        markov = (1.0 + sum(transitions)) / (2.0 + len(transitions))

        context = past[-2:]
        continuations = [
            opponent[i]
            for i in range(2, t)
            if opponent[i - 2:i] == context
        ] if t >= 2 else []
        second_order = (
            1.0 + sum(continuations)
        ) / (2.0 + len(continuations))

        # Opponent best-responds to our previous action.
        response = own[t - 1] if other == "p1" else 1 - own[t - 1]

        opponent_won = (
            (own[t - 1] == last) if other == "p1"
            else (own[t - 1] != last)
        )
        win_stay = last if opponent_won else 1 - last

        return [
            0.5,
            frequency,
            recent,
            0.15 + 0.70 * last,
            0.15 + 0.70 * (1 - last),
            markov,
            second_order,
            0.20 + 0.60 * response,
            0.20 + 0.60 * win_stay,
            0.20 + 0.60 * (1 - win_stay),
        ]

    priors = [2.0, 1.5, 1.5, 0.8, 1.2, 1.2, 0.7, 0.7, 0.7, 0.4]
    scores = [math.log(p) for p in priors]
    n = len(history)

    for t in range(1, n):
        predictions = forecasts(t)
        decay = 0.93 ** (n - 1 - t)
        for k, p in enumerate(predictions):
            likelihood = p if opponent[t] else 1.0 - p
            scores[k] += decay * math.log(max(likelihood, 1e-9))

    peak = max(scores)
    weights = [math.exp(s - peak) for s in scores]
    current = forecasts(n)
    opponent_star = sum(
        w * p for w, p in zip(weights, current)
    ) / sum(weights)

    response_star = opponent_star if seat == "p1" else 1.0 - opponent_star
    probability = 0.5 + 0.75 * (response_star - 0.5)

    # Weak priors for label preference and avoiding conspicuous own repetition.
    probability += 0.015
    run = 1
    while run < n and own[-run - 1] == own[-1]:
        run += 1
    probability += (1 - 2 * own[-1]) * min(0.045, 0.012 * run)

    return max(0.15, min(0.85, probability))
