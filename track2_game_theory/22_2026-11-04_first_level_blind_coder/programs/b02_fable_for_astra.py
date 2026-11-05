def predict(history, seat):
    STAR, TRI = "STAR", "TRIANGLE"
    n = len(history)
    if n == 0:
        # First-listed option bias; matcher slightly more inclined to STAR
        return 0.64 if seat == "p1" else 0.58

    me, opp = ("p1", "p2") if seat == "p1" else ("p2", "p1")
    my = [h[me] for h in history]
    op = [h[opp] for h in history]
    results = [h["result"] for h in history]
    opp_won_last = (results[-1] == ("Mismatcher" if seat == "p1" else "Matcher"))
    i_won_last = not opp_won_last

    # --- Model the LLM's prediction of the opponent's next move ---
    # Attribution: win-stay / lose-shift, plus alternation detection.
    p_opp_star = 0.5
    last = op[-1]
    stay_prob = 0.60 if opp_won_last else 0.40
    if n >= 2:
        if op[-1] != op[-2]:
            stay_prob -= 0.08  # alternation pattern -> expect continued alternation
        else:
            stay_prob += 0.05  # repeat pattern -> expect continued repeat
    if n >= 3 and op[-1] == op[-2] == op[-3]:
        stay_prob -= 0.10  # LLM often expects a streak to break
    # frequency component
    freq = op.count(STAR) / n
    p_opp_star = stay_prob if last == STAR else 1.0 - stay_prob
    p_opp_star = 0.75 * p_opp_star + 0.25 * freq

    # --- Translate into own action ---
    if seat == "p1":
        p = p_opp_star          # matcher plays predicted opponent choice
    else:
        p = 1.0 - p_opp_star    # mismatcher plays opposite

    # Shrink confidence (LLMs sometimes do level-2 flips / hedge)
    p = 0.5 + (p - 0.5) * 0.7

    # Own-streak aversion: tendency to switch after repeating oneself
    if n >= 2 and my[-1] == my[-2]:
        shift = 0.08 if n < 3 or my[-3] != my[-1] else 0.14
        if my[-1] == STAR:
            p -= shift
        else:
            p += shift

    # Win-stay tendency of the LLM itself (mild)
    if i_won_last:
        p += 0.05 if my[-1] == STAR else -0.05
    else:
        p += -0.04 if my[-1] == STAR else 0.04

    # Slight global STAR bias
    p += 0.02

    return max(0.08, min(0.92, p))
