"""BLIF parser for detectors: data-flow graph, gate classes, size statistics (spec section 4).

Only the released file is read. Names are used to join nets to graph nodes, never as features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from lemanruss.detect.data import read_text

# node classes (17, spec 4.3)
(C_INPUT, C_OUTPUT, C_LATCH, C_CONST, C_BUF, C_INV, C_AND, C_NAND, C_OR, C_NOR, C_XOR, C_XNOR,
 C_MUX, C_OTHER2, C_OTHER3, C_OTHER4, C_SUBCKT) = range(17)
N_CLASSES = 17
MAX_TT_INPUTS = 6


@dataclass
class Netlist:
    cls: np.ndarray  # node class, int8
    k: np.ndarray  # input count of the cell
    rows: np.ndarray  # cover rows of a .names (0 otherwise)
    src: np.ndarray  # edges driver -> reader
    dst: np.ndarray
    net_of: list[str] = field(default_factory=list)  # output net name per node ("" for PO)
    n_gates: int = 0
    n_ffs: int = 0
    depth: int = 0
    n_models: int = 1

    @property
    def n_nodes(self) -> int:
        return len(self.cls)


def _logical_lines(text: str) -> list[list[str]]:
    out: list[list[str]] = []
    pending = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        line = pending + line
        pending = ""
        if line.strip():
            out.append(line.split())
    return out


def truth_table(rows: list[tuple[str, str]], k: int) -> int | None:
    """Truth table as a bit mask over the 2^k input assignments (None when k is too large)."""
    if k > MAX_TT_INPUTS:
        return None
    on = 0
    off_rows = rows and rows[0][1] == "0"
    for pat, _val in rows:
        for a in range(1 << k):
            if all(pat[i] == "-" or int(pat[i]) == (a >> i) & 1 for i in range(k)):
                on |= 1 << a
    full = (1 << (1 << k)) - 1
    return (full & ~on) if off_rows else on


def classify(rows: list[tuple[str, str]], k: int) -> int:
    if k == 0:
        return C_CONST
    tt = truth_table(rows, k)
    if tt is None:
        return C_OTHER4
    n = 1 << k
    full = (1 << n) - 1
    if k == 1:
        return C_BUF if tt == 0b10 else C_INV if tt == 0b01 else C_CONST
    and_tt = 1 << (n - 1)
    or_tt = full & ~1
    par = 0
    for a in range(n):
        if bin(a).count("1") % 2:
            par |= 1 << a
    table = {and_tt: C_AND, full & ~and_tt: C_NAND, or_tt: C_OR, 1: C_NOR}
    if tt in table:
        return table[tt]
    if tt == par:
        return C_XOR
    if tt == full & ~par:
        return C_XNOR
    if tt in (0, full):
        return C_CONST
    if k == 3 and _is_mux(tt):
        return C_MUX
    return C_OTHER2 if k == 2 else C_OTHER3 if k == 3 else C_OTHER4


def _is_mux(tt: int) -> bool:
    """s ? a : b for some assignment of the three inputs to s, a, b (a, b not negated)."""
    for s in range(3):
        a, b = [i for i in range(3) if i != s]
        for ta, tb in ((a, b), (b, a)):
            want = 0
            for x in range(8):
                v = (x >> ta) & 1 if (x >> s) & 1 else (x >> tb) & 1
                want |= v << x
            if want == tt:
                return True
    return False


def parse(path: Path) -> Netlist:
    """All models of the file as one graph (disjoint union; a `.subckt` stays one node of its
    parent), so a Trojan inside a submodule is visible."""
    lines = _logical_lines(read_text(path))
    models: list[list[list[str]]] = []
    for ln in lines:
        if ln[0] == ".model":
            models.append([])
        if models:
            models[-1].append(ln)
    n_gates = sum(ln[0] == ".names" and len(ln) > 2 for m in models for ln in m)
    n_ffs = sum(ln[0] == ".latch" for m in models for ln in m)
    parts = [_model(m) for m in models]
    offs = np.cumsum([0] + [len(p[0]) for p in parts])
    nl = Netlist(
        np.concatenate([p[0] for p in parts]).astype(np.int8),
        np.concatenate([p[1] for p in parts]).astype(np.int32),
        np.concatenate([p[2] for p in parts]).astype(np.int32),
        np.concatenate([p[4] + o for p, o in zip(parts, offs, strict=False)]).astype(np.int64),
        np.concatenate([p[5] + o for p, o in zip(parts, offs, strict=False)]).astype(np.int64),
        [x for p in parts for x in p[3]], n_gates, n_ffs, 0, len(models),
    )
    nl.depth = _depth(nl)
    return nl


Part = tuple[np.ndarray, np.ndarray, np.ndarray, list[str], np.ndarray, np.ndarray]


def _model(top: list[list[str]]) -> Part:
    cls: list[int] = []
    ks: list[int] = []
    rws: list[int] = []
    outnet: list[str] = []
    readers: list[tuple[int, list[str]]] = []  # node, input nets
    subckt_pins: list[tuple[int, list[str]]] = []
    driver: dict[str, int] = {}
    pos: list[str] = []

    def add(c: int, k: int, rows: int, net: str) -> int:
        cls.append(c)
        ks.append(k)
        rws.append(rows)
        outnet.append(net)
        return len(cls) - 1

    i = 0
    while i < len(top):
        ln = top[i]
        key = ln[0]
        if key == ".inputs":
            for net in ln[1:]:
                driver[net] = add(C_INPUT, 0, 0, net)
        elif key == ".outputs":
            pos += ln[1:]
        elif key == ".names":
            nets = ln[1:]
            rows: list[tuple[str, str]] = []
            while i + 1 < len(top) and not top[i + 1][0].startswith("."):
                i += 1
                r = top[i]
                rows.append(("", r[0]) if len(r) == 1 else (r[0], r[1]))
            k = len(nets) - 1
            c = classify(rows, k)
            node = add(c, k, len(rows), nets[-1])
            driver[nets[-1]] = node
            readers.append((node, nets[:-1]))
        elif key in (".latch", ".mlatch"):
            node = add(C_LATCH, 1, 0, ln[2])
            driver[ln[2]] = node
            readers.append((node, [ln[1]]))
        elif key == ".subckt":
            node = add(C_SUBCKT, len(ln) - 2, 0, "")
            subckt_pins.append((node, [p.split("=", 1)[1] for p in ln[2:] if "=" in p]))
        i += 1
    for node, pins in subckt_pins:  # undriven pin nets are outputs of the subckt
        ins = []
        for net in pins:
            if net in driver:
                ins.append(net)
            else:
                driver[net] = node
                if not outnet[node]:
                    outnet[node] = net
        readers.append((node, ins))
    for net in pos:
        node = add(C_OUTPUT, 1, 0, "")
        readers.append((node, [net]))
    src: list[int] = []
    dst: list[int] = []
    for node, nets in readers:
        for net in nets:
            d = driver.get(net)
            if d is not None and d != node:
                src.append(d)
                dst.append(node)
    return (np.array(cls, dtype=np.int8), np.array(ks, dtype=np.int32),
            np.array(rws, dtype=np.int32), outnet, np.array(src, dtype=np.int64),
            np.array(dst, dtype=np.int64))


def _depth(nl: Netlist) -> int:
    """Longest combinational path in cells; latch outputs and inputs start at 0, edges into a
    latch end the path. Cells left in a combinational loop are ignored."""
    n = nl.n_nodes
    keep = nl.cls[nl.dst] != C_LATCH
    s, d = nl.src[keep], nl.dst[keep]
    indeg = np.bincount(d, minlength=n)
    order = np.argsort(s, kind="stable")
    s_sorted, d_sorted = s[order], d[order]
    start = np.searchsorted(s_sorted, np.arange(n + 1))
    level = np.zeros(n, dtype=np.int64)
    stack = [int(v) for v in np.nonzero(indeg == 0)[0]]
    best = 0
    while stack:
        v = stack.pop()
        lv = level[v] + (1 if nl.cls[v] not in (C_INPUT, C_OUTPUT, C_LATCH, C_CONST) else 0)
        best = max(best, int(lv))
        for w in d_sorted[start[v] : start[v + 1]]:
            level[w] = max(level[w], lv)
            indeg[w] -= 1
            if indeg[w] == 0:
                stack.append(int(w))
    return best
