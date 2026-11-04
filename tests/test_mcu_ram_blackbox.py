"""mcu RAM black-box patches (rc1): pure text edits on the upstream sources, skipped if absent."""

import os
import unittest
from pathlib import Path

from lemanruss.htl.mcu_ram_blackbox import (
    PatchNotFound,
    blackbox_subsystem,
    blackbox_top,
    mcu_odin_files,
    mcu_tb_with_ram_model,
)

WS = Path(os.environ.get("ODIN3_WS", "~/odin3-ws")).expanduser()  # holds odin3/, external/
_SRC = WS / "external/Arduino-on-RISC-V/quartus_project_revert_timer"
_TB = WS / "odin3/tests/mcu/mcu_tb.v"


class McuRamBlackboxTest(unittest.TestCase):
    def test_odin_files_drop_ram_modules(self) -> None:
        files = ["a.v", "dual_port_BRAM.v", "dual_port_BRAM_byte_en.v", "b.v"]
        self.assertEqual(mcu_odin_files(files), ["a.v", "b.v"])

    def test_missing_text_raises(self) -> None:
        with self.assertRaises(PatchNotFound):
            blackbox_subsystem("module x; endmodule")
        with self.assertRaises(PatchNotFound):
            blackbox_top("module x; endmodule")
        with self.assertRaises(PatchNotFound):
            mcu_tb_with_ram_model("module x; endmodule", "blink")

    @unittest.skipUnless(_SRC.is_dir() and _TB.is_file(), "upstream mcu sources absent")
    def test_patches_apply_to_upstream(self) -> None:
        sub = blackbox_subsystem((_SRC / "dual_port_BRAM_memory_subsystem.v").read_text())
        self.assertNotIn("dual_port_BRAM_byte_en #(", sub)
        self.assertIn("RAM_DDATA", sub)
        top = blackbox_top((_SRC / "single_cycle_BRAM_top.v").read_text())
        self.assertIn(".RAM_CTL(RAM_CTL)", top)
        tb = mcu_tb_with_ram_model(_TB.read_text(), "blink")
        self.assertIn('$readmemh("0blink.vmh"', tb)


if __name__ == "__main__":
    unittest.main()
