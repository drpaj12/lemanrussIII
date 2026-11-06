"""From per-node suspicion scores to claims (the claim rule of the three-level score).

A claim is one Trojan the detector says it found, with up to MAX_CELLS named cells. The rule:

1. A circuit gets claims only if the detector flags it (circuit score >= the threshold set at
   5% false positives on validation circuits, as for the level 1 matrix).
2. Candidate cells are gates, latches and sub-circuits that drive a named net (not inputs, outputs
   or constants). Their node scores are turned into robust z-scores within the circuit
   (median and 1.4826 MAD; the standard deviation if the MAD is 0).
3. Cells with z >= z* are flagged; z* is chosen from Z_GRID on the VALIDATION fold only, as the
   value with the highest mean level 3 score of the flagged infected validation circuits (ties:
   the larger z*, fewer claims). If no cell reaches z*, the single best cell is flagged.
4. Adjacent flagged cells (joined by a wire, either direction) form one claim. The MAX_CLAIMS
   claims with the highest best z are kept (a circuit holds at most 3 Trojans); each names its
   MAX_CELLS best cells.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from lemanruss.detect.netlist import C_CONST, C_INPUT, C_OUTPUT, Netlist
from lemanruss.score import levels

Z_GRID = (1.0, 2.0, 3.0, 4.0, 5.0)
MAX_CLAIMS = 3
MAX_CELLS = 10
DEFAULT_Z = 3.0


def robust_z(x: np.ndarray) -> np.ndarray:
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med))) * 1.4826
    if mad < 1e-12:
        mad = max(float(np.std(x)), 1e-12)
    return np.asarray((x - med) / mad, dtype=float)


def candidates(nl: Netlist) -> np.ndarray:
    ok = np.array([bool(n) for n in nl.net_of], dtype=bool)
    return np.asarray(ok & ~np.isin(nl.cls, (C_INPUT, C_OUTPUT, C_CONST)))


def claims_from_scores(nl: Netlist, score: np.ndarray, z_star: float) -> list[list[str]]:
    """Claims (lists of net names, best first) for one flagged circuit."""
    cand = np.nonzero(candidates(nl))[0]
    if len(cand) == 0:
        return []
    s = np.nan_to_num(np.asarray(score, dtype=float)[cand], nan=-1e9, neginf=-1e9, posinf=1e9)
    z = robust_z(s)
    flag = z >= z_star
    if not flag.any():
        flag[int(np.argmax(z))] = True
    keep = cand[flag]
    zk = z[flag]
    pos = {int(v): i for i, v in enumerate(keep)}
    parent = list(range(len(keep)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in zip(nl.src, nl.dst, strict=True):
        if int(a) in pos and int(b) in pos:
            parent[find(pos[int(a)])] = find(pos[int(b)])
    groups: dict[int, list[int]] = {}
    for i in range(len(keep)):
        groups.setdefault(find(i), []).append(i)
    ranked = sorted(groups.values(), key=lambda m: -max(zk[i] for i in m))[:MAX_CLAIMS]
    out: list[list[str]] = []
    for m in ranked:
        best = sorted(m, key=lambda i: -zk[i])[:MAX_CELLS]
        out.append([nl.net_of[int(keep[i])] for i in best])
    return out


def tune_z(items: Sequence[tuple[Netlist, np.ndarray, Sequence[frozenset[str]]]],
           grid: Sequence[float] = Z_GRID) -> float:
    """z* from flagged infected validation circuits: (netlist, node scores, Trojan regions)."""
    if not items:
        return DEFAULT_Z
    best_z, best = DEFAULT_Z, -1.0
    for z in grid:
        tot = 0.0
        for nl, sc, regs in items:
            cl = tuple(frozenset(c) for c in claims_from_scores(nl, sc, z))
            tot += levels.circuit_score(levels.Circ("v", "v", tuple(regs), cl), 3)
        m = tot / len(items)
        if m >= best:
            best_z, best = z, m
    return best_z

