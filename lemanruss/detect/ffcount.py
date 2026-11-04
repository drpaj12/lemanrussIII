"""FF-count control (rc7): the score is log(1 + flip-flop count), no training. On rc7 the Trojan
adds no flip-flop, so this should sit near 0.5; on rc5 / rc6 it separates the labels."""

from __future__ import annotations

import math
from collections.abc import Sequence

from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile
from lemanruss.detect.features import cached, fill
from lemanruss.detect.size_only import size_stats


class FfCount(Detector):
    name = "ffcount"

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        fill("size", circuits, size_stats)

    def score(self, circuits: Sequence[CircuitFile]) -> list[float]:
        return [math.log1p(cached("size", f, size_stats)[2]) for f in circuits]
