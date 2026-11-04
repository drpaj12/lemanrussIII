"""Command line: run a detector over a release and write the evaluation JSON.

    python -m lemanruss.detect.run --detector size --family Comb --release <dir> --out <dir>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lemanruss.detect import harness
from lemanruss.detect.api import Detector
from lemanruss.detect.data import Release


def make_detector(name: str) -> Detector:
    if name == "size":
        from lemanruss.detect.size_only import SizeOnly

        return SizeOnly()
    if name == "classhist":
        from lemanruss.detect.classhist import ClassHist

        return ClassHist()
    if name == "ffcount":
        from lemanruss.detect.ffcount import FfCount

        return FfCount()
    if name == "sanity":
        from lemanruss.detect.sanity import Sanity

        return Sanity()
    if name == "rare":
        from lemanruss.detect.rare_scoap import RareScoap

        return RareScoap()
    if name in ("gnn-yasaei", "gnn-a", "gnn-a-nosc"):
        from lemanruss.detect.gnn import make_gnn

        return make_gnn(name)
    if name == "graphlet-b":
        from lemanruss.detect.graphlet_b import GraphletB

        return GraphletB()
    raise SystemExit(f"unknown detector {name}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True)
    ap.add_argument("--family", default="")
    ap.add_argument("--release", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--splits", default="")
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--proc", type=Path, help="pilot2 release dir: run the challenge set instead")
    ap.add_argument("--train", type=Path, nargs="*", default=[],
                    help="with --proc: Comb and Seq release dirs to train on")
    args = ap.parse_args(argv)
    if args.proc is not None:
        from lemanruss.detect.proc import run_proc

        trains = [Release(p, "Comb" if "comb" in p.name else "Seq") for p in args.train]
        seeds = tuple(int(x) for x in args.seeds.split(","))
        print(json.dumps(run_proc(args.detector, trains, Release(args.proc, "Proc"), seeds,
                                  args.out), indent=1))
        return
    rel = Release(args.release, args.family)
    det = make_detector(args.detector)
    summary: dict[str, object] = {"seeds": args.seeds}
    cfg = getattr(det, "cfg", None)
    if cfg is not None:
        summary["settings"] = {"epochs": cfg.epochs, "batch": cfg.batch, "lr": cfg.lr}
    default = "base,set" if any(r.set in ("K4", "K6", "G") for r in rel.records) else "base,lut"
    for split in (args.splits or default).split(","):
        seeds = tuple(int(x) for x in args.seeds.split(","))
        runs = harness.run_all(
            det, rel.records, split, args.out / "runs" / args.release.name, seeds)
        for name in sorted({r.split for r in runs}):
            summary[name] = harness.headline([r for r in runs if r.split == name], rel.records)
    (args.out / f"{args.detector}-{args.release.name}.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
