import math


def predict(history, seat):
    """Return an online, history-only estimate of P(next choice == STAR)."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    other = "p2" if seat == "p1" else "p1"

    def experts(past):
        n = len(past)
        if not n:
            opening = 0.56 if seat == "p1" else 0.47
            return [0.5, opening, opening, opening, opening,
                    0.5, 0.5, 0.60, 0.40]

        own = [int(row[seat] == "STAR") for row in past]
        opp = [int(row[other] == "STAR") for row in past]

        def response(p):
            # A softened best response to an estimated opponent tendency.
            if seat == "p2":
                p = 1.0 - p
            return 0.5 + 0.7 * (p - 0.5)

        frequency = (sum(opp) + 2.0) / (n + 4.0)

        weighted_sum = 0.0
        weight_sum = 0.0
        for age, choice in enumerate(reversed(opp)):
            weight = 0.75 ** age
            weighted_sum += weight * choice
            weight_sum += weight
        recent = (weighted_sum + 1.0) / (weight_sum + 2.0)

        transition_sum = 0.0
        transition_count = 0.0
        for i in range(1, n):
            if opp[i - 1] == opp[-1]:
                weight = 0.9 ** (n - 1 - i)
                transition_sum += weight * opp[i]
                transition_count += weight
        transition = (transition_sum + 1.5) / (transition_count + 3.0)

        last_opponent = 0.75 if opp[-1] else 0.25
        matched = own[-1] == opp[-1]
        won = matched if seat == "p1" else not matched
        stay_shift = own[-1] if won else 1 - own[-1]

        return [
            0.5,
            response(frequency),
            response(recent),
            response(transition),
            response(last_opponent),
            0.65 if stay_shift else 0.35,
            0.35 if own[-1] else 0.65,
            0.60,
            0.40,
        ]

    # Most prior mass favors unpredictable play. Behavioral hypotheses gain
    # influence only when the player's recorded choices support them.
    priors = [0.48, 0.10, 0.10, 0.07, 0.07, 0.05, 0.05, 0.04, 0.04]
    log_weights = [math.log(p) for p in priors]

    for t, row in enumerate(history):
        estimates = experts(history[:t])
        observed = int(row[seat] == "STAR")
        for j, p in enumerate(estimates):
            likelihood = p if observed else 1.0 - p
            log_weights[j] += 0.85 * math.log(likelihood)

    offset = max(log_weights)
    weights = [math.exp(w - offset) for w in log_weights]
    estimates = experts(history)
    return sum(w * p for w, p in zip(weights, estimates)) / sum(weights)
