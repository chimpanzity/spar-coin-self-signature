def predict(history, seat):
    n = len(history)
    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    my_role = "Matcher" if seat == "p1" else "Mismatcher"
    if n == 0:
        return 0.60 if seat == "p1" else 0.55

    def s(v):  # +1 for STAR, -1 for TRIANGLE
        return 1.0 if v == "STAR" else -1.0

    last = history[-1]
    opp_last = s(last[opp])
    opp_won_last = (last["result"] != my_role)

    # Predicted opponent next move (signed toward STAR)
    pred = 0.0
    # Win-stay / lose-shift assumption about opponent
    pred += 0.45 * (opp_last if opp_won_last else -opp_last)
    # Recent frequency of opponent
    recent = history[-5:]
    freq = sum(s(r[opp]) for r in recent) / len(recent)
    pred += 0.35 * freq
    # Opponent streak: LLM expects "they'll break the streak" after 3+
    streak = 1
    for r in reversed(history[:-1]):
        if s(r[opp]) == opp_last:
            streak += 1
        else:
            break
    if streak >= 3:
        pred -= 0.4 * opp_last
    # Alternation detection in opponent
    if n >= 3:
        alt = all(s(history[-i][opp]) != s(history[-i - 1][opp]) for i in range(1, 3))
        if alt:
            pred += 0.4 * (-opp_last)

    pred = max(-1.0, min(1.0, pred))
    # My desired move
    desire = pred if seat == "p1" else -pred

    # Own streak avoidance
    my_last = s(last[me])
    mstreak = 1
    for r in reversed(history[:-1]):
        if s(r[me]) == my_last:
            mstreak += 1
        else:
            break
    if mstreak >= 2:
        desire -= 0.25 * my_last * min(mstreak - 1, 3)
    # Own win-stay / lose-shift tendency
    i_won = (last["result"] == my_role)
    desire += 0.2 * (my_last if i_won else -my_last)

    p = 0.5 + 0.18 * desire + 0.02  # slight STAR bias
    return max(0.15, min(0.85, p))
