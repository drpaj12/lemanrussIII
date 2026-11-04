"""`lemanruss verify <release-dir>` (spec section 10.3): independent re-check of a release from
the files on disk. Nothing from the build is reused except the libraries (BLIF text, bit-parallel
simulator, Odin III bindings, tools/equiv-check).
"""

from __future__ import annotations

import json
import math
import multiprocessing
import random
import re
import subprocess
from pathlib import Path

from lemanruss.htl import r4check
from lemanruss.htl.bitsim import (
    compile_model,
    exhaustive_lanes,
    reset_inputs,
    simulate_comb,
    simulate_given,
    simulate_seq,
)
from lemanruss.htl.blif_text import find_names_block, parse_single_model, render
from lemanruss.htl.release import (
    detect_style,
    read_blif_gz,
    sha256_file,
    style_regex,
)

WORDS = ("htl", "trojan", "trigger", "payload", "ht_", "infect", "clean", "odin3_edit")
# Odin III writes edit events as `.attr odin3_edit ...` (BLIF) or "odin3_edit" (JSON); they are
# internal provenance for the answer key and must not be in any detector-visible file.
EDIT_EVENT_MARKS = ("odin3_edit", "odin3 edit")
CEC_TIMEOUT = 600
RNG_SEED = 7777
Json = dict[str, object]


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _d(x: object) -> Json:
    assert isinstance(x, dict)
    return x


# ---- a: integrity ---------------------------------------------------------------------------

def check_integrity(root: Path) -> Json:
    problems: list[str] = []
    sums: dict[str, str] = {}
    for ln in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        h, _, rel = ln.partition("  ")
        sums[rel] = h
    on_disk = {p.relative_to(root).as_posix() for p in root.rglob("*")
               if p.is_file() and p.name != "SHA256SUMS"}
    problems += [f"listed but missing: {r}" for r in sorted(set(sums) - on_disk)]
    problems += [f"on disk but not listed: {r}" for r in sorted(on_disk - set(sums))]
    for rel, h in sums.items():
        if rel in on_disk and sha256_file(root / rel) != h:
            problems.append(f"sha256 mismatch: {rel}")
    man = _d(_load(root / "manifest.json"))
    prov = _d(_load(root / "answer_key" / "provenance.json"))
    circuits = man["circuits"]
    assert isinstance(circuits, list)
    for c in circuits:
        f = root / str(c["file"])
        if not f.is_file():
            problems.append(f"manifest file missing: {c['file']}")
        elif sha256_file(f) != c["sha256"] or f.stat().st_size != c["bytes"]:
            problems.append(f"manifest hash/size mismatch: {c['file']}")
    ids = {str(c["id"]) for c in circuits}
    if ids != set(prov):
        problems.append("manifest ids differ from answer_key/provenance.json ids")
    by_base: dict[str, int] = {}
    by_form: dict[str, int] = {}
    for c in circuits:
        by_base[str(c["base"])] = by_base.get(str(c["base"]), 0) + 1
    for p in prov.values():
        pd = _d(p)
        by_form[str(pd["restructuring"])] = by_form.get(str(pd["restructuring"]), 0) + 1
    counts = _d(man["counts"])
    if counts["circuits"] != len(circuits):
        problems.append("manifest counts.circuits != entries")
    if counts["by_base"] != by_base:
        problems.append("manifest counts.by_base differs from the files")
    forms_raw = man["restructurings"]
    assert isinstance(forms_raw, list)
    forms = [str(f) for f in forms_raw]
    if {k: by_form.get(k, 0) for k in forms} != counts["by_restructuring"]:
        problems.append("manifest counts.by_restructuring differs from provenance")
    return {"files": len(sums), "circuits": len(circuits), "by_base": by_base,
            "by_restructuring": by_form, "problems": problems, "ok": not problems}


# ---- b: label leak --------------------------------------------------------------------------

def net_names(text: str) -> set[str]:
    """Net names on `.names` and `.latch` lines (continuations joined)."""
    out: set[str] = set()
    for ln in text.replace("\\\n", " ").splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == ".names":
            out.update(t[1:])
        elif t[0] == ".latch" and len(t) >= 3:
            out.update(t[1:3])
            if len(t) >= 5:
                out.add(t[4])
    return out


def _leak_group(
    args: tuple[str, str, list[str], list[str], list[str], dict[str, str], bool,
                dict[str, list[str]]]
) -> tuple[list[str], int, list[str]]:
    root_s, clean_id, ids, infected_ids, extra_words, renames_inv, own_style, neutral = args
    root = Path(root_s)
    clean_text = read_blif_gz(root / "circuits" / f"{clean_id}.blif.gz")
    native = set(clean_text.split())
    pat = re.compile("|".join(re.escape(w) for w in [*WORDS, *extra_words]), re.IGNORECASE)
    style_fmt, _ = detect_style(clean_text)
    style = style_regex(style_fmt)
    clean_names = net_names(clean_text)
    leaks: list[str] = []
    native_hits = 0
    odd_names: list[str] = []
    for cid in ids:
        text = read_blif_gz(root / "circuits" / f"{cid}.blif.gz")
        for tok in set(text.split()):
            if pat.search(tok):
                if tok in native:
                    native_hits += 1
                else:
                    leaks.append(f"{cid}: token {tok}")
        if any(m in text for m in EDIT_EVENT_MARKS) and not any(m in clean_text
                                                              for m in EDIT_EVENT_MARKS):
            leaks.append(f"{cid}: odin3_edit event text")
        for ln in text.splitlines():
            if ln.startswith(".attr") or ln.lstrip().startswith("#"):
                leaks.append(f"{cid}: {ln[:60]}")
        if cid in infected_ids and renames_inv.get(cid) == "identity":
            if own_style:
                # circuits start from a rewrite with its own (ABC) names: the inserter's neutral
                # names must match the dominant style of the circuit itself
                own = style_regex(detect_style(text)[0])
                odd_names += [f"{cid}: {nm}" for nm in neutral.get(cid, []) if not own.match(nm)]
                continue
            for nm in sorted(net_names(text) - clean_names):
                if not style.match(nm):
                    odd_names.append(f"{cid}: {nm}")
    return leaks, native_hits, odd_names


def check_leak(root: Path, own_style: bool = False) -> Json:
    prov = _d(_load(root / "answer_key" / "provenance.json"))
    cat = _d(_load(root / "answer_key" / "catalogue.json"))
    renames = _d(_load(root / "answer_key" / "renames.json"))
    cats = _d(cat["trojan_catalogue"])
    extra: set[str] = set()
    for tid, t in cats.items():
        td = _d(t)
        extra.add(str(tid))
        extra.add(str(_d(td["trigger"])["kind"]))
        extra.add(str(_d(td["payload"])["kind"]))
    extra.add("trojan:")
    groups: dict[str, list[str]] = {}
    for cid, p in prov.items():
        groups.setdefault(str(_d(p)["clean_twin"]), []).append(cid)
    form = {cid: str(_d(p)["restructuring"]) for cid, p in prov.items()}
    infected = [cid for cid, p in prov.items()
                if _d(p)["role"] == "infected" or _d(p)["clean_twin"] != cid]
    tasks = [(str(root), g, sorted(ids), infected, sorted(extra), form, own_style,
              {c: sorted(_d(m)) for c, m in renames.items() if c in {i for i in ids}})
             for g, ids in sorted(groups.items())]
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(4) as pool:
        res = pool.map(_leak_group, tasks, chunksize=1)
    leaks = [x for r in res for x in r[0]]
    odd = [x for r in res for x in r[2]]
    patterns: dict[str, int] = {}
    for m in renames.values():
        for orig in _d(m).values():
            k = re.sub(r"\d+", "N", str(orig))
            patterns[k] = patterns.get(k, 0) + 1
    ids_checked = sum(len(v) for v in groups.values())
    manifest_text = (root / "manifest.json").read_text(encoding="utf-8")
    manifest_hits = sum(manifest_text.count(m) for m in EDIT_EVENT_MARKS)
    edit_leaks = [x for x in leaks if x.endswith("odin3_edit event text")]
    if manifest_hits:
        leaks.append("manifest.json: odin3_edit text")
    return {"circuits_scanned": ids_checked, "words": [*WORDS, ".attr", "#", *sorted(extra)],
            "leaks": leaks, "odd_names": odd,
            "native_hits": sum(r[1] for r in res),
            "odin3_edit_circuits": len(edit_leaks), "odin3_edit_manifest": manifest_hits,
            "inserter_name_patterns_scrubbed": dict(sorted(patterns.items())),
            "ok": not leaks and not odd}


# ---- c: function ----------------------------------------------------------------------------

def run_cec(a: Path, b: Path) -> tuple[str, int]:
    try:
        r = subprocess.run([str(r4check.equiv_check_bin()), str(a), str(b)],
                           capture_output=True, text=True, check=False, timeout=CEC_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "unproven", -1
    return {0: "equivalent", 1: "not-equivalent", 4: "unproven"}.get(r.returncode, "error"), \
        r.returncode


def _unpack(root: Path, cid: str, scratch: Path, tag: str) -> Path:
    path = scratch / f"{cid}.{tag}.blif"
    path.write_text(read_blif_gz(root / "circuits" / f"{cid}.blif.gz"), encoding="utf-8")
    return path


def _infected_task(args: tuple[str, str, Json, dict[str, str], str, int]) -> Json:
    root_s, cid, ins, ren, scratch_s, seed = args
    root, scratch = Path(root_s), Path(scratch_s)
    inv = {orig: neu for neu, orig in ren.items()}
    victim = str(ins["victim"])
    trig = inv.get("__htl_trigger", "__htl_trigger")
    tmp = inv.get(f"__htl_tmp_{victim}", f"__htl_tmp_{victim}")
    clean = _unpack(root, str(ins["clean"]), scratch, "clean")
    inf = _unpack(root, cid, scratch, "inf")
    cm = parse_single_model(clean.read_text(encoding="utf-8"))
    im = parse_single_model(inf.read_text(encoding="utf-8"))
    out: Json = {"circuit": cid, "base": ins["base"], "trigger_net": trig}
    try:
        fc = r4check.fire_check(clean, inf, cid, victim, int(str(ins["stuck"])),
                                int(str(ins["window"])), seed, None, trig, tmp)
        out["witness"], out["fires"], out["detail"] = fc.witness, fc.odin_fired, fc.detail
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"[:120]
        out["witness"], out["fires"], out["detail"] = False, False, msg
    off = scratch / f"{cid}.off.blif"
    found = find_names_block(im, trig)
    if found is None:
        out["cec"], out["cec_rc"] = "error", -2
    else:
        off.write_text(render(r4check.force_trigger_off(im, trig)), encoding="utf-8")
        out["cec"], out["cec_rc"] = run_cec(clean, off)
    del cm
    return out


def _restructured_task(args: tuple[str, str, list[str], str]) -> list[Json]:
    root_s, src, variants, scratch_s = args
    root, scratch = Path(root_s), Path(scratch_s)
    source = _unpack(root, src, scratch, "src")
    res: list[Json] = []
    for v in variants:
        var = _unpack(root, v, scratch, "var")
        verdict, rc = run_cec(source, var)
        res.append({"circuit": v, "source": src, "cec": verdict, "rc": rc})
    return res


def check_function(root: Path, scratch: Path, workers: int, seed: int) -> Json:
    scratch.mkdir(parents=True, exist_ok=True)
    prov = _d(_load(root / "answer_key" / "provenance.json"))
    ren = _d(_load(root / "answer_key" / "renames.json"))
    inf_tasks = []
    groups: dict[str, list[str]] = {}
    for cid, p in sorted(prov.items()):
        pd = _d(p)
        if pd["restructuring"] == "identity":
            if pd["role"] == "infected":
                ins = _d(pd["insert"])
                ins = {**ins, "clean": pd["clean_twin"], "base": pd["base"]}
                sd = scratch / f"w_{cid}"
                sd.mkdir(exist_ok=True)
                inf_tasks.append((str(root), cid, ins, {str(k): str(v) for k, v in
                                                       _d(ren.get(cid, {})).items()},
                                  str(sd), seed))
        else:
            groups.setdefault(str(pd["source"]), []).append(cid)
    rs_tasks = []
    for src, vs in sorted(groups.items()):
        sd = scratch / f"g_{src}"
        sd.mkdir(exist_ok=True)
        rs_tasks.append((str(root), src, sorted(vs), str(sd)))
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(workers) as pool:
        inf = pool.map(_infected_task, inf_tasks, chunksize=1)
        rs = [x for lst in pool.imap_unordered(_restructured_task, rs_tasks, chunksize=1)
              for x in lst]
    verdicts: dict[str, int] = {}
    for r in rs:
        verdicts[str(r["cec"])] = verdicts.get(str(r["cec"]), 0) + 1
    off_v: dict[str, int] = {}
    for i in inf:
        off_v[str(i["cec"])] = off_v.get(str(i["cec"]), 0) + 1
    n = len(inf)
    wit = sum(1 for i in inf if i["witness"])
    fired = sum(1 for i in inf if i["fires"])
    bad_rs = [r for r in rs if r["cec"] not in ("equivalent", "unproven")]
    unproven = sorted(str(r["circuit"]) for r in rs if r["cec"] == "unproven")
    ok = (fired == n and off_v.get("equivalent", 0) == n and not bad_rs)
    return {"infected": n, "witness": wit, "odin_fired": fired,
            "forced_off_cec": off_v, "restructured": len(rs), "restructured_cec": verdicts,
            "restructured_unproven": unproven,
            "failures": [i for i in inf if not i["fires"] or i["cec"] != "equivalent"] + bad_rs,
            "ok": ok}


# ---- d: rareness ----------------------------------------------------------------------------

def _sigma_ok(p_new: float, p_old: float, n_new: int, n_old: int, z: float = 5.0) -> bool:
    n1, n2 = max(n_new, 1), max(n_old, 1)
    pool = (p_new * n1 + p_old * n2) / (n1 + n2)
    sd = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    return abs(p_new - p_old) <= z * sd + 1e-9


def _rare_task(args: tuple[str, str, Json, Json, dict[str, str]]) -> Json:
    root_s, cid, prov, rec, ren = args
    root = Path(root_s)
    inv = {orig: neu for neu, orig in ren.items()}
    trig = inv.get("__htl_trigger", "__htl_trigger")
    ins = _d(prov["insert"])
    clean = parse_single_model(read_blif_gz(root / "circuits" / f"{prov['clean_twin']}.blif.gz"))
    inf = parse_single_model(read_blif_gz(root / "circuits" / f"{cid}.blif.gz"))
    icomp = compile_model(inf)
    out: Json = {"circuit": cid, "stratum": ins["variant"], "kind": ins["kind"]}
    if ins["kind"] == "comb":
        exact = len(icomp.data_inputs) <= 20
        if exact:
            given, nvec = exhaustive_lanes(icomp.data_inputs)
            vals = simulate_given(icomp, given, nvec)
        else:
            nvec = 1 << 20
            vals = simulate_comb(icomp, nvec, RNG_SEED)
        p_new = vals[trig].bit_count() / nvec
        p_old = float(str(rec["p"]))
        ok = abs(p_new - p_old) <= 1e-12 if exact else _sigma_ok(p_new, p_old, nvec, nvec)
        out.update({"p_new": p_new, "p_manifest": p_old, "exact": exact, "ok": ok})
    else:
        lanes = int(str(rec["seq_lanes"]))
        fixed = reset_inputs(clean)
        curves = simulate_seq(icomp, lanes, 1024, RNG_SEED, [trig], fixed)[trig]
        cmp_ = {}
        ok = True
        for n, vals_ in _d(rec["p_fire_within"]).items():
            assert isinstance(vals_, list)
            pn = curves[int(n) - 1] / lanes
            good = _sigma_ok(pn, float(vals_[0]), lanes, lanes)
            ok = ok and good
            cmp_[n] = {"new": pn, "manifest": vals_[0], "ok": good}
        out.update({"lanes": lanes, "within": cmp_, "ok": ok})
    return out


def pick_sample(strata: dict[str, list[str]], seed: int, frac: float = 0.10) -> list[str]:
    rng = random.Random(seed)
    pick: list[str] = []
    for _s, ids in sorted(strata.items()):
        k = max(1, math.ceil(frac * len(ids)))
        pick += rng.sample(sorted(ids), k)
    return sorted(pick)


def check_rareness(root: Path, workers: int, seed: int) -> Json:
    prov = _d(_load(root / "answer_key" / "provenance.json"))
    ren = _d(_load(root / "answer_key" / "renames.json"))
    raw = _load(root / "answer_key" / "rareness.json")
    assert isinstance(raw, list)
    recs = {str(_d(r)["circuit"]): _d(r) for r in raw}
    strata: dict[str, list[str]] = {}
    for cid, p in prov.items():
        pd = _d(p)
        if pd["restructuring"] == "identity" and pd["role"] == "infected":
            strata.setdefault(str(_d(pd["insert"])["variant"]), []).append(cid)
    sample = pick_sample(strata, seed)
    tasks = [(str(root), c, _d(prov[c]), recs[c],
              {str(k): str(v) for k, v in _d(ren.get(c, {})).items()}) for c in sample]
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(workers) as pool:
        res = pool.map(_rare_task, tasks, chunksize=1)
    return {"sample": sample, "strata": {k: len(v) for k, v in sorted(strata.items())},
            "results": res, "ok": all(bool(r["ok"]) for r in res)}


# ---- e: separation --------------------------------------------------------------------------

def check_separation(root: Path) -> Json:
    problems: list[str] = []
    man = _d(_load(root / "manifest.json"))
    for k in ("labels", "mix", "trojans", "trojan_catalogue", "inserts"):
        if k in man:
            problems.append(f"manifest has key {k}")
    txt = (root / "manifest.json").read_text(encoding="utf-8")
    for w in ("trojan", "trigger", "payload", "htl", "infect"):
        if w in txt.lower():
            problems.append(f"manifest text holds {w}")
    labels = _d(_load(root / "answer_key" / "labels.json"))
    mc = man["circuits"]
    assert isinstance(mc, list)
    ids = {str(_d(c)["id"]) for c in mc}
    if set(labels) != ids:
        problems.append("labels.json ids differ from manifest ids")
    prov = _d(_load(root / "answer_key" / "provenance.json"))
    for cid, p in prov.items():
        if (_d(p)["role"] == "clean") != (labels.get(cid) is None):
            problems.append(f"{cid}: role and label disagree")
    for cid in ids:
        if not re.fullmatch(r"s[cs]\d{4,}", cid):
            problems.append(f"{cid}: id is not opaque")
    for p in (root / "circuits").iterdir():
        if not re.fullmatch(r"s[cs]\d{4,}\.blif\.gz", p.name):
            problems.append(f"unexpected file in circuits/: {p.name}")
    return {"problems": problems, "clean": sum(1 for v in labels.values() if v is None),
            "infected": sum(1 for v in labels.values() if v is not None), "ok": not problems}


def verify_release(root: Path, scratch: Path, workers: int = 6, seed: int = 5) -> Json:
    rep: Json = {"release": root.name}
    rep["a_integrity"] = check_integrity(root)
    rep["e_separation"] = check_separation(root)
    rep["b_leak"] = check_leak(root)
    rep["d_rareness"] = check_rareness(root, workers, seed)
    rep["c_function"] = check_function(root, scratch, workers, seed)
    rep["ok"] = all(bool(_d(rep[k])["ok"]) for k in
                    ("a_integrity", "e_separation", "b_leak", "d_rareness", "c_function"))
    return rep
