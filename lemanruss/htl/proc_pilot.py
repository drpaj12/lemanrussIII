"""Round 7 (Seeker-Proc pilot) end-to-end driver: one base x one trigger -> a `PilotResult` with
every measure the brief and spec section 12 ask for (fire, agreement, stealth, rareness). Ties
together proc_run (build/sim), proc_rareness (SCOAP/probability) and proc_insert/proc_images
(the Trojan itself and its witness program). No equivalence check here -- the ABC `dsec`/`cec`
runs on these designs take minutes to unproven hours (the BRAM/RAM arrays `lower` without a
target architecture into tens of thousands of per-bit latches); it is driven separately with an
explicit timeout and recorded by hand in docs/results-round7.md (spec section 4(c): "state the
timeout" for the big case).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from lemanruss.htl.proc_images import write_dark_mem, write_mcu_vmh
from lemanruss.htl.proc_insert import insert_dark_trojan, insert_mcu_trojan
from lemanruss.htl.proc_rareness import (
    find_trigger_net,
    magic_match_probability,
    scoap_of_trigger,
)
from lemanruss.htl.proc_run import (
    DARK_TESTS_DIR,
    DARK_UPSTREAM,
    MCU_TESTS_DIR,
    MCU_UPSTREAM,
    prepare_dark,
    prepare_mcu,
    run_dark_once,
    run_mcu_iverilog_only,
    run_mcu_once,
    traces_agree,
    traces_equal,
)
from lemanruss.htl.rv32i import encode_addi, encode_lui, encode_nop, encode_self_loop, encode_sw

MCU_SHIPPED = ("blink", "blink_interrupt", "blink_function_call", "interrupt")
MCU_CYCLES = 2000
MCU_WITNESS_CYCLES = 30
DARK_WITNESS_CYCLES = 500


def mcu_witness_words(magic_words: list[int]) -> list[int]:
    """4 NOPs, then every magic word in order, then a self-loop (so a magic-sequence trigger of
    k words is exercised in full before the program stops making progress on its own)."""
    return [encode_nop()] * 4 + list(magic_words) + [encode_self_loop()]


def dark_witness_words(magic_words: list[int]) -> list[int]:
    """2 NOPs, `lui x6,0x40000` + `addi x5,x0,0x2a` (OPORT base address and a marker value,
    darklibc/include/io.h offset 0x18, darklibc/io.c base 0x40000000), every magic word in
    order, `sw x5,0x18(x6)` (writes the marker to OPORT, observable in dark_tb.v's trace) and a
    self-loop. The clean run writes the marker; the Trojan is expected to stop that."""
    return (
        [encode_nop(), encode_nop(), encode_lui(6, 0x40000), encode_addi(5, 0, 0x2A)]
        + list(magic_words)
        + [encode_sw(6, 5, 0x18), encode_self_loop()]
    )


@dataclass
class PilotResult:
    trojan_id: str
    base: str
    magic_words: list[int]
    witness_fires: bool  # True: infected witness trace differs from clean witness trace
    rtl_equals_iverilog_clean: bool
    rtl_equals_iverilog_infected: bool
    rtl_equals_netlist_infected: bool
    stealth: dict[str, bool] = field(default_factory=dict)
    dropped_for_firing: list[str] = field(default_factory=list)
    magic_bits: int = 0
    p_match: float = 0.0
    trigger_module: str = ""
    trigger_net: str = ""
    scoap_cc0: int | None = None
    scoap_cc1: int | None = None
    scoap_co: int | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "trojan_id": self.trojan_id,
            "base": self.base,
            "magic_words": [f"0x{w:08x}" for w in self.magic_words],
            "witness_fires": self.witness_fires,
            "rtl_equals_iverilog_clean": self.rtl_equals_iverilog_clean,
            "rtl_equals_iverilog_infected": self.rtl_equals_iverilog_infected,
            "rtl_equals_netlist_infected": self.rtl_equals_netlist_infected,
            "stealth": self.stealth,
            "dropped_for_firing": self.dropped_for_firing,
            "magic_bits": self.magic_bits,
            "p_match": self.p_match,
            "trigger_module": self.trigger_module,
            "trigger_net": self.trigger_net,
            "scoap_cc0": self.scoap_cc0,
            "scoap_cc1": self.scoap_cc1,
            "scoap_co": self.scoap_co,
            "notes": self.notes,
        }


def run_mcu_pilot(
    trojan_id: str, magic_words: list[int], odin3_bin: Path, work: Path
) -> PilotResult:
    clean = work / f"{trojan_id}-clean"
    inf = work / f"{trojan_id}-infected"
    shutil.rmtree(clean, ignore_errors=False) if clean.exists() else None
    shutil.rmtree(inf, ignore_errors=False) if inf.exists() else None
    files = prepare_mcu(MCU_UPSTREAM, clean, "blink")
    prepare_mcu(MCU_UPSTREAM, inf, "blink")

    witness = mcu_witness_words(magic_words)
    for d in (clean, inf):
        write_mcu_vmh(witness, d, "blink")
        write_mcu_vmh(witness, d / "iv", "blink")
    for rel in ("single_cycle_core.v", "iv/single_cycle_core.v"):
        p = inf / rel
        p.write_text(insert_mcu_trojan(p.read_text(), magic_words))

    clean_tr = run_mcu_once(clean, files, odin3_bin, MCU_WITNESS_CYCLES, "w")
    inf_tr = run_mcu_once(inf, files, odin3_bin, MCU_WITNESS_CYCLES, "w")

    result = PilotResult(
        trojan_id=trojan_id,
        base="mcu",
        magic_words=magic_words,
        witness_fires=not traces_equal(clean_tr["ref"], inf_tr["ref"]),
        rtl_equals_iverilog_clean=traces_agree(clean_tr["ref"], clean_tr["rtl"]),
        rtl_equals_iverilog_infected=traces_agree(inf_tr["ref"], inf_tr["rtl"]),
        rtl_equals_netlist_infected=traces_equal(inf_tr["rtl"], inf_tr["nl"]),
        magic_bits=32 * len(magic_words),
        p_match=magic_match_probability(len(magic_words)),
    )

    nl_path = inf / "w.nl.blif"
    module, net = find_trigger_net(nl_path.read_text())
    result.trigger_module, result.trigger_net = module, net
    result.scoap_cc0, result.scoap_cc1, result.scoap_co = scoap_of_trigger(nl_path, module, net)

    for prog in MCU_SHIPPED:
        s_clean = work / f"{trojan_id}-stealth-{prog}-clean"
        s_inf = work / f"{trojan_id}-stealth-{prog}-infected"
        files2 = prepare_mcu(MCU_UPSTREAM, s_clean, prog)
        prepare_mcu(MCU_UPSTREAM, s_inf, prog)
        for rel in ("single_cycle_core.v", "iv/single_cycle_core.v"):
            p = s_inf / rel
            p.write_text(insert_mcu_trojan(p.read_text(), magic_words))
        try:
            c_ref = run_mcu_once(s_clean, files2, odin3_bin, MCU_CYCLES, "s")["ref"]
            i_ref = run_mcu_once(s_inf, files2, odin3_bin, MCU_CYCLES, "s")["ref"]
        except RuntimeError as exc:
            # Defensive fallback (see proc_run.run_mcu_iverilog_only's docstring): sim_tb refused
            # a derived clock. The one case seen this round (prepare_mcu's derived-clock patch
            # missing, fixed in proc_run) no longer reaches here; kept for any other such gap.
            result.notes.append(f"{prog}: Odin III sim_tb refused, iverilog-only fallback ({exc})")
            c_ref = run_mcu_iverilog_only(s_clean, files2, MCU_CYCLES, "s")
            i_ref = run_mcu_iverilog_only(s_inf, files2, MCU_CYCLES, "s")
        ok = traces_equal(c_ref, i_ref)
        result.stealth[prog] = ok
        if not ok:
            result.dropped_for_firing.append(prog)
    return result


def run_dark_pilot(
    trojan_id: str, magic_words: list[int], odin3_bin: Path, work: Path
) -> PilotResult:
    clean = work / f"{trojan_id}-clean"
    inf = work / f"{trojan_id}-infected"
    shutil.rmtree(clean, ignore_errors=False) if clean.exists() else None
    shutil.rmtree(inf, ignore_errors=False) if inf.exists() else None
    files = prepare_dark(DARK_UPSTREAM, clean)
    prepare_dark(DARK_UPSTREAM, inf)

    witness = dark_witness_words(magic_words)
    for d in (clean, inf):
        write_dark_mem(witness, d / "src" / "darksocv.mem")
        write_dark_mem(witness, d / "iv" / "src" / "darksocv.mem")
    for rel in ("rtl/darkriscv.v", "iv/rtl/darkriscv.v"):
        p = inf / rel
        p.write_text(insert_dark_trojan(p.read_text(), magic_words))

    clean_tr = run_dark_once(clean, files, odin3_bin, DARK_WITNESS_CYCLES, "w")
    inf_tr = run_dark_once(inf, files, odin3_bin, DARK_WITNESS_CYCLES, "w")

    result = PilotResult(
        trojan_id=trojan_id,
        base="darkriscv",
        magic_words=magic_words,
        witness_fires=not traces_equal(clean_tr["ref"], inf_tr["ref"]),
        rtl_equals_iverilog_clean=traces_agree(clean_tr["ref"], clean_tr["rtl"]),
        rtl_equals_iverilog_infected=traces_agree(inf_tr["ref"], inf_tr["rtl"]),
        rtl_equals_netlist_infected=traces_equal(inf_tr["rtl"], inf_tr["nl"]),
        magic_bits=32 * len(magic_words),
        p_match=magic_match_probability(len(magic_words)),
    )

    nl_path = inf / "w.nl.blif"
    module, net = find_trigger_net(nl_path.read_text())
    result.trigger_module, result.trigger_net = module, net
    result.scoap_cc0, result.scoap_cc1, result.scoap_co = scoap_of_trigger(nl_path, module, net)

    s_clean = work / f"{trojan_id}-stealth-firmware-clean"
    s_inf = work / f"{trojan_id}-stealth-firmware-infected"
    files2 = prepare_dark(DARK_UPSTREAM, s_clean)
    prepare_dark(DARK_UPSTREAM, s_inf)
    for rel in ("rtl/darkriscv.v", "iv/rtl/darkriscv.v"):
        p = s_inf / rel
        p.write_text(insert_dark_trojan(p.read_text(), magic_words))
    c_tr = run_dark_once(s_clean, files2, odin3_bin, 4000, "s")
    i_tr = run_dark_once(s_inf, files2, odin3_bin, 4000, "s")
    ok = traces_equal(c_tr["ref"], i_tr["ref"])
    result.stealth["prebuilt-firmware"] = ok
    if not ok:
        result.dropped_for_firing.append("prebuilt-firmware")
    return result


__all__ = ["PilotResult", "run_mcu_pilot", "run_dark_pilot", "MCU_TESTS_DIR", "DARK_TESTS_DIR"]
