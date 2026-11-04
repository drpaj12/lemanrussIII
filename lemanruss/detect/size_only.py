"""Size-only control: logistic regression on gate count, depth and flip-flop count."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile
from lemanruss.detect.features import cached, fill
from lemanruss.detect.netlist import parse

L2 = 1.0


def size_stats(path: Path) -> tuple[int, int, int]:
    nl = parse(path)
    return nl.n_gates, nl.depth, nl.n_ffs


def fit_logistic(x: np.ndarray, y: np.ndarray, l2: float = L2, iters: int = 50) -> np.ndarray:
    """Class-balanced L2 logistic regression by IRLS; x has a leading bias column."""
    n_pos = max(float(y.sum()), 1.0)
    n_neg = max(float((1 - y).sum()), 1.0)
    w_cls = np.where(y == 1, 0.5 / n_pos, 0.5 / n_neg) * len(y)
    beta = np.zeros(x.shape[1])
    reg = l2 * np.eye(x.shape[1])
    reg[0, 0] = 0.0
    for _ in range(iters):
        z = x @ beta
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        wv = w_cls * np.maximum(p * (1 - p), 1e-6)
        grad = x.T @ (w_cls * (p - y)) + reg @ beta
        hess = (x * wv[:, None]).T @ x + reg
        step = np.linalg.solve(hess, grad)
        beta -= step
        if float(np.abs(step).max()) < 1e-8:
            break
    return beta


class SizeOnly(Detector):
    name = "size"

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        fill("size", circuits, size_stats)

    def __init__(self) -> None:
        self.beta = np.zeros(4)
        self.mu = np.zeros(3)
        self.sd = np.ones(3)

    @staticmethod
    def _x(files: Sequence[CircuitFile]) -> np.ndarray:
        raw = np.array([cached("size", f, size_stats) for f in files], dtype=float)
        return np.asarray(np.log1p(raw), dtype=float)

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
