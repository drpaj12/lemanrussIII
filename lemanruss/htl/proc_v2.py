"""Seeker-Proc v2.0 (2026-11-09): per-core sets of 100 in four forms.

The v2.0 release joins three sources, per core (mcu, picorv32, darkriscv, mips_16) and per form
(gates, lut4, lut6, silicon):

- the rc3 circuits (gates, lut4, lut6; 33 or 34 per core and form) with their ids, bytes and key
  rows unchanged;
- the Seeker-Si rc2 Proc circuits (silicon; 33 or 34 per core), bytes unchanged, new ids;
- new logical circuits built with the same gates as rc3 and mapped to all four forms, packaged
  by `proc_rc1_release.package_proc_rc1` core by core with a given number of infected circuits.

The number of infected circuits of a cell (core x form) is drawn once from 10..70 among the
values the released circuits allow (at least the released infected count, at most that count plus
the new circuits), then the new circuits' labels are drawn to reach it.
"""

from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from lemanruss.htl.proc_rc1_release import LogicalCircuit, package_proc_rc1
from lemanruss.htl.release import write_sha256sums

Json = dict[str, object]
FORMS = ("gates", "lut4", "lut6", "silicon")
BUILD_KEY = {"gates": "gates", "lut4": "k4", "lut6": "k6", "silicon": "si"}
N_CELL = 100


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _d(obj: object) -> dict[str, object]:
    assert isinstance(obj, dict)
    return obj


def _rows_of(root: Path) -> list[dict[str, object]]:
    rows = _d(_load(root / "manifest.json"))["circuits"]
    assert isinstance(rows, list)
    return [_d(r) for r in rows]


def _dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def load_new(result_json: Path, forms_root: Path) -> list[LogicalCircuit]:
    res = _d(_load(result_json))
    out = []
    passing = res["passing"]
    assert isinstance(passing, list)
    for c in passing:
        c = _d(c)
        kinds = c["kinds"]
        words = c["magic_words"]
        assert isinstance(kinds, list) and isinstance(words, list)
        out.append(LogicalCircuit(str(c["circuit_id"]), str(c["base"]), [str(k) for k in kinds],
                                  [int(str(w), 16) for w in words],
                                  forms_root / str(c["circuit_id"])))
    return out


def cell_counts(release: Path, form: str | None) -> dict[tuple[str, str], tuple[int, int]]:
    """(core, form) -> (infected, clean) of a released Proc tree."""
    prov = _d(_load(release / "answer_key" / "provenance.json"))
    out: dict[tuple[str, str], tuple[int, int]] = {}
    for p in prov.values():
        p = _d(p)
        key = (str(p["base"]), form or str(p["restructuring"]))
        i, c = out.get(key, (0, 0))
        out[key] = (i + 1, c) if p["role"] == "infected" else (i, c + 1)
    return out


def draw_cell_targets(
    exist: dict[tuple[str, str], tuple[int, int]], n_new: dict[str, int], seed: int,
) -> dict[tuple[str, str], int]:
    """Infected circuits to add per (core, form): n_total ~ Uniform over the feasible values
    of 10..70 (>= the released infected count, <= it plus the new circuits)."""
    out: dict[tuple[str, str], int] = {}
    for (core, form), (inf, clean) in sorted(exist.items()):
        if inf + clean + n_new[core] != N_CELL:
            raise ValueError(f"{core}/{form}: {inf + clean} released + {n_new[core]} new "
                             f"!= {N_CELL}")
        lo, hi = max(10, inf), min(70, inf + n_new[core])
        total = random.Random(f"{seed}:{core}:{form}:ninf").randint(lo, hi)
        out[(core, form)] = total - inf
    return out


def package_new(
    new: dict[str, list[LogicalCircuit]], targets: dict[tuple[str, str], int], tmp: Path,
    seed: int, odin3_bin: Path | None,
) -> dict[str, Path]:
    """One package per core with all four forms and the drawn infected counts."""
    fnames = {BUILD_KEY[f]: f for f in FORMS}
    roots: dict[str, Path] = {}
    for core, lcs in sorted(new.items()):
        root = tmp / f"new-{core}"
        n_inf = {f: targets[(core, f)] for f in FORMS}
        package_proc_rc1(lcs, root, seed, f"seeker-proc-v2.0-new-{core}", {}, odin3_bin,
                         fnames, n_inf)
        roots[core] = root
    return roots


def _copy_gz(src: Path, dst: Path) -> None:
    shutil.copyfile(src, dst)


def merge_proc(
    rc3: Path, si: Path, news: dict[str, Path], out: Path, seed: int, datasheet_text: str,
    release_name: str,
) -> Json:
    """Writes the merged release `out` (must not exist)."""
    ids_rc3 = [str(r["id"]) for r in _rows_of(rc3)]
    ids_si = [str(r["id"]) for r in _rows_of(si)]
    new_ids = {core: sorted(str(r["id"]) for r in _rows_of(root)) for core, root in news.items()}
    start = max(int(i[2:]) for i in ids_rc3) + 1
    todo = [("si", i) for i in sorted(ids_si)] + [
        (core, i) for core, ids in sorted(new_ids.items()) for i in ids]
    fresh = [f"pr{start + n:04d}" for n in range(len(todo))]
    random.Random(f"{seed}:proc-v2-ids").shuffle(fresh)
    rename: dict[tuple[str, str], str] = dict(zip(todo, fresh, strict=True))
    out_c, out_k = out / "circuits", out / "answer_key"
    out_c.mkdir(parents=True)
    for sub in ("twins", "witness"):
        (out_k / sub).mkdir(parents=True)
    labels: dict[str, object] = {}
    prov: dict[str, object] = {}
    cat: dict[str, object] = {}
    rare: dict[str, object] = {}
    renames: dict[str, object] = {}
    rows: list[Json] = []

    def take(tag: str, root: Path, ident: dict[str, str], logical_prefix: str) -> None:
        k = root / "answer_key"
        lab, pr = _d(_load(k / "labels.json")), _d(_load(k / "provenance.json"))
        ra = _d(_load(k / "rareness.json"))
        rn = _d(_load(k / "renames.json"))
        for r in _rows_of(root):
            old = str(r["id"])
            new = ident.get(old, old)
            _copy_gz(root / str(r["file"]), out_c / f"{new}.blif.gz")
            vsrc = root / "circuits_v" / f"{old}.v.gz"
            if vsrc.is_file():
                (out / "circuits_v").mkdir(exist_ok=True)
                _copy_gz(vsrc, out / "circuits_v" / f"{new}.v.gz")
            rows.append({"id": new, "base": r["base"], "file": f"circuits/{new}.blif.gz",
                         "bytes": r["bytes"], "sha256": r["sha256"]})
            lg = _d(pr[old])["logical"]
            lab_v = lab[old]
            labels[new] = None if lab_v is None else f"{logical_prefix}{lab_v}"
            p = dict(_d(pr[old]))
            p["source"] = new
            p["logical"] = f"{logical_prefix}{lg}"
            p["clean_twin"] = f"{new}-twin" if p["role"] == "infected" else new
            prov[new] = p
            if old in ra:
                rare[new] = ra[old]
            if old in rn:
                renames[new] = rn[old]
            if p["role"] == "infected":
                _copy_gz(k / "twins" / f"{old}.blif.gz", out_k / "twins" / f"{new}.blif.gz")
                shutil.copytree(k / "witness" / old, out_k / "witness" / new)
        for lid, c in _d(_load(k / "catalogue.json")).items():
            c = dict(_d(c))
            c["ids"] = {f: ident.get(str(i), str(i)) for f, i in _d(c["ids"]).items()}
            c["origin"] = tag
            cat[f"{logical_prefix}{lid}"] = c

    take("rc3", rc3, {}, "")
    take("si-rc2", si, {i: rename[("si", i)] for i in ids_si}, "s-")
    for core, root in sorted(news.items()):
        take("v2-new", root, {i: rename[(core, i)] for i in new_ids[core]}, "")
    by_form: dict[str, dict[str, int]] = {}
    cells: dict[str, dict[str, dict[str, int]]] = {}
    for p in prov.values():
        p = _d(p)
        d = by_form.setdefault(str(p["restructuring"]), {"clean": 0, "infected": 0})
        d[str(p["role"])] += 1
        cc = cells.setdefault(str(p["base"]), {}).setdefault(
            str(p["restructuring"]), {"clean": 0, "infected": 0})
        cc[str(p["role"])] += 1
    manifest = {
        "release": release_name, "family": release_name, "schema": 2,
        "counts": {"circuits": len(rows),
                   "by_base": {b: sum(1 for r in rows if r["base"] == b)
                               for b in sorted({str(r["base"]) for r in rows})}},
        "circuits": sorted(rows, key=lambda r: str(r["id"])),
    }
    _dump(out / "manifest.json", manifest)
    _dump(out_k / "labels.json", labels)
    _dump(out_k / "provenance.json", prov)
    _dump(out_k / "catalogue.json", cat)
    _dump(out_k / "rareness.json", rare)
    _dump(out_k / "renames.json", renames)
    _dump(out_k / "mix_by_form.json", by_form)
    _dump(out_k / "cells.json", cells)
    (out / "DATASHEET.md").write_text(datasheet_text, encoding="utf-8")
    write_sha256sums(out)
    return {"release": release_name, "circuits": len(rows), "by_form": by_form, "cells": cells}


__all__ = ["merge_proc", "package_new", "draw_cell_targets", "cell_counts", "load_new"]
