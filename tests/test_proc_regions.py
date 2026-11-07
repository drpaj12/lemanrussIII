"""Processor Trojan regions (spec section 9a): the trigger logic has no twin on random lanes."""

from __future__ import annotations

import unittest

from lemanruss.score import proc_regions
from lemanruss.score import regions as rg

GOLD = """.model m
.inputs a b c d clk
.outputs o
.latch n1 q re clk 0
.names a b n1
11 1
.names q c o
10 1
.end
"""

# the same core plus a rare trigger (a & b & c & d) that forces o high
INF = """.model m
.inputs a b c d clk
.outputs o
.latch n1 q re clk 0
.names a b n1
11 1
.names a b c d t
1111 1
.names q c o0
10 1
.names o0 t o
1- 1
-1 1
.end
"""


class TestProcRegions(unittest.TestCase):
    def test_trigger_and_merge_are_in_region_shared_logic_is_not(self) -> None:
        r = proc_regions.region_nets(rg.parse_blif(GOLD), rg.parse_blif(INF), "s")
        self.assertEqual(r["victims"], ["o"])
        self.assertIn("t", r["nets"])
        self.assertNotIn("n1", r["nets"])
        self.assertNotIn("q", r["nets"])

    def test_identical_circuits_have_empty_region(self) -> None:
        r = proc_regions.region_nets(rg.parse_blif(GOLD), rg.parse_blif(GOLD), "s")
        self.assertEqual(r["nets"], [])
        self.assertEqual(r["victims"], [])


if __name__ == "__main__":
    unittest.main()
