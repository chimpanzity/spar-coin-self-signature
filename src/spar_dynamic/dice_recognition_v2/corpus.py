"""Stage C fresh corpus (handoff section 6.1).

Collection: a seeded interleaved schedule of up to 160 attempts per source; a source stops once it has 110 valid
independent ten-roll responses. Every attempt is appended to corpus_v2/raw_attempts.jsonl (resume skips done
attempt ids). Validity is v1's: strict parse, finish stop, no reasoning, pinned provider served, no tool calls.

Partition (prespecified, SEEDS['partition']): each source's 110 valid records, in schedule order, are shuffled;
the first 10 are the familiarization reserve, the next 100 form 20 families x 5 blocks in shuffled order. Family
i pairs Qwen family i with Mistral family i. Records are keyed by response id, so no record can enter two roles.
Duplicate strings are kept as natural outcomes and flagged, never discarded or regenerated.
"""

from __future__ import annotations

import collections
import json
import os
import random

from spar_dynamic.dice_recognition.corpus import write_csv   # noqa: F401 (re-export)
from spar_dynamic.dice_recognition_v2 import client as CL, config as C, prompts as P


def schedule():
    jobs = [(m, i) for m in C.SOURCES for i in range(1, C.MAX_ATTEMPTS_PER_SOURCE + 1)]
    random.Random(C.SEEDS["gen_schedule"]).shuffle(jobs)
    return jobs


def is_valid(rec):
    faces = P.parse_sequence(rec.get("content"))
    return (faces is not None and rec.get("finish_reason") == "stop" and CL.thinking_clean(rec)
            and CL.provider_ok(rec) and not rec.get("tool_calls")), faces


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


def collect(oai, ledger, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "raw_attempts.jsonl")
    done, valid = set(), collections.Counter()
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            r = json.loads(l)
            done.add((r["model_key"], r["attempt_index"]))
            valid[r["model_key"]] += r["valid"]
    msgs = [{"role": "user", "content": P.GEN}]
    for n, (m, i) in enumerate(schedule(), 1):
        if all(valid[s] >= C.N_VALID_PER_SOURCE for s in C.SOURCES):
            break
        if (m, i) in done or valid[m] >= C.N_VALID_PER_SOURCE:
            continue
        rec = CL.call(oai, ledger, m, msgs, "generation", "corpus_v2")
        ok, faces = is_valid(rec)
        rec.update(attempt_index=i, schedule_index=n, valid=ok, faces=faces, prompt_sha256=P.sha256(P.GEN),
                   invalid_reason=None if ok else _reason(rec, faces))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        valid[m] += ok
        if rec.get("ok") and not CL.provider_ok(rec):
            raise SystemExit(f"STOP: {m} served by {rec.get('served_provider')}")
        print(f"[{n}] {m}#{i}: {rec.get('content')!r} valid={ok} ({dict(valid)}; ${ledger.spent:.4f})", flush=True)
    return dict(valid)


def records(out_dir):
    rows = [json.loads(l) for l in open(os.path.join(out_dir, "raw_attempts.jsonl"), encoding="utf-8")]
    out = {}
    for m in C.SOURCES:
        ok = sorted([r for r in rows if r["model_key"] == m and r["valid"]], key=lambda r: r["schedule_index"])
        out[m] = [dict(record_id=f"{m}-{k:03d}", source=m, response_id=r["response_id"], attempt_index=r["attempt_index"],
                       schedule_index=r["schedule_index"], sequence=r["content"]) for k, r in enumerate(ok, 1)]
    return out


def partition(recs):
    """-> (families, familiar). families: list of dict(family_id, qwen=[5 seqs], mistral=[5 seqs], *_ids)."""
    rng = random.Random(C.SEEDS["partition"])
    fam_blocks, familiar = {}, {}
    for m in C.SOURCES:
        r = list(recs[m][:C.N_VALID_PER_SOURCE])
        assert len(r) == C.N_VALID_PER_SOURCE
        rng.shuffle(r)
        familiar[m] = r[:C.N_FAMILIAR_PER_SOURCE]
        ev = r[C.N_FAMILIAR_PER_SOURCE:]
        fam_blocks[m] = [ev[i * C.BLOCKS_PER_FAMILY:(i + 1) * C.BLOCKS_PER_FAMILY] for i in range(C.N_FAMILIES)]
    ids = [x["response_id"] for m in C.SOURCES for x in familiar[m]] + \
          [x["response_id"] for m in C.SOURCES for f in fam_blocks[m] for x in f]
    assert len(ids) == len(set(ids)), "a generation record was assigned twice"
    families = []
    for i in range(C.N_FAMILIES):
        f = dict(family_id=f"F{i + 1:02d}")
        for m in C.SOURCES:
            f[m] = [x["sequence"] for x in fam_blocks[m][i]]
            f[f"{m}_record_ids"] = [x["record_id"] for x in fam_blocks[m][i]]
            f[f"{m}_response_ids"] = [x["response_id"] for x in fam_blocks[m][i]]
        families.append(f)
    return families, familiar


def duplicate_report(recs, families, familiar):
    all_seq = {m: [x["sequence"] for x in recs[m][:C.N_VALID_PER_SOURCE]] for m in C.SOURCES}
    cnt = {m: collections.Counter(all_seq[m]) for m in C.SOURCES}
    cross = sorted(set(all_seq["qwen"]) & set(all_seq["mistral"]))
    fam_seq = {m: {s for f in families for s in f[m]} for m in C.SOURCES}
    return dict(
        n_valid=dict((m, len(all_seq[m])) for m in C.SOURCES),
        unique_strings={m: len(cnt[m]) for m in C.SOURCES},
        within_source_duplicate_groups={m: sum(v > 1 for v in cnt[m].values()) for m in C.SOURCES},
        modal_string={m: cnt[m].most_common(1)[0] for m in C.SOURCES},
        cross_source_shared_strings=[dict(sequence=s, qwen=cnt["qwen"][s], mistral=cnt["mistral"][s]) for s in cross],
        families_with_identical_first_block=[f["family_id"] for f in families if f["qwen"][0] == f["mistral"][0]],
        families_sharing_any_string_across_sources=[f["family_id"] for f in families if set(f["qwen"]) & set(f["mistral"])],
        families_identical_full_sample=[f["family_id"] for f in families if f["qwen"] == f["mistral"]],
        familiar_strings_also_in_evaluation={m: sum(x["sequence"] in fam_seq[m] | fam_seq[C.OTHER[m]] for x in familiar[m])
                                             for m in C.SOURCES},
        within_family_repeated_blocks={m: sum(len(set(f[m])) < len(f[m]) for f in families) for m in C.SOURCES})
