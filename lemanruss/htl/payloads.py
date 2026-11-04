"""Payload effects for the Hardware Trojan Library (HTL).

Spec: docs/specs/2026-10-31-htl-design.md section 2. Payload "effect measure" strings name how
lemanruss.htl.verify scores the Trojan once built; the measure itself (functional diff, toggle
count, logic-level depth) is computed from a design, not stored on the payload description.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PayloadKind = Literal[
    "p-dos-stuck", "p-dos-reset", "p-err-hi", "p-err-lo", "p-energy", "p-slowdown"
]


@dataclass(frozen=True)
class DosStuckPayload:
    """Force a chosen output or internal enable/reset net to a constant when triggered."""

    kind: Literal["p-dos-stuck"] = "p-dos-stuck"
    victim: str = ""
    stuck_value: int = 0

    def description(self) -> str:
        return f"force {self.victim or '<victim>'} to {self.stuck_value} when triggered"

    def effect_measure(self) -> str:
        return "functional-diff"


@dataclass(frozen=True)
class DosResetPayload:
    """Force the design's reset net active when triggered."""

    kind: Literal["p-dos-reset"] = "p-dos-reset"
    reset_net: str = ""

    def description(self) -> str:
        return f"force reset net {self.reset_net or '<reset>'} active when triggered"

    def effect_measure(self) -> str:
        return "functional-diff"


@dataclass(frozen=True)
class ErrHiPayload:
    """Flip (or force) the top b bits of a chosen output word when triggered."""

    kind: Literal["p-err-hi"] = "p-err-hi"
    word: str = ""
    bits: int = 1
    force: bool = False

    def description(self) -> str:
        action = "force" if self.force else "flip"
        return f"{action} top {self.bits} bit(s) of {self.word or '<word>'} when triggered"

    def effect_measure(self) -> str:
        return "functional-diff-bit-weighted"


@dataclass(frozen=True)
class ErrLoPayload:
    """Flip (or force) the bottom b bits of a chosen output word when triggered."""

    kind: Literal["p-err-lo"] = "p-err-lo"
    word: str = ""
    bits: int = 1
    force: bool = False

    def description(self) -> str:
        action = "force" if self.force else "flip"
        return f"{action} bottom {self.bits} bit(s) of {self.word or '<word>'} when triggered"

    def effect_measure(self) -> str:
        return "functional-diff-bit-weighted"


@dataclass(frozen=True)
class EnergyPayload:
    """An always-toggling bit chain, gated by the trigger, sized to a fraction f of the design."""

    kind: Literal["p-energy"] = "p-energy"
    fraction: float = 0.05

    def description(self) -> str:
        pct = f"{self.fraction:.0%}"
        return f"toggling ring sized to {pct} of the design's nodes, gated by the trigger"

    def effect_measure(self) -> str:
        return "toggle-count-delta"


@dataclass(frozen=True)
class SlowdownPayload:
    """A delay chain spliced onto a chosen near-critical net, sized to a fraction g of its depth."""

    kind: Literal["p-slowdown"] = "p-slowdown"
    victim: str = ""
    fraction: float = 0.1

    def description(self) -> str:
        pct = f"{self.fraction:.0%}"
        victim = self.victim or '<victim>'
        return f"delay chain adding {pct} logic-level depth on {victim}"

    def effect_measure(self) -> str:
        return "logic-level-depth-delta"


Payload = (
    DosStuckPayload
    | DosResetPayload
    | ErrHiPayload
    | ErrLoPayload
    | EnergyPayload
    | SlowdownPayload
)
