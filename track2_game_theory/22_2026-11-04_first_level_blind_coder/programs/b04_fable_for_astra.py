def predict(history, seat):
    import math
    STAR, TRI = "STAR", "TRIANGLE"
    me = seat
    opp = "p2" if seat == "p1" else "p1"
    n = len(history)
    if n == 0:
        # First-option bias; mismatcher reasons opponent likely picks STAR and deviates
        return 0.60 if seat == "p1" else 0.44

    opp_moves = [r[opp] for r in history]
    my_moves = [r[me] for r in history]
    my_role = "Matcher" if seat == "p1" else "Mismatcher"
    opp_role = "Mismatcher" if seat == "p1" else "Matcher"

    # --- Model opponent's next move as the LLM would plausibly reason ---
    # 1. Frequency bias (smoothed)
    star_cnt = sum(1 for m in opp_moves if m == STAR)
    freq = (star_cnt + 1.0) / (n + 2.0)

    # 2. Switch / stay tendency, conditioned on opponent win/loss
    stay_win = [1, 1]  # [stays, total] with smoothing
    stay_loss = [1, 1]
    stay_all = [1, 2]
    for i in range(1, n):
        prev = history[i - 1]
        stayed = 1 if opp_moves[i] == opp_moves[i - 1] else 0
        stay_all[0] += stayed
        stay_all[1] += 1
        if prev["result"] == opp_role:
            stay_win[0] += stayed
            stay_win[1] += 1
        else:
            stay_loss[0] += stayed
            stay_loss[1] += 1
    last_opp = opp_moves[-1]
    opp_won_last = history[-1]["result"] == opp_role
    if opp_won_last:
        p_stay = stay_win[0] / float(stay_win[1])
        # default LLM prior: opponent who won tends to repeat
        p_stay = 0.5 * p_stay + 0.5 * 0.55
    else:
        p_stay = stay_loss[0] / float(stay_loss[1])
        # default prior: opponent who lost tends to switch
        p_stay = 0.5 * p_stay + 0.5 * 0.40
    p_stay = 0.6 * p_stay + 0.4 * (stay_all[0] / float(stay_all[1]))
    cond = p_stay if last_opp == STAR else 1.0 - p_stay

    # 3. Streak reasoning: long opponent streak -> LLM expects a break (or continuation)
    streak = 1
    for i in range(n - 2, -1, -1):
        if opp_moves[i] == last_opp:
            streak += 1
        else:
            break
    streak_adj = 0.0
    if streak >= 3:
        streak_adj = -0.10 if last_opp == STAR else 0.10  # expect break

    pred_opp_star = 0.35 * freq + 0.65 * cond + streak_adj
    pred_opp_star = min(0.9, max(0.1, pred_opp_star))

    # --- Own choice based on predicted opponent move ---
    if seat == "p1":
        p = pred_opp_star
    else:
        p = 1.0 - pred_opp_star

    # Soften: LLM mixes in "be unpredictable" reasoning
    p = 0.5 + 0.7 * (p - 0.5)

    # Self-streak aversion: LLMs dislike repeating own choice many times
    my_streak = 1
    for i in range(n - 2, -1, -1):
        if my_moves[i] == my_moves[-1]:
            my_streak += 1
        else:
            break
    if my_streak >= 2:
        shift = 0.06 * min(my_streak, 4)
        if my_moves[-1] == STAR:
            p -= shift
        else:
            p += shift

    # Slight lose-shift on own behaviour
    if history[-1]["result"] != my_role:
        if my_moves[-1] == STAR:
            p -= 0.05
        else:
            p += 0.05

    return min(0.88, max(0.12, p))
