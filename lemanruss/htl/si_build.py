"""Seeker-Si pilot build (spec docs/specs/2026-11-05-seeker-si.md sections 2, 4, 6, 9).

Reuses the n200 planning and insertion (`n200.BaseBuild`, `n200.build_pre`) on a sky130 cell
netlist read as `.names` BLIF, then obfuscates with the `silicon` kind of `obfuscate` (random ABC
script, `abc --gates sky130hd`, `dfflibmap sky130hd`, finalize), writes the cell Verilog and gates
every circuit. Seeds come from `lemanruss.seedsrc`; nothing secret is printed.
"""

from __future__ import annotations

import gzip
import json
import random
import re
import resource
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from lemanruss.htl import n200
from lemanruss.htl import obfuscate as ob
from lemanruss.htl.bitsim import compile_model
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.n200check import Json, odin_fire, run_cec
from lemanruss.htl.n200plan import DOS, ERR_HI, ERR_LO, Ctx, TSpec, make_ctx
from lemanruss.htl.proc_gate import gate_problems
from lemanruss.htl.si_cells import blif_to_verilog, verilog_to_blif

SIM_MIX = ((DOS, 0.5), (ERR_HI, 0.25), (ERR_LO, 0.25))
MAX_TRIES = 12
TRACE_MOD = """
module si_trace;
  always @(posedge tb_mmuart.clk)
    $display("T %b %b %b %b", tb_mmuart.csr_do, tb_mmuart.rx_irq, tb_mmuart.tx_irq,
             tb_mmuart.uart_tx);
endmodule
"""


@dataclass
class Sim:
    ok: bool
    passed: bool
    trace: list[str]
    reason: str


def _primitives_init0(pdk_v: Path) -> str:
    prim = (pdk_v / "primitives.v").read_text(encoding="utf-8")
    pat = re.compile(r"primitive\s+sky130_fd_sc_hd__udp_d(?:ff|latch)\S*\s*\(.*?\breg\s+Q\s*;",
                     re.S)
    return pat.sub(lambda m: f"{m.group(0)}\n    initial Q = 1'b0;", prim)


def simulate_cells(verilog: str, tb: Path, pdk_v: Path, work: Path, timeout: int = 1500) -> Sim:
    """iverilog + vvp of the cell netlist (module renamed to the testbench's `uart`) with the
    sky130 models, every flip-flop starting at 0 (the x-pessimism route of gate_sim), and the
    posedge output trace."""
    work.mkdir(parents=True, exist_ok=True)
    net = work / "net.v"
    net.write_text(verilog.replace("module top (", "module uart (", 1), encoding="utf-8")
    (work / "prim0.v").write_text(_primitives_init0(pdk_v), encoding="utf-8")
    (work / "trace.v").write_text(TRACE_MOD, encoding="utf-8")
    vvp = work / "sim.vvp"
    cmd = ["iverilog", "-g2005", "-DFUNCTIONAL", "-DUNIT_DELAY=#0", "-s", "tb_mmuart", "-s",
           "si_trace", "-o", str(vvp), str(tb), str(work / "trace.v"), str(net),
           str(work / "prim0.v"), str(pdk_v / "sky130_fd_sc_hd.v")]
    comp = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if comp.returncode != 0:
        return Sim(False, False, [], "iverilog: " + comp.stderr.strip()[:200])
    try:
        run = subprocess.run(["vvp", "-n", str(vvp)], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return Sim(False, False, [], f"vvp timeout {timeout} s")
    lines = run.stdout.splitlines()
    trace = [ln for ln in lines if ln.startswith("T ")]
    passed = any("PASS tb_mmuart" in ln for ln in lines)
    return Sim(True, passed, trace, "")


def ff_count(text: str) -> int:
    return sum(1 for ln in text.splitlines() if ln.startswith(".latch"))


class SiBuild:
    def __init__(self, golden: Path, out: Path, seed: int, odin_bin: Path, tb: Path,
                 pdk_v: Path) -> None:
        self.out = out
        self.odin_bin = odin_bin
        self.tb = tb
        self.pdk_v = pdk_v
        (out / "circuits").mkdir(parents=True, exist_ok=True)
        self.bb = n200.BaseBuild(golden, out, 0, seed)
        self.seed = seed
        made = make_ctx(self.bb.golden_path, seed)
        if isinstance(made, str):
            raise RuntimeError(made)
        self.ctx: Ctx = made
        self.ctx.mix = SIM_MIX
        self.records: list[Json] = []
        self.failures: list[Json] = []
        self.ref_trace: list[str] | None = None
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
        back.write_text(verilog_to_blif(verilog, inputs, outputs), encoding="utf-8")
        verdict = run_cec(final, back)[0]
        if verdict != "equivalent":
            return f"verilog round trip: {verdict}"
        sim = simulate_cells(verilog, self.tb, self.pdk_v, bb.scratch / f"{cid}.sim")
        if not sim.ok:
            return f"sim: {sim.reason}"
        if not sim.passed:
            return "sim: testbench did not print PASS (0-start)"
        silent = True
        if self.ref_trace is None:
            if pre is not None:
                return "need a clean circuit first"
            self.ref_trace = sim.trace
        else:
            silent = sim.trace == self.ref_trace
            if not silent:
                return "silence: trace differs from the clean circuit on the testbench stimulus"
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
                "trace_cycles": len(sim.trace), "wall_s": round(time.monotonic() - t0, 1)}

    def clean(self) -> Json:
        for _ in range(MAX_TRIES):
            cid = self.bb.next_id("si")
            res = self._finish(cid, None, [])
            if not isinstance(res, str):
                res.update({"label": "clean", "trojans": 0, "wall_total_s": res["wall_s"]})
                self.records.append(res)
                return res
            self.bb.slot -= 1
            self.failures.append({"stage": "clean", "reason": res})
        raise RuntimeError("no clean circuit passed the gate")

    def infected(self, m: int, rng: random.Random) -> Json:
        for _ in range(MAX_TRIES):
            specs = n200._draw_circuit(self.ctx, rng, m)
            if len(specs) != m:
                self.failures.append({"stage": f"draw{m}", "reason": "draw gave fewer trojans"})
                continue
            cid = self.bb.next_id("si")
            t0 = time.monotonic()
            pre = n200.build_pre(self.bb, self.ctx, specs, cid)
            if isinstance(pre, str):
                self.bb.slot -= 1
                self.failures.append({"stage": f"pre{m}", "reason": pre[:200]})
                continue
            rec, steps, pre_path = pre
            res = self._finish(cid, pre_path, steps)
            if isinstance(res, str):
                self.bb.slot -= 1
                if res != "dup":
                    self.failures.append({"stage": f"finish{m}", "reason": res})
                continue
            res.update({"label": "infected", "trojans": m, "wall_total_s":
                        round(time.monotonic() - t0, 1),
                        "specs": [s.to_dict() for s in specs], "records": rec["records"],
                        "off_cec": rec["off_cec"]})
            self.records.append(res)
            return res
        raise RuntimeError(f"no infected circuit with {m} trojans passed the gate")


def run_pilot(golden: Path, out: Path, seed: int, odin_bin: Path, tb: Path,
              pdk_v: Path) -> Json:
    t0 = time.monotonic()
    sb = SiBuild(golden, out, seed, odin_bin, tb, pdk_v)
    rng = random.Random(f"{seed}:si:pilot")
    sb.clean()
    sb.infected(1, rng)
    sb.infected(2, rng)
    key = out / "answer_key"
    key.mkdir(exist_ok=True)
    result: Json = {
        "records": sb.records, "failures": sb.failures,
        "wall_s": round(time.monotonic() - t0, 1),
        "peak_rss_self_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
        "peak_rss_children_mb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss // 1024,
        "golden_ff": sb.golden_ff,
        "cells_in_model": len(compile_model(parse_single_model(sb.bb.golden_text)).blocks),
    }
    (key / "pilot.json").write_text(json.dumps(result, sort_keys=True, indent=1) + "\n",
                                    encoding="utf-8")
    return result


NOT_COMPARABLE = (
    "Seeker-Si is a NEW set. Its bases are OpenCores designs mapped to sky130_fd_sc_hd standard "
    "cells, not the benchmarks of Seeker comb/seq/proc; do not compare per base, per form or by "
    "AUROC with those sets.")


def write_release(out: Path, rel: Path, bases: list[str]) -> None:
    """manifest.json (no labels, no seed), SHA256SUMS and the circuit list of a built tree."""
    import hashlib

    rel.mkdir(parents=True, exist_ok=True)
    files = sorted((out / "circuits").glob("*"))
    circuits = [{"id": f.stem, "file": f"circuits/{f.name}",
                 "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "bytes": f.stat().st_size}
                for f in files]
    manifest = {"family": "silicon", "version": "2.0-pilot", "bases": sorted(bases),
                "form": "sky130_fd_sc_hd structural Verilog (.v) plus gates-as-names BLIF",
                "note": NOT_COMPARABLE, "circuits": circuits,
                "labels": "answer_key/ (separate; a detector must not read it)"}
    (rel / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8")
    (rel / "SHA256SUMS").write_text(
        "".join(f"{c['sha256']}  {c['file']}\n" for c in circuits), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from lemanruss.seedsrc import release_seed

    ap = argparse.ArgumentParser(description="Seeker-Si pilot build")
    ap.add_argument("--golden", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--odin-bin", type=Path, required=True)
    ap.add_argument("--tb", type=Path, required=True)
    ap.add_argument("--pdk-verilog", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--release-dir", type=Path, default=None)
    a = ap.parse_args(argv)
    seed = release_seed(a.seed, "seeker-si")
    res = run_pilot(a.golden, a.out, seed, a.odin_bin, a.tb, a.pdk_verilog)
    if a.release_dir is not None:
        write_release(a.out, a.release_dir, [a.golden.stem])
    n = len(list((a.out / "circuits").glob("*.v")))
    print(f"circuits {n} wall_s {res['wall_s']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
