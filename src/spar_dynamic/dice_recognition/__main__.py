"""LOULA_DICE_RECOGNITION pilot CLI. Phases run in order; each refuses to start unless the previous gate passed.

  python -m spar_dynamic.dice_recognition dryrun     # zero API calls: frozen protocol, manifest, planned ids
  python -m spar_dynamic.dice_recognition preflight  # 4 generations + 2 judgments per model (labelled, not pooled)
  python -m spar_dynamic.dice_recognition corpus     # 50 valid sequences per model (cap 75 attempts), split
  python -m spar_dynamic.dice_recognition classify   # development-only discriminability gate (AUC >= 0.65)
  python -m spar_dynamic.dice_recognition judge      # 240 held-out A/B judgments (only if the gate passed)
  python -m spar_dynamic.dice_recognition analyse    # paired analyses, classifier benchmark, figures
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import subprocess
import sys

import numpy as np

import repo_paths
from spar_dynamic.dice_recognition import (analysis as A, classifier as K, client as CL, config as C, corpus as CO,
                                           features as F, prompts as P, trials as T)

EXP = str(repo_paths.T1_EXP["dice_recognition"])
PRE, COR, JUD, ANA = (os.path.join(EXP, d) for d in ("api_preflight", "corpus", "judgments", "analysis"))
SYNTHETIC_PAIR = ("1 2 3 4 5 6 1 2 3 4", "6 5 4 3 2 1 6 5 4 3")      # preflight only; never a stimulus


def _client():
    from openai import OpenAI
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set (load .env first)")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, max_retries=0, timeout=120.0)


def _ledger():
    os.makedirs(EXP, exist_ok=True)
    return CL.Ledger(os.path.join(EXP, "cost_ledger.json"))


def _jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")] if os.path.exists(path) else []


def _read_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def dryrun():
    os.makedirs(EXP, exist_ok=True)
    with open(os.path.join(EXP, "prompts_frozen.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(P.render_frozen())
    man = dict(tag=C.TAG, created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
               git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
               models=C.MODELS, generation=C.GENERATION, judgment=C.JUDGMENT,
               request_examples={m: {k: v for k, v in CL.request_body(m, P.generation_prompt(), "generation").items() if k != "messages"} for m in C.SOURCES},
               corpus=dict(n_valid_per_model=C.N_VALID_PER_MODEL, max_attempts_per_model=C.MAX_ATTEMPTS_PER_MODEL,
                           n_dev=C.N_DEV, n_holdout=C.N_HOLDOUT, split_rule=CO.__doc__.split("Split (prespecified):")[1].strip()),
               gates=dict(auc_gate=C.AUC_GATE, cv_folds=C.CV_FOLDS, n_permutations=C.N_PERMUTATIONS,
                          classifier_features=F.CLASSIFIER_FEATURES),
               seeds=dict(gen_order=C.GEN_ORDER_SEED, split=C.SPLIT_SEED, pair=C.PAIR_SEED, trial_order=C.TRIAL_ORDER_SEED,
                          permutation=C.PERMUTATION_SEED, bootstrap=C.BOOTSTRAP_SEED),
               cost_cap_usd=C.COST_CAP_USD, prompt_sha256=dict(generation=P.sha256(P.GEN), j_self=P.sha256(P.J_SELF), j_named=P.sha256(P.J_NAMED)),
               planned_generation_schedule=[f"{m}#{i}" for m, i in CO.schedule()],
               planned_judgment_calls=C.N_HOLDOUT * 2 * 2 * len(P.CONDITIONS))
    with open(os.path.join(EXP, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    print(json.dumps(dict(exp=EXP, planned_generation_attempts=len(man["planned_generation_schedule"]),
                          planned_judgment_calls=man["planned_judgment_calls"], api_calls_made=0)))


def preflight():
    oai, led = _client(), _ledger()
    os.makedirs(PRE, exist_ok=True)
    path = os.path.join(PRE, "raw_attempts.jsonl")
    if os.path.exists(path):
        raise SystemExit("preflight already run; inspect api_preflight/ (delete only with approval)")
    rows = []
    for m in C.SOURCES:
        for i in range(1, 5):
            r = CL.call(oai, led, m, P.generation_prompt(), "generation")
            ok, faces = CO.is_valid(r)
            rows.append(dict(r, check=f"generation_{i}", valid=ok, faces=faces))
        for cond in ("self", f"named_{m}"):
            r = CL.call(oai, led, m, P.judgment_prompt(cond, *SYNTHETIC_PAIR), "judgment")
            ch = P.parse_choice(r.get("content")) if r.get("ok") else None
            rows.append(dict(r, check=f"judgment_{cond}", valid=ch is not None and CL.thinking_clean(r) and CL.provider_ok(r), choice=ch))
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    g = {}
    for m in C.SOURCES:
        rs = [r for r in rows if r["model_key"] == m]
        g[f"{m}_provider_pinned"] = all(r.get("ok") and CL.provider_ok(r) for r in rs)
        g[f"{m}_no_thinking"] = all(CL.thinking_clean(r) for r in rs)
        if m == "qwen":
            g["qwen_reasoning_tokens_reported_zero"] = all(r.get("reasoning_tokens") == 0 for r in rs)
        g[f"{m}_generation_valid_3_of_4"] = sum(r["valid"] for r in rs if r["check"].startswith("generation")) >= 3
        g[f"{m}_judgment_strict_AB_2_of_2"] = all(r["valid"] for r in rs if r["check"].startswith("judgment"))
    res = dict(gates=g, overall="PASS" if all(g.values()) else "FAIL", spent_usd=led.spent,
               responses=[dict(model=r["model_key"], check=r["check"], content=r.get("content"), valid=r["valid"],
                               served_provider=r.get("served_provider"), reasoning_tokens=r.get("reasoning_tokens"),
                               finish=r.get("finish_reason"), cost=r.get("cost_usd"),
                               error=(r["attempts"][-1].get("error") if not r.get("ok") else None)) for r in rows])
    with open(os.path.join(PRE, "preflight_summary.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=1))


def _require(path, key, label):
    if not os.path.exists(path) or json.load(open(path)).get(key) not in ("PASS", True):
        raise SystemExit(f"STOP: {label} has not passed ({path})")


def corpus():
    _require(os.path.join(PRE, "preflight_summary.json"), "overall", "API preflight")
    valid = CO.collect(_client(), _ledger(), COR)
    stim = CO.build_stimuli(COR)
    ok, dup = CO.split(stim) if all(valid.get(s, 0) >= C.N_VALID_PER_MODEL for s in C.SOURCES) else (False, {})
    CO.write_csv(os.path.join(COR, "stimuli.csv"), stim)
    status = dict(valid_counts=valid, target=C.N_VALID_PER_MODEL, split_ok=ok, duplicates=dup,
                  overall="PASS" if ok else "FAIL",
                  reason=None if ok else ("fewer than 50 valid sequences within 75 attempts" if not dup
                                          else "exact 20/20 holdout not reachable under the duplicate-group rule"))
    rows = _jsonl(os.path.join(COR, "raw_attempts.jsonl"))
    status["attempts"] = {m: sum(r["model_key"] == m for r in rows) for m in C.SOURCES}
    status["invalid_reasons"] = {m: dict(__import__("collections").Counter(r["invalid_reason"] for r in rows if r["model_key"] == m and not r["valid"])) for m in C.SOURCES}
    with open(os.path.join(COR, "corpus_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, default=str)
    print(json.dumps(status, indent=1, default=str))


def classify():
    _require(os.path.join(COR, "corpus_status.json"), "overall", "corpus")
    stim = _read_csv(os.path.join(COR, "stimuli.csv"))
    feats = [F.features([int(s[f"f{k}"]) for k in range(1, 11)]) for s in stim]
    rows = [dict(stimulus_id=s["stimulus_id"], source=s["source"], split=s["split"], sequence=s["sequence"],
                 duplicate_group=s["duplicate_group"], **f) for s, f in zip(stim, feats)]
    CO.write_csv(os.path.join(COR, "phenotype_features.csv"), rows)
    CO.write_csv(os.path.join(COR, "development.csv"), [s for s in stim if s["split"] == "development"])
    CO.write_csv(os.path.join(COR, "heldout.csv"), [s for s in stim if s["split"] == "heldout"])
    dev = [r for r in rows if r["split"] == "development"]
    X = np.array([[r[k] for k in F.CLASSIFIER_FEATURES] for r in dev], float)
    y = np.array([1 if r["source"] == "qwen" else 0 for r in dev])
    g = np.array([int(r["duplicate_group"]) for r in dev])
    res = K.evaluate(X, y, g, F.CLASSIFIER_FEATURES.index("switch_frac"))
    CO.write_csv(os.path.join(COR, "classifier_cv.csv"),
                 [dict(stimulus_id=r["stimulus_id"], source=r["source"], duplicate_group=r["duplicate_group"], oof_p_qwen=s)
                  for r, s in zip(dev, res["oof_scores"])])
    final = K.make_model().fit(X, y)                     # frozen for the held-out benchmark
    sc, lr = final.named_steps["standardscaler"], final.named_steps["logisticregression"]
    res["frozen_model"] = dict(features=F.CLASSIFIER_FEATURES, mean=sc.mean_.tolist(), scale=sc.scale_.tolist(),
                               coef=lr.coef_[0].tolist(), intercept=float(lr.intercept_[0]))
    res["overall"] = "PASS" if res["gate_pass"] else "FAIL"
    with open(os.path.join(COR, "classifier_gate.json"), "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if k != "oof_scores"}, f, indent=2)
    A.corpus_figures(stim, feats, res, y, os.path.join(ANA, "figures"))
    with open(os.path.join(COR, "classifier_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(_classifier_report(res))
    print(json.dumps({k: v for k, v in res.items() if k not in ("oof_scores", "frozen_model")}, indent=1))


def _classifier_report(r):
    b, p = r["benchmarks"], r["permutation"]
    return (f"# Development-only source discriminability (gate)\n\n"
            f"Logistic regression (L2, C=1) on {', '.join(F.CLASSIFIER_FEATURES)}; standardized within each training fold; "
            f"grouped stratified {C.CV_FOLDS}-fold CV (identical strings share a fold). n = {r['n']} development sequences, "
            f"{r['n_unique_groups']} unique strings.\n\n"
            f"| Measure | Value |\n|---|---|\n| **CV ROC AUC (gate statistic)** | **{r['cv_auc']:.3f}** |\n"
            f"| 95% bootstrap over unique-string groups | {r['auc_bootstrap_ci95_by_group'][0]:.3f}–{r['auc_bootstrap_ci95_by_group'][1]:.3f} |\n"
            f"| Balanced accuracy (threshold 0.5) | {r['balanced_accuracy']:.3f} |\n"
            f"| Confusion [[Qwen→Qwen, Qwen→Mistral], [Mistral→Qwen, Mistral→Mistral]] | {r['confusion']} |\n"
            f"| Majority / chance | AUC 0.5, balanced accuracy 0.5 |\n"
            f"| Nearest-centroid CV AUC | {b['nearest_centroid_cv_auc']:.3f} |\n"
            f"| Switch-fraction-only CV AUC | {b['switch_fraction_only_cv_auc']:.3f} |\n"
            f"| Label permutations ({p['n']}): mean / 95th percentile AUC | {p['mean']:.3f} / {p['p95']:.3f} |\n"
            f"| Permutation p (AUC ≥ observed) | {p['p_value_ge_observed']:.4f} |\n\n"
            f"**Gate (AUC ≥ {C.AUC_GATE}): {'PASS: recognition judgments may run' if r['gate_pass'] else 'FAIL: stop before recognition'}.** "
            "The threshold is an operational feasibility screen, not a significance test.\n")


def judge():
    _require(os.path.join(COR, "classifier_gate.json"), "overall", "classifier gate")
    held = _read_csv(os.path.join(COR, "heldout.csv"))
    pairs = T.make_pairs(held)
    trials = T.make_trials(pairs)
    os.makedirs(JUD, exist_ok=True)
    CO.write_csv(os.path.join(JUD, "pairs.csv"), pairs)
    CO.write_csv(os.path.join(JUD, "trials.csv"), [{k: v for k, v in t.items() if k != "prompt"} for t in trials])
    T.run(_client(), _ledger(), trials, JUD)


def analyse():
    gate = json.load(open(os.path.join(COR, "classifier_gate.json")))
    held = _read_csv(os.path.join(COR, "heldout.csv"))
    fm = gate["frozen_model"]

    def p_qwen(seq):
        f = F.features([int(x) for x in seq.split()])
        z = (np.array([f[k] for k in fm["features"]]) - np.array(fm["mean"])) / np.array(fm["scale"])
        return float(1 / (1 + np.exp(-(z @ np.array(fm["coef"]) + fm["intercept"]))))
    from sklearn.metrics import roc_auc_score
    y = [1 if s["source"] == "qwen" else 0 for s in held]
    sc = [p_qwen(s["sequence"]) for s in held]
    pairs = _read_csv(os.path.join(JUD, "pairs.csv"))
    cls_pair = {p["pair_id"]: (1.0 if p_qwen(p["qwen_seq"]) > p_qwen(p["mistral_seq"]) else 0.5 if p_qwen(p["qwen_seq"]) == p_qwen(p["mistral_seq"]) else 0.0)
                for p in pairs}
    resp = _jsonl(os.path.join(JUD, "raw_attempts.jsonl"))
    CO.write_csv(os.path.join(JUD, "responses.csv"),
                 [{k: r.get(k) for k in ("trial_id", "judge", "condition", "pair_id", "orientation", "A_source", "B_source",
                                         "target_source", "correct", "content", "choice", "valid", "is_correct",
                                         "served_provider", "reasoning_tokens", "cost_usd", "response_id")} for r in resp])
    summ = A.summarise_judgments(resp, pairs, cls_pair)
    summ["classifier_heldout"] = dict(auc=float(roc_auc_score(y, sc)), pair_accuracy=float(np.mean(list(cls_pair.values()))),
                                      per_pair=cls_pair)
    summ["spent_usd"] = json.load(open(os.path.join(EXP, "cost_ledger.json")))["spent_usd"]
    os.makedirs(ANA, exist_ok=True)
    with open(os.path.join(ANA, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=2)
    pt = summ["point"]
    CO.write_csv(os.path.join(ANA, "paired_accuracy.csv"),
                 [dict(judge=j, condition=c, pair_averaged_accuracy=pt[f"{j}|{c}"], ci95=summ["ci95_pair_bootstrap"][f"{j}|{c}"],
                       **summ["per_cell"][f"{j}|{c}"]) for j in C.SOURCES for c in P.CONDITIONS])
    CO.write_csv(os.path.join(ANA, "judge_by_target.csv"),
                 [dict(judge=j, asked_about_qwen=pt[f"{j}|named_qwen"], asked_about_mistral=pt[f"{j}|named_mistral"],
                       self=pt[f"{j}|self"]) for j in C.SOURCES])
    A.judgment_figures(summ, os.path.join(ANA, "figures"))
    print(json.dumps(dict(point=pt, ci=summ["ci95_pair_bootstrap"], classifier_heldout={k: v for k, v in summ["classifier_heldout"].items() if k != "per_pair"},
                          per_cell={k: {kk: vv for kk, vv in v.items() if kk != "confusion_truth_by_choice"} for k, v in summ["per_cell"].items()},
                          spent=summ["spent_usd"]), indent=1))


if __name__ == "__main__":
    {"dryrun": dryrun, "preflight": preflight, "corpus": corpus, "classify": classify, "judge": judge,
     "analyse": analyse}[sys.argv[1]]()
