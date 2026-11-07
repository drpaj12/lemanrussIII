"""Silicon-form gates of Seeker-Si rc2 (spec 2026-11-07 section 3, gates 1, 2, 6, 7).

`check` takes a finalized silicon BLIF and returns (cell Verilog text, problems). Equivalence to
the source, fire and silence are the family's own steps (`n200.finish`, `proc_build`).
"""

from __future__ import annotations

from lemanruss.htl.obfuscate import parse
from lemanruss.htl.proc_gate import structural_problems
from lemanruss.htl.si_cells import blif_to_verilog, same_network, verilog_to_blif


def ff_count(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.startswith(".latch"))


def check(text: str, golden_ff: int | None) -> tuple[str, list[str]]:
    """(Verilog of the cells, problems); an empty problem list is a pass."""
    problems = structural_problems(text)
    if problems:
        return "", problems
    try:
        verilog = blif_to_verilog(text)  # raises when a cover is not a library cell
    except ValueError as exc:
        return "", [f"cell check: {exc}"]
    inputs, outputs, _blocks = parse(text)
    if not same_network(text, verilog_to_blif(verilog, inputs, outputs)):
        problems.append("Verilog round trip differs from the BLIF")
    if golden_ff is not None and ff_count(text) != golden_ff:
        problems.append(f"FF count {ff_count(text)} != golden {golden_ff}")
    return verilog, problems
