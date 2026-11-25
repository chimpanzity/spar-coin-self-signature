"""Experiment 36: python -m spar_dynamic.hidden_policy {freeze,validate,analyse} (repo root, PYTHONPATH=src)."""

from __future__ import annotations

import json
import sys

from spar_dynamic.dice_31_32 import stimuli as S31
from spar_dynamic.dice_31_32.gpu import canonical_sha
from spar_dynamic.dice_scaffolding import config as C33
from spar_dynamic.hidden_policy import design as D


def preconditions():
    S31.ground_truth()
    assert not D.leakage(), D.leakage()[:3]
    b = D.bank()
    assert len(b) == 480 and sum(x["eligible"] for x in b) == 432 and len(D.folds()) == 18 and len(D.pilot_prefixes()) == 6
    frozen33 = (C33.EXP / "prompts_frozen.md").read_text(encoding="utf-8")
    assert D.G in frozen33


def inputs():
    fs = [C33.EXP / "raw" / m / f"{n}.jsonl" for m in D.MODELS for n in ("forecasts_core", "forecasts_extensions", "direct_core", "direct_extensions")]
    return {p.relative_to(D.EXP.parent).as_posix(): canonical_sha(p) for p in [*fs, C33.EXP / "prompts_frozen.md"]}


def freeze():
    preconditions()
    for n, t in D.built().items():
        p = D.EXP / n
        if p.exists() and p.read_text(encoding="utf-8") != t:
            raise SystemExit(f"{n} already frozen and different")
        p.write_text(t, encoding="utf-8", newline="\n")
    rec = dict(archived_inputs=inputs(), frozen={n: canonical_sha(D.EXP / n) for n in ("PROTOCOL.md", *D.built())},
               analysis_code={n: canonical_sha(D.EXP.parents[1] / "src/spar_dynamic/hidden_policy" / n) for n in ("analysis.py", "design.py", "gpu.py")})
    (D.EXP / "inputs_sha256.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(D.manifest())


def validate():
    preconditions()
    rec = json.loads((D.EXP / "inputs_sha256.json").read_text(encoding="utf-8"))
    assert rec["archived_inputs"] == inputs(), "archived inputs changed"
    assert rec["frozen"] == {n: canonical_sha(D.EXP / n) for n in rec["frozen"]}, "frozen file changed"
    print("validate ok")


if __name__ == "__main__":
    ph = sys.argv[1]
    if ph == "analyse":
        from spar_dynamic.hidden_policy.analysis import main
        main()
    else:
        {"freeze": freeze, "validate": validate}[ph]()
