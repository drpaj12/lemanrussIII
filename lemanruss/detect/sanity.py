"""Sanity detector (controller 2026-11-01): exact-duplicate lookup plus local style counts.

Features of one circuit: how many other circuits of the release have the same decompressed BLIF
(sha256), and the shares of double inverters, double buffers, single-input buffers and constant
drivers among its cells. A logistic regression on those. On a clean release it must sit near
chance: any detector that beats it only by style is not detecting Trojans.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile, read_text
from lemanruss.detect.features import cached, fill
from lemanruss.detect.netlist import C_BUF, C_CONST, C_INV, parse
from lemanruss.detect.size_only import fit_logistic


def blif_hash(path: Path) -> str:
    return hashlib.sha256(read_text(path).encode("utf-8")).hexdigest()


def style_counts(path: Path) -> tuple[float, float, float, float]:
    """Shares (of cells with an input) of: double inverter, double buffer, buffer, and the share
    of constant drivers among all cells."""
    nl = parse(path)
    n = max(int((nl.k > 0).sum()), 1)
    cls = nl.cls
    inv_inv = int(((cls[nl.dst] == C_INV) & (cls[nl.src] == C_INV)).sum())
    buf_buf = int(((cls[nl.dst] == C_BUF) & (cls[nl.src] == C_BUF)).sum())
    bufs = int((cls == C_BUF).sum())
    consts = int((cls == C_CONST).sum())
    return inv_inv / n, buf_buf / n, bufs / n, consts / max(nl.n_nodes, 1)


def release_hashes(circuits_dir: Path) -> dict[str, int]:
    """sha256 -> number of circuits in the release directory with that content."""
    counts: dict[str, int] = {}
    for p in sorted(circuits_dir.glob("*.blif.gz")):
        h = blif_hash(p)
        counts[h] = counts.get(h, 0) + 1
    return counts


class Sanity(Detector):
    name = "sanity"

    def __init__(self) -> None:
        self.index: dict[Path, dict[str, int]] = {}
        self.beta = np.zeros(6)
        self.mu = np.zeros(5)
        self.sd = np.ones(5)

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        fill("style", circuits, style_counts)
        fill("blifhash", circuits, blif_hash)

    def _x(self, files: Sequence[CircuitFile]) -> np.ndarray:
        rows = []
        for f in files:
            d = f.path.parent
            if d not in self.index:
                counts: dict[str, int] = {}
                for p in sorted(d.glob("*.blif*")):
                    h = cached("blifhash", CircuitFile(p.name.split(".")[0], p), blif_hash)
                    counts[h] = counts.get(h, 0) + 1
                self.index[d] = counts
            dup = self.index[d][cached("blifhash", f, blif_hash)] - 1
            rows.append([np.log1p(dup), *cached("style", f, style_counts)])
        return np.array(rows, dtype=float)

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
