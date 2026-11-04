"""Energy payload measured by toggle counts (round 5).

The energy proxy of the Mimir rule (activity only, no power claim): the number of bit changes of
every net between cycle ends. Round 5 takes it from Odin III's simulator
(`Simulation.set_toggle_counting`, `toggles`) and cross-checks it against the bit-parallel Python
proxy (`toggles_python`) signal by signal on the same stimulus.

Circuits: a sequential base plus a toggle ring (`edit_netlist.energy`, `round(f * nodes)` bits)
behind an always-on trigger, built through the Odin III edit API.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from pathlib import Path

from lemanruss.htl import edit_netlist as en
from lemanruss.htl.bitsim import (
    Compiled,
    _initial_state,
    _next_state,
    _step,
    compile_model,
    reset_inputs,
)
from lemanruss.htl.blif_text import parse_single_model

CYCLES = 200
FRACTION = 0.05


def stimulus(comp: Compiled, fixed: dict[str, int], cycles: int, seed: int) -> list[dict[str, int]]:
    rng = random.Random(seed)
    return [{n: fixed.get(n, rng.getrandbits(1)) for n in comp.data_inputs} for _ in range(cycles)]


def toggles_python(comp: Compiled, steps: list[dict[str, int]]) -> dict[str, int]:
    """Bit changes per net between cycle ends. A cycle end is the state after the clock edge with
    that cycle's inputs still applied (what Odin III's simulator reads after `step`); the first
    cycle is compared with the power-on state settled under all-zero inputs (what Odin III
    holds before the first vector)."""
    state = _initial_state(comp, 1)
    zero = {**dict.fromkeys(comp.data_inputs, 0), **state}
    for c in comp.clocks:
        zero[c] = 0
    _step(comp, zero, 1)
    prev: dict[str, int] = zero
    tog: dict[str, int] = {}
    for step in steps:
        values = {**step, **state}
        for c in comp.clocks:
            values[c] = 0
        _step(comp, values, 1)
        state = _next_state(comp, values)
        end = {**step, **state}
        for c in comp.clocks:
            end[c] = 0
        _step(comp, end, 1)
        for k, v in end.items():
            if k in prev:
                tog[k] = tog.get(k, 0) + (v ^ prev[k])
        prev = end
    return tog


def toggles_odin(path: Path, steps: list[dict[str, int]], names: list[str]) -> dict[str, int]:
    """Toggle counts of `names` from Odin III's simulator over the same stimulus."""
    from odin3 import Design

    out: dict[str, int] = {}
    with Design() as design:
        design.run_pass("read_blif", str(path))
        with design.simulate() as sim:
            sigs = {n: sim.signal(n) for n in names}
            listed = [s for s in sigs.values() if s is not None]
            sim.set_toggle_counting()
            for step in steps:
                for n, v in step.items():
                    s = sigs.get(n) or sim.signal(n)
                    if s is not None:
                        sim.set(s, v)
                sim.step(1)
            for n, s in sigs.items():
                if s is not None and s in listed:
                    out[n] = sim.toggles(s)
    return out


@dataclass
class EnergyResult:
    circuit: str
    base: str
    ring_bits: int
    cycles: int
    signals_compared: int
    signals_equal: int
    odin_total_clean: int
    odin_total_infected: int
    python_total_clean: int
    python_total_infected: int
    odin_delta_per_cycle: float
    python_delta_per_cycle: float
    expected_delta_per_cycle: float
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _measure(path: Path, comp: Compiled, steps: list[dict[str, int]]) -> tuple[
        dict[str, int], dict[str, int]]:
    names = sorted({b[0] for b in comp.blocks} | {q for _d, q in comp.latches}
                   | set(comp.data_inputs))
    return toggles_odin(path, steps, names), toggles_python(comp, steps)


def run_one(base_path: Path, out_dir: Path, circuit: str, seed: int) -> EnergyResult:
    base = base_path.stem
    model = parse_single_model(base_path.read_text(encoding="utf-8"))
    comp = compile_model(model)
    clock = next(iter(sorted(comp.clocks)), None)
    n_bits = max(1, round(FRACTION * len(comp.blocks)))
    empty = EnergyResult(circuit, base, n_bits, CYCLES, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0)
    if clock is None:
        empty.error = "no clock"
        return empty
    inf_path = out_dir / f"{circuit}.blif"

    def recipe(ed: en.Editor) -> None:
        en.always_on_trigger(ed)
        en.energy(ed, clock, n_bits)

    try:
        rep = en.insert(base_path, inf_path, f"trojan:t-always__p-energy:{circuit}", recipe)
        if rep.method != "odin3-edit":
            empty.error = f"fallback: {rep.reason}"
            return empty
        icomp = compile_model(parse_single_model(inf_path.read_text(encoding="utf-8")))
        fixed = reset_inputs(model)
        steps = stimulus(comp, fixed, CYCLES, seed)
        o_c, p_c = _measure(base_path, comp, steps)
        o_i, p_i = _measure(inf_path, icomp, steps)
    except Exception as exc:
        empty.error = f"{type(exc).__name__}: {str(exc)[:120]}"
        return empty
    common = sorted(set(o_c) & set(p_c))
    equal = sum(1 for n in common if o_c[n] == p_c[n])
    common_i = sorted(set(o_i) & set(p_i))
    equal_i = sum(1 for n in common_i if o_i[n] == p_i[n])
    res = EnergyResult(
        circuit, base, n_bits, CYCLES, len(common) + len(common_i), equal + equal_i,
        sum(o_c.values()), sum(o_i.values()), sum(p_c.values()), sum(p_i.values()),
        (sum(o_i.values()) - sum(o_c.values())) / CYCLES,
        (sum(p_i.values()) - sum(p_c.values())) / CYCLES,
        2.0 * n_bits)
    return res
