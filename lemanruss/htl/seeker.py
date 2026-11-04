"""Seeker v2.0 family builds (Seeker-Comb, Seeker-Seq): SCOAP + signal-probability site
selection, trigger widening toward a rareness band, insertion, and the rareness report.

Brief "Round 3 addendum" / "Seeker v2.0 benchmark families". Netlist level on BLIF text; the
text inserters of lemanruss.htl.insert_netlist are kept until the Odin III netlist-editing API
merges.

Site selection (comb): every internal net gets its signal probability from a bit-parallel
simulation (lemanruss.htl.bitsim) AND SCOAP from Odin III's `scoap` pass (CC of its rare value);
candidates are ranked by SCOAP difficulty, then a trigger AND is widened net by net (k grows) until
its joint probability reaches the target band. The reported p is measured on an independent
vector sample (different seed), so the selection sample does not bias it (plan default 14).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lemanruss.htl import edit_netlist as en
from lemanruss.htl.bitsim import (
    Compiled,
    _latch_fields,
    compile_model,
    exhaustive_lanes,
    latches_of,
    simulate_comb,
    simulate_given,
)
from lemanruss.htl.blif_text import BlifModel, parse_single_model
from lemanruss.htl.edit_netlist import TRIGGER_NET, Editor, InsertReport
from lemanruss.htl.payloads import DosStuckPayload
from lemanruss.htl.rareness import (
    RarenessRecord,
    band_of,
    scoap_value,
    wilson,
)
from lemanruss.htl.triggers import CombRareTrigger
from lemanruss.htl.trojan import Trojan, compose

COMB_BANDS = (("p<1e-2", 1e-2), ("p<1e-3", 1e-3), ("p<1e-4", 1e-4))
SEQ_CYCLES = (16, 64, 256, 1024)
EXHAUSTIVE_MAX = 20


@dataclass(frozen=True)
class Failure:
    base: str
    variant: str
    reason: str


@dataclass(frozen=True)
class Built:
    circuit_id: str
    base: str
    variant: str
    trojan: Trojan
    infected_path: Path
    record: RarenessRecord
    victim: str = ""
    stuck: int = 1
    kind: str = "comb"
    window: int = 1
    insertion: InsertReport | None = None


def scoap_table(path: Path, sequential: bool, sigprob: int = 0) -> dict[str, dict[str, int]]:
    """Per-net SCOAP (and p1_ppm when sigprob > 0) of a BLIF, by net name, from Odin III."""
    from odin3 import Design

    with Design() as design:
        design.run_pass("read_blif", str(path))
        result = design.scoap(sequential=sequential, sigprob=sigprob, seed=1)
    return {n["name"]: n for n in result["modules"][0]["nets"]}


def _readers(model: BlifModel) -> set[str]:
    from lemanruss.htl.blif_sim import _names_blocks

    seen: set[str] = set()
    for ins, _out, _rows in _names_blocks(model):
        seen.update(ins)
    for d, _q, _c in latches_of(model):
        seen.add(d)
    return seen


def quiet_outputs(model: BlifModel) -> list[str]:
    """Primary outputs driven by a `.names` block that nothing reads (so a payload on them cannot
    close a loop through a trigger net); plan default 15."""
    from lemanruss.htl.blif_text import find_names_block

    read = _readers(model)
    return [o for o in model.outputs if o not in read and find_names_block(model, o) is not None]


def pick_comb_victim(
    quiet: list[str], values: dict[str, int], trig: int, full: int
) -> tuple[str, int, int] | None:
    """(output, stuck value, selection-sample vectors where the payload shows) for the quiet
    output and stuck value that make the payload show on the most triggered vectors; None when
    the payload would be masked on every sampled vector (round 4: a stuck-at that equals the
    clean value is no Trojan effect)."""
    best: tuple[str, int, int] | None = None
    for o in quiet:
        for stuck in (1, 0):
            shown = (trig & (~values[o] if stuck else values[o]) & full).bit_count()
            if shown and (best is None or shown > best[2]):
                best = (o, stuck, shown)
    return best


@dataclass
class _Cand:
    name: str
    rare: int
    p_rare: float
    mask: int
    cc: int


def _candidates(
    comp: Compiled, values: dict[str, int], nvec: int, scoap: dict[str, dict[str, int]],
    forbidden: set[str], min_p: float,
) -> list[_Cand]:
    full = (1 << nvec) - 1
    out: list[_Cand] = []
    for name, _ins, _pats, _on in comp.blocks:
        if name in forbidden:
            continue
        ones = values[name].bit_count()
        rare = 1 if ones * 2 <= nvec else 0
        cnt = ones if rare else nvec - ones
        if cnt == 0 or cnt / nvec < min_p:
            continue
        row = scoap.get(name, {})
        cc = row.get("cc1" if rare else "cc0", 10**18)
        mask = values[name] if rare else ~values[name] & full
        out.append(_Cand(name, rare, cnt / nvec, mask, cc))
    out.sort(key=lambda c: (-min(c.cc, 10**17), c.p_rare))
    return out


def widen_trigger(
    pool: list[_Cand], nvec: int, target_p: float, lower_p: float, min_hits: int, max_k: int
) -> tuple[list[_Cand], int]:
    """Greedy AND: add the candidate that lands the joint count inside [lower, current) with the
    smallest count (else the largest count below `lower`), until joint p <= target_p.
    Returns (chosen, joint lane mask)."""
    mask = (1 << nvec) - 1
    cnt = nvec
    chosen: list[_Cand] = []
    lower = lower_p * nvec
    while cnt / nvec > target_p and len(chosen) < max_k:
        best: tuple[tuple[int, float], _Cand, int] | None = None
        for c in pool[:400]:
            if c in chosen:
                continue
            n = (mask & c.mask).bit_count()
            if n < min_hits or n >= cnt:
                continue
            key = (0, n) if n >= lower else (1, -n)
            if best is None or key < best[0]:
                best = (key, c, n)
        if best is None:
            break
        chosen.append(best[1])
        mask &= best[1].mask
        cnt = best[2]
    return chosen, mask


def _percentiles(
    chosen: list[_Cand], comp: Compiled, values: dict[str, int], nvec: int
) -> tuple[float, float]:
    """% of internal nets that are LESS rare than a chosen net, (rarest chosen, mean chosen)."""
    rares = []
    for name, _i, _p, _o in comp.blocks:
        ones = values[name].bit_count()
        r = min(ones, nvec - ones) / nvec
        if r > 0:
            rares.append(r)
    rares.sort()
    pct = [100.0 * sum(1 for r in rares if r > c.p_rare) / len(rares) for c in chosen]
    return max(pct), sum(pct) / len(pct)


def _clock_of(model: BlifModel) -> str | None:
    """Clock of the first rising-edge flip-flop (`re`); a level-sensitive latch enable (`ah`,
    `al`, in VTR designs such as ch_intrinsics) is never used as the inserted logic's clock.
    Falls back to the first clocked latch."""
    first: str | None = None
    for line in model.body:
        if line.startswith(".latch"):
            w = line.split()
            clk = _latch_fields(line)[2]
            if clk and len(w) > 3 and w[3] == "re":
                return clk
            first = first or clk
    return first


def build_comb(
    base_path: Path, band: tuple[str, float], out_dir: Path, circuit_id: str, seed: int
) -> Built | Failure:
    """One Seeker-Comb infected circuit: wide rare trigger + DosStuck on a quiet output."""
    base = base_path.stem
    variant = band[0]
    model = parse_single_model(base_path.read_text(encoding="utf-8"))
    if latches_of(model):
        return Failure(base, variant, "has latches (not a combinational base)")
    quiet = quiet_outputs(model)
    if not quiet:
        return Failure(base, variant, "no quiet driven output for the payload")
    comp = compile_model(model)
    nvec_sel = 1 << 20
    values = simulate_comb(comp, nvec_sel, seed)
    sc = scoap_table(base_path, sequential=False, sigprob=20000)
    cands = _candidates(comp, values, nvec_sel, sc, set(model.outputs), min_p=1.0 / nvec_sel)
    target = band[1]
    chosen, lanes = widen_trigger(cands, nvec_sel, target, target / 10, min_hits=32, max_k=16)
    if not chosen:
        return Failure(base, variant, "no rare net with joint hits in the selection sample")
    joint = lanes.bit_count() / nvec_sel
    if joint > target:
        return Failure(base, variant, f"band unreachable: best joint p {joint:.2e} with "
                       f"k={len(chosen)} (design too small for this band)")
    picked = pick_comb_victim(quiet, values, lanes, (1 << nvec_sel) - 1)
    if picked is None:
        return Failure(base, variant, "payload masked: no quiet output differs from its stuck "
                       "value on any sampled triggered vector")
    victim, stuck, _shown = picked
    nets = tuple((c.name, c.rare) for c in chosen)
    trigger = CombRareTrigger(k=len(nets), nets=nets)
    payload = DosStuckPayload(victim=victim, stuck_value=stuck)
    trojan = compose(trigger, payload, "netlist", site=victim)
    path = out_dir / f"{circuit_id}.blif"

    def recipe(ed: Editor) -> None:
        en.comb_rare_trigger(ed, nets)
        en.dos_stuck(ed, victim, stuck)

    ins = en.insert(base_path, path, f"trojan:{trojan.id}", recipe,
                         events_dir=en.events_dir_of(path))
    infected = parse_single_model(path.read_text(encoding="utf-8"))
    rec = _measure_comb(model, infected, comp, chosen, sc, victim, path, base, variant, circuit_id,
                        trojan, seed + 1000, values, nvec_sel)
    return Built(circuit_id, base, variant, trojan, path, rec, victim, stuck, "comb", 1, ins)


def _measure_comb(
    model: BlifModel, infected: BlifModel, comp: Compiled, chosen: list[_Cand],
    sc: dict[str, dict[str, int]], victim: str, path: Path, base: str, variant: str,
    circuit_id: str, trojan: Trojan, seed: int, sel_values: dict[str, int], sel_nvec: int,
) -> RarenessRecord:
    icomp = compile_model(infected)
    n_in = len(icomp.data_inputs)
    exact = n_in <= EXHAUSTIVE_MAX
    if exact:
        given, nvec = exhaustive_lanes(icomp.data_inputs)
        iv = simulate_given(icomp, given, nvec)
        cv = simulate_given(comp, given, nvec)
    else:
        nvec = 1 << 20
        iv = simulate_comb(icomp, nvec, seed)
        cv = simulate_comb(comp, nvec, seed)
    trig = iv[TRIGGER_NET]
    hits = trig.bit_count()
    lo, hi = (hits / nvec, hits / nvec) if exact else wilson(hits, nvec)
    p = hits / nvec
    diff = 0
    for o in model.outputs:
        diff |= cv[o] ^ iv[o]
    mismatches = (diff & ~trig & ((1 << nvec) - 1)).bit_count()
    shown = (trig & (cv[victim] ^ iv[victim])).bit_count()
    fires = shown > 0
    inf_sc = scoap_table(path, sequential=False)
    rec = RarenessRecord(
        circuit=circuit_id, family="Seeker-Comb", base=base, trojan_id=trojan.id,
        target_band=variant, k=len(chosen), p=p, p_lo=lo, p_hi=hi, vectors=nvec, exact=exact,
        expected_vectors=(1 / p) if p > 0 else None, band=band_of(p),
        trigger_cc=[scoap_value(c.cc) for c in chosen],
        victim_co=scoap_value(sc.get(victim, {}).get("co")),
        infected_trigger_cc1=scoap_value(inf_sc.get(TRIGGER_NET, {}).get("cc1")),
        net_p_bitsim=[c.p_rare for c in chosen],
        net_p_odin=[_odin_p(sc, c) for c in chosen],
        fires=fires, stealth_mismatches=mismatches,
        payload_visible_fraction=(shown / hits) if hits else None,
    )
    rec.rank_percentile_min, rec.rank_percentile_mean = _percentiles(
        chosen, comp, sel_values, sel_nvec
    )
    return rec


def _odin_p(sc: dict[str, dict[str, int]], c: _Cand) -> float | None:
    ppm = sc.get(c.name, {}).get("p1_ppm")
    if ppm is None or ppm < 0:
        return None
    p1 = ppm / 1e6
    return p1 if c.rare else 1 - p1


def _family_job(
    job: tuple[str, Path, Path, int, int, int, int]
) -> list[Built | Failure]:
    """One base of a family in a worker: ids are fixed by the base's position, so the result
    does not depend on how many workers ran (`first` ids are used before this base).

    The result is cached in `answer_key/jobs/<base>.pkl` next to `circuits/`: a rerun after a
    crash loads it instead of building the base again. An exception while building a base
    (Odin III refuses a design: a combinational loop, say) becomes one Failure per variant, so
    one design never takes the run down (round 6: an unpicklable Odin3Error did)."""
    import pickle
    import resource
    import sys
    import time

    family, base_path, circuits, first, seed, max_blocks, _size = job
    cache = circuits.parent / "answer_key" / "jobs" / f"{base_path.stem}.pkl"
    if cache.exists():
        cached: list[Built | Failure] = pickle.loads(cache.read_bytes())
        return cached
    t0 = time.monotonic()
    short = "sc" if family == "Seeker-Comb" else "ss"
    n = first
    results: list[Built | Failure] = []
    names = [b[0] for b in COMB_BANDS] if family == "Seeker-Comb" else [
        f"{k}-{b}" for k in ("ctr", "pat") for b in ("fast", "mid", "slow")]
    try:
        if family == "Seeker-Comb":
            for band in COMB_BANDS:
                n += 1
                results.append(build_comb(base_path, band, circuits, f"{short}{n:04d}", seed))
        else:
            from lemanruss.htl.seqtune import build_seq_base

            def next_id() -> str:
                nonlocal n
                n += 1
                return f"{short}{n:04d}"

            results = build_seq_base(base_path, circuits, next_id, seed, max_blocks)
    except Exception as exc:
        why = f"{type(exc).__name__}: {str(exc)[:160]}"
        results = [Failure(base_path.stem, v, why) for v in names]
    built_n = sum(1 for r in results if isinstance(r, Built))
    print(f"BUILD-TIME {base_path.stem} {time.monotonic() - t0:.0f} s, max RSS "
          f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024} MB, built {built_n}, "
          f"failed {len(results) - built_n}", file=sys.stderr, flush=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(results))
    return results


def run_family(
    family: str, bases: list[Path], out_dir: Path, seed: int = 0, max_blocks: int = 30000,
    workers: int = 1,
) -> tuple[list[Built], list[Failure]]:
    """Builds every base x variant of a family into out_dir/circuits, writes the v2.0 manifest,
    the answer key (labels + rareness, kept apart under out_dir/answer_key), and clean copies.
    With `workers` > 1 the bases run in a pool, largest first; circuit ids are assigned by the
    base's position (1 clean + 3 or 6 variants each), so the output equals a serial run."""
    circuits = out_dir / "circuits"
    key_dir = out_dir / "answer_key"
    circuits.mkdir(parents=True, exist_ok=True)
    key_dir.mkdir(parents=True, exist_ok=True)
    short = "sc" if family == "Seeker-Comb" else "ss"
    per = 1 + (3 if family == "Seeker-Comb" else 6)
    built: list[Built] = []
    failures: list[Failure] = []
    clean_entries: list[dict[str, str]] = []
    jobs: list[tuple[str, Path, Path, int, int, int, int]] = []
    for i, base_path in enumerate(bases):
        first = i * per + 1  # the clean copy is id `first`, variants follow
        clean_id = f"{short}{first:04d}"
        (circuits / f"{clean_id}.blif").write_text(
            base_path.read_text(encoding="utf-8"), encoding="utf-8")
        clean_entries.append({"id": clean_id, "base": base_path.stem})
        jobs.append((family, base_path, circuits, first, seed, max_blocks,
                     base_path.stat().st_size))
    outs: dict[int, list[Built | Failure]] = {}
    if workers <= 1:
        for i, job in enumerate(jobs):
            outs[i] = _family_job(job)
    else:
        import multiprocessing

        order = sorted(range(len(jobs)), key=lambda i: -jobs[i][6])
        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(workers) as pool:
            done = pool.imap(_family_job, [jobs[i] for i in order], chunksize=1)
            for i, job_res in zip(order, done, strict=True):
                outs[i] = job_res
    for i in range(len(jobs)):
        for res in outs[i]:
            if isinstance(res, Failure):
                failures.append(res)
            else:
                built.append(res)
    _write_family_files(family, bases, out_dir, built, failures, clean_entries, seed)
    return built, failures


def _write_family_files(
    family: str, bases: list[Path], out_dir: Path, built: list[Built], failures: list[Failure],
    clean_entries: list[dict[str, str]], seed: int,
) -> None:
    from lemanruss.htl.families import family_manifest, family_readme

    key_dir = out_dir / "answer_key"
    manifest = family_manifest(family, [b.stem for b in bases], built, clean_entries, seed)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    labels: dict[str, str | None] = {e["id"]: None for e in clean_entries}
    for b in built:
        labels[b.circuit_id] = b.trojan.id
    (key_dir / "labels.json").write_text(
        json.dumps(labels, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    clean_of = {e["base"]: e["id"] for e in clean_entries}
    inserts = {
        b.circuit_id: {"base": b.base, "clean": clean_of[b.base], "variant": b.variant,
                       "victim": b.victim, "stuck": b.stuck, "kind": b.kind, "window": b.window}
        for b in built
    }
    (key_dir / "inserts.json").write_text(
        json.dumps(inserts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (key_dir / "insertion.json").write_text(
        json.dumps({b.circuit_id: b.insertion.__dict__ for b in built if b.insertion},
                   indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (key_dir / "rareness.json").write_text(
        json.dumps([b.record.to_dict() for b in built], indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (out_dir / "README.md").write_text(family_readme(family), encoding="utf-8")
    (key_dir / "failures.json").write_text(
        json.dumps([f.__dict__ for f in failures], indent=2) + "\n", encoding="utf-8")
