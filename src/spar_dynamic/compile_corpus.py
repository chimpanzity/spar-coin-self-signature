"""Compile the canonical SPAR Stimulus Corpus (pilot 5).

Produces a tidy CSV-based corpus from the 180 valid trajectories on disk:

  corpus/
    trajectories.csv         # 180 rows, canonical stimulus bank
    flips.csv                # 18000 rows, long-format trial-level
    metrics.csv              # 540 rows, phenotype at prefix 20/50/100
    manifest.json            # split seed, cell counts, run pointers
    README.md                # study overview + how to use
    data_dictionary.md       # field-by-field definitions
    stimulus_corpus.xlsx     # human-browsable Excel view (generated from CSVs)

The dev/holdout split is a stratified random 10/10 within each of the 9
(model, method) cells, using CORPUS_SPLIT_SEED (frozen in config.py).
Split assignment is independent of phenotype results.

Provenance chain:
  raw_attempts.jsonl        (every API attempt, immutable)
  trajectories/*.json       (per-trajectory result + metadata, immutable)
  corpus/*.csv              (this script's output; regenerable from the above)
"""

import argparse, csv, glob, json, os, random
from collections import defaultdict, Counter
from typing import Any, Dict, List, Optional, Tuple

from . import config as C
from .analyze import sequence_features
from .state import RunPaths, read_json


def _load_raw_attempts_by_trajectory(raw_path: str) -> Dict[str, List[Dict]]:
    by_traj: Dict[str, List[Dict]] = defaultdict(list)
    if not os.path.exists(raw_path):
        return by_traj
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            tid = r.get("trajectory_id")
            if tid:
                by_traj[tid].append(r)
    return by_traj


def _summarize_trajectory_provenance(attempts: List[Dict]) -> Dict[str, Any]:
    """From the raw attempts for one trajectory, extract:
      returned_model_id, provider (from any successful attempt, else first),
      total_api_calls (all recorded attempts),
      first_timestamp (earliest recorded call)."""
    if not attempts:
        return {"returned_model_id": "", "provider": "",
                "total_api_calls": 0, "first_timestamp": ""}
    ok = [a for a in attempts if a.get("valid")]
    seed = ok[0] if ok else attempts[0]
    return {
        "returned_model_id": seed.get("returned_model_id", ""),
        "provider": seed.get("provider", ""),
        "total_api_calls": len(attempts),
        "first_timestamp": min((a.get("timestamp", "") for a in attempts if a.get("timestamp")),
                               default=""),
    }


def _stratified_split(trajectories_in_cell: List[Dict],
                      dev_n: int, hold_n: int, seed: int) -> Tuple[List[Dict], List[Dict]]:
    """Random 10/10 stratified split within one cell. Deterministic given seed."""
    tids = sorted(t["trajectory_id"] for t in trajectories_in_cell)  # sort for determinism
    rng = random.Random(seed)
    rng.shuffle(tids)
    dev_tids = set(tids[:dev_n])
    hold_tids = set(tids[dev_n:dev_n + hold_n])
    by_tid = {t["trajectory_id"]: t for t in trajectories_in_cell}
    dev = sorted([by_tid[t] for t in dev_tids], key=lambda x: x["trajectory_id"])
    hold = sorted([by_tid[t] for t in hold_tids], key=lambda x: x["trajectory_id"])
    return dev, hold


def _cell_seed(base_seed: int, model: str, method: str) -> int:
    """Deterministic per-cell seed derived from the base — same base always
    yields the same 9 cell seeds, and cells are independent of each other."""
    # simple stable hash: sum of ordinals of the cell key + base
    return base_seed + sum(ord(c) for c in f"{model}/{method}")


def load_valid_trajectories(traj_dir: str) -> List[Dict]:
    valids = []
    for fn in sorted(os.listdir(traj_dir)):
        if not (fn.startswith("trajectory-") and fn.endswith(".json")):
            continue
        r = read_json(os.path.join(traj_dir, fn))
        if r and r.get("status") == "ok" \
                and len(r.get("parsed_sequence", "")) == C.CORPUS_SEQUENCE_LENGTH:
            valids.append(r)
    return valids


def build_corpus(run_id: str, data_root: str, out_dir: Optional[str]) -> Dict[str, Any]:
    paths = RunPaths(data_root, run_id); paths.ensure()
    traj_dir = os.path.join(paths.root, "trajectories")
    raw_path = os.path.join(paths.root, "raw_attempts.jsonl")
    corpus_dir = out_dir or os.path.join(paths.results, "corpus")
    os.makedirs(corpus_dir, exist_ok=True)

    print(f"[compile] loading trajectories from {traj_dir}", flush=True)
    all_valid = load_valid_trajectories(traj_dir)
    print(f"[compile] valid trajectories on disk: {len(all_valid)}", flush=True)

    print(f"[compile] loading raw_attempts for provenance", flush=True)
    raw_by_traj = _load_raw_attempts_by_trajectory(raw_path)

    # Group by (model, method) cell
    by_cell: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for t in all_valid:
        by_cell[(t["model_label"], t["method"])].append(t)

    # Verify every cell has at least dev+hold trajectories
    need = C.CORPUS_DEV_PER_CELL + C.CORPUS_HOLDOUT_PER_CELL
    for m in C.CORPUS_MODEL_LABELS:
        for meth in C.CORPUS_GENERATION_METHODS:
            n = len(by_cell[(m, meth)])
            if n < need:
                raise RuntimeError(f"cell {m}/{meth} has only {n} valid trajectories, need {need}")

    # Assign splits per cell with a derived-but-deterministic per-cell seed
    trajectories_rows: List[Dict] = []
    per_cell_counts: Dict[str, Dict[str, int]] = {}
    for m in C.CORPUS_MODEL_LABELS:
        for meth in C.CORPUS_GENERATION_METHODS:
            cell_seed = _cell_seed(C.CORPUS_SPLIT_SEED, m, meth)
            dev, hold = _stratified_split(by_cell[(m, meth)],
                                          C.CORPUS_DEV_PER_CELL,
                                          C.CORPUS_HOLDOUT_PER_CELL,
                                          seed=cell_seed)
            per_cell_counts[f"{m}/{meth}"] = {"dev": len(dev), "holdout": len(hold),
                                              "cell_seed": cell_seed}
            for split_name, group in (("development", dev), ("holdout", hold)):
                for i, t in enumerate(group, start=1):
                    prov = _summarize_trajectory_provenance(raw_by_traj.get(t["trajectory_id"], []))
                    trajectories_rows.append({
                        "trajectory_id": t["trajectory_id"],
                        "model": t["model_label"],
                        "method": t["method"],
                        "split": split_name,
                        "replicate": i,
                        "sequence": t["parsed_sequence"],
                        "n_flips": len(t["parsed_sequence"]),
                        "requested_model_id": t["requested_model_id"],
                        "returned_model_id": prov["returned_model_id"],
                        "provider": prov["provider"],
                        "run_id": t["run_id"],
                        "first_call_utc": prov["first_timestamp"],
                        "finished_utc": t["finished_utc"],
                        "temperature": C.TEMPERATURE,
                        "prompt_version": "pilot5_v1",
                        "total_api_calls_recorded": prov["total_api_calls"],
                        "trajectory_cost_usd": t["total_cost_usd"],
                        "original_replicate_index": t["replicate_index"],
                    })

    # trajectories.csv
    traj_csv = os.path.join(corpus_dir, "trajectories.csv")
    traj_fields = ["trajectory_id", "model", "method", "split", "replicate",
                   "sequence", "n_flips",
                   "requested_model_id", "returned_model_id", "provider",
                   "run_id", "first_call_utc", "finished_utc",
                   "temperature", "prompt_version",
                   "total_api_calls_recorded", "trajectory_cost_usd",
                   "original_replicate_index"]
    with open(traj_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=traj_fields)
        w.writeheader()
        for row in sorted(trajectories_rows,
                          key=lambda r: (r["model"], r["method"], r["split"], r["replicate"])):
            w.writerow(row)
    print(f"[compile] wrote {traj_csv} ({len(trajectories_rows)} rows)", flush=True)

    # flips.csv — long format: one row per flip
    flips_csv = os.path.join(corpus_dir, "flips.csv")
    flips_fields = ["trajectory_id", "model", "method", "split", "replicate",
                    "trial", "choice", "history_before"]
    n_flip_rows = 0
    with open(flips_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=flips_fields)
        w.writeheader()
        for row in sorted(trajectories_rows,
                          key=lambda r: (r["model"], r["method"], r["split"], r["replicate"])):
            seq = row["sequence"]
            for i, ch in enumerate(seq, start=1):
                w.writerow({
                    "trajectory_id": row["trajectory_id"],
                    "model": row["model"],
                    "method": row["method"],
                    "split": row["split"],
                    "replicate": row["replicate"],
                    "trial": i,
                    "choice": ch,
                    "history_before": seq[:i-1] if row["method"] == "history_conditioned" else "",
                })
                n_flip_rows += 1
    print(f"[compile] wrote {flips_csv} ({n_flip_rows} rows)", flush=True)

    # metrics.csv — derived phenotype at prefix 20/50/100
    metrics_csv = os.path.join(corpus_dir, "metrics.csv")
    metrics_fields = ["trajectory_id", "model", "method", "split", "replicate",
                      "prefix_n", "p_H", "switch_rate", "runs_z", "longest_run",
                      "HH", "HT", "TH", "TT", "entropy_binary"]
    n_metric_rows = 0
    with open(metrics_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=metrics_fields)
        w.writeheader()
        for row in sorted(trajectories_rows,
                          key=lambda r: (r["model"], r["method"], r["split"], r["replicate"])):
            seq = row["sequence"]
            for prefix in C.CORPUS_PREFIX_LENGTHS:
                sub = seq[:prefix]
                feat = sequence_features(sub)
                w.writerow({
                    "trajectory_id": row["trajectory_id"],
                    "model": row["model"],
                    "method": row["method"],
                    "split": row["split"],
                    "replicate": row["replicate"],
                    "prefix_n": prefix,
                    "p_H": round(feat["prop_H"], 6),
                    "switch_rate": round(feat["switch_rate"], 6),
                    "runs_z": (None if feat["runs_Z"] != feat["runs_Z"]
                               else round(feat["runs_Z"], 6)),
                    "longest_run": int(feat["longest_run"]),
                    "HH": round(feat["HH"], 6),
                    "HT": round(feat["HT"], 6),
                    "TH": round(feat["TH"], 6),
                    "TT": round(feat["TT"], 6),
                    "entropy_binary": round(feat["entropy_binary"], 6),
                })
                n_metric_rows += 1
    print(f"[compile] wrote {metrics_csv} ({n_metric_rows} rows)", flush=True)

    # manifest.json
    manifest = {
        "corpus_name": "SPAR Stimulus Corpus — Pilot 5",
        "experiment_tag": C.STIMULUS_CORPUS_TAG,
        "source_run_id": run_id,
        "source_run_root": paths.root,
        "sequence_length": C.CORPUS_SEQUENCE_LENGTH,
        "models": list(C.CORPUS_MODEL_LABELS),
        "model_ids": {m.label: m.slug for m in C.CORPUS_MODELS},
        "methods": list(C.CORPUS_GENERATION_METHODS),
        "trajectories_per_cell": C.CORPUS_TRAJECTORIES_PER_CELL,
        "dev_per_cell": C.CORPUS_DEV_PER_CELL,
        "holdout_per_cell": C.CORPUS_HOLDOUT_PER_CELL,
        "split_seed_base": C.CORPUS_SPLIT_SEED,
        "per_cell_split_seeds": {k: v["cell_seed"] for k, v in per_cell_counts.items()},
        "per_cell_counts": per_cell_counts,
        "temperature": C.TEMPERATURE,
        "prompt_version": "pilot5_v1",
        "prompts": {
            "batch": C.CORPUS_BATCH_PROMPT,
            "history_conditioned_trial1": C.CORPUS_HISTORY_TRIAL1_PROMPT,
            "history_conditioned_general_template": (
                "Previous flips (oldest → most recent):\n<HISTORY>\n\n"
                "Simulate the next flip of a fair coin. Return exactly one character: H or T."),
            "independent_calls": C.CORPUS_INDEPENDENT_CALLS_PROMPT,
        },
    }
    with open(os.path.join(corpus_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[compile] wrote manifest.json", flush=True)

    # README.md and data_dictionary.md
    _write_readme(corpus_dir, manifest, len(trajectories_rows), n_flip_rows, n_metric_rows)
    _write_dictionary(corpus_dir)
    print(f"[compile] wrote README.md and data_dictionary.md", flush=True)

    # stimulus_corpus.xlsx (best-effort; skip if openpyxl unavailable)
    try:
        _write_excel(corpus_dir, manifest)
        print(f"[compile] wrote stimulus_corpus.xlsx", flush=True)
    except ImportError:
        print(f"[compile] openpyxl not available; skipping xlsx", flush=True)

    return {"trajectories": len(trajectories_rows),
            "flips": n_flip_rows, "metrics": n_metric_rows,
            "corpus_dir": corpus_dir}


def _write_readme(corpus_dir: str, manifest: Dict, n_traj: int, n_flip: int, n_metric: int):
    lines = [
        "# SPAR Stimulus Corpus — Pilot 5",
        "",
        "Reusable stimulus bank of 180 fair-coin trajectories produced by three models",
        "under three call architectures.",
        "",
        "## Contents",
        "",
        f"- `trajectories.csv` — {n_traj} rows, canonical stimulus bank (one row per 100-flip trajectory)",
        f"- `flips.csv`        — {n_flip} rows, long-format trial-level view (one row per flip)",
        f"- `metrics.csv`      — {n_metric} rows, derived phenotype at prefix length 20 / 50 / 100",
        "- `manifest.json`    — machine-readable summary of the compilation (seeds, cell counts, prompts)",
        "- `data_dictionary.md` — field-by-field definitions",
        "- `stimulus_corpus.xlsx` — human-readable Excel view generated from the CSVs (browsing only)",
        "",
        "## Design",
        "",
        "- **Models**: " + ", ".join(f"`{lab}` ({sid})" for lab, sid in manifest["model_ids"].items()),
        "- **Methods**: " + ", ".join(f"`{m}`" for m in manifest["methods"]),
        f"- **Trajectories per (model, method) cell**: {manifest['trajectories_per_cell']}",
        f"- **Sequence length**: {manifest['sequence_length']} flips",
        f"- **Temperature**: {manifest['temperature']} (all calls)",
        f"- **Prompt version**: `{manifest['prompt_version']}`",
        "",
        "## Development / holdout split",
        "",
        f"A stratified random 10/10 split within each of the 9 (model, method) cells,",
        f"assigned once at corpus compilation using base seed `{manifest['split_seed_base']}`.",
        "",
        "Per-cell seeds (derived deterministically from the base):",
        "",
        "| cell | seed |",
        "|---|---|",
    ]
    for cell, seed in sorted(manifest["per_cell_split_seeds"].items()):
        lines.append(f"| {cell} | {seed} |")
    lines += [
        "",
        "The split assignment is independent of any phenotype result — it is a random",
        "partition, chosen once from the seed above with no reference to the trajectory",
        "contents. However, the pilot-5 source report already computed aggregate",
        "cell-level phenotype statistics over all 20 trajectories per cell (mean p_H,",
        "switch rate, longest run, etc.). The 10 holdout trajectories in each cell",
        "should therefore be treated as a **frozen evaluation set for subsequent",
        "producer-vs-observer recognition experiments**: any classifier, matching rule,",
        "or stimulus-selection procedure developed from this point forward is built",
        "using only the 10 development trajectories per cell, and the frozen procedure",
        "is then applied to the 10 evaluation trajectories.",
        "",
        "## Provenance",
        "",
        f"- Source run: `{manifest['source_run_id']}` at `{manifest['source_run_root']}`",
        "- Every API attempt (successful and failed) is preserved in the source run's",
        "  `raw_attempts.jsonl`. This corpus is a derived, regenerable view.",
        f"- Compilation is reproducible from `raw_attempts.jsonl` + `trajectories/*.json`",
        "  by rerunning `python -m spar_dynamic.compile_corpus`.",
        "",
        "## Prompts (verbatim)",
        "",
        "**batch:**",
        "```",
        manifest["prompts"]["batch"],
        "```",
        "",
        "**history_conditioned (trial 1; empty history):**",
        "```",
        manifest["prompts"]["history_conditioned_trial1"],
        "```",
        "",
        "**history_conditioned (general form, `<HISTORY>` = growing string of prior H/T):**",
        "```",
        manifest["prompts"]["history_conditioned_general_template"],
        "```",
        "",
        "**independent_calls (identical every call, no history):**",
        "```",
        manifest["prompts"]["independent_calls"],
        "```",
        "",
        "## Sanity",
        "",
        "- `trajectories.csv` has exactly 180 rows.",
        "- `flips.csv` has exactly 18,000 rows (180 × 100).",
        "- `metrics.csv` has exactly 540 rows (180 × 3 prefix lengths).",
        "- Every cell has 10 development + 10 holdout trajectories.",
        "",
        "## Do not edit",
        "",
        "The CSVs and the Excel workbook are regenerated from the source run.",
        "Do not edit them by hand. To change something, change the source data or",
        "the compile script and re-run.",
    ]
    with open(os.path.join(corpus_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_dictionary(corpus_dir: str):
    lines = [
        "# Data dictionary — SPAR Stimulus Corpus",
        "",
        "## trajectories.csv (180 rows — one per trajectory)",
        "",
        "| field | type | description |",
        "|---|---|---|",
        "| trajectory_id | string | Unique ID from source run (e.g. `astra_batch_00`). Stable across recompilations. |",
        "| model | string | One of `astra`, `fable`, `mimo`. |",
        "| method | string | One of `batch`, `history_conditioned`, `independent_calls`. |",
        "| split | string | `development` or `holdout` (frozen at compilation). |",
        "| replicate | int | 1..10, numbered within (cell, split). Replicate 1 in dev ≠ replicate 1 in holdout. |",
        "| sequence | string | The 100-character H/T sequence. |",
        "| n_flips | int | Sequence length (always 100). |",
        "| requested_model_id | string | The OpenRouter slug that was requested (e.g. `openai/gpt-6-astra`). |",
        "| returned_model_id | string | The model_id OpenRouter served (usually equal to requested). |",
        "| provider | string | Serving provider reported by OpenRouter. |",
        "| run_id | string | Source run ID. |",
        "| first_call_utc | ISO 8601 | Timestamp of the first API attempt for this trajectory. |",
        "| finished_utc | ISO 8601 | Timestamp when the trajectory was closed (success). |",
        "| temperature | float | Sampling temperature (0.0 for all pilot 5 calls). |",
        "| prompt_version | string | Prompt-set identifier (`pilot5_v1`). |",
        "| total_api_calls_recorded | int | Every attempt made for this trajectory (including retries and failed parses). |",
        "| trajectory_cost_usd | float | Sum of per-attempt costs for this trajectory. |",
        "| original_replicate_index | int | Source-run replicate index (0-based). Backfill trajectories have index ≥ 20. |",
        "",
        "## flips.csv (18,000 rows — one per flip)",
        "",
        "| field | type | description |",
        "|---|---|---|",
        "| trajectory_id | string | Foreign key to `trajectories.csv`. |",
        "| model | string | Redundant with trajectories.csv, kept for convenience in analyses. |",
        "| method | string | Same. |",
        "| split | string | Same. |",
        "| replicate | int | Same. |",
        "| trial | int | 1..100, position of the flip within the trajectory. |",
        "| choice | char | `H` or `T`. |",
        "| history_before | string | For `history_conditioned` only: the exact H/T history the model saw when producing this flip (empty for the other two methods). |",
        "",
        "## metrics.csv (540 rows — one per (trajectory, prefix))",
        "",
        "| field | type | description |",
        "|---|---|---|",
        "| trajectory_id | string | Foreign key to `trajectories.csv`. |",
        "| model / method / split / replicate | | Same as trajectories.csv. |",
        "| prefix_n | int | Prefix length the metrics are computed over (20, 50, or 100). |",
        "| p_H | float | Proportion of H in the prefix. |",
        "| switch_rate | float | Fraction of consecutive positions where the choice changes. |",
        "| runs_z | float | Wald–Wolfowitz runs Z (positive = too many alternations; negative = too many runs). |",
        "| longest_run | int | Longest consecutive run of a single symbol in the prefix. |",
        "| HH / HT / TH / TT | float | Fractions of the four bigrams over the (prefix_n − 1) bigrams. |",
        "| entropy_binary | float | Binary entropy of p_H (bits). |",
        "",
        "## Related files (outside `corpus/`)",
        "",
        "- `../../raw_attempts.jsonl` — every API attempt for the source run (immutable provenance).",
        "- `../../trajectories/trajectory-*.json` — per-trajectory result and metadata (source of truth for this compilation).",
        "- `../THREE_ARCHITECTURE_SOURCE_REPORT.md` — narrative analysis and headline results.",
    ]
    with open(os.path.join(corpus_dir, "data_dictionary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_excel(corpus_dir: str, manifest: Dict):
    """Optional Excel view. Generated from the CSVs; do not edit."""
    import openpyxl  # local import so pure-CSV compile still works without it
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    def _sheet_from_csv(name: str, csv_path: str, freeze: str = "A2"):
        ws = wb.create_sheet(name)
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for r_idx, row in enumerate(reader, start=1):
                for c_idx, val in enumerate(row, start=1):
                    ws.cell(row=r_idx, column=c_idx, value=val)
        # Header formatting
        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="DDDDDD")
        ws.freeze_panes = freeze

    _sheet_from_csv("Trajectories", os.path.join(corpus_dir, "trajectories.csv"))
    _sheet_from_csv("Flips", os.path.join(corpus_dir, "flips.csv"))
    _sheet_from_csv("Metrics", os.path.join(corpus_dir, "metrics.csv"))

    # Cell Summary sheet
    ws = wb.create_sheet("Cell Summary")
    ws.append(["cell", "trajectories", "dev", "holdout", "cell_seed"])
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDDDDD")
    for cell, counts in sorted(manifest["per_cell_counts"].items()):
        ws.append([cell, counts["dev"] + counts["holdout"], counts["dev"],
                   counts["holdout"], counts["cell_seed"]])
    ws.freeze_panes = "A2"

    # Data Dictionary sheet — pulled from data_dictionary.md as plain text
    ws = wb.create_sheet("Data Dictionary")
    with open(os.path.join(corpus_dir, "data_dictionary.md"), "r", encoding="utf-8") as f:
        for line in f:
            ws.append([line.rstrip("\n")])
    for c in ws[1]:
        c.font = Font(bold=True)

    wb.save(os.path.join(corpus_dir, "stimulus_corpus.xlsx"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data-root", default="data/spar_dynamic")
    ap.add_argument("--out-dir", default="",
                    help="output directory (default: <run>/results/corpus)")
    args = ap.parse_args()
    result = build_corpus(args.run_id, args.data_root, args.out_dir or None)
    print(f"[compile] DONE — corpus at {result['corpus_dir']}", flush=True)


if __name__ == "__main__":
    main()
