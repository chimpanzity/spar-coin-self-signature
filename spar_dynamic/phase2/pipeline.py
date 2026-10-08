"""Stage orchestration: stage1 -> freeze -> stage2 -> retained -> analyze."""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import config as C
from . import tasks as T
from .__main__ import combined_hash, make_executor, recipe_hash, run_dir_for
from .baselines import headroom_oof
from .client import progress, utc_now
from .corpus import cell_summary, load_calls, sequence_rows, write_csv


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _jdump(path: Path, obj: Any) -> str:
    text = json.dumps(obj, indent=1, default=str)
    path.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def _gen_rows(rd: Path) -> List[Dict[str, Any]]:
    rows = sequence_rows(load_calls(rd))
    write_csv(rd / "sequences.csv", rows)
    return rows


def _valid_by_cell(rows, split) -> Dict[Tuple[str, str], Dict[str, str]]:
    out: Dict[Tuple[str, str], Dict[str, str]] = defaultdict(dict)
    for r in rows:
        if r["split"] == split and r["valid"] and r["source"] in C.CORE_ORDER:
            out[(r["source"], r["prompt"])][r["parent_id"]] = r["outcomes"]
    return out


def _pick_index(n: int, *seed_parts) -> Optional[int]:
    return None if n == 0 else C.derive_seed(*seed_parts) % n


def _run_with_retry(ex, slots, label):
    ex.run(slots, label)
    if not ex.stop_flag.is_set():
        failed = [s for s in slots if ex.log.done_ids().get(s.slot_id, {}).get("status") == "transport_failed"]
        if failed:
            progress(ex.run_dir, f"{label}: one resume pass for {len(failed)} transport failures (same payloads)")
            ex.run(slots, label + " resume", retry_failed=True)


def _parents(cellmap, ids=None):
    out = []
    for (g, p), d in sorted(cellmap.items()):
        for pid, s in sorted(d.items()):
            if ids is None or pid in ids:
                out.append({"parent_id": pid, "source": g, "prompt": p, "first_ten": s[:10], "sequence": s})
    return out


def _fallback_parents(cellmap, k, *seed):
    ids = set()
    for (g, p), d in sorted(cellmap.items()):
        ids.update(T.seeded_shuffle(sorted(d.keys()), *seed, g, p)[:k])
    return ids


# ---------------------------------------------------------------------------
# Stage 1
# ---------------------------------------------------------------------------

def cmd_stage1(args) -> None:
    rd = run_dir_for(args.run)
    ex = make_executor(rd, args.live)
    progress(rd, "STAGE 1 start")
    _run_with_retry(ex, T.generation_slots("development"), "generation/development")
    rows = _gen_rows(rd)
    summ = cell_summary([r for r in rows if r["split"] == "development"])
    _jdump(rd / "corpus_summary_development.json", summ)
    for c in summ:
        progress(rd, f"  dev {c['source']}/{c['prompt']}: valid {c['valid']}/{c['attempted']} "
                     f"heads={c['mean_heads']} switch={c['switch_rate']} distinct={c['distinct_strings']} "
                     f"eff_prefix10={c['effective_prefix10']}")
    dev = _valid_by_cell(rows, "development")

    # objective fixtures for the two protected tasks (72 calls)
    fix_slots, fix_truth = [], {}
    for j in C.CORE_ORDER:
        for slot, truth in T.completion_fixtures(j) + T.pair_fixtures(j):
            fix_slots.append(slot); fix_truth[slot.slot_id] = truth
    _jdump(rd / "fixtures_truth_core.json", fix_truth)
    _run_with_retry(ex, fix_slots, "fixtures/completion+pairs")
    fixtures = score_fixtures(rd, fix_slots, fix_truth)
    _jdump(rd / "fixtures_results_core.json", fixtures)
    for k, v in fixtures["summary"].items():
        progress(rd, f"  fixture {k}: valid {v['valid']}/{v['n']}, correct {v['correct']}/{v['n']}")

    # rehearsal (108 calls): one complete development block per prompt
    reh = {"blocks": {}, "completion_parents": [], "pairs": []}
    pair_items = []
    comp_ids = set()
    for p in C.PROMPT_ORDER:
        blocks, pairs = T.build_pair_blocks({g: list(dev.get((g, p), {}).keys()) for g in C.CORE_ORDER},
                                            "development", p)
        i = _pick_index(len(blocks), "rehearsal_block", p)
        if i is None:
            reh["blocks"][p] = None
            fb = _fallback_parents({k: v for k, v in dev.items() if k[1] == p}, 2, "rehearsal_fallback")
            comp_ids |= fb
            progress(rd, f"  rehearsal: no complete development block for prompt {p}; "
                         f"completion rehearsal uses {len(fb)} fallback parents, no pair rehearsal")
            continue
        b = blocks[i]
        reh["blocks"][p] = b
        comp_ids |= set(b["parents"].values())
        pair_items += [x for x in pairs if x.block_id == b["block_id"]]
    comp_parents = _parents(dev, comp_ids)
    alloc = T.allocate_completion({(x["source"], x["prompt"]): [y["parent_id"] for y in comp_parents
                                    if y["source"] == x["source"] and y["prompt"] == x["prompt"]] for x in comp_parents},
                                  "rehearsal")
    seqs = {pid: s for d in dev.values() for pid, s in d.items()}
    reh_slots = (T.completion_slots(comp_parents, alloc, "rehearsal_completion", "stage1")
                 + T.pair_slots(pair_items, seqs, "rehearsal_pairs", "stage1", orders=("designated",)))
    reh["completion_parents"] = sorted(comp_ids)
    reh["pairs"] = [x.__dict__ for x in pair_items]
    reh["allocation"] = alloc
    _jdump(rd / "rehearsal_manifest.json", reh)
    _run_with_retry(ex, reh_slots, "rehearsal")

    # headroom review (Section 5.5)
    hr = headroom_oof(dev)
    decision = {"option": "a", "text": "continue the fixed pilot with explicitly limited external evidence "
                "of disclosure headroom", "source": "approvals.jsonl (inferred from Chris's go-ahead; flagged)"}
    hr_out = {k: v for k, v in hr.items() if k != "per_parent"}
    hr_out["decision_if_required"] = decision if hr["headroom_review_required"] else None
    hr_out["computed_utc"] = utc_now()
    _jdump(rd / "headroom_review.json", hr_out)
    write_csv(rd / "headroom_per_parent.csv", hr["per_parent"])
    progress(rd, f"  headroom I[g] = {json.dumps({k: (round(v, 4) if v is not None else None) for k, v in hr['I_g'].items()})}; "
                 f"review_required={hr['headroom_review_required']}")

    from .report import write_stage1_docs
    write_stage1_docs(rd, summ, fixtures, hr_out, reh)
    progress(rd, "STAGE 1 complete")


def score_fixtures(rd: Path, slots, truth) -> Dict[str, Any]:
    from .tasks import score_fixture
    calls = load_calls(rd)
    rows, summary = [], defaultdict(lambda: {"n": 0, "valid": 0, "correct": 0})
    for s in slots:
        r = calls.get(s.slot_id)
        p = (r or {}).get("parse") or {}
        ok = bool(p.get("valid"))
        corr = ok and score_fixture(s.answer_kind, truth[s.slot_id]["truth"], p["value"])
        key = f"{s.task}|{s.alias}"
        summary[key]["n"] += 1
        summary[key]["valid"] += int(ok)
        summary[key]["correct"] += int(bool(corr))
        rows.append({"slot_id": s.slot_id, "task": s.task, "judge": s.alias, "valid": ok,
                     "reason": p.get("reason"), "value": p.get("value"), "truth": truth[s.slot_id]["truth"],
                     "correct": bool(corr), "detail": {k: v for k, v in truth[s.slot_id].items() if k not in ("truth", "slot_id")}})
    gate = {}
    for k, v in summary.items():
        need = 5 if "named" in k else 11
        gate[k] = {"valid_gate_pass": v["valid"] >= need, "threshold": need}
    return {"summary": dict(summary), "gates": gate, "rows": rows}


# ---------------------------------------------------------------------------
# Freeze
# ---------------------------------------------------------------------------

def cmd_freeze(args) -> None:
    rd = run_dir_for(args.run)
    appr = (rd / "approvals.jsonl").read_text()
    freeze = {
        "frozen_utc": utc_now(), "protocol": C.PROTOCOL, "combined_recipe_hash": combined_hash(),
        "recipe_hashes": recipe_hash(), "approvals_sha256": hashlib.sha256(appr.encode()).hexdigest(),
        "approval_basis": "Stage 2 freeze pre-approved by Chris Martin in chat on 2026-10-07",
        "margins": {"delta_brier": C.DELTA_BRIER, "delta_auc": C.DELTA_AUC},
        "headroom_threshold": C.HEADROOM_THRESHOLD, "n_boot": C.N_BOOT, "master_seed": C.MASTER_SEED,
        "prefix_len": C.PREFIX_LEN, "test_attempts_per_cell": C.TEST_ATTEMPTS_PER_CELL,
        "note": "Scientific-specification lock: prompts, parsers, settings, allocation, benchmarks, grids, "
                "intervals, masks, headroom rule, quotas and audit-selection algorithms are the code at these hashes.",
    }
    for f in ("headroom_review.json", "fixtures_results_core.json", "PRECISION_PLAN.md", "DECISION_MEMO.md"):
        if (rd / f).exists():
            freeze.setdefault("stage1_artifacts", {})[f] = hashlib.sha256((rd / f).read_bytes()).hexdigest()
    _jdump(rd / "freeze.json", freeze)
    with open(rd / "approvals.jsonl", "a") as fh:
        fh.write(json.dumps({"utc": utc_now(), "by": "Chris Martin (pre-approved)", "decision": "freeze_executed",
                             "value": freeze["combined_recipe_hash"]}) + "\n")
    progress(rd, f"FREEZE recorded: recipe hash {freeze['combined_recipe_hash'][:12]}")


def _check_freeze(rd: Path) -> Dict[str, Any]:
    fz = json.loads((rd / "freeze.json").read_text())
    cur = combined_hash()
    if cur != fz["combined_recipe_hash"]:
        amends = [json.loads(l) for l in (rd / "amendments.jsonl").read_text().splitlines() if l.strip()] \
            if (rd / "amendments.jsonl").exists() else []
        if not any(a.get("post_freeze") and a.get("new_recipe_hash") == cur for a in amends):
            raise SystemExit(f"recipe hash {cur[:12]} differs from frozen {fz['combined_recipe_hash'][:12]} "
                             f"without a post-freeze amendment record")
    return fz


# ---------------------------------------------------------------------------
# Stage 2
# ---------------------------------------------------------------------------

def build_test_manifests(rd: Path, rows) -> Dict[str, Any]:
    test = _valid_by_cell(rows, "test")
    alloc = T.allocate_completion({k: list(v.keys()) for k, v in test.items()}, "test")
    blocks_all, pairs_all = [], []
    audit_blocks, named_blocks = {}, {}
    for p in C.PROMPT_ORDER:
        blocks, pairs = T.build_pair_blocks({g: list(test.get((g, p), {}).keys()) for g in C.CORE_ORDER}, "test", p)
        blocks_all += blocks; pairs_all += pairs
        i = _pick_index(len(blocks), "audit_block", p)
        audit_blocks[p] = blocks[i]["block_id"] if i is not None else None
        rest = [b["block_id"] for b in blocks if b["block_id"] != audit_blocks[p]]
        chosen = ([audit_blocks[p]] if audit_blocks[p] else []) + T.seeded_shuffle(rest, "named_blocks", p)
        named_blocks[p] = chosen[: C.N_NAMED_BLOCKS_PER_PROMPT]
    audit_parent_ids = set()
    for b in blocks_all:
        if b["block_id"] in audit_blocks.values():
            audit_parent_ids |= set(b["parents"].values())
    fallback_prompts = [p for p in C.PROMPT_ORDER if audit_blocks[p] is None]
    if fallback_prompts:
        audit_parent_ids |= _fallback_parents({k: v for k, v in test.items() if k[1] in fallback_prompts},
                                              2, "audit_fallback")
    named_parents = []
    for b in blocks_all:
        if b["block_id"] in sum(named_blocks.values(), []):
            named_parents += list(b["parents"].values())
    src_of = {pid: g for (g, p), d in test.items() for pid in d}
    prm_of = {pid: p for (g, p), d in test.items() for pid in d}
    named_order = {}
    cells = defaultdict(list)
    for pid in named_parents:
        cells[(src_of[pid], prm_of[pid])].append(pid)
    for key, pids in cells.items():
        for i, pid in enumerate(T.seeded_shuffle(sorted(pids), "named_orders", *key)):
            named_order[pid] = i % 6
    man = {
        "built_utc": utc_now(), "completion_allocation": alloc,
        "pair_blocks": blocks_all, "pairs": [x.__dict__ for x in pairs_all],
        "audit_blocks": audit_blocks, "audit_parents": sorted(audit_parent_ids),
        "audit_fallback_prompts": fallback_prompts,
        "named_blocks": named_blocks, "named_order": named_order,
        "n_valid_test_parents": {f"{g}|{p}": len(d) for (g, p), d in test.items()},
    }
    h = _jdump(rd / "manifests.json", man)
    with open(rd / "items_private.jsonl", "w") as f:
        for (g, p), d in sorted(test.items()):
            for pid, s in sorted(d.items()):
                f.write(json.dumps({"parent_id": pid, "source": g, "prompt": p, "sequence": s}) + "\n")
        for x in pairs_all:
            f.write(json.dumps({"pair_id": x.pair_id, **x.__dict__}) + "\n")
    with open(rd / "items_public.jsonl", "w") as f:
        for (g, p), d in sorted(test.items()):
            for pid, s in sorted(d.items()):
                f.write(json.dumps({"parent_id": pid, "prompt": p, "first_ten": s[:10]}) + "\n")
        for x in pairs_all:
            f.write(json.dumps({"pair_id": x.pair_id, "block_id": x.block_id, "prompt": x.prompt,
                                "sequence_1_parent": x.first, "sequence_2_parent": x.second}) + "\n")
    man["sha256"] = h
    return man


def stage2_slots(rd: Path, rows, man) -> Dict[str, List]:
    test = _valid_by_cell(rows, "test")
    parents = _parents(test)
    seqs = {x["parent_id"]: x["sequence"] for x in parents}
    pairs = [T.PairItem(**d) for d in man["pairs"]]
    audit = set(man["audit_parents"])
    audit_pairs = [x for x in pairs if x.block_id in [b for b in man["audit_blocks"].values() if b]]
    alloc = man["completion_allocation"]
    aud_par = [x for x in parents if x["parent_id"] in audit]
    return {
        "h4": T.completion_slots(parents, alloc, "completion", "stage2"),
        "completion_repeat": T.completion_slots(aud_par, alloc, "completion_repeat", "stage2"),
        "completion_polarity": T.completion_slots(aud_par, alloc, "completion_polarity", "stage2", target="T"),
        "completion_priors": T.completion_prior_slots(),
        "pairs": T.pair_slots(pairs, seqs, "pairs", "stage2"),
        "pair_repeat": T.pair_slots(audit_pairs, seqs, "pair_repeat", "stage2", orders=("designated",)),
        "pair_polarity": T.pair_slots(audit_pairs, seqs, "pair_polarity", "stage2", orders=("designated",),
                                      polarity="DIFFERENT"),
        "pair_priors": T.pair_prior_slots(),
    }


def cmd_stage2(args) -> None:
    rd = run_dir_for(args.run)
    _check_freeze(rd)
    ex = make_executor(rd, args.live)
    progress(rd, "STAGE 2 start (freeze verified)")
    _run_with_retry(ex, T.generation_slots("test"), "generation/test")
    rows = _gen_rows(rd)
    summ = cell_summary([r for r in rows if r["split"] == "test"])
    _jdump(rd / "corpus_summary_test.json", summ)
    for c in summ:
        progress(rd, f"  test {c['source']}/{c['prompt']}: valid {c['valid']}/{c['attempted']}")
    man = build_test_manifests(rd, rows) if not (rd / "manifests.json").exists() else json.loads((rd / "manifests.json").read_text())
    progress(rd, f"  manifests built and hashed: {len(man['pairs'])} pairs in {len(man['pair_blocks'])} blocks; "
                 f"audit blocks {man['audit_blocks']}")
    S = stage2_slots(rd, rows, man)
    for key in ("h4", "completion_repeat", "completion_polarity", "completion_priors",
                "pairs", "pair_repeat", "pair_polarity", "pair_priors"):
        if ex.stop_flag.is_set():
            break
        _run_with_retry(ex, S[key], key)
    progress(rd, "STAGE 2 complete")


# ---------------------------------------------------------------------------
# Retained arms
# ---------------------------------------------------------------------------

def cmd_retained(args) -> None:
    rd = run_dir_for(args.run)
    _check_freeze(rd)
    ex = make_executor(rd, args.live)
    progress(rd, "RETAINED ARMS start")
    fix_slots, fix_truth = [], {}
    for j in C.CORE_ORDER:
        for slot, truth in T.named_fixtures(j):
            fix_slots.append(slot); fix_truth[slot.slot_id] = truth
    _jdump(rd / "fixtures_truth_named.json", fix_truth)
    _run_with_retry(ex, fix_slots, "fixtures/named")
    nf = score_fixtures(rd, fix_slots, fix_truth)
    _jdump(rd / "fixtures_results_named.json", nf)
    rows = _gen_rows(rd)
    man = json.loads((rd / "manifests.json").read_text())
    test = _valid_by_cell(rows, "test")
    named_ids = set(man["named_order"].keys())
    parents = _parents(test, named_ids)
    _run_with_retry(ex, T.named_slots(parents, man["named_order"]), "named")
    _run_with_retry(ex, T.named_prior_slots(), "named_priors")
    _run_with_retry(ex, T.historical_slots(), "historical_generation")
    _gen_rows(rd)
    progress(rd, "RETAINED ARMS complete")


def cmd_analyze(args) -> None:
    from .report import analyze_all
    analyze_all(run_dir_for(args.run))


def cmd_verify(args) -> None:
    """Full fake end-to-end run in a scratch run directory."""
    import shutil
    rd = run_dir_for(args.run)
    for f in rd.iterdir():
        if f.is_file():
            f.unlink()
        else:
            shutil.rmtree(f)
    (rd / "approvals.jsonl").write_text(json.dumps({"decision": "fake verification"}) + "\n")
    a = type("A", (), {"run": args.run, "live": False})
    cmd_stage1(a); cmd_freeze(a); cmd_stage2(a); cmd_retained(a); cmd_analyze(a)
