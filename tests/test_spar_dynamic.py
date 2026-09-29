"""Local (no-API) tests for the SPAR Dynamic Behavioral Self-Signature Pilot."""

import json, os, random, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from spar_dynamic import config as C
from spar_dynamic.api import (parse_batch, parse_online,
                              parse_judgment_json, parse_judgment_text)
from spar_dynamic.trials import build_all_trials, build_trials_for_judge_arch
from spar_dynamic.analyze import (sequence_features, nearest_centroid_loo,
                                   summarize_judgment,
                                   feature_distance_baseline, FEATURE_NAMES)


# ---------- parsers --------------------------------------------------------
class TestParsers(unittest.TestCase):
    def test_batch_exact_50(self):
        self.assertEqual(parse_batch("H" * 50), "H" * 50)
        self.assertEqual(parse_batch("t" * 50), "T" * 50)
    def test_batch_strips_whitespace(self):
        s = "  " + "HT" * 25 + "  \n"
        self.assertEqual(parse_batch(s), "HT" * 25)
    def test_batch_rejects_wrong_len(self):
        self.assertIsNone(parse_batch("H" * 49))
        self.assertIsNone(parse_batch("H" * 51))
    def test_batch_rejects_explanation(self):
        self.assertIsNone(parse_batch("Here are 50 flips: " + "HT" * 25))

    def test_online_strict(self):
        self.assertEqual(parse_online("H"), "H")
        self.assertEqual(parse_online("t"), "T")
        self.assertEqual(parse_online("  T\n"), "T")
    def test_online_rejects_more_than_one_char(self):
        self.assertIsNone(parse_online("HT"))
        self.assertIsNone(parse_online("H."))
        self.assertIsNone(parse_online("I choose H"))

    def test_judgment_json_ok(self):
        self.assertEqual(parse_judgment_json('{"judgment":"SAME"}'), "SAME")
        self.assertEqual(parse_judgment_json('{"judgment": "DIFFERENT"}'), "DIFFERENT")
    def test_judgment_json_none(self):
        self.assertIsNone(parse_judgment_json("SAME"))
        self.assertIsNone(parse_judgment_json(""))
    def test_judgment_text_ok(self):
        self.assertEqual(parse_judgment_text("SAME"), "SAME")
        self.assertEqual(parse_judgment_text("different"), "DIFFERENT")
        self.assertEqual(parse_judgment_text("I think they are SAME"), "SAME")


# ---------- online history prompt shape ------------------------------------
class TestOnlinePrompt(unittest.TestCase):
    def test_trial_1_no_history(self):
        p = C.online_trial_prompt("")
        self.assertEqual(p, C.ONLINE_TRIAL1_PROMPT)
        self.assertNotIn("Previous flips", p)
    def test_trial_2_shows_one(self):
        p = C.online_trial_prompt("H")
        self.assertIn("Previous flips (oldest → most recent):", p)
        self.assertIn("\nH\n", p)
    def test_trial_50_shows_49(self):
        history = "HT" * 24 + "H"   # 49 chars
        p = C.online_trial_prompt(history)
        self.assertIn(history, p)
        # exactly one occurrence of the raw history block
        self.assertEqual(p.count(history), 1)
    def test_ordering_oldest_to_most_recent(self):
        history = "HHHHTTTT"   # 8 chars, oldest H, newest T
        p = C.online_trial_prompt(history)
        idx = p.index(history)
        self.assertEqual(p[idx], "H")
        self.assertEqual(p[idx + len(history) - 1], "T")
    def test_no_history_truncation(self):
        history = "HT" * 50   # 100 chars, longer than any single trial's history
        p = C.online_trial_prompt(history)
        self.assertIn(history, p)
        # only ONE full-history block; no summary/count
        self.assertNotIn("count", p.lower())
        self.assertNotIn("total", p.lower())
        self.assertNotIn("switch", p.lower())
        self.assertNotIn("runs", p.lower())


# ---------- trial construction ---------------------------------------------
def _fake_source_pool():
    """Return dict[(arch, model_label)] -> list of (label, traj_id, sequence).
    3 models x 2 architectures x 10 trajectories each; sequences are dummies."""
    out = {}
    for arch in C.ARCHITECTURES:
        for ml in C.MODEL_LABELS:
            lst = []
            for i in range(C.TRAJECTORIES_PER_MODEL_ARCH):
                # dummy 50-char sequence: alternating with an offset per model
                if ml == "astra":
                    seq = ("HT" * 25)[:50]
                elif ml == "fable":
                    seq = ("HHTT" * 13)[:50]
                else:  # qwen
                    seq = ("HTTH" * 13)[:50]
                tid = f"{arch}/{ml}/{i:02d}"
                lst.append((ml, tid, seq))
            out[(arch, ml)] = lst
    return out


class TestTrialsShape(unittest.TestCase):
    def setUp(self):
        self.source = _fake_source_pool()
        self.trials = build_all_trials(self.source)

    def test_total_count_144(self):
        self.assertEqual(len(self.trials), 144)

    def test_per_judge_arch_24(self):
        from collections import Counter
        by = Counter((t.judge_label, t.architecture) for t in self.trials)
        for judge in C.MODEL_LABELS:
            for arch in C.ARCHITECTURES:
                self.assertEqual(by[(judge, arch)], 24)

    def test_per_cell_counts_6(self):
        from collections import Counter
        by = Counter((t.judge_label, t.architecture, t.cell) for t in self.trials)
        for judge in C.MODEL_LABELS:
            for arch in C.ARCHITECTURES:
                for cell in C.JUDGMENT_CELLS:
                    self.assertEqual(by[(judge, arch, cell)], 6,
                        f"cell {cell} count for judge={judge} arch={arch} is not 6")

    def test_correct_answer_matches_cell(self):
        for t in self.trials:
            if t.cell in ("A", "C"):
                self.assertEqual(t.correct_answer, "SAME")
            else:
                self.assertEqual(t.correct_answer, "DIFFERENT")

    def test_no_architecture_mixing_within_pair(self):
        # both strings' trajectories should carry the same architecture prefix.
        for t in self.trials:
            self.assertTrue(t.trajectory_id_1.startswith(t.architecture + "/"),
                            f"trial {t.trial_id}: string1 arch mismatch")
            self.assertTrue(t.trajectory_id_2.startswith(t.architecture + "/"),
                            f"trial {t.trial_id}: string2 arch mismatch")

    def test_cell_A_uses_own_only(self):
        for t in self.trials:
            if t.cell == "A":
                self.assertEqual(t.source_model_1, t.judge_label)
                self.assertEqual(t.source_model_2, t.judge_label)

    def test_cell_B_one_own_one_other(self):
        for t in self.trials:
            if t.cell == "B":
                self.assertIn(t.judge_label, (t.source_model_1, t.source_model_2))
                self.assertNotEqual(t.source_model_1, t.source_model_2)

    def test_cell_C_both_non_self_same(self):
        for t in self.trials:
            if t.cell == "C":
                self.assertNotEqual(t.source_model_1, t.judge_label)
                self.assertEqual(t.source_model_1, t.source_model_2)

    def test_cell_D_two_different_non_self(self):
        for t in self.trials:
            if t.cell == "D":
                self.assertNotIn(t.judge_label, (t.source_model_1, t.source_model_2))
                self.assertNotEqual(t.source_model_1, t.source_model_2)

    def test_no_self_pair(self):
        for t in self.trials:
            self.assertNotEqual(t.trajectory_id_1, t.trajectory_id_2)

    def test_no_duplicate_unordered_pair_within_block(self):
        from collections import defaultdict
        by_block = defaultdict(set)
        for t in self.trials:
            uk = tuple(sorted([t.trajectory_id_1, t.trajectory_id_2]))
            key = (t.judge_label, t.architecture)
            self.assertNotIn(uk, by_block[key],
                             f"duplicate pair within block {key}: {uk}")
            by_block[key].add(uk)

    def test_prompt_never_reveals_source_labels(self):
        # Simulate rendering the judgment prompt and confirm no source metadata
        # appears in the model-facing text.
        from spar_dynamic.judgment import _judgment_prompt
        for t in self.trials:
            for mode in ("json_schema", "chat"):
                p = _judgment_prompt(t, mode)
                for banned in ("astra", "fable", "qwen", "cell", "correct_answer",
                               "trajectory_id", "source_model", "judge_label",
                               "architecture"):
                    self.assertNotIn(banned, p.lower(),
                                     f"leaked {banned!r} into prompt for trial {t.trial_id}")

    def test_b_split_across_both_others(self):
        # for each judge x arch, the B cell's non-self model appears at both possible values
        from collections import defaultdict
        by = defaultdict(list)
        for t in self.trials:
            if t.cell == "B":
                other = (t.source_model_2 if t.source_model_1 == t.judge_label
                         else t.source_model_1)
                by[(t.judge_label, t.architecture)].append(other)
        for (judge, arch), lst in by.items():
            others = set(lst)
            self.assertEqual(len(others), 2,
                             f"B cell for {judge}/{arch} did not use both non-self models")


# ---------- analysis math --------------------------------------------------
class TestSequenceFeatures(unittest.TestCase):
    def test_all_H(self):
        f = sequence_features("H" * 50)
        self.assertEqual(f["prop_H"], 1.0)
        self.assertEqual(f["switch_rate"], 0.0)
        self.assertEqual(f["longest_run"], 50.0)

    def test_perfect_alternation(self):
        f = sequence_features("HT" * 25)
        self.assertAlmostEqual(f["prop_H"], 0.5)
        self.assertAlmostEqual(f["switch_rate"], 1.0)
        self.assertEqual(f["longest_run"], 1.0)


class TestClassifier(unittest.TestCase):
    def test_perfectly_separable(self):
        feats = {"astra": [{k: 0.1 for k in FEATURE_NAMES} for _ in range(4)],
                 "fable": [{k: 0.9 for k in FEATURE_NAMES} for _ in range(4)],
                 "qwen":  [{k: 0.5 for k in FEATURE_NAMES} for _ in range(4)]}
        r = nearest_centroid_loo(feats)
        self.assertAlmostEqual(r["accuracy"], 1.0)


class TestSummarize(unittest.TestCase):
    def test_summary_shape(self):
        # 24 trials for one (judge, arch), all correct -> accuracy 1.0
        recs = []
        for cell in ("A", "B", "C", "D"):
            for i in range(6):
                recs.append({"trial_id": f"{cell}-{i}", "judge_label": "astra",
                             "architecture": "batch", "cell": cell,
                             "correct_answer": "SAME" if cell in ("A","C") else "DIFFERENT",
                             "parsed_judgment": "SAME" if cell in ("A","C") else "DIFFERENT",
                             "correct": True})
        s = summarize_judgment(recs)
        ja = [row for row in s["per_judge_arch"]
              if row["judge"]=="astra" and row["architecture"]=="batch"][0]
        self.assertAlmostEqual(ja["accuracy_A"], 1.0)
        self.assertAlmostEqual(ja["total_accuracy"], 1.0)
        self.assertAlmostEqual(ja["self_advantage"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
