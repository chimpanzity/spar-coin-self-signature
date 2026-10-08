"""Stage 1 documents, full analysis driver, and reports."""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import analysis as A
from . import config as C
from .baselines import (CompletionL2, HeadsCountClassifier, Observer, PairL2, brier,
                        pair_features, rank_scores)
from .client import progress, utc_now
from .corpus import cell_summary, describe, load_calls, sequence_rows, write_csv
from . import lasso as LZ
from . import tasks as T

J = C.CORE_ORDER
f4 = lambda x: "NA" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.4f}"
f3 = lambda x: "NA" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.3f}"


def _ci(c):
    if not c or c[0] is None:
        return "[NA]"
    return f"[{c[0]:+.4f}, {c[1]:+.4f}]"


# ---------------------------------------------------------------------------
# Stage 1 documents
# ---------------------------------------------------------------------------

def _rehearsal_stats(rd: Path) -> List[Dict[str, Any]]:
    calls = load_calls(rd)
    out = defaultdict(lambda: {"n": 0, "valid": 0, "values": []})
    for r in calls.values():
        if not r["task"].startswith("rehearsal"):
            continue
        k = (r["task"], r["alias"], r["meta"].get("condition", r["meta"].get("order")))
        out[k]["n"] += 1
        p = r.get("parse") or {}
        if p.get("valid"):
            out[k]["valid"] += 1
            v = p["value"]
            out[k]["values"] += v if isinstance(v, list) else [v]
    rows = []
    for (task, judge, cond), d in sorted(out.items()):
        vals = d["values"]
        rows.append({"task": task, "judge": judge, "condition": cond, "n": d["n"], "valid": d["valid"],
                     "mean_value": round(statistics.mean(vals), 3) if vals else None,
                     "sd_value": round(statistics.pstdev(vals), 3) if len(vals) > 1 else None,
                     "share_exact_0.5": round(sum(1 for v in vals if v == 0.5) / len(vals), 3) if vals else None})
    return rows


def write_stage1_docs(rd: Path, summ, fixtures, hr, reh) -> None:
    reh_stats = _rehearsal_stats(rd)
    write_csv(rd / "rehearsal_validity.csv", reh_stats)
    hp = [r for r in (rd / "headroom_per_parent.csv").read_text().splitlines()]
    L = ["# Stage 1 report (development only)", "",
         f"Generated {utc_now()}. Run `{rd.name}`. Protocol {C.PROTOCOL}.", "",
         "## Development corpus", "",
         "| source | prompt | valid / attempted | mean heads | first-H rate | switch rate | longest run | distinct strings | effective strings | distinct first-10 | effective first-10 | failures |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for c in summ:
        L.append(f"| {c['source']} | {c['prompt']} | {c['valid']}/{c['attempted']} | {c['mean_heads']} | {c['first_H_rate']} | "
                 f"{c['switch_rate']} | {c['mean_longest_run']} | {c['distinct_strings']} | {c['effective_strings']} | "
                 f"{c['distinct_prefix10']} | {c['effective_prefix10']} | {c['failure_reasons'] or ''} |")
    L += ["", "Most frequent strings per cell (string, count):", ""]
    for c in summ:
        L.append(f"- {c['source']}/{c['prompt']}: " + "; ".join(f"`{s}` x{n}" for s, n in c["top_strings"]))
    L += ["", "Cells below 80% validity are NOT paused (Chris, 2026-10-07: keep going).", ""]
    L += ["## Objective fixtures (invented sources, explicit rules)", "",
          "| task / judge | valid | correct (max abs error <= 0.2) | valid gate (>= 11/12) |", "|---|---:|---:|---|"]
    for k, v in sorted(fixtures["summary"].items()):
        L.append(f"| {k} | {v['valid']}/{v['n']} | {v['correct']}/{v['n']} | {'pass' if fixtures['gates'][k]['valid_gate_pass'] else 'FAIL'} |")
    L += ["", "## Rehearsal (development data; validity and response variability only)", "",
          "| task | judge | condition/order | valid / n | mean value | SD | share exactly 0.5 |", "|---|---|---|---:|---:|---:|---:|"]
    for r in reh_stats:
        L.append(f"| {r['task']} | {r['judge']} | {r['condition']} | {r['valid']}/{r['n']} | {r['mean_value']} | {r['sd_value']} | {r['share_exact_0.5']} |")
    L += ["", "Source-linked rehearsal scores were not computed or inspected (Section 5.4).", "",
          "## Headroom review (five-fold out-of-fold empirical-prefix observer)", "",
          "I[g,p] = mean(B_withheld - B_known) on held-out development parents. Prefix value = source-position loss minus source-known prefix loss.", "",
          "| source | prompt | I[g,p] | prefix value |", "|---|---|---:|---:|"]
    for g in J:
        for p in C.PROMPT_ORDER:
            L.append(f"| {g} | {p} | {f4(hr['I_gp'].get(f'{g}|{p}'))} | {f4(hr['prefix_value'].get(f'{g}|{p}'))} |")
    L += ["", "| source | I[g] (prompt-averaged) |", "|---|---:|"] + [f"| {g} | {f4(hr['I_g'][g])} |" for g in J]
    L += ["", f"headroom_review_required = **{hr['headroom_review_required']}** (threshold {C.HEADROOM_THRESHOLD} Brier units; "
          "operational reviewer threshold, not a futility test).", ""]
    if hr["headroom_review_required"]:
        L += [f"Recorded decision: option ({hr['decision_if_required']['option']}) {hr['decision_if_required']['text']}. "
              f"Source: {hr['decision_if_required']['source']}.", ""]
    (rd / "STAGE1_REPORT.md").write_text("\n".join(L) + "\n")

    v = {(c["source"], c["prompt"]): c["valid"] for c in summ}
    exp_test = {f"{g}|{p}": round(C.TEST_ATTEMPTS_PER_CELL * v.get((g, p), 0) / C.DEV_ATTEMPTS_PER_CELL, 1) for g in J for p in C.PROMPT_ORDER}
    s_vals = [0.05, 0.10, 0.20, 0.30]
    P = ["# Precision plan (written before test generation)", "",
         "## Planned support", "",
         f"- {C.TEST_ATTEMPTS_PER_CELL} attempted test parents per source x prompt (144 total).",
         "- At most 12 pair blocks per prompt (24 blocks, 144 unordered pairs, each judged in both orders by all three judges).",
         "- Named arm: at most six parents per source x prompt (36 total).", "",
         "## Expected usable support, from development validity rates (assumption, not a guarantee)", "",
         "| source x prompt | development valid rate | expected valid test parents of 24 |", "|---|---:|---:|"]
    for g in J:
        for p in C.PROMPT_ORDER:
            P.append(f"| {g} x {p} | {v.get((g, p), 0)}/60 | {exp_test[f'{g}|{p}']} |")
    nq = exp_test["qwen|fair"]
    P += ["", f"The Qwen x fair cell is expected to yield about {nq} valid test parents. Pair blocks for the fair prompt need at least two valid parents "
          "from every source, so the fair-prompt pair arm may have only zero to two blocks, and any crossover that needs Qwen sources under the "
          "fair prompt may be non-estimable. Under the frozen rules a non-estimable component makes the panel summary non-estimable; it is never "
          "silently dropped. Per-prompt results are reported separately.", "",
          "## Assumption-only completion half-width scenarios (Section 11.4)", "",
          "Normal half-width approx 1.96 s / sqrt(144) for independent parent-level contrasts with no missingness and equal cell weights. "
          "These are arithmetic sensitivity scenarios, not estimated study intervals.", "",
          "| s | half-width |", "|---:|---:|"] + [f"| {s:.2f} | {1.96 * s / 12:.4f} |" for s in s_vals]
    P += ["", "## Reporting margins (fixed before test generation)", "",
          f"- delta_Brier = {C.DELTA_BRIER} for H4, gains and own-advantage contrasts.",
          f"- delta_AUC = {C.DELTA_AUC} for R/P/D and named contrasts.",
          "- Formal equivalence/absence claims are disabled.", "",
          "## Task-specific power", "",
          "Task-specific power for R/P/D and the named arm is unknown: no score simulations were run. Large reliable effects may be detectable; "
          "small effects cannot be ruled out by the planned size. The twelve-parent rehearsal cannot pin down variance assumptions.", ""]
    (rd / "PRECISION_PLAN.md").write_text("\n".join(P) + "\n")

    fx_ok = all(g["valid_gate_pass"] for g in fixtures["gates"].values())
    D = ["# Decision memo (Stage 1 -> Stage 2)", "",
         f"- Apparatus and generation parser valid? Yes, after amendments A1 (Qwen seeds) and A2 (parser gen_v2), both recorded in amendments.jsonl before any judge data.",
         f"- Completion and pair fixtures valid? {'All valid-response gates passed.' if fx_ok else 'One or more valid-response gates FAILED (see STAGE1_REPORT.md); per Chris, the run continues and failures are reported.'}",
         "- Rehearsal valid? See STAGE1_REPORT.md rehearsal table; flat judgments are reported, not rejected.",
         f"- Minimal observer diagnostics and headroom decision recorded? Yes; review_required={hr['headroom_review_required']}."
         + (" Decision (a) continue, inferred from Chris's go-ahead and flagged." if hr["headroom_review_required"] else ""),
         "- Prefix k=10 and probability-response policy retained? Yes.",
         "- Two-sided H4 and common-set rules fixed? Yes (analysis.py at the frozen hash).",
         "- Precision plan acknowledged? PRECISION_PLAN.md written before test generation.",
         f"- Cost ceiling: hard cap ${C.BUDGET_CAP_USD:.0f} (Chris).",
         "- Arm status: core completion and anonymous arms ready; named fixtures, named calls and historical generation run after the protected core calls; LASSO/regularized code exists before the freeze.",
         "- Low-validity cells (Qwen x fair) are not paused, per Chris's instruction.", ""]
    (rd / "DECISION_MEMO.md").write_text("\n".join(D) + "\n")
    ready = {"shared": "ready", "completion": "ready", "anonymous": "ready",
             "named": "pending (fixtures run in retained stage)", "historical": "pending (retained stage)",
             "lasso": "implemented before freeze", "fixture_gates": fixtures["gates"]}
    (rd / "arm_readiness.json").write_text(json.dumps(ready, indent=1))


# ---------------------------------------------------------------------------
# Analysis driver
# ---------------------------------------------------------------------------

def _load(rd: Path):
    calls = load_calls(rd)
    rows = sequence_rows(calls)
    man = json.loads((rd / "manifests.json").read_text())
    seq = {r["parent_id"]: r for r in rows if r["valid"]}
    return calls, rows, man, seq


def _val(r):
    p = (r or {}).get("parse") or {}
    return p.get("value") if p.get("valid") else None


def _completion_cells(calls, seq, test_cells, task="completion"):
    cells = {}
    for (g, p), pids in test_cells.items():
        lst = []
        for pid in sorted(pids):
            d = {"parent_id": pid}
            y = seq[pid]["outcomes"][10:]
            for j in J:
                for c in A.CONDS:
                    v = _val(calls.get(f"{task}:{pid}:{j}:{c}"))
                    d[(j, c)] = brier(v, y) if v is not None else None
            lst.append(d)
        cells[(g, p)] = lst
    return cells


def _test_cells(rows):
    out = defaultdict(list)
    for r in rows:
        if r["split"] == "test" and r["valid"] and r["source"] in J:
            out[(r["source"], r["prompt"])].append(r["parent_id"])
    return out


def _dev_cells(rows):
    out = defaultdict(dict)
    for r in rows:
        if r["split"] == "development" and r["valid"] and r["source"] in J:
            out[(r["source"], r["prompt"])][r["parent_id"]] = r["outcomes"]
    return out


def _pair_items(calls, man, task="pairs", orders=("designated", "swapped")):
    items = []
    for d in man["pairs"]:
        q = {}
        per = {}
        for j in J:
            vals = [_val(calls.get(f"{task}:{d['pair_id']}:{o}:{j}")) for o in orders]
            per[j] = vals
            q[j] = (sum(vals) / len(vals)) if all(v is not None for v in vals) else None
        items.append({"pair_id": d["pair_id"], "block_id": d["block_id"], "prompt": d["prompt"],
                      "relation": d["relation"], "src": (d["src_first"], d["src_second"]),
                      "first": d["first"], "second": d["second"], "q": q, "per_order": per})
    return items


def analyze_all(rd: Path) -> None:
    progress(rd, "ANALYZE start")
    calls, rows, man, seq = _load(rd)
    test_cells = _test_cells(rows)
    dev = _dev_cells(rows)
    out: Dict[str, Any] = {"generated_utc": utc_now(), "run": rd.name}

    # ---------------- scores.csv ----------------
    srows = []
    for sid, r in calls.items():
        if r["task"] in ("generation", "historical_generation"):
            continue
        m = r["meta"]
        p = r.get("parse") or {}
        loss = None
        if r["task"] in ("completion", "completion_repeat", "completion_polarity") and p.get("valid"):
            v = p["value"]
            if r["task"] == "completion_polarity":
                v = [1 - x for x in v]
            pid = m["parent_id"]
            if pid in seq:
                loss = brier(v, seq[pid]["outcomes"][10:])
        srows.append({"slot_id": sid, "task": r["task"], "judge": r["alias"], "parent_id": m.get("parent_id"),
                      "pair_id": m.get("pair_id"), "condition": m.get("condition"), "order": m.get("order"),
                      "polarity": m.get("polarity", m.get("target")), "prompt": m.get("prompt"),
                      "status": r["status"], "valid": bool(p.get("valid")), "parse_reason": p.get("reason"),
                      "strict_valid": p.get("strict_valid"), "wrapped": p.get("wrapped_payload"),
                      "value": p.get("value"), "brier_loss": loss,
                      "primary": r["task"] in ("completion", "pairs", "named"),
                      "cost_usd": r.get("cost_usd"), "finish_reason": (r.get("response") or {}).get("finish_reason")})
    write_csv(rd / "scores.csv", srows)
    write_csv(rd / "invalids.csv", [x for x in srows if not x["valid"]])
    validity = defaultdict(lambda: [0, 0])
    for x in srows:
        validity[(x["task"], x["judge"])][0] += 1
        validity[(x["task"], x["judge"])][1] += int(x["valid"])
    out["validity"] = {f"{k[0]}|{k[1]}": {"n": v[0], "valid": v[1], "rate": round(v[1] / v[0], 3)} for k, v in sorted(validity.items())}

    # ---------------- H4 ----------------
    cells = _completion_cells(calls, seq, test_cells)
    for key in [(g, p) for g in J for p in C.PROMPT_ORDER]:
        cells.setdefault(key, [])
    h4 = A.h4_panel(cells, "pairwise")
    h4b = A.bootstrap_h4(cells, "pairwise", C.N_BOOT, "primary")
    h4c3 = A.h4_panel(cells, "common3")
    h4c3b = A.bootstrap_h4(cells, "common3", C.N_BOOT, "common3")
    out["h4"] = {"primary": h4, "primary_boot": h4b, "common3": h4c3, "common3_boot": h4c3b,
                 "available_case": A.available_case_matrix(cells), "worst_case_bounds": A.h4_worst_case(cells),
                 "support": {f"{g}|{p}": len(v) for (g, p), v in cells.items()}}
    progress(rd, f"  H4 primary panel: {h4['panel']}")

    # absolute skill and baselines on the same test parents
    base = completion_baselines(dev, seq, test_cells)
    out["completion_baselines"] = base
    skill = []
    for (g, p), lst in cells.items():
        for j in J:
            for c in A.CONDS:
                v = [d[(j, c)] for d in lst if d[(j, c)] is not None]
                skill.append({"judge": j, "source": g, "prompt": p, "condition": c, "n": len(v),
                              "mean_brier": statistics.mean(v) if v else None})
    out["completion_skill"] = skill

    # per-model identity gains (available case)
    gains = []
    for (g, p), lst in cells.items():
        for j in J:
            dd = [d[(j, "withheld")] - d[(j, "known")] for d in lst if d[(j, "withheld")] is not None and d[(j, "known")] is not None]
            gains.append({"judge": j, "source": g, "prompt": p, "own": j == g, "n": len(dd),
                          "gain_withheld_minus_known": statistics.mean(dd) if dd else None})
    out["identity_gains"] = gains

    # suffix permutation diagnostic
    out["suffix_permutation"] = suffix_permutation(calls, seq, test_cells, rows)

    # ---------------- completion controls ----------------
    out["completion_controls"] = completion_controls(calls, man)

    # ---------------- anonymous pairs ----------------
    items = _pair_items(calls, man)
    pdr = A.pdr_panel(items)
    pdrb = A.bootstrap_pdr(items, C.N_BOOT, "primary")
    pdr3 = A.pdr_common3(items)
    first = _pair_items(calls, man, orders=("designated",))
    pdr_first = A.pdr_panel(first)
    out["pairs"] = {"primary": pdr, "primary_boot": pdrb, "common3": pdr3, "first_orientation": pdr_first,
                    "bias": A.pair_bias_table(items), "order_effects": order_effects(items),
                    "support": {"n_pairs": len(items), "n_blocks": len({i['block_id'] for i in items}),
                                "per_prompt_pairs": dict(Counter(i["prompt"] for i in items))},
                    "baselines": pair_baselines(dev, seq, items, rows),
                    "time_gaps": time_gaps(items, calls, rows),
                    "overall_auc": {p: {j: A.auroc([i["q"][j] for i in items if i["prompt"] == p and i["relation"] == "SAME" and i["q"][j] is not None],
                                                   [i["q"][j] for i in items if i["prompt"] == p and i["relation"] == "DIFFERENT" and i["q"][j] is not None])
                                        for j in J} for p in C.PROMPT_ORDER}}
    progress(rd, f"  anonymous R/P/D panel: {pdr['panel']}")
    out["pair_controls"] = pair_controls(calls, man)

    # ---------------- named ----------------
    named_items = named_items_from(calls, man, seq)
    if named_items:
        nb = A.bootstrap_named(named_items, C.N_BOOT, "primary")
        anon_matched = [i for i in items if i["block_id"] in sum(man["named_blocks"].values(), [])]
        out["named"] = {"primary": A.named_panel(named_items), "boot": nb, "common3": A.named_common3(named_items),
                        "secondary": A.named_secondary(named_items), "priors": named_priors(calls),
                        "n_items": len(named_items),
                        "anonymous_on_named_blocks": A.pdr_panel(anon_matched) if anon_matched else None}
        nf = rd / "fixtures_results_named.json"
        if nf.exists():
            out["named"]["fixtures"] = json.loads(nf.read_text())["summary"]
    else:
        out["named"] = None

    # ---------------- LASSO (core + historical) ----------------
    out["lasso_core"] = {}
    for g in J:
        for p in C.PROMPT_ORDER:
            fit = LZ.fit_cell(dev.get((g, p), {}), f"core|{g}|{p}")
            tst = {pid: seq[pid]["outcomes"] for pid in test_cells.get((g, p), [])}
            ev = LZ.evaluate(fit, tst, f"core|{g}|{p}")
            out["lasso_core"][f"{g}|{p}"] = {"fit": {k: v for k, v in fit.items() if k != "model"},
                                             "eval": {k: v for k, v in ev.items() if k != "per_parent"}}
    out["historical"] = historical(rows)

    # ---------------- resolution table ----------------
    res = []
    if h4["panel"] is not None or True:
        for k in A.H4_KEYS:
            est = h4["panel"][k] if h4["panel"] else None
            res.append(A.resolution_row(k, est, h4b["ci"][k], C.DELTA_BRIER, h4b["undefined_frac"],
                                        f"parents {sum(len(v) for v in cells.values())}", "pairwise-common"))
        for pk, v in h4["pair_means"].items():
            res.append(A.resolution_row(f"H4 crossover {pk}", v["H4"] if v else None, h4b["pair_ci"][pk]["H4"],
                                        C.DELTA_BRIER, 0.0 if v else 1.0, "", "pairwise-common"))
        for p in C.PROMPT_ORDER:
            v = h4["per_prompt"][p]
            res.append(A.resolution_row(f"H4 prompt={p}", v["H4"] if v else None, h4b["prompt_ci"][p]["H4"],
                                        C.DELTA_BRIER, 0.0 if v else 1.0, "", "pairwise-common (per prompt, secondary)"))
    for k in ("R", "P", "D"):
        res.append(A.resolution_row(k, pdr["panel"][k] if pdr["panel"] else None, pdrb["ci"][k], C.DELTA_AUC,
                                    pdrb["undefined_frac"], f"pairs {len(items)}", "pairwise-common both orders"))
    for pk, v in pdr["pair_means"].items():
        res.append(A.resolution_row(f"R crossover {pk}", v["R"] if v else None, pdrb["pair_ci"][pk]["R"],
                                    C.DELTA_AUC, 0.0 if v else 1.0, "", "pairwise-common both orders"))
    for p in C.PROMPT_ORDER:
        v = pdr["per_prompt"][p]
        res.append(A.resolution_row(f"R prompt={p}", v["R"] if v else None, (None, None), C.DELTA_AUC,
                                    0.0 if v else 1.0, "", "per prompt, point estimate only"))
    if out["named"]:
        npn = out["named"]["primary"]
        for k in ("R", "P", "D"):
            res.append(A.resolution_row(f"named {k}", npn["panel"][k] if npn["panel"] else None,
                                        out["named"]["boot"]["ci"][k], C.DELTA_AUC, out["named"]["boot"]["undefined_frac"],
                                        f"parents {len(named_items)}", "pairwise-common (secondary)"))
    out["resolution"] = res
    write_csv(rd / "RESOLUTION_TABLE.csv", res)
    (rd / "comparison_masks.json").write_text(json.dumps(mask_summary(cells, items), indent=1))
    (rd / "contrasts.json").write_text(json.dumps(out, indent=1, default=_json_default))

    from .rescore import rescore
    out["rescore"] = rescore(rd)
    (rd / "contrasts.json").write_text(json.dumps(out, indent=1, default=_json_default))
    write_reports(rd, out, man, rows)
    files = sorted(p for p in rd.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (rd / "checksums.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    progress(rd, "ANALYZE complete")


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, tuple):
        return list(o)
    return str(o)


def mask_summary(cells, items):
    m = {"completion": {}, "pairs": {}}
    for (g, p), lst in cells.items():
        for a, b in A.PAIRS:
            if g in (a, b):
                S = [d["parent_id"] for d in lst if all(d.get((j, c)) is not None for j in (a, b) for c in A.CONDS)]
                m["completion"][f"{a}-{b}|{g}|{p}"] = {"n": len(S), "sha256": hashlib.sha256("|".join(S).encode()).hexdigest()[:16]}
        S3 = [d["parent_id"] for d in lst if all(d.get((j, c)) is not None for j in J for c in A.CONDS)]
        m["completion"][f"common3|{g}|{p}"] = {"n": len(S3), "of": len(lst)}
    for a, b in A.PAIRS:
        S = [i["pair_id"] for i in items if i["q"][a] is not None and i["q"][b] is not None]
        m["pairs"][f"{a}-{b}"] = {"n": len(S), "sha256": hashlib.sha256("|".join(S).encode()).hexdigest()[:16]}
    m["pairs"]["common3"] = {"n": sum(1 for i in items if all(i["q"][j] is not None for j in J)), "of": len(items)}
    return m


def completion_baselines(dev, seq, test_cells):
    out = {"per_cell": {}, "note": "All fits use development data only; evaluated on the same valid test parents."}
    for p in C.PROMPT_ORDER:
        train = {g: list(dev.get((g, p), {}).values()) for g in J}
        if any(len(v) == 0 for v in train.values()):
            out["per_cell"][p] = "observer not fittable (a source has no valid development parents)"
            continue
        obs = Observer(train)
        pooled = [sum(obs.models[g].position()[i] for g in J) / 3 for i in range(10)]
        l2k = {g: CompletionL2(train[g], list(dev[(g, p)].keys()), None, f"{g}|{p}") for g in J}
        ids_all, seqs_all, w_all = [], [], []
        for g in J:
            for pid, s in dev[(g, p)].items():
                ids_all.append(pid); seqs_all.append(s); w_all.append(1.0 / len(dev[(g, p)]))
        l2w = CompletionL2(seqs_all, ids_all, w_all, f"pooled|{p}")
        for g in J:
            losses = defaultdict(list)
            for pid in test_cells.get((g, p), []):
                s = seq[pid]["outcomes"]; u, y = s[:10], s[10:]
                losses["fair"].append(brier([0.5] * 10, y))
                losses["source_position"].append(brier(obs.models[g].position(), y))
                losses["pooled_position"].append(brier(pooled, y))
                losses["observer_known"].append(brier(obs.forecast_known(g, u), y))
                losses["observer_withheld"].append(brier(obs.forecast_withheld(u), y))
                losses["l2_known"].append(brier(l2k[g].predict(u), y))
                losses["l2_withheld"].append(brier(l2w.predict(u), y))
            out["per_cell"][f"{g}|{p}"] = {k: (statistics.mean(v) if v else None) for k, v in losses.items()} | {"n": len(losses["fair"])}
    return out


def suffix_permutation(calls, seq, test_cells, rows):
    tb = {r["parent_id"]: r["time_block"] for r in rows}
    rng = random.Random(C.derive_seed("suffix_permutation"))
    groups = defaultdict(list)
    for (g, p), pids in test_cells.items():
        for pid in pids:
            groups[(g, p, tb[pid])].append(pid)
    preds = {}
    for pids in groups.values():
        for pid in pids:
            for j in J:
                for c in A.CONDS:
                    v = _val(calls.get(f"completion:{pid}:{j}:{c}"))
                    if v is not None:
                        preds[(pid, j, c)] = v
    def mean_loss(assign):
        acc = defaultdict(list)
        for (pid, j, c), v in preds.items():
            acc[(j, c)].append(brier(v, seq[assign[pid]]["outcomes"][10:]))
        return {k: statistics.mean(v) for k, v in acc.items()}
    intact = mean_loss({pid: pid for pids in groups.values() for pid in pids})
    perm_vals = defaultdict(list)
    for _ in range(C.N_SUFFIX_PERMUTATIONS):
        assign = {}
        for pids in groups.values():
            sh = pids[:]; rng.shuffle(sh)
            assign.update(dict(zip(pids, sh)))
        for k, v in mean_loss(assign).items():
            perm_vals[k].append(v)
    return [{"judge": j, "condition": c, "intact_loss": intact.get((j, c)),
             "permuted_mean_loss": statistics.mean(perm_vals[(j, c)]) if perm_vals[(j, c)] else None,
             "share_perm_le_intact": (sum(1 for x in perm_vals[(j, c)] if x <= intact[(j, c)]) / len(perm_vals[(j, c)])) if perm_vals[(j, c)] else None}
            for j in J for c in A.CONDS if (j, c) in intact]


def completion_controls(calls, man):
    rows = []
    for pid in man["audit_parents"]:
        for j in J:
            for c in A.CONDS:
                o = _val(calls.get(f"completion:{pid}:{j}:{c}"))
                rp = _val(calls.get(f"completion_repeat:{pid}:{j}:{c}"))
                pt = _val(calls.get(f"completion_polarity:{pid}:{j}:{c}"))
                rows.append({"parent_id": pid, "judge": j, "condition": c,
                             "repeat_mad": statistics.mean(abs(a - b) for a, b in zip(o, rp)) if o and rp else None,
                             "polarity_mad": statistics.mean(abs(a - (1 - b)) for a, b in zip(o, pt)) if o and pt else None,
                             "polarity_signed": statistics.mean(a - (1 - b) for a, b in zip(o, pt)) if o and pt else None})
    summ = {}
    for j in J:
        rs = [r for r in rows if r["judge"] == j]
        g = lambda k: [r[k] for r in rs if r[k] is not None]
        summ[j] = {"n": len(rs), "repeat_mad": statistics.mean(g("repeat_mad")) if g("repeat_mad") else None,
                   "polarity_mad": statistics.mean(g("polarity_mad")) if g("polarity_mad") else None,
                   "polarity_signed": statistics.mean(g("polarity_signed")) if g("polarity_signed") else None}
    priors = []
    for sid, r in calls.items():
        if r["task"] == "completion_prior":
            v = _val(r)
            priors.append({"judge": r["alias"], "prompt": r["meta"]["prompt"], "disclosed": r["meta"].get("disclosed"),
                           "mean_pH": statistics.mean(v) if v else None, "values": v})
    return {"summary": summ, "rows": rows, "priors": priors}


def pair_controls(calls, man):
    rows = []
    audit_blocks = [b for b in man["audit_blocks"].values() if b]
    for d in man["pairs"]:
        if d["block_id"] not in audit_blocks:
            continue
        for j in J:
            o = _val(calls.get(f"pairs:{d['pair_id']}:designated:{j}"))
            rp = _val(calls.get(f"pair_repeat:{d['pair_id']}:designated:{j}"))
            pd = _val(calls.get(f"pair_polarity:{d['pair_id']}:designated:{j}"))
            rows.append({"pair_id": d["pair_id"], "judge": j,
                         "repeat_abs": abs(o - rp) if o is not None and rp is not None else None,
                         "polarity_abs": abs(o - (1 - pd)) if o is not None and pd is not None else None,
                         "polarity_signed": (o - (1 - pd)) if o is not None and pd is not None else None})
    summ = {}
    for j in J:
        rs = [r for r in rows if r["judge"] == j]
        g = lambda k: [r[k] for r in rs if r[k] is not None]
        summ[j] = {k: (statistics.mean(g(k)) if g(k) else None) for k in ("repeat_abs", "polarity_abs", "polarity_signed")}
    priors = [{"judge": r["alias"], "prompt": r["meta"]["prompt"], "polarity": r["meta"]["polarity"], "value": _val(r)}
              for r in calls.values() if r["task"] == "pair_prior"]
    return {"summary": summ, "rows": rows, "priors": priors}


def order_effects(items):
    out = {}
    for j in J:
        d = [(v[0], v[1]) for it in items for v in [it["per_order"][j]] if v[0] is not None and v[1] is not None]
        if not d:
            out[j] = None; continue
        out[j] = {"n": len(d), "mean_abs_diff": statistics.mean(abs(a - b) for a, b in d),
                  "mean_signed_designated_minus_swapped": statistics.mean(a - b for a, b in d),
                  "threshold_disagreement": statistics.mean(1.0 if (a > 0.5) != (b > 0.5) else 0.0 for a, b in d),
                  "share_exact_0.5": statistics.mean(1.0 if a == 0.5 else 0.0 for a, _ in d)}
    return out


def pair_baselines(dev, seq, items, rows):
    out = {}
    for p in C.PROMPT_ORDER:
        train = {g: list(dev.get((g, p), {}).values()) for g in J}
        its = [i for i in items if i["prompt"] == p]
        if not its:
            continue
        scores = defaultdict(dict)
        fittable = all(len(v) > 0 for v in train.values())
        if fittable:
            obs = Observer(train); hc = HeadsCountClassifier(train)
            # L2 pair classifier trained on development pair blocks
            blocks, pairs = T.build_pair_blocks({g: list(dev.get((g, p), {}).keys()) for g in J}, "development", p)
            dseq = {pid: s for g in J for pid, s in dev.get((g, p), {}).items()}
            if pairs:
                l2 = PairL2([pair_features(dseq[x.first], dseq[x.second]) for x in pairs],
                            [1 if x.relation == "SAME" else 0 for x in pairs], [x.block_id for x in pairs], p)
            else:
                l2 = None
        for i in its:
            x, y = seq[i["first"]]["outcomes"], seq[i["second"]]["outcomes"]
            sc = rank_scores(x, y)
            if fittable:
                sc["observer_p_same"] = obs.p_same(x, y)
                sc["heads_count_p_same"] = hc.p_same(x, y)
                if l2 is not None:
                    sc["l2_pair"] = l2.predict([pair_features(x, y)])[0]
            scores[i["pair_id"]] = sc
        res = {}
        names = sorted({k for v in scores.values() for k in v})
        for nm in names:
            q = {i["pair_id"]: scores[i["pair_id"]].get(nm) for i in its}
            overall = A.auroc([q[i["pair_id"]] for i in its if i["relation"] == "SAME"],
                              [q[i["pair_id"]] for i in its if i["relation"] == "DIFFERENT"])
            per = {}
            for g in J:
                for r in J:
                    if g != r:
                        per[f"{g}>{r}"] = A.auroc([q[i["pair_id"]] for i in its if i["relation"] == "SAME" and i["src"][0] == g],
                                                  [q[i["pair_id"]] for i in its if i["relation"] == "DIFFERENT" and set(i["src"]) == {g, r}])
            res[nm] = {"overall_auc": overall, "per_comparison_auc": per}
        out[p] = res
    return out


def time_gaps(items, calls, rows):
    t = {}
    tb = {r["parent_id"]: r["time_block"] for r in rows}
    for r in rows:
        if r["completed_utc"]:
            t[r["parent_id"]] = datetime.strptime(r["completed_utc"], "%Y-%m-%dT%H:%M:%S.%fZ")
    agg = defaultdict(list)
    same_block = defaultdict(list)
    for i in items:
        if i["first"] in t and i["second"] in t:
            gap = abs((t[i["first"]] - t[i["second"]]).total_seconds())
            typ = "SAME" if i["relation"] == "SAME" else "DIFFERENT"
            agg[typ].append(gap)
            same_block[typ].append(1.0 if tb[i["first"]] == tb[i["second"]] else 0.0)
    return {k: {"n": len(v), "mean_gap_s": statistics.mean(v), "median_gap_s": statistics.median(v),
                "share_same_time_block": statistics.mean(same_block[k])} for k, v in agg.items()}


def named_items_from(calls, man, seq):
    orders = C.candidate_orders()
    items = []
    for pid, oi in man["named_order"].items():
        if pid not in seq:
            continue
        prob = {}
        for j in J:
            v = _val(calls.get(f"named:{pid}:{j}"))
            prob[j] = ({orders[oi][k]: v[f"C{k + 1}"] for k in range(3)} if v else None)
        if all(x is None for x in prob.values()) and not any(f"named:{pid}:{j}" in calls for j in J):
            continue
        items.append({"parent_id": pid, "prompt": seq[pid]["prompt"], "source": seq[pid]["source"], "prob": prob})
    return items


def named_priors(calls):
    orders = C.candidate_orders()
    out = []
    for r in calls.values():
        if r["task"] == "named_prior":
            v = _val(r); oi = r["meta"]["order_index"]
            out.append({"judge": r["alias"], "prompt": r["meta"]["prompt"], "order_index": oi,
                        "probs": ({orders[oi][k]: v[f"C{k + 1}"] for k in range(3)} if v else None)})
    return out


PAPER_FIRST_FLIP_GPT35 = {("plain", 0.0): 1.00, ("plain", 0.8): 1.00, ("plain", 1.5): 1.00,
                          ("fair", 0.0): 1.00, ("fair", 0.8): 1.00, ("fair", 1.5): 0.86}


def historical(rows):
    hr = [r for r in rows if r["source"] == C.HISTORICAL.alias]
    if not hr:
        return None
    summ = cell_summary(hr)
    lz = {}
    for p in C.PROMPT_ORDER:
        for t in C.HIST_TEMPERATURES:
            devc = {r["parent_id"]: r["outcomes"] for r in hr if r["prompt"] == p and r["temperature"] == t and r["split"] == "development" and r["valid"]}
            hold = {r["parent_id"]: r["outcomes"] for r in hr if r["prompt"] == p and r["temperature"] == t and r["split"] == "holdout" and r["valid"]}
            fit = LZ.fit_cell(devc, f"hist|{p}|{t}")
            ev = LZ.evaluate(fit, hold, f"hist|{p}|{t}")
            lz[f"{p}|{t}"] = {"fit": {k: v for k, v in fit.items() if k != "model"}, "eval": {k: v for k, v in ev.items() if k != "per_parent"}}
    comp = []
    for p in C.PROMPT_ORDER:
        for t in C.HIST_TEMPERATURES:
            v = [r for r in hr if r["prompt"] == p and r["temperature"] == t and r["valid"]]
            comp.append({"prompt": p, "temperature": t, "n_valid": len(v),
                         "first_flip_H_rate": (sum(1 for r in v if r["outcomes"][0] == "H") / len(v)) if v else None,
                         "paper_table2_first_flip_H": PAPER_FIRST_FLIP_GPT35[(p, t)]})
    return {"summary": summ, "lasso": lz, "first_flip_vs_paper": comp}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def write_reports(rd: Path, out: Dict[str, Any], man, rows) -> None:
    h4 = out["h4"]; hb = h4["primary_boot"]
    pr = out["pairs"]; pb = pr["primary_boot"]
    status_named = "complete" if out.get("named") else "pending"
    status_hist = "complete" if out.get("historical") else "pending"
    L = ["# SPAR Phase 2 pilot: core report", "",
         f"Run `{rd.name}`, protocol {C.PROTOCOL}, generated {out['generated_utc']}.",
         f"Report scope: CORE plus retained arms (named: {status_named}; historical: {status_hist}).", "",
         "Exploratory pilot. Intervals are marginal two-sided 95% percentile bootstrap intervals, not multiplicity-adjusted. "
         f"Reporting margins: delta_Brier = {C.DELTA_BRIER}, delta_AUC = {C.DELTA_AUC}.", "",
         "## 1. H4 completion readout (key, two-sided)", "",
         "Positive values mean disclosure of the true source helps the panel's own-model forecasts relatively more than other-model "
         "forecasts. Neither sign is evidence of introspection.", "",
         "| quantity | estimate | 95% CI | direction | bounded within margin |", "|---|---:|---|---|---|"]
    resmap = {r["contrast"]: r for r in out["resolution"]}
    for k in A.H4_KEYS:
        r = resmap[k]
        L.append(f"| {k} | {f4(r['estimate'])} | {_ci((r['ci_lower'], r['ci_upper']))} | {r['direction']} | {r['bounded_small']} |")
    L += ["", f"Bootstrap: {C.N_BOOT} parent resamples within source x prompt; undefined replicates {hb['undefined_frac']:.3f}. "
          f"Panel estimable: {h4['primary']['estimable']}.", ""]
    if not h4["primary"]["estimable"]:
        L += ["**The panel H4 is not estimable** because at least one crossover lacks a required source group in one prompt "
              "(see per-prompt rows). Per the frozen rules the remaining comparisons are not averaged into a substitute panel.", ""]
    L += ["### Per prompt and per judge pair (pairwise-common sets)", "", "| crossover | H4 | gain_own | gain_other | C_known | C_withheld |", "|---|---:|---:|---:|---:|---:|"]
    for key, t in h4["primary"]["crossovers"].items():
        L.append(f"| {key} | " + " | ".join(f4(t[k]) if t else "NA" for k in A.H4_KEYS) + " |")
    for p in C.PROMPT_ORDER:
        v = h4["primary"]["per_prompt"][p]
        ci = hb["prompt_ci"][p]["H4"]
        L.append(f"| **prompt {p} (3-pair mean)** | {f4(v['H4']) if v else 'NA'} {_ci(ci) if v else ''} | " +
                 " | ".join(f4(v[k]) if v else "NA" for k in A.H4_KEYS[1:]) + " |")
    c3 = h4["common3"]
    L += ["", "Common-three-judge sensitivity panel: " + (", ".join(f"{k} {f4(c3['panel'][k])} {_ci(h4['common3_boot']['ci'][k])}" for k in A.H4_KEYS) if c3["panel"] else "not estimable"),
          f"Worst-case complete-data bounds on panel H4 (unobserved losses set to 0/1): [{f4(h4['worst_case_bounds']['lower'])}, {f4(h4['worst_case_bounds']['upper'])}].", "",
          "### Absolute forecast skill (mean Brier; fair coin = 0.25)", "",
          "| judge | condition | " + " | ".join(f"{g}/{p}" for g in J for p in C.PROMPT_ORDER) + " |",
          "|---|---|" + "---:|" * 6]
    sk = {(s["judge"], s["source"], s["prompt"], s["condition"]): s for s in out["completion_skill"]}
    for j in J:
        for c in A.CONDS:
            L.append(f"| {j} | {c} | " + " | ".join(f"{f3(sk[(j, g, p, c)]['mean_brier'])} (n={sk[(j, g, p, c)]['n']})" for g in J for p in C.PROMPT_ORDER) + " |")
    L += ["", "External baselines on the same test parents (fit on development only):", "",
          "| source/prompt | n | fair | pooled position | source position | observer known | observer withheld | L2 known | L2 withheld |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key, v in out["completion_baselines"]["per_cell"].items():
        if isinstance(v, dict):
            L.append(f"| {key} | {v['n']} | " + " | ".join(f3(v[k]) for k in ("fair", "pooled_position", "source_position", "observer_known", "observer_withheld", "l2_known", "l2_withheld")) + " |")
        else:
            L.append(f"| {key} | | {v} |")
    L += ["", "Per-model identity gains (withheld minus known loss, available case; positive = disclosure helped):", "",
          "| judge | " + " | ".join(f"{g}/{p}" for g in J for p in C.PROMPT_ORDER) + " |", "|---|" + "---:|" * 6]
    gm = {(x["judge"], x["source"], x["prompt"]): x for x in out["identity_gains"]}
    for j in J:
        L.append(f"| {j} | " + " | ".join(f4(gm[(j, g, p)]["gain_withheld_minus_known"]) + (" *own*" if j == g else "") for g in J for p in C.PROMPT_ORDER) + " |")
    L += ["", "Suffix-permutation coupling diagnostic (intact vs within-cell permuted suffixes; share of permutations with loss <= intact):", "",
          "| judge | condition | intact | permuted mean | share perm <= intact |", "|---|---|---:|---:|---:|"]
    for r in out["suffix_permutation"]:
        L.append(f"| {r['judge']} | {r['condition']} | {f3(r['intact_loss'])} | {f3(r['permuted_mean_loss'])} | {f3(r['share_perm_le_intact'])} |")
    cc = out["completion_controls"]["summary"]
    L += ["", "Completion controls on the audit parents (mean absolute difference per position):", "",
          "| judge | identical repeat | P(T) polarity (canonicalized) | polarity signed |", "|---|---:|---:|---:|"]
    for j in J:
        L.append(f"| {j} | {f3(cc[j]['repeat_mad'])} | {f3(cc[j]['polarity_mad'])} | {f4(cc[j]['polarity_signed'])} |")

    L += ["", "## 2. Anonymous SAME/DIFFERENT recognition (primary recognition endpoint)", "",
          "R = (P + D)/2, where P compares the focal-source judge with the uninvolved judge and D compares the alternative-source judge "
          "with the uninvolved judge, using AUROC of the two-order mean P(SAME). R measures own-model involvement in source-relation "
          "discrimination, not self-authorship.", "",
          "| quantity | estimate | 95% CI (block bootstrap) | direction | bounded within margin |", "|---|---:|---|---|---|"]
    for k in ("R", "P", "D"):
        r = resmap[k]
        L.append(f"| {k} | {f4(r['estimate'])} | {_ci((r['ci_lower'], r['ci_upper']))} | {r['direction']} | {r['bounded_small']} |")
    L += ["", f"Support: {pr['support']}. Undefined bootstrap replicates: {pb['undefined_frac']:.3f}. Panel estimable: {pr['primary']['estimable']}.", "",
          "| crossover | P | D | R | items |", "|---|---:|---:|---:|---:|"]
    for key, t in pr["primary"]["crossovers"].items():
        L.append(f"| {key} | {f4(t['P'])} | {f4(t['D'])} | {f4(t['R'])} | {t['n_items']} |")
    c3p = pr["common3"]
    L += ["", "Common-three sensitivity: " + (", ".join(f"{k} {f4(c3p['panel'][k])}" for k in ("P", "D", "R", "D_legacy")) if c3p["panel"] else "not estimable")
          + "; first-orientation-only: " + (", ".join(f"{k} {f4(pr['first_orientation']['panel'][k])}" for k in ("P", "D", "R")) if pr["first_orientation"]["panel"] else "not estimable"), "",
          "Per-judge source-relation AUROC (all SAME vs all DIFFERENT pairs, two-order mean):", ""]
    for p in C.PROMPT_ORDER:
        L.append(f"- prompt {p}: " + ", ".join(f"{j} {f3(v)}" for j, v in pr["overall_auc"][p].items()))
    bias = pr["bias"]
    L += ["", "| prompt | judge | focal>alternative | role | AUC | SAME hit | false SAME | balanced acc |", "|---|---|---|---|---:|---:|---:|---:|"]
    for b in bias:
        L.append(f"| {b['prompt']} | {b['judge']} | {b['focal']}>{b['alternative']} | {b['role']} | {f3(b['auc'])} | {f3(b['same_hit_rate'])} | {f3(b['false_same_rate'])} | {f3(b['balanced_accuracy'])} |")
    L += ["", "Order effects (designated vs swapped presentation):", ""]
    for j, v in pr["order_effects"].items():
        if v:
            L.append(f"- {j}: mean |diff| {f3(v['mean_abs_diff'])}, signed {f4(v['mean_signed_designated_minus_swapped'])}, threshold disagreement {f3(v['threshold_disagreement'])}, share exactly 0.5 {f3(v['share_exact_0.5'])}")
    L += ["", "External pair baselines on the same pair IDs (fit on development only); overall SAME-vs-DIFFERENT AUROC:", ""]
    for p, res in pr["baselines"].items():
        L.append(f"- prompt {p}: " + ", ".join(f"{nm} {f3(v['overall_auc'])}" for nm, v in res.items()))
    pcs = out["pair_controls"]["summary"]
    L += ["", "Pair controls on the audit block (absolute difference):", ""] + [
        f"- {j}: identical repeat {f3(pcs[j]['repeat_abs'])}, P(DIFFERENT) polarity {f3(pcs[j]['polarity_abs'])} (signed {f4(pcs[j]['polarity_signed'])})" for j in J]
    L += ["", f"Time gaps between paired parents: {json.dumps(pr['time_gaps'])}", ""]

    L += ["## 3. Validity of every task", "", "| task / judge | valid / n |", "|---|---:|"]
    for k, v in out["validity"].items():
        L.append(f"| {k} | {v['valid']}/{v['n']} ({v['rate']}) |")
    L += ["", "## 4. Independent rescore", "", f"`rescore.py` recomputed the headline numbers from `scores.csv` with separate code: {json.dumps(out['rescore'])}", ""]
    L += ["## 5. Interpretation boundaries", "",
          "- 'Own model' means another independently queried instance of the same documented model configuration, not memory of the test string.",
          "- Three model configurations are three subjects. Thousands of calls are not thousands of independent models.",
          "- An unresolved direction is not evidence of no effect; a bounded-small interval is bounded only for this configuration and assay.",
          "- Similar training, brand associations, shared output preferences and skill-by-difficulty interactions remain possible explanations.",
          "- The pair task borrows a naming control from Loula et al.; it is not a Loula replication.", ""]
    (rd / "CORE_REPORT.md").write_text("\n".join(L) + "\n")

    R = ["# SPAR Phase 2 pilot: retained arms", "", f"Run `{rd.name}`, generated {out['generated_utc']}.", ""]
    n = out.get("named")
    if n:
        R += ["## Named attribution (secondary; small matched subset)", "",
              f"Parents judged: {n['n_items']}. Six per source x prompt at most; intervals are wide.", "",
              "| quantity | estimate | 95% CI |", "|---|---:|---|"]
        for k in ("R", "P", "D"):
            r = resmap[f"named {k}"]
            R.append(f"| named {k} | {f4(r['estimate'])} | {_ci((r['ci_lower'], r['ci_upper']))} |")
        R += ["", "| judge | prompt | n | choice counts | self-choice rate | balanced accuracy | multiclass Brier sum (uniform 0.667) |", "|---|---|---:|---|---:|---:|---:|"]
        for s in n["secondary"]:
            R.append(f"| {s['judge']} | {s['prompt']} | {s['n']} | {s['choice_counts']} | {f3(s['self_choice_rate'])} | {f3(s['balanced_accuracy'])} | {f3(s['multiclass_brier_sum'])} |")
        R += ["", "No-sequence priors (probability assigned to each candidate):", ""]
        for x in n["priors"]:
            R.append(f"- {x['judge']}/{x['prompt']}/order {x['order_index']}: {x['probs']}")
        if n.get("anonymous_on_named_blocks"):
            a = n["anonymous_on_named_blocks"]["panel"]
            R += ["", f"Anonymous P/D/R on the same named blocks (descriptive only; different task): {a}"]
        if n.get("fixtures"):
            R += ["", f"Named fixtures: {n['fixtures']}"]
        R.append("")
    else:
        R += ["Named attribution: pending (not run).", ""]
    h = out.get("historical")
    if h:
        R += ["## Historical Van Koevering replication check (gpt-3.5-turbo-0613, Azure)", "",
              "| prompt | temperature | valid / attempted | mean heads | first-H rate | switch rate | longest run |", "|---|---:|---|---:|---:|---:|---:|"]
        for c in h["summary"]:
            R.append(f"| {c['prompt']} ({c['split']}) | {c['temperature']} | {c['valid']}/{c['attempted']} | {c['mean_heads']} | {c['first_H_rate']} | {c['switch_rate']} | {c['mean_longest_run']} |")
        R += ["", "First flip heads rate vs the paper's Table 2 (GPT-3.5; the paper's model version may differ from 0613):", "",
              "| prompt | temperature | n valid | observed | paper |", "|---|---:|---:|---:|---:|"]
        for c in h["first_flip_vs_paper"]:
            R.append(f"| {c['prompt']} | {c['temperature']} | {c['n_valid']} | {f3(c['first_flip_H_rate'])} | {c['paper_table2_first_flip_H']:.2f} |")
        R += ["", "No formal equivalence is claimed.", ""]
    else:
        R += ["Historical check: pending.", ""]
    R += ["## Seven-to-one LASSO (`history7_runs14_v1`; offline; predicts flips, not identity)", "",
          "Raw linear MSE averaged within parent then across parents. Improvement = baseline MSE minus LASSO MSE (positive = LASSO better).", "",
          "| generator | prompt | dev parents | alpha | test parents | LASSO MSE | vs 0.5 | vs train mean | vs position mean [95% CI] |", "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    def lrow(name, key, d):
        fit, ev = d["fit"], d["eval"]
        if ev.get("status") != "ok":
            return f"| {name} | {key} | {fit.get('n_dev_parents')} | | | {ev.get('status')} | | | |"
        s, im, ci = ev["summary"], ev["improvement"], ev["improvement_ci95"]
        return (f"| {name} | {key} | {fit['n_dev_parents']} | {fit['alpha']:.4g} | {ev['n_test_parents']} | {s['mse_lasso_raw']:.4f} | "
                f"{im['vs_half']:+.4f} | {im['vs_train_mean']:+.4f} | {im['vs_position_mean']:+.4f} {_ci(ci['vs_position_mean'])} |")
    for key, d in out["lasso_core"].items():
        g, p = key.split("|")
        R.append(lrow(g, p, d))
    if h:
        for key, d in h["lasso"].items():
            R.append(lrow("gpt35_0613", key, d))
    R += ["", "An independent P(H)=0.9 source has optimal constant error 0.09, so error below 0.25 alone is not sequential knowledge. "
          "Predictability is not source recognition and is not self-awareness.", ""]
    (rd / "RETAINED_ARMS_REPORT.md").write_text("\n".join(R) + "\n")
    S = ["# Stage 2 report index", "", "- `CORE_REPORT.md`: H4 readout, anonymous R/P/D, validity, rescore.",
         "- `RETAINED_ARMS_REPORT.md`: named arm, historical check, LASSO.", "- `RESOLUTION_TABLE.csv`, `contrasts.json`, `scores.csv`, `comparison_masks.json`.",
         "- Stage 1: `STAGE1_REPORT.md`, `PRECISION_PLAN.md`, `DECISION_MEMO.md`, `headroom_review.json`, `freeze.json`.",
         "- Provenance: `calls.jsonl` (every request/response), `amendments.jsonl`, `approvals.jsonl`, `PROGRESS.md`, `checksums.sha256`.", ""]
    (rd / "STAGE2_REPORT.md").write_text("\n".join(S))
