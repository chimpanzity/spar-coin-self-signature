"""Trial builders for Stages A-D (handoff sections 4-7) and the live D2 session runner.

Every trial is a fresh stateless chat (one user message) except D2. Orientation names which source/candidate is
Sample A: 'XA'/'XB' for calibration (X is the correct candidate), 'QA'/'MA' for Qwen/Mistral as A. A swap moves the
whole sample (all its blocks, in fixed order) and nothing else. Truth comes from provenance only.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import random

from spar_dynamic.dice_recognition_v2 import client as CL, config as C, prompts as P


def _number(rows, seed):
    random.Random(seed).shuffle(rows)
    for n, r in enumerate(rows, 1):
        r["dispatch_index"] = n
    return rows


def _ab(orient):
    return ("qwen", "mistral") if orient == "QA" else ("mistral", "qwen")


# ------------------------------------------------------------------------------------------------ Stage A --
def calibration_trials(items):
    rows = []
    for judge in C.SOURCES:
        for fmt in C.FORMATS:
            for it in items:
                for orient in ("XA", "XB"):
                    a, b = (it["X"], it["Y"]) if orient == "XA" else (it["Y"], it["X"])
                    rows.append(dict(trial_id=f"cal|{judge}|{fmt}|{it['item_id']}|{orient}", stage="calibration", judge=judge,
                                     fmt=fmt, task=it["task"], item_id=it["item_id"], orientation=orient,
                                     A_content=a, B_content=b, correct="A" if orient == "XA" else "B",
                                     prompt=P.calibration_prompt(it["task"], fmt, a, b)))
    return _number(rows, C.SEEDS["calibration_order"])


# ------------------------------------------------------------------------------------------------ Stage B --
def screen_trials(pairs, cells):
    """pairs: Experiment 22 pairs.csv rows. cells: {judge: [formats that passed Stage A]}."""
    rows = []
    for judge, fmts in cells.items():
        for fmt in fmts:
            for frame in P.FRAMES:
                for p in pairs:
                    seq = {"qwen": [p["qwen_seq"]], "mistral": [p["mistral_seq"]]}
                    for orient in ("QA", "MA"):
                        a, b = _ab(orient)
                        rows.append(dict(trial_id=f"scr|{judge}|{fmt}|{frame}|{p['pair_id']}|{orient}", stage="screen",
                                         judge=judge, fmt=fmt, frame=frame, K=1, unit_id=p["pair_id"], orientation=orient,
                                         A_source=a, B_source=b, target_source=judge, correct="A" if a == judge else "B",
                                         A_content="|".join(seq[a]), B_content="|".join(seq[b]),
                                         prompt=P.frame_prompt(frame, fmt, seq[a], seq[b])))
    return _number(rows, C.SEEDS["screen_order"])


# ------------------------------------------------------------------------------------------------ Stage C --
def dose_trials(families, primary):
    rows = []
    for judge, fmt in primary.items():
        for frame in P.FRAMES:
            for K in C.DOSES:
                for f in families:
                    seq = {m: f[m][:K] for m in C.SOURCES}
                    for orient in ("QA", "MA"):
                        a, b = _ab(orient)
                        rows.append(dict(trial_id=f"dose|{judge}|{frame}|K{K}|{f['family_id']}|{orient}", stage="dose",
                                         judge=judge, fmt=fmt, frame=frame, K=K, unit_id=f["family_id"], orientation=orient,
                                         A_source=a, B_source=b, target_source=judge, correct="A" if a == judge else "B",
                                         A_content="|".join(seq[a]), B_content="|".join(seq[b]),
                                         prompt=P.frame_prompt(frame, fmt, seq[a], seq[b])))
    return _number(rows, C.SEEDS["dose_order"])


def named_trials(families, primary):
    rows = []
    K = max(C.DOSES)
    for judge, fmt in primary.items():
        for target in C.SOURCES:
            for name_order in (("qwen", "mistral"), ("mistral", "qwen")):
                no = "QM" if name_order[0] == "qwen" else "MQ"
                for f in families:
                    seq = {m: f[m][:K] for m in C.SOURCES}
                    for orient in ("QA", "MA"):
                        a, b = _ab(orient)
                        rows.append(dict(trial_id=f"named|{judge}|{target}|{no}|{f['family_id']}|{orient}", stage="named",
                                         judge=judge, fmt=fmt, frame=f"NAMED_{target}", K=K, name_order=no,
                                         unit_id=f["family_id"], orientation=orient, A_source=a, B_source=b,
                                         target_source=target, correct="A" if a == target else "B",
                                         A_content="|".join(seq[a]), B_content="|".join(seq[b]),
                                         prompt=P.named_prompt(fmt, seq[a], seq[b], target, name_order)))
    return _number(rows, C.SEEDS["named_order"])


# ------------------------------------------------------------------------------------------------ Stage D --
def exposure_examples(families, familiar):
    """Per family and source: a seeded choice of 5 of that source's 10 reserved records (same for both orientations
    and for every judge). Chosen before any D1 call and independent of test labels."""
    rng = random.Random(C.SEEDS["exposure_select"])
    sel = {}
    for f in families:
        for m in C.SOURCES:
            pick = sorted(rng.sample(range(C.N_FAMILIAR_PER_SOURCE), C.N_EXPOSURE_EXAMPLES))
            sel[(f["family_id"], m)] = [familiar[m][i] for i in pick]
    return sel


def exposure_trials(families, sel, primary):
    rows = []
    K = max(C.DOSES)
    for judge, fmt in primary.items():
        for kind in ("own", "other"):
            ex_src = judge if kind == "own" else C.OTHER[judge]
            for f in families:
                ex = sel[(f["family_id"], ex_src)]
                seq = {m: f[m][:K] for m in C.SOURCES}
                for orient in ("QA", "MA"):
                    a, b = _ab(orient)
                    rows.append(dict(trial_id=f"exp|{judge}|{kind}|{f['family_id']}|{orient}", stage="exposure",
                                     judge=judge, fmt=fmt, frame="AUTH", exposure=kind.upper(), K=K, unit_id=f["family_id"],
                                     orientation=orient, A_source=a, B_source=b, target_source=judge,
                                     correct="A" if a == judge else "B", exemplar_source=ex_src,
                                     exemplar_record_ids=[x["record_id"] for x in ex],
                                     A_content="|".join(seq[a]), B_content="|".join(seq[b]),
                                     prompt=P.exposure_prompt(kind, [x["sequence"] for x in ex], fmt, seq[a], seq[b])))
    return _number(rows, C.SEEDS["exposure_order"])


def live_sessions(families, primary):
    """D2: first N_LIVE_FAMILIES families x both orientations per judge; TYP question at K=5."""
    rows = []
    K = max(C.DOSES)
    for judge, fmt in primary.items():
        for f in families[:C.N_LIVE_FAMILIES]:
            seq = {m: f[m][:K] for m in C.SOURCES}
            for orient in ("QA", "MA"):
                a, b = _ab(orient)
                rows.append(dict(trial_id=f"live|{judge}|{f['family_id']}|{orient}", stage="live", judge=judge, fmt=fmt,
                                 frame="TYP_LIVE", K=K, unit_id=f["family_id"], orientation=orient, A_source=a, B_source=b,
                                 target_source=judge, correct="A" if a == judge else "B",
                                 A_content="|".join(seq[a]), B_content="|".join(seq[b]),
                                 prompt=P.frame_prompt("TYP", fmt, seq[a], seq[b])))
    return _number(rows, C.SEEDS["live_order"])


def run_live(oai, ledger, sessions, path):
    """Sequential multi-turn sessions: three live generation turns (each reply kept verbatim as the assistant
    message, valid or not), then the TYP judgment in the same conversation. Resume skips finished sessions."""
    done = {json.loads(l)["trial_id"] for l in open(path, encoding="utf-8")} if os.path.exists(path) else set()
    for s in sessions:
        if s["trial_id"] in done:
            continue
        msgs, gens = [], []
        for _ in range(C.N_LIVE_GEN_TURNS):
            msgs.append({"role": "user", "content": P.GEN})
            g = CL.call(oai, ledger, s["judge"], list(msgs), "generation", "live")
            if not g.get("ok") or not CL.provider_ok(g) or not CL.thinking_clean(g):
                raise SystemExit(f"STOP: live generation failed or drifted for {s['trial_id']}")
            msgs.append({"role": "assistant", "content": g["content"] or ""})
            gens.append(dict(content=g["content"], valid=P.parse_sequence(g["content"]) is not None,
                             finish_reason=g["finish_reason"], response_id=g["response_id"], cost_usd=g["cost_usd"],
                             served_provider=g["served_provider"], reasoning_tokens=g["reasoning_tokens"]))
        msgs.append({"role": "user", "content": s["prompt"]})
        rec = CL.call(oai, ledger, s["judge"], msgs, s["fmt"], "live")
        choice = CL.judged(rec, s["fmt"])
        rec.update({k: v for k, v in s.items() if k != "prompt"}, messages=msgs, live_generations=gens, choice=choice,
                   valid=choice is not None, is_correct=(choice == s["correct"]) if choice else None,
                   completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        print(f"[live {s['dispatch_index']}] {s['trial_id']}: gens {[g['content'] for g in gens]} -> {choice} "
              f"(correct {s['correct']}; ${getattr(ledger, "spent", 0):.4f})", flush=True)
