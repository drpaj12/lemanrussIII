"""Seeker-Si pilot build (spec docs/specs/2026-11-05-seeker-si.md sections 2, 4, 6, 9).

Reuses the n200 planning and insertion (`n200.BaseBuild`, `n200.build_pre`) on a sky130 cell
netlist read as `.names` BLIF, then obfuscates with the `silicon` kind of `obfuscate` (random ABC
script, `abc --gates sky130hd`, `dfflibmap sky130hd`, finalize), writes the cell Verilog and gates
every circuit. Seeds come from `lemanruss.seedsrc`; nothing secret is printed.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from lemanruss.htl import n200
from lemanruss.htl import obfuscate as ob
from lemanruss.htl.n200check import Json, odin_fire, run_cec
from lemanruss.htl.n200plan import DOS, ERR_HI, ERR_LO, Ctx, TSpec, make_ctx
from lemanruss.htl.proc_gate import gate_problems
from lemanruss.htl.si_cells import blif_to_verilog, same_network, verilog_to_blif

SIM_MIX = ((DOS, 0.5), (ERR_HI, 0.25), (ERR_LO, 0.25))
MAX_TRIES = 300
BAD_LINE = re.compile(r"^FAIL|ERROR:|Data compare error", re.M)
OUT_DECL = re.compile(r"^\s*output\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*[,)]?\s*$", re.M)


@dataclass(frozen=True)
class BaseCfg:
    """Per-base simulation set-up: where the design's own testbench lives and how it names the
    design under test (the tb instantiates it as `module`, instance path `dut`)."""

    name: str
    golden: Path
    module: str
    tb_dir: Path
    tb_files: tuple[str, ...]
    tb_top: str
    dut: str
    clk: str
    pass_text: str
    strip_params: tuple[str, ...] = ()
    timeout: int = 1500


@dataclass
class Sim:
    ok: bool
    passed: bool
    digest: str
    cycles: int
    reason: str


def _primitives_init0(pdk_v: Path) -> str:
    prim = (pdk_v / "primitives.v").read_text(encoding="utf-8")
    pat = re.compile(r"primitive\s+sky130_fd_sc_hd__udp_d(?:ff|latch)\S*\s*\(.*?\breg\s+Q\s*;",
                     re.S)
    return pat.sub(lambda m: f"{m.group(0)}\n    initial Q = 1'b0;", prim)


def _strip_param(tb: str, name: str) -> str:
    return re.sub(rf"#\s*\(\s*\.{re.escape(name)}\s*\([^()]*\)\s*\)", "", tb)


def simulate_cells(verilog: str, cfg: BaseCfg, pdk_v: Path, work: Path,
                   timeout: float | None = None) -> Sim:
    """iverilog + vvp of the cell netlist (module renamed to the one the testbench instantiates)
    with the sky130 models, every flip-flop starting at 0 (the x-pessimism route of gate_sim).
    The output trace is the DUT's output ports at each rising clock edge, kept as a digest."""
    work.mkdir(parents=True, exist_ok=True)
    for f in cfg.tb_dir.iterdir():
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="replace") if f.suffix == ".v" else None
            if text is None:
                (work / f.name).write_bytes(f.read_bytes())
            else:
                for p in cfg.strip_params:
                    text = _strip_param(text, p)
                (work / f.name).write_text(text, encoding="utf-8")
    net = work / "net.v"
    net.write_text(verilog.replace("module top (", f"module {cfg.module} (", 1), encoding="utf-8")
    decls = OUT_DECL.findall(verilog)
    outs = sorted(d[2] for d in decls)
    width = sum(abs(int(d[0]) - int(d[1])) + 1 if d[0] else 1 for d in decls)
    if not outs:
        return Sim(False, False, "", 0, "no output ports found in the netlist")
    (work / "prim0.v").write_text(_primitives_init0(pdk_v), encoding="utf-8")
    sigs = ", ".join(f"{cfg.dut}.{o}" for o in outs)
    trace = (f"module si_trace;\n  wire [{width - 1}:0] tr = {{{sigs}}};\n"
             f"  always @(posedge {cfg.clk})\n    $strobe(\"T %b\", tr);\nendmodule\n")
    (work / "trace.v").write_text(trace, encoding="utf-8")
    vvp = work / "sim.vvp"
    cmd = ["iverilog", "-g2005", "-DFUNCTIONAL", "-DUNIT_DELAY=#0", "-I", str(work), "-s",
           cfg.tb_top, "-s", "si_trace", "-o", str(vvp), *[str(work / t) for t in cfg.tb_files],
           str(work / "trace.v"), str(net), str(work / "prim0.v"),
           str(pdk_v / "sky130_fd_sc_hd.v")]
    comp = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=work)
    if comp.returncode != 0:
        return Sim(False, False, "", 0, "iverilog: " + comp.stderr.strip()[:200])
    limit = float(cfg.timeout if timeout is None else timeout)
    h = hashlib.sha256()
    n = 0
    other: list[str] = []
    try:
        with subprocess.Popen(["vvp", "-n", str(vvp)], stdout=subprocess.PIPE, text=True,
                              stdin=subprocess.DEVNULL, cwd=work) as proc:
            assert proc.stdout is not None
            expired = threading.Event()

            def _kill() -> None:
                expired.set()
                proc.kill()

            timer = threading.Timer(limit, _kill)
            timer.start()
            for ln in proc.stdout:
                if ln.startswith("T "):
                    h.update(ln.encode())
                    n += 1
                else:
                    other.append(ln)
                if expired.is_set():
                    break
            timer.cancel()
            if expired.is_set():
                return Sim(False, False, "", n, f"vvp timeout {limit:.0f} s")
    except OSError as exc:
        return Sim(False, False, "", 0, f"vvp: {exc}")
    if n == 0:
        return Sim(False, False, "", 0, "vvp printed no trace line")
    text = "".join(other)
    passed = cfg.pass_text in text and not BAD_LINE.search(text)
    return Sim(True, passed, h.hexdigest(), n, "")


def ff_count(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.startswith(".latch"))


class SiBuild:
    def __init__(self, cfg: BaseCfg, out: Path, seed: int, odin_bin: Path, pdk_v: Path,
                 first: int = 0) -> None:
        golden = cfg.golden
        self.out = out
        self.odin_bin = odin_bin
        self.cfg = cfg
        self.pdk_v = pdk_v
        (out / "circuits").mkdir(parents=True, exist_ok=True)
        self.bb = n200.BaseBuild(golden, out, first, seed)
        self.seed = seed
        made = make_ctx(self.bb.golden_path, seed)
        if isinstance(made, str):
            raise RuntimeError(made)
        self.ctx: Ctx = made
        self.ctx.mix = SIM_MIX
        self.records: list[Json] = []
        self.failures: list[Json] = []
        self.ref_trace: str | None = None
        self.ref_passed = False
        self.ref_wall: float | None = None
        self.golden_ff = ff_count(self.bb.golden_text)

    def _finish(self, cid: str, pre: Path | None,
                steps: list[tuple[TSpec, list[dict[str, int]]]]) -> Json | str:
        bb = self.bb
        t0 = time.monotonic()
        src = pre if pre is not None else bb.golden_path
        rng = bb.rng("SI")
        got = ob.obfuscate_traced(src, "silicon", rng, bb.scratch, cid)
        if isinstance(got, str):
            return got
        text, script, mapped, renames = got
        engines: dict[str, str] = {}
        problems = gate_problems(text, self.odin_bin, ref_text=src.read_text(encoding="utf-8"),
                                 engines=engines, key=cid, trace=(mapped, renames))
        if problems:
            return "gate: " + "; ".join(problems)[:200]
        sig = ob.signature(text)
        if ("silicon", sig) in bb.sigs:
            return "dup"
        final = bb.scratch / f"{cid}.final.blif"
        final.write_text(text, encoding="utf-8")
        for t, st in steps:
            ok, detail = odin_fire(bb.golden_path, final, t, st)
            if not ok:
                return f"fire check fails after obfuscation: {detail}"
        inputs, outputs, blocks = ob.parse(text)
        order = list(range(len(blocks)))
        rng.shuffle(order)
        try:
            verilog = blif_to_verilog(text, "top", order)
        except ValueError as exc:
            return f"verilog: {exc}"
        back = bb.scratch / f"{cid}.back.blif"
        back_text = verilog_to_blif(verilog, inputs, outputs)
        back.write_text(back_text, encoding="utf-8")
        if not same_network(text, back_text):
            verdict = run_cec(final, back)[0]
            if verdict != "equivalent":
                return f"verilog round trip: {verdict}"
        t_sim = time.monotonic()
        limit = None if self.ref_wall is None else min(self.cfg.timeout, 4 * self.ref_wall + 30)
        sim = simulate_cells(verilog, self.cfg, self.pdk_v, bb.scratch / f"{cid}.sim", limit)
        if not sim.ok and sim.reason.startswith("vvp timeout") and pre is not None:
            return "testbench-fires: simulation hangs (over 4x the clean time plus 30 s)"
        if not sim.ok:
            return f"sim: {sim.reason}"
        if self.ref_wall is None:
            self.ref_wall = time.monotonic() - t_sim
        if pre is not None and self.ref_passed and not sim.passed:
            return "testbench-fires: no PASS on the 0-start run although the clean circuit passes"
        silent = True
        if self.ref_trace is None:
            if pre is not None:
                return "need a clean circuit first"
            if not sim.passed:
                return "sim: the clean circuit does not pass the design testbench from a 0 start"
            self.ref_trace = sim.digest
            self.ref_passed = True
        else:
            silent = sim.digest == self.ref_trace
            if not silent:
                return ("testbench-fires: output trace differs from the clean circuit on the "
                        "testbench stimulus")
        (self.out / "circuits" / f"{cid}.v").write_text(verilog, encoding="utf-8")
        (self.out / "circuits" / f"{cid}.blif").write_text(text, encoding="utf-8")
        bb.sigs.add(("silicon", sig))
        if pre is not None:
            with gzip.open(bb.key / "pre" / f"{cid}.blif.gz", "wt", encoding="utf-8") as fh:
                fh.write(pre.read_text(encoding="utf-8"))
        return {"id": cid, "script": script, "engine": engines.get(cid, ""),
                "ff": ff_count(text), "ff_golden": self.golden_ff,
                "ff_pre": ff_count(pre.read_text(encoding="utf-8")) if pre else None,
                "cells": len(blocks) - ff_count(text), "fire_checked": len(steps),
                "tb_pass_0start": sim.passed, "tb_silent_vs_clean": silent,
                "trace_cycles": sim.cycles, "wall_s": round(time.monotonic() - t0, 1)}

    def _fail(self, rec: Json) -> None:
        self.failures.append(rec)
        with (self.out / "progress.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"fail": rec}, sort_keys=True) + "\n")

    def _done(self, rec: Json) -> Json:
        self.records.append(rec)
        with (self.out / "progress.jsonl").open("a", encoding="utf-8") as fh:
            slim = {k: v for k, v in rec.items() if k not in ("specs", "records")}
            fh.write(json.dumps({"ok": slim}, sort_keys=True) + "\n")
        return rec

    def clean(self) -> Json:
        for _ in range(MAX_TRIES):
            cid = self.bb.next_id("si")
            res = self._finish(cid, None, [])
            if not isinstance(res, str):
                res.update({"label": "clean", "trojans": 0, "wall_total_s": res["wall_s"]})
                return self._done(res)
            self.bb.slot -= 1
            self._fail({"stage": "clean", "trig": [], "reason": res})
        raise RuntimeError("no clean circuit passed the gate")

    def infected(self, m: int, rng: random.Random) -> Json:
        for _ in range(MAX_TRIES):
            specs = n200._draw_circuit(self.ctx, rng, m)
            if len(specs) != m:
                self._fail({"stage": f"draw{m}", "trig": [], "reason": "draw gave fewer trojans"})
                continue
            cid = self.bb.next_id("si")
            kinds = [s.trig for s in specs]
            t0 = time.monotonic()
            pre = n200.build_pre(self.bb, self.ctx, specs, cid)
            if isinstance(pre, str):
                self.bb.slot -= 1
                self._fail({"stage": f"pre{m}", "trig": kinds, "reason": pre[:200]})
                continue
            rec, steps, pre_path = pre
            res = self._finish(cid, pre_path, steps)
            if isinstance(res, str):
                self.bb.slot -= 1
                self._fail({"stage": f"finish{m}", "trig": kinds, "reason": res})
                continue
            res.update({"label": "infected", "trojans": m, "wall_total_s":
                        round(time.monotonic() - t0, 1),
                        "specs": [s.to_dict() for s in specs], "records": rec["records"],
                        "off_cec": rec["off_cec"]})
            return self._done(res)
        raise RuntimeError(f"no infected circuit with {m} trojans passed the gate")
