"""Seeker-Proc, leave-one-base-out, with the circuit threshold, the range flag and claims.

For one form and one held-out core a detector trains on the other two cores (a stratified fifth is
the validation set, `within.split_train_val`), the threshold is the 5% false-positive value on the
validation circuits, and every held-out circuit gets a score (mean over seeds), a flag with and
without the flip-flop range check (`ffrange`) and, for a localising detector, claims by the rule
of `localise` at the default z (the key of a processor release has no Trojan regions, so z* cannot
be tuned and level 3 cannot be scored; level 2 uses the number of Trojans of the key).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from lemanruss.detect import localise, metrics
from lemanruss.detect.data import CircuitFile, Record, Release, ref_view, view
from lemanruss.detect.ffrange import ff_range
from lemanruss.detect.netlist import parse
from lemanruss.detect.run import make_detector
from lemanruss.detect.size_only import size_stats
from lemanruss.detect.within import DETECTORS, split_train_val


def run_cell(det_name: str, records: list[Record], form: str, held: str,
             seeds: tuple[int, ...]) -> dict[str, Any]:
    recs = [r for r in records if r.form == form]
    test = [r for r in recs if r.base == held]
    train, val = split_train_val([r for r in recs if r.base != held])
    det = make_detector(det_name)

    def views(rs: list[Record]) -> list[CircuitFile]:
        return [ref_view(r) if det.needs_reference else view(r) for r in rs]

    det.prepare(views(train + val + test))
    rng = ff_range([size_stats(r.path)[2] for r in train])
    vs: dict[str, list[float]] = defaultdict(list)
    ts: dict[str, list[float]] = defaultdict(list)
    nodes: dict[str, np.ndarray] = {}
    for seed in (seeds if det.seeded else (0,)):
        det = make_detector(det_name)
        det.fit(views(train), [int(r.infected) for r in train], views(val),
                [int(r.infected) for r in val], seed)
        for s, r in zip(det.score(views(val)), val, strict=True):
            vs[r.id].append(s)
        for s, r in zip(det.score(views(test)), test, strict=True):
            ts[r.id].append(s)
        if det.localises and not nodes:
            for r in test:
                ns = det.node_scores(view(r))
                if ns is not None:
                    nodes[r.id] = ns
    val_mean = [float(np.nanmean(vs[r.id])) for r in val]
    thr = metrics.val_threshold(val_mean, [r.infected for r in val])
    out: dict[str, Any] = {"threshold": thr, "train_ff_range": None if rng is None else list(rng),
                           "circuits": {}}
    for r in test:
        ok = [x for x in ts[r.id] if not math.isnan(x)]
        m = float(np.mean(ok)) if ok else None
        ff = size_stats(r.path)[2]
        lo, hi = rng if rng is not None else (ff, ff)
        entry: dict[str, Any] = {"score": m, "ff": ff, "infected": r.infected,
                                 "n_trojans": r.n_trojans, "in_range": lo <= ff <= hi,
                                 "flag": None if m is None else m >= thr}
        if m is not None and m >= thr and r.id in nodes:
            entry["claims"] = localise.claims_from_scores(parse(r.path), nodes[r.id],
                                                          localise.DEFAULT_Z)
        out["circuits"][r.id] = entry
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--detector", action="append", default=[])
    ap.add_argument("--forms", default="gates,lut4,lut6")
    ap.add_argument("--seeds", default="0,1,2")
    a = ap.parse_args(argv)
    rel = Release(a.release, "Proc")
    seeds = tuple(int(x) for x in a.seeds.split(","))
    a.out.mkdir(parents=True, exist_ok=True)
    for d in a.detector or list(DETECTORS):
        for form in a.forms.split(","):
            for held in sorted({r.base for r in rel.records if r.form == form}):
                f = a.out / f"{d}-{form}-{held}.json"
                if f.is_file():
                    continue
                try:
                    cell = run_cell(d, rel.records, form, held, seeds)
                except ValueError as exc:
                    cell = {"error": str(exc)}
                f.write_text(json.dumps(cell), encoding="utf-8")
                print(d, form, held, flush=True)


if __name__ == "__main__":
    main()
