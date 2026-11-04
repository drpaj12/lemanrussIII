"""Round 5: toggle-count cross-check, RTL testbench via sim_tb vs iverilog, extra restructurings."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.bitsim import compile_model
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.energy import run_one, stimulus, toggles_python
from lemanruss.htl.restructure import RESTRUCTURINGS, ROUND5_EXTRA
from lemanruss.htl.rtl_tb import first_diff, ports_of, testbench
from tests.helpers import odin_available

SEQ = """.model top
.inputs a b reset clock
.outputs y z
.latch d q re clock 0
.names a b d
11 1
.names q a y
1- 1
-1 1
.names y b z
10 1
.end
"""


class Round5Test(unittest.TestCase):
    def test_eighteen_restructurings(self) -> None:
        self.assertEqual(len(RESTRUCTURINGS), 18)
        self.assertTrue(set(ROUND5_EXTRA) <= set(RESTRUCTURINGS))

    def test_ports_and_testbench(self) -> None:
        src = "module M(input [3:0] a, input b, output [3:0] y);\nassign y = a;\nendmodule\n"
        ports = ports_of(src)
        self.assertEqual([(p.name, p.width) for p in ports], [("a", 4), ("b", 1), ("y", 4)])
        tb = testbench("M", ports, [{"a": 3, "b": 1}, {"a": 5, "b": 0}])
        self.assertIn("v_a[1] = 4'h5;", tb)
        self.assertIn('$display("%0d %h", i, y);', tb)

    def test_first_diff(self) -> None:
        self.assertIsNone(first_diff("0 a\n1 b\n", "0 0a\n1 0b\n"))
        self.assertEqual(first_diff("0 a\n1 b\n", "0 a\n1 c\n"), 1)

    def test_toggles_python_counts(self) -> None:
        comp = compile_model(parse_single_model(SEQ))
        steps = [{"a": 1, "b": 1, "reset": 0}, {"a": 0, "b": 0, "reset": 0}]
        tog = toggles_python(comp, steps)
        self.assertEqual(tog["a"], 2)  # 0 (power-on) -> 1 -> 0
        self.assertEqual(len(stimulus(comp, {}, 5, 0)), 5)

    @unittest.skipUnless(odin_available(), "odin3 not available")
    def test_energy_odin_equals_python(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(SEQ, encoding="utf-8")
            res = run_one(base, Path(td), "e1", 0)
            self.assertEqual(res.error, "")
            self.assertEqual(res.signals_equal, res.signals_compared)
            self.assertEqual(res.odin_delta_per_cycle, res.expected_delta_per_cycle)

    @unittest.skipUnless(odin_available() and shutil.which("iverilog") is not None,
                         "odin3 or iverilog not available")
    def test_simtb_agrees_with_iverilog(self) -> None:
        from lemanruss.htl.rtl_tb import build_and_check

        odin = Path(os.environ["ODIN3_LIB"]).parent / "odin3"
        tool = Path(os.environ["ODIN3_LIB"]).resolve().parents[2] / "tools/tb-compare/tb_compare.py"
        if not tool.exists():
            self.skipTest("tb-compare not in this Odin III checkout")
        src = ("module RefModule(input [7:0] a, input [7:0] b, output [7:0] y, output z);\n"
               "assign y = a ^ b;\nassign z = a[0] & b[1];\nendmodule\n")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "Prob_x_ref.sv"
            p.write_text(src, encoding="utf-8")
            res = build_and_check(p, Path(td) / "w", "rt1", odin, tool, 0)
            self.assertEqual([r.verdict for r in res], ["agree"] * 3, [r.detail for r in res])


if __name__ == "__main__":
    unittest.main()


class CommentedAssignTest(unittest.TestCase):
    def test_assign_in_comment_is_skipped(self) -> None:
        from lemanruss.htl.insert_hdl import insert_dos_stuck_payload
        from lemanruss.htl.payloads import DosStuckPayload

        src = ("module m(input a, output y);\n  // assign y = 1'b0;\n  assign y = a;\n"
               "  wire __htl_trigger = a;\nendmodule\n")
        out = insert_dos_stuck_payload(src, DosStuckPayload(victim="y", stuck_value=1))
        self.assertIn("// assign y = 1'b0;", out)
        self.assertIn("assign y = __htl_trigger ? 1 : (a);", out)
