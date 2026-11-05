def predict(history, seat):
    STAR, TRI = "STAR", "TRIANGLE"
    n = len(history)
    me = seat
    opp = "p2" if seat == "p1" else "p1"
    base_star = 0.58  # first-listed option bias

    if n == 0:
        return base_star

    def s(x):
        return 1.0 if x == STAR else 0.0

    opp_moves = [r[opp] for r in history]
    my_moves = [r[me] for r in history]
    my_role = "Matcher" if me == "p1" else "Mismatcher"
    my_wins = [r["result"] == my_role for r in history]
    opp_wins = [not w for w in my_wins]

    # --- Model the LLM's prediction of the opponent ---
    # Recent-weighted frequency
    wsum, tot = 0.0, 0.0
    for i, m in enumerate(opp_moves):
        w = 0.8 ** (n - 1 - i)
        wsum += w * s(m); tot += w
    freq_star = (wsum + 0.5) / (tot + 1.0)

    # Opponent stay/switch tendency (recent weighted)
    stay_w, trans_w = 0.0, 0.0
    for i in range(1, n):
        w = 0.8 ** (n - 1 - i)
        trans_w += w
        if opp_moves[i] == opp_moves[i - 1]:
            stay_w += w
    stay_rate = (stay_w + 0.5) / (trans_w + 1.0)
    last_opp = s(opp_moves[-1])
    trans_pred = stay_rate * last_opp + (1 - stay_rate) * (1 - last_opp)

    # Opponent win-stay / lose-shift
    ws_num = ws_den = ls_num = ls_den = 0.0
    for i in range(1, n):
        w = 0.8 ** (n - 1 - i)
        stayed = opp_moves[i] == opp_moves[i - 1]
        if opp_wins[i - 1]:
            ws_den += w; ws_num += w * stayed
        else:
            ls_den += w; ls_num += w * stayed
    if opp_wins[-1]:
        st = (ws_num + 0.55) / (ws_den + 1.0)
    else:
        st = (ls_num + 0.4) / (ls_den + 1.0)
    wsls_pred = st * last_opp + (1 - st) * (1 - last_opp)

    # Streak detection: strong recent streak -> LLM expects continuation or break
    streak = 1
    for i in range(n - 1, 0, -1):
        if opp_moves[i] == opp_moves[i - 1]:
            streak += 1
        else:
            break
    p_opp = 0.3 * freq_star + 0.35 * trans_pred + 0.35 * wsls_pred
    if streak >= 3:
        # LLMs tend to expect streak continuation
        p_opp = 0.6 * p_opp + 0.4 * last_opp

    pattern_choice = p_opp if me == "p1" else 1.0 - p_opp

    # --- Own win-stay/lose-shift habit ---
    mws_num = mws_den = mls_num = mls_den = 0.0
    for i in range(1, n):
        stayed = my_moves[i] == my_moves[i - 1]
        if my_wins[i - 1]:
            mws_den += 1; mws_num += stayed
        else:
            mls_den += 1; mls_num += stayed
    if my_wins[-1]:
        mst = (mws_num + 0.55 * 2) / (mws_den + 2.0)
    else:
        mst = (mls_num + 0.35 * 2) / (mls_den + 2.0)
    last_me = s(my_moves[-1])
    own_pred = mst * last_me + (1 - mst) * (1 - last_me)

    # --- Self-balancing: LLMs avoid looking skewed ---
    my_star_frac = sum(s(m) for m in my_moves) / n
    balance = 0.5 + (0.5 - my_star_frac) * 0.6

    p = 0.45 * pattern_choice + 0.25 * own_pred + 0.15 * balance + 0.15 * base_star
    return max(0.15, min(0.85, p))
