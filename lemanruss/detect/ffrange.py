"""`out_of_range`: a detector's flag is never a false positive/miss on a circuit whose FF count
falls outside the detector's own training range (spec `docs/specs/2026-11-03-seeker-proc-rc1.md`
section 6; round 9 found `ffcount` flagging all four Proc pilot3 circuits, clean too, because
67k-132k RAM-as-latches is far above the Comb/Seq training range -- a detector extrapolating, not
detecting). Pure functions: no file I/O of their own, callers pass FF counts already read from
the netlist (`lemanruss.detect.size_only.size_stats`'s third element).
"""

from __future__ import annotations

from collections.abc import Sequence

OUT_OF_RANGE = "out_of_range"


def ff_range(train_ff_counts: Sequence[int]) -> tuple[int, int] | None:
    """[min, max] FF count of a training fold; None if the fold is empty (no range to check)."""
    if not train_ff_counts:
        return None
    return min(train_ff_counts), max(train_ff_counts)


def in_range(ff_count: int, rng: tuple[int, int] | None) -> bool:
    """True if `rng` is None (nothing to check against) or `ff_count` falls inside it inclusive."""
    if rng is None:
        return True
    lo, hi = rng
    return lo <= ff_count <= hi


def classify(score: float, threshold: float, ff_count: int,
             rng: tuple[int, int] | None) -> bool | str:
    """The flag a circuit gets: `out_of_range` (a third value, not counted either way) when
    `ff_count` falls outside the training fold's own FF range; otherwise the ordinary
    `score >= threshold` flag."""
    if not in_range(ff_count, rng):
        return OUT_OF_RANGE
    return score >= threshold
