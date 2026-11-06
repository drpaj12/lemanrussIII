"""Rare-signal / SCOAP score in the line of COTD (salmani2017cotd). Not a reproduction: the COTD
text was not read. Score = share of nets that are joint robust outliers in controllability and
observability (both robust z > 3 within the circuit) + share of nets with min(p, 1-p) < 0.01.

Circularity: the benchmark's site selection ranks nets by SCOAP and signal probability, so this
score can see an inserted trigger by construction (docs/specs/2026-11-01-*, section 4.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile
from lemanruss.detect.features import cached, fill
from lemanruss.detect.isolated import isolated
from lemanruss.detect.scoap_feat import ScoapFeat

Z_CUT = 3.0
RARE_P = 0.01


def robust_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x)
    mad = np.median(np.abs(x - med)) * 1.4826
    if mad < 1e-12:
        mad = max(float(np.std(x)), 1e-12)
    return np.asarray((x - med) / mad, dtype=float)


def rare_score(f: ScoapFeat) -> float:
    if len(f.names) == 0:
        return 0.0
    ctrl = np.log1p(np.maximum(f.cc0, f.cc1))
    obs = np.log1p(f.co)
    joint = (robust_z(ctrl) > Z_CUT) & (robust_z(obs) > Z_CUT)
    score = float(joint.mean())
    p = f.p1[~np.isnan(f.p1)]
    if f.sigprob_ran and len(p):
        score += float((np.minimum(p, 1 - p) < RARE_P).mean())
    return score


def safe_scoap(path: Path) -> ScoapFeat | None:
    out = isolated("scoap", path)
    return out if isinstance(out, ScoapFeat) else None


def rare_node_scores(f: ScoapFeat) -> dict[str, float]:
    """Per net: the lower of its controllability and observability outlier z-scores, plus 4 if
    its signal probability is rarer than RARE_P (the two parts of `rare_score`)."""
    if len(f.names) == 0:
        return {}
    z = np.minimum(robust_z(np.log1p(np.maximum(f.cc0, f.cc1))), robust_z(np.log1p(f.co)))
    rare = np.zeros(len(f.names))
    if f.sigprob_ran:
        p = np.nan_to_num(f.p1, nan=0.5)
        rare = (np.minimum(p, 1 - p) < RARE_P).astype(float)
    sc = z + 4.0 * rare
    return {n: float(v) for n, v in zip(f.names, sc, strict=True)}


class RareScoap(Detector):
    name = "rare"
    localises = True

    def node_scores(self, circuit: CircuitFile) -> np.ndarray | None:
        from lemanruss.detect.netlist import parse

        f = cached("scoap", circuit, safe_scoap)
        if f is None:
            return None
        per = rare_node_scores(f)
        nl = parse(circuit.path)
        lo = min(per.values(), default=0.0)
        return np.array([per.get(n, lo) for n in nl.net_of], dtype=float)

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        fill("scoap", circuits, safe_scoap)

    def score(self, circuits: Sequence[CircuitFile]) -> list[float]:
        out = []
        for c in circuits:
            f = cached("scoap", c, safe_scoap)
            out.append(float("nan") if f is None else rare_score(f))
        return out
