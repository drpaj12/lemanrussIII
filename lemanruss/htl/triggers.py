"""Trigger mechanisms for the Hardware Trojan Library (HTL).

Spec: docs/specs/2026-10-31-htl-design.md section 2. Each trigger is a small, serialisable
description of *when* a Trojan fires; the actual logic (BLIF text / Verilog text) is built by
lemanruss.htl.insert, not here, so the same trigger description drives both the HDL and the
netlist inserter and both testbench generators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TriggerKind = Literal[
    "t-comb-rare", "t-seq-counter", "t-seq-pattern", "t-always-on", "t-input-pattern",
    "t-state-pattern",
]


@dataclass(frozen=True)
class CombRareTrigger:
    """AND of `k` rare-valued internal nets, each at its rare polarity.

    `nets` holds (net_name, rare_value) pairs chosen by site selection (lemanruss.htl.sites); it
    is empty until a selector binds it to a real design.
    """

    kind: Literal["t-comb-rare"] = "t-comb-rare"
    k: int = 4
    nets: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    def description(self) -> str:
        return f"AND of {self.k} rare-valued nets"

    def stealth_note(self) -> str:
        return (
            "fires only when all k rare conditions coincide; rare under random "
            "vectors by construction"
        )


@dataclass(frozen=True)
class SeqCounterTrigger:
    """Time-bomb: an internal counter fires once it has seen N occurrences of a rare condition."""

    kind: Literal["t-seq-counter"] = "t-seq-counter"
    n: int = 8192
    condition_k: int = 2
    nets: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    def description(self) -> str:
        return f"counter fires after {self.n} occurrences of a {self.condition_k}-net rare AND"

    def stealth_note(self) -> str:
        return "needs a long run to activate; a short stealth-check run almost never reaches N"


@dataclass(frozen=True)
class SeqPatternTrigger:
    """FSM that fires after a fixed in-order sequence of k rare-condition cycles."""

    kind: Literal["t-seq-pattern"] = "t-seq-pattern"
    k: int = 4
    steps: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    def description(self) -> str:
        return f"FSM fires after an in-order sequence of {self.k} rare-condition steps"

    def stealth_note(self) -> str:
        return "order matters, not just occurrence; harder to hit by uncorrelated random vectors"


@dataclass(frozen=True)
class AlwaysOnTrigger:
    """Constant-1 trigger; only legal with payloads that must be continuously present."""

    kind: Literal["t-always-on"] = "t-always-on"

    def description(self) -> str:
        return "always active (no trigger logic)"

    def stealth_note(self) -> str:
        return "no activation condition to hide; stealth comes from the payload's effect size only"


@dataclass(frozen=True)
class InputPatternTrigger:
    """A magic value on a chosen group of input bits."""

    kind: Literal["t-input-pattern"] = "t-input-pattern"
    bits: tuple[str, ...] = field(default_factory=tuple)
    magic_value: int = 0

    def description(self) -> str:
        width = len(self.bits)
        return f"input pattern 0x{self.magic_value:x} on {width} bits"

    def stealth_note(self) -> str:
        return (
            "a single specific input word; activation probability is 2**-width "
            "under random vectors"
        )


@dataclass(frozen=True)
class StatePatternTrigger:
    """AND of `k` literals over EXISTING host signals: register (flip-flop) Q outputs and/or
    primary inputs, each at a chosen value. Same shape as `CombRareTrigger` (a combinational AND
    SOP, zero added flip-flops/latches), but drawn from host state and inputs rather than
    combinational-internal nets -- round 9 (rc7), spec section 13.1: "then we don't have to
    worry about the FF hiding" (Peter 2026-11-02). Distinct `kind` keeps it separate from
    `t-comb-rare` and the stateful `t-seq-counter`/`t-seq-pattern` in every report and label.
    """

    kind: Literal["t-state-pattern"] = "t-state-pattern"
    k: int = 4
    nets: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    def description(self) -> str:
        return f"AND of {self.k} rare-valued register/input bits (magic-number trigger)"

    def stealth_note(self) -> str:
        return (
            "fires only when all k existing-signal conditions coincide; adds no flip-flop or "
            "latch of its own, so flip-flop count carries no label signal"
        )


Trigger = (
    CombRareTrigger
    | SeqCounterTrigger
    | SeqPatternTrigger
    | AlwaysOnTrigger
    | InputPatternTrigger
    | StatePatternTrigger
)
