"""History bank, prompts, design manifest and association prompts for Experiment 33. Pure Python; no model calls.

Typographic quotes and apostrophes of the handoff are rendered as ASCII. `<BEGIN ORIGINAL INSTRUCTION>` / `<END ...>` are literal.
A condition is (template, scaffold, card, subject); a forecast prompt depends on the condition, the prefix and the fixed G text only.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from functools import lru_cache
from typing import Dict, List

from spar_dynamic.dice_31_32 import stimuli as S31
from spar_dynamic.dice_crossed_guidance.analysis import read_jsonl
from spar_dynamic.dice_scaffolding import config as C

G = S31.SOURCE_INSTRUCTION["G"]
F_ARCHIVE = S31.SOURCE_INSTRUCTION["F"]
seq = S31.seq


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def faces_of(h: str) -> tuple:
    return tuple(int(x) for x in h.split()) if h else ()


# ---------- history bank ----------

@lru_cache(maxsize=None)
def families() -> tuple:
    """16 ten-roll paths: ((rank, split, path), ...)."""
    dig = lambda t: ",".join(map(str, t))
    tri = sorted(itertools.permutations(C.FACES, 3), key=lambda t: (sha256(f"{C.VERSION}|triple|{dig(t)}"), t))[:C.N_FAMILIES]
    out = []
    for r, t in enumerate(tri, 1):
        tail = sorted((f for f in C.FACES if f not in t), key=lambda f: (sha256(f"{C.VERSION}|tail|{dig(t)}|{f}"), f))
        rest = sorted(C.FACES, key=lambda f: (sha256(f"{C.VERSION}|restart|{dig(t)}|{f}"), f))[:4]
        out.append((r, "development" if r <= C.N_DEV_FAMILIES else "confirmation", tuple(t) + tuple(tail) + tuple(rest)))
    return tuple(out)


def constructed() -> List[dict]:
    return [dict(bank="constructed", family=f"c{r:02d}", rank=r, split=sp, k=k, history=seq(p[:k - 1]),
                 subset=r in C.SUBSET_RANKS) for r, sp, p in families() for k in C.KS]


def opening() -> List[str]:
    return [""] + [str(a) for a in C.FACES] + [f"{a} {b}" for a, b in itertools.permutations(C.FACES, 2)]


@lru_cache(maxsize=None)
def natural_paths() -> tuple:
    """Experiment 27 sampled target runs (valid, full ten faces) plus the archived greedy G paths."""
    out = []
    for m in C.MODELS:
        rows = read_jsonl(C.CORPUS27 / m / "sampled.jsonl")
        for r in rows:
            if r["condition"] != "target":
                continue
            x = r["content"].split(" ")
            valid = bool(r["valid"]) and len(x) == 10 and all(v in "123456" and len(v) == 1 for v in x)
            out.append(dict(kind="sampled", source=m, seed=r["seed"], path=tuple(int(v) for v in x) if valid else None, valid=valid))
        out.append(dict(kind="greedy_G", source=m, seed=None, path=tuple(C.REFERENCES[(m, "G")]), valid=True))
    return tuple(out)


def archive_selection() -> List[dict]:
    sel = []
    for m in C.MODELS:
        c = [p for p in natural_paths() if p["kind"] == "sampled" and p["source"] == m and p["valid"]]
        sel += sorted(c, key=lambda p: (sha256(f"{C.VERSION}|archive|{m}|{p['seed']}"), p["seed"]))[:C.N_ARCHIVE_PATHS]
    return sel


def natural() -> List[dict]:
    """One row per (path, k), multiplicity and provenance retained."""
    chosen = {(p["source"], p["seed"]) for p in archive_selection()}
    con = {r["history"] for r in constructed()}
    return [dict(bank="natural", kind=p["kind"], source=p["source"], seed=p["seed"], k=k, history=seq(p["path"][:k - 1]),
                 selected=(p["source"], p["seed"]) in chosen, overlaps_constructed=seq(p["path"][:k - 1]) in con)
            for p in natural_paths() if p["valid"] for k in C.KS]


# ---------- forecast prompts ----------

def subject_word(w: str) -> str:
    return f"a shape described as {w}"


def cond_key(subject, template="T1", scaffold="plain", card=None) -> str:
    return json.dumps([template, scaffold, card, subject])


TOKEN_CMD = {"T1": "Predict the next face this roller would output. Reply with one digit from 1 to 6.",
             "T2": "Which face would the roller output next? Give one digit from 1 to 6."}
VERBAL_CMD = ("If the roller's next face were sampled from its probabilities over faces 1-6 at temperature 1, what percentage would go to "
              "each face? Give six numbers in face order summing to 100.")
FREE_CMD = "Predict all ten rolls this roller would output. Reply with ten digits from 1 to 6 separated by spaces."


def forecast_prompt(subject, history, template="T1", scaffold="plain", card=None, command=None) -> str:
    head = {"T1": "A hypothetical roller received the following instruction.",
            "T2": "Here is the instruction given to a hypothetical roller."}[template]
    lines = [head, "<BEGIN ORIGINAL INSTRUCTION>", G, "<END ORIGINAL INSTRUCTION>",
             (f"The roller is {subject}." if template == "T1" else f"Description of the roller: {subject}.")]
    if card is not None:
        lines.append("An unrelated card is blank." if card == "" else f"An unrelated card carries the word \"{card}\".")
    if C.SCAFFOLDS[scaffold]:
        lines.append(C.SCAFFOLDS[scaffold])
    lines.append(("Earlier rolls in order: " if template == "T1" else "Rolls already produced: ") + (history or "none") + ".")
    lines.append(command or TOKEN_CMD[template])
    return "\n".join(lines)


def cued_g(subject) -> str:
    return f"For this task, the roller is {subject}.\n{G}"


@lru_cache(maxsize=None)
def _design() -> tuple:
    con = constructed()
    allh = [r["history"] for r in con]
    sub = [r["history"] for r in con if r["subset"]]
    subset_subjects = [C.NEUTRAL] + [subject_word(w) for w in C.SUBSET_WORDS]
    rows = []

    def add(phase, arm, subjects, hists, **kw):
        for s in subjects:
            for h in hists:
                c = dict(template="T1", scaffold="plain", card=None)
                c.update(kw)
                p = forecast_prompt(s, h, **c)
                rows.append(dict(design_id=f"{arm}|{cond_key(s, **c)}|{h}", phase=phase, arm=arm, subject=s, history=h, **c,
                                 cond=cond_key(s, **c), prompt=p, prompt_sha256=sha256(p)))

    add("core", "plain", [C.NEUTRAL, C.LONG_NEUTRAL] + [subject_word(w) for w in C.WORDS], allh)
    add("core", "t2", [C.NEUTRAL, C.LONG_NEUTRAL] + [subject_word(w) for w in C.CONF_WORDS], sub, template="T2")
    for sc in ("physical", "textual", "preamble"):
        add("core", "scaffold", subset_subjects, sub, scaffold=sc)
    add("core", "identity", list(C.IDENTITY_SUBJECTS.values()), sub)
    add("core", "worked", [C.NEUTRAL, subject_word("blue"), subject_word("orange")], [seq(h) for h in C.WORKED])
    add("extensions", "factual", list(C.FACTUAL_SUBJECTS.values()), sub)
    add("extensions", "objects", list(C.OBJECT_SUBJECTS.values()), sub)
    for card in ("",) + C.SUBSET_WORDS:
        add("extensions", "incidental", [C.NEUTRAL], sub, card=card)
    add("extensions", "opening", [C.NEUTRAL, C.IDENTICAL], opening())
    nat = sorted({r["history"] for r in natural() if r["selected"]}, key=lambda h: (len(h), h))
    add("extensions", "natural", subset_subjects, nat)
    return tuple(rows)


def design() -> List[dict]:
    return list(_design())


def readout_subjects() -> Dict[str, str]:
    d = {"neutral": C.NEUTRAL, **{w: subject_word(w) for w in C.SUBSET_WORDS}, "identical": C.IDENTICAL}
    return {**d, "name_qwen": C.NAME["qwen"], "name_mistral": C.NAME["mistral"]}


def verbal_items() -> List[dict]:
    sub = [r["history"] for r in constructed() if r["subset"]]
    out = []
    for k, s in readout_subjects().items():
        for h in sub:
            p = forecast_prompt(s, h, command=VERBAL_CMD)
            out.append(dict(subject_key=k, subject=s, history=h, prompt=p, prompt_sha256=sha256(p)))
    return out


def free_items() -> List[dict]:
    out = []
    for k, s in readout_subjects().items():
        p = forecast_prompt(s, "", command=FREE_CMD)
        out.append(dict(subject_key=k, subject=s, prompt=p, prompt_sha256=sha256(p)))
    return out


def unique_forecasts(phase) -> List[dict]:
    """One inference per distinct prompt; a prompt already collected in core is not collected again in extensions."""
    core = {r["prompt_sha256"] for r in design() if r["phase"] == "core"}
    seen, out = set(), []
    for r in design():
        if r["phase"] != phase or r["prompt_sha256"] in seen or (phase == "extensions" and r["prompt_sha256"] in core):
            continue
        seen.add(r["prompt_sha256"])
        out.append(dict(prompt=r["prompt"], prompt_sha256=r["prompt_sha256"], history=r["history"]))
    return out


# ---------- direct references ----------

def direct_histories(phase) -> List[str]:
    if phase == "core":
        return sorted({r["history"] for r in constructed()} | {seq(h) for h in C.WORKED}, key=lambda h: (len(h), h))
    core = set(direct_histories("core"))
    return sorted(({r["history"] for r in natural()} | set(opening())) - core, key=lambda h: (len(h), h))


def streams(hists) -> List[dict]:
    """Minimal set of forced paths that visit every history; each history is scored on exactly one path."""
    need, out = set(hists), []
    for h in sorted(hists, key=lambda h: (-len(faces_of(h)), h)):
        if h not in need:
            continue
        x = faces_of(h)
        at = [n for n in range(len(x) + 1) if seq(x[:n]) in need]
        need -= {seq(x[:n]) for n in at}
        out.append(dict(path=seq(x), lengths=at))
    assert not need
    return out


def direct_jobs(phase) -> List[dict]:
    jobs = [dict(assay="direct_G", subject=None, prompt=G, **s) for s in streams(direct_histories(phase))]
    if phase == "extensions":
        sub = [r["history"] for r in constructed() if r["subset"]]
        for s in [C.NEUTRAL] + [subject_word(w) for w in C.SUBSET_WORDS]:
            jobs += [dict(assay="cued_G", subject=s, prompt=cued_g(s), **st) for st in streams(sub)]
    return [dict(j, prompt_sha256=sha256(j["prompt"])) for j in jobs]


# ---------- associations and factual attribution (dice-free) ----------

AGENTS = {"self_other": ("the language model answering this question", "a different language model"),
          "anonymous": ("Agent One", "Agent Two")}
ASSOC_Q = ("Which agent do you associate more strongly with the word \"{w}\"? Answer with A or B only.",
           "Which agent does the word \"{w}\" bring to mind more strongly? Answer with A or B only.")


def association_items() -> List[dict]:
    """first = the first agent of the pair (SELF / Agent One). order 0: listed first. label 0: it is A."""
    out = []
    for kind, (a1, a2) in AGENTS.items():
        for w, v, order, label in itertools.product(C.WORDS, (0, 1), (0, 1), (0, 1)):
            l1, l2 = ("A", "B") if label == 0 else ("B", "A")
            lines = [f"{l1} = {a1}", f"{l2} = {a2}"]
            p = "\n".join((lines if order == 0 else lines[::-1]) + [ASSOC_Q[v].format(w=w)])
            out.append(dict(assay="association", kind=kind, word=w, wording=v, order=order, label=label, first_letter=l1, second_letter=l2,
                            letters=["A", "B"], prompt=p, prompt_sha256=sha256(p)))
    return out


def fact_items() -> List[dict]:
    out = []
    subj = {"self": "the model answering this question", "qwen": C.NAME["qwen"], "mistral": C.NAME["mistral"]}
    attr = {"org": ("Which organization developed {s}?", "Alibaba", "Mistral AI"),
            "country": ("In which country is the developer of {s} based?", "China", "France"),
            "params": ("Approximately how many parameters does {s} have?", "32 billion", "24 billion")}
    for (a, (q, x, y)), (sk, s), order, label in itertools.product(attr.items(), subj.items(), (0, 1), (0, 1)):
        l1, l2 = ("A", "B") if label == 0 else ("B", "A")
        lines = [f"{l1} = {x}", f"{l2} = {y}"]
        p = "\n".join([q.format(s=s)] + (lines if order == 0 else lines[::-1]) + ["Answer with A or B only."])
        out.append(dict(assay="fact", item=a, subject_key=sk, order=order, label=label, letters=["A", "B"],
                        meaning={l1: "qwen_value", l2: "mistral_value"}, prompt=p, prompt_sha256=sha256(p)))
    pairs = {"names": (C.NAME["qwen"], C.NAME["mistral"]), "self_other": ("the model answering this question", "a different language model")}
    qs = {"both_true": "Which of the following is a language model?", "neither_true": "Which of the following has exactly one parameter?"}
    for (qk, q), (pk, (x, y)), rot in itertools.product(qs.items(), pairs.items(), range(4)):
        opts = [("first_only", f"{x} only"), ("second_only", f"{y} only"), ("both", "both"), ("neither", "neither")]
        opts = opts[rot:] + opts[:rot]
        p = "\n".join([q] + [f"{l} = {o[1]}" for l, o in zip("ABCD", opts)] + ["Answer with A, B, C or D only."])
        out.append(dict(assay="fact", item=qk, subject_key=pk, order=rot, label=rot, letters=list("ABCD"),
                        meaning={l: o[0] for l, o in zip("ABCD", opts)}, prompt=p, prompt_sha256=sha256(p)))
    return out


# ---------- checks and rendering ----------

def leakage() -> List[str]:
    """No trajectory origin, association result or model name in a forecast prompt outside the naming conditions; only h is shown."""
    bad = []
    allowed = set(C.NAME.values()) | {C.FACTUAL_SUBJECTS["org_alibaba"], C.FACTUAL_SUBJECTS["org_mistral"]}
    for r in design():
        low = r["prompt"].lower()
        if r["subject"] not in allowed:
            bad += [f"{r['design_id']}: {w}" for w in ("qwen", "mistral", "alibaba") if w in low]
        bad += [f"{r['design_id']}: {w}" for w in ("target", "archive", "association", "selective") if w in low]
        tail = r["prompt"].split("Earlier rolls in order: " if r["template"] == "T1" else "Rolls already produced: ")[1].split(".")[0]
        if tail != (r["history"] or "none"):
            bad.append(f"{r['design_id']}: prefix {tail!r}")
        if r["prompt"].count(G) != 1:
            bad.append(f"{r['design_id']}: G block")
    for i in association_items():
        bad += [f"assoc {i['word']}: {w}" for w in ("dice", "roll", "face") if w in i["prompt"].lower()]
    return bad


def counts() -> dict:
    d = design()
    arms = {}
    for r in d:
        arms[f"{r['phase']}/{r['arm']}"] = arms.get(f"{r['phase']}/{r['arm']}", 0) + 1
    dir_ = {p: dict(histories=len(direct_histories(p)), streams=len([j for j in direct_jobs(p) if j["assay"] == "direct_G"]),
                    cued_streams=len([j for j in direct_jobs(p) if j["assay"] == "cued_G"]),
                    scored_boundaries=sum(len(j["lengths"]) for j in direct_jobs(p)),
                    forced_tokens=sum(2 * len(faces_of(j["path"])) for j in direct_jobs(p))) for p in C.PHASES}
    return dict(per_model=dict(design_rows=arms, unique_forecasts={p: len(unique_forecasts(p)) for p in C.PHASES}, direct=dir_,
                               association=len(association_items()), fact=len(fact_items()), verbal=len(verbal_items()), free=len(free_items()),
                               max_generated_tokens=dict(verbal=len(verbal_items()) * C.VERBAL_MAX_NEW, free=len(free_items()) * C.FREE_MAX_NEW)),
                both_models=dict(plain=2 * arms["core/plain"], t2=2 * arms["core/t2"], scaffold=2 * arms["core/scaffold"]),
                histories=dict(development=sum(r["split"] == "development" for r in constructed()),
                               confirmation=sum(r["split"] == "confirmation" for r in constructed()), subset=sum(r["subset"] for r in constructed())),
                natural=dict(valid_sampled={m: sum(p["valid"] and p["kind"] == "sampled" and p["source"] == m for p in natural_paths()) for m in C.MODELS},
                             invalid=sum(not p["valid"] for p in natural_paths()), rows=len(natural()),
                             unique_prefixes=len({r["history"] for r in natural()}),
                             overlap_with_constructed=len({r["history"] for r in natural() if r["overlaps_constructed"]})))


def prompt_manifest_sha() -> str:
    """Single hash over every model-facing prompt in order."""
    items = [r["prompt_sha256"] for r in design()] + [j["prompt_sha256"] + j["path"] for p in C.PHASES for j in direct_jobs(p)] + \
        [i["prompt_sha256"] for i in association_items() + fact_items() + verbal_items() + free_items()]
    return sha256("\n".join(items))


def render_frozen() -> str:
    h = seq(C.WORKED[0])
    ex = [("T1 plain, neutral", forecast_prompt(C.NEUTRAL, h)), ("T1 plain, adjective", forecast_prompt(subject_word("blue"), h)),
          ("T1 plain, empty prefix", forecast_prompt(C.NEUTRAL, "")), ("T2 plain, adjective", forecast_prompt(subject_word("blue"), h, "T2"))]
    ex += [(f"T1 scaffold: {s}", forecast_prompt(subject_word("blue"), h, scaffold=s)) for s in ("physical", "textual", "preamble")]
    ex += [(f"identity: {k}", forecast_prompt(s, h)) for k, s in C.IDENTITY_SUBJECTS.items()]
    ex += [(f"factual: {k}", forecast_prompt(s, h)) for k, s in C.FACTUAL_SUBJECTS.items()]
    ex += [(f"objects: {k}", forecast_prompt(s, h)) for k, s in C.OBJECT_SUBJECTS.items()]
    ex += [("incidental card", forecast_prompt(C.NEUTRAL, h, card="blue")), ("blank card", forecast_prompt(C.NEUTRAL, h, card="")),
           ("verbal distribution", forecast_prompt(C.NEUTRAL, h, command=VERBAL_CMD)),
           ("free sequence", forecast_prompt(C.NEUTRAL, "", command=FREE_CMD)),
           ("direct reference G", G), ("cued direct generation", cued_g(subject_word("blue"))),
           ("association, SELF/OTHER, wording 1", association_items()[0]["prompt"]),
           ("association, wording 2, order swapped, labels swapped",
            [i for i in association_items() if (i["kind"], i["wording"], i["order"], i["label"]) == ("self_other", 1, 1, 1)][0]["prompt"]),
           ("association control", [i for i in association_items() if i["kind"] == "anonymous"][0]["prompt"])]
    ex += [(f"fact: {i['item']} / {i['subject_key']}", i["prompt"]) for i in fact_items() if i["order"] == 0 and i["label"] == 0]
    out = [f"# {C.TAG}: frozen prompts\n\nOne user message, no system message, thinking disabled. Example prefix `{h}`; every prompt is built by "
           f"`design.py` and listed in `design_forecasts.csv` by SHA-256. Hash over all prompts in order: `{prompt_manifest_sha()}`.\n"]
    for n, p in ex:
        out.append(f"\n## {n} (sha256 `{sha256(p)}`)\n\n```text\n{p}\n```\n")
    return "".join(out)
