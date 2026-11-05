"""Obfuscation of one circuit (round 8, rc4 redesign; spec section 4).

Every non-golden circuit, clean or infected, goes through the same steps: a random ABC
logic-optimisation script, a mapping run by Odin III (`abc --lut K` or `abc --gates andornot`),
then a text pass that shuffles ports and blocks, renames every internal net and removes everything
that is not the netlist itself. Nothing here looks at a label.
"""

from __future__ import annotations

import hashlib
import os
import random
import re
from pathlib import Path

MODEL = "top"
LIB = Path(__file__).resolve().parents[1] / "data" / "andornot.o3lib"
LIB_NAME = "andornot"
KINDS = ("k4", "k6", "gates")
# ABC logic-optimisation operations (every one valid on combinational and sequential networks).
OPS = ("balance", "balance -l", "rewrite", "rewrite -z", "rewrite -l", "refactor", "refactor -z",
       "refactor -l", "resub -K 6", "resub -K 8 -N 2", "resub -K 10 -z", "resub -K 12", "dc2",
       "dc2 -l", "drw", "drw -z", "drf", "ifraig")


def random_script(rng: random.Random, kind: str) -> str:
    """ABC script text for `kind`; one distribution for every label. `{K}` is `abc --lut K`."""
    ops = [rng.choice(OPS) for _ in range(rng.randint(1, 8))]
    lines = ["strash", *ops]
    if rng.random() < 0.7:
        lines.append("dch -f")
    if kind == "gates":
        lines.append(rng.choice(("map -a", "map")))
    else:
        lines.append("if -K {K}")
        if rng.random() < 0.4:
            lines.append("mfs2")
    return "\n".join(lines) + "\n"


# ---- text handling ---------------------------------------------------------------------------

Block = list[str]


def parse(text: str) -> tuple[list[str], list[str], list[Block]]:
    """(inputs, outputs, blocks): a block is a `.names` line with its cover rows, or a `.latch`
    line. Comments, `.attr`, `.cname`, `.model` and `.end` are dropped."""
    inputs: list[str] = []
    outputs: list[str] = []
    blocks: list[Block] = []
    for ln in text.replace("\\\n", " ").splitlines():
        ln = ln.strip()
        if not ln or ln[0] == "#":
            continue
        if ln[0] != ".":
            blocks[-1].append(ln)
            continue
        w = ln.split()
        if w[0] == ".inputs":
            inputs += w[1:]
        elif w[0] == ".outputs":
            outputs += w[1:]
        elif w[0] in (".names", ".latch"):
            blocks.append([ln])
    return inputs, outputs, blocks


def _latch(line: str) -> tuple[str, str, str, str, str]:
    """(D, Q, type, clock, init) of a `.latch` line; missing fields default to `re`, none, 3."""
    w = line.split()[1:]
    d, q, rest = w[0], w[1], w[2:]
    init = rest[-1] if rest and rest[-1] in "0123" and len(rest[-1]) == 1 else "3"
    if rest and rest[-1] == init and len(rest) in (1, 3):
        rest = rest[:-1]
    typ = rest[0] if rest else "re"
    clk = rest[1] if len(rest) > 1 else ""
    return d, q, typ, clk, init


def render(inputs: list[str], outputs: list[str], blocks: list[Block]) -> str:
    out = [f".model {MODEL}", ".inputs " + " ".join(inputs), ".outputs " + " ".join(outputs)]
    for b in blocks:
        if b[0].startswith(".latch"):
            d, q, typ, clk, init = _latch(b[0])
            init = "2" if init == "3" else init  # one spelling of "unknown" (ABC writes 2)
            out.append(f".latch {d} {q} {typ} {clk} {init}" if clk else f".latch {d} {q} {init}")
        else:
            out += b
    out.append(".end")
    return "\n".join(out) + "\n"


def canonical(text: str) -> str:
    """The same netlist with the common header and layout. Order and names are unchanged, except
    that an internal net named in another tool's style (`$n5`, `a@b`) gets a plain `n<index>`
    name, so the golden shows no more of its origin than the others."""
    inputs, outputs, blocks = parse(text)
    ports = set(inputs) | set(outputs)
    clocks = {_latch(b[0])[3] for b in blocks if b[0].startswith(".latch")} - {""}
    bad: list[str] = []
    used: set[str] = set(ports)
    for b in blocks:
        names = b[0].split()[1:3] if b[0].startswith(".latch") else b[0].split()[1:]
        for n in names:
            if (n not in used and n not in clocks and any(c in n for c in "$\\@")):
                bad.append(n)
            used.add(n)
    if bad:
        k = 1
        ren: dict[str, str] = {}
        for n in dict.fromkeys(bad):
            while f"n{k}" in used:
                k += 1
            ren[n] = f"n{k}"
            used.add(f"n{k}")
        for b in blocks:
            w = b[0].split()
            if w[0] == ".latch":
                w[1], w[2] = ren.get(w[1], w[1]), ren.get(w[2], w[2])
            else:
                w = [w[0], *(ren.get(x, x) for x in w[1:])]
            b[0] = " ".join(w)
    return render(inputs, outputs, blocks)


def _net_key(name: str) -> tuple[int, int, str]:
    return (0, int(name[1:]), "") if re.fullmatch(r"n\d+", name) else (1, 0, name)


def _sorted_cell(nets: list[str], rows: list[str]) -> Block:
    """A `.names` block with its input nets in ascending order (`n<index>`, then ports) and its
    cubes ascending: one layout for every cell of every circuit, so the order ABC or a cut
    happened to leave carries nothing. The function is unchanged (columns and rows permuted)."""
    ins, out = nets[:-1], nets[-1]
    order = sorted(range(len(ins)), key=lambda c: _net_key(ins[c]))
    if not ins:
        return [" ".join([".names", out]), *rows]
    body = sorted(
        "".join(r.split()[0][c] for c in order) + " " + r.split()[-1] for r in rows if r.split())
    return [" ".join([".names", *(ins[c] for c in order), out]), *body]


def finalize(text: str, rng: random.Random, renames: dict[str, str] | None = None) -> str:
    """Shuffles ports and blocks, renames every internal net to `n<index>`. With `renames`, the
    old-to-new net name map is written into it (answer key only: it says where a net went)."""
    inputs, outputs, blocks = parse(text)
    ports = set(inputs) | set(outputs)
    clocks = {_latch(b[0])[3] for b in blocks if b[0].startswith(".latch")} - {""}
    nets: list[str] = []
    seen: set[str] = set()
    for b in blocks:
        names = b[0].split()[1:3] if b[0].startswith(".latch") else b[0].split()[1:]
        for n in names:
            if n not in ports and n not in clocks and n not in seen:
                seen.add(n)
                nets.append(n)
    idx = rng.sample(range(1, 4 * len(nets) + 8), len(nets))
    ren = {n: f"n{i}" for n, i in zip(nets, idx, strict=True)}
    if renames is not None:
        renames.update(ren)
    new_blocks: list[Block] = []
    for b in blocks:
        w = b[0].split()
        if w[0] == ".latch":
            d, q, typ, clk, init = _latch(b[0])
            line = f".latch {ren.get(d, d)} {ren.get(q, q)} {typ} {clk} {init}"
            new_blocks.append([line.replace("  ", " ")])
        else:
            new_blocks.append(_sorted_cell([ren.get(n, n) for n in w[1:]], b[1:]))
    rng.shuffle(new_blocks)
    ins, outs = list(inputs), list(outputs)
    rng.shuffle(ins)
    rng.shuffle(outs)
    return render(ins, outs, new_blocks)


def signature(text: str) -> str:
    """Hash of the structure that does not depend on net names, block order or input order of a
    cell: two circuits with the same signature are the same netlist up to renaming."""
    inputs, outputs, blocks = parse(text)
    sig: dict[str, str] = dict.fromkeys(inputs, "")
    for n in inputs:
        sig[n] = "pi:" + n
    latches = [b for b in blocks if b[0].startswith(".latch")]
    names = [b for b in blocks if b[0].startswith(".names")]
    for b in latches:
        _d, q, typ, clk, init = _latch(b[0])
        sig[q] = f"ff:{typ}:{init}"
    pending = list(names)
    guard = 0
    while pending and guard < len(names) + 2:
        guard += 1
        rest = []
        for b in pending:
            w = b[0].split()[1:]
            ins, out = w[:-1], w[-1]
            if all(i in sig for i in ins):
                cols = sorted(range(len(ins)), key=lambda c: sig[ins[c]])
                rows = sorted(
                    "".join(r.split()[0][c] for c in cols) + " " + r.split()[-1] if ins
                    else r.split()[-1] for r in b[1:])
                body = ";".join(rows) + "|" + ",".join(sig[ins[c]] for c in cols)
                sig[out] = hashlib.sha1(body.encode()).hexdigest()[:16]
            else:
                rest.append(b)
        pending = rest
    ffs = sorted(hashlib.sha1((sig.get(_latch(b[0])[0], "?") + sig[_latch(b[0])[1]]).encode())
                 .hexdigest()[:16] for b in latches)
    outs = sorted(f"{o}={sig.get(o, '?')}" for o in outputs)
    return hashlib.sha256("|".join(outs + ffs).encode()).hexdigest()


# ---- the Odin III run ------------------------------------------------------------------------

def _abc_env() -> None:
    lib = os.environ.get("ODIN3_LIB")
    if "ODIN3_ABC_EXE" not in os.environ and lib:
        os.environ["ODIN3_ABC_EXE"] = str(Path(lib).resolve().parent / "odin3-abc")


def map_with_odin(src: Path, kind: str, script: str, work: Path, tag: str) -> str:
    """Text of `src` optimised with `script` and mapped (kind k4 / k6 / gates) by Odin III."""
    from odin3 import Design

    _abc_env()
    sfile = work / f"{tag}.abc"
    out = work / f"{tag}.odin.blif"
    sfile.write_text(script, encoding="utf-8")
    with Design() as design:
        if kind == "gates":
            design.run_script(f"read_techlib {LIB}; read_blif {src}; "
                              f"abc --gates {LIB_NAME} --script {sfile}; "
                              f"write_blif --gates-as-names {out}")
        else:
            design.run_script(f"read_blif {src}; abc --script {sfile} --lut {kind[1:]}; "
                              f"write_blif {out}")
    return out.read_text(encoding="utf-8")


def obfuscate_traced(
    src: Path, kind: str, rng: random.Random, work: Path, tag: str
) -> tuple[str, str, str, dict[str, str]] | str:
    """`obfuscate` plus the hints a register-matched equivalence check needs: (finished text,
    ABC script, Odin III's mapped text before `finalize`, net renames old -> new), or the
    reason it failed. The random draws are exactly those of `obfuscate`."""
    script = random_script(rng, kind)
    try:
        mapped = map_with_odin(src, kind, script, work, tag)
    except Exception as exc:
        return f"obfuscate {kind}: {type(exc).__name__}: {str(exc)[:100]}"
    renames: dict[str, str] = {}
    return finalize(mapped, rng, renames), script, mapped, renames


def obfuscate(
    src: Path, kind: str, rng: random.Random, work: Path, tag: str
) -> tuple[str, str] | str:
    """(finished text, ABC script) of `src`, or the reason it failed."""
    out = obfuscate_traced(src, kind, rng, work, tag)
    return out if isinstance(out, str) else (out[0], out[1])
