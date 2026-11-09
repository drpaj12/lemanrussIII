"""Neutral stimulus per benchmark (Seeker v2.0 full sets, 2026-11-09).

A stimulus is public: a vector set (Comb) or one vector sequence from reset (Seq) that the golden
and the infected circuits answer identically, so no Trojan fires on it. Which circuits it was
checked against stays in the answer key; the file carries only input names and bit rows.

- Comb: a pool of random vectors (all assignments when the benchmark has at most 12 inputs) is
  simulated on the golden and on every infected circuit of the benchmark in every set; a vector on
  which any primary output differs is removed; the first `n_target` remaining vectors are kept
  and the whole set is checked again.
- Seq: `cycles` cycles from reset. At each cycle `lanes` random input vectors are tried from the
  current state of the golden and of every infected circuit; the first vector on which no output
  differs is taken (the vectors that fire a Trojan are the ones dropped). If every candidate
  differs the sequence stops there (shorter than `cycles`; recorded). The finished sequence is
  replayed once more on every circuit as the check.

Files: first line the input names, then one row of 0/1 characters per vector (Comb) or per cycle
(Seq), in the same order. Reset inputs named `reset` or `rst` are 1 with probability 1/16.
"""

from __future__ import annotations

import random
import re
from collections.abc import Sequence

from lemanruss.htl.bitsim import (
    Compiled,
    _initial_state,
    _next_state,
    _step,
    compile_model,
    exhaustive_lanes,
    simulate_given,
)
from lemanruss.htl.blif_text import parse_single_model

Json = dict[str, object]
RESET = re.compile(r"(?i)^(reset|rst)$")


def compile_text(text: str) -> Compiled:
    return compile_model(parse_single_model(text))


def _rows(names: Sequence[str], lanes: dict[str, int], picked: list[int]) -> list[str]:
    return ["".join("1" if (lanes[n] >> i) & 1 else "0" for n in names) for i in picked]


def _lane_words(names: Sequence[str], rows: list[str]) -> dict[str, int]:
    out = dict.fromkeys(names, 0)
    for i, row in enumerate(rows):
        for n, ch in zip(names, row, strict=True):
            if ch == "1":
                out[n] |= 1 << i
    return out


def comb_diff(golden: Compiled, circuit: Compiled, given: dict[str, int], nvec: int) -> int:
    """Lanes on which some primary output of `circuit` differs from the golden's."""
    g = simulate_given(golden, given, nvec)
    c = simulate_given(circuit, given, nvec)
    d = 0
    for o in golden.outputs:
        d |= g[o] ^ c[o]
    return d


def comb_stimulus(
    golden: Compiled, circuits: list[Compiled], n_target: int, pool: int, seed: int,
) -> tuple[list[str], list[str], Json]:
    """(input names, rows, stats). `circuits` are the infected circuits of the benchmark."""
    names = list(golden.data_inputs)
    if len(names) <= 12:
        lanes, nvec = exhaustive_lanes(names)
    else:
        nvec = pool
        rng = random.Random(seed)
        lanes = {n: rng.getrandbits(nvec) for n in names}
    fired = 0
    for c in circuits:
        fired |= comb_diff(golden, c, lanes, nvec)
    mask = (1 << nvec) - 1
    ok = [i for i in range(nvec) if not (fired >> i) & 1 and (mask >> i) & 1]
    random.Random(f"{seed}:pick").shuffle(ok)
    picked = sorted(ok[:n_target])
    rows = _rows(names, lanes, picked)
    check = _lane_words(names, rows)
    bad = sum(comb_diff(golden, c, check, max(1, len(rows))) != 0 for c in circuits)
    stats: Json = {"pool": nvec, "exhaustive": len(names) <= 12, "removed": fired.bit_count(),
                   "kept": len(rows), "infected_checked": len(circuits),
                   "circuits_differing_on_final": bad}
    return names, rows, stats


def _broadcast(word: int, lane: int, mask: int) -> int:
    return mask if (word >> lane) & 1 else 0


def seq_stimulus(
    golden: Compiled, circuits: list[Compiled], cycles: int, lanes: int, seed: int,
    alt_golden: Compiled | None = None, alt: list[bool] | None = None,
) -> tuple[list[str], list[str], Json]:
    """`alt_golden` / `alt`: circuits flagged in `alt` are compared with `alt_golden` instead of
    `golden` (the silicon circuits start from a state without initial values, so their reference
    is the mapped silicon golden, not the gate-level one)."""
    names = list(golden.data_inputs)
    mask = (1 << lanes) - 1
    rng = random.Random(seed)
    refs = [golden] + ([alt_golden] if alt_golden is not None else [])
    ref_of = [1 if (alt and alt[k]) else 0 for k in range(len(circuits))]
    sg = [_initial_state(r, mask) for r in refs]
    sc = [_initial_state(c, mask) for c in circuits]
    rows: list[str] = []
    snaps: list[tuple[list[dict[str, int]], list[dict[str, int]]]] = []
    stuck = False
    retries = 0
    steps = 0
    while len(rows) < cycles and steps < cycles * 40:
        steps += 1
        ins = {n: rng.getrandbits(lanes) for n in names}
        for n in names:
            if RESET.match(n):
                ins[n] = rng.getrandbits(lanes) & rng.getrandbits(lanes) \
                    & rng.getrandbits(lanes) & rng.getrandbits(lanes)
        vgs = []
        for r, st in zip(refs, sg, strict=True):
            vg = {n: ins[n] for n in r.data_inputs if n in ins} | st
            for c_name in r.clocks:
                vg[c_name] = 0
            _step(r, vg, mask)
            vgs.append(vg)
        diff = 0
        vcs = []
        for c, st, ri in zip(circuits, sc, ref_of, strict=True):
            have = set(c.data_inputs)
            vc = {n: ins[n] for n in names if n in have} | st
            for c_name in c.clocks:
                vc[c_name] = 0
            _step(c, vc, mask)
            vcs.append(vc)
            for o in golden.outputs:
                diff |= vgs[ri][o] ^ vc[o]
        free = [i for i in range(lanes) if not (diff >> i) & 1]
        if not free:  # every candidate fires: step back one cycle and draw again
            retries += 1
            if not snaps:
                stuck = True
                break
            sg, sc = snaps.pop()
            rows.pop()
            continue
        lane = rng.choice(free)
        snaps.append((sg, sc))
        rows.append("".join("1" if (ins[n] >> lane) & 1 else "0" for n in names))
        sg = [{q: _broadcast(w, lane, mask) for q, w in _next_state(r, vg).items()}
              for r, vg in zip(refs, vgs, strict=True)]
        sc = [{q: _broadcast(w, lane, mask) for q, w in _next_state(c, vc).items()}
              for c, vc in zip(circuits, vcs, strict=True)]
    stuck = stuck or len(rows) < cycles
    bad = seq_check(golden, circuits, names, rows, alt_golden, alt)
    stats: Json = {"cycles": len(rows), "requested": cycles, "stopped_early": stuck,
                   "candidate_lanes": lanes, "backtracks": retries,
                   "infected_checked": len(circuits), "circuits_differing_on_final": bad}
    return names, rows, stats


def seq_check(golden: Compiled, circuits: list[Compiled], names: list[str], rows: list[str],
              alt_golden: Compiled | None = None, alt: list[bool] | None = None) -> int:
    """Number of circuits whose outputs differ from their reference's somewhere on the sequence."""
    def trace(c: Compiled) -> list[tuple[int, ...]]:
        st = _initial_state(c, 1)
        out: list[tuple[int, ...]] = []
        have = set(c.data_inputs)
        for row in rows:
            v = {n: int(ch) for n, ch in zip(names, row, strict=True) if n in have} | st
            for c_name in c.clocks:
                v[c_name] = 0
            _step(c, v, 1)
            out.append(tuple(v[o] for o in golden.outputs))
            st = _next_state(c, v)
        return out

    refs = [trace(golden)] + ([trace(alt_golden)] if alt_golden is not None else [])
    return sum(trace(c) != refs[1 if (alt and alt[k]) else 0] for k, c in enumerate(circuits))


RESET_TRIGGER_MAX_P = 1e-2  # the loosest rareness band of the release (Comb p < 1e-2)


def reset_trigger_prob(comp: Compiled, trigs: list[str], lanes: int = 1 << 16,
                       seed: int = 0) -> float:
    """Largest P(trigger | reset state, uniform random inputs) over `trigs`, estimated on
    `lanes` random input vectors. Latches start at their reset value (init 1 -> 1, else 0)."""
    rng = random.Random(f"{seed}:reset-trigger")
    mask = (1 << lanes) - 1
    vals = {n: rng.getrandbits(lanes) for n in comp.data_inputs}
    vals.update(_initial_state(comp, mask))
    for c_name in comp.clocks:
        vals[c_name] = 0
    _step(comp, vals, mask)
    return max((vals.get(t, 0).bit_count() / lanes for t in trigs), default=0.0)


def reset_trigger_hit(comp: Compiled, trigs: list[str], lanes: int = 1 << 16,
                      seed: int = 0) -> bool:
    """Build gate (Seeker v2.0): True when some trigger fires in the reset state for more than
    `RESET_TRIGGER_MAX_P` of the random inputs, i.e. at cycle 0 for (almost) any input. A trigger
    that matches the reset state only with a rare input pattern is a rare Trojan and passes."""
    return reset_trigger_prob(comp, trigs, lanes, seed) > RESET_TRIGGER_MAX_P


def reset_active(golden: Compiled, circuits: list[Compiled], lanes: int, seed: int) -> list[int]:
    """Indices of circuits whose outputs differ from the golden's at the reset state for every
    one of `lanes` random input vectors: a Trojan whose magic value is the reset state itself
    fires at cycle 0 whatever the inputs, so no stimulus from reset can keep it silent."""
    rng = random.Random(f"{seed}:reset")
    mask = (1 << lanes) - 1
    ins = {n: rng.getrandbits(lanes) for n in golden.data_inputs}
    vg = {**ins, **_initial_state(golden, mask)}
    for c_name in golden.clocks:
        vg[c_name] = 0
    _step(golden, vg, mask)
    bad: list[int] = []
    for k, c in enumerate(circuits):
        vc = {n: ins[n] for n in c.data_inputs} | _initial_state(c, mask)
        for c_name in c.clocks:
            vc[c_name] = 0
        _step(c, vc, mask)
        d = 0
        for o in golden.outputs:
            d |= vg[o] ^ vc[o]
        if d == mask:
            bad.append(k)
    return bad


def to_text(names: list[str], rows: list[str]) -> str:
    return " ".join(names) + "\n" + "\n".join(rows) + "\n"
