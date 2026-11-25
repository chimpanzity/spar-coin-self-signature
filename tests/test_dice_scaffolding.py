"""Offline tests for Experiment 33 (handoff section 7): prompts, design, scoring arithmetic, parsers, planted fixture, storage, end to end."""

from __future__ import annotations

import hashlib
import json
import math
import types

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from spar_dynamic.dice_crossed_guidance.models import Engine  # noqa: E402
from spar_dynamic.dice_scaffolding import analysis as A  # noqa: E402
from spar_dynamic.dice_scaffolding import config as C  # noqa: E402
from spar_dynamic.dice_scaffolding import design as D  # noqa: E402
from spar_dynamic.dice_scaffolding import gpu as G  # noqa: E402

CK = D.cond_key


# ---------- prompts ----------

def test_prompt_snapshots():
    g = ("Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, "
         "with no other text.")
    assert D.G == g and D.sha256(g) == "edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe"
    assert D.forecast_prompt("a shape described as blue", "5 2 6", scaffold="physical") == (
        "A hypothetical roller received the following instruction.\n<BEGIN ORIGINAL INSTRUCTION>\n" + g + "\n<END ORIGINAL INSTRUCTION>\n"
        "The roller is a shape described as blue.\nImagine the die leaving the roller's hand, striking the ground, and settling. Follow the rolls "
        "in order.\nEarlier rolls in order: 5 2 6.\nPredict the next face this roller would output. Reply with one digit from 1 to 6.")
    assert D.forecast_prompt("a shape", "", "T2") == (
        "Here is the instruction given to a hypothetical roller.\n<BEGIN ORIGINAL INSTRUCTION>\n" + g + "\n<END ORIGINAL INSTRUCTION>\n"
        "Description of the roller: a shape.\nRolls already produced: none.\nWhich face would the roller output next? Give one digit from 1 to 6.")
    assert "The roller is a shape.\nAn unrelated card carries the word \"blue\".\nEarlier" in D.forecast_prompt("a shape", "1", card="blue")
    assert D.cued_g("a shape").endswith("\n" + g)
    i = [x for x in D.association_items() if x["word"] == "restless"][0]
    assert i["prompt"] == ("A = the language model answering this question\nB = a different language model\nWhich agent do you associate more strongly "
                           "with the word \"restless\"? Answer with A or B only.")


def test_switching_adjective_changes_only_the_word_and_target_never_enters():
    a, b = (D.forecast_prompt(D.subject_word(w), "5 2 6") for w in ("blue", "orange"))
    assert a.replace("blue", "orange") == b
    import inspect
    assert "target" not in inspect.signature(D.forecast_prompt).parameters and D.leakage() == []
    for r in D.design():
        assert r["prompt"] == D.forecast_prompt(r["subject"], r["history"], r["template"], r["scaffold"], r["card"])


# ---------- design ----------

def test_bank_split_and_counts():
    fam = D.families()
    assert len({p[:3] for _, _, p in fam}) == 16 and all(len(set(p[:6])) == 6 and len(set(p[6:])) == 4 and len(p) == 10 for _, _, p in fam)
    r1 = min(__import__("itertools").permutations(C.FACES, 3), key=lambda t: hashlib.sha256(f"spar-dice-v1|triple|{t[0]},{t[1]},{t[2]}".encode()).hexdigest())
    assert fam[0][2][:3] == r1
    t = fam[4][2]
    d = lambda kind, f: hashlib.sha256(f"spar-dice-v1|{kind}|{t[0]},{t[1]},{t[2]}|{f}".encode()).hexdigest()
    assert list(t[3:6]) == sorted(set(C.FACES) - set(t[:3]), key=lambda f: d("tail", f)) and list(t[6:]) == sorted(C.FACES, key=lambda f: d("restart", f))[:4]
    con = D.constructed()
    dev, conf = ({r["history"] for r in con if r["split"] == s} for s in ("development", "confirmation"))
    assert len(dev) == 28 and len(conf) == 84 and not dev & conf
    assert {r["family"] for r in con if r["subset"]} == {"c05", "c06", "c07", "c08"}
    c = D.counts()
    assert c["both_models"] == dict(plain=5824, t2=784, scaffold=1176) and c["per_model"]["association"] == 384
    assert len(C.CONF_PAIRS) == len(C.DEV_PAIRS) == 6 and len(set(C.WORDS)) == 24
    assert len(D.opening()) == 37 and len(D.readout_subjects()) == 10


def test_streams_cover_each_history_once():
    for ph in C.PHASES:
        h = [D.seq(D.faces_of(s["path"])[:n]) for s in D.streams(D.direct_histories(ph)) for n in s["lengths"]]
        assert sorted(h) == sorted(D.direct_histories(ph)) and len(h) == len(set(h))
    assert set(D.direct_histories("core")).isdisjoint(D.direct_histories("extensions"))
    need = {d["history"] for d in D.design()}
    assert need <= set(D.direct_histories("core")) | set(D.direct_histories("extensions"))
    assert {d["history"] for d in D.design() if d["phase"] == "core"} <= set(D.direct_histories("core"))


def test_association_design_balanced():
    it = [i for i in D.association_items() if i["kind"] == "self_other" and i["word"] == "blue"]
    assert len(it) == 8 and len({i["prompt"] for i in it}) == 8
    for i in it:
        assert i["prompt"].count("the language model answering this question") == 1 and i["prompt"].count("a different language model") == 1
        assert f"{i['first_letter']} = the language model answering" in i["prompt"]
        assert i["prompt"].startswith(f"{i['first_letter']} = the language model") == (i["order"] == 0)
    for i in D.fact_items():
        assert sorted(i["meaning"]) == i["letters"]


# ---------- scoring arithmetic ----------

def test_js_and_normalise():
    assert A.js([.2, .3, .5, 0, 0, 0], [.2, .3, .5, 0, 0, 0]) == 0
    assert abs(A.js([1, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1]) - 1) < 1e-12
    a, b = [.5, .1, .1, .1, .1, .1], [.1, .5, .1, .1, .1, .1]
    assert abs(A.js(a, b) - A.js(b, a)) < 1e-15
    n = G.normalise([math.log(x) for x in (.1, .2, .05, .05, .05, .05)])
    assert abs(n["mass"] - .5) < 1e-12 and abs(sum(n["q"]) - 1) < 1e-12 and abs(n["q"][1] - .4) < 1e-12


def test_worked_fixture():
    own, oth = [.15, .01, .60, .22, .01, .01], [.50, .01, .30, .17, .01, .01]
    neu, blue = [.33, .01, .33, .31, .01, .01], [.16, .01, .57, .24, .01, .01]
    g_own, g_oth = A.js(neu, own) - A.js(blue, own), A.js(neu, oth) - A.js(blue, oth)
    assert abs(g_own - 0.05847) < 2e-5 and abs(g_oth + 0.07327) < 2e-5 and abs(g_own - g_oth - 0.13173) < 2e-5


# ---------- planted two-target fixture ----------

def _planted(kind):
    """Both targets follow the remaining-face rule but prefer different unused faces. The left word of each pair is self-associated.
    hurt_other_only: neutral and cue are mirror images about a target that is symmetric in two faces, so own JS is identical and only
    the other target's JS grows."""
    rows = [r for r in D.constructed() if r["split"] == "confirmation"]
    norm = lambda v: np.asarray(v, float) / np.sum(v)
    F, GT = {}, {}
    sym = dict(qwen=[.3, .3, .2, .05, .075, .075], mistral=[.2, .05, .3, .3, .075, .075])
    for r in rows:
        h, u = r["history"], A.unused_faces(r["history"])
        base = norm([1.0 if f in u else 0.02 for f in C.FACES])
        pref = dict(qwen=u[0], mistral=u[-1])
        for t in C.MODELS:
            GT[(t, h)] = norm(sym[t]) if kind == "hurt_other_only" else norm(base + 0.6 * np.eye(6)[pref[t] - 1])
        for p in C.MODELS:
            own, oth = GT[(p, h)], GT[(A.OTHER[p], h)]
            neutral, cue = base, dict(own=norm(base + own), generic=norm(base + own + oth), neutral=base).get(kind)
            if kind == "hurt_other_only":
                x, y = (0, 1) if p == "qwen" else (2, 3)                          # other target prefers x
                d = 0.1 * (np.eye(6)[x] - np.eye(6)[y])
                neutral, cue = own + d, own - d
            F[(p, A.NEU, h)] = neutral
            for l, w in C.CONF_PAIRS:
                F[(p, CK(D.subject_word(l)), h)], F[(p, CK(D.subject_word(w)), h)] = cue, neutral
    As = {p: {w: (1.0 if i == 0 else -1.0) for x in C.CONF_PAIRS for i, w in enumerate(x)} for p in C.MODELS}
    return F, GT, As, A.by_family(rows)


@pytest.mark.parametrize("kind,label", [("own", "selective_with_own_improvement"), ("neutral", "no_positive_selectivity"),
                                        ("hurt_other_only", "selective_without_own_improvement")])
def test_planted_fixture_signs(kind, label):
    F, GT, As, fams = _planted(kind)
    s = A.boot_summary(A.primary_cells(F, GT, As, C.CONF_PAIRS, fams), B=200)
    if kind == "hurt_other_only":
        assert all(abs(s[e]["mean"]) < 1e-12 for e in ("qwen_O", "mistral_O", "joint_O")) and s["joint_T"]["mean"] > 0.01   # no own improvement
    for n in ("qwen", "mistral", "joint"):
        assert A.classify(s, n) == label, (n, s)
    # reversing the association reverses the directional test
    rev = {p: {w: -v for w, v in As[p].items()} for p in C.MODELS}
    s2 = A.boot_summary(A.primary_cells(F, GT, rev, C.CONF_PAIRS, fams), B=50)
    assert abs(s2["joint_T"]["mean"] + s["joint_T"]["mean"]) < 1e-12


def test_planted_generic_cue_helps_both_targets():
    F, GT, As, fams = _planted("generic")
    h = next(iter(fams.values()))[0]
    for p in C.MODELS:
        c = CK(D.subject_word("blue"))
        assert A.gain(F, GT, p, p, c, h) > 0 and A.gain(F, GT, p, A.OTHER[p], c, h) > 0
    s = A.boot_summary(A.primary_cells(F, GT, As, C.CONF_PAIRS, fams), B=50)
    own = A.boot_summary(A.primary_cells(*_planted("own")[:2], As, C.CONF_PAIRS, fams), B=50)
    assert abs(s["joint_T"]["mean"]) < 0.1 * own["joint_T"]["mean"] and s["joint_O"]["mean"] > 0


def test_association_tie_contributes_zero_and_averages_gains():
    F, GT, As, fams = _planted("own")
    As["qwen"]["blue"] = As["qwen"]["orange"] = 0.0
    c = A.primary_cells(F, GT, As, C.CONF_PAIRS, fams)["qwen"]
    assert (c["T"][0] == 0).all()
    h = list(fams.values())[0]
    gl = np.mean([A.gain(F, GT, "qwen", "qwen", CK(D.subject_word("blue")), x) for x in h])
    assert abs(c["O"][0, 0] - gl / 2) < 1e-12


# ---------- parsers ----------

def test_parsers():
    assert G.parse_verbal("10 20 30 20 10 10")[0] == [.1, .2, .3, .2, .1, .1]
    assert G.parse_verbal("10%, 20%, 30%, 20%, 10%, 10%")[0] is not None
    assert G.parse_verbal("16.67, 16.67, 16.67, 16.67, 16.67, 16.67")[0] is not None
    assert G.parse_verbal("17 17 17 17 17 16")[0] is not None and G.parse_verbal("17 17 17 17 17 17")[0] is None        # 101 accepted, 102 not
    assert G.parse_verbal("17 17 17 17 17 14")[0] is not None and G.parse_verbal("17 17 17 17 17 13")[0] is None        # 99 accepted, 98 not
    for bad in ("", "1: 10, 2: 20, 3: 30, 4: 20, 5: 10, 6: 10", "10 20 30 20 10", "-10 30 30 30 10 10", "nan 20 30 20 10 20", "The answer is 4."):
        assert G.parse_verbal(bad)[0] is None, bad
    assert G.parse_free("5 2 6 3 1 4 6 2 5 3") == (5, 2, 6, 3, 1, 4, 6, 2, 5, 3)
    for bad in ("5 2 6 3 1 4 6 2 5", "5 2 6 3 1 4 6 2 5 7", "Rolls: 5 2 6 3 1 4 6 2 5 3", "5263146253"):
        assert G.parse_free(bad) is None


# ---------- storage ----------

def test_store_resume_and_conflicts(tmp_path):
    p = tmp_path / "x.jsonl"
    s = G.Store(p)
    s.add(dict(row_id="a", l=[0.0]))
    with pytest.raises(SystemExit):
        s.add(dict(row_id="a", l=[1.0]))
    with pytest.raises(SystemExit):
        s.add(dict(row_id="b", l=[float("nan")]))
    with open(p, "a") as f:
        f.write('{"row_id": "torn"')
    assert list(G.Store(p).rows) == ["a"] and p.read_text().endswith("\n")


# ---------- end to end on a tiny engine ----------

class Tiny(Engine):
    device = "cpu"

    def __init__(self, key):
        self.key, self.model_id, self.commit = key, C.MODEL[key]["model_id"], C.MODEL[key]["revision"]
        self.face_ids, self.eos = dict(C.MODEL[key]["face_ids"]), {2}
        self.inv = {v: k for k, v in self.face_ids.items()}
        self.letter = {x: 900 + i for i, x in enumerate("ABCD")}
        self.model = self._model

    def _model(self, input_ids, past_key_values=None, use_cache=True):
        ids = list(past_key_values or []) + input_ids[0].tolist()
        n = input_ids.shape[1]
        rows = []
        for k in range(len(ids) - n, len(ids)) if n < 40 else [len(ids) - 1]:
            z = torch.randn(1100, generator=torch.Generator().manual_seed(int.from_bytes(hashlib.sha256(repr(ids[:k + 1]).encode()).digest()[:7], "little")))
            if 999 in ids[:k + 1]:
                gen = ids[ids.index(999) + 1:k + 1]
                tail = gen[-1] if gen else None
                if tail in self.inv and len(gen) < 19:
                    z[C.SEPARATOR_ID[self.key]] += 30
                elif tail in self.inv:
                    z[2] += 30
                else:
                    for i in self.face_ids.values():
                        z[i] += 12
            rows.append(z)
        if len(rows) < n:
            rows = [rows[0]] * n
        return types.SimpleNamespace(logits=torch.stack(rows).unsqueeze(0), past_key_values=ids)

    def prompt_ids(self, prompt):
        return [100 + int.from_bytes(hashlib.sha256(prompt.encode()).digest()[i:i + 1], "little") for i in range(6)] + [999]

    def hist_ids(self, text):
        if text in self.letter:
            return [self.letter[text]]
        return [C.SEPARATOR_ID[self.key] if ch == " " else self.face_ids[int(ch)] for ch in text]

    def decode(self, ids):
        return "".join(" " if i == C.SEPARATOR_ID[self.key] else str(self.inv[i]) if i in self.inv else next((a for a, b in self.letter.items() if b == i), "x") for i in ids)

    def rendered_text(self, p):
        return p

    def env_common(self):
        return dict(max_memory_allocated_gb=0.0)


def test_end_to_end_tiny(tmp_path, monkeypatch):
    from spar_dynamic.dice_31_32 import gpu as G31
    from spar_dynamic.dice_scaffolding import __main__ as M

    def fake_preflight(eng, raw, phase):
        env = dict(model_commit=eng.commit, archival_check=dict(ok=True, per_instruction={}), on_path=dict(ok=True), instrumentation={},
                   vocab_scan=dict(variant_face_tokens=[]), prompt_manifest_sha256=D.prompt_manifest_sha(), letter_variant_ids=[950])
        json.dump(env, open(raw / f"env_{phase}.json", "w"))
        return env
    monkeypatch.setattr(G, "preflight", fake_preflight)
    monkeypatch.setattr(G.os, "fsync", lambda fd: None)
    monkeypatch.setattr(D, "association_items", __import__("functools").lru_cache(None)(D.association_items))
    for m in C.MODELS:
        e = Tiny(m)
        # the canonical history ends in exactly one separator and the face boundary follows it
        ids = G.direct_ids(e, "5 2 6")
        assert ids == [x for f in (5, 2, 6) for x in (e.face_ids[f], C.SEPARATOR_ID[m])] and G.direct_ids(e, "") == []
        ds = G31.forced_dists(e, D.G, ids, "incremental")
        assert ds[5]["argmax_token_id"] == C.SEPARATOR_ID[m] and ds[6]["argmax_token_id"] in e.inv           # separator then face
        G.collect(e, "core", tmp_path)
        seal = json.load(open(tmp_path / "raw" / m / "association_seal.json"))
        assert seal["dice_rows_at_seal"] == 0
        G.collect(e, "extensions", tmp_path)
    before = (tmp_path / "raw" / "qwen" / "forecasts_core.jsonl").read_bytes()
    assert len(G.Store(tmp_path / "raw" / "qwen" / "forecasts_core.jsonl").rows) == 4094
    G.run_forecasts(Tiny("qwen"), G.Store(tmp_path / "raw" / "qwen" / "forecasts_core.jsonl"), "core")        # resume adds nothing
    assert (tmp_path / "raw" / "qwen" / "forecasts_core.jsonl").read_bytes() == before
    r = M.run_checks("all", tmp_path, frozen=False)
    assert r["overall"] == "PASS", [k for k, v in r["checks"].items() if v["status"] != "PASS"]
    M.main(["analyse", "--phase", "all", "--root", str(tmp_path)])
    s = json.load(open(tmp_path / "results" / "summary.json"))
    assert s["core"]["primary"]["joint_T"]["n_families"] == 12 and (tmp_path / "figures" / "fig33_primary.png").exists()
    with open(tmp_path / "raw" / "qwen" / "forecasts_core.jsonl", "a") as f:
        f.write(json.dumps(dict(row_id="extra", l=[0.0] * 6, q=[1 / 6] * 6, mass=1, digit_ids=[], timestamp="9", prompt_sha256="z")) + "\n")
    assert M.run_checks("core", tmp_path, frozen=False)["overall"] == "FAIL"


# ---------- real tokenizers (local cache only) ----------

def test_real_tokenizers_letters_digits_boundary():
    try:
        from huggingface_hub import hf_hub_download
        from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
        from transformers import AutoTokenizer
        qt = AutoTokenizer.from_pretrained(C.MODEL["qwen"]["model_id"], revision=C.MODEL["qwen"]["revision"], local_files_only=True)
        tp = hf_hub_download(C.MODEL["mistral"]["model_id"], "tekken.json", revision=C.MODEL["mistral"]["revision"], local_files_only=True)
    except Exception as e:
        pytest.skip(f"tokenizer files not cached: {e}")
    mt = MistralTokenizer.from_file(tp).instruct_tokenizer.tokenizer
    for key, e in (("qwen", lambda s: qt(s, add_special_tokens=False).input_ids), ("mistral", lambda s: mt.encode(s, bos=False, eos=False))):
        assert [e(str(f)) for f in C.FACES] == [[C.MODEL[key]["face_ids"][f]] for f in C.FACES]
        assert all(len(e(x)) == 1 for x in "ABCD") and len({e(x)[0] for x in "ABCD"}) == 4
        for _, _, p in D.families():
            assert e(D.seq(p))[1::2] == [C.SEPARATOR_ID[key]] * 9
