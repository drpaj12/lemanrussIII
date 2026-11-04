"""rc1 (2026-11-04, controller finding): darkriscv's `darkram` module is a single `reg [31:0]
MEM[0:2047]` array (`` `MLEN `` = 13, rtl/config.vh) with a byte-enable split write (four separate
conditional byte writes keyed on `XBE[i]`). Odin III's `hardmap`/`partial_map` RAM mapping
explicitly leaves an inferred memory with "a split write enable" soft for `lower`
(`docs/PASSES.md`'s `partial_map` row, R-8..R-12), so it cannot be bound to the `vtr.o3lib`
`single_port_ram`/`dual_port_ram` hard cells; `lower` then expands the 2048x32 array into
per-bit latches (67638 FFs total, round 9/10's finding), far outside the Comb/Seq detector
training range (spec `docs/specs/2026-11-03-seeker-proc-rc1.md` section 6) and slow enough that
Odin III's own cycle simulator takes 30+ minutes per 500-cycle witness run on it.

Fix (not an Odin III change -- `darkriscv.v`/`darkriscv` core logic is untouched, and this patches
only the lemanruss build's own scratch copy, never `external/darkriscv` or the Odin III repo):
move the `darkram` instance out of `darksocv.v`'s hierarchy, so Odin III's `read_verilog` for this
copy never reads `darkram.v` at all and so never sees its array. `darksocv.v` gains new top-level
`RAM_*` ports in its place (plain assigns to the wires the removed instance used to drive).
`dark_tb.v` gains a hand-written behavioural replica of `darkram`'s *active* configuration (default
`config.vh`: `__HARVARD__` defined, `__ICACHE__`/`__RMW_CYCLE__`/`__WAITSTATE__` undefined --
single-cycle-latency synchronous read, `IDACK == IDREQ`, no read-modify-write) wired to those new
ports -- a `reg`/`always` block in the TESTBENCH's own interpreted layer (`sim_tb`'s supported
subset, `docs/user/testbench.md`: "What is supported" lists `reg`/array declarations, `always`,
`$readmemh`), never passed through `proc`/`opt`/`lower`, so it costs nothing and is never charged
to the DUT's FF count.

This changes *only* the lemanruss-built copy Odin III reads (`out/rtl/`); the iverilog copy
(`out/iv/rtl/`) is untouched and keeps the real `darkram.v` instance unpatched, so both engines
simulate functionally identical behaviour and `run_dark_once`'s cross-engine trace comparison
still holds. `dark_odin_files` drops `darkram.v` from the file list passed to Odin III's own
`read_verilog` (the iverilog file list, built from `prepare_dark`'s unfiltered return value, is
unaffected).

Known fragility (not root-caused further, logged as an open item): the behavioural model
hardcodes `` `MLEN `` = 13 (2048 32-bit words) as a Python/Verilog literal, since a testbench file
cannot `` `include `` config.vh (`docs/user/testbench.md`: "compiler directives other than
`timescale`" stop the run); if a future base config changes `` `MLEN ``, this constant must be
updated by hand.
"""

from __future__ import annotations

MLEN = 13  # rtl/config.vh `MLEN (8kB for darkshell); hardcoded, see module docstring.
_MEM_WORDS = 2**MLEN // 4

DARKSOCV_PORT_TAIL = "    output [3:0]  DEBUG      // osciloscope\n);"
DARKSOCV_PORT_TAIL_PATCHED = """\
    output [3:0]  DEBUG,      // osciloscope

    // rc1 (2026-11-04, lemanruss): darkram's instance moves out of this module (see
    // lemanruss.htl.dark_ram_blackbox); these ports replace that one internal instantiation.
    // sim_tb refuses a DUT instance with more than 16 port connections (darksocv already has 8,
    // so at most 8 more fit); the single-bit control signals are bundled into two buses:
    // RAM_CTL0 = {HLT, RES}, RAM_CTL1 = {XBE[3:0], XWR, XRD, XDREQ, IDREQ} (outputs),
    // RAM_CTL2 = {XDACK, IDACK} (input).
    output [1:0]  RAM_CTL0,
    output [7:0]  RAM_CTL1,
    input  [1:0]  RAM_CTL2,
    output [31:0] RAM_IADDR,
    input  [31:0] RAM_IDATA,
    output [31:0] RAM_XADDR,
    output [31:0] RAM_XATAI,
    input  [31:0] RAM_XATAO
);"""

DARKRAM_INSTANCE_BLOCK = (
    "    darkram bram0\n"
    "    (\n"
    "        .CLK    (CLK),\n"
    "        .RES    (RES),\n"
    "        .HLT    (HLT),\n"
    "        \n"
    "        .IDREQ  (IDREQ),\n"
    "        .IADDR  (IADDR),\n"
    "        .IDATA  (IDATA),\n"
    "        .IDACK  (IDACK),\n"
    "        \n"
    "        .XDREQ  (XDREQMUX[0]),\n"
    "        .XRD    (XRD),\n"
    "        .XWR    (XWR),\n"
    "        .XBE    (XBE),\n"
    "        .XADDR  (XADDR),\n"
    "        .XATAI  (XATAO),\n"
    "        .XATAO  (XATAIMUX[0]),\n"
    "        .XDACK  (XDACKMUX[0])\n"
    "    );"
)

DARKRAM_INSTANCE_REPLACEMENT = """\
    // rc1 (2026-11-04, lemanruss): darkram's instance replaced by direct wiring to the new
    // RAM_* top-level ports (see lemanruss.htl.dark_ram_blackbox). Bit order: RAM_CTL0 =
    // {HLT, RES}, RAM_CTL1 = {XBE[3:0], XWR, XRD, XDREQ, IDREQ}, RAM_CTL2 = {XDACK, IDACK}.
    assign RAM_CTL0 = {HLT, RES};
    assign RAM_CTL1 = {XBE, XWR, XRD, XDREQMUX[0], IDREQ};
    assign RAM_IADDR = IADDR;
    assign IDATA     = RAM_IDATA;
    assign IDACK     = RAM_CTL2[0];
    assign RAM_XADDR = XADDR;
    assign RAM_XATAI = XATAO;
    assign XATAIMUX[0] = RAM_XATAO;
    assign XDACKMUX[0] = RAM_CTL2[1];"""

_TB_SOC0_ORIGINAL = """\
  darksocv soc0 (
    .XCLK(clock), .XRES(res), .UART_RXD(1'b1), .UART_TXD(txd),
    .LED(led), .IPORT(32'd0), .OPORT(oport), .DEBUG(dbg)
  );"""

# Plain string (not f-string/`.format()`): the Verilog body below is full of literal `{`/`}`
# concatenation syntax, which would have to be doubled throughout for either; `__WORDS__` and
# `__MLEN__` are substituted with a plain `.replace()` instead (unambiguous: neither token can
# appear in Verilog source).
_TB_SOC0_PATCHED_TEMPLATE = """\
  // RAM_CTL0 = {ram_hlt, ram_res}, RAM_CTL1 = {ram_xbe[3:0], ram_xwr, ram_xrd,
  // ram_xdreq, ram_idreq}, RAM_CTL2 = {ram_xdack, ram_idack} (see lemanruss.htl.
  // dark_ram_blackbox: darksocv's RAM_* ports are bundled to stay within sim_tb's 16-port limit).
  wire [1:0]  ram_ctl0;
  wire [7:0]  ram_ctl1;
  wire [1:0]  ram_ctl2;
  wire        ram_res, ram_hlt;
  wire        ram_idreq, ram_xdreq, ram_xrd, ram_xwr;
  wire [3:0]  ram_xbe;
  wire [31:0] ram_iaddr, ram_xaddr, ram_xatai;
  wire [31:0] ram_idata;
  wire [31:0] ram_xatao;

  assign ram_res   = ram_ctl0[0];
  assign ram_hlt   = ram_ctl0[1];
  assign ram_idreq = ram_ctl1[0];
  assign ram_xdreq = ram_ctl1[1];
  assign ram_xrd   = ram_ctl1[2];
  assign ram_xwr   = ram_ctl1[3];
  assign ram_xbe   = ram_ctl1[7:4];

  // The RAM clock is the testbench's own `clock` (CLK = XCLK in this config): a DUT output
  // carrying the clock cannot clock a node in the netlist sim (clocks must be primary inputs).
  // rc1 (2026-11-04, lemanruss): behavioural replica of darkram.v's active configuration
  // (__HARVARD__ defined, __ICACHE__/__RMW_CYCLE__/__WAITSTATE__ undefined -- single-cycle-
  // latency synchronous read, IDACK == IDREQ, no read-modify-write; see
  // lemanruss.htl.dark_ram_blackbox). Interpreted by the testbench, never lowered.
  reg [31:0] ram_model [0:__WORDS__-1];
  reg [31:0] ram_romff;
  reg [31:0] ram_ramff;
  reg [3:0]  ram_dtack;
  wire [31:0] ram_xrdata;
  wire [31:0] ram_wdata;

  assign ram_idata = ram_romff;
  assign ram_xatao = ram_ramff;
  assign ram_ctl2 = {((ram_dtack == 1) || (ram_xdreq && ram_xwr)), ram_idreq};
  // rc1: sim_tb's testbench subset refuses a part-select on an array-indexed expression at all
  // (read or write: "not a memory word, which has no name after lower; no part-selects",
  // docs/user/testbench.md) -- `ram_model[addr][bits]` is refused either as an assignment target
  // or inside an expression. `ram_xrdata` reads the whole word first (no slice on the array
  // expression itself); the per-byte old-vs-new mux then slices `ram_xrdata`, a plain wire, and
  // the write below targets the whole word, never a slice of `ram_model`.
  assign ram_xrdata = ram_model[ram_xaddr[__MLEN__-1:2]];
  assign ram_wdata = {
    ram_xbe[3] ? ram_xatai[31:24] : ram_xrdata[31:24],
    ram_xbe[2] ? ram_xatai[23:16] : ram_xrdata[23:16],
    ram_xbe[1] ? ram_xatai[15:8]  : ram_xrdata[15:8],
    ram_xbe[0] ? ram_xatai[7:0]   : ram_xrdata[7:0]
  };

  darksocv soc0 (
    .XCLK(clock), .XRES(res), .UART_RXD(1'b1), .UART_TXD(txd),
    .LED(led), .IPORT(32'd0), .OPORT(oport), .DEBUG(dbg),
    .RAM_CTL0(ram_ctl0), .RAM_CTL1(ram_ctl1), .RAM_CTL2(ram_ctl2),
    .RAM_IADDR(ram_iaddr), .RAM_IDATA(ram_idata),
    .RAM_XADDR(ram_xaddr), .RAM_XATAI(ram_xatai), .RAM_XATAO(ram_xatao)
  );

  initial $readmemh("../src/darksocv.mem", ram_model, 0);

  always @(posedge clock) begin
    ram_romff <= ram_model[ram_iaddr[__MLEN__-1:2]];
    ram_dtack <= ram_res ? 0 : (ram_dtack ? ram_dtack - 1 : ((ram_xdreq && ram_xrd) ? 1 : 0));
    ram_ramff <= ram_model[ram_xaddr[__MLEN__-1:2]];
    if (ram_xwr && ram_xdreq)
      ram_model[ram_xaddr[__MLEN__-1:2]] <= ram_wdata;
  end"""

_TB_SOC0_PATCHED = (
    _TB_SOC0_PATCHED_TEMPLATE.replace("__WORDS__", str(_MEM_WORDS)).replace(
        "__MLEN__", str(MLEN)
    )
)


class PatchNotFound(ValueError):
    """The exact text this module edits was not found (upstream source changed under us)."""


def blackbox_darksocv(text: str) -> str:
    """Patches one copy of `darksocv.v`: removes the `darkram` instance, exposes its connections
    as new `RAM_*` top-level ports instead."""
    if DARKSOCV_PORT_TAIL not in text:
        raise PatchNotFound("darksocv.v port tail not found")
    if DARKRAM_INSTANCE_BLOCK not in text:
        raise PatchNotFound("darkram bram0 instance not found")
    text = text.replace(DARKSOCV_PORT_TAIL, DARKSOCV_PORT_TAIL_PATCHED)
    text = text.replace(DARKRAM_INSTANCE_BLOCK, DARKRAM_INSTANCE_REPLACEMENT)
    return text


def dark_tb_with_ram_model(text: str) -> str:
    """Patches one copy of `dark_tb.v`: wires the new `darksocv` `RAM_*` ports to a behavioural
    RAM model written directly in the testbench (never passed through Odin III's `lower`)."""
    if _TB_SOC0_ORIGINAL not in text:
        raise PatchNotFound("dark_tb.v's darksocv instance not found")
    return text.replace(_TB_SOC0_ORIGINAL, _TB_SOC0_PATCHED)


def dark_odin_files(files: list[str]) -> list[str]:
    """Drops `darkram.v` from a `prepare_dark`-returned file list, for the call sites that build
    Odin III's own `read_verilog` command line on the (blackboxed) main copy only -- the iverilog
    copy (`iv/`) is untouched and still needs `darkram.v` in its own file list."""
    return [f for f in files if f != "darkram.v"]


__all__ = [
    "PatchNotFound",
    "blackbox_darksocv",
    "dark_tb_with_ram_model",
    "dark_odin_files",
]
