"""Seeker-Seq v2.0 tuned sequential builds (round 4; brief item 4).

Every sequential variant must fire within a stated window of N = 1024 cycles with a measured
probability in [1e-3, 1] (limited by the lane count: a probability below 3 / lanes is not
resolved). One multi-cycle pass over the clean design watches, for several candidate condition
sets, a bit-sliced event counter (so P(count >= 2**b by cycle N) is known for every counter
width b at once) and, for several candidate net orderings, the pattern chain (so P(pattern of
length L completes by N) is known for every L at once). A variant per kind (counter or pattern)
and target band (fast / mid / slow) then takes the LARGEST width or length whose probability
lands in the band, builds the infected circuit and re-measures it on an independent sample
(plan default 14).

Victim choice by observability (s298 / s526 / s953 read every output internally): an output that
toggles under the multi-cycle run is chosen, quiet outputs first; if it is read inside the design
it gets its own buffer (blif_text.isolate_output) so the payload cannot feed back. The stuck
value is the minority value of the output, so the payload shows whenever the trigger is high and
the clean output differs.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lemanruss.htl import edit_netlist as en
from lemanruss.htl.bitsim import (
    Compiled,
    compile_model,
    latches_of,
    reset_inputs,
    simulate_comb,
    simulate_seq,
    simulate_seq_pair,
)
from lemanruss.htl.blif_text import (
    BlifModel,
    find_names_block,
    parse_single_model,
)
from lemanruss.htl.edit_netlist import TRIGGER_NET, Editor
from lemanruss.htl.payloads import DosStuckPayload
from lemanruss.htl.rareness import RarenessRecord, scoap_value, wilson
from lemanruss.htl.seeker import (
    Built,
    Failure,
    _Cand,
    _candidates,
    _clock_of,
    _odin_p,
    _readers,
    scoap_table,
    widen_trigger,
)
from lemanruss.htl.triggers import SeqCounterTrigger, SeqPatternTrigger, StatePatternTrigger
from lemanruss.htl.trojan import compose

WINDOW = 1024
PLANES = 13  # counter widths 1..12
MAX_PATTERN = 8
MIN_HITS = 4
SEQ_BANDS = (("fast", 0.5, 1.0), ("mid", 0.05, 0.5), ("slow", 0.003, 0.05))
CHECK_CYCLES = (16, 64, 256, 1024)


def lanes_for(blocks: int) -> int:
    """Lane count by design size (time bound): bigger designs resolve fewer rare events."""
    if blocks <= 3000:
        return 2048
    return 1024 if blocks <= 12000 else 512


@dataclass
class _Obs:
    """Everything the single selection pass records."""

    lanes: int
    out_ones: dict[str, int]
    cond_sets: list[tuple[tuple[str, int], ...]]
    ge: list[list[int]]  # [cond set][b] lanes that counted >= 2**b events by the window
    orderings: list[tuple[tuple[str, int], ...]]
    ever: list[list[int]]  # [ordering][i] lanes where chain stage i has been high


def _lit(values: dict[str, int], name: str, val: int, mask: int) -> int:
    return values[name] if val else ~values[name] & mask


def observe(
    comp: Compiled, lanes: int, seed: int, fixed: dict[str, int],
    cond_sets: list[tuple[tuple[str, int], ...]], orderings: list[tuple[tuple[str, int], ...]],
) -> _Obs:
    mask = (1 << lanes) - 1
    planes = [[0] * PLANES for _ in cond_sets]
    ge = [[0] * PLANES for _ in cond_sets]
    prev = [[0] * MAX_PATTERN for _ in orderings]
    ever = [[0] * MAX_PATTERN for _ in orderings]
    out_ones = dict.fromkeys(comp.outputs, 0)

    def hook(_t: int, values: dict[str, int]) -> None:
        for o in comp.outputs:
            out_ones[o] += values[o].bit_count()
        for j, cs in enumerate(cond_sets):
            carry = mask
            for name, val in cs:
                carry &= _lit(values, name, val, mask)
            pl = planes[j]
            for i in range(PLANES):
                nxt = pl[i] ^ carry
                carry &= pl[i]
                pl[i] = nxt
                if not carry:
                    break
            g = ge[j]
            for b in range(0, PLANES):
                g[b] |= pl[b]
            # b=0: the counter's bit 0 goes high (and stays OR'd true) the first time the
            # condition is ever seen, so ge[j][0] is exactly "fired at least once by cycle N"
            # (rc7 magic-trigger reachability, spec section 13.2); the b in 1..12 readers below
            # (t-seq-counter) are unaffected -- purely additive.
        for k, order in enumerate(orderings):
            cur = [0] * MAX_PATTERN
            for i, (name, val) in enumerate(order):
                c = _lit(values, name, val, mask)
                cur[i] = c if i == 0 else prev[k][i - 1] & c
                ever[k][i] |= cur[i]
            prev[k] = cur

    simulate_seq(comp, lanes, WINDOW, seed, [], fixed, hook)
    return _Obs(lanes, out_ones, cond_sets, ge, orderings, ever)


def choose_victim(model: BlifModel, obs: _Obs) -> tuple[str, int, bool] | None:
    """(victim output, stuck value, needs an isolation buffer) by observability: toggling
    outputs (0.02 <= P(1) <= 0.98 over the run) first, then quiet (unread) ones, then the one the
    payload shows on most often; a near-constant output is the fallback (stuck at the other
    value, always visible)."""
    read = _readers(model)
    total = obs.lanes * WINDOW
    best: tuple[tuple[bool, bool, float], str, int, bool] | None = None
    for o in model.outputs:
        p1 = obs.out_ones.get(o, 0) / total
        toggles = 0.02 <= p1 <= 0.98
        stuck = 1 if p1 <= 0.5 else 0
        visible = 1 - (p1 if stuck else 1 - p1)
        quiet = o not in read and find_names_block(model, o) is not None
        key = (not toggles, not quiet, -visible)
        if best is None or key < best[0]:
            best = (key, o, stuck, not quiet)
    return None if best is None else (best[1], best[2], best[3])


def _state_candidates(
    model: BlifModel, values: dict[str, int], nvec: int, sc: dict[str, dict[str, int]],
    min_p: float = 0.02,
) -> list[_Cand]:
    """rc7 magic trigger candidate pool (spec section 13.1): every register (latch) Q output
    and every primary input, ranked by SCOAP difficulty then rareness over `values` (a
    `simulate_comb` scan-view sample -- latch Q values are randomised there, the same
    combinational-mode view `seeker._candidates` uses for internal nets)."""
    full = (1 << nvec) - 1
    names = [q for _d, q, _c in latches_of(model)] + list(model.inputs)
    out: list[_Cand] = []
    seen: set[str] = set()
    for name in names:
        if name in seen or name not in values:
            continue
        seen.add(name)
        ones = values[name].bit_count()
        rare = 1 if ones * 2 <= nvec else 0
        cnt = ones if rare else nvec - ones
        if cnt == 0 or cnt / nvec < min_p:
            continue
        row = sc.get(name, {})
        cc = row.get("cc1" if rare else "cc0", row.get("sc1" if rare else "sc0", 10**18))
        mask = values[name] if rare else ~values[name] & full
        out.append(_Cand(name, rare, cnt / nvec, mask, cc))
    out.sort(key=lambda c: (-min(c.cc, 10**17), c.p_rare))
    return out


def _candidates_in_band_magic(
    obs: _Obs, lo: float, hi: float
) -> list[tuple[int, int, int]]:
    """(k literals, cond-set index, hits) for every magic AND combination whose P(fired at
    least once by cycle N) over the selection sample lands in [lo, hi] (rc7, spec section 13.2),
    largest k (rarest) first. `obs.ge[j][0]` is "ever fired" (see `observe`'s hook comment)."""
    found: list[tuple[int, int, int]] = []
    for j, g in enumerate(obs.ge):
        hits = g[0].bit_count()
        if hits >= MIN_HITS and lo <= hits / obs.lanes <= hi:
            found.append((len(obs.cond_sets[j]), j, hits))
    found.sort(key=lambda x: (-x[0], x[1]))
    return found


def _cond_sets(cands: list[_Cand], nvec: int) -> list[tuple[tuple[str, int], ...]]:
    found: list[tuple[tuple[str, int], ...]] = []
    for q in (0.5, 0.3, 0.2, 0.1, 0.05, 0.03, 0.015, 0.007):
        chosen, _m = widen_trigger(cands, nvec, q, q / 3, min_hits=64, max_k=8)
        if chosen:
            nets = tuple((c.name, c.rare) for c in chosen)
            if nets not in found:
                found.append(nets)
    return found


def _orderings(cands: list[_Cand], seed: int) -> list[tuple[tuple[str, int], ...]]:
    freq = [c for c in cands if c.p_rare >= 0.1]
    lists = [list(freq), sorted(freq, key=lambda c: -c.p_rare)]
    for k in range(4):
        shuffled = list(freq)
        random.Random(seed + k).shuffle(shuffled)
        lists.append(shuffled)
    lists.append(sorted(freq, key=lambda c: c.p_rare))
    out: list[tuple[tuple[str, int], ...]] = []
    for lst in lists:
        order = tuple((c.name, c.rare) for c in lst[:MAX_PATTERN])
        if len(order) >= 2 and order not in out:
            out.append(order)
    return out


def _candidates_in_band(obs: _Obs, kind: str, lo: float, hi: float) -> list[tuple[int, int, int]]:
    """(size, set index, hits) for every counter width / pattern length whose selection-sample
    probability lies in [lo, hi], largest size first."""
    found: list[tuple[int, int, int]] = []
    if kind == "ctr":
        for j, g in enumerate(obs.ge):
            for b in range(1, PLANES):
                hits = g[b].bit_count()
                if hits >= MIN_HITS and lo <= hits / obs.lanes <= hi:
                    found.append((b, j, hits))
    else:
        for k, ev in enumerate(obs.ever):
            for length in range(2, len(obs.orderings[k]) + 1):
                hits = ev[length - 1].bit_count()
                if hits >= MIN_HITS and lo <= hits / obs.lanes <= hi:
                    found.append((length, k, hits))
    found.sort(key=lambda x: (-x[0], x[1]))
    return found


def build_seq_variant(
    model: BlifModel, comp: Compiled, obs: _Obs, victim: tuple[str, int, bool],
    clock: str, fixed: dict[str, int], sc: dict[str, dict[str, int]],
    base: str, vname: str, kind: str, band: tuple[str, float, float],
    out_dir: Path, circuit_id: str, seed: int, nets_by_name: dict[str, _Cand],
    base_path: Path,
) -> Built | Failure:
    vic, stuck, isolate = victim
    if kind == "magic":
        tried = _candidates_in_band_magic(obs, band[1], band[2])[:3]
    else:
        tried = _candidates_in_band(obs, kind, band[1], band[2])[:3]
    if not tried:
        return Failure(base, vname, f"no {kind} size reaches P(fire<={WINDOW}) in "
                       f"[{band[1]}, {band[2]}] (selection sample, {obs.lanes} lanes)")
    last = "measured outside range"
    clean_ff = len(latches_of(model))
    for size, idx, _hits in tried:
        if kind == "ctr":
            nets = obs.cond_sets[idx]
            trigger: SeqCounterTrigger | SeqPatternTrigger | StatePatternTrigger = (
                SeqCounterTrigger(n=2**size, condition_k=len(nets), nets=nets))
        elif kind == "magic":
            nets = obs.cond_sets[idx]
            trigger = StatePatternTrigger(k=size, nets=nets)
        else:
            nets = obs.orderings[idx][:size]
            trigger = SeqPatternTrigger(k=size, steps=nets)
        payload = DosStuckPayload(victim=vic, stuck_value=stuck)
        trojan = compose(trigger, payload, "netlist", site=vic)
        path = out_dir / f"{circuit_id}.blif"

        def recipe(ed: Editor, nets: tuple[tuple[str, int], ...] = nets, size: int = size) -> None:
            if isolate:
                ed.isolate(vic)
            if kind == "ctr":
                en.seq_counter(ed, nets, size, clock)
            elif kind == "magic":
                en.comb_rare_trigger(ed, nets)
            else:
                en.seq_pattern(ed, nets, clock)
            en.dos_stuck(ed, vic, stuck)

        ins = en.insert(base_path, path, f"trojan:{trojan.id}", recipe,
                         events_dir=en.events_dir_of(path))
        infected = parse_single_model(path.read_text(encoding="utf-8"))
        if kind == "magic":
            inf_ff = len(latches_of(infected))
            if inf_ff != clean_ff:
                last = (f"FF/latch equality hard gate failed: clean {clean_ff}, "
                        f"infected {inf_ff}")
                continue
        icomp = compile_model(infected)
        curve, mism = simulate_seq_pair(comp, icomp, obs.lanes, WINDOW, seed + 1000, TRIGGER_NET,
                                        fixed)
        hits = curve[WINDOW - 1]
        if hits < 3:
            last = f"independent sample: {hits} / {obs.lanes} lanes fired (needs >= 3)"
            continue
        within = {}
        for n in CHECK_CYCLES:
            h = curve[n - 1]
            lo, hi = wilson(h, obs.lanes)
            within[n] = (h / obs.lanes, lo, hi)
        inf_sc = scoap_table(path, sequential=True)
        chosen = [nets_by_name[n] for n, _v in nets if n in nets_by_name]
        rec = RarenessRecord(
            circuit=circuit_id, family="Seeker-Seq", base=base, trojan_id=f"{trojan.id}:{vname}",
            target_band=vname, k=len(nets),
            trigger_cc=[scoap_value(c.cc) for c in chosen],
            trigger_sc=[scoap_value(sc.get(c.name, {}).get("sc1" if c.rare else "sc0"))
                        for c in chosen],
            victim_so=scoap_value(sc.get(vic, {}).get("so")),
            infected_trigger_sc1=scoap_value(inf_sc.get(TRIGGER_NET, {}).get("sc1")),
            net_p_bitsim=[c.p_rare for c in chosen],
            net_p_odin=[_odin_p(sc, c) for c in chosen],
            p_fire_within=within, seq_lanes=obs.lanes, vectors=obs.lanes * WINDOW,
            fires=hits > 0, stealth_mismatches=mism,
            ff_count_clean=clean_ff if kind == "magic" else None,
            ff_count_infected=len(latches_of(infected)) if kind == "magic" else None,
        )
        return Built(circuit_id, base, vname, trojan, path, rec, vic, stuck, "seq", WINDOW, ins)
    return Failure(base, vname, last)


def build_seq_base_rc7(
    base_path: Path, out_dir: Path, next_id: Callable[[], str], seed: int, max_blocks: int,
) -> list[Built | Failure]:
    """Seeker-Seq rc7 (round 9, spec section 13): magic-number trigger only (`t-state-pattern`),
    fast / mid / slow bands. Everything else as `build_seq_base` (victim choice, cond-set
    widening, re-measure on an independent sample); `_state_candidates` replaces `_candidates` as
    the literal pool (register Q outputs and primary inputs, not combinational-internal nets)."""
    base = base_path.stem
    model = parse_single_model(base_path.read_text(encoding="utf-8"))
    clock = _clock_of(model)
    names = [f"magic-{b[0]}" for b in SEQ_BANDS]
    if clock is None:
        return [Failure(base, v, "no latch clock (not a sequential base)") for v in names]
    comp = compile_model(model)
    if len(comp.blocks) > max_blocks:
        return [Failure(base, v, f"{len(comp.blocks)} gates > cap {max_blocks} (run time)")
                for v in names]
    fixed = reset_inputs(model)
    lanes = lanes_for(len(comp.blocks))
    nvec = 1 << 15
    values = simulate_comb(comp, nvec, seed, fixed)
    sc = scoap_table(base_path, sequential=True, sigprob=20000)
    cands = _state_candidates(model, values, nvec, sc, min_p=0.02)
    if not cands:
        return [Failure(base, v, "no register/input literal cleared min_p") for v in names]
    cond_sets = _cond_sets(cands, nvec)
    obs = observe(comp, lanes, seed, fixed, cond_sets, [])
    victim = choose_victim(model, obs)
    if victim is None:
        return [Failure(base, v, "no output to carry the payload") for v in names]
    by_name = {c.name: c for c in cands}
    results: list[Built | Failure] = []
    for band in SEQ_BANDS:
        results.append(build_seq_variant(
            model, comp, obs, victim, clock, fixed, sc, base, f"magic-{band[0]}", "magic",
            band, out_dir, next_id(), seed, by_name, base_path))
    return results


def build_seq_base(
    base_path: Path, out_dir: Path, next_id: Callable[[], str], seed: int, max_blocks: int,
) -> list[Built | Failure]:
    """All Seeker-Seq variants of one base: counter and pattern x fast / mid / slow."""
    base = base_path.stem
    model = parse_single_model(base_path.read_text(encoding="utf-8"))
    clock = _clock_of(model)
    names = [f"{k}-{b[0]}" for k in ("ctr", "pat") for b in SEQ_BANDS]
    if clock is None:
        return [Failure(base, v, "no latch clock (not a sequential base)") for v in names]
    comp = compile_model(model)
    if len(comp.blocks) > max_blocks:
        return [Failure(base, v, f"{len(comp.blocks)} gates > cap {max_blocks} (run time)")
                for v in names]
    fixed = reset_inputs(model)
    lanes = lanes_for(len(comp.blocks))
    nvec = 1 << 15
    values = simulate_comb(comp, nvec, seed, fixed)
    sc = scoap_table(base_path, sequential=True, sigprob=20000)
    cands = _candidates(comp, values, nvec, sc, set(model.outputs), min_p=0.02)
    cond_sets = _cond_sets(cands, nvec)
    orderings = _orderings(cands, seed)
    obs = observe(comp, lanes, seed, fixed, cond_sets, orderings)
    victim = choose_victim(model, obs)
    if victim is None:
        return [Failure(base, v, "no output to carry the payload") for v in names]
    by_name = {c.name: c for c in cands}
    results: list[Built | Failure] = []
    for kind in ("ctr", "pat"):
        for band in SEQ_BANDS:
            results.append(build_seq_variant(
                model, comp, obs, victim, clock, fixed, sc, base, f"{kind}-{band[0]}", kind,
                band, out_dir, next_id(), seed, by_name, base_path))
    return results
