"""Splits, metrics and the detector interface on toy data (spec docs/specs/2026-11-01-*)."""

from __future__ import annotations

import unittest
from pathlib import Path

from lemanruss.detect import metrics
from lemanruss.detect.data import LUT_FORMS, Record
from lemanruss.detect.splits import all_splits, make_folds, source_of

BASES = (
    [f"C{i}" for i in range(10)]
    + [f"s{i}" for i in range(10)]
    + [f"b{i:02d}" for i in range(10)]
    + ["alu4", "apex2", "apex4", "cordic", "ex5p", "misex3", "pdc", "spla", "t481"]
    + [f"ve_P{i}" for i in range(7)]
    + ["diffeq1", "diffeq2", "sha"]
)
FORMS = ["identity", "strash", "lut4", "lut5", "lut6", "lut6mfs", "balance"]


def toy_records() -> list[Record]:
    recs = []
    for b in BASES:
        for f in FORMS:
            for k in (0, 1):
                recs.append(Record(f"{b}-{f}-{k}", b, f, bool(k), k, "", "", Path("x"), Path("x")))
    return recs


class SplitTests(unittest.TestCase):
    def test_folds_partition_and_balance(self) -> None:
        folds = make_folds(BASES)
        flat = [b for f in folds for b in f]
        self.assertEqual(sorted(flat), sorted(BASES))
        self.assertLessEqual(max(map(len, folds)) - min(map(len, folds)), 1)

    def test_folds_deterministic_and_stratified(self) -> None:
        self.assertEqual(make_folds(BASES), make_folds(list(reversed(BASES))))
        folds = make_folds(BASES)
        for f in folds:  # every source (10 or more bases) reaches every fold
            self.assertLessEqual(
                {source_of(b) for b in BASES if source_of(b) != "VTR"}, {source_of(b) for b in f}
            )

    def test_no_base_on_two_sides(self) -> None:
        for name in ("base", "lut"):
            splits = all_splits(toy_records(), name)
            tested = []
            for sp in splits:
                tr = {r.base for r in sp.train}
                va = {r.base for r in sp.val}
                te = {r.base for r in sp.test}
                self.assertFalse(tr & te or tr & va or va & te)
                tested += sorted(te)
            self.assertEqual(sorted(tested), sorted(BASES))  # each base tested once

    def test_lut_split_forms(self) -> None:
        for sp in all_splits(toy_records(), "lut"):
            self.assertTrue(all(r.form in LUT_FORMS for r in sp.test))
            self.assertTrue(all(r.form not in LUT_FORMS for r in sp.train + sp.val))

    def test_set_split_holds_out_one_set(self) -> None:
        recs = []
        for b in BASES:
            for st in ("K4", "K6", "G", "golden"):
                for k in (0, 1):
                    recs.append(Record(f"{b}-{st}-{k}", b, "identity", bool(k), k, st, "",
                                       Path("x"), Path("x")))
        splits = all_splits(recs, "set")
        self.assertEqual(len(splits), 15)
        for sp in splits:
            held = sp.name.split("-")[1]
            self.assertTrue(all(r.set == held for r in sp.test))
            self.assertTrue(all(r.set not in (held, "golden") for r in sp.train + sp.val))
            self.assertFalse({r.base for r in sp.train} & {r.base for r in sp.test})
        self.assertTrue(all(r.set != "golden" for sp in splits for r in sp.test))

    def test_unknown_source_is_error(self) -> None:
        with self.assertRaises(ValueError):
            source_of("mystery")


class MetricTests(unittest.TestCase):
    def test_auroc(self) -> None:
        self.assertEqual(metrics.auroc([1, 2, 3, 4], [0, 0, 1, 1]), 1.0)
        self.assertEqual(metrics.auroc([4, 3, 2, 1], [0, 0, 1, 1]), 0.0)
        self.assertEqual(metrics.auroc([1, 1, 1, 1], [0, 0, 1, 1]), 0.5)
        self.assertAlmostEqual(metrics.auroc([1, 3, 2, 4], [0, 0, 1, 1]) or 0, 0.75)
        self.assertIsNone(metrics.auroc([1, 2], [1, 1]))

    def test_threshold_and_rates(self) -> None:
        clean = [float(i) for i in range(100)]  # 0..99
        thr = metrics.threshold_at_fpr(clean)
        self.assertEqual(sum(c >= thr for c in clean), 5)
        tpr, fpr = metrics.rates([10, 96, 98, 3], [1, 1, 0, 0], thr)
        self.assertEqual((tpr, fpr), (0.5, 0.5))

    def test_threshold_with_ties_and_zero(self) -> None:
        thr = metrics.threshold_at_fpr([0.0] * 10)
        self.assertGreater(thr, 0.0)  # flags d > 0 only
        with self.assertRaises(ValueError):
            metrics.threshold_at_fpr([])

    def test_f1_reweighting(self) -> None:
        self.assertAlmostEqual(metrics.f1_at_prevalence(1.0, 0.0, 0.1), 1.0)
        # tpr .8, fpr .1, prevalence .5: P = .4/.45, R = .8
        p = 0.4 / 0.45
        self.assertAlmostEqual(metrics.f1_at_prevalence(0.8, 0.1, 0.5), 2 * p * 0.8 / (p + 0.8))
        self.assertEqual(metrics.f1_at_prevalence(0.0, 0.0, 0.3), 0.0)

    def test_wlt(self) -> None:
        m = {"a": 0.9, "b": 0.5, "c": 0.7, "d": None}
        c = {"a": 0.5, "b": 0.5, "c": 0.8, "d": 0.5}
        self.assertEqual(metrics.wlt(m, c), (1, 1, 1))

    def test_bootstrap_resamples_bases(self) -> None:
        # perfect separation inside every base: interval is exactly 1.0
        fold = {f"b{i}": [(0.0, 0), (1.0, 1)] for i in range(4)}
        ci = metrics.bootstrap_ci([fold], metrics.pair_auroc, reps=50)
        self.assertEqual(ci, (1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
