"""Release loading: released circuit files for detectors, answer-key metadata for the harness."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

LUT_FORMS = ("lut4", "lut5", "lut6", "lut6mfs")
SETS = ("K4", "K6", "G")  # rc4: LUT k=4, LUT k=6, AND/OR/NOT gates; "golden" is unobfuscated


@dataclass(frozen=True)
class CircuitFile:
    """All a detector may see of a circuit: an opaque id and the released BLIF path."""

    id: str
    path: Path


@dataclass(frozen=True)
class ReferencedFile(CircuitFile):
    """Reference-assisted detectors only (Method B): adds the form and the clean reference."""

    form: str
    reference: Path


@dataclass(frozen=True)
class Record:
    """Harness-side metadata of one circuit (answer key)."""

    id: str
    base: str
    form: str
    infected: bool
    n_trojans: int
    set: str  # "A", "B" or "" (rc1/rc2)
    variant: str  # rareness variant/band ("" for clean)
    path: Path
    reference: Path


def read_text(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return fh.read()
    return path.read_text(encoding="utf-8")


def _trojans(insert: dict[str, object]) -> int:
    n = insert.get("n_trojans", 1)
    return int(n) if isinstance(n, int) else 1


def _variant(insert: dict[str, object]) -> str:
    v = insert.get("variant")
    if isinstance(v, str):
        return v
    ts = insert.get("trojans")
    if isinstance(ts, list) and ts and isinstance(ts[0], dict):
        band = str(ts[0].get("band", ""))
        trig = str(ts[0].get("trig", ""))
        return band if trig in ("", "comb") else f"{trig}-{band}"
    return ""


class Release:
    """A release directory (circuits/, manifest.json, answer_key/)."""

    def __init__(self, root: Path, family: str) -> None:
        self.root = root
        self.family = family
        man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        prov = json.loads((root / "answer_key" / "provenance.json").read_text(encoding="utf-8"))
        sets: dict[str, str] = {}
        sets_file = root / "answer_key" / "sets.json"
        files = {c["id"]: root / c["file"] for c in man["circuits"]}
        goldens: dict[str, str] = {}
        if sets_file.is_file():
            for base, per_base in json.loads(sets_file.read_text(encoding="utf-8")).items():
                if isinstance(per_base.get("golden"), str):
                    goldens[base] = per_base["golden"]
        # Seeker-Proc ships the clean twin of an infected circuit only in the answer key (the
        # released set holds one circuit per slot): the reference of Method B for those.
        twin_dir = root / "answer_key" / "twins"
        twins = {f.name.split(".")[0]: f for f in sorted(twin_dir.glob("*.blif*"))}
        self.records: list[Record] = []
        for cid, meta in prov.items():
            if cid not in files:
                continue
            insert = meta.get("insert") or prov[meta["source"]].get("insert") or {}
            twin = goldens.get(meta["base"], meta["clean_twin"])
            infected = meta["role"] == "infected"
            self.records.append(
                Record(
                    id=cid,
                    base=meta["base"],
                    form=meta["restructuring"],
                    infected=infected,
                    n_trojans=_trojans(insert) if infected else 0,
                    set=str(meta.get("set") or sets.get(cid, sets.get(meta["source"], ""))),
                    variant=_variant(insert) if infected else "",
                    path=files[cid],
                    reference=files.get(twin) or twins.get(cid) or files[cid],
                )
            )
        self.records.sort(key=lambda r: r.id)

    def bases(self) -> list[str]:
        return sorted({r.base for r in self.records})

    def of_bases(self, bases: set[str]) -> list[Record]:
        return [r for r in self.records if r.base in bases]


def view(rec: Record) -> CircuitFile:
    return CircuitFile(rec.id, rec.path)


def ref_view(rec: Record) -> ReferencedFile:
    """Method B's view; the 'form' it calibrates per is the set when the release has sets."""
    return ReferencedFile(rec.id, rec.path, rec.set or rec.form, rec.reference)
