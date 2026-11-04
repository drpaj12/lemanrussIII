"""Tests for lemanruss.htl.sites: signal probability (needs Odin III) and pure victim rules."""

from __future__ import annotations

import unittest
from pathlib import Path

from lemanruss.htl.sites import ScopVictimRule, SignalProbability, SimProbabilityRarity
from tests.helpers import odin_available

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestVictimRule(unittest.TestCase):
    def test_output_victim_picks_first_output(self) -> None:
        rule = ScopVictimRule(outputs=("y", "z"))
        self.assertEqual(rule.output_victim(), "y")

    def test_output_victim_none_when_no_outputs(self) -> None:
        self.assertIsNone(ScopVictimRule(outputs=()).output_victim())

    def test_reset_victim_prefers_named_reset(self) -> None:
        rule = ScopVictimRule(outputs=())
        self.assertEqual(rule.reset_victim(("clk", "rst", "a")), "rst")

    def test_reset_victim_falls_back_to_first_input(self) -> None:
        rule = ScopVictimRule(outputs=())
        self.assertEqual(rule.reset_victim(("clk", "a")), "clk")

    def test_reset_victim_none_with_no_inputs(self) -> None:
        rule = ScopVictimRule(outputs=())
        self.assertIsNone(rule.reset_victim(()))


class TestSimProbabilityRarity(unittest.TestCase):
    def test_rare_at_one(self) -> None:
        measurements = (SignalProbability("y", 1, 0.02, 4096),)
        self.assertEqual(SimProbabilityRarity(measurements).rare_nets(), [("y", 1)])

    def test_rare_at_zero(self) -> None:
        measurements = (SignalProbability("y", 1, 0.99, 4096),)
        self.assertEqual(SimProbabilityRarity(measurements).rare_nets(), [("y", 0)])

    def test_not_rare_in_the_middle(self) -> None:
        measurements = (SignalProbability("y", 1, 0.5, 4096),)
        self.assertEqual(SimProbabilityRarity(measurements).rare_nets(), [])


@unittest.skipUnless(odin_available(), "Odin III not available (set ODIN3_LIB/PYTHONPATH)")
class TestMeasureSignalProbability(unittest.TestCase):
    def test_and_gate_output_is_rare_at_one(self) -> None:
        from odin3 import Design

        from lemanruss.htl.sites import measure_signal_probability

        path = FIXTURES / "rare_and.v"
        with Design() as design:
            design.run_script(f'read_verilog "{path}"; proc; opt; lower')
            measurements = measure_signal_probability(design, cycles=4096, seed=1)
            by_name = {m.name: m for m in measurements}
            # P(a&b=1) = 0.25 over uniform random a, b; generous tolerance for n=4096 samples.
            self.assertAlmostEqual(by_name["y"].p_one, 0.25, delta=0.08)


if __name__ == "__main__":
    unittest.main()
