"""Round 7 (Seeker-Proc pilot) orchestration: build a patched scratch copy of one base, run the
witness program and the shipped programs through iverilog and Odin III `sim_tb` (RTL and
netlist), and report fire / stealth / agreement. Mirrors `tests/mcu/run.sh` and
`tests/darkriscv/run.sh` (same patch-copy-build-compare shape) but drives it from Python so one
script can build both the clean and the Trojan copy of a base and diff them.

Odin III is invoked as the CLI binary (not the Python API): `sim_tb` is a Verilog-testbench pass
with no Python binding (spec section 4, "Testbench gap"), so this module shells out the same way
the existing `tests/mcu/run.sh` / `tests/darkriscv/run.sh` do.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from lemanruss.htl.dark_ram_blackbox import (
    blackbox_darksocv,
    dark_odin_files,
    dark_tb_with_ram_model,
)
from lemanruss.htl.mcu_ram_blackbox import (
    blackbox_subsystem,
    blackbox_top,
    mcu_odin_files,
    mcu_tb_with_ram_model,
)
from lemanruss.htl.proc_images import write_dark_mem, write_mcu_vmh
from lemanruss.htl.proc_insert import (
    insert_dark_multitrojan,
    insert_dark_trojan,
    insert_mcu_multitrojan,
    insert_mcu_trojan,
)
from lemanruss.htl.verify import EquivResult, check_equivalence

TIMEOUT = 600
WS = Path(os.environ.get("ODIN3_WS", "~/odin3-ws")).expanduser()  # holds odin3/, external/
MCU_TESTS_DIR = WS / "odin3/tests/mcu"
DARK_TESTS_DIR = WS / "odin3/tests/darkriscv"
MCU_UPSTREAM = WS / "external/Arduino-on-RISC-V"
DARK_UPSTREAM = WS / "external/darkriscv"
DARK_COMMIT = "9555119"


MASK_CYCLES = 8  # tests/mcu/compare.py's own reset-window constant


def _data_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln[:1].isdigit() or ln[:1] in "Uu"]


def _field_matches(ref: str, out: str, allow_x: bool) -> bool:
    """True when `out` equals `ref`; with `allow_x`, an x/z digit of `ref` matches any digit of
    `out` (tests/mcu/compare.py's own rule: iverilog starts BRAM at x, Odin III's simulator at
    0, in the reset window only)."""
    if len(ref) != len(out):
        return False
    return all(r == o or (allow_x and r in "xXzZ") for r, o in zip(ref, out, strict=True))


def traces_agree(ref: str, out: str, mask_cycles: int = MASK_CYCLES) -> bool:
    """Cross-engine trace agreement: like `traces_equal`, but an x/z field on a line whose cycle
    number is below `mask_cycles` matches any value (tests/mcu/compare.py's own masking rule for
    iverilog-vs-Odin-III comparisons; a masked field on a later line is still a mismatch)."""
    ref_lines, out_lines = _data_lines(ref), _data_lines(out)
    if len(ref_lines) != len(out_lines):
        return False
    for ref_ln, out_ln in zip(ref_lines, out_lines, strict=True):
        ref_fields, out_fields = ref_ln.split(), out_ln.split()
        if len(ref_fields) != len(out_fields):
            return False
        in_reset = ref_fields[0].isdigit() and int(ref_fields[0]) < mask_cycles
        for r, o in zip(ref_fields, out_fields, strict=True):
            if r != o and not _field_matches(r, o, in_reset):
                return False
    return True


def _run(cmd: list[str], cwd: Path, timeout: int = TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )


@dataclass
class TrojanResult:
    trojan_id: str
    base: str
    witness_fires_iverilog: bool
    witness_fires_rtl: bool
    witness_fires_netlist: bool
    rtl_equals_iverilog: bool
    netlist_equals_rtl: bool
    stealth: dict[str, bool]  # program name -> True if clean == infected (good)
    dropped_for_firing: list[str]  # shipped programs where stealth failed (would be dropped)
    errors: list[str]


_CLK_T0_ORIGINAL = "always @ (posedge clk_T0 or posedge reset)"
_CLK_T0_PATCHED = (
    "reg clk_T0_q;\n"
    "always @(posedge clock) clk_T0_q <= clk_T0;\n"
    "wire clk_T0_en = (CS0 == 3'd1) | (clk_T0 & ~clk_T0_q);\n"
    "always @ (posedge clock or posedge reset)"
)
_CS0_ORIGINAL = "else if (CS0 == 1'b0)"
_CS0_PATCHED = "else if (!clk_T0_en) begin end\nelse if (CS0 == 1'b0)"


def _patch_derived_clock(path: Path) -> None:
    """Re-applies tests/mcu/prepare.sh's own former patch 5 (8bit_TC.v's `clk_T0`, a mux of the
    prescaler outputs, is a derived clock) if `path` does not already carry it. This repo's
    pinned Odin III (brief: "Odin III library: ~/odin3-ws/odin3/build/rel-main", main 0d3d735a)
    predates the 2026-11-01 Odin III fix that made the patch optional (`tests/mcu/prepare.sh`'s
    own comment, "the Odin III simulator takes [the derived clock] since 2026-11-01"); the main
    checkout this repo reads `tests/mcu/prepare.sh` from is shared with other concurrent agent
    sessions on this workspace and moved under us mid-round (observed: a prior green witness run
    silently started failing once `prepare.sh` dropped the patch). Idempotent: a no-op if the
    marker text is already present (upstream patched it back, or sim_tb no longer needs it)."""
    text = path.read_text()
    if "clk_T0_en" in text:
        return
    if _CLK_T0_ORIGINAL not in text or _CS0_ORIGINAL not in text:
        raise RuntimeError(f"_patch_derived_clock: patch points not found in {path}")
    text = text.replace(_CLK_T0_ORIGINAL, _CLK_T0_PATCHED)
    text = text.replace(_CS0_ORIGINAL, _CS0_PATCHED)
    path.write_text(text)


def prepare_mcu(up: Path, out: Path, prog: str, blackbox: bool = True) -> list[str]:
    """Runs tests/mcu/prepare.sh; returns the design file list (relative names). Re-applies the
    derived-clock patch (`_patch_derived_clock`) to both copies if the script did not."""
    res = _run(
        [str(MCU_TESTS_DIR / "prepare.sh"), str(up), str(out), f"{prog}.vmh"],
        cwd=MCU_TESTS_DIR,
    )
    if res.returncode != 0:
        raise RuntimeError(f"prepare.sh (mcu) failed: {res.stderr}")
    _patch_derived_clock(out / "8bit_TC.v")
    _patch_derived_clock(out / "iv" / "8bit_TC.v")
    files = res.stdout.strip().splitlines()[-1].split()
    if blackbox:
        # rc1 (2026-11-04, `lemanruss.htl.mcu_ram_blackbox`): RAM out of Odin III's view in the
        # main copy; the `iv/` copy keeps the real RAM. Odin III call sites use
        # `mcu_odin_files(files)`.
        sub = out / "dual_port_BRAM_memory_subsystem.v"
        sub.write_text(blackbox_subsystem(sub.read_text()))
        top = out / "single_cycle_BRAM_top.v"
        top.write_text(blackbox_top(top.read_text()))
        tb = out / "mcu_tb.v"
        tb.write_text(mcu_tb_with_ram_model(tb.read_text(), prog))
    return files


def prepare_dark(up: Path, out: Path) -> list[str]:
    """Runs tests/darkriscv/prepare.sh; returns the design file list (relative to out/rtl, for
    iverilog -- the unfiltered list, `darkram.v` included).

    rc1 (2026-11-04, controller finding, `lemanruss.htl.dark_ram_blackbox`): also black-boxes the
    *main* copy's `darksocv.v`/`dark_tb.v` (`out/rtl/`, the copy Odin III reads), moving the
    `darkram` array out of Odin III's view so `lower` never expands it into per-bit latches. The
    `iv/` copy is left untouched (iverilog does not have this problem and needs the real
    `darkram.v` instance). Call sites that build Odin III's own `read_verilog` command must use
    `dark_odin_files(files)`, not `files`, on this copy.
    """
    res = _run([str(DARK_TESTS_DIR / "prepare.sh"), str(up), str(out)], cwd=DARK_TESTS_DIR)
    if res.returncode != 0:
        raise RuntimeError(f"prepare.sh (darkriscv) failed: {res.stderr}")
    files = res.stdout.strip().splitlines()[-1].split()
    socv = out / "rtl" / "darksocv.v"
    socv.write_text(blackbox_darksocv(socv.read_text()))
    tb = out / "rtl" / "dark_tb.v"
    tb.write_text(dark_tb_with_ram_model(tb.read_text()))
    return files


def _set_cycles(tb_path: Path, cycles: int) -> None:
    text = tb_path.read_text()
    text = re.sub(r"parameter CYCLES = \d+", f"parameter CYCLES = {cycles}", text)
    tb_path.write_text(text)


def write_mcu_program(out: Path, words: list[int], name: str) -> None:
    """Overwrites `<name>.vmh` (both the main build dir and its `iv/` copy) with `words`."""
    write_mcu_vmh(words, out, name)
    write_mcu_vmh(words, out / "iv", name)


def run_mcu_iverilog_only(out: Path, files: list[str], cycles: int, tag: str) -> str:
    """iverilog-only trace of single_cycle_BRAM_top (no Odin III). A defensive fallback for the
    'clock ... is not a primary input' sim_tb error (8bit_TC.v's derived timer clock): the real
    cause, found and fixed, was `prepare_mcu`'s own `_patch_derived_clock` missing (the shared
    main checkout's `tests/mcu/prepare.sh` dropped that patch mid-round); kept here in case a
    future shipped program hits a different unpatched derived clock, so the stealth check still
    gets a result (iverilog-only, clean vs infected under the same engine) instead of failing
    outright."""
    _set_cycles(out / "iv" / "mcu_tb.v", cycles)
    iv = _run(["iverilog", "-g2005", "-o", f"../{tag}.vvp", "mcu_tb.v", *files], cwd=out / "iv")
    if iv.returncode != 0:
        raise RuntimeError(f"iverilog failed: {iv.stderr}")
    run = _run(["vvp", f"{tag}.vvp"], cwd=out)
    text = "\n".join(_data_lines(run.stdout))
    (out / f"{tag}.ref.txt").write_text(text)
    return text


def write_dark_program(out: Path, words: list[int]) -> None:
    """Overwrites `src/darksocv.mem` (both the main build dir and its `iv/` copy) with `words`."""
    write_dark_mem(words, out / "src" / "darksocv.mem")
    write_dark_mem(words, out / "iv" / "src" / "darksocv.mem")


def run_mcu_once(
    out: Path, files: list[str], odin3_bin: Path, cycles: int, tag: str
) -> dict[str, str]:
    """iverilog + Odin III RTL + Odin III netlist sim of single_cycle_BRAM_top; three trace
    files `<tag>.ref.txt`, `<tag>.rtl.txt`, `<tag>.nl.txt` under `out`."""
    _set_cycles(out / "mcu_tb.v", cycles)
    _set_cycles(out / "iv" / "mcu_tb.v", cycles)
    file_list = " ".join(mcu_odin_files(files))
    iv = _run(["iverilog", "-g2005", "-o", f"../{tag}.vvp", "mcu_tb.v", *files], cwd=out / "iv")
    if iv.returncode != 0:
        raise RuntimeError(f"iverilog failed: {iv.stderr}")
    run = _run(["vvp", f"{tag}.vvp"], cwd=out)
    (out / f"{tag}.ref.txt").write_text("\n".join(_data_lines(run.stdout)))

    rtl = _run(
        [str(odin3_bin), "--top", "single_cycle_BRAM_top", "-p",
         f'read_verilog {file_list}; proc; opt; lower; sim_tb --out {tag}.rtl.txt mcu_tb.v'],
        cwd=out,
    )
    if rtl.returncode != 0:
        raise RuntimeError(f"odin3 rtl sim_tb failed: {rtl.stdout}\n{rtl.stderr}")

    nl = _run(
        [str(odin3_bin), "--top", "single_cycle_BRAM_top", "-p",
         f'read_verilog {file_list}; proc; opt; lower; write_blif {tag}.nl.blif'],
        cwd=out,
    )
    if nl.returncode != 0:
        raise RuntimeError(f"odin3 write_blif failed: {nl.stdout}\n{nl.stderr}")
    nl2 = _run(
        [str(odin3_bin), "--top", "single_cycle_BRAM_top", "-p",
         f'read_blif {tag}.nl.blif; sim_tb --out {tag}.nl.txt mcu_tb.v'],
        cwd=out,
    )
    if nl2.returncode != 0:
        raise RuntimeError(f"odin3 netlist sim_tb failed: {nl2.stdout}\n{nl2.stderr}")
    return {
        "ref": (out / f"{tag}.ref.txt").read_text(),
        "rtl": (out / f"{tag}.rtl.txt").read_text(),
        "nl": (out / f"{tag}.nl.txt").read_text(),
    }


def traces_equal(a: str, b: str) -> bool:
    """Exact equality of data lines (no x-masking: both sides come from the same reset-released
    simulator state here, unlike the oracle-vs-Odin III x-masked comparison in tests/mcu)."""
    return _data_lines(a) == _data_lines(b)


def patch_mcu_core(out: Path, magic_words: list[int], *, force_inactive: bool = False) -> None:
    for rel in ("single_cycle_core.v", "iv/single_cycle_core.v"):
        p = out / rel
        p.write_text(insert_mcu_trojan(p.read_text(), magic_words, force_inactive=force_inactive))


def patch_dark_core(out: Path, magic_words: list[int], *, force_inactive: bool = False) -> None:
    for rel in ("rtl/darkriscv.v", "iv/rtl/darkriscv.v"):
        p = out / rel
        p.write_text(insert_dark_trojan(p.read_text(), magic_words, force_inactive=force_inactive))


def patch_mcu_multicore(
    out: Path, magic_words: list[int], *, force_inactive: bool = False
) -> list[str]:
    """rc1: 1-3 independent magic-word Trojans (`insert_mcu_multitrojan`), not the single-
    sequence `patch_mcu_core`. Returns the per-Trojan trigger wire names."""
    names: list[str] = []
    for rel in ("single_cycle_core.v", "iv/single_cycle_core.v"):
        p = out / rel
        patched, names = insert_mcu_multitrojan(
            p.read_text(), magic_words, force_inactive=force_inactive)
        p.write_text(patched)
    return names


def patch_dark_multicore(
    out: Path, magic_words: list[int], *, force_inactive: bool = False
) -> list[str]:
    """rc1: 1-3 independent magic-word Trojans (`insert_dark_multitrojan`), not the single-
    sequence `patch_dark_core`. Returns the per-Trojan trigger wire names."""
    names: list[str] = []
    for rel in ("rtl/darkriscv.v", "iv/rtl/darkriscv.v"):
        p = out / rel
        patched, names = insert_dark_multitrojan(
            p.read_text(), magic_words, force_inactive=force_inactive)
        p.write_text(patched)
    return names


def run_dark_once(
    out: Path, files: list[str], odin3_bin: Path, cycles: int, tag: str
) -> dict[str, str]:
    """iverilog + Odin III RTL + Odin III netlist sim of darksocv; three trace files under
    `out` (paths relative to `out/rtl`, matching tests/darkriscv/run.sh's own layout).

    rc1 (2026-11-04): the iverilog build uses `files` unfiltered (its `iv/` copy still has the
    real `darkram` instance); Odin III's two builds use `dark_odin_files(files)` (the main copy's
    `darkram` array moved to the testbench's own behavioural model, `dark_ram_blackbox`), so
    `darkram.v` is never passed to Odin III's `read_verilog` and never reaches `lower`."""
    _set_cycles(out / "rtl" / "dark_tb.v", cycles)
    _set_cycles(out / "iv" / "rtl" / "dark_tb.v", cycles)
    odin_file_list = " ".join(dark_odin_files(files))
    iv = _run(
        ["iverilog", "-g2005", "-o", f"../{tag}.vvp", "dark_tb.v", *files], cwd=out / "iv" / "rtl"
    )
    if iv.returncode != 0:
        raise RuntimeError(f"iverilog failed: {iv.stderr}")
    run = _run(["vvp", f"{tag}.vvp"], cwd=out / "iv")
    (out / f"{tag}.ref.txt").write_text("\n".join(_data_lines(run.stdout)))

    rtl = _run(
        [str(odin3_bin), "--top", "darksocv", "-p",
         f'read_verilog {odin_file_list}; proc; opt; lower; '
         f'sim_tb --out ../{tag}.rtl.txt dark_tb.v'],
        cwd=out / "rtl",
    )
    if rtl.returncode != 0:
        raise RuntimeError(f"odin3 rtl sim_tb failed: {rtl.stdout}\n{rtl.stderr}")

    nl = _run(
        [str(odin3_bin), "--top", "darksocv", "-p",
         f'read_verilog {odin_file_list}; proc; opt; lower; write_blif ../{tag}.nl.blif'],
        cwd=out / "rtl",
    )
    if nl.returncode != 0:
        raise RuntimeError(f"odin3 write_blif failed: {nl.stdout}\n{nl.stderr}")
    nl2 = _run(
        [str(odin3_bin), "--top", "darksocv", "-p",
         f'read_blif ../{tag}.nl.blif; sim_tb --out ../{tag}.nl.txt dark_tb.v'],
        cwd=out / "rtl",
    )
    if nl2.returncode != 0:
        raise RuntimeError(f"odin3 netlist sim_tb failed: {nl2.stdout}\n{nl2.stderr}")
    return {
        "ref": (out / f"{tag}.ref.txt").read_text(),
        "rtl": (out / f"{tag}.rtl.txt").read_text(),
        "nl": (out / f"{tag}.nl.txt").read_text(),
    }


def equivalence_forced_off(clean_blif: Path, forced_off_blif: Path) -> EquivResult:
    """ABC equivalence (tools/equiv-check) of a clean netlist against an infected netlist built
    with `force_inactive=True` (spec section 4(c)): the Trojan's logic stays in the netlist, its
    trigger is a constant 0."""
    root = os.environ.get("ODIN3_ROOT")
    base = Path(root) if root else Path(os.environ["ODIN3_LIB"]).resolve().parents[2]
    equiv_bin = base / "tools" / "equiv-check" / "equiv-check"
    return check_equivalence(equiv_bin, clean_blif, forced_off_blif)
