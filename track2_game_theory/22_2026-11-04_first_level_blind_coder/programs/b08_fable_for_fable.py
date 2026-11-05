import math

def predict(history, seat):
    n = len(history)
    me, opp = ("p1", "p2") if seat == "p1" else ("p2", "p1")
    matcher = (seat == "p1")
    if n == 0:
        return 0.6 if matcher else 0.45

    def v(c):
        return 1.0 if c == "STAR" else -1.0

    last = history[-1]
    opp_last = v(last[opp])
    my_last = v(last[me])
    i_won = (last["result"] == ("Matcher" if matcher else "Mismatcher"))

    # --- predicted opponent next move (positive = STAR) ---
    pred = 0.0
    # opponent lose-shift / win-stay tendency as perceived by an LLM
    if i_won:
        pred += -0.45 * opp_last  # opponent lost -> likely switches
    else:
        pred += 0.15 * opp_last   # opponent won -> maybe stays, but may anticipate
    # opponent frequency bias, recency weighted
    tot = 0.0
    wsum = 0.0
    for k, r in enumerate(history):
        w = 0.8 ** (n - 1 - k)
        tot += w * v(r[opp])
        wsum += w
    freq = tot / wsum if wsum else 0.0
    pred += 0.6 * freq
    # opponent streak: LLM extrapolates streaks (or expects a break if long)
    streak = 1
    for k in range(n - 2, -1, -1):
        if history[k][opp] == last[opp]:
            streak += 1
        else:
            break
    if streak >= 2:
        pred += (0.25 if streak <= 3 else -0.15) * opp_last
    # opponent alternation detection
    if n >= 3:
        alt = all(history[k][opp] != history[k + 1][opp] for k in range(n - 3, n - 1))
        if alt:
            pred += -0.35 * opp_last

    score = pred if matcher else -pred

    # --- own behavioural biases ---
    if i_won:
        score += -0.12 * my_last   # slight tendency to switch anyway
    else:
        score += -0.3 * my_last    # lose-shift
    my_streak = 1
    for k in range(n - 2, -1, -1):
        if history[k][me] == last[me]:
            my_streak += 1
        else:
            break
    if my_streak >= 3:
        score += -0.25 * my_last   # avoid long repetition
    # overall own balance aversion
    my_tot = sum(v(r[me]) for r in history) / n
    score += -0.3 * my_tot

    p = 0.5 + 0.5 * math.tanh(score)
    return max(0.15, min(0.85, p))
