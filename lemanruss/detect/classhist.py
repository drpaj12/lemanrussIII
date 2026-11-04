"""Diagnostic baseline (not in the brief): logistic regression on the share of each of the 17
node classes plus log gates, log depth, log FFs. If this matches the GNNs, the GNNs learn a
class-mix signature, not graph structure."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile
from lemanruss.detect.features import cached, fill
from lemanruss.detect.netlist import N_CLASSES, parse
from lemanruss.detect.size_only import fit_logistic


def hist_features(path: Path) -> np.ndarray:
    nl = parse(path)
    share = np.bincount(nl.cls, minlength=N_CLASSES) / max(nl.n_nodes, 1)
    return np.concatenate([share, np.log1p([nl.n_gates, nl.depth, nl.n_ffs])])


class ClassHist(Detector):
    name = "classhist"

    def __init__(self) -> None:
        self.beta = np.zeros(N_CLASSES + 4)
        self.mu = np.zeros(N_CLASSES + 3)
        self.sd = np.ones(N_CLASSES + 3)

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        fill("hist", circuits, hist_features)

    def _x(self, files: Sequence[CircuitFile]) -> np.ndarray:
        return np.array([cached("hist", f, hist_features) for f in files], dtype=float)

    def fit(self, train: Sequence[CircuitFile], y_train: Sequence[int],
            val: Sequence[CircuitFile], y_val: Sequence[int], seed: int) -> None:
        x = self._x(train)
        self.mu = x.mean(axis=0)
        self.sd = np.maximum(x.std(axis=0), 1e-9)
        z = np.hstack([np.ones((len(x), 1)), (x - self.mu) / self.sd])
        self.beta = fit_logistic(z, np.asarray(y_train, dtype=float))

    def score(self, circuits: Sequence[CircuitFile]) -> list[float]:
        x = self._x(circuits)
        z = np.hstack([np.ones((len(x), 1)), (x - self.mu) / self.sd])
        return [float(v) for v in z @ self.beta]
