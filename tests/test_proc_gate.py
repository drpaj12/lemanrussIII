"""Release gate (rc2): the rc1 defect classes are each caught, a clean flat BLIF passes."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from lemanruss.htl.proc_gate import odin_read_problem, structural_problems

OK = """.model top
.inputs a b clk
.outputs y q
.names a b n1
11 1
.latch n1 q re clk 2
.names n1 q y
10 1
.end
"""
ODIN = Path(os.environ.get("ODIN3_BIN", "odin3"))


class StructuralTest(unittest.TestCase):
    def test_clean_passes(self) -> None:
        self.assertEqual(structural_problems(OK), [])

    def test_several_models(self) -> None:
        self.assertTrue(any("2 .model" in p for p in structural_problems(
            OK + ".model sub\n.inputs x\n.outputs z\n.names x z\n1 1\n.end\n")))

    def test_duplicate_ports(self) -> None:
        bad = OK.replace(".inputs a b clk", ".inputs a b clk a")
        self.assertTrue(any("duplicate input" in p for p in structural_problems(bad)))

    def test_input_also_driven(self) -> None:
        bad = OK.replace(".inputs a b clk", ".inputs a b clk n1")
        self.assertTrue(any("also driven" in p for p in structural_problems(bad)))

    def test_multi_driven_by_names_and_latch(self) -> None:
        bad = OK.replace(".end", ".names a q\n1 1\n.end")
        self.assertTrue(any("multi-driven" in p for p in structural_problems(bad)))

    def test_continuation_lines_are_joined(self) -> None:
        bad = OK.replace(".inputs a b clk", ".inputs a b \\\nclk a")
        self.assertTrue(any("duplicate input" in p for p in structural_problems(bad)))


@unittest.skipUnless(ODIN.is_file(), "needs ODIN3_BIN")
class OdinReadTest(unittest.TestCase):
    def test_good_reads_and_multi_driver_does_not(self) -> None:
        self.assertIsNone(odin_read_problem(ODIN, OK))
        bad = OK.replace(".end", ".names a q\n1 1\n.end")
        self.assertIsNotNone(odin_read_problem(ODIN, bad))


HIER = """module sub(input clk, input d, output reg q);
  always @(posedge clk) q <= ~d;
endmodule
module top(input clk, input a, input b, output y);
  wire w;
  sub u(.clk(clk), .d(a & b), .q(w));
  assign y = w ^ a;
endmodule
"""


@unittest.skipUnless(ODIN.is_file(), "needs ODIN3_BIN")
class FlatLoweringTest(unittest.TestCase):
    """rc1 regression: lower_gates_as_names left a hierarchy as several .model sections."""

    def test_hierarchy_lowers_to_one_valid_model(self) -> None:
        import tempfile

        from lemanruss.htl.proc_release import lower_gates_as_names
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "h.v").write_text(HIER, encoding="utf-8")
            out = d / "o.blif"
            lower_gates_as_names(ODIN, "top", ["h.v"], d, out)
            text = out.read_text(encoding="utf-8")
        self.assertEqual(structural_problems(text), [])
        self.assertIsNone(odin_read_problem(ODIN, text))


if __name__ == "__main__":
    unittest.main()
