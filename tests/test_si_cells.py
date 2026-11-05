"""Seeker-Si cell Verilog writer (lemanruss.htl.si_cells): library, matching, round trip."""

from __future__ import annotations

import os
import unittest

from lemanruss.htl import si_cells as sc
from lemanruss.htl.obfuscate import parse, signature, sky130_lib


def lib_available() -> bool:
    try:
        return sky130_lib().exists()
    except (KeyError, IndexError):
        return False


@unittest.skipUnless(lib_available() and "ODIN3_LIB" in os.environ, "needs sky130hd.o3lib")
class SiCellsTest(unittest.TestCase):
    def test_library_has_the_combinational_cells(self) -> None:
        lib = sc.library()
        self.assertEqual(len(lib), 83)
        self.assertIn("sky130_fd_sc_hd__nand2_1", lib)
        self.assertNotIn(sc.DFF, lib)

    def test_cover_tt(self) -> None:
        self.assertEqual(sc.cover_tt(2, ["11 1"]), 0b1000)
        self.assertEqual(sc.cover_tt(2, ["1- 1", "-1 1"]), 0b1110)
        self.assertEqual(sc.cover_tt(0, ["1"]), 1)
        self.assertEqual(sc.cover_tt(0, []), 0)

    def test_round_trip(self) -> None:
        blif = "\n".join([
            ".model top", ".inputs a[0] a[1] clk", ".outputs y q",
            ".names a[0] a[1] n1", "11 1",
            ".names n1 a[1] y", "1- 1", "-1 1",
            ".names n1 d", "0 1",
            ".latch d q re clk 2", ".names c1", "1", ".end", ""])
        v = sc.blif_to_verilog(blif)
        self.assertIn("sky130_fd_sc_hd__and2_1", v)
        self.assertIn("sky130_fd_sc_hd__or2_1", v)
        self.assertIn("sky130_fd_sc_hd__inv_1", v)
        self.assertIn(sc.DFF, v)
        self.assertIn("input [1:0] a", v)
        i, o, _ = parse(blif)
        back = sc.verilog_to_blif(v, i, o)
        self.assertEqual(sorted(b[0].split()[0] for b in parse(back)[2]),
                         sorted(b[0].split()[0] for b in parse(blif)[2]))
        self.assertEqual(len(signature(back)), 64)

    def test_unknown_cover_is_an_error(self) -> None:
        blif = ".model top\n.inputs a b c d e f\n.outputs y\n.names a b c d e f y\n111111 1\n.end\n"
        with self.assertRaises(ValueError):
            sc.blif_to_verilog(blif)


if __name__ == "__main__":
    unittest.main()
