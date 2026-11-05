def predict(history, seat):
    import math
    STAR, TRI = "STAR", "TRIANGLE"
    n = len(history)
    if n == 0:
        # first-listed-option bias, slightly stronger for matcher
        return 0.6 if seat == "p1" else 0.55

    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    my_hist = [r[me] for r in history]
    op_hist = [r[opp] for r in history]
    my_role = "Matcher" if seat == "p1" else "Mismatcher"
    won_last = history[-1]["result"] == my_role

    def to_sign(c):  # +1 for STAR, -1 for TRIANGLE
        return 1.0 if c == STAR else -1.0

    # Build an estimate of what the LLM thinks the opponent will play next (sign toward STAR)
    pred = 0.0
    # 1. opponent repeats last move
    pred += 0.9 * to_sign(op_hist[-1])
    # 2. opponent streak -> stronger continuation belief
    streak = 1
    for i in range(n - 2, -1, -1):
        if op_hist[i] == op_hist[-1]:
            streak += 1
        else:
            break
    if streak >= 2:
        pred += 0.5 * min(streak - 1, 3) * to_sign(op_hist[-1])
    # 3. opponent frequency bias (recent window)
    window = op_hist[-6:]
    freq = sum(to_sign(c) for c in window) / len(window)
    pred += 0.8 * freq
    # 4. opponent lose-shift heuristic: if opponent lost last round, LLM may expect a switch
    opp_role = "Mismatcher" if seat == "p1" else "Matcher"
    opp_won_last = history[-1]["result"] == opp_role
    if not opp_won_last:
        pred -= 0.6 * to_sign(op_hist[-1])
    # 5. opponent alternation pattern detection
    if n >= 3:
        alt = all(op_hist[i] != op_hist[i - 1] for i in range(n - 2, n))
        if alt:
            pred += 1.0 * (-to_sign(op_hist[-1]))

    # Convert predicted opponent move to own move
    if seat == "p1":
        own = pred           # matcher copies predicted opponent move
    else:
        own = -pred          # mismatcher opposes it

    # Self-behaviour adjustments
    my_last = to_sign(my_hist[-1])
    if won_last:
        own += 0.5 * my_last      # win-stay tendency
    else:
        own -= 0.8 * my_last      # lose-shift tendency
    # avoid own long streaks (desire to look unpredictable)
    ms = 1
    for i in range(n - 2, -1, -1):
        if my_hist[i] == my_hist[-1]:
            ms += 1
        else:
            break
    if ms >= 3:
        own -= 0.6 * my_last
    # slight STAR bias
    own += 0.15

    p = 1.0 / (1.0 + math.exp(-0.7 * own))
    return max(0.15, min(0.85, p))
