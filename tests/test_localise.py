"""Claim rule: grouping of adjacent flagged cells, limits, fall-back to the best cell."""

from __future__ import annotations

import unittest

import numpy as np

from lemanruss.detect import localise
from lemanruss.detect.netlist import C_AND, C_INPUT, C_OUTPUT, Netlist


def chain(n: int) -> Netlist:
    """input, n gates g0..g{n-1} in a chain, output."""
    cls = np.array([C_INPUT] + [C_AND] * n + [C_OUTPUT], dtype=np.int8)
    nodes = n + 2
    src = np.arange(nodes - 1, dtype=np.int64)
    dst = src + 1
    return Netlist(cls, np.zeros(nodes, dtype=np.int32), np.zeros(nodes, dtype=np.int32), src, dst,
                   ["in"] + [f"g{i}" for i in range(n)] + [""])


class LocaliseTest(unittest.TestCase):
    def test_adjacent_group_into_one_claim(self) -> None:
        nl = chain(12)
        sc = np.zeros(14)
        sc[[3, 4]] = 10.0   # g2, g3 adjacent
        sc[9] = 8.0         # g8 apart
        cl = localise.claims_from_scores(nl, sc, 1.0)
        self.assertEqual(len(cl), 2)
        self.assertEqual(set(cl[0]), {"g2", "g3"})
        self.assertEqual(cl[1], ["g8"])

    def test_limits(self) -> None:
        nl = chain(40)
        sc = np.zeros(42)
        for i in (2, 10, 20, 30):
            sc[i] = 10.0 + i
        cl = localise.claims_from_scores(nl, sc, 1.0)
        self.assertEqual(len(cl), localise.MAX_CLAIMS)
        sc2 = np.zeros(42)
        sc2[5:25] = np.arange(20) + 100.0
        sc2[30:] = 0.0
        big = localise.claims_from_scores(nl, sc2, 1.0)
        self.assertTrue(all(len(c) <= localise.MAX_CELLS for c in big))

    def test_fallback_best_cell(self) -> None:
        nl = chain(5)
        sc = np.ones(7)
        sc[3] = 1.5
        cl = localise.claims_from_scores(nl, sc, 50.0)
        self.assertEqual(cl, [["g2"]])

    def test_tune_prefers_hitting_z(self) -> None:
        nl = chain(30)
        sc = np.zeros(32)
        sc[8] = 50.0
        sc[20:23] = 2.0
        items = [(nl, sc, (frozenset({"g7"}),))]
        z = localise.tune_z(items)
        self.assertGreaterEqual(z, 1.0)


if __name__ == "__main__":
    unittest.main()
