def predict(history, seat):
    n = len(history)
    if n == 0:
        # First-listed option bias for LLMs
        return 0.62 if seat == "p1" else 0.58

    me = seat
    opp = "p2" if seat == "p1" else "p1"
    my_win = "Matcher" if seat == "p1" else "Mismatcher"

    def s(x):
        return 1.0 if x == "STAR" else 0.0

    # --- Estimate opponent's next move ---
    # Opponent's switch tendency conditioned on their win/loss
    sw_lose = [1.0, 1.0]  # pseudo counts: switches, total (prior ~ lean switch)
    sw_lose = [1.4, 2.0]
    sw_win = [1.0, 2.0]
    for i in range(1, n):
        prev, cur = history[i - 1], history[i]
        switched = 1.0 if prev[opp] != cur[opp] else 0.0
        opp_won_prev = (prev["result"] != my_win)
        if opp_won_prev:
            sw_win[0] += switched; sw_win[1] += 1
        else:
            sw_lose[0] += switched; sw_lose[1] += 1
    last = history[-1]
    opp_last_star = s(last[opp])
    opp_won_last = (last["result"] != my_win)
    p_sw = (sw_win[0] / sw_win[1]) if opp_won_last else (sw_lose[0] / sw_lose[1])
    p_opp_switch_based = opp_last_star * (1 - p_sw) + (1 - opp_last_star) * p_sw

    # Opponent frequency (recent weighted)
    wsum = 0.0; ssum = 0.0
    for i, r in enumerate(history):
        w = 0.8 ** (n - 1 - i)
        wsum += w; ssum += w * s(r[opp])
    p_opp_freq = (ssum + 0.5) / (wsum + 1.0)

    p_opp = 0.6 * p_opp_switch_based + 0.4 * p_opp_freq

    # Best response as perceived by an LLM
    if seat == "p1":
        target = p_opp
    else:
        target = 1 - p_opp
    signal = (target - 0.5) * 0.7  # moderate confidence

    # --- Own habit: lose-shift, mild win-shift ---
    my_last_star = s(last[me])
    i_won = (last["result"] == my_win)
    p_my_switch = 0.45 if i_won else 0.68
    p_habit = my_last_star * (1 - p_my_switch) + (1 - my_last_star) * p_my_switch

    p = 0.5 + signal
    p = 0.65 * p + 0.35 * p_habit
    p += 0.03  # slight STAR bias
    return max(0.15, min(0.85, p))
