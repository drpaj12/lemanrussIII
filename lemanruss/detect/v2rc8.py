"""Seeker-Seq rc8 with and without the reset-state circuits, scored as in `v2report`.

    python -m lemanruss.detect.v2rc8 --runs <dir> --release <rc8> --out-md <md> --out-tex <tex>

`runs/rc8-all` holds the fold files of all rc8 circuits, `runs/rc8-minus` those with the circuits
that are absent from Seeker-Seq v2.0 removed (the reset-state and early-trigger replacements).
Aggregates only; no circuit id, seed or label is written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lemanruss.detect import v2report as rep
from lemanruss.detect.data import Release


def load(runs: Path, name: str, rel_dir: Path) -> list[rep.Obs]:
    rel = Release(rel_dir, "Seq")
    meta = {r.id: r for r in rel.records}
    out: list[rep.Obs] = []
    for f in sorted((runs / name).glob("*-base-f*-s0.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        det = f.name.split("-base-f")[0]
        for cid, s in d["scores"].items():
            r = meta[cid]
            out.append(rep.Obs(det, "Seq", r.set, r.base, f"f{d['fold']}", float(s),
                               float(d["threshold"]), r.infected, r.n_trojans, r.base))
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-tex", type=Path, required=True)
    a = ap.parse_args(argv)
    sums: dict[str, dict[str, Any]] = {}
    counts: dict[str, tuple[int, int]] = {}
    for name in ("rc8-all", "rc8-minus"):
        obs = load(a.runs, name, a.release)
        sums[name] = rep.summarise(obs)
        size = [o for o in obs if o.det == "size"]
        counts[name] = (sum(1 for o in size if o.inf), sum(1 for o in size if not o.inf))
    a.out_json.write_text(json.dumps(sums, indent=1, sort_keys=True), encoding="utf-8")
    md = ["| detector | target | circuits (inf/clean) | AUROC all [95% CI] | AUROC minus [95% CI] "
          "| TPR/FPR all | TPR/FPR minus | label all | label minus |", "|---|" + "---|" * 8]
    tex = [r"\begin{tabular}{@{}llrrcc@{}}", r"\toprule",
           r"detector & target & AUROC all [95\% CI] & AUROC minus [95\% CI] & TPR/FPR all "
           r"& TPR/FPR minus \\", r"\midrule"]
    for tgt in ("all", *rep.TARGETS):
        for det in rep.DETECTORS:
            k = f"Seq|{tgt}|{det}"
            x, y = sums["rc8-all"].get(k), sums["rc8-minus"].get(k)
            if x is None or y is None:
                continue
            tr = [f"{rep.f3(r['TPR'])}/{rep.f3(r['FPR'])}" for r in (x, y)]
            md.append(f"| {det} | {tgt} | {counts['rc8-all'][0]}/{counts['rc8-all'][1]} -> "
                      f"{counts['rc8-minus'][0]}/{counts['rc8-minus'][1]} | {rep.ci_s(x)} | "
                      f"{rep.ci_s(y)} | {tr[0]} | {tr[1]} | {x['label']} | {y['label']} |")
            if tgt == "all":
                tex.append(f"{det} & {tgt} & {rep.ci_s(x)} & {rep.ci_s(y)} & {tr[0]} & "
                           f"{tr[1]} \\\\".replace("_", r"\_"))
    tex += [r"\bottomrule", r"\end{tabular}"]
    a.out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    a.out_tex.mkdir(parents=True, exist_ok=True)
    (a.out_tex / "v2_rc8.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
