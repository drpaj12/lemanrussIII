"""Release packaging (spec section 10): the label scrub, the release directory, manifest,
SHA256SUMS and DATASHEET. `lemanruss.htl.relverify` re-reads the result from disk.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import random
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

INSERTER_TOKEN = re.compile(r"\S*__htl_\S*")
# name styles of the internal nets of the clean circuits: (format, regex with the number group)
STYLES: list[tuple[str, str]] = [
    ("[{}]", r"\[(\d+)\]"),
    ("$n{}", r"\$n(\d+)"),
    ("new_n{}", r"new_n(\d+)"),
    ("n_n{}", r"n_n(\d+)"),
    ("n{}", r"n(\d+)"),
]
FORMS = ("identity", "strash", "balance", "rewrite", "refactor", "resyn", "resyn2", "compress2",
         "dc2", "dc2x2", "lut4", "lut6", "lut6mfs", "resyn2a", "resyn3", "resyn2rs", "compress",
         "resub", "lut5")


def gz_bytes(text: str) -> bytes:
    """Deterministic gzip of `text` (zero timestamp, no file name)."""
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as fh:
        fh.write(text.encode("utf-8"))
    return buf.getvalue()


def strip_comments(text: str) -> tuple[str, int]:
    """`text` without its `#` comment lines (ABC writes a banner with a time stamp), and how
    many lines were dropped."""
    keep = [ln for ln in text.splitlines(keepends=True) if not ln.lstrip().startswith("#")]
    return "".join(keep), text.count("\n") - sum(k.count("\n") for k in keep)


def read_blif_gz(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_style(text: str) -> tuple[str, int]:
    """The name style most used among the internal nets of `text` (inserter names ignored) and
    the largest number seen in it."""
    toks = {t for t in text.split() if "__htl_" not in t}
    best, best_n, best_max = "n{}", 0, 0
    for fmt, rx in STYLES:
        pat = re.compile(rf"^{rx}$")
        nums = [int(m.group(1)) for t in toks if (m := pat.match(t))]
        if len(nums) > best_n:
            best, best_n, best_max = fmt, len(nums), max(nums)
    return best, best_max


def style_regex(fmt: str) -> re.Pattern[str]:
    for f, rx in STYLES:
        if f == fmt:
            return re.compile(rf"^{rx}$")
    raise ValueError(fmt)


def scrub_group(
    texts: dict[str, str], style_text: str, key: str, seed: int
) -> tuple[dict[str, str], dict[str, str]]:
    """Renames every inserter token in `texts` (the source circuit and all its restructured
    variants) to a neutral name in the style of `style_text`; one map for the whole group.
    Returns (new texts, map original -> neutral)."""
    tokens = sorted({m.group(0) for t in texts.values() for m in INSERTER_TOKEN.finditer(t)})
    if not tokens:
        return dict(texts), {}
    fmt, top = detect_style(style_text)
    taken = {t for text in texts.values() for t in text.split()}
    rng = random.Random(f"{seed}:{key}")
    # Inserted nets are named like the circuit's own nets in scheme and range. ABC and Odin
    # number with gaps, so the new names take free indices from the circuit's own range extended
    # by the inserted count times the circuit's gap ratio (largest index / numbered nets); the
    # largest index against the net count then stays where it was without the insertion.
    used = {int(m.group(1)) for t in taken if (m := re.match(rf"^{dict(STYLES)[fmt]}$", t))}
    ratio = max(1.0, top / max(len(used), 1))
    upper = top + int(len(tokens) * ratio) + 1
    pool = [n for n in range(1, upper + 1) if n not in used]
    rng.shuffle(pool)
    pool += range(upper + 1, upper + 1 + 4 * len(tokens) + 8)
    mapping: dict[str, str] = {}
    it = iter(pool)
    for tok in tokens:
        for n in it:
            name = fmt.format(n)
            if name not in taken:
                taken.add(name)
                mapping[tok] = name
                break
        else:
            raise RuntimeError(f"name pool exhausted for {key}")
    out = {k: INSERTER_TOKEN.sub(lambda m: mapping[m.group(0)], t) for k, t in texts.items()}
    return out, mapping


def unscrub(text: str, mapping: dict[str, str]) -> str:
    """Inverse of the scrub; `mapping` is original -> neutral."""
    inv = {v: k for k, v in mapping.items()}
    if not inv:
        return text
    alt = "|".join(re.escape(n) for n in sorted(inv, key=len, reverse=True))
    rx = re.compile(rf"(?<!\S)(?:{alt})(?!\S)")
    return rx.sub(lambda m: inv[m.group(0)], text)


def _json(obj: object) -> str:
    return json.dumps(obj, indent=1, sort_keys=True) + "\n"


@dataclass
class Tools:
    odin3_build_pin: str
    odin3_checkout: str
    abc: str


def licence_lines(licences: Path | None, bases: list[str], family: str) -> list[str]:
    """Licence of each base group as Mimir records it (never inferred)."""
    rules = tomllib.loads(licences.read_text(encoding="utf-8"))["rule"] if licences else []

    def rule(slug: str) -> str:
        import fnmatch

        for r in rules:
            if any(fnmatch.fnmatchcase(slug, m) for m in r["match"]):
                return f"{r['licence']} (Mimir rule {r['id']})"
        return "not recorded in Mimir"

    iscas85 = [b for b in bases if re.fullmatch(r"C\d+", b)]
    mcnc = [b for b in bases if b in {"alu4", "apex2", "apex4", "cordic", "ex5p", "misex3",
                                        "pdc", "spla", "t481"}]
    ve = [b for b in bases if b.startswith("ve_")]
    iscas89 = [b for b in bases if re.fullmatch(r"s\d+", b)]
    itc = [b for b in bases if re.fullmatch(r"b\d\d", b)]
    vtr = [b for b in bases
           if b in {"diffeq1", "diffeq2", "sha", "mkPktMerge", "mkSMAdapter4B"}]
    out = []
    if iscas85:
        out.append(f"- ISCAS-85 ({len(iscas85)}: {', '.join(iscas85)}): licence unread. Mimir "
                   "`licences.toml` has no ISCAS rule and the ISCAS licence has not been read.")
    if mcnc:
        out.append(f"- MCNC ({len(mcnc)}: {', '.join(mcnc)}): "
                   f"{rule('mcnc20/' + mcnc[0])}. The MCNC licence itself has not been read.")
    if ve:
        out.append(f"- VerilogEval gate netlists ({len(ve)}: {', '.join(ve)}): "
                   f"{rule('loki/x/' + ve[0])}.")
    if iscas89:
        out.append(f"- ISCAS-89 ({len(iscas89)}: {', '.join(iscas89)}): "
                   "licence unread (the ISCAS licence has not been read).")
    if itc:
        out.append(f"- ITC-99 ({len(itc)}: {itc[0]} to {itc[-1]}): not in Mimir "
                   "`licences.toml`. Source: ccsl-uaegean/ITC99-RTL-Verilog, a vhd2vl "
                   "conversion of the Politecnico di Torino ITC'99 VHDL; the repository's LICENSE "
                   "says GPL-3.0 (spec section 8); the licence of the original VHDL has "
                   "not been read.")
    for b in vtr:
        out.append(f"- VTR Verilog `{b}`: {rule('norns/' + b)}.")
    if family == "Seeker-Comb" or family == "Seeker-Seq":
        out.append("- The infected circuits are derivatives of these bases; each base's own "
                   "licence applies to its derivative.")
    return out


def datasheet(
    family: str, name: str, tools: Tools, counts: dict[str, object], bases: list[str],
    rareness_md: str, licences: Path | None, unproven: list[str], failures: int, lineage: str,
    version: str = "2.0-rc1", excluded: dict[str, str] | None = None, design_md: str = "",
) -> str:
    comb = family == "Seeker-Comb"
    by_base = counts["by_base"]
    assert isinstance(by_base, dict)
    lines = [
        f"# {name} datasheet",
        "",
        f"Family: {family}. Version {version} (release candidate; the final v2.0 follows after "
        "later rounds add the remaining bases and Seeker-Proc). Produced by "
        "Leman Russ III (Yggdrasil III).",
        "",
        "Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to "
        "detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.",
        "",
        "## Lineage",
        "",
        lineage,
        "",
        "## Contents",
        "",
        f"- circuits: {counts['circuits']} in `circuits/<id>.blif.gz` (gzip, zero timestamp), "
        f"{counts['clean']} clean and {counts['infected']} infected, opaque ids.",
        f"- bases: {len(bases)}; each has one clean circuit and its infected circuits.",
        f"- restructurings: identity plus 18 ABC restructurings of every circuit, "
        f"{counts['forms']} forms, every one checked ABC-equivalent to its source "
        f"({counts['equiv_note']}).",
        f"- variants that could not be built: {failures} (`answer_key/failures.json`; a "
        "band no rare net could reach).",
        "- answer key: `answer_key/` (labels, provenance, renames, rareness, and for the "
        "infected identity circuits `edit_events/<id>.edit.blif.gz`: the circuit written with "
        "Odin III edit events, `write_blif --edit-tags`, which mark every inserted or moved "
        "cell); a detector must not read it. Clean circuits carry no label and infected "
        "circuits carry no label.",
        "",
        "Circuits per base (all forms):",
        "",
        ", ".join(f"{b} {n}" for b, n in sorted(by_base.items())),
        "",
        *([design_md, ""] if design_md else []),
        "## Rareness bands",
        "",
        ("Seeker-Comb: the trigger is an AND of rare-valued nets grown until the joint "
         "activation probability per random vector falls in a target band: p < 1e-2, p < 1e-3, "
         "p < 1e-4 (estimated on 2^20 vectors, exact when the design has at most 20 inputs)."
         if comb else
         "Seeker-Seq: counter (time bomb) and FSM-pattern triggers, three speed bands each "
         "(fast, mid, slow) defined by P(trigger high within 1024 cycles): fast 0.5-1, mid "
         "0.05-0.5, slow 0.003-0.05. P(fire within N) for N = 16, 64, 256, 1024 is in "
         "`answer_key/rareness.json`. Odin III's sequential SCOAP underestimates time-bomb "
         "rareness, so P(fire within N) is the primary measure."),
        "",
        rareness_md,
        "",
        *(["## Built but not released", "",
           *[f"- {b}: {why}" for b, why in sorted((excluded or {}).items())], ""]
          if excluded else []),
        "## Restructurings",
        "",
        "identity, strash, balance, rewrite, refactor, resyn, resyn2, compress2, dc2, dc2x2, "
        "lut4, lut6, lut6mfs, resyn2a, resyn3, resyn2rs, compress, resub, lut5 (ABC standard "
        "scripts and LUT mappings; Seeker1's own list of 18 was not read, so this is the count, "
        "not the same list).",
        "",
        "Equivalence: " + ("all restructured circuits were proven equivalent to their source." if
                           not unproven else
                           "all but " + str(len(unproven)) + " restructured circuit(s) were "
                           "proven equivalent to their source by ABC; the unproven one: "
                           + ", ".join(unproven) + " (ABC equivalence timeout, 600 s; it is not "
                           "known to be non-equivalent)."),
        "",
        "## Bases and licences",
        "",
        *licence_lines(licences, bases, family),
        "",
        "## Tools",
        "",
        f"- Odin III (build of the circuits): {tools.odin3_build_pin}; checkout used for "
        f"`lemanruss verify`: {tools.odin3_checkout}.",
        f"- ABC: {tools.abc}.",
        "",
        "## Names",
        "",
        "Every net the inserter added is renamed to a neutral internal name in the style of the "
        "clean circuit (spec section 10.2); `answer_key/renames.json` maps them back.",
        "",
        "## Fetch and check",
        "",
        "Unpack the circuits and answer-key archives into one directory, then "
        "`sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.",
        "",
    ]
    return "\n".join(lines)


def build_release(
    root: Path, out: Path, family: str, short: str, seed: int, tools: Tools,
    licences: Path | None, version: str = "2.0-rc1", excluded: dict[str, str] | None = None,
    n200: bool = False,
) -> dict[str, object]:
    """Packages the family build under `root` (read only) into the release directory `out`
    (created; must be empty or absent). `excluded` maps a base to the reason it is built but not
    released (for example: its restructurings cannot be equivalence-checked); nothing of such a
    base, clean or infected, enters the release or its answer key."""
    excluded = excluded or {}
    key = root / "answer_key"
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    labels: dict[str, str | None] = json.loads((key / "labels.json").read_text(encoding="utf-8"))
    inserts = json.loads((key / "inserts.json").read_text(encoding="utf-8"))
    restr = {r["id"]: r for r in json.loads((key / "restructured.json").read_text(encoding="utf-8"))
             if r["verdict"] != "abc-failed" and not r.get("duplicate_of")}
    restr = {i: r for i, r in restr.items()
             if man_base(man, str(r["source"])) not in excluded}
    out_c = out / "circuits"
    out_k = out / "answer_key"
    out_c.mkdir(parents=True, exist_ok=False)
    out_k.mkdir()

    all_entries = {c["id"]: c for c in man["circuits"]}
    entries = {i: c for i, c in all_entries.items() if c["base"] not in excluded}
    identity = sorted(i for i, c in entries.items() if c["file"].startswith("circuits/"))
    variants: dict[str, list[str]] = {i: [] for i in identity}
    for rid, r in sorted(restr.items()):
        if rid in entries:
            variants[str(r["source"])].append(rid)
    if len(entries) != sum(1 + len(v) for v in variants.values()):
        raise RuntimeError("manifest circuits and restructured.json disagree")

    renames: dict[str, dict[str, str]] = {}
    files: dict[str, bytes] = {}
    dropped = 0
    for src in identity:
        texts = {src: (root / entries[src]["file"]).read_text(encoding="utf-8")}
        for v in variants[src]:
            texts[v], n_dropped = strip_comments(read_blif_gz(root / entries[v]["file"]))
            dropped += n_dropped
        new, mapping = scrub_group(texts, texts[src], src, seed)
        for cid, text in new.items():
            if "__htl_" in text:
                raise RuntimeError(f"{cid}: inserter token left after scrub")
            if unscrub(text, mapping) != texts[cid]:
                raise RuntimeError(f"{cid}: scrub is not reversible")
            files[cid] = gz_bytes(text)
            if mapping and INSERTER_TOKEN.search(texts[cid]):
                renames[cid] = {neutral: orig for orig, neutral in mapping.items()
                                if orig in texts[cid]}
    ids = sorted(files)
    for cid in ids:
        (out_c / f"{cid}.blif.gz").write_bytes(files[cid])

    # provenance
    clean_root = {i: (inserts[i]["clean"] if i in inserts else i) for i in identity}
    prov: dict[str, dict[str, object]] = {}
    for src in identity:
        prov[src] = {"base": entries[src]["base"], "source": src, "restructuring": "identity",
                     "role": "clean" if labels[src] is None else "infected",
                     "clean_twin": clean_root[src],
                     "insert": inserts.get(src)}
        for v in variants[src]:
            prov[v] = {"base": entries[v]["base"], "source": src,
                       "restructuring": str(restr[v]["variant"]),
                       "role": "clean" if labels[v] is None else "infected",
                       "clean_twin": clean_root[src], "insert": None}
    by_base: dict[str, int] = {}
    by_form: dict[str, int] = dict.fromkeys(FORMS, 0)
    for p in prov.values():
        by_base[str(p["base"])] = by_base.get(str(p["base"]), 0) + 1
        by_form[str(p["restructuring"])] += 1
    n_clean = sum(1 for i in ids if labels[i] is None)
    unproven = sorted(f"{r['id']} ({r['variant']} of {r['source']})" for r in restr.values()
                      if r["verdict"] == "unproven")
    counts: dict[str, object] = {
        "circuits": len(ids), "clean": n_clean, "infected": len(ids) - n_clean,
        "forms": len(FORMS), "by_base": by_base, "by_restructuring": by_form,
        "equiv_note": ("all proven" if not unproven else
                       f"{len(unproven)} unproven by timeout: {', '.join(unproven)}"),
    }

    # internal edit-event files (answer key only; the detector never reads answer_key/)
    ev_src = key / "edit_events"
    n_events = 0
    if ev_src.is_dir():
        (out_k / "edit_events").mkdir()
        for cid in ids:
            f = ev_src / f"{cid}.edit.blif"
            if labels[cid] is not None and f.is_file():
                (out_k / "edit_events" / f"{cid}.edit.blif.gz").write_bytes(
                    gz_bytes(f.read_text(encoding="utf-8")))
                n_events += 1

    # answer key
    (out_k / "labels.json").write_text(_json({i: labels[i] for i in ids}), encoding="utf-8")
    (out_k / "provenance.json").write_text(_json(prov), encoding="utf-8")
    (out_k / "renames.json").write_text(_json(renames), encoding="utf-8")
    kept = set(ids)
    for name in ("rareness", "insertion", "failures"):
        data = json.loads((key / f"{name}.json").read_text(encoding="utf-8"))
        if name == "failures":
            data = [d for d in data if d["base"] not in excluded]
        elif name == "rareness":
            data = [d for d in data if d["circuit"] in kept]
        else:
            data = {k: v for k, v in data.items() if k in kept}
        (out_k / f"{name}.json").write_text(_json(data), encoding="utf-8")
    (out_k / "restructured.json").write_text(_json(
        [{k: v for k, v in r.items() if k != "measure"} for r in
         sorted(restr.values(), key=lambda r: str(r["id"])) if r["id"] in entries]),
        encoding="utf-8")
    (out_k / "catalogue.json").write_text(_json({
        "trojan_catalogue": man["trojan_catalogue"], "trojans": man["trojans"],
        "mix": {"clean": n_clean, "infected": len(ids) - n_clean},
    }), encoding="utf-8")

    if n200:
        wsrc = key / "witnesses"
        (out_k / "witnesses").mkdir()
        for f in sorted(wsrc.glob("*.json.gz")):
            if f.name[: -len(".json.gz")] not in excluded:
                (out_k / "witnesses" / f.name).write_bytes(f.read_bytes())
        sets = json.loads((key / "sets.json").read_text(encoding="utf-8"))
        (out_k / "sets.json").write_text(
            _json({b: v for b, v in sets.items() if b not in excluded}), encoding="utf-8")

    # manifest (no label, catalogue or mix)
    name = f"{short_name(family)}-v{version}"
    manifest = {
        "release": name, "family": family, "version": version,
        "tools": {"odin3_build_pin": tools.odin3_build_pin, "abc": tools.abc},
        "restructurings": list(FORMS),
        "counts": {"circuits": len(ids), "by_base": dict(sorted(by_base.items())),
                   "by_restructuring": by_form},
        "answer_key": "answer_key/ (shipped as a separate archive; a detector must not read it)",
        "circuits": [{"id": cid, "base": entries[cid]["base"], "file": f"circuits/{cid}.blif.gz",
                      "bytes": len(files[cid]), "sha256": hashlib.sha256(files[cid]).hexdigest()}
                     for cid in ids],
    }
    (out / "manifest.json").write_text(_json(manifest), encoding="utf-8")
    design_md = ""
    if n200:
        from lemanruss.htl.n200run import DESIGN_MD, tables

        design_md = DESIGN_MD
        pooled_tbl = "\n".join(tables(root))
        manifest["goldens"] = {b: g for b, g in man["goldens"].items() if b not in excluded}
        (out / "manifest.json").write_text(_json(manifest), encoding="utf-8")
    else:
        rareness_md = (key / "rareness.md").read_text(encoding="utf-8")
        pooled_tbl = _pooled_only(rareness_md)
    if family == "Seeker-Seq" and not n200:  # from the records of the released circuits only
        from lemanruss.htl.r6report import pooled

        pooled_tbl = "\n".join(pooled(json.loads(
            (out_k / "rareness.json").read_text(encoding="utf-8"))))
    failures = len([f for f in json.loads((key / "failures.json").read_text(encoding="utf-8"))
                    if f["base"] not in excluded])
    (out / "DATASHEET.md").write_text(datasheet(
        family, name, tools, counts, [str(b) for b in man["bases"] if b not in excluded],
        pooled_tbl, licences,
        unproven, failures, str(man["v1_lineage"]).replace("Van Nestle's", "Caroline van Neste's")
        .replace(" (in progress; name as dictated, spelling to be confirmed; no unpublished "
                 "results are cited)", "; no unpublished results are cited"), version, excluded,
        design_md),
        encoding="utf-8")
    write_sha256sums(out)
    return {"release": name, "counts": counts, "renamed_circuits": len(renames),
            "renamed_tokens": sum(len(v) for v in renames.values()),
            "comment_lines_removed": dropped, "edit_event_files": n_events}


def man_base(man: dict[str, object], cid: str) -> str:
    circuits = man["circuits"]
    assert isinstance(circuits, list)
    for c in circuits:
        if c["id"] == cid:
            return str(c["base"])
    raise KeyError(cid)


def _pooled_only(rareness_md: str) -> str:
    """The pooled tables of rareness.md (not the per-circuit rows)."""
    lines = rareness_md.splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if ln.startswith("| band reached") or ln.startswith("| N cycles")), 0)
    end = next((i for i, ln in enumerate(lines) if ln.startswith("Failures")), len(lines))
    return "\n".join(lines[start:end]).strip()


def short_name(family: str) -> str:
    return {"Seeker-Comb": "seeker-comb", "Seeker-Seq": "seeker-seq"}[family]


def write_sha256sums(out: Path) -> None:
    lines = []
    for p in sorted(q for q in out.rglob("*") if q.is_file() and q.name != "SHA256SUMS"):
        lines.append(f"{sha256_file(p)}  {p.relative_to(out).as_posix()}")
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
