"""Seeker-Proc rc1 release packaging: mix, opacity, leak checks (synthetic circuits)."""

from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.proc_rc1_release import (
    FORM_NAMES,
    LogicalCircuit,
    draw_infected,
    package_proc_rc1,
    verify_proc_rc1,
)

BLIF = ".model top\n.inputs a b\n.outputs y\n.names a b n1\n11 1\n.latch n1 y 0\n.end\n"


def make(root: Path, n: int) -> list[LogicalCircuit]:
    out = []
    for i in range(n):
        d = root / f"mcu-{i:04d}"
        d.mkdir(parents=True)
        for f in FORM_NAMES:
            blif = BLIF.replace("n1", f"n{i}{f}")
            (d / f"{f}-clean.blif").write_text(blif, encoding="utf-8")
            (d / f"{f}-infected.blif").write_text(
                blif.replace(".end", f".names n{i}{f} g9\n1 1\n.end"), encoding="utf-8")
        out.append(LogicalCircuit(f"mcu-{i:04d}", "mcu", ["reset"], [0x12345293], d))
    return out


class TestRc1Release(unittest.TestCase):
    def test_draw_infected_range(self) -> None:
        for s in range(20):
            k = len(draw_infected(100, random.Random(s)))
            self.assertTrue(10 <= k <= 70)

    def test_package_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            circuits = make(Path(tmp) / "forms", 12)
            out = Path(tmp) / "rel"
            info = package_proc_rc1(circuits, out, seed=7)
            self.assertEqual(info["circuits"], 36)
            res = verify_proc_rc1(out)
            self.assertTrue(res["ok"], res)
            man = json.loads((out / "manifest.json").read_text())
            self.assertEqual(len({c["id"] for c in man["circuits"]}), 36)
            ds = (out / "DATASHEET.md").read_text()
            self.assertNotIn("0x12345293", ds)
            self.assertNotIn("0x12345293", json.dumps(man))

    def test_leak_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            circuits = make(Path(tmp) / "forms", 12)
            out = Path(tmp) / "rel"
            package_proc_rc1(circuits, out, seed=7)
            (out / "circuits" / "pr0001.blif.gz").write_bytes(b"corrupt")
            self.assertFalse(verify_proc_rc1(out)["ok"])


if __name__ == "__main__":
    unittest.main()
