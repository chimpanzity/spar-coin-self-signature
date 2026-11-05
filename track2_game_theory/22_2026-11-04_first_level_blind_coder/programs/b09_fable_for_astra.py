def predict(history, seat):
    n = len(history)
    if n == 0:
        return 0.62 if seat == "p1" else 0.45

    me = seat
    opp = "p2" if seat == "p1" else "p1"
    matcher = (seat == "p1")

    opp_moves = [r[opp] for r in history]
    my_moves = [r[me] for r in history]

    # Opponent tendency estimates (overall and recent)
    overall = sum(1 for m in opp_moves if m == "STAR") / n
    recent = opp_moves[-3:]
    recent_rate = sum(1 for m in recent if m == "STAR") / len(recent)
    last_opp_star = 1.0 if opp_moves[-1] == "STAR" else 0.0

    # Opponent's own-switch tendency: probability opponent switches from last move
    if n >= 2:
        switches = sum(1 for i in range(1, n) if opp_moves[i] != opp_moves[i - 1])
        sw = (switches + 1) / (n - 1 + 2)
    else:
        sw = 0.5
    # predicted opponent next = last move with prob (1-sw)
    pred_from_switch = last_opp_star * (1 - sw) + (1 - last_opp_star) * sw

    # Combine predictions of opponent playing STAR
    ps = 0.35 * overall + 0.30 * recent_rate + 0.35 * pred_from_switch

    # Translate into own choice
    strength = min(1.0, 0.5 + 0.08 * n)  # model exploits more as evidence accumulates
    if matcher:
        p = 0.5 + strength * (ps - 0.5)
    else:
        p = 0.5 - strength * (ps - 0.5)

    # Win-stay / lose-shift adjustment on own last move
    last = history[-1]
    won = (last["result"] == "Matcher") == matcher
    my_last_star = my_moves[-1] == "STAR"
    adj = 0.10 if won else -0.14
    if my_last_star:
        p += adj
    else:
        p -= adj

    # Anti-streak: LLMs dislike repeating the same choice many times
    streak = 1
    for i in range(n - 2, -1, -1):
        if my_moves[i] == my_moves[-1]:
            streak += 1
        else:
            break
    if streak >= 2:
        shift = min(0.25, 0.08 * (streak - 1))
        if my_last_star:
            p -= shift
        else:
            p += shift

    # Mild baseline preference for the first-listed option
    p += 0.03

    return max(0.05, min(0.95, p))
