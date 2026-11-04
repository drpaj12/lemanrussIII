"""Round 5 reports: edit-API insertion counts, the provenance demo, comparison with round 4."""

from __future__ import annotations

import json
from pathlib import Path

from lemanruss.htl import edit_netlist as en


def insertion_summary(root: Path) -> list[str]:
    """Counts from `answer_key/insertion.json` of one family build."""
    ins = json.loads((root / "answer_key" / "insertion.json").read_text(encoding="utf-8"))
    n = len(ins)
    edit = [v for v in ins.values() if v["method"] == "odin3-edit"]
    fall = [(k, v["reason"]) for k, v in ins.items() if v["method"] != "odin3-edit"]
    split_ok = sum(1 for v in edit
                   if v["untagged_nodes"] + v.get("modified_nodes", 0) == v["base_nodes"]
                   and v["tagged_nodes"] == v["nodes"] - v["base_nodes"])
    htl = sum(1 for v in edit if v["tagged_all_htl"])
    lines = [f"- {n} infected circuits inserted; {len(edit)} by the Odin III edit API, "
             f"{len(fall)} by the text fallback",
             f"- provenance separates inserted from clean: {split_ok}/{len(edit)} circuits have "
             f"untouched + moved-pin nodes == clean nodes and tagged nodes == added nodes; "
             f"{htl}/{len(edit)} have every tagged net named __htl*",
             f"- inserted nodes in total {sum(v['tagged_nodes'] for v in edit)}, nets "
             f"{sum(v['tagged_nets'] for v in edit)}, clean nodes carried unchanged "
             f"{sum(v['untagged_nodes'] for v in edit)}, clean nodes with moved pins (events "
             f"removed / rewired) {sum(v.get('modified_nodes', 0) for v in edit)}"]
    lines += [f"- fallback {k}: {why}" for k, why in fall]
    return lines


def provenance_demo(base: Path, out: Path, tag: str = "trojan:demo") -> list[str]:
    """Inserts a small Trojan and prints what the provenance says about each object."""
    from odin3 import Design

    def recipe(ed: en.Editor) -> None:
        en.always_on_trigger(ed)
        en.energy(ed, "clock", 1)

    lines: list[str] = []
    with Design() as design:
        design.run_pass("read_blif", str(base))
        ed = en.EditNetlist(design, tag)
        recipe(ed)
        for node in ed.top.nodes():
            if node.granularity == "port":
                continue
            recs = node.provenance()
            kind = recs[0].kind if recs else "none"
            outs = [n.name for p in node.pins() if p.direction() == "out"
                    and (n := p.net()) is not None]
            lines.append(f"- {node.type_name} -> {','.join(outs)}: edit_tag={node.edit_tag!r}, "
                         f"provenance kind={kind}")
        design.run_pass("write_blif", str(out))
    return lines
