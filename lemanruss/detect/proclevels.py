"""Levels 1 to 3 for Seeker-Proc from `procrun` cells and the processor regions.

    python -m lemanruss.detect.proclevels --release R --regions regions.json --cells DIR \
        --detector NAME --out levels.json [--range-check]

Per form, the circuits of all held-out cores are pooled; a circuit is scored when the detector
ran on it (a cell without an error). With `--range-check` a circuit whose flip-flop count lies
outside the detector's training range is left out and counted (`out_of_range`), as in the
confusion matrix (spec `2026-11-03-seeker-proc-rc1.md` section 6). A flagged circuit makes the
detector's claims if it has any (a localising detector) and otherwise one claim naming no cell
(level 1 only is meaningful then). Regions come from `lemanruss.score.proc_regions`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lemanruss.detect import metrics
from lemanruss.score import levels
from lemanruss.score.levels import Circ


def circs_from_cells(cells: list[dict[str, Any]], bases: list[str], regions: dict[str, Any],
                     range_check: bool) -> tuple[list[Circ], dict[str, Any]]:
    out: list[Circ] = []
    pairs: list[tuple[float, int]] = []
    n_oor = n_err = 0
    for base, cell in zip(bases, cells, strict=True):
        if "error" in cell:
            n_err += 1
            continue
        for cid, e in sorted(cell["circuits"].items()):
            if e["score"] is None:
                continue
            if range_check and not e["in_range"]:
                n_oor += 1
                continue
            pairs.append((float(e["score"]), int(e["infected"])))
            regs: tuple[frozenset[str], ...] = ()
            n_cells = 0
            if e["infected"]:
                reg = regions[cid]
                regs = tuple(frozenset(t["nets"]) for t in reg["trojans"])
                n_cells = int(reg["n_nets"])
            claims: tuple[frozenset[str], ...] = ()
            if e["flag"]:
                claims = tuple(frozenset(c) for c in e.get("claims", [])) or (frozenset(),)
            out.append(Circ(cid, base, regs, claims, n_cells))
    au = metrics.auroc([s for s, _ in pairs], [y for _, y in pairs]) if pairs else None
    return out, {"auroc": au, "n_scored": len(pairs), "out_of_range": n_oor, "cell_errors": n_err}


def report(cells_dir: Path, detector: str, form: str, regions: dict[str, Any],
           range_check: bool) -> dict[str, Any]:
    files = sorted(cells_dir.glob(f"{detector}-{form}-*.json"))
    cells = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    bases = [f.name[len(f"{detector}-{form}-"):-len(".json")] for f in files]
    circs, meta = circs_from_cells(cells, bases, regions, range_check)
    res: dict[str, Any] = {"detector": detector, "form": form, "bases": bases, **meta}
    if circs:
        summ = levels.summarise(circs, levels.chance_expectation(circs))
        res["levels"] = {str(k): v for k, v in summ.items()}
    return res


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", type=Path, required=True)
    ap.add_argument("--cells", type=Path, required=True)
    ap.add_argument("--detector", action="append", required=True)
    ap.add_argument("--forms", default="gates,lut4,lut6")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--range-check", action="store_true")
    a = ap.parse_args(argv)
    regions = json.loads(a.regions.read_text(encoding="utf-8"))
    rows = [report(a.cells, d, f, regions, a.range_check)
            for d in a.detector for f in a.forms.split(",")]
    a.out.write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
