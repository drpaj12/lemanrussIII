"""Tests for lemanruss.htl.picorv32_tb: pure text/file generation, no Odin III needed (the
Odin III read_verilog/sim_tb re-validation of the generated testbench happens in
tests/test_proc_insert.py's TestPicorv32KindedPatch and by hand in the smoke build, recorded in
docs/results-round11.md)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.picorv32_tb import write_pico_prog, write_pico_tb


class TestWritePicoTb(unittest.TestCase):
    def test_writes_module_with_requested_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_pico_tb(Path(tmp), cycles=123)
            text = path.read_text()
        self.assertIn("module pico_tb;", text)
        self.assertIn("parameter CYCLES = 123;", text)
        self.assertIn("picorv32 uut (", text)
        # no part-select on an array-indexed expression (round 10's sim_tb limit): the byte
        # merge must happen on the plain scratch reg, not on memory[...] directly.
        self.assertNotIn("memory[mem_addr[9:2]][7:0]", text)
        self.assertIn("mem_next[7:0]", text)

    def test_default_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = write_pico_tb(Path(tmp)).read_text()
        self.assertIn("parameter CYCLES = 300;", text)


class TestWritePicoProg(unittest.TestCase):
    def test_pads_to_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_pico_prog([0x12300293, 0x00000013], Path(tmp) / "p.mem", depth=4)
            lines = path.read_text().splitlines()
        self.assertEqual(lines, ["12300293", "00000013", "00000000", "00000000"])

    def test_truncates_to_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_pico_prog([1, 2, 3, 4, 5], Path(tmp) / "p.mem", depth=3)
            lines = path.read_text().splitlines()
        self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
