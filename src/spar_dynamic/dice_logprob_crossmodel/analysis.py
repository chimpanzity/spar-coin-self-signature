"""Offline analysis for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (prespecified in PROTOCOL_FROZEN.md, section "Analysis plan").

Input per model: main/<model>/{raw_attempts,matched_prefix}.jsonl. Everything is recomputed from raw records.
Greedy decoding is deterministic, so the 20 replicates of a condition are reliability checks, not independent samples: each
condition contributes one output and one set of six-face vectors (its modal output, which must be its only output for G
and F). No p-values over replicates are computed anywhere.

Six-face vector p6 = full-vocabulary log-probs of the six bare face tokens, renormalised over the faces (the distribution
conditional on emitting a face); raw mass = their summed probability. A position's top face is a near-tie when its margin
over the runner-up is below the model's numerical floor (max |dp6| between incremental and full-pass arithmetic).
"""

from __future__ import annotations

import math
from collections import Counter

from spar_dynamic.dice_crossed_guidance.analysis import _lp, entropy_bits, js_bits, parse_n, rank_of, read_jsonl, six
from spar_dynamic.dice_logprob_crossmodel import config as C
from spar_dynamic.dice_logprob_crossmodel import prompts as P

FACES = C.FACES
U6 = [1 / 6] * 6


def r4(x):
    return None if x is None else round(x, 4)


def load(model: str, d=None) -> dict:
    d = d or C.MAIN / model
    return dict(model=model, raw=read_jsonl(d / "raw_attempts.jsonl"), mp=read_jsonl(d / "matched_prefix.jsonl"))


# ---------- vectors ----------

def vec(face_logprobs: dict) -> dict:
    p, mass = six(face_logprobs)
    order = sorted(FACES, key=lambda f: -p[f - 1])
    return dict(lp=_lp(face_logprobs), p=p, mass=mass, top=order[0], top_p=p[order[0] - 1], second=order[1],
                margin=p[order[0] - 1] - p[order[1] - 1])


def floors(data: dict) -> dict:
    """Numerical floor: max |dp6| and max JS between incremental and full-pass scoring over the predefined subset."""
    dps, jss = [], []

    def add(a, b):
        va, vb = vec(a), vec(b)
        dps.append(max(abs(x - y) for x, y in zip(va["p"], vb["p"])))
        jss.append(js_bits(va["p"], vb["p"]))
    for r in data["raw"]:
        if r.get("own_rescored_full_pass"):
            for x, y in zip(r["own_rescored"], r["own_rescored_full_pass"]):
                add(x["face_logprobs"], y["face_logprobs"])
    inc = {(x["kind"], x["instruction"], x["history"], x["position"]): x["face_logprobs"] for x in data["mp"] if x["method"] == "incremental"}
    for x in data["mp"]:
        if x["method"] == "full_pass":
            add(inc[(x["kind"], x["instruction"], x["history"], x["position"])], x["face_logprobs"])
    return dict(dp=max(dps), js_bits=max(jss), n=len(dps))


def modal(data: dict) -> dict:
    """Per condition: its modal output record (lowest replicate) and reliability statistics over replicates."""
    out = {}
    for c in P.conditions():
        rs = sorted((r for r in data["raw"] if r["condition"] == c["condition"]), key=lambda r: r["replicate"])
        cnt = Counter(r["content"] for r in rs)
        content = cnt.most_common(1)[0][0]
        rec = next(r for r in rs if r["content"] == content)
        spread = 0.0
        for r in rs:
            if r["content"] == content:
                for a, b in zip(r["digit_steps"], rec["digit_steps"]):
                    spread = max(spread, max(abs(x - y) for x, y in zip(vec(a["face_logprobs"])["p"], vec(b["face_logprobs"])["p"])))
        faces = parse_n(content, c["n_expected"]) if rec["finish_reason"] == "stop" else None
        out[c["condition"]] = dict(rec=rec, content=content, faces=faces, valid=faces is not None, n=len(rs),
                                   n_valid=sum(bool(parse_n(r["content"], c["n_expected"])) and r["finish_reason"] == "stop" for r in rs),
                                   n_distinct=len(cnt), modal_count=cnt[content], max_dp_spread=spread)
    return out


def free_positions(m: dict) -> dict:
    """{condition: {original position: row}} for valid modal outputs; plus S/W first-token rows for every output."""
    out = {}
    for k, v in m.items():
        rec, rows = v["rec"], {}
        if v["valid"] and len(rec["digit_steps"]) == len(v["faces"]):
            for j, (pos, s) in enumerate(zip(rec["target_positions"], rec["digit_steps"])):
                assert int(s["token"]) == v["faces"][j], "digit step does not match the parsed face"
                rows[pos] = dict(vec(s["face_logprobs"]), face=v["faces"][j], local_index=j + 1,
                                 prefix=" ".join(map(str, v["faces"][:j])), token_id=s["token_id"])
        first = vec(rec["steps"][0]["face_logprobs"]) if rec["steps"] else None
        face_ids = set(C.MODEL[rec["model"]]["face_ids"].values())
        out[k] = dict(rows=rows, first_token=first, first_token_is_face=bool(rec["steps"]) and rec["steps"][0]["token_id"] in face_ids)
    return out


def scored(data: dict, kind: str) -> dict:
    """{(instruction, history): {original position: row}} for incremental matched rows of one kind."""
    out = {}
    for x in data["mp"]:
        if x["kind"] == kind and x["method"] == "incremental":
            out.setdefault((x["instruction"], x["history"]), {})[x["original_position"]] = dict(vec(x["face_logprobs"]), face=x["history_face"])
    return out


def _cmp(a: dict, b: dict) -> dict:
    """a vs b at one position: JS, chosen-face agreement, each side's probability and rank of the other's chosen face."""
    return dict(js=r4(js_bits(a["p"], b["p"])), same_face=a["face"] == b["face"], same_top=a["top"] == b["top"],
                p_b_face_under_a=r4(a["p"][b["face"] - 1]), rank_b_face_under_a=rank_of(a["p"], b["face"]),
                p_a_face_under_b=r4(b["p"][a["face"] - 1]), rank_a_face_under_b=rank_of(b["p"], a["face"]))


# ---------- sequence structure ----------

def bigrams(s):
    return [(a, b) for a, b in zip(s, s[1:])]


def best_shift(a, b) -> dict:
    """Shift s maximising matches a[i] == b[i + s] (s in -9..9), and the longest common contiguous run."""
    best = max(((sum(1 for i in range(len(a)) if 0 <= i + s < len(b) and a[i] == b[i + s]), -abs(s), s) for s in range(-9, 10)))
    lcs, at = 0, None
    for i in range(len(a)):
        for j in range(len(b)):
            n = 0
            while i + n < len(a) and j + n < len(b) and a[i + n] == b[j + n]:
                n += 1
            if n > lcs:
                lcs, at = n, (i + 1, j + 1)
    return dict(shift=best[2], matches_at_shift=best[0], longest_common_run=lcs, run_start_a_b=at)


def structure(s) -> dict:
    c = Counter(s)
    return dict(sequence=" ".join(map(str, s)), counts={f: c.get(f, 0) for f in FACES}, adjacent_repeats=sum(a == b for a, b in bigrams(s)),
                first6_is_permutation=sorted(s[:6]) == list(FACES), distinct_in_every_6_window=all(len(set(s[i:i + 6])) == 6 for i in range(len(s) - 5)),
                steps_mod6=[(b - a) % 6 for a, b in bigrams(s)])


# ---------- analyses ----------

def integrity(data, m, fl) -> list:
    rows = []
    for c in P.conditions():
        v = m[c["condition"]]
        ms = [vec(s["face_logprobs"])["mass"] for s in v["rec"]["digit_steps"]]
        rows.append(dict(model=data["model"], condition=c["condition"], n=v["n"], n_valid=v["n_valid"], n_distinct_outputs=v["n_distinct"],
                         modal_output=v["content"] if len(v["content"]) <= 60 else v["content"][:57] + "...",
                         modal_count=v["modal_count"], max_dp_spread_across_replicates=v["max_dp_spread"],
                         finish_reason=v["rec"]["finish_reason"], completion_tokens=v["rec"]["completion_tokens"],
                         min_six_face_mass=r4(min(ms)) if ms else None, mean_six_face_mass=r4(sum(ms) / len(ms)) if ms else None,
                         floor_dp=r4(fl["dp"]), prompt_sha256=c["prompt_sha256"]))
    return rows


def natural_gf(fp, m, fl) -> dict:
    g, f = fp["G"]["rows"], fp["F"]["rows"]
    rows = []
    for k in range(1, 11):
        a, b = g[k], f[k]
        rows.append(dict(position=k, G_face=a["face"], F_face=b["face"], G_p=[r4(x) for x in a["p"]], F_p=[r4(x) for x in b["p"]],
                         G_prefix=a["prefix"], F_prefix=b["prefix"], same_history=a["prefix"] == b["prefix"],
                         G_near_tie=a["margin"] < fl["dp"], F_near_tie=b["margin"] < fl["dp"], **_cmp(a, b)))
    gs, fs = m["G"]["faces"], m["F"]["faces"]
    summ = dict(G=" ".join(map(str, gs)), F=" ".join(map(str, fs)), exact_sequence_match=gs == fs,
                aligned_face_matches=sum(a == b for a, b in zip(gs, fs)),
                shared_bigrams=sum(1 for x in bigrams(gs) if x in set(bigrams(fs))), **best_shift(gs, fs),
                position1=rows[0], mean_js_2_10=r4(sum(r["js"] for r in rows[1:]) / 9), mean_js_all=r4(sum(r["js"] for r in rows) / 10))
    return dict(rows=rows, summary=summ)


def matched_gf(sc, fp, fl) -> dict:
    rows, summ = [], {}
    nat = {k: fp["G"]["rows"][k]["face"] != fp["F"]["rows"][k]["face"] for k in range(1, 11)}
    for h in ("G", "F"):
        a, b = sc[("G", h)], sc[("F", h)]
        dis = []
        for k in range(1, 11):
            x, y = dict(a[k], face=a[k]["top"]), dict(b[k], face=b[k]["top"])
            row = dict(history=h, position=k, history_face=a[k]["face"], G_top=x["top"], F_top=y["top"],
                       G_p=[r4(v) for v in x["p"]], F_p=[r4(v) for v in y["p"]], js=r4(js_bits(x["p"], y["p"])),
                       top_agree=x["top"] == y["top"], G_margin=r4(x["margin"]), F_margin=r4(y["margin"]),
                       near_tie=min(x["margin"], y["margin"]) < fl["dp"], G_top_is_history=x["top"] == a[k]["face"],
                       F_top_is_history=y["top"] == a[k]["face"],
                       p_history_face_G=r4(x["p"][a[k]["face"] - 1]), p_history_face_F=r4(y["p"][a[k]["face"] - 1]))
            rows.append(row)
            dis.append(row)
        later = dis[1:]
        robust = [r for r in later if not r["top_agree"] and not r["near_tie"]]
        summ[h] = dict(top_disagreements_2_10=sum(not r["top_agree"] for r in later), robust_disagreements_2_10=len(robust),
                       robust_positions=[r["position"] for r in robust], mean_js_2_10=r4(sum(r["js"] for r in later) / 9),
                       max_js_2_10=max(r["js"] for r in later), js_position1=dis[0]["js"],
                       natural_disagreements_2_10=sum(nat[k] for k in range(2, 11)),
                       natural_disagreements_resolved_2_10=sum(1 for r in later if nat[r["position"]] and r["top_agree"]))
    return dict(rows=rows, summary=summ)


def singles(fp, m, fl) -> dict:
    g, f = fp["G"]["rows"], fp["F"]["rows"]
    rows = []
    for k in range(1, 11):
        v, s = m[f"S{k}"], fp[f"S{k}"]
        ft = s["first_token"]
        face = v["faces"][0] if v["valid"] else None
        x = dict(ft, face=face if face is not None else ft["top"])
        rows.append(dict(position=k, S_output=v["content"][:40], S_valid=v["valid"], S_face=face, S_top=ft["top"], S_mass=r4(ft["mass"]),
                         S_p=[r4(p) for p in ft["p"]], S_near_tie=ft["margin"] < fl["dp"], G_face=g[k]["face"], F_face=f[k]["face"],
                         **{f"vsG_{a}": b for a, b in _cmp(x, g[k]).items()}, **{f"vsF_{a}": b for a, b in _cmp(x, f[k]).items()}))
    faces = [r["S_face"] if r["S_face"] is not None else r["S_top"] for r in rows]
    mean_p = [sum(r["S_p"][i] for r in rows) / 10 for i in range(6)]
    summ = dict(S_faces=faces, n_valid=sum(r["S_valid"] for r in rows), matches_G=sum(r["vsG_same_face"] for r in rows),
                matches_F=sum(r["vsF_same_face"] for r in rows), chance_expected=round(10 / 6, 2),
                mean_js_vs_G=r4(sum(r["vsG_js"] for r in rows) / 10), mean_js_vs_F=r4(sum(r["vsF_js"] for r in rows) / 10),
                S_face_counts=dict(Counter(faces)), distinct_S_faces=len(set(faces)), mean_S_p=[r4(x) for x in mean_p],
                mean_S_entropy_bits=r4(sum(entropy_bits(r["S_p"]) for r in rows) / 10),
                S1_vs_G1_js=rows[0]["vsG_js"], S1_vs_F1_js=rows[0]["vsF_js"])
    return dict(rows=rows, summary=summ)


def windows(fp, m, sc, fl) -> dict:
    g, f = fp["G"]["rows"], fp["F"]["rows"]
    wsc = sc
    rows, summ = [], {}
    for a, b in C.WINDOWS:
        w = f"W{a}-{b}"
        v, nat = m[w], fp[w]["rows"]
        for k in range(a, b + 1):
            s = fp[f"S{k}"]
            sv = dict(s["first_token"], face=m[f"S{k}"]["faces"][0] if m[f"S{k}"]["valid"] else s["first_token"]["top"])
            row = dict(window=w, position=k, local_index=k - a + 1, W_output=v["content"][:40], W_valid=v["valid"])
            if k in nat:
                x = nat[k]
                row.update(W_face=x["face"], W_prefix=x["prefix"], W_p=[r4(p) for p in x["p"]], W_near_tie=x["margin"] < fl["dp"],
                           **{f"vsG_{c}": d for c, d in _cmp(x, g[k]).items()}, **{f"vsF_{c}": d for c, d in _cmp(x, f[k]).items()},
                           **{f"vsS_{c}": d for c, d in _cmp(x, sv).items()})
            for h, ref in (("G", sc_ref(wsc, "G")), ("F", sc_ref(wsc, "F"))):
                y = wsc.get((w, h), {}).get(k)
                if y is not None and ref.get(k) is not None:
                    yt, rt = dict(y, face=y["top"]), dict(ref[k], face=ref[k]["top"])
                    row[f"matched_{h}_js_vs_{h}|{h}"] = r4(js_bits(y["p"], ref[k]["p"]))
                    row[f"matched_{h}_top"] = y["top"]
                    row[f"matched_{h}_top_agrees_{h}|{h}"] = yt["top"] == rt["top"]
                    row[f"matched_{h}_top_is_history"] = y["top"] == y["face"]
                    row[f"matched_{h}_mass"] = r4(y["mass"])
            rows.append(row)
        wr = [r for r in rows if r["window"] == w]
        nat_rows = [r for r in wr if "W_face" in r]
        summ[w] = dict(output=v["content"][:60], valid=v["valid"], n_positions=b - a + 1,
                       matches_G=sum(r["vsG_same_face"] for r in nat_rows), matches_F=sum(r["vsF_same_face"] for r in nat_rows),
                       matches_S=sum(r["vsS_same_face"] for r in nat_rows),
                       mean_js_vs_G=r4(sum(r["vsG_js"] for r in nat_rows) / len(nat_rows)) if nat_rows else None,
                       mean_js_vs_F=r4(sum(r["vsF_js"] for r in nat_rows) / len(nat_rows)) if nat_rows else None,
                       mean_js_vs_S=r4(sum(r["vsS_js"] for r in nat_rows) / len(nat_rows)) if nat_rows else None,
                       matched_G_mean_js=r4(_mean(r.get("matched_G_js_vs_G|G") for r in wr)),
                       matched_F_mean_js=r4(_mean(r.get("matched_F_js_vs_F|F") for r in wr)),
                       matched_G_top_agree=sum(bool(r.get("matched_G_top_agrees_G|G")) for r in wr),
                       matched_F_top_agree=sum(bool(r.get("matched_F_top_agrees_F|F")) for r in wr))
    ov = []
    for w1, w2, pos in C.OVERLAPS:
        n1, n2 = f"W{w1[0]}-{w1[1]}", f"W{w2[0]}-{w2[1]}"
        for k in pos:
            x, y = fp[n1]["rows"].get(k), fp[n2]["rows"].get(k)
            r = dict(pair=f"{n1} vs {n2}", position=k)
            if x and y:
                r.update(face_1=x["face"], face_2=y["face"], prefix_1=x["prefix"], prefix_2=y["prefix"], same_face=x["face"] == y["face"],
                         js=r4(js_bits(x["p"], y["p"])), same_top=x["top"] == y["top"])
            for h in ("G", "F"):
                p1, p2 = wsc.get((n1, h), {}).get(k), wsc.get((n2, h), {}).get(k)
                if p1 and p2:
                    r[f"matched_{h}_js"] = r4(js_bits(p1["p"], p2["p"]))
                    r[f"matched_{h}_same_top"] = p1["top"] == p2["top"]
            ov.append(r)
    return dict(rows=rows, summary=summ, overlaps=ov)


def sc_ref(sc, h):
    """Reference for a matched window under history h: the h instruction scored on its own full history (h|h)."""
    return sc.get(("mp", h, h), {})


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def dynamics(fp, m, sc) -> dict:
    """Descriptive: face marginals, repeats, permutation structure, and the probability given to repeating the previous face."""
    out = {}
    for k in ("G", "F"):
        rows = fp[k]["rows"]
        p_rep = [rows[j]["p"][rows[j - 1]["face"] - 1] for j in range(2, 11)]
        out[k] = dict(structure(m[k]["faces"]), mean_p_repeat_previous=r4(sum(p_rep) / 9), max_p_repeat_previous=r4(max(p_rep)),
                      uniform_p_repeat=r4(1 / 6))
    for x in ("G", "F"):
        for h in ("G", "F"):
            rr = sc.get(("mp", x, h)) or {}
            if len(rr) == 10:
                p_rep = [rr[j]["p"][rr[j - 1]["face"] - 1] for j in range(2, 11)]
                out[f"{x}|{h}_mean_p_repeat_previous"] = r4(sum(p_rep) / 9)
    for a, b in C.WINDOWS:
        w = f"W{a}-{b}"
        if m[w]["valid"]:
            out[w] = structure(m[w]["faces"])
    return out


def analyse_model(data: dict) -> dict:
    fl = floors(data)
    m = modal(data)
    fp = free_positions(m)
    mp = scored(data, "mp")
    sc = {("mp",) + k: v for k, v in mp.items()}
    sc.update(scored(data, "window"))
    for need in ("G", "F"):
        if not m[need]["valid"]:
            raise SystemExit(f"{data['model']}: {need} modal output is not valid; G/F analyses undefined")
    return dict(model=data["model"], floor=fl, integrity=integrity(data, m, fl), natural=natural_gf(fp, m, fl),
                matched=matched_gf(mp, fp, fl), singles=singles(fp, m, fl), windows=windows(fp, m, sc, fl),
                dynamics=dynamics(fp, m, sc), modal={k: v["content"] for k, v in m.items()})


def cross_model(res: dict) -> list:
    """One row per metric, one column per model (descriptive; two checkpoints, not model families)."""
    rows = []

    def add(name, fn):
        rows.append(dict(metric=name, **{k: fn(v) for k, v in res.items()}))
    add("G greedy sequence", lambda r: r["natural"]["summary"]["G"])
    add("F greedy sequence", lambda r: r["natural"]["summary"]["F"])
    add("valid outputs (of 300)", lambda r: sum(x["n_valid"] for x in r["integrity"]))
    add("conditions with >1 distinct output", lambda r: sum(x["n_distinct_outputs"] > 1 for x in r["integrity"]))
    add("numerical floor, max |dp6|", lambda r: r4(r["floor"]["dp"]))
    add("numerical floor, max JS bits", lambda r: r4(r["floor"]["js_bits"]))
    add("G vs F natural: aligned face matches /10", lambda r: r["natural"]["summary"]["aligned_face_matches"])
    add("G vs F natural: best shift (matches)", lambda r: f"{r['natural']['summary']['shift']} ({r['natural']['summary']['matches_at_shift']})")
    add("G vs F natural: longest common run", lambda r: r["natural"]["summary"]["longest_common_run"])
    add("G vs F position 1 JS bits (same empty history)", lambda r: r["natural"]["summary"]["position1"]["js"])
    add("G vs F natural mean JS, positions 2-10", lambda r: r["natural"]["summary"]["mean_js_2_10"])
    for h in ("G", "F"):
        add(f"matched prefix on {h} history: mean JS 2-10", lambda r, h=h: r["matched"]["summary"][h]["mean_js_2_10"])
        add(f"matched prefix on {h} history: top-face disagreements 2-10 (beyond floor)",
            lambda r, h=h: f"{r['matched']['summary'][h]['top_disagreements_2_10']} ({r['matched']['summary'][h]['robust_disagreements_2_10']})")
    add("S(k) valid /10", lambda r: r["singles"]["summary"]["n_valid"])
    add("S(k) faces, k=1..10", lambda r: " ".join(map(str, r["singles"]["summary"]["S_faces"])))
    add("S(k) = G(k) /10", lambda r: r["singles"]["summary"]["matches_G"])
    add("S(k) = F(k) /10", lambda r: r["singles"]["summary"]["matches_F"])
    add("S(k) mean JS vs G(k) / F(k)", lambda r: f"{r['singles']['summary']['mean_js_vs_G']} / {r['singles']['summary']['mean_js_vs_F']}")
    for a, b in C.WINDOWS:
        w = f"W{a}-{b}"
        add(f"{w} output", lambda r, w=w: r["windows"]["summary"][w]["output"])
        add(f"{w} = G / F / S faces (of {b - a + 1})",
            lambda r, w=w: f"{r['windows']['summary'][w]['matches_G']} / {r['windows']['summary'][w]['matches_F']} / {r['windows']['summary'][w]['matches_S']}")
    add("window overlaps agreeing (natural)", lambda r: f"{sum(bool(o.get('same_face')) for o in r['windows']['overlaps'])}/{len(r['windows']['overlaps'])}")
    return rows
