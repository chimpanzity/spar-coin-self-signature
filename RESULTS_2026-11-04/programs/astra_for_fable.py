def predict(history):
    import math

    n = len(history)
    if n == 0:
        return (0.72, 0.36)

    sequences = [
        [1.0 if row["p1"] == "STAR" else -1.0 for row in history],
        [1.0 if row["p2"] == "STAR" else -1.0 for row in history],
    ]
    forecasts = []

    for player in range(2):
        own = sequences[player]
        opponent = sequences[1 - player]

        # Weak prior favoring the first-listed symbol.
        numerator = 0.10
        denominator = 1.0

        # Persistent empirical preferences, emphasizing recent observations.
        weights = [0.88 ** (n - 1 - t) for t in range(n)]
        total = sum(weights)
        preference = sum(w * x for w, x in zip(weights, own)) / (total + 2.0)
        numerator += 1.1 * preference
        denominator += 1.1

        # Continuation and alternation are especially salient to an observer.
        if n >= 2:
            transition_sum = 0.0
            transition_weight = 0.0
            for t in range(1, n):
                w = 0.90 ** (n - 1 - t)
                transition_sum += w * own[t] * own[t - 1]
                transition_weight += w
            transition = transition_sum / (transition_weight + 1.6)
            strength = 1.3 + 1.4 * abs(transition)
            numerator += strength * transition * own[-1]
            denominator += strength

        # Look for a short repeating schedule.
        best_score = 0.0
        best_prediction = 0.0
        for period in range(2, min(5, n // 2) + 1):
            comparisons = n - period
            agreement = sum(
                own[t] * own[t - period] for t in range(period, n)
            )
            reliability = agreement / (comparisons + 2.5)
            score = reliability - 0.035 * (period - 2)
            if score > best_score:
                best_score = score
                best_prediction = own[n - period] * reliability
        if best_score > 0.35:
            strength = 3.0 * best_score
            numerator += strength * best_prediction
            denominator += strength

        # Infer whether this player stays or switches after the latest outcome.
        latest_match = own[-1] == opponent[-1]
        conditional_sum = 0.0
        conditional_weight = 0.0
        for t in range(1, n):
            previous_match = own[t - 1] == opponent[t - 1]
            if previous_match == latest_match:
                w = 0.90 ** (n - 1 - t)
                conditional_sum += w * own[t] * own[t - 1]
                conditional_weight += w
        if conditional_weight:
            conditional = conditional_sum / (conditional_weight + 2.0)
            strength = min(1.2, conditional_weight / 3.0)
            numerator += strength * conditional * own[-1]
            denominator += strength

        # A common observer heuristic: match or oppose the opponent's last move.
        target = opponent[-1] if player == 0 else -opponent[-1]
        response_sum = 0.0
        response_weight = 0.0
        for t in range(1, n):
            w = 0.90 ** (n - 1 - t)
            previous_target = opponent[t - 1]
            if player == 1:
                previous_target = -previous_target
            response_sum += w * own[t] * previous_target
            response_weight += w
        response = (response_sum + 0.7) / (response_weight + 2.0)
        numerator += 0.9 * target * response
        denominator += 0.9

        signal = numerator / denominator
        probability = 0.5 + 0.43 * math.tanh(2.0 * signal)
        forecasts.append(max(0.05, min(0.95, probability)))

    return (forecasts[0], forecasts[1])
