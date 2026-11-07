"""Seeker-Proc rc1 full-build orchestration (rc1 Continuation 3, 2026-11-04): one logical circuit
(a base + a clean/infected Trojan draw) built once at the RTL/gate level (FF equality, each
Trojan's own witness, H-P1-amended silence), then mapped to all three release forms (gates, lut4,
lut6) via `lemanruss.htl.obfuscate.obfuscate` (the same ABC-script-per-circuit variety n200/Comb-
Seq already use), giving the per-circuit synthesis variety spec section 4 asks for even with only
a handful of real bases. Peter's standing rule (every pass goes smaller to bigger, size can be a
stop condition): bases run smallest-FF-first -- mcu 1310, then picorv32 1615, then darkriscv
2034 (black-boxed-RAM FF counts, docs/results-round10.md section 4.1 and results-round11.md
section 3) -- and within a base, circuits build in ascending slot order (`build_n_circuits`'s own
loop). A circuit that hits a time/memory limit is recorded with where it stopped (`BuiltCircuit.
error`) and the pass continues to the next circuit, never aborting the whole batch.

Scope note (controller-facing, not silently dropped): this module makes the full build possible
at any N; the N actually run under heavy-run this round, and why, is in results-round11.md
section 3 -- this module itself does not hard-code N=100.
"""

from __future__ import annotations

import random
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from lemanruss.htl import mips16
from lemanruss.htl.bitsim import latches_of
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.dark_ram_blackbox import dark_odin_files
from lemanruss.htl.mcu_ram_blackbox import mcu_odin_files
from lemanruss.htl.obfuscate import obfuscate_traced
from lemanruss.htl.picorv32_pilot import PICO_WITNESS_CYCLES, pico_witness_words
from lemanruss.htl.proc_gate import gate_problems, structural_problems
from lemanruss.htl.proc_insert import (
    insert_dark_kinded_multitrojan,
    insert_mcu_kinded_multitrojan,
    insert_picorv32_kinded_multitrojan,
)
from lemanruss.htl.proc_pilot import (
    DARK_WITNESS_CYCLES,
    MCU_CYCLES,
    MCU_SHIPPED,
    MCU_WITNESS_CYCLES,
    dark_witness_words,
    mcu_witness_words,
)
from lemanruss.htl.proc_rareness import magic_match_probability
from lemanruss.htl.proc_release import lower_gates_as_names
from lemanruss.htl.proc_run import (
    DARK_UPSTREAM,
    MCU_UPSTREAM,
    PICO_UPSTREAM,
    prepare_dark,
    prepare_mcu,
    prepare_picorv32,
    run_dark_once,
    run_mcu_once,
    run_picorv32_once,
    traces_equal,
    write_dark_program,
    write_mcu_program,
    write_pico_program,
)
from lemanruss.htl.proc_witness import (
    alu_magic_word,
    alu_witness_words,
    forbidden_words,
    neutral_shift_word,
)
from lemanruss.htl.rv32i import random_magic_word

BASES = ("mips_16", "mcu", "picorv32", "darkriscv")  # smallest-to-biggest by black-boxed FF
# count (Peter's standing smaller-to-bigger rule): mips_16 268, mcu 1310, picorv32 1615,
# darkriscv 2034
# (docs/results-round10.md section 4.1, results-round11.md section 3).
PAYLOAD_KINDS = ("reset", "stall", "alu")
FORMS = ("gates", "k4", "k6")
ALL_FORMS = (*FORMS, "si")  # "si" = silicon (sky130_fd_sc_hd), Seeker-Si rc2 (spec 2026-11-07)

# spec docs/specs/2026-11-01-seeker-n200-design.md section 3's own Trojan-count prior, reused
# verbatim for Proc (docs/specs/2026-11-03-seeker-proc-rc1.md section 2).
_TROJAN_COUNT_P = (0.5, 0.3, 0.2)


def draw_trojan_count(rng: random.Random) -> int:
    r = rng.random()
    if r < _TROJAN_COUNT_P[0]:
        return 1
    if r < _TROJAN_COUNT_P[0] + _TROJAN_COUNT_P[1]:
        return 2
    return 3


def draw_trojans(
    base: str, rng: random.Random, used_words: set[int]
) -> tuple[list[str], list[int]]:
    """One circuit's Trojan draw: count, a kind per Trojan, a magic word per Trojan (added to
    `used_words`, which starts as the base's rejection set, `proc_witness.forbidden_words`)."""
    kinds = [rng.choice(PAYLOAD_KINDS) for _ in range(draw_trojan_count(rng))]
    words = []
    for kind in kinds:
        # per-base alu magic word: see proc_witness.alu_magic_word; reset/stall: any legal ADDI.
        w = (alu_magic_word(base, rng, used_words) if kind == "alu"
             else mips16.random_magic_word(rng, used_words) if base == "mips_16"
             else random_magic_word(rng, used_words))
        used_words.add(w)
        words.append(w)
    return kinds, words


def ff_count(text: str) -> int:
    return len(latches_of(parse_single_model(text)))


@dataclass
class BuiltCircuit:
    circuit_id: str
    base: str
    role: str  # "clean" | "infected"
    magic_words: list[int] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)
    ff_clean: int = 0
    ff_infected: int = 0
    ff_equal: bool = True
    per_trojan_fires: dict[str, bool] = field(default_factory=dict)
    silent_on_neutral: bool = False
    silent_on_neutral_iverilog: bool = False
    silent_on_neutral_shift: bool = True  # alu circuits: a non-magic shift-right stays correct
    shipped_silence: dict[str, dict[str, bool]] = field(default_factory=dict)
    shipped_silent: bool = True  # True vacuously for picorv32 (no shipped programs)
    form_text: dict[str, str] = field(default_factory=dict)  # form -> BLIF text
    form_script: dict[str, str] = field(default_factory=dict)  # form -> ABC script used
    form_errors: dict[str, str] = field(default_factory=dict)
    gate_engines: dict[str, str] = field(default_factory=dict)  # form key -> equivalence engine
    gate_pass: bool = False
    error: str = ""
    form_seconds: float = 0.0  # mapping plus release gate of the forms (wall)


def _prepare_and_patch(
    base: str, magic_words: list[int], kinds: list[str], work: Path, odin3_bin: Path,
) -> tuple[Path, Path, list[str]]:
    clean = work / "clean"
    inf = work / "infected"
    for d in (clean, inf):
        if d.exists():
            shutil.rmtree(d)
    if base == "darkriscv":
        files = prepare_dark(DARK_UPSTREAM, clean)
        prepare_dark(DARK_UPSTREAM, inf)
        for rel in ("rtl/darkriscv.v", "iv/rtl/darkriscv.v"):
            p = inf / rel
            patched, _ = insert_dark_kinded_multitrojan(p.read_text(), magic_words, kinds)
            p.write_text(patched)
    elif base == "mcu":
        files = prepare_mcu(MCU_UPSTREAM, clean, "blink")
        prepare_mcu(MCU_UPSTREAM, inf, "blink")
        for rel in ("single_cycle_core.v", "iv/single_cycle_core.v"):
            p = inf / rel
            patched, _ = insert_mcu_kinded_multitrojan(p.read_text(), magic_words, kinds)
            p.write_text(patched)
    elif base == "picorv32":
        files = prepare_picorv32(PICO_UPSTREAM, clean)
        prepare_picorv32(PICO_UPSTREAM, inf)
        for rel in ("picorv32.v", "iv/picorv32.v"):
            p = inf / rel
            patched, _ = insert_picorv32_kinded_multitrojan(p.read_text(), magic_words, kinds)
            p.write_text(patched)
    elif base == "mips_16":
        files = mips16.prepare_mips16(MIPS_UPSTREAM, clean)
        mips16.prepare_mips16(MIPS_UPSTREAM, inf, magic_words=magic_words, kinds=kinds)
    else:
        raise ValueError(f"unknown base {base!r}")
    return clean, inf, files


MIPS_UPSTREAM = PICO_UPSTREAM.parent / "opencores" / "mips_16" / "rtl"
_UPSTREAM = {"mcu": MCU_UPSTREAM, "darkriscv": DARK_UPSTREAM, "picorv32": PICO_UPSTREAM,
             "mips_16": MIPS_UPSTREAM}


def _odin_top(base: str) -> str:
    return {"darkriscv": "darksocv", "mcu": "single_cycle_BRAM_top", "picorv32": "picorv32",
            "mips_16": mips16.TOP}[base]


def _lower(base: str, cwd: Path, files: list[str], odin3_bin: Path, out: Path) -> None:
    if base == "darkriscv":
        lower_gates_as_names(odin3_bin, "darksocv", dark_odin_files(files), cwd / "rtl", out)
    elif base == "mcu":
        lower_gates_as_names(odin3_bin, "single_cycle_BRAM_top", mcu_odin_files(files), cwd, out)
    elif base == "mips_16":
        lower_gates_as_names(odin3_bin, mips16.TOP, files, cwd, out)
    else:
        lower_gates_as_names(odin3_bin, "picorv32", files, cwd, out)


def _witness_words(base: str, magic_words: list[int]) -> list[int]:
    if base == "darkriscv":
        return dark_witness_words(magic_words)
    if base == "mcu":
        return mcu_witness_words(magic_words)
    if base == "mips_16":
        return mips16.witness_words(magic_words)
    return pico_witness_words(magic_words)


def _write_program(base: str, out: Path, words: list[int]) -> None:
    if base == "darkriscv":
        write_dark_program(out, words)
    elif base == "mcu":
        write_mcu_program(out, words, "blink")
    elif base == "mips_16":
        mips16.write_program(out, words)
    else:
        write_pico_program(out, words)


def _run_once(
    base: str, out: Path, files: list[str], odin3_bin: Path, cycles: int, tag: str
) -> dict[str, str]:
    if base == "darkriscv":
        return run_dark_once(out, files, odin3_bin, cycles, tag)
    if base == "mcu":
        return run_mcu_once(out, files, odin3_bin, cycles, tag)
    if base == "mips_16":
        return mips16.run_once(out, files, odin3_bin, cycles, tag)
    return run_picorv32_once(out, files, odin3_bin, cycles, tag)


def _witness_cycles(base: str) -> int:
    return {"darkriscv": DARK_WITNESS_CYCLES, "mcu": MCU_WITNESS_CYCLES,
            "picorv32": PICO_WITNESS_CYCLES, "mips_16": mips16.WITNESS_CYCLES}[base]


DARK_SHIPPED_CYCLES = 4000  # proc_pilot.run_dark_pilot's own "prebuilt-firmware" stealth check


def shipped_programs(base: str) -> tuple[str, ...]:
    """Names of `base`'s own shipped program images (spec section 0a, Continuation 5 step 2):
    mcu's four `tests/mcu` demo programs (`proc_pilot.MCU_SHIPPED`), darkriscv's one prebuilt
    firmware image (`DARK_UPSTREAM/src/darksocv.mem`, left untouched by `prepare_dark` unless a
    witness program overwrites it), and none for picorv32 (no shipped firmware in the checkout,
    `docs/specs/2026-11-03-seeker-proc-rc1.md` section 4)."""
    if base == "mcu":
        return MCU_SHIPPED
    if base == "darkriscv":
        return ("firmware",)
    if base == "mips_16":
        return mips16.SHIPPED
    return ()


def _run_shipped_one(
    base: str, prog: str, magic_words: list[int], kinds: list[str], odin3_bin: Path, work: Path,
    circuit_id: str,
) -> dict[str, bool]:
    """One shipped program, clean vs infected, on all three engines. Returns
    {"rtl": equal, "nl": equal, "iverilog": equal}; the caller gates on rtl/nl only (H-P1
    amendment, spec section 0a: iverilog is recorded for shipped programs, not gating -- this
    function records all three so the caller can do either)."""
    s_clean = work / f"{circuit_id}-ship-{prog}-clean"
    s_inf = work / f"{circuit_id}-ship-{prog}-infected"
    for d in (s_clean, s_inf):
        if d.exists():
            shutil.rmtree(d)
    if base == "mcu":
        files = prepare_mcu(MCU_UPSTREAM, s_clean, prog)
        prepare_mcu(MCU_UPSTREAM, s_inf, prog)
        for rel in ("single_cycle_core.v", "iv/single_cycle_core.v"):
            p = s_inf / rel
            patched, _ = insert_mcu_kinded_multitrojan(p.read_text(), magic_words, kinds)
            p.write_text(patched)
        c = run_mcu_once(s_clean, files, odin3_bin, MCU_CYCLES, "ship")
        i = run_mcu_once(s_inf, files, odin3_bin, MCU_CYCLES, "ship")
    elif base == "darkriscv":
        files = prepare_dark(DARK_UPSTREAM, s_clean)
        prepare_dark(DARK_UPSTREAM, s_inf)
        for rel in ("rtl/darkriscv.v", "iv/rtl/darkriscv.v"):
            p = s_inf / rel
            patched, _ = insert_dark_kinded_multitrojan(p.read_text(), magic_words, kinds)
            p.write_text(patched)
        c = run_dark_once(s_clean, files, odin3_bin, DARK_SHIPPED_CYCLES, "ship")
        i = run_dark_once(s_inf, files, odin3_bin, DARK_SHIPPED_CYCLES, "ship")
    elif base == "mips_16":
        words = mips16.read_prog(MIPS_UPSTREAM.parent / "bench" / "mips_16_core_top"
                                 / f"{prog}.prog")
        files = mips16.prepare_mips16(MIPS_UPSTREAM, s_clean)
        mips16.prepare_mips16(MIPS_UPSTREAM, s_inf, magic_words=magic_words, kinds=kinds)
        for d in (s_clean, s_inf):
            mips16.write_program(d, words)
        cyc = mips16.SHIPPED_CYCLES[prog]
        c = mips16.run_once(s_clean, files, odin3_bin, cyc, "ship")
        i = mips16.run_once(s_inf, files, odin3_bin, cyc, "ship")
    else:
        raise ValueError(f"{base!r} has no shipped program {prog!r}")
    return {
        "rtl": traces_equal(c["rtl"], i["rtl"]),
        "nl": traces_equal(c["nl"], i["nl"]),
        "iverilog": traces_equal(c["ref"], i["ref"]),
    }


def check_shipped_silence(
    base: str, magic_words: list[int], kinds: list[str], odin3_bin: Path, work: Path,
    circuit_id: str,
) -> dict[str, dict[str, bool]]:
    """Every shipped program of `base`, clean vs infected (section 0a: Odin III RTL + netlist
    sim gate every program; iverilog is recorded, never gating, because it is the engine with
    the recorded four-state difference, round 10 sections 4.0/4.1). picorv32 has none
    (`shipped_programs` returns `()`): callers see an empty dict, not a false pass or failure."""
    return {
        prog: _run_shipped_one(base, prog, magic_words, kinds, odin3_bin, work, circuit_id)
        for prog in shipped_programs(base)
    }


def shipped_silence_ok(silence: dict[str, dict[str, bool]]) -> bool:
    """The gate itself: every shipped program's Odin III RTL and netlist traces must equal
    clean. iverilog is excluded from this check by construction (dict key ignored here)."""
    return all(res["rtl"] and res["nl"] for res in silence.values())


def build_one_circuit(
    circuit_id: str, base: str, rng: random.Random, used_words: set[int], odin3_bin: Path,
    work: Path, forced: tuple[list[str], list[int]] | None = None, functional_only: bool = False,
    forms: tuple[str, ...] = FORMS,
) -> BuiltCircuit:
    """Builds one logical circuit (clean + its infected twin, 1-3 independent Trojans) at the
    RTL/gate level, runs every rc1 functional gate once (FF equality, each Trojan's witness,
    H-P1-amended silence on the neutral witness), then maps the clean gate-level BLIF to all
    three release forms (gates/k4/k6) with its own random ABC script (spec section 4, clean/
    infected variety) for the catalogue this circuit contributes to. Only the CLEAN side is
    mapped to forms this function returns -- the caller packages the matching infected gate-
    level BLIF the same way, outside this function, when (and only when) every gate above
    passes (a circuit failing any gate is dropped and redrawn, spec section 5).
    `forced` = (kinds, magic words) replays one fixed draw (regression tests, repros).
    `functional_only` returns right after the functional gates (no form mapping, no release-gate
    equivalence proofs; `gate_pass` then covers the functional gates only). The release gate's
    ABC miters dominate the wall time (about 90 of 110 s for a darkriscv circuit), so draw
    regression tests that only need the functional gates set it."""
    if forced is not None:
        kinds, magic_words = list(forced[0]), list(forced[1])
    else:
        kinds, magic_words = draw_trojans(base, rng, used_words)
    n_trojans = len(kinds)
    trojan_ids = [f"{circuit_id}-t{i}" for i in range(n_trojans)]

    result = BuiltCircuit(circuit_id=circuit_id, base=base, role="infected",
                           magic_words=magic_words, kinds=kinds)
    try:
        clean, inf, files = _prepare_and_patch(base, magic_words, kinds, work, odin3_bin)
        clean_nl = work / f"{circuit_id}-clean.nl.blif"
        inf_nl = work / f"{circuit_id}-infected.nl.blif"
        _lower(base, clean, files, odin3_bin, clean_nl)
        _lower(base, inf, files, odin3_bin, inf_nl)
        ff_clean, ff_infected = ff_count(clean_nl.read_text()), ff_count(inf_nl.read_text())
        result.ff_clean, result.ff_infected = ff_clean, ff_infected
        result.ff_equal = ff_clean == ff_infected
        if not result.ff_equal:
            result.error = f"FF/latch equality failed: clean={ff_clean} infected={ff_infected}"
            return result

        cycles = _witness_cycles(base)
        for tid, word, kind in zip(trojan_ids, magic_words, kinds, strict=True):
            witness = (alu_witness_words(base, word) if kind == "alu"
                       else _witness_words(base, [word]))
            _write_program(base, inf, witness)
            _write_program(base, clean, witness)
            c = _run_once(base, clean, files, odin3_bin, cycles, f"w-{tid}")
            i = _run_once(base, inf, files, odin3_bin, cycles, f"w-{tid}")
            # fires on all three engines (brief Continuation 3 step 3), not only the iverilog
            # reference, whose four-state x on darkriscv differs from clean for any program.
            result.per_trojan_fires[tid] = all(
                not traces_equal(c[e], i[e]) for e in ("ref", "rtl", "nl"))

        neutral = _witness_words(base, [])
        _write_program(base, inf, neutral)
        _write_program(base, clean, neutral)
        c = _run_once(base, clean, files, odin3_bin, cycles, "w-neutral")
        i = _run_once(base, inf, files, odin3_bin, cycles, "w-neutral")
        result.silent_on_neutral = (
            traces_equal(c["rtl"], i["rtl"]) and traces_equal(c["nl"], i["nl"]))
        result.silent_on_neutral_iverilog = traces_equal(c["ref"], i["ref"])

        for word, kind in zip(magic_words, kinds, strict=True):
            if kind != "alu":
                continue
            shift = alu_witness_words(base, neutral_shift_word(word, base))
            _write_program(base, inf, shift)
            _write_program(base, clean, shift)
            c = _run_once(base, clean, files, odin3_bin, cycles, "w-neutral-shift")
            i = _run_once(base, inf, files, odin3_bin, cycles, "w-neutral-shift")
            result.silent_on_neutral_shift &= (
                traces_equal(c["rtl"], i["rtl"]) and traces_equal(c["nl"], i["nl"]))

        result.shipped_silence = check_shipped_silence(
            base, magic_words, kinds, odin3_bin, work, circuit_id)
        result.shipped_silent = shipped_silence_ok(result.shipped_silence)

        result.gate_pass = (
            result.ff_equal and all(result.per_trojan_fires.values()) and result.silent_on_neutral
            and result.silent_on_neutral_shift and result.shipped_silent
        )
        if not result.gate_pass:
            result.error = "one or more functional gates failed (see fields)"
            return result
        if functional_only:
            return result

        hints: dict[str, tuple[str, dict[str, str]]] = {}  # form key -> (mapped text, renames)
        t_forms = time.monotonic()
        for form in forms:
            out = obfuscate_traced(clean_nl, "silicon" if form == "si" else form, rng, work,
                                   f"{circuit_id}-clean-{form}")
            if isinstance(out, str):
                result.form_errors[form] = out
                continue
            text, script, mapped, renames = out
            result.form_text[form] = text
            result.form_script[form] = script
            hints[f"{form}-clean"] = (mapped, renames)
        inf_form_text: dict[str, str] = {}
        for form in forms:
            out = obfuscate_traced(inf_nl, "silicon" if form == "si" else form, rng, work,
                                   f"{circuit_id}-inf-{form}")
            if isinstance(out, str):
                result.form_errors[f"infected-{form}"] = out
                continue
            text, _script, mapped, renames = out
            inf_form_text[form] = text
            hints[f"{form}-infected"] = (mapped, renames)
        result.form_text = {f"{f}-clean": t for f, t in result.form_text.items()}
        result.form_text.update({f"{f}-infected": t for f, t in inf_form_text.items()})
        # release gate (rc2): every form file is one valid flat model, Odin III reads it, and
        # it is equivalent to the lowered netlist it was mapped from; a failure stops the build
        problems: list[str] = []
        for key, nl in (("clean", clean_nl), ("infected", inf_nl)):
            problems += [f"{key}.nl: {x}" for x in structural_problems(nl.read_text())]
        for key, ftext in result.form_text.items():
            ref = clean_nl if key.endswith("-clean") else inf_nl
            problems += [f"{key}: {x}" for x in gate_problems(
                ftext, odin3_bin, ref.read_text(), result.gate_engines, key,
                hints.get(key))]
        problems += [f"form not produced: {k}: {v}" for k, v in result.form_errors.items()]
        for key, ftext in result.form_text.items():
            if key.startswith("si-"):  # silicon: mapped FF count must equal the netlist count
                want = ff_clean if key.endswith("-clean") else ff_infected
                if ff_count(ftext) != want:
                    problems.append(f"{key}: FF count {ff_count(ftext)} != netlist {want}")
        result.form_seconds = round(time.monotonic() - t_forms, 1)
        if problems:
            result.error = "release gate: " + "; ".join(problems)[:400]
            result.gate_pass = False
    except Exception as exc:  # noqa: BLE001 -- a build failure is data (failures.json), not a crash
        result.error = f"{type(exc).__name__}: {str(exc)[:200]}"
        result.gate_pass = False
    return result


def build_n_circuits(
    n: int, base: str, seed: int, odin3_bin: Path, work: Path, max_redraws: int = 4,
) -> tuple[list[BuiltCircuit], list[BuiltCircuit]]:
    """`n` passing circuits for `base` (spec section 5: "a circuit failing any gate is dropped
    and redrawn ... never shipped"); returns (passing, failed) -- every attempt, passing or not,
    so a caller can report the failure rate honestly rather than only the survivors. Gives up on
    one slot after `max_redraws` failed redraws and moves to the next slot (so a systematically
    bad draw space shows up as a short `passing` list, not an infinite loop)."""
    rng = random.Random(seed)
    used_words: set[int] = set(forbidden_words(base, _UPSTREAM[base]))  # rejection rule
    passing: list[BuiltCircuit] = []
    failed: list[BuiltCircuit] = []
    for slot in range(1, n + 1):
        for redraw in range(max_redraws + 1):
            circuit_id = f"{base}-{slot:04d}r{redraw}"
            built = build_one_circuit(circuit_id, base, rng, used_words, odin3_bin, work)
            if built.gate_pass:
                passing.append(built)
                break
            failed.append(built)
    return passing, failed


__all__ = ["BASES", "PAYLOAD_KINDS", "FORMS", "ALL_FORMS", "BuiltCircuit", "build_one_circuit",
           "build_n_circuits", "draw_trojans", "ff_count", "draw_trojan_count",
           "magic_match_probability", "shipped_programs", "check_shipped_silence",
           "shipped_silence_ok"]
