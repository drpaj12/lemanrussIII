"""Bases from the Mimir benchmark registry (round 5): VerilogEval and VTR Verilog designs,
fetched with `mimir bench` (refs `suite:design@flow` for netlists, `--kind source` for sources),
converted to `.names`-only BLIF by Odin III, and kept as Seeker-Comb bases when combinational.

Every design gets a record (kept or skipped with the reason) in `bases.json`.
"""

from __future__ import annotations

import json
import resource
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from lemanruss.htl.bitsim import compile_model
from lemanruss.htl.blif_text import parse_single_model

MIN_GATES = 8
MAX_GATES = 30000
TIMEOUT = 180
MEM_BYTES = 6 * 1024**3
VEREVAL_FLOW = "yosys-0.51-vereval"

# The registry's VerilogEval netlists are Yosys `abc -g NAND,NOR` output: instances of the cells
# NAND, NOR, NOT, BUF, DFF (and DFFSR, not defined here: those designs are sequential and
# skipped). Their definitions are prepended so Odin III can read the file.
CELL_LIB = """\
module NAND(input A, input B, output Y); assign Y = ~(A & B); endmodule
module NOR(input A, input B, output Y); assign Y = ~(A | B); endmodule
module NOT(input A, output Y); assign Y = ~A; endmodule
module BUF(input A, output Y); assign Y = A; endmodule
module DFF(input C, input D, output reg Q); always @(posedge C) Q <= D; endmodule
"""


@dataclass
class BaseRecord:
    ref: str
    kept: bool
    reason: str
    gates: int = 0
    inputs: int = 0
    outputs: int = 0
    file: str = ""


def _mimir(mimir_root: Path, *args: str) -> str:
    run = subprocess.run([sys.executable, "-m", "mimir.cli", "bench", *args], cwd=mimir_root,
                         capture_output=True, text=True, check=False, timeout=TIMEOUT)
    if run.returncode != 0:
        raise RuntimeError(run.stderr.strip().splitlines()[-1] if run.stderr else "mimir failed")
    return run.stdout


def list_designs(mimir_root: Path, suite: str) -> list[str]:
    out = _mimir(mimir_root, "list", "--suite", suite)
    return [line.split("\t")[0] for line in out.splitlines() if line.strip()]


def odin_bin() -> Path:
    import os

    return Path(os.environ["ODIN3_LIB"]).parent / "odin3"


def convert(
    src: Path, out: Path, top: str | None = None, arch: Path | None = None,
    timeout: int = TIMEOUT, mem_bytes: int = MEM_BYTES, flatten: bool = False,
) -> str:
    """Odin III Verilog to `.names` BLIF in a memory-capped subprocess; '' when ok, else why.
    `arch` selects the VTR-primitive script (`build.lowering_script`)."""
    from lemanruss.htl.build import lowering_script

    cmd = [str(odin_bin()), *(["--top", top] if top else []), "-p",
           f'{lowering_script(src, arch, flatten)}; write_blif --gates-as-names "{out}"']

    def limits() -> None:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    try:
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             preexec_fn=limits, check=False)
    except subprocess.TimeoutExpired:
        return f"Odin III timeout {timeout} s"
    if run.returncode != 0:
        errs = [ln for ln in run.stderr.splitlines() if "error" in ln]
        last = run.stderr.strip().splitlines()[-1][:80] if run.stderr.strip() else ""
        return (errs[0].split("error:", 1)[-1].strip()[:100] if errs
                else f"Odin III exit {run.returncode} (crash or out of memory) {last}".strip())
    if not out.exists():
        return "no BLIF written"
    return keep_first_model(out)


def keep_first_model(path: Path) -> str:
    """`write_blif` writes the top first and then every other module of the design (a module the
    top does not instantiate stays, for example b15 inside b17.v). A flattened top has no
    `.subckt`; keep that first model only. '' when ok, else why (a `.subckt` is left)."""
    text = path.read_text(encoding="utf-8")
    end = text.find("\n.end\n")
    if end < 0:
        return "no .end in the BLIF"
    first = text[: end + len("\n.end\n")]
    if "\n.subckt " in first or "\n.gate " in first:
        return "the top still holds sub-circuits after flatten"
    if len(first) < len(text):
        path.write_text(first, encoding="utf-8")
    return ""


def collect(mimir_root: Path, suite: str, out_dir: Path) -> list[BaseRecord]:
    """Fetch and convert every design of `suite`; keep combinational ones of MIN_GATES..MAX."""
    src_dir = out_dir / "src"
    blif_dir = out_dir / "blif"
    src_dir.mkdir(parents=True, exist_ok=True)
    blif_dir.mkdir(parents=True, exist_ok=True)
    records: list[BaseRecord] = []
    for name in list_designs(mimir_root, suite):
        ref = f"{suite}:{name}"
        try:
            if suite == "verilogeval":
                ref = f"{ref}@{VEREVAL_FLOW}"
                src = src_dir / f"{name}.v"
                _mimir(mimir_root, "fetch", "--kind", "netlist", "--out", str(src), ref)
                src.write_text(CELL_LIB + src.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                src = Path(_mimir(mimir_root, "fetch", "--kind", "source", ref).strip())
        except RuntimeError as exc:
            records.append(BaseRecord(ref, False, f"mimir fetch: {exc}"))
            continue
        top = "RefModule" if suite == "verilogeval" else None
        why = convert(src, blif_dir / f"{name}.blif", top) if src.exists() else "source missing"
        if why:
            records.append(BaseRecord(ref, False, why))
            continue
        path = blif_dir / f"{name}.blif"
        try:
            model = parse_single_model(path.read_text(encoding="utf-8"))
            comp = compile_model(model)
        except ValueError as exc:
            records.append(BaseRecord(ref, False, f"BLIF not usable: {exc}"))
            continue
        gates = len(comp.blocks)
        rec = BaseRecord(ref, False, "", gates, len(model.inputs), len(model.outputs), path.name)
        if comp.latches:
            rec.reason = f"sequential ({len(comp.latches)} latches)"
        elif gates < MIN_GATES:
            rec.reason = f"{gates} gates < {MIN_GATES}"
        elif gates > MAX_GATES:
            rec.reason = f"{gates} gates > {MAX_GATES}"
        else:
            rec.kept = True
        records.append(rec)
    (out_dir / f"{suite}-bases.json").write_text(
        json.dumps([asdict(r) for r in records], indent=1) + "\n", encoding="utf-8")
    return records


def combinational_sources(mimir_root: Path) -> list[Path]:
    """VerilogEval reference sources (via the registry) with `assign` and no clocked or
    procedural logic: the RTL bases of the sim_tb check."""
    out: list[Path] = []
    for name in list_designs(mimir_root, "verilogeval"):
        try:
            path = Path(_mimir(mimir_root, "fetch", "--kind", "source",
                               f"verilogeval:{name}").strip())
        except RuntimeError:
            continue
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "always" not in text and "posedge" not in text and "assign" in text:
            out.append(path)
    return out
