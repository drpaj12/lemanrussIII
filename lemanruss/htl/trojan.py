"""Trojan composition: trigger x payload x insertion site x level.

Spec: docs/specs/2026-10-31-htl-design.md section 2. A Trojan here is a description only (id,
trigger, payload, level, a free-text site note); building it into a real design is
lemanruss.htl.insert's job, scoring it is lemanruss.htl.verify's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lemanruss.htl.payloads import Payload
from lemanruss.htl.triggers import AlwaysOnTrigger, Trigger

Level = Literal["hdl", "netlist"]

# Payloads that need no activation gate at all are legal only with t-always-on (spec section 2:
# "t-always-on (for the delay and power payloads)"); every other payload needs a real trigger.
ALWAYS_ON_ONLY_PAYLOADS = frozenset({"p-energy", "p-slowdown"})


class IllegalCombination(ValueError):
    """Raised by Trojan.compose for a trigger x payload pairing the spec rules out."""


@dataclass(frozen=True)
class Trojan:
    trigger: Trigger
    payload: Payload
    level: Level
    site: str = ""

    @property
    def id(self) -> str:
        return f"{self.trigger.kind}__{self.payload.kind}__{self.level}"

    def description(self) -> str:
        return f"{self.trigger.description()}; {self.payload.description()}"

    def stealth_note(self) -> str:
        return self.trigger.stealth_note()

    def effect_measure(self) -> str:
        return self.payload.effect_measure()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": 1,
            "id": self.id,
            "trigger": {
                "kind": self.trigger.kind,
                "description": self.trigger.description(),
                "stealth_note": self.trigger.stealth_note(),
            },
            "payload": {
                "kind": self.payload.kind,
                "description": self.payload.description(),
                "effect_measure": self.payload.effect_measure(),
            },
            "level": self.level,
            "site": self.site,
        }


def compose(trigger: Trigger, payload: Payload, level: Level, site: str = "") -> Trojan:
    """Builds a Trojan, refusing a trigger/payload pairing the spec rules out.

    p-energy and p-slowdown are legal with any trigger (spec: "always-on, or switched by the
    trigger" for p-slowdown; p-energy likewise may be trigger-gated); every other payload needs a
    trigger that is not t-always-on, since an always-active functional payload (stuck output,
    forced reset, bit error) would not be a Trojan at all -- it would just be a broken design.
    """
    if isinstance(trigger, AlwaysOnTrigger) and payload.kind not in ALWAYS_ON_ONLY_PAYLOADS:
        raise IllegalCombination(
            f"{payload.kind} needs a real activation condition, not t-always-on "
            "(spec section 2: always-on is only for the delay and energy payloads)"
        )
    return Trojan(trigger=trigger, payload=payload, level=level, site=site)
