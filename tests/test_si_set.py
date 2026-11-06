"""Seeker-Si set planner (lemanruss.htl.si_set.make_plan): sizes, infected share, Trojan counts."""

from __future__ import annotations

import unittest

from lemanruss.htl.si_build import OUT_DECL
from lemanruss.htl.si_set import make_plan


class PlanTest(unittest.TestCase):
    def test_even_sizes_and_infected_total(self) -> None:
        plan = make_plan(123, ["a", "b", "c"], 100)
        self.assertEqual(sorted(plan["size"].values()), [33, 33, 34])
        self.assertTrue(10 <= plan["n_inf"] <= 70)
        self.assertEqual(sum(plan["infected"].values()), plan["n_inf"])
        for b in "abc":
            ms = plan["ms"][b]
            self.assertEqual(len(ms), plan["size"][b])
            self.assertEqual(sum(1 for m in ms if m), plan["infected"][b])
            self.assertTrue(all(0 <= m <= 3 for m in ms))

    def test_same_seed_same_plan(self) -> None:
        self.assertEqual(make_plan(7, ["a", "b"], 100), make_plan(7, ["a", "b"], 100))


class OutDeclTest(unittest.TestCase):
    def test_bus_and_scalar_outputs(self) -> None:
        text = "module top (\n  input a,\n  output [31:0] csr_do,\n  output tx_irq\n);\n"
        self.assertEqual(OUT_DECL.findall(text), [("31", "0", "csr_do"), ("", "", "tx_irq")])


if __name__ == "__main__":
    unittest.main()
