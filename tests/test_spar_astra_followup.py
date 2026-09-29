"""Local (no-API) tests for SPAR Pilot 4 — Astra provenance replication."""

import os, sys, unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from spar_dynamic import config as C
from spar_dynamic.astra_followup import build_trials, ASTRA_LABEL, JUDGE_SLUG


def _fake_sources():
    """Redesign: 20 astra + 20 fable (10/10 per architecture; qwen dropped) = 40 unique."""
    out = []
    counts = C.ASTRA_FOLLOWUP_SOURCE_COUNTS   # {"astra":10, "fable":10, "qwen":0}
    for arch in C.ARCHITECTURES:
        for ml in ("astra", "fable", "qwen"):
            for i in range(counts[ml]):
                base = {"astra": "HT", "fable": "HHTT", "qwen": "HTTH"}[ml] * 20
                s = list(base[:50])
                idx = (arch == "online") * 25 + i
                s[idx % 50] = "T" if s[idx % 50] == "H" else "H"
                out.append((ml, arch, f"{arch}/{ml}/{i:02d}", "".join(s)))
    return out


class TestBuildTrials(unittest.TestCase):
    def setUp(self):
        self.sources = _fake_sources()
        self.trials = build_trials(self.sources)

    def test_120_total(self):
        self.assertEqual(len(self.trials), 120)

    def test_40_unique_trajectories(self):
        unique = {t.source_trajectory_id for t in self.trials}
        self.assertEqual(len(unique), 40)

    def test_each_trajectory_shown_three_times(self):
        by_traj: dict = {}
        for t in self.trials:
            by_traj.setdefault(t.source_trajectory_id, []).append(t.stated_condition)
        for tid, stated in by_traj.items():
            self.assertEqual(sorted(stated), sorted(C.STATED_CONDITIONS),
                             f"{tid}: got {sorted(stated)}")

    def test_cell_counts_ten_each(self):
        c = Counter((t.true_source_identity, t.actual_architecture, t.stated_condition)
                    for t in self.trials)
        for identity in ("SELF", "OTHER"):
            for arch in C.ARCHITECTURES:
                for stated in C.STATED_CONDITIONS:
                    self.assertEqual(c[(identity, arch, stated)], 10,
                        f"cell {(identity, arch, stated)} = {c[(identity, arch, stated)]}")

    def test_self_is_astra(self):
        for t in self.trials:
            if t.true_source_identity == "SELF":
                self.assertEqual(t.source_model_label, ASTRA_LABEL)
            else:
                self.assertNotEqual(t.source_model_label, ASTRA_LABEL)

    def test_other_all_fable(self):
        # Redesign: OTHER pool is all fable (qwen dropped). 10 fable per arch × 3 conditions = 30 per arch.
        for arch in C.ARCHITECTURES:
            others = [t for t in self.trials
                      if t.true_source_identity == "OTHER" and t.actual_architecture == arch]
            self.assertEqual(len(others), 30)
            by_src = Counter(t.source_model_label for t in others)
            self.assertEqual(by_src["fable"], 30)
            self.assertEqual(by_src.get("qwen", 0), 0)

    def test_three_versions_not_adjacent(self):
        by_traj: dict = {}
        for t in self.trials:
            by_traj.setdefault(t.source_trajectory_id, []).append(t.trial_position)
        for tid, positions in by_traj.items():
            ps = sorted(positions)
            self.assertEqual(len(ps), 3)
            # smallest gap between consecutive versions >= 2
            gaps = [b - a for a, b in zip(ps, ps[1:])]
            self.assertGreaterEqual(min(gaps), 2,
                f"{tid} versions too close: positions {ps}")

    def test_trial_positions_0_to_119(self):
        positions = sorted(t.trial_position for t in self.trials)
        self.assertEqual(positions, list(range(120)))

    def test_deterministic(self):
        a = build_trials(self.sources)
        b = build_trials(self.sources)
        for x, y in zip(a, b):
            self.assertEqual(x.true_source_identity, y.true_source_identity)
            self.assertEqual(x.actual_architecture, y.actual_architecture)
            self.assertEqual(x.stated_condition, y.stated_condition)
            self.assertEqual(x.source_trajectory_id, y.source_trajectory_id)
            self.assertEqual(x.trial_position, y.trial_position)


class TestPromptSafety(unittest.TestCase):
    BANNED = ["astra", "fable", "qwen", "trajectory", "condition", "cell",
              "source_model", "actual_architecture", "true_source_identity",
              "prior study", "self-awareness"]

    def test_no_banned_in_prompts(self):
        for stated in C.STATED_CONDITIONS:
            p = C.astra_followup_prompt("H" * 25 + "T" * 25, stated)
            low = p.lower()
            for term in self.BANNED:
                self.assertNotIn(term, low, f"banned {term!r} in {stated} prompt")

    def test_correct_provenance_sentence(self):
        p_batch = C.astra_followup_prompt("HTHT" * 12 + "HT", "told_batch")
        p_online = C.astra_followup_prompt("HTHT" * 12 + "HT", "told_online")
        p_none = C.astra_followup_prompt("HTHT" * 12 + "HT", "no_provenance")
        self.assertIn(C.PROVENANCE_STATED_BATCH, p_batch)
        self.assertIn(C.PROVENANCE_STATED_ONLINE, p_online)
        self.assertNotIn(C.PROVENANCE_STATED_BATCH, p_online)
        self.assertNotIn(C.PROVENANCE_STATED_ONLINE, p_batch)
        # no-provenance prompt must not contain either provenance sentence
        self.assertNotIn(C.PROVENANCE_STATED_BATCH, p_none)
        self.assertNotIn(C.PROVENANCE_STATED_ONLINE, p_none)

    def test_judge_slug(self):
        self.assertEqual(JUDGE_SLUG, "openai/gpt-6-astra")


if __name__ == "__main__":
    unittest.main(verbosity=2)
