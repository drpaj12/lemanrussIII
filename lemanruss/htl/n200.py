"""Seeker v2.0 at n = 300 per base (rc4 redesign): build one base and a whole family.

Spec: docs/specs/2026-11-01-seeker-n200-design.md section 4. Per base: the golden and three sets
of 100 circuits (LUT k = 4, LUT k = 6, AND/OR/NOT gates). Each set draws its own number of infected
circuits (uniform 10..70) with 1..3 Trojans; clean and infected circuits go through the same
obfuscation (`obfuscate.py`). Output tree:

    <out>/circuits/<id>.blif                  golden and the 300 obfuscated circuits
    <out>/manifest.json                       circuits (id, base, file) and the golden of each base
    <out>/answer_key/{labels,sets,trojans,rareness,failures,scripts}.json
    <out>/answer_key/pre/<id>.blif.gz         infected circuits before obfuscation
    <out>/answer_key/witnesses/<base>.json.gz input sequences, one per Trojan with a witness
    <out>/answer_key/jobs/<base>.json         per-base result (cache: a rerun loads it)
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import random
import resource
import sys
import time
from pathlib import Path

from lemanruss.htl import cutstitch as cs
from lemanruss.htl import edit_netlist as en
from lemanruss.htl import obfuscate as ob
from lemanruss.htl import si_gates
from lemanruss.htl.bitsim import compile_model
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.edit_netlist import Editor
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
    DOS,
    ENERGY,
    SLOW,
    Ctx,
    TSpec,
    depth_analysis,
    make_ctx,
    pick_weighted,
    trojan_of,
)

N_SET = 100
N_INF_LO, N_INF_HI = 10, 70
SETS = (("K4", "k4"), ("K6", "k6"), ("G", "gates"))
SETS_ALL = (*SETS, ("S", "silicon"))  # S = Seeker-Si rc2 (spec 2026-11-07)


def active_sets() -> tuple[tuple[str, str], ...]:
    """The sets built: `LEMANRUSS_SETS` (comma list of K4,K6,G,S), default the three of rc5/rc7."""
    names = os.environ.get("LEMANRUSS_SETS", "")
    if not names:
        return SETS
    want = names.split(",")
    return tuple(s for s in SETS_ALL if s[0] in want)
MULTI = ((1, 0.5), (2, 0.3), (3, 0.2))
MAX_FAILED = 300  # failed proposals per set before the set is declared exhausted
MAX_DUP = 60  # consecutive repeated structures of a clean circuit before the set is exhausted
DUMMY_SIZE_LO, DUMMY_SIZE_HI = 2, 10  # fallback when a base has drawn no real cut yet


def support(ins_of: dict[str, list[str]], net: str) -> set[str]:
    """The sources (primary inputs, latch outputs) in the combinational cone of `net`, and the
    gate outputs on the way."""
    seen: set[str] = set()
    todo = [net]
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        todo += ins_of.get(n, [])
    return seen


def apply_specs(
    ed: Editor, specs: list[TSpec], clock: str | None, sources: list[str],
    ins_of: dict[str, list[str]],
) -> None:
    """The Trojans of one circuit as recipes; every Trojan has its own net names (index j).
    `p-slowdown` has no trigger (always on, spec section 2): only the chain is spliced in."""
    for j, t in enumerate(specs):
        if t.payload == SLOW:
            # A source in the victim's own cone could make `tmp & s` constant (tmp implies not s);
            # a constant cell would be a label (rc5 gate `const`), so the AND terms read others.
            free = [x for x in sources if x not in support(ins_of, t.victim)]
            if not free:
                raise ValueError(f"no free source for the slowdown on {t.victim}")
            m = max(1, min(4, t.param, len(free)))
            pick = random.Random(f"slow:{t.victim}:{t.param}").sample(free, m)
            en.slowdown_absorb(ed, t.victim, pick)
            continue
        trig = trig_name(j)
        if t.isolate:
            ed.isolate(t.victim)
        if t.trig in ("comb", "magic"):
            # t-comb-rare and t-state-pattern are the same combinational AND-of-literals
            # primitive; "magic" just draws its nets from register Q outputs/inputs, not
            # combinational-internal nets (rc7, spec section 13.1), and adds no latch.
            en.comb_rare_trigger(ed, t.nets, trig)
        elif clock is None:
            raise ValueError("sequential trigger on a design without a clock")
        elif t.trig == "ctr":
            en.seq_counter(ed, t.nets, t.size, clock, trig, f"__htl_c{j}")
        else:
            en.seq_pattern(ed, t.nets, clock, trig, f"__htl_s{j}")
        if t.payload == DOS:
            en.dos_stuck(ed, t.victim, t.param, trig)
        elif t.payload == ENERGY:
            assert clock is not None
            en.energy(ed, clock, t.param, trig, f"__htl_energy{j}")
        else:
            en.err_bit(ed, t.victim, False, trig)


def cuts_for(
    bb: BaseBuild, src: Path, specs: list[TSpec], rng: random.Random
) -> list[cs.CutSpec]:
    """The real cuts of `src` (one per energy / slowdown Trojan of `specs`), or, when there is
    none, a dummy cut of the same size distribution (section 1/2 of the cut-and-stitch spec): so
    a detector cannot tell "this circuit was cut" from the presence of a cut alone."""
    text = src.read_text(encoding="utf-8")
    inputs, outputs, blocks = ob.parse(text)
    cuts: list[cs.CutSpec] = []
    for j, t in enumerate(specs):
        if t.payload == ENERGY:
            cut = cs.energy_cut(blocks, j, t.param)
            if cut.idx:
                cuts.append(cs.CutSpec(cut, True, f"energy{j}"))
                bb.cut_sizes.append(len(cut.idx))
        elif t.payload == SLOW:
            cut = cs.slowdown_cut(blocks, t.victim)
            if cut.idx:
                cuts.append(cs.CutSpec(cut, True, f"slow{j}"))
                bb.cut_sizes.append(len(cut.idx))
    if cuts:
        return cuts
    size = rng.choice(bb.cut_sizes) if bb.cut_sizes else rng.randint(DUMMY_SIZE_LO, DUMMY_SIZE_HI)
    dummy = cs.dummy_cut(list(inputs), list(outputs), blocks, rng, size)
    return [cs.CutSpec(dummy, True, "dummy")] if dummy is not None else []


def _sha(text: str) -> str:
    """Hash ignoring the `.model` line and comments (what the distinctness gate compares)."""
    norm = "\n".join(ln for ln in text.splitlines()
                     if not ln.startswith(".model") and not ln.lstrip().startswith("#"))
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


class BaseBuild:
    """State of one base's build."""

    def __init__(self, base_path: Path, out: Path, first: int, seed: int) -> None:
        self.base_path = base_path
        self.base = base_path.stem
        self.out = out
        self.seed = seed
        self.circuits = out / "circuits"
        self.key = out / "answer_key"
        self.scratch = out / "scratch" / self.base
        self.scratch.mkdir(parents=True, exist_ok=True)
        (self.key / "pre").mkdir(parents=True, exist_ok=True)
        self.perm = random.Random(f"{seed}:{self.base}:ids").sample(
            range(len(active_sets()) * N_SET + 1), len(active_sets()) * N_SET + 1)
        self.first = first
        self.slot = 0
        self.golden_text = ob.canonical(base_path.read_text(encoding="utf-8"))
        self.golden_path = self.scratch / "golden.blif"
        self.golden_path.write_text(self.golden_text, encoding="utf-8")
        self.conv = en.convention_of(self.golden_text)
        self.golden_inputs = compile_model(parse_single_model(self.golden_text)).data_inputs
        self.hashes = {_sha(self.golden_text)}
        self.sigs: set[tuple[str, str]] = set()
        self.failures: list[Json] = []
        self.witness: dict[str, dict[str, list[str]]] = {}
        self.meas_seed = 1000 + seed
        self.attempt = 0
        self.cut_sizes: list[int] = []  # real cuts drawn so far (block count); dummy cuts sample it
        self.depth_ref: dict[str, int] = {}  # set_name -> one reference obfuscated-golden depth

    def next_id(self, short: str) -> str:
        cid = f"{short}{self.first + self.perm[self.slot]:04d}"
        self.slot += 1
        return cid

    def fail(self, set_name: str, reason: str) -> None:
        self.failures.append({"base": self.base, "set": set_name, "reason": reason})

    def rng(self, set_name: str) -> random.Random:
        self.attempt += 1
        return random.Random(f"{self.seed}:{self.base}:{set_name}:ob:{self.attempt}")


def finish(
    bb: BaseBuild, set_name: str, kind: str, cid: str, pre: Path | None,
    steps: list[tuple[TSpec, list[dict[str, int]]]], specs: list[TSpec],
) -> Json | str:
    """Obfuscates `pre` (infected) or the golden (clean), proves and fire-checks the result,
    accepts it. A Json record on success, else the reason. Cut-and-stitch (spec section 13):
    every circuit is cut, either on its own energy-ring / slowdown-chain Trojans (real cuts) or,
    when it has none, on a dummy region of the same size distribution, so "the circuit was cut"
    carries no label."""
    t_fin = time.monotonic()
    src = pre if pre is not None else bb.golden_path
    rng = bb.rng(set_name)
    cuts = cuts_for(bb, src, specs, rng)
    got = cs.cut_and_stitch(src, kind, rng, bb.scratch, cid, cuts) if cuts else \
        ob.obfuscate(src, kind, rng, bb.scratch, cid)
    if isinstance(got, str):
        return got
    text, script = got
    rings: dict[str, list[str]] = {}
    if cuts:
        info = json.loads(script)
        rings = {k.removeprefix("energy"): v for k, v in info.get("rings", {}).items()}
    sig = ob.signature(text)
    if (kind, sig) in bb.sigs:
        return "dup"
    final = bb.scratch / f"{cid}.final.blif"
    final.write_text(text, encoding="utf-8")
    verdict, rc = run_cec(src, final)
    if verdict != "equivalent":
        return (f"obfuscated circuit vs its source: {verdict} (rc {rc}, cuts "
                f"{[c.label for c in cuts]}, {kind})")
    fired: list[bool] = []
    for t, st in steps:
        ring = rings.get(str(specs.index(t))) if t.payload == ENERGY else None
        ok, detail = odin_fire(bb.golden_path, final, t, st, ring)
        if not ok:
            return f"fire check fails after obfuscation ({t.payload}): {detail}"
        fired.append(ok)
    h = _sha(text)
    if h in bb.hashes:
        return "dup"
    verilog = ""
    if kind == "silicon":
        verilog, problems = si_gates.check(text, si_gates.ff_count(bb.golden_text))
        if problems:
            return "silicon gate: " + "; ".join(problems)[:300]
    bb.hashes.add(h)
    bb.sigs.add((kind, sig))
    (bb.circuits / f"{cid}.blif").write_text(text, encoding="utf-8")
    if verilog:
        (bb.out / "circuits_v").mkdir(exist_ok=True)
        (bb.out / "circuits_v" / f"{cid}.v").write_text(verilog, encoding="utf-8")
    if pre is not None:
        with gzip.open(bb.key / "pre" / f"{cid}.blif.gz", "wt", encoding="utf-8") as fh:
            fh.write(pre.read_text(encoding="utf-8"))
    cut_labels = [c.label for c in cuts]
    rec: Json = {"id": cid, "set": set_name, "map": kind, "script": script, "obf_cec": verdict,
                 "fire_checked": len(fired),
                 "cut_sizes": [len(c.cut.idx) for c in cuts], "cut_labels": cut_labels,
                 "rings": rings, "finish_s": round(time.monotonic() - t_fin, 2)}
    if any(label.startswith("slow") for label in cut_labels):
        rec["slow_depth"] = _depth(text)
        rec["slow_depth_ref"] = slow_depth_ref(bb, kind, set_name)
    return rec


def slow_depth_ref(bb: BaseBuild, kind: str, set_name: str) -> int:
    """One reference obfuscation of the base's own golden (same `kind`, no cut), cached per
    (base, set): the baseline a slowdown circuit's finished depth is reported against (spec
    section 13)."""
    if set_name not in bb.depth_ref:
        rng = random.Random(f"{bb.seed}:{bb.base}:{set_name}:depth-ref")
        got = ob.obfuscate(bb.golden_path, kind, rng, bb.scratch, f"depth-ref-{set_name}")
        bb.depth_ref[set_name] = -1 if isinstance(got, str) else _depth(got[0])
    return bb.depth_ref[set_name]


def _depth(text: str) -> int:
    model = parse_single_model(text)
    return depth_analysis(compile_model(model), model).depth


def build_pre(
    bb: BaseBuild, ctx: Ctx, specs: list[TSpec], cid: str
) -> tuple[Json, list[tuple[TSpec, list[dict[str, int]]]], Path] | str:
    """Insert the Trojans into the golden, measure, witness, replay, prove forced-off. Returns
    (record, [(spec, witness steps)], pre path) or the reason."""
    tmp = bb.scratch / f"{cid}.pre.blif"
    # Primary inputs / latch outputs the golden itself reads (a net the golden never uses would be
    # a foreign net in the infected circuit only, rc5 gate `name_foreign`).
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
    icomp = compile_model(model)
    recs: list[Json] = []
    trigs: list[str] = []
    steps_out: list[tuple[TSpec, list[dict[str, int]]]] = []
    wit: dict[str, list[str]] = {}
    meas = measure(ctx, icomp, specs, bb.meas_seed)
    for j, (t, (fields, steps)) in enumerate(zip(specs, meas, strict=True)):
        base_rec: Json = {
            "circuit": cid, "family": "Seeker-Comb" if ctx.kind == "comb" else "Seeker-Seq",
            "base": bb.base, "trojan_index": j, "trojan_id": trojan_of(t).id,
            "trigger": t.trig, "payload": t.payload, "victim": t.victim,
            "target_band": t.band, "k": len(t.nets) if t.nets else 0, "size": t.size,
            "param": t.param, "always_on": False,
        }
        base_rec.update(scoap_fields(ctx, t))
        base_rec.update(fields)
        if t.payload == SLOW:
            # Always on (spec section 2): no trigger net exists to witness or to force off.
            base_rec["always_on"] = True
            recs.append(base_rec)
            continue
        trigs.append(trig_name(j))
        if steps is None:
            return f"no witness for Trojan {j} ({t.payload}, {t.trig}): {fields}"
        pre_ring = [f"__htl_energy{j}_q{i}" for i in range(t.param)]
        ok, detail = odin_fire(bb.golden_path, tmp, t, steps, pre_ring)
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


def build_set(
    bb: BaseBuild, set_name: str, kind: str, short: str, ctx: Ctx, n_inf: int, out: list[Json]
) -> tuple[int, int]:
    """One set of up to 100 circuits: n_inf infected, the rest clean. Returns the counts."""
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
        pre = build_pre(bb, ctx, specs, cid)
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


def build_base(job: tuple[str, Path, Path, int, int]) -> Json:
    """One base of a family; returns its result dict (also cached in answer_key/jobs)."""
    family, base_path, out, first, seed = job
    short = "sc" if family == "Seeker-Comb" else "ss"
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
    try:
        for set_name, kind in active_sets():
            si = [n for n, _k in SETS_ALL].index(set_name)
            made = make_ctx(bb.golden_path, seed * 10 + si)
            if isinstance(made, str):
                bb.fail(set_name, made)
                continue
            # made.mix stays Ctx's own default (COMB_MIX / SEQ_MIX): rc5/rc6 cut-and-stitch
            # restores the energy and slowdown payloads rc4 dropped (spec section 13).
            result["kind"], result["gates"] = made.kind, made.gates
            n_inf = random.Random(f"{seed}:{bb.base}:{set_name}:ninf").randint(N_INF_LO, N_INF_HI)
            b_inf, b_clean = build_set(bb, set_name, kind, short, made, n_inf, circuits)
            sets[set_name] = {"map": kind, "n_infected_drawn": n_inf, "infected": b_inf,
                              "clean": b_clean}
    except Exception as exc:
        bb.fail("all", f"{type(exc).__name__}: {str(exc)[:160]}")
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
