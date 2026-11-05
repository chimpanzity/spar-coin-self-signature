import math

def predict(history, seat):
    n = len(history)
    if n == 0:
        return 0.62 if seat == "p1" else 0.42

    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    my_role = "Matcher" if seat == "p1" else "Mismatcher"

    last = history[-1]
    my_last = last[me]
    opp_last = last[opp]
    won_last = (last["result"] == my_role)

    def sgn(choice):  # +1 for STAR, -1 for TRIANGLE
        return 1.0 if choice == "STAR" else -1.0

    s = 0.0  # log-odds toward STAR

    # General tendency to switch own choice (stronger after a loss)
    if won_last:
        s += -0.25 * sgn(my_last)
    else:
        s += -0.75 * sgn(my_last)

    # Own streak: avoid long runs of the same symbol
    streak = 0
    for r in reversed(history):
        if r[me] == my_last:
            streak += 1
        else:
            break
    if streak >= 2:
        s += -0.35 * (streak - 1) * sgn(my_last)

    # Opponent modeling: opponent assumed lose-shift / win-stay (weakly)
    opp_won = not won_last
    if opp_won:
        pred_opp = sgn(opp_last) * 0.5
    else:
        pred_opp = -sgn(opp_last) * 0.8
    if seat == "p1":
        s += 0.6 * pred_opp
    else:
        s += -0.6 * pred_opp

    # Opponent frequency bias over recent rounds
    recent = history[-6:]
    bias = sum(sgn(r[opp]) for r in recent) / len(recent)
    if seat == "p1":
        s += 0.5 * bias
    else:
        s += -0.5 * bias

    # Opponent alternation detection
    if n >= 3:
        alt = 0
        for i in range(1, min(n, 5)):
            if history[-i][opp] != history[-i - 1][opp]:
                alt += 1
            else:
                alt -= 1
        if alt >= 3:
            pred = -sgn(opp_last)
            s += (0.5 if seat == "p1" else -0.5) * pred
        elif alt <= -3:
            pred = sgn(opp_last)
            s += (0.5 if seat == "p1" else -0.5) * pred

    # Slight baseline STAR preference
    s += 0.1

    p = 1.0 / (1.0 + math.exp(-s))
    return max(0.15, min(0.85, p))
