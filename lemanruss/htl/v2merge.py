"""Seeker v2.0 full sets (2026-11-09): joins the released rc tree, the top-up trees and the
silicon (Seeker-Si rc2) tree into one release of cells K4, K6, G and S.

Rules (brief of 2026-11-09):

- every circuit of the rc release keeps its id, its bytes and its key rows;
- top-up circuits keep the ids they were drawn with (unused ids of the base's own block);
- silicon circuits get new opaque ids (the Si tree reused the id range of the rc release), bytes
  unchanged; their key rows are renamed, nothing else changes;
- a cell (base x set) ships only when it holds exactly 100 circuits; a short cell is dropped with
  its cause from the build records (`answer_key/dropped_cells.json`) and so is a base with no
  complete cell; nothing is padded;
- no seed, no label and no key row is printed or committed by this module.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
from pathlib import Path

from lemanruss.htl.n200 import N_SET
from lemanruss.htl.release import Tools, gz_bytes, short_name, write_sha256sums

Json = dict[str, object]
SET_ORDER = ("K4", "K6", "G", "S")


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _as_dict(obj: object) -> dict[str, object]:
    assert isinstance(obj, dict)
    return obj


def _as_list(obj: object) -> list[object]:
    assert isinstance(obj, list)
    return obj


class Source:
    """One input tree: a released directory (`.blif.gz`) or a build tree (`.blif`)."""

    def __init__(self, root: Path, tag: str, released: bool) -> None:
        self.root, self.tag, self.released = root, tag, released
        self.key = root / "answer_key"

    def circuit_gz(self, cid: str) -> bytes:
        if self.released:
            return (self.root / "circuits" / f"{cid}.blif.gz").read_bytes()
        return gz_bytes((self.root / "circuits" / f"{cid}.blif").read_text(encoding="utf-8"))

    def verilog_gz(self, cid: str) -> bytes | None:
        p = self.root / "circuits_v" / f"{cid}.v.gz"
        if p.is_file():
            return p.read_bytes()
        q = self.root / "circuits_v" / f"{cid}.v"
        return gz_bytes(q.read_text(encoding="utf-8")) if q.is_file() else None

    def pre_gz(self, cid: str) -> bytes | None:
        p = self.key / "pre" / f"{cid}.blif.gz"
        return p.read_bytes() if p.is_file() else None

    def witnesses(self, base: str) -> Json:
        p = self.key / "witnesses" / f"{base}.json.gz"
        if not p.is_file():
            return {"inputs": [], "steps": {}}
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            return _as_dict(json.load(fh))


def tree_rows(src: Source) -> Json:
    """The key rows of a source as one dict: labels, scripts, cuts, trojans, rareness, sets,
    failures, catalogue. For a top-up tree the rows are rebuilt from the per-base job files."""
    k = src.key
    if (k / "labels.json").is_file():
        return {n: _load(k / f"{n}.json") for n in
                ("labels", "scripts", "cuts", "trojans", "rareness", "sets", "failures")}
    labels: Json = {}
    scripts: Json = {}
    cuts: Json = {}
    trojans: Json = {}
    rareness: list[object] = []
    sets: Json = {}
    failures: list[object] = []
    for jf in sorted((k / "jobs").glob("*.json")):
        r = _as_dict(_load(jf))
        base = str(r["base"])
        failures += _as_list(r.get("failures", []))
        sets[base] = {"new": _as_dict(r["sets"]), "golden": r.get("golden")}
        for c in _as_list(r["circuits"]):
            c = _as_dict(c)
            cid = str(c["id"])
            scripts[cid] = {"set": c["set"], "map": c["map"], "script": c["script"]}
            cuts[cid] = {"sizes": c.get("cut_sizes", []), "labels": c.get("cut_labels", []),
                         "rings": c.get("rings", {}), "slow_depth": c.get("slow_depth"),
                         "slow_depth_ref": c.get("slow_depth_ref")}
            specs = c.get("specs")
            if isinstance(specs, list):
                from lemanruss.htl.n200run import _tid

                labels[cid] = "+".join(_tid(_as_dict(s)) for s in specs)
                trojans[cid] = specs
                rareness += _as_list(c["records"])
            else:
                labels[cid] = None
    return {"labels": labels, "scripts": scripts, "cuts": cuts, "trojans": trojans,
            "rareness": rareness, "sets": sets, "failures": failures}


def reason_summary(failures: list[object], base: str, set_name: str) -> str:
    """The distinct causes recorded for a cell, counted, shortest first."""
    seen: dict[str, int] = {}
    for f in failures:
        f = _as_dict(f)
        if f["base"] == base and (set_name == "all" or f["set"] in (set_name, "all")):
            r = str(f["reason"])
            for pre in ("insert: ", "obfuscated circuit vs its source"):
                if r.startswith(pre):
                    r = r.split(":")[0] if pre == "insert: " else pre
            seen[r[:100]] = seen.get(r[:100], 0) + 1
    return "; ".join(f"{k}" + (f" (x{n})" if n > 1 else "") for k, n in sorted(seen.items()))


def merge_family(
    family: str, rc: Source, tops: list[Source], si: Source | None, si_tops: list[Source],
    out: Path, tools: Tools, version: str, id_seed: int, datasheet_text: str,
) -> Json:
    """Writes the merged release `out` (must not exist). Returns counts and dropped cells."""
    short = "sc" if family == "Seeker-Comb" else "ss"
    rows = tree_rows(rc)
    rc_sets = _as_dict(rows["sets"])
    labels = dict(_as_dict(rows["labels"]))
    scripts = dict(_as_dict(rows["scripts"]))
    cuts = dict(_as_dict(rows["cuts"]))
    trojans = dict(_as_dict(rows["trojans"]))
    rareness = list(_as_list(rows["rareness"]))
    failures = list(_as_list(rows["failures"]))
    src_of: dict[str, Source] = {c: rc for c in labels}
    wit: dict[str, Json] = {}
    cells: dict[tuple[str, str], Json] = {}
    gold: dict[str, str] = {}
    kind_of: dict[str, tuple[object, object]] = {}
    for base, v in rc_sets.items():
        v = _as_dict(v)
        gold[base] = str(v["golden"])
        kind_of[base] = (v.get("kind"), v.get("gates"))
        for name, cell in _as_dict(v["sets"]).items():
            cells[(base, name)] = dict(_as_dict(cell))
    for t in tops:
        tr = tree_rows(t)
        for cid in _as_dict(tr["labels"]):
            src_of[cid] = t
        labels.update(_as_dict(tr["labels"]))
        scripts.update(_as_dict(tr["scripts"]))
        cuts.update(_as_dict(tr["cuts"]))
        trojans.update(_as_dict(tr["trojans"]))
        rareness += _as_list(tr["rareness"])
        failures += _as_list(tr["failures"])
    # attach top-up circuits to their cells through the per-base job files
    for t in tops:
        for jf in sorted((t.key / "jobs").glob("*.json")):
            r = _as_dict(_load(jf))
            base = str(r["base"])
            for c in _as_list(r["circuits"]):
                c = _as_dict(c)
                cell = cells.setdefault((base, str(c["set"])), {
                    "map": str(c["map"]), "n_infected_drawn": 0,
                    "infected_ids": [], "clean_ids": []})
                key = "infected_ids" if str(c["id"]) in trojans else "clean_ids"
                _as_list(cell.setdefault(key, [])).append(str(c["id"]))
            for name, info in _as_dict(r["sets"]).items():
                cell = cells[(base, name)]
                cell["map"] = _as_dict(info)["map"]
                cell["n_infected_drawn"] = _as_dict(info)["n_infected_drawn"]
            w = t.witnesses(base)
            wit.setdefault(base, {"inputs": w["inputs"], "steps": {}})
            _as_dict(wit[base]["steps"]).update(_as_dict(w["steps"]))
    # silicon: new ids, renamed rows
    s_gold: dict[str, str] = {}
    rename: dict[str, str] = {}
    if si is not None:
        si_rows = tree_rows(si)
        s_sets = _as_dict(si_rows["sets"])
        s_ids: list[str] = []
        for _b, v in sorted(s_sets.items()):
            v = _as_dict(v)
            s_ids.append(str(v["golden"]))
            for _name, cell in _as_dict(v["sets"]).items():
                s_ids += [str(i) for i in _as_list(_as_dict(cell)["infected_ids"])
                          + _as_list(_as_dict(cell)["clean_ids"])]
        for st in si_tops:
            for jf in sorted((st.key / "jobs").glob("*.json")):
                r = _as_dict(_load(jf))
                s_ids += [str(_as_dict(c)["id"]) for c in _as_list(r["circuits"])]
        top = max(int(i[2:]) for i in src_of) + 1
        new = [f"{short}{top + n:04d}" for n in range(len(s_ids))]
        random.Random(f"{id_seed}:silicon-ids").shuffle(new)
        rename = dict(zip(sorted(s_ids), new, strict=True))
        # the silicon rows, under the new ids
        for cid, v in _as_dict(si_rows["labels"]).items():
            if cid in rename:
                labels[rename[cid]] = v
        for name_, dst in (("scripts", scripts), ("cuts", cuts), ("trojans", trojans)):
            for cid, v in _as_dict(si_rows[name_]).items():
                if cid in rename:
                    dst[rename[cid]] = v
        for r0 in _as_list(si_rows["rareness"]):
            rr = dict(_as_dict(r0))
            if str(rr["circuit"]) in rename:
                rr["circuit"] = rename[str(rr["circuit"])]
                rareness.append(rr)
        failures += _as_list(si_rows["failures"])
        for cid in rename.values():
            src_of[cid] = si
        for base, v in s_sets.items():
            v = _as_dict(v)
            s_gold[base] = rename[str(v["golden"])]
            for name, cell in _as_dict(v["sets"]).items():
                c2 = dict(_as_dict(cell))
                c2["infected_ids"] = [rename[str(i)] for i in _as_list(c2["infected_ids"])]
                c2["clean_ids"] = [rename[str(i)] for i in _as_list(c2["clean_ids"])]
                cells[(base, name)] = c2
            w = si.witnesses(base)
            wit.setdefault(base, {"inputs": w["inputs"], "steps": {}})
            _as_dict(wit[base]["steps"]).update(
                {rename.get(k, k): v2 for k, v2 in _as_dict(w["steps"]).items()})
        for st in si_tops:
            tr = tree_rows(st)
            for name_, dst in (("labels", labels), ("scripts", scripts), ("cuts", cuts),
                               ("trojans", trojans)):
                for cid, v in _as_dict(tr[name_]).items():
                    dst[rename[cid]] = v
            for r1 in _as_list(tr["rareness"]):
                rr = dict(_as_dict(r1))
                rr["circuit"] = rename[str(rr["circuit"])]
                rareness.append(rr)
            failures += _as_list(tr["failures"])
            for cid in _as_dict(tr["labels"]):
                src_of[rename[cid]] = st
            for jf in sorted((st.key / "jobs").glob("*.json")):
                r = _as_dict(_load(jf))
                base = str(r["base"])
                for c in _as_list(r["circuits"]):
                    c = _as_dict(c)
                    new_id = rename[str(c["id"])]
                    cell = cells.setdefault((base, "S"), {
                        "map": "silicon", "n_infected_drawn": 0, "infected_ids": [],
                        "clean_ids": []})
                    key = "infected_ids" if str(c["id"]) in _as_dict(tr["trojans"]) else "clean_ids"
                    _as_list(cell[key]).append(new_id)
                w = st.witnesses(base)
                _as_dict(wit[base]["steps"]).update(
                    {rename[k]: v2 for k, v2 in _as_dict(w["steps"]).items()})
    # decide cells
    kept: dict[tuple[str, str], Json] = {}
    dropped: list[Json] = []
    for (base, name), cell in sorted(cells.items()):
        n_inf, n_cl = len(_as_list(cell["infected_ids"])), len(_as_list(cell["clean_ids"]))
        if n_inf + n_cl == N_SET:
            cell["infected"], cell["clean"] = n_inf, n_cl
            kept[(base, name)] = cell
        else:
            dropped.append({"base": base, "set": name, "circuits_built": n_inf + n_cl,
                            "infected": n_inf, "clean": n_cl,
                            "n_infected_drawn": cell.get("n_infected_drawn"),
                            "cause": reason_summary(failures, base, name)})
    bases = sorted({b for b, _n in kept})
    for base in sorted(set(gold) - set(bases)):
        dropped.append({"base": base, "set": "all", "circuits_built": 0,
                        "cause": "no complete cell: " + reason_summary(failures, base, "all")})
    # write
    out_c, out_k = out / "circuits", out / "answer_key"
    out_c.mkdir(parents=True, exist_ok=False)
    (out_k / "pre").mkdir(parents=True)
    (out_k / "witnesses").mkdir()
    keep_ids: dict[str, tuple[str, str]] = {}
    sets_out: dict[str, Json] = {}
    for base in bases:
        entry: Json = {"golden": gold[base], "kind": kind_of[base][0], "gates": kind_of[base][1],
                       "sets": {}}
        keep_ids[gold[base]] = (base, "golden")
        for name in SET_ORDER:
            cell = kept.get((base, name))
            if cell is None:
                continue
            c2 = {k: v for k, v in cell.items() if k in
                  ("map", "n_infected_drawn", "infected", "clean", "infected_ids", "clean_ids")}
            if name == "S":
                c2["golden"] = s_gold[base]
                keep_ids[s_gold[base]] = (base, "S-golden")
            _as_dict(entry["sets"])[name] = c2
            for cid2 in _as_list(c2["infected_ids"]) + _as_list(c2["clean_ids"]):
                keep_ids[str(cid2)] = (base, name)
        sets_out[base] = entry
    files: dict[str, bytes] = {}
    inv = {v: k for k, v in rename.items()}
    for cid in sorted(keep_ids):
        s = src_of.get(cid)
        if s is None:  # a golden (rc tree) or a silicon golden
            s = si if cid in inv and si is not None else rc
        orig = inv.get(cid, cid)
        files[cid] = s.circuit_gz(orig)
        (out_c / f"{cid}.blif.gz").write_bytes(files[cid])
        v = s.verilog_gz(orig)
        if v is not None:
            (out / "circuits_v").mkdir(exist_ok=True)
            (out / "circuits_v" / f"{cid}.v.gz").write_bytes(v)
        p = s.pre_gz(orig)
        if p is not None:
            (out_k / "pre" / f"{cid}.blif.gz").write_bytes(p)
    kept_labels = {c: labels.get(c) for c in keep_ids}
    for base in bases:
        wb = wit.get(base)
        rcw: Json = rc.witnesses(base)
        base_w: Json = {"inputs": rcw["inputs"], "steps": dict(_as_dict(rcw["steps"]))}
        if wb:
            if not base_w["inputs"]:
                base_w["inputs"] = wb["inputs"]
            _as_dict(base_w["steps"]).update(_as_dict(wb["steps"]))
        steps = {k: v for k, v in _as_dict(base_w["steps"]).items() if k in keep_ids}
        if steps:
            with gzip.GzipFile(filename="", mode="wb", mtime=0, compresslevel=9,
                               fileobj=(out_k / "witnesses" / f"{base}.json.gz").open("wb")) as fh:
                fh.write(json.dumps({"inputs": base_w["inputs"], "steps": steps}).encode("utf-8"))
    gold_of: dict[str, str] = {}
    set_of: dict[str, str] = {}
    for entry in sets_out.values():
        gold_of[str(entry["golden"])] = str(entry["golden"])
        set_of[str(entry["golden"])] = "golden"
        for name, cell in _as_dict(entry["sets"]).items():
            cell = _as_dict(cell)
            g = str(cell.get("golden", entry["golden"]))
            if "golden" in cell:
                gold_of[g] = g
                set_of[g] = "S-golden"
            for cid2 in _as_list(cell["infected_ids"]) + _as_list(cell["clean_ids"]):
                gold_of[str(cid2)] = g
                set_of[str(cid2)] = name
    prov: dict[str, Json] = {}
    by_base: dict[str, int] = {}
    for cid in sorted(keep_ids):
        base = keep_ids[cid][0]
        by_base[base] = by_base.get(base, 0) + 1
        kind = _as_dict(sets_out[base]).get("kind")
        prov[cid] = {"base": base, "stratum": f"{base}/{set_of[cid]}", "source": cid,
                     "restructuring": "identity",
                     "role": "clean" if kept_labels[cid] is None else "infected",
                     "clean_twin": gold_of[cid], "set": set_of[cid],
                     "insert": ({"kind": kind, "trojans": trojans[cid], "base": base,
                                 "n_trojans": len(_as_list(trojans[cid]))}
                                if cid in trojans else None)}
    n_clean = sum(1 for v in kept_labels.values() if v is None)
    cat_all: Json = {}
    mans = [rc] + tops + ([si] if si else []) + si_tops
    for m in mans:
        mp = m.root / "manifest.json"
        if mp.is_file():
            cat_all.update(_as_dict(_as_dict(_load(mp)).get("trojan_catalogue", {})))
        cp = m.key / "catalogue.json"
        if cp.is_file():
            cat_all.update(_as_dict(_as_dict(_load(cp)).get("trojan_catalogue", {})))
    used_t = {t for v in kept_labels.values() if v for t in str(v).split("+")}
    catalogue = {k: v for k, v in cat_all.items() if k in used_t}
    _dump(out_k / "labels.json", kept_labels)
    _dump(out_k / "provenance.json", prov)
    (out_k / "renames.json").write_text("{}\n", encoding="utf-8")
    _dump(out_k / "sets.json", sets_out)
    _dump(out_k / "rareness.json", [r for r in rareness if str(_as_dict(r)["circuit"]) in keep_ids])
    _dump(out_k / "failures.json", failures)
    _dump(out_k / "dropped_cells.json", dropped)
    _dump(out_k / "scripts.json", {c: scripts[c] for c in keep_ids if c in scripts})
    _dump(out_k / "trojans.json", {c: trojans[c] for c in keep_ids if c in trojans})
    _dump(out_k / "cuts.json", {c: cuts[c] for c in keep_ids if c in cuts})
    _dump(out_k / "catalogue.json", {"trojan_catalogue": catalogue, "trojans": sorted(catalogue),
                                     "mix": {"clean": n_clean,
                                             "infected": len(keep_ids) - n_clean}})
    name = f"{short_name(family)}-v{version}"
    manifest: Json = {
        "release": name, "family": family, "version": version,
        "tools": {"odin3_build_pin": tools.odin3_build_pin, "abc": tools.abc},
        "restructurings": ["identity"],
        "goldens": {b: _as_dict(sets_out[b])["golden"] for b in bases},
        "goldens_silicon": {b: s_gold[b] for b in bases if (b, "S") in kept},
        "counts": {"circuits": len(files), "by_base": dict(sorted(by_base.items())),
                   "by_restructuring": {"identity": len(files)}},
        "answer_key": "answer_key/ (shipped as a separate archive; a detector must not read it)",
        "circuits": [{"id": cid, "base": keep_ids[cid][0], "file": f"circuits/{cid}.blif.gz",
                      "bytes": len(files[cid]), "sha256": hashlib.sha256(files[cid]).hexdigest()}
                     for cid in sorted(files)],
    }
    _dump(out / "manifest.json", manifest)
    (out / "DATASHEET.md").write_text(datasheet_text, encoding="utf-8")
    write_sha256sums(out)
    return {"release": name, "circuits": len(files), "clean": n_clean,
            "infected": len(files) - n_clean, "bases": len(bases),
            "cells": len(kept), "dropped": dropped}


def v2_datasheet(family: str, name: str, root: Path, tools: Tools, odin_version: str,
                 stimulus_md: str) -> str:
    """Datasheet of a merged release: contents, per-base table, dropped cells with causes."""
    from lemanruss.htl.n200run import tables
    from lemanruss.htl.seqoc import source_of

    man = _as_dict(_load(root / "manifest.json"))
    counts = _as_dict(man["counts"])
    dropped = _as_list(_load(root / "answer_key" / "dropped_cells.json"))
    labels = _as_dict(_load(root / "answer_key" / "labels.json"))
    n_inf = sum(1 for v in labels.values() if v is not None)
    by_base = _as_dict(counts["by_base"])
    lines = [
        f"# {name} datasheet", "",
        f"Family: {family}. Version 2.0 (supersedes the release candidates). Produced by Leman "
        "Russ III (Yggdrasil III). Defensive hardware-Trojan detection research; the circuits "
        "are Trojans to detect, nothing here is meant to be deployed.", "",
        "## Contents", "",
        f"- circuits: {counts['circuits']} in `circuits/<id>.blif.gz`, {n_inf} infected and "
        f"{int(str(counts['circuits'])) - n_inf} clean, opaque ids; silicon cell Verilog in "
        "`circuits_v/<id>.v.gz`.",
        f"- benchmarks: {len(by_base)}; per benchmark a golden (plus a silicon golden), and every "
        "target with exactly 100 circuits: K4 (LUT k=4), K6 (LUT k=6), G (AND/OR/NOT gates), "
        "S (sky130_fd_sc_hd silicon). A random 10 to 70 of each 100 are infected with 1 to 3 "
        "Trojans (P = 0.5, 0.3, 0.2). A target short of 100 distinct, gated circuits is not "
        "shipped (below).",
        "- rc circuits of the earlier candidates are kept byte for byte (same ids); circuits "
        "added to fill cells were built with the same pipeline and gates, distinct from every "
        "earlier circuit of the base; silicon circuits are those of Seeker-Si rc2 under new ids.",
        "- answer key: `answer_key/` (labels, sets, Trojans, scripts, rareness, witnesses, "
        "`pre/`, `dropped_cells.json`); a detector must not read it.", "",
        "Circuits per benchmark: " + ", ".join(f"{b} {n}" for b, n in sorted(by_base.items())), "",
        "## Dropped cells (never padded, distinctness never relaxed)", "",
        "| benchmark | target | built | cause |", "|---|---|---|---|"]
    for d in dropped:
        d = _as_dict(d)
        lines.append(f"| {d['base']} | {d['set']} | {d['circuits_built']} | {d['cause']} |")
    lines += ["", stimulus_md, "", "## Tools", "",
              f"- Odin III {odin_version} builds the added circuits (rc circuits: "
              f"{tools.odin3_build_pin}); ABC: {tools.abc}.", "",
              "## Bases", "",
              ", ".join(f"{b} ({source_of(b)})" for b in sorted(by_base)), "",
              "## Tables", "", *tables(root), "",
              "## Check", "", "`sha256sum -c SHA256SUMS`, then `lemanruss verify <dir>`.", ""]
    return "\n".join(lines)
