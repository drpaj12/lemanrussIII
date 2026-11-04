"""rc7 FF gates: stratum AUROC and bootstrap CI behave on a synthetic example."""

from __future__ import annotations

import unittest

from lemanruss.htl.ffgate import pooled_with_ci


class FfGateTest(unittest.TestCase):
    def test_separable_and_tied(self) -> None:
        sep = {("a", "K4"): ([1.0, 1.0], [5.0, 6.0]), ("b", "K4"): ([2.0], [9.0])}
        r = pooled_with_ci(sep, draws=50)
        self.assertEqual(r["auroc"], 1.0)
        tie = {("a", "K4"): ([3.0, 3.0], [3.0, 3.0]), ("b", "K4"): ([3.0], [3.0])}
        r = pooled_with_ci(tie, draws=50)
        self.assertEqual(r["auroc"], 0.5)


if __name__ == "__main__":
    unittest.main()
