"""Round 4 verification (brief items 1 and 2): bit-parallel simulator cross-checked against Odin
III's own simulator, the Odin III fire check restored as the authoritative one, and the ABC
equivalence check (clean part, trigger forced inactive) on every infected circuit.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from lemanruss.htl.bitsim import (
    Compiled,
    compile_model,
    exhaustive_lanes,
    replay,
    reset_inputs,
    simulate_comb,
    simulate_given,
    simulate_seq,
    simulate_seq_pair,
)
from lemanruss.htl.blif_text import BlifModel, find_names_block, parse_single_model, render
from lemanruss.htl.insert_netlist import TRIGGER_NET
from lemanruss.htl.verify import FireVsClean, check_equivalence, check_fires_vs_clean

SEQ_LANES = 6
SEQ_CYCLES = 48


def equiv_check_bin() -> Path:
    """tools/equiv-check of the Odin III checkout that ODIN3_LIB points into."""
    root = os.environ.get("ODIN3_ROOT")
    base = Path(root) if root else Path(os.environ["ODIN3_LIB"]).resolve().parents[2]
    return base / "tools" / "equiv-check" / "equiv-check"


def force_trigger_off(model: BlifModel, trigger_net: str = TRIGGER_NET) -> BlifModel:
    """The infected model with the trigger net driven by a constant 0 (a `.names` with no cover
    rows): the clean part with the Trojan switched off (spec section 4(c))."""
    found = find_names_block(model, trigger_net)
    if found is None:
        return model
    index, _ins, rows = found
    body = list(model.body)
    body[index : index + 1 + len(rows)] = [f".names {trigger_net}"]
    return BlifModel(model.name, model.inputs, model.outputs, body)


@dataclass
class CecResult:
    circuit: str
    verdict: str  # equivalent | not-equivalent | unproven | error
    returncode: int


def cec_forced_off(
    clean_path: Path, infected_path: Path, scratch: Path, circuit: str
) -> CecResult:
    """ABC equivalence (tools/equiv-check: cec, or dsec with latches) of the clean circuit
    against the infected circuit with its trigger forced inactive. `scratch` is a per-worker
    file that is overwritten every call (nothing is deleted)."""
    model = parse_single_model(infected_path.read_text(encoding="utf-8"))
    scratch.write_text(render(force_trigger_off(model)), encoding="utf-8")
    res = check_equivalence(equiv_check_bin(), clean_path, scratch)
    verdict = {0: "equivalent", 1: "not-equivalent", 4: "unproven"}.get(res.returncode, "error")
    return CecResult(circuit, verdict, res.returncode)


@dataclass
class CrossResult:
    circuit: str
    kind: str  # comb | seq
    vectors: int  # (vector or lane-cycle) points compared
    compares: int  # signal comparisons
    mismatches: int
    skipped_signals: int  # watched names Odin III's netlist does not list
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def crosscheck(
    path: Path, circuit: str, vectors: int, seed: int,
    witness: list[dict[str, int]] | None = None, extra: tuple[str, ...] = (TRIGGER_NET,),
) -> CrossResult:
    """Bit-parallel simulation vs Odin III's cycle simulator on one circuit: random vectors
    (combinational) or SEQ_LANES independent runs of SEQ_CYCLES cycles (sequential). Compared:
    every primary output and the `extra` nets that Odin III lists, at every point, before the
    clock edge. `witness` (an input sequence that fires the trigger) is replayed as one more run,
    so the trigger and payload paths are exercised too, not only the quiet random ones."""
    from odin3 import Design

    model = parse_single_model(path.read_text(encoding="utf-8"))
    comp = compile_model(model)
    fixed = reset_inputs(model)
    seq = bool(comp.latches)
    watch = [*model.outputs, *[e for e in extra if e not in model.outputs]]
    watch = [w for w in watch if w in {*model.outputs, *(b[0] for b in comp.blocks)}]
    try:
        if seq:
            nlanes, steps = SEQ_LANES, SEQ_CYCLES
            trace: list[dict[str, int]] = []
            keep = [*comp.data_inputs, *watch]
            simulate_seq(
                comp, nlanes, steps, seed, [], fixed,
                lambda _t, v: trace.append({k: v[k] for k in keep}),
            )
            runs = [[{k: (cyc[k] >> lane) & 1 for k in keep} for cyc in trace]
                    for lane in range(nlanes)]
        else:
            nvec = vectors
            vals = simulate_comb(comp, nvec, seed, fixed)
            runs = [[{k: (vals[k] >> i) & 1 for k in [*comp.data_inputs, *watch]}
                     for i in range(nvec)]]
        if witness:
            wv = replay(comp, witness)
            runs.append([{k: v[k] for k in [*comp.data_inputs, *watch]} for v in wv])
        compares = mism = skipped = points = 0
        with Design() as design:
            design.run_pass("read_blif", str(path))
            with design.simulate() as sim:
                info = {n: sim.signal(n) for n in [*comp.data_inputs, *watch]}
                for run in runs:
                    sim.reset()
                    for point in run:
                        for n in comp.data_inputs:
                            if (sig_in := info[n]) is not None:
                                sim.set(sig_in, point[n])
                        sim.settle()
                        points += 1
                        for w in watch:
                            sig = info[w]
                            if sig is None:
                                skipped += 1
                                continue
                            compares += 1
                            mism += sim.get(sig) != point[w]
                        if seq:
                            sim.step(1)
        return CrossResult(circuit, "seq" if seq else "comb", points, compares, mism, skipped)
    except Exception as exc:
        return CrossResult(circuit, "seq" if seq else "comb", 0, 0, 0, 0, f"{type(exc).__name__}: "
                           f"{str(exc)[:100]}")


@dataclass
class FireCheck:
    circuit: str
    witness: bool  # the bit-parallel sim found a firing input sequence
    odin_fired: bool  # Odin III confirms: trigger high and payload differs from the clean design
    detail: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _bit_steps(comp: Compiled, words: list[dict[str, int]], lane: int) -> list[dict[str, int]]:
    return [{n: (w[n] >> lane) & 1 for n in comp.data_inputs} for w in words]


def find_witness(
    clean: BlifModel, infected: BlifModel, victim: str, stuck: int, window: int, seed: int,
    trigger_net: str = TRIGGER_NET, tmp_net: str | None = None,
) -> list[dict[str, int]] | None:
    """One input sequence (a single vector for a combinational design) on which the trigger is
    high and the payload changes the victim relative to the clean design."""
    ccomp = compile_model(clean)
    icomp = compile_model(infected)
    fixed = reset_inputs(clean)
    if not ccomp.latches:
        n_in = len(icomp.data_inputs)
        if n_in <= 20:
            given, nvec = exhaustive_lanes(icomp.data_inputs)
            iv = simulate_given(icomp, given, nvec)
        else:
            nvec = 1 << 20
            iv = simulate_comb(icomp, nvec, seed, fixed)
        tmp = tmp_net or f"__htl_tmp_{victim}"
        shows = iv[trigger_net] & (~iv[tmp] if stuck else iv[tmp]) & ((1 << nvec) - 1)
        if not shows:
            return None
        lane = (shows & -shows).bit_length() - 1
        return [{n: (iv[n] >> lane) & 1 for n in icomp.data_inputs}]
    lanes = 1024
    record: list[dict[str, int]] = []
    found: list[int] = []
    simulate_seq_pair(
        ccomp, icomp, lanes, window, seed, trigger_net, fixed, record, victim, found)
    if not found:
        return None
    mask = found[0]
    lane = (mask & -mask).bit_length() - 1
    return _bit_steps(icomp, record, lane)


def fire_check(
    clean_path: Path, infected_path: Path, circuit: str, victim: str, stuck: int, window: int,
    seed: int, steps: list[dict[str, int]] | None = None, trigger_net: str = TRIGGER_NET,
    tmp_net: str | None = None,
) -> FireCheck:
    """Authoritative fire check by Odin III's simulator (verify.check_fires_vs_clean): replay a
    witness found by the bit-parallel simulator in Odin III on both designs."""
    from odin3 import Design

    clean = parse_single_model(clean_path.read_text(encoding="utf-8"))
    infected = parse_single_model(infected_path.read_text(encoding="utf-8"))
    if steps is None:
        steps = find_witness(
            clean, infected, victim, stuck, window, seed, trigger_net, tmp_net)
    if steps is None:
        return FireCheck(circuit, False, False, "no witness found by bit-parallel simulation")
    try:
        with Design() as cd, Design() as idesign:
            cd.run_pass("read_blif", str(clean_path))
            idesign.run_pass("read_blif", str(infected_path))
            res: FireVsClean = check_fires_vs_clean(
                cd, idesign, steps, victim, trigger_net, stuck)
    except Exception as exc:
        return FireCheck(circuit, True, False, f"{type(exc).__name__}: {str(exc)[:100]}")
    return FireCheck(circuit, True, res.fired, res.detail)
