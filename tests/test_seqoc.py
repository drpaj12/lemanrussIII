"""Seeker-Seq rc8: OpenCores admission table, source column and the rc7 + new merge."""

from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl import ocbases
from lemanruss.htl.seqoc import merge_roots, opencores_licence_lines, source_of


def _w(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


class AdmissionTable(unittest.TestCase):
    def test_twelve_designs_two_waves(self) -> None:
        names = [d.name for d in ocbases.DESIGNS]
        self.assertEqual(len(names), 12)
        self.assertEqual(len(set(names)), 12)
        self.assertEqual(sum(1 for d in ocbases.DESIGNS if d.wave == 1), 8)
        self.assertEqual(sum(1 for d in ocbases.DESIGNS if d.wave == 2), 4)

    def test_every_row_has_licence_and_reason(self) -> None:
        for d in ocbases.DESIGNS:
            self.assertTrue(d.licence and d.licence_where and d.reason, d.name)

    def test_unlicensed_and_memory_designs_are_excluded(self) -> None:
        by = {d.name: d for d in ocbases.DESIGNS}
        for n in ("simple_spi", "sdram_16bit", "wb_lcd", "verilog_cordic_core"):
            self.assertFalse(by[n].admitted, n)

    def test_source_column(self) -> None:
        self.assertEqual(source_of("s27"), "ISCAS-89")
        self.assertEqual(source_of("b04"), "ITC-99")
        self.assertEqual(source_of("sha"), "VTR")
        self.assertEqual(source_of("des"), "OpenCores")

    def test_licence_lines_only_for_opencores(self) -> None:
        self.assertEqual(opencores_licence_lines(["s27", "sha"]), [])
        lines = opencores_licence_lines(["mmuart", "s27"])
        self.assertIn("GPL-3.0", "\n".join(lines))

    def test_flist(self) -> None:
        d = next(x for x in ocbases.DESIGNS if x.name == "spi")
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "spi.f"
            ocbases.write_flist(Path("/x"), d, f)
            text = f.read_text(encoding="utf-8").splitlines()
        self.assertTrue(text[0].startswith("+incdir+/x/opencores/spi/"))
        self.assertEqual(len(text), 1 + len(d.files))


class Merge(unittest.TestCase):
    def test_merge_keeps_rc7_bytes_and_adds_new(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            rc7, new = r / "rc7", r / "new"
            blif7 = ".model a\n.end\n"
            (rc7 / "circuits").mkdir(parents=True)
            (rc7 / "circuits" / "ss0001.blif.gz").write_bytes(gzip.compress(blif7.encode()))
            for name, val in (("labels", {"ss0001": None}), ("sets", {"s27": {}}),
                              ("scripts", {}), ("trojans", {}), ("cuts", {}),
                              ("rareness", []), ("failures", []),
                              ("catalogue", {"trojan_catalogue": {}})):
                _w(rc7 / "answer_key" / f"{name}.json", val)
            (rc7 / "answer_key" / "pre").mkdir()
            (rc7 / "answer_key" / "witnesses").mkdir()
            man7 = {"circuits": [{"id": "ss0001", "base": "s27"}], "goldens": {"s27": "ss0001"}}
            (r / "m7.json.gz").write_bytes(gzip.compress(json.dumps(man7).encode()))
            (new / "circuits").mkdir(parents=True)
            (new / "circuits" / "ss9001.blif").write_text(".model b\n.end\n", encoding="utf-8")
            new_files: tuple[tuple[str, object], ...] = (
                ("labels", {"ss9001": "t1"}), ("sets", {"mmuart": {}}),
                ("scripts", {}), ("trojans", {}), ("cuts", {}),
                ("rareness", []), ("failures", []))
            for name, val in new_files:
                _w(new / "answer_key" / f"{name}.json", val)
            (new / "answer_key" / "pre").mkdir()
            (new / "answer_key" / "witnesses").mkdir()
            _w(new / "manifest.json", {
                "version": "2.0", "schema": 4, "v1_lineage": "x", "adds": "y",
                "goldens": {"mmuart": "ss9001"}, "trojan_catalogue": {"t1": {}},
                "circuits": [{"id": "ss9001", "base": "mmuart", "file": "circuits/ss9001.blif"}]})
            out = r / "out"
            got = merge_roots(rc7, r / "m7.json.gz", new, out)
            self.assertEqual(got, {"rc7": 1, "new": 1, "infected": 1})
            self.assertEqual((out / "circuits" / "ss0001.blif").read_text(encoding="utf-8"),
                             blif7)
            man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(man["bases"], ["mmuart", "s27"])
            self.assertEqual(man["trojans"], ["t1"])

    def test_id_collision_refused(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            rc7, new = r / "rc7", r / "new"
            (rc7 / "circuits").mkdir(parents=True)
            (rc7 / "circuits" / "ss0001.blif.gz").write_bytes(gzip.compress(b"x\n"))
            (new / "circuits").mkdir(parents=True)
            (new / "circuits" / "ss0001.blif").write_text("y\n", encoding="utf-8")
            (r / "m7.json.gz").write_bytes(gzip.compress(json.dumps(
                {"circuits": [{"id": "ss0001", "base": "a"}], "goldens": {}}).encode()))
            _w(new / "manifest.json", {"circuits": [
                {"id": "ss0001", "base": "b", "file": "circuits/ss0001.blif"}]})
            with self.assertRaises(ValueError):
                merge_roots(rc7, r / "m7.json.gz", new, r / "out")


if __name__ == "__main__":
    unittest.main()
