"""Benchmark build (spec docs/specs/2026-10-31-htl-design.md section 5, "Then build" D).

Ties the library together on a set of base designs: site selection, netlist insertion,
verification, and a results table.

Round 1 used Odin III's Simulation API for rarity, which needed `(* keep *)` on candidate
internal nets in the HDL -- impossible on a real base design under `external/` (read-only).
Round 2 replaces that with lemanruss.htl.blif_sim: a pure-Python evaluator over the exact BLIF
`write_blif --gates-as-names` writes, so every net name already matches (no cname-prefix lookup
needed either) and no HDL annotation is needed. `check_fires` still opens a real odin3.Design and
Simulation: that is the authoritative check that the BLIF edit behaves as intended on Odin III's
own engine, not just this module's own evaluator.

Scope this round: CombRareTrigger with k=2 rare *internal* nets, the DosStuck payload, at the
netlist level, on combinational designs (SystemVerilog `_ref.sv` files from
external/Gate-Breaker-verilog-eval route through Odin III's slang-backed SV reader
automatically; see docs/PASSES.md's `read_verilog` row, v1.1.0 paragraph). Equivalence is
brute-forced (blif_sim, every primary-input combination but the trigger's own) up to
`_BRUTE_FORCE_MAX_INPUTS` inputs; above that, lemanruss.htl.verify.check_equivalence wraps
tools/equiv-check (ABC cec) on the infected design with its trigger forced permanently inactive.
Stealth is a Monte Carlo run (blif_sim) comparing clean and infected outputs over random inputs,
counting mismatches while the trigger is inactive and the trigger's own measured activation
rate.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from pathlib import Path

from lemanruss.htl.blif_sim import evaluate_cycle, find_driving_inputs, monte_carlo_probability
from lemanruss.htl.blif_text import BlifModel, parse_single_model, render
from lemanruss.htl.insert_netlist import (
    TRIGGER_NET,
    insert_comb_rare_trigger,
    insert_dos_stuck_payload,
)
from lemanruss.htl.manifest import CatalogueEntry, write_labels, write_manifest
from lemanruss.htl.payloads import DosStuckPayload
from lemanruss.htl.triggers import CombRareTrigger
from lemanruss.htl.trojan import compose
from lemanruss.htl.verify import check_equivalence, check_fires

_BRUTE_FORCE_MAX_INPUTS = 20  # 2**20 combos is already a lot for this round's pure-Python loop
_STEALTH_CYCLES = 4096
_RARITY_CYCLES = 4096
_RARITY_THRESHOLD = 0.3


@dataclass(frozen=True)
class BuildFailure:
    base_design: str
    reason: str


def lowering_script(verilog_path: Path, arch: Path | None, flatten: bool = False) -> str:
    """The Odin III script that turns `verilog_path` into a gate-level netlist. Designs that use
    the VTR primitives (`single_port_ram`, `dual_port_ram`, `multiply`, `adder`) need `arch`:
    `read_arch` first, `--vtr-compat` on the read, and `unmap` to turn the hard-block cells back
    into soft logic before `lower` (Odin III front-end triage note, issue 2). `flatten` expands
    module instances (b17 holds three b15; `bitsim` needs one flat model): `flatten; opt` after
    `proc; opt`."""
    flat = "flatten; opt; " if flatten else ""
    if arch is None:
        return f'read_verilog "{verilog_path}"; proc; opt; {flat}lower'
    return (f'read_arch "{arch}"; read_verilog --vtr-compat "{verilog_path}"; proc; opt; '
            f"{flat}unmap; lower")


def _write_gates_as_names_blif(
    verilog_path: Path, out_path: Path, arch: Path | None = None
) -> tuple[str, list[str]]:
    """Reads `verilog_path` (Verilog or, via the registered slang reader, SystemVerilog), writes
    `out_path` as plain-dialect `.names`-only BLIF, and returns (top module name, input port
    names)."""
    import contextlib

    from odin3 import Design

    from lemanruss.htl.sv_reader import SlangNotFound, register_slang_reader

    with Design() as design:
        if verilog_path.suffix == ".sv":
            # read_verilog's own error ("no SystemVerilog reader registered") follows otherwise.
            with contextlib.suppress(SlangNotFound):
                register_slang_reader(design)
        design.run_script(lowering_script(verilog_path, arch))
        top = design.top()
        if top is None:
            raise ValueError(f"{verilog_path}: no top module")
        top_name = top.name
        inputs = [p.wire.name for p in top.ports() if p.node.type_name == "$port_in"]
        design.run_pass("write_blif", f"--gates-as-names {out_path}")
    return top_name, inputs


def _force_trigger_off(model: BlifModel, trigger_net: str) -> BlifModel:
    """Replaces the `.names` block driving `trigger_net` with the zero-input constant-0 block
    (spec section 4(c): "the trigger forced permanently inactive")."""
    from lemanruss.htl.blif_text import find_names_block

    found = find_names_block(model, trigger_net)
    new_body = list(model.body)
    if found is not None:
        index, _inputs, rows = found
        end = index + 1 + len(rows)
        new_body[index:end] = [f".names {trigger_net}", "0"]
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=new_body)


def _brute_force_equivalent(clean: BlifModel, infected: BlifModel, trigger_net: str) -> bool:
    """True when `clean` and `infected` agree on every output over every primary-input
    combination where `trigger_net` is inactive (sound, exhaustive; blif_sim, no Odin III call).
    Excludes every combination the trigger fires on, not just the one witness
    `find_driving_inputs` returned: a rare *net* value can be realised by more than one input
    combination (found by running this against adder_4bit/sub_4bit, which have exactly that
    shape -- an earlier version excluded only the witness and wrongly reported "not
    equivalent")."""
    for combo in itertools.product([0, 1], repeat=len(clean.inputs)):
        draw = dict(zip(clean.inputs, combo, strict=True))
        infected_values = evaluate_cycle(infected, draw)
        if infected_values.get(trigger_net, 0):
            continue
        clean_values = evaluate_cycle(clean, draw)
        for name in clean.outputs:
            if clean_values.get(name) != infected_values.get(name):
                return False
    return True


def _equiv_check_equivalent(
    clean_path: Path, infected: BlifModel, trigger_net: str, out_dir: Path, base_name: str
) -> bool | None:
    """`verify.check_equivalence` on `clean_path` vs. `infected` with its trigger forced off, for
    a design too wide to brute-force; None when no ABC binary is found (recorded as a failure by
    the caller, not silently skipped)."""
    import os

    abc_bin = os.environ.get("ODIN3_ABC")
    if abc_bin is None:
        root = os.environ.get("ODIN3_ROOT", "")
        for build in ("release", "debug", "clang-debug"):
            candidate = Path(f"{root}/build/{build}/third_party/abc/abc")
            if candidate.is_file():
                abc_bin = str(candidate)
                break
    if abc_bin is None:
        return None
    forced_off = _force_trigger_off(infected, trigger_net)
    forced_off_path = out_dir / f"{base_name}.forced_off.blif"
    forced_off_path.write_text(render(forced_off), encoding="utf-8")
    result = check_equivalence(Path(abc_bin), clean_path, forced_off_path)
    return result.equivalent


def _stealth(
    clean: BlifModel,
    infected: BlifModel,
    trigger_net: str,
    cycles: int = _STEALTH_CYCLES,
    seed: int = 1,
) -> tuple[float, int]:
    """(measured activation probability, mismatch count while inactive) over `cycles` uniform
    random input draws (spec section 4(b))."""
    rng = random.Random(seed)
    active = 0
    mismatches = 0
    for _ in range(cycles):
        draw = {name: rng.getrandbits(1) for name in clean.inputs}
        infected_values = evaluate_cycle(infected, draw)
        if infected_values.get(trigger_net, 0):
            active += 1
            continue
        clean_values = evaluate_cycle(clean, draw)
        if any(clean_values.get(n) != infected_values.get(n) for n in clean.outputs):
            mismatches += 1
    return active / cycles if cycles else 0.0, mismatches


def build_one(verilog_path: Path, out_dir: Path) -> list[CatalogueEntry] | BuildFailure:
    """Builds and verifies one CombRare+DosStuck Trojan for `verilog_path`'s first output, at the
    netlist level; returns the catalogue entry or a BuildFailure with the reason (never raises
    for an expected gap, so callers can report it in the results table)."""
    base_name = verilog_path.stem
    clean_path = out_dir / f"{base_name}.clean.blif"
    try:
        top_name, inputs = _write_gates_as_names_blif(verilog_path, clean_path)
    except Exception as exc:  # the design did not elaborate/write; recorded, not raised
        return BuildFailure(base_name, f"write_blif failed: {exc}")

    model = parse_single_model(clean_path.read_text(encoding="utf-8"))
    if not model.outputs:
        return BuildFailure(base_name, "no outputs")
    victim = model.outputs[0]

    measurements = monte_carlo_probability(model, cycles=_RARITY_CYCLES, seed=0)
    # Excludes every output net, not just the victim: a trigger reading the victim's own net
    # creates a combinational loop once the payload rewires that net's driver (found by running
    # this against Prob011_norgate_ref, whose only two candidate rare nets were an internal net
    # and the single output "out" -- Simulation.open then failed on the resulting cycle).
    # A net stuck at an exact constant (p_one == 0.0 or 1.0 -- seen in practice on
    # Prob027_fadd_ref/Prob009_popcount3_ref, both carrying dead logic off an unconnected "gnd
    # gnd" pair) passes the rarity test trivially but gives find_driving_inputs no input
    # combination to realise it, since it never varies; excluded here, not just left to fail.
    outputs = set(model.outputs)
    rare = [
        (m.name, 1 if m.p_one <= _RARITY_THRESHOLD else 0)
        for m in measurements
        if m.name not in outputs
        and 0.0 < m.p_one < 1.0
        and (m.p_one <= _RARITY_THRESHOLD or m.p_one >= 1.0 - _RARITY_THRESHOLD)
    ]
    if len(rare) < 2:
        return BuildFailure(base_name, f"fewer than 2 rare nets found ({len(rare)})")
    trigger_nets = tuple(rare[:2])

    if len(model.inputs) <= _BRUTE_FORCE_MAX_INPUTS:
        driving_inputs = find_driving_inputs(model, trigger_nets)
        if driving_inputs is None:
            return BuildFailure(base_name, "no input combination realises the chosen trigger nets")
    else:
        driving_inputs = None  # too wide to brute-force a witness this round

    trigger = CombRareTrigger(k=2, nets=trigger_nets)
    payload = DosStuckPayload(victim=victim, stuck_value=1)
    trojan = compose(trigger, payload, "netlist", site=victim)

    with_trigger = insert_comb_rare_trigger(model, trigger)
    try:
        infected_model = insert_dos_stuck_payload(with_trigger, payload)
    except Exception as exc:
        return BuildFailure(base_name, f"insert_dos_stuck_payload failed: {exc}")

    infected_path = out_dir / f"{base_name}.{trojan.id}.blif"
    infected_path.write_text(render(infected_model), encoding="utf-8")

    fires: bool | None = None
    victim_after: int | None = None
    if driving_inputs is not None:
        from odin3 import Design

        with Design() as design:
            design.run_pass("read_blif", str(infected_path))
            fire = check_fires(design, drive=driving_inputs, victim=victim, top=top_name)
            fires, victim_after = fire.fired, fire.victim_after

    if driving_inputs is not None:
        equivalent: bool | None = _brute_force_equivalent(model, infected_model, TRIGGER_NET)
        equivalence_method = "exhaustive-input-comparison"
    else:
        equivalent = _equiv_check_equivalent(
            clean_path, infected_model, TRIGGER_NET, out_dir, base_name
        )
        equivalence_method = "tools/equiv-check (ABC cec)"

    activation_probability, stealth_mismatches = _stealth(model, infected_model, TRIGGER_NET)

    entry = CatalogueEntry(
        base_design=base_name,
        trojan=trojan,
        verification={
            "fires": fires,
            "victim_after": victim_after,
            "activation_probability": activation_probability,
            "stealth_mismatches": stealth_mismatches,
            "stealth_cycles": _STEALTH_CYCLES,
            "equivalent_clean_part": equivalent,
            "equivalence_method": equivalence_method,
        },
    )
    return [entry]


def build_benchmark(
    base_designs: list[Path], out_dir: Path, mix_ratio: float = 0.5, seed: int = 0
) -> tuple[list[CatalogueEntry], list[BuildFailure]]:
    """Builds and verifies one Trojan per base design, writes manifest.json, labels.json (the
    answer key, kept separate) and mix.json (the Seeker's Dilemma style clean/infected draw) under
    out_dir, and returns (entries, failures)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[CatalogueEntry] = []
    failures: list[BuildFailure] = []
    for path in base_designs:
        result = build_one(path, out_dir)
        if isinstance(result, BuildFailure):
            failures.append(result)
        else:
            entries.extend(result)
    write_manifest(entries, out_dir / "manifest.json")
    write_labels(entries, out_dir / "labels.json")
    _write_mix(entries, out_dir / "mix.json", mix_ratio, seed)
    return entries, failures


def _write_mix(entries: list[CatalogueEntry], path: Path, mix_ratio: float, seed: int) -> None:
    """A Seeker's Dilemma style draw: each base design is "infected" (shown with its Trojan) at
    probability `mix_ratio`, else "clean" (shown without it) -- written without labels, so a
    detector pointed at this file alone cannot see which is which (spec section 5)."""
    import json

    rng = random.Random(seed)
    draw = {
        e.base_design: "infected" if rng.random() < mix_ratio else "clean" for e in entries
    }
    path.write_text(
        json.dumps({"schema": 1, "mix_ratio": mix_ratio, "seed": seed, "draw": draw}, indent=2,
                   sort_keys=True) + "\n",
        encoding="utf-8",
    )
