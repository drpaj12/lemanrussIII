"""Round 4 runner: verification of a built family (cross-check, fire, cec) in parallel, and the
summary counts. Results go to answer_key/verification.json."""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

from lemanruss.htl import r4check
from lemanruss.htl.blif_text import parse_single_model

COMB_VECTORS = 512


def _verify_one(args: tuple[str, str, dict[str, object], str, int]) -> dict[str, object]:
    root_s, cid, meta, scratch_s, seed = args
    root = Path(root_s)
    circuits = root / "circuits"
    clean = circuits / f"{meta['clean']}.blif"
    inf = circuits / f"{cid}.blif"
    kind = str(meta["kind"])
    victim = str(meta["victim"])
    stuck = int(str(meta["stuck"]))
    window = int(str(meta["window"]))
    steps = r4check.find_witness(
        parse_single_model(clean.read_text(encoding="utf-8")),
        parse_single_model(inf.read_text(encoding="utf-8")), victim, stuck, window, seed)
    out: dict[str, object] = {"circuit": cid, "base": meta["base"], "kind": kind}
    out["cross_clean"] = r4check.crosscheck(clean, str(meta["clean"]), COMB_VECTORS, seed).to_dict()
    out["cross_infected"] = r4check.crosscheck(inf, cid, COMB_VECTORS, seed, steps).to_dict()
    out["fire"] = r4check.fire_check(clean, inf, cid, victim, stuck, window, seed, steps).to_dict()
    cec = r4check.cec_forced_off(clean, inf, Path(scratch_s), cid)
    out["cec"] = {"verdict": cec.verdict, "returncode": cec.returncode}
    return out


def verify_family(root: Path, workers: int = 4, seed: int = 5) -> list[dict[str, object]]:
    """Runs the checks on every infected circuit of a family build under `root`."""
    inserts = json.loads((root / "answer_key" / "inserts.json").read_text(encoding="utf-8"))
    scratch = root / "scratch"
    scratch.mkdir(exist_ok=True)
    tasks = [
        (str(root), cid, meta, str(scratch / f"{cid}.blif"), seed)
        for cid, meta in sorted(inserts.items())
    ]
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(workers) as pool:
        results = pool.map(_verify_one, tasks, chunksize=1)
    (root / "answer_key" / "verification.json").write_text(
        json.dumps(results, indent=1) + "\n", encoding="utf-8")
    return results


def summarise(results: list[dict[str, object]]) -> list[str]:
    n = len(results)

    def cross(key: str) -> tuple[int, int, int, int]:
        pts = cmp_ = mis = bad = 0
        for r in results:
            c = r[key]
            assert isinstance(c, dict)
            pts += int(c["vectors"])
            cmp_ += int(c["compares"])
            mis += int(c["mismatches"])
            bad += 1 if c["error"] else 0
        return pts, cmp_, mis, bad

    fired = sum(1 for r in results if isinstance(r["fire"], dict) and r["fire"]["odin_fired"])
    wit = sum(1 for r in results if isinstance(r["fire"], dict) and r["fire"]["witness"])
    verdicts: dict[str, int] = {}
    for r in results:
        c = r["cec"]
        assert isinstance(c, dict)
        verdicts[str(c["verdict"])] = verdicts.get(str(c["verdict"]), 0) + 1
    lines = [f"Verification of {n} infected circuits:"]
    for key, label in (("cross_clean", "clean base"), ("cross_infected", "infected")):
        pts, cmp_, mis, bad = cross(key)
        lines.append(f"- bit-parallel vs Odin III simulator, {label}: {pts} points, {cmp_} "
                     f"signal comparisons, {mis} mismatches, {bad} circuits errored")
    lines.append(f"- Odin III fire check: witness found {wit}/{n}, Odin III confirms {fired}/{n}")
    lines.append("- ABC equivalence (trigger forced inactive): " + ", ".join(
        f"{k} {v}" for k, v in sorted(verdicts.items())))
    return lines


# ---- restructuring runner --------------------------------------------------------------------

RARE_NET = 1e-2
OUT_DIR = "restructured"


def _measure_restructured(
    clean_path: Path, rpath: Path, nvec_comb: int = 1 << 17
) -> dict[str, object]:
    """Observable activation (outputs differ from the clean circuit) and rare-net statistics of
    one restructured infected circuit."""
    import gzip

    from lemanruss.htl.bitsim import compile_model, reset_inputs, simulate_comb, simulate_diff

    clean = parse_single_model(clean_path.read_text(encoding="utf-8"))
    with gzip.open(rpath, "rt", encoding="utf-8") as fh:
        rmodel = parse_single_model(fh.read())
    cc, rc = compile_model(clean), compile_model(rmodel)
    fixed = reset_inputs(clean)
    seq = bool(cc.latches)
    lanes, cycles = (256, 256) if seq else (nvec_comb, 1)
    curve = simulate_diff(cc, rc, lanes, cycles, 11, fixed)
    vals = simulate_comb(rc, 1 << 14, 3, fixed)
    n = 1 << 14
    ps = [min(vals[o].bit_count(), n - vals[o].bit_count()) / n for o, *_ in rc.blocks]
    rare = sum(1 for p in ps if p < RARE_NET)
    return {
        "p_obs": curve[-1] / lanes, "p_obs_lanes": lanes, "p_obs_cycles": cycles,
        "rare_net_fraction": rare / len(ps) if ps else 0.0,
        "rarest_net_p": min((p for p in ps if p > 0), default=0.0),
    }


def _restructure_task(
    args: tuple[str, str, str, str, str, str, str | None]
) -> dict[str, object]:
    from lemanruss.htl.restructure import restructure_one

    root_s, src_id, variant, new_id, scratch_s, tag, clean_id = args
    root = Path(root_s)
    out_dir = root / OUT_DIR
    res = restructure_one(root / "circuits" / f"{src_id}.blif", src_id, variant,
                          out_dir / f"{new_id}.blif.gz", Path(scratch_s), tag)
    d = res.to_dict()
    d["id"] = new_id
    d["clean"] = clean_id
    if clean_id is not None and res.verdict != "abc-failed":
        d["measure"] = _measure_restructured(
            root / "circuits" / f"{clean_id}.blif", out_dir / f"{new_id}.blif.gz")
    return d


def restructure_family(root: Path, short: str, workers: int = 4) -> list[dict[str, object]]:
    """Every circuit of the family build (clean and infected) x every ABC restructuring; each
    result equivalence-checked against its own source. Writes restructured/*.blif.gz and
    answer_key/restructured.json, and extends manifest.json and labels.json."""
    from lemanruss.htl.restructure import RESTRUCTURINGS

    # the pristine (identity-only) manifest and labels are kept beside the extended ones, so a
    # re-run starts from them and never reads its own output
    for name, path in (("manifest_base.json", root / "manifest.json"),
                       ("labels_base.json", root / "answer_key" / "labels.json")):
        saved = root / "answer_key" / name
        if not saved.exists():
            saved.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    man = json.loads((root / "answer_key" / "manifest_base.json").read_text(encoding="utf-8"))
    labels = json.loads((root / "answer_key" / "labels_base.json").read_text(encoding="utf-8"))
    inserts = json.loads((root / "answer_key" / "inserts.json").read_text(encoding="utf-8"))
    (root / OUT_DIR).mkdir(exist_ok=True)
    scratch = root / "scratch"
    scratch.mkdir(exist_ok=True)
    sources = sorted(c["id"] for c in man["circuits"])
    n = max(int(sid[len(short):]) for sid in sources)  # new ids start above every source id
    tasks = []
    for sid in sources:
        clean_id = inserts[sid]["clean"] if sid in inserts else None
        for variant in RESTRUCTURINGS:
            n += 1
            tasks.append((str(root), sid, variant, f"{short}{n:04d}", str(scratch),
                          f"w{n}", clean_id))
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(workers) as pool:
        results = pool.map(_restructure_task, tasks, chunksize=2)
    bases = {c["id"]: c["base"] for c in man["circuits"]}
    for r in results:
        if r["verdict"] != "abc-failed":
            man["circuits"].append({"id": r["id"], "base": bases[str(r["source"])],
                                    "file": f"{OUT_DIR}/{r['id']}.blif.gz"})
            labels[str(r["id"])] = labels[str(r["source"])]
    man["restructurings"] = ["identity", *RESTRUCTURINGS]
    clean_n = sum(1 for v in labels.values() if v is None)
    man["mix"] = {"clean": clean_n, "infected": len(labels) - clean_n,
                  "infected_fraction": (len(labels) - clean_n) / len(labels)}
    man["circuits"].sort(key=lambda c: c["id"])
    (root / "manifest.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    (root / "answer_key" / "labels.json").write_text(
        json.dumps(labels, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "answer_key" / "restructured.json").write_text(
        json.dumps(results, indent=1) + "\n", encoding="utf-8")
    return results


def _num(m: object, key: str) -> float:
    if isinstance(m, dict) and isinstance(m.get(key), (int, float)):
        return float(m[key])
    return 0.0


def restructure_tables(results: list[dict[str, object]]) -> list[str]:
    """Per-restructuring pooled table: equivalence, structure ratio vs source, rareness of the
    infected circuits."""
    import math

    from lemanruss.htl.restructure import RESTRUCTURINGS

    out = [
        "| restructuring | circuits | equivalent | unproven | not equiv / error | "
        "gates (geomean ratio) | depth (geomean ratio) | infected: observable P (geomean) | "
        "infected: rare-net fraction (mean) | infected: rarest net p (median) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for v in RESTRUCTURINGS:
        rs = [r for r in results if r["variant"] == v]
        eq = [r for r in rs if r["verdict"] == "equivalent"]
        un = [r for r in rs if r["verdict"] == "unproven"]
        bad = [r for r in rs if r["verdict"] not in ("equivalent", "unproven")]
        gr, dr = [], []
        for r in eq:
            b, a = r["before"], r["after"]
            assert isinstance(b, dict) and isinstance(a, dict)
            if b["names"] and a["names"] and b["depth"] and a["depth"]:
                gr.append(math.log(a["names"] / b["names"]))
                dr.append(math.log(a["depth"] / b["depth"]))
        ms = [r["measure"] for r in eq if isinstance(r.get("measure"), dict)]
        pobs = [x for x in (_num(m, "p_obs") for m in ms) if x > 0]
        rf = [_num(m, "rare_net_fraction") for m in ms]
        rn = sorted(_num(m, "rarest_net_p") for m in ms)

        def gm(xs: list[float]) -> str:
            return f"{math.exp(sum(xs) / len(xs)):.3f}" if xs else "-"

        out.append(
            f"| {v} | {len(rs)} | {len(eq)} | {len(un)} | {len(bad)} | {gm(gr)} | {gm(dr)} | "
            f"{(f'{math.exp(sum(map(math.log, pobs)) / len(pobs)):.2e}' if pobs else '-')} | "
            f"{(f'{sum(rf) / len(rf):.3f}' if rf else '-')} | "
            f"{(f'{rn[len(rn) // 2]:.2e}' if rn else '-')} |")
    return out
