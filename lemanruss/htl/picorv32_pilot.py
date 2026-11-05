"""picorv32 smoke (rc1 Continuation 3, controller addition 2026-11-04: "Why can't we use
picorv32?" -- "Do picorv32's smoke ... before it joins the N=100 build"). Same shape as
`lemanruss.htl.proc_multi_pilot`'s `run_dark_multi_smoke`/`run_mcu_multi_smoke`: 1-3 independent
Trojans, each its own payload kind, FF/latch equality hard gate on the whole circuit, each
Trojan's own witness, and silence on a witness carrying no magic word at all.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from lemanruss.htl.bitsim import latches_of
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.proc_rareness import magic_match_probability
from lemanruss.htl.proc_release import lower_gates_as_names
from lemanruss.htl.proc_run import (
    PICO_UPSTREAM,
    patch_picorv32_kinded_multicore,
    prepare_picorv32,
    run_picorv32_once,
    traces_equal,
    write_pico_program,
)
from lemanruss.htl.rv32i import encode_addi, encode_nop, encode_self_loop, encode_srli, encode_sw

MARKER_ADDR = 0x100  # byte address; word index 64 of pico_tb.v's 256-word memory array
PICO_WITNESS_CYCLES = 60


def pico_witness_words(magic_words: list[int]) -> list[int]:
    """2 NOPs, `addi x5,x0,0x37` (a shift operand whose LSB is 1, so an LSB-flip payload is
    observable), every magic word in order, `srli x6,x5,1` (the ALU witness's own shift-right),
    `sw x6,0x100(x0)` (writes the shift result to the fixed marker address, observable in
    pico_tb.v's trace the same way mcu's PORTB/PORTD and darkriscv's OPORT witnesses are) and a
    self-loop. An empty `magic_words` is the neutral witness (no magic word anywhere in the
    instruction stream): the brief's "a witness carrying no magic word" case."""
    return (
        [encode_nop(), encode_nop(), encode_addi(5, 0, 0x37)]
        + list(magic_words)
        + [encode_srli(6, 5, 1), encode_sw(0, 6, MARKER_ADDR), encode_self_loop()]
    )


def ff_count(text: str) -> int:
    return len(latches_of(parse_single_model(text)))


@dataclass
class PicoMultiPilotResult:
    trojan_ids: list[str]
    kinds: list[str]
    magic_words: list[int]
    per_trojan_fires: dict[str, bool] = field(default_factory=dict)
    all_silent_on_no_witness: bool = False  # Odin III RTL + netlist (H-P1 amendment's own gate)
    silent_on_no_witness_iverilog: bool = False  # recorded, not gating (neutral witness, not
    # a shipped program; H-P1 amendment names iverilog only for shipped programs)
    ff_clean: int = 0
    ff_infected: int = 0
    ff_equal: bool = False
    p_match_per_trojan: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "base": "picorv32", "trojan_ids": self.trojan_ids, "kinds": self.kinds,
            "magic_words": [f"0x{w:08x}" for w in self.magic_words],
            "per_trojan_fires": self.per_trojan_fires,
            "all_silent_on_no_witness": self.all_silent_on_no_witness,
            "silent_on_no_witness_iverilog": self.silent_on_no_witness_iverilog,
            "ff_clean": self.ff_clean, "ff_infected": self.ff_infected,
            "ff_equal": self.ff_equal, "p_match_per_trojan": self.p_match_per_trojan,
            "error": self.error,
        }


def run_picorv32_multi_smoke(
    trojan_ids: list[str], magic_words: list[int], kinds: list[str], odin3_bin: Path, work: Path
) -> PicoMultiPilotResult:
    if len(trojan_ids) != len(magic_words) or len(trojan_ids) != len(kinds):
        raise ValueError("one trojan id and one kind per magic word")
    clean = work / "pico-multi-clean"
    inf = work / "pico-multi-infected"
    for d in (clean, inf):
        if d.exists():
            shutil.rmtree(d)
    files = prepare_picorv32(PICO_UPSTREAM, clean)
    prepare_picorv32(PICO_UPSTREAM, inf)
    patch_picorv32_kinded_multicore(inf, magic_words, kinds)

    clean_nl = work / "pico-multi-clean.nl.blif"
    inf_nl = work / "pico-multi-infected.nl.blif"
    lower_gates_as_names(odin3_bin, "picorv32", files, clean, clean_nl)
    lower_gates_as_names(odin3_bin, "picorv32", files, inf, inf_nl)
    ff_clean, ff_infected = ff_count(clean_nl.read_text()), ff_count(inf_nl.read_text())

    result = PicoMultiPilotResult(
        trojan_ids=trojan_ids, kinds=kinds, magic_words=magic_words,
        ff_clean=ff_clean, ff_infected=ff_infected, ff_equal=ff_clean == ff_infected,
        p_match_per_trojan=magic_match_probability(1),
    )
    if ff_clean != ff_infected:
        result.error = (
            f"FF/latch equality hard gate failed: clean={ff_clean} infected={ff_infected}")
        return result

    for tid, word in zip(trojan_ids, magic_words, strict=True):
        witness = pico_witness_words([word])
        write_pico_program(inf, witness)
        write_pico_program(clean, witness)
        clean_tr = run_picorv32_once(clean, files, odin3_bin, PICO_WITNESS_CYCLES, f"w-{tid}")
        inf_tr = run_picorv32_once(inf, files, odin3_bin, PICO_WITNESS_CYCLES, f"w-{tid}")
        result.per_trojan_fires[tid] = not traces_equal(clean_tr["ref"], inf_tr["ref"])

    neutral = pico_witness_words([])
    write_pico_program(inf, neutral)
    write_pico_program(clean, neutral)
    clean_tr = run_picorv32_once(clean, files, odin3_bin, PICO_WITNESS_CYCLES, "w-neutral")
    inf_tr = run_picorv32_once(inf, files, odin3_bin, PICO_WITNESS_CYCLES, "w-neutral")
    # H-P1 amendment (docs/specs/2026-11-03-seeker-proc-rc1.md section 0a): silence on a program
    # that is not shipped (the synthetic neutral witness, here) is judged by Odin III's own RTL
    # and netlist sims; iverilog's result is recorded for the record, not a gate.
    result.all_silent_on_no_witness = (
        traces_equal(clean_tr["rtl"], inf_tr["rtl"]) and traces_equal(clean_tr["nl"], inf_tr["nl"])
    )
    result.silent_on_no_witness_iverilog = traces_equal(clean_tr["ref"], inf_tr["ref"])
    return result


__all__ = ["PicoMultiPilotResult", "pico_witness_words", "run_picorv32_multi_smoke"]
