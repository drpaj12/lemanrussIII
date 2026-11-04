"""HDL-level Trojan insertion (spec docs/specs/2026-10-31-htl-design.md section 3).

A line-based Verilog text splice: insert a trigger wire's `assign` before `endmodule`, and rewrite
one victim's existing `assign` statement to pass through a mux. The caller re-runs
`read_verilog --parse-only` on the result (lemanruss.htl.odin_check) as the brief's parse check;
this module does not import odin3 itself, so its own unit tests run without ODIN3_LIB/PYTHONPATH.

Round 1 scope (CombRareTrigger, DosStuck/ErrHi/ErrLo) stays on a victim that is a plain
continuous `assign` target (one line, no concatenation on the lhs); a victim driven by an
`always` block is out of scope (recorded, not hidden): HDL rewrite would need to touch the
process body, not just one line.

Round 2 adds AlwaysOnTrigger, InputPatternTrigger, SeqCounterTrigger, and the DosReset/Energy/
Slowdown payloads. These lean on real Verilog arithmetic (registers, `+`, `~`) rather than a
gate-by-gate build, so the HDL inserter is simpler here than lemanruss.htl.insert_netlist's
equivalents; SeqPatternTrigger (the FSM-sequence trigger) is modelled in lemanruss.htl.triggers
but not wired into either inserter yet (next step).
"""

from __future__ import annotations

import re

from lemanruss.htl.payloads import (
    DosResetPayload,
    DosStuckPayload,
    EnergyPayload,
    ErrHiPayload,
    ErrLoPayload,
    SlowdownPayload,
)
from lemanruss.htl.triggers import (
    CombRareTrigger,
    InputPatternTrigger,
    SeqCounterTrigger,
)

TRIGGER_WIRE = "__htl_trigger"

_ENDMODULE = re.compile(r"\bendmodule\b")
_ASSIGN = re.compile(r"assign\s+(\w+)\s*=\s*(.*?);", re.DOTALL)


def _insert_before_endmodule(source: str, text: str) -> str:
    match = _ENDMODULE.search(source)
    if match is None:
        raise ValueError("insert_hdl: no endmodule found")
    return source[: match.start()] + text + source[match.start() :]


class NoAssignDriver(ValueError):
    """Raised when the victim is not the target of a plain `assign victim = expr;` statement."""


def insert_comb_rare_trigger(
    source: str, trigger: CombRareTrigger, trigger_wire: str = TRIGGER_WIRE
) -> str:
    """Declares `trigger_wire` as the AND of the trigger's rare-valued nets, before `endmodule`."""
    if not trigger.nets:
        raise ValueError("insert_comb_rare_trigger: trigger.nets is empty (bind it first)")
    terms = [f"({name} == {value})" for name, value in trigger.nets]
    decl = f"    wire {trigger_wire} = " + " && ".join(terms) + ";\n"
    match = _ENDMODULE.search(source)
    if match is None:
        raise ValueError("insert_comb_rare_trigger: no endmodule found")
    return source[: match.start()] + decl + source[match.start() :]


def _find_assign(source: str, victim: str) -> re.Match[str]:
    for match in _ASSIGN.finditer(source):
        line_start = source.rfind("\n", 0, match.start()) + 1
        if "//" in source[line_start : match.start()]:
            continue  # the assign sits in a line comment
        if match.group(1) == victim:
            return match
    raise NoAssignDriver(f"{victim}: no plain 'assign {victim} = ...;' statement found")


def insert_dos_stuck_payload(
    source: str, payload: DosStuckPayload, trigger_wire: str = TRIGGER_WIRE
) -> str:
    """Rewrites `assign victim = expr;` to force `stuck_value` when `trigger_wire` is 1."""
    match = _find_assign(source, payload.victim)
    expr = match.group(2)
    new_assign = (
        f"assign {payload.victim} = {trigger_wire} ? {payload.stuck_value} : ({expr});"
    )
    return source[: match.start()] + new_assign + source[match.end() :]


def insert_err_bit_payload(
    source: str,
    payload: ErrHiPayload | ErrLoPayload,
    width: int,
    trigger_wire: str = TRIGGER_WIRE,
) -> str:
    """Rewrites `assign word = expr;` to flip (XOR), or force to 1 (OR), the top (`ErrHiPayload`)
    or bottom (`ErrLoPayload`) `bits` bits of a `width`-bit `word` when `trigger_wire` is 1.
    `payload.word` must name the assign's lhs exactly; `width` is the word's declared width (not
    derived from the HDL here -- the caller already knows it from the module's port list)."""
    match = _find_assign(source, payload.word)
    expr = match.group(2)
    is_hi = isinstance(payload, ErrHiPayload)
    mask = ((1 << payload.bits) - 1) << (width - payload.bits) if is_hi else (1 << payload.bits) - 1
    op = "|" if payload.force else "^"
    patched = f"({expr}) {op} ({trigger_wire} ? {width}'d{mask} : {width}'d0)"
    new_assign = f"assign {payload.word} = {patched};"
    return source[: match.start()] + new_assign + source[match.end() :]


def insert_always_on_trigger(source: str, trigger_wire: str = TRIGGER_WIRE) -> str:
    """Declares `trigger_wire` tied to 1'b1 (round 2: AlwaysOnTrigger; spec section 2, only legal
    with a payload that needs no activation condition -- see lemanruss.htl.trojan.compose)."""
    return _insert_before_endmodule(source, f"    wire {trigger_wire} = 1'b1;\n")


def insert_input_pattern_trigger(
    source: str, trigger: InputPatternTrigger, trigger_wire: str = TRIGGER_WIRE
) -> str:
    """Declares `trigger_wire` as 1 exactly when `{trigger.bits}` concatenated reads
    `trigger.magic_value` (round 2: InputPatternTrigger)."""
    if not trigger.bits:
        raise ValueError("insert_input_pattern_trigger: trigger.bits is empty (bind it first)")
    width = len(trigger.bits)
    concat = "{" + ", ".join(trigger.bits) + "}"
    decl = f"    wire {trigger_wire} = ({concat} == {width}'d{trigger.magic_value});\n"
    return _insert_before_endmodule(source, decl)


def insert_seq_counter_trigger(
    source: str,
    trigger: SeqCounterTrigger,
    clock: str,
    trigger_wire: str = TRIGGER_WIRE,
) -> str:
    """Declares a time-bomb trigger: a free-running counter that increments on every cycle the
    condition (an AND of `trigger.nets` at their rare polarity) holds, and sticks `trigger_wire`
    at 1 once the counter reaches `trigger.n` (round 2: SeqCounterTrigger). Verilog arithmetic
    makes this far simpler at the HDL level than the netlist level's gate-by-gate counter (see
    insert_netlist.insert_seq_counter_trigger for that)."""
    if not trigger.nets:
        raise ValueError("insert_seq_counter_trigger: trigger.nets is empty (bind it first)")
    width = max(1, trigger.n.bit_length())
    cond_terms = [f"({name} == {value})" for name, value in trigger.nets]
    cond_wire = f"{trigger_wire}_cond"
    counter_reg = f"{trigger_wire}_counter"
    decl = (
        f"    wire {cond_wire} = " + " && ".join(cond_terms) + ";\n"
        f"    reg [{width - 1}:0] {counter_reg};\n"
        f"    reg {trigger_wire};\n"
        f"    always @(posedge {clock}) begin\n"
        f"        if ({cond_wire} && !{trigger_wire}) {counter_reg} <= {counter_reg} + 1'b1;\n"
        f"        if ({counter_reg} >= {width}'d{trigger.n}) {trigger_wire} <= 1'b1;\n"
        f"    end\n"
    )
    return _insert_before_endmodule(source, decl)


def insert_dos_reset_payload(
    source: str, payload: DosResetPayload, trigger_wire: str = TRIGGER_WIRE
) -> str:
    """Forces `payload.reset_net` active (1) when `trigger_wire` is 1 (round 2:
    DosResetPayload; `payload.reset_net` must be a plain `assign`-driven net, same scope as
    insert_dos_stuck_payload -- the common case, a top-level `reset`/`rst` wire, is usually a
    primary input instead, which this text splice cannot rewrite the driver of; see
    docs/plans next step)."""
    dos_stuck = DosStuckPayload(victim=payload.reset_net, stuck_value=1)
    return insert_dos_stuck_payload(source, dos_stuck, trigger_wire)


def insert_energy_payload(
    source: str,
    payload: EnergyPayload,
    clock: str,
    node_count: int,
    trigger_wire: str = TRIGGER_WIRE,
) -> str:
    """Declares `round(payload.fraction * node_count)` free-running toggle bits, each flipping
    every cycle while `trigger_wire` is 1 (round 2: EnergyPayload; toggle count is the activity
    proxy lemanruss.htl.verify measures, per the Mimir rule -- no power claim)."""
    n_bits = max(1, round(payload.fraction * node_count))
    reg_name = f"{trigger_wire}_energy"
    decl = (
        f"    reg [{n_bits - 1}:0] {reg_name};\n"
        f"    always @(posedge {clock}) if ({trigger_wire}) {reg_name} <= ~{reg_name};\n"
    )
    return _insert_before_endmodule(source, decl)


def insert_slowdown_payload(source: str, payload: SlowdownPayload, depth: int) -> str:
    """Rewrites `assign victim = expr;` to pass through `depth` extra identity (buffer) stages,
    always-on (round 2: SlowdownPayload; spec section 2's "extra logic levels", not a functional
    change: `depth` is the number of added levels, the effect size lemanruss.htl.verify reports)."""
    match = _find_assign(source, payload.victim)
    expr = match.group(2)
    chain = f"({expr})"
    for _ in range(depth):
        chain = f"({chain} | 1'b0)"  # a pass-through logic level, not a function change
    new_assign = f"assign {payload.victim} = {chain};"
    return source[: match.start()] + new_assign + source[match.end() :]
