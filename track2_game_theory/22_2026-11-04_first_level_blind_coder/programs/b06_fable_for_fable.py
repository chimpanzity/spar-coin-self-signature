import math

def predict(history, seat):
    n = len(history)
    if n == 0:
        # First round: mild bias toward the first-listed option (STAR)
        return 0.6 if seat == "p1" else 0.55

    me = "p1" if seat == "p1" else "p2"
    opp = "p2" if seat == "p1" else "p1"
    my_role = "Matcher" if seat == "p1" else "Mismatcher"

    def s(x):
        return 1.0 if x == "STAR" else -1.0

    opp_moves = [r[opp] for r in history]
    my_moves = [r[me] for r in history]
    results = [r["result"] for r in history]

    last_opp = opp_moves[-1]
    last_me = my_moves[-1]
    opp_won_last = (results[-1] != my_role)

    # --- Model of what Claude thinks the opponent will do next ---
    # 1) Win-stay / lose-shift attribution to the opponent
    wsls_pred = s(last_opp) if opp_won_last else -s(last_opp)

    # 2) Frequency tendency of the opponent (recent-weighted)
    freq = 0.0
    wsum = 0.0
    for i, m in enumerate(opp_moves):
        w = 0.8 ** (n - 1 - i)
        freq += w * s(m)
        wsum += w
    freq /= max(wsum, 1e-9)

    # 3) Alternation detection in opponent's moves
    alt = 0.0
    if n >= 2:
        switches = sum(1 for i in range(1, n) if opp_moves[i] != opp_moves[i-1])
        alt_rate = switches / (n - 1)
        # positive alt score -> predicts opponent switches
        alt = (alt_rate - 0.5) * 2.0
    alt_pred = -s(last_opp) * alt  # if opp tends to switch, predict flip

    # 4) Simple repeat-last recency
    rep_pred = s(last_opp)

    pred_opp = 0.9 * wsls_pred + 0.9 * freq + 0.7 * alt_pred + 0.3 * rep_pred

    # Claude's intended action given predicted opponent move
    if seat == "p1":
        act = pred_opp          # match
    else:
        act = -pred_opp         # mismatch

    logit = 0.75 * act

    # --- Own behavior adjustments ---
    # Reluctance to repeat the same choice many times in a row
    streak = 1
    for i in range(n - 2, -1, -1):
        if my_moves[i] == last_me:
            streak += 1
        else:
            break
    if streak >= 2:
        logit -= s(last_me) * min(0.35 * (streak - 1), 1.0)

    # Lose-shift tendency in own play
    if opp_won_last:
        logit -= 0.3 * s(last_me)
    else:
        logit += 0.15 * s(last_me)

    # If losing repeatedly, Claude may "break pattern" -> pulls toward 0.5
    recent_losses = sum(1 for r in results[-3:] if r != my_role)
    if recent_losses >= 3:
        logit *= 0.5

    # Small STAR bias as first-listed option
    logit += 0.1

    p = 1.0 / (1.0 + math.exp(-logit))
    return min(0.85, max(0.15, p))
