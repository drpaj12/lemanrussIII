"""Rare-signal score, Method B arithmetic and the GNN on tiny synthetic data."""

from __future__ import annotations

import gzip
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

from lemanruss.detect.data import CircuitFile
from lemanruss.detect.graphlet_b import drift
from lemanruss.detect.rare_scoap import rare_score, robust_z
from lemanruss.detect.scoap_feat import ScoapFeat

HAVE_TORCH = (
    importlib.util.find_spec("torch") is not None
    and importlib.util.find_spec("torch_geometric") is not None
)


def feat(cc: list[float], co: list[float], p: list[float], ran: bool = True) -> ScoapFeat:
    n = len(cc)
    return ScoapFeat([f"n{i}" for i in range(n)], np.array(cc), np.array(cc), np.array(co),
                     np.array(p), ran, False)


class RareTests(unittest.TestCase):
    def test_outlier_net_raises_score(self) -> None:
        n = 100
        base = feat([5.0] * n, [4.0] * n, [0.5] * n)
        odd = feat([5.0] * 99 + [1e6], [4.0] * 99 + [1e6], [0.5] * 99 + [0.001])
        self.assertLess(rare_score(base), rare_score(odd))

    def test_robust_z_constant(self) -> None:
        self.assertTrue(np.all(robust_z(np.ones(5)) == 0))

    def test_no_sigprob_drops_second_term(self) -> None:
        f = feat([5.0] * 10, [4.0] * 10, [0.001] * 10, ran=False)
        self.assertEqual(rare_score(f), 0.0)


class MethodBTests(unittest.TestCase):
    def test_drift(self) -> None:
        ref = np.array([10, 10, 0])
        self.assertEqual(drift(ref, ref), 0.0)
        self.assertAlmostEqual(drift(np.array([10, 5, 5]), ref), 10 / 20)


def blif(n: int, extra: bool) -> str:
    lines = [".model m", ".inputs a b", ".outputs o"]
    prev = "a"
    for i in range(n):
        lines += [f".names {prev} b n{i}", "11 1"]
        prev = f"n{i}"
    if extra:
        lines += [f".names {prev} a t", "11 1", f".names t {prev} o", "10 1"]
    else:
        lines += [f".names {prev} o", "1 1"]
    return "\n".join(lines + [".end", ""])


@unittest.skipUnless(HAVE_TORCH, "torch and torch_geometric not installed")
class GnnTests(unittest.TestCase):
    def test_gnn_learns_toy_task(self) -> None:
        import os

        from lemanruss.detect.gnn import GnnDetector

        os.environ["LEMANRUSS_EPOCHS"] = "30"
        os.environ["LEMANRUSS_BATCH"] = "8"
        with tempfile.TemporaryDirectory() as d:
            os.environ["LEMANRUSS_FEAT"] = str(Path(d) / "feat")
            files, ys = [], []
            for i in range(24):
                y = i % 2
                p = Path(d) / "rel" / "circuits" / f"c{i:02d}.blif.gz"
                p.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(p, "wt") as fh:
                    fh.write(blif(3 + i % 4, bool(y)))
                files.append(CircuitFile(f"c{i:02d}", p))
                ys.append(y)
            det = GnnDetector("gnn-yasaei")
            det.fit(files, ys, files, ys, seed=0)
            sc = det.score(files)
        self.assertEqual(len(sc), 24)
        pos = np.mean([s for s, y in zip(sc, ys, strict=True) if y])
        neg = np.mean([s for s, y in zip(sc, ys, strict=True) if not y])
        self.assertGreater(pos, neg)


if __name__ == "__main__":
    unittest.main()
