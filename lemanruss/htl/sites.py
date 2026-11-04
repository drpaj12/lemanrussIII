"""Site selection: rare nets for triggers, victim nets for payloads by role.

Spec: docs/specs/2026-10-31-htl-design.md section 3. Until the Odin III `scoap` pass merges,
rarity comes from signal probability measured by driving a design's Odin III Simulation with a
seeded pseudo-random generator (not Odin III's own `sim`-pass PRNG, since that pass's vector file
only carries port bits -- see docs/PASSES.md's `sim` row -- and rarity needs internal-signal
probability too). A `ScoapRarity` implementation is left as a documented follow-up (spec section
6); nothing here waits on it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

# odin3 is only imported for type checking, so this module is importable (and its pure-Python
# pieces testable) without ODIN3_LIB/PYTHONPATH set (loki's tests/helpers.py pattern).
if TYPE_CHECKING:
    from odin3 import Design


@dataclass(frozen=True)
class SignalProbability:
    """P(signal == 1) over the sampled run, plus the sample count behind it."""

    name: str
    width: int
    p_one: float
    samples: int


def measure_signal_probability(
    design: Design, top: str | None = None, cycles: int = 4096, seed: int = 0
) -> list[SignalProbability]:
    """Drives `design`'s inputs with a seeded PRNG for `cycles` cycles and returns, for every
    1-bit signal the Simulation lists (SignalInfo.width == 1; wider signals are skipped -- a
    rare *value*, not a rare bit pattern, is what triggers need), the fraction of cycles it was 1.

    `design` is an odin3.Design already past `proc; opt; lower` (Simulation's own requirement);
    the caller runs those passes, not this function, so callers that already have a simulable
    design do not pay for it twice.
    """
    rng = random.Random(seed)
    with design.simulate(top) as sim:
        signals = [s for s in sim.signals() if s.width == 1]
        ones = {s.id: 0 for s in signals}
        inputs = [s for s in signals if s.kind == "input"]
        for _ in range(cycles):
            for sig in inputs:
                sim[sig] = rng.getrandbits(1)
            sim.step()
            for sig in signals:
                ones[sig.id] += sim[sig]
        return [
            SignalProbability(s.name, s.width, ones[s.id] / cycles if cycles else 0.0, cycles)
            for s in signals
        ]


class RarityRule(Protocol):
    """A rule that turns a measured run into (net_name, rare_value) candidates."""

    def rare_nets(self, threshold: float = 0.05) -> list[tuple[str, int]]: ...


@dataclass(frozen=True)
class SimProbabilityRarity:
    """RarityRule backed by measure_signal_probability. The brief's interim choice (spec section
    3) until the `scoap` pass lane merges."""

    measurements: tuple[SignalProbability, ...]

    def rare_nets(self, threshold: float = 0.05) -> list[tuple[str, int]]:
        out: list[tuple[str, int]] = []
        for m in self.measurements:
            if m.p_one <= threshold:
                out.append((m.name, 1))
            elif m.p_one >= 1.0 - threshold:
                out.append((m.name, 0))
        return out


@dataclass(frozen=True)
class ScopVictimRule:
    """Victim-by-role selection (spec section 3): outputs, word MSB/LSB group, near-critical-by-
    fanin-depth stand-in. Left here as the single place payload-victim choice happens, so it can
    later read real SCOAP CO or VPR timing without touching the inserters.
    """

    outputs: tuple[str, ...]
    reset_candidates: tuple[str, ...] = ("rst", "reset", "rst_n")

    def output_victim(self) -> str | None:
        return self.outputs[0] if self.outputs else None

    def reset_victim(self, inputs: tuple[str, ...]) -> str | None:
        for name in self.reset_candidates:
            if name in inputs:
                return name
        return inputs[0] if inputs else None

    def msb_lsb_word(self) -> str | None:
        return self.outputs[0] if self.outputs else None
