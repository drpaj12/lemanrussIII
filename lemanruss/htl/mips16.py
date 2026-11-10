"""Seeker-Proc rc3: the fourth base, OpenCores `mips_16` (a 16-bit, 5-stage, 13-instruction MIPS
style pipeline with an 8-register file; `external/opencores/mips_16`, rtl/ only).

Why this base (Peter 2026-11-06, "add mips_16 as a 4th Proc base"): the processor set needs four
cores for the outside-the-training-range test and for leave-one-base-out level 3; mips_16 is
smaller than every earlier base (about 250 flip-flops after the memories are taken out).

What this module does, in the style of the other bases (`picorv32_tb`, `proc_insert`):

* `prepare_mips16` copies the core's RTL into a scratch directory (never into this repository),
  applies a small set of *deterministic-variant* patches, takes the instruction ROM and the data
  RAM out of the core (they become ports, modelled in the hand-written testbench `mips_tb.v`, so
  Odin III never expands them into latches, as for the other black-boxed memories) and writes the
  testbench. Patches (each is an exact text replace that fails loudly when the upstream text
  moved):
    1. `ALU_NC` (the "not care" ALU command, `3'bxxx`) becomes `3'b000`, the first arm of the ALU
       case (`ALU_NC: r = 16'bx;`, which matches every command in synthesis and folds the whole
       datapath, Mimir row note) is removed, and the decoder's `1'bx` don't-cares become `1'b0`.
       Reason: four-state iverilog and the two-state Odin III simulator must agree on every
       program (the XOR operand mux was `x`, so XOR was undefined). The result is an ordinary,
       fully specified mips_16; the datasheet says so.
    2. `CODE_FOR_SYNTHESIS` is defined (drops the `$display` error messages).
    3. ROM and RAM become ports (`imem_instruction`, `dmem_*`) and three observation ports
       (`dbg_wb_*`) expose the write-back stage, so synthesis keeps the datapath.
* `insert_mips16` adds 1 to 3 independent Trojans (payload kinds reset, stall, alu) to the
  infected copy. Trigger: the 16-bit instruction register `instruction_reg` of `ID_stage`
  (reset to 0, holds while the decode stage is frozen), compared with one magic word per Trojan.
  Payloads: reset restarts the program counter at 0 (`IF_stage`); stall freezes fetch and decode
  (`pipeline_stall_n` ANDed with the trigger); alu flips bit 0 of a shift-right result while the
  instruction register holds the magic word (the magic word of an alu Trojan is the instruction
  *after* a shift-right: when that shift is in the execute stage the register already holds the
  next word, the same offset picorv32 has). No Trojan adds a flip-flop.
* Programs are hand-assembled with the encoder below (no toolchain), witness programs follow the
  other bases' scheme (activation program in the answer key only).

Region definition for the answer key: see `lemanruss.htl.proc_regions`.
"""

from __future__ import annotations

import random
import re
import subprocess
from pathlib import Path

from lemanruss.htl.proc_insert import PatchNotFound
from lemanruss.htl.procmask import masking_on

MIPS_UPSTREAM_NAME = "external/opencores/mips_16/rtl"
TOP = "mips_16_core_top"
WITNESS_CYCLES = 120
SHIPPED_CYCLES = {"test1": 400, "test2": 700}
SHIPPED = ("test1", "test2")
PROG_DEPTH = 256

OPS = {"NOP": 0, "ADD": 1, "SUB": 2, "AND": 3, "OR": 4, "XOR": 5, "SL": 6, "SR": 7, "SRU": 8,
       "ADDI": 9, "LD": 10, "ST": 11, "BZ": 12}
# Magic-word instruction set: register-writing ALU forms with a defined destination (r1..r7),
# so the word is a legal, observable instruction (no branch, no store: those would redirect or
# clobber the witness).
MAGIC_OPS = ("ADD", "SUB", "AND", "OR", "XOR", "SL", "SR", "SRU", "ADDI")
STOP = [0b1100000000111111, 0]  # BZ R0,-1 ; NOP : the stop loop of the project's test2
NOP = 0
GAP = 4  # nops between dependent steps (hazard unit stalls anyway; this keeps traces short)


def enc_r(op: str, rd: int, rs1: int, rs2: int) -> int:
    assert 0 <= rd < 8 and 0 <= rs1 < 8 and 0 <= rs2 < 8
    return (OPS[op] << 12) | (rd << 9) | (rs1 << 6) | (rs2 << 3)


def enc_i(op: str, rd: int, rs1: int, imm: int) -> int:
    assert -32 <= imm < 32, f"6-bit immediate out of range: {imm}"
    return (OPS[op] << 12) | (rd << 9) | (rs1 << 6) | (imm & 63)


def random_magic_word(rng: random.Random, exclude: set[int]) -> int:
    """A random legal, register-writing mips_16 word (module note), not in `exclude`."""
    while True:
        op = rng.choice(MAGIC_OPS)
        rd, rs1 = rng.randrange(1, 8), rng.randrange(0, 8)
        word = (enc_i(op, rd, rs1, rng.randrange(-32, 32)) if op == "ADDI"
                else enc_r(op, rd, rs1, rng.randrange(0, 8)))
        if word not in exclude and word != NOP:
            return word


def scaffolding_words() -> set[int]:
    """Every fixed word the witness and neutral programs use, so a magic word never equals one."""
    words = {NOP, *STOP}
    for rd in range(1, 8):
        for rs in range(8):
            for imm in (-1, 1, 5, 6, 21):
                words.add(enc_i("ADDI", rd, rs, imm))
            words.add(enc_r("SRU", rd, rs, 2))
    return words


def read_prog(path: Path) -> list[int]:
    """The words of a `$readmemb` program image (one 16-bit binary word per line)."""
    return [int(t, 2) for ln in path.read_text().splitlines()
            for t in ln.split("//")[0].split() if set(t) <= {"0", "1"}]


def shipped_words(upstream: Path) -> set[int]:
    """Every instruction word of the project's own shipped programs (`bench/mips_16_core_top`)."""
    out: set[int] = set()
    for name in SHIPPED:
        p = upstream.parent / "bench" / "mips_16_core_top" / f"{name}.prog"
        if p.exists():
            out |= set(read_prog(p))
    return out


def forbidden_words(upstream: Path) -> set[int]:
    return scaffolding_words() | shipped_words(upstream)


def neutral_word(word: int) -> int:
    """A word that is not `word` but is the same kind of instruction (low bit flipped)."""
    return word ^ 1


def witness_words(magic_words: list[int]) -> list[int]:
    """Reset/stall witness: setup, each magic word followed by NOPs, a marker write, the stop
    loop. `[]` is the neutral witness (no magic word anywhere)."""
    prog = [NOP, NOP, enc_i("ADDI", 1, 0, 21), *[NOP] * GAP]
    for w in magic_words:
        prog += [w, *[NOP] * GAP]
    prog += [enc_i("ADDI", 3, 0, 5), *[NOP] * GAP, enc_i("ADDI", 4, 0, 6), *[NOP] * GAP, *STOP]
    return prog


def alu_witness_words(word: int) -> list[int]:
    """Alu witness: r1 = 0xFFFF, r2 = 1, `SRU r3,r1,r2` immediately followed by the magic word
    (while the shift is in the execute stage the instruction register holds the magic word); the
    shift result (0x7FFF; 0x7FFE with the Trojan) is seen on the write-back port."""
    return [NOP, NOP, enc_i("ADDI", 1, 0, -1), enc_i("ADDI", 2, 0, 1), *[NOP] * GAP,
            enc_r("SRU", 3, 1, 2), word, *[NOP] * GAP, enc_i("ADDI", 4, 0, 6), *[NOP] * GAP, *STOP]


def write_prog(words: list[int], path: Path) -> None:
    lines = [f"{w & 0xFFFF:016b}" for w in words]
    lines += ["0" * 16] * max(0, PROG_DEPTH - len(words))
    path.write_text("\n".join(lines[:PROG_DEPTH]) + "\n")


# --- patches --------------------------------------------------------------------------------

def _sub1(text: str, pattern: str, repl: str, what: str) -> str:
    new, n = re.subn(pattern, lambda _m: repl, text, count=0, flags=re.S)
    if n != 1:
        raise PatchNotFound(f"mips_16 patch {what!r}: {n} matches, expected 1")
    return new


def _variant(files: dict[str, str]) -> dict[str, str]:
    """The deterministic variant plus the memory-out ports (module note, patches 1 to 3)."""
    f = dict(files)
    f["alu.v"] = _sub1(f["alu.v"], r"\t*`ALU_NC\s*:\s*r = 16'bx;\s*", "", "alu NC arm")
    d = f["mips_16_defs.v"]
    d = _sub1(d, r"`define ALU_NC\s+3'bxxx", "`define ALU_NC 3'b000", "ALU_NC value")
    d = _sub1(d, r"//`define CODE_FOR_SYNTHESIS[^\n]*", "`define CODE_FOR_SYNTHESIS", "synthesis")
    f["mips_16_defs.v"] = d
    f["ID_stage.v"] = f["ID_stage.v"].replace("1'bx;", "1'b0;")
    if "1'bx" in f["ID_stage.v"]:
        raise PatchNotFound("mips_16 ID_stage still holds 1'bx")
    # instruction ROM out of IF_stage
    i = f["IF_stage.v"]
    i = _sub1(i, r"output\s+\[15:0\]\s+instruction\s*\)",
              "input [15:0] imem_instruction,\n\toutput [15:0] instruction\n)", "IF ports")
    i = _sub1(i, r"instruction_mem\s+imem\s*\(.*?\);", "assign instruction = imem_instruction;",
              "IF rom")
    f["IF_stage.v"] = i
    # data RAM out of MEM_stage
    m = f["MEM_stage.v"]
    m = _sub1(m, r"output\s+\[2:0\]\s+mem_op_dest\s*\)",
              "output [2:0] mem_op_dest,\n\toutput [15:0] dmem_addr,\n\toutput [15:0] dmem_wdata,\n"
              "\toutput dmem_we,\n\tinput [15:0] dmem_rdata\n)", "MEM ports")
    m = _sub1(m, r"data_mem\s+dmem\s*\(.*?\);",
              "assign dmem_addr = ex_alu_result;\n\tassign dmem_wdata = mem_write_data;\n"
              "\tassign dmem_we = mem_write_en;\n\tassign mem_read_data = dmem_rdata;", "MEM ram")
    f["MEM_stage.v"] = m
    t = f["mips_16_core_top.v"]
    t = _sub1(t, r"output\s+\[`PC_WIDTH-1:0\]\s+pc\s*\)",
              "output [`PC_WIDTH-1:0] pc,\n\tinput [15:0] imem_instruction,\n"
              "\toutput [15:0] dmem_addr,\n\toutput [15:0] dmem_wdata,\n\toutput dmem_we,\n"
              "\tinput [15:0] dmem_rdata,\n\toutput dbg_wb_en,\n\toutput [2:0] dbg_wb_dest,\n"
              "\toutput [15:0] dbg_wb_data\n)", "top ports")
    t = _sub1(t, r"IF_stage IF_stage_inst \(",
              "IF_stage IF_stage_inst (\n\t\t.imem_instruction(imem_instruction),", "top IF inst")
    t = _sub1(t, r"MEM_stage MEM_stage_inst \(",
              "MEM_stage MEM_stage_inst (\n\t\t.dmem_addr(dmem_addr), .dmem_wdata(dmem_wdata),"
              "\n\t\t.dmem_we(dmem_we), .dmem_rdata(dmem_rdata),", "top MEM inst")
    t = _sub1(t, r"endmodule\s*$",
              "assign dbg_wb_en = reg_write_en;\nassign dbg_wb_dest = reg_write_dest;\n"
              "assign dbg_wb_data = reg_write_data;\nendmodule\n", "top dbg")
    f["mips_16_core_top.v"] = t
    return f


def _trigger_decl(magic_words: list[int], kinds: list[str], *, force_inactive: bool) -> str:
    if len(magic_words) != len(kinds) or not magic_words:
        raise ValueError("one kind per magic word, at least one")
    if len(set(magic_words)) != len(magic_words):
        raise ValueError("magic_words must be pairwise distinct")
    bad = [k for k in kinds if k not in ("reset", "stall", "alu")]
    if bad:
        raise ValueError(f"bad kinds {bad}")
    names = [f"__htl_trigger_{i}" for i in range(len(magic_words))]
    if force_inactive:
        lines = [f"wire {n} = 1'b0;" for n in names]
    else:
        lines = [f"wire {n} = (__htl_ir == 16'h{w:04x});"
                 for n, w in zip(names, magic_words, strict=True)]
    for kind in ("reset", "stall", "alu"):
        sel = [n for n, k in zip(names, kinds, strict=True) if k == kind]
        expr = " | ".join(sel) if sel else "1'b0"
        if sel and masking_on():  # v2.0 rule: no payload acts while rst (active high) is on
            expr = f"({expr}) & ~rst"
        lines.append(f"wire __htl_trigger_{kind} = {expr};")
    return "\n".join(lines) + "\n"


def insert_mips16(
    files: dict[str, str], magic_words: list[int], kinds: list[str], *, force_inactive: bool = False
) -> dict[str, str]:
    """The infected copy of the (already variant-patched) files."""
    trig = _trigger_decl(magic_words, kinds, force_inactive=force_inactive)
    f = dict(files)
    i = f["ID_stage.v"]
    i = _sub1(i, r"output\s+\[5:0\]\s+branch_offset_imm,",
              "output [5:0] branch_offset_imm,\n\toutput [15:0] __htl_ir,", "ID port")
    i = _sub1(i, r"endmodule\s*$", "assign __htl_ir = instruction_reg;\nendmodule\n", "ID tap")
    f["ID_stage.v"] = i
    s = f["IF_stage.v"]
    s = _sub1(s, r"input\s+instruction_fetch_en,",
              "input instruction_fetch_en,\n\tinput __htl_pc_rst,", "IF port")
    s = _sub1(s, r"\t\telse begin\s+if\(instruction_fetch_en\) begin",
              "\t\telse if (__htl_pc_rst) begin\n\t\t\tpc <= `PC_WIDTH'b0;\n\t\tend\n"
              "\t\telse begin\n\t\t\tif(instruction_fetch_en) begin", "IF reset payload")
    f["IF_stage.v"] = s
    e = f["EX_stage.v"]
    e = _sub1(e, r"input\s+rst,", "input rst,\n\tinput __htl_alu_flip,", "EX port")
    e = _sub1(e, r"pipeline_reg_out\[37:22\] <= ex_alu_result;",
              "pipeline_reg_out[37:22] <= ex_alu_result ^ {15'b0, __htl_alu_flip "
              "& (alu_cmd == 3'b110 | alu_cmd == 3'b111)};", "EX alu payload")
    f["EX_stage.v"] = e
    t = f["mips_16_core_top.v"]
    t = _sub1(t, r"\.pipeline_stall_n\s*\(pipeline_stall_n\)", ".pipeline_stall_n(__htl_stall_raw)",
              "hazard out")
    t = _sub1(t, r"ID_stage ID_stage_inst \(", "ID_stage ID_stage_inst (\n\t\t.__htl_ir(__htl_ir),",
              "ID inst")
    t = _sub1(t, r"IF_stage IF_stage_inst \(",
              "IF_stage IF_stage_inst (\n\t\t.__htl_pc_rst(__htl_trigger_reset),", "IF inst")
    t = _sub1(t, r"EX_stage EX_stage_inst \(",
              "EX_stage EX_stage_inst (\n\t\t.__htl_alu_flip(__htl_trigger_alu),", "EX inst")
    decl = ("wire [15:0] __htl_ir;\nwire __htl_stall_raw;\n"
            + trig
            + "assign pipeline_stall_n = __htl_stall_raw & ~__htl_trigger_stall;\n")
    t = _sub1(t, r"endmodule\s*$", decl + "endmodule\n", "top decl")
    f["mips_16_core_top.v"] = t
    return f


# --- testbench --------------------------------------------------------------------------------

TB_TEMPLATE = """\
// Port-only testbench for mips_16 (hand-written for lemanruss). ROM and RAM are modelled here, so
// the core is the only thing Odin III elaborates. One line per cycle: cycle pc wb_en wb_dest data.
`timescale 1ns/1ps
module mips_tb;
  parameter CYCLES = 120;
  reg clk;
  reg rst;
  integer cycle;
  wire [7:0] pc;
  wire [15:0] dmem_addr, dmem_wdata;
  wire dmem_we;
  wire dbg_wb_en;
  wire [2:0] dbg_wb_dest;
  wire [15:0] dbg_wb_data;
  reg [15:0] rom [0:255];
  reg [15:0] ram [0:255];
  wire [15:0] imem_instruction;
  wire [15:0] dmem_rdata;
  assign imem_instruction = rom[pc];
  assign dmem_rdata = ram[dmem_addr[7:0]];
  initial $readmemb("mips_prog.mem", rom);
  initial $readmemb("mips_zero.mem", ram);

  mips_16_core_top uut (
    .clk(clk), .rst(rst), .pc(pc), .imem_instruction(imem_instruction),
    .dmem_addr(dmem_addr), .dmem_wdata(dmem_wdata), .dmem_we(dmem_we), .dmem_rdata(dmem_rdata),
    .dbg_wb_en(dbg_wb_en), .dbg_wb_dest(dbg_wb_dest), .dbg_wb_data(dbg_wb_data)
  );

  initial begin
    clk = 0; rst = 1; cycle = 0;
  end
  always #5 clk = ~clk;
  initial #43 rst = 0;

  always @(posedge clk) begin
    if (dmem_we) ram[dmem_addr[7:0]] <= dmem_wdata;
  end

  always @(negedge clk) begin
    $display("%0d %h %b %h %h", cycle, pc, dbg_wb_en, dbg_wb_dest, dbg_wb_data);
    cycle = cycle + 1;
    if (cycle == CYCLES) $finish;
  end
endmodule
"""


def _rd(path: Path) -> str:
    return path.read_text()  # universal newlines: upstream files carry CRLF


def load_upstream(up: Path) -> dict[str, str]:
    names = ["alu.v", "EX_stage.v", "ID_stage.v", "IF_stage.v", "MEM_stage.v", "WB_stage.v",
             "hazard_detection_unit.v", "mips_16_core_top.v", "register_file.v",
             "mips_16_defs.v"]
    return {n: _rd(up / n) for n in names}


DESIGN_FILES = ["alu.v", "EX_stage.v", "ID_stage.v", "IF_stage.v", "MEM_stage.v", "WB_stage.v",
                "hazard_detection_unit.v", "register_file.v", "mips_16_core_top.v"]


def _write_dir(d: Path, files: dict[str, str], cycles: int) -> None:
    d.mkdir(parents=True, exist_ok=True)
    for n, text in files.items():
        (d / n).write_text(text)
    (d / "mips_tb.v").write_text(TB_TEMPLATE.replace("parameter CYCLES = 120;",
                                                     f"parameter CYCLES = {cycles};"))
    (d / "mips_zero.mem").write_text("\n".join(["0" * 16] * PROG_DEPTH) + "\n")
    write_prog([NOP], d / "mips_prog.mem")


def prepare_mips16(
    up: Path, out: Path, *, magic_words: list[int] | None = None, kinds: list[str] | None = None,
    cycles: int = WITNESS_CYCLES, force_inactive: bool = False,
) -> list[str]:
    """Writes the variant (clean when `magic_words` is None, else infected) into `out` and
    `out/iv`; returns the design file list."""
    files = _variant(load_upstream(up))
    if magic_words is not None:
        files = insert_mips16(files, magic_words, kinds or [], force_inactive=force_inactive)
    _write_dir(out, files, cycles)
    _write_dir(out / "iv", files, cycles)
    return list(DESIGN_FILES)


def write_program(out: Path, words: list[int]) -> None:
    write_prog(words, out / "mips_prog.mem")
    write_prog(words, out / "iv" / "mips_prog.mem")


def _run(cmd: list[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          check=False)


def _data_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln[:1].isdigit()]


def run_once(out: Path, files: list[str], odin3_bin: Path, cycles: int, tag: str) -> dict[str, str]:
    """iverilog, Odin III RTL sim and Odin III netlist sim of mips_tb; trace texts by engine."""
    for d in (out, out / "iv"):
        tb = d / "mips_tb.v"
        tb.write_text(re.sub(r"parameter CYCLES = \d+", f"parameter CYCLES = {cycles}",
                             tb.read_text()))
    iv = _run(["iverilog", "-g2005", "-o", f"../{tag}.vvp", "mips_tb.v", *files], cwd=out / "iv")
    if iv.returncode != 0:
        raise RuntimeError(f"iverilog failed: {iv.stderr}")
    run = _run(["vvp", f"../{tag}.vvp"], cwd=out / "iv")
    (out / f"{tag}.ref.txt").write_text("\n".join(_data_lines(run.stdout)))
    fl = " ".join(files)
    rtl = _run([str(odin3_bin), "--top", TOP, "-p",
                f"read_verilog {fl}; proc; opt; lower; sim_tb --out {tag}.rtl.txt mips_tb.v"],
               cwd=out)
    if rtl.returncode != 0:
        raise RuntimeError(f"odin3 rtl sim_tb failed: {rtl.stdout}\n{rtl.stderr}")
    nl = _run([str(odin3_bin), "--top", TOP, "-p",
               f"read_verilog {fl}; proc; opt; lower; write_blif {tag}.nl.blif"], cwd=out)
    if nl.returncode != 0:
        raise RuntimeError(f"odin3 write_blif failed: {nl.stdout}\n{nl.stderr}")
    nl2 = _run([str(odin3_bin), "--top", TOP, "-p",
                f"read_blif {tag}.nl.blif; sim_tb --out {tag}.nl.txt mips_tb.v"], cwd=out)
    if nl2.returncode != 0:
        raise RuntimeError(f"odin3 netlist sim_tb failed: {nl2.stdout}\n{nl2.stderr}")
    return {e: (out / f"{tag}.{e}.txt").read_text() for e in ("ref", "rtl", "nl")}
