"""Markdown tables of the detector results (docs/results-detectors.md) from stored fold-runs."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from lemanruss.detect import harness, metrics
from lemanruss.detect.data import Record, Release
from lemanruss.detect.harness import FoldRun

DETECTORS = ["size", "sanity", "classhist", "rare", "gnn-yasaei", "gnn-a", "graphlet-b"]


def load_runs(out: Path, release: str, det: str, split: str) -> list[FoldRun]:
    d = out / "runs" / release
    return [
        FoldRun.from_json(json.loads(f.read_text(encoding="utf-8")))
        for f in sorted(d.glob(f"{det}-{split}-f*-s*.json"))
    ]


def fmt(x: float | None, nd: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def label(ci: tuple[float, float] | None) -> str:
    """Strict label from the AUROC interval (CAD reporting convention)."""
    if ci is None:
        return "n/a"
    lo, hi = ci
    if lo > 0.5:
        return "ABOVE CHANCE"
    if hi < 0.5:
        return "BELOW CHANCE"
    return "INCONCLUSIVE"


def _f(h: dict[str, object], k: str) -> float | None:
    v = h[k]
    assert v is None or isinstance(v, float)
    return v


def split_names(rel: Release) -> list[str]:
    if any(r.set in ("K4", "K6", "G") for r in rel.records):
        return ["base", "set-K4", "set-K6", "set-G"]
    return ["base", "lut"]


def headline_table(out: Path, rel: Release, release: str, dets: list[str]) -> str:
    rows = [
        "| detector | split | AUROC [95% CI] | TPR | FPR | F1 rel | F1 10% | F1 30% | "
        "F1 50% | F1 70% | W/L/T vs size | label |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for split in split_names(rel):
        control = harness.per_base_auroc(load_runs(out, release, "size", split), rel.records)
        for det in dets:
            runs = load_runs(out, release, det, split)
            if not runs:
                continue
            h = harness.headline(runs, rel.records)
            f1 = h["f1"]
            assert isinstance(f1, dict)
            ci = h["auroc_ci"]
            assert ci is None or isinstance(ci, tuple)
            w, lo, t = metrics.wlt(harness.per_base_auroc(runs, rel.records), control)
            wlt_s = "control" if det == "size" else f"{w}/{lo}/{t}"
            ci_s = "n/a" if ci is None else f"[{ci[0]:.3f}, {ci[1]:.3f}]"
            rows.append(
                f"| {det} | {split} | {fmt(_f(h, 'auroc'))} {ci_s} | {fmt(_f(h, 'tpr'))} | "
                f"{fmt(_f(h, 'fpr'))} | {fmt(f1.get('release'))} | {fmt(f1.get('10'))} | "
                f"{fmt(f1.get('30'))} | {fmt(f1.get('50'))} | {fmt(f1.get('70'))} | "
                f"{wlt_s} | {label(ci)} |"
            )
    return "\n".join(rows)


def breakdown_table(out: Path, rel: Release, release: str, dets: list[str], split: str,
                    key: str) -> str:
    recs = rel.records
    if key == "form":
        cells = sorted({r.form for r in recs})
    elif key == "variant":
        cells = sorted({r.variant for r in recs if r.infected and r.variant})
    elif key == "set":
        cells = sorted({r.set for r in recs if r.infected and r.set})
    else:
        cells = ["1", "2", "3"]
    rows = ["| detector | " + " | ".join(cells) + " |", "|---|" + "---|" * len(cells)]
    for det in dets:
        runs = load_runs(out, release, det, split)
        if not runs:
            continue
        vals = []
        for c in cells:
            def pos(r: Record, c: str = c) -> bool:
                if key == "form":
                    return r.form == c
                if key == "variant":
                    return r.variant == c
                if key == "set":
                    return r.set == c
                return min(r.n_trojans, 3) == int(c)

            def neg(r: Record, c: str = c) -> bool:
                if key == "form":
                    return r.form == c
                return r.set == c if key == "set" else True

            vals.append(fmt(harness.cell_auroc(runs, recs, pos, neg), 2))
        rows.append(f"| {det} | " + " | ".join(vals) + " |")
    return "\n".join(rows)


def run_summary(out: Path, release: str, det: str) -> dict[str, object]:
    f = out / f"{det}-{release}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}


def failed_counts(out: Path, release: str, dets: list[str]) -> dict[str, int]:
    res: dict[str, int] = defaultdict(int)
    for det in dets:
        for split in ("base", "lut", "set-K4", "set-K6", "set-G"):
            for run in load_runs(out, release, det, split):
                res[det] += len(run.failed)
    return dict(res)


def results_tables(out: Path, releases: list[tuple[str, str, Path]], dets: list[str]) -> str:
    """The tables part of docs/results-detectors.md: (family, release name, release dir)."""
    parts: list[str] = []
    for family, name, root in releases:
        rel = Release(root, family)
        present = [d for d in dets if len(load_runs(out, name, d, "base")) >= 5]
        parts.append(f"## {family} ({name})\n")
        parts.append(f"Circuits {len(rel.records)}, bases {len(rel.bases())}.\n")
        parts.append("### Headline (means over folds and seeds; AUROC with 95% base-bootstrap)\n")
        parts.append(headline_table(out, rel, name, present) + "\n")
        for split in split_names(rel):
            keys = [("variant", "rareness band / variant")]
            if len({r.form for r in rel.records}) > 1:
                keys.insert(0, ("form", "form"))
            if any(r.set for r in rel.records):
                keys.append(("set", "set"))
            if any(r.n_trojans > 1 for r in rel.records):
                keys.append(("trojans", "Trojan count"))
            for key, title in keys:
                t = breakdown_table(out, rel, name, present, split, key)
                if t.count("\n") > 1 and len(t.split("\n")[0].split("|")) > 3:
                    parts.append(f"### AUROC by {title}, {split} split\n")
                    parts.append(t + "\n")
        nf = failed_counts(out, name, present)
        if any(nf.values()):
            parts.append("Circuits not scored (Odin III timeout or refusal; never imputed): "
                         + ", ".join(f"{k} {v}" for k, v in nf.items() if v) + ".\n")
    return "\n".join(parts)


def paper_table(out: Path, entries: list[tuple[str, str, Path]], dets: list[str],
                tex: Path, js: Path) -> None:
    """Base-split AUROC [95% CI] and W/L/T per detector and release; LaTeX and JSON."""
    summary: dict[str, dict[str, object]] = {}
    for family, name, root in entries:
        rel = Release(root, family)
        control = harness.per_base_auroc(load_runs(out, name, "size", "base"), rel.records)
        for det in dets:
            runs = load_runs(out, name, det, "base")
            if len(runs) < 5:
                continue
            h = harness.headline(runs, rel.records)
            w, lo, t = metrics.wlt(harness.per_base_auroc(runs, rel.records), control)
            summary.setdefault(det, {})[name] = {
                "auroc": h["auroc"], "ci": h["auroc_ci"], "wlt": [w, lo, t], "tpr": h["tpr"],
                "fpr": h["fpr"], "f1": h["f1"],
            }
    js.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    names = [n for _, n, _ in entries]
    head = " & ".join(f"{n.split('-')[1].capitalize()} {n.split('-')[-1]}" for n in names)
    lines = [
        "% Generated by lemanruss.detect.report.paper_table; do not edit by hand.",
        "\\begin{tabular}{@{}l" + "r" * len(names) + "@{}}\\toprule",
        f"Detector & {head} \\\\\\midrule",
    ]
    for det in dets:
        if det not in summary:
            continue
        cells = []
        for n in names:
            e = summary[det].get(n)
            if not isinstance(e, dict):
                cells.append("--")
                continue
            ci = e["ci"]
            assert isinstance(ci, tuple | list)
            a = e["auroc"]
            assert isinstance(a, float)
            cells.append(f"{a:.2f} [{ci[0]:.2f}, {ci[1]:.2f}]")
        lines.append(f"{det} & " + " & ".join(cells) + " \\\\")
    lines.append("\\bottomrule\\end{tabular}")
    tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
