"""`lemanruss verify` for an n = 300 release (rc4): integrity, separation and leak checks as before,
the distinct-file, style-parity and provenance gates, and the chain of the obfuscation, all
re-run from the files on disk:

- every Trojan of every infected circuit: its stored witness replayed in Odin III, golden against
  the finished circuit (the payload shows);
- every infected circuit equivalent to its pre-obfuscation form (`answer_key/pre/`), and that form
  equivalent to the golden with all its triggers forced inactive;
- every clean circuit equivalent to the golden;
- the rareness records of a sample (per base) re-measured on the pre-obfuscation circuits.
"""

from __future__ import annotations

import gzip
import json
import multiprocessing
import random
from pathlib import Path

from lemanruss.htl.bitsim import (
    compile_model,
    exhaustive_lanes,
    reset_inputs,
    simulate_comb,
    simulate_given,
    simulate_seq,
)
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.n200check import (
    cec_forced_off,
    decode_steps,
    odin_fire,
    run_cec,
    trig_name,
)
from lemanruss.htl.n200plan import ENERGY, SLOW
from lemanruss.htl.n200run import _spec
from lemanruss.htl.relverify import (
    RNG_SEED,
    Json,
    _d,
    _load,
    _sigma_ok,
    _unpack,
    check_integrity,
    check_leak,
    check_separation,
)

SAMPLE_PER_BASE = 2  # per base and set


def _witnesses(root: Path, base: str) -> tuple[list[str], dict[str, dict[str, list[str]]]]:
    f = root / "answer_key" / "witnesses" / f"{base}.json.gz"
    if not f.exists():
        return [], {}
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    return list(data["inputs"]), dict(data["steps"])


def _inf_task(args: tuple[str, str, Json, str]) -> Json:
    root_s, cid, prov, scratch_s = args
    root, scratch = Path(root_s), Path(scratch_s)
    ins = _d(prov["insert"])
    base = str(prov["base"])
    golden = _unpack(root, str(prov["clean_twin"]), scratch, "golden")
    final = _unpack(root, cid, scratch, "final")
    pre = scratch / f"{cid}.pre.blif"
    with gzip.open(root / "answer_key" / "pre" / f"{cid}.blif.gz", "rt", encoding="utf-8") as fh:
        pre.write_text(fh.read(), encoding="utf-8")
    trojans = ins["trojans"]
    assert isinstance(trojans, list)
    specs = [_spec(_d(t)) for t in trojans]
    inputs, wit = _witnesses(root, base)
    cuts_file = root / "answer_key" / "cuts.json"
    rings: dict[str, list[str]] = {}
    if cuts_file.exists():
        got = _d(_d(_load(cuts_file)).get(cid, {})).get("rings", {})
        assert isinstance(got, dict)
        rings = {str(k): [str(x) for x in v] for k, v in got.items()}
    replayed = fired = 0
    out: Json = {"circuit": cid, "base": base, "trojans": len(specs)}
    problems: list[str] = []
    for j, t in enumerate(specs):
        if t.payload == SLOW:
            continue  # always on: no trigger, no witness (depth is reported, not replayed)
        rows = wit.get(cid, {}).get(str(j))
        if rows is None:
            problems.append(f"Trojan {j}: no stored witness")
            continue
        replayed += 1
        try:
            ok, detail = odin_fire(golden, final, t, decode_steps(inputs, rows),
                                   rings.get(str(j)) if t.payload == ENERGY else None)
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {str(exc)[:80]}"
        if ok:
            fired += 1
        else:
            problems.append(f"Trojan {j}: {detail}")
    out["replayed"], out["fired"] = replayed, fired
    out["cec"] = cec_forced_off(golden, pre, scratch / f"{cid}.off.blif",
                                [trig_name(j) for j, t in enumerate(specs) if t.payload != SLOW])
    out["obf_cec"] = run_cec(pre, final)[0]
    if out["cec"] != "equivalent":
        problems.append(f"forced-off cec {out['cec']}")
    if out["obf_cec"] != "equivalent":
        problems.append(f"obfuscation cec {out['obf_cec']}")
    out["problems"] = problems
    return out


def _group_task(args: tuple[str, str, list[str], str]) -> list[Json]:
    """cec of every circuit in `ids` against `src` (a golden: its variants; a variant or an
    infected identity circuit: its restructured forms)."""
    root_s, src, ids, scratch_s = args
    root, scratch = Path(root_s), Path(scratch_s)
    a = _unpack(root, src, scratch, "src")
    res: list[Json] = []
    for v in ids:
        b = _unpack(root, v, scratch, "var")
        verdict, rc = run_cec(a, b)
        res.append({"circuit": v, "source": src, "cec": verdict, "rc": rc})
    return res


def check_function(root: Path, scratch: Path, workers: int) -> Json:
    scratch.mkdir(parents=True, exist_ok=True)
    prov = _d(_load(root / "answer_key" / "provenance.json"))
    inf_tasks = []
    var_groups: dict[str, list[str]] = {}
    for cid, p in sorted(prov.items()):
        pd = _d(p)
        if pd["role"] == "infected":
            sd = scratch / f"w_{cid}"
            sd.mkdir(exist_ok=True)
            inf_tasks.append((str(root), cid, pd, str(sd)))
        elif pd["clean_twin"] != cid:
            var_groups.setdefault(str(pd["clean_twin"]), []).append(cid)
    rs_tasks = []
    for src, vs in sorted(var_groups.items()):
        sd = scratch / f"v_{src}"
        sd.mkdir(exist_ok=True)
        rs_tasks.append((str(root), src, sorted(vs), str(sd)))
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(workers) as pool:
        inf = pool.map(_inf_task, inf_tasks, chunksize=1)
        rs = [x for lst in pool.imap_unordered(_group_task, rs_tasks, chunksize=1) for x in lst]
    verdicts: dict[str, int] = {}
    for r in rs:
        verdicts[str(r["cec"])] = verdicts.get(str(r["cec"]), 0) + 1
    off_v: dict[str, int] = {}
    obf_v: dict[str, int] = {}
    for i in inf:
        off_v[str(i["cec"])] = off_v.get(str(i["cec"]), 0) + 1
        obf_v[str(i["obf_cec"])] = obf_v.get(str(i["obf_cec"]), 0) + 1
    bad_rs = [r for r in rs if r["cec"] != "equivalent"]
    bad_inf = [i for i in inf if i["problems"]]
    return {"infected": len(inf), "trojans": sum(int(str(i["trojans"])) for i in inf),
            "witnesses_replayed": sum(int(str(i["replayed"])) for i in inf),
            "odin_fired": sum(int(str(i["fired"])) for i in inf),
            "forced_off_cec": off_v, "obfuscation_cec": obf_v, "clean_checked": len(rs),
            "clean_cec": verdicts, "failures": [*bad_inf, *bad_rs],
            "ok": not bad_inf and not bad_rs}


def _rare_task(args: tuple[str, str, Json, list[Json]]) -> Json:
    from lemanruss.htl.release import read_blif_gz

    root_s, cid, prov, recs = args
    root = Path(root_s)
    clean = parse_single_model(read_blif_gz(root / "circuits" / f"{prov['clean_twin']}.blif.gz"))
    with gzip.open(root / "answer_key" / "pre" / f"{cid}.blif.gz", "rt", encoding="utf-8") as fh:
        icomp = compile_model(parse_single_model(fh.read()))
    out: Json = {"circuit": cid, "ok": True, "checks": []}
    checks: list[Json] = []
    if _d(prov["insert"])["kind"] == "comb":
        exact = len(icomp.data_inputs) <= 20
        if exact:
            given, nvec = exhaustive_lanes(icomp.data_inputs)
            vals = simulate_given(icomp, given, nvec)
        else:
            nvec = 1 << 20
            vals = simulate_comb(icomp, nvec, RNG_SEED)
        for r in [x for x in recs if not x.get("always_on")]:
            trig = trig_name(int(str(r["trojan_index"])))
            p_new, p_old = vals[trig].bit_count() / nvec, float(str(r["p"]))
            good = abs(p_new - p_old) <= 1e-12 if exact else _sigma_ok(p_new, p_old, nvec, nvec)
            checks.append({"j": r["trojan_index"], "p_new": p_new, "p_manifest": p_old,
                           "ok": good})
    else:
        recs = [x for x in recs if not x.get("always_on")]
        if not recs:
            out["checks"] = []
            return out
        lanes = int(str(recs[0]["seq_lanes"]))
        trigs = [trig_name(int(str(r["trojan_index"]))) for r in recs]
        curves = simulate_seq(icomp, lanes, 1024, RNG_SEED, trigs, reset_inputs(clean))
        for r, tn in zip(recs, trigs, strict=True):
            w = r["p_fire_within"]
            assert isinstance(w, dict)
            for n, vals_ in w.items():
                pn = curves[tn][int(n) - 1] / lanes
                good = _sigma_ok(pn, float(vals_[0]), lanes, lanes)
                checks.append({"j": r["trojan_index"], "n": n, "new": pn,
                               "manifest": vals_[0], "ok": good})
    out["checks"] = checks
    out["ok"] = all(bool(c["ok"]) for c in checks)
    return out


def check_rareness(root: Path, workers: int, seed: int) -> Json:
    prov = _d(_load(root / "answer_key" / "provenance.json"))
    raw = _load(root / "answer_key" / "rareness.json")
    assert isinstance(raw, list)
    by_circuit: dict[str, list[Json]] = {}
    for r in raw:
        by_circuit.setdefault(str(_d(r)["circuit"]), []).append(_d(r))
    strata: dict[str, list[str]] = {}
    for cid, p in prov.items():
        pd = _d(p)
        if pd["role"] == "infected" and cid in by_circuit:
            strata.setdefault(str(pd["stratum"]), []).append(cid)
    rng = random.Random(seed)
    sample = sorted(c for ids in strata.values()
                    for c in rng.sample(sorted(ids), min(SAMPLE_PER_BASE, len(ids))))
    tasks = [(str(root), c, _d(prov[c]), by_circuit[c]) for c in sample]
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(workers) as pool:
        res = pool.map(_rare_task, tasks, chunksize=1)
    return {"sample": sample, "per_stratum": SAMPLE_PER_BASE, "results": res,
            "ok": all(bool(r["ok"]) for r in res)}


def verify_n200(root: Path, scratch: Path, workers: int = 6, seed: int = 5) -> Json:
    rep: Json = {"release": root.name}
    rep["a_integrity"] = check_integrity(root)
    rep["e_separation"] = check_separation(root)
    rep["b_leak"] = check_leak(root, own_style=True)
    rep["d_rareness"] = check_rareness(root, workers, seed)
    rep["c_function"] = check_function(root, scratch, workers)
    from lemanruss.htl.n200gates import verify_gates

    rep.update(verify_gates(root, workers))
    rep["ok"] = all(bool(_d(rep[k])["ok"]) for k in
                    ("a_integrity", "e_separation", "b_leak", "d_rareness", "c_function",
                     "f_distinct", "g_style", "h_provenance"))
    return rep
