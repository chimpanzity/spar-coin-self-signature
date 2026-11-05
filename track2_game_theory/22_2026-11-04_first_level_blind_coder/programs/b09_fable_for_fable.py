import math

def predict(history, seat):
    if not history:
        return 0.58  # mild first-listed-option bias toward STAR

    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    sign = 1.0 if seat == "p1" else -1.0  # matcher wants same as opponent, mismatcher opposite

    def v(c):
        return 1.0 if c == "STAR" else -1.0

    logit = 0.15  # small STAR bias

    # Opponent's recent frequency (last 5 rounds)
    recent = history[-5:]
    f = sum(1 for r in recent if r[opp] == "STAR") / len(recent)
    logit += sign * 1.2 * (f - 0.5) * 2

    # Level-1 prediction of opponent via win-stay / lose-shift
    last = history[-1]
    opp_won = (last["result"] == "Matcher") == (opp == "p1")
    pred_opp = last[opp] if opp_won else ("TRIANGLE" if last[opp] == "STAR" else "STAR")
    logit += sign * 0.5 * v(pred_opp)

    # Anti-streak tendency on own choices
    k = 1
    own_last = last[me]
    for r in reversed(history[:-1]):
        if r[me] == own_last:
            k += 1
        else:
            break
    if k >= 2:
        logit -= 0.35 * min(k - 1, 3) * v(own_last)

    # Slight tendency to switch own choice, stronger after losing
    i_won = not opp_won
    logit -= (0.15 if i_won else 0.4) * v(own_last)

    p = 1.0 / (1.0 + math.exp(-logit))
    return max(0.15, min(0.85, p))
