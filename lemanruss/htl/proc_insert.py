"""HDL-level processor-Trojan insertion (round 7, Seeker-Proc pilot; spec section 12).

Both bases run under Odin III sim_tb, RTL and netlist equal to iverilog (brief). Insertion is a
line-based text splice, the same style as `lemanruss.htl.insert_hdl` (section 3 "HDL level"):
rewire one existing net's single consumer (or producer) through a new wire, and declare the new
trigger/payload logic once before `endmodule`. Both patch points below were found by reading the
core RTL (not guessed): `single_cycle_core.v`'s `fetch_issue` instance (`next_PC_select`, itself
documented in `fetch_issue.v` as "2'b01: Stall (PC = PC)"), a DoS-stall payload (`p-dos-stuck` on
the single-cycle core's own stall encoding); and `darkriscv.v`'s own synchronous self-reset
register `XRES` (`always @(posedge CLK) XRES <= RES;`), a DoS-reset payload (`p-dos-reset`).

`darkriscv` needed `p-dos-reset`, not `p-dos-stuck` on its own `HLT` (pipeline-stall) wire: a
first attempt OR'd the trigger into `HLT` the same way as the mcu stall, but `HLT` only holds off
the *next* instruction fetch -- by the time the magic word's own fetch is acknowledged
(`IDACK`), the following instruction is already in flight in this pipelined core, so the
instruction after the magic word still completed (measured: a witness SW one slot after the
magic word still wrote its value). Forcing the core's own reset register is not sensitive to
pipeline depth (round-7 agent default, docs/results-round7.md).

Trigger: a comparator on the fetched instruction word (`instruction` in single_cycle_core.v;
darkriscv.v rc1 (2026-11-04) samples `XIDATA`, the execute-stage latched instruction register --
see the module docstring note below for why not the raw `IDATA`/`IDACK` fetch bus).
`len(magic_words) == 1` is the magic-word trigger (plain comparator); `len(magic_words) > 1` is
the magic-sequence trigger (spec "t-seq-pattern": a small FSM that advances on each word in
order, resets to 1 if the first word reappears out of sequence, and fires -- combinationally, not
sticky -- on the cycle the last word of the sequence is seen).

darkriscv rc1 note (Peter 2026-11-04, "move the trigger off IDATA/IDACK to another net, comment
the behavior in the rtl"): round 10 found the single/multi-Trojan smoke on darkriscv was not
silent on a witness carrying neither magic word -- the infected trace went to `x` partway through
a run while the clean trace stayed defined (docs/results-round10.md section 4). The construction
sampled `IDATA` gated by `IDACK` directly off the fetch bus; `IDATA`/`IDACK` can themselves read
`x` during the core's idle bubble (no fetch in flight), and `x && (...)` or `0 || x` does not
reduce to a clean 0/1 the way `0 && (...)`/`0 || 0` does, so an `x` on the bus could reach the
comparator and, through the OR into the self-reset register, pollute `XRES`. Not root-caused
further (brief: do not root-cause it) -- instead the comparator now reads `XIDATA`
(`darkriscv.v`'s own eXecute-stage instruction register, `reg [31:0] XIDATA` under `` `__3STAGE__
``, the config's default): it updates only on a cycle whose fetch was acknowledged (`XIDATA <=
HLT ? XIDATA : IDATAX`, and `HLT` is high exactly while a fetch is still unacknowledged) and holds
its last value otherwise, so it is only ever assigned from a fetch that was actually acked and
never samples the bus while idle. This matches the brief's default: "a core-internal latched
instruction register is the first choice" for the IR trigger. No `valid_wire` gate is needed (the
register's own freeze-on-stall behavior already does that job), so the darkriscv comparator is
now the same shape as mcu's (plain, ungated).

Payload: DoS only this round (`p-dos-stuck` on mcu, `p-dos-reset` on darkriscv -- logged as an
agent default in docs/results-round7.md). Error-insertion (`p-err-hi`/`p-err-lo` on register
write-back or data-bus write) and netlist-level insertion are out of this pilot's scope: recorded
as a deferred axis, not attempted and silently skipped.
"""

from __future__ import annotations

MCU_FI_CONNECTION = "  .next_PC_select(next_PC_select),"
MCU_FI_CONNECTION_PATCHED = "  .next_PC_select(__htl_pc_mux),"

DARK_XRES_LINE = "        XRES <= RES;"
DARK_XRES_LINE_PATCHED = "        XRES <= RES || __htl_trigger;"

# rc1 (2026-11-04), module docstring's darkriscv rc1 note: sample the execute-stage latched
# instruction, not the raw fetch bus -- the fetch bus may read x in the idle bubble before an
# acknowledgement; this register only updates on an acknowledged fetch and holds its value
# otherwise.
DARK_TRIGGER_COMMENT = (
    "  // sample the execute-stage latched instruction (XIDATA), not the raw fetch bus: the\n"
    "  // fetch bus may read x in the idle bubble before an acknowledgement arrives; XIDATA\n"
    "  // only updates on a cycle whose fetch was acknowledged and holds its value otherwise.\n"
)


class PatchNotFound(ValueError):
    """The exact text this module edits was not found (upstream source changed under us)."""


def _state_bits(k: int) -> int:
    n = 1
    while (1 << n) < (k + 1):
        n += 1
    return n


def _trigger_decl(
    magic_words: list[int],
    sample_wire: str,
    valid_wire: str | None,
    clock_wire: str,
    *,
    seq_advance_wire: str | None = None,
    force_inactive: bool = False,
) -> str:
    """`sample_wire`: the 32-bit instruction wire; `valid_wire`: None (always valid -- mcu, and
    darkriscv rc1 onward: `XIDATA` is already a latched register that only updates on an
    acknowledged fetch, so it needs no external qualifier) or an AND-qualifier.
    `clock_wire`: the core's own clock net name (`clock` on mcu, `CLK` on darkriscv -- found by
    reading each RTL file, not assumed to be the same name). `seq_advance_wire`: the magic-
    sequence FSM's own advance-enable expression, when it differs from `valid_wire` (mcu's
    `!flush_fetch_receive`, darkriscv's `!HLT` -- both None-`valid_wire` bases, so both must pass
    this explicitly; see below).
    `force_inactive` (spec section 4.3, equivalence check): ties the trigger's enable wire to 0,
    keeping the rest of the payload wiring (the mux / OR term) in place -- the equivalence check
    needs the infected design with the trigger permanently off, not the clean design back.

    The magic-sequence FSM must only advance on a genuinely new fetched word. A first attempt
    gated on "`instruction` changed since last cycle" (any `valid_wire`-less base); measured
    (iverilog, `$monitor` on a live witness run) that mcu's `fetch_receive.v` inserts a one-cycle
    NOP bubble between every two real fetches (`assign instruction = flush ? NOP : i_mem_data`),
    which the core's own `flush_fetch_receive` wire marks and a mcu witness picks up as "this
    core holds the previous instruction, then a NOP, on alternating cycles" -- a plain
    change-detect FSM read the bubble's NOP as "the wrong next word" and reset the sequence
    before the real next word ever arrived (measured: a 3-word sequence never fired). mcu's own
    `flush_fetch_receive` (negated: a bubble is *not* a new fetch) is the correct advance signal,
    passed in by the caller as `seq_advance_wire` (round 7 agent default: found by instrumenting
    a live run, not derivable from the port list alone).
    """
    if not magic_words:
        raise ValueError("magic_words must hold at least one 32-bit value")
    if force_inactive:
        return "  wire __htl_trigger = 1'b0;\n"
    gate = f"{valid_wire} && " if valid_wire else ""
    if len(magic_words) == 1:
        return f"  wire __htl_trigger = {gate}({sample_wire} == 32'h{magic_words[0]:08x});\n"
    bits = _state_bits(len(magic_words))
    k = len(magic_words)
    words_decl = "\n".join(
        f"  localparam [31:0] __htl_seq_{i} = 32'h{w:08x};" for i, w in enumerate(magic_words)
    )
    cmp_cases = "\n".join(
        f"      {i}: __htl_seq_state <= ({sample_wire} == __htl_seq_{i}) ? {i + 1} "
        f"                              : (({sample_wire} == __htl_seq_0) ? 1 : 0);"
        for i in range(k)
    )
    advance_en = seq_advance_wire or valid_wire
    if advance_en is None:
        raise ValueError("_trigger_decl: a magic sequence needs seq_advance_wire or valid_wire")
    return (
        f"{words_decl}\n"
        f"  reg [{bits - 1}:0] __htl_seq_state = 0;\n"
        f"  always @(posedge {clock_wire}) begin\n"
        f"    if ({advance_en}) case (__htl_seq_state)\n"
        f"{cmp_cases}\n"
        f"      default: __htl_seq_state <= ({sample_wire} == __htl_seq_0) ? 1 : 0;\n"
        "    endcase\n"
        "  end\n"
        f"  wire __htl_trigger = {gate}(__htl_seq_state == {k - 1}) "
        f"&& ({sample_wire} == __htl_seq_{k - 1});\n"
    )


def _independent_triggers_decl(
    magic_words: list[int], sample_wire: str, valid_wire: str | None, *,
    force_inactive: bool = False,
) -> tuple[str, list[str]]:
    """rc1 (2026-11-03): 1 to 3 *independent* magic-word Trojans sharing one circuit (Peter
    2026-11-03: "1 to 3 payllods per core"). Each word gets its own comparator wire
    `__htl_trigger_<j>` (its own witness: the input sequence that fetches only that word), OR'd
    into the combined `__htl_trigger` the payload mux already reads -- no added flip-flop (the
    comparators and the OR are purely combinational), and each Trojan's own firing is checked
    independently by replaying that Trojan's own witness and reading `__htl_trigger_<j>` (or, on
    the finished netlist, the payload's own effect) with the other words' comparators silent
    (true for any witness that fetches a single legal instruction word at a time, as every
    witness program here does). Order of `magic_words` is not meaningful (unlike
    `_trigger_decl`'s magic-sequence case): these are independent triggers, not a sequence.
    `force_inactive` ties every `__htl_trigger_<j>` to 0 (equivalence check, section 4.3 of the
    HTL design spec: the infected design with every trigger permanently off, not the clean
    design back)."""
    if not magic_words:
        raise ValueError("magic_words must hold at least one 32-bit value")
    if len(magic_words) != len(set(magic_words)):
        raise ValueError("magic_words must be pairwise distinct (one Trojan key each)")
    names = [f"__htl_trigger_{i}" for i in range(len(magic_words))]
    if force_inactive:
        lines = [f"  wire {n} = 1'b0;" for n in names]
    else:
        gate = f"{valid_wire} && " if valid_wire else ""
        lines = [
            f"  wire {n} = {gate}({sample_wire} == 32'h{w:08x});"
            for n, w in zip(names, magic_words, strict=True)
        ]
    combined = " | ".join(names)
    lines.append(f"  wire __htl_trigger = {combined};")
    return "\n".join(lines) + "\n", names


def insert_mcu_multitrojan(
    source: str, magic_words: list[int], *, force_inactive: bool = False
) -> tuple[str, list[str]]:
    """rc1: 1 to 3 independent magic-word Trojans on mcu, same payload point as
    `insert_mcu_trojan` (`p-dos-stuck` on `next_PC_select`; a second payload kind per core is an
    open question, section 7 of the rc1 spec, not added this round). Returns the patched source
    and the per-Trojan trigger wire names (`__htl_trigger_0`..), for a build script to probe or
    force individually when proving each Trojan's own witness."""
    if MCU_FI_CONNECTION not in source:
        raise PatchNotFound(f"{MCU_FI_CONNECTION!r} not found in single_cycle_core.v")
    if source.count(MCU_FI_CONNECTION) != 1:
        raise PatchNotFound("next_PC_select connection is not unique")
    patched = source.replace(MCU_FI_CONNECTION, MCU_FI_CONNECTION_PATCHED)
    decl, names = _independent_triggers_decl(
        magic_words, "instruction", valid_wire=None, force_inactive=force_inactive)
    decl += "  wire [1:0] __htl_pc_mux = __htl_trigger ? 2'b01 : next_PC_select;\n"
    idx = patched.rindex("endmodule")
    return patched[:idx] + decl + patched[idx:], names


def insert_dark_multitrojan(
    source: str, magic_words: list[int], *, force_inactive: bool = False
) -> tuple[str, list[str]]:
    """rc1: 1 to 3 independent magic-word Trojans on darkriscv, same payload point as
    `insert_dark_trojan` (`p-dos-reset` ORed into `XRES`; a second payload kind per core is an
    open question, section 7 of the rc1 spec, not added this round). rc1 (2026-11-04): each
    comparator samples `XIDATA`, not `IDATA`/`IDACK` -- see the module docstring's darkriscv rc1
    note."""
    if DARK_XRES_LINE not in source:
        raise PatchNotFound(f"{DARK_XRES_LINE!r} not found in darkriscv.v")
    if source.count(DARK_XRES_LINE) != 1:
        raise PatchNotFound("XRES reset line is not unique")
    patched = source.replace(DARK_XRES_LINE, DARK_XRES_LINE_PATCHED)
    decl, names = _independent_triggers_decl(
        magic_words, "XIDATA", valid_wire=None, force_inactive=force_inactive)
    decl = DARK_TRIGGER_COMMENT + decl
    idx = patched.rindex("endmodule")
    return patched[:idx] + decl + patched[idx:], names


def insert_mcu_trojan(
    source: str, magic_words: list[int], *, force_inactive: bool = False
) -> str:
    """Patches `single_cycle_core.v`: trigger on `instruction`, payload forces `next_PC_select`
    into fetch_issue's own stall encoding (2'b01) via a new mux wire `__htl_pc_mux`."""
    if MCU_FI_CONNECTION not in source:
        raise PatchNotFound(f"{MCU_FI_CONNECTION!r} not found in single_cycle_core.v")
    if source.count(MCU_FI_CONNECTION) != 1:
        raise PatchNotFound("next_PC_select connection is not unique")
    patched = source.replace(MCU_FI_CONNECTION, MCU_FI_CONNECTION_PATCHED)
    decl = _trigger_decl(
        magic_words, "instruction", valid_wire=None, clock_wire="clock",
        seq_advance_wire="!flush_fetch_receive", force_inactive=force_inactive,
    )
    decl += "  wire [1:0] __htl_pc_mux = __htl_trigger ? 2'b01 : next_PC_select;\n"
    idx = patched.rindex("endmodule")
    return patched[:idx] + decl + patched[idx:]


def insert_dark_trojan(
    source: str, magic_words: list[int], *, force_inactive: bool = False
) -> str:
    """Patches `darkriscv.v`: trigger on `XIDATA` (the execute-stage latched instruction
    register; rc1 2026-11-04, see module docstring's darkriscv rc1 note for why not the raw
    `IDATA`/`IDACK` fetch bus), payload ORs into the core's own synchronous self-reset register
    `XRES` (p-dos-reset; see module docstring for why not `HLT`/p-dos-stuck)."""
    if DARK_XRES_LINE not in source:
        raise PatchNotFound(f"{DARK_XRES_LINE!r} not found in darkriscv.v")
    if source.count(DARK_XRES_LINE) != 1:
        raise PatchNotFound("XRES reset line is not unique")
    patched = source.replace(DARK_XRES_LINE, DARK_XRES_LINE_PATCHED)
    decl = _trigger_decl(
        magic_words, "XIDATA", valid_wire=None, clock_wire="CLK",
        seq_advance_wire="!HLT", force_inactive=force_inactive,
    )
    decl = DARK_TRIGGER_COMMENT + decl
    idx = patched.rindex("endmodule")
    return patched[:idx] + decl + patched[idx:]


# --- rc1 (2026-11-04), Peter's continuation-3 decisions: "1a with a secret program that
# activates trojans (right?)"; "2 that's fine, but why not a trojan that messes up the lsb of an
# alu operation (maybe shift right) or rotate" -- RV32I has no rotate instruction (checked: the
# base integer set has no ROR/ROL/RORI opcode; the brief's "check, state it" answer is "no rotate
# in RV32I", so only the shift-right LSB-flip variant is built). Each Trojan now carries its own
# PAYLOAD KIND, independent of the others in the same circuit (brief Continuation 3 step 2:
# "kinds drawn per Trojan"): "reset" (the existing p-dos-reset mechanism), "stall" (the existing
# p-dos-stuck mechanism), "alu" (new: flip bit 0 of a shift-right result -- SRL/SRA/SRLI/SRAI --
# while triggered, on the core's own ALU result wire, found by reading each core's ALU/writeback
# path, not guessed).
PAYLOAD_KINDS = ("reset", "stall", "alu")

# mcu: the EX (execution_unit) instance connection carrying the raw ALU result into
# single_cycle_core.v, found by reading single_cycle_core.v (the `.ALU_result(ALU_result)` line
# is not unique in the file -- WB (writeback_unit) reads the same wire by the same port name a
# few lines later -- so the anchor is the 3-line block around the EX instance's own output ports,
# which is unique).
MCU_ALU_ANCHOR = "  .branch(branch),\n  .ALU_result(ALU_result),\n  .JALR_target(JALR_target),"
MCU_ALU_ANCHOR_PATCHED = (
    "  .branch(branch),\n  .ALU_result(__htl_alu_raw),\n  .JALR_target(JALR_target),"
)

# darkriscv: RMDATA is the combinational ALU result wire (`always`-free `assign`-style wire
# declaration higher up in the file); its one write-back use is this line (unique, checked).
DARK_RMDATA_LINE = "                  MCC||RCC ? RMDATA:"
DARK_RMDATA_LINE_PATCHED = "                  MCC||RCC ? __htl_rmdata:"

# darkriscv stall payload: HLT is a combinational `wire HLT = ...;` (multi-line, `||`-chained);
# OR'ing a trigger into its own *definition* (not into the trigger-sampling net, which round 10's
# darkriscv rc1 note already rejected for IDATA/IDACK reasons unrelated to this payload target)
# forces the pipeline's own stall condition permanently true while triggered -- a genuine stall,
# distinct from darkriscv's existing reset payload on XRES.
DARK_HLT_LINE = "    wire HLT =\n"
DARK_HLT_LINE_PATCHED = "    wire HLT =\n                __htl_trigger_stall ||\n"

DARK_XRES_LINE_KINDED_PATCHED = "        XRES <= RES || __htl_trigger_reset;"

# picorv32 (external/picorv32, YosysHQ, ISC license; default parameters: no ENABLE_MUL/
# ENABLE_DIV/ENABLE_IRQ -- Q-L12's finding on the multiplier/divide submodules is unaffected by
# this round's additions, which touch none of them). Trigger: `next_insn_opcode`, a register that
# updates only on a completed memory transfer (`if (mem_xfer) next_insn_opcode <= ...;`) and holds
# its value otherwise -- the brief's "always defined after reset" requirement, same intent as
# darkriscv's XIDATA.
PICO_TRIGGER_SAMPLE = "next_insn_opcode"
PICO_CLOCK = "clk"

# Reset payload: the FSM's own `if (!resetn) begin ... end else case (cpu_state) ...` branch
# (single `always @(posedge clk)` block controlling reg_pc/reg_next_pc/cpu_state and friends).
# This exact `!resetn` line is not unique on its own (several unrelated always blocks each reset
# their own registers the same way); the 4-line anchor ending in it is unique.
PICO_RESET_ANCHOR = "\t\tif (!ENABLE_TRACE)\n\t\t\ttrace_data <= 'bx;\n\n\t\tif (!resetn) begin\n"
PICO_RESET_ANCHOR_PATCHED = (
    "\t\tif (!ENABLE_TRACE)\n\t\t\ttrace_data <= 'bx;\n\n"
    "\t\tif (!resetn || __htl_trigger_reset) begin\n"
)

# Stall payload: `decoder_trigger` only ever becomes 1 after a completed instruction fetch
# (`decoder_trigger <= mem_do_rinst && mem_done;`); forcing it to 0 while triggered means the
# decode stage never launches another instruction -- the core holds its current architectural
# state forever, a stall rather than a restart (unlike the reset payload above).
PICO_STALL_LINE = "\t\tdecoder_trigger <= mem_do_rinst && mem_done;"
PICO_STALL_LINE_PATCHED = "\t\tdecoder_trigger <= !__htl_trigger_stall && mem_do_rinst && mem_done;"

# ALU payload: `cpu_state_shift`'s own completion branch (`reg_sh == 0`) writes the finished
# shift result to `reg_out` (this single line is unique: every other `reg_out <=` assignment in
# the file sets it from a different source). `instr_srli`/`instr_srl`/`instr_srai`/`instr_sra`
# are the module's own per-opcode decode flags (declared near the top of the file), so no new
# decode logic is needed to tell a shift-right apart from a shift-left here.
PICO_ALU_LINE = "\t\t\t\t\treg_out <= reg_op1;\n"
PICO_ALU_LINE_PATCHED = (
    "\t\t\t\t\treg_out <= (__htl_trigger_alu && (instr_srli || instr_srl "
    "|| instr_srai || instr_sra))\n"
    "\t\t\t\t\t\t? {reg_op1[31:1], ~reg_op1[0]} : reg_op1;\n"
)


def _kinded_triggers_decl(
    magic_words: list[int], kinds: list[str], sample_wire: str, valid_wire: str | None, *,
    force_inactive: bool = False, reset_active: str | None = None,
) -> tuple[str, list[str]]:
    """Like `_independent_triggers_decl`, plus three combined wires (`__htl_trigger_reset`,
    `__htl_trigger_stall`, `__htl_trigger_alu`), each the OR of the per-Trojan trigger wires whose
    own `kinds[i]` matches (brief Continuation 3 step 2: "kinds drawn per Trojan"); a kind with no
    Trojan this circuit is wired to `1'b0`, so every payload site can always read its own combined
    wire without a Python-side conditional."""
    if len(magic_words) != len(kinds):
        raise ValueError("one kind per magic word")
    bad = [k for k in kinds if k not in PAYLOAD_KINDS]
    if bad:
        raise ValueError(f"kind must be one of {PAYLOAD_KINDS}, got {bad}")
    decl, names = _independent_triggers_decl(
        magic_words, sample_wire, valid_wire, force_inactive=force_inactive)
    lines = [decl.rstrip("\n")]
    for kind in PAYLOAD_KINDS:
        matched = [n for n, k in zip(names, kinds, strict=True) if k == kind]
        expr = " | ".join(matched) if matched else "1'b0"
        if matched and reset_active:
            # v2.0 masking rule: no payload acts while the core's own reset is active, so the
            # host's hold logic sees its original signals and its registers load known values
            # (a trigger that reads a no-reset register would otherwise put x into a hold path)
            expr = f"({expr}) & ~({reset_active})"
        lines.append(f"  wire __htl_trigger_{kind} = {expr};")
    return "\n".join(lines) + "\n", names


def insert_mcu_kinded_multitrojan(
    source: str, magic_words: list[int], kinds: list[str], *, force_inactive: bool = False
) -> tuple[str, list[str]]:
    """rc1 Continuation 3: 1-3 independent Trojans on mcu, each its own payload kind (reset/
    stall/alu). Reset reuses the existing `__htl_pc_mux` payload point with a second encoding
    (`2'b11`, `fetch_issue.v`'s own case default: `PC_reg <= {ADDRESS_BITS{1'b0}}`, a jump to
    address 0 -- a genuine restart, distinct from the existing stall encoding `2'b01`); alu is new
    (`MCU_ALU_ANCHOR`, the EX instance's `ALU_result` port)."""
    for anchor in (MCU_FI_CONNECTION, MCU_ALU_ANCHOR):
        if anchor not in source or source.count(anchor) != 1:
            raise PatchNotFound(f"{anchor!r} not found (or not unique) in single_cycle_core.v")
    patched = source.replace(MCU_FI_CONNECTION, MCU_FI_CONNECTION_PATCHED)
    patched = patched.replace(MCU_ALU_ANCHOR, MCU_ALU_ANCHOR_PATCHED)
    decl, names = _kinded_triggers_decl(
        magic_words, kinds, "instruction", None, force_inactive=force_inactive,
        reset_active="reset")
    decl += (
        "  wire [1:0] __htl_pc_mux = __htl_trigger_stall ? 2'b01 :\n"
        "                            __htl_trigger_reset ? 2'b11 : next_PC_select;\n"
        "  wire [31:0] __htl_alu_raw;\n"
        "  assign ALU_result = (__htl_trigger_alu && "
        "(ALU_operation==6'd12 || ALU_operation==6'd13))\n"
        "                       ? {__htl_alu_raw[31:1], ~__htl_alu_raw[0]} : __htl_alu_raw;\n"
    )
    idx = patched.rindex("endmodule")
    return patched[:idx] + decl + patched[idx:], names


def insert_dark_kinded_multitrojan(
    source: str, magic_words: list[int], kinds: list[str], *, force_inactive: bool = False
) -> tuple[str, list[str]]:
    """rc1 Continuation 3: 1-3 independent Trojans on darkriscv, each its own payload kind. Reset
    reuses the existing XRES payload point; stall is new (`DARK_HLT_LINE`, the pipeline's own
    stall condition, not the comparator sampling net round 10 moved off of `IDATA`/`IDACK`); alu
    is new (`DARK_RMDATA_LINE`, the ALU's write-back use of its own `RMDATA` wire)."""
    for anchor in (DARK_XRES_LINE, DARK_HLT_LINE, DARK_RMDATA_LINE):
        if anchor not in source or source.count(anchor) != 1:
            raise PatchNotFound(f"{anchor!r} not found (or not unique) in darkriscv.v")
    patched = source.replace(DARK_XRES_LINE, DARK_XRES_LINE_KINDED_PATCHED)
    patched = patched.replace(DARK_HLT_LINE, DARK_HLT_LINE_PATCHED)
    patched = patched.replace(DARK_RMDATA_LINE, DARK_RMDATA_LINE_PATCHED)
    decl, names = _kinded_triggers_decl(
        magic_words, kinds, "XIDATA", None, force_inactive=force_inactive,
        reset_active="RES || XRES")
    decl = (
        DARK_TRIGGER_COMMENT + decl
        + "  wire [31:0] __htl_rmdata = (__htl_trigger_alu && (FCT3==3'd5))\n"
        "                       ? {RMDATA[31:1], ~RMDATA[0]} : RMDATA;\n"
    )
    idx = patched.rindex("endmodule")
    return patched[:idx] + decl + patched[idx:], names


def insert_picorv32_kinded_multitrojan(
    source: str, magic_words: list[int], kinds: list[str], *, force_inactive: bool = False
) -> tuple[str, list[str]]:
    """rc1 Continuation 3 (controller addition, 2026-11-04, "Why can't we use picorv32?"): 1-3
    independent Trojans on picorv32 (external/picorv32, default params: no ENABLE_MUL/DIV/IRQ),
    each its own payload kind, found by reading `picorv32.v`'s single-cycle-state-machine core
    (not guessed): trigger on `next_insn_opcode` (the latched fetched-instruction register); reset
    re-enters the FSM's own `!resetn` branch (`PICO_RESET_ANCHOR`); stall gates `decoder_trigger`
    so the decode stage never launches another instruction (`PICO_STALL_LINE`); alu flips bit 0 of
    a completed SRL/SRA/SRLI/SRAI result at `cpu_state_shift`'s own write-back line
    (`PICO_ALU_LINE`)."""
    for anchor in (PICO_RESET_ANCHOR, PICO_STALL_LINE, PICO_ALU_LINE):
        if anchor not in source or source.count(anchor) != 1:
            raise PatchNotFound(f"{anchor!r} not found (or not unique) in picorv32.v")
    patched = source.replace(PICO_RESET_ANCHOR, PICO_RESET_ANCHOR_PATCHED)
    patched = patched.replace(PICO_STALL_LINE, PICO_STALL_LINE_PATCHED)
    patched = patched.replace(PICO_ALU_LINE, PICO_ALU_LINE_PATCHED)
    decl, names = _kinded_triggers_decl(
        magic_words, kinds, PICO_TRIGGER_SAMPLE, None, force_inactive=force_inactive,
        reset_active="!resetn")
    # picorv32.v holds several modules (picorv32, picorv32_regs, picorv32_pcpi_mul, ...,
    # picorv32_axi, picorv32_wb); `str.rindex("endmodule")` (every other inserter in this file
    # uses it, safe there -- their upstream files hold exactly one module) would land the new
    # declarations in whichever module happens to close last in the file, not in `picorv32`
    # itself. Verilog modules do not nest, so the first `endmodule` after `picorv32`'s own
    # `module` line is always its own.
    mod_start = patched.index("module picorv32 #(")
    idx = patched.index("endmodule", mod_start)
    return patched[:idx] + decl + patched[idx:], names
