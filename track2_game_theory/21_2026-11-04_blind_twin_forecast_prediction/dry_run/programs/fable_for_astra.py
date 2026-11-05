import math

def predict(history):
    n = len(history)
    s1 = sum(r['p1'] == 'STAR' for r in history)
    s2 = sum(r['p2'] == 'STAR' for r in history)
    return ((s1 + 1) / (n + 2), (s2 + 1) / (n + 2))
