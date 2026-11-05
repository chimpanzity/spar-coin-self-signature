import math

def predict(history, seat):
    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    n = len(history)
    if n == 0:
        return 0.6  # first-listed option bias

    my_moves = [r[me] for r in history]
    opp_moves = [r[opp] for r in history]
    results = [r["result"] for r in history]
    my_role = "Matcher" if seat == "p1" else "Mismatcher"
    last_me = my_moves[-1]
    last_opp = opp_moves[-1]
    won_last = (results[-1] == my_role)

    def sgn(m):
        return 1.0 if m == "STAR" else -1.0

    logit = 0.0

    # 1. Own switch tendency (level-1 reasoning -> switch; lose-shift stronger)
    p_switch = 0.66 if not won_last else 0.57
    logit += -sgn(last_me) * math.log(p_switch / (1 - p_switch))

    # 2. Anti-streak on own choices
    k = 1
    for m in reversed(my_moves[:-1]):
        if m == last_me:
            k += 1
        else:
            break
    if k >= 2:
        logit += -sgn(last_me) * 0.35 * (k - 1)

    # 3. Balancing of own overall frequency
    star_frac = sum(1 for m in my_moves if m == "STAR") / n
    logit += -(star_frac - 0.5) * 1.5

    # 4. Opponent modelling: predict opponent via empirical stay rate (shrunk)
    stays = 0
    trans = 0
    for i in range(1, n):
        trans += 1
        if opp_moves[i] == opp_moves[i - 1]:
            stays += 1
    stay_rate = (stays + 1.0) / (trans + 2.0)
    # opponent lose-shift adjustment
    opp_role = "Mismatcher" if seat == "p1" else "Matcher"
    opp_won = (results[-1] == opp_role)
    stay_rate = 0.6 * stay_rate + 0.4 * (0.5 if opp_won else 0.4)
    p_opp_star = stay_rate if last_opp == "STAR" else 1 - stay_rate
    p_opp_star = min(max(p_opp_star, 0.05), 0.95)
    opp_logit = math.log(p_opp_star / (1 - p_opp_star))
    if seat == "p1":
        logit += 0.5 * opp_logit
    else:
        logit -= 0.5 * opp_logit

    # 5. Mild recency: opponent's last move (naive matching) for matcher
    if seat == "p1":
        logit += 0.15 * sgn(last_opp)
    else:
        logit -= 0.15 * sgn(last_opp)

    p = 1.0 / (1.0 + math.exp(-logit))
    return min(max(p, 0.18), 0.82)
