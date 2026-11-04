"""Seeker v2.0 at n = 200 per base: the pool of distinct Trojans of one base (round 8).

Spec: docs/specs/2026-11-01-seeker-n200-design.md. A `Ctx` holds everything one base needs to
draw Trojans (rare-net candidates, observation pass for sequential bases, depth analysis for the
slowdown payload). `Ctx.draw` returns a `TSpec` or None when the base cannot supply another
Trojan of that payload; nothing is ever padded with copies. Randomness: every draw comes from
`random.Random(f"{seed}:{base}:plan")`, so a base builds the same in any pool order.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from pathlib import Path

from lemanruss.htl.bitsim import (
    Compiled,
    compile_model,
    exhaustive_lanes,
    reset_inputs,
    simulate_comb,
    simulate_given,
)
from lemanruss.htl.blif_text import BlifModel, parse_single_model
from lemanruss.htl.payloads import (
    DosStuckPayload,
    EnergyPayload,
    ErrHiPayload,
    ErrLoPayload,
    Payload,
    SlowdownPayload,
)
from lemanruss.htl.seeker import COMB_BANDS, _candidates, _clock_of, _readers, scoap_table
from lemanruss.htl.seeker import widen_trigger as widen
from lemanruss.htl.seqtune import (
    MAX_PATTERN,
    MIN_HITS,
    SEQ_BANDS,
    _Obs,
    _state_candidates,
    lanes_for,
    observe,
)
from lemanruss.htl.triggers import (
    AlwaysOnTrigger,
    CombRareTrigger,
    SeqCounterTrigger,
    SeqPatternTrigger,
    StatePatternTrigger,
    Trigger,
)
from lemanruss.htl.trojan import Trojan, compose

DOS, ERR_HI, ERR_LO, ENERGY, SLOW = (
    "p-dos-stuck", "p-err-hi", "p-err-lo", "p-energy", "p-slowdown")
COMB_MIX = ((DOS, 0.4), (ERR_HI, 0.2), (ERR_LO, 0.2), (SLOW, 0.2))
SEQ_MIX = ((DOS, 0.3), (ERR_HI, 0.15), (ERR_LO, 0.15), (ENERGY, 0.2), (SLOW, 0.2))
N_SETS = 270  # most distinct triggers one base can be asked for: 100 + 1.7 * 100
SLOW_MAX_SLACK = 3


@dataclass(frozen=True)
class TSpec:
    """One Trojan to insert. `trig` is comb | ctr | pat | none (always-on slowdown)."""

    trig: str
    nets: tuple[tuple[str, int], ...]
    size: int  # counter bits / pattern length / 0
    band: str  # target band name
    payload: str
    victim: str
    param: int  # stuck value (dos), ring bits (energy), chain depth (slowdown), else 0
    isolate: bool
    sel_p: float  # selection-sample probability of the trigger (comb) or of P(fire<=1024) (seq)

    def key(self) -> tuple[object, ...]:
        return (self.trig, tuple(sorted(self.nets)), self.size, self.payload, self.victim,
                self.param)

    def net_set(self) -> frozenset[str]:
        return frozenset(n for n, _v in self.nets)

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["nets"] = [list(n) for n in self.nets]
        return d


def trojan_of(t: TSpec, gates: int = 1, depth: int = 1) -> Trojan:
    """The catalogue Trojan (id = trigger kind x payload kind x level) of a spec."""
    trigger: Trigger
    if t.trig == "comb":
        trigger = CombRareTrigger(k=len(t.nets), nets=t.nets)
    elif t.trig == "ctr":
        trigger = SeqCounterTrigger(n=2**t.size, condition_k=len(t.nets), nets=t.nets)
    elif t.trig == "pat":
        trigger = SeqPatternTrigger(k=t.size, steps=t.nets)
    elif t.trig == "magic":
        trigger = StatePatternTrigger(k=len(t.nets), nets=t.nets)
    else:
        trigger = AlwaysOnTrigger()
    payload: Payload
    if t.payload == DOS:
        payload = DosStuckPayload(victim=t.victim, stuck_value=t.param)
    elif t.payload == ERR_HI:
        payload = ErrHiPayload(word=t.victim, bits=1, force=False)
    elif t.payload == ERR_LO:
        payload = ErrLoPayload(word=t.victim, bits=1, force=False)
    elif t.payload == ENERGY:
        payload = EnergyPayload(fraction=t.param / max(gates, 1))
    else:
        payload = SlowdownPayload(victim=t.victim, fraction=t.param / max(depth, 1))
    return compose(trigger, payload, "netlist", site=t.victim)


def pick_weighted(rng: random.Random, mix: tuple[tuple[str, float], ...]) -> str:
    return rng.choices([m[0] for m in mix], weights=[m[1] for m in mix])[0]


@dataclass
class Depths:
    depth: int
    level: dict[str, int]
    slack: dict[str, int]


def depth_analysis(comp: Compiled, model: BlifModel) -> Depths:
    """Logic levels (levels of `.names`, sources at 0), and the slack of every gate output: how
    many levels shorter than the circuit depth the longest path through it is."""
    level: dict[str, int] = {}
    for out, ins, _p, _o in comp.blocks:
        level[out] = 1 + max((level.get(i, 0) for i in ins), default=0)
    depth = max(level.values(), default=0)
    down: dict[str, int] = {}
    for out, ins, _p, _o in reversed(comp.blocks):
        d_out = down.get(out, 0)
        for i in ins:
            if d_out + 1 > down.get(i, 0):
                down[i] = d_out + 1
    slack = {n: depth - (level[n] + down.get(n, 0)) for n in level}
    del model
    return Depths(depth, level, slack)


class Ctx:
    """Per-base planning state shared by the comb and seq draw rules."""

    kind = "comb"

    def __init__(self, base_path: Path, seed: int) -> None:
        self.base = base_path.stem
        self.base_path = base_path
        self.model = parse_single_model(base_path.read_text(encoding="utf-8"))
        self.comp = compile_model(self.model)
        self.rng = random.Random(f"{seed}:{self.base}:plan")
        self.readers = _readers(self.model)
        driven = {b[0] for b in self.comp.blocks} | {q for _d, q in self.comp.latches}
        self.outs = [o for o in self.model.outputs if o in driven]
        self.dep = depth_analysis(self.comp, self.model)
        self.gates = len(self.comp.blocks)
        self.used_sets: set[frozenset[str]] = set()
        self.used_keys: set[tuple[object, ...]] = set()
        self.clock: str | None = None
        self.lanes = 0
        self.sc: dict[str, dict[str, int]] = {}
        self.mix: tuple[tuple[str, float], ...] = COMB_MIX
        slow = [n for n, s in self.dep.slack.items()
                if s <= SLOW_MAX_SLACK and n not in self.model.outputs and n in self.readers]
        self.slow_pool = sorted(slow)

    # -- rules shared by both families ------------------------------------------------------
    def _victim_for(self, payload: str, exc: set[str]) -> str | None:
        pool = [o for o in self.outs if o not in exc]
        if payload in (ERR_HI, ERR_LO):
            half = len(self.model.outputs) // 2
            upper = set(self.model.outputs[half:] if half else self.model.outputs)
            lower = set(self.model.outputs[:half] if half else self.model.outputs)
            pool = [o for o in pool if o in (upper if payload == ERR_HI else lower)]
        return self.rng.choice(pool) if pool else None

    def _draw_slow(self, exc_nets: set[str], exc_victims: set[str]) -> TSpec | None:
        pairs = [(v, self.dep.slack[v] + 1 + k) for v in self.slow_pool
                 if v not in exc_nets and v not in exc_victims for k in range(4)]
        pairs = [p for p in pairs if (SLOW, p[0], p[1]) not in self.used_keys]
        if not pairs:
            return None
        v, depth = self.rng.choice(pairs)
        self.used_keys.add((SLOW, v, depth))
        return TSpec("none", (), 0, "always-on", SLOW, v, depth, False, 1.0)

    def draw(self, payload: str, exc_nets: set[str], exc_victims: set[str]) -> TSpec | None:
        if payload == SLOW:
            return self._draw_slow(exc_nets, exc_victims)
        if payload == ENERGY and self.kind != "seq":
            return None
        return self._draw_triggered(payload, exc_nets, exc_victims)

    def _draw_triggered(
        self, payload: str, exc_nets: set[str], exc_victims: set[str]
    ) -> TSpec | None:
        raise NotImplementedError

    def energy_bits(self) -> int:
        g = self.rng.uniform(0.005, 0.05)
        return max(2, min(64, round(g * self.gates)))


class CombCtx(Ctx):
    kind = "comb"
    TRIES = 120

    def __init__(self, base_path: Path, seed: int) -> None:
        super().__init__(base_path, seed)
        comp = self.comp
        n_in = len(comp.data_inputs)
        self.exact = n_in <= 20
        if self.exact:
            given, self.nvec = exhaustive_lanes(comp.data_inputs)
            self.values = simulate_given(comp, given, self.nvec)
        else:
            self.nvec = 1 << 20
            self.values = simulate_comb(comp, self.nvec, seed)
        self.sc = scoap_table(base_path, sequential=False, sigprob=20000)
        self.cands = _candidates(comp, self.values, self.nvec, self.sc,
                                 set(self.model.outputs), min_p=1.0 / self.nvec)
        self.min_hits = max(1, min(32, self.nvec >> 14))
        self.mix = COMB_MIX

    def _draw_triggered(
        self, payload: str, exc_nets: set[str], exc_victims: set[str]
    ) -> TSpec | None:
        full = (1 << self.nvec) - 1
        for _attempt in range(self.TRIES):
            band = self.rng.choice(COMB_BANDS)
            pool = [c for c in self.cands if c.name not in exc_nets]
            if not pool:
                return None
            sub = self.rng.sample(pool, min(self.rng.randint(16, 120), len(pool)))
            chosen, lanes = widen(sub, self.nvec, band[1], band[1] / 10, self.min_hits, 16)
            if not chosen or lanes.bit_count() / self.nvec > band[1]:
                continue
            nets = tuple(sorted((c.name, c.rare) for c in chosen))
            fs = frozenset(n for n, _v in nets)
            if fs in self.used_sets:
                continue
            victim: str | None
            stuck = 0
            if payload == DOS:
                pairs = [(o, s) for o in self.outs if o not in exc_victims for s in (0, 1)
                         if lanes & ((~self.values[o] if s else self.values[o]) & full)]
                if not pairs:
                    continue
                victim, stuck = self.rng.choice(pairs)
            else:
                victim = self._victim_for(payload, exc_victims)
                if victim is None:
                    return None
            bits = self.energy_bits() if payload == ENERGY else 0
            self.used_sets.add(fs)
            return TSpec("comb", nets, 0, band[0], payload, victim,
                         stuck if payload == DOS else bits, victim in self.readers,
                         lanes.bit_count() / self.nvec)
        return None


class SeqCtx(Ctx):
    kind = "seq"
    ORDER_TRIES = 700
    SET_TRIES = 1500

    def __init__(self, base_path: Path, seed: int) -> None:
        super().__init__(base_path, seed)
        self.mix = SEQ_MIX
        self.clock = _clock_of(self.model)
        self.fixed = reset_inputs(self.model)
        self.lanes = lanes_for(self.gates)
        nvec = 1 << 15
        values = simulate_comb(self.comp, nvec, seed, self.fixed)
        self.sc = scoap_table(base_path, sequential=True, sigprob=20000)
        self.cands = _candidates(self.comp, values, nvec, self.sc, set(self.model.outputs),
                                 min_p=0.02)
        self.nvec = nvec
        self.cond_sets = self._cond_sets()
        self.orderings = self._orderings()
        self.obs: _Obs = observe(self.comp, self.lanes, seed, self.fixed, self.cond_sets,
                                 self.orderings)
        self.feas = self._feasible()

    def _cond_sets(self) -> list[tuple[tuple[str, int], ...]]:
        found: list[tuple[tuple[str, int], ...]] = []
        seen: set[frozenset[str]] = set()
        qs = (0.5, 0.3, 0.2, 0.1, 0.05, 0.03, 0.015, 0.007)
        if not self.cands:
            return found
        for i in range(self.SET_TRIES):
            if len(found) >= N_SETS + 40:
                break
            q = qs[i % len(qs)]
            sub = self.rng.sample(self.cands, min(self.rng.randint(16, 200), len(self.cands)))
            chosen, _m = widen(sub, self.nvec, q, q / 3, 64, 8)
            if not chosen:
                continue
            nets = tuple(sorted((c.name, c.rare) for c in chosen))
            fs = frozenset(n for n, _v in nets)
            if fs not in seen:
                seen.add(fs)
                found.append(nets)
        return found

    def _orderings(self) -> list[tuple[tuple[str, int], ...]]:
        freq = [c for c in self.cands if c.p_rare >= 0.1]
        out: list[tuple[tuple[str, int], ...]] = []
        seen: set[tuple[tuple[str, int], ...]] = set()
        if len(freq) < 2:
            return out
        for _ in range(self.ORDER_TRIES):
            if len(out) >= N_SETS + 40:
                break
            pick = self.rng.sample(freq, min(MAX_PATTERN, len(freq)))
            order = tuple((c.name, c.rare) for c in pick)
            if order not in seen:
                seen.add(order)
                out.append(order)
        return out

    def _feasible(self) -> dict[tuple[str, str], list[tuple[int, int]]]:
        """(kind, band name) -> [(set index, size)] whose selection-sample P(fire <= 1024) lies
        in the band."""
        obs = self.obs
        feas: dict[tuple[str, str], list[tuple[int, int]]] = {}
        for kind in ("ctr", "pat"):
            for name, _lo, _hi in SEQ_BANDS:
                feas[(kind, name)] = []
        for j, g in enumerate(obs.ge):
            for b in range(1, len(g)):
                h = g[b].bit_count()
                if h >= MIN_HITS:
                    for name, lo, hi in SEQ_BANDS:
                        if lo <= h / obs.lanes <= hi:
                            feas[("ctr", name)].append((j, b))
        for k, ev in enumerate(obs.ever):
            for length in range(2, len(obs.orderings[k]) + 1):
                h = ev[length - 1].bit_count()
                if h >= MIN_HITS:
                    for name, lo, hi in SEQ_BANDS:
                        if lo <= h / obs.lanes <= hi:
                            feas[("pat", name)].append((k, length))
        return feas

    def _victim_seq(self, payload: str, exc: set[str]) -> tuple[str, int] | None:
        total = self.obs.lanes * 1024
        pool = [o for o in self.outs if o not in exc]
        if payload in (ERR_HI, ERR_LO):
            v = self._victim_for(payload, exc)
            return None if v is None else (v, 0)
        if not pool:
            return None
        togg = [o for o in pool if 0.02 <= self.obs.out_ones.get(o, 0) / total <= 0.98]
        victim = self.rng.choice(togg or pool)
        p1 = self.obs.out_ones.get(victim, 0) / total
        return victim, 1 if p1 <= 0.5 else 0

    def _draw_triggered(
        self, payload: str, exc_nets: set[str], exc_victims: set[str]
    ) -> TSpec | None:
        combos = [(k, b[0]) for k in ("ctr", "pat") for b in SEQ_BANDS]
        self.rng.shuffle(combos)
        for kind, band in combos:
            entries = [(i, s) for i, s in self.feas[(kind, band)]
                       if self._nets_of(kind, i, s).isdisjoint(exc_nets)
                       and self._nets_of(kind, i, s) not in self.used_sets]
            if not entries:
                continue
            idx, size = self.rng.choice(entries)
            vs = self._victim_seq(payload, exc_victims)
            if vs is None:
                return None
            victim, stuck = vs
            fs = self._nets_of(kind, idx, size)
            nets = (self.cond_sets[idx] if kind == "ctr" else self.orderings[idx][:size])
            self.used_sets.add(fs)
            bits = self.energy_bits() if payload == ENERGY else 0
            return TSpec(kind, tuple(nets), size, band, payload, victim,
                         stuck if payload == DOS else bits, victim in self.readers, 0.0)
        return None

    def _nets_of(self, kind: str, idx: int, size: int) -> frozenset[str]:
        nets = self.cond_sets[idx] if kind == "ctr" else self.orderings[idx][:size]
        return frozenset(n for n, _v in nets)


SEQ_MIX_RC7 = ((DOS, 0.4), (ERR_HI, 0.2), (ERR_LO, 0.2), (SLOW, 0.2))  # no p-energy (adds a latch)


class SeqCtxRc7(SeqCtx):
    """rc7 (round 9, spec section 13): the magic-number trigger only (`t-state-pattern`), drawn
    from register Q outputs and primary inputs (`seqtune._state_candidates`), not combinational-
    internal nets. `p-energy` is dropped from the payload mix (the one payload that adds a
    latch); `t-seq-counter`/`t-seq-pattern` stay unused (`_feasible`/`_draw_triggered` below only
    ever propose `"magic"`)."""

    def __init__(self, base_path: Path, seed: int) -> None:
        super().__init__(base_path, seed)
        self.mix = SEQ_MIX_RC7
        nvec = 1 << 15
        values = simulate_comb(self.comp, nvec, seed, self.fixed)
        self.cands = _state_candidates(self.model, values, nvec, self.sc, min_p=0.02)
        self.cond_sets = self._cond_sets()
        self.orderings = []
        self.obs = observe(self.comp, self.lanes, seed, self.fixed, self.cond_sets, [])
        self.feas = self._feasible()

    def _feasible(self) -> dict[tuple[str, str], list[tuple[int, int]]]:
        """(("magic", band) -> [(set index, k)]) whose P(fired at least once by cycle N) over
        the selection sample lands in the band (spec section 13.2; `obs.ge[j][0]` is "ever
        fired", see `seqtune.observe`'s hook comment)."""
        obs = self.obs
        feas: dict[tuple[str, str], list[tuple[int, int]]] = {
            ("magic", name): [] for name, _lo, _hi in SEQ_BANDS}
        for j, g in enumerate(obs.ge):
            h = g[0].bit_count()
            if h < MIN_HITS:
                continue
            k = len(self.cond_sets[j])
            for name, lo, hi in SEQ_BANDS:
                if lo <= h / obs.lanes <= hi:
                    feas[("magic", name)].append((j, k))
        return feas

    def _draw_triggered(
        self, payload: str, exc_nets: set[str], exc_victims: set[str]
    ) -> TSpec | None:
        bands = [b[0] for b in SEQ_BANDS]
        self.rng.shuffle(bands)
        for band in bands:
            entries = [(i, k) for i, k in self.feas[("magic", band)]
                       if self._nets_of("magic", i, k).isdisjoint(exc_nets)
                       and self._nets_of("magic", i, k) not in self.used_sets]
            if not entries:
                continue
            for _attempt in range(24):
                idx, size = self.rng.choice(entries)
                vs = self._victim_seq(payload, exc_victims)
                if vs is None:
                    return None
                victim, stuck = vs
                fs = self._nets_of("magic", idx, size)
                # A trigger bit that is the victim net reads the payload's own output (the victim
                # is a register Q or input): a combinational loop. Redraw instead.
                if victim in fs:
                    continue
                nets = self.cond_sets[idx]
                self.used_sets.add(fs)
                return TSpec("magic", tuple(nets), size, band, payload, victim, stuck,
                            victim in self.readers, 0.0)
        return None

    def _nets_of(self, kind: str, idx: int, size: int) -> frozenset[str]:
        del kind, size
        return frozenset(n for n, _v in self.cond_sets[idx])


def make_ctx_rc7(base_path: Path, seed: int) -> Ctx | str:
    """rc7 planning context: Seeker-Seq only (the magic trigger needs register state; the Comb
    family keeps its rc5 numbers unchanged, per Peter's 2026-11-02 decision)."""
    model = parse_single_model(base_path.read_text(encoding="utf-8"))
    if not any(ln.startswith(".latch") for ln in model.body):
        return "not a sequential base (rc7 is Seeker-Seq only)"
    if _clock_of(model) is None:
        return "no latch clock (not a sequential base)"
    return SeqCtxRc7(base_path, seed)


def make_ctx(base_path: Path, seed: int) -> Ctx | str:
    """A planning context, or the reason the base cannot be planned."""
    model = parse_single_model(base_path.read_text(encoding="utf-8"))
    if any(ln.startswith(".latch") for ln in model.body):
        if _clock_of(model) is None:
            return "no latch clock (not a sequential base)"
        return SeqCtx(base_path, seed)
    return CombCtx(base_path, seed)


def neutral_signatures(
    ctx: Ctx, count: int, rng: random.Random
) -> list[tuple[tuple[str, str], ...]]:
    """Up to `count` distinct neutral-edit signatures: 2..6 (net, kind) pairs, kind `inv2`
    (two inverters in series) or `buf2` (two buffers), on internal gate outputs."""
    nets = sorted(b[0] for b in ctx.comp.blocks if b[0] not in ctx.model.outputs)
    out: list[tuple[tuple[str, str], ...]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    if len(nets) < 6:  # tiny bases (every gate an output): the output nets may be edited too
        nets = sorted(b[0] for b in ctx.comp.blocks)
    if not nets:
        return out
    for _ in range(count * 8):
        if len(out) >= count:
            break
        m = min(rng.randint(2, 6), len(nets))
        chosen = rng.sample(nets, m)
        sig = tuple(sorted((n, rng.choice(("inv2", "buf2"))) for n in chosen))
        if sig not in seen:
            seen.add(sig)
            out.append(sig)
    return out
