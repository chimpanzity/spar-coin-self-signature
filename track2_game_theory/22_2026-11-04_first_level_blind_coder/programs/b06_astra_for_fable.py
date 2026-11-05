import math


def predict(history, seat):
    """Heuristic probability of STAR; no model-specific calibration is assumed."""
    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    n = len(history)
    if not n:
        return 0.64 if seat == "p1" else 0.42

    other = "p2" if seat == "p1" else "p1"
    mine = [int(row[seat] == "STAR") for row in history]
    theirs = [int(row[other] == "STAR") for row in history]

    # Candidate forecasts of the opponent's next move. Shrink estimates
    # because histories are short and apparent patterns may be accidental.
    def forecasts(t):
        xs = theirs[:t]
        ys = mine[:t]
        if not t:
            return [0.55] * 5

        frequency = (2.0 + sum(xs)) / (4.0 + t)

        total = 0.0
        stars = 0.0
        for i, x in enumerate(xs):
            weight = 0.8 ** (t - 1 - i)
            total += weight
            stars += weight * x
        recent = (1.0 + stars) / (2.0 + total)

        last = xs[-1]
        hits = count = 0
        for i in range(1, t):
            if xs[i - 1] == last:
                count += 1
                hits += xs[i]
        transition = (1.5 + hits) / (3.0 + count)

        # Opponent reacting to our previous choice.
        reaction = 0.5
        if t >= 2:
            hits = count = 0
            for i in range(1, t):
                if ys[i - 1] == ys[-1]:
                    count += 1
                    hits += xs[i]
            reaction = (1.5 + hits) / (3.0 + count)

        opponent_won = (
            xs[-1] == ys[-1] if other == "p1"
            else xs[-1] != ys[-1]
        )
        stay_shift = 0.7 if (
            last if opponent_won else 1 - last
        ) else 0.3
        return [frequency, recent, transition, reaction, stay_shift]

    # Weight simple hypotheses by their historical forecasting performance.
    losses = [0.0] * 5
    for t in range(1, n):
        guesses = forecasts(t)
        for j, guess in enumerate(guesses):
            losses[j] = 0.9 * losses[j] + (guess - theirs[t]) ** 2

    priors = [1.2, 1.2, 1.0, 0.7, 0.4]
    weights = [
        prior * math.exp(-2.0 * loss)
        for prior, loss in zip(priors, losses)
    ]
    guesses = forecasts(n)
    opponent_star = sum(
        w * p for w, p in zip(weights, guesses)
    ) / sum(weights)

    advantage = 2.0 * opponent_star - 1.0
    if seat == "p2":
        advantage = -advantage

    # Partial best response, tempered by uncertainty about the target's
    # reasoning and its possible attempts to randomize.
    response = math.tanh(2.5 * advantage)
    opening_bias = (0.06 if seat == "p1" else -0.03) * math.exp(-n / 4.0)
    alternation_bias = 0.025 * (1 - 2 * mine[-1])
    probability = 0.5 + 0.29 * response + opening_bias + alternation_bias
    return max(0.15, min(0.85, probability))
