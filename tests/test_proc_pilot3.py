"""Pilot3 regression: the MCU witness image is the four byte planes, not a nonexistent
`blink.vmh` (FileNotFoundError in the first pilot3 run)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.proc_images import write_mcu_vmh
from lemanruss.htl.proc_pilot3 import dark_rtl_dir, mcu_witness_image


class WitnessImageTest(unittest.TestCase):
    def test_four_planes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            write_mcu_vmh([0x2a500293, 0x13], d, "blink")
            img = mcu_witness_image(d)
            self.assertEqual(sorted(img), [f"{p}blink.vmh" for p in range(4)])
            self.assertTrue(img["0blink.vmh"].startswith(b"@00000000\n93\n"))

    def test_dark_runs_in_rtl_dir(self) -> None:
        self.assertEqual(dark_rtl_dir(Path("/x/dark-clean")), Path("/x/dark-clean/rtl"))


if __name__ == "__main__":
    unittest.main()
