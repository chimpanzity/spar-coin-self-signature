def predict(history):
    if not history:
        return (0.5, 0.5)
    last = history[-1]
    return (0.65 if last['p1'] == 'STAR' else 0.35, 0.65 if last['p2'] == 'STAR' else 0.35)
