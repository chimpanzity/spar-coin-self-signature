def predict(history, seat):
    if not history:
        return 0.65 if seat == "p1" else 0.6
    me = seat
    opp = "p2" if seat == "p1" else "p1"
    my_moves = [r[me] for r in history]
    opp_moves = [r[opp] for r in history]
    my_role = "Matcher" if seat == "p1" else "Mismatcher"
    won_last = history[-1]["result"] == my_role
    sign = 1.0 if seat == "p1" else -1.0  # matcher moves toward predicted opp; mismatcher away

    def tostar(m):
        return 1.0 if m == "STAR" else -1.0

    # Predict opponent's next move (value in [-1,1], +1 = STAR)
    pred = 0.0
    n = len(opp_moves)
    last = opp_moves[-1]
    # streak detection
    k = 1
    while k < n and opp_moves[-1 - k] == last:
        k += 1
    if k >= 2:
        pred += 0.35 * tostar(last) * min(k, 4) / 2.0
    # alternation detection
    if n >= 3 and all(opp_moves[-i] != opp_moves[-i - 1] for i in range(1, 3)):
        pred += 0.4 * -tostar(last)
    # frequency bias (recent window)
    win = opp_moves[-6:]
    freq = sum(tostar(m) for m in win) / len(win)
    pred += 0.3 * freq
    # opponent win-stay/lose-shift tendency
    opp_won_last = not won_last
    if opp_won_last:
        pred += 0.15 * tostar(last)
    else:
        pred -= 0.2 * tostar(last)
    pred = max(-1.0, min(1.0, pred))

    p = 0.5 + 0.22 * sign * pred
    # own tendency: shift after loss, slight shift after win
    mine = tostar(my_moves[-1])
    if not won_last:
        p -= 0.22 * mine
    else:
        p -= 0.06 * mine
    # mild overall STAR bias
    p += 0.02
    return max(0.12, min(0.88, p))
