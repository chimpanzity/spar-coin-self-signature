import math


def predict(history, seat):
    """Estimate P(STAR) with a conservative, history-adaptive strategy mixture."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    other = "p2" if seat == "p1" else "p1"

    def forecasts(rows):
        # Expert forecasts concern the target player's action, not who will win.
        opening = 0.55 if seat == "p1" else 0.47
        if not rows:
            return [0.5, opening] + [0.5] * 8

        own = [int(r[seat] == "STAR") for r in rows]
        opp = [int(r[other] == "STAR") for r in rows]
        n = len(rows)

        def response(p):
            return p if seat == "p1" else 1.0 - p

        frequency = (2.0 + sum(opp)) / (4.0 + n)

        numerator, denominator = 1.5, 3.0
        for age, action in enumerate(reversed(opp)):
            weight = 0.78 ** age
            numerator += weight * action
            denominator += weight
        recent = numerator / denominator

        # Opponent's next move conditional on their previous move.
        numerator, denominator = 2.0, 4.0
        for i in range(1, n):
            if opp[i - 1] == opp[-1]:
                numerator += opp[i]
                denominator += 1.0
        transition = numerator / denominator

        # Opponent's response to the target's previous move.
        numerator, denominator = 2.0, 4.0
        for i in range(1, n):
            if own[i - 1] == own[-1]:
                numerator += opp[i]
                denominator += 1.0
        reactive = numerator / denominator

        won = (
            rows[-1]["result"]
            == ("Matcher" if seat == "p1" else "Mismatcher")
        )
        stay_shift = own[-1] if won else 1 - own[-1]

        return [
            0.5,
            opening,
            response(frequency),
            response(recent),
            response(transition),
            response(reactive),
            response(0.35 + 0.30 * opp[-1]),
            0.35 + 0.30 * (1 - own[-1]),
            0.35 + 0.30 * stay_shift,
            (3.0 + sum(own)) / (6.0 + n),
        ]

    priors = [0.34, 0.08, 0.12, 0.10, 0.07,
              0.05, 0.07, 0.06, 0.06, 0.05]
    scores = [math.log(w) for w in priors]

    # Learn which hypotheses have actually predicted this player's choices.
    for i, row in enumerate(history):
        observed = int(row[seat] == "STAR")
        for j, p in enumerate(forecasts(history[:i])):
            likelihood = p if observed else 1.0 - p
            scores[j] += 0.75 * math.log(max(1e-12, likelihood))

    offset = max(scores)
    weights = [math.exp(s - offset) for s in scores]
    current = forecasts(history)
    estimate = sum(w * p for w, p in zip(weights, current)) / sum(weights)
    return max(0.0, min(1.0, estimate))
