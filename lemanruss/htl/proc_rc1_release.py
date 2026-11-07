"""Seeker-Proc v2.0-rc1 release packaging and verification (rc1 Continuation 5 step 4).

One release directory holds, per form (gates, lut4, lut6), the same 100 logical circuits mapped
to that form. Per form the clean/infected mix is drawn as Seeker-Comb/Seq draw it
(`docs/specs/2026-11-01-seeker-n200-design.md` section 4, spec section 3): n_inf ~ Uniform{10..70}
once per form, the infected circuits chosen at random, the rest shipped as their clean variant.
Every circuit gets an opaque id, shuffled across forms and bases, so an id says nothing about its
form, base, label or logical circuit (the answer key links them).

`circuits/<id>.blif.gz` and `manifest.json` are all a detector sees. `answer_key/` holds the
labels, provenance, the logical-circuit catalogue (kinds, magic words, links across forms), the
clean twin of each infected circuit, and each infected circuit's secret activation programs.
The seed and the magic words live only in the answer key (and in the private run records
outside this repository); nothing in the repository's source or docs names them.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

from lemanruss.htl.proc_build import _witness_words
from lemanruss.htl.proc_gate import GateError, gate_problems, structural_problems
from lemanruss.htl.proc_rareness import magic_match_probability, word_bits
from lemanruss.htl.proc_release import LEAK_TOKENS, NAME_VOCAB, check_name_vocabulary
from lemanruss.htl.proc_witness import alu_witness_words
from lemanruss.htl.release import gz_bytes, read_blif_gz, scrub_group, sha256_file, write_sha256sums

# build-time form key (proc_build.FORMS) -> released form name
FORM_NAMES = {"gates": "gates", "k4": "lut4", "k6": "lut6"}
RELEASE_NAME = "seeker-proc-v2.0-rc1"
N_INF_RANGE = (10, 70)


@dataclass(frozen=True)
class LogicalCircuit:
    """One built logical circuit: its clean and infected mapped BLIFs in every form."""

    logical_id: str
    base: str
    kinds: list[str]
    magic_words: list[int]
    forms_dir: Path

    def text(self, form: str, role: str) -> str:
        return (self.forms_dir / f"{form}-{role}.blif").read_text(encoding="utf-8")


def load_logical(result_json: Path, forms_root: Path) -> list[LogicalCircuit]:
    """The passing circuits of one base's driver result file (build_n100.py output)."""
    res = json.loads(result_json.read_text(encoding="utf-8"))
    out = []
    for c in res["passing"]:
        out.append(LogicalCircuit(
            c["circuit_id"], c["base"], list(c["kinds"]),
            [int(w, 16) for w in c["magic_words"]], forms_root / c["circuit_id"]))
    return out


def draw_infected(n: int, rng: random.Random) -> set[int]:
    """Indices (0..n-1) shipped infected in one form: n_inf ~ Uniform{10..70} (clamped to n)."""
    n_inf = min(rng.randint(*N_INF_RANGE), n)
    return set(rng.sample(range(n), n_inf))


def package_proc_rc1(
    circuits: list[LogicalCircuit], out_dir: Path, seed: int, release_name: str = RELEASE_NAME,
    notes: dict[str, object] | None = None, odin3_bin: Path | None = None,
) -> dict[str, object]:
    """`odin3_bin` set: every file passes the release gate (`proc_gate`) before it is written,
    or `GateError` stops the packaging."""
    out_dir.mkdir(parents=True, exist_ok=False)
    cdir, adir = out_dir / "circuits", out_dir / "answer_key"
    cdir.mkdir()
    adir.mkdir()
    (adir / "twins").mkdir()
    (adir / "witness").mkdir()
    rng = random.Random(f"proc-rc1:{seed}")

    # one slot per (form, logical circuit); ids are a seeded shuffle of 1..N
    slots = [(f, i) for f in FORM_NAMES.values() for i in range(len(circuits))]
    order = list(range(1, len(slots) + 1))
    rng.shuffle(order)
    ids = {slot: f"pr{n:04d}" for slot, n in zip(slots, order, strict=True)}
    build_key = {v: k for k, v in FORM_NAMES.items()}

    infected_idx = {f: draw_infected(len(circuits), rng) for f in FORM_NAMES.values()}
    labels: dict[str, str | None] = {}
    prov: dict[str, dict[str, object]] = {}
    manifest_rows: list[dict[str, object]] = []
    catalogue: dict[str, dict[str, object]] = {}
    rareness: dict[str, dict[str, object]] = {}
    renames: dict[str, dict[str, str]] = {}
    for i, lc in enumerate(circuits):
        catalogue[lc.logical_id] = {
            "base": lc.base, "kinds": lc.kinds,
            "magic_words": [f"0x{w:0{word_bits(lc.base) // 4}x}" for w in lc.magic_words],
            "ids": {f: ids[(f, i)] for f in FORM_NAMES.values()},
            "infected_in": [f for f in FORM_NAMES.values() if i in infected_idx[f]],
        }

    for form in FORM_NAMES.values():
        bk = build_key[form]
        for i, lc in enumerate(circuits):
            cid = ids[(form, i)]
            infected = i in infected_idx[form]
            clean_text = lc.text(bk, "clean")
            text = lc.text(bk, "infected") if infected else clean_text
            text_before_scrub = text
            if infected:
                new, mapping = scrub_group({cid: text}, clean_text, cid, seed)
                text = new[cid]
                if mapping:
                    renames[cid] = {v: k for k, v in mapping.items()}
                (adir / "twins" / f"{cid}.blif.gz").write_bytes(gz_bytes(clean_text))
                wdir = adir / "witness" / cid
                wdir.mkdir()
                for k, (kind, w) in enumerate(zip(lc.kinds, lc.magic_words, strict=True)):
                    prog = (alu_witness_words(lc.base, w) if kind == "alu"
                            else _witness_words(lc.base, [w]))
                    hexw = word_bits(lc.base) // 4
                    (wdir / f"t{k}.words.gz").write_bytes(
                        gz_bytes("\n".join(f"{x:0{hexw}x}" for x in prog) + "\n"))
                rareness[cid] = {"p_match_per_trojan":
                                 magic_match_probability(1, word_bits(lc.base)),
                                 "n_trojans": len(lc.kinds), "kinds": lc.kinds,
                                 "scoap": "not measured in rc1"}
            # release gate (rc2): the file as released is valid, and equivalent to its pre-scrub
            # mapped netlist (the scrub only renames inserter nets)
            problems = gate_problems(
                text, odin3_bin, text_before_scrub if text != text_before_scrub else None
            ) if odin3_bin else []
            if problems:
                raise GateError(f"{cid}: " + "; ".join(problems))
            data = gz_bytes(text)
            (cdir / f"{cid}.blif.gz").write_bytes(data)
            manifest_rows.append({"id": cid, "base": lc.base, "file": f"circuits/{cid}.blif.gz",
                                  "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            labels[cid] = lc.logical_id if infected else None
            prov[cid] = {
                "base": lc.base, "source": cid, "restructuring": form,
                "role": "infected" if infected else "clean",
                "clean_twin": f"{cid}-twin" if infected else cid,
                "logical": lc.logical_id,
                "insert": ({"n_trojans": len(lc.kinds),
                            "trojans": [{"kind": k} for k in lc.kinds]} if infected else {}),
            }

    by_form: dict[str, dict[str, int]] = {}
    for p in prov.values():
        d = by_form.setdefault(str(p["restructuring"]), {"clean": 0, "infected": 0})
        d[str(p["role"])] += 1
    manifest = {
        "release": release_name, "family": release_name, "schema": 2,
        "counts": {"circuits": len(manifest_rows),
                   "by_base": {b: sum(1 for r in manifest_rows if r["base"] == b)
                               for b in sorted({str(r["base"]) for r in manifest_rows})}},
        "circuits": sorted(manifest_rows, key=lambda r: str(r["id"])),
    }

    def dump(path: Path, obj: object) -> None:
        path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    dump(out_dir / "manifest.json", manifest)
    dump(adir / "labels.json", labels)
    dump(adir / "provenance.json", prov)
    dump(adir / "catalogue.json", catalogue)
    dump(adir / "rareness.json", rareness)
    dump(adir / "renames.json", renames)
    dump(adir / "mix_by_form.json", by_form)
    (out_dir / "DATASHEET.md").write_text(
        datasheet(release_name, manifest, by_form, circuits, notes or {}), encoding="utf-8")
    write_sha256sums(out_dir)
    return {"release": release_name, "circuits": len(manifest_rows), "by_form": by_form}


def datasheet(
    name: str, manifest: dict[str, object], by_form: dict[str, dict[str, int]],
    circuits: list[LogicalCircuit], notes: dict[str, object],
) -> str:
    counts = manifest["counts"]
    assert isinstance(counts, dict)
    lines = [
        f"# {name} datasheet", "",
        f"Family: Seeker-Proc. Version {name.removeprefix('seeker-proc-v')}. "
        "Produced by Leman Russ III "
        "(Yggdrasil III). Defensive hardware-Trojan detection research; the circuits are Trojans "
        "to detect, nothing here is meant to be deployed.", "",
        "## What it is", "",
        f"{counts['circuits']} circuits: the same {len(circuits)} logical circuits in three "
        "forms (gates: AND/OR/NOT gate netlist; lut4 and lut6: ABC `if` mapped to 4- and "
        "6-input LUTs), each form a gzip BLIF (`circuits/<id>.blif.gz`, zero timestamp, no "
        "comment lines). Ids are opaque and shuffled across forms and bases. A detector is not "
        "told whether a circuit is infected.", "",
        "| form | clean | infected |", "|---|---|---|",
    ]
    for f in FORM_NAMES.values():
        d = by_form[f]
        lines.append(f"| {f} | {d['clean']} | {d['infected']} |")
    lines += [
        "", "Per form the number of infected circuits is drawn once, uniformly from 10 to 70, as "
        "Seeker-Comb and Seeker-Seq do; the rest are clean variants. An infected circuit carries "
        "1 to 3 Trojans (P = 0.5, 0.3, 0.2).", "",
        "## Bases (open source, no flip-flop added by any Trojan)", "",
        "| base | licence | flip-flops | logical circuits |", "|---|---|---|---|",
    ]
    lic = {"mcu": ("MIT (Arduino-on-RISC-V)", 1310), "picorv32": ("ISC (YosysHQ picorv32, "
           "default parameters: no multiplier, divider or IRQ)", 1615),
           "darkriscv": ("BSD 3-Clause (darkriscv)", 2034),
           "mips_16": ("OpenCores mips_16 (16-bit, 5-stage; x don't-cares resolved to 0, "
                       "memories black-boxed)", 0)}
    for b in sorted(lic):
        n = sum(1 for c in circuits if c.base == b)
        lines.append(f"| {b} | {lic[b][0]} | {lic[b][1]} | {n} |")
    lines += [
        "", "Memories are black-box hard blocks in all three forms, so flip-flop counts are the "
        "cores' own (not per-bit RAM latches). Infected and clean twins have equal flip-flop "
        "counts (hard gate, per circuit).", "",
        "## Triggers and payloads", "",
        "Trigger: a 32-bit magic word on the core's instruction register (mcu `instruction`, "
        "single cycle; darkriscv `XIDATA`, its registered instruction; picorv32 "
        "`next_insn_opcode`). Payload kinds: reset DoS, stall DoS, and ALU data corruption "
        "(flip the LSB of a shift-right result). RV32I has no rotate instruction. Each Trojan "
        "has its own random legal word; words equal to a word of a shipped program image or of "
        "a witness scaffold are never drawn. The activation programs are in the answer key only.",
        "",
        "## Variety", "",
        "Each logical circuit is one (base, Trojan draw) built once, then mapped per form with "
        "its own random ABC script from the 18-script catalogue (`obfuscate`), clean and "
        "infected separately. Odin III's in-process ABC path is used; ABC `read_blif` on the "
        "source netlists fails on these cores. Dummy cuts were not applied.", "",
        "## Gates every circuit passed", "",
        "Release gate (rc2): every file is one flat `.model`, declares no port twice, drives no "
        "net twice, is read by Odin III `read_blif`, and is equivalent (ABC) to the lowered "
        "netlist it was mapped from. rc1 lacked this and its darkriscv and mcu files were "
        "malformed (several `.model` sections merged); rc1 is superseded.", "",
        "Flip-flop equality with the clean twin; every Trojan's activation program changes the "
        "trace on iverilog, Odin III RTL and Odin III netlist simulation; Odin III RTL and "
        "netlist traces equal the clean twin's on the neutral program, on a non-magic "
        "shift-right (ALU Trojans) and on every shipped program of the base (mcu: 4, darkriscv: "
        "1, picorv32: none in the checkout). iverilog is recorded on shipped programs, not "
        "gating (four-state `x` difference on darkriscv, spec section 0a).", "",
    ]
    for k, v in notes.items():
        lines += [f"- {k}: {v}"]
    lines += [
        "", "## Out of range", "",
        "A detector's score on a circuit whose flip-flop count lies outside the detector's own "
        "training range is reported `out_of_range`, never as a flag.", "",
        "## Check", "",
        "`sha256sum -c SHA256SUMS`, then `lemanruss.htl.proc_rc1_release.verify_proc_rc1`.", "",
    ]
    return "\n".join(lines)


_INS = re.compile(r"\b_ins\d+\b")


def verify_proc_rc1(out_dir: Path) -> dict[str, object]:
    """Independent re-check from disk. Returns {"ok": bool, ...checks}."""
    errors: list[str] = []
    sums = out_dir / "SHA256SUMS"
    if not sums.is_file():
        return {"ok": False, "errors": ["SHA256SUMS missing"]}
    for line in sums.read_text(encoding="utf-8").splitlines():
        digest, _, rel = line.partition("  ")
        p = out_dir / rel
        if not p.is_file() or sha256_file(p) != digest:
            errors.append(f"hash mismatch or missing: {rel}")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = manifest["circuits"]
    for r in rows:
        f = out_dir / str(r["file"])
        if not f.is_file() or sha256_file(f) != r["sha256"] or f.stat().st_size != r["bytes"]:
            errors.append(f"manifest hash/size mismatch: {r['file']}")
    nv = check_name_vocabulary(out_dir)
    prov = json.loads((out_dir / "answer_key" / "provenance.json").read_text(encoding="utf-8"))
    labels = json.loads((out_dir / "answer_key" / "labels.json").read_text(encoding="utf-8"))
    labels_ok = all(str(r["id"]) in labels and str(r["id"]) in prov for r in rows)
    pat = re.compile("|".join(re.escape(w) for w in (*LEAK_TOKENS, *NAME_VOCAB)), re.I)
    leaks: list[str] = []
    traces: list[str] = []
    ff_mismatch: list[str] = []
    ids = [str(r["id"]) for r in rows]
    if len(set(ids)) != len(ids):
        errors.append("duplicate ids")
    hashes: dict[str, str] = {}
    dups = 0
    for r in rows:
        cid = str(r["id"])
        try:
            text = read_blif_gz(out_dir / str(r["file"]))
        except (OSError, EOFError) as exc:
            errors.append(f"{cid}: unreadable ({type(exc).__name__})")
            continue
        errors += [f"{cid}: {x}" for x in structural_problems(text)]  # release gate (rc2)
        if r["sha256"] in hashes:
            dups += 1
        hashes[str(r["sha256"])] = cid
        if any(ln.lstrip().startswith("#") for ln in text.splitlines()):
            traces.append(f"{cid}: comment line")
        toks = set(text.split())
        if any(_INS.search(t) or "__htl" in t for t in toks):
            traces.append(f"{cid}: inserter-only name")
        if prov[cid]["role"] == "infected":
            twin = read_blif_gz_bytes(out_dir / "answer_key" / "twins" / f"{cid}.blif.gz")
            native = set(twin.split())
            for t in toks - native:
                if pat.search(t):
                    leaks.append(f"{cid}: token {t}")
            if text.count(".latch") != twin.count(".latch"):
                ff_mismatch.append(cid)
    return {
        "ok": (not errors and nv.ok and not leaks and not traces and not ff_mismatch
               and labels_ok and dups == 0),
        "errors": errors, "name_vocab_ok": nv.ok, "name_vocab_hits": nv.hits,
        "content_leaks": leaks, "provenance_traces": traces, "ff_mismatch": ff_mismatch,
        "labels_present": labels_ok, "duplicate_circuits": dups, "circuits": len(rows),
    }


def read_blif_gz_bytes(path: Path) -> str:
    return gzip.decompress(path.read_bytes()).decode("utf-8")


__all__ = ["LogicalCircuit", "load_logical", "draw_infected", "package_proc_rc1", "datasheet",
           "verify_proc_rc1", "FORM_NAMES", "RELEASE_NAME"]
