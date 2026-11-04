"""Tests for lemanruss.htl.dark_ram_blackbox: text patches on the real upstream darksocv.v and
the testbench copy; skipped without the external/darkriscv checkout."""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

from lemanruss.htl.dark_ram_blackbox import (
    PatchNotFound,
    blackbox_darksocv,
    dark_odin_files,
    dark_tb_with_ram_model,
)

WS = Path(os.environ.get("ODIN3_WS", "~/odin3-ws")).expanduser()  # holds odin3/, external/
SOC = WS / "external/darkriscv/rtl/darksocv.v"
TB = WS / "odin3/tests/darkriscv/dark_tb.v"


class TestFiles(unittest.TestCase):
    def test_drops_only_darkram(self) -> None:
        files = ["darksocv.v", "darkram.v", "darkio.v"]
        self.assertEqual(dark_odin_files(files), ["darksocv.v", "darkio.v"])


@unittest.skipUnless(SOC.is_file(), "needs the external/darkriscv checkout")
class TestSoc(unittest.TestCase):
    def test_instance_replaced_ports_added(self) -> None:
        out = blackbox_darksocv(SOC.read_text())
        self.assertNotIn("darkram bram0", out)
        for port in ("RAM_CTL0", "RAM_CTL1", "RAM_CTL2", "RAM_IADDR", "RAM_XATAO"):
            self.assertIn(port, out)

    def test_missing_point_raises(self) -> None:
        with self.assertRaises(PatchNotFound):
            blackbox_darksocv("module m; endmodule")


@unittest.skipUnless(TB.is_file(), "needs the Odin III tests/darkriscv checkout")
class TestTb(unittest.TestCase):
    def test_model_added_within_port_limit(self) -> None:
        out = dark_tb_with_ram_model(TB.read_text())
        self.assertIn("ram_model", out)
        self.assertIn("$readmemh", out)
        self.assertNotIn("][31:24]", out)  # no part-select on an array element (sim_tb refuses)
        inst = out[out.index("darksocv soc0"):]
        inst = inst[: inst.index(");")]
        self.assertLessEqual(len(re.findall(r"\.[A-Z_0-9]+\(", inst)), 16)

    def test_missing_point_raises(self) -> None:
        with self.assertRaises(PatchNotFound):
            dark_tb_with_ram_model("module t; endmodule")


if __name__ == "__main__":
    unittest.main()
