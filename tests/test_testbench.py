"""Tests for lemanruss.htl.testbench: vectors-file and iverilog testbench text generators."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.testbench import Port, build_iverilog_testbench, build_vectors_file

HAVE_IVERILOG = shutil.which("iverilog") is not None and shutil.which("vvp") is not None


class TestBuildVectorsFile(unittest.TestCase):
    def test_header_and_fixed_drive(self) -> None:
        inputs = [Port("a", 1), Port("b", 1)]
        outputs = [Port("y", 1)]
        text = build_vectors_file(inputs, outputs, drive={"a": 1, "b": 1}, cycles=3)
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("# htl seed 0 cycles 3"))
        self.assertIn("# input a 1", lines)
        self.assertIn("# input b 1", lines)
        self.assertIn("# output y 1", lines)
        data_lines = [line for line in lines if not line.startswith("#")]
        self.assertEqual(len(data_lines), 3)
        self.assertEqual(data_lines[0], "0 11 0")

    def test_undriven_input_defaults_to_zero(self) -> None:
        inputs = [Port("a", 1), Port("b", 1)]
        text = build_vectors_file(inputs, [], drive={"a": 1}, cycles=1)
        data_line = [line for line in text.splitlines() if not line.startswith("#")][0]
        self.assertEqual(data_line, "0 10 -")


class TestBuildIverilogTestbench(unittest.TestCase):
    def test_includes_dut_instance_and_display(self) -> None:
        inputs = [Port("a", 1), Port("b", 1)]
        tb = build_iverilog_testbench("rare_and", inputs, drive={"a": 1, "b": 1}, victim="y")
        self.assertIn("rare_and dut(", tb)
        self.assertIn("$display(\"HTL_RESULT %b\", y_out);", tb)
        self.assertIn("a = 1;", tb)
        self.assertIn("b = 1;", tb)

    @unittest.skipUnless(HAVE_IVERILOG, "iverilog/vvp not installed")
    def test_compiles_and_runs_with_iverilog(self) -> None:
        dut_source = """\
module rare_and(input a, input b, output y);
    assign y = a & b;
endmodule
"""
        inputs = [Port("a", 1), Port("b", 1)]
        tb = build_iverilog_testbench("rare_and", inputs, drive={"a": 1, "b": 1}, victim="y")
        with tempfile.TemporaryDirectory() as tmp:
            dut_path = Path(tmp) / "dut.v"
            tb_path = Path(tmp) / "tb.v"
            out_path = Path(tmp) / "a.out"
            dut_path.write_text(dut_source, encoding="utf-8")
            tb_path.write_text(tb, encoding="utf-8")
            subprocess.run(
                ["iverilog", "-o", str(out_path), str(dut_path), str(tb_path)],
                check=True, capture_output=True, text=True,
            )
            result = subprocess.run(
                ["vvp", str(out_path)], check=True, capture_output=True, text=True, timeout=30
            )
            self.assertIn("HTL_RESULT 1", result.stdout)


if __name__ == "__main__":
    unittest.main()
