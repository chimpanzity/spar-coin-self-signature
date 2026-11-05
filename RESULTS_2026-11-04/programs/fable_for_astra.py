import math

def predict(history):
    S, T = "STAR", "TRIANGLE"
    n = len(history)
    if n == 0:
        # First round: LLM observer tends to anchor on STAR / the example JSON.
        return (0.68, 0.42)

    def ms(m):
        return 1.0 if m == S else -1.0

    # ---- Per-player naive tendency estimates (as an LLM observer might reason) ----
    def tendency(key, won_key):
        last = history[-1]
        lm = ms(last[key])
        won = (last["result"] == won_key)
        score = 0.0
        # win-stay / lose-shift heuristic, strongly used by LLM observers
        score += (1.1 if won else -0.9) * lm
        # frequency bias
        k = min(n, 8)
        rec = history[-k:]
        freq = sum(ms(r[key]) for r in rec) / k
        score += 0.6 * freq
        # streak detection: long same streak -> observer may expect a switch
        streak = 1
        for r in reversed(history[:-1]):
            if r[key] == last[key]:
                streak += 1
            else:
                break
        if streak >= 3:
            score -= 0.5 * lm
        # alternation detection
        if n >= 3:
            alt = all(history[-i][key] != history[-i-1][key] for i in range(1, 3))
            if alt:
                score -= 0.8 * lm
        return score

    s1 = tendency("p1", "Matcher")
    s2 = tendency("p2", "Mismatcher")

    # ---- Strategic layer: P1 tries to match P2's expected move, P2 tries to mismatch P1 ----
    f1 = 0.65 * s1 + 0.45 * s2
    f2 = 0.65 * s2 - 0.45 * s1

    # Slight STAR anchoring bias
    f1 += 0.15
    f2 += 0.05

    def sig(x):
        return 1.0 / (1.0 + math.exp(-x))

    p1 = sig(1.2 * f1)
    p2 = sig(1.2 * f2)
    p1 = min(0.9, max(0.1, p1))
    p2 = min(0.9, max(0.1, p2))
    return (p1, p2)
