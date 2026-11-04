"""`out_of_range`: a circuit whose FF count falls outside the detector's own training fold's FF
range is flagged `out_of_range`, never counted as a true/false flag (spec
`docs/specs/2026-11-03-seeker-proc-rc1.md` section 6; round 9: `ffcount` flagged all four Proc
pilot3 circuits, clean too, because 67k-132k RAM-as-latches sat far above the Comb/Seq training
range of hundreds to low thousands of FFs)."""

from __future__ import annotations

import unittest

from lemanruss.detect.ffrange import OUT_OF_RANGE, classify, ff_range, in_range


class FfRangeTest(unittest.TestCase):
    def test_empty_training_fold_has_no_range(self) -> None:
        self.assertIsNone(ff_range([]))

    def test_range_is_min_max(self) -> None:
        self.assertEqual(ff_range([5, 1, 9, 3]), (1, 9))

    def test_in_range_inclusive(self) -> None:
        rng = (10, 100)
        self.assertTrue(in_range(10, rng))
        self.assertTrue(in_range(100, rng))
        self.assertTrue(in_range(50, rng))
        self.assertFalse(in_range(9, rng))
        self.assertFalse(in_range(101, rng))

    def test_no_range_means_everything_in_range(self) -> None:
        self.assertTrue(in_range(999999, None))

    def test_classify_inside_range_uses_threshold(self) -> None:
        rng = (0, 1000)
        self.assertTrue(classify(score=5.0, threshold=1.0, ff_count=500, rng=rng))
        self.assertFalse(classify(score=0.5, threshold=1.0, ff_count=500, rng=rng))

    def test_classify_outside_range_is_out_of_range_even_if_score_would_flag(self) -> None:
        rng = (0, 1000)
        # Round 9's actual failure mode: a huge FF count (RAM as per-bit latches) makes ffcount's
        # score huge too, so a naive threshold check would flag it (score >= threshold is True)
        # on every circuit, clean or infected, regardless of the Trojan.
        self.assertEqual(classify(score=99.0, threshold=1.0, ff_count=132446, rng=rng),
                          OUT_OF_RANGE)
        self.assertEqual(classify(score=99.0, threshold=1.0, ff_count=-1, rng=rng), OUT_OF_RANGE)

    def test_pilot3_scenario_clean_and_infected_both_out_of_range(self) -> None:
        """Round 9: Comb/Seq training FFs are in the hundreds; Proc pilot3's mcu pair (132446
        FFs, clean = infected) and darkriscv pair (67638 FFs, clean = infected) are both far
        outside it -- out_of_range for all four, not a false positive on the clean twins."""
        train_ffs = [12, 40, 88, 203, 950]  # representative Comb/Seq identity-form FF counts
        rng = ff_range(train_ffs)
        for ff in (132446, 67638):
            self.assertEqual(classify(score=11.8, threshold=5.0, ff_count=ff, rng=rng),
                              OUT_OF_RANGE)


if __name__ == "__main__":
    unittest.main()
