import math


def predict(history, seat):
    """Estimate STAR probability with a conservative behavioral ensemble."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    own_key = seat
    other_key = "p2" if seat == "p1" else "p1"
    own = [int(row[own_key] == "STAR") for row in history]
    other = [int(row[other_key] == "STAR") for row in history]
    n = len(history)

    if not n:
        return 0.55 if seat == "p1" else 0.45

    def forecasts(t):
        past = other[:t]
        if not past:
            return [0.5] * 8

        frequency = (sum(past) + 2.0) / (t + 4.0)

        weighted_sum = 0.0
        total_weight = 0.0
        for i, value in enumerate(past):
            weight = 0.8 ** (t - 1 - i)
            weighted_sum += weight * value
            total_weight += weight
        recent = (weighted_sum + 1.5) / (total_weight + 3.0)

        repeat = 0.25 + 0.5 * past[-1]
        alternate = 1.0 - repeat

        relevant = [
            past[i]
            for i in range(1, t)
            if past[i - 1] == past[-1]
        ]
        transition = (sum(relevant) + 1.5) / (len(relevant) + 3.0)

        # Opponent may respond to our previous action according to its role.
        response_bit = own[t - 1] if seat == "p2" else 1 - own[t - 1]
        response = 0.25 + 0.5 * response_bit

        opponent_won = (
            past[-1] == own[t - 1]
            if seat == "p2"
            else past[-1] != own[t - 1]
        )
        stay_shift_bit = past[-1] if opponent_won else 1 - past[-1]
        stay_shift = 0.25 + 0.5 * stay_shift_bit

        return [
            0.5, frequency, recent, repeat, alternate,
            transition, response, stay_shift
        ]

    log_weights = [math.log(w) for w in (4, 2, 2, 1, 1, 1, 1, 1)]
    for t in range(n):
        candidates = forecasts(t)
        for j, probability in enumerate(candidates):
            likelihood = probability if other[t] else 1.0 - probability
            log_weights[j] += 0.7 * math.log(likelihood)

    offset = max(log_weights)
    weights = [math.exp(value - offset) for value in log_weights]
    candidates = forecasts(n)
    opponent_star = sum(
        weight * probability
        for weight, probability in zip(weights, candidates)
    ) / sum(weights)

    desired_star = opponent_star if seat == "p1" else 1.0 - opponent_star

    # Shrink toward random play: opponent predictability does not imply
    # that the target model will consistently exploit that predictability.
    opening_bias = (0.05 if seat == "p1" else -0.05) * math.exp(-n / 3.0)
    probability = 0.5 + 0.6 * (desired_star - 0.5) + opening_bias
    return max(0.05, min(0.95, probability))
