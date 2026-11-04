"""Round 7 rareness measures (spec section 12, brief item 2): per Trojan, (i) P(fire) over the
shipped programs (expected 0, else dropped and listed), (ii) the magic-word/sequence match
probability, (iii) SCOAP CC/CO of the trigger net, (iv) P(fire within N cycles) for counter
triggers (not defined for magic-word/sequence: this pilot has none).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_CNAME = re.compile(r"\.cname __htl_trigger\.\w+")
_SUBCKT_Y = re.compile(r"\bY=(\S+)")
_NAMES_LINE = re.compile(r"^\.names\b.*\s(\S+)\s*$")
_MODEL = re.compile(r"^\.model\s+(\S+)")


def find_trigger_net(blif_text: str) -> tuple[str, str]:
    """The `(module, net)` carrying the inserted comparator's final value in a written BLIF.

    Odin III's `write_blif` tags every primitive cell it builds for the Verilog assignment to
    wire `__htl_trigger` with a `.cname __htl_trigger.<op><index>` (one per XOR/OR/NOT/AND
    stage of the comparator); the *last* such tag in the file is always the top-level operation
    (the one whose output is the wire's final value), since Odin emits an assignment's
    sub-expressions before the operation that combines them. Checked against two shapes: a
    single magic word lowers to NOT(OR(XOR bits)) (no trailing AND, mcu); a gated magic word
    (darkriscv's `IDACK && (...)`) lowers to one more AND on top, so the last cname is `.and0`.

    BLIF net names are local to their `.model` block, so a design with many modules can reuse
    the same `$nNNN` name in an unrelated module (observed: mcu's `single_cycle_BRAM_top` top
    module happened to also hold an unrelated net named the same as the trigger's own net inside
    the `single_cycle_core` instance); the owning module is the nearest `.model` line before the
    match, since BLIF model bodies are contiguous between `.model` and `.end`.
    """
    lines = blif_text.splitlines()
    last_idx = None
    for i, ln in enumerate(lines):
        if _CNAME.search(ln):
            last_idx = i
    if last_idx is None:
        raise ValueError("find_trigger_net: no __htl_trigger .cname found")
    prev = lines[last_idx - 1]
    net = None
    m = _SUBCKT_Y.search(prev)
    if m:
        net = m.group(1)
    else:
        m2 = _NAMES_LINE.match(prev)
        if m2:
            net = m2.group(1)
    if net is None:
        raise ValueError(f"find_trigger_net: cannot read the net from: {prev!r}")
    module = None
    for ln in reversed(lines[:last_idx]):
        mm = _MODEL.match(ln)
        if mm:
            module = mm.group(1)
            break
    if module is None:
        raise ValueError("find_trigger_net: no enclosing .model found")
    return module, net


@dataclass
class ProcRareness:
    trojan_id: str
    base: str
    magic_bits: int  # 32 * number of magic words
    p_match: float  # 2 ** -magic_bits: probability a uniformly random word sequence matches
    trigger_net: str
    cc0: int | None
    cc1: int | None
    co: int | None
    shipped_p_fire: dict[str, float]  # program -> measured P(fire) (expected 0.0 for all)
    dropped_for_firing: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "trojan_id": self.trojan_id,
            "base": self.base,
            "magic_bits": self.magic_bits,
            "p_match": self.p_match,
            "trigger_net": self.trigger_net,
            "scoap_cc0": self.cc0,
            "scoap_cc1": self.cc1,
            "scoap_co": self.co,
            "shipped_p_fire": self.shipped_p_fire,
            "dropped_for_firing": self.dropped_for_firing,
        }


def magic_match_probability(n_words: int) -> float:
    """P(a uniformly random 32-bit value, or n_words of them in order, matches): 2**-(32*n)."""
    return 2.0 ** -(32 * n_words)


def scoap_of_trigger(
    blif_path: Path, top: str, net: str
) -> tuple[int | None, int | None, int | None]:
    """CC0, CC1, CO of `net` in module `top`, from Odin III's `scoap` pass (spec section 12 item
    (iii); schema `odin3-scoap` v2, docs/user/scoap.md: `modules` is a list, each module's `nets`
    a list of `{id, name, cc0, cc1, co}`; `inf` (1e18) marks "unreachable", not a measurement)."""
    from odin3 import Design

    with Design() as design:
        design.run_pass("read_blif", str(blif_path))
        result = design.scoap()
    inf = int(result["inf"])
    modules = result["modules"]
    assert isinstance(modules, list)
    for mod in modules:
        if mod["name"] != top:
            continue
        for rec in mod["nets"]:
            if rec["name"] == net:
                return (
                    _clean(rec["cc0"], inf),
                    _clean(rec["cc1"], inf),
                    _clean(rec["co"], inf),
                )
    return None, None, None


def _clean(value: object, inf: int) -> int | None:
    assert isinstance(value, int)
    return None if value >= inf else value
