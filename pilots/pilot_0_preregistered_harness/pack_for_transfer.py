"""Zip the project (code, docs, raw data, derived data, results) for transfer to another machine.

    python pack_for_transfer.py                 # writes spar-coin-pilot-transfer-<timestamp>.zip next to this file
    python pack_for_transfer.py --name my.zip   # choose the archive name

Excluded: .venv, .git, caches, *.pyc, *.egg-info, fake_* runs, other .zip files, and .env (the API key
must never travel with the data). The archive is checked afterwards for a .env entry and for a
key-shaped string, and the script fails loudly if either is found.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import zipfile
from pathlib import Path

SKIP_DIRS = {".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".idea", ".vscode", "build", "dist"}
KEY_PATTERN = re.compile(rb"sk-or-v1-[0-9a-f]{20,}")


def wanted(path: Path) -> bool:
    parts = path.parts
    if any(p in SKIP_DIRS for p in parts):
        return False
    if any(p.endswith(".egg-info") for p in parts):
        return False
    if any(p.startswith("fake_") for p in parts[:-1]):  # fake_* run directories, not fake_client.py
        return False
    if path.name == ".env" or path.suffix in {".pyc", ".zip"}:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default=None, help="archive file name (default: spar-coin-pilot-transfer-<timestamp>.zip)")
    args = ap.parse_args(argv)
    root = Path(__file__).resolve().parent
    name = args.name or f"spar-coin-pilot-transfer-{dt.datetime.now():%Y%m%d_%H%M%S}.zip"
    out = root / name
    files = sorted(p for p in root.rglob("*") if p.is_file() and wanted(p.relative_to(root)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, p.relative_to(root).as_posix())
    # Safety check: no .env, no key-shaped string anywhere in the archive.
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        bad = [n for n in names if n == ".env" or n.endswith("/.env")]
        leaked = [n for n in names if KEY_PATTERN.search(zf.read(n))]
    if bad or leaked:
        out.unlink()
        print(f"refused: archive would contain {bad or leaked}; not written", file=sys.stderr)
        return 1
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(names)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
