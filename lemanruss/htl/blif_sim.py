"""A tiny combinational BLIF evaluator (round 2): signal probability and driving-input search
directly on a written BLIF, with no dependency on Odin III's Simulation API and no need to mark
any wire `(* keep *)` in the HDL (round 1's workaround, which cannot touch a real base design
under `external/`, read-only). `.names` only (gate-level after `write_blif --gates-as-names`);
`.latch` nets are treated as free (round-2 scope stays combinational-only; see
docs/plans/2026-10-31-htl-plan.md next step for a sequential extension).
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from lemanruss.htl.blif_text import BlifModel


def _names_blocks(model: BlifModel) -> list[tuple[list[str], str, list[str]]]:
    """Every `.names` block as (inputs, output, cover rows), in the order written."""
    blocks: list[tuple[list[str], str, list[str]]] = []
    i = 0
    while i < len(model.body):
        line = model.body[i]
        if line.startswith(".names "):
            words = line.split()[1:]
            rows: list[str] = []
            j = i + 1
            while j < len(model.body) and not model.body[j].startswith("."):
                rows.append(model.body[j])
                j += 1
            blocks.append((words[:-1], words[-1], rows))
            i = j
        else:
            i += 1
    return blocks


def _pattern_matches(pattern: str, values: list[int]) -> bool:
    return all(bit == "-" or int(bit) == value for bit, value in zip(pattern, values, strict=True))


def _row_fields(row: str) -> tuple[str, str]:
    """(pattern, output value): a zero-input `.names Y` row is just the value alone (no pattern,
    `write_blif`'s own constant-table shape; docs/PASSES.md's `write_blif` row)."""
    tokens = row.split()
    return (tokens[0], tokens[1]) if len(tokens) == 2 else ("", tokens[0])


def _eval_names(rows: list[str], values: list[int]) -> int:
    """Standard BLIF `.names` semantics: every row's output bit is the same (0 or 1) -- the
    on-set (all rows "1") or the off-set (all rows "0") -- and a pattern not covered gets the
    other value. A zero-row block (the constant `.names Y` with no rows) is the constant 0."""
    if not rows:
        return 0
    on_set = _row_fields(rows[0])[1] == "1"
    matched = any(_pattern_matches(_row_fields(row)[0], values) for row in rows)
    return (1 if matched else 0) if on_set else (0 if matched else 1)


def evaluate_cycle(model: BlifModel, inputs: dict[str, int]) -> dict[str, int]:
    """Evaluates every `.names` net for one combinational assignment of primary inputs (fixed
    point over the blocks: handles any write order, not just a topological one)."""
    values = dict(inputs)
    blocks = _names_blocks(model)
    pending = list(blocks)
    while pending:
        progressed = False
        still_pending = []
        for block_inputs, output, rows in pending:
            if all(name in values for name in block_inputs):
                in_values = [values[name] for name in block_inputs]
                values[output] = _eval_names(rows, in_values)
                progressed = True
            else:
                still_pending.append((block_inputs, output, rows))
        pending = still_pending
        if not progressed and pending:
            unresolved = [output for _, output, _ in pending]
            raise ValueError(f"evaluate_cycle: cannot resolve {unresolved} (missing a driver?)")
    return values


@dataclass(frozen=True)
class NetProbability:
    name: str
    p_one: float
    samples: int


def monte_carlo_probability(
    model: BlifModel, cycles: int = 4096, seed: int = 0
) -> list[NetProbability]:
    """P(net == 1) for every net (input, internal, output) over `cycles` uniform-random input
    draws."""
    rng = random.Random(seed)
    totals: dict[str, int] = {}
    for _ in range(cycles):
        draw = {name: rng.getrandbits(1) for name in model.inputs}
        values = evaluate_cycle(model, draw)
        for name, value in values.items():
            totals[name] = totals.get(name, 0) + value
    return [NetProbability(name, total / cycles, cycles) for name, total in totals.items()]


def find_driving_inputs(
    model: BlifModel, trigger_nets: tuple[tuple[str, int], ...]
) -> dict[str, int] | None:
    """Brute-forces every primary-input combination and returns the first that makes every
    trigger net equal its target value, or None if none does."""
    for combo in itertools.product([0, 1], repeat=len(model.inputs)):
        draw = dict(zip(model.inputs, combo, strict=True))
        values = evaluate_cycle(model, draw)
        if all(values.get(name) == value for name, value in trigger_nets):
            return draw
    return None
