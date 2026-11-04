"""Verify gates added after the rc3 label leaks (round 8 fix, 2026-11-01).

rc3 leaked the label in two ways: clean variants carried Odin III neutral edits (double
inverters, buffer pairs) that infected circuits did not, and ABC removed those edits so every
restructured clean variant was byte-identical to the restructured golden. Two gates catch both
from the released files alone:

(a) distinct files: no two released circuits are identical after decompression, and none is
    identical to another once the `.model` line and comment lines are ignored.
(b) style parity (local artefacts and the net-name scheme: count of new nets outside the
    dominant name pattern, largest index against the number of nets, so a name outside the common
    scheme or
    range is caught): per form, the clean and the
    infected circuits
    (golden and its own restructured forms left out) must not differ in the local artefacts of
    their `.names` cells beyond a stated bound. Test: Cochran-Mantel-Haenszel test of the 2x2
    table (clean / infected x
    artefact present) stratified by base, so a different mix of bases between the groups cannot
    produce a difference. An artefact is flagged when the Bonferroni-corrected p < ALPHA / m
    (m = tests of the release) AND the stratified difference of shares exceeds MIN_DELTA
    (practical size; with 10^5 circuits a 1 % effect is significant, and only a difference
    that a detector could use is a leak). The report also gives a trivial classifier (one style
    feature as the score, AUROC within each base, pair-weighted over bases, orientation free);
    the gate bound is AUROC <= max(AUROC_BOUND, the largest best-feature AUROC under 8
    permutations of the labels within each base + NULL_MARGIN), so a
    tiny base set is not failed by chance. The bound is exceeded only when the AUROC minus
    1.645 standard errors (Hanley-McNeil) is above it (rc5: rc4 Seq measured 0.596 and rc5 0.601
    on the same share of constant cells, a feature diluted by the Trojan's own cells; the latch
    leak of rc4 is at 1.0 with error 0). Cube-pattern classes (cells of at most 3 inputs) are
    reported (`class_info`) but do not
    gate: the Trojan's own trigger and payload cells are such cells and cannot be told apart
    from the circuit's after optimisation.
    In the identity form the answer
    key is used only to drop the inserted cells (names renamed from `__htl_*` and the cell that
    now drives a Trojan victim); restructured forms cannot be split that way, so the Trojan
    logic is in them, which is why the bound is on shares of local artefacts (cells of at most
    three inputs, buffers, inverters, constants), not on the size or the wide cells.
"""

from __future__ import annotations

import functools
import gzip
import hashlib
import json
import math
import multiprocessing
import random
import re
from collections import Counter
from pathlib import Path

Json = dict[str, object]

ALPHA = 0.01  # family-wise level of the style gate
MIN_DELTA = 0.05  # smallest stratified difference of shares that counts as a leak
AUROC_BOUND = 0.60  # best single style feature, per form
IDX_RANGE = 2.0  # largest name index above this many times the net count is out of range
Z_ONE_SIDED = 1.645  # the bound is exceeded only beyond the AUROC's error (95 %, one-sided)
NULL_MARGIN = 0.03  # allowance over the permutation null of the best feature
MAX_CLASS_INPUTS = 3  # cube-pattern classes are cells of at most this many inputs


# ---- one circuit -----------------------------------------------------------------------------

def normalised(text: str) -> str:
    """`text` without its `.model` line and its comment lines."""
    return "\n".join(ln for ln in text.splitlines()
                     if not ln.startswith(".model") and not ln.lstrip().startswith("#"))


def cells_of(text: str) -> list[tuple[list[str], str, list[str]]]:
    """(inputs, output, cover rows) of every `.names` cell."""
    cells: list[tuple[list[str], str, list[str]]] = []
    cur: tuple[list[str], str, list[str]] | None = None
    for ln in text.replace("\\\n", " ").splitlines():
        if not ln or ln[0] == "#":
            continue
        if ln[0] == ".":
            t = ln.split()
            if t[0] == ".names":
                cur = (t[1:-1], t[-1], [])
                cells.append(cur)
            else:
                cur = None
        elif cur is not None:
            cur[2].append(ln.strip())
    return cells


def _kind(ins: list[str], rows: list[str]) -> str:
    """const0 | const1 | buf | inv | other, from the cover."""
    if not ins:
        return "const1" if rows else "const0"
    if len(ins) == 1 and len(rows) == 1:
        r = rows[0].split()
        if r in (["1", "1"], ["0", "0"]):
            return "buf"
        if r in (["0", "1"], ["1", "0"]):
            return "inv"
    return "other"


def latch_features(text: str) -> Json:
    """Per-field counts of the `.latch` lines of `text` (rc5: rc4 gave the Trojan's own
    flip-flops away through the init value `0`, where every other latch had `2`).
    Keys: `latches`; `init`, `type`, `clock` (value -> count; the clock as `main` for the
    circuit's most used clock, else `other`); `dkind` (what drives D: pi, latch, buf, inv, const,
    other); `selfq` (latches whose D cone, through `.names` only, reads their own Q: the footprint
    of counters and FSMs, reported but not gated)."""
    lats: list[list[str]] = []
    cells = cells_of(text)
    kind_of = {out: _kind(ins, rows) for ins, out, rows in cells}
    for ln in text.splitlines():
        if ln.startswith(".latch "):
            w = ln.split()
            if len(w) == 6:
                lats.append(w[1:])
    qs = {w[1] for w in lats}
    ins_of = {out: ins for ins, out, _rows in cells}
    qbit = {q: 1 << i for i, q in enumerate(sorted(qs))}
    cone: dict[str, int] = {}

    def reach(net: str) -> int:
        """Bitmask of the latch outputs in the combinational fan-in cone of `net`."""
        stack = [net]
        while stack:
            n = stack[-1]
            if n in cone:
                stack.pop()
                continue
            if n in qbit:
                cone[n] = qbit[n]
                stack.pop()
                continue
            ins = ins_of.get(n, [])
            todo = [i for i in ins if i not in cone]
            if todo:
                stack.extend(todo)
                continue
            m = 0
            for i in ins:
                m |= cone[i]
            cone[n] = m
            stack.pop()
        return cone[net]

    clocks = Counter(w[3] for w in lats)
    main = clocks.most_common(1)[0][0] if clocks else ""
    init: Counter[str] = Counter()
    typ: Counter[str] = Counter()
    clk: Counter[str] = Counter()
    dkind: Counter[str] = Counter()
    selfq = 0
    for d, q, t, c, i in lats:
        init[i] += 1
        typ[t] += 1
        clk["main" if c == main else "other"] += 1
        dkind["latch" if d in qs else kind_of.get(d, "pi")] += 1
        if reach(d) & qbit[q]:
            selfq += 1
    return {"latches": len(lats), "init": dict(init), "type": dict(typ), "clock": dict(clk),
            "dkind": dict(dkind), "selfq": selfq}


def _cover_fields(n: Counter[str], ins: list[str], rows: list[str]) -> None:
    """Per-cell fields of the cover not seen by the kind test (rc5): `cov0` off-set cover (output
    column 0), `dc` a don't-care in a cube, `rows_unsorted` cubes not in ascending order,
    `in_unsorted` input nets not in ascending order of their `n<digits>` index."""
    if not ins:
        return
    cubes = [r.split()[0] for r in rows if r.split()]
    if any(r.split()[-1] == "0" for r in rows if r.split()):
        n["cov0"] += 1
    if any("-" in c for c in cubes):
        n["dc"] += 1
    if len(cubes) > 1 and cubes != sorted(cubes):
        n["rows_unsorted"] += 1
    idx = [int(x[1:]) for x in ins if re.fullmatch(r"n\d+", x)]
    if len(idx) > 1 and idx != sorted(idx):
        n["in_unsorted"] += 1


def style_features(text: str, drop: frozenset[str] = frozenset()) -> Json:
    """Counts of the local artefacts of `text`; cells whose output is in `drop` are ignored.
    A buffer or inverter that drives a primary output is not an artefact of the style but of the
    interface (a Trojan's payload replaces the driver of its victim output), so it is counted as
    `po_buf` / `po_inv` and kept out of the artefact counts."""
    outs: set[str] = set()
    for ln in text.splitlines():
        if ln.startswith(".outputs"):
            outs.update(ln.split()[1:])
    cells = [c for c in cells_of(text) if c[1] not in drop]
    kind_of: dict[str, str] = {}
    for ins, out, rows in cells:
        kind_of[out] = _kind(ins, rows)
    n = Counter[str]()
    hist = Counter[str]()
    for ins, out, rows in cells:
        k = kind_of[out]
        n["cells"] += 1
        if k in ("buf", "inv"):
            if out in outs:
                n["po_" + k] += 1
            else:
                n[k] += 1
                if kind_of.get(ins[0]) == k:
                    n["dbl_" + k] += 1
        elif k.startswith("const"):
            n["const"] += 1
        _cover_fields(n, ins, rows)
        if 0 < len(ins) <= MAX_CLASS_INPUTS:
            hist[f"{len(ins)}:" + "|".join(sorted(rows))] += 1
    return {"n": dict(n), "hist": dict(hist), "lat": latch_features(text)}


def name_features(text: str, golden: frozenset[str] = frozenset()) -> Json:
    """Net-name scheme of a circuit: the share of nets whose name has the circuit's dominant
    pattern (digits as N), and the largest index of those names against the number of nets.
    Inserted nets are included on purpose (no cell is dropped): a name-style detector sees
    them. `foreign` counts the nets that are not the golden's own and do not fit the dominant
    pattern
    (a count, not a share, so the size of the insertion does not move it)."""
    from lemanruss.htl.relverify import net_names

    names = net_names(text)
    pats = Counter(re.sub(r"\d+", "N", nm) for nm in names)
    if not names or not pats:
        return {"fit": 1.0, "idx": 0.0, "nets": 0}
    dom, _n = pats.most_common(1)[0]
    rx = re.compile("^" + re.escape(dom).replace("N", r"(\d+)") + "$")
    nums = [int(m.group(1)) for nm in names if (m := rx.match(nm)) and m.groups()]
    new = [nm for nm in names if nm not in golden]
    foreign = sum(1 for nm in new if not rx.match(nm))
    return {"fit": pats[dom] / len(names), "foreign": foreign,
            "idx": (max(nums) / len(names)) if nums else 0.0, "nets": len(names)}


@functools.lru_cache(maxsize=8)
def _golden_names(path_s: str) -> frozenset[str]:
    from lemanruss.htl.relverify import net_names

    with gzip.open(path_s, "rt", encoding="utf-8") as fh:
        return frozenset(net_names(fh.read()))


DIRECTIVES = {".model", ".inputs", ".outputs", ".names", ".latch", ".end"}
LATCH_RX = re.compile(r"^\.latch \S+ \S+ (re|fe|ah|al|as) \S+ [0-3]$")
FOREIGN_CHARS = ("$", "\\", "@", "__htl", "odin", "yosys")


def latch_convention(text: str) -> list[str]:
    """The distinct `type/clock/init` of the `.latch` lines of `text`, sorted."""
    return sorted({"/".join(w[3:6]) for w in (ln.split() for ln in text.splitlines()
                                              if ln.startswith(".latch ")) if len(w) == 6})


def provenance_problems(text: str, golden: bool) -> list[str]:
    """What in `text` could only come from an Odin III write or from the inserter: a directive
    outside the plain set, a comment, a foreign character or word, a `.latch` in another format,
    a `.model` other than `top`, and (not for the golden) an internal net not named `n<digits>`."""
    out: list[str] = []
    ports: set[str] = set()
    clocks: set[str] = set()
    names: list[str] = []
    for ln in text.splitlines():
        if not ln.strip():
            continue
        if ln.lstrip().startswith("#"):
            out.append("comment line")
            continue
        w = ln.split()
        if w[0].startswith("."):
            if w[0] not in DIRECTIVES:
                out.append(f"directive {w[0]}")
            if w[0] == ".model" and w[1:] != ["top"]:
                out.append(f".model {' '.join(w[1:])}")
            if w[0] in (".inputs", ".outputs"):
                ports.update(w[1:])
            if w[0] == ".names":
                names += w[1:]
            if w[0] == ".latch":
                if not LATCH_RX.match(ln):
                    out.append(f"latch format: {ln[:40]}")
                else:
                    clocks.add(w[4])
                    names += w[1:3]
    conv = latch_convention(text)
    if len(conv) > 1:
        out.append(f"latch conventions mixed: {', '.join(conv)}")
    if not golden:
        out += [f"net name {n}" for n in dict.fromkeys(names)
                if n not in ports and n not in clocks and not re.fullmatch(r"n\d+", n)][:3]
    for tok in FOREIGN_CHARS:
        if tok in text:
            out.append(f"foreign text {tok!r}")
    return out[:6]


def scan_file(args: tuple[str, str, list[str], str, bool]) -> Json:
    """Hashes and style features of one released file; `drop` lists output nets to ignore."""
    path_s, cid, drop, golden_s, is_golden = args
    with gzip.open(path_s, "rt", encoding="utf-8") as fh:
        text = fh.read()
    out: Json = {"id": cid,
                 "sha": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                 "norm": hashlib.sha256(normalised(text).encode("utf-8")).hexdigest()}
    out.update(style_features(text, frozenset(drop)))
    out["names"] = name_features(text, _golden_names(golden_s))
    out["prov"] = provenance_problems(text, is_golden)
    out["lat_conv"] = latch_convention(text)
    return out


def inserted_outputs(prov: Json, ren: Json, cid: str) -> list[str]:
    """Nets whose driving cell the inserter made or took over (identity infected circuits)."""
    drop = [new for new, orig in _d(ren.get(cid, {})).items() if str(orig).startswith("__htl_")]
    ins = prov.get("insert")
    if isinstance(ins, dict):
        for t in ins.get("trojans") or []:
            if t.get("victim"):
                drop.append(str(t["victim"]))
    return drop


def _d(x: object) -> Json:
    assert isinstance(x, dict)
    return x


def scan_release(
    root: Path, workers: int = 4, bases: set[str] | None = None
) -> tuple[dict[str, Json], Json, Json]:
    """Scans every released circuit (optionally only the given bases). Returns the records by id,
    provenance and labels."""
    key = root / "answer_key"
    prov = _d(json.loads((key / "provenance.json").read_text(encoding="utf-8")))
    labels = _d(json.loads((key / "labels.json").read_text(encoding="utf-8")))
    ren = _d(json.loads((key / "renames.json").read_text(encoding="utf-8")))
    jobs = []
    for cid in sorted(prov):
        p = _d(prov[cid])
        if bases is not None and p["base"] not in bases:
            continue
        drop = (inserted_outputs(p, ren, cid)
                if p["restructuring"] == "identity" and p["role"] == "infected" else [])
        jobs.append((str(root / "circuits" / f"{cid}.blif.gz"), cid, drop,
                     str(root / "circuits" / f"{p['clean_twin']}.blif.gz"), p["clean_twin"] == cid))
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(workers) as pool:
        recs = list(pool.imap(scan_file, jobs, chunksize=16))
    return {str(r["id"]): r for r in recs}, prov, labels


# ---- gate (a): distinct files ----------------------------------------------------------------

def gate_distinct(recs: dict[str, Json], prov: Json) -> Json:
    """No two files identical (exact), none identical ignoring `.model` and comments."""
    out: Json = {}
    problems: list[str] = []
    for field, what in (("sha", "identical"), ("norm", "identical ignoring .model and comments")):
        groups: dict[str, list[str]] = {}
        for cid, r in recs.items():
            groups.setdefault(str(r[field]), []).append(cid)
        dups = [sorted(g) for g in groups.values() if len(g) > 1]
        across = [g for g in dups if len({str(_d(prov[c])["role"]) for c in g}) > 1]
        out[field] = {"groups": len(dups), "files_in_groups": sum(len(g) for g in dups),
                      "groups_across_labels": len(across), "examples": dups[:5]}
        if dups:
            problems.append(f"{len(dups)} groups of files {what} ({len(across)} across labels)")
    out["problems"] = problems
    out["ok"] = not problems
    return out


# ---- gate (b): style parity ------------------------------------------------------------------

def _p_two_sided(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2))


def cmh(strata: list[tuple[int, int, int, int]]) -> tuple[float, float, float]:
    """Cochran-Mantel-Haenszel over strata (clean with, clean without, infected with, infected
    without). Returns (z, stratified share difference infected - clean, p)."""
    num = var = 0.0
    dnum = dden = 0.0
    for a, b, c, d in strata:
        n_c, n_i, k, n = a + b, c + d, a + c, a + b + c + d
        if n_c == 0 or n_i == 0:
            continue
        num += c - n_i * k / n
        if n > 1:
            var += n_i * n_c * k * (n - k) / (n * n * (n - 1))
        w = n_c * n_i / n
        dnum += w * (c / n_i - a / n_c)
        dden += w
    z = num / math.sqrt(var) if var > 0 else 0.0
    return z, (dnum / dden if dden else 0.0), _p_two_sided(z)


def _auroc(pos: list[float], neg: list[float]) -> float:
    """P(score_pos > score_neg) + half the ties, by mid-ranks."""
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks_pos = 0.0
    i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        mid = (i + j + 1) / 2
        ranks_pos += mid * sum(1 for _v, lab in allv[i:j] if lab)
        i = j
    n_p, n_n = len(pos), len(neg)
    return (ranks_pos - n_p * (n_p + 1) / 2) / (n_p * n_n)


ARTEFACTS = ("dbl_inv", "dbl_buf", "buf", "inv", "const", "cov0", "dc", "rows_unsorted",
             "in_unsorted")


def _binary_features(f: Json, classes: bool) -> dict[str, int]:
    n = _d(f["n"])
    out = {k: int(int(str(n.get(k, 0))) > 0) for k in ARTEFACTS}
    lat = _d(f["lat"])
    if int(str(lat["latches"])) > 0:
        for grp in ("init", "type", "clock", "dkind"):
            for v in _d(lat[grp]):
                out[f"lat_{grp}_{v}_any"] = 1
        out["info lat_selfq_any"] = int(int(str(lat["selfq"])) > 0)
    if classes:
        for cls in _d(f["hist"]):
            out["cls " + cls] = 1
    if classes:  # names: identity form only (ABC renames every net of a restructured form,
        # and its numbering depends on the whole circuit including the Trojan's logic)
        nm = _d(f["names"])
        out["name_foreign_any"] = int(int(str(nm["foreign"])) > 0)
        out["name_idx_out_of_range"] = int(float(str(nm["idx"])) > IDX_RANGE)
    return out


def _fractions(f: Json, classes: bool) -> dict[str, float]:
    n = _d(f["n"])
    cells = max(int(str(n.get("cells", 0))), 1)
    out = {k + "/cells": int(str(n.get(k, 0))) / cells for k in ARTEFACTS}
    lat = _d(f["lat"])
    nl = int(str(lat["latches"]))
    if nl > 0:
        for grp in ("init", "type", "clock", "dkind"):
            for val, cnt in _d(lat[grp]).items():
                out[f"lat_{grp}_{val}/latches"] = int(str(cnt)) / nl
        out["info lat_selfq/latches"] = int(str(lat["selfq"])) / nl
    if classes:
        for cls, v in _d(f["hist"]).items():
            out["cls " + cls + "/cells"] = int(str(v)) / cells
    if classes:
        nm = _d(f["names"])
        out["name_foreign"] = float(str(nm["foreign"]))
    return out


def best_auroc(feats: list[tuple[str, str, dict[str, float]]]) -> tuple[str, float]:
    """The single feature with the highest orientation-free AUROC (per base, pair-weighted)."""
    bases = sorted({b for b, _r, _f in feats})
    fnames = sorted({k for _b, _r, fr in feats for k in fr})
    best = ("", 0.5)
    for name in fnames:
        tot = wsum = 0.0
        for base in bases:
            pos = [fr.get(name, 0.0) for bb, role, fr in feats if bb == base and role != "clean"]
            neg = [fr.get(name, 0.0) for bb, role, fr in feats if bb == base and role == "clean"]
            if pos and neg:
                npair = len(pos) * len(neg)
                tot += npair * _auroc(pos, neg)
                wsum += npair
        if wsum:
            au = tot / wsum
            au = max(au, 1 - au)
            if au > best[1]:
                best = (name, au)
    return best


def null_auroc(feats: list[tuple[str, str, dict[str, float]]], perms: int, seed: int) -> float:
    """Largest best-feature AUROC over `perms` permutations of the labels within each base: what
    chance alone gives with this many circuits and features."""
    rng = random.Random(seed)
    by_base: dict[str, list[int]] = {}
    for i, (b, _r, _f) in enumerate(feats):
        by_base.setdefault(b, []).append(i)
    top = 0.5
    for _ in range(perms):
        roles = [r for _b, r, _f in feats]
        for idx in by_base.values():
            lab = [feats[i][1] for i in idx]
            rng.shuffle(lab)
            for i, r in zip(idx, lab, strict=True):
                roles[i] = r
        shuffled = [(feats[i][0], roles[i], feats[i][2]) for i in range(len(feats))]
        top = max(top, best_auroc(shuffled)[1])
    return top


def auroc_se(auc: float, n_pos: int, n_neg: int) -> float:
    """Hanley-McNeil standard error of an AUROC estimate."""
    if n_pos < 2 or n_neg < 2:
        return 0.0
    q1, q2 = auc / (2 - auc), 2 * auc * auc / (1 + auc)
    var = (auc * (1 - auc) + (n_pos - 1) * (q1 - auc * auc)
           + (n_neg - 1) * (q2 - auc * auc)) / (n_pos * n_neg)
    return math.sqrt(max(var, 0.0))


def style_parity(
    recs: dict[str, Json], prov: Json, bonferroni_m: int | None = None, perms: int = 8
) -> Json:
    """Per form: CMH tests per artefact and the AUROC of the best single style feature."""
    golden = {str(_d(p)["clean_twin"]) for p in prov.values()}
    rows: dict[str, list[tuple[str, str, Json]]] = {}
    for cid, r in recs.items():
        p = _d(prov[cid])
        if cid in golden or str(p["source"]) in golden:
            continue
        rows.setdefault(str(p["restructuring"]), []).append(
            (str(p.get("stratum", p["base"])), str(p["role"]), r))
    tests: list[Json] = []
    aurocs: dict[str, Json] = {}
    for form, items in sorted(rows.items()):
        classes = form == "identity"  # the Trojan logic is in the restructured forms
        feats = [(b, role, _binary_features(r, classes), _fractions(r, classes))
                 for b, role, r in items]
        names = sorted({k for _b, _r, bf, _f in feats for k in bf})
        bases = sorted({b for b, _r, _bf, _f in feats})
        for name in names:
            strata = []
            for base in bases:
                a = b_ = c = d = 0
                for bb, role, bf, _fr in feats:
                    if bb != base:
                        continue
                    has = bf.get(name, 0)
                    if role == "clean":
                        a, b_ = a + has, b_ + 1 - has
                    else:
                        c, d = c + has, d + 1 - has
                strata.append((a, b_, c, d))
            z, delta, pv = cmh(strata)
            if z != 0.0 or delta != 0.0:
                tests.append({"form": form, "feature": name, "z": z, "delta": delta, "p": pv,
                              "strata": len(strata), "info": name.startswith(("cls ", "info "))})
        fl = [(b, role, {k: v for k, v in fr.items() if not k.startswith(("cls ", "info "))})
              for b, role, _bf, fr in feats]
        best = best_auroc(fl)
        null = null_auroc(fl, perms, 17) if best[1] > AUROC_BOUND else 0.5
        aurocs[form] = {"best_feature": best[0], "auroc": best[1], "null_max": null,
                        "clean": sum(1 for _b, role, _r in items if role == "clean"),
                        "infected": sum(1 for _b, role, _r in items if role != "clean")}
        aurocs[form]["se"] = auroc_se(best[1], int(str(aurocs[form]["infected"])),
                                      int(str(aurocs[form]["clean"])))
    m = bonferroni_m or max(len(tests), 1)
    threshold = ALPHA / m
    over = [t for t in tests if float(str(t["p"])) < threshold
            and abs(float(str(t["delta"]))) > MIN_DELTA]
    flagged = [t for t in over if not t["info"]]
    class_info = sorted((t for t in over if t["info"]), key=lambda t: -abs(float(str(t["delta"]))))
    bad_auc = {f: a for f, a in aurocs.items()
               if float(str(a["auroc"])) - Z_ONE_SIDED * float(str(a["se"]))
               > max(AUROC_BOUND, float(str(a["null_max"])) + NULL_MARGIN)}
    problems = [f"{len(flagged)} artefact tests differ beyond the bound"] if flagged else []
    problems += [f"form {f}: best style feature AUROC {float(str(a['auroc'])):.3f} "
                 f"(se {float(str(a['se'])):.4f}) > max({AUROC_BOUND}, permutation null "
                 f"{float(str(a['null_max'])):.3f} + {NULL_MARGIN})"
                 for f, a in sorted(bad_auc.items())]
    flagged.sort(key=lambda t: -abs(float(str(t["delta"]))))
    idx_means: dict[str, float] = {}
    for role_name, want in (("clean", True), ("infected", False)):
        vals = [float(str(_d(r["names"])["idx"])) for cid, r in recs.items()
                if (str(_d(prov[cid])["role"]) == "clean") == want
                and cid not in golden and _d(prov[cid])["restructuring"] == "identity"]
        idx_means[role_name] = sum(vals) / len(vals) if vals else 0.0
    return {"name_idx_mean": idx_means, "tests": len(tests),
            "alpha": ALPHA, "bonferroni_threshold": threshold,
            "min_delta": MIN_DELTA, "auroc_bound": AUROC_BOUND, "flagged": flagged[:40],
            "n_flagged": len(flagged), "class_info_n": len(class_info),
            "class_info": class_info[:10], "auroc_by_form": aurocs, "problems": problems,
            "ok": not problems}


def gate_provenance(recs: dict[str, Json], prov: Json | None = None) -> Json:
    """No file shows how it was made: see `provenance_problems`. With `prov`, also one latch
    convention (type, clock, init) across all files of a base."""
    bad = {cid: r["prov"] for cid, r in recs.items() if r["prov"]}
    problems = [f"{len(bad)} files with provenance traces"] if bad else []
    mixed: dict[str, list[str]] = {}
    if prov is not None:
        per: dict[str, set[str]] = {}
        for cid, r in recs.items():
            per.setdefault(str(_d(prov[cid])["base"]), set()).update(
                str(x) for x in _d_list(r["lat_conv"]))
        mixed = {b: sorted(v) for b, v in per.items() if len(v) > 1}
        if mixed:
            problems.append(f"{len(mixed)} bases with more than one latch convention")
    return {"files_with_traces": len(bad), "examples": dict(list(bad.items())[:5]),
            "bases_mixed_latch_convention": dict(list(mixed.items())[:5]),
            "problems": problems, "ok": not problems}


def _d_list(x: object) -> list[object]:
    assert isinstance(x, list)
    return x


def verify_gates(root: Path, workers: int = 4, bases: set[str] | None = None) -> Json:
    recs, prov, _labels = scan_release(root, workers, bases)
    return {"f_distinct": gate_distinct(recs, prov), "g_style": style_parity(recs, prov),
            "h_provenance": gate_provenance(recs, prov)}
