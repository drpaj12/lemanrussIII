"""RTL-level Trojans with per-Trojan trigger testbenches run through Odin III `sim_tb` (round 5).

For a combinational VerilogEval reference design: an input-pattern trigger over k input bits and
one payload (DosStuck, ErrHi flip, ErrLo flip) are spliced into the Verilog (`insert_hdl`). One
testbench (the sim_tb subset of Verilog: arrays, `for`, `#`, `$display`, `$finish`) is generated
per Trojan: N stimulus vectors held in arrays, none matching the trigger except vector F, which
does. It runs on the clean and the infected RTL under

- iverilog (the oracle), and
- Odin III `sim_tb`, the two designs compared with Odin III's `tools/tb-compare`.

Agreement means: sim_tb output equals iverilog output on both designs (compared as numbers per
field), and both simulators put the first clean-vs-infected difference at vector F (so the trigger
is silent before F and the payload shows at F).
"""

from __future__ import annotations

import random
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from lemanruss.htl.insert_hdl import (
    insert_dos_stuck_payload,
    insert_err_bit_payload,
    insert_input_pattern_trigger,
)
from lemanruss.htl.payloads import DosStuckPayload, ErrHiPayload, ErrLoPayload
from lemanruss.htl.triggers import InputPatternTrigger

N_VECTORS = 64
TRIGGER_BITS = 10
TIMEOUT = 120

_HEADER = re.compile(r"module\s+\w+\s*\((.*?)\)\s*;", re.DOTALL)
_PORT = re.compile(
    r"\b(input|output)\s+(?:reg\s+|wire\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(\w+)")


@dataclass(frozen=True)
class RtlPort:
    name: str
    width: int
    direction: str


def ports_of(source: str) -> list[RtlPort]:
    """Ports of the first module from an ANSI header."""
    m = _HEADER.search(source)
    if m is None:
        return []
    return [RtlPort(p.group(4), int(p.group(2)) - int(p.group(3)) + 1 if p.group(2) else 1,
                    p.group(1)) for p in _PORT.finditer(m.group(1))]


def module_name(source: str) -> str:
    m = re.search(r"\bmodule\s+(\w+)", source)
    assert m is not None
    return m.group(1)


def testbench(top: str, ports: list[RtlPort], vectors: list[dict[str, int]]) -> str:
    """The sim_tb-subset testbench: one `$display` line per vector, `index out1 out2 ...` (hex)."""
    ins = [p for p in ports if p.direction == "input"]
    outs = [p for p in ports if p.direction == "output"]
    n = len(vectors)
    lines = ["module tb;"]
    lines += [f"  reg [{p.width - 1}:0] {p.name};" for p in ins]
    lines += [f"  wire [{p.width - 1}:0] {p.name};" for p in outs]
    lines += [f"  reg [{p.width - 1}:0] v_{p.name} [0:{n - 1}];" for p in ins]
    conn = ", ".join(f".{p.name}({p.name})" for p in ports)
    lines += [f"  {top} dut({conn});", "  integer i;", "  initial begin"]
    for k, vec in enumerate(vectors):
        lines += [f"    v_{p.name}[{k}] = {p.width}'h{vec[p.name]:x};" for p in ins]
    lines.append(f"    for (i = 0; i < {n}; i = i + 1) begin")
    lines += [f"      {p.name} = v_{p.name}[i];" for p in ins]
    lines.append("      #10;")
    fmt = " ".join(["%0d"] + ["%h"] * len(outs))
    args = ", ".join(["i", *(p.name for p in outs)])
    lines += [f'      $display("{fmt}", {args});', "    end", "    $finish;", "  end", "endmodule"]
    return "\n".join(lines) + "\n"


def run_iverilog(dut: Path, tb: Path, work: Path, tag: str) -> str:
    exe = work / f"{tag}.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(dut), str(tb)], check=True,
                   capture_output=True, text=True, timeout=TIMEOUT)
    run = subprocess.run(["vvp", str(exe)], check=True, capture_output=True, text=True,
                         timeout=TIMEOUT)
    return "\n".join(ln for ln in run.stdout.splitlines() if ln[:1].isdigit())


def run_simtb(odin_bin: Path, dut: Path, tb: Path, out: Path) -> str:
    cmd = [str(odin_bin), "-p",
           f'read_verilog "{dut}"; proc; opt; lower; sim_tb --out "{out}" "{tb}"']
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=TIMEOUT)
    return out.read_text(encoding="utf-8")


def tb_compare(odin_bin: Path, tool: Path, tb: Path, clean: Path, infected: Path) -> int | None:
    """tb-compare of clean vs infected under sim_tb: the 0-based vector of the first mismatch,
    None when identical; ValueError when the tool fails."""
    script = "read_verilog \"{}\"; proc; opt; lower"
    run = subprocess.run(
        [sys.executable, str(tool), "--odin3", str(odin_bin), "--tb", str(tb),
         "--a", script.format(clean), "--b", script.format(infected)],
        capture_output=True, text=True, timeout=TIMEOUT, check=False)
    if run.returncode == 0:
        return None
    m = re.search(r"line (\d+)", run.stdout)
    if run.returncode != 1 or m is None:
        raise ValueError(f"tb-compare failed: {(run.stderr or run.stdout)[-200:]}")
    return int(m.group(1)) - 1


def _rows(text: str) -> list[list[int]]:
    return [[int(f, 16) if k else int(f) for k, f in enumerate(ln.split())]
            for ln in text.splitlines() if ln.strip()]


def first_diff(a: str, b: str) -> int | None:
    ra, rb = _rows(a), _rows(b)
    for k, (x, y) in enumerate(zip(ra, rb, strict=False)):
        if x != y:
            return k
    return None if len(ra) == len(rb) else min(len(ra), len(rb))


@dataclass
class RtlResult:
    circuit: str
    base: str
    trojan: str
    fire_index: int
    verdict: str = ""  # agree | disagree | error
    detail: str = ""
    iverilog_first_diff: int | None = None
    simtb_first_diff: int | None = None
    simtb_equals_iverilog_clean: bool = False
    simtb_equals_iverilog_infected: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _bit_names(ins: list[RtlPort]) -> list[str]:
    out: list[str] = []
    for p in ins:
        out += [p.name] if p.width == 1 else [f"{p.name}[{i}]" for i in range(p.width)]
    return out


def _vectors(
    ins: list[RtlPort], bits: tuple[str, ...], magic: int, rng: random.Random
) -> tuple[list[dict[str, int]], int]:
    """N_VECTORS random vectors, none matching the trigger, plus the firing one at index F."""

    def match(vec: dict[str, int]) -> bool:
        val = 0
        for b in bits:
            name, _, idx = b.partition("[")
            bit = (vec[name] >> int(idx[:-1])) & 1 if idx else vec[name] & 1
            val = (val << 1) | bit
        return val == magic

    def draw() -> dict[str, int]:
        return {p.name: rng.getrandbits(p.width) for p in ins}

    vecs: list[dict[str, int]] = []
    while len(vecs) < N_VECTORS:
        v = draw()
        if not match(v):
            vecs.append(v)
    fire = draw()
    for k, b in enumerate(bits):
        want = (magic >> (len(bits) - 1 - k)) & 1
        name, _, idx = b.partition("[")
        pos = int(idx[:-1]) if idx else 0
        fire[name] = (fire[name] & ~(1 << pos)) | (want << pos)
    f = N_VECTORS // 2
    vecs.insert(f, fire)
    return vecs, f


def build_and_check(
    base_src: Path, work: Path, circuit: str, odin_bin: Path, tbc_tool: Path, seed: int
) -> list[RtlResult]:
    """Three Trojans (DosStuck, ErrHi, ErrLo) on one base; each checked as described above."""
    work.mkdir(parents=True, exist_ok=True)
    text = base_src.read_text(encoding="utf-8")
    top = module_name(text)
    ports = ports_of(text)
    ins = [p for p in ports if p.direction == "input"]
    outs = [p for p in ports if p.direction == "output"]
    base = base_src.stem.removesuffix("_ref")
    results: list[RtlResult] = []
    bits_all = _bit_names(ins)
    if len(bits_all) < 2:
        return [RtlResult(circuit, base, "-", -1, "skipped", "fewer than 2 input bits")]
    if not outs:
        return [RtlResult(circuit, base, "-", -1, "skipped", "no output")]
    if any(p.width > 64 for p in ports):
        return [RtlResult(circuit, base, "-", -1, "skipped", "a port is wider than 64 bits")]
    rng = random.Random(f"{base}:{seed}")
    k = min(TRIGGER_BITS, len(bits_all))
    bits = tuple(rng.sample(bits_all, k))
    magic = rng.getrandbits(k)
    vectors, f = _vectors(ins, bits, magic, rng)
    tb = work / f"{circuit}_tb.v"
    tb.write_text(testbench(top, ports, vectors), encoding="utf-8")
    clean = work / f"{circuit}_clean.v"
    clean.write_text(text, encoding="utf-8")
    assigned = set(re.findall(r"\bassign\s+(\w+)\s*=", text))
    cands = [o for o in outs if o.name in assigned]
    if not cands:
        return [RtlResult(circuit, base, "-", f, "skipped", "no output driven by a plain assign")]
    victim = cands[0]
    trig_src = insert_input_pattern_trigger(
        text, InputPatternTrigger(bits=bits, magic_value=magic))
    try:
        ci = run_iverilog(clean, tb, work, f"{circuit}_c")
        cs = run_simtb(odin_bin, clean, tb, work / f"{circuit}_c.out")
    except (subprocess.SubprocessError, OSError) as exc:
        return [RtlResult(circuit, base, "-", f, "error", f"clean run: {str(exc)[-160:]}")]
    if re.search(r"\b[0-9a-f]*[xz][0-9a-fxz]*\b", ci.replace("\n", " "), re.I):
        return [RtlResult(circuit, base, "-", f, "skipped", "iverilog (4-state) prints x/z")]
    clean_out = _rows(ci)[f][1 + [o.name for o in outs].index(victim.name)]
    stuck = 0 if clean_out != 0 else 1
    makers: list[tuple[str, Callable[[str], str]]] = [
        ("dos-stuck", lambda s: insert_dos_stuck_payload(
            s, DosStuckPayload(victim=victim.name, stuck_value=stuck))),
        ("err-hi", lambda s: insert_err_bit_payload(
            s, ErrHiPayload(word=victim.name, bits=1), victim.width)),
        ("err-lo", lambda s: insert_err_bit_payload(
            s, ErrLoPayload(word=victim.name, bits=1), victim.width)),
    ]
    for tid, make in makers:
        res = RtlResult(f"{circuit}-{tid}", base, tid, f)
        results.append(res)
        try:
            inf_text = make(trig_src)
        except ValueError as exc:
            res.verdict, res.detail = "error", f"insert: {exc}"
            continue
        inf = work / f"{circuit}_{tid}.v"
        inf.write_text(inf_text, encoding="utf-8")
        try:
            ii = run_iverilog(inf, tb, work, f"{circuit}_{tid}")
            si = run_simtb(odin_bin, inf, tb, work / f"{circuit}_{tid}.out")
            res.simtb_first_diff = tb_compare(odin_bin, tbc_tool, tb, clean, inf)
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            res.verdict, res.detail = "error", str(exc)[-200:]
            continue
        try:
            res.iverilog_first_diff = first_diff(ci, ii)
            res.simtb_equals_iverilog_clean = first_diff(ci, cs) is None
            res.simtb_equals_iverilog_infected = first_diff(ii, si) is None
        except ValueError as exc:
            res.verdict, res.detail = "error", f"unparsable output: {exc}"
            continue
        ok = (res.simtb_equals_iverilog_clean and res.simtb_equals_iverilog_infected
              and res.iverilog_first_diff == f and res.simtb_first_diff == f)
        res.verdict = "agree" if ok else "disagree"
    return results


def run_all(
    sources: list[Path], work: Path, odin_bin: Path, tbc_tool: Path, seed: int = 0
) -> list[RtlResult]:
    out: list[RtlResult] = []
    for n, src in enumerate(sources, 1):
        try:
            out += build_and_check(src, work / f"rt{n:03d}", f"rt{n:03d}", odin_bin, tbc_tool,
                                   seed)
        except Exception as exc:  # one bad design must not stop the sweep; recorded
            out.append(RtlResult(f"rt{n:03d}", src.stem, "-", -1, "error",
                                 f"{type(exc).__name__}: {str(exc)[:150]}"))
    return out


def summary_lines(results: list[RtlResult]) -> list[str]:
    ran = [r for r in results if r.verdict in ("agree", "disagree", "error")]
    by = {v: sum(1 for r in ran if r.verdict == v) for v in ("agree", "disagree", "error")}
    skipped = sorted({r.base for r in results if r.verdict == "skipped"})
    lines = [f"RTL Trojans: {len(ran)} run on {len({r.base for r in ran})} bases; "
             f"sim_tb agrees with iverilog on {by['agree']}, disagrees on {by['disagree']}, "
             f"errors {by['error']}; bases skipped {len(skipped)}"]
    lines += [f"- {r.circuit} ({r.base}, {r.trojan}): {r.verdict} {r.detail}"
              f" iverilog first diff {r.iverilog_first_diff}, sim_tb {r.simtb_first_diff},"
              f" expected {r.fire_index}" for r in ran if r.verdict != "agree"]
    return lines
