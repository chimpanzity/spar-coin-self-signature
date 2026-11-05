import math

def predict(history):
    def sig(x):
        return 1.0 / (1.0 + math.exp(-x))

    n = len(history)
    if n == 0:
        # Anchoring on the example JSON and first-listed option.
        return (0.62, 0.42)

    def s(v):
        return 1.0 if v == "STAR" else -1.0

    def player_logit(key, is_matcher):
        last = history[-1]
        last_choice = s(last[key])
        won = (last["result"] == ("Matcher" if is_matcher else "Mismatcher"))

        # 1) Default win-stay / lose-shift reasoning (equivalent to level-1 best response).
        wsls = last_choice if won else -last_choice

        # 2) Empirical stay tendency conditioned on win/loss, smoothed.
        stay_w = [1.0, 1.0]  # [stays, total] after wins
        stay_l = [1.0, 1.0]  # after losses
        for i in range(1, n):
            prev, cur = history[i - 1], history[i]
            pw = (prev["result"] == ("Matcher" if is_matcher else "Mismatcher"))
            stayed = 1.0 if prev[key] == cur[key] else 0.0
            if pw:
                stay_w[0] += stayed; stay_w[1] += 1.0
            else:
                stay_l[0] += stayed; stay_l[1] += 1.0
        if won:
            p_stay = (stay_w[0] + 0.5) / (stay_w[1] + 1.0)
            cnt = stay_w[1] - 1.0
        else:
            p_stay = (stay_l[0] + 0.3) / (stay_l[1] + 1.0)
            cnt = stay_l[1] - 1.0
        emp = (2.0 * p_stay - 1.0) * last_choice
        emp_w = min(1.0, cnt / 4.0)

        # 3) Overall frequency bias.
        star_frac = sum(1 for h in history if h[key] == "STAR") / float(n)
        freq = 2.0 * star_frac - 1.0

        # 4) Streak / alternation pattern detection.
        streak = 1
        for i in range(n - 1, 0, -1):
            if history[i][key] == history[i - 1][key]:
                streak += 1
            else:
                break
        alt = 1
        for i in range(n - 1, 0, -1):
            if history[i][key] != history[i - 1][key]:
                alt += 1
            else:
                break
        pattern = 0.0
        if streak >= 3:
            pattern += 0.35 * min(streak - 2, 3) * last_choice   # expect persistence
        if alt >= 3:
            pattern += 0.45 * min(alt - 2, 3) * (-last_choice)  # expect alternation

        lg = 0.9 * wsls + 1.4 * emp_w * emp + 0.6 * freq + pattern
        if n == 1:
            lg += 0.15  # slight STAR anchoring early
        return lg

    p1 = sig(player_logit("p1", True))
    p2 = sig(player_logit("p2", False))
    lo, hi = 0.08, 0.92
    p1 = min(hi, max(lo, p1))
    p2 = min(hi, max(lo, p2))
    return (p1, p2)
