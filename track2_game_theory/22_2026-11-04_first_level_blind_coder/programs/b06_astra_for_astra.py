import math


def predict(history, seat):
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    if not history:
        return 0.60 if seat == "p1" else 0.44

    other = "p2" if seat == "p1" else "p1"
    own = [int(row[seat] == "STAR") for row in history]
    opp = [int(row[other] == "STAR") for row in history]
    n = len(history)

    def forecasts(t):
        if t == 0:
            return [0.5] * 9

        past = opp[:t]
        frequency = (sum(past) + 2.0) / (t + 4.0)

        weights = [0.82 ** (t - 1 - i) for i in range(t)]
        recent = (1.5 + sum(w * x for w, x in zip(weights, past)))
        recent /= 3.0 + sum(weights)

        last = past[-1]
        repeat = 0.15 + 0.70 * last
        alternate = 1.0 - repeat

        matched = own[t - 1] == opp[t - 1]
        opponent_won = matched if other == "p1" else not matched
        win_stay = last if opponent_won else 1 - last

        copy = 0.15 + 0.70 * own[t - 1]
        counter = 1.0 - copy

        count = 0.0
        stars = 0.0
        for i in range(1, t):
            if opp[i - 1] == last:
                w = 0.92 ** (t - 1 - i)
                count += w
                stars += w * opp[i]
        conditional = (stars + 1.5) / (count + 3.0)

        periodic = 0.5 if t < 2 else 0.15 + 0.70 * opp[t - 2]
        return [
            frequency, recent, repeat, alternate,
            0.15 + 0.70 * win_stay, copy, counter,
            conditional, periodic,
        ]

    priors = [0.22, 0.18, 0.12, 0.12, 0.09, 0.06, 0.06, 0.10, 0.05]
    scores = [math.log(p) for p in priors]

    for t in range(1, n):
        candidates = forecasts(t)
        decay = 0.94 ** (n - 1 - t)
        for j, p in enumerate(candidates):
            likelihood = p if opp[t] else 1.0 - p
            scores[j] += decay * math.log(likelihood)

    peak = max(scores)
    weights = [math.exp(s - peak) for s in scores]
    candidates = forecasts(n)
    expected_opponent_star = sum(
        w * p for w, p in zip(weights, candidates)
    ) / sum(weights)

    response = (
        expected_opponent_star
        if seat == "p1"
        else 1.0 - expected_opponent_star
    )
    probability = 0.5 + 0.72 * (response - 0.5)

    won = (own[-1] == opp[-1]) if seat == "p1" else (
        own[-1] != opp[-1]
    )
    behavioral_choice = own[-1] if won else 1 - own[-1]
    probability += 0.025 * (2 * behavioral_choice - 1)
    probability += 0.015 * math.exp(-n / 6.0)

    return max(0.12, min(0.88, probability))
