"""Netlist-level Trojan insertion through the Odin III edit API (round 5).

Replaces the BLIF text inserters of `lemanruss.htl.insert_netlist` (kept as a fallback). A Trojan
is written once as *recipes* over four primitives (`names`, `latch`, `splice`, `isolate`); two
editors implement them:

- `EditNetlist`: the Odin III edit API (`Module.add_net`, `add_sop`, `add_node`, `Pin.connect`,
  `Pin.disconnect`, `Pin.rewire`; docs/user/edit.md of Odin III). Every net and node it creates
  carries the edit tag `trojan:<Trojan id>`, so the provenance (`edit_tag`) separates inserted
  objects from the clean design.
- `TextNetlist`: the old BLIF text edits, used only when the edit API refuses (the reason is
  recorded in the `InsertReport`).

Spec section 3 and the round 5 plan section of docs/plans.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from lemanruss.htl.blif_text import (
    BlifModel,
    find_names_block,
    isolate_output,
    names_line,
    parse_single_model,
    render,
)

TRIGGER_NET = "__htl_trigger"


class Editor(Protocol):
    """The four primitives every recipe is written against."""

    def names(self, inputs: list[str], out: str, rows: list[str]) -> None: ...

    def latch(self, d: str, q: str, clock: str) -> None: ...

    def splice(self, victim: str) -> str: ...

    def isolate(self, net: str) -> None: ...


# ---- recipes (one per trigger / payload; same logic as insert_netlist) -----------------------


def comb_rare_trigger(
    ed: Editor, nets: tuple[tuple[str, int], ...], trig: str = TRIGGER_NET
) -> None:
    ed.names([n for n, _ in nets], trig, ["".join(str(v) for _, v in nets) + " 1"])


def always_on_trigger(ed: Editor, trig: str = TRIGGER_NET) -> None:
    ed.names([], trig, ["1"])


def input_pattern_trigger(
    ed: Editor, bits: tuple[str, ...], magic: int, trig: str = TRIGGER_NET
) -> None:
    ed.names(list(bits), trig, [format(magic, f"0{len(bits)}b") + " 1"])


def dos_stuck(ed: Editor, victim: str, stuck: int, trig: str = TRIGGER_NET) -> None:
    tmp = ed.splice(victim)
    ed.names([trig, tmp], victim, ["1- 1", "01 1"] if stuck else ["01 1"])


def err_bit(ed: Editor, victim: str, force: bool, trig: str = TRIGGER_NET) -> None:
    tmp = ed.splice(victim)
    ed.names([trig, tmp], victim, ["1- 1", "01 1"] if force else ["10 1", "01 1"])


def energy(
    ed: Editor, clock: str, n_bits: int, trig: str = TRIGGER_NET, p: str = "__htl_energy"
) -> None:
    for i in range(n_bits):
        q, d = f"{p}_q{i}", f"{p}_d{i}"
        ed.names([trig, q], d, ["10 1", "01 1"])
        ed.latch(d, q, clock)


def slowdown(ed: Editor, victim: str, depth: int) -> None:
    stage = ed.splice(victim)
    for i in range(depth):
        nxt = victim if i == depth - 1 else f"__htl_slow_{i + 1}_{victim}"
        ed.names([stage], nxt, ["1 1"])
        stage = nxt


def slowdown_absorb(ed: Editor, victim: str, srcs: list[str]) -> None:
    """Always-on slowdown that survives optimisation (cut-and-stitch rc5/rc6): the victim is
    `tmp | (tmp & s_1) | ... | (tmp & s_m)`, which equals `tmp` (absorption) but is not
    reducible by a tool that sees the OR alone (its inputs are independent nets). The ANDs stay
    in the host; the OR is the cut. `srcs` are primary inputs / latch outputs, so no loop."""
    stage = ed.splice(victim)
    ands = []
    for i, s in enumerate(srcs):
        u = f"__htl_slow_u{i}_{victim}"
        ed.names([stage, s], u, ["11 1"])
        ands.append(u)
    n = len(ands) + 1
    rows = ["-" * k + "1" + "-" * (n - k - 1) + " 1" for k in range(n)]
    ed.names([stage, *ands], victim, rows)


def seq_counter(
    ed: Editor, cond: tuple[tuple[str, int], ...], bits: int, clock: str, trig: str = TRIGGER_NET,
    p: str = "__htl_c",
) -> None:
    ed.names([n for n, _ in cond], f"{p}_e", ["".join(str(v) for _, v in cond) + " 1"])
    carry = f"{p}_e"
    for i in range(bits):
        q, d, nxt = f"{p}_q{i}", f"{p}_d{i}", f"{p}_k{i + 1}"
        ed.names([carry, q], d, ["10 1", "01 1"])
        ed.names([carry, q], nxt, ["11 1"])
        ed.latch(d, q, clock)
        carry = nxt
    ed.names([f"{p}_f", carry], f"{p}_fd", ["1- 1", "-1 1"])
    ed.latch(f"{p}_fd", f"{p}_f", clock)
    # The trigger is the sticky flag itself (one cycle after the last stage). `f | last` built
    # twice (flag input and trigger) is one node after ABC's strash; its complemented edge to the
    # latch then needs an inverter in front of the latch (rc5 gate `lat_dkind_inv`).
    ed.names([f"{p}_f"], trig, ["1 1"])


def seq_pattern(
    ed: Editor, cond: tuple[tuple[str, int], ...], clock: str, trig: str = TRIGGER_NET,
    p: str = "__htl_s",
) -> None:
    prev: str | None = None
    for i, (net, val) in enumerate(cond):
        d, q = f"{p}_d{i}", f"{p}_q{i}"
        if prev is None:
            # `net == val` and not yet fired: a two-input cell in front of the first latch (never a
            # lone inverter or buffer, which ABC would leave in front of the latch as a footprint,
            # rc5 gate `lat_dkind_inv`). After the flag is set nothing changes: the trigger is the
            # flag.
            ed.names([net, f"{p}_f"], d, [f"{val}0 1"])
        else:
            ed.names([prev, net], d, [f"1{val} 1"])
        ed.latch(d, q, clock)
        prev = q
    assert prev is not None
    ed.names([f"{p}_f", prev], f"{p}_fd", ["1- 1", "-1 1"])
    ed.latch(f"{p}_fd", f"{p}_f", clock)
    # The trigger is the sticky flag itself (one cycle after the last stage). `f | last` built
    # twice (flag input and trigger) is one node after ABC's strash; its complemented edge to the
    # latch then needs an inverter in front of the latch (rc5 gate `lat_dkind_inv`).
    ed.names([f"{p}_f"], trig, ["1 1"])


# ---- the two editors --------------------------------------------------------------------------


@dataclass
class InsertReport:
    """What one insertion did. `tagged_nodes` / `tagged_nets` are read back from the provenance
    (`edit_tag`) of the edited design, not counted from the recipe."""

    method: str  # "odin3-edit" or "text-fallback"
    reason: str = ""  # why the fallback ran; empty for odin3-edit
    tag: str = ""
    base_nodes: int = 0  # non-port nodes before the edit
    nodes: int = 0  # non-port nodes after the edit
    tagged_nodes: int = 0
    tagged_nets: int = 0
    untagged_nodes: int = 0  # non-port nodes no edit touched
    tagged_all_htl: bool = False  # every tagged net name holds __htl
    tagged_node_outputs: list[str] = field(default_factory=list)
    modified_nodes: int = 0  # clean nodes whose pins moved (events "removed" / "rewired")
    edit_blif: str = ""  # internal provenance file (write_blif --edit-tags), answer key only


@dataclass(frozen=True)
class LatchConvention:
    """How the circuit's own `.latch` lines are written: edge (`re` / `fe`) and init value
    (0, 1 or 2 / 3 = unknown). An inserted latch carries the same, so no field of a `.latch` line
    tells a Trojan flip-flop from the circuit's own (rc5; rc4 wrote init 0 where every other
    latch had 2 and so gave the label away)."""

    edge: str = "re"
    init: int = 0


DEFAULT_CONV = LatchConvention()


def convention_of(text: str) -> LatchConvention:
    """The most used (edge, init) of the `.latch` lines of the BLIF `text`; init 3 is read as 2
    (both are unknown). No latch: the default (`re`, 0)."""
    from collections import Counter

    seen = Counter[tuple[str, int]]()
    for ln in text.replace("\\\n", " ").splitlines():
        w = ln.split()
        if w and w[0] == ".latch" and len(w) == 6 and w[5] in "0123":
            seen[(w[3], 2 if w[5] == "3" else int(w[5]))] += 1
    if not seen:
        return LatchConvention()
    (edge, init), _n = seen.most_common(1)[0]
    if edge not in ("re", "fe"):
        raise ValueError(f"latch type {edge}: no flip-flop cell of that kind to insert")
    return LatchConvention(edge, init)


class EditNetlist:
    """Recipes on an open Odin III `Design` whose top module is the clean circuit."""

    def __init__(self, design: object, tag: str, conv: LatchConvention = DEFAULT_CONV) -> None:
        from odin3 import Design, Module

        assert isinstance(design, Design)
        top = design.top()
        assert isinstance(top, Module)
        self.top = top
        self.tag = tag
        self.conv = conv
        self.base_nodes = sum(1 for n in top.nodes() if n.granularity != "port")

    def _net(self, name: str) -> object:
        net = self.top.net(name)
        return net if net is not None else self.top.add_net(name, tag=self.tag)

    def names(self, inputs: list[str], out: str, rows: list[str]) -> None:
        from odin3 import Net

        cover = "\n".join(rows) + "\n"
        node = self.top.add_sop(len(inputs), cover, None, tag=self.tag)
        pins = node.pins()
        for pin, name in zip(pins, [*inputs, out], strict=True):
            net = self._net(name)
            assert isinstance(net, Net)
            pin.connect(net)

    def latch(self, d: str, q: str, clock: str) -> None:
        from odin3 import Net

        # INIT as the circuit's own latches (default 0 as the text `.latch ... 0`); no twin node
        # since Odin III 42394c3d
        cell = "$_DFF_P_" if self.conv.edge == "re" else "$_DFF_N_"
        node = self.top.add_node(cell, None, tag=self.tag, params={"INIT": self.conv.init})
        by_name = {p.name: p.pins[0] for p in node.ports()}
        for port, name in (("C", clock), ("D", d), ("Q", q)):
            net = self._net(name)
            assert isinstance(net, Net)
            by_name[port].connect(net)

    def splice(self, victim: str) -> str:
        """Move the driver of `victim` onto a fresh net; returns that net's name."""
        net = self.top.net(victim)
        if net is None:
            raise ValueError(f"{victim}: no such net")
        drv = net.driver()
        if drv is None:
            raise ValueError(f"{victim}: net has no driver")
        tmp = f"__htl_tmp_{victim}"
        fresh = self.top.add_net(tmp, tag=self.tag)
        drv.disconnect(tag=self.tag)  # the old driver's node gets a "removed" event
        drv.connect(fresh)
        return tmp

    def isolate(self, net_name: str) -> None:
        """Give primary output `net_name` a buffer of its own: driver and in-design readers move
        to `<net>__htl_pre`, a new buffer drives the port net."""
        net = self.top.net(net_name)
        if net is None:
            raise ValueError(f"{net_name}: no such net")
        drv = net.driver()
        if drv is None:
            raise ValueError(f"{net_name}: net has no driver")
        pre = self.top.add_net(net_name + "__htl_pre", tag=self.tag)
        readers = [p for p in net.pins() if p.direction() == "in"
                   and p.node().granularity != "port"]
        drv.disconnect(tag=self.tag)
        drv.connect(pre)
        for pin in readers:
            pin.rewire(pre, tag=self.tag)  # each moved reader's node gets a "rewired" event
        self.names([net_name + "__htl_pre"], net_name, ["1 1"])

    def report(self, reason: str = "") -> InsertReport:
        nodes = [n for n in self.top.nodes() if n.granularity != "port"]
        added: list[object] = []
        modified = 0
        untouched = 0
        outs: list[str] = []
        for n in nodes:
            kinds = {k for k, t in n.edit_events if t == self.tag}
            if "added" in kinds:
                added.append(n)
                for p in n.pins():
                    if p.direction() == "out":
                        pn = p.net()
                        outs.append(pn.name if pn is not None else "")
            elif kinds:
                modified += 1
            elif not n.edit_events:
                untouched += 1
        nets = list(self.top.nets())
        tagged_nets = [n for n in nets if n.edit_tag == self.tag]
        return InsertReport(
            method="odin3-edit", reason=reason, tag=self.tag, base_nodes=self.base_nodes,
            nodes=len(nodes), tagged_nodes=len(added), tagged_nets=len(tagged_nets),
            untagged_nodes=untouched, modified_nodes=modified,
            tagged_all_htl=all("__htl" in n.name for n in tagged_nets),
            tagged_node_outputs=sorted(outs))


class TextNetlist:
    """The same primitives on BLIF text (fallback only)."""

    def __init__(self, model: BlifModel, conv: LatchConvention = DEFAULT_CONV) -> None:
        self.model = model
        self.conv = conv

    def names(self, inputs: list[str], out: str, rows: list[str]) -> None:
        self.model.body += [names_line(inputs, out), *rows]

    def latch(self, d: str, q: str, clock: str) -> None:
        self.model.body.append(
            f".latch {d} {q} {self.conv.edge} {clock} {self.conv.init}")

    def splice(self, victim: str) -> str:
        found = find_names_block(self.model, victim)
        if found is None:
            raise ValueError(f"{victim}: no .names line drives it")
        index = found[0]
        tmp = f"__htl_tmp_{victim}"
        self.model.body[index] = self.model.body[index].rsplit(None, 1)[0] + f" {tmp}"
        return tmp

    def isolate(self, net: str) -> None:
        self.model = isolate_output(self.model, net)


def events_dir_of(out: Path) -> Path:
    """Where the internal edit-event file of `out` (a circuit under `<root>/circuits/`) goes:
    `<root>/answer_key/edit_events/`. Never next to the circuit the detector sees."""
    return out.parent.parent / "answer_key" / "edit_events"


def insert(
    base: Path, out: Path, tag: str, recipe: RecipeFn, allow_fallback: bool = True,
    events_dir: Path | None = None, conv: LatchConvention = DEFAULT_CONV,
) -> InsertReport:
    """Reads `base` (BLIF) into Odin III, applies `recipe` with the edit API, writes `out`.
    On an Odin III error the recipe runs again on BLIF text (fallback) and the reason is in the
    report. With `events_dir`, a second file with the edit events (`write_blif --edit-tags`) is
    written there for the answer key; `out` itself never carries them."""
    from odin3 import Design, Odin3Error

    try:
        with Design() as design:
            design.run_pass("read_blif", str(base))
            ed = EditNetlist(design, tag, conv)
            recipe(ed)
            rep = ed.report()
            design.run_pass("write_blif", str(out))  # detector-visible: no edit events
            if events_dir is not None:
                events_dir.mkdir(parents=True, exist_ok=True)
                ev = events_dir / f"{out.stem}.edit.blif"
                design.run_pass("write_blif", f"--edit-tags {ev}")  # internal, answer key only
                rep.edit_blif = ev.name
        return rep
    except (Odin3Error, ValueError) as exc:
        if not allow_fallback:
            raise
        reason = f"{type(exc).__name__}: {exc}"
    model = parse_single_model(base.read_text(encoding="utf-8"))
    text = TextNetlist(model, conv)
    recipe(text)
    out.write_text(render(text.model), encoding="utf-8")
    return InsertReport(method="text-fallback", reason=reason, tag=tag)


class RecipeFn(Protocol):
    def __call__(self, ed: Editor) -> None: ...
