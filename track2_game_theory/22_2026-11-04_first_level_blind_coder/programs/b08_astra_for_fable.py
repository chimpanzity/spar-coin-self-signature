import math


def predict(history, seat):
    """Return a deterministic, heuristic probability of choosing STAR."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if n == 0:
        return 0.65 if seat == "p1" else 0.38

    other = "p2" if seat == "p1" else "p1"
    opponent = [int(row[other] == "STAR") for row in history]
    own = [int(row[seat] == "STAR") for row in history]

    # Candidate patterns a history-reading player might try to exploit.
    def forecasts(t):
        past = opponent[:t]
        if not past:
            return [0.55] * 7

        weights = [0.83 ** (t - 1 - i) for i in range(t)]
        recent = (1.0 + sum(w * x for w, x in zip(weights, past))) / (
            2.0 + sum(weights)
        )
        frequency = (1.0 + sum(past)) / (t + 2.0)
        persistence = 0.12 + 0.76 * past[-1]
        alternation = 1.0 - persistence

        transition = []
        for i in range(1, t):
            if past[i - 1] == past[-1]:
                transition.append(past[i])
        markov = (1.0 + sum(transition)) / (2.0 + len(transition))

        # Opponent win-stay / lose-switch and reaction to our last move.
        opponent_won = (
            history[t - 1]["result"]
            == ("Matcher" if other == "p1" else "Mismatcher")
        )
        wsls_choice = past[-1] if opponent_won else 1 - past[-1]
        wsls = 0.2 + 0.6 * wsls_choice
        reactive_choice = own[t - 1] if other == "p1" else 1 - own[t - 1]
        reactive = 0.2 + 0.6 * reactive_choice
        return [frequency, recent, persistence, alternation, markov, wsls, reactive]

    priors = [1.2, 1.4, 0.85, 0.85, 1.0, 0.6, 0.6]
    losses = [0.0] * len(priors)
    for t in range(1, n):
        decay = 0.94 ** (n - 1 - t)
        for j, estimate in enumerate(forecasts(t)):
            losses[j] += decay * (estimate - opponent[t]) ** 2

    weights = [
        prior * math.exp(-2.2 * loss)
        for prior, loss in zip(priors, losses)
    ]
    estimates = forecasts(n)
    p_opponent_star = sum(
        w * p for w, p in zip(weights, estimates)
    ) / sum(weights)

    advantage = 2.0 * p_opponent_star - 1.0
    if seat == "p2":
        advantage = -advantage

    # Retain substantial uncertainty: strategic prediction is not a model trace.
    p = 0.5 + 0.36 * math.tanh(2.4 * advantage)

    # Small allowance for symbolic preference and deliberate run avoidance.
    p += 0.015
    run = 1
    while run < n and own[-run - 1] == own[-1]:
        run += 1
    if run >= 3:
        p += (1 if own[-1] == 0 else -1) * min(0.055, 0.015 * (run - 2))

    return max(0.10, min(0.90, p))
