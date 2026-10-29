"""Phenotype features of one 10-roll sequence (handoff section 5)."""

from __future__ import annotations

import collections
from typing import Dict, List

# Prespecified classifier inputs: six face proportions + switch fraction + longest run + number of distinct faces.
CLASSIFIER_FEATURES = ["p1", "p2", "p3", "p4", "p5", "p6", "switch_frac", "max_run", "n_distinct"]


def features(faces: List[int]) -> Dict[str, float]:
    n = len(faces)
    c = collections.Counter(faces)
    switches = sum(a != b for a, b in zip(faces, faces[1:]))
    run = best = 1
    for a, b in zip(faces, faces[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    out = {f"count{f}": c[f] for f in range(1, 7)}
    out.update({f"p{f}": c[f] / n for f in range(1, 7)})
    out.update(mean_face=sum(faces) / n, switch_frac=switches / (n - 1), repeat_frac=1 - switches / (n - 1),
               max_run=best, n_distinct=len(c))
    return out


def bigrams(faces: List[int]):
    return collections.Counter(zip(faces, faces[1:]))
