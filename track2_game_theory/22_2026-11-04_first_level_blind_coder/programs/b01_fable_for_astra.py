import math

def predict(history, seat):
    def val(c):
        return 1.0 if c == "STAR" else 0.0

    n = len(history)
    if n == 0:
        # First-listed option bias
        return 0.62 if seat == "p1" else 0.58

    me, opp = ("p1", "p2") if seat == "p1" else ("p2", "p1")
    my_role = "Matcher" if seat == "p1" else "Mismatcher"

    last = history[-1]
    my_last = last[me]
    opp_last = last[opp]
    i_won = (last["result"] == my_role)

    # logit for choosing STAR
    logit = 0.0

    # 1. Alternation / lose-shift tendency relative to own last choice
    switch_p = 0.66 if not i_won else 0.56
    stay_star = 1.0 if my_last == "STAR" else 0.0
    p_from_self = switch_p * (1 - stay_star) + (1 - switch_p) * stay_star
    logit += math.log(p_from_self / (1 - p_from_self))

    # 2. Opponent modeling: predict opponent's next move
    # win-stay / lose-shift attributed to opponent
    opp_won = not i_won
    p_opp_repeat = 0.6 if opp_won else 0.42

    # opponent streak amplifies expectation of repetition
    streak = 1
    for r in range(n - 2, -1, -1):
        if history[r][opp] == opp_last:
            streak += 1
        else:
            break
    if streak >= 3:
        p_opp_repeat = min(0.85, p_opp_repeat + 0.12 * (streak - 2))

    # opponent frequency
    opp_star_cnt = sum(val(h[opp]) for h in history)
    freq = (opp_star_cnt + 1.0) / (n + 2.0)

    p_opp_star_rep = p_opp_repeat * val(opp_last) + (1 - p_opp_repeat) * (1 - val(opp_last))
    w_freq = min(0.5, n / 20.0)
    p_opp_star = (1 - w_freq) * p_opp_star_rep + w_freq * freq
    p_opp_star = min(0.9, max(0.1, p_opp_star))

    # Matcher plays predicted, Mismatcher plays opposite
    if seat == "p1":
        p_target = p_opp_star
    else:
        p_target = 1 - p_opp_star
    logit += 0.9 * math.log(p_target / (1 - p_target))

    # 3. Mild intrinsic STAR bias
    logit += 0.1

    p = 1 / (1 + math.exp(-logit))
    return min(0.85, max(0.15, p))
