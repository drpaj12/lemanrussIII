"""Verification: fires, stealth, equivalence (spec docs/specs/2026-10-31-htl-design.md section 4).

Netlist-level checks drive an odin3.Design's Simulation directly (in-process, no file needed for
"fires"/"stealth" -- a crafted odin3-sim-vectors file is still built by lemanruss.htl.testbench
for the on-disk testbench the brief asks for, and is exercised separately in tests/). The
equivalence check shells out to the repo's own tools/equiv-check (ABC cec), the same binary Loki's
CLAUDE.md names for the same purpose.
"""

from __future__ import annotations

import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odin3 import Design


@dataclass(frozen=True)
class FireResult:
    fired: bool
    victim_before: int
    victim_after: int


def check_fires(
    design: Design,
    drive: dict[str, int],
    victim: str,
    cycles: int = 1,
    top: str | None = None,
) -> FireResult:
    """Drives `drive` (every clock input stays whatever `step` does with it) for `cycles` cycles
    and reports whether `victim` changed value across the run -- the "trigger fires, payload
    shows" check (spec section 4(a))."""
    with design.simulate(top) as sim:
        before = sim[victim]
        for sig, value in drive.items():
            sim[sig] = value
        sim.step(cycles)
        after = sim[victim]
        return FireResult(fired=(before != after), victim_before=before, victim_after=after)


@dataclass(frozen=True)
class FireVsClean:
    fired: bool
    detail: str


def check_fires_vs_clean(
    clean: Design, infected: Design, steps: list[dict[str, int]], victim: str, trigger: str,
    stuck: int, top: str | None = None,
) -> FireVsClean:
    """Round 4 form of the fire check, both designs run by Odin III's simulator: replays `steps`
    (one input dict per cycle; set, settle, then step) from reset and looks at the last one. It
    fired when the trigger net is high (if Odin III lists it), the infected victim equals `stuck`
    and the clean victim does not; earlier cycles must show no victim difference."""
    with clean.simulate(top) as cs, infected.simulate(top) as isim:
        early = 0
        for k, drive in enumerate(steps):
            for name, value in drive.items():
                for sim in (cs, isim):
                    sig = sim.signal(name)
                    if sig is not None and sig.kind == "input":
                        sim.set(sig, value)
            cs.settle()
            isim.settle()
            last = k == len(steps) - 1
            if not last:
                early += cs[victim] != isim[victim]
                cs.step(1)
                isim.step(1)
        trig_sig = isim.signal(trigger)
        trig = None if trig_sig is None else isim[trig_sig]
        cv, iv = cs[victim], isim[victim]
    fired = (trig in (None, 1)) and iv == stuck and cv != stuck
    detail = f"trigger={trig} infected_victim={iv} clean_victim={cv} early_diffs={early}"
    return FireVsClean(fired, detail)


@dataclass(frozen=True)
class StealthResult:
    activation_probability: float
    mismatches: int
    cycles: int


def check_stealth(
    clean_design: Design,
    infected_design: Design,
    trigger_signal: str,
    cycles: int = 4096,
    seed: int = 0,
    top: str | None = None,
) -> StealthResult:
    """Drives both designs with the same seeded random inputs for `cycles` cycles; counts how
    often every output differs between them while `trigger_signal` is inactive (spec section
    4(b): stealth is "no diff when the trigger is not met"), and reports the trigger's measured
    activation probability over the run."""
    rng = random.Random(seed)
    mismatches = 0
    active = 0
    with clean_design.simulate(top) as clean, infected_design.simulate(top) as infected:
        clean_inputs = [s for s in clean.signals() if s.kind == "input"]
        infected_outputs = {s.name: s for s in infected.signals() if s.kind == "output"}
        for _ in range(cycles):
            for sig in clean_inputs:
                value = rng.getrandbits(min(sig.width, 63))
                clean[sig] = value
                infected[sig.name] = value
            clean.step()
            infected.step()
            triggered = bool(infected[trigger_signal])
            if triggered:
                active += 1
                continue
            for out_sig in clean.signals():
                if out_sig.kind != "output":
                    continue
                if out_sig.name not in infected_outputs:
                    continue
                if clean[out_sig] != infected[infected_outputs[out_sig.name]]:
                    mismatches += 1
                    break
    return StealthResult(
        activation_probability=active / cycles if cycles else 0.0,
        mismatches=mismatches,
        cycles=cycles,
    )


@dataclass(frozen=True)
class EquivResult:
    equivalent: bool
    returncode: int
    stdout: str
    stderr: str


def check_equivalence(
    equiv_check_bin: Path, clean_blif: Path, forced_off_blif: Path, timeout: int = 120,
    extra_args: tuple[str, ...] = (),
) -> EquivResult:
    """Runs the repo's `tools/equiv-check` (ABC cec) on the clean design against the infected
    design with its trigger forced inactive (spec section 4(c)): exit 0 equivalent, 1 not, 2
    error (`equiv_check.py`'s own convention)."""
    result = subprocess.run(
        [str(equiv_check_bin), str(clean_blif), str(forced_off_blif), *extra_args],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    return EquivResult(
        equivalent=result.returncode == 0,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
