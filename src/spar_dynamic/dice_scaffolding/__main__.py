"""Experiment 33 command line: freeze -> dryrun -> validate -> collect -> checks -> analyse.

Usage (repo root): PYTHONPATH=src python -m spar_dynamic.dice_scaffolding <phase> [--phase core|extensions|all] [--model qwen|mistral]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path

from spar_dynamic.dice_31_32 import stimuli as S31
from spar_dynamic.dice_scaffolding import config as C
from spar_dynamic.dice_scaffolding import design as D
from spar_dynamic.dice_scaffolding.gpu import canonical_sha, code_sha, row_id

FROZEN = ("PROTOCOL.md", "prompts_frozen.md", "design_forecasts.csv", "design_histories.csv", "design_direct.csv", "design_letters.csv",
          "manifest.json")


def to_csv(rows, cols=None) -> str:
    cols = cols or list(dict.fromkeys(k for r in rows for k in r))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict, tuple)) else v) for k, v in r.items()})
    return buf.getvalue()


def manifest() -> dict:
    return dict(tag=C.TAG, design_source=C.DESIGN_SOURCE, status="frozen before GPU collection", counts=D.counts(), expected=C.EXPECTED,
                families=[dict(rank=r, split=s, path=D.seq(p)) for r, s, p in D.families()],
                archive_selection=[dict(source=p["source"], seed=p["seed"], path=D.seq(p["path"])) for p in D.archive_selection()],
                pairs=dict(development=C.DEV_PAIRS, confirmation=C.CONF_PAIRS), subset_words=C.SUBSET_WORDS, strata={k: list(v) for k, v in C.STRATA.items()},
                models={m: dict(model_id=C.MODEL[m]["model_id"], revision=C.MODEL[m]["revision"], face_ids=C.MODEL[m]["face_ids"],
                                separator_id=C.SEPARATOR_ID[m]) for m in C.MODELS},
                bootstrap=dict(draws=C.BOOT_B, seed=C.BOOT_SEED, generator="PCG64"), prompt_manifest_sha256=D.prompt_manifest_sha(),
                stop_rules=dict(scorer_tol_logp=C.SCORER_TOL_LOGP, floor_stop_p=C.FLOOR_STOP_P, low_mass_flag=C.LOW_MASS), gpu_cap_usd=C.GPU_CAP_USD)


def built() -> dict:
    strip = [{k: v for k, v in r.items() if k != "prompt"} for r in D.design()]
    hist = D.constructed() + D.natural() + [dict(bank="opening", history=h, k=len(D.faces_of(h)) + 1) for h in D.opening()] + \
        [dict(bank="worked", history=D.seq(h), k=len(h) + 1, overlaps_constructed=D.seq(h) in {r["history"] for r in D.constructed()}) for h in C.WORKED]
    direct = [dict(phase=p, **{k: v for k, v in j.items() if k != "prompt"}) for p in C.PHASES for j in D.direct_jobs(p)]
    letters = [{k: v for k, v in i.items() if k != "prompt"} for i in D.association_items() + D.fact_items()]
    return {"prompts_frozen.md": D.render_frozen(), "design_forecasts.csv": to_csv(strip), "design_histories.csv": to_csv(hist),
            "design_direct.csv": to_csv(direct), "design_letters.csv": to_csv(letters), "manifest.json": json.dumps(manifest(), indent=2) + "\n"}


def archived_inputs() -> dict:
    fs = [C.EXP28_MAIN / m / "raw_attempts.jsonl" for m in C.MODELS] + [C.CORPUS27 / m / "sampled.jsonl" for m in C.MODELS]
    return {f"{p.parts[-4]}/{p.parts[-3]}/{p.parts[-2]}/{p.name}": canonical_sha(p) for p in fs}


def preconditions():
    S31.ground_truth()
    c = D.counts()
    assert c["histories"] == dict(development=28, confirmation=84, subset=28) and c["both_models"] == dict(plain=5824, t2=784, scaffold=1176)
    assert not D.leakage(), D.leakage()[:5]


def freeze(_):
    if (C.EXP / "inputs_sha256.json").exists():
        raise SystemExit("already frozen")
    preconditions()
    if not (C.EXP / "PROTOCOL.md").exists():
        raise SystemExit("PROTOCOL.md must be written first")
    for n, t in built().items():
        (C.EXP / n).write_text(t, encoding="utf-8", newline="\n")
    json.dump(dict(files={n: canonical_sha(C.EXP / n) for n in FROZEN}, code_sha256=code_sha(), archived_inputs=archived_inputs(),
                   prompt_manifest_sha256=D.prompt_manifest_sha()), open(C.EXP / "inputs_sha256.json", "w", encoding="utf-8", newline="\n"), indent=2)
    print("frozen", C.EXP.name)


def verify_frozen(code=True) -> list:
    old = json.load(open(C.EXP / "inputs_sha256.json", encoding="utf-8"))
    bad = [n for n in FROZEN if canonical_sha(C.EXP / n) != old["files"][n]]
    bad += [f"{n} (rebuilt)" for n, t in built().items() if t != (C.EXP / n).read_text(encoding="utf-8").replace("\r\n", "\n")]
    if old["archived_inputs"] != archived_inputs():
        bad.append("archived inputs")
    if code and old["code_sha256"] != code_sha():
        bad += [f"code {k}" for k, v in old["code_sha256"].items() if code_sha().get(k) != v]
    return bad


def validate(_):
    bad = verify_frozen()
    if bad:
        raise SystemExit(f"frozen inputs changed: {bad}")
    preconditions()
    print("validate OK")


def dryrun(_):
    preconditions()
    print(json.dumps(D.counts(), indent=1))
    print(D.render_frozen()[:6000])


def collect(a):
    if a.root is None:
        validate(a)
    from spar_dynamic.dice_crossed_guidance.models import load
    from spar_dynamic.dice_scaffolding import gpu
    gpu.collect(load(a.model), a.phase, a.root)


# ---------- post-run checks ----------

def _c(ok, detail=None):
    return dict(status="PASS" if ok else "FAIL", detail=detail)


def run_checks(phase="core", root=None, frozen=True) -> dict:
    from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl
    from spar_dynamic.dice_scaffolding import analysis as A
    root = Path(root or C.EXP)
    phases = ("core",) if phase == "core" else C.PHASES
    g = {}
    if frozen:
        # The figures/analysis code may be re-run locally; model-facing and scoring code must equal the frozen hashes.
        bad = [b for b in verify_frozen(code=True)]
        g["frozen_files_and_code"] = _c(not bad, bad)
    frows, nf, ids, mass_ok, norm_ok, consist = {}, True, set(), True, True, True
    for m in C.MODELS:
        raw = root / "raw" / m
        for ph in phases:
            env = json.load(open(raw / f"env_{ph}.json", encoding="utf-8"))
            done = json.load(open(raw / f"done_{ph}.json", encoding="utf-8"))
            g[f"{m}_{ph}_archival_replay"] = _c(env["archival_check"]["ok"], {k: v["max_dp_vs_exp28"] for k, v in env["archival_check"]["per_instruction"].items()})
            g[f"{m}_{ph}_on_path_and_boundaries"] = _c(env["on_path"]["ok"] and all(v["ok"] for v in env["instrumentation"].values()), env["on_path"])
            g[f"{m}_{ph}_serving_identity"] = _c(env["model_commit"] == C.MODEL[m]["revision"] and not env["vocab_scan"]["variant_face_tokens"])
            g[f"{m}_{ph}_prompt_hash"] = _c(env["prompt_manifest_sha256"] == D.prompt_manifest_sha())
            # env_core.json and the raw files of a finished phase must be unchanged since that phase finished
            g[f"{m}_{ph}_raw_hashes"] = _c(all(canonical_sha(raw / n) == s for n, s in done["files"].items()), len(done["files"]))
            F = read_jsonl(raw / f"forecasts_{ph}.jsonl")
            R = read_jsonl(raw / f"direct_{ph}.jsonl")
            want = {row_id_for(m, env["model_commit"], it["prompt_sha256"]) for it in D.unique_forecasts(ph)}
            g[f"{m}_{ph}_forecast_rows"] = _c({r["row_id"] for r in F} == want, len(F))
            nd = sum(len(j["lengths"]) for j in D.direct_jobs(ph))
            g[f"{m}_{ph}_direct_rows"] = _c(len(R) == nd == len({r["row_id"] for r in R}), len(R))
            for r in F + R:
                nf &= all(math.isfinite(x) for x in r["l"])
                mass_ok &= -1e-9 <= r["mass"] <= 1 + 1e-5
                norm_ok &= abs(sum(r["q"]) - 1) < 1e-9
                consist &= r["digit_ids"] == [C.MODEL[m]["face_ids"][f] for f in C.FACES]
            if ph == "core":
                g[f"{m}_repro_and_floor"] = _c(done["repro"]["ok"], done["repro"])
                seal = json.load(open(raw / "association_seal.json", encoding="utf-8"))
                a = read_jsonl(raw / "associations.jsonl")
                g[f"{m}_association_sealed_before_dice"] = _c(seal["dice_rows_at_seal"] == 0 and seal["scores_sha256"] == canonical_sha(raw / "association_scores.json")
                                                             and seal["rows_sha256"] == canonical_sha(raw / "associations.jsonl") and len(a) == len(D.association_items())
                                                             and max(r["timestamp"] for r in a) <= min(r["timestamp"] for r in F + R), seal)
                from spar_dynamic.dice_scaffolding.gpu import association_scores
                g[f"{m}_association_scores_rederive"] = _c(json.dumps(association_scores(a), sort_keys=True) == json.dumps(json.load(open(raw / "association_scores.json", encoding="utf-8")), sort_keys=True))
            else:
                g[f"{m}_generation_rows"] = _c(len(read_jsonl(raw / "generations.jsonl")) == len(D.verbal_items()) + len(D.free_items()))
                g[f"{m}_fact_rows"] = _c(len(read_jsonl(raw / "facts.jsonl")) == len(D.fact_items()))
    g["finite_scores"], g["mass_in_0_1"], g["normalised"], g["digit_ids"] = _c(nf), _c(mass_ok), _c(norm_ok), _c(consist)
    g["js_identity_bounds_symmetry"] = _c(A.js([.2] * 5 + [0], [.2] * 5 + [0]) == 0 and abs(A.js([1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]) - 1) < 1e-12)
    g["no_leakage"] = _c(not D.leakage())
    # both forecasters saw byte-identical prompts
    sh = [{r["prompt_sha256"] for r in read_jsonl(root / "raw" / m / f"forecasts_{ph}.jsonl")} for m in C.MODELS for ph in phases]
    n = len(phases)
    g["identical_stimuli_both_forecasters"] = _c(sh[:n] == sh[n:])
    return dict(experiment=C.TAG, phase=phase, overall="PASS" if all(v["status"] == "PASS" for v in g.values()) else "FAIL", checks=g)


def row_id_for(m, commit, prompt_sha):
    class E:
        pass
    e = E()
    e.commit = commit
    return row_id(e, "forecast", prompt_sha, "first_answer")


def checks(a):
    res = run_checks(a.phase, a.root, frozen=a.root is None)
    out = Path(a.root or C.EXP) / "results"
    out.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(out / f"checks_{a.phase}.json", "w", encoding="utf-8", newline="\n"), indent=2)
    md = [f"# {C.TAG} post-run checks ({a.phase}): **{res['overall']}**\n", "| Check | Status | Detail |", "|---|---|---|"]
    md += [f"| {k} | {v['status']} | {json.dumps(v['detail'])[:160] if v['detail'] is not None else ''} |" for k, v in res["checks"].items()]
    (out / ("CHECKS.md" if a.phase == "all" else f"CHECKS_{a.phase}.md")).write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print(res["overall"], [k for k, v in res["checks"].items() if v["status"] != "PASS"])
    if res["overall"] != "PASS":
        raise SystemExit(1)


def analyse(a):
    from spar_dynamic.dice_scaffolding import analysis as A
    phases = ("core",) if a.phase == "core" else C.PHASES
    root = Path(a.root or C.EXP)
    data = A.Data(root, phases)
    out = root / "results"
    out.mkdir(parents=True, exist_ok=True)
    res = dict(core=A.core(data))
    if len(phases) == 2:
        res["extensions"] = A.extensions(data)
    tables = {}
    for ph, d in res.items():
        for k, v in d.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                tables[f"{ph}_{k}"] = v
    if "extensions" in res:
        for k in ("words", "tests", "separability"):
            tables[f"extensions_natural_{k}"] = res["extensions"]["natural"][k]
    for k, v in tables.items():
        (out / f"{k}.csv").write_text(to_csv(v), encoding="utf-8", newline="\n")
    (out / "analysis_rows.csv").write_text(to_csv(A.analysis_rows(data, phases)), encoding="utf-8", newline="\n")
    slim = {ph: {k: v for k, v in d.items() if k not in ("verbal_rows", "coverage")} for ph, d in res.items()}
    json.dump(slim, open(out / "summary.json", "w", encoding="utf-8", newline="\n"), indent=1)
    from spar_dynamic.dice_scaffolding import figures
    figures.all(data, res, root / "figures")
    print(json.dumps(res["core"]["primary"], indent=1), res["core"]["primary_labels"])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dice_scaffolding", description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for n, fn in (("freeze", freeze), ("dryrun", dryrun), ("validate", validate), ("collect", collect), ("checks", checks), ("analyse", analyse)):
        p = sp.add_parser(n)
        p.set_defaults(fn=fn)
        if n == "collect":
            p.add_argument("--phase", choices=C.PHASES, required=True)
            p.add_argument("--model", choices=C.MODELS, required=True)
        if n in ("checks", "analyse"):
            p.add_argument("--phase", choices=("core", "all"), default="all")
        if n in ("collect", "checks", "analyse"):
            p.add_argument("--root", default=None, help="alternative output root (tests only)")
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
