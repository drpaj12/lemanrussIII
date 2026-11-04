"""Tests for lemanruss.htl.blif_sim: pure-Python BLIF evaluation (no Odin III needed)."""

from __future__ import annotations

import unittest

from lemanruss.htl.blif_sim import evaluate_cycle, find_driving_inputs, monte_carlo_probability
from lemanruss.htl.blif_text import parse_single_model

TWO_AND = """\
.model two_and
.inputs a b c d
.outputs y
.names a b n8
11 1
.names c d n9
11 1
.names n8 n9 y
00 0
.end
"""


class TestEvaluateCycle(unittest.TestCase):
    def test_and_or_tree(self) -> None:
        model = parse_single_model(TWO_AND)
        values = evaluate_cycle(model, {"a": 1, "b": 1, "c": 0, "d": 0})
        self.assertEqual(values["n8"], 1)
        self.assertEqual(values["n9"], 0)
        self.assertEqual(values["y"], 1)  # y = n8 | n9 (the "00 0" row is a NOR-of-complements)

    def test_all_zero(self) -> None:
        model = parse_single_model(TWO_AND)
        values = evaluate_cycle(model, {"a": 0, "b": 0, "c": 0, "d": 0})
        self.assertEqual(values["y"], 0)


class TestMonteCarloProbability(unittest.TestCase):
    def test_internal_nets_are_rare(self) -> None:
        model = parse_single_model(TWO_AND)
        measurements = {m.name: m for m in monte_carlo_probability(model, cycles=4096, seed=0)}
        self.assertAlmostEqual(measurements["n8"].p_one, 0.25, delta=0.05)
        self.assertAlmostEqual(measurements["n9"].p_one, 0.25, delta=0.05)
        self.assertAlmostEqual(measurements["a"].p_one, 0.5, delta=0.05)


class TestFindDrivingInputs(unittest.TestCase):
    def test_finds_exact_combination(self) -> None:
        model = parse_single_model(TWO_AND)
        driving = find_driving_inputs(model, (("n8", 1), ("n9", 1)))
        self.assertIsNotNone(driving)
        assert driving is not None
        values = evaluate_cycle(model, driving)
        self.assertEqual(values["n8"], 1)
        self.assertEqual(values["n9"], 1)

    def test_none_when_impossible(self) -> None:
        model = parse_single_model(TWO_AND)
        # y can never be 0 while n8 is 1 and n9 is 0 is possible, but y=1 AND n8=0 AND n9=0 is
        # impossible given y's cover (y = NOT(NOT n8 AND NOT n9) = n8 OR n9).
        driving = find_driving_inputs(model, (("y", 1), ("n8", 0), ("n9", 0)))
        self.assertIsNone(driving)


if __name__ == "__main__":
    unittest.main()
