"""Within-Proc detection (H-P2 proper): leave-one-base-out on the Seeker-Proc release.

For one form (gates, lut4 or lut6) and one held-out base, a detector is trained on the circuits
of the other bases of that form and scores the held-out base. A fifth of the training circuits
(stratified by label, fixed seed) is held back as the validation set for model selection. Only
AUROC is reported, so no threshold is used. With three bases the base bootstrap is meaningless:
the interval is a bootstrap over circuits of the pooled held-out scores (each scored by a model
that never saw its base), and W/L/T against the size control counts the three bases.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from lemanruss.detect import metrics
from lemanruss.detect.data import CircuitFile, Record, Release, ref_view, view
from lemanruss.detect.run import make_detector

VAL_FRACTION = 0.2
VAL_SEED = 1
ERROR_KEY = "_error"
DETECTORS = ("size", "ffcount", "classhist", "sanity", "rare", "graphlet-b",
             "gnn-a-nosc", "gnn-a", "gnn-yasaei")


def split_train_val(records: Sequence[Record], seed: int = VAL_SEED
                    ) -> tuple[list[Record], list[Record]]:
    """Stratified (by infected) deterministic split; each side keeps at least one of each label
    when the class has two or more circuits."""
    rng = random.Random(seed)
    train: list[Record] = []
    val: list[Record] = []
    for label in (False, True):
        grp = sorted((r for r in records if r.infected == label), key=lambda r: r.id)
        rng.shuffle(grp)
        n_val = max(1, round(VAL_FRACTION * len(grp))) if len(grp) > 1 else 0
        val += grp[:n_val]
        train += grp[n_val:]
    return train, val


def run_cell(det_name: str, records: Sequence[Record], form: str, held: str,
             seeds: Sequence[int]) -> dict[str, float]:
    """Scores (id -> mean over seeds, NaN dropped) of the held-out base of one form."""
    recs = [r for r in records if r.form == form]
    test = [r for r in recs if r.base == held]
    train, val = split_train_val([r for r in recs if r.base != held])
    det = make_detector(det_name)

    def views(rs: Sequence[Record]) -> list[CircuitFile]:
        return [ref_view(r) if det.needs_reference else view(r) for r in rs]

    det.prepare(views(train + val + test))
    acc: dict[str, list[float]] = defaultdict(list)
    for seed in (seeds if det.seeded else (0,)):
        det = make_detector(det_name)
        det.fit(views(train), [int(r.infected) for r in train], views(val),
                [int(r.infected) for r in val], seed)
        for s, r in zip(det.score(views(test)), test, strict=True):
            if s == s:
                acc[r.id].append(float(s))
    return {i: float(np.mean(v)) for i, v in acc.items()}


def pooled_ci(pairs: list[tuple[float, int]], reps: int = 1000,
              seed: int = 0) -> tuple[float, float] | None:
    """95% percentile bootstrap of the pooled AUROC, resampling infected and clean circuits
    separately (the class sizes stay fixed)."""
    pos = [p for p in pairs if p[1] == 1]
    neg = [p for p in pairs if p[1] == 0]
    if not pos or not neg:
        return None
    rng = random.Random(seed)
    vals: list[float] = []
    for _ in range(reps):
        sample = [rng.choice(pos) for _ in pos] + [rng.choice(neg) for _ in neg]
        a = metrics.pair_auroc(sample)
        if a is not None:
            vals.append(a)
    if not vals:
        return None
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def summarise(scores: dict[str, dict[str, float]], records: Sequence[Record]
              ) -> dict[str, object]:
    """One (detector, form): pooled AUROC with CI, per-base AUROC, scored/total counts."""
    by_id = {r.id: r for r in records}
    pairs: list[tuple[float, int]] = []
    per_base: dict[str, float | None] = {}
    n_total = 0
    for base, sc in sorted(scores.items()):
        bp = [(s, int(by_id[i].infected)) for i, s in sc.items()]
        pairs += bp
        per_base[base] = metrics.pair_auroc(bp)
        n_total += sum(1 for r in records if r.base == base)
    return {"auroc": metrics.pair_auroc(pairs), "ci": pooled_ci(pairs),
            "per_base": per_base, "n_scored": len(pairs), "n_total": n_total}


def run_form(det_name: str, rel: Release, form: str, seeds: Sequence[int],
             out: Path) -> dict[str, object]:
    """All held-out bases of one form; each cell's scores are cached as JSON under `out`."""
    out.mkdir(parents=True, exist_ok=True)
    recs = [r for r in rel.records if r.form == form]
    scores: dict[str, dict[str, float]] = {}
    errors: dict[str, str] = {}
    for held in sorted({r.base for r in recs}):
        f = out / f"{det_name}-{form}-{held}.json"
        if f.is_file():
            cell = json.loads(f.read_text("utf-8"))
        else:
            try:
                cell = run_cell(det_name, rel.records, form, held, seeds)
            except ValueError as exc:  # e.g. no scorable training circuit for this detector
                cell = {ERROR_KEY: str(exc)}
            f.write_text(json.dumps(cell), encoding="utf-8")
        if ERROR_KEY in cell:
            errors[held] = str(cell[ERROR_KEY])
            cell = {}
        scores[held] = {k: float(v) for k, v in cell.items()}
    res = summarise(scores, recs)
    res["errors"] = errors
    return res


def _fmt(x: object) -> str:
    return "n/a" if not isinstance(x, float) else f"{x:.3f}"


def tables(out: Path, forms: Sequence[str] = ("gates", "lut4", "lut6")) -> str:
    """Markdown: per form, pooled AUROC [95% CI over circuits], per-base AUROC, W/L/T vs the size
    control over the held-out bases, the strict label, and scored/total."""
    from lemanruss.detect.report import label

    res = {p.stem[len("within-"):]: json.loads(p.read_text("utf-8"))
           for p in sorted(out.glob("within-*.json"))}
    order = [d for d in DETECTORS if d in res]
    lines: list[str] = []
    for form in forms:
        size = res.get("size", {}).get(form, {})
        control = {b: v for b, v in size.get("per_base", {}).items() if isinstance(v, float)}
        bases = sorted({b for d in order for b in res[d].get(form, {}).get("per_base", {})})
        lines += [f"### Form {form}", "",
                  "| detector | pooled AUROC [95% CI] | " + " | ".join(bases)
                  + " | W/L/T vs size | label | scored |",
                  "|---|---|" + "---|" * len(bases) + "---|---|---|"]
        for d in order:
            r = res[d].get(form)
            if not r:
                continue
            ci = r["ci"]
            ci_t = None if ci is None else (float(ci[0]), float(ci[1]))
            ci_s = "n/a" if ci_t is None else f"[{ci_t[0]:.3f}, {ci_t[1]:.3f}]"
            pb = {b: v for b, v in r["per_base"].items() if isinstance(v, float)}
            wl = "control" if d == "size" else "{}/{}/{}".format(*metrics.wlt(pb, control))
            lines.append(f"| {d} | {_fmt(r['auroc'])} {ci_s} | "
                         + " | ".join(_fmt(r["per_base"].get(b)) for b in bases)
                         + f" | {wl} | {label(ci_t)} | {r['n_scored']}/{r['n_total']} |")
            for b, msg in r.get("errors", {}).items():
                lines.append(f"<!-- {d} {form} {b}: {msg} -->")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--detector", action="append", default=[])
    ap.add_argument("--forms", default="gates,lut4,lut6")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--tables", action="store_true", help="print the markdown tables of --out")
    args = ap.parse_args(argv)
    if args.tables:
        print(tables(args.out))
        return
    rel = Release(args.release, "Proc")
    seeds = tuple(int(x) for x in args.seeds.split(","))
    for det in args.detector or list(DETECTORS):
        res: dict[str, object] = {}
        for form in args.forms.split(","):
            res[form] = run_form(det, rel, form, seeds, args.out / "cells")
        (args.out / f"within-{det}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(det, json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
