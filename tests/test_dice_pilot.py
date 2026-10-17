"""Pre-paid-run tests for the dice-pilot (DICE_PILOT_v3.1, spec §10)."""

import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

from spar_dynamic.dice_pilot import prompts
from spar_dynamic.dice_pilot.parsers import parse_phase1, parse_phase2
from spar_dynamic.dice_pilot import config as C


class TestPromptConsistency(unittest.TestCase):
    def test_phase2_quotes_phase1_byte_exact(self):
        prompts.assert_consistency()  # raises on failure

    def test_only_four_permitted_ordinals(self):
        self.assertEqual(sorted(prompts.PHASE2_ORDINALS.keys()), [1, 2, 5, 9])
        self.assertEqual(set(prompts.PHASE2_ORDINALS.values()),
                         {"first", "second", "fifth", "ninth"})

    def test_each_phase2_prompt_substitutes_correctly(self):
        for pos, ord_word in prompts.PHASE2_ORDINALS.items():
            p = prompts.phase2_prompt(pos)
            self.assertIn(ord_word, p)
            self.assertNotIn("{ORDINAL}", p)
            # Phase 1 instruction appears verbatim once, inside quotation marks
            self.assertEqual(p.count(prompts.PHASE1_PROMPT), 1,
                              f"Phase 1 should appear exactly once in Phase 2 prompt for position {pos}")


class TestPhase1Parser(unittest.TestCase):
    def test_accepts_space_separated_ten_integers(self):
        r = parse_phase1("1 2 3 4 5 6 1 2 3 4")
        self.assertTrue(r.valid); self.assertEqual(r.values, [1,2,3,4,5,6,1,2,3,4])

    def test_accepts_comma_separated(self):
        r = parse_phase1("1,2,3,4,5,6,1,2,3,4")
        self.assertTrue(r.valid); self.assertEqual(len(r.values), 10)

    def test_accepts_newline_separated(self):
        r = parse_phase1("1\n2\n3\n4\n5\n6\n1\n2\n3\n4")
        self.assertTrue(r.valid)

    def test_accepts_trailing_period_flagged(self):
        r = parse_phase1("1 2 3 4 5 6 1 2 3 4.")
        self.assertTrue(r.valid); self.assertTrue(r.had_trailing_punct)

    def test_rejects_wrong_length(self):
        self.assertFalse(parse_phase1("1 2 3 4 5 6 1 2 3").valid)        # 9
        self.assertFalse(parse_phase1("1 2 3 4 5 6 1 2 3 4 5").valid)    # 11

    def test_rejects_out_of_range(self):
        self.assertFalse(parse_phase1("1 2 3 4 5 7 1 2 3 4").valid)      # 7
        self.assertFalse(parse_phase1("0 1 2 3 4 5 6 1 2 3").valid)      # 0

    def test_rejects_prose(self):
        self.assertFalse(parse_phase1("Here are 10 rolls: 1 2 3 4 5 6 1 2 3 4").valid)
        self.assertFalse(parse_phase1("1 2 3 4 5 6 1 2 3 4\nThat's my answer").valid)

    def test_empty_rejected(self):
        self.assertFalse(parse_phase1("").valid)
        self.assertFalse(parse_phase1("   ").valid)


class TestPhase2Parser(unittest.TestCase):
    def test_valid_bare_digit(self):
        for d in "123456":
            r = parse_phase2(d)
            self.assertEqual(r.category, "valid"); self.assertEqual(r.value, int(d))

    def test_valid_with_trailing_period_and_whitespace(self):
        r = parse_phase2("  4.\n")
        self.assertEqual(r.category, "valid"); self.assertEqual(r.value, 4)

    def test_prefix_leak_multiple_integers(self):
        r = parse_phase2("3 5 2")
        self.assertEqual(r.category, "prefix_leak")
        self.assertEqual(r.extracted_integers, [3, 5, 2])

    def test_prefix_leak_commas(self):
        r = parse_phase2("1, 2, 3")
        self.assertEqual(r.category, "prefix_leak")

    def test_decline_cannot_be_determined(self):
        r = parse_phase2("The answer cannot be determined without running the generation.")
        self.assertEqual(r.category, "decline")

    def test_decline_refuse(self):
        r = parse_phase2("I refuse to speculate about future outputs.")
        self.assertEqual(r.category, "decline")

    def test_invalid_integer_in_prose(self):
        # Spec: "exactly one integer in the range 1–6, optionally with surrounding
        # whitespace or a terminal period" - prose with an embedded digit is NOT valid.
        r = parse_phase2("The answer is 4.")
        self.assertEqual(r.category, "invalid")

    def test_invalid_no_integer_no_decline(self):
        r = parse_phase2("Sure thing!")
        self.assertEqual(r.category, "invalid")

    def test_invalid_out_of_range_digit(self):
        r = parse_phase2("7")
        self.assertEqual(r.category, "invalid")  # 7 is not a 1..6 integer
        self.assertEqual(r.extracted_integers, [])

    def test_empty_invalid(self):
        self.assertEqual(parse_phase2("").category, "invalid")


class TestCallBudget(unittest.TestCase):
    def test_total_calls_within_spec_cap(self):
        self.assertLessEqual(C.total_calls_max(), 150)
    def test_phase2_calls_count(self):
        self.assertEqual(C.PHASE2_CALLS_PER_CONFIG, 20)
    def test_phase1_calls_count(self):
        self.assertEqual(C.PHASE1_CALLS_PER_CONFIG, 5)


class TestCapabilityTableSanity(unittest.TestCase):
    def test_execution_order_includes_three_models(self):
        self.assertEqual(C.EXECUTION_ORDER, ("astra", "fable", "qwen"))

    def test_astra_fable_lack_temperature(self):
        self.assertFalse(C.MODELS_BY_LABEL["astra"].supports_temperature)
        self.assertFalse(C.MODELS_BY_LABEL["fable"].supports_temperature)

    def test_qwen_supports_both(self):
        q = C.MODELS_BY_LABEL["qwen"]
        self.assertTrue(q.supports_temperature)
        self.assertTrue(q.supports_reasoning)


if __name__ == "__main__":
    unittest.main(verbosity=2)
