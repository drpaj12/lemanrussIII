"""Seeker-Seq rc7 (round 9): the n200 family build, magic-number trigger only (spec section 13).

Reuses every shared n200 primitive (`BaseBuild`, `apply_specs`, `finish`, cut-and-stitch with its
dummy-cut fallback, `n200check.measure`/`odin_fire`/`cec_forced_off`) unmodified; only
`make_ctx_rc7` (Seeker-Seq only, `SeqCtxRc7`: the magic trigger drawn from register Q outputs and
primary inputs, no `p-energy`) and the per-circuit FF/latch equality hard gate (spec section
13.4, checked on the pre-obfuscation infected BLIF, before ABC) are new. Output tree and answer-
key schema are identical to `lemanruss.htl.n200`'s, so `n200run.assemble`/`n200release`/
`n200verify`/`lemanruss verify` read an rc7 tree unchanged.
"""

from __future__ import annotations

import gzip
import json
import random
import resource
import sys
import time
from pathlib import Path

from lemanruss.htl import edit_netlist as en
from lemanruss.htl.bitsim import compile_model, latches_of
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.n200 import SETS_ALL, BaseBuild, active_sets, apply_specs, finish
from lemanruss.htl.n200check import (
    Json,
    cec_forced_off,
    encode_steps,
    measure,
    odin_fire,
    run_cec,
    scoap_fields,
    trig_name,
)
from lemanruss.htl.n200plan import (
    SLOW,
    Ctx,
    TSpec,
    make_ctx_rc7,
    pick_weighted,
    trojan_of,
)
from lemanruss.htl.stimulus import reset_trigger_hit

N_SET = 100
N_INF_LO, N_INF_HI = 10, 70
MULTI = ((1, 0.5), (2, 0.3), (3, 0.2))
MAX_FAILED = 300
MAX_DUP = 60


def _draw_circuit(ctx: Ctx, rng: random.Random, m: int) -> list[TSpec]:
    specs: list[TSpec] = []
    nets: set[str] = set()
    victims: set[str] = set()
    for _ in range(m):
        order = [pick_weighted(rng, ctx.mix)]
        rest = [p for p, _w in ctx.mix if p != order[0]]
        rng.shuffle(rest)
        order += rest
        got: TSpec | None = None
        for payload in order:
            got = ctx.draw(payload, nets, victims)
            if got is not None:
                break
        if got is None:
            break
        specs.append(got)
        nets |= got.net_set()
        victims.add(got.victim)
    return specs


def build_pre_rc7(
    bb: BaseBuild, ctx: Ctx, specs: list[TSpec], cid: str
) -> tuple[Json, list[tuple[TSpec, list[dict[str, int]]]], Path] | str:
    """`n200.build_pre`, plus the rc7 FF/latch equality hard gate (spec section 13.4): before
    ABC, the infected circuit's flip-flop/latch count must equal the golden's, exactly."""
    tmp = bb.scratch / f"{cid}.pre.blif"
    read = {n for _o, ins, _p, _q in ctx.comp.blocks for n in ins}
    sources = sorted(n for n in [*ctx.comp.data_inputs, *(q for _d, q in ctx.comp.latches)]
                     if n in read)
    ins_of = {o: list(ins) for o, ins, _p, _q in ctx.comp.blocks}
    tag = "trojan:" + "+".join(trojan_of(t, ctx.gates, ctx.dep.depth).id for t in specs)
    try:
        en.insert(bb.golden_path, tmp, tag,
                  lambda ed: apply_specs(ed, specs, ctx.clock, sources, ins_of),
                  allow_fallback=False, conv=bb.conv)
    except Exception as exc:
        return f"insert: {type(exc).__name__}: {str(exc)[:100]}"
    model = parse_single_model(tmp.read_text(encoding="utf-8"))
    clean_ff = len(latches_of(ctx.model))
    infected_ff = len(latches_of(model))
    if infected_ff != clean_ff:
        return (f"rc7 FF/latch equality hard gate failed: clean {clean_ff}, "
                f"infected {infected_ff}")
    icomp = compile_model(model)
    if reset_trigger_hit(icomp, [trig_name(j) for j, t in enumerate(specs) if t.payload != SLOW]):
        return "trigger satisfied in the reset state"
    recs: list[Json] = []
    trigs: list[str] = []
    steps_out: list[tuple[TSpec, list[dict[str, int]]]] = []
    wit: dict[str, list[str]] = {}
    meas = measure(ctx, icomp, specs, bb.meas_seed)
    for j, (t, (fields, steps)) in enumerate(zip(specs, meas, strict=True)):
        base_rec: Json = {
            "circuit": cid, "family": "Seeker-Seq",
            "base": bb.base, "trojan_index": j, "trojan_id": trojan_of(t).id,
            "trigger": t.trig, "payload": t.payload, "victim": t.victim,
            "target_band": t.band, "k": len(t.nets) if t.nets else 0, "size": t.size,
            "param": t.param, "always_on": False,
            "ff_count_clean": clean_ff, "ff_count_infected": infected_ff,
        }
        base_rec.update(scoap_fields(ctx, t))
        base_rec.update(fields)
        if t.payload == SLOW:
            base_rec["always_on"] = True
            recs.append(base_rec)
            continue
        trigs.append(trig_name(j))
        if steps is None:
            return f"no witness for Trojan {j} ({t.payload}, {t.trig}): {fields}"
        ok, detail = odin_fire(bb.golden_path, tmp, t, steps, None)
        base_rec["odin_replay"] = ok
        if not ok:
            return f"Odin III replay of Trojan {j} ({t.payload}) fails: {detail}"
        steps_out.append((t, steps))
        wit[str(j)] = encode_steps(bb.golden_inputs, steps)
        recs.append(base_rec)
    verdict = cec_forced_off(bb.golden_path, tmp, bb.scratch / f"{cid}.off.blif", trigs)
    if verdict != "equivalent":
        return f"cec with the triggers forced inactive: {verdict}"
    bb.witness[cid] = wit
    return {"records": recs, "off_cec": verdict}, steps_out, tmp


def build_set_rc7(
    bb: BaseBuild, set_name: str, kind: str, short: str, ctx: Ctx, n_inf: int, out: list[Json]
) -> tuple[int, int]:
    """`n200.build_set`, calling `build_pre_rc7` (the FF/latch gate) instead of `build_pre`."""
    rng = random.Random(f"{bb.seed}:{bb.base}:{set_name}:draw")
    built = failed = empty = 0
    while built < n_inf and failed < MAX_FAILED and empty < 4:
        m = rng.choices([c for c, _w in MULTI], weights=[w for _c, w in MULTI])[0]
        specs = _draw_circuit(ctx, rng, m)
        if not specs:
            empty += 1
            continue
        empty = 0
        cid = bb.next_id(short)
        pre = build_pre_rc7(bb, ctx, specs, cid)
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
    if built < n_inf:
        bb.fail(set_name, f"supplied {built} of {n_inf} infected circuits "
                f"({failed} failed proposals, {empty} empty draws)")
    want = N_SET - n_inf
    clean = dups = failed = 0
    while clean < want and failed < MAX_FAILED and dups < MAX_DUP:
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
    if clean < want:
        bb.fail(set_name, f"supplied {clean} of {want} clean circuits "
                f"(structures repeat: {dups} in a row, {failed} failed)")
    return built, clean


def build_base_rc7(job: tuple[str, Path, Path, int, int]) -> Json:
    """One Seeker-Seq rc7 base; same cacheable shape as `n200.build_base`."""
    family, base_path, out, first, seed = job
    short = "ss"
    cache = out / "answer_key" / "jobs" / f"{base_path.stem}.json"
    if cache.exists():
        loaded: Json = json.loads(cache.read_text(encoding="utf-8"))
        return loaded
    t0 = time.monotonic()
    (out / "circuits").mkdir(parents=True, exist_ok=True)
    bb = BaseBuild(base_path, out, first, seed)
    result: Json = {"base": bb.base, "family": family}
    circuits: list[Json] = []
    gid = bb.next_id(short)
    (bb.circuits / f"{gid}.blif").write_text(bb.golden_text, encoding="utf-8")
    result["golden"] = gid
    verdict = run_cec(base_path, bb.golden_path)[0]
    if verdict != "equivalent":
        bb.fail("all", f"canonical golden: {verdict}")
    sets: dict[str, dict[str, int | str]] = {}
    for set_name, kind in active_sets():
        si = [n for n, _k in SETS_ALL].index(set_name)
        try:
            made = make_ctx_rc7(bb.golden_path, seed * 10 + si)
            if isinstance(made, str):
                bb.fail(set_name, made)
                continue
            result["kind"], result["gates"] = made.kind, made.gates
            n_inf = random.Random(f"{seed}:{bb.base}:{set_name}:ninf").randint(N_INF_LO, N_INF_HI)
            b_inf, b_clean = build_set_rc7(bb, set_name, kind, short, made, n_inf, circuits)
            sets[set_name] = {"map": kind, "n_infected_drawn": n_inf, "infected": b_inf,
                              "clean": b_clean}
        except Exception as exc:
            # A set that raised is dropped whole (no half-built set reaches the answer key);
            # the other sets of the base still build.
            circuits[:] = [c for c in circuits if c.get("set") != set_name]
            sets.pop(set_name, None)
            bb.fail(set_name, f"{type(exc).__name__}: {str(exc)[:160]}")
    result["sets"] = sets
    result["circuits"] = circuits
    result["failures"] = bb.failures
    result["seconds"] = round(time.monotonic() - t0)
    result["max_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    if bb.witness:
        wdir = out / "answer_key" / "witnesses"
        wdir.mkdir(exist_ok=True)
        with gzip.open(wdir / f"{bb.base}.json.gz", "wt", encoding="utf-8") as fh:
            json.dump({"inputs": list(bb.golden_inputs), "steps": bb.witness}, fh)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    counts = {k: (v["infected"], v["clean"]) for k, v in sets.items()}
    print(f"BUILD-TIME {bb.base} {result['seconds']} s, max RSS {result['max_rss_mb']} MB, "
          f"(infected, clean) {counts}, failures {len(bb.failures)}", file=sys.stderr, flush=True)
    return result


def run_family_rc7(
    bases: list[Path], out: Path, seed: int = 0, workers: int = 1, max_gates: int = 10**9,
    first_index: int = 0,
) -> list[Json]:
    """`n200run.run_family`, for `build_base_rc7` (Seeker-Seq only). `first_index` shifts the id
    blocks (rc8 builds the OpenCores bases after the 36 rc7 blocks, so ids never repeat)."""
    import multiprocessing

    from lemanruss.htl.n200run import BLOCK, assemble, gate_count

    order = sorted(bases, key=lambda p: (gate_count(p), p.stem))
    jobs = [("Seeker-Seq", p, out, (first_index + i) * BLOCK + 1, seed)
            for i, p in enumerate(order)
            if gate_count(p) <= max_gates]
    skipped = [p.stem for p in order if gate_count(p) > max_gates]
    (out / "answer_key").mkdir(parents=True, exist_ok=True)
    if workers <= 1:
        results = [build_base_rc7(j) for j in jobs]
    else:
        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(workers) as pool:
            results = list(pool.imap(build_base_rc7, jobs, chunksize=1))
    assemble("Seeker-Seq", out, results, skipped, seed)
    return results
