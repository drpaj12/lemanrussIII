"""Release packaging of an n = 300 per base (rc4) build tree: circuits, answer key, manifest,
SHA256SUMS and DATASHEET. `lemanruss verify` re-reads the result from disk.

The circuits are copied as they are (they are already obfuscated and carry no provenance); only
gzip (zero timestamp) is added. The answer key holds the labels, the sets, the Trojans, the ABC
scripts, the pre-obfuscation infected circuits and the witnesses.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from lemanruss.htl.n200run import DESIGN_MD, tables
from lemanruss.htl.release import (
    Tools,
    gz_bytes,
    licence_lines,
    short_name,
    write_sha256sums,
)
from lemanruss.htl.seqoc import opencores_licence_lines

Json = dict[str, object]


def _json(obj: object) -> str:
    return json.dumps(obj, indent=1, sort_keys=True) + "\n"


RC7_DESIGN_MD = (
    "## rc7 (round 9): magic-number triggers (rc8: unchanged)\n\n"
    "Every Trojan trigger is a magic-number comparator: an AND of literals on nets that already "
    "exist in the host (flip-flop outputs and primary inputs). It adds no flip-flop and no latch, "
    "and the energy payload (the one payload that adds flip-flops) is not used. Before ABC, each "
    "infected circuit has exactly the flip-flop and latch count of its golden (a hard build "
    "gate). The value is drawn from the golden's random multi-cycle simulation: it is reached at "
    "least once and its probability of being high within 1024 cycles lies in the fast, mid or "
    "slow band. Payloads: stuck output, bit error on an upper-half or lower-half output, and the "
    "always-on slowdown. Spec section 13.")


def rc8_md() -> str:
    from lemanruss.htl import ocbases

    adm = [d for d in ocbases.DESIGNS if d.admitted]
    return "\n".join([
        "## rc8: OpenCores bases", "",
        "The 36 rc7 bases (circuits, answer key and witnesses) are carried over byte for byte; "
        f"rc8 adds {len(adm)} OpenCores bases (" + ", ".join(d.name for d in adm)
        + ") built as rc7 builds them (same construction and gates), with Odin III rel-v150 "
        "reading the RTL (`read_verilog; proc; opt; flatten; opt; lower`). The set stays "
        "flip-flops only, no memories. Reset style: Odin III lowers asynchronous reset / set to "
        "synchronous logic (its warning is kept in the run record), so the netlists differ from "
        "the RTL on reset timing. Only projects whose licence clearly permits redistribution "
        "of derived netlists without copyleft terms are included; the others are listed below "
        "with their licence and left out.", "",
        "### OpenCores candidates", "", *ocbases.candidates_table()])


def datasheet(
    family: str, name: str, tools: Tools, counts: Json, bases: list[str], tables_md: str,
    licences: Path | None, lineage: str, version: str,
) -> str:
    by_base = counts["by_base"]
    assert isinstance(by_base, dict)
    comb = family == "Seeker-Comb"
    rc7 = not comb and version.endswith(("rc7", "rc8"))
    if rc7:
        lineage = lineage.replace("ISCAS-89, ITC-99 and VTR sequential designs",
                                  "ISCAS-89, ITC-99, VTR and OpenCores sequential designs"
                                  if version.endswith("rc8") else
                                  "ISCAS-89, ITC-99 and VTR sequential designs")
        lineage = lineage.replace(
            "counter and FSM-pattern triggers", "magic-number triggers (rc7)")
    return "\n".join([
        f"# {name} datasheet", "",
        f"Family: {family}. Version {version} (release candidate). Produced by Leman Russ III "
        "(Yggdrasil III).", "",
        "Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to "
        "detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.", "",
        "## Lineage", "", lineage, "",
        "## Contents", "",
        f"- circuits: {counts['circuits']} in `circuits/<id>.blif.gz` (gzip, zero timestamp), "
        f"{counts['clean']} clean and {counts['infected']} infected, opaque ids.",
        f"- bases: {len(bases)}; per base one golden and up to three sets of 100 circuits "
        "(LUT k = 4, LUT k = 6, AND/OR/NOT gates).",
        "- answer key: `answer_key/` (labels, sets, Trojans, ABC scripts, rareness, witnesses, "
        "and `pre/<id>.blif.gz`, each infected circuit before obfuscation); a detector must "
        "not read it.", "",
        "Circuits per base:", "",
        ", ".join(f"{b} {n}" for b, n in sorted(by_base.items())), "",
        DESIGN_MD, "",
        *([RC7_DESIGN_MD, ""] if rc7 else []),
        *([rc8_md(), ""] if not comb and version.endswith("rc8") else []),
        "## Rareness", "",
        ("Seeker-Comb: the trigger is an AND of rare-valued nets grown until the joint "
         "activation probability per random vector falls in a target band (p < 1e-2, 1e-3, "
         "1e-4; exact when the design has at most 20 inputs, else 2^20 vectors)."
         if comb else
         ("Seeker-Seq rc7 / rc8: magic-number triggers (an AND of literals on existing register "
          "outputs and primary inputs, no added flip-flop), three speed bands each defined by "
          "P(trigger high at least once within 1024 cycles) over random multi-cycle simulation "
          "of the golden: fast 0.5-1, mid 0.05-0.5, slow 0.003-0.05."
          if rc7 else
          "Seeker-Seq: counter and FSM-pattern triggers, three speed bands each defined by "
          "P(trigger high within 1024 cycles): fast 0.5-1, mid 0.05-0.5, slow 0.003-0.05.")),
        "Rareness is measured on the circuit before obfuscation (`pre/`), where the trigger net "
        "exists.", "",
        tables_md, "",
        "## Bases and licences", "", *licence_lines(licences, bases, family),
        *opencores_licence_lines(bases), "",
        "## Tools", "",
        f"- Odin III (build of the circuits): {tools.odin3_build_pin}; checkout used for "
        f"`lemanruss verify`: {tools.odin3_checkout}.",
        f"- ABC: {tools.abc}.", "",
        "## Fetch and check", "",
        "Unpack the circuits and answer-key archives into one directory, then "
        "`sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.", "",
    ])


def build_release_n200(
    root: Path, out: Path, family: str, short: str, tools: Tools, licences: Path | None,
    version: str,
) -> Json:
    key = root / "answer_key"
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    labels = json.loads((key / "labels.json").read_text(encoding="utf-8"))
    sets = json.loads((key / "sets.json").read_text(encoding="utf-8"))
    trojans = json.loads((key / "trojans.json").read_text(encoding="utf-8"))
    out_c, out_k = out / "circuits", out / "answer_key"
    out_c.mkdir(parents=True, exist_ok=False)
    (out_k / "pre").mkdir(parents=True)
    (out_k / "witnesses").mkdir()
    entries = {c["id"]: c for c in man["circuits"]}
    gold_of = {}
    set_of = {}
    for s in sets.values():
        gold_of[s["golden"]] = s["golden"]
        for name, v in s["sets"].items():
            for cid in v["infected_ids"] + v["clean_ids"]:
                gold_of[cid] = s["golden"]
                set_of[cid] = name
    files: dict[str, bytes] = {}
    for cid in sorted(entries):
        files[cid] = gz_bytes((root / entries[cid]["file"]).read_text(encoding="utf-8"))
        (out_c / f"{cid}.blif.gz").write_bytes(files[cid])
    prov: dict[str, Json] = {}
    by_base: dict[str, int] = {}
    for cid in sorted(entries):
        base = str(entries[cid]["base"])
        by_base[base] = by_base.get(base, 0) + 1
        stratum = f"{base}/{set_of.get(cid, 'golden')}"
        kind = sets[base].get("kind")
        prov[cid] = {"base": base, "stratum": stratum, "source": cid, "restructuring": "identity",
                     "role": "clean" if labels[cid] is None else "infected",
                     "clean_twin": gold_of[cid], "set": set_of.get(cid, "golden"),
                     "insert": ({"kind": kind, "trojans": trojans[cid], "base": base,
                                 "n_trojans": len(trojans[cid])} if cid in trojans else None)}
        pre = key / "pre" / f"{cid}.blif.gz"
        if pre.is_file():
            (out_k / "pre" / pre.name).write_bytes(pre.read_bytes())
    for f in sorted((key / "witnesses").glob("*.json.gz")):
        (out_k / "witnesses" / f.name).write_bytes(f.read_bytes())
    n_clean = sum(1 for v in labels.values() if v is None)
    counts: Json = {
        "circuits": len(files), "clean": n_clean, "infected": len(files) - n_clean,
        "by_base": dict(sorted(by_base.items())), "by_restructuring": {"identity": len(files)},
    }
    (out_k / "labels.json").write_text(_json(labels), encoding="utf-8")
    (out_k / "provenance.json").write_text(_json(prov), encoding="utf-8")
    (out_k / "renames.json").write_text("{}\n", encoding="utf-8")
    (out_k / "sets.json").write_text(_json(sets), encoding="utf-8")
    for name in ("rareness", "failures", "scripts", "trojans", "cuts"):
        (out_k / f"{name}.json").write_text(
            (key / f"{name}.json").read_text(encoding="utf-8"), encoding="utf-8")
    (out_k / "catalogue.json").write_text(_json({
        "trojan_catalogue": man["trojan_catalogue"], "trojans": man["trojans"],
        "mix": {"clean": n_clean, "infected": len(files) - n_clean}}), encoding="utf-8")
    name = f"{short_name(family)}-v{version}"
    manifest: Json = {
        "release": name, "family": family, "version": version,
        "tools": {"odin3_build_pin": tools.odin3_build_pin, "abc": tools.abc},
        "restructurings": ["identity"], "goldens": man["goldens"],
        "counts": {"circuits": len(files), "by_base": dict(sorted(by_base.items())),
                   "by_restructuring": {"identity": len(files)}},
        "answer_key": "answer_key/ (shipped as a separate archive; a detector must not read it)",
        "circuits": [{"id": cid, "base": entries[cid]["base"], "file": f"circuits/{cid}.blif.gz",
                      "bytes": len(files[cid]), "sha256": hashlib.sha256(files[cid]).hexdigest()}
                     for cid in sorted(files)],
    }
    (out / "manifest.json").write_text(_json(manifest), encoding="utf-8")
    (out / "DATASHEET.md").write_text(datasheet(
        family, name, tools, counts, [str(b) for b in man["bases"]], "\n".join(tables(root)),
        licences, str(man["v1_lineage"]).replace("Van Nestle's", "Caroline van Neste's")
        .replace(" (in progress; name as dictated, spelling to be confirmed; no unpublished "
                 "results are cited)", "; no unpublished results are cited"), version),
        encoding="utf-8")
    write_sha256sums(out)
    return {"release": name, "counts": counts}
