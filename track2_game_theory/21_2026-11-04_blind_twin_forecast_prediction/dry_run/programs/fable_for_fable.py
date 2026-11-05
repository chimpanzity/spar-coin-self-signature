def predict(history):
    if not history:
        return (0.6, 0.4)
    last = history[-1]
    flip = last['result'] == 'Mismatcher'
    return (0.4 if flip else 0.6, 0.6 if flip else 0.4)
