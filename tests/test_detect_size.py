"""Netlist parser and the size-only control on toy BLIF files."""

from __future__ import annotations

import gzip
import tempfile
import unittest
from pathlib import Path

import numpy as np

from lemanruss.detect import netlist as nlmod
from lemanruss.detect.data import CircuitFile
from lemanruss.detect.size_only import SizeOnly, fit_logistic

AND_CHAIN = """.model m
.inputs a b c
.outputs o
.names a b n1
11 1
.names n1 c n2
11 1
.names n2 o
0 1
.latch n2 q re clk 0
.end
"""


class ParseTests(unittest.TestCase):
    def test_parse_chain(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.blif.gz"
            with gzip.open(p, "wt") as fh:
                fh.write(AND_CHAIN)
            nl = nlmod.parse(p)
        self.assertEqual((nl.n_gates, nl.n_ffs, nl.depth), (3, 1, 3))
        counts = np.bincount(nl.cls, minlength=nlmod.N_CLASSES)
        self.assertEqual(counts[nlmod.C_AND], 2)
        self.assertEqual(counts[nlmod.C_INV], 1)
        self.assertEqual(counts[nlmod.C_INPUT], 3)

    def test_classify(self) -> None:
        self.assertEqual(nlmod.classify([("1-", "1"), ("-1", "1")], 2), nlmod.C_OR)
        self.assertEqual(nlmod.classify([("01", "1"), ("10", "1")], 2), nlmod.C_XOR)
        self.assertEqual(nlmod.classify([("0-", "1")], 2), nlmod.C_OTHER2)
        self.assertEqual(nlmod.classify([("11-", "1"), ("0-1", "1")], 3), nlmod.C_MUX)
        self.assertEqual(nlmod.classify([("1", "1")], 0 + 1), nlmod.C_BUF)


class SizeTests(unittest.TestCase):
    def test_logistic_learns_threshold(self) -> None:
        rng = np.random.default_rng(0)
        x = rng.normal(size=(200, 1))
        y = (x[:, 0] > 0).astype(float)
        z = np.hstack([np.ones((200, 1)), x])
        beta = fit_logistic(z, y)
        self.assertGreater(beta[1], 1.0)
        self.assertGreater(((z @ beta > 0) == (y == 1)).mean(), 0.95)

    def test_detector_interface_sees_only_path(self) -> None:
        self.assertEqual(set(CircuitFile.__dataclass_fields__), {"id", "path"})
        self.assertFalse(SizeOnly().needs_reference)


class SanityTests(unittest.TestCase):
    def test_style_counts_and_duplicates(self) -> None:
        from lemanruss.detect.sanity import release_hashes, style_counts

        text = (".model m\n.inputs a\n.outputs o\n.names a n1\n0 1\n.names n1 n2\n0 1\n"
                ".names n2 o\n1 1\n.end\n")
        with tempfile.TemporaryDirectory() as d:
            rel = Path(d) / "circuits"
            rel.mkdir()
            for name in ("x1", "x2"):
                with gzip.open(rel / f"{name}.blif.gz", "wt") as fh:
                    fh.write(text)
            inv_inv, _bb, bufs, _c = style_counts(rel / "x1.blif.gz")
            counts = release_hashes(rel)
        self.assertGreater(inv_inv, 0.0)
        self.assertGreater(bufs, 0.0)
        self.assertEqual(list(counts.values()), [2])


if __name__ == "__main__":
    unittest.main()
