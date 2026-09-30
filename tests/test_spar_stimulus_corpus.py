"""Local (no-API) tests for Pilot 5 — SPAR Stimulus Corpus."""

import json, os, sys, tempfile, unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from spar_dynamic import config as C
from spar_dynamic.api import parse_batch, parse_online, load_prior_spend_from_jsonl
from spar_dynamic.stimulus_corpus import (
    rebuild_trajectory_state_from_attempts,
    generate_history_conditioned_trajectory,
    generate_independent_calls_trajectory,
)
from spar_dynamic.orchestrator_stimulus_corpus import build_execution_schedule


# ---------- prompt structure -----------------------------------------------

class TestPrompts(unittest.TestCase):
    def test_batch_prompt_requests_100(self):
        self.assertIn("100 flips", C.CORPUS_BATCH_PROMPT)
        self.assertIn("exactly 100 outcomes", C.CORPUS_BATCH_PROMPT)
        self.assertIn("only H and T", C.CORPUS_BATCH_PROMPT)

    def test_history_prompt_grows_with_history(self):
        self.assertEqual(C.CORPUS_HISTORY_TRIAL1_PROMPT, C.ONLINE_TRIAL1_PROMPT)
        p1 = C.corpus_history_trial_prompt("")
        p2 = C.corpus_history_trial_prompt("HTHT")
        self.assertNotIn("Previous flips", p1)
        self.assertIn("Previous flips", p2)
        self.assertIn("HTHT", p2)

    def test_history_prompt_history_before_property(self):
        history = "HHTHT" * 19   # length 95, so trial 96
        p = C.corpus_history_trial_prompt(history)
        # the exact history should appear once, no truncation, no summary stats
        self.assertEqual(p.count(history), 1)
        for banned in ["count", "total", "so far", "summary",
                       "switch rate", "runs", "proportion", "biased"]:
            self.assertNotIn(banned, p.lower())

    def test_independent_calls_prompt_is_fixed(self):
        # every call must receive the same prompt — the constant is the prompt itself
        self.assertIsInstance(C.CORPUS_INDEPENDENT_CALLS_PROMPT, str)
        self.assertIn("Simulate one fair coin flip", C.CORPUS_INDEPENDENT_CALLS_PROMPT)
        self.assertIn("exactly one character", C.CORPUS_INDEPENDENT_CALLS_PROMPT)
        # No mention of previous flips, no history block
        for term in ["previous", "history", "prior flips", "trial", "so far"]:
            self.assertNotIn(term, C.CORPUS_INDEPENDENT_CALLS_PROMPT.lower())


# ---------- parser --------------------------------------------------------

class TestParser(unittest.TestCase):
    def test_batch_100_strict(self):
        s = "H" * 50 + "T" * 50
        self.assertEqual(parse_batch(s, length=100), s)
        self.assertIsNone(parse_batch("H" * 99, length=100))
        self.assertIsNone(parse_batch("H" * 101, length=100))
    def test_batch_100_whitespace_ok(self):
        s = "\n  " + ("HT" * 50) + "\n"
        self.assertEqual(parse_batch(s, length=100), "HT" * 50)
    def test_batch_50_still_works(self):
        s = "H" * 50
        self.assertEqual(parse_batch(s), s)   # default length=50
        self.assertEqual(parse_batch(s, length=50), s)
    def test_batch_rejects_prose(self):
        self.assertIsNone(parse_batch("Here are 100 flips: " + "HT" * 50, length=100))


# ---------- execution schedule --------------------------------------------

class TestSchedule(unittest.TestCase):
    def setUp(self):
        self.schedule = build_execution_schedule()

    def test_schedule_size_matches_config(self):
        expected = (len(C.CORPUS_MODELS) * len(C.CORPUS_GENERATION_METHODS)
                    * C.CORPUS_TRAJECTORIES_PER_CELL)
        self.assertEqual(len(self.schedule), expected)

    def test_cell_balance(self):
        from collections import Counter
        c = Counter((s["model_label"], s["method"]) for s in self.schedule)
        for m in C.CORPUS_MODEL_LABELS:
            for meth in C.CORPUS_GENERATION_METHODS:
                self.assertEqual(c[(m, meth)], C.CORPUS_TRAJECTORIES_PER_CELL,
                                 f"{m}/{meth} = {c[(m, meth)]}")

    def test_trajectory_ids_unique(self):
        ids = [s["trajectory_id"] for s in self.schedule]
        self.assertEqual(len(ids), len(set(ids)))

    def test_execution_order_is_permutation(self):
        orders = sorted(s["execution_order"] for s in self.schedule)
        self.assertEqual(orders, list(range(len(self.schedule))))

    def test_shuffled_not_blocked_by_model(self):
        # ensure not all first 10 entries are the same model
        first_10_models = {s["model_label"] for s in self.schedule[:10]}
        # extremely unlikely to be same model given uniform shuffle, but not impossible
        # so we just check for shuffle diversity somewhere in the manifest
        first_30_models = {s["model_label"] for s in self.schedule[:30]}
        self.assertGreater(len(first_30_models), 1)


# ---------- mocked-client trajectory tests --------------------------------

class MockClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self._idx = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.prompts_seen = []
    def _create(self, model, messages, temperature=0.0, max_tokens=1024, **kwargs):
        prompt = messages[0]["content"]
        self.prompts_seen.append(prompt)
        text = self._responses[self._idx]; self._idx += 1
        choice = SimpleNamespace(message=SimpleNamespace(content=text), finish_reason="stop")
        usage = SimpleNamespace(prompt_tokens=len(prompt.split()), completion_tokens=1,
                                total_tokens=len(prompt.split())+1,
                                completion_tokens_details=SimpleNamespace(reasoning_tokens=0))
        return SimpleNamespace(choices=[choice], model=model, id="mock",
                                provider="mock", usage=usage)


class TestMockedHistoryTrajectory(unittest.TestCase):
    def test_history_accumulates_and_prompt_grows(self):
        from spar_dynamic.api import CostAccountant
        scripted = ["H", "T", "H", "H", "T"]
        client = MockClient(scripted)
        acc = CostAccountant(client)
        acc.prices = {"anthropic/claude-fable-5.1": (0.0, 0.0)}   # skip real snapshot
        m = C.CORPUS_MODEL_BY_LABEL["fable"]
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "raw.jsonl")
            # override sequence length via monkey-patch for this test
            orig_len = C.CORPUS_SEQUENCE_LENGTH
            C.CORPUS_SEQUENCE_LENGTH = 5
            try:
                rec = generate_history_conditioned_trajectory(
                    client, acc,
                    run_id="test", trajectory_id="fable_history_conditioned_00",
                    model=m, replicate_index=0, raw_jsonl_path=raw)
            finally:
                C.CORPUS_SEQUENCE_LENGTH = orig_len
        self.assertTrue(rec.valid)
        self.assertEqual(rec.parsed_sequence, "HTHHT")
        # trial 1 prompt has empty history
        self.assertNotIn("Previous flips", client.prompts_seen[0])
        # trial 2 prompt has 1-char history
        self.assertIn("Previous flips", client.prompts_seen[1])
        self.assertIn("\nH\n", client.prompts_seen[1])
        # trial 5 prompt has 4-char history
        self.assertIn("HTHH", client.prompts_seen[4])


class TestMockedIndependentTrajectory(unittest.TestCase):
    def test_all_prompts_identical(self):
        from spar_dynamic.api import CostAccountant
        scripted = ["H"] * 5
        client = MockClient(scripted)
        acc = CostAccountant(client)
        acc.prices = {"xiaomi/mimo-v2.6-pro": (0.0, 0.0)}
        m = C.CORPUS_MODEL_BY_LABEL["mimo"]
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "raw.jsonl")
            orig_len = C.CORPUS_SEQUENCE_LENGTH
            C.CORPUS_SEQUENCE_LENGTH = 5
            try:
                rec = generate_independent_calls_trajectory(
                    client, acc,
                    run_id="test", trajectory_id="mimo_independent_calls_00",
                    model=m, replicate_index=0, raw_jsonl_path=raw)
            finally:
                C.CORPUS_SEQUENCE_LENGTH = orig_len
        self.assertTrue(rec.valid)
        self.assertEqual(rec.parsed_sequence, "HHHHH")
        # ALL prompts must be identical
        self.assertEqual(len(set(client.prompts_seen)), 1)
        # And that identical prompt must be CORPUS_INDEPENDENT_CALLS_PROMPT
        self.assertEqual(client.prompts_seen[0], C.CORPUS_INDEPENDENT_CALLS_PROMPT)
        # No history anywhere
        for p in client.prompts_seen:
            for term in ["previous", "history", "prior"]:
                self.assertNotIn(term, p.lower())


# ---------- rebuild-state resume test -------------------------------------

class TestResume(unittest.TestCase):
    def test_rebuild_from_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "raw.jsonl")
            # simulate an interrupted history_conditioned trajectory: 3 valid + 1 invalid
            entries = [
                {"trajectory_id": "T", "trial_index": 1, "attempt_index": 1,
                 "parsed_flip": "H", "valid": True, "cost_usd": 0.0, "kind": "x"},
                {"trajectory_id": "T", "trial_index": 2, "attempt_index": 1,
                 "parsed_flip": "T", "valid": True, "cost_usd": 0.0, "kind": "x"},
                {"trajectory_id": "T", "trial_index": 3, "attempt_index": 1,
                 "parsed_flip": "H", "valid": True, "cost_usd": 0.0, "kind": "x"},
                {"trajectory_id": "T", "trial_index": 4, "attempt_index": 1,
                 "parsed_flip": None, "valid": False, "cost_usd": 0.0, "kind": "x"},
                # unrelated trajectory
                {"trajectory_id": "OTHER", "trial_index": 1, "attempt_index": 1,
                 "parsed_flip": "T", "valid": True, "cost_usd": 0.0, "kind": "x"},
            ]
            with open(path, "w") as f:
                for e in entries:
                    f.write(json.dumps(e) + "\n")
            recovered = rebuild_trajectory_state_from_attempts(path, "T")
            self.assertEqual(recovered, "HTH")

    def test_cost_accounting_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "raw.jsonl")
            entries = [
                {"cost_usd": 0.01, "kind": "batch"},
                {"cost_usd": 0.02, "kind": "batch"},
                {"cost_usd": 0.005, "kind": "step"},
            ]
            with open(path, "w") as f:
                for e in entries:
                    f.write(json.dumps(e) + "\n")
            total, by_kind, calls = load_prior_spend_from_jsonl(path)
            self.assertAlmostEqual(total, 0.035)
            self.assertAlmostEqual(by_kind["batch"], 0.03)
            self.assertAlmostEqual(by_kind["step"], 0.005)
            self.assertEqual(calls["batch"], 2)
            self.assertEqual(calls["step"], 1)


# ---------- corpus models ---------------------------------------------------

class TestCorpusModels(unittest.TestCase):
    def test_three_models_astra_fable_mimo(self):
        self.assertEqual(len(C.CORPUS_MODELS), 3)
        labels = {m.label for m in C.CORPUS_MODELS}
        self.assertEqual(labels, {"astra", "fable", "mimo"})
        slugs = {m.label: m.slug for m in C.CORPUS_MODELS}
        self.assertEqual(slugs["mimo"], "xiaomi/mimo-v2.6-pro")

    def test_per_cell_is_20(self):
        self.assertEqual(C.CORPUS_TRAJECTORIES_PER_CELL, 20)

    def test_batch_max_attempts_headroom_for_mimo(self):
        self.assertGreaterEqual(C.CORPUS_BATCH_MAX_ATTEMPTS, 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
