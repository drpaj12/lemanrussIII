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
