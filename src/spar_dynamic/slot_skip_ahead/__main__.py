"""Experiment 38: python -m spar_dynamic.slot_skip_ahead {freeze,validate,dryrun,analyse} (repo root, PYTHONPATH=src)."""

from __future__ import annotations

import json
import sys

from spar_dynamic.dice_31_32 import config as C32
from spar_dynamic.dice_31_32 import stimuli as S32
from spar_dynamic.dice_31_32.gpu import canonical_sha
from spar_dynamic.slot_skip_ahead import design as D


def built():
    return {"prompts_frozen.md": D.render_frozen(), "design_prompts.csv": D.prompts_csv(), "design_sources.csv": D.sources_csv(),
            "manifest.json": D.manifest()}


def inputs():
    fs = [C32.EXP28_MAIN / m / "raw_attempts.jsonl" for m in D.MODELS] + [D.EXP27_CORPUS / m / "sampled.jsonl" for m in D.MODELS] + \
        [C32.EXP31 / "raw" / m / "streams.jsonl" for m in D.MODELS] + [C32.EXP32 / "raw" / m / "cells.jsonl" for m in D.MODELS] + \
        [D.EXP35 / "raw" / m / "cells_standard.jsonl" for m in D.MODELS] + [C32.EXP32 / "prompts_frozen.md", D.EXP35 / "prompts_frozen.md"]
    return {p.relative_to(D.EXP.parent).as_posix(): canonical_sha(p) for p in fs}


def preconditions():
    S32.ground_truth()
    assert not D.leakage(), D.leakage()
    it = D.prompt_items()
    assert len(it) == 548 and len({r["prompt_id"] for r in it}) == 548 and len({r["prompt_sha256"] for r in it}) == 548
    assert len(D.policy_items()) == 170 and len(D.sources()) == 66
    f32 = (C32.EXP32 / "prompts_frozen.md").read_text(encoding="utf-8")
    f35 = (D.EXP35 / "prompts_frozen.md").read_text(encoding="utf-8")
    shas = {r["prompt_sha256"] for r in it}
    for a in D.anchors():
        assert S32.sha256(a["prompt"]) == a["sha"] and a["sha"] in shas, a["anchor"]
        assert f"(sha256 `{a['sha']}`)" in (f35 if a["anchor"].startswith("exp35") else f32), a["anchor"]


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


def dryrun():
    """End to end on the tiny scripted engines (no GPU): collection functions, then the analysis on their output, in a temp dir."""
    import tempfile
    from pathlib import Path
    from tests.test_slot_skip_ahead import tiny_run
    with tempfile.TemporaryDirectory() as d:
        tiny_run(Path(d))
    print("dryrun ok")


if __name__ == "__main__":
    ph = sys.argv[1]
    if ph == "analyse":
        from spar_dynamic.slot_skip_ahead.analysis import main
        main()
    else:
        {"freeze": freeze, "validate": validate, "dryrun": dryrun}[ph]()
