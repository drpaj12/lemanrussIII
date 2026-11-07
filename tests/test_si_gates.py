"""Silicon-form gates of Seeker-Si rc2 (lemanruss.htl.si_gates) and the set switch of n200."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from lemanruss.htl import n200, si_gates
from tests.test_si_cells import lib_available

GOOD = (".model top\n.inputs a b clk\n.outputs y\n.names a b n1\n11 1\n"
        ".latch n1 y re clk 2\n.end\n")


class ActiveSetsTest(unittest.TestCase):
    def test_default_is_the_three_sets(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LEMANRUSS_SETS", None)
            self.assertEqual([s[0] for s in n200.active_sets()], ["K4", "K6", "G"])

    def test_silicon_only(self) -> None:
        with mock.patch.dict(os.environ, {"LEMANRUSS_SETS": "S"}):
            self.assertEqual(n200.active_sets(), (("S", "silicon"),))


@unittest.skipUnless(lib_available() and "ODIN3_LIB" in os.environ, "needs sky130hd.o3lib")
class SiGatesTest(unittest.TestCase):
    def test_pass(self) -> None:
        verilog, problems = si_gates.check(GOOD, 1)
        self.assertEqual(problems, [])
        self.assertIn("dfxtp_1", verilog)

    def test_ff_count_mismatch(self) -> None:
        _v, problems = si_gates.check(GOOD, 2)
        self.assertTrue(any("FF count" in p for p in problems))

    def test_cover_not_a_cell_is_a_problem(self) -> None:
        # a XNOR-like cover is a library cell, so use an unmatchable 6-input cover instead
        text = (".model top\n.inputs a b c d e f\n.outputs y\n.names a b c d e f y\n"
                "111111 1\n000000 1\n.end\n")
        _v, problems = si_gates.check(text, None)
        self.assertTrue(problems)


if __name__ == "__main__":
    unittest.main()
