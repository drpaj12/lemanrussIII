"""Top-up of the short cells of a released Seeker family (Seeker v2.0 full sets, 2026-11-09).

A cell is one base in one mapping set (K4, K6, G or S). Released cells below 100 circuits are
filled with new draws; every existing circuit stays as it is. The new draws:

- keep the set's own number of infected circuits (`n_infected_drawn`, drawn once from 10..70) and
  add the missing infected and clean circuits, so the infected share stays inside the rule;
- run the same pipeline and every gate of the family build (`n200.build_pre` for Comb,
  `n200rc7.build_pre_rc7` for Seq, `n200.finish`: obfuscation, equivalence to the source, fire
  check, distinctness, silicon cell check). No gate is relaxed to fill a set;
- start from the structures already released: the hashes and signatures of the base's existing
  circuits are loaded first, so a new circuit is distinct from every old one;
- take new ids from the unused ids of the base's own id block (the block is 301 ids; a short cell
  left some unused), so the ids say nothing about which circuits are new;
- use a new seed (never committed) for the drawing, the pipeline scripts and the id choice.

The output is a build tree with only the new circuits; `lemanruss/htl/v2merge.py` joins it to the
released tree. A cell that cannot reach 100 with distinct, gated circuits stays short, with the
build record (`failures`) giving the cause; the merge drops it from the release.
"""

from __future__ import annotations

import gzip
import json
import random
import resource
import sys
import time
from collections.abc import Callable
from pathlib import Path

from lemanruss.htl import obfuscate as ob
from lemanruss.htl.bitsim import compile_model
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.n200 import (
    MAX_FAILED,
    MULTI,
    N_SET,
    SETS_ALL,
    BaseBuild,
    _draw_circuit,
    _sha,
    build_pre,
    finish,
)
from lemanruss.htl.n200check import Json, run_cec
from lemanruss.htl.n200plan import Ctx, TSpec, make_ctx, make_ctx_rc7

Steps = list[tuple[TSpec, list[dict[str, int]]]]
MAX_DUP = 300  # five times the original build's 60 repeats in a row: a top-up tries harder
PreBuilder = Callable[[BaseBuild, Ctx, list[TSpec], str], tuple[Json, Steps, Path] | str]


class TopupBuild(BaseBuild):
    """`BaseBuild` whose ids come from a list of free ids (shuffled by the caller)."""

    def __init__(self, base_path: Path, out: Path, seed: int, free: list[int]) -> None:
        super().__init__(base_path, out, 0, seed)
        self.free = free

    def next_id(self, short: str) -> str:
        if self.slot >= len(self.free):
            raise ValueError("no free id left in the base's id block")
        cid = f"{short}{self.free[self.slot]:04d}"
        self.slot += 1
        return cid


def read_gz(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read()


def _pre_builder(mode: str) -> PreBuilder:
    if mode == "seq":
        from lemanruss.htl.n200rc7 import build_pre_rc7

        return build_pre_rc7
    return build_pre


def _make_ctx(mode: str, golden: Path, seed: int) -> Ctx | str:
    return make_ctx_rc7(golden, seed) if mode == "seq" else make_ctx(golden, seed)


def fill_set(
    bb: BaseBuild, set_name: str, kind: str, short: str, ctx: Ctx, need_inf: int,
    need_clean: int, pre_builder: PreBuilder, out: list[Json],
) -> tuple[int, int]:
    """The loops of `n200.build_set` with the missing counts instead of a fresh draw."""
    rng = random.Random(f"{bb.seed}:{bb.base}:{set_name}:draw")
    built = failed = empty = 0
    while built < need_inf and failed < MAX_FAILED and empty < 4:
        m = rng.choices([c for c, _w in MULTI], weights=[w for _c, w in MULTI])[0]
        specs = _draw_circuit(ctx, rng, m)
        if not specs:
            empty += 1
            continue
        empty = 0
        cid = bb.next_id(short)
        pre = pre_builder(bb, ctx, specs, cid)
        res: Json | str
        if isinstance(pre, str):
            res = pre
        else:
            rec, steps, pre_path = pre
            res = finish(bb, set_name, kind, cid, pre_path, steps, specs)
            if not isinstance(res, str):
                res.update(rec)
                res["specs"] = [s.to_dict() for s in specs]
        if isinstance(res, str):
            failed += 1
            bb.slot -= 1
            if res != "dup":
                bb.fail(set_name, res)
            continue
        out.append(res)
        built += 1
    if built < need_inf:
        bb.fail(set_name, f"top-up supplied {built} of {need_inf} missing infected circuits "
                f"({failed} failed proposals, {empty} empty draws)")
    clean = dups = failed = 0
    while clean < need_clean and failed < MAX_FAILED and dups < MAX_DUP:
        cid = bb.next_id(short)
        res = finish(bb, set_name, kind, cid, None, [], [])
        if isinstance(res, str):
            bb.slot -= 1
            if res == "dup":
                dups += 1
            else:
                failed += 1
                bb.fail(set_name, res)
            continue
        dups = 0
        res["records"] = []
        out.append(res)
        clean += 1
    if clean < need_clean:
        bb.fail(set_name, f"top-up supplied {clean} of {need_clean} missing clean circuits "
                f"(structures repeat: {dups} in a row, {failed} failed)")
    return built, clean


def _ids_of(entry: Json) -> list[str]:
    sets = entry["sets"]
    assert isinstance(sets, dict)
    ids: list[str] = [str(entry["golden"])]
    for v in sets.values():
        ids += [str(i) for i in v["infected_ids"] + v["clean_ids"]]
    return ids


def free_ids(used: list[str], block: int, seed: int, base: str) -> list[int]:
    """The unused ids of the block that holds `used`, in a seeded random order."""
    nums = [int(u[2:]) for u in used]
    first = ((nums[0] - 1) // block) * block + 1
    if any((n - 1) // block != (first - 1) // block for n in nums):
        raise ValueError(f"{base}: ids of one base span more than one block")
    free = [n for n in range(first, first + block) if n not in set(nums)]
    random.Random(f"{seed}:{base}:free-ids").shuffle(free)
    return free


def topup_base(
    job: tuple[str, str, Path, Path, str, Path, int, list[str], int],
) -> Json:
    """job = (family, mode, release tree, plain-golden file, base, out, seed, set names,
    id block). Returns the result dict (also cached under out/answer_key/jobs)."""
    family, mode, rel, golden_file, base, out, seed, set_names, block = job
    cache = out / "answer_key" / "jobs" / f"{base}.json"
    if cache.exists():
        loaded: Json = json.loads(cache.read_text(encoding="utf-8"))
        return loaded
    t0 = time.monotonic()
    short = "sc" if family == "Seeker-Comb" else "ss"
    key = rel / "answer_key"
    sets_all = json.loads((key / "sets.json").read_text(encoding="utf-8"))
    entry = sets_all[base]
    used = _ids_of(entry)
    (out / "circuits").mkdir(parents=True, exist_ok=True)
    bb = TopupBuild(golden_file, out, seed, free_ids(used, block, seed, base))
    cuts = json.loads((key / "cuts.json").read_text(encoding="utf-8"))
    scripts = json.loads((key / "scripts.json").read_text(encoding="utf-8"))
    for cid in used[1:]:
        text = read_gz(rel / "circuits" / f"{cid}.blif.gz")
        bb.hashes.add(_sha(text))
        bb.sigs.add((str(scripts[cid]["map"]), ob.signature(text)))
        c = cuts.get(cid, {})
        for size, label in zip(c.get("sizes", []), c.get("labels", []), strict=False):
            if label != "dummy":
                bb.cut_sizes.append(int(size))
    result: Json = {"base": base, "family": family, "golden": entry["golden"],
                    "kind": entry.get("kind"), "gates": entry.get("gates")}
    circuits: list[Json] = []
    sets: dict[str, Json] = {}
    pre_builder = _pre_builder(mode)
    for set_name in set_names:
        cell = entry["sets"].get(set_name)
        if cell is None:  # the cell was never built (the original build stopped before it)
            kinds = {n: k for n, k in SETS_ALL}
            n_draw = random.Random(f"{seed}:{base}:{set_name}:ninf").randint(10, 70)
            cell = {"map": kinds[set_name], "n_infected_drawn": n_draw, "infected": 0,
                    "clean": 0}
        kind = str(cell["map"])
        n_inf = int(cell["n_infected_drawn"])
        need_inf = max(0, n_inf - int(cell["infected"]))
        need_clean = max(0, N_SET - n_inf - int(cell["clean"]))
        if need_inf == 0 and need_clean == 0:
            continue
        try:
            si = [n for n, _k in SETS_ALL].index(set_name)
            made = _make_ctx(mode, bb.golden_path, seed * 10 + si)
            if isinstance(made, str):
                bb.fail(set_name, made)
                continue
            b_inf, b_clean = fill_set(bb, set_name, kind, short, made, need_inf, need_clean,
                                      pre_builder, circuits)
            sets[set_name] = {"map": kind, "n_infected_drawn": n_inf, "need_infected": need_inf,
                              "need_clean": need_clean, "infected": b_inf, "clean": b_clean}
        except Exception as exc:
            circuits[:] = [c for c in circuits if c.get("set") != set_name]
            bb.fail(set_name, f"{type(exc).__name__}: {str(exc)[:160]}")
    result["sets"] = sets
    result["circuits"] = circuits
    result["failures"] = bb.failures
    result["seconds"] = round(time.monotonic() - t0)
    result["max_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    if bb.witness:
        wdir = out / "answer_key" / "witnesses"
        wdir.mkdir(exist_ok=True)
        keep = {c["id"] for c in circuits}
        with gzip.open(wdir / f"{base}.json.gz", "wt", encoding="utf-8") as fh:
            json.dump({"inputs": list(bb.golden_inputs),
                       "steps": {k: v for k, v in bb.witness.items() if k in keep}}, fh)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    counts = {k: (v["infected"], v["clean"]) for k, v in sets.items()}
    print(f"TOPUP-TIME {base} {result['seconds']} s, max RSS {result['max_rss_mb']} MB, "
          f"(infected, clean) {counts}, failures {len(bb.failures)}", file=sys.stderr, flush=True)
    return result


def golden_ok(base_file: Path, golden_file: Path) -> bool:
    """The released golden equals the plain base (canonical form), by ABC cec."""
    return run_cec(base_file, golden_file)[0] == "equivalent"


def circuit_count(path: Path) -> int:
    return len(compile_model(parse_single_model(path.read_text(encoding="utf-8"))).blocks)
