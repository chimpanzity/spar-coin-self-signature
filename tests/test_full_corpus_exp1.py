"""Section 22: pre-paid-run tests for FCE1."""

import csv, hashlib, json, os, sys, tempfile, unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

from spar_dynamic.full_corpus_exp1 import config as F
from spar_dynamic.full_corpus_exp1.pairs import (build_triplets, build_pairs,
                                                 build_trials, build_prompt,
                                                 prompt_hash)
from spar_dynamic.full_corpus_exp1.runner import parse_ab, worst_case_cost, CostLedger
from spar_dynamic.full_corpus_exp1.audit import sha256_text
from spar_dynamic.full_corpus_exp1.analysis import (
    producer_observer_contrasts, named_judge_target_matrix,
    target_complementarity, baseline_predictions_and_summary,
    bootstrap_intervals, join_trials_outcomes)


# -- Fixtures ----------------------------------------------------------------

def _canonical_corpus_rows():
    """Load the real corpus (history_conditioned only). Required for schedule tests."""
    corpus_csv = os.path.join(ROOT, "corpus", "trajectories.csv")
    rows = []
    with open(corpus_csv, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["method"] == F.SOURCE_METHOD:
                rows.append(r)
    return rows


class TestCorpusInput(unittest.TestCase):
    def setUp(self):
        self.rows = _canonical_corpus_rows()
    def test_sixty_history_conditioned(self):
        self.assertEqual(len(self.rows), 60)
    def test_three_models_ten_dev_ten_hold(self):
        c = Counter((r["model"], r["split"]) for r in self.rows)
        for m in F.JUDGE_LABELS:
            self.assertEqual(c[(m, "development")], 10, f"{m} dev")
            self.assertEqual(c[(m, "holdout")], 10, f"{m} hold")
    def test_sequences_are_100_HT(self):
        import re
        for r in self.rows:
            self.assertTrue(re.fullmatch(r"[HT]{100}", r["sequence"]))
    def test_requested_model_ids(self):
        for r in self.rows:
            want = F.JUDGE_BY_LABEL[r["model"]].slug
            self.assertEqual(r["requested_model_id"], want)


class TestScheduleCounts(unittest.TestCase):
    def setUp(self):
        self.rows = _canonical_corpus_rows()
        self.triplets = build_triplets(self.rows)
        self.pairs = build_pairs(self.triplets, self.rows)
        self.trials = build_trials(self.pairs)
    def test_20_triplets(self):
        self.assertEqual(len(self.triplets), 20)
        self.assertEqual(sum(1 for t in self.triplets if t.split == "development"), 10)
        self.assertEqual(sum(1 for t in self.triplets if t.split == "holdout"), 10)
    def test_60_pairs(self):
        self.assertEqual(len(self.pairs), 60)
        self.assertEqual(sum(1 for p in self.pairs if p.split == "development"), 30)
        self.assertEqual(sum(1 for p in self.pairs if p.split == "holdout"), 30)
    def test_480_trials(self):
        self.assertEqual(len(self.trials), 480)
        self.assertEqual(sum(1 for t in self.trials if t.split == "development"), 240)
        self.assertEqual(sum(1 for t in self.trials if t.split == "holdout"), 240)
    def test_counts_by_judge(self):
        c = Counter(t.judge_label for t in self.trials)
        for j in F.JUDGE_LABELS:
            self.assertEqual(c[j], 160, f"judge {j}")
        # 120 named, 40 SELF each
        for j in F.JUDGE_LABELS:
            named = sum(1 for t in self.trials if t.judge_label == j and t.wording_condition == "NAMED")
            self_c = sum(1 for t in self.trials if t.judge_label == j and t.wording_condition == "SELF")
            self.assertEqual(named, 120)
            self.assertEqual(self_c, 40)
    def test_360_named_120_self(self):
        c = Counter(t.wording_condition for t in self.trials)
        self.assertEqual(c["NAMED"], 360)
        self.assertEqual(c["SELF"], 120)
    def test_each_trajectory_in_two_pairs(self):
        used = Counter()
        for p in self.pairs:
            used[p.sequence_A_id] += 1
            used[p.sequence_B_id] += 1
        for tid, n in used.items():
            self.assertEqual(n, 2, f"{tid} used {n} times")
    def test_each_pair_six_named_two_self(self):
        for p in self.pairs:
            trials_for_p = [t for t in self.trials if t.pair_id == p.pair_id]
            named = [t for t in trials_for_p if t.wording_condition == "NAMED"]
            self_c = [t for t in trials_for_p if t.wording_condition == "SELF"]
            self.assertEqual(len(named), 6, p.pair_id)
            self.assertEqual(len(self_c), 2, p.pair_id)
    def test_60_unique_source_pairs(self):
        pair_sigs = {tuple(sorted([p.sequence_A_id, p.sequence_B_id])) for p in self.pairs}
        self.assertEqual(len(pair_sigs), 60)
    def test_120_target_items(self):
        items = {t.target_item_id for t in self.trials}
        self.assertEqual(len(items), 120)
    def test_480_unique_trial_ids(self):
        ids = [t.trial_id for t in self.trials]
        self.assertEqual(len(ids), len(set(ids)))

    def test_ab_balance_within_cells(self):
        """For each (split, source_pair_type) 5 pairs put alpha-first in A and 5 in B."""
        for sp in ("development", "holdout"):
            for pt in ("AF", "AM", "FM"):
                subset = [p for p in self.pairs if p.split == sp and p.source_pair_type == pt]
                self.assertEqual(len(subset), 10, f"{sp}/{pt}")
                first_letter = pt[0]   # 'A','A','F'
                first_label = {"A": "astra", "F": "fable"}[first_letter]
                in_A = sum(1 for p in subset if p.source_label_A == first_label)
                self.assertEqual(in_A, 5, f"{sp}/{pt} first-in-A balance")

    def test_self_trial_only_for_target_producer(self):
        for t in self.trials:
            if t.wording_condition == "SELF":
                self.assertEqual(t.judge_label, t.target_label)

    def test_named_prompt_identical_across_judges(self):
        """For a given (pair, target) the NAMED prompt string is byte-identical across judges."""
        by_item = {}
        for t in self.trials:
            if t.wording_condition != "NAMED": continue
            key = (t.pair_id, t.target_label)
            by_item.setdefault(key, []).append(build_prompt(t))
        for k, prompts in by_item.items():
            hashes = {hashlib.sha256(p.encode()).hexdigest() for p in prompts}
            self.assertEqual(len(hashes), 1, f"NAMED prompt varies across judges for {k}")

    def test_named_self_prompts_differ_only_in_target_name(self):
        """For judge==target NAMED and SELF: differ only in the target-name substitution."""
        for t in self.trials:
            if t.wording_condition != "NAMED": continue
            if t.judge_label != t.target_label: continue
            # find the matching SELF trial
            self_trial = next((s for s in self.trials
                               if s.pair_id == t.pair_id
                               and s.target_label == t.target_label
                               and s.wording_condition == "SELF"), None)
            self.assertIsNotNone(self_trial)
            p_named = build_prompt(t)
            p_self = build_prompt(self_trial)
            name = F.JUDGE_BY_LABEL[t.target_label].display_name
            substituted = p_named.replace(name, "the same underlying model as you")
            self.assertEqual(p_self.count(name), 0,
                             f"SELF prompt should not mention {name}")
            # NAMED replaces into SELF only via the target-name substitution
            # and no other change
            self.assertEqual(substituted, p_self,
                             f"NAMED vs SELF differ by more than target-name substitution")


class TestParser(unittest.TestCase):
    def test_accepts_A_B(self):
        self.assertEqual(parse_ab("A"), "A")
        self.assertEqual(parse_ab("b"), "B")
        self.assertEqual(parse_ab("  A \n"), "A")
    def test_rejects_everything_else(self):
        for bad in ("SELF", "OTHER", "", "A.", "The answer is A", "AA", "A\nreasoning",
                    "{\"answer\":\"A\"}", "Letter A"):
            self.assertIsNone(parse_ab(bad), f"should reject {bad!r}")


class TestLedger(unittest.TestCase):
    def test_cap_blocks_dispatch(self):
        L = CostLedger(cap_usd=1.0)
        self.assertTrue(L.reserve(0.5))
        self.assertTrue(L.reserve(0.4))
        self.assertFalse(L.reserve(0.2))  # 0.5+0.4+0.2=1.1 > 1.0
    def test_commit_frees_reservation(self):
        L = CostLedger(cap_usd=1.0)
        L.reserve(0.5)
        L.commit(0.1, reservation=0.5)
        self.assertAlmostEqual(L.spent_usd, 0.1)
        self.assertAlmostEqual(L.reserved_usd, 0.0)


class TestWorstCaseCost(unittest.TestCase):
    def test_scales_with_max_tokens(self):
        price = {"prompt": 1e-6, "completion": 1e-6}
        c1 = worst_case_cost("x" * 4000, 4096, price)
        c2 = worst_case_cost("x" * 4000, 8192, price)
        self.assertGreater(c2, c1)


class TestAnalysisOnSyntheticData(unittest.TestCase):
    """Section 22: fake known-response datasets give expected S/O/F and
    target-complementarity results."""
    def setUp(self):
        self.rows = _canonical_corpus_rows()
        self.triplets = build_triplets(self.rows)
        self.pairs = build_pairs(self.triplets, self.rows)
        self.trials = build_trials(self.pairs)

    def _synthesize_outcomes(self, judge_strength: dict, self_boost: dict = None):
        """judge_strength[judge][target] -> prob correct on NAMED; self_boost[judge] added for SELF."""
        import random
        rng = random.Random(1)
        outcomes = {}
        for t in self.trials:
            p = judge_strength[t.judge_label][t.target_label]
            if t.wording_condition == "SELF" and self_boost:
                p = min(1.0, p + self_boost.get(t.judge_label, 0.0))
            correct = rng.random() < p
            answer = t.correct_answer if correct else ("A" if t.correct_answer == "B" else "B")
            outcomes[t.trial_id] = {
                "status": "ok", "visible_answer": answer,
                "correct": (answer == t.correct_answer),
                "first_attempt_valid": True, "attempts": 1,
                "total_cost_usd": 0.0, "returned_model_id": "", "provider": "",
            }
        return outcomes

    def test_SOF_decomposition_algebra(self):
        """For complete items on the same scope: S = O + F always holds."""
        strength = {j: {t: 0.6 for t in F.JUDGE_LABELS} for j in F.JUDGE_LABELS}
        outcomes = self._synthesize_outcomes(strength, self_boost={j: 0.1 for j in F.JUDGE_LABELS})
        joined = join_trials_outcomes(self.trials, outcomes)
        poc = producer_observer_contrasts(joined)
        for r in poc:
            if r["S"] is None or r["O"] is None or r["F"] is None: continue
            # S should equal O + F up to float rounding
            self.assertAlmostEqual(r["S"], r["O"] + r["F"], places=3,
                                   msg=f"{r['split']}/{r['target']}: S={r['S']} O={r['O']} F={r['F']}")

    def test_target_complementarity_perfect_judge(self):
        """A perfect judge always answers A for target_A and B for target_B => complementarity = 1.0"""
        strength = {j: {t: 1.0 for t in F.JUDGE_LABELS} for j in F.JUDGE_LABELS}
        outcomes = self._synthesize_outcomes(strength)
        joined = join_trials_outcomes(self.trials, outcomes)
        comp = target_complementarity(joined)
        for r in comp:
            if r["n_pairs_complete"] > 0:
                self.assertEqual(r["pct_complementary"], 1.0,
                                 f"{r['split']}/{r['judge']} should be 1.0")


class TestBaselineBasics(unittest.TestCase):
    def setUp(self):
        self.rows = _canonical_corpus_rows()
        self.triplets = build_triplets(self.rows)
        self.pairs = build_pairs(self.triplets, self.rows)
        self.trials = build_trials(self.pairs)
    def test_baseline_rows_count(self):
        pred, summ = baseline_predictions_and_summary(self.trials, self.rows)
        # 60 pairs * 2 target versions = 120 holdout + dev items per baseline... but
        # we deduplicate by (pair_id, target_label). 60 holdout items + 60 dev items
        # per baseline = 120 per baseline. 2 baselines = 240 rows.
        self.assertEqual(len(pred), 240, f"got {len(pred)}")
        self.assertEqual(len(summ), 4, f"got {len(summ)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
