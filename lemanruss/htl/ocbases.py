"""OpenCores bases for Seeker-Seq rc8: the 12 Mimir catalogue projects of the two waves, an
admission record per design (admitted or excluded with the reason), and the Odin III conversion of
the admitted ones to `.names`-only BLIF.

Source files are those of the Mimir OpenCores flow (`opencores-runs/cfg/<name>.env`): the RTL
files of the project, nothing of the testbenches. The checkouts live under a root given by the
caller (`external/opencores` and `external/opencores-candidates` of the workspace); nothing here
names a home directory.
"""

from __future__ import annotations

import json
import re
import resource
import subprocess
import time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

TIMEOUT = 1800
MEM_BYTES = 4 * 1024**3
SCRIPT = "read_verilog; proc; opt; flatten; opt; lower"

PERMISSIVE = (
    "permissive notice in the file headers: 'This source file may be used and distributed "
    "without restriction provided that this copyright statement is not removed from the file "
    "and that any derivative work contains the original copyright notice and the associated "
    "disclaimer.'")


@dataclass(frozen=True)
class OcDesign:
    name: str
    wave: int
    checkout: str  # "opencores" or "opencores-candidates"
    top: str
    files: tuple[str, ...]  # relative to <root>/<checkout>/<name>
    incdirs: tuple[str, ...]
    licence: str
    licence_where: str
    admitted: bool
    reason: str  # why excluded, or the admission note
    notes: str = ""
    category: str = ""  # exclusion category: memory, licence: copyleft, licence: none stated, size


_SURVEY: tuple[OcDesign, ...] = (
    OcDesign(
        "ca_prng", 1, "opencores", "ca_prng", ("src/rtl/ca_prng.v",), (),
        "BSD-3-Clause style (InformAsic AB)", "COPYING.txt:1-5; src/rtl/ca_prng.v:16-19",
        True, "no memory, no tri-state; redistribution allowed with the notice kept"),
    OcDesign(
        "mmuart", 1, "opencores", "uart", ("rtl/uart.v", "rtl/uart_transceiver.v"), (),
        "GPL-3.0", "rtl/uart.v:6-7",
        True, "no memory, no tri-state; GPL-3.0 permits redistribution of derived works under "
        "GPL-3.0, the derived netlists carry that licence"),
    OcDesign(
        "simple_spi", 1, "opencores", "simple_spi_top",
        ("rtl/verilog/fifo4.v", "rtl/verilog/simple_spi_top.v"), (),
        PERMISSIVE, "rtl/verilog/simple_spi_top.v:11-20",
        False, "memory: rtl/verilog/fifo4.v:77 `reg [dw:1] mem[0:3]` (a 4-entry FIFO array; "
        "lowered to flip-flops it is still a memory)"),
    OcDesign(
        "i2cslave", 1, "opencores", "i2cSlaveTop",
        ("rtl/serialInterface.v", "rtl/registerInterface.v", "rtl/i2cSlave.v",
         "rtl/i2cSlaveTop.v"), ("rtl",),
        "LGPL-2.1+ per file header (the OpenCores page says GPL: mismatch; either licence "
        "permits redistribution)", "rtl/i2cSlave.v:27-30",
        True, "no memory; the tri-state `assign sda = (sdaOut == 1'b0) ? 1'b0 : 1'bz` is "
        "lowered by Odin III with the enable dropped (warning recorded): no tri-state is left, "
        "the inout becomes an output and the bus read path is internal"),
    OcDesign(
        "sdram_16bit", 1, "opencores", "sdram", ("rtl/sdram.v",), (),
        "GPL-2.0+", "rtl/sdram.v:9,15-17",
        False, "memory: rtl/sdram.v:151 `reg [SDRAM_ROW_W-1:0] active_row_q[0:SDRAM_BANKS-1]` "
        "(Odin III: 'replacing memory active_row_q with list of registers'); also vendor "
        "primitives ODDR2 / IOBUF (rtl/sdram.v:689,709) and an inout top port"),
    OcDesign(
        "i2c", 1, "opencores", "i2c_master_top",
        ("rtl/verilog/i2c_master_bit_ctrl.v", "rtl/verilog/i2c_master_byte_ctrl.v",
         "rtl/verilog/i2c_master_top.v"), ("rtl/verilog",),
        PERMISSIVE + " (Richard Herveille, 2001)", "rtl/verilog/i2c_master_top.v:17-20",
        True, "no memory, no tri-state"),
    OcDesign(
        "spi", 1, "opencores", "spi_top",
        ("rtl/verilog/spi_clgen.v", "rtl/verilog/spi_shift.v", "rtl/verilog/spi_top.v"),
        ("rtl/verilog",),
        "LGPL-2.1+ per file header", "rtl/verilog/spi_top.v:24-26",
        True, "no memory, no tri-state"),
    OcDesign(
        "uart2spi", 1, "opencores-candidates", "top",
        ("rtl/top/top.v", "rtl/uart_core/uart_core.v", "rtl/uart_core/clk_ctl.v",
         "rtl/uart_core/uart_rxfsm.v", "rtl/uart_core/uart_txfsm.v",
         "rtl/msg_hand/uart_msg_handler.v", "rtl/spi/spi_core.v", "rtl/spi/spi_ctl.v",
         "rtl/spi/spi_if.v", "rtl/spi/spi_cfg.v", "rtl/lib/registers.v"), (),
        "LGPL-2.1+ per file header (top.v)", "rtl/top/top.v header",
        True, "no memory, no tri-state"),
    OcDesign(
        "wb_lcd", 2, "opencores", "wb_lcd",
        ("verilog/wb_lcd/rtl/delay_counter.v", "verilog/wb_lcd/rtl/lcd_display.v",
         "verilog/wb_lcd/rtl/wb_lcd.v"), ("verilog/wb_lcd/rtl",),
        "LGPL-3.0+ per file header", "verilog/wb_lcd/rtl/wb_lcd.v:27-30",
        False, "memory: verilog/wb_lcd/rtl/lcd_display.v:114 `reg [`DAT_WIDTH-1:0] ram "
        "[0:`MEM_LENGTH-1]` (the character RAM; it is in the 660 flip-flops)"),
    OcDesign(
        "verilog_cordic_core", 2, "opencores", "cordic", ("cordic.v",), (),
        "none stated (no licence text in cordic.v or the project; the OpenCores page has none)",
        "cordic.v:1-12",
        False, "licence unclear (none stated), so not redistributed; also cordic.v:178 has a "
        "non-constant for-loop bound that Odin III rejects (Mimir builds a patched variant)"),
    OcDesign(
        "sdr_ctrl", 2, "opencores", "sdrc_top",
        ("rtl/lib/async_fifo.v", "rtl/lib/sync_fifo.v", "rtl/wb2sdrc/wb2sdrc.v",
         "rtl/core/sdrc_bank_ctl.v", "rtl/core/sdrc_bank_fsm.v", "rtl/core/sdrc_bs_convert.v",
         "rtl/core/sdrc_core.v", "rtl/core/sdrc_req_gen.v", "rtl/core/sdrc_xfr_ctl.v",
         "rtl/top/sdrc_top.v"), ("rtl/core",),
        "LGPL-2.1+ per file header", "rtl/top/sdrc_top.v:44-46",
        True, "no memory in the elaborated design (rtl/lib/async_fifo.v:92 and sync_fifo.v:78 "
        "hold arrays but no module instantiates them: they are dropped by `flatten`); the "
        "tri-state on sdr_dq is lowered by Odin III with the enable dropped (warning "
        "recorded): no tri-state is left, the inout becomes an output"),
    OcDesign(
        "des", 2, "opencores", "des",
        ("rtl/verilog/perf_opt/des.v", "rtl/verilog/perf_opt/key_sel.v",
         "rtl/verilog/common/crp.v", "rtl/verilog/common/sbox1.v", "rtl/verilog/common/sbox2.v",
         "rtl/verilog/common/sbox3.v", "rtl/verilog/common/sbox4.v", "rtl/verilog/common/sbox5.v",
         "rtl/verilog/common/sbox6.v", "rtl/verilog/common/sbox7.v", "rtl/verilog/common/sbox8.v"),
        (), PERMISSIVE + " (Rudolf Usselmann, 2001)", "rtl/verilog/perf_opt/des.v:11-20",
        True, "no memory (the S-boxes are case statements, combinational), no tri-state"),
)


# Peter 2026-11-08: des is left out (size, owner's call); only licences that clearly permit
# redistribution of derived netlists without copyleft terms (BSD / MIT style, or an explicit
# "may be used and distributed without restriction" notice) are included; the rest are listed
# with their licence and left out.
_COPYLEFT = {"mmuart", "i2cslave", "spi", "uart2spi", "sdr_ctrl"}


def _apply_policy(d: OcDesign) -> OcDesign:
    if d.name == "des":
        return replace(d, admitted=False, category="size: des, left out per owner",
                       notes=d.reason, reason="left out per owner (size: 124035 gates, "
                       "1984 flip-flops)")
    if d.name in _COPYLEFT:
        return replace(d, admitted=False, category="licence: copyleft", notes=d.reason,
                       reason=f"copyleft licence ({d.licence.split(' per')[0].split(' (')[0]}); "
                       "left out, licence noted")
    if not d.admitted:
        cat = "licence: none stated" if d.licence.startswith("none stated") else "memory"
        return replace(d, category=cat)
    return d


DESIGNS: tuple[OcDesign, ...] = tuple(_apply_policy(d) for d in _SURVEY)


@dataclass
class ConvResult:
    name: str
    ok: bool
    why: str = ""
    gates: int = 0
    latches: int = 0
    inputs: int = 0
    outputs: int = 0
    seconds: float = 0.0
    sync_reset_bits: int = 0
    tribuf_dropped: int = 0
    warnings: list[str] = field(default_factory=list)


_SYNC = re.compile(r"asynchronous reset/set/load made synchronous on (\d+) flip-flop bits")
_TRI = re.compile(r"(\d+) '\$tribuf' cells lowered with the enable dropped")


def project_dir(root: Path, d: OcDesign) -> Path:
    return root / d.checkout / d.name


def check_licence_files(root: Path, d: OcDesign) -> list[str]:
    """The named source files exist (a missing one is an admission failure, not a guess)."""
    base = project_dir(root, d)
    return [f for f in d.files if not (base / f).is_file()]


def write_flist(root: Path, d: OcDesign, path: Path) -> None:
    base = project_dir(root, d)
    lines = [f"+incdir+{base / i}" for i in d.incdirs] + [str(base / f) for f in d.files]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def convert_design(root: Path, d: OcDesign, odin: Path, out_dir: Path) -> ConvResult:
    """Odin III (SCRIPT) to `out_dir/<name>.blif` in a memory-capped subprocess."""
    out_dir.mkdir(parents=True, exist_ok=True)
    missing = check_licence_files(root, d)
    if missing:
        return ConvResult(d.name, False, f"missing source files: {missing}")
    flist = out_dir / f"{d.name}.f"
    write_flist(root, d, flist)
    blif = out_dir / f"{d.name}.blif"
    cmd = [str(odin), "--top", d.top, "-f", str(flist), "-p",
           f'{SCRIPT}; write_blif --gates-as-names "{blif}"']

    def limits() -> None:
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))

    t0 = time.monotonic()
    try:
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT,
                             preexec_fn=limits, check=False)
    except subprocess.TimeoutExpired:
        return ConvResult(d.name, False, f"Odin III timeout {TIMEOUT} s")
    res = ConvResult(d.name, False, seconds=round(time.monotonic() - t0, 2))
    for ln in run.stderr.splitlines():
        m = _SYNC.search(ln)
        if m:
            res.sync_reset_bits = int(m.group(1))
        m = _TRI.search(ln)
        if m:
            res.tribuf_dropped = int(m.group(1))
    if run.returncode != 0 or not blif.exists():
        errs = [ln for ln in run.stderr.splitlines() if "error" in ln]
        res.why = (errs[0][:160] if errs else f"Odin III exit {run.returncode}")
        return res
    text = blif.read_text(encoding="utf-8")
    res.gates = sum(1 for ln in text.splitlines() if ln.startswith(".names"))
    res.latches = sum(1 for ln in text.splitlines() if ln.startswith(".latch"))
    if "\n.subckt " in text or "\n.gate " in text:
        res.why = "the BLIF still holds sub-circuits or gates"
        return res
    res.ok = True
    return res


def write_record(path: Path, results: list[ConvResult]) -> None:
    by = {r.name: r for r in results}
    rows = []
    for d in DESIGNS:
        row = asdict(d)
        row["files"] = list(d.files)
        row["incdirs"] = list(d.incdirs)
        r = by.get(d.name)
        row["conversion"] = asdict(r) if r else None
        rows.append(row)
    path.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")


def admitted() -> list[OcDesign]:
    return [d for d in DESIGNS if d.admitted]


def survey() -> list[OcDesign]:
    """The 12 designs before the licence / size policy (conversion record of every design)."""
    return list(_SURVEY)


def candidates_table() -> list[str]:
    """Markdown table of all 12 candidates: licence (file:line) and the verdict."""
    out = ["| base | wave | licence | read at | verdict |", "|---|---|---|---|---|"]
    for d in DESIGNS:
        verdict = "included" if d.admitted else f"excluded, {d.category}: {d.reason}"
        out.append(f"| {d.name} | {d.wave} | {d.licence} | {d.licence_where} | {verdict} |")
    return out
