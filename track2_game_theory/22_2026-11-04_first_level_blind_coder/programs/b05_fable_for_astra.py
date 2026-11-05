def predict(history, seat):
    STAR = "STAR"
    n = len(history)
    if n == 0:
        return 0.62 if seat == "p1" else 0.56

    me = seat
    opp = "p2" if seat == "p1" else "p1"
    my_role_win = "Matcher" if seat == "p1" else "Mismatcher"

    opp_choices = [r[opp] for r in history]
    my_choices = [r[me] for r in history]
    last = history[-1]
    opp_last = last[opp]
    my_last = last[me]
    i_won = (last["result"] == my_role_win)

    # --- estimate what the LLM thinks the opponent will do next (prob STAR) ---
    # frequency component (LLMs love counting)
    star_cnt = sum(1 for c in opp_choices if c == STAR)
    freq = (star_cnt + 1.0) / (n + 2.0)
    # recency weighted frequency
    w = 0.0
    ws = 0.0
    for k, c in enumerate(opp_choices):
        wt = 0.75 ** (n - 1 - k)
        w += wt
        ws += wt * (1.0 if c == STAR else 0.0)
    rfreq = ws / w if w > 0 else 0.5

    # streak / last-move component
    streak = 1
    for c in reversed(opp_choices[:-1]):
        if c == opp_last:
            streak += 1
        else:
            break
    if i_won:
        # opponent lost -> LLM expects opponent to switch
        repeat_p = 0.40
    else:
        # opponent won -> LLM expects opponent to stay
        repeat_p = 0.64
    if streak >= 3:
        # long streak: "they'll keep doing it" vs "they're due to switch" -> mixed, slight repeat
        repeat_p = 0.5 * repeat_p + 0.5 * 0.55
    last_comp = repeat_p if opp_last == STAR else 1.0 - repeat_p

    # alternation detection (LLMs notice ABAB patterns)
    alt_comp = None
    if n >= 4:
        alt = all(opp_choices[k] != opp_choices[k + 1] for k in range(n - 4, n - 1))
        if alt:
            alt_comp = 0.25 if opp_last == STAR else 0.75

    q = 0.45 * last_comp + 0.25 * freq + 0.30 * rfreq
    if alt_comp is not None:
        q = 0.6 * alt_comp + 0.4 * q

    # map to own choice
    if seat == "p1":
        target = q
    else:
        target = 1.0 - q

    # win-stay / lose-shift bias on own last choice
    own_bias = 0.0
    if i_won:
        own_bias = 0.08 if my_last == STAR else -0.08
    else:
        own_bias = -0.08 if my_last == STAR else 0.08
    target += own_bias

    # aversion to long self-streaks
    mstreak = 1
    for c in reversed(my_choices[:-1]):
        if c == my_last:
            mstreak += 1
        else:
            break
    if mstreak >= 3:
        target += -0.10 if my_last == STAR else 0.10

    # shrink toward 0.5 (second-level reasoning noise)
    p = 0.5 + 0.75 * (target - 0.5)
    # slight general STAR bias (first-listed option)
    p += 0.02
    if p < 0.08:
        p = 0.08
    if p > 0.92:
        p = 0.92
    return p
