def predict(history, seat):
    import math
    n = len(history)
    if n == 0:
        # slight first-listed-option bias
        return 0.58 if seat == "p1" else 0.55

    me = seat
    opp = "p2" if seat == "p1" else "p1"
    my_role = "Matcher" if seat == "p1" else "Mismatcher"

    def s(x):  # +1 for STAR, -1 for TRIANGLE
        return 1.0 if x == "STAR" else -1.0

    last = history[-1]
    my_last = s(last[me])
    opp_last = s(last[opp])
    i_won = (last["result"] == my_role)
    opp_won = not i_won

    # --- Predict what the LLM thinks the opponent will do next ---
    # Opponent's own streak and outcome: lose-shift / win-stay assumption
    opp_streak = 1
    for r in range(n - 2, -1, -1):
        if history[r][opp] == last[opp]:
            opp_streak += 1
        else:
            break
    if opp_won:
        pred_opp = opp_last * 0.25  # expect stay, mildly
    else:
        pred_opp = -opp_last * 0.45  # expect switch after loss
    if opp_streak >= 3:
        # LLM suspects the opponent will break a long streak
        pred_opp -= opp_last * 0.3 * min(opp_streak - 2, 3)
    # Opponent's overall frequency bias (level-1 exploitation)
    opp_star = sum(1 for h in history if h[opp] == "STAR")
    freq_bias = (opp_star - (n - opp_star)) / float(n)
    pred_opp += 0.35 * freq_bias
    # Opponent's recent lag-1 transition pattern
    if n >= 3:
        same = 0; tot = 0
        for r in range(1, n):
            tot += 1
            if history[r][opp] == history[r - 1][opp]:
                same += 1
        trans = (same - (tot - same)) / float(tot)
        pred_opp += 0.3 * trans * opp_last

    # Matcher wants to match predicted opponent; mismatcher wants opposite
    target = pred_opp if seat == "p1" else -pred_opp

    # --- Own behavioural tendencies ---
    my_streak = 1
    for r in range(n - 2, -1, -1):
        if history[r][me] == last[me]:
            my_streak += 1
        else:
            break
    own = 0.0
    # win-stay / lose-shift (weak for LLMs, but present)
    own += (0.15 if i_won else -0.3) * my_last
    # anti-streak: LLMs dislike repeating themselves many times
    if my_streak >= 2:
        own -= 0.35 * min(my_streak - 1, 3) * my_last
    # balance overall own frequency toward 50/50
    my_star = sum(1 for h in history if h[me] == "STAR")
    own -= 0.25 * (my_star - (n - my_star)) / float(n)

    z = 0.9 * target + 0.8 * own
    p = 1.0 / (1.0 + math.exp(-2.0 * z))
    return max(0.22, min(0.78, p))
