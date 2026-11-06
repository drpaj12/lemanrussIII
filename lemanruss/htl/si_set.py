"""Seeker-Si full set (spec docs/specs/2026-11-05-seeker-si.md, brief phase 3): plan, per-base
build, one-circuit check and release assembly of the 100-circuit silicon set.

Bases are OpenCores designs with a sky130 cell netlist from the silicon-flow ladder
(`flow/gates.blif`). Seeds come from `lemanruss.seedsrc`; nothing secret is printed or committed.
Subcommands: plan, check, build, assemble (see `main`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import resource
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lemanruss.detect.metrics import auroc
from lemanruss.htl.si_build import BaseCfg, SiBuild
from lemanruss.seedsrc import release_seed

Json = dict[str, Any]
# Roots come from the environment (default ~/odin3-ws layout): no home path is committed.
WS = Path(os.environ.get("LEMANRUSS_WS", str(Path.home() / "odin3-ws" / "work")))
LADDER = WS / "sifix3-out" / "ladder2"
FAMILY = "silicon"
VERSION = "2.0-rc1"
M_MIX = ((1, 0.5), (2, 0.3), (3, 0.2))
NOT_COMPARABLE = (
    "Seeker-Si is a NEW set. Its bases are OpenCores designs mapped to sky130_fd_sc_hd standard "
    "cells, not the benchmarks of Seeker comb/seq/proc; do not compare per base, per form or by "
    "AUROC with those sets.")


def _cfg(name: str, golden: Path, module: str, tb: str, files: tuple[str, ...], top: str,
         dut: str, clk: str, pass_text: str, strip: tuple[str, ...] = (),
         timeout: int = 1500) -> BaseCfg:
    return BaseCfg(name, golden, module, LADDER / "tb" / tb, files, top, dut, clk, pass_text,
                   strip, timeout)


BASES: dict[str, BaseCfg] = {c.name: c for c in (
    _cfg("mmuart", LADDER / "mmuart/flow/gates.blif", "uart", "mmuart", ("tb_mmuart.v",),
         "tb_mmuart", "tb_mmuart.dut", "tb_mmuart.clk", "PASS tb_mmuart"),
    _cfg("simple_spi", WS / "silicon-ladder-out/simple_spi/flow/gates.blif", "simple_spi_top",
         "simple_spi", ("tst_bench_top.v", "wb_master_model.v", "spi_slave_model.v"),
         "tst_bench_top", "tst_bench_top.spi_top", "tst_bench_top.clk", "Testbench done"),
    _cfg("i2c", LADDER / "i2c/flow/gates.blif", "i2c_master_top", "i2c",
         ("tst_bench_top.v", "wb_master_model.v", "i2c_slave_model.v"), "tst_bench_top",
         "tst_bench_top.i2c_top", "tst_bench_top.clk", "Testbench done", ("ARST_LVL",)),
    _cfg("verilog_cordic_core", LADDER / "verilog_cordic_core/flow/gates.blif", "cordic",
         "verilog_cordic_core", ("tb_cordic.v",), "tb_cordic", "tb_cordic.dut", "tb_cordic.clk",
         "PASS tb_cordic"),
    _cfg("des", LADDER / "des/flow/gates.blif", "des", "des", ("des_test_po.v",), "test",
         "test.u0", "test.clk", "DES Test done", timeout=3000),
)}
ORDER = list(BASES)  # smallest first
PDK_V = WS / "tools/pdk/sky130A/libs.ref/sky130_fd_sc_hd/verilog"
ODIN_BIN = Path(os.environ.get(
    "ODIN3_BIN", str(Path.home() / "odin3-ws" / "odin3" / "build" / "rel-main3" / "odin3")))


def _peak_mb() -> dict[str, int]:
    return {"self": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
            "children": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss // 1024}


def make_plan(seed: int, bases: list[str], total: int) -> Json:
    """Sizes as even as possible, a seeded n_inf in 10..70, infected shares proportional, and a
    list of Trojan counts per base (0 = clean). Answer-key material: kept in the run root."""
    rng = random.Random(f"{seed}:si:plan")
    n_inf = rng.randint(10, 70)
    size = {b: total // len(bases) + (1 if i < total % len(bases) else 0)
            for i, b in enumerate(bases)}
    share = {b: n_inf * size[b] / total for b in bases}
    inf = {b: int(share[b]) for b in bases}
    short = n_inf - sum(inf.values())
    for b in sorted(bases, key=lambda x: share[x] - inf[x], reverse=True)[:short]:
        inf[b] += 1
    ms: dict[str, list[int]] = {}
    for b in bases:
        draws = [rng.choices([m for m, _ in M_MIX], [w for _, w in M_MIX])[0]
                 for _ in range(inf[b])]
        ms[b] = [0] * (size[b] - inf[b]) + draws
    return {"n_inf": n_inf, "size": size, "infected": inf, "ms": ms}


def build_base(name: str, root: Path, seed: int, ms: list[int], first: int) -> Json:
    cfg = BASES[name]
    t0 = time.monotonic()
    out = root / name
    sb = SiBuild(cfg, out, seed, ODIN_BIN, PDK_V, first)
    rng = random.Random(f"{seed}:si:{name}:draw")
    sb.clean()  # the silence reference
    for m in ms[1:] if ms[:1] == [0] else ms:
        if m == 0:
            sb.clean()
        else:
            sb.infected(m, rng)
    return finish_result(sb, out, t0, name)


def finish_result(sb: SiBuild, out: Path, t0: float, name: str) -> Json:
    res: Json = {"base": name, "records": sb.records, "failures": sb.failures,
                 "wall_s": round(time.monotonic() - t0, 1), "peak_rss_mb": _peak_mb(),
                 "golden_ff": sb.golden_ff, "witness": sb.bb.witness,
                 "golden_names": sum(1 for ln in sb.bb.golden_text.splitlines()
                                     if ln.startswith(".names"))}
    (out / "result.json").write_text(json.dumps(res, sort_keys=True) + "\n", encoding="utf-8")
    return res


def check_base(name: str, root: Path, seed: int, infected: bool) -> Json:
    t0 = time.monotonic()
    out = root / ("check_" + name)
    sb = SiBuild(BASES[name], out, seed, ODIN_BIN, PDK_V, 0)
    c = sb.clean()
    print(f"clean ok {c['wall_s']} s engine {c['engine']} cells {c['cells']} ff {c['ff']} "
          f"tb_pass {c['tb_pass_0start']} cycles {c['trace_cycles']}", file=sys.stderr)
    if infected:
        i = sb.infected(1, random.Random(f"{seed}:si:{name}:chk"))
        print(f"infected ok {i['wall_total_s']} s engine {i['engine']} ff {i['ff']}",
              file=sys.stderr)
    return finish_result(sb, out, t0, name)


def reason_class(reason: str) -> str:
    r = reason.lower()
    if r.startswith("testbench-fires"):
        return "design testbench fires the Trojan (silence rule)"
    if "no witness" in r:
        return "no witness for the drawn Trojan"
    if "replay" in r or "fire check" in r:
        return "Trojan does not fire after insertion or re-mapping"
    if "forced inactive" in r:
        return "forced-off circuit not equivalent"
    if "unproven" in r:
        return "equivalence unproven"
    if "equiv" in r or "counterexample" in r:
        return "not equivalent"
    if r == "dup":
        return "duplicate structure"
    if r.startswith("sim"):
        return "cell simulation error"
    if r.startswith("insert"):
        return "insertion failed"
    return "other: " + reason[:60]


def assemble(root: Path, seed: int, bases: list[str], rel: Path, key_dir: Path) -> Json:
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    results = {b: json.loads((root / b / "result.json").read_text(encoding="utf-8"))
               for b in bases}
    rng = random.Random(f"{seed}:si:final-ids")
    allrecs = [(b, r) for b in bases for r in results[b]["records"]]
    ids = rng.sample(range(1, 9999), len(allrecs))
    rng.shuffle(allrecs)
    (rel / "circuits").mkdir(parents=True, exist_ok=True)
    (key_dir / "pre").mkdir(parents=True, exist_ok=True)
    circuits: list[Json] = []
    key: list[Json] = []
    for (b, r), n in zip(allrecs, ids, strict=True):
        fid = f"si{n:04d}"
        for ext in ("v", "blif"):
            shutil.copyfile(root / b / "circuits" / f"{r['id']}.{ext}",
                            rel / "circuits" / f"{fid}.{ext}")
        if r["label"] == "infected":
            shutil.copyfile(root / b / "answer_key" / "pre" / f"{r['id']}.blif.gz",
                            key_dir / "pre" / f"{fid}.blif.gz")
        v = (rel / "circuits" / f"{fid}.v").read_bytes()
        k = (rel / "circuits" / f"{fid}.blif").read_bytes()
        circuits.append({"id": fid, "base": b, "v": f"circuits/{fid}.v",
                         "v_sha256": hashlib.sha256(v).hexdigest(), "v_bytes": len(v),
                         "blif": f"circuits/{fid}.blif",
                         "blif_sha256": hashlib.sha256(k).hexdigest(), "blif_bytes": len(k)})
        entry = dict(r)
        entry.update({"id": fid, "build_id": r["id"], "base": b,
                      "witness": results[b]["witness"].get(r["id"], {}),
                      "ff_in_cells": v.decode().count("sky130_fd_sc_hd__dfxtp_1")})
        key.append(entry)
    circuits.sort(key=lambda c: c["id"])
    key.sort(key=lambda e: e["id"])
    manifest = {"family": FAMILY, "version": VERSION, "bases": sorted(bases),
                "form": "sky130_fd_sc_hd structural Verilog (.v) plus gates-as-names BLIF",
                "note": NOT_COMPARABLE, "circuits": circuits,
                "labels": "answer_key/ (separate; a detector must not read it)"}
    rel.mkdir(parents=True, exist_ok=True)
    (rel / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8")
    (rel / "SHA256SUMS").write_text(
        "".join(f"{c[p + '_sha256']}  {c[p]}\n" for c in circuits for p in ("v", "blif")),
        encoding="utf-8")
    (key_dir / "answer_key.json").write_text(
        json.dumps({"plan": plan, "circuits": key, "failures":
                    {b: results[b]["failures"] for b in bases}}, sort_keys=True) + "\n",
        encoding="utf-8")
    stats = summarize(plan, results, key)
    (key_dir / "stats.json").write_text(json.dumps(stats, indent=1, sort_keys=True) + "\n",
                                        encoding="utf-8")
    return stats


def summarize(plan: Json, results: dict[str, Json], key: list[Json]) -> Json:
    st: Json = {"per_base": {}, "engines": {}, "rejections": {}, "rejections_by_trigger": {},
                "attempts_by_trigger": {}, "ffcount_auroc": {}, "wall_s": {}, "peak_rss_mb": {}}
    eng: dict[str, Counter[str]] = defaultdict(Counter)
    for e in key:
        b = e["base"]
        row = st["per_base"].setdefault(b, {"clean": 0, "infected": 0, "trojans": 0,
                                            "m1": 0, "m2": 0, "m3": 0})
        if e["label"] == "clean":
            row["clean"] += 1
        else:
            row["infected"] += 1
            row["trojans"] += e["trojans"]
            row[f"m{e['trojans']}"] += 1
        eng[b][e["engine"]] += 1
        eng["all"][e["engine"]] += 1
    st["engines"] = {b: dict(c) for b, c in eng.items()}
    for b, r in results.items():
        cls = Counter(reason_class(f["reason"]) for f in r["failures"])
        st["rejections"][b] = dict(cls)
        kinds: Counter[str] = Counter()
        for f in r["failures"]:
            if reason_class(f["reason"]).startswith("design testbench"):
                for t in set(f["trig"]):
                    kinds[t] += 1
        st["rejections_by_trigger"][b] = dict(kinds)
        att: Counter[str] = Counter()
        for f in r["failures"]:
            for t in set(f["trig"]):
                att[t] += 1
        for rec in r["records"]:
            for s in rec.get("specs", []):
                att[s["trig"]] += 1
        st["attempts_by_trigger"][b] = dict(att)
        st["wall_s"][b] = r["wall_s"]
        st["peak_rss_mb"][b] = r["peak_rss_mb"]
        sub = [e for e in key if e["base"] == b]
        st["ffcount_auroc"][b] = auroc([float(e["ff_in_cells"]) for e in sub],
                                       [1 if e["label"] == "infected" else 0 for e in sub])
    st["ffcount_auroc"]["all"] = auroc([float(e["ff_in_cells"]) for e in key],
                                       [1 if e["label"] == "infected" else 0 for e in key])
    st["ff_table"] = [{"id": e["id"], "base": e["base"], "label": e["label"],
                       "trojans": e["trojans"], "ff": e["ff_in_cells"],
                       "ff_golden": e["ff_golden"]} for e in key]
    return st


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Seeker-Si set builder")
    ap.add_argument("cmd", choices=["plan", "check", "build", "assemble"])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--base", default="")
    ap.add_argument("--bases", default=",".join(ORDER))
    ap.add_argument("--total", type=int, default=100)
    ap.add_argument("--infected-check", action="store_true")
    ap.add_argument("--release-dir", type=Path, default=None)
    ap.add_argument("--key-dir", type=Path, default=None)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args(argv)
    seed = release_seed(a.seed, "seeker-si")
    bases = [b for b in a.bases.split(",") if b]
    a.root.mkdir(parents=True, exist_ok=True)
    if a.cmd == "plan":
        plan = make_plan(seed, bases, a.total)
        (a.root / "plan.json").write_text(json.dumps(plan, sort_keys=True) + "\n",
                                          encoding="utf-8")
        print("planned", {b: plan["size"][b] for b in bases}, file=sys.stderr)
    elif a.cmd == "check":
        r = check_base(a.base, a.root, seed, a.infected_check)
        print("check done", a.base, r["wall_s"], r["peak_rss_mb"], file=sys.stderr)
    elif a.cmd == "build":
        plan = json.loads((a.root / "plan.json").read_text(encoding="utf-8"))
        r = build_base(a.base, a.root, seed, plan["ms"][a.base], 1000 * ORDER.index(a.base))
        print("built", a.base, len(r["records"]), "fails", len(r["failures"]), r["wall_s"],
              r["peak_rss_mb"], file=sys.stderr)
    else:
        assert a.release_dir is not None and a.key_dir is not None
        st = assemble(a.root, seed, bases, a.release_dir, a.key_dir)
        print("assembled", {b: st["per_base"][b] for b in st["per_base"]}, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
