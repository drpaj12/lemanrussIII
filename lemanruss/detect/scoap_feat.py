"""SCOAP and signal probability of a released circuit from Odin III (`scoap` pass, read only)."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from lemanruss.detect.data import read_text

SIGPROB_VECTORS = 4096
SIGPROB_SEED = 1
CAP = 1e9  # INF (1e18) and SAT-saturated values are capped before any log


@dataclass
class ScoapFeat:
    names: list[str]
    cc0: np.ndarray
    cc1: np.ndarray
    co: np.ndarray
    p1: np.ndarray  # P(net = 1), NaN where the simulator did not list the net
    sigprob_ran: bool
    sequential: bool


def scoap_arrays(path: Path) -> ScoapFeat:
    """Run `scoap` (sequential when the circuit has latches) with 4096 random vectors, seed 1."""
    from odin3 import Design

    text = read_text(path)
    sequential = "\n.latch" in text
    with tempfile.TemporaryDirectory() as tmp:
        blif = Path(tmp) / "c.blif"
        blif.write_text(text, encoding="utf-8")
        with Design() as design:
            design.run_pass("read_blif", str(blif))
            res = design.scoap(sequential=sequential, sigprob=SIGPROB_VECTORS, seed=SIGPROB_SEED)
    nets = res["modules"][0]["nets"]
    ran = int(res.get("sigprob_vectors", 0)) > 0 and bool(res.get("sigprob_ran", True))
    p1 = np.array([n.get("p1_ppm", -1) for n in nets], dtype=float)
    p1 = np.where(p1 < 0, np.nan, p1 / 1e6)
    return ScoapFeat(
        [str(n["name"]) for n in nets],
        np.minimum(np.array([n["cc0"] for n in nets], dtype=float), CAP),
        np.minimum(np.array([n["cc1"] for n in nets], dtype=float), CAP),
        np.minimum(np.array([n["co"] for n in nets], dtype=float), CAP),
        p1, ran, sequential,
    )
