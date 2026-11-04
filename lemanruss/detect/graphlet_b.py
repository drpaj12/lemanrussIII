"""Method B (s6-methods.tex): directed graphlet drift against the clean identity reference.

Signature = the 129 directed orbit totals of Odin III's `graphlets --directed --exclude-global
--global-fanout 16` pass (no second counter; nets of fanout above 16 are left out).
d(c) = ||s(c) - s(r)||_1 / ||s(r)||_1; z per form from the clean circuits of the
training bases (sigma floored at 1e-3). The identity form is flagged when d > 0 (exact).
A form with no training clean circuits (the unseen LUT forms) uses the pooled statistics of all
training non-identity forms, which is what an unseen restructuring costs this method.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile, ReferencedFile, read_text
from lemanruss.detect.features import cached, fill
from lemanruss.detect.isolated import isolated

SIGMA_FLOOR = 1e-3


def signature(path: Path) -> np.ndarray:
    from odin3 import Design

    with tempfile.TemporaryDirectory() as tmp:
        blif = Path(tmp) / "c.blif"
        blif.write_text(read_text(path), encoding="utf-8")
        with Design() as design:
            design.run_pass("read_blif", str(blif))
            res = design.graphlets(directed=True, exclude_global=True, global_fanout=16)
    return np.array(res["groups"][0]["orbit_totals"], dtype=np.int64)


def safe_signature(path: Path) -> np.ndarray | None:
    out = isolated("glet", path)
    return out if isinstance(out, np.ndarray) else None


def drift(sig: np.ndarray, ref: np.ndarray) -> float:
    return float(np.abs(sig - ref).sum() / max(int(np.abs(ref).sum()), 1))


class GraphletB(Detector):
    name = "graphlet-b"
    needs_reference = True

    def __init__(self) -> None:
        self.stats: dict[str, tuple[float, float]] = {}
        self.pooled = (0.0, SIGMA_FLOOR)

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        paths = list(circuits)
        for c in circuits:
            if isinstance(c, ReferencedFile):
                paths.append(CircuitFile(c.reference.name.split(".")[0], c.reference))
        fill("glet2", paths, safe_signature)

    def _d(self, c: ReferencedFile) -> float:
        ref = CircuitFile(c.reference.name.split(".")[0], c.reference)
        a = cached("glet2", c, safe_signature)
        b = cached("glet2", ref, safe_signature)
        return float("nan") if a is None or b is None else drift(a, b)

    def fit(self, train: Sequence[CircuitFile], y_train: Sequence[int],
            val: Sequence[CircuitFile], y_val: Sequence[int], seed: int) -> None:
        per_form: dict[str, list[float]] = {}
        for c, y in zip(train, y_train, strict=True):
            if y == 0 and isinstance(c, ReferencedFile):
                d = self._d(c)
                if d == d:
                    per_form.setdefault(c.form, []).append(d)
        self.stats = {
            f: (float(np.mean(v)), max(float(np.std(v)), SIGMA_FLOOR)) for f, v in per_form.items()
        }
        rest = [x for f, v in per_form.items() if f != "identity" for x in v]
        if rest:
            self.pooled = (float(np.mean(rest)), max(float(np.std(rest)), SIGMA_FLOOR))

    def score(self, circuits: Sequence[CircuitFile]) -> list[float]:
        out = []
        for c in circuits:
            assert isinstance(c, ReferencedFile)
            d = self._d(c)
            if d != d:  # NaN: Odin III refused or timed out on this circuit
                out.append(d)
                continue
            mu, sd = self.stats.get(c.form, self.pooled)
            out.append((d - mu) / sd)
        return out
