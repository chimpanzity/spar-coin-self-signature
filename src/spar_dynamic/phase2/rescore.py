"""Independent rescore of headline numbers from scores.csv (Section 14).

Deliberately does NOT import analysis.py: H4 is computed from the complete-
data 3x3 coefficient form on each pairwise mask, and AUROC by rank sums.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional

from . import config as C


def _rank_auc(pos: List[float], neg: List[float]) -> Optional[float]:
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks = {}
    i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        r = (i + j + 1) / 2.0          # average rank, 1-indexed
        for k in range(i, j):
            ranks.setdefault(allv[k][0], r)
        i = j
    rsum = sum(ranks[v] for v in pos)
    n1, n0 = len(pos), len(neg)
    return (rsum - n1 * (n1 + 1) / 2) / (n1 * n0)


def rescore(rd: Path) -> Dict[str, object]:
    J = C.CORE_ORDER
    src, prm, suffix = {}, {}, {}
    pairs = {}
    for line in (rd / "items_private.jsonl").read_text().splitlines():
        d = json.loads(line)
        if "sequence" in d:
            src[d["parent_id"]] = d["source"]; prm[d["parent_id"]] = d["prompt"]
        elif "relation" in d:
            pairs[d["pair_id"]] = d
    loss: Dict[tuple, float] = {}
    pv: Dict[tuple, float] = {}
    with open(rd / "scores.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["valid"] != "True":
                continue
            if r["task"] == "completion" and r["brier_loss"]:
                loss[(r["parent_id"], r["judge"], r["condition"])] = float(r["brier_loss"])
            if r["task"] == "pairs":
                pv[(r["pair_id"], r["order"], r["judge"])] = float(r["value"])
    # H4 panel: mean over prompts of mean over judge pairs of crossover H4
    by_cell = defaultdict(list)
    for pid in src:
        by_cell[(src[pid], prm[pid])].append(pid)
    vals = []
    ok = True
    for p in C.PROMPT_ORDER:
        for a, b in combinations(J, 2):
            M = {}
            for g in (a, b):
                S = [pid for pid in by_cell[(g, p)] if all((pid, j, c) in loss for j in (a, b) for c in ("known", "withheld"))]
                if not S:
                    ok = False
                    break
                for j in (a, b):
                    for c in ("known", "withheld"):
                        M[(j, g, c)] = sum(loss[(pid, j, c)] for pid in S) / len(S)
            if not ok:
                break
            gain = lambda j, g: M[(j, g, "withheld")] - M[(j, g, "known")]
            vals.append(0.5 * (gain(a, a) + gain(b, b)) - 0.5 * (gain(b, a) + gain(a, b)))
        if not ok:
            break
    h4 = sum(vals) / len(vals) if ok and vals else None
    # R panel
    q = {}
    for pid in pairs:
        for j in J:
            a1, a2 = pv.get((pid, "designated", j)), pv.get((pid, "swapped", j))
            q[(pid, j)] = (a1 + a2) / 2 if a1 is not None and a2 is not None else None
    Rv, okR = [], True
    for p in C.PROMPT_ORDER:
        for a, b in combinations(J, 2):
            m = [x for x in J if x not in (a, b)][0]
            S = [pid for pid, d in pairs.items() if d["prompt"] == p and q[(pid, a)] is not None and q[(pid, b)] is not None]
            def auc(j, g, r):
                pos = [q[(pid, j)] for pid in S if pairs[pid]["relation"] == "SAME" and pairs[pid]["src_first"] == g]
                neg = [q[(pid, j)] for pid in S if pairs[pid]["relation"] == "DIFFERENT" and {pairs[pid]["src_first"], pairs[pid]["src_second"]} == {g, r}]
                return _rank_auc(pos, neg)
            terms = [auc(a, a, m), auc(b, a, m), auc(b, b, m), auc(a, b, m), auc(a, m, a), auc(b, m, a), auc(b, m, b), auc(a, m, b)]
            if any(t is None for t in terms):
                okR = False
                break
            P = 0.5 * (terms[0] - terms[1] + terms[2] - terms[3])
            D = 0.5 * (terms[4] - terms[5] + terms[6] - terms[7])
            Rv.append((P + D) / 2)
        if not okR:
            break
    R = sum(Rv) / len(Rv) if okR and Rv else None
    main = json.loads((rd / "contrasts.json").read_text())
    mh = (main["h4"]["primary"]["panel"] or {}).get("H4")
    mr = (main["pairs"]["primary"]["panel"] or {}).get("R")
    agree = lambda x, y: (x is None and y is None) or (x is not None and y is not None and abs(x - y) < 1e-9)
    return {"H4_rescore": h4, "H4_main": mh, "H4_agree": agree(h4, mh),
            "R_rescore": R, "R_main": mr, "R_agree": agree(R, mr)}
