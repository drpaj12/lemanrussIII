"""Seeker v2.0 family manifests and READMEs (brief "Seeker v2.0 benchmark families").

A manifest lists family, version, v1 lineage, bases, restructurings, Trojan catalogue, circuits
(id, base, file) and the mix ratio. Labels and rareness live under answer_key/, never in the
manifest, so a detector pointed at manifest.json + circuits/ cannot see them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lemanruss.htl.seeker import Built

VERSION = "2.0"

LINEAGE = {
    "Seeker-Comb": (
        "v1 = Seeker1: Sarihi, Patooghy, Badawy, Jamieson, 'The Seeker's Dilemma', arXiv "
        "2402.17918, "
        "IPCCC 2024 (8 ISCAS-85 bases x 18 ABC restructurings = 144 HT-free and 14,400 HT-infected "
        "circuits, combinational gate-level). v2.0 keeps the formulation (the detector "
        "does not know "
        "whether a circuit is infected) and builds the infected circuits with the HTL on ISCAS-85 "
        "plus further combinational bases, with a rareness report per circuit."),
    "Seeker-Seq": (
        "v1 = Caroline van Neste's master's thesis (in progress; "
        "no unpublished results are cited). v2.0: sequential bases (ISCAS-89, ITC-99 and VTR "
        "sequential designs), counter and FSM-pattern triggers, multi-cycle rareness."),
}

ADDS = {
    "Seeker-Comb": (
        "Wide rare-AND triggers grown until the joint activation probability falls in a target "
        "band (p < 1e-2, 1e-3, 1e-4); sites chosen by SCOAP plus signal probability; per-circuit "
        "and pooled rareness report (answer_key/rareness.json). Round 4: 12 ABC functional "
        "restructurings of every clean and infected circuit (circuits_r/, gzip), each checked "
        "equivalent to its source."),
    "Seeker-Seq": (
        "Latch-based counter (time bomb) and FSM-pattern triggers at the netlist level; rareness "
        "reported as SCOAP SC/SO (structural heuristic) AND P(trigger high within N cycles) from "
        "multi-cycle simulation. Odin III's sequential SCOAP ignores set/reset/enable pins for "
        "controllability (Goldstein models them), and counts register-setting depth, not elapsed "
        "cycles, so it underestimates time-bomb rareness: P(fire within N) is the "
        "primary measure. Round 4: per-variant tuning so each fires within N = 1024 cycles with "
        "P in [1e-3, 1] (fast / mid / slow bands), victim chosen by observability, ITC-99 and "
        "VTR sequential bases, and the same 12 ABC restructurings."),
}


def family_manifest(
    family: str, bases: list[str], built: list[Built], clean: list[dict[str, str]], seed: int
) -> dict[str, object]:
    circuits: list[dict[str, str]] = [
        {"id": c["id"], "base": c["base"], "file": f"circuits/{c['id']}.blif"} for c in clean
    ]
    circuits += [
        {"id": b.circuit_id, "base": b.base, "file": f"circuits/{b.circuit_id}.blif"} for b in built
    ]
    trojans = sorted({b.trojan.id for b in built})
    catalogue = {b.trojan.id: b.trojan.to_dict() for b in built}
    infected = len(built)
    return {
        "family": family,
        "version": VERSION,
        "schema": 2,
        "v1_lineage": LINEAGE[family],
        "bases": sorted(bases),
        "restructurings": ["identity"],
        "trojans": trojans,
        "trojan_catalogue": catalogue,
        "circuits": sorted(circuits, key=lambda c: c["id"]),
        "mix": {
            "clean": len(clean),
            "infected": infected,
            "infected_fraction": infected / (infected + len(clean)) if infected + len(clean) else 0,
        },
        "seed": seed,
        "labels": "answer_key/labels.json (separate; a detector must not read answer_key/)",
    }


def family_readme(family: str) -> str:
    return (
        f"# {family} v{VERSION}\n\n"
        f"Lineage. {LINEAGE[family]}\n\n"
        f"What v{VERSION} adds. {ADDS[family]}\n\n"
        "Layout. `circuits/` holds clean and infected BLIF under opaque ids, `manifest.json` the "
        "family description, `answer_key/` the labels, per-circuit rareness records and the list "
        "of variants that could not be built (kept apart: a detector must not read it).\n"
    )
