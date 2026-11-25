"""Experiment 35: python -m spar_dynamic.roll7_scaffolding {freeze,validate,analyse} (repo root, PYTHONPATH=src)."""

from __future__ import annotations

import json
import sys

from spar_dynamic.dice_31_32 import config as C32
from spar_dynamic.dice_31_32 import stimuli as S32
from spar_dynamic.dice_31_32.gpu import canonical_sha
from spar_dynamic.roll7_scaffolding import design as D


def built():
    return {"prompts_frozen.md": D.render_frozen(), "design_cells.csv": D.design_csv(), "manifest.json": D.manifest()}


def inputs():
    fs = [C32.EXP28_MAIN / m / "raw_attempts.jsonl" for m in D.MODELS] + [C32.EXP32 / "raw" / m / "cells.jsonl" for m in D.MODELS] + \
        [C32.EXP32 / "prompts_frozen.md", C32.EXP32 / "results" / "cells_12.csv"]
    return {p.relative_to(D.EXP.parent).as_posix(): canonical_sha(p) for p in fs}


def preconditions():
    S32.ground_truth()
    assert not D.leakage(), D.leakage()
    cs = D.cells()
    assert len(cs) == 36 and len({c["cell_id"] for c in cs}) == 36 and len({c["prompt_sha256"] for c in cs}) == 12
    frozen32 = (C32.EXP32 / "prompts_frozen.md").read_text(encoding="utf-8")
    for s, _ in D.SOURCES:
        x = C32.REFERENCES[(s, "G")]
        assert D.prompt(s, "B") == S32.prompt32("B", x[:5]) and S32.sha256(D.prompt(s, "B")) == D.B_SHA[s]
        assert f"### {s}-G-B (sha256 `{D.B_SHA[s]}`)" in frozen32


def freeze():
    preconditions()
    for n, t in built().items():
        p = D.EXP / n
        if p.exists() and p.read_text(encoding="utf-8") != t:
            raise SystemExit(f"{n} already frozen and different")
        p.write_text(t, encoding="utf-8", newline="\n")
    rec = dict(archived_inputs=inputs(), frozen={n: canonical_sha(D.EXP / n) for n in ("PROTOCOL.md", *built())})
    (D.EXP / "inputs_sha256.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(rec, indent=1))


def validate():
    preconditions()
    rec = json.loads((D.EXP / "inputs_sha256.json").read_text(encoding="utf-8"))
    assert rec["archived_inputs"] == inputs(), "archived inputs changed"
    assert rec["frozen"] == {n: canonical_sha(D.EXP / n) for n in rec["frozen"]}, "frozen file changed"
    for n, t in built().items():
        assert (D.EXP / n).read_bytes().replace(b"\r\n", b"\n").decode("utf-8") == t, n
    print("validate ok")


if __name__ == "__main__":
    ph = sys.argv[1]
    if ph == "analyse":
        from spar_dynamic.roll7_scaffolding.analysis import main
        main()
    else:
        {"freeze": freeze, "validate": validate}[ph]()
