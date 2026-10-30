"""Where everything lives after the 2026-10-21 reorganisation.

Experiments now sit in dated folders under track1_self_prediction/ and
track2_game_theory/; all Python code is in src/. Code that used to hard-code
an old repo-relative path calls legacy("<old path>") instead, so the old
location stays readable in the source and the mapping lives in one place.
docs/PATH_MAP.md is generated from MOVES (python -m repo_paths).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
T1 = REPO / "track1_self_prediction"
T2 = REPO / "track2_game_theory"
DOCS = REPO / "docs"
EXPORTS = REPO / "exports"

# Experiment folders, chronological within each track.
T1_EXP = {
    "prereg_harness":        T1 / "01_2026-09-21_preregistered_harness",
    "pilot1":                T1 / "02_2026-09-29_pilot1_source_signature",
    "pilot2":                T1 / "03_2026-09-29_pilot2_self_vs_other",
    "pilot3":                T1 / "04_2026-09-29_pilot3_provenance",
    "pilot4":                T1 / "05_2026-09-29_pilot4_astra_followup",
    "corpus":                T1 / "06_2026-09-30_stimulus_corpus",
    "fce1":                  T1 / "07_2026-10-01_fce1_history_conditioned",
    "fce2":                  T1 / "08_2026-10-01_fce2_batch_and_independent",
    "ab_validation":         T1 / "09_2026-10-01_ab_task_validation",
    "story_swap":            T1 / "10_2026-10-01_story_swap",
    "phenotype":             T1 / "11_2026-10-01_phenotype_prediction",
    "phase2_qwen":           T1 / "12_2026-10-07_phase2_qwen",
    "phase2_mimo":           T1 / "13_2026-10-08_phase2_mimo",
    "dice_v31":              T1 / "14_2026-10-15_dice_v31",
    "dice_ext":              T1 / "15_2026-10-15_dice_model_extension",
    "dice_v41":              T1 / "16_2026-10-16_dice_v41",
    "favorite_integer":      T1 / "17_2026-10-16_favorite_integer",
    "favorite_animal":       T1 / "18_2026-10-16_favorite_animal",
    "favorite_animal_crossed": T1 / "19_2026-10-16_favorite_animal_crossed",
    "static_selfpred":       T1 / "20_2026-10-20_static_selfpred_replication",
    "dice_logprob":          T1 / "21_2026-10-29_dice_logprob",
    "dice_recognition":      T1 / "22_2026-10-29_loula_dice_recognition_pilot",
    "dice_recognition_v2":   T1 / "23_2026-10-29_loula_recognition_redesign",
}
T2_EXP = {
    "blind_twin_v1":         T2 / "01_2026-10-09_blind_twin_v1_mp",
    "blind_twin_v2":         T2 / "02_2026-10-09_blind_twin_v2_mp",
    "blind_twin_rps":        T2 / "03_2026-10-09_blind_twin_rps",
    "disclosure_pilot":      T2 / "04_2026-10-09_opponent_disclosure_pilot",
    "study1_exp1":           T2 / "05_2026-10-10_study1_exp1_disclosure",
    "exp2_judges":           T2 / "06_2026-10-10_exp2_blind_twin_judges",
    "selfself":              T2 / "07_2026-10-11_selfself_judges_and_retest",
    "post_hoc":              T2 / "08_2026-10-11_post_hoc_analyses",
    "paca_believed_self":    T2 / "09_2026-10-11_paca_believed_self",
    "paint_circle":          T2 / "10_2026-10-20_paint_circle_selfplay",
    "fable_specificity":     T2 / "11_2026-10-21_paint_circle_fable_specificity",
    "fable_perspective":     T2 / "12_2026-10-21_paint_circle_fable_perspective",
    "scripted_opponent":     T2 / "13_2026-10-21_paint_circle_scripted_opponent_pilot",
    "scripted_identity":     T2 / "14_2026-10-21_paint_circle_scripted_identity_framing",
    "iid_identity":          T2 / "15_2026-10-21_paint_circle_iid_identity_framing",
    "iid_deterministic":     T2 / "16_2026-10-22_paint_circle_iid_deterministic_program",
    "entropy_gradient":      T2 / "17_2026-10-22_paint_circle_entropy_gradient",
    "entropy_gradient_rep":  T2 / "18_2026-10-22_paint_circle_entropy_gradient_replication",
    "noise_label":           T2 / "19_2026-10-27_paint_circle_noise_label_predictability",
    "noise_label_rep":       T2 / "20_2026-10-27_paint_circle_noise_label_replication",
}
EXP = {**T1_EXP, **T2_EXP}

_SD = "data/spar_dynamic"
# (old repo-relative prefix, new location). Longest prefixes are matched first.
MOVES = [
    # ---- track 1
    ("pilots/pilot_0_preregistered_harness", T1_EXP["prereg_harness"]),
    ("pilots/pilot_1_dynamic_source", T1_EXP["pilot1"]),
    ("pilots/pilot_2_self_other", T1_EXP["pilot2"]),
    ("pilots/pilot_3_provenance", T1_EXP["pilot3"]),
    ("pilots/pilot_4_astra_followup", T1_EXP["pilot4"]),
    ("pilots/README.md", DOCS / "archive" / "pilots_README_2026-10-11.md"),
    ("corpus", T1_EXP["corpus"] / "corpus"),
    (f"{_SD}/spar-stimulus-corpus-20260930T012044Z", T1_EXP["corpus"] / "spar-stimulus-corpus-20260930T012044Z"),
    (f"{_SD}/full_corpus_experiment_1", T1_EXP["fce1"] / "full_corpus_experiment_1"),
    (f"{_SD}/full_corpus_experiment_1_batch", T1_EXP["fce2"] / "full_corpus_experiment_1_batch"),
    (f"{_SD}/full_corpus_experiment_1_independent_calls", T1_EXP["fce2"] / "full_corpus_experiment_1_independent_calls"),
    (f"{_SD}/FCE1_FCE2_CROSS_METHOD_REPORT.md", T1_EXP["fce2"] / "FCE1_FCE2_CROSS_METHOD_REPORT.md"),
    (f"{_SD}/full_corpus_validation", T1_EXP["ab_validation"] / "full_corpus_validation"),
    (f"{_SD}/full_corpus_experiment_1_independent_calls_story_batch",
     T1_EXP["story_swap"] / "full_corpus_experiment_1_independent_calls_story_batch"),
    (f"{_SD}/cross_story_indep_stimuli", T1_EXP["story_swap"] / "cross_story_indep_stimuli"),
    (f"{_SD}/full_corpus_phenotype_prediction", T1_EXP["phenotype"] / "full_corpus_phenotype_prediction"),
    (f"{_SD}/full_corpus_phenotype_prediction_switch_rate", T1_EXP["phenotype"] / "full_corpus_phenotype_prediction_switch_rate"),
    (f"{_SD}/PHENOTYPE_BASELINES_REPORT.md", T1_EXP["phenotype"] / "PHENOTYPE_BASELINES_REPORT.md"),
    (f"{_SD}/phase2/_preflight", T1_EXP["phase2_qwen"] / "phase2" / "_preflight"),
    (f"{_SD}/phase2/p2-20261007", T1_EXP["phase2_qwen"] / "phase2" / "p2-20261007"),
    (f"{_SD}/phase2/p2-mimo-20261008", T1_EXP["phase2_mimo"] / "phase2" / "p2-mimo-20261008"),
    ("docs/handoffs/PHASE2_PILOT_RESULTS_2026-10-08.md", T1_EXP["phase2_qwen"] / "PHASE2_PILOT_RESULTS_2026-10-08.md"),
    ("docs/handoffs/PHASE2_MIMO_RUN_RESULTS_2026-10-08.md", T1_EXP["phase2_mimo"] / "PHASE2_MIMO_RUN_RESULTS_2026-10-08.md"),
    (f"{_SD}/dice_pilot", T1_EXP["dice_v31"] / "dice_pilot"),
    (f"{_SD}/dice_pilot_ext", T1_EXP["dice_ext"] / "dice_pilot_ext"),
    (f"{_SD}/dice_pilot_v41", T1_EXP["dice_v41"] / "dice_pilot_v41"),
    (f"{_SD}/favorite_integer", T1_EXP["favorite_integer"] / "favorite_integer"),
    (f"{_SD}/favorite_animal", T1_EXP["favorite_animal"] / "favorite_animal"),
    (f"{_SD}/favorite_animal_crossed", T1_EXP["favorite_animal_crossed"] / "favorite_animal_crossed"),
    (f"{_SD}/static_selfpred", T1_EXP["static_selfpred"] / "static_selfpred"),
    ("docs/handoffs/STATIC_PILOT_AUDIT_2026-10-20.md", T1_EXP["static_selfpred"] / "STATIC_PILOT_AUDIT_2026-10-20.md"),
    ("docs/handoffs/STATIC_SELFPRED_PROMPTS_v1.0_FROZEN_2026-10-20.txt",
     T1_EXP["static_selfpred"] / "STATIC_SELFPRED_PROMPTS_v1.0_FROZEN_2026-10-20.txt"),
    ("RESULTS_2026-10-21/1_static_self_prediction", T1_EXP["static_selfpred"] / "results_summary"),
    # ---- track 2
    ("blind_twin/results/bt-20261009T0455Z", T2_EXP["blind_twin_v1"] / "bt-20261009T0455Z"),
    ("blind_twin/results/bt2-20261009T0957Z", T2_EXP["blind_twin_v2"] / "bt2-20261009T0957Z"),
    ("blind_twin_rps/results", T2_EXP["blind_twin_rps"]),
    ("opponent_disclosure/results", T2_EXP["disclosure_pilot"]),
    ("opponent_disclosure_rps_3models/results/rps3m-20261009T1240Z", T2_EXP["study1_exp1"] / "superseded" / "rps3m-20261009T1240Z"),
    ("opponent_disclosure_rps_3models/results", T2_EXP["study1_exp1"]),
    ("opponent_disclosure_mp_3models/results", T2_EXP["study1_exp1"]),
    ("docs/study1", T2_EXP["study1_exp1"] / "docs"),
    ("blind_twin_exp1/results", T2_EXP["exp2_judges"]),
    ("blind_twin_selfself/results", T2_EXP["selfself"]),
    ("post_hoc", T2_EXP["post_hoc"]),
    ("paca_believed_self", T2_EXP["paca_believed_self"]),
    ("paint_circle/results/shadow_calibration.json", T2_EXP["paint_circle"] / "shadow_calibration.json"),
    ("paint_circle/results/pilot-20261020", T2_EXP["paint_circle"] / "pilot-20261020"),
    ("paint_circle/results/main-20261020", T2_EXP["paint_circle"] / "main-20261020"),
    ("paint_circle/results/makeups-20261020", T2_EXP["paint_circle"] / "makeups-20261020"),
    ("paint_circle/results/analysis-20261020", T2_EXP["paint_circle"] / "analysis-20261020"),
    ("paint_circle/results/fable-specificity-20261021", T2_EXP["fable_specificity"] / "fable-specificity-20261021"),
    ("paint_circle/results/analysis-20261021", T2_EXP["fable_specificity"] / "analysis-20261021"),
    ("paint_circle/results/fable-perspective-20261021", T2_EXP["fable_perspective"] / "fable-perspective-20261021"),
    ("RESULTS_2026-10-21/2_self_play", T2_EXP["paint_circle"] / "results_summary"),
    ("RESULTS_2026-10-21/3_fable_followup", T2_EXP["fable_specificity"] / "results_summary"),
    ("RESULTS_2026-10-21/4_fable_perspective_taking", T2_EXP["fable_perspective"] / "results_summary"),
    # ---- cross-cutting
    ("docs/handoffs/SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md",
     DOCS / "reports" / "SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md"),
    ("RESULTS_2026-10-21/REPORT.md", DOCS / "reports" / "SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md"),
    ("RESULTS_2026-10-21/upload_pack", EXPORTS / "upload_pack_2026-10-21"),
    ("REVIEW_GUIDE.md", DOCS / "archive" / "REVIEW_GUIDE_2026-10-11.md"),
    ("llms.txt", DOCS / "archive" / "llms_2026-10-11.txt"),
]
# Code packages and scripts moved from the repo root into src/.
CODE = ["spar_dynamic", "blind_twin", "blind_twin_rps", "blind_twin_exp1", "blind_twin_selfself",
        "opponent_disclosure", "opponent_disclosure_rps_3models", "opponent_disclosure_mp_3models",
        "paint_circle", "blind_twin_retest.py", "experiment1_derived.py", "experiment1_makeup.py",
        "experiment1_post_hoc_strategy.py", "experiment1_sequential_structure.py",
        "experiment2_observation_equivalence.py", "export_results.py"]

# New runs of the pilot-era spar_dynamic orchestrators (no single experiment
# folder applies) go here unless --data-root is given.
NEW_RUNS = REPO / "new_runs"


def legacy(old) -> Path:
    """Map an old repo-relative path to its location after the reorganisation.

    Absolute paths are returned unchanged. Unmapped paths under the retired
    data/spar_dynamic/ go to new_runs/spar_dynamic/; anything else is taken
    relative to the repo root.
    """
    if Path(old).is_absolute():
        return Path(old)
    old = str(old).replace("\\", "/").strip("/")
    if old.startswith("./"):
        old = old[2:]
    for prefix, new in sorted(MOVES, key=lambda m: -len(m[0])):
        if old == prefix or old.startswith(prefix + "/"):
            return Path(new) / old[len(prefix):].lstrip("/")
    if old == _SD or old.startswith(_SD + "/"):
        return NEW_RUNS / "spar_dynamic" / old[len(_SD):].lstrip("/")
    return REPO / old


def find_run(run_id: str) -> Optional[Path]:
    """Locate a run folder by its id anywhere under the two track folders."""
    for track in (T1, T2):
        hits = [p for p in track.rglob(run_id) if p.is_dir()]
        if hits:
            return hits[0]
    return None


def write_path_map(path: Path = DOCS / "PATH_MAP.md") -> None:
    rel = lambda p: Path(p).relative_to(REPO).as_posix()
    lines = ["# Path map: old locations → new locations (reorganisation of 2026-10-21)", "",
             "Older reports, handoffs and run manifests refer to the pre-reorganisation layout. "
             "Use this table to find those files now. Generated from `src/repo_paths.py`.", "",
             "| Old path | New path |", "|---|---|"]
    for old, new in MOVES:
        lines.append(f"| `{old}` | `{rel(new)}` |")
    for c in CODE:
        lines.append(f"| `{c}` | `src/{c}` |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    missing = [(o, n) for o, n in MOVES if not Path(n).exists()]
    for o, n in missing:
        print("MISSING:", o, "->", n, file=sys.stderr)
    write_path_map()
    print(f"{len(MOVES)} moves, {len(missing)} missing; wrote docs/PATH_MAP.md")
