"""rc7 flip-flop gates on a built tree or a release (spec section 13.4).

Hard gate (before ABC): every rareness record has `ff_count_clean == ff_count_infected`.
Soft gate (after ABC, on the released circuits): pooled within-(base, set) AUROC, clean vs
infected, of FF count, log(1 + FF count) and latch share (`ff / cells`, `cutreport.features`),
with a percentile bootstrap CI over bases (bases resampled with replacement; each stratum keeps
its pair-count weight). Expected near 0.5 because the magic trigger adds no flip-flop.

    python -m lemanruss.htl.ffgate <release dir> --out <json>
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from lemanruss.htl.cutreport import _base_map, _load, auroc, features, read_circuits

Json = dict[str, object]
MEASURES = ("ff", "log1ff", "ff_share")


def hard_gate(root: Path) -> Json:
    recs = _load(root / "answer_key" / "rareness.json")
    assert isinstance(recs, list)
    bad = [r["circuit"] for r in recs
           if r.get("ff_count_clean") != r.get("ff_count_infected")]
    return {"records": len(recs), "mismatches": len(bad), "mismatch_circuits": bad[:20]}


def strata_aurocs(
    cells: dict[tuple[str, str], tuple[list[float], list[float]]], bases: list[str]
) -> float:
    """Pair-weighted mean of the stratum AUROCs over the given (possibly repeated) bases."""
    num = den = 0.0
    for b in bases:
        for (bb, _s), (neg, pos) in cells.items():
            if bb != b or not neg or not pos:
                continue
            w = len(neg) * len(pos)
            num += w * auroc(pos, neg)
            den += w
    return num / den if den else 0.5


def pooled_with_ci(
    cells: dict[tuple[str, str], tuple[list[float], list[float]]], draws: int = 2000, seed: int = 0
) -> Json:
    bases = sorted({b for b, _s in cells})
    est = strata_aurocs(cells, bases)
    rng = random.Random(seed)
    vals = sorted(strata_aurocs(cells, [rng.choice(bases) for _ in bases]) for _ in range(draws))
    return {"auroc": round(est, 4), "ci95": [round(vals[int(0.025 * draws)], 4),
                                             round(vals[int(0.975 * draws) - 1], 4)],
            "bases": len(bases), "strata": len(cells)}


def ff_gates(root: Path, draws: int = 2000) -> Json:
    labels = _load(root / "answer_key" / "labels.json")
    sc = _load(root / "answer_key" / "scripts.json")
    base_of = _base_map(_load(root / "manifest.json"))
    assert isinstance(labels, dict) and isinstance(sc, dict)
    circuits = read_circuits(root)
    feats = {cid: features(t) for cid, t in circuits.items() if cid in sc}
    out: Json = {"hard_gate_pre_abc": hard_gate(root)}
    for m in MEASURES:
        by_set: Json = {}
        for sset in (None, "K4", "K6", "G"):
            cells: dict[tuple[str, str], tuple[list[float], list[float]]] = {}
            for cid, f in feats.items():
                s = str(sc[cid]["set"])
                if sset is not None and s != sset:
                    continue
                neg, pos = cells.setdefault((base_of[cid], s), ([], []))
                (pos if labels[cid] is not None else neg).append(f[m])
            by_set[sset or "all"] = pooled_with_ci(cells, draws)
        out[m] = by_set
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("release", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rep = ff_gates(args.release)
    args.out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v["all"] if isinstance(v, dict) and "all" in v else v)
                      for k, v in rep.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
