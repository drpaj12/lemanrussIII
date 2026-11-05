"""Register-matched combinational equivalence of two flat sequential BLIFs.

If a bijection pi between the latches of A and B exists such that, with the latch outputs cut and
matched ones tied to one free input, every primary output and every latch input of A equals its
counterpart in B, then A and B are sequentially equivalent from any common initial state (same
state update, same outputs). The check is sound but not complete (retimed or re-encoded state
fails it and the caller falls back to a sequential engine).

Initial values are read as `tools/equiv-check` reads them: 2 and 3 (don't care, unknown) count as
0, so the proof is equivalence from that initial state, the same claim as the dsec fallback. A
matched pair whose initial values still differ is cut in opposite phase (ABC may complement a
latch with init 1 and push the inverter into its fanin and fanout); that is accepted only if the
cut check then proves the netlists equal.

The bijection is a hint and is never trusted: ABC `cec` (through `tools/equiv-check`) proves the
cut netlists equal. Two hints are available for the Seeker-Proc build chain:

- Odin III's `abc` keeps the latch order of the BLIF it reads (`pairs_by_order`);
- `obfuscate.finalize` renames nets by a known map (`pairs_by_rename`).
"""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from lemanruss.htl.r4check import equiv_check_bin
from lemanruss.htl.verify import check_equivalence


@dataclass
class Flat:
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    names: list[tuple[list[str], str, list[str]]] = field(default_factory=list)  # ins, out, rows
    latches: list[tuple[str, str, str, str]] = field(default_factory=list)  # d, q, clock, init


class NotApplicable(Exception):
    """The netlists are outside what the register matcher handles (sub-circuits, loops, ...)."""


def parse_flat(text: str) -> Flat:
    f = Flat()
    cur: tuple[list[str], str, list[str]] | None = None
    for ln in text.replace("\\\n", " ").splitlines():
        w = ln.split()
        if not w or w[0].startswith("#"):
            continue
        if w[0] == ".inputs":
            f.inputs += w[1:]
        elif w[0] == ".outputs":
            f.outputs += w[1:]
        elif w[0] == ".names":
            cur = (w[1:-1], w[-1], [])
            f.names.append(cur)
        elif w[0] == ".latch":
            clk = w[4] if len(w) > 4 else ""
            init = w[5] if len(w) > 5 else (w[3] if len(w) == 4 and w[3] in "0123" else "3")
            f.latches.append((w[1], w[2], clk, init))
            cur = None
        elif w[0] in (".subckt", ".gate", ".mlatch"):
            raise NotApplicable(w[0])
        elif w[0] in (".model", ".end"):
            cur = None
        elif w[0][0] != ".":
            if cur is None:
                raise NotApplicable("cover row outside .names")
            cur[2].append(ln.strip())
    return f


def cut_text(f: Flat, order: list[int], tag: str, invert: frozenset[int] = frozenset()) -> str:
    """Combinational BLIF of `f` with latch k (in `order`) cut: output net -> input `__q{k}`,
    input net -> output `__d{k}`. Primary ports keep their names. For k in `invert` the latch is
    taken in the opposite phase: the cut input stands for the complement of the latch output and
    the cut output is the complement of the latch input."""
    qname = {f.latches[i][1]: f"__q{k}" for k, i in enumerate(order)}
    use = {f.latches[i][1]: (f"__q{k}n" if k in invert else f"__q{k}") for k, i in enumerate(order)}
    ins = [*f.inputs, *qname.values()]
    outs = [*f.outputs, *(f"__d{k}" for k in range(len(order)))]
    lines = [f".model {tag}", ".inputs " + " ".join(ins), ".outputs " + " ".join(outs)]
    for k in sorted(invert):
        lines += [f".names __q{k} __q{k}n", "0 1"]
    for q, qi in use.items():
        if q in f.outputs:
            lines += [f".names {qi} {q}", "1 1"]
    for gi, go, rows in f.names:
        lines.append(".names " + " ".join([use.get(n, n) for n in gi] + [go]))
        lines += rows
    for k, i in enumerate(order):
        d = f.latches[i][0]
        phase = "0 1" if k in invert else "1 1"
        lines += [f".names {use.get(d, d)} __d{k}", phase]
    lines.append(".end")
    return "\n".join(lines) + "\n"


def effective_init(init: str) -> str:
    """Initial value as `tools/equiv-check` reads it: 2 and 3 (don't care, unknown) are 0."""
    return init if init in ("0", "1") else "0"


def pairs_by_order(a: Flat, b: Flat) -> list[tuple[int, int]]:
    """Latch k of a with latch k of b."""
    if len(a.latches) != len(b.latches):
        raise NotApplicable("different latch counts")
    return [(k, k) for k in range(len(a.latches))]


def pairs_by_rename(a: Flat, b: Flat, rename: Mapping[str, str]) -> list[tuple[int, int]]:
    """Latch of a with the latch of b whose output is `rename[q]` (`q` itself when not renamed,
    e.g. a port)."""
    if len(a.latches) != len(b.latches):
        raise NotApplicable("different latch counts")
    where = {q: j for j, (_d, q, _c, _i) in enumerate(b.latches)}
    pairs: list[tuple[int, int]] = []
    for i, (_d, q, _c, _i) in enumerate(a.latches):
        j = where.get(rename.get(q, q))
        if j is None:
            raise NotApplicable(f"no latch for output {q}")
        pairs.append((i, j))
    if len({j for _i, j in pairs}) != len(pairs):
        raise NotApplicable("latch hint is not a bijection")
    return pairs


def cut_equivalent(a_text: str, b_text: str, hint: str, rename: Mapping[str, str] | None = None,
                   timeout: int = 900) -> None:
    """Proves a == b (sequentially, from the initial state read with 2/3 as 0) by the cut check
    under the latch matching `hint` ("order" or "rename"); returns normally on a proof, raises
    NotApplicable otherwise."""
    a, b = parse_flat(a_text), parse_flat(b_text)
    if sorted(a.inputs) != sorted(b.inputs) or sorted(a.outputs) != sorted(b.outputs):
        raise NotApplicable("port sets differ")
    pairs = pairs_by_order(a, b) if hint == "order" else pairs_by_rename(a, b, rename or {})
    # Initial values are read as equiv-check reads them (2 and 3 count as 0), so the claim is
    # equivalence from that initial state, the same as the dsec fallback. A matched pair whose
    # initial values then differ is tried in opposite phase (ABC may complement a latch with
    # init 1 to init 0 and push the inverter into its fanin and fanout): b's latch is cut as
    # the complement, so the initial values agree after the complement. The cut check is the
    # proof; a pair that is not really complemented fails it.
    invert = frozenset(
        k for k, (ia, ib) in enumerate(pairs)
        if effective_init(a.latches[ia][3]) != effective_init(b.latches[ib][3]))
    ca = cut_text(a, [p[0] for p in pairs], "a")
    cb = cut_text(b, [p[1] for p in pairs], "b", invert)
    with tempfile.TemporaryDirectory() as td:
        fa, fb = Path(td) / "a.blif", Path(td) / "b.blif"
        fa.write_text(ca, encoding="utf-8")
        fb.write_text(cb, encoding="utf-8")
        try:
            res = check_equivalence(equiv_check_bin(), fa, fb, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise NotApplicable("combinational check timed out") from exc
    if res.returncode != 0:
        raise NotApplicable(f"cut check did not prove equivalence (exit {res.returncode})")


def chain_equivalent(form_text: str, mapped_text: str, renames: Mapping[str, str],
                     source_text: str) -> None:
    """form == mapped (latches matched through `renames`) and mapped == source (same latch
    order, as Odin III's ABC keeps it); both cut checks must prove. Raises NotApplicable."""
    cut_equivalent(mapped_text, form_text, "rename", renames)
    cut_equivalent(source_text, mapped_text, "order")


__all__ = ["Flat", "NotApplicable", "parse_flat", "cut_text", "pairs_by_order",
           "pairs_by_rename", "cut_equivalent", "chain_equivalent"]
