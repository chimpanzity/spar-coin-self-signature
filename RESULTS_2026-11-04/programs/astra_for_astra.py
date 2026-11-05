import math


def predict(history):
    n = len(history)
    if n == 0:
        return (0.65, 0.42)

    moves = [
        [1 if row["p1"] == "STAR" else 0 for row in history],
        [1 if row["p2"] == "STAR" else 0 for row in history],
    ]
    answers = []

    for player in range(2):
        own = moves[player]
        other = moves[1 - player]
        experts = []

        # A smoothed frequency forecast provides a conservative fallback.
        total = 0.0
        stars = 0.0
        for t, choice in enumerate(own):
            weight = 0.88 ** (n - 1 - t)
            total += weight
            stars += weight * choice
        frequency = (stars + 1.5) / (total + 3.0)
        experts.append((1.5, frequency))

        # Score simple rules by how consistently they explain recent play.
        rules = [
            ("constant_star", 0.35, 0),
            ("constant_triangle", 0.35, 0),
            ("repeat", 0.75, 1),
            ("alternate", 1.10, 1),
            ("copy_opponent", 1.20 if player == 0 else 0.55, 1),
            ("oppose_opponent", 1.20 if player == 1 else 0.55, 1),
        ]
        for period in range(2, 6):
            rules.append(("period", 0.65 / (period - 1), period))

        for name, prior, start in rules:
            if start > n:
                continue

            support = 0.0
            evidence = 0.0
            for t in range(start, n):
                if name == "constant_star":
                    predicted = 1
                elif name == "constant_triangle":
                    predicted = 0
                elif name == "repeat":
                    predicted = own[t - 1]
                elif name == "alternate":
                    predicted = 1 - own[t - 1]
                elif name == "copy_opponent":
                    predicted = other[t - 1]
                elif name == "oppose_opponent":
                    predicted = 1 - other[t - 1]
                else:
                    predicted = own[t - start]

                weight = 0.94 ** (n - 1 - t)
                support += weight
                evidence += weight * (
                    math.log(1.64) if predicted == own[t]
                    else math.log(0.36)
                )

            if name == "constant_star":
                next_choice = 1
            elif name == "constant_triangle":
                next_choice = 0
            elif name == "repeat":
                next_choice = own[-1]
            elif name == "alternate":
                next_choice = 1 - own[-1]
            elif name == "copy_opponent":
                next_choice = other[-1]
            elif name == "oppose_opponent":
                next_choice = 1 - other[-1]
            else:
                next_choice = own[n - start]

            confidence = 0.30 + 0.60 * support / (support + 3.0)
            probability = 0.5 + confidence * (next_choice - 0.5)
            weight = prior * math.exp(min(12.0, evidence))
            experts.append((weight, probability))

        # Local transition tendencies can remain salient without a global rule.
        for context_length, prior in ((1, 0.65), (2, 0.45)):
            if n <= context_length:
                continue
            context = own[-context_length:]
            matches = 0.0
            successes = 0.0
            for t in range(context_length, n):
                if own[t - context_length:t] == context:
                    weight = 0.92 ** (n - 1 - t)
                    matches += weight
                    successes += weight * own[t]
            if matches:
                probability = (successes + 1.0) / (matches + 2.0)
                experts.append((prior * min(matches, 4.0), probability))

        denominator = sum(weight for weight, _ in experts)
        probability = sum(
            weight * value for weight, value in experts
        ) / denominator

        # Predict the observer's categorical forecast, not just the next move.
        centered = 2.0 * probability - 1.0
        sharpened = math.tanh(1.35 * centered)
        probability = 0.5 + 0.47 * sharpened

        initial_bias = (0.06 if player == 0 else -0.035) * (0.65 ** n)
        answers.append(max(0.02, min(0.98, probability + initial_bias)))

    return (answers[0], answers[1])
