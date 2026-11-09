"""Cut-and-stitch: keeps the parts ABC would otherwise destroy (round 9, rc5 Comb / rc6 Seq).

Spec: docs/specs/2026-11-01-seeker-n200-design.md section 13. Peter, 2026-11-02, verbatim:
"except for our previous seeker's dilemma. We cut out what couldn't be handled by other tools and
then reinserted it by making the outputs or the inputs to the part we can as primary outputs and
the outputs as primary inputs. Could we do this for the parts that get destroyed by ABC?"

Method: for each part of a circuit that a check shows ABC destroys (the energy ring: no net reads
its state, so any logic optimiser removes it as dead code; a dummy region drawn only to carry no
label), the nets crossing the cut become extra primary outputs (host nets the part reads) and
extra primary inputs (part nets the host reads) of the host; the host goes through one random ABC
script with those extra ports; each such part is mapped on its own the same way, with its own
boundary as primary inputs/outputs so ABC keeps it; the pieces are stitched back on the boundary
nets (which keep their exact names across both runs, so simply holding the blocks together wires
them) and the whole stitched text goes through the usual `obfuscate.finalize` once, so the
boundary nets are renamed like any other internal net and carry no trace of the cut.

Finding (tested on the smoke bases; not a claim about how Seeker v1 was built). This defeats
dead-code elimination, but not identity-buffer collapse: ABC's AIG (`strash`) has no node for
`a = b`, so a chain of 1-input buffers collapses to a wire whether or not its ends are primary
outputs. Carrying the buffer chain through unmapped (tried first) keeps its depth but is a label:
the gate `g_style` found "any buffer" / "double buffer" at AUROC 0.74 on the smoke Comb build. The
slowdown payload is therefore an absorption stage that no tool reduces without the host: the
victim is `tmp | (tmp & s_1) | ... | (tmp & s_m)` (= `tmp`), the ANDs stay in the host (their
inputs are `tmp` and primary inputs / latch outputs) and only the OR is cut, so the cut's
inputs are independent nets and ABC cannot fold it, while no buffer appears.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from lemanruss.htl import obfuscate as ob

Block = list[str]
Json = dict[str, object]


def _io(block: Block) -> tuple[list[str], str]:
    """(inputs, output) of a `.names` or `.latch` block; a latch's clock is not an input here
    (clocks are shared globally, never a cut boundary net)."""
    w = block[0].split()
    if w[0] == ".latch":
        return [w[1]], w[2]
    return w[1:-1], w[-1]


def _producers(blocks: list[Block]) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, b in enumerate(blocks):
        out[_io(b)[1]] = i
    return out


def _consumers(blocks: list[Block]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, b in enumerate(blocks):
        for n in _io(b)[0]:
            out.setdefault(n, []).append(i)
    return out


@dataclass
class Cut:
    """One cut: the block indices removed from the host, and the nets crossing it."""

    idx: set[int]
    boundary_in: list[str]  # host nets the cut reads (cut's primary inputs)
    boundary_out: list[str]  # cut nets the host (or the top module) reads (cut's primary outputs)
    extra_out: list[str] = field(default_factory=list)  # cut-local only; kept alive, then dropped


@dataclass
class CutSpec:
    cut: Cut
    run_abc: bool  # False: carried through unmapped (identity chains ABC would collapse anyway)
    label: str


def energy_cut(blocks: list[Block], j: int, n_bits: int) -> Cut:
    """The ring of Trojan `j` (`edit_netlist.energy`): its bits have no other reader, so they are
    also the cut's own primary outputs (`extra_out`), kept alive for its standalone ABC run."""
    p = f"__htl_energy{j}"
    outs = {f"{p}_d{i}" for i in range(n_bits)} | {f"{p}_q{i}" for i in range(n_bits)}
    prod = _producers(blocks)
    idx = {prod[o] for o in outs if o in prod}
    trig = f"__htl_trigger_{j}"
    return Cut(idx, [trig], [], [f"{p}_q{i}" for i in range(n_bits) if f"{p}_q{i}" in prod])


def slowdown_cut(blocks: list[Block], victim: str) -> Cut:
    """The OR of a slowdown payload (`edit_netlist.slowdown_absorb`): its
    inputs are the net `splice` moved the old driver to and the `m` AND terms (host cells), its
    output is `victim`, which the host reads downstream as before."""
    prod = _producers(blocks)
    if victim not in prod:
        return Cut(set(), [], [victim])
    region = {prod[victim]}
    cons = _consumers(blocks)
    _close_latches(region, blocks, prod, cons)
    return _boundary_of(region, [], blocks, cons)


def dummy_cut(
    inputs: list[str], outputs: list[str], blocks: list[Block], rng: random.Random, size: int
) -> Cut | None:
    """A random connected region of about `size` blocks, grown backward (toward producers) from
    a primary output, so its boundary is never empty: `boundary_out` always holds that output.
    None when the circuit has no output a block drives (nothing to cut)."""
    prod = _producers(blocks)
    cons = _consumers(blocks)
    roots = [o for o in outputs if o in prod]
    if not roots:
        return None
    root = rng.choice(roots)
    region = {prod[root]}
    frontier = [prod[root]]
    while len(region) < size and frontier:
        i = frontier.pop(rng.randrange(len(frontier)))
        ins, _out = _io(blocks[i])
        cands = [prod[n] for n in ins if n in prod and prod[n] not in region]
        rng.shuffle(cands)
        for c in cands:
            if len(region) >= size:
                break
            region.add(c)
            frontier.append(c)
    del inputs
    _close_latches(region, blocks, prod, cons)
    return _boundary_of(region, outputs, blocks, cons)


def _close_latches(
    region: set[int], blocks: list[Block], prod: dict[str, int], cons: dict[str, list[int]]
) -> None:
    """Grows `region` until no latch sits on the cut with a bare net on the other side. A latch
    whose D is a primary input of its piece, or whose Q is a primary output of its piece, gets a
    buffer from ABC's gate mapping (`map`): "latch D driven by a buffer" is the rc5 gate
    `lat_dkind_buf`, and a cut would otherwise add it to the cut circuits only (smoke: 28 of 30
    cut s27 circuits against 0 of 30 plain). So: a latch inside the region takes the block that
    drives its D with it; a latch outside whose D is a region output joins the region; a latch
    that a region block reads joins the region; a net that is both a latch's D and a boundary net
    (a port of the piece) is buffered the same way, so its other readers / the latch join too."""
    latch = [i for i, b in enumerate(blocks) if b[0].startswith(".latch")]
    for _ in range(len(blocks)):
        grew = False
        outs = {_io(blocks[i])[1] for i in region}
        reads = {n for i in region for n in _io(blocks[i])[0]}
        for i in latch:
            d, q = _io(blocks[i])[0][0], _io(blocks[i])[1]
            if i in region:
                if d in prod and prod[d] not in region:
                    region.add(prod[d])
                    grew = True
                outside = [c for c in cons.get(d, []) if c not in region]
                if outside:  # D is also a boundary net: gates mode buffers it
                    region.update(outside)
                    grew = True
            elif d in outs or d in reads or any(c in region for c in cons.get(q, [])):
                region.add(i)
                grew = True
        if not grew:
            return


def _boundary_of(
    region: set[int], outputs: list[str], blocks: list[Block], cons: dict[str, list[int]]
) -> Cut:
    region_outs = {_io(blocks[i])[1] for i in region}
    b_in: list[str] = []
    for i in sorted(region):
        for n in _io(blocks[i])[0]:
            if n not in region_outs and n not in b_in:
                b_in.append(n)
    out_set = set(outputs)
    b_out: list[str] = []
    for n in sorted(region_outs):
        read_outside = any(c not in region for c in cons.get(n, []))
        if (n in out_set or read_outside) and n not in b_out:
            b_out.append(n)
    return Cut(region, b_in, b_out)


def _map_part(path: Path, kind: str, rng: random.Random, work: Path, tag: str) -> tuple[
        str, str] | str:
    """`obfuscate.obfuscate` without the final `finalize`: the shuffle/rename must happen exactly
    once, after every part is stitched back, or boundary net names would drift apart."""
    script = ob.random_script(rng, kind)
    try:
        text = ob.map_with_odin(path, kind, script, work, tag)
    except Exception as exc:
        return f"obfuscate {kind}: {type(exc).__name__}: {str(exc)[:100]}"
    return text, script


def _private(
    inputs: list[str], outputs: list[str], blocks: list[Block], prefix: str
) -> list[Block]:
    """`blocks` with every net that is neither a port of this piece nor a latch clock renamed
    `<prefix><net>`: two ABC runs each name their internal nets `n1`, `n2`, ..., and stitching
    them without this would drive one net from two pieces. Boundary nets are ports of both
    pieces and keep their name."""
    ports = set(inputs) | set(outputs)
    out: list[Block] = []
    for b in blocks:
        w = b[0].split()
        if w[0] == ".latch":
            w[1], w[2] = (n if n in ports else prefix + n for n in (w[1], w[2]))
        else:
            w = [w[0], *(n if n in ports else prefix + n for n in w[1:])]
        out.append([" ".join(w), *b[1:]])
    return out


def cut_and_stitch(
    src: Path, kind: str, rng: random.Random, work: Path, tag: str, cuts: list[CutSpec],
) -> tuple[str, str] | str:
    """Drop-in replacement for `obfuscate.obfuscate` when `cuts` is non-empty: partitions `src`
    into a host and one sub-circuit per `CutSpec`, maps the host once (with every cut's boundary
    added as extra primary inputs/outputs) and each ABC-mapped cut on its own, carries the
    non-ABC cuts through unmapped, stitches the blocks back on the boundary net names, and
    `finalize`s the result once. Returns (text, script info) or the reason it failed."""
    text = src.read_text(encoding="utf-8")
    inputs, outputs, blocks = ob.parse(text)
    used: set[int] = set()
    for cs in cuts:
        used |= cs.cut.idx
    host_blocks = [b for i, b in enumerate(blocks) if i not in used]
    read_by_host = {n for b in host_blocks for n in _io(b)[0]}
    driven_by_cut = {n for cs in cuts for n in cs.cut.boundary_out}
    extra_in: list[str] = []  # host's own extra primary inputs: cut nets the host reads
    extra_out: list[str] = []  # host's own extra primary outputs: host nets the cuts read
    for cs in cuts:
        for n in cs.cut.boundary_out:
            if n in read_by_host and n not in inputs and n not in extra_in:
                extra_in.append(n)
        for n in cs.cut.boundary_in:
            if n not in inputs and n not in outputs and n not in extra_out:
                extra_out.append(n)
    host_outputs = [o for o in outputs if o not in driven_by_cut] + extra_out
    host_file = work / f"{tag}.cs-host.blif"
    host_file.write_text(
        ob.render(list(inputs) + extra_in, host_outputs, host_blocks), encoding="utf-8")
    hres = _map_part(host_file, kind, rng, work, f"{tag}.cs-host")
    if isinstance(hres, str):
        return f"cut-stitch host: {hres}"
    host_mapped, host_script = hres
    hi, ho, hb = ob.parse(host_mapped)
    merged_blocks = _private(hi, ho, hb, "h_")
    scripts: Json = {"host": host_script}
    for cs in cuts:
        part_blocks = [blocks[i] for i in sorted(cs.cut.idx)]
        if not cs.run_abc:
            merged_blocks += part_blocks
            scripts[cs.label] = "identity (not run through ABC)"
            continue
        c_in = list(cs.cut.boundary_in)
        c_out = [*cs.cut.boundary_out, *cs.cut.extra_out]
        cfile = work / f"{tag}.cs-{cs.label}.blif"
        cfile.write_text(ob.render(c_in, c_out, part_blocks), encoding="utf-8")
        cres = _map_part(cfile, kind, rng, work, f"{tag}.cs-{cs.label}")
        if isinstance(cres, str):
            return f"cut-stitch {cs.label}: {cres}"
        cmapped, cscript = cres
        ci, co, cb = ob.parse(cmapped)
        merged_blocks += _private(ci, co, cb, f"{cs.label}_")
        scripts[cs.label] = cscript
    merged = ob.render(list(inputs), list(outputs), merged_blocks)
    if kind == "silicon":  # the buffer-free rule also covers the nets the pieces were joined on
        merged = ob.strip_buffers(merged)
    ren: dict[str, str] = {}
    final = ob.finalize(merged, rng, ren)
    # Where each ring bit went (answer key only): the energy witness reads these nets.
    rings = {cs.label: [ren[q] for q in cs.cut.extra_out if q in ren]
             for cs in cuts if cs.run_abc and cs.cut.extra_out}
    scripts["rings"] = rings
    return final, json.dumps(scripts, sort_keys=True)
