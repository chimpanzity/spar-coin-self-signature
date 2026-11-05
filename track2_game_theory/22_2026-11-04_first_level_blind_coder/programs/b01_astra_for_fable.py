import math


def predict(history, seat):
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    own_key = seat
    opp_key = "p2" if seat == "p1" else "p1"
    own = [int(row[own_key] == "STAR") for row in history]
    opp = [int(row[opp_key] == "STAR") for row in history]
    n = len(history)

    if n == 0:
        return 0.66 if seat == "p1" else 0.35

    def experts(t):
        past = opp[:t]
        if not past:
            return [0.55] * 9

        frequency = (sum(past) + 1.5) / (t + 3.0)

        weights = [0.76 ** (t - 1 - j) for j in range(t)]
        recent = (0.8 + sum(w * x for w, x in zip(weights, past))) / (
            1.6 + sum(weights)
        )

        repeat = 0.14 + 0.72 * past[-1]
        alternate = 1.0 - repeat

        # Estimate transitions conditional on the opponent's last symbol.
        total, stars = 2.0, 1.0
        for j in range(1, t):
            if past[j - 1] == past[-1]:
                w = 0.9 ** (t - 1 - j)
                total += w
                stars += w * past[j]
        transition = stars / total

        # Look for recurrence of the latest two-symbol context.
        total, stars = 2.0, 1.0
        if t >= 2:
            context = past[-2:]
            for j in range(2, t):
                if past[j - 2:j] == context:
                    w = 0.93 ** (t - 1 - j)
                    total += w
                    stars += w * past[j]
        context_prediction = stars / total

        periodic = 0.5 if t < 2 else 0.18 + 0.64 * past[-2]

        # An opponent may respond directly to our previous action.
        response = own[t - 1] if seat == "p2" else 1 - own[t - 1]
        reactive = 0.2 + 0.6 * response

        matched = own[t - 1] == past[-1]
        opponent_won = matched if seat == "p2" else not matched
        stay_shift = past[-1] if opponent_won else 1 - past[-1]
        stay_shift = 0.22 + 0.56 * stay_shift

        return [
            frequency, recent, repeat, alternate, transition,
            context_prediction, periodic, reactive, stay_shift
        ]

    priors = [1.5, 1.8, 0.8, 0.8, 1.3, 0.7, 0.4, 0.7, 0.6]
    scores = [math.log(w) for w in priors]

    for t in range(1, n):
        predictions = experts(t)
        age_weight = 0.92 ** (n - 1 - t)
        for k, p in enumerate(predictions):
            likelihood = p if opp[t] else 1.0 - p
            scores[k] += 0.85 * age_weight * math.log(likelihood)

    maximum = max(scores)
    weights = [math.exp(s - maximum) for s in scores]
    current = experts(n)
    opponent_star = sum(w * p for w, p in zip(weights, current)) / sum(weights)

    target = opponent_star if seat == "p1" else 1.0 - opponent_star
    strategic = 0.5 + 0.40 * math.tanh(3.0 * (target - 0.5))

    matched = own[-1] == opp[-1]
    won = matched if seat == "p1" else not matched
    stay_shift = own[-1] if won else 1 - own[-1]

    probability = 0.90 * strategic + 0.10 * (0.25 + 0.50 * stay_shift)
    return max(0.08, min(0.92, probability))
