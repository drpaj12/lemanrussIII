"""Detector interface. A detector never receives a base name, a clean twin or a label of a test
circuit; only Method B (`needs_reference`) receives `ReferencedFile`."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from lemanruss.detect.data import CircuitFile


class Detector:
    name = "detector"
    needs_reference = False
    seeded = False  # True: the harness reruns it for seeds 0-4

    def fit(
        self,
        train: Sequence[CircuitFile],
        y_train: Sequence[int],
        val: Sequence[CircuitFile],
        y_val: Sequence[int],
        seed: int,
    ) -> None:
        """Learn from training circuits (label 1 = infected); `val` is for model selection."""

    def score(self, circuits: Sequence[CircuitFile]) -> list[float]:
        """Anomaly score per circuit, higher = more likely infected; NaN = could not score."""
        raise NotImplementedError

    localises = False  # True: node_scores gives a suspicion per netlist node

    def node_scores(self, circuit: CircuitFile) -> np.ndarray | None:
        """Suspicion per node of `lemanruss.detect.netlist.parse(circuit.path)` (higher = more
        suspicious), or None when it cannot be computed. Only for `localises` detectors."""
        raise NotImplementedError

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        """Optional: fill feature caches for every circuit of the release in parallel."""
