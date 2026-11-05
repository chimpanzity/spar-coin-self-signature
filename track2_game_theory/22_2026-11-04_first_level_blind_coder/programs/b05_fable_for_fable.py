def predict(history, seat):
    n = len(history)
    if n == 0:
        # First-listed option bias, mild.
        return 0.58 if seat == "p1" else 0.55

    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    my_role = "Matcher" if seat == "p1" else "Mismatcher"

    def other(c):
        return "TRIANGLE" if c == "STAR" else "STAR"

    # --- Estimate how Claude would predict the opponent's next move ---
    # 1. Opponent conditional transitions: after a win / after a loss, stay or switch?
    stay_after_win = [0.0, 0.0]   # [stays, total]
    stay_after_loss = [0.0, 0.0]
    for i in range(1, n):
        prev, cur = history[i - 1], history[i]
        opp_won_prev = (prev["result"] == ("Matcher" if opp == "p1" else "Mismatcher"))
        stayed = prev[opp] == cur[opp]
        bucket = stay_after_win if opp_won_prev else stay_after_loss
        bucket[1] += 1
        if stayed:
            bucket[0] += 1

    last = history[-1]
    opp_won_last = (last["result"] == ("Matcher" if opp == "p1" else "Mismatcher"))
    # priors: LLM assumes opponents tend to switch after losing, slightly stay after winning
    if opp_won_last:
        prior_stay, w = 0.5, 2.0
        s, t = stay_after_win
    else:
        prior_stay, w = 0.4, 2.0
        s, t = stay_after_loss
    p_stay = (s + prior_stay * w) / (t + w)

    # 2. Overall opponent base rate of STAR (Claude notices imbalance)
    opp_star = sum(1 for h in history if h[opp] == "STAR")
    base_star = (opp_star + 1.0) / (n + 2.0)

    # 3. Opponent streak: long streaks make Claude expect either continuation or a break
    streak = 1
    for i in range(n - 1, 0, -1):
        if history[i][opp] == history[i - 1][opp]:
            streak += 1
        else:
            break

    p_opp_star_trans = p_stay if last[opp] == "STAR" else 1.0 - p_stay
    pred_opp_star = 0.6 * p_opp_star_trans + 0.4 * base_star
    if streak >= 3:
        # Claude typically expects a streak to be broken ("they'll switch now")
        if last[opp] == "STAR":
            pred_opp_star = 0.5 * pred_opp_star + 0.5 * 0.35
        else:
            pred_opp_star = 0.5 * pred_opp_star + 0.5 * 0.65

    # --- Translate prediction into Claude's choice ---
    if my_role == "Matcher":
        p_star = pred_opp_star
    else:
        p_star = 1.0 - pred_opp_star

    # Sharpen: Claude commits to its reasoning with moderate confidence
    p_star = 0.5 + (p_star - 0.5) * 1.3

    # --- Own-streak avoidance: Claude dislikes repeating the same move too long ---
    my_streak = 1
    for i in range(n - 1, 0, -1):
        if history[i][me] == history[i - 1][me]:
            my_streak += 1
        else:
            break
    if my_streak >= 2:
        pull = min(0.08 * (my_streak - 1), 0.25)
        if last[me] == "STAR":
            p_star -= pull
        else:
            p_star += pull

    # Lost last round -> stronger urge to change something
    i_won_last = (last["result"] == my_role)
    if not i_won_last:
        if last[me] == "STAR":
            p_star -= 0.06
        else:
            p_star += 0.06

    return max(0.12, min(0.88, p_star))
