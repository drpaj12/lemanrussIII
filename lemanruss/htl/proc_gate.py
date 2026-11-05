"""Release gate for Seeker-Proc circuit files (rc2). A released BLIF must

1. hold exactly one `.model` (rc1's darkriscv and mcu circuits held several that a parser merged);
2. declare no port twice, list no driven net as an input, and drive no net twice
   (a `.names` or `.latch` output);
3. be read by Odin III (`read_blif`);
4. when a reference is given, be equivalent to it (ABC through `tools/equiv-check`; exit 0 only,
   "unproven" is a failure).

Every check returns problem strings; an empty list is a pass. Builders stop on a non-empty list.
"""

from __future__ import annotations

import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from lemanruss.htl.r4check import equiv_check_bin
from lemanruss.htl.verify import check_equivalence

EQUIV_TIMEOUT_S = 900


def structural_problems(text: str) -> list[str]:
    """Checks 1 and 2 on the BLIF text."""
    lines = text.replace("\\\n", " ").splitlines()
    out: list[str] = []
    n_model = sum(1 for ln in lines if ln.startswith(".model"))
    if n_model != 1:
        out.append(f"{n_model} .model sections (need exactly 1)")
    ins: list[str] = []
    outs: list[str] = []
    drivers: Counter[str] = Counter()
    for ln in lines:
        w = ln.split()
        if not w:
            continue
        if w[0] == ".inputs":
            ins += w[1:]
        elif w[0] == ".outputs":
            outs += w[1:]
        elif w[0] == ".names" and len(w) > 1:
            drivers[w[-1]] += 1
        elif w[0] == ".latch" and len(w) > 2:
            drivers[w[2]] += 1
    for kind, ports in (("input", ins), ("output", outs)):
        dup = sorted(p for p, c in Counter(ports).items() if c > 1)
        if dup:
            out.append(f"{len(dup)} duplicate {kind} ports (first: {dup[0]})")
    driven_in = sorted(set(ins) & set(drivers))
    if driven_in:
        out.append(f"{len(driven_in)} inputs also driven inside (first: {driven_in[0]})")
    multi = sorted(n for n, c in drivers.items() if c > 1)
    if multi:
        out.append(f"{len(multi)} multi-driven nets (first: {multi[0]})")
    return out


def odin_read_problem(odin3_bin: Path, text: str) -> str | None:
    """Check 3: `odin3 -p "read_blif f"` must exit 0."""
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "c.blif"
        f.write_text(text, encoding="utf-8")
        run = subprocess.run([str(odin3_bin), "-p", f"read_blif {f}"], capture_output=True,
                             text=True, check=False, timeout=300)
    if run.returncode != 0:
        err = [x for x in (run.stdout + run.stderr).splitlines() if "error" in x]
        return "Odin III read_blif failed: " + (err[0] if err else f"exit {run.returncode}")
    return None


def equivalence_problem(text: str, ref_text: str, timeout: int = EQUIV_TIMEOUT_S) -> str | None:
    """Check 4: ABC equivalence of `text` to `ref_text`; only exit 0 passes."""
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "a.blif", Path(td) / "b.blif"
        a.write_text(text, encoding="utf-8")
        b.write_text(ref_text, encoding="utf-8")
        try:
            res = check_equivalence(equiv_check_bin(), a, b, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"equivalence check timed out after {timeout} s"
    if res.returncode == 0:
        return None
    last = (res.stdout + res.stderr).strip().splitlines()
    return f"not equivalent to the reference (equiv-check exit {res.returncode}): " + (
        last[-1] if last else "")


def gate_problems(text: str, odin3_bin: Path, ref_text: str | None = None) -> list[str]:
    """All four checks; structural problems short-circuit the slower ones."""
    problems = structural_problems(text)
    if problems:
        return problems
    rd = odin_read_problem(odin3_bin, text)
    if rd:
        return [rd]
    if ref_text is not None:
        eq = equivalence_problem(text, ref_text)
        if eq:
            return [eq]
    return []


class GateError(RuntimeError):
    """A released circuit failed the release gate: the build stops."""
