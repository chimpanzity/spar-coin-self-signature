def predict(history, seat):
    n = len(history)
    if n == 0:
        # First-move bias: STAR is listed first; matcher leans STAR, mismatcher leans away.
        return 0.58 if seat == "p1" else 0.42

    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    my_win = "Matcher" if seat == "p1" else "Mismatcher"

    def star_prob_opp_next():
        # Blend of several naive opponent models that an LLM tends to apply.
        last = history[-1]
        opp_last = last[opp]
        opp_won = (last["result"] != my_win)
        # 1) opponent repeats last move
        rep = 1.0 if opp_last == "STAR" else 0.0
        # 2) opponent win-stay / lose-shift
        if opp_won:
            wsls = rep
        else:
            wsls = 1.0 - rep
        # 3) frequency bias over recent window
        window = history[-6:]
        stars = sum(1 for r in window if r[opp] == "STAR")
        freq = (stars + 1.0) / (len(window) + 2.0)
        # 4) alternation detection
        alt = 0.5
        if n >= 3:
            seq = [r[opp] for r in history[-4:]]
            alts = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
            if alts == len(seq) - 1:
                alt = 1.0 - rep
            elif alts == 0:
                alt = rep
        # streak strengthens "they'll break the streak" belief for LLMs
        streak = 1
        for i in range(n - 2, -1, -1):
            if history[i][opp] == opp_last:
                streak += 1
            else:
                break
        p = 0.25 * rep + 0.30 * wsls + 0.20 * freq + 0.25 * alt
        if streak >= 3:
            # LLM often predicts the opponent will finally switch
            p = 0.6 * (1.0 - rep) + 0.4 * p
        return p

    p_opp_star = star_prob_opp_next()
    # Claude's best response to its belief
    if seat == "p1":
        p_star = p_opp_star
    else:
        p_star = 1.0 - p_opp_star

    # Own win-stay / lose-shift tendency
    last = history[-1]
    my_last = last[me]
    i_won = (last["result"] == my_win)
    if i_won:
        own = 1.0 if my_last == "STAR" else 0.0
        w = 0.25
    else:
        own = 0.0 if my_last == "STAR" else 1.0
        w = 0.35
    p_star = (1 - w) * p_star + w * own

    # Shrink toward 0.5 for hedging / deliberate randomization
    p_star = 0.5 + (p_star - 0.5) * 0.7
    return max(0.15, min(0.85, p_star))
