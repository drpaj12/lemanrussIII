"""Tests for lemanruss.htl.sv_reader: registering Odin III's slang SystemVerilog reader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import odin_available

SV_SOURCE = """\
module RefModule (
  input a,
  input b,
  output out
);
  assign out = a & b;
endmodule
"""


@unittest.skipUnless(odin_available(), "Odin III not available (set ODIN3_LIB/PYTHONPATH)")
class TestRegisterSlangReader(unittest.TestCase):
    def test_reads_systemverilog_after_registering(self) -> None:
        from odin3 import Design

        from lemanruss.htl.sv_reader import register_slang_reader

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ref.sv"
            path.write_text(SV_SOURCE, encoding="utf-8")
            with Design() as design:
                register_slang_reader(design)  # idempotent if an earlier test registered it
                design.run_script(f'read_verilog "{path}"; proc; opt; lower')
                top = design.top()
                self.assertIsNotNone(top)
                assert top is not None
                self.assertEqual(top.name, "RefModule")


if __name__ == "__main__":
    unittest.main()
