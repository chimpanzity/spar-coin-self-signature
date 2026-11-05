import math


def predict(history, seat):
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if not n:
        return 0.62 if seat == "p1" else 0.40

    other = "p2" if seat == "p1" else "p1"
    opp = [int(row[other] == "STAR") for row in history]
    own = [int(row[seat] == "STAR") for row in history]

    def forecast(kind, t):
        xs = opp[:t]
        if not t:
            return 0.5

        if kind == "frequency":
            return (sum(xs) + 1.5) / (t + 3.0)

        if kind == "recent":
            weights = [0.75 ** (t - 1 - i) for i in range(t)]
            return (0.8 + sum(w * x for w, x in zip(weights, xs))) / (
                1.6 + sum(weights)
            )

        if kind == "repeat":
            return 0.85 if xs[-1] else 0.15

        if kind == "alternate":
            return 0.15 if xs[-1] else 0.85

        if kind == "markov":
            matches = [xs[i] for i in range(1, t) if xs[i - 1] == xs[-1]]
            return (sum(matches) + 1.0) / (len(matches) + 2.0)

        if kind == "context":
            if t < 2:
                return 0.5
            context = xs[-2:]
            matches = [
                xs[i] for i in range(2, t) if xs[i - 2:i] == context
            ]
            return (sum(matches) + 1.0) / (len(matches) + 2.0)

        if kind == "react":
            # Opponent best responds to our most recent choice.
            target = own[t - 1] if other == "p1" else 1 - own[t - 1]
            return 0.8 if target else 0.2

        if kind == "win_stay":
            same = opp[t - 1] == own[t - 1]
            won = same if other == "p1" else not same
            target = xs[-1] if won else 1 - xs[-1]
            return 0.8 if target else 0.2

        period = int(kind[6:])
        if t < period:
            return 0.5
        return 0.85 if xs[t - period] else 0.15

    models = [
        ("frequency", 1.8),
        ("recent", 1.5),
        ("repeat", 0.7),
        ("alternate", 0.9),
        ("markov", 1.0),
        ("context", 0.5),
        ("react", 0.6),
        ("win_stay", 0.6),
        ("period3", 0.25),
        ("period4", 0.20),
    ]

    scores = []
    for kind, prior in models:
        score = math.log(prior)
        for t in range(1, n):
            p = forecast(kind, t)
            likelihood = p if opp[t] else 1.0 - p
            score += (0.94 ** (n - 1 - t)) * math.log(likelihood)
        scores.append(score)

    top = max(scores)
    weights = [math.exp(s - top) for s in scores]
    opponent_star = sum(
        w * forecast(kind, n) for w, (kind, _) in zip(weights, models)
    ) / sum(weights)

    advantage = 2.0 * opponent_star - 1.0
    if seat == "p2":
        advantage = -advantage

    # A language-model player may exploit perceived patterns, but also
    # deliberately avoid predictable best responses.
    exploitation = 1.0 / (1.0 + math.exp(-4.5 * advantage))
    baseline = 0.52 if seat == "p1" else 0.49
    probability = 0.72 * exploitation + 0.28 * baseline
    return min(0.90, max(0.10, probability))
