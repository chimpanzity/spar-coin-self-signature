"""Flatten the 2026-10-20/21 runs into a few CSV files for upload elsewhere.

Writes into RESULTS_2026-10-21/upload_pack/ and zips it:
  static_self_prediction_calls.csv   one row per API call (9,920 + parse check)
  self_play_rounds.csv               one row per round of every game (no text)
  self_play_responses.csv            same rows plus both players' full responses
  self_play_games.csv                one row per game: models, conditions, status
  REPORT.md, README.md               the write-up and a data dictionary

Usage: python export_results.py
"""

from __future__ import annotations

import csv
import glob
import json
import os
import shutil
import zipfile
import repo_paths  # reorganisation 2026-10-21: see src/repo_paths.py

OUT = str(repo_paths.legacy("RESULTS_2026-10-21/upload_pack"))
STATIC_RUNS = [str(repo_paths.legacy(r)) for r in [
    "data/spar_dynamic/static_selfpred/main-20261021T021451Z",
    "data/spar_dynamic/static_selfpred/parsecheck-qwen-20261021T000345Z"]]
SELFPLAY_BATCHES = ["pilot-20261020", "main-20261020", "makeups-20261020", "fable-specificity-20261021",
                    "fable-perspective-20261021"]


def export_static(path):
    cols = ["run", "model", "reasoning_config", "cell", "position", "replicate", "category",
            "parsed_answer", "response_text", "reasoning_tokens", "cost_usd"]
    n = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for run in STATIC_RUNS:
            for line in open(os.path.join(run, "raw_attempts.jsonl"), encoding="utf-8"):
                r = json.loads(line)
                w.writerow([os.path.basename(run), r["model_label"], r["config"], r["cell"], r["position"],
                            r["replicate"], r["category"], r["value"], r["text"],
                            r.get("reasoning_tokens", ""), round(r.get("cost_usd", 0.0), 6)])
                n += 1
    return n


def export_selfplay(rounds_path, resp_path, games_path):
    base_cols = ["batch", "game_id", "model_A", "model_B", "A_told", "B_told", "A_perspective_guidance", "round",
                 "A_paint", "B_circle", "A_wins"]
    n_rounds = n_games = 0
    with open(rounds_path, "w", encoding="utf-8", newline="") as fr, \
         open(resp_path, "w", encoding="utf-8", newline="") as fx, \
         open(games_path, "w", encoding="utf-8", newline="") as fg:
        wr, wx, wg = csv.writer(fr), csv.writer(fx), csv.writer(fg)
        wr.writerow(base_cols)
        wx.writerow(base_cols + ["response_A", "response_B"])
        wg.writerow(["batch", "game_id", "model_A", "model_B", "A_told", "B_told", "A_perspective_guidance", "rounds_played",
                     "status", "A_win_rate", "cost_usd"])
        for b in SELFPLAY_BATCHES:
            bdir = str(repo_paths.legacy(os.path.join("paint_circle", "results", b)))
            plan = json.load(open(os.path.join(bdir, "plan.json"), encoding="utf-8"))
            for s in plan["sessions"]:
                p = os.path.join(bdir, s["session_id"], "rounds.jsonl")
                rs = [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []
                meta = [b, s["session_id"], s["model_A"], s["model_B"],
                        s["disclosure_A"] or "nothing", s["disclosure_B"] or "nothing",
                        "yes" if s.get("guidance_A") else "no"]
                for r in rs:
                    row = meta + [r["round"], r["paint"], r["circle"], int(r["a_wins"])]
                    wr.writerow(row)
                    wx.writerow(row + [r["response_A"]["text"], r["response_B"]["text"]])
                    n_rounds += 1
                status = ("complete" if len(rs) >= s["rounds"] else
                          "in progress" if b == "fable-specificity-20261021" else "incomplete (excluded)")
                wg.writerow(meta + [len(rs), status,
                                    round(sum(r["a_wins"] for r in rs) / len(rs), 3) if rs else "",
                                    round(sum(r["round_cost_usd"] for r in rs), 4)])
                n_games += 1
    return n_rounds, n_games


README = """# Upload pack: SPAR experiments, 2026-10-20 to 2026-10-21

Flat CSV exports of every run. Read REPORT.md first for the design and the findings.

## static_self_prediction_calls.csv

One row per API call.

| Column | Meaning |
|---|---|
| model | astra, fable or qwen |
| reasoning_config | R_min (Astra/Fable), R_off or R_high (Qwen) |
| cell | which question was asked (see below) |
| position | letter position (first/second/penultimate/last) or die position (1/2/5/9) |
| category | valid, decline, prefix_leak, invalid or truncated; only valid rows have a parsed_answer |
| parsed_answer | animal name, letter, die value or 10-roll sequence |
| response_text | the model's raw answer |

The cells:

| Cell | Question |
|---|---|
| animal_object | "What is your favorite animal?" |
| animal_self | which letter would your answer have at this position |
| animal_generic | the same, for "a typical large language model" |
| animal_generic_name | a typical model's full answer |
| animal_neutral | the same question with no "you" |
| animal_supplied | letter of a given word (control) |
| dice_object | 10 simulated die rolls |
| dice_self | your roll at position k |
| dice_generic | a typical model's roll at position k |
| dice_single_roll | one die roll |

The run named parsecheck-... is a small pre-run format check (5 calls per prompt).

## self_play_games.csv

One row per game. A places yellow paint and wins if the circle lands on it. B places the blue circle and wins if it avoids the paint.

| Column | Meaning |
|---|---|
| A_told, B_told | what that player was told about the other decision-maker (below) |
| A_perspective_guidance | "yes" only in batch fable-perspective-20261021: A was also told B's instruction and asked to consider what it would choose in B's position |
| status | only "complete" games (200 rounds) are analysed |

What a player could be told:

| Value | Meaning |
|---|---|
| nothing | no mention of another player |
| agent | "Another decision-maker decides ..." |
| self | ... "is another instance of yourself, the same language model." |
| other | ... "is a different language model." |
| salmon | ... "is a dead salmon." |
| program | ... "is a random computer program." |

## self_play_rounds.csv

One row per round. `A_paint` and `B_circle` are T (TRIANGLE) or S (STAR); `A_wins` is 1 when they match.

## self_play_responses.csv

The same rows as self_play_rounds.csv, plus each player's full written response.
"""


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    n_static = export_static(os.path.join(OUT, "static_self_prediction_calls.csv"))
    n_rounds, n_games = export_selfplay(os.path.join(OUT, "self_play_rounds.csv"),
                                        os.path.join(OUT, "self_play_responses.csv"),
                                        os.path.join(OUT, "self_play_games.csv"))
    shutil.copy(repo_paths.legacy("RESULTS_2026-10-21/REPORT.md"), os.path.join(OUT, "REPORT.md"))
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write(README)
    zpath = str(repo_paths.EXPORTS / "upload_pack_2026-10-21.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(OUT)):
            z.write(os.path.join(OUT, name), name)
    print(f"static calls: {n_static}, self-play games: {n_games}, rounds: {n_rounds}")
    for name in sorted(os.listdir(OUT)) + ["../upload_pack_2026-10-21.zip"]:
        p = os.path.join(OUT, name)
        print(f"{os.path.getsize(p) / 1e6:7.1f} MB  {os.path.normpath(p)}")


if __name__ == "__main__":
    main()
