"""Report numbers of a cut-and-stitch release (round 9): payload counts, the energy ring measure,
the independent style check and the flip-flop AUROC. Reads the release from disk only
(`python -m lemanruss.htl.cutreport <release> [--energy-sample N]`); shares no code with the
`n200gates` verify gates for the style check, on purpose (controller-style second opinion).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

Json = dict[str, object]
DIRECTIVES = {".model", ".inputs", ".outputs", ".names", ".latch", ".end"}
LEAK = re.compile(r"__htl|\$|@|odin|yosys|\\")


def _load(p: Path) -> object:
    return json.loads(p.read_text(encoding="utf-8"))


def _base_map(man: object) -> dict[str, str]:
    assert isinstance(man, dict)
    circuits = man["circuits"]
    assert isinstance(circuits, list)
    return {str(c["id"]): str(c["base"]) for c in circuits}


def auroc(pos: list[float], neg: list[float]) -> float:
    """P(score of a random positive > random negative), ties half; 0.5 when a side is empty."""
    if not pos or not neg:
        return 0.5
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum = 0.0
    i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        mid = (i + j + 1) / 2
        rank_sum += mid * sum(1 for k in range(i, j) if allv[k][1] == 1)
        i = j
    n1, n0 = len(pos), len(neg)
    return (rank_sum - n1 * (n1 + 1) / 2) / (n1 * n0)


def features(text: str) -> dict[str, float]:
    """Per-circuit style numbers computed here, not by the verify gates."""
    lines = text.replace("\\\n", " ").splitlines()
    names = [ln.split() for ln in lines if ln.startswith(".names")]
    latches = [ln.split() for ln in lines if ln.startswith(".latch")]
    drv = {w[-1]: w for w in names}
    cells = max(len(names), 1)

    def kind(w: list[str]) -> str:
        return "const" if len(w) == 2 else ("1in" if len(w) == 3 else "n")

    one = sum(1 for w in names if kind(w) == "1in")
    dbl = sum(1 for w in names if kind(w) == "1in" and w[1] in drv and kind(drv[w[1]]) == "1in")
    ff = len(latches)
    d_buf = sum(1 for w in latches if w[1] in drv and kind(drv[w[1]]) == "1in")
    inits = Counter(w[-1] for w in latches)
    return {"ff": float(ff), "log1ff": math.log1p(ff), "cells": float(len(names)),
            "one_in_share": one / cells, "dbl_share": dbl / cells,
            "const_share": sum(1 for w in names if kind(w) == "const") / cells,
            "ff_dbuf": float(d_buf), "init0": float(inits.get("0", 0)),
            "init1": float(inits.get("1", 0)), "ff_share": ff / cells}


def read_circuits(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in sorted((root / "circuits").glob("*.blif.gz")):
        out[f.name[: -len(".blif.gz")]] = gzip.decompress(f.read_bytes()).decode("utf-8")
    return out


def payload_counts(root: Path) -> Json:
    recs = _load(root / "answer_key" / "rareness.json")
    assert isinstance(recs, list)
    sc = _load(root / "answer_key" / "scripts.json")
    assert isinstance(sc, dict)
    per: dict[str, Counter[str]] = defaultdict(Counter)
    for r in recs:
        per[str(sc[str(r["circuit"])]["set"])][str(r["payload"])] += 1
    tot: Counter[str] = Counter()
    for c in per.values():
        tot.update(c)
    return {"total": dict(tot), "by_set": {k: dict(v) for k, v in sorted(per.items())}}


def style_check(root: Path, circuits: dict[str, str]) -> Json:
    """Independent check: duplicates, leak tokens, directives, latch fields, and the AUROC of
    each style feature per set (pair-weighted over base x set strata), clean vs infected."""
    labels = _load(root / "answer_key" / "labels.json")
    sc = _load(root / "answer_key" / "scripts.json")
    man = _load(root / "manifest.json")
    assert isinstance(labels, dict) and isinstance(sc, dict)
    base_of = _base_map(man)
    hashes = Counter(hashlib.sha256(re.sub(r"^\.model .*$", "", t, flags=re.M).encode()).hexdigest()
                     for t in circuits.values())
    dups = sum(1 for n in hashes.values() if n > 1)
    bad_tokens = bad_directives = 0
    latch_fmt: Counter[str] = Counter()
    for t in circuits.values():
        if LEAK.search(t):
            bad_tokens += 1
        for ln in t.splitlines():
            w = ln.split()
            if w and w[0].startswith(".") and w[0] not in DIRECTIVES:
                bad_directives += 1
            if w and w[0] == ".latch":
                latch_fmt[f"{len(w)}:{w[3] if len(w) > 3 else ''}:{w[-1]}"] += 1
    feats = {cid: features(t) for cid, t in circuits.items() if cid in sc}
    strata: dict[tuple[str, str], tuple[list[str], list[str]]] = {}
    for cid in feats:
        key = (base_of[cid], str(sc[cid]["set"]))
        neg, pos = strata.setdefault(key, ([], []))
        (pos if labels[cid] is not None else neg).append(cid)
    out: dict[str, Json] = {}
    for set_name in ("K4", "K6", "G"):
        per_feat: dict[str, float] = {}
        for fname in next(iter(feats.values())):
            num = den = 0.0
            for (_b, s), (neg, pos) in strata.items():
                if s != set_name or not neg or not pos:
                    continue
                pairs = len(neg) * len(pos)
                num += pairs * auroc([feats[c][fname] for c in pos], [feats[c][fname] for c in neg])
                den += pairs
            per_feat[fname] = round(num / den, 3) if den else 0.5
        out[set_name] = {"auroc": per_feat}
    return {"duplicates_groups": dups, "files_with_leak_tokens": bad_tokens,
            "unknown_directive_lines": bad_directives,
            "latch_formats": dict(latch_fmt.most_common(6)), "by_set": out}


def ff_auroc(root: Path, circuits: dict[str, str]) -> Json:
    """AUROC of total flip-flop count and of log(1 + FF), clean vs infected, within each base
    and set (a base x set stratum), then pooled by pair count. log(1 + x) is monotone, so the
    two AUROCs are equal; both are given because the controller asked for both."""
    labels = _load(root / "answer_key" / "labels.json")
    sc = _load(root / "answer_key" / "scripts.json")
    man = _load(root / "manifest.json")
    assert isinstance(labels, dict) and isinstance(sc, dict)
    base_of = _base_map(man)
    cells: dict[tuple[str, str], tuple[list[float], list[float]]] = {}
    for cid, text in circuits.items():
        if cid not in sc:
            continue
        ff = float(sum(1 for ln in text.splitlines() if ln.startswith(".latch")))
        neg, pos = cells.setdefault((base_of[cid], str(sc[cid]["set"])), ([], []))
        (pos if labels[cid] is not None else neg).append(ff)
    rows: list[Json] = []
    num = num_log = den = 0.0
    set_num: Counter[str] = Counter()
    set_den: Counter[str] = Counter()
    for (b, s), (neg, pos) in sorted(cells.items()):
        if not neg or not pos:
            continue
        a = auroc(pos, neg)
        al = auroc([math.log1p(v) for v in pos], [math.log1p(v) for v in neg])
        w = len(neg) * len(pos)
        num += w * a
        num_log += w * al
        den += w
        set_num[s] += int(w * a * 1e6)
        set_den[s] += w
        rows.append({"base": b, "set": s, "clean": len(neg), "infected": len(pos),
                     "auroc_ff": round(a, 3), "auroc_log1p_ff": round(al, 3)})
    by_set = {k: round(set_num[k] / 1e6 / set_den[k], 3) for k in sorted(set_den)}
    vals = sorted(float(str(r["auroc_ff"])) for r in rows)
    return {"pooled_auroc_ff": round(num / den, 3) if den else 0.5,
            "pooled_auroc_log1p_ff": round(num_log / den, 3) if den else 0.5,
            "by_set": by_set, "strata": len(rows),
            "stratum_min_median_max": [vals[0], vals[len(vals) // 2], vals[-1]] if vals else [],
            "rows": rows}


def energy_measure(root: Path, sample: int) -> Json:
    """Ring toggles under the witness (trigger fires) against an all-zero input run of the same
    length, replayed in Odin III on the released circuits; smallest bases first."""
    from lemanruss.htl.n200check import Steps, decode_steps, odin_ring_toggles

    cuts = _load(root / "answer_key" / "cuts.json")
    trojans = _load(root / "answer_key" / "trojans.json")
    labels = _load(root / "answer_key" / "labels.json")
    man = _load(root / "manifest.json")
    assert isinstance(cuts, dict) and isinstance(trojans, dict) and isinstance(labels, dict)
    base_of = _base_map(man)
    rows = []
    tmp = root.parent / f"{root.name}-energy-scratch"
    tmp.mkdir(exist_ok=True)
    for cid in sorted(trojans, key=lambda c: (base_of[c], c)):
        entry = cuts.get(cid, {})
        assert isinstance(entry, dict)
        rings = entry.get("rings", {})
        if not rings or not isinstance(rings, dict):
            continue
        wf = root / "answer_key" / "witnesses" / f"{base_of[cid]}.json.gz"
        wd = json.loads(gzip.decompress(wf.read_bytes()))
        for j, names in rings.items():
            rowsw = wd["steps"].get(cid, {}).get(j)
            if rowsw is None:
                continue
            steps: Steps = decode_steps(wd["inputs"], rowsw)
            path = tmp / f"{cid}.blif"
            path.write_text(gzip.decompress(
                (root / "circuits" / f"{cid}.blif.gz").read_bytes()).decode("utf-8"),
                encoding="utf-8")
            on = odin_ring_toggles(path, steps, [str(n) for n in names])
            idle = odin_ring_toggles(path, [dict.fromkeys(s, 0) for s in steps],
                                     [str(n) for n in names])
            rows.append({"circuit": cid, "base": base_of[cid], "bits": len(names),
                         "cycles": len(steps), "ring_toggles_witness": on,
                         "ring_toggles_idle": idle})
        if len(rows) >= sample:
            break
    on_l = sorted(float(str(r["ring_toggles_witness"])) for r in rows)
    idle_l = sorted(float(str(r["ring_toggles_idle"])) for r in rows)
    return {"measured": len(rows), "witness_gt_idle": sum(
        1 for r in rows if int(str(r["ring_toggles_witness"])) > int(str(r["ring_toggles_idle"]))),
        "witness_min_median_max": [on_l[0], on_l[len(on_l) // 2], on_l[-1]] if on_l else [],
        "idle_min_median_max": [idle_l[0], idle_l[len(idle_l) // 2], idle_l[-1]] if idle_l else [],
        "rows": rows[:20]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("release", type=Path)
    ap.add_argument("--energy-sample", type=int, default=40)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    circuits = read_circuits(args.release)
    rep: Json = {"release": args.release.name, "payloads": payload_counts(args.release),
                 "style": style_check(args.release, circuits),
                 "ff_auroc": ff_auroc(args.release, circuits)}
    if (args.release / "answer_key" / "cuts.json").exists():
        rep["energy"] = energy_measure(args.release, args.energy_sample)
    args.out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print(f"{args.release.name}: report written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
