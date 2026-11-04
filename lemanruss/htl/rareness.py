"""Rareness report (round 3; brief "Round 3 addendum").

Peter 2026-10-31: report the rareness quality of the insertion, not how well the Trojan is
inserted. One `RarenessRecord` per infected circuit, a pooled table across circuits; insertion
quality (fires, stealth mismatches) is a secondary column only.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

INF = 10**18
BANDS = (("p<1e-4", 1e-4), ("p<1e-3", 1e-3), ("p<1e-2", 1e-2))


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion (well behaved at 0 hits)."""
    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def band_of(p: float) -> str:
    """Smallest band the estimate falls in; 'p>=1e-2' above all bands; 'never' for zero hits."""
    if p <= 0:
        return "never"
    for name, limit in BANDS:
        if p < limit:
            return name
    return "p>=1e-2"


def scoap_value(v: int | None) -> int | None:
    """None for SCOAP INF (unreachable)."""
    return None if v is None or v >= INF else v


@dataclass
class RarenessRecord:
    circuit: str
    family: str
    base: str
    trojan_id: str
    target_band: str
    k: int  # number of nets / stages in the trigger
    # activation probability (combinational: per random vector; sequential: see p_fire_within)
    p: float | None = None
    p_lo: float | None = None
    p_hi: float | None = None
    vectors: int = 0
    exact: bool = False
    expected_vectors: float | None = None  # 1/p
    band: str = ""
    # SCOAP of the trigger nets (clean design) and of the payload victim
    trigger_cc: list[int | None] = field(default_factory=list)  # CC of each rare value
    trigger_sc: list[int | None] = field(default_factory=list)  # SC of each rare value (seq)
    victim_co: int | None = None
    victim_so: int | None = None
    infected_trigger_cc1: int | None = None  # SCOAP on the infected netlist's trigger net
    infected_trigger_sc1: int | None = None
    # signal probability of the chosen nets: this module's bit-parallel sim vs Odin III sigprob
    net_p_bitsim: list[float] = field(default_factory=list)
    net_p_odin: list[float | None] = field(default_factory=list)
    rank_percentile_min: float | None = None  # % of nets less rare than the rarest chosen net
    rank_percentile_mean: float | None = None
    # sequential: P(trigger high within N cycles) from multi-cycle simulation
    p_fire_within: dict[int, tuple[float, float, float]] = field(default_factory=dict)
    seq_lanes: int = 0
    # secondary: insertion quality
    fires: bool | None = None
    stealth_mismatches: int | None = None
    equivalent: bool | None = None
    payload_visible_fraction: float | None = None  # triggered vectors where outputs differ
    # rc7 FF/latch equality hard gate (spec section 13.4): before ABC, must be exactly equal
    ff_count_clean: int | None = None
    ff_count_infected: int | None = None

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["p_fire_within"] = {str(n): list(v) for n, v in self.p_fire_within.items()}
        return d


def _fmt(p: float | None) -> str:
    return "-" if p is None else f"{p:.2e}"


def table_rows(records: list[RarenessRecord]) -> list[str]:
    """Markdown rows: one per infected circuit."""
    out = [
        "| circuit | trigger | k | target | p (95% CI) | vectors | 1/p | band | CC max | "
        "CO victim | rank pct | fires | stealth mism |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        ccs = [c for c in r.trigger_cc if c is not None]
        out.append(
            f"| {r.circuit} | {r.trojan_id} | {r.k} | {r.target_band} | "
            f"{_fmt(r.p)} [{_fmt(r.p_lo)}, {_fmt(r.p_hi)}]{' exact' if r.exact else ''} | "
            f"{r.vectors} | {_fmt(r.expected_vectors)} | {r.band} | "
            f"{max(ccs) if ccs else '-'} | {r.victim_co if r.victim_co is not None else '-'} | "
            f"{_fmt(r.rank_percentile_min)} | {r.fires} | {r.stealth_mismatches} |"
        )
    return out


def seq_table_rows(records: list[RarenessRecord]) -> list[str]:
    """Markdown rows for sequential triggers: SC/SO beside P(fire within N cycles)."""
    ns = sorted({n for r in records for n in r.p_fire_within})
    head = "| circuit | trigger | k | SC max | SO victim | infected SC1 | " + " | ".join(
        f"P(fire<=N={n}) [95% CI]" for n in ns
    ) + " | lanes | fires | stealth mism |"
    out = [head, "|" + "---|" * (head.count("|") - 1)]
    for r in records:
        scs = [c for c in r.trigger_sc if c is not None]
        cells = [
            f"{_fmt(r.p_fire_within[n][0])} [{_fmt(r.p_fire_within[n][1])}, "
            f"{_fmt(r.p_fire_within[n][2])}]" if n in r.p_fire_within else "-"
            for n in ns
        ]
        out.append(
            f"| {r.circuit} | {r.trojan_id} | {r.k} | {max(scs) if scs else '-'} | "
            f"{r.victim_so if r.victim_so is not None else '-'} | "
            f"{r.infected_trigger_sc1 if r.infected_trigger_sc1 is not None else '-'} | "
            + " | ".join(cells)
            + f" | {r.seq_lanes} | {r.fires} | {r.stealth_mismatches} |"
        )
    return out


def pooled_comb(records: list[RarenessRecord]) -> list[str]:
    """Pooled across circuits: counts per band, geometric mean of p, total vectors."""
    out = ["| band reached | circuits |", "|---|---|"]
    counts: dict[str, int] = {}
    for r in records:
        counts[r.band] = counts.get(r.band, 0) + 1
    for name in [b for b, _ in BANDS] + ["p>=1e-2", "never"]:
        out.append(f"| {name} | {counts.get(name, 0)} |")
    ps = [r.p for r in records if r.p]
    if ps:
        gm = math.exp(sum(math.log(p) for p in ps) / len(ps))
        out.append(f"\nPooled: {len(records)} infected circuits, geometric mean p = {gm:.3e} "
                   f"over the {len(ps)} that fired at least once, "
                   f"{sum(r.vectors for r in records)} vectors in total.")
    return out


def pooled_seq(records: list[RarenessRecord]) -> list[str]:
    ns = sorted({n for r in records for n in r.p_fire_within})
    out = [
        "| N cycles | circuits | with P(fire<=N)>0 | min | median | max |",
        "|---|---|---|---|---|---|",
    ]
    for n in ns:
        vals = sorted(r.p_fire_within[n][0] for r in records if n in r.p_fire_within)
        pos = [v for v in vals if v > 0]
        med = vals[len(vals) // 2] if vals else None
        out.append(
            f"| {n} | {len(vals)} | {len(pos)} | {_fmt(vals[0] if vals else None)} | "
            f"{_fmt(med)} | {_fmt(vals[-1] if vals else None)} |"
        )
    return out
