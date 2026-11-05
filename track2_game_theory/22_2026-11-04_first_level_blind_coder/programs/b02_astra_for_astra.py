import math


def predict(history, seat):
    """Heuristic probability estimate; no model-specific calibration is assumed."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    if not history:
        return 0.57 if seat == "p1" else 0.46

    opponent = "p2" if seat == "p1" else "p1"
    opp = [int(row[opponent] == "STAR") for row in history]
    own = [int(row[seat] == "STAR") for row in history]

    def forecasts(sequence, other):
        n = len(sequence)
        frequency = (2.0 + sum(sequence)) / (4.0 + n)

        total = 0.0
        stars = 0.0
        for age, value in enumerate(reversed(sequence)):
            weight = 0.85 ** age
            total += weight
            stars += weight * value
        recent = (1.5 + stars) / (3.0 + total)

        transition_stars = 1.5
        transition_total = 3.0
        response_stars = 1.5
        response_total = 3.0
        for i in range(1, n):
            if sequence[i - 1] == sequence[-1]:
                transition_stars += sequence[i]
                transition_total += 1.0
            if other[i - 1] == other[-1]:
                response_stars += sequence[i]
                response_total += 1.0

        return (
            0.5,
            frequency,
            recent,
            transition_stars / transition_total,
            response_stars / response_total,
            0.2 + 0.6 * sequence[-1],
            0.8 - 0.6 * sequence[-1],
        )

    # Favor patterns only to the extent that they predicted earlier rounds.
    weights = [3.0, 1.5, 1.5, 1.0, 0.75, 0.5, 0.5]
    losses = [0.0] * len(weights)
    for t in range(1, len(opp)):
        candidates = forecasts(opp[:t], own[:t])
        for j, probability in enumerate(candidates):
            losses[j] = 0.9 * losses[j] + (probability - opp[t]) ** 2

    candidates = forecasts(opp, own)
    weights = [
        weight * math.exp(-3.0 * loss)
        for weight, loss in zip(weights, losses)
    ]
    opponent_star = sum(
        weight * probability
        for weight, probability in zip(weights, candidates)
    ) / sum(weights)

    target_star = opponent_star if seat == "p1" else 1.0 - opponent_star

    # Substantial shrinkage accounts for randomization and uncertainty about
    # whether the target model uses any of these opponent-pattern heuristics.
    estimate = 0.5 + 0.55 * (target_star - 0.5)
    estimate += 0.02 * math.exp(-len(history) / 5.0)
    return max(0.05, min(0.95, estimate))
