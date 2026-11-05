"""picorv32 build harness (rc1 Continuation 3, controller addition 2026-11-04: "Why can't we use
picorv32?"). picorv32 (external/picorv32, YosysHQ, ISC license) has no RAM of its own (unlike mcu
and darkriscv, its memory bus is external by design); upstream's own `testbench_ez.v` is a
reference-only port-only testbench with a built-in behavioural memory array, the same shape as
this repo's hand-written `mcu_tb.v`/`dark_tb.v` (CLAUDE.md: never commit external/'s content, so
this module writes its own testbench text rather than copying `testbench_ez.v`).

`pico_tb.v` (written below, not copied): a port-only wrapper (`picorv32 uut (...)`, matching the
mcu_tb.v/dark_tb.v convention so Odin III's `sim_tb` pass can read it the same way) around a
single 256-word memory array loaded by `$readmemh` from a program file this module also writes
(`write_pico_prog`, the same style as `lemanruss.htl.proc_images.write_dark_mem`). One trace line
per cycle: `<cycle> <trap> <mem_wstrb> <mem_addr> <mem_wdata>` (a store's address/data/strobe,
observable the same way mcu's PORTB/PORTD and darkriscv's OPORT witnesses are: the Trojan's
effect or stealth is read off a memory-mapped write, not off an internal register).

No RISC-V cross toolchain is installed in this workspace; every program here is hand-assembled
with `lemanruss.htl.rv32i`'s encoder (same as the mcu/darkriscv witness programs), stated per the
controller's instruction.
"""

from __future__ import annotations

from pathlib import Path

PICO_TB_TEMPLATE = """\
// Port-only testbench for picorv32 (hand-written for lemanruss; not copied from upstream's own
// testbench_ez.v, per repo rule "never commit external/'s content"). One line per cycle at the
// posedge clock: cycle trap mem_wstrb mem_addr mem_wdata (a store transaction's fields; reads are
// not traced, so the witness's own effect is observed via its own memory-mapped write).
`timescale 1 ns / 1 ns
module pico_tb;
  parameter CYCLES = 300;
  reg clk;
  reg resetn;
  integer cycle;
  wire trap;
  wire mem_valid, mem_instr;
  reg mem_ready;
  wire [31:0] mem_addr;
  wire [31:0] mem_wdata;
  wire [3:0] mem_wstrb;
  reg [31:0] mem_rdata;

  picorv32 uut (
    .clk(clk), .resetn(resetn), .trap(trap),
    .mem_valid(mem_valid), .mem_instr(mem_instr), .mem_ready(mem_ready),
    .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata)
  );

  reg [31:0] memory [0:255];
  reg [31:0] mem_next;
  initial $readmemh("pico_prog.mem", memory);

  initial begin
    clk = 0; resetn = 0; cycle = 0; mem_ready = 0;
  end

  always #5 clk = ~clk;
  initial #40 resetn = 1;

  // Odin III's sim_tb testbench subset refuses a part-select on an array-indexed expression
  // (round 10 note, docs/results-round10.md section 4.0, found there for a RAM model): the byte
  // merge happens on the plain scratch reg `mem_next`, never on `memory[...]` directly; only a
  // whole-word read and a whole-word write touch the array itself.
  always @(posedge clk) begin
    mem_ready <= 0;
    if (mem_valid && !mem_ready) begin
      mem_ready <= 1;
      mem_rdata <= memory[mem_addr[9:2]];
      mem_next = memory[mem_addr[9:2]];
      if (mem_wstrb[0]) mem_next[7:0] = mem_wdata[7:0];
      if (mem_wstrb[1]) mem_next[15:8] = mem_wdata[15:8];
      if (mem_wstrb[2]) mem_next[23:16] = mem_wdata[23:16];
      if (mem_wstrb[3]) mem_next[31:24] = mem_wdata[31:24];
      if (mem_wstrb != 4'b0000) memory[mem_addr[9:2]] <= mem_next;
    end
  end

  always @(posedge clk) begin
    $display("%0d %b %b %h %h", cycle, trap, mem_wstrb, mem_addr, mem_wdata);
    cycle = cycle + 1;
    if (cycle == CYCLES) $finish;
  end
endmodule
"""


def write_pico_tb(out_dir: Path, cycles: int = 300) -> Path:
    path = out_dir / "pico_tb.v"
    text = PICO_TB_TEMPLATE.replace(
        "parameter CYCLES = 300;", f"parameter CYCLES = {cycles};")
    path.write_text(text)
    return path


def write_pico_prog(words: list[int], out_path: Path, depth: int = 256) -> Path:
    """Writes a 256-word (default) `$readmemh` program image; `words` fill addresses 0.., the
    rest default to 0 (picorv32's own reset vector is address 0, `PROGADDR_RESET` default)."""
    lines = [f"{w & 0xFFFFFFFF:08x}" for w in words]
    lines += ["00000000"] * max(0, depth - len(words))
    out_path.write_text("\n".join(lines[:depth]) + "\n")
    return out_path
