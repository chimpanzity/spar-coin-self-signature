import math


def predict(history, seat):
    """Heuristic probability estimate; requires no model-specific training data."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    if not history:
        return 0.60 if seat == "p1" else 0.43

    other = "p2" if seat == "p1" else "p1"
    own = [int(row[seat] == "STAR") for row in history]
    opp = [int(row[other] == "STAR") for row in history]
    n = len(history)

    def estimate(kind, t):
        xs = opp[:t]
        if kind == "fair":
            return 0.5
        if kind == "frequency":
            return (sum(xs) + 1.5) / (t + 3.0)
        if kind == "recent":
            weights = [0.78 ** (t - 1 - i) for i in range(t)]
            return (1.0 + sum(w * x for w, x in zip(weights, xs))) / (
                2.0 + sum(weights)
            )
        if t == 0:
            return 0.5
        if kind == "repeat":
            return 0.88 if xs[-1] else 0.12
        if kind == "alternate":
            return 0.12 if xs[-1] else 0.88
        if kind == "copy":
            return 0.85 if own[t - 1] else 0.15
        if kind == "counter":
            return 0.15 if own[t - 1] else 0.85
        if kind == "win_stay":
            matched = own[t - 1] == xs[-1]
            opponent_won = matched if other == "p1" else not matched
            target = xs[-1] if opponent_won else 1 - xs[-1]
            return 0.85 if target else 0.15
        if kind == "transition":
            following = [
                xs[i] for i in range(1, t) if xs[i - 1] == xs[-1]
            ]
            return (sum(following) + 1.0) / (len(following) + 2.0)
        if kind.startswith("period"):
            period = int(kind[6:])
            if t < period:
                return 0.5
            return 0.85 if xs[t - period] else 0.15
        return 0.5

    priors = {
        "fair": 0.24,
        "frequency": 0.18,
        "recent": 0.14,
        "repeat": 0.09,
        "alternate": 0.12,
        "transition": 0.07,
        "copy": 0.035,
        "counter": 0.045,
        "win_stay": 0.04,
        "period3": 0.02,
        "period4": 0.02,
    }

    scores = {}
    for kind, prior in priors.items():
        score = math.log(prior)
        for t, observed in enumerate(opp):
            p = estimate(kind, t)
            likelihood = p if observed else 1.0 - p
            score += (0.94 ** (n - 1 - t)) * math.log(likelihood)
        scores[kind] = score

    largest = max(scores.values())
    weights = {k: math.exp(v - largest) for k, v in scores.items()}
    total = sum(weights.values())
    opponent_star = sum(
        weights[k] * estimate(k, n) for k in weights
    ) / total

    # Approximate an LLM's tendency to best-respond to visible patterns,
    # while retaining uncertainty about its reasoning and randomization.
    advantage = 2.0 * opponent_star - 1.0
    if seat == "p2":
        advantage = -advantage
    probability = 0.5 + 0.37 * math.tanh(2.5 * advantage)

    won = history[-1]["result"] == (
        "Matcher" if seat == "p1" else "Mismatcher"
    )
    fallback = own[-1] if won else 1 - own[-1]
    ambiguity = math.exp(-7.0 * abs(advantage))
    probability += ambiguity * (
        0.025 * (2 * fallback - 1) + (0.015 if seat == "p1" else -0.005)
    )

    return max(0.08, min(0.92, probability))
