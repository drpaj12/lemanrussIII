"""Levels from procrun cells (spec 2026-11-06 Proc levels)."""

from __future__ import annotations

import unittest

from lemanruss.detect import proclevels

REG = {"i1": {"n_nets": 10, "trojans": [{"nets": ["a", "b"]}]},
       "i2": {"n_nets": 10, "trojans": [{"nets": ["c"]}, {"nets": ["c"]}]}}


def cell(circs: dict[str, dict[str, object]]) -> dict[str, object]:
    return {"circuits": circs}


class TestProcLevels(unittest.TestCase):
    def test_range_check_drops_out_of_range_and_claims_hit(self) -> None:
        c = cell({
            "i1": {"score": 0.9, "infected": True, "flag": True, "in_range": True,
                   "claims": [["a"]]},
            "i2": {"score": 0.8, "infected": True, "flag": True, "in_range": False},
            "k1": {"score": 0.1, "infected": False, "flag": False, "in_range": True},
        })
        circs, meta = proclevels.circs_from_cells([c], ["b1"], REG, True)
        self.assertEqual({x.cid for x in circs}, {"i1", "k1"})
        self.assertEqual(meta["out_of_range"], 1)
        i1 = next(x for x in circs if x.cid == "i1")
        self.assertEqual(i1.claims, (frozenset({"a"}),))
        circs2, _ = proclevels.circs_from_cells([c], ["b1"], REG, False)
        i2 = next(x for x in circs2 if x.cid == "i2")
        self.assertEqual(i2.claims, (frozenset(),))  # flagged without cells: a level-1 claim
        self.assertEqual(len(i2.regions), 2)

    def test_error_cell_is_counted(self) -> None:
        _, meta = proclevels.circs_from_cells([{"error": "x"}], ["b"], REG, True)
        self.assertEqual(meta["cell_errors"], 1)


if __name__ == "__main__":
    unittest.main()
