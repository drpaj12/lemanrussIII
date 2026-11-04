"""Seeker v2.0 at n = 200: measuring, witnessing and proving one finished circuit (round 8).

Per circuit: the rareness of each Trojan and a witness input sequence come from one
bit-parallel run of the finished circuit (independent seed); the witness is then replayed in Odin
III's simulator against the golden; equivalence with every trigger forced inactive is ABC cec /
dsec (`tools/equiv-check`). The same functions re-run on the released files in `n200verify`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from lemanruss.htl import r4check
from lemanruss.htl.bitsim import (
    Compiled,
    exhaustive_lanes,
    reset_inputs,
    simulate_comb,
    simulate_given,
    simulate_seq,
)
from lemanruss.htl.blif_text import BlifModel, find_names_block, parse_single_model, render
from lemanruss.htl.n200plan import DOS, ENERGY, ERR_HI, ERR_LO, SLOW, Ctx, TSpec
from lemanruss.htl.rareness import band_of, scoap_value, wilson

CEC_TIMEOUT = 600
WINDOW = 1024
NS = (16, 64, 256, 1024)
Json = dict[str, object]
Steps = list[dict[str, int]]


def trig_name(j: int) -> str:
    return f"__htl_trigger_{j}"


def tmp_name(victim: str) -> str:
    return f"__htl_tmp_{victim}"


def ring_name(j: int) -> str:
    return f"__htl_energy{j}_q0"


def force_off(model: BlifModel, nets: list[str]) -> BlifModel:
    """`model` with every named net driven by a constant 0 (a `.names` with no cover rows)."""
    for net in nets:
        found = find_names_block(model, net)
        if found is None:
            raise ValueError(f"{net}: no .names block drives it")
        index, _ins, rows = found
        body = list(model.body)
        body[index : index + 1 + len(rows)] = [f".names {net}"]
        model = BlifModel(model.name, model.inputs, model.outputs, body)
    return model


def run_cec(a: Path, b: Path) -> tuple[str, int]:
    try:
        r = subprocess.run([str(r4check.equiv_check_bin()), str(a), str(b)],
                           capture_output=True, text=True, check=False, timeout=CEC_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "unproven", -1
    return {0: "equivalent", 1: "not-equivalent", 4: "unproven"}.get(r.returncode, "error"), \
        r.returncode


def cec_forced_off(golden: Path, infected: Path, scratch: Path, trigs: list[str]) -> str:
    """Verdict of cec / dsec of the golden against `infected` with the triggers forced to 0."""
    model = parse_single_model(infected.read_text(encoding="utf-8"))
    scratch.write_text(render(force_off(model, trigs)), encoding="utf-8")
    return run_cec(golden, scratch)[0]


def _lowest(mask: int) -> int:
    return (mask & -mask).bit_length() - 1


def _bits(comp: Compiled, words: list[dict[str, int]], lane: int) -> Steps:
    return [{n: (w[n] >> lane) & 1 for n in comp.data_inputs} for w in words]


def _shows(t: TSpec, trig: int, tmp: int, full: int) -> int:
    """Lanes where the Trojan's trigger is high and its payload changes the victim."""
    if t.payload == DOS:
        return trig & ((~tmp if t.param else tmp) & full)
    return trig


def measure(
    ctx: Ctx, icomp: Compiled, specs: list[TSpec], seed: int
) -> list[tuple[Json, Steps | None]]:
    """(rareness fields, witness) per Trojan of the finished circuit `icomp`. Always-on
    Trojans (slowdown) have no trigger: empty fields and no witness."""
    live = [(j, t) for j, t in enumerate(specs) if t.payload != SLOW]
    out: dict[int, tuple[Json, Steps | None]] = {}
    if ctx.kind == "comb":
        exact = len(icomp.data_inputs) <= 20
        if exact:
            given, nvec = exhaustive_lanes(icomp.data_inputs)
            iv = simulate_given(icomp, given, nvec)
        else:
            nvec = 1 << 20
            iv = simulate_comb(icomp, nvec, seed)
        full = (1 << nvec) - 1
        for j, t in live:
            trig = iv[trig_name(j)]
            hits = trig.bit_count()
            lo, hi = (hits / nvec, hits / nvec) if exact else wilson(hits, nvec)
            p = hits / nvec
            shows = _shows(t, trig, iv.get(tmp_name(t.victim), 0), full)
            steps = _bits(icomp, [iv], _lowest(shows)) if shows else None
            out[j] = ({"p": p, "p_lo": lo, "p_hi": hi, "vectors": nvec, "exact": exact,
                       "band": band_of(p), "shows": shows.bit_count() > 0}, steps)
    else:
        fixed = reset_inputs(ctx.model)
        lanes = ctx.lanes
        full = (1 << lanes) - 1
        rec: list[dict[str, int]] = []
        found: dict[int, tuple[int, int]] = {}

        def hook(t_cycle: int, values: dict[str, int]) -> None:
            rec.append({n: values[n] for n in icomp.data_inputs})
            for j, t in live:
                if j in found:
                    continue
                hit = _shows(t, values[trig_name(j)], values.get(tmp_name(t.victim), 0), full)
                if hit:
                    found[j] = (t_cycle, _lowest(hit))

        watch = [trig_name(j) for j, _t in live]
        curves = simulate_seq(icomp, lanes, WINDOW, seed, watch, fixed, hook)
        for j, _t in live:
            curve = curves[trig_name(j)]
            within: dict[str, list[float]] = {}
            for n in NS:
                h = curve[n - 1]
                lo, hi = wilson(h, lanes)
                within[str(n)] = [h / lanes, lo, hi]
            steps = None
            if j in found:
                tc, lane = found[j]
                steps = _bits(icomp, rec[: tc + 1], lane)
            out[j] = ({"p_fire_within": within, "seq_lanes": lanes,
                       "shows": j in found}, steps)
    return [out.get(j, ({}, None)) for j in range(len(specs))]


def encode_steps(inputs: list[str], steps: Steps) -> list[str]:
    return ["".join(str(s[n]) for n in inputs) for s in steps]


def decode_steps(inputs: list[str], rows: list[str]) -> Steps:
    return [{n: int(c) for n, c in zip(inputs, row, strict=True)} for row in rows]


def odin_replay(
    golden: Path, infected: Path, t: TSpec, steps: Steps, trig: str, ring: str
) -> tuple[bool, str]:
    """Replays `steps` from reset in Odin III's simulator on the golden and the finished circuit;
    the Trojan fired when, in the last cycle, its trigger is high and its payload shows (dos:
    victim equals the stuck value and the golden's does not; err: victim differs from the
    golden's; energy: the ring bit that the trigger toggles is 1 after the next clock edge)."""
    from odin3 import Design

    with Design() as cd, Design() as idg:
        cd.run_pass("read_blif", str(golden))
        idg.run_pass("read_blif", str(infected))
        with cd.simulate() as cs, idg.simulate() as isim:
            last = len(steps) - 1
            for k, drive in enumerate(steps):
                for name, value in drive.items():
                    for sim in (cs, isim):
                        sig = sim.signal(name)
                        if sig is not None and sig.kind == "input":
                            sim.set(sig, value)
                cs.settle()
                isim.settle()
                if k != last:
                    cs.step(1)
                    isim.step(1)
            tsig = isim.signal(trig)
            tv = None if tsig is None else isim[tsig]
            cv, iv = cs[t.victim], isim[t.victim]
            ring_after = None
            if t.payload == ENERGY:
                isim.step(1)
                rsig = isim.signal(ring)
                ring_after = None if rsig is None else isim[rsig]
    detail = f"trigger={tv} infected_victim={iv} golden_victim={cv} ring={ring_after}"
    if tv != 1:
        return False, detail
    if t.payload == DOS:
        return iv == t.param and cv != t.param, detail
    if t.payload in (ERR_HI, ERR_LO):
        return iv != cv, detail
    return ring_after == 1, detail


def odin_ring_toggles(path: Path, steps: Steps, ring: list[str]) -> int:
    """Total bit toggles of the ring nets `ring` in Odin III's simulator over `steps` from reset
    (one extra clock edge after the last vector)."""
    from odin3 import Design

    with Design() as design:
        design.run_pass("read_blif", str(path))
        with design.simulate() as sim:
            sigs = [s for s in (sim.signal(n) for n in ring) if s is not None]
            sim.set_toggle_counting()
            for drive in steps:
                for name, value in drive.items():
                    sig = sim.signal(name)
                    if sig is not None and sig.kind == "input":
                        sim.set(sig, value)
                sim.step(1)
            sim.step(1)
            return sum(sim.toggles(s) for s in sigs)


def odin_fire(
    golden: Path, other: Path, t: TSpec, steps: Steps, ring: list[str] | None = None
) -> tuple[bool, str]:
    """Replays `steps` from reset in Odin III's simulator on the golden and on `other` (the
    infected circuit, before or after obfuscation); the payload shows in the last cycle: dos: the
    victim equals the stuck value and the golden's does not; err: the victim differs from the
    golden's. energy: the ring nets `ring` (their names in `other`; the answer key keeps them
    through the renaming) toggle at least once over the witness; the detail also gives the
    toggles of the same ring under an all-zero input sequence of the same length (the idle
    measure). Needs no trigger net, so it also runs on an optimised circuit."""
    from odin3 import Design

    if t.payload == ENERGY:
        if not ring:
            return False, "no ring nets given"
        on = odin_ring_toggles(other, steps, ring)
        idle = odin_ring_toggles(other, [dict.fromkeys(d, 0) for d in steps], ring)
        return on > 0, f"ring_toggles_witness={on} ring_toggles_idle={idle} bits={len(ring)}"
    with Design() as cd, Design() as idg:
        cd.run_pass("read_blif", str(golden))
        idg.run_pass("read_blif", str(other))
        with cd.simulate() as cs, idg.simulate() as isim:
            last = len(steps) - 1
            for k, drive in enumerate(steps):
                for name, value in drive.items():
                    for sim in (cs, isim):
                        sig = sim.signal(name)
                        if sig is not None and sig.kind == "input":
                            sim.set(sig, value)
                cs.settle()
                isim.settle()
                if k != last:
                    cs.step(1)
                    isim.step(1)
            cv, iv = cs[t.victim], isim[t.victim]
    detail = f"infected_victim={iv} golden_victim={cv}"
    if t.payload == DOS:
        return iv == t.param and cv != t.param, detail
    return iv != cv, detail


def scoap_fields(ctx: Ctx, t: TSpec) -> Json:
    cc_key, sc_key = ("cc1", "cc0"), ("sc1", "sc0")
    out: Json = {}
    if t.trig == "comb":
        out["trigger_cc"] = [scoap_value(ctx.sc.get(n, {}).get(cc_key[0] if v else cc_key[1]))
                             for n, v in t.nets]
    elif t.trig in ("ctr", "pat", "magic"):
        out["trigger_sc"] = [scoap_value(ctx.sc.get(n, {}).get(sc_key[0] if v else sc_key[1]))
                             for n, v in t.nets]
    if t.victim:
        out["victim_co"] = scoap_value(ctx.sc.get(t.victim, {}).get("co"))
        out["victim_so"] = scoap_value(ctx.sc.get(t.victim, {}).get("so"))
    return out


def parse(path: Path) -> BlifModel:
    return parse_single_model(path.read_text(encoding="utf-8"))
