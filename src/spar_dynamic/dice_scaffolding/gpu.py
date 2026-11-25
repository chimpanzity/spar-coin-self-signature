"""Collection for Experiment 33 (one model per process; rented GPU). Scoring is Experiment 31's `forced_dists`, `history_ids` and
archival check on the Experiment 27-32 engine, unchanged (bf16 weights, fp32 output layer, batch 1, incremental KV cache).

collect --phase core:       env + vocabulary scan; Experiment 31 archival G/F replay (stop rule); boundary instrumentation; development
                            face-mass look; dice-free associations, scored and hashed BEFORE any dice row; direct references; forecasts;
                            bit-identity repeats and full-pass floor.
collect --phase extensions: archival replay again (new process); factual attribution; extension references, cued generation, forecasts,
                            verbal distributions, free sequences.
Rows are appended one per line with a deterministic row_id; a resumed run verifies existing rows and skips them.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path

from spar_dynamic.dice_31_32 import gpu as G31
from spar_dynamic.dice_scaffolding import config as C
from spar_dynamic.dice_scaffolding import design as D

PKG = Path(__file__).resolve().parent
SCORER_VERSION = "exp33-v1 (dice_31_32.gpu.forced_dists incremental)"
canonical_sha = G31.canonical_sha


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def code_sha() -> dict:
    files = sorted(PKG.glob("*.py"))
    files += [PKG.parent / d / f for d, f in (("dice_31_32", "gpu.py"), ("dice_31_32", "config.py"), ("dice_31_32", "stimuli.py"),
                                              ("dice_crossed_guidance", "models.py"), ("dice_crossed_guidance", "config.py"),
                                              ("dice_logprob_crossmodel", "gpu.py"), ("dice_logprob", "prompts.py"),
                                              ("dice_logprob", "gpu_runner.py"))]
    return {f"{p.parent.name}/{p.name}": canonical_sha(p) for p in files}


def guard_out(root):
    for part in os.path.abspath(str(root)).replace("\\", "/").split("/"):
        m = re.match(r"^(\d{2})_\d{4}-\d{2}-\d{2}_", part)
        if m and int(m.group(1)) <= C.LAST_FROZEN_INDEX:
            raise SystemExit(f"refusing to write into frozen experiment folder {part}")


# ---------- row storage ----------

class Store:
    """Append-only JSONL keyed by row_id. Rejects conflicting duplicates; drops one torn final line on resume."""

    def __init__(self, path):
        self.path, self.rows = Path(path), {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raw = self.path.read_bytes()
            if raw and not raw.endswith(b"\n"):
                raw = raw[:raw.rfind(b"\n") + 1]
                self.path.write_bytes(raw)
            for line in raw.decode("utf-8").splitlines():
                r = json.loads(line)
                if r["row_id"] in self.rows:
                    raise SystemExit(f"duplicate row {r['row_id']} in {self.path}")
                self.rows[r["row_id"]] = r

    def has(self, rid):
        return rid in self.rows

    def add(self, row):
        rid = row["row_id"]
        if rid in self.rows:
            raise SystemExit(f"conflicting duplicate row {rid}")
        bad = [v for v in row.get("l", []) if not math.isfinite(v)]
        if bad:
            raise SystemExit(f"STOP: nonfinite score in {rid}")
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.rows[rid] = row


def row_id(eng, assay, prompt_sha, boundary, history="", extra="") -> str:
    return hashlib.sha256("|".join([C.TAG, eng.commit, assay, prompt_sha, boundary, history, SCORER_VERSION, extra]).encode()).hexdigest()[:24]


def normalise(l) -> dict:
    """Handoff 5.4: natural-log face scores -> log mass, mass, conditional log-probabilities and probabilities (float64)."""
    m = max(l)
    log_mass = m + math.log(sum(math.exp(x - m) for x in l))
    log_q = [x - log_mass for x in l]
    return dict(l=list(l), log_mass=log_mass, mass=math.exp(log_mass), log_q=log_q, q=[math.exp(x) for x in log_q])


def compact(eng, d) -> dict:
    """The stored part of a `forced_dists` record."""
    return dict(**normalise([d["face_logprobs"][str(f)] for f in C.FACES]), digit_ids=[eng.face_ids[f] for f in C.FACES],
                argmax_token_id=d["argmax_token_id"], argmax_token=d["argmax_token"], argmax_logprob=d["argmax_logprob"],
                separator_logprob=d["separator_logprob"], entropy_bits=d["entropy_bits"], top=d["top"][:C.TOP_STORED])


_RUN = {}


def base(eng, assay, prompt, boundary) -> dict:
    ids = eng.prompt_ids(prompt)
    return dict(model=eng.key, revision=eng.commit, assay=assay, prompt_sha256=D.sha256(prompt),
                prompt_token_sha256=hashlib.sha256(json.dumps(ids).encode()).hexdigest(), n_prompt_tokens=len(ids), n_chars=len(prompt),
                boundary=boundary, dtype="bf16 weights, fp32 logits", scorer_version=SCORER_VERSION, run_id=_RUN.get("id"), timestamp=now())


# ---------- scoring ----------

def score_forecast(eng, item) -> dict:
    """F: h is in the user turn; score the first assistant decision."""
    d = G31.forced_dists(eng, item["prompt"], [], "incremental")[0]
    return dict(row_id=row_id(eng, "forecast", item["prompt_sha256"], "first_answer"), **base(eng, "forecast", item["prompt"], "first_answer"),
                history=item["history"], k=len(D.faces_of(item["history"])) + 1, **compact(eng, d))


def direct_ids(eng, path) -> list:
    """Canonical assistant history plus one trailing separator after the last face (handoff 5.1)."""
    x = D.faces_of(path)
    return G31.history_ids(eng, x) + [C.SEPARATOR_ID[eng.key]] if x else []


def score_direct(eng, job, method="incremental") -> list:
    forced = direct_ids(eng, job["path"])
    ds = G31.forced_dists(eng, job["prompt"], forced, method, at=[2 * n for n in job["lengths"]])
    out = []
    for n, d in zip(job["lengths"], ds):
        h = D.seq(D.faces_of(job["path"])[:n])
        assert d["n_forced"] == 2 * n
        b = "first_assistant" if n == 0 else "after_separator"
        out.append(dict(row_id=row_id(eng, job["assay"], job["prompt_sha256"], b, h), **base(eng, job["assay"], job["prompt"], b), history=h, k=n + 1,
                        path=job["path"], forced_ids=d["forced_ids"], subject=job["subject"], **compact(eng, d)))
    return out


def letter_ids(eng, letters) -> dict:
    out = {}
    for x in letters:
        ids = eng.hist_ids(x)
        if len(ids) != 1 or eng.decode(ids) != x:
            raise SystemExit(f"STOP: letter {x} is not one token for {eng.key}: {ids}")
        out[x] = ids[0]
    if len(set(out.values())) != len(letters):
        raise SystemExit("STOP: letter tokens are not distinct")
    return out


def letter_variants(eng) -> list:
    """Vocabulary tokens whose text is A-D with surrounding whitespace, other than the bare letter."""
    if eng.key == "qwen":
        n, first, dec = len(eng.tok), 0, lambda i: eng.tok.decode([i])
    else:
        n, first, dec = eng.t.n_words, eng.t.num_special_tokens, lambda i: eng.t.decode([i])
    bare = set(letter_ids(eng, "ABCD").values())
    out = []
    for i in range(first, n):
        if i in bare:
            continue
        try:
            s = dec(i)
        except Exception:
            continue
        if re.fullmatch(r"\s*[ABCD]\s*", s):
            out.append(i)
    return out


def score_letters(eng, item, variants) -> dict:
    import torch
    with torch.no_grad():
        lp = torch.log_softmax(eng._fwd(eng.prompt_ids(item["prompt"])).logits[0, -1].float(), dim=-1)
    ids = letter_ids(eng, item["letters"])
    l = [float(lp[ids[x]]) for x in item["letters"]]
    top = torch.topk(lp, C.TOP_STORED)
    meta = {k: v for k, v in item.items() if k not in ("prompt", "assay", "prompt_sha256")}
    return dict(row_id=row_id(eng, item["assay"], item["prompt_sha256"], "first_answer", extra=json.dumps(meta, sort_keys=True)),
                **base(eng, item["assay"], item["prompt"], "first_answer"), **meta, l=l, letter_ids=[ids[x] for x in item["letters"]],
                mass=float(sum(math.exp(x) for x in l)), variant_mass=float(lp[variants].exp().sum()) if variants else 0.0,
                argmax_token=eng.decode([int(top.indices[0])]), top=[[int(i), eng.decode([int(i)]), float(v)] for v, i in zip(top.values.tolist(), top.indices.tolist())])


def greedy(eng, prompt, max_new) -> dict:
    """Engine.generate's greedy arithmetic with a per-readout token budget (engine constant is 128)."""
    import torch
    with torch.no_grad():
        out = eng._fwd(eng.prompt_ids(prompt))
        gen, finish = [], "length"
        for _ in range(max_new):
            nxt = int(torch.argmax(torch.log_softmax(out.logits[0, -1].float(), dim=-1)).item())
            if nxt in eng.eos:
                finish = "stop"
                break
            gen.append(nxt)
            out = eng._fwd([nxt], out.past_key_values)
    return dict(generated_ids=gen, content=eng.decode(gen), finish_reason=finish, max_new_tokens=max_new)


# ---------- parsers ----------

_NUM = re.compile(r"(?<![\w.])[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse_verbal(text):
    """Exactly six finite nonnegative numbers (optional %), total within 1 point of 100 -> (normalised list, None) or (None, reason)."""
    if re.search(r"\b(nan|inf|infinity)\b", text, re.I):
        return None, "nonfinite"
    v = [float(x) for x in _NUM.findall(text)]
    if len(v) != 6:
        return None, f"{len(v)} numbers"
    if any(not math.isfinite(x) or x < 0 for x in v):
        return None, "negative or nonfinite"
    if abs(sum(v) - 100) > C.VERBAL_TOL_PP + 1e-9:
        return None, f"total {sum(v):g}"
    return [x / sum(v) for x in v], None


def parse_free(text):
    return tuple(int(x) for x in text.split()) if re.fullmatch(r"\s*[1-6](?:\s+[1-6]){9}\s*", text) else None


# ---------- preflight ----------

def instrumentation(eng) -> dict:
    """G and F (archival) at the empty prefix and after 5 2 6: separator boundary precedes the face boundary; both arithmetic paths."""
    res = {}
    sep = C.SEPARATOR_ID[eng.key]
    for k, p in (("G", D.G), ("F", D.F_ARCHIVE)):
        forced = G31.history_ids(eng, (5, 2, 6)) + [sep]
        inc = G31.forced_dists(eng, p, forced, "incremental")
        full = G31.forced_dists(eng, p, forced, "full_pass")
        fl = max(abs(math.exp(a["face_logprobs"][f]) - math.exp(b["face_logprobs"][f])) for a, b in zip(inc, full) for f in a["face_logprobs"])
        ids = eng.prompt_ids(p)
        res[k] = dict(prompt_tail_text=eng.decode(ids[-8:]), forced_ids=forced, separator_boundary_argmax=[inc[n]["argmax_token_id"] for n in (1, 3, 5)],
                      separator_logprob=[inc[n]["separator_logprob"] for n in (1, 3, 5)],
                      face_boundary_mass=[sum(math.exp(v) for v in inc[n]["face_logprobs"].values()) for n in (0, 2, 4, 6)],
                      face_boundary_argmax_is_face=[inc[n]["argmax_token_id"] in eng.face_ids.values() for n in (0, 2, 4, 6)], floor_max_dp=fl)
        res[k]["ok"] = (all(i == sep for i in res[k]["separator_boundary_argmax"]) and all(res[k]["face_boundary_argmax_is_face"])
                        and fl <= C.FLOOR_STOP_P)
    return res


def on_path(eng, arch) -> dict:
    """Teacher-forced G on this model's own greedy path reproduces the generation trace's six-face scores."""
    g = next(r for r in arch if r["condition"] == "G" and r["replicate"] == 1)
    x = tuple(C.REFERENCES[(eng.key, "G")])
    job = dict(assay="direct_G", prompt=D.G, prompt_sha256=D.sha256(D.G), subject=None, path=D.seq(x[:9]), lengths=list(range(10)))
    rows = score_direct(eng, job)
    dl = max(abs(a - s["face_logprobs"][str(f)]) for r, s in zip(rows, g["digit_steps"]) for a, f in zip(r["l"], C.FACES))
    return dict(max_abs_dlogp=dl, ok=dl <= C.SCORER_TOL_LOGP and len(g["digit_steps"]) == 10)


def preflight(eng, raw, phase) -> dict:
    import accelerate
    import huggingface_hub
    from spar_dynamic.dice_logprob_crossmodel.gpu import vocab_scan
    vs = vocab_scan(eng)
    if vs["variant_face_tokens"]:
        raise SystemExit(f"STOP: variant face tokens {vs['variant_face_tokens'][:5]}")
    ids = [eng.hist_ids(str(f)) for f in C.FACES]
    if ids != [[eng.face_ids[f]] for f in C.FACES] or len({i[0] for i in ids}) != 6 or [eng.decode(i) for i in ids] != [str(f) for f in C.FACES]:
        raise SystemExit("STOP: six distinct bare digit tokens required")
    arch = G31.archival(eng)
    chk = G31.archival_check(eng, arch, C.EXP28_MAIN)
    inst, op = instrumentation(eng), on_path(eng, arch)
    env = dict(eng.env(), phase=phase, started_utc=now(), vocab_scan=vs, archival_check=chk, instrumentation=inst, on_path=op,
               letter_variant_ids=letter_variants(eng), letter_ids=letter_ids(eng, "ABCD"), rendered_G=eng.rendered_text(D.G),
               rendered_T1_example=eng.rendered_text(D.forecast_prompt(C.NEUTRAL, "5 2 6")), prompt_manifest_sha256=D.prompt_manifest_sha(),
               accelerate=accelerate.__version__, huggingface_hub=huggingface_hub.__version__, code_sha256=code_sha(),
               code_commit=os.environ.get("SPAR_CODE_COMMIT", "unknown"), hourly_usd=os.environ.get("SPAR_HOURLY_USD"), run_id=_RUN.get("id"))
    path = raw / f"env_{phase}.json"
    json.dump(env, open(path, "w", encoding="utf-8", newline="\n"), indent=2)
    with open(raw / f"archival_{phase}.jsonl", "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r) + "\n" for r in arch)
    if not (chk["ok"] and op["ok"] and all(v["ok"] for v in inst.values())):
        raise SystemExit(f"STOP: preflight failed: {json.dumps(dict(archival=chk['ok'], on_path=op, instrumentation={k: v['ok'] for k, v in inst.items()}))}")
    return env


# ---------- phases ----------

def association_scores(rows) -> dict:
    """A(p, w) = mean over eight prompts of log p(first agent) - log p(second agent); per kind, word, wording."""
    out = {}
    for r in rows:
        d = r["l"][r["letters"].index(r["first_letter"])] - r["l"][r["letters"].index(r["second_letter"])]
        out.setdefault((r["kind"], r["word"]), []).append((r["wording"], r["order"], r["label"], d))
    res = {}
    for (kind, w), v in out.items():
        res.setdefault(kind, {})[w] = dict(A=sum(x[3] for x in v) / len(v), n=len(v),
                                           by_wording=[sum(x[3] for x in v if x[0] == j) / sum(x[0] == j for x in v) for j in (0, 1)])
    return res


def run_rows(store, items, fn, rid, label):
    t0, n = time.time(), 0
    for i, it in enumerate(items, 1):
        if store.has(rid(it)):
            continue
        store.add(fn(it))
        n += 1
        if n % 200 == 0:
            print(f"[{label}] {i}/{len(items)} | {(time.time() - t0) / n:.3f} s/row", flush=True)
    print(f"[{label}] done {len(items)} ({n} new) in {time.time() - t0:.0f} s", flush=True)


def run_direct(eng, store, phase):
    for j in D.direct_jobs(phase):
        last = D.seq(D.faces_of(j["path"])[:j["lengths"][-1]])
        if store.has(row_id(eng, j["assay"], j["prompt_sha256"], "after_separator" if last else "first_assistant", last)):
            continue
        for r in score_direct(eng, j):
            if not store.has(r["row_id"]):
                store.add(r)


def run_forecasts(eng, store, phase):
    run_rows(store, D.unique_forecasts(phase), lambda it: score_forecast(eng, it),
             lambda it: row_id(eng, "forecast", it["prompt_sha256"], "first_answer"), f"{eng.key} forecasts {phase}")


def repro(eng, fstore, dstore) -> dict:
    """Bit-identity of re-scored forecasts and direct streams, and the incremental-vs-full-pass floor on the core direct bank."""
    items = D.unique_forecasts("core")
    step = max(1, len(items) // C.N_REPRO)
    bad_f = 0
    for it in items[::step][:C.N_REPRO]:
        bad_f += score_forecast(eng, it)["l"] != fstore.rows[row_id(eng, "forecast", it["prompt_sha256"], "first_answer")]["l"]
    bad_d, floor = 0, 0.0
    for j in D.direct_jobs("core"):
        for a, b in zip(score_direct(eng, j), score_direct(eng, j, "full_pass")):
            s = dstore.rows[a["row_id"]]
            bad_d += a["l"] != s["l"]
            floor = max(floor, max(abs(math.exp(x) - math.exp(y)) for x, y in zip(s["l"], b["l"])))
    return dict(forecasts_rescored=min(C.N_REPRO, len(items[::step])), forecast_mismatches=bad_f, direct_mismatches=bad_d, floor_max_dp=floor,
                ok=bad_f == 0 and bad_d == 0 and floor <= C.FLOOR_STOP_P)


def collect(eng, phase, root=None):
    root = Path(root or C.EXP)
    guard_out(root)
    raw = root / "raw" / eng.key
    raw.mkdir(parents=True, exist_ok=True)
    _RUN["id"] = f"{eng.key}-{phase}-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}"
    t0 = time.time()
    if phase == "extensions" and not (raw / "done_core.json").exists():
        raise SystemExit("extensions need a completed core run")
    env = preflight(eng, raw, phase)
    print(f"preflight ok in {time.time() - t0:.0f} s", flush=True)
    fs, ds = Store(raw / f"forecasts_{phase}.jsonl"), Store(raw / f"direct_{phase}.jsonl")
    info = {}
    if phase == "core":
        look = [C.NEUTRAL, D.subject_word("red")]                # development words and family only
        h = next(r["history"] for r in D.constructed() if r["split"] == "development")
        info["development_look"] = [dict(subject=s, mass=x["mass"], argmax=x["argmax_token"], q=x["q"]) for s in look
                                    for x in [score_forecast(eng, dict(prompt=D.forecast_prompt(s, h), prompt_sha256="look", history=h))]]
        print("development look:", info["development_look"], flush=True)
        a = Store(raw / "associations.jsonl")
        run_rows(a, D.association_items(), lambda it: score_letters(eng, it, env["letter_variant_ids"]),
                 lambda it: row_id(eng, it["assay"], it["prompt_sha256"], "first_answer",
                                   extra=json.dumps({k: v for k, v in it.items() if k not in ("prompt", "assay", "prompt_sha256")}, sort_keys=True)),
                 f"{eng.key} associations")
        sc = raw / "association_scores.json"
        text = json.dumps(association_scores(a.rows.values()), indent=1, sort_keys=True) + "\n"
        if sc.exists() and sc.read_text(encoding="utf-8") != text:
            raise SystemExit("STOP: association scores changed on resume")
        sc.write_text(text, encoding="utf-8", newline="\n")
        seal = raw / "association_seal.json"
        if not seal.exists():
            seal.write_text(json.dumps(dict(sealed_utc=now(), scores_sha256=canonical_sha(sc), rows_sha256=canonical_sha(raw / "associations.jsonl"),
                                            dice_rows_at_seal=len(fs.rows) + len(ds.rows))) + "\n", encoding="utf-8", newline="\n")
    else:
        f = Store(raw / "facts.jsonl")
        run_rows(f, D.fact_items(), lambda it: score_letters(eng, it, env["letter_variant_ids"]),
                 lambda it: row_id(eng, it["assay"], it["prompt_sha256"], "first_answer",
                                   extra=json.dumps({k: v for k, v in it.items() if k not in ("prompt", "assay", "prompt_sha256")}, sort_keys=True)),
                 f"{eng.key} facts")
    t1 = time.time()
    run_direct(eng, ds, phase)
    print(f"direct {phase}: {len(ds.rows)} rows in {time.time() - t1:.0f} s", flush=True)
    run_forecasts(eng, fs, phase)
    if phase == "core":
        info["repro"] = repro(eng, fs, ds)
        print("repro:", info["repro"], flush=True)
    else:
        g = Store(raw / "generations.jsonl")
        for it in [dict(x, assay="verbal", max_new=C.VERBAL_MAX_NEW) for x in D.verbal_items()] + \
                [dict(x, assay="free", history="", max_new=C.FREE_MAX_NEW) for x in D.free_items()]:
            rid = row_id(eng, it["assay"], it["prompt_sha256"], "generation")
            if not g.has(rid):
                g.add(dict(row_id=rid, **base(eng, it["assay"], it["prompt"], "generation"), subject_key=it["subject_key"], subject=it["subject"],
                           history=it["history"], **greedy(eng, it["prompt"], it["max_new"])))
        print(f"generations {len(g.rows)}", flush=True)
    files = {p.name: canonical_sha(p) for p in sorted(raw.glob("*.json*")) if not p.name.startswith("done_")}
    json.dump(dict(phase=phase, model=eng.key, finished_utc=now(), seconds=round(time.time() - t0, 1), files=files, run_id=_RUN["id"],
                   max_memory_allocated_gb=eng.env_common().get("max_memory_allocated_gb"), **info),
              open(raw / f"done_{phase}.json", "w", encoding="utf-8", newline="\n"), indent=2)
    if phase == "core" and not info["repro"]["ok"]:
        raise SystemExit("STOP: reproducibility check failed")
