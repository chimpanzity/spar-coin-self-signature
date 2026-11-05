def predict(history, seat):
    if not history:
        return 0.5
    last = history[-1][seat]
    stay = 0.487
    return stay if last == 'STAR' else 1 - stay
