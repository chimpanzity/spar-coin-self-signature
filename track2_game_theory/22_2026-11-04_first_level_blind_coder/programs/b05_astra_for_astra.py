import math


def predict(history, seat):
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    own = [int(row[seat] == "STAR") for row in history]
    other_seat = "p2" if seat == "p1" else "p1"
    opp = [int(row[other_seat] == "STAR") for row in history]
    n = len(history)

    if not n:
        return 0.58 if seat == "p1" else 0.45

    def forecasts(t):
        xs = opp[:t]
        if not xs:
            return [0.5] * 7

        frequency = (2.0 + sum(xs)) / (4.0 + t)

        weighted_sum = 0.0
        total_weight = 0.0
        for i, x in enumerate(xs):
            w = 0.82 ** (t - 1 - i)
            weighted_sum += w * x
            total_weight += w
        recent = (1.5 + weighted_sum) / (3.0 + total_weight)

        matches = [
            xs[i] for i in range(1, t)
            if xs[i - 1] == xs[-1]
        ]
        transition = (1.5 + sum(matches)) / (3.0 + len(matches))

        repeat = 0.75 if xs[-1] else 0.25
        alternate = 1.0 - repeat

        # An opponent might best-respond to our previous move.
        response = own[t - 1] if other_seat == "p1" else 1 - own[t - 1]
        reactive = 0.25 + 0.5 * response

        return [0.5, frequency, recent, transition,
                repeat, alternate, reactive]

    # Average simple opponent models, rewarding past predictive accuracy.
    log_weights = [math.log(w) for w in
                   (0.30, 0.18, 0.16, 0.14, 0.07, 0.08, 0.07)]
    for t in range(n):
        predictions = forecasts(t)
        for j, p in enumerate(predictions):
            likelihood = p if opp[t] else 1.0 - p
            log_weights[j] += 0.7 * math.log(likelihood)

    peak = max(log_weights)
    weights = [math.exp(w - peak) for w in log_weights]
    predictions = forecasts(n)
    q = sum(w * p for w, p in zip(weights, predictions)) / sum(weights)

    # Allow substantial uncertainty about whether the player exploits
    # perceived patterns or deliberately mixes its actions.
    strategic = q if seat == "p1" else 1.0 - q
    strategic = 0.5 + 0.75 * (strategic - 0.5)

    prior = 0.54 if seat == "p1" else 0.48
    personal = (6.0 * prior + sum(own)) / (6.0 + n)

    p_star = 0.85 * strategic + 0.15 * personal
    return max(0.05, min(0.95, p_star))
