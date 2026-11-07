"""Silicon-form goldens of a Seeker-Si rc2 tree (spec 2026-11-07 section 2.1).

The n200 builds write the golden of each base as the canonical gates BLIF. In a silicon tree the
golden is the base mapped to sky130 cells as well, so every file a detector sees has one form.
`silicon_goldens` maps each base's `golden.blif` (scratch) with a random ABC script, checks the
result equivalent to the golden, and overwrites the golden file in `circuits/` (and `circuits_v/`).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from lemanruss.htl import obfuscate as ob
from lemanruss.htl.n200check import run_cec
from lemanruss.htl.si_gates import check


def silicon_goldens(root: Path, seed: int) -> tuple[dict[str, str], dict[str, str]]:
    """({golden id: verdict}, {base: reason}). A base whose golden Odin III cannot map to cells
    (a tiny VerilogEval base that already fails to parse) is dropped from the tree's manifest:
    a golden in another form would put two forms in one release. A golden that maps but is not
    equivalent stops the run."""
    jobs = sorted((root / "answer_key" / "jobs").glob("*.json"))
    out: dict[str, str] = {}
    dropped: dict[str, str] = {}
    for job in jobs:
        rec = json.loads(job.read_text(encoding="utf-8"))
        base, gid = str(rec["base"]), str(rec["golden"])
        src = root / "scratch" / base / "golden.blif"
        rng = random.Random(f"{seed}:{base}:golden")
        got = ob.obfuscate(src, "silicon", rng, root / "scratch" / base, f"{gid}.gold")
        if isinstance(got, str):
            dropped[base] = got[:120]
            continue
        text = got[0]
        final = root / "scratch" / base / f"{gid}.gold.final.blif"
        final.write_text(text, encoding="utf-8")
        verdict = run_cec(src, final)[0]
        verilog, problems = check(text, None)
        if verdict != "equivalent" or problems:
            raise RuntimeError(f"{base}: golden {verdict} {problems}")
        (root / "circuits" / f"{gid}.blif").write_text(text, encoding="utf-8")
        (root / "circuits_v").mkdir(exist_ok=True)
        (root / "circuits_v" / f"{gid}.v").write_text(verilog, encoding="utf-8")
        out[gid] = verdict
    if dropped:
        man_path = root / "manifest.json"
        man = json.loads(man_path.read_text(encoding="utf-8"))
        man["circuits"] = [c for c in man["circuits"] if c["base"] not in dropped]
        man["bases"] = [b for b in man["bases"] if b not in dropped]
        man["goldens"] = {b: g for b, g in man["goldens"].items() if b not in dropped}
        man["dropped_bases"] = dropped
        man_path.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out, dropped
