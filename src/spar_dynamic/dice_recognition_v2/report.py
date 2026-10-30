"""Offline analysis for v2 (`analyse`): reads every stage that ran, labels the rest NOT_RUN, writes
analysis/summary.json, CSV tables, the six figures, and prints the investigator readout."""

from __future__ import annotations

import collections
import json
import os

import numpy as np

from spar_dynamic.dice_recognition_v2 import analysis as A, config as C, corpus as CO

NAME = {m: C.MODELS[m]["display"] for m in C.SOURCES}
SHORT = {"qwen": "Qwen", "mistral": "Mistral"}


def _jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []


def _load(p):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def _true_counts(r):
    from spar_dynamic.dice_recognition_v2.synthetic import n_repeats, n_sixes
    f = n_sixes if r["task"] == "MORE_SIXES" else n_repeats
    return {s: f([int(x) for x in r[f"{s}_content"].split()]) for s in "AB"}


def _evidence(resps, counts=False):
    rs = [r for r in resps if r["fmt"] == "brief" and r.get("content")]
    if not rs:
        return None
    ev = [A.evidence_check(r, _true_counts(r) if counts and r.get("task") in ("MORE_SIXES", "MORE_REPEATS") else None) for r in rs]
    c = collections.Counter(e["claim"] for e in ev)
    return dict(n=len(rs), cites_feature=float(np.mean([e["cites_feature"] for e in ev])), count_claims=dict(c))


def run(EXP, D, old_pairs, fm):
    out = dict(tag=C.TAG, stages={})
    fig = os.path.join(D["analysis"], "figures")
    os.makedirs(fig, exist_ok=True)
    ledger = _load(os.path.join(EXP, "cost_ledger.json")) or {}

    # ---------------------------------------------------------------------------------------- Stage A --
    cal = _jsonl(os.path.join(D["calibration"], "raw_attempts.jsonl"))
    if not cal:
        out["stages"]["A"] = "NOT_RUN"
    else:
        gate = A.calibration_gate(cal)
        ev = {f"{j}|{t}": _evidence([r for r in cal if r["judge"] == j and r["task"] == t], counts=True)
              for j in C.SOURCES for t in C.CAL_TASKS}
        out["stages"]["A"] = dict(gate=gate, brief_evidence=ev)
        A.fig_calibration(gate, os.path.join(fig, "1_calibration.png"))
        CO.write_csv(os.path.join(D["calibration"], "gate_table.csv"),
                     [dict(judge=r["judge"], fmt=r["fmt"], validity=r["validity"], PASS=r["PASS"],
                           **{f"{t}_{k}": r[t][k] for t in C.CAL_TASKS for k in ("correct", "consistent_pairs", "A_rate", "pass_")})
                      for r in gate.values()])

    # ---------------------------------------------------------------------------------------- Stage B --
    scr = _jsonl(os.path.join(D["elicitation_screen"], "raw_attempts.jsonl"))
    cls_old = {p["pair_id"]: A.classifier_pair([p["qwen_seq"]], [p["mistral_seq"]], fm) for p in old_pairs}
    if not scr:
        out["stages"]["B"] = "NOT_RUN"
    else:
        key = lambda r: f"{r['judge']}|{r['fmt']}|{r['frame']}"
        cells = A.unit_table(scr, key)
        summ = A.cell_summary(cells)
        series = {f"acc|{c}": v for c, v in A.series_of(cells, "acc").items()}
        series.update({f"cons|{c}": v for c, v in A.series_of(cells, "consistent").items()})
        series["cls"] = cls_old
        boot = A.bootstrap(series, [p["pair_id"] for p in old_pairs])
        for c in summ:
            rs = [r for r in scr if key(r) == c and r["valid"]]
            pref = {u: ("qwen" if v == 1 else "mistral" if v == 0 else None) for u, v in cls_old.items()}
            agree = [A.chosen(r) == pref[r["unit_id"]] for r in rs if pref[r["unit_id"]]]
            summ[c].update(acc_ci=[boot[f"acc|{c}"]["lo"], boot[f"acc|{c}"]["hi"]],
                           classifier_agreement=float(np.mean(agree)) if agree else None,
                           evidence=_evidence([r for r in scr if key(r) == c]),
                           exact_outputs=dict(collections.Counter((r.get("content") or "")[-12:] for r in scr if key(r) == c).most_common(4)))
        out["stages"]["B"] = dict(cells=summ, classifier_pair_accuracy=boot["cls"])
        keys = sorted(summ, key=lambda k: (k.split("|")[0] != "qwen", k))
        A.fig_cells(summ, keys, [k.replace("|", " ") for k in keys], os.path.join(fig, "2_elicitation_screen.png"),
                    "Stage B: Experiment 22 pairs, one 10-roll line per sample",
                    ci={k: boot[f"acc|{k}"] for k in keys})
        CO.write_csv(os.path.join(D["elicitation_screen"], "diagnostics.csv"),
                     [dict(cell=k, **{kk: vv for kk, vv in v.items() if kk not in ("evidence", "exact_outputs")}) for k, v in summ.items()])

    # ---------------------------------------------------------------------------------------- corpus --
    fams = _load(os.path.join(D["corpus_v2"], "families.json"))
    if not fams:
        out["stages"]["C"] = out["stages"]["D"] = "NOT_RUN"
        return _finish(out, EXP, D, ledger)
    st = _load(os.path.join(D["corpus_v2"], "corpus_status.json"))
    recs = CO.records(D["corpus_v2"])
    phen = {m: A.phenotype([r["sequence"] for r in recs[m][:C.N_VALID_PER_SOURCE]]) for m in C.SOURCES}
    fids = [f["family_id"] for f in fams]
    series = {f"cls|K{K}": {f["family_id"]: A.classifier_pair(f["qwen"][:K], f["mistral"][:K], fm) for f in fams} for K in C.DOSES}
    out["corpus"] = dict(status={k: v for k, v in st.items()}, phenotype=phen)

    # ---------------------------------------------------------------------------------------- Stage C --
    dose = _jsonl(os.path.join(D["recognition_dose"], "dose_raw_attempts.jsonl"))
    named = _jsonl(os.path.join(D["recognition_dose"], "named_raw_attempts.jsonl"))
    d1 = _jsonl(os.path.join(D["familiarization"], "d1_raw_attempts.jsonl"))
    d2 = _jsonl(os.path.join(D["familiarization"], "d2_live_sessions.jsonl"))
    judges = sorted({r["judge"] for r in dose}, key=C.SOURCES.index)
    derived = {}
    summ_all = {}
    if dose:
        kd = lambda r: f"{r['judge']}|{r['frame']}|K{r['K']}"
        cells = A.unit_table(dose, kd)
        summ_all.update({f"dose|{k}": v for k, v in A.cell_summary(cells).items()})
        series.update({f"acc|{c}": v for c, v in A.series_of(cells, "acc").items()})
        series.update({f"cons|{c}": v for c, v in A.series_of(cells, "consistent").items()})
        for j in judges:
            for fr in ("AUTH", "TYP"):
                for m in ("acc", "cons"):
                    for a_, b_ in ((3, 1), (5, 1), (5, 3)):
                        derived[f"{m}_diff|{j}|{fr}|K{a_}-K{b_}"] = (lambda x, j=j, fr=fr, m=m, a_=a_, b_=b_:
                                                                   x[f"{m}|{j}|{fr}|K{a_}"] - x[f"{m}|{j}|{fr}|K{b_}"])
            derived[f"acc_diff|{j}|K5|AUTH-TYP"] = lambda x, j=j: x[f"acc|{j}|AUTH|K5"] - x[f"acc|{j}|TYP|K5"]
    if named:
        cn = A.unit_table(named, lambda r: f"named|{r['judge']}|{r['target_source']}")
        cno = A.unit_table(named, lambda r: f"named|{r['judge']}|{r['target_source']}|{r['name_order']}")
        summ_all.update(A.cell_summary(cno))
        summ_all.update({k: dict(v, orientation_consistency=None) for k, v in A.cell_summary(cn).items()})
        series.update({f"acc|{c}": v for c, v in A.series_of(cn, "acc").items()})
        series.update({f"acc|{c}": v for c, v in A.series_of(cno, "acc").items()})
        series.update({f"cons|{c}": v for c, v in A.series_of(cno, "consistent").items()})
        for j in judges:
            for t in C.SOURCES:
                derived[f"name_order_effect|{j}|{t}|QM-MQ"] = (lambda x, j=j, t=t: x[f"acc|named|{j}|{t}|QM"] - x[f"acc|named|{j}|{t}|MQ"])
            derived[f"self_minus_named_own|{j}"] = lambda x, j=j: x[f"acc|{j}|AUTH|K5"] - x[f"acc|named|{j}|{j}"]
        derived["S_named"] = lambda x: 0.5 * ((x["acc|named|qwen|qwen"] - x["acc|named|mistral|qwen"])
                                              + (x["acc|named|mistral|mistral"] - x["acc|named|qwen|mistral"]))
        # does the letter follow the position of the target's name in the opening sentence?
        pos = collections.defaultdict(list)
        for r in named:
            if r["valid"]:
                first = "qwen" if r["name_order"] == "QM" else "mistral"
                pos[r["judge"]].append(r["choice"] == ("A" if r["target_source"] == first else "B"))
        out["named_letter_follows_name_position"] = {j: float(np.mean(v)) for j, v in pos.items()}
    if d1:
        ce = A.unit_table(d1, lambda r: f"exp|{r['judge']}|{r['exposure']}")
        summ_all.update(A.cell_summary(ce))
        series.update({f"acc|{c}": v for c, v in A.series_of(ce, "acc").items()})
        series.update({f"cons|{c}": v for c, v in A.series_of(ce, "consistent").items()})
        for j in judges:
            for m in ("acc", "cons"):
                derived[f"{m}_exp|{j}|OWN-NONE"] = lambda x, j=j, m=m: x[f"{m}|exp|{j}|OWN"] - x[f"{m}|{j}|AUTH|K5"]
                derived[f"{m}_exp|{j}|OWN-OTHER"] = lambda x, j=j, m=m: x[f"{m}|exp|{j}|OWN"] - x[f"{m}|exp|{j}|OTHER"]
                derived[f"{m}_exp|{j}|OTHER-NONE"] = lambda x, j=j, m=m: x[f"{m}|exp|{j}|OTHER"] - x[f"{m}|{j}|AUTH|K5"]
    if d2:
        cl = A.unit_table(d2, lambda r: f"live|{r['judge']}")
        summ_all.update(A.cell_summary(cl))
        series.update({f"acc|{c}": v for c, v in A.series_of(cl, "acc").items()})
        series.update({f"cons|{c}": v for c, v in A.series_of(cl, "consistent").items()})
        lg = [g for r in d2 for g in r["live_generations"]]
        out["live_generation_validity"] = dict(n=len(lg), valid=sum(g["valid"] for g in lg))
    boot = A.bootstrap(series, fids, derived)
    out["family_bootstrap"] = boot
    out["cells"] = summ_all
    out["evidence_brief"] = {s: _evidence(rs) for s, rs in (("dose", dose), ("named", named), ("exposure", d1), ("live", d2)) if rs}
    out["stages"]["C"] = "COMPLETE" if dose and named else ("PARTIAL" if dose else "NOT_RUN")
    out["stages"]["D1"] = "COMPLETE" if d1 else "NOT_RUN"
    out["stages"]["D2"] = "COMPLETE" if d2 else "NOT_RUN"
    sens = [f["family_id"] for f in fams if f["family_id"] not in st["duplicates"]["families_sharing_any_string_across_sources"]]
    if len(sens) < len(fids):
        out["sensitivity_excluding_cross_source_shared_families"] = dict(
            n_families=len(sens), **{k: v for k, v in A.bootstrap(series, sens, derived).items()
                                     if k.startswith(("acc|", "cls|", "S_named"))})

    # ------------------------------------------------------------------------------------------ figures --
    cls_by_k = {K: boot[f"cls|K{K}"] for K in C.DOSES}
    A.fig_corpus(phen, cls_by_k, os.path.join(fig, "3_corpus_and_classifier.png"))
    if dose:
        A.fig_dose(boot, cls_by_k, judges, os.path.join(fig, "4_evidence_dose.png"))
    if named:
        keys, labs, cols = [], [], []
        for j in judges:
            for t in C.SOURCES:
                for o in ("QM", "MQ"):
                    keys.append(f"acc|named|{j}|{t}|{o}")
                    labs.append(f"{SHORT[j]} judge: which is {SHORT[t]}? ({'Qwen' if o == 'QM' else 'Mistral'} named first)")
                    cols.append(A.COL[j])
            keys.append(f"acc|{j}|AUTH|K5")
            labs.append(f"{SHORT[j]} judge: self (AUTH)")
            cols.append(A.COL[j])
        A.fig_bars(boot, keys, labs, cols, os.path.join(fig, "5_named_and_self_K5.png"),
                   f"Stage C named control, K=5.  S_named = {boot.get('S_named', {}).get('point')}")
    if d1:
        keys, labs, cols = [], [], []
        for j in judges:
            for k, lab in ((f"acc|{j}|AUTH|K5", "none"), (f"acc|exp|{j}|OWN", "own exemplars"),
                           (f"acc|exp|{j}|OTHER", "other-model exemplars")) + (((f"acc|live|{j}", "D2 live (TYP)"),) if d2 else ()):
                keys.append(k)
                labs.append(f"{SHORT[j]}: {lab}")
                cols.append(A.COL[j])
        A.fig_bars(boot, keys, labs, cols, os.path.join(fig, "6_familiarization.png"),
                   "Stage D: K=5 AUTH with supplied exemplars (D2 live is a separate, history-conditioned arm)")
    rows = []
    for k, v in sorted(boot.items()):
        rows.append(dict(estimand=k, point=v["point"], lo=v["lo"], hi=v["hi"]))
    CO.write_csv(os.path.join(D["analysis"], "family_bootstrap_estimates.csv"), rows)
    CO.write_csv(os.path.join(D["analysis"], "cell_diagnostics.csv"), [dict(cell=k, **v) for k, v in summ_all.items()])
    return _finish(out, EXP, D, ledger)


def _finish(out, EXP, D, ledger):
    out["spend"] = ledger
    with open(os.path.join(D["analysis"], "summary.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(readout(out))
    return out


def _f(v, d=2):
    return "—" if v is None else f"{v:.{d}f}"


def readout(o):
    L = []
    if isinstance(o["stages"].get("A"), dict):
        L.append("Calibration: " + "; ".join(f"{SHORT[r['judge']]} {r['fmt']} {'PASS' if r['PASS'] else 'FAIL'}"
                                            for r in o["stages"]["A"]["gate"].values()))
    if isinstance(o["stages"].get("B"), dict):
        L.append("Elicitation screen (acc / consistency / A-rate): " + "; ".join(
            f"{k} {_f(v['accuracy'])}/{_f(v['orientation_consistency'])}/{_f(v['A_rate'])}" for k, v in o["stages"]["B"]["cells"].items()))
    b = o.get("family_bootstrap", {})
    if b:
        L.append("Classifier pair acc K1/K3/K5: " + " ".join(_f(b[f"cls|K{K}"]["point"]) for K in C.DOSES))
        for k in sorted(k for k in b if k.startswith("acc|") and "|K" in k and "named" not in k):
            L.append(f"  {k}: {_f(b[k]['point'])} [{_f(b[k]['lo'])}, {_f(b[k]['hi'])}]  cons {_f(b.get(k.replace('acc|', 'cons|'), {}).get('point'))}")
        for k in sorted(k for k in b if k.startswith(("acc|named", "S_named", "self_minus", "acc|exp", "acc_exp", "acc|live", "name_order"))):
            L.append(f"  {k}: {_f(b[k]['point'])} [{_f(b[k]['lo'])}, {_f(b[k]['hi'])}]")
    L.append(f"Stages: {json.dumps({k: (v if isinstance(v, str) else 'RUN') for k, v in o['stages'].items()})}")
    L.append(f"Spend: ${o['spend'].get('spent_usd', 0):.4f} over {o['spend'].get('calls', 0)} charged calls")
    return "\n".join(L)
