"""Seeker v2.0 full-set test: confusion matrices, AUROC with interval, found-rate by Trojan count,
win/loss/tie against the size-only control, per family x target and per benchmark.

    python -m lemanruss.detect.v2report --runs <dir> --comb <rel> --seq <rel> --proc <rel> \
        --out-md docs/results-v2-full.md --out-json docs/results-v2-full-summary.json \
        --out-tex docs/v2-full-tex

Inputs are the fold files of `v2run` (Comb, Seq: base split, flag = score >= validation
threshold at 5% false positives) and the cell files of `procrun` (Proc: one core held out per
form). No circuit id, seed, label or magic word is written: aggregates only.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lemanruss.detect import metrics
from lemanruss.detect.data import Release

DETECTORS = ("size", "sanity", "ffcount", "classhist", "rare", "gnn-yasaei", "gnn-a",
             "gnn-a-nosc", "graphlet-b")
CONTROLS = ("size", "sanity", "ffcount")
TARGETS = ("K4", "K6", "G", "S")
PROC_FORMS = {"lut4": "K4", "lut6": "K6", "gates": "G", "silicon": "S"}
FAMS = ("Comb", "Seq", "Proc")


@dataclass(frozen=True)
class Obs:
    det: str
    fam: str
    target: str
    bench: str
    fold: str
    score: float
    thr: float
    inf: bool
    n: int
    group: str


def load_comb_seq(runs: Path, fam: str, rel_dir: Path) -> list[Obs]:
    rel = Release(rel_dir, fam)
    meta = {r.id: r for r in rel.records}
    out: list[Obs] = []
    for f in sorted((runs / fam).glob("*-base-f*-s0.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        det = f.name.split("-base-f")[0]
        for cid, s in d["scores"].items():
            r = meta[cid]
            out.append(Obs(det, fam, r.set, r.base, f"f{d['fold']}", float(s),
                           float(d["threshold"]), r.infected, r.n_trojans, r.base))
    return out


def load_proc(runs: Path) -> list[Obs]:
    out: list[Obs] = []
    for f in sorted((runs / "Proc").glob("*.json")):
        det, form, held = f.stem.split("-", 2)[0], "", ""
        for form_name in PROC_FORMS:
            marker = f"-{form_name}-"
            if marker in f.stem:
                det, held = f.stem.split(marker)
                form = form_name
        if not form:
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if "circuits" not in d:
            continue
        for cid, c in d["circuits"].items():
            if c["score"] is None:
                continue
            out.append(Obs(det, "Proc", PROC_FORMS[form], held, f"{form}-{held}",
                           float(c["score"]), float(d["threshold"]), bool(c["infected"]),
                           int(c["n_trojans"]), cid))
    return out


def label(ci: tuple[float, float] | None) -> str:
    if ci is None:
        return "n/a"
    if ci[0] > 0.5:
        return "ABOVE CHANCE"
    if ci[1] < 0.5:
        return "BELOW CHANCE"
    return "INCONCLUSIVE"


def conf(obs: list[Obs]) -> dict[str, Any]:
    tp = sum(1 for o in obs if o.inf and o.score >= o.thr)
    fn = sum(1 for o in obs if o.inf and o.score < o.thr)
    fp = sum(1 for o in obs if not o.inf and o.score >= o.thr)
    tn = sum(1 for o in obs if not o.inf and o.score < o.thr)
    p, nn = tp + fn, fp + tn
    tpr = tp / p if p else None
    fpr = fp / nn if nn else None
    prec = tp / (tp + fp) if tp + fp else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn, "TPR": tpr, "FPR": fpr, "precision": prec,
            "F1": f1, "accuracy": (tp + tn) / len(obs) if obs else None}


def fold_auroc(obs: list[Obs]) -> tuple[float | None, tuple[float, float] | None]:
    """Mean over folds of the AUROC, and a 95% interval resampling benchmarks (circuits for
    Proc, whose three cores are the folds) inside each fold."""
    folds: dict[str, dict[str, metrics.Pairs]] = defaultdict(lambda: defaultdict(list))
    for o in obs:
        folds[o.fold][o.group].append((o.score, int(o.inf)))
    per = []
    for f in folds.values():
        pairs = [p for g in f.values() for p in g]
        a = metrics.pair_auroc(pairs)
        if a is not None:
            per.append(a)
    if not per:
        return None, None
    return sum(per) / len(per), metrics.bootstrap_ci([dict(f) for f in folds.values()],
                                                     metrics.pair_auroc)


def bench_auroc(obs: list[Obs]) -> dict[str, float | None]:
    by: dict[str, metrics.Pairs] = defaultdict(list)
    for o in obs:
        by[o.bench].append((o.score, int(o.inf)))
    return {b: metrics.pair_auroc(p) for b, p in by.items()}


def geomean_gain(method: dict[str, float | None], control: dict[str, float | None]) -> float | None:
    xs = [math.log(max(m, 1e-3) / max(c, 1e-3)) for b, m in method.items()
          if m is not None and (c := control.get(b)) is not None]
    return 100.0 * (math.exp(sum(xs) / len(xs)) - 1.0) if xs else None


def summarise(all_obs: list[Obs]) -> dict[str, Any]:
    idx: dict[tuple[str, str, str], list[Obs]] = defaultdict(list)
    for o in all_obs:
        idx[(o.det, o.fam, o.target)].append(o)
        idx[(o.det, o.fam, "all")].append(o)
    out: dict[str, Any] = {}
    for (det, fam, tgt), obs in sorted(idx.items()):
        c = conf(obs)
        a, ci = fold_auroc(obs)
        ctrl = bench_auroc(idx.get(("size", fam, tgt), []))
        per_b = bench_auroc(obs)
        w, lo, t = metrics.wlt(per_b, ctrl)
        found = {}
        for k in (1, 2, 3):
            sub = [o for o in obs if o.inf and o.n == k]
            hit = sum(1 for o in sub if o.score >= o.thr)
            found[str(k)] = {"n": len(sub), "found": hit,
                             "rate": hit / len(sub) if sub else None}
        out[f"{fam}|{tgt}|{det}"] = {
            **c, "n": len(obs), "AUROC": a, "AUROC_ci": ci, "label": label(ci),
            "wlt_vs_size": None if det == "size" else [w, lo, t],
            "geomean_gain_pct": None if det == "size" else geomean_gain(per_b, ctrl),
            "found_by_trojan_count": found,
            "per_benchmark_auroc": per_b}
    return out


def f3(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}"


def best(summ: dict[str, Any], fam: str, tgt: str) -> str:
    cands = [d for d in DETECTORS if d not in CONTROLS and f"{fam}|{tgt}|{d}" in summ
             and summ[f"{fam}|{tgt}|{d}"]["AUROC"] is not None]
    return max(cands, key=lambda d: summ[f"{fam}|{tgt}|{d}"]["AUROC"]) if cands else ""


def ci_s(r: dict[str, Any]) -> str:
    ci = r["AUROC_ci"]
    return f"{f3(r['AUROC'])} [{f3(ci[0])}, {f3(ci[1])}]" if ci else f3(r["AUROC"])


def wlt_s(r: dict[str, Any]) -> str:
    return "control" if r["wlt_vs_size"] is None else "/".join(str(x) for x in r["wlt_vs_size"])


def gm_s(r: dict[str, Any]) -> str:
    g = r["geomean_gain_pct"]
    return "control" if g is None else f"{g:+.1f}"


def md_tables(summ: dict[str, Any], bases: dict[str, list[str]]) -> str:
    L: list[str] = []
    for fam in FAMS:
        L += [f"### {fam}: every detector, per target (summed over benchmarks)", "",
              "Geomean gain = geometric mean over benchmarks of the detector AUROC over the "
              "size-only AUROC, in percent. W/L/T over benchmarks (higher AUROC, EPS 1e-6).", "",
              "| target | detector | TP | FP | TN | FN | TPR | FPR | precision | F1 | accuracy | "
              "AUROC [95% CI] | geomean gain % | W/L/T vs size | label |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for tgt in (*TARGETS, "all"):
            for det in DETECTORS:
                r = summ.get(f"{fam}|{tgt}|{det}")
                if r is None:
                    continue
                L.append(f"| {tgt} | {det} | {r['TP']} | {r['FP']} | {r['TN']} | {r['FN']} | "
                         f"{f3(r['TPR'])} | {f3(r['FPR'])} | {f3(r['precision'])} | "
                         f"{f3(r['F1'])} | {f3(r['accuracy'])} | {ci_s(r)} | {gm_s(r)} | "
                         f"{wlt_s(r)} | {r['label']} |")
        L.append("")
        L += [f"### {fam}: found-rate by Trojan count (flagged infected circuits / infected "
              "circuits with that many Trojans), best detector and size-only", "",
              "| target | detector | 1 Trojan | 2 Trojans | 3 Trojans |", "|---|---|---|---|---|"]
        for tgt in (*TARGETS, "all"):
            for det in (best(summ, fam, tgt), "size"):
                r = summ.get(f"{fam}|{tgt}|{det}")
                if r is None:
                    continue
                fb = r["found_by_trojan_count"]
                cells = [f"{fb[k]['found']}/{fb[k]['n']} ({pct(fb[k]['rate'])}%)" for k in "123"]
                L.append(f"| {tgt} | {det} | " + " | ".join(cells) + " |")
        L.append("")
        L += [f"### {fam}: per benchmark, AUROC of the best detector of the target "
              "(size-only in brackets)", "",
              "| benchmark | " + " | ".join(TARGETS) + " |", "|---|" + "---|" * len(TARGETS)]
        for b in bases[fam]:
            row = []
            for tgt in TARGETS:
                d = best(summ, fam, tgt)
                r = summ.get(f"{fam}|{tgt}|{d}")
                s = summ.get(f"{fam}|{tgt}|size")
                if r is None or b not in r["per_benchmark_auroc"]:
                    row.append("-")
                else:
                    row.append(f"{f3(r['per_benchmark_auroc'][b])} "
                               f"({f3(s['per_benchmark_auroc'].get(b)) if s else 'n/a'})")
            L.append(f"| {b} | " + " | ".join(row) + " |")
        L.append("")
    return "\n".join(L)


def tex_conf(summ: dict[str, Any], fam: str) -> str:
    rows = [r"\begin{tabular}{@{}llrrrrrrrll@{}}", r"\toprule",
            r"target & detector & TP & FP & TN & FN & TPR & FPR & AUROC [95\% CI] & W/L/T "
            r"& label \\",
            r"\midrule"]
    for tgt in (*TARGETS, "all"):
        for det in DETECTORS:
            r = summ.get(f"{fam}|{tgt}|{det}")
            if r is None:
                continue
            lab = r["label"].replace("CHANCE", "chance").title().replace("Inconclusive", "Incl.")
            rows.append(f"{tgt} & {det} & {r['TP']} & {r['FP']} & {r['TN']} & {r['FN']} & "
                        f"{f3(r['TPR'])} & {f3(r['FPR'])} & {ci_s(r)} & {wlt_s(r)} & "
                        f"{lab} \\\\")
        rows.append(r"\midrule")
    rows[-1] = r"\bottomrule"
    rows.append(r"\end{tabular}")
    return "\n".join(rows) + "\n"


def tex_headline(summ: dict[str, Any]) -> str:
    rows = [r"\begin{tabular}{@{}llrrrrrrl@{}}", r"\toprule",
            r"set & target & detector & TP & FP & TN & FN & TPR/FPR & AUROC [95\% CI]  \\",
            r"\midrule"]
    for fam in FAMS:
        for tgt in (*TARGETS, "all"):
            for det in (best(summ, fam, tgt), "size"):
                r = summ.get(f"{fam}|{tgt}|{det}")
                if r is None:
                    continue
                rows.append(f"{fam} & {tgt} & {det} & {r['TP']} & {r['FP']} & {r['TN']} & "
                            f"{r['FN']} & {f3(r['TPR'])}/{f3(r['FPR'])} & {ci_s(r)} \\\\")
        rows.append(r"\midrule")
    rows[-1] = r"\bottomrule"
    rows.append(r"\end{tabular}")
    return "\n".join(rows).replace("_", r"\_") + "\n"


def tex_bench(summ: dict[str, Any], fam: str, names: list[str]) -> str:
    rows = [r"\begin{tabular}{@{}l" + "r" * len(TARGETS) + r"@{}}", r"\toprule",
            "benchmark & " + " & ".join(TARGETS) + r" \\", r"\midrule"]
    for b in names:
        cells = []
        for tgt in TARGETS:
            d = best(summ, fam, tgt)
            r = summ.get(f"{fam}|{tgt}|{d}")
            s = summ.get(f"{fam}|{tgt}|size")
            if r is None or b not in r["per_benchmark_auroc"]:
                cells.append("--")
            else:
                sv = s["per_benchmark_auroc"].get(b) if s else None
                cells.append(f"{f3(r['per_benchmark_auroc'][b])} ({f3(sv)})")
        rows.append(b.replace("_", r"\_") + " & " + " & ".join(cells) + r" \\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(rows) + "\n"


def tex_found(summ: dict[str, Any]) -> str:
    rows = [r"\begin{tabular}{@{}llrrr@{}}", r"\toprule",
            r"set & detector & 1 Trojan & 2 Trojans & 3 Trojans \\", r"\midrule"]
    for fam in FAMS:
        for det in (best(summ, fam, "all"), "size"):
            r = summ.get(f"{fam}|all|{det}")
            if r is None:
                continue
            fb = r["found_by_trojan_count"]
            cells = [f"{pct(fb[k]['rate'])}\\% of {fb[k]['n']}" for k in "123"]
            rows.append(f"{fam} & {det} & " + " & ".join(cells) + r" \\")
        rows.append(r"\midrule")
    rows[-1] = r"\bottomrule"
    rows.append(r"\end{tabular}")
    return "\n".join(rows).replace("_", r"\_") + "\n"


def tex_layout(all_obs: list[Obs]) -> str:
    """Release layout from the scored circuits of the size-only control."""
    rows = [r"\begin{tabular}{@{}llrrrrrrr@{}}", r"\toprule",
            r"set & target & bench. & circuits & infected & clean & 1 Tr. & 2 Tr. & 3 Tr. \\",
            r"\midrule"]
    for fam in FAMS:
        for tgt in TARGETS:
            o = [x for x in all_obs if x.det == "size" and x.fam == fam and x.target == tgt]
            inf = [x for x in o if x.inf]
            ks = [sum(1 for x in inf if x.n == k) for k in (1, 2, 3)]
            nb = len({x.bench for x in o})
            rows.append(f"{fam} & {tgt} & {nb} & {len(o)} & {len(inf)} & {len(o) - len(inf)} & "
                        f"{ks[0]} & {ks[1]} & {ks[2]} \\\\")
        rows.append(r"\midrule")
    rows[-1] = r"\bottomrule"
    rows.append(r"\end{tabular}")
    return "\n".join(rows) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--comb", type=Path, required=True)
    ap.add_argument("--seq", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-tex", type=Path, required=True)
    a = ap.parse_args(argv)
    obs = load_comb_seq(a.runs, "Comb", a.comb) + load_comb_seq(a.runs, "Seq", a.seq) \
        + load_proc(a.runs)
    summ = summarise(obs)
    bases = {f: sorted({o.bench for o in obs if o.fam == f}) for f in FAMS}
    a.out_json.write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    a.out_md.write_text(md_tables(summ, bases), encoding="utf-8")
    a.out_tex.mkdir(parents=True, exist_ok=True)
    (a.out_tex / "v2_headline.tex").write_text(tex_headline(summ), encoding="utf-8")
    (a.out_tex / "v2_layout.tex").write_text(tex_layout(obs), encoding="utf-8")
    (a.out_tex / "v2_found.tex").write_text(tex_found(summ), encoding="utf-8")
    for fam in FAMS:
        (a.out_tex / f"v2_conf_{fam.lower()}.tex").write_text(tex_conf(summ, fam), encoding="utf-8")
        (a.out_tex / f"v2_bench_{fam.lower()}.tex").write_text(
            tex_bench(summ, fam, bases[fam]), encoding="utf-8")


if __name__ == "__main__":
    main()
