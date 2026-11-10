"""Seeker v2.0 full-set report: confusion counts, labels, split source of the OpenCores bases."""

from __future__ import annotations

import unittest

from lemanruss.detect import splits, v2report
from lemanruss.detect.v2report import Obs


def ob(score: float, inf: bool, n: int = 1, bench: str = "b", fold: str = "f0") -> Obs:
    return Obs("d", "Seq", "K4", bench, fold, score, 0.5, inf, n, bench)


class V2ReportTest(unittest.TestCase):
    def test_conf(self) -> None:
        c = v2report.conf([ob(0.9, True), ob(0.1, True), ob(0.9, False), ob(0.1, False)])
        self.assertEqual((c["TP"], c["FN"], c["FP"], c["TN"]), (1, 1, 1, 1))
        self.assertEqual(c["TPR"], 0.5)
        self.assertEqual(c["accuracy"], 0.5)

    def test_label(self) -> None:
        self.assertEqual(v2report.label((0.6, 0.7)), "ABOVE CHANCE")
        self.assertEqual(v2report.label((0.3, 0.4)), "BELOW CHANCE")
        self.assertEqual(v2report.label((0.45, 0.6)), "INCONCLUSIVE")

    def test_summarise_found_rate(self) -> None:
        obs = [ob(0.9, True, 2), ob(0.1, True, 2), ob(0.2, False), ob(0.8, False)]
        r = v2report.summarise(obs)["Seq|K4|d"]
        self.assertEqual(r["found_by_trojan_count"]["2"]["found"], 1)
        self.assertEqual(r["found_by_trojan_count"]["2"]["n"], 2)

    def test_opencores_source(self) -> None:
        self.assertEqual(splits.source_of("ca_prng"), "OpenCores")
        self.assertEqual(splits.source_of("i2c"), "OpenCores")


if __name__ == "__main__":
    unittest.main()
