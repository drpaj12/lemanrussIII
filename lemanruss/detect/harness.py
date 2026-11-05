"""Run a detector over the protocol splits and evaluate (spec section 3)."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from lemanruss.detect import metrics
from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile, Record, ref_view, view
from lemanruss.detect.splits import Split, all_splits

SEEDS = (0, 1, 2, 3, 4)


@dataclass
class FoldRun:
    split: str
    fold: int
    seed: int
    threshold: float
    scores: dict[str, float]  # test circuit id -> score (NaN dropped)
    failed: list[str]

    def to_json(self) -> dict[str, object]:
        return {
            "split": self.split, "fold": self.fold, "seed": self.seed,
            "threshold": self.threshold, "scores": self.scores, "failed": self.failed,
        }

    @staticmethod
    def from_json(d: dict[str, object]) -> FoldRun:
        scores = d["scores"]
        failed = d["failed"]
        assert isinstance(scores, dict) and isinstance(failed, list)
        return FoldRun(
            str(d["split"]), int(str(d["fold"])), int(str(d["seed"])), float(str(d["threshold"])),
            {str(k): float(v) for k, v in scores.items()}, [str(x) for x in failed],
        )


def _views(det: Detector, recs: list[Record]) -> list[CircuitFile]:
    return [ref_view(r) if det.needs_reference else view(r) for r in recs]


def _labels(recs: list[Record]) -> list[int]:
    return [int(r.infected) for r in recs]


def run_split(det: Detector, split: Split, seed: int) -> FoldRun:
    det.fit(_views(det, split.train), _labels(split.train), _views(det, split.val),
            _labels(split.val), seed)
    val_scores = det.score(_views(det, split.val))
    thr = metrics.val_threshold(val_scores, [r.infected for r in split.val])
    test_scores = det.score(_views(det, split.test))
    scores: dict[str, float] = {}
    failed: list[str] = []
    for s, r in zip(test_scores, split.test, strict=True):
        if math.isnan(s):
            failed.append(r.id)
        else:
            scores[r.id] = float(s)
    return FoldRun(split.name, split.fold, seed, thr, scores, failed)


def run_all(det: Detector, records: list[Record], split_name: str, out: Path,
            seeds: tuple[int, ...] = SEEDS) -> list[FoldRun]:
    """All folds x seeds (one seed for unseeded detectors); each fold-run is cached as JSON."""
    out.mkdir(parents=True, exist_ok=True)
    det.prepare(_views(det, records))
    runs: list[FoldRun] = []
    for split in all_splits(records, split_name):
        for seed in (seeds if det.seeded else (0,)):
            f = out / f"{det.name}-{split.name}-f{split.fold}-s{seed}.json"
            if f.is_file():
                runs.append(FoldRun.from_json(json.loads(f.read_text(encoding="utf-8"))))
                continue
            run = run_split(det, split, seed)
            f.write_text(json.dumps(run.to_json()), encoding="utf-8")
            runs.append(run)
    return runs


# ---- evaluation --------------------------------------------------------------------------------

def _fold_pairs(run: FoldRun, by_id: dict[str, Record]) -> list[tuple[Record, float]]:
    return [(by_id[i], s) for i, s in run.scores.items()]


def mean(xs: list[float]) -> float | None:
    return float(np.mean(xs)) if xs else None


def headline(runs: list[FoldRun], records: list[Record]) -> dict[str, object]:
    by_id = {r.id: r for r in records}
    au: list[float] = []
    tprs: list[float] = []
    fprs: list[float] = []
    f1s: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        pr = _fold_pairs(run, by_id)
        sc = [s for _, s in pr]
        y = [int(r.infected) for r, _ in pr]
        a = metrics.auroc(sc, y)
        tpr, fpr = metrics.rates(sc, y, run.threshold)
        if a is not None:
            au.append(a)
        if tpr is not None and fpr is not None:
            tprs.append(tpr)
            fprs.append(fpr)
            prev = sum(y) / len(y)
            f1s["release"].append(metrics.f1_at_prevalence(tpr, fpr, prev))
            for p in metrics.PREVALENCES:
                f1s[f"{int(p * 100)}"].append(metrics.f1_at_prevalence(tpr, fpr, p))
    return {
        "auroc": mean(au), "tpr": mean(tprs), "fpr": mean(fprs),
        "f1": {k: mean(v) for k, v in f1s.items()},
        "auroc_ci": auroc_ci(runs, by_id),
        "n_runs": len(runs), "n_failed": sum(len(r.failed) for r in runs),
    }


def auroc_ci(runs: list[FoldRun], by_id: dict[str, Record]) -> tuple[float, float] | None:
    """Bootstrap over bases; seeds averaged first so each circuit has one score per fold."""
    folds: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        for i, s in run.scores.items():
            folds[(run.split, run.fold)][i].append(s)
    units: list[dict[str, metrics.Pairs]] = []
    for per_id in folds.values():
        d: dict[str, metrics.Pairs] = defaultdict(list)
        for i, ss in per_id.items():
            r = by_id[i]
            d[r.base].append((float(np.mean(ss)), int(r.infected)))
        units.append(dict(d))
    return metrics.bootstrap_ci(units, metrics.pair_auroc)


def cell_auroc(
    runs: list[FoldRun],
    records: list[Record],
    pos_ok: Callable[[Record], bool],
    neg_ok: Callable[[Record], bool],
) -> float | None:
    """Mean over fold-runs of AUROC(positives passing pos_ok vs negatives passing neg_ok)."""
    by_id = {r.id: r for r in records}
    out: list[float] = []
    for run in runs:
        sc: list[float] = []
        y: list[int] = []
        for r, s in _fold_pairs(run, by_id):
            if r.infected and pos_ok(r):
                sc.append(s)
                y.append(1)
            elif not r.infected and neg_ok(r):
                sc.append(s)
                y.append(0)
        a = metrics.auroc(sc, y)
        if a is not None:
            out.append(a)
    return mean(out)


def per_base_auroc(runs: list[FoldRun], records: list[Record]) -> dict[str, float | None]:
    by_id = {r.id: r for r in records}
    acc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        for i, s in run.scores.items():
            acc[by_id[i].base][i].append(s)
    res: dict[str, float | None] = {}
    for b, per_id in acc.items():
        sc = [float(np.mean(v)) for v in per_id.values()]
        y = [int(by_id[i].infected) for i in per_id]
        res[b] = metrics.auroc(sc, y)
    return res
