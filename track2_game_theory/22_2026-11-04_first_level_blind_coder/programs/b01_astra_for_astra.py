def predict(history, seat):
    import math

    if seat not in ("p1", "p2"):
        raise ValueError("seat must be 'p1' or 'p2'")

    other = "p2" if seat == "p1" else "p1"

    def star(choice):
        return 1.0 if choice == "STAR" else 0.0

    def policies(past):
        # These are uncertain behavioral hypotheses, not access to the
        # target model's internal probabilities.
        baseline = 0.54 if seat == "p1" else 0.48
        if not past:
            return [baseline] * 10

        own = [star(row[seat]) for row in past]
        opp = [star(row[other]) for row in past]
        n = len(past)

        def response(p):
            return p if seat == "p1" else 1.0 - p

        frequency = (2.0 + sum(opp)) / (4.0 + n)

        weighted_sum = 0.0
        total_weight = 0.0
        for age, value in enumerate(reversed(opp)):
            weight = 0.75 ** age
            weighted_sum += weight * value
            total_weight += weight
        recent = (1.0 + weighted_sum) / (2.0 + total_weight)

        transitions = [
            opp[i]
            for i in range(1, n)
            if opp[i - 1] == opp[-1]
        ]
        conditional = (
            1.5 + sum(transitions)
        ) / (3.0 + len(transitions))

        # Opponent may react to this player's previous choice.
        reactive = [
            opp[i]
            for i in range(1, n)
            if own[i - 1] == own[-1]
        ]
        reactive_probability = (
            2.0 + sum(reactive)
        ) / (4.0 + len(reactive))

        won = (own[-1] == opp[-1]) == (seat == "p1")
        stay_after_win = own[-1] if won else 1.0 - own[-1]

        def soften(p, strength=0.55):
            return 0.5 + strength * (p - 0.5)

        return [
            baseline,
            0.66,
            0.34,
            soften(1.0 - own[-1], 0.40),
            soften(stay_after_win, 0.40),
            soften(response(frequency), 0.75),
            soften(response(recent), 0.65),
            soften(response(opp[-1]), 0.35),
            soften(response(conditional), 0.70),
            soften(response(reactive_probability), 0.65),
        ]

    priors = [0.36, 0.08, 0.06, 0.10, 0.06,
              0.10, 0.08, 0.06, 0.05, 0.05]
    log_weights = [math.log(weight) for weight in priors]

    for i, row in enumerate(history):
        predictions = policies(history[:i])
        observed = star(row[seat])
        for j, probability in enumerate(predictions):
            likelihood = probability if observed else 1.0 - probability
            # Temper evidence because the hypotheses are approximate.
            log_weights[j] += 0.75 * math.log(likelihood)

    offset = max(log_weights)
    weights = [math.exp(value - offset) for value in log_weights]
    predictions = policies(history)
    probability = sum(
        weight * prediction
        for weight, prediction in zip(weights, predictions)
    ) / sum(weights)

    return max(0.0, min(1.0, probability))
