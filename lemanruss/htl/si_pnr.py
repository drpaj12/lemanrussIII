"""Place and route of one silicon circuit (Seeker-Si rc2, controller rule 2026-11-07).

Runs the Odin III silicon flow's own `openroad_flow.tcl` (floorplan to fill) on the cell Verilog.
A run that passes the wall cap is stopped and recorded as a flow limit with its cell count; one
retry uses a different floorplan utilisation. Nothing here reads a label.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

CAP_S = 1800
STALL_S = 300  # a log silent this long at DRT-0179 "Init gr pin query" is a hang, not slowness
UTILS = (25, 18)  # percent: first try, retry
TOOLS = Path("/home/jamiespa/odin3-ws/work/tools")


def _rss_mb(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip().splitlines()[-1]) // 1024
    except (OSError, ValueError, IndexError):
        return -1


def _in_pin_query(log: Path) -> bool:
    tail = log.read_bytes()[-400:].decode("utf-8", "replace").strip().splitlines()
    return bool(tail) and "Init gr pin query" in tail[-1]


def clock_of(blif: str) -> str:
    """Clock port of the first `.latch` line, or '' for a combinational circuit."""
    for ln in blif.splitlines():
        if ln.startswith(".latch"):
            w = ln.split()
            return w[4] if len(w) > 4 else ""
    return ""


def run_once(
    verilog: Path, clk: str, out: Path, util: int, cap_s: int, odin_root: Path
) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    (out / "clean.v").write_text(verilog.read_text(encoding="utf-8"), encoding="utf-8")
    tcl = (odin_root / "tools/silicon/openroad_flow.tcl").read_text(encoding="utf-8")
    if "-utilization 25" not in tcl:
        raise RuntimeError("openroad_flow.tcl no longer holds '-utilization 25'")
    flow = out / "flow.tcl"
    flow.write_text(tcl.replace("-utilization 25", f"-utilization {util}"), encoding="utf-8")
    env = dict(os.environ, PDK=str(TOOLS / "pdk/sky130A"), OUT=str(out), TOP="top", CLK=clk)
    exe = TOOLS / "mamba/envs/orcond/bin/openroad"
    t0 = time.monotonic()
    log = (out / "openroad.log").open("w", encoding="utf-8")
    rss_file = out / "rss.txt"
    cmd = ["/usr/bin/time", "-f", "%M", "-o", str(rss_file), str(exe), "-exit", "-no_splash",
           str(flow)]
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                            start_new_session=True)
    capped = False
    stalled = False
    last_size, last_change = -1, time.monotonic()
    while True:
        try:
            proc.wait(timeout=5)
            break
        except subprocess.TimeoutExpired:
            pass
        now = time.monotonic()
        size = (out / "openroad.log").stat().st_size
        if size != last_size:
            last_size, last_change = size, now
        elif now - last_change > STALL_S and _in_pin_query(out / "openroad.log"):
            stalled = True  # detailed routing sits at DRT-0179 with a silent log (deterministic)
        if stalled or now - t0 > cap_s:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            capped = True
            break
    log.close()
    steps = out / "or/steps.txt"
    last = steps.read_text(encoding="utf-8").strip().splitlines()[-1] if steps.exists() else ""
    drc = out / "or/drc.rpt"
    return {"util": util, "stalled": stalled, "wall_s": round(time.monotonic() - t0, 1),
            "capped": capped,
            "rc": proc.returncode, "last_step": last.split(",")[0],
            "rss_mb": _rss_mb(rss_file),
            "drc_violations": drc.read_text(encoding="utf-8").count("violation")
            if drc.exists() else None}


def run(
    verilog: Path, clk: str, out: Path, cells: int, odin_root: Path, cap_s: int = CAP_S
) -> dict[str, object]:
    """Both tries as needed; the record always carries the cell count and every attempt."""
    attempts: list[dict[str, object]] = []
    for util in UTILS:
        a = run_once(verilog, clk, out / f"u{util}", util, cap_s, odin_root)
        attempts.append(a)
        if a["rc"] == 0 and not a["capped"]:
            break
    ok = attempts[-1]["rc"] == 0 and not attempts[-1]["capped"]
    limit: str | None = None
    if not ok:
        last = attempts[-1]
        limit = ("stall" if last["stalled"] else "cap") if last["capped"] else f"rc{last['rc']}"
    rec: dict[str, object] = {"cells": cells, "ok": ok, "attempts": attempts, "flow_limit": limit}
    (out / "pnr.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec
