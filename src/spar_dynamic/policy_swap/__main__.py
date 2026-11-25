"""Experiment 37: python -m spar_dynamic.policy_swap {freeze,probes,validate,analyse} (repo root, PYTHONPATH=src)."""

from __future__ import annotations

import json
import sys

from spar_dynamic.dice_31_32.gpu import canonical_sha
from spar_dynamic.hidden_policy.__main__ import preconditions as pre36
from spar_dynamic.policy_swap import design as D


def preconditions():
    pre36()
    s = {k: {r["family"] for r in D.prefixes(k)} for k in ("train", "dev", "holdout")}
    assert not (s["train"] & s["holdout"] or s["train"] & s["dev"] or s["dev"] & s["holdout"])
    assert [len(s[k]) for k in ("train", "dev", "holdout")] == [10, 2, 8]
    assert max(D.BLOCKS) < 47


def freeze():
    preconditions()
    for n, t in D.built().items():
        p = D.EXP / n
        if p.exists() and p.read_text(encoding="utf-8") != t:
            raise SystemExit(f"{n} already frozen and different")
        p.write_text(t, encoding="utf-8", newline="\n")
    src = D.EXP.parents[1] / "src/spar_dynamic/policy_swap"
    rec = dict(frozen={n: canonical_sha(D.EXP / n) for n in ("PROTOCOL.md", *D.built())}, code={p.name: canonical_sha(p) for p in sorted(src.glob("*.py"))})
    (D.EXP / "inputs_sha256.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8", newline="\n")


def validate(probes=False):
    preconditions()
    rec = json.loads((D.EXP / "inputs_sha256.json").read_text(encoding="utf-8"))
    assert rec["frozen"] == {n: canonical_sha(D.EXP / n) for n in rec["frozen"]}, "frozen file changed"
    if probes:
        assert (D.EXP / "probes_manifest.json").exists(), "probes must be frozen before held-out evaluation"
    print("validate ok")


if __name__ == "__main__":
    ph = sys.argv[1]
    if ph == "analyse":
        from spar_dynamic.policy_swap.analysis import main
        main()
    elif ph == "probes":
        from spar_dynamic.policy_swap.probes import freeze as fp
        print(json.dumps(fp(), indent=1))
    else:
        {"freeze": freeze, "validate": validate}[ph]()
