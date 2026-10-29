"""Stimulus corpus (handoff sections 4-5): interleaved sampled generation, strict validity, grouped dev/holdout split.

Collection: a seeded interleaved schedule of up to 75 attempts per model; a model's attempts stop once it has 50
valid sequences. Every attempt is appended to corpus/raw_attempts.jsonl; resuming skips completed attempt ids.
Validity: strict 10-face parse, finish_reason stop, no reasoning payload/think text, served provider == pinned.
A provider mismatch stops the phase (no contamination).

Split (prespecified): identical strings form one group. Groups containing both sources (cross-source
collisions) are nondiagnostic and go to development. The remaining groups are shuffled (SPLIT_SEED) and added
whole to the holdout for their source while they fit, until each source has exactly 20 holdout sequences.
If exactly 20 per source cannot be reached, STOP (no silent change).
"""

from __future__ import annotations

import collections
import csv
import json
import os
import random

from spar_dynamic.dice_recognition import client as CL, config as C, prompts as P


def schedule():
    jobs = [(m, i) for m in C.SOURCES for i in range(1, C.MAX_ATTEMPTS_PER_MODEL + 1)]
    random.Random(C.GEN_ORDER_SEED).shuffle(jobs)
    return jobs


def is_valid(rec):
    faces = P.parse_sequence(rec.get("content"))
    return (faces is not None and rec.get("finish_reason") == "stop" and CL.thinking_clean(rec)
            and CL.provider_ok(rec) and not rec.get("tool_calls")), faces


def collect(oai, ledger, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "raw_attempts.jsonl")
    done, valid = set(), collections.Counter()
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            r = json.loads(l)
            done.add((r["model_key"], r["attempt_index"]))
            valid[r["model_key"]] += r["valid"]
    prompt = P.generation_prompt()
    for n, (m, i) in enumerate(schedule(), 1):
        if (m, i) in done or valid[m] >= C.N_VALID_PER_MODEL:
            continue
        if all(valid[s] >= C.N_VALID_PER_MODEL for s in C.SOURCES):
            break
        rec = CL.call(oai, ledger, m, prompt, "generation")
        ok, faces = is_valid(rec)
        rec.update(attempt_index=i, schedule_index=n, valid=ok, faces=faces, prompt_sha256=P.sha256(prompt),
                   invalid_reason=None if ok else _reason(rec, faces))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        valid[m] += ok
        if rec.get("ok") and not CL.provider_ok(rec):
            raise SystemExit(f"STOP: {m} served by {rec.get('served_provider')} instead of {rec['requested_provider']}")
        print(f"[{n}] {m}#{i}: {rec.get('content')!r} valid={ok} (valid {dict(valid)}; spent ${ledger.spent:.4f})", flush=True)
    return dict(valid)


def _reason(rec, faces):
    if not rec.get("ok"):
        return "transport_or_request_error"
    if not CL.provider_ok(rec):
        return "provider_mismatch"
    if not CL.thinking_clean(rec):
        return "thinking_payload"
    if rec.get("finish_reason") != "stop":
        return f"finish_{rec.get('finish_reason')}"
    return "format" if faces is None else "other"


def build_stimuli(out_dir):
    """Valid sequences -> stimuli with ids, in attempt order; at most 50 per model."""
    rows = [json.loads(l) for l in open(os.path.join(out_dir, "raw_attempts.jsonl"), encoding="utf-8")]
    stim = []
    for m in C.SOURCES:
        ok = sorted([r for r in rows if r["model_key"] == m and r["valid"]], key=lambda r: r["schedule_index"])
        for k, r in enumerate(ok[:C.N_VALID_PER_MODEL], 1):
            stim.append(dict(stimulus_id=f"{m}-{k:02d}", source=m, generation_replicate=k, attempt_index=r["attempt_index"],
                             sequence=r["content"], **{f"f{j + 1}": v for j, v in enumerate(r["faces"])},
                             provider=r["served_provider"], request_id=r["response_id"],
                             timestamp=r["attempts"][-1]["timestamp"], valid=True))
    return stim


def split(stim):
    by_seq = collections.defaultdict(list)
    for s in stim:
        by_seq[s["sequence"]].append(s)
    groups = sorted(by_seq)                                   # deterministic before shuffling
    cross = [g for g in groups if len({s["source"] for s in by_seq[g]}) > 1]
    single = [g for g in groups if g not in cross]
    random.Random(C.SPLIT_SEED).shuffle(single)
    hold = collections.Counter()
    hold_groups = set()
    for g in single:
        src = by_seq[g][0]["source"]
        if hold[src] + len(by_seq[g]) <= C.N_HOLDOUT:
            hold[src] += len(by_seq[g])
            hold_groups.add(g)
    ok = all(hold[s] == C.N_HOLDOUT for s in C.SOURCES)
    for s in stim:
        s["split"] = "heldout" if s["sequence"] in hold_groups else "development"
        s["duplicate_group"] = groups.index(s["sequence"])
        s["group_size"] = len(by_seq[s["sequence"]])
        s["cross_source_collision"] = s["sequence"] in cross
    dup = dict(n_unique_strings=len(groups), cross_source_collisions=len(cross),
               within_source_duplicate_groups={src: sum(1 for g in single if by_seq[g][0]["source"] == src and len(by_seq[g]) > 1)
                                               for src in C.SOURCES},
               unique_per_source={src: len({s["sequence"] for s in stim if s["source"] == src}) for src in C.SOURCES},
               modal_sequence_per_source={src: collections.Counter(s["sequence"] for s in stim if s["source"] == src).most_common(1)[0]
                                          for src in C.SOURCES if any(s["source"] == src for s in stim)},
               holdout_counts=dict(hold), dev_counts={src: sum(1 for s in stim if s["source"] == src and s["split"] == "development")
                                                      for src in C.SOURCES})
    return ok, dup


def write_csv(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict, tuple)) else v) for k, v in r.items()})
