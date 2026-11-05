"""Leave-one-base-out helpers (H-P2): the validation split and the pooled AUROC summary."""

from __future__ import annotations

import unittest
from pathlib import Path

from lemanruss.detect.data import Record
from lemanruss.detect.within import pooled_ci, split_train_val, summarise


def rec(i: int, base: str, infected: bool) -> Record:
    return Record(f"p{i:03d}", base, "gates", infected, 1 if infected else 0, "", "",
                  Path("x"), Path("x"))


class SplitTest(unittest.TestCase):
    def test_split_is_disjoint_deterministic_and_has_both_labels_each_side(self) -> None:
        recs = [rec(i, "a" if i % 2 else "b", i % 3 == 0) for i in range(30)]
        tr, va = split_train_val(recs)
        self.assertEqual({r.id for r in tr} & {r.id for r in va}, set())
        self.assertEqual(len(tr) + len(va), 30)
        self.assertEqual([r.id for r in va], [r.id for r in split_train_val(recs)[1]])
        for side in (tr, va):
            self.assertEqual({r.infected for r in side}, {False, True})


class SummariseTest(unittest.TestCase):
    def test_perfect_scores_give_auroc_one_and_ci_above_half(self) -> None:
        recs = [rec(i, "a", i % 2 == 0) for i in range(20)] + \
               [rec(100 + i, "b", i % 2 == 0) for i in range(20)]
        scores = {"a": {r.id: (1.0 if r.infected else 0.0) for r in recs if r.base == "a"},
                  "b": {r.id: (1.0 if r.infected else 0.0) for r in recs if r.base == "b"}}
        s = summarise(scores, recs)
        self.assertEqual(s["auroc"], 1.0)
        self.assertEqual(s["n_scored"], 40)
        ci = s["ci"]
        assert isinstance(ci, tuple)
        self.assertGreater(ci[0], 0.5)

    def test_one_class_only_has_no_ci(self) -> None:
        self.assertIsNone(pooled_ci([(0.1, 0), (0.2, 0)]))


if __name__ == "__main__":
    unittest.main()
