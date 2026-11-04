"""Minimal BLIF text helpers used by the netlist-level inserter (lemanruss.htl.insert_netlist).

Not a full BLIF parser: enough structure to find a model's `.inputs`/`.outputs` lines and the
`.names` block driving a chosen net, append new `.names` lines, and rewrite one output's driver.
Every edit is re-validated by re-reading the result with Odin III's `read_blif` (the parse check
the brief asks for); this module only produces text, it never claims a result is legal BLIF.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BlifModel:
    """One `.model ... .end` block, split into its header lines and body lines."""

    name: str
    inputs: list[str]
    outputs: list[str]
    body: list[str]  # every line between the header lines and `.end`, verbatim


def parse_single_model(text: str) -> BlifModel:
    """Parses a BLIF file with exactly one `.model`; ValueError otherwise."""
    # BLIF continuation: a line ending in a backslash continues on the next line (MCNC / VTR
    # BLIF wrap long .inputs / .outputs lists this way).
    lines = text.replace("\\\n", " ").replace("\\\r\n", " ").splitlines()
    name = None
    inputs: list[str] = []
    outputs: list[str] = []
    body: list[str] = []
    in_model = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith(".model "):
            if in_model:
                raise ValueError("blif_text: more than one .model (not supported)")
            name = line.split(None, 1)[1].strip()
            in_model = True
        elif line == ".end":
            in_model = False
        elif line.startswith(".inputs "):
            inputs.extend(line.split()[1:])
        elif line.startswith(".outputs "):
            outputs.extend(line.split()[1:])
        elif line.strip():
            body.append(line)
    if name is None:
        raise ValueError("blif_text: no .model found")
    return BlifModel(name=name, inputs=inputs, outputs=outputs, body=body)


def find_names_block(model: BlifModel, output_net: str) -> tuple[int, list[str], list[str]] | None:
    """The `.names <inputs...> output_net` line driving `output_net`, if any: its index in
    `model.body`, its input net names, and its cover-row lines. None when no `.names` line in the
    body drives that net (e.g. it is a `.latch` output or a primary input)."""
    i = 0
    while i < len(model.body):
        line = model.body[i]
        if line.startswith(".names "):
            words = line.split()[1:]
            if words and words[-1] == output_net:
                rows: list[str] = []
                j = i + 1
                while j < len(model.body) and not model.body[j].startswith("."):
                    rows.append(model.body[j])
                    j += 1
                return i, words[:-1], rows
        i += 1
    return None


def render(model: BlifModel) -> str:
    """Renders `model` back to BLIF text (the shape Odin III's own `.model`/`.end` wrap)."""
    lines = [f".model {model.name}"]
    if model.inputs:
        lines.append(".inputs " + " ".join(model.inputs))
    if model.outputs:
        lines.append(".outputs " + " ".join(model.outputs))
    lines.extend(model.body)
    lines.append(".end")
    return "\n".join(lines) + "\n"


def names_line(inputs: list[str], output: str) -> str:
    return ".names " + " ".join([*inputs, output])


def net_name_by_cname_prefix(model: BlifModel, wire_name: str) -> str | None:
    """The BLIF net name of the `.names` block whose `.cname` starts with `wire_name + "."`
    (`write_blif`'s own convention: the cell name is `<HDL wire name>.<generator>`, written right
    after the cover rows it names -- docs/PASSES.md's `write_blif` row). None when no such
    `.cname` line exists.

    Needed because `write_blif`'s default net naming ("short") assigns internal nets fresh names
    ($n8, $n9, ...) unrelated to the HDL wire name a `(* keep *)` Simulation measurement reports
    (lemanruss.htl.sites); `--name-style provenance` would keep the HDL name but needs `--vtr`,
    which refuses `--gates-as-names` (confirmed by running write_blif, not assumed) -- so this
    module's own inserters need this lookup to go from a measured wire name to the net name they
    must edit.
    """
    current_output: str | None = None
    for line in model.body:
        if line.startswith(".names "):
            current_output = line.split()[-1]
        elif line.startswith(".cname "):
            cname = line.split(None, 1)[1].strip()
            if cname.startswith(wire_name + ".") and current_output is not None:
                return current_output
    return None


ISO_SUFFIX = "__htl_pre"


def isolate_output(model: BlifModel, net: str) -> BlifModel:
    """Gives primary output `net` a fresh buffer of its own: every driver and reader inside the
    model now uses `net__htl_pre`, and a new `.names net__htl_pre net` buffer drives the port. A
    payload spliced on `net` then cannot feed back into the design (round 4: s298 / s526 / s953
    read every output internally). Functionally the identity. ValueError if `net` is not an
    output, or sits on a `.subckt`/`.gate` line (not handled)."""
    if net not in model.outputs:
        raise ValueError(f"isolate_output: {net} is not a primary output")
    pre = net + ISO_SUFFIX
    body: list[str] = []
    for line in model.body:
        if line.startswith((".subckt", ".gate")) and net in line.split():
            raise ValueError("isolate_output: net is used by a .subckt/.gate")
        if line.startswith(".names "):
            line = ".names " + " ".join(pre if w == net else w for w in line.split()[1:])
        elif line.startswith(".latch "):
            w = line.split()
            w[1:3] = [pre if x == net else x for x in w[1:3]]
            line = " ".join(w)
        body.append(line)
    body += [names_line([pre], net), "1 1"]
    return BlifModel(name=model.name, inputs=model.inputs, outputs=model.outputs, body=body)
