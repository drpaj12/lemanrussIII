"""JSON manifest for a built HTL catalogue or benchmark set.

Spec: docs/specs/2026-10-31-htl-design.md sections 2 and 5. Deterministic output (sorted keys,
\\n line ends, UTF-8, schema = 1) per the repo's own CLAUDE.md rule (mirrors loki).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from lemanruss.htl.trojan import Trojan


@dataclass
class CatalogueEntry:
    """One Trojan in the catalogue, with its base design and verification result (if run)."""

    base_design: str
    trojan: Trojan
    verification: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "base_design": self.base_design,
            "trojan": self.trojan.to_dict(),
            "verification": self.verification,
        }


def write_manifest(entries: list[CatalogueEntry], path: Path) -> None:
    """Writes the full catalogue manifest (schema 1) atomically-enough for this repo's needs."""
    doc = {
        "schema": 1,
        "entries": [e.to_dict() for e in entries],
    }
    path.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_labels(entries: list[CatalogueEntry], path: Path) -> None:
    """Writes labels.json: base_design -> trojan id, kept separate from any circuit file.

    This is the answer key (spec section 5 / CLAUDE.md): a detector pointed at the circuits
    directory must never see this file.
    """
    labels = {f"{e.base_design}::{e.trojan.id}": e.trojan.id for e in entries}
    path.write_text(
        json.dumps(labels, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
