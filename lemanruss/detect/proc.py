"""Seeker-Proc as a held-out challenge set (s6-methods.tex): detectors trained on the identity
forms of Seeker-Comb and Seeker-Seq score the six pilot2 circuits; raw outcomes, no statistics.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from lemanruss.detect import metrics
from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile, Record, Release, ref_view, view
from lemanruss.detect.ffrange import classify, ff_range
from lemanruss.detect.run import make_detector
from lemanruss.detect.size_only import size_stats
from lemanruss.detect.splits import make_folds


def run_proc(det_name: str, releases: list[Release], proc: Release, seeds: tuple[int, ...],
             out: Path) -> dict[str, object]:
    train: list[Record] = []
    val: list[Record] = []
    for rel in releases:
        folds = make_folds(rel.bases())
        val_b = set(folds[1])
        ident = [r for r in rel.records if r.form == "identity"]
        val += [r for r in ident if r.base in val_b]
        train += [r for r in ident if r.base not in val_b and r.base not in set(folds[0])]
    scores: dict[str, list[float]] = {r.id: [] for r in proc.records}
    thr: list[float] = []
    det: Detector = make_detector(det_name)

    def views(rs: list[Record]) -> list[CircuitFile]:
        return [ref_view(r) if det.needs_reference else view(r) for r in rs]

    det.prepare(views(train + val + proc.records))
    rng = ff_range([size_stats(r.path)[2] for r in train])
    for seed in seeds if det.seeded else (0,):
        det = make_detector(det_name)
        det.fit(views(train), [int(r.infected) for r in train], views(val),
                [int(r.infected) for r in val], seed)
        vs = det.score(views(val))
        clean = [s for s, r in zip(vs, val, strict=True) if not r.infected and not math.isnan(s)]
        thr.append(metrics.threshold_at_fpr(clean))
        for s, r in zip(det.score(views(proc.records)), proc.records, strict=True):
            scores[r.id].append(s)
    res: dict[str, object] = {"detector": det_name, "seeds": list(seeds), "circuits": {}}
    circuits: dict[str, object] = {}
    t = sum(thr) / len(thr)
    for r in proc.records:
        ss = scores[r.id]
        ok = [x for x in ss if not math.isnan(x)]
        m = sum(ok) / len(ok) if ok else None
        ff = size_stats(r.path)[2]
        flag = None if m is None else classify(m, t, ff, rng)
        circuits[r.id] = {"score": m, "flag": flag, "ff_count": ff,
                          "infected": r.infected, "base": r.base}
    res["circuits"] = circuits
    res["threshold"] = t
    res["train_ff_range"] = None if rng is None else list(rng)
    (out / f"proc-{det_name}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res
