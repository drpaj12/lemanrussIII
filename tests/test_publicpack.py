"""Public package text: family README, index pages, public datasheets."""

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl import publicpack as pp

ROOT = Path(__file__).resolve().parent.parent


def _mk(public: Path, fam: str, name: str, cycles: int) -> None:
    d = public / fam / name
    for s in ("K4", "gates"):
        (d / s).mkdir(parents=True)
        for i in range(3):
            (d / s / f"x{s}{i}.blif.gz").write_bytes(b"x")
    (d / "stimulus").mkdir()
    head = "a b\n" if fam == "seq" else "a\n"
    (d / "stimulus" / ("sequence.txt" if fam == "seq" else "vectors.txt")).write_text(
        head + "0\n" * cycles
    )
    (d / "golden.blif.gz").write_bytes(b"g")


class FamilyReadmeTest(unittest.TestCase):
    def test_heading_has_blank_lines(self) -> None:
        text = pp.family_readme("comb")
        self.assertIn("(see each README).\n\n# How to submit (summary)\n\n", text)
        self.assertNotIn("README). #", text)
        self.assertIn("seeker-comb-v2.0", text)


class IndexPagesTest(unittest.TestCase):
    def test_pages_and_readme(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pub = Path(td) / "public"
            _mk(pub, "seq", "s382", 4)
            _mk(pub, "comb", "C432", 1024)
            docs = Path(td) / "docs"
            self.assertEqual(pp.write_docs(pub, docs), 2)
            page = (docs / "seq" / "s382.md").read_text()
            self.assertIn("4 cycles", page)
            self.assertIn("shorter than 64 cycles", page)
            self.assertIn(f"{pp.RELEASE_URL}/seeker-seq-v2.0-s382.tar.gz", page)
            self.assertIn(f"{pp.RELEASE_URL}/seeker-seq-v2.0-all.tar.gz", page)
            self.assertIn("SUBMISSION.md", page)
            self.assertIn("1024 neutral input vectors", (docs / "comb" / "C432.md").read_text())
            readme = (docs / "README.md").read_text()
            self.assertIn("Scoring opens when the seeker-scoring service is live", readme)
            self.assertIn("comb/C432.md", readme)
            for text in (page, readme):
                self.assertEqual(pp.has_per_set_counts(text), [])


class PublicDatasheetTest(unittest.TestCase):
    PRIVATE = (
        "intro\n\n| core | gates inf/clean | lut4 inf/clean |\n|---|---|---|\n"
        "| mcu | 21 / 79 | 57 / 43 |\n\nafter\n\n"
        "| base | source | gates | K4 drawn / infected / clean | G drawn / infected / clean |\n"
        "|---|---|---|---|---|\n| C432 | ISCAS-85 | 182 | 45 / 45 / 55 | 70 / 70 / 30 |\n\n"
        "Data only, no rejection: b01 16/9\n"
        "checked: mcu: gates 21 infected, 0 differing, lut4 57 infected, 0 differing.\n"
    )

    def test_removes_counts(self) -> None:
        self.assertNotEqual(pp.has_per_set_counts(self.PRIVATE), [])
        out = pp.public_datasheet(self.PRIVATE)
        self.assertEqual(pp.has_per_set_counts(out), [])
        self.assertIn(pp.PER_SET_SENTENCE, out)
        self.assertIn("| C432 | ISCAS-85 | 182 |", out)
        self.assertIn("gates 0 differing", out)

    def test_committed_datasheets_clean(self) -> None:
        for p in sorted((ROOT / "releases").glob("seeker-*-v2.0*/DATASHEET.md")):
            with self.subTest(p=p.parent.name):
                self.assertEqual(pp.has_per_set_counts(p.read_text()), [])


if __name__ == "__main__":
    unittest.main()
