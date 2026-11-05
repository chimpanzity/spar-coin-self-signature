import math

def predict(history, seat):
    def s(c):
        return 1.0 if c == "STAR" else -1.0

    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    sign = 1.0 if seat == "p1" else -1.0  # matcher follows prediction, mismatcher opposes
    my_role = "Matcher" if seat == "p1" else "Mismatcher"

    n = len(history)
    # Base: slight bias toward the first-listed option (STAR)
    logit = 0.25 if n == 0 else 0.1
    if n == 0:
        return 1.0 / (1.0 + math.exp(-logit))

    last = history[-1]
    opp_last = s(last[opp])
    my_last = s(last[me])
    opp_won = (last["result"] != my_role)

    # LLM-style opponent model: win-stay / lose-shift for the opponent
    pred_opp = opp_last if opp_won else -opp_last
    logit += sign * 0.55 * pred_opp

    # Opponent overall frequency bias
    freq = sum(s(r[opp]) for r in history) / n
    logit += sign * 0.6 * freq

    # Opponent's own repeat tendency estimated from history
    if n >= 2:
        reps = 0
        for i in range(1, n):
            if history[i][opp] == history[i - 1][opp]:
                reps += 1
        rep_rate = reps / (n - 1)
        logit += sign * 0.8 * (rep_rate - 0.5) * opp_last

    # Own anti-streak tendency: avoid repeating own choice many times
    streak = 1
    for i in range(n - 2, -1, -1):
        if history[i][me] == last[me]:
            streak += 1
        else:
            break
    if streak >= 2:
        logit -= 0.35 * min(streak - 1, 3) * my_last

    # Own outcome: mild lose-shift tendency for self
    if not opp_won:
        logit += 0.15 * my_last
    else:
        logit -= 0.25 * my_last

    p = 1.0 / (1.0 + math.exp(-logit))
    return max(0.12, min(0.88, p))
