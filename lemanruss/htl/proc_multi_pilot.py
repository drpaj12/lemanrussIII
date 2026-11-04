"""Seeker-Proc rc1 multi-Trojan smoke (spec `docs/specs/2026-11-03-seeker-proc-rc1.md` section 8,
"Smoke build"): 1 to 3 independent magic-word Trojans on one base (darkriscv first: smaller
netlist, 67638 FFs in pilot3 vs mcu's 132446), proving per default 2 (Peter 2026-11-03: "1 to 3
payllods per core") that each Trojan has its own witness and the FF/latch equality hard gate
holds across the whole multi-Trojan circuit, not just per Trojan. Same payload point per core as
pilot3 (one payload kind; a second is an open question, spec section 7). Reuses `proc_pilot.
dark_witness_words` with a single-element list per witness: feeding only Trojan j's own magic
word into the instruction stream exercises `__htl_trigger_j` alone (the others' comparators never
see their word), so no new witness generator is needed for the independent-trigger case.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from lemanruss.htl.bitsim import latches_of
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.dark_ram_blackbox import dark_odin_files
from lemanruss.htl.mcu_ram_blackbox import mcu_odin_files
from lemanruss.htl.proc_images import write_dark_mem, write_mcu_vmh
from lemanruss.htl.proc_pilot import (
    DARK_WITNESS_CYCLES,
    MCU_WITNESS_CYCLES,
    dark_witness_words,
    mcu_witness_words,
)
from lemanruss.htl.proc_rareness import magic_match_probability
from lemanruss.htl.proc_release import lower_gates_as_names
from lemanruss.htl.proc_run import (
    DARK_UPSTREAM,
    MCU_UPSTREAM,
    patch_dark_multicore,
    patch_mcu_multicore,
    prepare_dark,
    prepare_mcu,
    run_dark_once,
    run_mcu_once,
    traces_equal,
)


def ff_count(text: str) -> int:
    return len(latches_of(parse_single_model(text)))


@dataclass
class MultiPilotResult:
    trojan_ids: list[str]
    base: str
    magic_words: list[int]
    per_trojan_fires: dict[str, bool] = field(default_factory=dict)
    all_silent_on_no_witness: bool = False
    ff_clean: int = 0
    ff_infected: int = 0
    ff_equal: bool = False
    p_match_per_trojan: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "trojan_ids": self.trojan_ids,
            "base": self.base,
            "magic_words": [f"0x{w:08x}" for w in self.magic_words],
            "per_trojan_fires": self.per_trojan_fires,
            "all_silent_on_no_witness": self.all_silent_on_no_witness,
            "ff_clean": self.ff_clean,
            "ff_infected": self.ff_infected,
            "ff_equal": self.ff_equal,
            "p_match_per_trojan": self.p_match_per_trojan,
        }


def run_dark_multi_smoke(
    trojan_ids: list[str], magic_words: list[int], odin3_bin: Path, work: Path
) -> MultiPilotResult:
    if len(trojan_ids) != len(magic_words):
        raise ValueError("one trojan id per magic word")
    clean = work / "dark-multi-clean"
    inf = work / "dark-multi-infected"
    for d in (clean, inf):
        if d.exists():
            shutil.rmtree(d)
    files = prepare_dark(DARK_UPSTREAM, clean)
    prepare_dark(DARK_UPSTREAM, inf)
    patch_dark_multicore(inf, magic_words)

    # FF/latch equality hard gate, whole circuit (section 2 of the rc1 spec: checked after every
    # Trojan is added, not just per Trojan).
    clean_nl = work / "dark-multi-clean.nl.blif"
    inf_nl = work / "dark-multi-infected.nl.blif"
    odin_files = dark_odin_files(files)
    lower_gates_as_names(odin3_bin, "darksocv", odin_files, clean / "rtl", clean_nl)
    lower_gates_as_names(odin3_bin, "darksocv", odin_files, inf / "rtl", inf_nl)
    ff_clean, ff_infected = ff_count(clean_nl.read_text()), ff_count(inf_nl.read_text())

    result = MultiPilotResult(
        trojan_ids=trojan_ids, base="darkriscv", magic_words=magic_words,
        ff_clean=ff_clean, ff_infected=ff_infected, ff_equal=ff_clean == ff_infected,
        p_match_per_trojan=magic_match_probability(1),
    )
    if ff_clean != ff_infected:
        raise AssertionError(
            f"darkriscv multi-Trojan FF/latch equality hard gate failed: "
            f"clean={ff_clean} infected={ff_infected}")

    # Each Trojan's own witness: feed only its magic word, check the trace differs from clean.
    for tid, word in zip(trojan_ids, magic_words, strict=True):
        witness = dark_witness_words([word])
        write_dark_mem(witness, inf / "src" / "darksocv.mem")
        write_dark_mem(witness, inf / "iv" / "src" / "darksocv.mem")
        write_dark_mem(witness, clean / "src" / "darksocv.mem")
        write_dark_mem(witness, clean / "iv" / "src" / "darksocv.mem")
        clean_tr = run_dark_once(clean, files, odin3_bin, DARK_WITNESS_CYCLES, f"w-{tid}")
        inf_tr = run_dark_once(inf, files, odin3_bin, DARK_WITNESS_CYCLES, f"w-{tid}")
        result.per_trojan_fires[tid] = not traces_equal(clean_tr["ref"], inf_tr["ref"])

    # None of the Trojans' words: a witness with neither magic word must be silent (the shipped-
    # program stand-in for this smoke; the full build's own shipped-program gate is separate).
    neutral = dark_witness_words([0x00000013])  # addi x0,x0,0 (NOP-equivalent, not a magic word)
    write_dark_mem(neutral, inf / "src" / "darksocv.mem")
    write_dark_mem(neutral, inf / "iv" / "src" / "darksocv.mem")
    write_dark_mem(neutral, clean / "src" / "darksocv.mem")
    write_dark_mem(neutral, clean / "iv" / "src" / "darksocv.mem")
    clean_tr = run_dark_once(clean, files, odin3_bin, DARK_WITNESS_CYCLES, "w-neutral")
    inf_tr = run_dark_once(inf, files, odin3_bin, DARK_WITNESS_CYCLES, "w-neutral")
    result.all_silent_on_no_witness = traces_equal(clean_tr["ref"], inf_tr["ref"])
    return result


def run_mcu_multi_smoke(
    trojan_ids: list[str], magic_words: list[int], odin3_bin: Path, work: Path
) -> MultiPilotResult:
    """mcu's own multi-Trojan smoke (brief Continuation 2026-11-04 step 3), same shape as
    `run_dark_multi_smoke`: mcu's trigger is unaffected by the darkriscv rc1 net change (mcu
    already samples `instruction`, never gated, so there is nothing to move here)."""
    if len(trojan_ids) != len(magic_words):
        raise ValueError("one trojan id per magic word")
    clean = work / "mcu-multi-clean"
    inf = work / "mcu-multi-infected"
    for d in (clean, inf):
        if d.exists():
            shutil.rmtree(d)
    files = prepare_mcu(MCU_UPSTREAM, clean, "blink")
    prepare_mcu(MCU_UPSTREAM, inf, "blink")
    patch_mcu_multicore(inf, magic_words)

    clean_nl = work / "mcu-multi-clean.nl.blif"
    inf_nl = work / "mcu-multi-infected.nl.blif"
    mfiles = mcu_odin_files(files)
    lower_gates_as_names(odin3_bin, "single_cycle_BRAM_top", mfiles, clean, clean_nl)
    lower_gates_as_names(odin3_bin, "single_cycle_BRAM_top", mfiles, inf, inf_nl)
    ff_clean, ff_infected = ff_count(clean_nl.read_text()), ff_count(inf_nl.read_text())

    result = MultiPilotResult(
        trojan_ids=trojan_ids, base="mcu", magic_words=magic_words,
        ff_clean=ff_clean, ff_infected=ff_infected, ff_equal=ff_clean == ff_infected,
        p_match_per_trojan=magic_match_probability(1),
    )
    if ff_clean != ff_infected:
        raise AssertionError(
            f"mcu multi-Trojan FF/latch equality hard gate failed: "
            f"clean={ff_clean} infected={ff_infected}")

    for tid, word in zip(trojan_ids, magic_words, strict=True):
        witness = mcu_witness_words([word])
        for d in (clean, inf):
            write_mcu_vmh(witness, d, "blink")
            write_mcu_vmh(witness, d / "iv", "blink")
        clean_tr = run_mcu_once(clean, files, odin3_bin, MCU_WITNESS_CYCLES, f"w-{tid}")
        inf_tr = run_mcu_once(inf, files, odin3_bin, MCU_WITNESS_CYCLES, f"w-{tid}")
        result.per_trojan_fires[tid] = not traces_equal(clean_tr["ref"], inf_tr["ref"])

    neutral = mcu_witness_words([0x00000013])  # addi x0,x0,0 (NOP-equivalent, not a magic word)
    for d in (clean, inf):
        write_mcu_vmh(neutral, d, "blink")
        write_mcu_vmh(neutral, d / "iv", "blink")
    clean_tr = run_mcu_once(clean, files, odin3_bin, MCU_WITNESS_CYCLES, "w-neutral")
    inf_tr = run_mcu_once(inf, files, odin3_bin, MCU_WITNESS_CYCLES, "w-neutral")
    result.all_silent_on_no_witness = traces_equal(clean_tr["ref"], inf_tr["ref"])
    return result


__all__ = ["MultiPilotResult", "run_dark_multi_smoke", "run_mcu_multi_smoke"]
