"""ABC functional restructurings (round 4, brief item 3).

Seeker1 used 18 ABC methods. This set has 18 (12 from round 4 plus ROUND5_EXTRA), listed
explicitly (ABC aliases such as resyn2 live
in abc.rc and are not built in, so each script spells its commands out): AIG-only structural
rewrites (strash, balance, rewrite, refactor, resyn, resyn2, compress2, dc2, dc2x2) and three
LUT-mapped variants (4-LUT and 6-LUT after choice computation, 6-LUT with don't-care resub).
Each restructuring is applied to a clean AND an infected circuit, then checked equivalent to its
own source with tools/equiv-check (ABC cec / dsec) and its structure recorded.

ABC drops the latch clock; it is written back (`re <clock>`) so the result is a normal BLIF for
the rest of the repo. Results are written gzip-compressed.
"""

from __future__ import annotations

import gzip
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from lemanruss.htl.bitsim import compile_model, latches_of
from lemanruss.htl.blif_text import BlifModel, parse_single_model, render
from lemanruss.htl.r4check import equiv_check_bin
from lemanruss.htl.verify import check_equivalence

_RESYN2 = (
    "balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; "
    "rewrite -z; balance"
)
_COMPRESS2 = (
    "balance -l; resub -K 6 -l; rewrite -l; resub -K 6 -N 2 -l; refactor -l; resub -K 8 -l; "
    "balance -l; resub -K 8 -N 2 -l; rewrite -l; resub -K 10 -l; rewrite -z -l; "
    "resub -K 10 -N 2 -l; balance -l; resub -K 12 -l; refactor -z -l; resub -K 12 -N 2 -l; "
    "rewrite -z -l; balance -l"
)

_RESYN2RS = (
    "balance; resub -K 6; rewrite; resub -K 6 -N 2; refactor; resub -K 8; balance; "
    "resub -K 8 -N 2; rewrite; resub -K 10; rewrite -z; resub -K 10 -N 2; balance; "
    "resub -K 12; refactor -z; resub -K 12 -N 2; rewrite -z; balance"
)

# The 6 added in round 5 (12 + 6 = 18, the count Seeker1 used; Seeker1's own list of 18 was not
# read, so these are ABC's standard scripts and one more LUT size, not a copy of that list).
ROUND5_EXTRA = ("resyn2a", "resyn3", "resyn2rs", "compress", "resub", "lut5")

RESTRUCTURINGS: dict[str, str] = {
    "strash": "strash",
    "balance": "strash; balance",
    "rewrite": "strash; rewrite; rewrite -z",
    "refactor": "strash; refactor; refactor -z",
    "resyn": "strash; balance; rewrite; rewrite -z; balance; rewrite -z; balance",
    "resyn2": f"strash; {_RESYN2}",
    "compress2": f"strash; {_COMPRESS2}",
    "dc2": "strash; dc2",
    "dc2x2": "strash; dc2; balance; dc2",
    "lut4": "strash; dch; if -K 4",
    "lut6": "strash; dch; if -K 6",
    "lut6mfs": "strash; dch; if -K 6; mfs -a",
    "resyn2a": "strash; balance; rewrite; balance; rewrite; rewrite -z; balance; rewrite -z; "
    "balance",
    "resyn3": "strash; balance; resub; resub -K 6; balance; resub -z; resub -z -K 6; balance; "
    "resub -z -K 5; balance",
    "resyn2rs": f"strash; {_RESYN2RS}",
    "compress": "strash; balance -l; rewrite -l; rewrite -z -l; balance -l; rewrite -z -l; "
    "balance -l",
    "resub": "strash; resub -K 8; resub -K 8 -z",
    "lut5": "strash; dch; if -K 5",
}


def abc_bin() -> Path:
    return equiv_check_bin().parents[2] / "build" / "release" / "third_party" / "abc" / "abc"


@dataclass
class Structure:
    names: int
    latches: int
    depth: int
    cubes: int
    inputs: int
    outputs: int


def structure_of(model: BlifModel) -> Structure:
    """Gate count, latch count, logic depth (levels of `.names`), cube count."""
    comp = compile_model(model)
    level: dict[str, int] = {}
    depth = cubes = 0
    for out, ins, pats, _on in comp.blocks:
        lv = 1 + max((level.get(i, 0) for i in ins), default=0)
        level[out] = lv
        depth = max(depth, lv)
        cubes += len(pats)
    return Structure(len(comp.blocks), len(comp.latches), depth, cubes, len(comp.data_inputs),
                     len(comp.outputs))


def restore_clock(abc_text: str, source: BlifModel) -> BlifModel:
    """ABC output as a BlifModel whose latches carry the source's clock again."""
    out = parse_single_model(abc_text)
    clocks = [c for _d, _q, c in latches_of(source) if c]
    if not clocks:
        return out
    clock = clocks[0]
    body = []
    for line in out.body:
        if line.startswith(".latch "):
            w = line.split()
            init = w[3] if len(w) == 4 else "0"
            line = f".latch {w[1]} {w[2]} re {clock} {init}"
        body.append(line)
    inputs = out.inputs if clock in out.inputs else [*out.inputs, clock]
    return BlifModel(out.name, inputs, out.outputs, body)


@dataclass
class Restructured:
    source: str
    variant: str
    file: str
    verdict: str  # equivalent | not-equivalent | unproven | error | abc-failed
    before: Structure
    after: Structure | None

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        return d


def restructure_one(
    src: Path, source_id: str, variant: str, out_path: Path, scratch_dir: Path, tag: str,
    timeout: int = 300,
) -> Restructured:
    """Applies one ABC script to `src`, checks the result equivalent to `src`, and writes it
    gzip-compressed to `out_path`. `scratch_dir/<tag>_*.blif` are overwritten per call."""
    source = parse_single_model(src.read_text(encoding="utf-8"))
    before = structure_of(source)
    raw = scratch_dir / f"{tag}_abc.blif"
    cmd = f"read_blif {src}; {RESTRUCTURINGS[variant]}; write_blif {raw}"
    try:
        run = subprocess.run([str(abc_bin()), "-q", cmd], capture_output=True, text=True,
                             timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return Restructured(source_id, variant, "", "abc-failed", before, None)
    abc_error = "** cmd error" in run.stdout or "Error:" in run.stdout or "Error:" in run.stderr
    if run.returncode != 0 or not raw.exists() or abc_error:
        return Restructured(source_id, variant, "", "abc-failed", before, None)
    model = restore_clock(raw.read_text(encoding="utf-8"), source)
    checked = scratch_dir / f"{tag}_chk.blif"
    text = render(model)
    checked.write_text(text, encoding="utf-8")
    try:
        res = check_equivalence(equiv_check_bin(), src, checked)
        verdict = {0: "equivalent", 1: "not-equivalent", 4: "unproven"}.get(
            res.returncode, "error")
    except subprocess.TimeoutExpired:
        verdict = "unproven"
    with gzip.open(out_path, "wt", encoding="utf-8", compresslevel=9) as fh:
        fh.write(text)
    return Restructured(source_id, variant, out_path.name, verdict, before, structure_of(model))
