"""Seeker-Si (silicon set) as a detector release: records, the three leave-one-base-out
splits and Trojan regions from the answer key (victim output, witness replayed on a clean circuit of
the same base as golden). The circuit a detector reads is the gates-as-names BLIF of each circuit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lemanruss.detect.data import Record, read_text
from lemanruss.detect.splits import Split, make_split
from lemanruss.score import regions as rg


class SiRelease:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.family = "Si"
        man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        self.key: dict[str, Any] = json.loads(
            (root / "answer_key.json").read_text(encoding="utf-8"))
        files = {c["id"]: root / c["blif"] for c in man["circuits"]}
        by_base: dict[str, Path] = {}
        for e in self.key["circuits"]:
            if e["label"] == "clean":
                by_base.setdefault(e["base"], files[e["id"]])
        self.records: list[Record] = []
        for e in self.key["circuits"]:
            inf = e["label"] == "infected"
            self.records.append(Record(
                e["id"], e["base"], "si", inf, int(e["trojans"]) if inf else 0, "", "",
                files[e["id"]], by_base[e["base"]]))
        self.records.sort(key=lambda r: r.id)

    def bases(self) -> list[str]:
        return sorted({r.base for r in self.records})

    def splits(self) -> list[Split]:
        folds = [[b] for b in self.bases()]
        return [make_split(self.records, "base", k, folds) for k in range(len(folds))]

    def regions(self) -> dict[str, Any]:
        """Trojan regions of every infected circuit (answer-key use only)."""
        ref = {r.base: r.reference for r in self.records}
        out: dict[str, Any] = {}
        for e in self.key["circuits"]:
            if e["label"] != "infected":
                continue
            rel = rg.parse_blif(read_text(self.root / "circuits" / f"{e['id']}.blif"))
            gold = rg.parse_blif(read_text(ref[e["base"]]))
            clocks = _clocks(read_text(ref[e["base"]]))
            names = [n for n in gold.inputs if n not in clocks]
            wl = [(names, e["witness"].get(str(j), [])) for j in range(len(e["specs"]))]
            victims = [str(t["victim"]) for t in e["specs"]]
            n_nets = len(rel.gates) + len(rel.latches)
            out[e["id"]] = {"n_nets": n_nets, "trojans": rg.region_of(
                gold, rel, wl, victims, f"si-regions/{e['id']}")}
        return out


def _clocks(text: str) -> set[str]:
    """Clock nets of a BLIF: the control field of its `.latch d q type control init` lines."""
    out: set[str] = set()
    for ln in text.splitlines():
        w = ln.split()
        if w and w[0] == ".latch" and len(w) >= 5:
            out.add(w[4])
    return out
