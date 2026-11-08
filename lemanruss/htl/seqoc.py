"""Seeker-Seq rc8: the rc7 release unchanged plus the admitted OpenCores bases.

The OpenCores bases are built as a separate rc7-style tree (`n200rc7.run_family_rc7` with
`first_index` after the 36 rc7 id blocks). `merge_roots` then joins that tree and an unpacked
rc7 release into one build root that `build_release_n200` packages: the rc7 circuits are
byte-identical (gunzip here, the same zero-timestamp gzip in the release), so the 36 rc7 bases
are not rebuilt. Nothing in this module reads or prints a seed.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
from pathlib import Path

from lemanruss.htl import ocbases

Json = dict[str, object]

RC7_BASES = 36


def source_of(base: str) -> str:
    """Where a base comes from (the datasheet's source column)."""
    if base in {d.name for d in ocbases.DESIGNS}:
        return "OpenCores"
    if re.fullmatch(r"s\d+", base):
        return "ISCAS-89"
    if re.fullmatch(r"b\d\d", base):
        return "ITC-99"
    if re.fullmatch(r"C\d+", base):
        return "ISCAS-85"
    if base.startswith("ve_"):
        return "VerilogEval"
    if base in {"alu4", "apex2", "apex4", "cordic", "ex5p", "misex3", "pdc", "spla", "t481"}:
        return "MCNC"
    return "VTR"


def opencores_licence_lines(bases: list[str]) -> list[str]:
    """Datasheet lines for the OpenCores bases (licence as the file header or COPYING states
    it, with the place it was read)."""
    by = {d.name: d for d in ocbases.DESIGNS}
    out = []
    got = [b for b in bases if b in by]
    if got:
        out.append(f"- OpenCores ({len(got)}: {', '.join(sorted(got))}), per project:")
        for b in sorted(got):
            d = by[b]
            out.append(f"  - {b}: {d.licence} ({d.licence_where}). {d.reason}.")
        out.append("  The circuits derived from an OpenCores project are derivative works of "
                   "its RTL: each project's own licence applies to them, and the notices above "
                   "are kept with this release.")
    return out


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_dict(obj: object) -> dict[str, object]:
    assert isinstance(obj, dict)
    return obj


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def merge_roots(rc7: Path, rc7_manifest: Path, new: Path, out: Path) -> dict[str, int]:
    """Builds the rc8 build root `out` from the unpacked rc7 release `rc7` (circuits/ and
    answer_key/ of the archive), its release manifest, and the OpenCores build tree `new`.
    Returns the circuit counts. `out` must not exist."""
    key7, keyn = rc7 / "answer_key", new / "answer_key"
    out_c, out_k = out / "circuits", out / "answer_key"
    out_c.mkdir(parents=True)
    (out_k / "pre").mkdir(parents=True)
    (out_k / "witnesses").mkdir()
    man7 = json.loads(gzip.decompress(rc7_manifest.read_bytes()).decode("utf-8"))
    mann = _read_json(new / "manifest.json")
    assert isinstance(mann, dict)
    circuits: list[dict[str, str]] = []
    for c in man7["circuits"]:
        cid = str(c["id"])
        (out_c / f"{cid}.blif").write_bytes(
            gzip.decompress((rc7 / "circuits" / f"{cid}.blif.gz").read_bytes()))
        circuits.append({"id": cid, "base": str(c["base"]), "file": f"circuits/{cid}.blif"})
    n7 = len(circuits)
    for c in mann["circuits"]:
        cid = str(c["id"])
        shutil.copyfile(new / c["file"], out_c / f"{cid}.blif")
        circuits.append({"id": cid, "base": str(c["base"]), "file": f"circuits/{cid}.blif"})
    ids = [c["id"] for c in circuits]
    if len(set(ids)) != len(ids):
        raise ValueError("circuit ids collide between rc7 and the OpenCores tree")
    for name in ("labels", "sets", "scripts", "trojans", "cuts"):
        a, b = _read_json(key7 / f"{name}.json"), _read_json(keyn / f"{name}.json")
        assert isinstance(a, dict) and isinstance(b, dict)
        if set(a) & set(b):
            raise ValueError(f"{name}: keys collide")
        _write_json(out_k / f"{name}.json", {**a, **b})
    for name in ("rareness", "failures"):
        a, b = _read_json(key7 / f"{name}.json"), _read_json(keyn / f"{name}.json")
        assert isinstance(a, list) and isinstance(b, list)
        _write_json(out_k / f"{name}.json", a + b)
    for src in (key7, keyn):
        for sub in ("pre", "witnesses"):
            for f in sorted((src / sub).iterdir()):
                shutil.copyfile(f, out_k / sub / f.name)
    cat7 = _read_json(key7 / "catalogue.json")
    assert isinstance(cat7, dict)
    tc = {**_as_dict(cat7["trojan_catalogue"]), **_as_dict(mann["trojan_catalogue"])}
    labels = _read_json(out_k / "labels.json")
    assert isinstance(labels, dict)
    infected = sum(1 for v in labels.values() if v is not None)
    manifest: Json = {
        "family": "Seeker-Seq", "version": mann["version"], "schema": mann["schema"],
        "v1_lineage": mann["v1_lineage"], "adds": mann["adds"],
        "bases": sorted({c["base"] for c in circuits}),
        "goldens": {**_as_dict(man7["goldens"]), **_as_dict(mann["goldens"])},
        "trojans": sorted(tc), "trojan_catalogue": tc,
        "circuits": sorted(circuits, key=lambda c: c["id"]),
        "mix": {"clean": len(labels) - infected, "infected": infected,
                "infected_fraction": infected / len(labels)},
        "seed": 0,
        "labels": "answer_key/labels.json (separate; a detector must not read answer_key/)",
    }
    _write_json(out / "manifest.json", manifest)
    return {"rc7": n7, "new": len(circuits) - n7, "infected": infected}
