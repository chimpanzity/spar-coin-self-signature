# Working on SPAR with Claude Code

Claude Code reads this file automatically at the start of every session in this repo. It records how experiments here have been run, so a session on any machine can continue them the same way. Chris (the PI) supplies a handoff document for each new experiment; follow it, and follow the rules below wherever it is silent.

## Standing rules (from Chris)

- **Keys:** read `OPENROUTER_API_KEY` and `VAST_API_KEY` from the environment. Never print, log, commit or copy them into any file (including notes or memory).
- **Ask before:**
  - spending money: give a cost and time estimate and a hard cap, and wait for an explicit yes;
  - `git push`;
  - creating GitHub repos or anything else outward-facing.
- **Never modify a frozen experiment.** Do not touch a committed experiment folder, a frozen tag or its code once data exist. New work goes in a new numbered folder.
- **Freeze before data:** protocol, prompts, manifests, code and the analysis plan are committed (and hash-recorded) before any paid collection. Deviations are written down, never silently patched.
- **Report outcomes faithfully.** Nulls are results. Every number in a report comes from generated output files, not from memory.
- **Plain, understated writing.** Reports are for Chris and the SPAR mentors (and, for PACA, reviewers).

## Setting up a new machine

Python **3.14** (3.14.5 used through Nov 2026). From the repo root:

```bash
git config --global core.autocrlf false   # avoids CRLF hash mismatches (see Gotchas)
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # minimal
# exact versions used through Nov 2026:
grep -v '^torch==' requirements-lock.txt > /tmp/lock.txt && .venv/Scripts/python -m pip install -r /tmp/lock.txt
# torch is only needed for local tokenizer tests of the open-weight experiments:
# .venv/Scripts/python -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
```

Copy these from the old machine through a password manager or an encrypted drive, never git, email or Dropbox:
- **`.env`** (repo root, gitignored): it holds `OPENROUTER_API_KEY` and `VAST_API_KEY`.
- **`~/.ssh/vast_spar` and `~/.ssh/vast_spar.pub`**, the vast.ai SSH key. A new key can be attached with `vastai attach ssh <id> "$(cat ~/.ssh/vast_spar.pub)"`.

Most scripts read `os.environ` and do not load `.env` themselves. Export the keys first:

```bash
set -a; . ./.env; set +a      # bash (Claude Code's Bash tool)
```

The original paths are `C:\Chimpanzity_Spar\spar-coin-self-signature` (this repo) and `C:\Users\chris\Claude\Projects\LLM Game Theory Study\Protean Choice Task` (PACA). Reusing them keeps Claude Code's per-project memory and the documents' path references valid.

## Repository conventions

- **Two tracks:** `track1_self_prediction/` (static self-prediction) and `track2_game_theory/`. Each has a README with a timeline table; add a row for every new experiment.
- **One folder per experiment,** numbered and dated (`31_2026-11-15_cross_model_teacher_forcing/`). It contains:
  - `README.md` (the status table, a short result and a figure);
  - `PROTOCOL.md` (frozen) and `prompts_frozen.md`;
  - the design CSV, `manifest.json` and `inputs_sha256.json`;
  - `raw/`, `results/` (including `CHECKS.md`), `figures/`;
  - `REPORT.md`;
  - `run_record.json` (instance, cost, environment, file hashes);
  - `APPROVALS.md` (Chris's decisions).
- **Code** lives in `src/spar_dynamic/<experiment>/`, tests in `tests/`, and handoffs in `docs/handoffs/`. `docs/PATH_MAP.md` maps old paths.
- **Results index:** a top-level `RESULTS_<date>/` folder with a plain README links each batch's reports, tables and figures. Chris asked for this so results are easy to find. Raw data stay where the code writes them.
- **Experiment entry points:** `python -m src.spar_dynamic.<exp>` with phases. For example, experiments 31–32 use `freeze`, `dryrun`, `validate`, `checks` and `analyse`.

## Workflow for a new experiment

1. Read the handoff completely, then the nearest previous experiment's code and report. Reuse its machinery as an isolated copy or import; never edit the old one.
2. Implement in a new numbered folder and `src/` package. Write tests: prompt bytes and hashes, parser edge cases, leakage, replay, and the stop rules.
3. Run the offline phases (`freeze`, `dryrun`, `validate`) and a fake or tiny-model end-to-end check.
4. **Commit the freeze** (protocol, prompts, manifests, code) and record the hashes.
5. **Report to Chris and wait:** cost and time estimate, hard cap, test counts, design ambiguities and deviations. No paid calls before an explicit yes.
6. Run. Monitor the cost against the cap and stop on any failed stop rule.
7. Run the post-run checks (`checks`), then `analyse`. Write `REPORT.md`, the folder `README.md`, the track README row and the `RESULTS_<date>` index.
8. Commit the results. Ask before pushing.

## OpenRouter

These quirks are measured, not visible in the code:
- **Qwen3-32B on DeepInfra ignores `reasoning.enabled=false`;** SiliconFlow honours it. Qwen at temperature 0 is not deterministic, and in long matching-pennies histories it may echo the grid or answer a bare letter, so accept a bare final letter and allow re-requests.
- **Astra and Fable accept no temperature parameter.**
- **Cost:** about $1.9 (Astra) to $3.7 (Fable) per 200-round two-player session; about $0.0016 per static call at minimal effort.
- **Getting `cost` back:** read `usage.cost` from each raw response, and keep raw responses in JSONL per session.

## vast.ai open-weight runs (Qwen3-32B, Mistral Small 3.2 24B)

This recipe reproduced experiments 21, 26, 28 and 30 bit for bit.

**Renting the GPU**
- **CLI:** `vastai` is in the venv; on Windows use `--raw` with `PYTHONIOENCODING=utf-8`, because the table output crashes on cp1252.
- **GPU:** A100-SXM4-80GB. **Always filter `gpu_ram>=79`**, because `gpu_name=A100_SXM4` also matches 40 GB cards.
- **Offers that worked:**
  - Czechia 34475479: $1.25/h, driver 595.91.07;
  - North Carolina 53873543: driver 595.91.07, cheap download;
  - Texas: driver 580.173.02.
- **Budget disk and download, not just $/h:** in experiment 27, 49% of the cost was non-GPU. Check `vastai show invoices-v1 -c -s <date> -e <date> --raw`.
- **A failed create can still leave an instance:** `create instance` may return `success: false` and leave a stopped instance whose GPU was taken. Destroy it (`echo y | vastai destroy instance <id>`) and take the next offer.

**Software on the instance**
- **Image:** `pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime`. Then install `torch==2.11.0` (cu128 index), `transformers==5.22.0`, `accelerate==1.15.0`, `huggingface_hub==2.4.0`, `mistral_common==1.13.0` and `hf_xet`.
- **Must uninstall torchvision and torchaudio:** the image's torchvision breaks transformers imports.
- **Models:** download with `snapshot_download(max_workers=16)`.
  - Qwen3-32B @ `9216db57…`;
  - Mistral `mistralai/Mistral-Small-3.2-24B-Instruct-2506` @ `95a6d26c…`. Skip `consolidated.safetensors`. It has no HF chat template: tokenise with mistral_common tekken (faces are ids 1049–1054).
- **Mistral is slow on prediction prompts:** it writes prose up to the token cap (about 5.6 s per trial against about 1.5 s for Qwen).

**Deploying and keeping costs down**
- **Deploy exact committed bytes:** `git -c core.autocrlf=false archive <commit> src ... | ssh ... tar -x`. Plain `git archive` on a CRLF checkout breaks bash (`pipefail\r`) and the hashes.
- **Destroy the instance as soon as the run and its archival check finish,** and record the cost in `run_record.json`.

## Gotchas

- **Line endings:** with `core.autocrlf=true` the working tree turns LF files into CRLF, and frozen-file hash checks fail although the git blobs are intact. Hash LF-normalised bytes, or set `autocrlf false`.
- **GitHub push protection** flags the docstring text "Mistral" directly followed by "Mistral3ForConditionalGeneration" as a secret (a false positive). Don't put "Mistral" right before that class name.
- **The `gh` CLI is not installed;** give Chris compare or PR URLs instead.
- **No Docker or WSL on the Windows host.** Untrusted generated code runs in the Job Object and audit-hook sandbox from track 2 folder 21 (`src/blind_twin_forecast_prediction/sandbox.py`). The venv `python.exe` is a launcher stub, so launch `sys.base_prefix/python.exe` inside a one-process Job Object.
- **Paths with `/c/...` inside `python -c` resolve wrongly;** pass paths through argv.

## Related project: PACA (Dodging Proteus, ICLR 2027 revision)

PACA experiments live in a separate repo (local: `...\LLM Game Theory Study\Protean Choice Task`; public snapshot: `chimpanzity/PACA_Revision`). Its `CLAUDE.md` has the PACA runbook. Two things carry over from this repo:
- **The key:** PACA runs read the same OpenRouter key, exported from this repo's `.env`.
- **The manuscript:** the current version is the October 2026 ICLR PDF ("Assessing Dynamic Predictability in LLM Strategic Behavior", Martin & Bhui), not the August preprint.
