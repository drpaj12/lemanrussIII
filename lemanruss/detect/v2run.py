"""Seeker v2.0 full-set run: every detector over the Comb or Seq release, base split.

    python -m lemanruss.detect.v2run --detector gnn-a --family Seq --release <dir> --out <dir>

The release is the private full one (all benchmarks, four targets K4 / K6 / G / S). The golden
and the silicon golden of each benchmark are references, never test circuits. Splits: five folds
over benchmarks (`splits.make_folds`), one fold tests, the next validates, the rest train; the
threshold is the 5% false-positive value on the validation fold. One seed, the budget of the
earlier runs (LEMANRUSS_EPOCHS, LEMANRUSS_MAX_TRAIN). Each fold is cached as JSON (resumable).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from lemanruss.detect import harness
from lemanruss.detect.data import Record, Release
from lemanruss.detect.run import make_detector

TARGETS = ("K4", "K6", "G", "S")


def v2_records(rel: Release) -> list[Record]:
    """Test records of a v2.0 release: goldens dropped, the silicon reference set to its golden."""
    sets = json.loads((rel.root / "answer_key" / "sets.json").read_text(encoding="utf-8"))
    path = {r.id: r.path for r in rel.records}
    out: list[Record] = []
    for r in rel.records:
        if r.set not in TARGETS:
            continue
        if r.set == "S":
            gold = sets[r.base]["sets"]["S"].get("golden")
            if gold in path:
                r = dataclasses.replace(r, reference=path[gold])
        out.append(r)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True)
    ap.add_argument("--family", required=True, choices=("Comb", "Seq"))
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--name", help="output sub-directory (default: the family)")
    ap.add_argument("--exclude", type=Path, help="file with one circuit id per line to leave out")
    args = ap.parse_args(argv)
    rel = Release(args.release, args.family)
    recs = v2_records(rel)
    if args.exclude is not None:
        gone = set(args.exclude.read_text(encoding="utf-8").split())
        recs = [r for r in recs if r.id not in gone]
    det = make_detector(args.detector)
    runs = harness.run_all(det, recs, "base", args.out / (args.name or args.family), (0,))
    print(args.detector, args.family, len(recs), "records", len(runs), "folds", flush=True)


if __name__ == "__main__":
    main()
