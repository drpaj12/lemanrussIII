"""Netlist-level Trojan insertion (spec docs/specs/2026-10-31-htl-design.md section 3).

Edits BLIF text directly (lemanruss.htl.blif_text) because odin3.py's Design/Module/Net object
model is read-only (no add_node/connect/write call -- confirmed by reading
plugins/python/odin3.py in full; spec section 6 gap note). Every edit here is meant to be
re-validated by the caller re-reading the result with Odin III's `read_blif` (the parse check the
brief asks for); this module does not call Odin III itself, so it stays usable without
ODIN3_LIB/PYTHONPATH for its own unit tests.

Needs BLIF written with `write_blif --gates-as-names` (docs/PASSES.md `write_blif` row): plain
`write_blif` emits `.subckt $_AND_ ...` for a built-in gate, not a `.names` line, so
`find_names_block` would never find the driver; `--gates-as-names` writes every built-in gate as
`.names` with its truth table, which this module's helpers edit.

Round 1 scope: CombRareTrigger, and the DosStuck, ErrHi and ErrLo payloads, each on a single-bit
victim net.

Round 2 adds AlwaysOnTrigger, InputPatternTrigger, and the DosReset/Energy/Slowdown payloads
(gate-level this time: a `.names` constant, a `.latch`-based toggle ring, an identity `.names`
buffer chain). SeqCounterTrigger needs a gate-by-gate ripple counter + comparator + sticky
`.latch` -- modelled in lemanruss.htl.triggers, built at the HDL level
(lemanruss.htl.insert_hdl.insert_seq_counter_trigger, where Verilog arithmetic makes it far
simpler), not yet at this (netlist) level; see docs/plans/2026-10-31-htl-plan.md's next step.
SeqPatternTrigger (the FSM-sequence trigger) is not wired into either inserter yet.
"""

from __future__ import annotations

from lemanruss.htl.blif_text import BlifModel, find_names_block, names_line
from lemanruss.htl.payloads import (
    DosResetPayload,
    DosStuckPayload,
    EnergyPayload,
    ErrHiPayload,
    ErrLoPayload,
    SlowdownPayload,
)
from lemanruss.htl.triggers import CombRareTrigger, InputPatternTrigger

TRIGGER_NET = "__htl_trigger"


class NoDriver(ValueError):
    """Raised when the chosen victim net has no `.names` line driving it in this model's body
    (e.g. it is a primary input or a `.latch` output); out of scope for this round (see module
    docstring)."""


def _trigger_cover_row(values: tuple[int, ...]) -> str:
    return "".join(str(v) for v in values) + " 1"


def insert_comb_rare_trigger(
    model: BlifModel, trigger: CombRareTrigger, trigger_net: str = TRIGGER_NET
) -> BlifModel:
    """Appends a `.names` AND of the trigger's rare nets at their rare polarity, driving
    `trigger_net`. `trigger.nets` must already be bound to real net names (lemanruss.htl.sites)."""
    if not trigger.nets:
        raise ValueError("insert_comb_rare_trigger: trigger.nets is empty (bind it first)")
    inputs = [name for name, _ in trigger.nets]
    values = tuple(value for _, value in trigger.nets)
    new_body = [*model.body, names_line(inputs, trigger_net), _trigger_cover_row(values)]
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


def _mux_rows_force_constant(stuck_value: int) -> list[str]:
    """Cover rows for `Y = trig ? stuck_value : tmp` as `.names trig tmp Y`."""
    if stuck_value:
        return ["1- 1", "01 1"]
    return ["01 1"]


def insert_dos_stuck_payload(
    model: BlifModel, payload: DosStuckPayload, trigger_net: str = TRIGGER_NET
) -> BlifModel:
    """Forces `payload.victim` to `payload.stuck_value` whenever `trigger_net` is 1, by renaming
    the victim's existing driver to a fresh internal net and adding a 2-input mux `.names`."""
    found = find_names_block(model, payload.victim)
    if found is None:
        raise NoDriver(f"{payload.victim}: no .names line drives it in this model's body")
    index, _driver_inputs, _rows = found
    tmp_net = f"__htl_tmp_{payload.victim}"
    new_body = list(model.body)
    new_body[index] = new_body[index].rsplit(None, 1)[0] + f" {tmp_net}"
    new_body.extend(
        [
            names_line([trigger_net, tmp_net], payload.victim),
            *_mux_rows_force_constant(payload.stuck_value),
        ]
    )
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


def _mux_rows_force_bit(force: bool) -> list[str]:
    """Cover rows for `.names trig tmp Y`: `Y = trig ? 1 : tmp` when force, else the flipped bit
    `Y = trig XOR tmp` when triggered, passed through otherwise."""
    if force:
        return ["1- 1", "01 1"]
    return ["10 1", "01 1"]  # trig&!tmp -> 1 ; !trig&tmp -> 1  (Y = trig XOR tmp)


def insert_err_bit_payload(
    model: BlifModel,
    payload: ErrHiPayload | ErrLoPayload,
    victim_bit_net: str,
    trigger_net: str = TRIGGER_NET,
) -> BlifModel:
    """Flips (or forces to 1) one bit net of a word payload, driven by `trigger_net`. The caller
    (lemanruss.htl.sites / the benchmark builder) resolves which of the word's bit nets this call
    targets, since BLIF carries no word grouping; see spec section 3's "word MSB/LSB" note."""
    found = find_names_block(model, victim_bit_net)
    if found is None:
        raise NoDriver(f"{victim_bit_net}: no .names line drives it in this model's body")
    index, _driver_inputs, _rows = found
    tmp_net = f"__htl_tmp_{victim_bit_net}"
    new_body = list(model.body)
    new_body[index] = new_body[index].rsplit(None, 1)[0] + f" {tmp_net}"
    new_body.extend(
        [
            names_line([trigger_net, tmp_net], victim_bit_net),
            *_mux_rows_force_bit(payload.force),
        ]
    )
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


def insert_always_on_trigger(model: BlifModel, trigger_net: str = TRIGGER_NET) -> BlifModel:
    """Appends the zero-input `.names trigger_net` constant-1 block (round 2: AlwaysOnTrigger;
    docs/PASSES.md's `write_blif` row: "a constant table as the zero-input `.names Y`")."""
    new_body = [*model.body, f".names {trigger_net}", "1"]
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


def insert_input_pattern_trigger(
    model: BlifModel, trigger: InputPatternTrigger, trigger_net: str = TRIGGER_NET
) -> BlifModel:
    """Appends a `.names` AND testing `trigger.bits` against `trigger.magic_value` (round 2:
    InputPatternTrigger), bits MSB first to match insert_hdl's `{bits}` concatenation order."""
    if not trigger.bits:
        raise ValueError("insert_input_pattern_trigger: trigger.bits is empty (bind it first)")
    width = len(trigger.bits)
    pattern = format(trigger.magic_value, f"0{width}b")
    new_body = [*model.body, names_line(list(trigger.bits), trigger_net), f"{pattern} 1"]
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


def insert_dos_reset_payload(
    model: BlifModel, payload: DosResetPayload, trigger_net: str = TRIGGER_NET
) -> BlifModel:
    """Forces `payload.reset_net` to 1 when `trigger_net` is 1 (round 2: DosResetPayload; a thin
    wrapper on insert_dos_stuck_payload, same scope: `reset_net` must be `.names`-driven)."""
    dos_stuck = DosStuckPayload(victim=payload.reset_net, stuck_value=1)
    return insert_dos_stuck_payload(model, dos_stuck, trigger_net)


def insert_energy_payload(
    model: BlifModel,
    payload: EnergyPayload,
    clock_net: str,
    node_count: int,
    trigger_net: str = TRIGGER_NET,
) -> BlifModel:
    """Adds `round(payload.fraction * node_count)` toggle-ring bits, each a `.latch` whose data
    input is `trigger_net XOR Q` (freezes when `trigger_net` is 0, flips every `clock_net` edge
    otherwise) -- round 2: EnergyPayload. Toggle count is the activity proxy
    lemanruss.htl.verify measures (Mimir rule: no power claim)."""
    n_bits = max(1, round(payload.fraction * node_count))
    new_body = list(model.body)
    for i in range(n_bits):
        q_net = f"__htl_energy_q{i}"
        d_net = f"__htl_energy_d{i}"
        new_body.extend(
            [
                names_line([trigger_net, q_net], d_net),
                "10 1",  # trig=1, Q=0 -> D=1
                "01 1",  # trig=0, Q=1 -> D=1  (D = trig XOR Q)
                f".latch {d_net} {q_net} re {clock_net} 0",
            ]
        )
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


def insert_slowdown_payload(model: BlifModel, payload: SlowdownPayload, depth: int) -> BlifModel:
    """Splices `depth` identity (buffer) `.names` stages onto `payload.victim`'s existing driver
    (round 2: SlowdownPayload; "extra logic levels", not a functional change -- `depth` is the
    effect size lemanruss.htl.verify reports as the logic-level-depth delta)."""
    found = find_names_block(model, payload.victim)
    if found is None:
        raise NoDriver(f"{payload.victim}: no .names line drives it in this model's body")
    index, _driver_inputs, _rows = found
    new_body = list(model.body)
    stage_net = f"__htl_slow_0_{payload.victim}"
    new_body[index] = new_body[index].rsplit(None, 1)[0] + f" {stage_net}"
    for i in range(depth):
        next_net = payload.victim if i == depth - 1 else f"__htl_slow_{i + 1}_{payload.victim}"
        new_body.extend([names_line([stage_net], next_net), "1 1"])
        stage_net = next_net
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


# ---- Round 3: sequential (latch-based) triggers at the netlist level -------------------------


def _latch(d: str, q: str, clock: str) -> str:
    return f".latch {d} {q} re {clock} 0"


def _or2_rows() -> list[str]:
    return ["1- 1", "-1 1"]


def _cond_rows(values: tuple[int, ...]) -> list[str]:
    return ["".join(str(v) for v in values) + " 1"]


def insert_seq_counter_netlist(
    model: BlifModel,
    cond_nets: tuple[tuple[str, int], ...],
    bits: int,
    clock: str,
    trigger_net: str = TRIGGER_NET,
) -> BlifModel:
    """Time bomb: an `bits`-bit ripple counter counts cycles in which the AND of `cond_nets`
    (at their given polarity) holds; the trigger goes high at the N = 2**bits-th such cycle and
    stays high (sticky latch). Reset state 0."""
    if not cond_nets or bits < 1:
        raise ValueError("insert_seq_counter_netlist: need cond_nets and bits >= 1")
    p = "__htl_c"
    body = list(model.body)
    body += [
        names_line([n for n, _ in cond_nets], f"{p}_e"),
        *_cond_rows(tuple(v for _, v in cond_nets)),
    ]
    carry = f"{p}_e"
    for i in range(bits):
        q, d, nxt = f"{p}_q{i}", f"{p}_d{i}", f"{p}_k{i + 1}"
        body += [names_line([carry, q], d), "10 1", "01 1"]
        body += [names_line([carry, q], nxt), "11 1"]
        body.append(_latch(d, q, clock))
        carry = nxt
    body += [names_line([f"{p}_f", carry], f"{p}_fd"), *_or2_rows()]
    body.append(_latch(f"{p}_fd", f"{p}_f", clock))
    body += [names_line([f"{p}_f", carry], trigger_net), *_or2_rows()]
    return BlifModel(model.name, model.inputs, model.outputs, body)


def insert_seq_pattern_netlist(
    model: BlifModel,
    cond_nets: tuple[tuple[str, int], ...],
    clock: str,
    trigger_net: str = TRIGGER_NET,
) -> BlifModel:
    """FSM sequence: the trigger goes high (sticky) after `cond_nets[i]` held at its polarity in
    L = len(cond_nets) consecutive cycles, in order (stage i is set when stage i-1 was set and
    cond i holds). Reset state 0."""
    if not cond_nets:
        raise ValueError("insert_seq_pattern_netlist: need cond_nets")
    p = "__htl_s"
    body = list(model.body)
    prev: str | None = None
    for i, (net, val) in enumerate(cond_nets):
        d, q = f"{p}_d{i}", f"{p}_q{i}"
        if prev is None:
            body += [names_line([net], d), f"{val} 1"]
        else:
            body += [names_line([prev, net], d), f"1{val} 1"]
        body.append(_latch(d, q, clock))
        prev = q
    assert prev is not None
    body += [names_line([f"{p}_f", prev], f"{p}_fd"), *_or2_rows()]
    body.append(_latch(f"{p}_fd", f"{p}_f", clock))
    body += [names_line([f"{p}_f", prev], trigger_net), *_or2_rows()]
    return BlifModel(model.name, model.inputs, model.outputs, body)
