def predict(history, seat):
    STAR, TRI = "STAR", "TRIANGLE"
    def flip(c):
        return TRI if c == STAR else STAR

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
    opp_won = not i_won

    votes = []  # (predicted choice, weight)

    # 1. Model opponent as win-stay / lose-shift, then best respond.
    opp_pred = opp_last if opp_won else flip(opp_last)
    br = opp_pred if seat == "p1" else flip(opp_pred)
    votes.append((br, 0.30))

    # 2. Model opponent as repeating their last move (simple persistence).
    br2 = opp_last if seat == "p1" else flip(opp_last)
    votes.append((br2, 0.15))

    # 3. Own win-stay / lose-shift tendency (stronger shift after loss).
    if i_won:
        votes.append((my_last, 0.10))
        votes.append((flip(my_last), 0.08))
    else:
        votes.append((flip(my_last), 0.20))

    # 4. Counter opponent's overall frequency.
    opp_star = sum(1 for h in history if h[opp] == STAR)
    opp_tri = n - opp_star
    if opp_star != opp_tri:
        opp_freq = STAR if opp_star > opp_tri else TRI
        br3 = opp_freq if seat == "p1" else flip(opp_freq)
        w = 0.10 * min(1.0, abs(opp_star - opp_tri) / max(2.0, n / 2.0))
        votes.append((br3, w))

    # 5. Anti-streak: break own runs of 3+.
    run = 1
    for h in reversed(history[:-1]):
        if h[me] == my_last:
            run += 1
        else:
            break
    if run >= 3:
        votes.append((flip(my_last), 0.15 + 0.05 * min(run - 3, 3)))
    elif run == 2:
        votes.append((flip(my_last), 0.06))

    # 6. Opponent alternation detection.
    if n >= 3:
        alt = all(history[k][opp] != history[k + 1][opp] for k in range(n - 3, n - 1))
        if alt:
            pred = flip(opp_last)
            votes.append((pred if seat == "p1" else flip(pred), 0.12))

    total_w = sum(w for _, w in votes)
    star_w = sum(w for c, w in votes if c == STAR)
    p = star_w / total_w if total_w > 0 else 0.5

    # Mild overall STAR bias and shrink toward 0.5
    p = 0.5 + (p - 0.5) * 0.7 + 0.03
    return max(0.08, min(0.92, p))
