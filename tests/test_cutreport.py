"""Round 9 report helpers (pure functions)."""

from __future__ import annotations

import unittest

from lemanruss.htl.cutreport import auroc, features


class TestReport(unittest.TestCase):
    def test_auroc_separated_tied_and_empty(self) -> None:
        self.assertEqual(auroc([3.0, 4.0], [1.0, 2.0]), 1.0)
        self.assertEqual(auroc([1.0], [1.0]), 0.5)
        self.assertEqual(auroc([], [1.0]), 0.5)
        self.assertEqual(auroc([1.0, 2.0], [3.0, 4.0]), 0.0)

    def test_features_count_flip_flops_and_buffers(self) -> None:
        text = (".model top\n.inputs a clk\n.outputs y\n.names a n1\n1 1\n.names n1 n2\n1 1\n"
                ".latch n2 n3 re clk 2\n.names n3 y\n0 1\n.end\n")
        f = features(text)
        self.assertEqual(f["ff"], 1.0)
        self.assertEqual(f["ff_dbuf"], 1.0)
        self.assertEqual(f["dbl_share"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
