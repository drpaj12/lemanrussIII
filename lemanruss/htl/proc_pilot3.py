"""Seeker-Proc pilot3 (brief "ADDED 2026-11-02: Seeker-Proc too"): magic-word-only trojans on
mcu and darkriscv, FF/latch equality hard gate, package as seeker-proc-v2.0-pilot3.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from lemanruss.htl.bitsim import latches_of
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.dark_ram_blackbox import dark_odin_files
from lemanruss.htl.mcu_ram_blackbox import mcu_odin_files
from lemanruss.htl.proc_insert import insert_dark_trojan, insert_mcu_trojan
from lemanruss.htl.proc_pilot import run_dark_pilot, run_mcu_pilot
from lemanruss.htl.proc_release import (
    ProcCircuitSpec,
    lower_gates_as_names,
    package_proc_pilot2,
)
from lemanruss.htl.proc_run import (
    DARK_UPSTREAM,
    MCU_UPSTREAM,
    patch_dark_core,
    patch_mcu_core,
    prepare_dark,
    prepare_mcu,
)
from lemanruss.seedsrc import private_words

ODIN3_BIN = Path(os.environ.get("ODIN3_BIN", "odin3"))
WORK = Path(os.environ.get("PILOT3_WORK", "proc-pilot3"))
OUT = Path(os.environ.get("PILOT3_OUT", "seeker-proc-v2.0-pilot3"))
# Trigger words come from a private file (LEMANRUSS_PROC_MAGIC_FILE: {"mcu": [...], "dark": [...]}).
MCU_MAGIC = private_words("mcu") if os.environ.get("LEMANRUSS_PROC_MAGIC_FILE") else []
DARK_MAGIC = private_words("dark") if os.environ.get("LEMANRUSS_PROC_MAGIC_FILE") else []


def ff_count(text: str) -> int:
    return len(latches_of(parse_single_model(text)))


def mcu_witness_image(pilot_dir: Path, name: str = "blink") -> dict[str, bytes]:
    """The witness program image of an MCU pilot run: the four byte planes 0..3<name>.vmh
    that run_mcu_pilot wrote into its infected work dir (the program that fires the trigger;
    never a single <name>.vmh, which does not exist, and not the shipped program)."""
    return {f"{p}{name}.vmh": (pilot_dir / f"{p}{name}.vmh").read_bytes() for p in range(4)}


def dark_rtl_dir(build: Path) -> Path:
    """Where Odin III must run for darkriscv: `prepare_dark`'s file list is relative to
    `<build>/rtl` (running in `<build>` gave `missing_file: 'darksocv.v'`)."""
    return build / "rtl"


def build_mcu() -> tuple[ProcCircuitSpec, ProcCircuitSpec, dict[str, dict[str, object]]]:
    clean = WORK / "mcu-clean"
    inf = WORK / "mcu-infected"
    for d in (clean, inf):
        if d.exists():
            shutil.rmtree(d)
    files = prepare_mcu(MCU_UPSTREAM, clean, "blink")
    prepare_mcu(MCU_UPSTREAM, inf, "blink")
    patch_mcu_core(inf, MCU_MAGIC)

    clean_nl = WORK / "mcu-clean.nl.blif"
    inf_nl = WORK / "mcu-infected.nl.blif"
    mfiles = mcu_odin_files(files)
    lower_gates_as_names(ODIN3_BIN, "single_cycle_BRAM_top", mfiles, clean, clean_nl)
    lower_gates_as_names(ODIN3_BIN, "single_cycle_BRAM_top", mfiles, inf, inf_nl)
    clean_text, inf_text = clean_nl.read_text(), inf_nl.read_text()
    clean_ff, inf_ff = ff_count(clean_text), ff_count(inf_text)
    gate = {"base": "mcu", "clean_ff": clean_ff, "infected_ff": inf_ff, "equal": clean_ff == inf_ff}
    if clean_ff != inf_ff:
        raise AssertionError(f"mcu FF/latch equality hard gate failed: {gate}")

    pilot = run_mcu_pilot("proc-mcu-magicword-stall", MCU_MAGIC, ODIN3_BIN, WORK)
    patched_src = insert_mcu_trojan((clean / "single_cycle_core.v").read_text(), MCU_MAGIC)
    clean_spec = ProcCircuitSpec(
        trojan_id="proc-mcu-magicword-stall", base="mcu", role="clean", identity_text=clean_text)
    inf_spec = ProcCircuitSpec(
        trojan_id="proc-mcu-magicword-stall", base="mcu", role="infected",
        identity_text=inf_text, magic_words=MCU_MAGIC, trigger_kind="t-input-pattern",
        payload_kind="p-dos-stuck", patched_text=patched_src,
        patched_file="single_cycle_core.v",
        witness_image=mcu_witness_image(WORK / "proc-mcu-magicword-stall-infected"))
    rareness = {
        "proc-mcu-magicword-stall": {
            "base": "mcu", "magic_bits": pilot.magic_bits, "p_match": pilot.p_match,
            "scoap_cc0": pilot.scoap_cc0, "scoap_cc1": pilot.scoap_cc1, "scoap_co": pilot.scoap_co,
            "witness_fires": pilot.witness_fires,
            "rtl_equals_iverilog_clean": pilot.rtl_equals_iverilog_clean,
            "rtl_equals_iverilog_infected": pilot.rtl_equals_iverilog_infected,
            "rtl_equals_netlist_infected": pilot.rtl_equals_netlist_infected,
            "stealth": pilot.stealth, "dropped_for_firing": pilot.dropped_for_firing,
            "ff_gate": gate,
        }
    }
    return clean_spec, inf_spec, rareness


def build_dark() -> tuple[ProcCircuitSpec, ProcCircuitSpec, dict[str, dict[str, object]]]:
    clean = WORK / "dark-clean"
    inf = WORK / "dark-infected"
    for d in (clean, inf):
        if d.exists():
            shutil.rmtree(d)
    files = prepare_dark(DARK_UPSTREAM, clean)
    prepare_dark(DARK_UPSTREAM, inf)
    patch_dark_core(inf, DARK_MAGIC)

    clean_nl = WORK / "dark-clean.nl.blif"
    inf_nl = WORK / "dark-infected.nl.blif"
    odin_files = dark_odin_files(files)
    lower_gates_as_names(ODIN3_BIN, "darksocv", odin_files, dark_rtl_dir(clean), clean_nl)
    lower_gates_as_names(ODIN3_BIN, "darksocv", odin_files, dark_rtl_dir(inf), inf_nl)
    clean_text, inf_text = clean_nl.read_text(), inf_nl.read_text()
    clean_ff, inf_ff = ff_count(clean_text), ff_count(inf_text)
    gate = {"base": "darkriscv", "clean_ff": clean_ff, "infected_ff": inf_ff,
            "equal": clean_ff == inf_ff}
    if clean_ff != inf_ff:
        raise AssertionError(f"darkriscv FF/latch equality hard gate failed: {gate}")

    pilot = run_dark_pilot("proc-dark-magicword-reset", DARK_MAGIC, ODIN3_BIN, WORK)
    patched_src = insert_dark_trojan((clean / "rtl" / "darkriscv.v").read_text(), DARK_MAGIC)
    clean_spec = ProcCircuitSpec(
        trojan_id="proc-dark-magicword-reset", base="darkriscv", role="clean",
        identity_text=clean_text)
    inf_spec = ProcCircuitSpec(
        trojan_id="proc-dark-magicword-reset", base="darkriscv", role="infected",
        identity_text=inf_text, magic_words=DARK_MAGIC, trigger_kind="t-input-pattern",
        payload_kind="p-dos-reset", patched_text=patched_src,
        patched_file="rtl/darkriscv.v",
        witness_image={"darksocv.mem": (
            WORK / "proc-dark-magicword-reset-infected" / "src" / "darksocv.mem").read_bytes()})
    rareness = {
        "proc-dark-magicword-reset": {
            "base": "darkriscv", "magic_bits": pilot.magic_bits, "p_match": pilot.p_match,
            "scoap_cc0": pilot.scoap_cc0, "scoap_cc1": pilot.scoap_cc1, "scoap_co": pilot.scoap_co,
            "witness_fires": pilot.witness_fires,
            "rtl_equals_iverilog_clean": pilot.rtl_equals_iverilog_clean,
            "rtl_equals_iverilog_infected": pilot.rtl_equals_iverilog_infected,
            "rtl_equals_netlist_infected": pilot.rtl_equals_netlist_infected,
            "stealth": pilot.stealth, "dropped_for_firing": pilot.dropped_for_firing,
            "ff_gate": gate,
        }
    }
    return clean_spec, inf_spec, rareness


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    mcu_clean, mcu_inf, mcu_rareness = build_mcu()
    dark_clean, dark_inf, dark_rareness = build_dark()
    rareness = {**mcu_rareness, **dark_rareness}
    specs = [mcu_clean, mcu_inf, dark_clean, dark_inf]
    if OUT.exists():
        shutil.rmtree(OUT)
    info = package_proc_pilot2(specs, OUT, rareness, {}, seed=0,
                                release_name="seeker-proc-v2.0-pilot3")
    (WORK / "pilot3_rareness.json").write_text(json.dumps(rareness, indent=1), encoding="utf-8")
    print(json.dumps(info, indent=1))
    print(json.dumps(rareness, indent=1))


if __name__ == "__main__":
    main()
