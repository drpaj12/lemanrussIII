"""Three-level score: hand-checked cases (the paper's worked table) and the chance control."""

from __future__ import annotations

import unittest

from lemanruss.score import levels as lv
from lemanruss.score.levels import Circ


def fs(*x: str) -> frozenset[str]:
    return frozenset(x)


R1 = fs("a", "b")
R2 = fs("c", "d")


def table() -> list[Circ]:
    return [
        Circ("1", "x", (), (), 10),
        Circ("2", "x", (), (fs("p"), fs("q")), 10),
        Circ("3", "x", (R1,), (fs("a"),), 10),
        Circ("4", "x", (R1, R2), (fs("p"), fs("q")), 10),
        Circ("5", "x", (R1,), (fs("a"), fs("q")), 10),
    ]


class LevelsTest(unittest.TestCase):
    def test_worked_table(self) -> None:
        cs = table()
        got = [[lv.circuit_score(c, k) for c in cs] for k in (1, 2, 3)]
        self.assertEqual(got[0], [1, 0, 1, 1, 1])
        self.assertEqual(got[1], [1, 0, 1, 1, 0.5])
        self.assertEqual(got[2], [1, 0, 1, 0, 0.5])
        self.assertAlmostEqual(lv.mean_score(cs, 1) or 0, 0.8)
        self.assertAlmostEqual(lv.mean_score(cs, 2) or 0, 0.7)
        self.assertAlmostEqual(lv.mean_score(cs, 3) or 0, 0.5)
        self.assertEqual(lv.cells(cs, 1), lv.Cells(3, 1, 0, 1))
        self.assertEqual(lv.cells(cs, 2), lv.Cells(4, 3, 0, 1))
        self.assertEqual(lv.cells(cs, 3), lv.Cells(2, 5, 2, 1))

    def test_peter_case(self) -> None:
        c = Circ("p", "x", (R1,), (fs("q"), fs("r")), 10)
        self.assertEqual(lv.circuit_score(c, 1), 1)
        self.assertEqual(lv.circuit_score(c, 3), 0)

    def test_one_to_one(self) -> None:
        # both claims hit the same Trojan only: one match, not two
        c = Circ("o", "x", (R1, R2), (fs("a"), fs("b")), 10)
        self.assertEqual(lv.max_matching(c.claims, c.regions), 1)
        self.assertAlmostEqual(lv.circuit_score(c, 3), 1 / 3)
        # a claim that touches both regions can still take only one
        c2 = Circ("o2", "x", (R1, R2), (fs("a", "c"), fs("c")), 10)
        self.assertEqual(lv.max_matching(c2.claims, c2.regions), 2)
        c3 = Circ("o3", "x", (R1, R2), (fs("a", "c"),), 10)
        self.assertEqual(lv.max_matching(c3.claims, c3.regions), 1)

    def test_order_ladder(self) -> None:
        for c in table():
            s = [lv.circuit_score(c, k) for k in (1, 2, 3)]
            self.assertGreaterEqual(s[0], s[1])
            self.assertGreaterEqual(s[1], s[2])

    def test_chance_and_label(self) -> None:
        cs = [Circ(f"c{i}", "b", (R1,), (fs("a"),), 4) for i in range(6)]
        ex = lv.chance_expectation(cs, reps=20, seed=1)
        e3 = sum(v[2] for v in ex.values()) / 6
        self.assertTrue(0 < e3 < 1)  # 1 claim of 1 cell: hits R1 (2 of 4 cells) half the time
        self.assertAlmostEqual(e3, 0.5, delta=0.2)
        self.assertEqual(lv.label(0.1, 0.2), "ABOVE CHANCE")
        self.assertEqual(lv.label(-0.2, -0.1), "BELOW CHANCE")
        self.assertEqual(lv.label(-0.1, 0.1), "INCONCLUSIVE")

    def test_summarise(self) -> None:
        cs = table() + [Circ("6", "y", (R1,), (fs("a"),), 10)]
        out = lv.summarise(cs, lv.chance_expectation(cs, reps=5), reps=50)
        self.assertEqual(set(out), {1, 2, 3})
        self.assertEqual(out[3]["n"], 6)
        self.assertEqual(sum(out[3]["wlt"]), 2)


if __name__ == "__main__":
    unittest.main()
