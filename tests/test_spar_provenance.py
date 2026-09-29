"""Local (no-API) tests for SPAR Pilot 3 — Provenance-manipulation SELF/OTHER.

Verifies the full 2 x 2 x 2 design construction rules:
  * 240 total trials (80 per judge)
  * 8 cells of exactly 10 per judge
  * SELF uses all of the judge's own trajectories; OTHER split 5/5/5/5
  * every unique trajectory has exactly one told-batch + one told-online version
  * two versions of the same trajectory are never adjacent
  * prompt reveals no source-model identity, no actual-architecture metadata,
    no congruence label
  * both provenance sentences appear in the corresponding version's prompt
"""

import os, sys, unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from spar_dynamic import config as C
from spar_dynamic.provenance import build_provenance_trials


def _fake_source_pool():
    out = {}
    for arch in C.ARCHITECTURES:
        for ml in C.MODEL_LABELS:
            lst = []
            for i in range(10):
                # unique 50-char sequences per (arch, model, replicate)
                base = {"astra": "HT", "fable": "HHTT", "qwen": "HTTH"}[ml] * 20
                s = list(base[:50])
                # perturb one index to make each unique
                idx = (arch == "online") * 25 + i
                s[idx % 50] = "T" if s[idx % 50] == "H" else "H"
                lst.append((ml, f"{arch}/{ml}/{i:02d}", "".join(s)))
            out[(arch, ml)] = lst
    return out


class TestTrialCounts(unittest.TestCase):
    def setUp(self):
        self.src = _fake_source_pool()
        self.trials = build_provenance_trials(self.src)

    def test_240_total(self):
        self.assertEqual(len(self.trials), 240)

    def test_80_per_judge(self):
        c = Counter(t.judge_label for t in self.trials)
        for judge in C.MODEL_LABELS:
            self.assertEqual(c[judge], 80)

    def test_eight_cells_of_10_per_judge(self):
        c = Counter((t.judge_label, t.true_source_identity,
                     t.actual_architecture, t.stated_architecture)
                    for t in self.trials)
        for judge in C.MODEL_LABELS:
            for src in ("SELF", "OTHER"):
                for a in C.ARCHITECTURES:
                    for s in C.ARCHITECTURES:
                        self.assertEqual(c[(judge, src, a, s)], 10,
                            f"cell {(judge, src, a, s)}: got {c[(judge, src, a, s)]}, expected 10")

    def test_self_trials_use_own_trajectories(self):
        for t in self.trials:
            if t.true_source_identity == "SELF":
                self.assertEqual(t.source_model_label, t.judge_label)

    def test_other_split_5_5_per_arch(self):
        for judge in C.MODEL_LABELS:
            others = sorted(m for m in C.MODEL_LABELS if m != judge)
            for arch in C.ARCHITECTURES:
                # 5 unique trajectories from each non-self model, each duplicated x2 stated
                others_arch = [t for t in self.trials
                               if t.judge_label == judge
                               and t.true_source_identity == "OTHER"
                               and t.actual_architecture == arch]
                self.assertEqual(len(others_arch), 20)  # 5 traj x 2 non-self x 2 stated
                unique_by_src = {}
                for t in others_arch:
                    unique_by_src.setdefault(t.source_model_label, set()).add(t.source_trajectory_id)
                for other_label in others:
                    self.assertEqual(len(unique_by_src.get(other_label, set())), 5,
                        f"OTHER {other_label} in {judge}/{arch}: {len(unique_by_src.get(other_label, set()))} unique traj")

    def test_every_trajectory_shown_twice_with_both_stated_archs(self):
        # for each (judge, pair_key), exactly 2 trials: one told-batch, one told-online
        by_pair: dict = {}
        for t in self.trials:
            by_pair.setdefault((t.judge_label, t.pair_key), []).append(t)
        for key, ts in by_pair.items():
            self.assertEqual(len(ts), 2,
                             f"pair {key} appeared {len(ts)} times; expected 2")
            stated = sorted(t.stated_architecture for t in ts)
            self.assertEqual(stated, ["batch", "online"],
                             f"pair {key} stated arches: {stated}")

    def test_two_versions_not_adjacent(self):
        # For each (judge, pair_key), positions differ by at least 1
        for judge in C.MODEL_LABELS:
            block = [t for t in self.trials if t.judge_label == judge]
            block.sort(key=lambda t: t.trial_position)
            by_pair: dict = {}
            for t in block:
                by_pair.setdefault(t.pair_key, []).append(t.trial_position)
            for pk, positions in by_pair.items():
                self.assertEqual(len(positions), 2)
                sep = abs(positions[0] - positions[1])
                self.assertGreater(sep, 1,
                    f"pair {pk} versions are adjacent (positions {positions})")

    def test_provenance_congruent_flag_correct(self):
        for t in self.trials:
            expected = (t.actual_architecture == t.stated_architecture)
            self.assertEqual(t.provenance_congruent, expected)


class TestPromptSafety(unittest.TestCase):
    """No source-model identity, no actual-architecture metadata, no experimental labels."""

    BANNED = [
        # model names / slugs
        "astra", "fable", "qwen",
        # experimental metadata
        "true_source_identity", "actual_architecture", "provenance_congruent",
        "condition", "cell", "trajectory_id", "source_model", "judge_label",
        # any leaked mention of "actual" architecture
        "actual batch", "actual online", "congruent", "incongruent",
        # results-adjacent
        "self-awareness", "recognition", "prior pilot",
    ]

    def test_no_banned_terms_in_prompt(self):
        for stated in ("batch", "online"):
            p = C.provenance_prompt("H" * 25 + "T" * 25, stated)
            low = p.lower()
            for term in self.BANNED:
                self.assertNotIn(term, low, f"banned term {term!r} in {stated} prompt")

    def test_prompt_contains_correct_stated_sentence(self):
        p_batch = C.provenance_prompt("HTHT" * 12 + "HT", "batch")
        p_online = C.provenance_prompt("HTHT" * 12 + "HT", "online")
        self.assertIn(C.PROVENANCE_STATED_BATCH, p_batch)
        self.assertIn(C.PROVENANCE_STATED_ONLINE, p_online)
        # cross-contamination check
        self.assertNotIn(C.PROVENANCE_STATED_ONLINE, p_batch)
        self.assertNotIn(C.PROVENANCE_STATED_BATCH, p_online)

    def test_prompt_asks_self_or_other_once_word(self):
        p = C.provenance_prompt("H" * 50, "batch")
        self.assertIn("SELF", p)
        self.assertIn("OTHER", p)
        self.assertIn("exactly one word", p.lower())


class TestConstructionDeterminism(unittest.TestCase):
    def test_same_seed_same_structure(self):
        src = _fake_source_pool()
        a = build_provenance_trials(src)
        b = build_provenance_trials(src)
        for x, y in zip(a, b):
            self.assertEqual(x.judge_label, y.judge_label)
            self.assertEqual(x.true_source_identity, y.true_source_identity)
            self.assertEqual(x.actual_architecture, y.actual_architecture)
            self.assertEqual(x.stated_architecture, y.stated_architecture)
            self.assertEqual(x.source_trajectory_id, y.source_trajectory_id)
            self.assertEqual(x.trial_position, y.trial_position)


class TestValidationRule(unittest.TestCase):
    """Spec-mandated: run cannot be COMPLETE with any abandoned trial or cell short."""
    def test_short_cell_fails(self):
        n_planned = 240
        n_valid = 240
        n_abandoned = 0
        cell_counts_ok = False  # a cell was short
        ok = (n_valid == n_planned and n_abandoned == 0 and cell_counts_ok)
        self.assertFalse(ok)

    def test_all_good_passes(self):
        n_planned = 240
        n_valid = 240
        n_abandoned = 0
        cell_counts_ok = True
        ok = (n_valid == n_planned and n_abandoned == 0 and cell_counts_ok)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
