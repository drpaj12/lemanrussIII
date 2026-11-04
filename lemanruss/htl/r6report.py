"""Round 6 report: counts and rareness of a Seeker-Seq build per base set (old = the round 5
bases, new = the bases added in round 6), per-base outcome and build time of the new bases.
Everything is read from the files of the build tree (`answer_key/rareness.json`, `failures.json`,
the build log's `BUILD-TIME` lines)."""

from __future__ import annotations

import json
import re
from pathlib import Path

Json = dict[str, object]
VARIANTS = ("ctr-fast", "ctr-mid", "ctr-slow", "pat-fast", "pat-mid", "pat-slow")
NS = ("16", "64", "256", "1024")


def _fmt(p: float | None) -> str:
    return "-" if p is None else f"{p:.2e}"


def _p_within(rec: Json, n: str) -> float | None:
    within = rec["p_fire_within"]
    assert isinstance(within, dict)
    v = within.get(n)
    return None if v is None else float(v[0])


def pooled(recs: list[Json]) -> list[str]:
    """P(trigger high within N cycles) pooled over the infected circuits."""
    out = ["| N cycles | circuits | with P(fire<=N)>0 | min | median | max |",
           "|---|---|---|---|---|---|"]
    for n in NS:
        vals = sorted(v for v in (_p_within(r, n) for r in recs) if v is not None)
        pos = [v for v in vals if v > 0]
        out.append(f"| {n} | {len(vals)} | {len(pos)} | {_fmt(vals[0] if vals else None)} | "
                   f"{_fmt(vals[len(vals) // 2] if vals else None)} | "
                   f"{_fmt(vals[-1] if vals else None)} |")
    return out


def by_variant(recs: list[Json], fails: list[Json], bases: set[str]) -> list[str]:
    """Per variant: built, band not reachable, min / median / max of P(fire <= 1024)."""
    out = ["| variant | built | band not reachable | min | median | max |",
           "|---|---|---|---|---|---|"]
    for v in VARIANTS:
        ps = sorted(p for r in recs if r["target_band"] == v
                    and (p := _p_within(r, "1024")) is not None)
        nf = sum(1 for f in fails if f["variant"] == v and f["base"] in bases
                )
        out.append(f"| {v} | {len(ps)} | {nf} | {_fmt(ps[0] if ps else None)} | "
                   f"{_fmt(ps[len(ps) // 2] if ps else None)} | {_fmt(ps[-1] if ps else None)} |")
    return out


def build_times(log: Path) -> dict[str, tuple[int, int]]:
    """base -> (seconds, max RSS MB) from the `BUILD-TIME` lines of the build's stderr."""
    out: dict[str, tuple[int, int]] = {}
    rx = re.compile(r"BUILD-TIME (\S+) (\d+) s, max RSS (\d+) MB")
    for ln in log.read_text(encoding="utf-8").splitlines():
        m = rx.search(ln)
        if m:
            out[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    return out


def _compact_reasons(fails: list[Json]) -> list[str]:
    """Failure reasons with the band ranges merged: 'no ctr size reaches P(fire<=1024) in
    [0.5, 1.0] (...)' counts as 'band unreachable (ctr: fast mid slow)'."""
    rx = re.compile(r"no (ctr|pat) size reaches P\(fire<=1024\) in \[([\d.]+), ")
    names = {"0.5": "fast", "0.05": "mid", "0.003": "slow"}
    bands: dict[str, list[str]] = {}
    other: set[str] = set()
    for f in fails:
        m = rx.search(str(f["reason"]))
        if m:
            bands.setdefault(m.group(1), []).append(names.get(m.group(2), m.group(2)))
        else:
            other.add(str(f["reason"])[:90])
    return [f"band not reachable, {k}: {' '.join(v)}" for k, v in sorted(bands.items())] + \
        sorted(other)


def report(
    root: Path, new_bases: list[str], log: Path | None = None,
    not_released: list[str] | None = None,
) -> list[str]:
    key = root / "answer_key"
    recs: list[Json] = json.loads((key / "rareness.json").read_text(encoding="utf-8"))
    fails: list[Json] = json.loads((key / "failures.json").read_text(encoding="utf-8"))
    base_labels = key / "labels_base.json"  # identity circuits only (written by `restructure`)
    labels: dict[str, str | None] = json.loads(
        (base_labels if base_labels.exists() else key / "labels.json").read_text(
            encoding="utf-8"))
    inserts: dict[str, Json] = json.loads((key / "inserts.json").read_text(encoding="utf-8"))
    out_bases = set(not_released or [])
    all_bases = {str(i["base"]) for i in inserts.values()} - out_bases
    clean_ids = [c for c, v in labels.items() if v is None]
    new = set(new_bases)
    # the pooled tables cover the released bases only; the per-base table lists every new base
    all_recs = recs
    recs = [r for r in recs if r["base"] not in out_bases]
    old_recs = [r for r in recs if r["base"] not in new]
    new_recs = [r for r in recs if r["base"] in new]
    times = build_times(log) if log is not None else {}
    n_bases = len(clean_ids) - len(out_bases)
    out = [
        f"Seeker-Seq: {n_bases} clean bases, {len(recs)} infected circuits "
        f"({n_bases + len(recs)} with clean copies); old set {len(old_recs)} infected, new set "
        f"{len(new_recs)} infected on {len(new & all_bases)} of {len(new)} new bases.", ""]
    for title, rs, bs in (("old bases (round 5 set)", old_recs, all_bases - new),
                          ("new bases (round 6)", new_recs, new - out_bases),
                          ("all bases", recs, all_bases)):
        out += [f"### Rareness, {title}", "", *pooled(rs), "", *by_variant(rs, fails, bs), ""]
    out += ["### New bases: outcome and build wall time", "",
            "| base | released | infected built | variants failed | wall time | max RSS | "
            "failure reasons |", "|---|---|---|---|---|---|---|"]
    for b in sorted(new):
        built = sum(1 for r in all_recs if r["base"] == b)
        fl = [f for f in fails if f["base"] == b]
        reasons = _compact_reasons(fl)
        t = times.get(b)
        rel = "no" if b in out_bases else "yes"
        out.append(f"| {b} | {rel} | {built} | {len(fl)} | {f'{t[0]} s' if t else '-'} | "
                   f"{f'{t[1]} MB' if t else '-'} | {'; '.join(reasons) or '-'} |")
    return out
