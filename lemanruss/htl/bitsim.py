"""Compiled bit-parallel BLIF simulator (round 3).

One Python big int holds one net's value across `nvec` independent vectors (lane i = vector i),
so a `.names` block is a handful of big-int AND / OR / NOT operations and 1e5 to 1e6 vectors cost
about the same as a few hundred scalar ones. Needed for the rareness report: a trigger with
p < 1e-4 needs at least ~1e5 vectors to be seen at all.

Sequential: `.latch D Q ...` is a flip-flop; every lane is an independent run from reset state 0
(the `.latch` init value 2 / 3 "unknown" is simulated as 0, plan agent default 12). The latch clock
net is not a data input: it is never driven randomly.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from lemanruss.htl.blif_sim import _names_blocks, _row_fields
from lemanruss.htl.blif_text import BlifModel


@dataclass
class Compiled:
    data_inputs: list[str]
    outputs: list[str]
    # (output net, input nets, on-set patterns, is_on_set): topological order
    blocks: list[tuple[str, list[str], list[str], bool]]
    latches: list[tuple[str, str]] = field(default_factory=list)  # (D net, Q net)
    clocks: set[str] = field(default_factory=set)
    latch_init: list[int] = field(default_factory=list)  # 1 only when `.latch ... 1`; else 0
    # level-sensitive (transparent) latches `ah` / `al`: Q net -> (D net, enable net, active-high)
    level: dict[str, tuple[str, str, bool]] = field(default_factory=dict)


def _latch_fields(line: str) -> tuple[str, str, str | None, str | None]:
    """(D, Q, clock or None, init char or None) of one `.latch` line: BLIF allows
    `.latch D Q [type clock] [init]`."""
    w = line.split()
    rest = w[3:]
    init = None
    if len(rest) in (1, 3):
        init = rest[-1]
        rest = rest[:-1]
    clock = rest[1] if len(rest) == 2 else None
    return w[1], w[2], clock, init


def latch_type(line: str) -> str:
    """Latch type word of one `.latch` line (`re`, `fe`, `ah`, `al`, `as`) or ''."""
    w = line.split()
    rest = w[3:]
    if len(rest) in (1, 3):
        rest = rest[:-1]
    return rest[0] if len(rest) == 2 else ""


def latches_of(model: BlifModel) -> list[tuple[str, str, str | None]]:
    """(D, Q, clock) for every `.latch` line in the body."""
    found: list[tuple[str, str, str | None]] = []
    for line in model.body:
        if line.startswith(".latch"):
            d, q, clock, _init = _latch_fields(line)
            found.append((d, q, clock))
    return found


_RESET_ACTIVE_HIGH = re.compile(r"^(reset|rst|RESET|RST|Reset)$")
_RESET_ACTIVE_LOW = re.compile(r"^(reset_?n|rst_?n|resetb|rstb|RESETN|RSTN|nreset|nrst)$")


def reset_inputs(model: BlifModel) -> dict[str, int]:
    """Primary inputs that look like a reset, with the INACTIVE level (agent default: random
    vectors would otherwise hold a design in reset half of the time and no counter could run).
    Name-based: active-high `reset`/`rst` held 0, active-low `resetn`/`rst_n` held 1."""
    held: dict[str, int] = {}
    for n in model.inputs:
        if _RESET_ACTIVE_HIGH.match(n):
            held[n] = 0
        elif _RESET_ACTIVE_LOW.match(n):
            held[n] = 1
    return held


def compile_model(model: BlifModel) -> Compiled:
    """Topologically orders the `.names` blocks (latch Q nets and primary inputs are sources)."""
    lat = latches_of(model)
    level: dict[str, tuple[str, str, bool]] = {}
    clocks: set[str] = set()
    for ln in model.body:
        if ln.startswith(".latch"):
            d, q, ctrl, _init = _latch_fields(ln)
            if ctrl is not None and latch_type(ln) in ("ah", "al"):
                level[q] = (d, ctrl, latch_type(ln) == "ah")
            elif ctrl is not None:
                clocks.add(ctrl)
    ready = {n for n in model.inputs} | {q for _, q, _ in lat}
    pending = []
    for ins, out, rows in _names_blocks(model):
        if rows:
            on = _row_fields(rows[0])[1] == "1"
            pats = [_row_fields(r)[0] for r in rows]
        else:
            on, pats = True, []
        pending.append((out, ins, pats, on))
    # Kahn's algorithm
    consumers: dict[str, list[int]] = {}
    missing = [0] * len(pending)
    for i, (_o, ins, _p, _on) in enumerate(pending):
        for n in set(ins):
            if n not in ready:
                missing[i] += 1
                consumers.setdefault(n, []).append(i)
    queue = [i for i, m in enumerate(missing) if m == 0]
    order: list[tuple[str, list[str], list[str], bool]] = []
    while queue:
        i = queue.pop()
        order.append(pending[i])
        for j in consumers.get(pending[i][0], []):
            missing[j] -= 1
            if missing[j] == 0:
                queue.append(j)
    if len(order) != len(pending):
        raise ValueError("bitsim: combinational loop or undriven net")
    data_inputs = [n for n in model.inputs if n not in clocks]
    inits = [
        1 if _latch_fields(ln)[3] == "1" else 0 for ln in model.body if ln.startswith(".latch")
    ]
    return Compiled(
        data_inputs, list(model.outputs), order, [(d, q) for d, q, _ in lat], clocks, inits,
        level,
    )


def _eval_block(
    ins: list[str], pats: list[str], on: bool, values: dict[str, int], mask: int
) -> int:
    if not pats:
        return 0
    acc = 0
    for pat in pats:
        term = mask
        for bit, name in zip(pat, ins, strict=True):
            if bit == "1":
                term &= values[name]
            elif bit == "0":
                term &= ~values[name]
        acc |= term
    acc &= mask
    return acc if on else (~acc) & mask


LEVEL_PASSES = 16


def _eval_all(c: Compiled, values: dict[str, int], mask: int) -> None:
    for out, ins, pats, on in c.blocks:
        values[out] = _eval_block(ins, pats, on, values, mask)


def _step(c: Compiled, values: dict[str, int], mask: int) -> None:
    """Evaluates every block. Level-sensitive latches are transparent while enabled: the blocks
    are re-evaluated until no latch output changes (LEVEL_PASSES bounds loops through latches);
    a latch holds the value its Q net had on entry."""
    _eval_all(c, values, mask)
    if not c.level:
        return
    hold = {q: values[q] for q in c.level}
    for _ in range(LEVEL_PASSES):
        changed = False
        for q, (d, en, high) in c.level.items():
            e = values[en] if high else ~values[en] & mask
            new = (e & values[d]) | (~e & hold[q] & mask)
            if new != values[q]:
                values[q] = new
                changed = True
        if not changed:
            return
        _eval_all(c, values, mask)


def _next_state(c: Compiled, values: dict[str, int]) -> dict[str, int]:
    """State after the clock edge: edge flip-flops take D, level latches keep their settled Q."""
    return {q: (values[q] if q in c.level else values[d]) for d, q in c.latches}


def _draw(
    c: Compiled, rng: random.Random, nvec: int, mask: int, fixed: dict[str, int] | None
) -> dict[str, int]:
    """One cycle of input lane words; `fixed` inputs get a constant 0 / all-ones word (the random
    draw is still consumed so the stream does not depend on `fixed`)."""
    out = {n: rng.getrandbits(nvec) for n in c.data_inputs}
    if fixed:
        for n, v in fixed.items():
            if n in out:
                out[n] = mask if v else 0
    return out


def simulate_comb(
    c: Compiled, nvec: int, seed: int, fixed: dict[str, int] | None = None
) -> dict[str, int]:
    """Every net's value over `nvec` uniform-random vectors (latch outputs random too: the
    scan-view that SCOAP's combinational mode uses)."""
    rng = random.Random(seed)
    mask = (1 << nvec) - 1
    values = _draw(c, rng, nvec, mask, fixed)
    for c_name in c.clocks:
        values[c_name] = 0
    for _d, q in c.latches:
        values[q] = rng.getrandbits(nvec)
    _step(c, values, mask)
    return values


def _initial_state(c: Compiled, mask: int) -> dict[str, int]:
    inits = c.latch_init or [0] * len(c.latches)
    return {q: (mask if i else 0) for (_d, q), i in zip(c.latches, inits, strict=True)}


def simulate_seq(
    c: Compiled, nvec: int, cycles: int, seed: int, watch: list[str],
    fixed: dict[str, int] | None = None,
    hook: Callable[[int, dict[str, int]], None] | None = None,
) -> dict[str, list[int]]:
    """Multi-cycle run from the reset state (latch init 1 -> 1, else 0), fresh random inputs each
    cycle. For each watched net: curve[n-1] = number of lanes (of `nvec`) where the net was 1 at
    any cycle <= n. `hook(cycle, values)` sees every cycle's full net values."""
    rng = random.Random(seed)
    mask = (1 << nvec) - 1
    state = _initial_state(c, mask)
    ever = dict.fromkeys(watch, 0)
    curves: dict[str, list[int]] = {w: [] for w in watch}
    for t in range(cycles):
        values = _draw(c, rng, nvec, mask, fixed)
        for c_name in c.clocks:
            values[c_name] = 0
        values.update(state)
        _step(c, values, mask)
        if hook is not None:
            hook(t, values)
        for w in watch:
            ever[w] |= values[w]
            curves[w].append(ever[w].bit_count())
        state = _next_state(c, values)
    return curves


def simulate_given(c: Compiled, given: dict[str, int], nvec: int) -> dict[str, int]:
    """Like `simulate_comb` but with caller-supplied lane values for inputs and latch outputs
    (used for exhaustive enumeration)."""
    mask = (1 << nvec) - 1
    values = dict(given)
    for c_name in c.clocks:
        values[c_name] = 0
    _step(c, values, mask)
    return values


def exhaustive_lanes(names: list[str]) -> tuple[dict[str, int], int]:
    """Lane values enumerating all 2**len(names) assignments, and the lane count."""
    n = len(names)
    nvec = 1 << n
    out: dict[str, int] = {}
    for j, name in enumerate(names):
        period = 1 << (j + 1)
        unit = ((1 << (1 << j)) - 1) << (1 << j)
        out[name] = unit * (((1 << nvec) - 1) // ((1 << period) - 1))
    return out, nvec


def simulate_seq_pair(
    clean: Compiled, infected: Compiled, nvec: int, cycles: int, seed: int, trigger: str,
    fixed: dict[str, int] | None = None,
    record: list[dict[str, int]] | None = None,
    stop_on: str | None = None,
    found: list[int] | None = None,
) -> tuple[list[int], int]:
    """Runs clean and infected side by side on identical random inputs. Returns (curve of lanes
    where the trigger has been high by cycle n, count of (lane, cycle) output mismatches at
    lanes where the trigger had never been high). `record`, if given, receives each cycle's input
    lane words (to replay one lane elsewhere). `stop_on`, if given, names a net: the run stops at
    the first cycle where the trigger is high and that net differs between clean and infected
    (a witness that the payload shows), and the curve/mismatch counts cover cycles so far; the
    lane mask of that witness is appended to `found`."""
    rng = random.Random(seed)
    mask = (1 << nvec) - 1
    sc = _initial_state(clean, mask)
    si = _initial_state(infected, mask)
    ever = 0
    curve: list[int] = []
    mismatches = 0
    for _ in range(cycles):
        ins = _draw(clean, rng, nvec, mask, fixed)
        if record is not None:
            record.append(ins)
        vc = {**ins, **sc}
        vi = {**ins, **si}
        for c_name in clean.clocks:
            vc[c_name] = 0
        for c_name in infected.clocks:
            vi[c_name] = 0
        _step(clean, vc, mask)
        _step(infected, vi, mask)
        diff = 0
        for o in clean.outputs:
            diff |= vc[o] ^ vi[o]
        mismatches += (diff & ~ever & ~vi[trigger] & mask).bit_count()
        ever |= vi[trigger]
        curve.append(ever.bit_count())
        if stop_on is not None:
            hit = vi[trigger] & (vc[stop_on] ^ vi[stop_on])
            if hit:
                if found is not None:
                    found.append(hit)
                break
        sc = _next_state(clean, vc)
        si = _next_state(infected, vi)
    return curve, mismatches


def replay(c: Compiled, steps: list[dict[str, int]]) -> list[dict[str, int]]:
    """One lane driven by explicit per-cycle input bits from the reset state; returns every net's
    0/1 value at each cycle (before the clock edge)."""
    state = _initial_state(c, 1)
    out: list[dict[str, int]] = []
    for step in steps:
        values = dict(step)
        for c_name in c.clocks:
            values[c_name] = 0
        values.update(state)
        _step(c, values, 1)
        out.append(values)
        state = _next_state(c, values)
    return out


def simulate_diff(
    a: Compiled, b: Compiled, nvec: int, cycles: int, seed: int,
    fixed: dict[str, int] | None = None,
) -> list[int]:
    """Two circuits with the same primary I/O names on identical random inputs: curve[n-1] = lanes
    where some primary output differed at any cycle <= n (combinational circuits: cycles = 1)."""
    rng = random.Random(seed)
    mask = (1 << nvec) - 1
    sa = _initial_state(a, mask)
    sb = _initial_state(b, mask)
    ever = 0
    b_inputs = set(b.data_inputs)
    curve: list[int] = []
    for _ in range(cycles):
        ins = _draw(a, rng, nvec, mask, fixed)
        va = {**ins, **sa}
        vb = {**{n: v for n, v in ins.items() if n in b_inputs}, **sb}
        for c_name in a.clocks:
            va[c_name] = 0
        for c_name in b.clocks:
            vb[c_name] = 0
        _step(a, va, mask)
        _step(b, vb, mask)
        for o in a.outputs:
            ever |= va[o] ^ vb[o]
        curve.append(ever.bit_count())
        sa = _next_state(a, va)
        sb = _next_state(b, vb)
    return curve
