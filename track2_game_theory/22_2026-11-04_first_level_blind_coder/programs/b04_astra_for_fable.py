import math


def predict(history, seat):
    """Heuristic prediction, not a calibrated model of Claude's behavior."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if n == 0:
        return 0.60 if seat == "p1" else 0.44

    other = "p2" if seat == "p1" else "p1"
    mine = [int(row[seat] == "STAR") for row in history]
    theirs = [int(row[other] == "STAR") for row in history]

    def forecasts(t):
        if not t:
            return [0.5] * 11

        ys = theirs[:t]
        xs = mine[:t]
        frequency = (sum(ys) + 2.0) / (t + 4.0)

        weights = [0.80 ** (t - 1 - j) for j in range(t)]
        recent = (
            1.5 + sum(w * y for w, y in zip(weights, ys))
        ) / (3.0 + sum(weights))

        repeat = 0.15 + 0.70 * ys[-1]
        alternate = 1.0 - repeat

        transition_samples = [
            ys[j] for j in range(1, t) if ys[j - 1] == ys[-1]
        ]
        markov = (1.5 + sum(transition_samples)) / (
            3.0 + len(transition_samples)
        )

        context_samples = []
        if t >= 2:
            for j in range(2, t):
                if ys[j - 2:j] == ys[-2:]:
                    context_samples.append(ys[j])
        context = (1.5 + sum(context_samples)) / (
            3.0 + len(context_samples)
        )

        copy_me = 0.20 + 0.60 * xs[-1]
        oppose_me = 1.0 - copy_me

        matched = xs[-1] == ys[-1]
        opponent_won = matched if other == "p1" else not matched
        stay_shift_choice = ys[-1] if opponent_won else 1 - ys[-1]
        stay_shift = 0.20 + 0.60 * stay_shift_choice

        lag_two = 0.5 if t < 2 else 0.20 + 0.60 * ys[-2]
        return [
            0.5, frequency, recent, repeat, alternate, markov,
            context, copy_me, oppose_me, stay_shift, lag_two
        ]

    priors = [3.0, 1.5, 1.2, 0.7, 0.7, 1.0, 0.6, 0.5, 0.5, 0.6, 0.5]
    scores = [math.log(p) for p in priors]
    for t in range(n):
        candidates = forecasts(t)
        discount = 0.94 ** (n - 1 - t)
        for k, p in enumerate(candidates):
            likelihood = p if theirs[t] else 1.0 - p
            scores[k] += discount * math.log(likelihood)

    maximum = max(scores)
    weights = [math.exp(s - maximum) for s in scores]
    candidates = forecasts(n)
    opponent_star = sum(
        w * p for w, p in zip(weights, candidates)
    ) / sum(weights)

    best_response_star = opponent_star if seat == "p1" else 1.0 - opponent_star

    # Allow substantial probability for deliberate randomization and
    # reasoning strategies absent from the opponent-pattern ensemble.
    probability = 0.5 + 0.65 * (best_response_star - 0.5)

    matched = mine[-1] == theirs[-1]
    won = matched if seat == "p1" else not matched
    reactive_choice = mine[-1] if won else 1 - mine[-1]
    probability += 0.025 * (2 * reactive_choice - 1)

    opening_bias = 0.035 if seat == "p1" else -0.020
    probability += opening_bias * math.exp(-n / 4.0)

    return max(0.15, min(0.85, probability))
