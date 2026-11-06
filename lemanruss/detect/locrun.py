"""Localising run: circuit scores, flags and claims per circuit, base split, five folds.

    python -m lemanruss.detect.locrun run --detector gnn-a --family Comb --release <dir> \
        --regions <regions.json> --out <dir>
    python -m lemanruss.detect.locrun report --release <dir> --regions <regions.json> \
        --out <dir> --detector gnn-a

A fold: fit on the training bases, set the circuit threshold on the validation bases (5% false
positives), tune z* on the validation bases (`localise.tune_z`), then score the test bases; each
flagged test circuit gets claims by the rule of `localise`. Seed 0, the budget of the earlier
runs (LEMANRUSS_EPOCHS, LEMANRUSS_MAX_TRAIN). Saved per fold as JSON and resumable.
"""

from __future__ import annotations

import argparse
import json
import math
import resource
import time
from pathlib import Path
from typing import Any

from lemanruss.detect import localise, metrics
from lemanruss.detect.data import CircuitFile, Record, Release, ref_view, view
from lemanruss.detect.netlist import parse
from lemanruss.detect.run import make_detector
from lemanruss.detect.sirelease import SiRelease
from lemanruss.detect.splits import all_splits
from lemanruss.score import levels
from lemanruss.score.levels import Circ


def load_regions(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return out


def trojan_regions(reg: dict[str, Any], cid: str) -> tuple[frozenset[str], ...]:
    return tuple(frozenset(t["nets"]) for t in reg[cid]["trojans"])


def run(det_name: str, rel: Any, regions: dict[str, Any], out: Path,
        split: str = "base", seed: int = 0) -> None:
    out.mkdir(parents=True, exist_ok=True)
    det = make_detector(det_name)
    def views(rs: list[Record]) -> list[CircuitFile]:
        return [ref_view(r) if det.needs_reference else view(r) for r in rs]

    det.prepare(views(rel.records))
    sps = rel.splits() if hasattr(rel, "splits") else all_splits(rel.records, split)
    for sp in sps:
        f = out / f"{det_name}-{sp.name}-f{sp.fold}-s{seed}.json"
        if f.is_file():
            continue
        det = make_detector(det_name)
        det.fit(views(sp.train), [int(r.infected) for r in sp.train], views(sp.val),
                [int(r.infected) for r in sp.val], seed)
        vs = det.score(views(sp.val))
        thr = metrics.val_threshold(vs, [r.infected for r in sp.val])
        items = []
        for s, r in zip(vs, sp.val, strict=True):
            if det.localises and r.infected and not math.isnan(s) and s >= thr \
                    and r.id in regions:
                ns = det.node_scores(view(r))
                if ns is not None:
                    items.append((parse(r.path), ns, trojan_regions(regions, r.id)))
        z = localise.tune_z(items)
        scores: dict[str, float] = {}
        claims: dict[str, list[list[str]]] = {}
        failed: list[str] = []
        for s, r in zip(det.score(views(sp.test)), sp.test, strict=True):
            if math.isnan(s):
                failed.append(r.id)
                continue
            scores[r.id] = float(s)
            if s >= thr and det.localises:
                ns = det.node_scores(view(r))
                claims[r.id] = ([] if ns is None
                                else localise.claims_from_scores(parse(r.path), ns, z))
            elif s >= thr:
                claims[r.id] = []
        f.write_text(json.dumps({
            "fold": sp.fold, "threshold": thr, "z": z, "n_val_tuned": len(items),
            "scores": scores, "claims": claims, "failed": failed,
            "localises": det.localises}), encoding="utf-8")
        print(det_name, "fold", sp.fold, "z", z, "tuned on", len(items), flush=True)


def circs_of(rel: Any, regions: dict[str, Any], folds: list[dict[str, Any]]) -> list[Circ]:
    by_id = {r.id: r for r in rel.records}
    out: list[Circ] = []
    for fd in folds:
        for cid in fd["scores"]:
            r = by_id[cid]
            regs = trojan_regions(regions, cid) if r.infected else ()
            if r.infected and not regs:
                continue
            cl = tuple(frozenset(c) for c in fd["claims"].get(cid, []))
            if cid in fd["claims"] and not cl:  # flagged: a claim with no cells (level 1)
                cl = (frozenset(),)
            n = int(regions[cid]["n_nets"]) if r.infected else 0
            out.append(Circ(cid, r.base, regs, cl, n))
    return out


def report(det_name: str, rel: Any, regions: dict[str, Any], out: Path,
           seed: int = 0) -> dict[str, Any]:
    files = sorted(out.glob(f"{det_name}-base-f*-s{seed}.json"))
    folds = [json.loads(p.read_text("utf-8")) for p in files]
    circs = circs_of(rel, regions, folds)
    by_id = {r.id: r for r in rel.records}
    pairs = [(by_id[c.cid].infected, folds_score(folds, c.cid)) for c in circs]
    au = metrics.auroc([s for _, s in pairs], [int(i) for i, _ in pairs])
    summ = levels.summarise(circs, levels.chance_expectation(circs))
    nclaims = [len(c.claims) for c in circs if c.claims]
    return {"detector": det_name, "n_folds": len(folds), "n_circuits": len(circs),
            "n_failed": sum(len(f["failed"]) for f in folds), "auroc": au,
            "localises": bool(folds and folds[0].get("localises", True)),
            "z_by_fold": [f["z"] for f in folds],
            "claims_per_flagged_circuit": (sum(nclaims) / len(nclaims)) if nclaims else None,
            "levels": {str(k): v for k, v in summ.items()}}


def folds_score(folds: list[dict[str, Any]], cid: str) -> float:
    for f in folds:
        if cid in f["scores"]:
            return float(f["scores"][cid])
    raise KeyError(cid)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "report"))
    ap.add_argument("--detector", required=True)
    ap.add_argument("--family", default="")
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--regions", type=Path, required=True)
    ap.add_argument("--si", action="store_true", help="release is Seeker-Si")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    rel: Any = SiRelease(args.release) if args.si else Release(args.release, args.family)
    if args.si and not args.regions.is_file():
        args.regions.write_text(json.dumps(rel.regions()), encoding="utf-8")
    regions = load_regions(args.regions)
    t0 = time.time()
    if args.cmd == "run":
        run(args.detector, rel, regions, args.out)
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        (args.out / f"{args.detector}-time.json").write_text(
            json.dumps({"wall_s": time.time() - t0, "peak_rss_mb": peak}), encoding="utf-8")
    else:
        res = report(args.detector, rel, regions, args.out)
        (args.out / f"{args.detector}-levels.json").write_text(json.dumps(res, indent=1),
                                                             encoding="utf-8")
        print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
