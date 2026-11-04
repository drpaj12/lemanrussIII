"""rc1 (2026-11-04, Continuation 2 step 1): mcu's RAM as a black box, same construction as
`dark_ram_blackbox` (Peter 2026-11-03: "Yes for the black box ram", applies to every base).

mcu's memory is `dual_port_BRAM_byte_en`: four byte lanes, each a `dual_port_BRAM` of 8-bit words
with 2**12 entries (`MEM_ADDRESS_BITS` = 14, minus 2 byte-offset bits), 4 x 4096 x 8 = 131072
per-bit latches after `lower` (132446 FFs in all, rounds 9/10). The `memory` instance inside
`dual_port_BRAM_memory_subsystem` moves out of the lemanruss build's own scratch copy: the
subsystem and `single_cycle_BRAM_top` gain 7 `RAM_*` ports in its place, and `mcu_tb.v` gains a
behavioural replica of the RAM, written in the testbench's interpreted layer (never lowered, never
charged to the DUT's FF count). `dual_port_BRAM.v` and `dual_port_BRAM_byte_en.v` are dropped from
Odin III's `read_verilog` list. The iverilog copy (`iv/`) is untouched and keeps the real RAM.

The replica follows `dual_port_BRAM.v` as shipped: per lane, at `posedge clock`, port 1 read
(`readEnable_1`) and port 2 read (`readEnable_2`) sample the array BEFORE this cycle's write
(reads precede the blocking write in the original always block); port 1 never writes
(`writeEnable_1` tied to 0), port 2 writes lane i when `d_mem_write & d_mem_byte_en[i]`. The array
starts as zeros overlaid by `{0,1,2,3}<prog>.vmh`. Hardcoded: 12 address bits (a testbench cannot
read the DUT parameter); update by hand if `MEM_ADDRESS_BITS` ever changes.
"""

from __future__ import annotations

ADDR_BITS = 12  # MEM_ADDRESS_BITS (14) - log2(4 bytes)

SUB_PORT_TAIL = "  //scan signal\n  input      scan\n);"
SUB_PORT_TAIL_PATCHED = """\
  //scan signal
  input      scan,
  // rc1 (lemanruss, mcu_ram_blackbox): RAM moved out of this module into the testbench.
  // RAM_CTL = {d_mem_byte_en[3:0], d_mem_write, d_mem_read, i_mem_read}
  output     [6:0] RAM_CTL,
  output     [MEM_ADDRESS_BITS-3:0] RAM_IADDR,
  output     [MEM_ADDRESS_BITS-3:0] RAM_DADDR,
  output     [DATA_WIDTH-1:0] RAM_WDATA,
  input      [DATA_WIDTH-1:0] RAM_IDATA,
  input      [DATA_WIDTH-1:0] RAM_DDATA
);"""

_INST_START = "dual_port_BRAM_byte_en #("
_INST_END = "  .scan(scan)\n);\n"

SUB_REPLACEMENT = """\
// rc1 (lemanruss): the byte-enabled dual-port RAM instance is replaced by direct wiring to the
// RAM_* ports; the RAM itself is modelled in the testbench (see mcu_ram_blackbox).
assign RAM_CTL = {d_mem_byte_en, d_mem_write, d_mem_read, i_mem_read};
assign RAM_IADDR = i_mem_address_in[MEM_ADDRESS_BITS-1:log2(NUM_BYTES)];
assign RAM_DADDR = d_mem_address_in[MEM_ADDRESS_BITS-1:log2(NUM_BYTES)];
assign RAM_WDATA = d_mem_data_in;
assign i_mem_data_out = RAM_IDATA;
assign d_mem_data_out = RAM_DDATA;
"""

TOP_PORT_TAIL = "  input scan\n);"
TOP_PORT_TAIL_PATCHED = """\
  input scan,
  // rc1 (lemanruss, mcu_ram_blackbox): RAM ports, see dual_port_BRAM_memory_subsystem.
  output [6:0] RAM_CTL,
  output [MEM_ADDRESS_BITS-3:0] RAM_IADDR,
  output [MEM_ADDRESS_BITS-3:0] RAM_DADDR,
  output [DATA_WIDTH-1:0] RAM_WDATA,
  input  [DATA_WIDTH-1:0] RAM_IDATA,
  input  [DATA_WIDTH-1:0] RAM_DDATA
);"""
TOP_SCAN_CONN = "  .scan(scan)\n);\n\n\n// Interrupt Setup"
TOP_SCAN_CONN_PATCHED = (
    "  .scan(scan),\n  .RAM_CTL(RAM_CTL), .RAM_IADDR(RAM_IADDR), .RAM_DADDR(RAM_DADDR),\n"
    "  .RAM_WDATA(RAM_WDATA), .RAM_IDATA(RAM_IDATA), .RAM_DDATA(RAM_DDATA)\n"
    ");\n\n\n// Interrupt Setup"
)

_TB_DUT_ORIGINAL = """\
  single_cycle_BRAM_top dut (
    .clock(clock), .reset(reset), .start(start), .PC(pc),
    .PORTB_data_out(portb), .PORTD_data_out(portd),
    .PIND2_in(pind2), .PIND3_in(pind3), .scan(scan)
  );"""

_TB_DUT_PATCHED_TEMPLATE = """\
  // rc1 (lemanruss, mcu_ram_blackbox): behavioural replica of dual_port_BRAM_byte_en (4 lanes of
  // dual_port_BRAM). Reads sample before this cycle's write; port 1 never writes.
  wire [6:0] ram_ctl;
  wire [11:0] ram_iaddr;
  wire [11:0] ram_daddr;
  wire [31:0] ram_wdata;
  wire [31:0] ram_idata;
  wire [31:0] ram_ddata;
  reg [7:0] ram_l0 [0:4095];
  reg [7:0] ram_l1 [0:4095];
  reg [7:0] ram_l2 [0:4095];
  reg [7:0] ram_l3 [0:4095];
  reg [7:0] ri0;
  reg [7:0] ri1;
  reg [7:0] ri2;
  reg [7:0] ri3;
  reg [7:0] rd0;
  reg [7:0] rd1;
  reg [7:0] rd2;
  reg [7:0] rd3;
  assign ram_idata = {ri3, ri2, ri1, ri0};
  assign ram_ddata = {rd3, rd2, rd1, rd0};

  initial begin
    $readmemh("0__PROG__.vmh", ram_l0);
    $readmemh("1__PROG__.vmh", ram_l1);
    $readmemh("2__PROG__.vmh", ram_l2);
    $readmemh("3__PROG__.vmh", ram_l3);
  end

  always @(posedge clock) begin
    if (ram_ctl[0]) begin
      ri0 <= ram_l0[ram_iaddr];
      ri1 <= ram_l1[ram_iaddr];
      ri2 <= ram_l2[ram_iaddr];
      ri3 <= ram_l3[ram_iaddr];
    end
    if (ram_ctl[1]) begin
      rd0 <= ram_l0[ram_daddr];
      rd1 <= ram_l1[ram_daddr];
      rd2 <= ram_l2[ram_daddr];
      rd3 <= ram_l3[ram_daddr];
    end
    if (ram_ctl[2] && ram_ctl[3]) ram_l0[ram_daddr] <= ram_wdata[7:0];
    if (ram_ctl[2] && ram_ctl[4]) ram_l1[ram_daddr] <= ram_wdata[15:8];
    if (ram_ctl[2] && ram_ctl[5]) ram_l2[ram_daddr] <= ram_wdata[23:16];
    if (ram_ctl[2] && ram_ctl[6]) ram_l3[ram_daddr] <= ram_wdata[31:24];
  end

  single_cycle_BRAM_top dut (
    .clock(clock), .reset(reset), .start(start), .PC(pc),
    .PORTB_data_out(portb), .PORTD_data_out(portd),
    .PIND2_in(pind2), .PIND3_in(pind3), .scan(scan),
    .RAM_CTL(ram_ctl), .RAM_IADDR(ram_iaddr), .RAM_DADDR(ram_daddr),
    .RAM_WDATA(ram_wdata), .RAM_IDATA(ram_idata), .RAM_DDATA(ram_ddata)
  );"""

ODIN_DROPPED = ("dual_port_BRAM.v", "dual_port_BRAM_byte_en.v")


class PatchNotFound(ValueError):
    """The exact text this module edits was not found (upstream source changed under us)."""


def blackbox_subsystem(text: str) -> str:
    for needle in (SUB_PORT_TAIL, _INST_START, _INST_END):
        if needle not in text:
            raise PatchNotFound(f"memory subsystem: {needle!r} not found")
    text = text.replace(SUB_PORT_TAIL, SUB_PORT_TAIL_PATCHED)
    start = text.index(_INST_START)
    end = text.index(_INST_END, start) + len(_INST_END)
    return text[:start] + SUB_REPLACEMENT + text[end:]


def blackbox_top(text: str) -> str:
    for needle in (TOP_PORT_TAIL, TOP_SCAN_CONN):
        if needle not in text:
            raise PatchNotFound(f"single_cycle_BRAM_top: {needle!r} not found")
    text = text.replace(TOP_PORT_TAIL, TOP_PORT_TAIL_PATCHED, 1)
    return text.replace(TOP_SCAN_CONN, TOP_SCAN_CONN_PATCHED, 1)


def mcu_tb_with_ram_model(text: str, prog: str) -> str:
    if _TB_DUT_ORIGINAL not in text:
        raise PatchNotFound("mcu_tb.v dut instance not found")
    return text.replace(_TB_DUT_ORIGINAL, _TB_DUT_PATCHED_TEMPLATE.replace("__PROG__", prog))


def mcu_odin_files(files: list[str]) -> list[str]:
    """Odin III's `read_verilog` list: without the two RAM modules (iverilog keeps them)."""
    return [f for f in files if f not in ODIN_DROPPED]


__all__ = [
    "PatchNotFound",
    "blackbox_subsystem",
    "blackbox_top",
    "mcu_tb_with_ram_model",
    "mcu_odin_files",
]
