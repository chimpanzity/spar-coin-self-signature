# Repository reorganisation, 2026-10-21

The repository was reorganised so that each mini-experiment has its own dated folder, grouped into two tracks:

- `track1_self_prediction/`: static self-prediction and self-modelling (coin flips, corpus experiments, Phase 2, dice, favourite integer and animal, static replication).
- `track2_game_theory/`: game-theory experiments (Blind Twin, opponent disclosure, Study 1, post-hoc analyses, PACA believed-self, paint-and-circle self-play).

No data, results or reports changed content. Files were moved with `git mv`, so `git log --follow <file>` shows each file's history across the move.

## What moved where

`docs/PATH_MAP.md` lists every old location and its new one. The same table is in `src/repo_paths.py` (`MOVES`), and older reports and run manifests that mention pre-reorganisation paths can be read against it. In short:

| Before | After |
|---|---|
| Experiment data and results (`data/spar_dynamic/...`, `pilots/`, `corpus/`, `<package>/results/`, `post_hoc/`, `paint_circle/results/`, `RESULTS_2026-10-21/`) | The matching dated experiment folder. Inside it, run folders keep their original names. |
| Experiment-specific docs (`docs/study1/`, the Phase 2 result summaries, the static-study audit and frozen prompts) | The matching experiment folder |
| All Python packages and root scripts | `src/` (package names unchanged) |
| `paca_believed_self/` (a self-contained package with its data) | `track2_game_theory/09_2026-10-11_paca_believed_self/`, kept whole |
| `pilots/pilot_0_preregistered_harness/` (a self-contained package) | `track1_self_prediction/01_2026-09-21_preregistered_harness/`, kept whole |
| Combined report `SPAR_RESULTS_STATIC_AND_SELFPLAY_2026-10-21.md` | `docs/reports/` |
| Upload pack | `exports/upload_pack_2026-10-21/` (the zip is git-ignored) |
| Old `README.md`, `REVIEW_GUIDE.md`, `llms.txt`, `pilots/README.md` | `docs/archive/` (dated) |

## Code changes (paths only)

- **New `src/repo_paths.py`.** It holds the experiment folder locations and a `legacy("<old path>")` function that maps an old repo-relative path to its new location.
- **Hard-coded paths now call `legacy(...)`.** The old path is still visible in the code, wrapped in the call. 57 edits in 37 files, all path strings:
  - package `RESULTS` folders
  - `REPO = PKG.parent`
  - lists of earlier runs
  - the inputs of the post-hoc analysis scripts
  - the default corpus folder
  - `--data-root` defaults
- **New runs** of an experiment's package go next to that experiment's earlier runs. Runs that fit no single experiment go to `new_runs/`.
- **Phase 2 and Blind Twin run lookup:** `spar_dynamic.phase2`, `blind_twin` and `blind_twin_rps` now find an existing run by its id (`repo_paths.find_run`). The phase2 `REPO_ROOT` is the repository root again.
- **Fixed during review:** a variable-name clash in `paint_circle/calibrate_shadow.py`. It was introduced by the path edit and caught before the script was ever run.
- **Proteus location:** `paint_circle/shadow.py` loads the PACA Proteus code from its new location.
- **Tests:** `pytest.ini` adds `pythonpath = src`, and a root `conftest.py` puts `src/` on `PYTHONPATH` for tests that start subprocesses.

### Verification

- **Tests:** all 391 pass, including the two end-to-end fake-game tests.
- **Re-run analyses:** these re-ran on the moved data and reproduced their committed outputs byte for byte:
  - `paint_circle.fable_specificity`
  - `paint_circle.fable_perspective`
  - `spar_dynamic.static_selfpred.analysis`
- **Post-hoc scripts:** `experiment1_post_hoc_strategy.py` and `experiment2_observation_equivalence.py` also ran on the moved data. Their point estimates were unchanged.
  - Bootstrap interval endpoints moved by 0.01 in a few cells. That is ordinary floating-point and random-number variation between the original machine (macOS) and this one (Windows).
  - The committed outputs were kept as originally produced.

### Frozen-code fingerprints

Several packages store a hash of their own `.py` files in each run's manifest. They refuse to resume or extend a run if the code has changed since. The packages are:

- `blind_twin`, `blind_twin_rps`, `blind_twin_exp1`, `blind_twin_selfself`
- `opponent_disclosure`, `opponent_disclosure_rps_3models`, `opponent_disclosure_mp_3models`
- `experiment1_makeup.py`
- `spar_dynamic.phase2`

The path edits above change those hashes. Every run they guard is finished, so nothing current is affected. Resuming one of those historical runs would need the guard to be told that the change was paths-only. The code logic is unchanged; compare with git tag `pre-reorg-2026-10-21`.

## Running code after the reorganisation

From the repository root:

```bash
export PYTHONPATH=src          # PowerShell: $env:PYTHONPATH = "src"
python -m pytest               # pytest.ini already adds src
python -m paint_circle.fable_specificity --out <dir>
python -m spar_dynamic.static_selfpred.analysis track1_self_prediction/20_2026-10-20_static_selfpred_replication/static_selfpred/main-20261021T021451Z
python src/experiment1_post_hoc_strategy.py
```

Live runs need `OPENROUTER_API_KEY`, which is read from `.env` at the repository root. That file is git-ignored.
