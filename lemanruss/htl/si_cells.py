"""Seeker-Si (spec docs/specs/2026-11-05-seeker-si.md section 4, step 6): a finished gates-as-names
BLIF of sky130_fd_sc_hd cells written as a structural Verilog netlist of those cells, and read back.

Odin III's `write_blif --gates-as-names` gives one `.names` per cell and drops the cell type. The
type is recovered here from the cover's truth table against the cells of `lib/sky130hd.o3lib`
(the silicon flow's own library); the Verilog route of `write_verilog` carries `src` attributes
and the design's names, which the release must not. A cover that no cell implements is an error,
never guessed. Pin names are the library's, which are the SKY130 Verilog model's.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from lemanruss.htl.obfuscate import parse, sky130_lib

PREFIX = "sky130_fd_sc_hd__"
DFF = PREFIX + "dfxtp_1"
CONB = PREFIX + "conb_1"


@dataclass(frozen=True)
class Cell:
    name: str
    area: float
    ins: tuple[str, ...]
    out: str
    fn: str


@cache
def library(path: str = "") -> dict[str, Cell]:
    """Combinational cells of the o3lib, by name (the flip-flop is not in this map)."""
    text = Path(path or sky130_lib()).read_text(encoding="utf-8")
    cells: dict[str, Cell] = {}
    name, area, fn, out = "", 0.0, "", ""
    ins: list[str] = []
    for ln in text.splitlines():
        w = ln.split()
        if not w:
            continue
        if w[0] == "cell":
            name, area, fn, out, ins = w[1], float(w[-1]), "", "", []
        elif w[0] == "end":
            if name and fn:
                cells[name] = Cell(name, area, tuple(ins), out, fn)
            name = ""
        else:
            for part in ln.split(";"):
                p = part.split()
                if len(p) >= 2 and p[0] == "in":
                    ins.append(p[1])
                elif len(p) >= 2 and p[0] == "out":
                    out = p[1]
                elif len(p) >= 4 and p[0] == "fn":
                    fn = " ".join(p[3:])
    return cells


def _eval_fn(fn: str, vals: dict[str, int]) -> int:
    """Value of an o3lib `fn` expression (`~`, `&`, `|`, parentheses, pin names)."""
    toks = fn.replace("(", " ( ").replace(")", " ) ").replace("~", " ~ ").split()
    pos = 0

    def or_() -> int:
        nonlocal pos
        v = and_()
        while pos < len(toks) and toks[pos] == "|":
            pos += 1
            v |= and_()
        return v

    def and_() -> int:
        nonlocal pos
        v = not_()
        while pos < len(toks) and toks[pos] == "&":
            pos += 1
            v &= not_()
        return v

    def not_() -> int:
        nonlocal pos
        t = toks[pos]
        pos += 1
        if t == "~":
            return 1 - not_()
        if t == "(":
            v = or_()
            pos += 1  # the closing parenthesis
            return v
        return vals[t]

    return or_()


def _cell_value(c: Cell, vals: dict[str, int]) -> int:
    return _eval_fn(c.fn, vals)


@cache
def _match_table(path: str = "") -> dict[tuple[int, int], tuple[Cell, tuple[int, ...]]]:
    """(n inputs, truth table over cover inputs 0..n-1) -> (cell, pin index per cover input)."""
    table: dict[tuple[int, int], tuple[Cell, tuple[int, ...]]] = {}
    for c in sorted(library(path).values(), key=lambda x: (x.area, x.name)):
        n = len(c.ins)
        for perm in itertools.permutations(range(n)):
            tt = 0
            for m in range(1 << n):
                vals = {c.ins[perm[k]]: (m >> k) & 1 for k in range(n)}
                tt |= _cell_value(c, vals) << m
            table.setdefault((n, tt), (c, perm))
    return table


def cover_tt(n: int, rows: list[str]) -> int:
    """Truth table (bit m = value at minterm m, cover input k = bit k of m) of a `.names` cover."""
    on = off = 0
    for r in rows:
        w = r.split()
        pat, val = (w[0], w[1]) if n else ("", w[0])
        for m in range(1 << n):
            if all(ch == "-" or int(ch) == (m >> k) & 1 for k, ch in enumerate(pat)):
                if val == "1":
                    on |= 1 << m
                else:
                    off |= 1 << m
    full = (1 << (1 << n)) - 1
    return on if on or not off else full & ~off


def _ident(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"\\{name} "


def _bus(name: str) -> tuple[str, int] | None:
    m = re.fullmatch(r"(.+)\[(\d+)\]", name)
    return (m.group(1), int(m.group(2))) if m else None


def _ports(names: list[str]) -> list[tuple[str, int, int]]:
    """(base, hi, lo) per port in first-seen order; a bus must have contiguous bits."""
    order: list[str] = []
    bits: dict[str, list[int]] = {}
    for n in names:
        b = _bus(n)
        key = b[0] if b else n
        if key not in bits:
            order.append(key)
            bits[key] = []
        bits[key].append(b[1] if b else -1)
    out: list[tuple[str, int, int]] = []
    for key in order:
        v = bits[key]
        if v == [-1]:
            out.append((key, -1, -1))
        elif -1 not in v and sorted(v) == list(range(min(v), max(v) + 1)):
            out.append((key, max(v), min(v)))
        else:
            raise ValueError(f"port {key}: bits {sorted(v)} are not a plain bus")
    return out


def blif_to_verilog(text: str, module: str = "top", inst_order: list[int] | None = None) -> str:
    """Structural Verilog of a finished BLIF. `inst_order` is a permutation of the instance
    indices (the caller shuffles it); instances are named `u<k>`, k the position in the BLIF."""
    inputs, outputs, blocks = parse(text)
    table = _match_table()
    insts: list[str] = []
    nets: set[str] = set()
    clocks: set[str] = set()
    for k, b in enumerate(blocks):
        w = b[0].split()
        if w[0] == ".latch":
            d, q, clk = w[1], w[2], (w[4] if len(w) > 4 else "")
            clk = w[4] if len(w) >= 5 and w[3] in ("re", "fe", "ah", "al", "as") else clk
            clocks.add(clk)
            insts.append(f"  {DFF} u{k} (.CLK({_ref(clk)}), .D({_ref(d)}), .Q({_ref(q)}));")
            nets |= {d, q}
            continue
        ins, out = w[1:-1], w[-1]
        rows = b[1:]
        nets.add(out)
        nets.update(ins)
        tt = cover_tt(len(ins), rows)
        if not ins:
            pin = "HI" if tt & 1 else "LO"
            insts.append(f"  {CONB} u{k} (.{pin}({_ref(out)}));")
            continue
        hit = table.get((len(ins), tt))
        if hit is None:
            raise ValueError(f"cover for {out} ({len(ins)} inputs) is not a library cell")
        cell, perm = hit
        pins = ", ".join(f".{cell.ins[perm[i]]}({_ref(n)})" for i, n in enumerate(ins))
        insts.append(f"  {cell.name} u{k} ({pins}, .{cell.out}({_ref(out)}));")
    ports = {n for n in inputs} | set(outputs)
    port_bases = {(_bus(n) or (n, 0))[0] for n in ports}
    head_in = _ports(inputs)
    head_out = _ports(outputs)
    hdr = []
    for base, hi, lo in head_in:
        hdr.append(f"input {'' if hi < 0 else f'[{hi}:{lo}] '}{_ident(base)}")
    for base, hi, lo in head_out:
        hdr.append(f"output {'' if hi < 0 else f'[{hi}:{lo}] '}{_ident(base)}")
    wires = sorted(n for n in nets if n not in ports and (_bus(n) or (n, 0))[0] not in port_bases
                   and n not in clocks)
    order = inst_order if inst_order is not None else list(range(len(insts)))
    lines = [f"module {module} (", "  " + ",\n  ".join(hdr), ");"]
    lines += [f"  wire {_ident(n)};" for n in wires]
    lines += [insts[i] for i in order]
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def _ref(name: str) -> str:
    b = _bus(name)
    return f"{_ident(b[0])}[{b[1]}]" if b else _ident(name)


_INST = re.compile(r"^\s*(sky130_fd_sc_hd__\w+)\s+(\w+)\s*\((.*)\);\s*$")
_PIN = re.compile(r"\.(\w+)\(((?:\\\S+ )|[^()]*?)\)")


def verilog_to_blif(text: str, inputs: list[str], outputs: list[str]) -> str:
    """BLIF (covers from the library functions) of a netlist written by `blif_to_verilog`; the
    input and output lists give the BLIF port order. Used to check the writer round-trips."""
    lib = library()
    body: list[str] = []
    for ln in text.splitlines():
        m = _INST.match(ln)
        if not m:
            continue
        typ, _name, rest = m.groups()
        pins = {p: v.strip().lstrip("\\").strip() for p, v in _PIN.findall(rest)}
        if typ == DFF:
            body.append(f".latch {pins['D']} {pins['Q']} re {pins['CLK']} 2")
        elif typ == CONB:
            if "HI" in pins:
                body += [f".names {pins['HI']}", "1"]
            else:
                body.append(f".names {pins['LO']}")
        else:
            c = lib[typ]
            n = len(c.ins)
            rows = []
            for mm in range(1 << n):
                vals = {c.ins[k]: (mm >> k) & 1 for k in range(n)}
                if _cell_value(c, vals):
                    rows.append("".join(str(vals[p]) for p in c.ins) + " 1")
            body += [".names " + " ".join(pins[p] for p in c.ins) + f" {pins[c.out]}", *rows]
    return "\n".join([".model top", ".inputs " + " ".join(inputs),
                      ".outputs " + " ".join(outputs), *body, ".end"]) + "\n"



def _canon(text: str) -> dict[str, tuple[object, ...]] | None:
    """Per driven net: its function over the sorted fanin names (a flip-flop: its D net). None
    when a net has two drivers or a cover has more than 8 inputs."""
    from lemanruss.htl.obfuscate import parse

    _ins, _outs, blocks = parse(text)
    out: dict[str, tuple[object, ...]] = {}
    val: tuple[object, ...]
    for blk in blocks:
        w = blk[0].split()
        if w[0] == ".latch":
            key, val = w[2], ("L", w[1])
        else:
            nets = w[1:-1]
            n = len(nets)
            if n > 8:
                return None
            tt = cover_tt(n, blk[1:])
            order = sorted(range(n), key=lambda i: nets[i])
            canon = 0
            for m in range(1 << n):
                src = sum(((m >> j) & 1) << order[j] for j in range(n))
                canon |= ((tt >> src) & 1) << m
            key, val = w[-1], ("N", tuple(nets[i] for i in order), canon)
        if key in out:
            return None
        out[key] = val
    return out


def same_network(a: str, b: str) -> bool:
    """True when both BLIFs drive the same nets with the same functions of the same fanin nets,
    so they are the same network (a proof of equivalence needing no solver)."""
    ca, cb = _canon(a), _canon(b)
    return ca is not None and ca == cb
