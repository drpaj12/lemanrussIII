"""AUROC and W/L/T vs the size control per payload kind (rc7 analysis; the harness itself is
unchanged). A circuit counts for a payload when one of its Trojans has that payload; the
negatives are all clean circuits of the same test folds. Reads the answer key (labels.json),
so it is an evaluation-side tool, never a detector.

    python -m lemanruss.detect.payload_report <det out dir> <release dir> <family> DET...
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from lemanruss.detect import harness, metrics
from lemanruss.detect.data import Record, Release
from lemanruss.detect.report import fmt, load_runs

PAYLOADS = ("p-dos-stuck", "p-err-hi", "p-err-lo", "p-slowdown")


def _restrict(runs: list[harness.FoldRun], keep: set[str]) -> list[harness.FoldRun]:
    return [replace(r, scores={i: s for i, s in r.scores.items() if i in keep}) for r in runs]


def payload_table(out: Path, root: Path, family: str, dets: list[str], split: str = "base") -> str:
    rel = Release(root, family)
    labels = json.loads((root / "answer_key" / "labels.json").read_text(encoding="utf-8"))
    name = root.name
    recs: list[Record] = rel.records
    rows = ["| payload | infected | detector | AUROC | W/L/T vs size |", "|---|---|---|---|---|"]
    for p in PAYLOADS:
        keep = {r.id for r in recs if not r.infected
                or p in str(labels.get(r.id) or "")}
        n_inf = sum(1 for r in recs if r.infected and p in str(labels.get(r.id) or ""))
        sub = [r for r in recs if r.id in keep]
        control = harness.per_base_auroc(
            _restrict(load_runs(out, name, "size", split), keep), sub)
        for det in dets:
            runs = _restrict(load_runs(out, name, det, split), keep)
            if not runs:
                continue
            a = harness.cell_auroc(runs, sub, lambda r: True, lambda r: True)
            w, lo, t = metrics.wlt(harness.per_base_auroc(runs, sub), control)
            rows.append(f"| {p} | {n_inf} | {det} | {fmt(a)} | "
                        f"{'control' if det == 'size' else f'{w}/{lo}/{t}'} |")
    return "\n".join(rows)


if __name__ == "__main__":
    print(payload_table(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4:]))
