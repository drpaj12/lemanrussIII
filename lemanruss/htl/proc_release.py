"""Seeker-Proc v2.0-pilot release packaging and verification (round 7, brief item 4).

Shaped differently from `lemanruss.htl.release`/`relverify` (the Seeker-Comb/Seq families: a
BLIF circuit catalogue with 19 restructured forms per base). A processor Trojan here is a
one-or-few-line patch to a single upstream RTL file plus a witness program image; the upstream
design itself is never redistributed (CLAUDE.md: never commit external/'s content), so the
release holds the patch and the witness only, named `proc-release` / `proc-verify` (round 7
agent default) rather than reusing the family verbs.

Label scrub: the patch text itself names its own trigger/payload wires (`__htl_trigger`,
`__htl_pc_mux`, `__htl_seq_state`, ...) -- exactly the leaked-label problem spec section 10.2
found in round 5, so the same rule applies (no `__htl_`/`trojan`/`odin3_edit` token in a
detector-visible file). This pilot's scrub is a plain `_insN` counter per unique identifier
(not styled to the base's own naming the way the family release's `[N]`/`$nN` scrub is, since
matching house style is not needed for a one-file preliminary release) -- recorded as a round 7
agent default; the map is reversible and `proc_verify_release` replays it to re-check leak-free.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

LEAK_TOKENS = ("htl", "trojan", "odin3_edit", "odin3 edit")
_HTL_IDENT = re.compile(r"__htl_\w+")

# Fix round (2026-11-01, controller finding on pilot1): directory names, file names and manifest
# keys must never carry the label vocabulary -- `circuits/proc-mcu-magicword-stall/` and the
# matching manifest key leaked the trigger/payload identity even though the file *content* was
# leak-scanned clean. An opaque id (`pp0001`, ...) never matches any of these words.
NAME_VOCAB = (
    "trigger", "payload", "magic", "seq", "word", "stall", "reset", "dos", "trojan", "htl",
    "infect", "clean",
)


@dataclass(frozen=True)
class ProcTrojanSpec:
    trojan_id: str
    base: str  # "mcu" | "darkriscv"
    patched_file: str  # relative name, e.g. "single_cycle_core.v"
    patched_text: str  # the post-insertion source (still carries __htl_ names)
    magic_words: list[int]
    trigger_kind: str  # "t-input-pattern" (magic word) | "t-seq-pattern" (magic sequence)
    payload_kind: str  # "p-dos-stuck" (mcu) | "p-dos-reset" (darkriscv)
    witness_image: dict[str, bytes]  # relative name -> bytes (the .vmh planes or .mem file)


def scrub(text: str) -> tuple[str, dict[str, str]]:
    """Replaces every `__htl_*` identifier with `_insN` (N stable per unique identifier, in
    first-seen order); returns the scrubbed text and the identifier -> neutral-name map."""
    seen: dict[str, str] = {}

    def repl(m: re.Match[str]) -> str:
        ident = m.group(0)
        if ident not in seen:
            seen[ident] = f"_ins{len(seen)}"
        return seen[ident]

    return _HTL_IDENT.sub(repl, text), seen


def unscrub(text: str, rename: dict[str, str]) -> str:
    """Inverse of `scrub`: replaces every neutral name back with its original identifier."""
    reverse = {v: k for k, v in rename.items()}
    pattern = re.compile("|".join(re.escape(k) for k in reverse))
    return pattern.sub(lambda m: reverse[m.group(0)], text)


def leak_scan(text: str) -> list[str]:
    """Every leak token (case-insensitive) found in `text`; empty means clean."""
    lower = text.lower()
    return [tok for tok in LEAK_TOKENS if tok in lower]


def package_proc_release(
    specs: list[ProcTrojanSpec], out_dir: Path, rareness: dict[str, dict[str, object]]
) -> Path:
    """Writes the release directory: circuits/<id>/{patch.v.gz, <image files>.gz}, manifest.json,
    answer_key/{labels.json, renames.json, rareness.json}, SHA256SUMS, DATASHEET.md."""
    out_dir.mkdir(parents=True, exist_ok=True)
    circuits_dir = out_dir / "circuits"
    answer_dir = out_dir / "answer_key"
    circuits_dir.mkdir(exist_ok=True)
    answer_dir.mkdir(exist_ok=True)

    manifest: dict[str, object] = {"schema": 1, "family": "seeker-proc-v2.0-pilot", "circuits": {}}
    labels: dict[str, object] = {}
    renames: dict[str, dict[str, str]] = {}
    leaks: list[str] = []

    for spec in specs:
        cdir = circuits_dir / spec.trojan_id
        cdir.mkdir(exist_ok=True)
        scrubbed, rename = scrub(spec.patched_text)
        found = leak_scan(scrubbed)
        if found:
            leaks.append(f"{spec.trojan_id}: {found}")
        patch_path = cdir / f"{spec.patched_file}.gz"
        patch_path.write_bytes(gzip.compress(scrubbed.encode(), mtime=0))
        image_names = []
        for name, data in spec.witness_image.items():
            img_leaks = leak_scan(data.decode(errors="ignore"))
            if img_leaks:
                leaks.append(f"{spec.trojan_id}/{name}: {img_leaks}")
            (cdir / f"{name}.gz").write_bytes(gzip.compress(data, mtime=0))
            image_names.append(f"{name}.gz")
        renames[spec.trojan_id] = rename
        manifest["circuits"][spec.trojan_id] = {  # type: ignore[index]
            "base": spec.base,
            "patched_file": f"{spec.patched_file}.gz",
            "witness_images": image_names,
            "sha256_patch": hashlib.sha256(patch_path.read_bytes()).hexdigest(),
        }
        labels[spec.trojan_id] = {
            "trigger_kind": spec.trigger_kind,
            "payload_kind": spec.payload_kind,
            "magic_words": [f"0x{w:08x}" for w in spec.magic_words],
        }

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    (answer_dir / "labels.json").write_text(json.dumps(labels, indent=2, sort_keys=True))
    (answer_dir / "renames.json").write_text(json.dumps(renames, indent=2, sort_keys=True))
    (answer_dir / "rareness.json").write_text(json.dumps(rareness, indent=2, sort_keys=True))
    if leaks:
        raise ValueError(f"package_proc_release: leak(s) found before packaging: {leaks}")

    _write_sha256sums(out_dir)
    return out_dir


def _write_sha256sums(out_dir: Path) -> None:
    lines = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(out_dir)}")
    (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n")


@dataclass(frozen=True)
class NameVocabResult:
    hits: list[str]
    ok: bool


def check_name_vocabulary(out_dir: Path) -> NameVocabResult:
    """Every directory and file name under `circuits/`, and every key of `manifest.json`
    (recursively: a circuit id, a field name, anything used as a dict key), scanned
    case-insensitively against `NAME_VOCAB`. A hit means the *name itself* -- not file content
    -- carries the answer (fix round, brief item (d)): this is what pilot1 missed (content was
    leak-scanned clean; `circuits/proc-mcu-magicword-stall/` and the matching manifest key were
    not scanned at all)."""
    hits: list[str] = []
    circuits_dir = out_dir / "circuits"
    if circuits_dir.is_dir():
        for p in sorted(circuits_dir.rglob("*")):
            rel = p.relative_to(circuits_dir).as_posix()
            low = rel.lower()
            for w in NAME_VOCAB:
                if w in low:
                    hits.append(f"circuits/{rel}: name contains {w!r}")

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))

    def walk(obj: object, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                low = str(k).lower()
                for w in NAME_VOCAB:
                    if w in low:
                        hits.append(f"manifest key {path}{k!r}: contains {w!r}")
                walk(v, f"{path}{k}.")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}].")

    walk(manifest, "")
    return NameVocabResult(hits, not hits)


@dataclass
class ProcVerifyResult:
    integrity_ok: bool
    leak_free: bool
    leaks: list[str]
    labels_present: bool
    errors: list[str]
    name_vocab_ok: bool = True
    name_vocab_hits: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (self.integrity_ok and self.leak_free and self.labels_present
                and not self.errors and self.name_vocab_ok)


def verify_proc_release(out_dir: Path) -> ProcVerifyResult:
    """Re-reads the release from disk: SHA256SUMS integrity, the leak scan on every
    detector-visible file (circuits/ and manifest.json only, never answer_key/), that every
    circuit in manifest.json has a label, and (fix round, brief item (d)) that no directory
    name, file name or manifest key carries the label vocabulary (`NAME_VOCAB`) -- this last
    check is new and is what makes pilot1's leaked layout (`circuits/<trojan-id>/`, manifest
    keyed by trojan id) fail where it previously passed; see `tests/test_proc_release.py`'s
    `test_old_trojan_named_layout_fails`."""
    errors: list[str] = []
    integrity_ok = True
    sums_path = out_dir / "SHA256SUMS"
    if not sums_path.exists():
        return ProcVerifyResult(False, False, [], False, ["SHA256SUMS missing"])
    for line in sums_path.read_text().splitlines():
        digest, _, rel = line.partition("  ")
        path = out_dir / rel
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            integrity_ok = False
            errors.append(f"hash mismatch or missing: {rel}")

    leaks: list[str] = []
    manifest = json.loads((out_dir / "manifest.json").read_text())
    for name in manifest["circuits"]:
        found = leak_scan(json.dumps(manifest["circuits"][name]))
        if found:
            leaks.append(f"manifest/{name}: {found}")
    for gz in (out_dir / "circuits").rglob("*.gz"):
        text = gzip.decompress(gz.read_bytes()).decode(errors="ignore")
        found = leak_scan(text)
        if found:
            leaks.append(f"{gz.relative_to(out_dir)}: {found}")

    labels = json.loads((out_dir / "answer_key" / "labels.json").read_text())
    labels_present = all(tid in labels for tid in manifest["circuits"])

    nv = check_name_vocabulary(out_dir)
    return ProcVerifyResult(integrity_ok, not leaks, leaks, labels_present, errors,
                             nv.ok, nv.hits)


# ===============================================================================================
# Pilot2 (fix round, 2026-11-01): the controller found pilot1 released the patched *RTL* file
# (trivially diffable against the public upstream it patches -- an exact answer key) and no
# clean circuit at all. The detector-visible form here is the *lowered netlist* instead (Odin
# III's own build flow: `read_verilog <files>; proc; opt; lower; write_blif --gates-as-names`,
# the same flow `write_blif --gates-as-names` docs call "the reference" for a tool that must read
# plain gates -- ABC's own `strash` otherwise refuses the plain dialect's `.subckt $_AND_` cells:
# measured, `Cannot find the model for subcircuit`/`Reading network ... has failed`), plus a
# clean twin of every infected circuit, both scrubbed and named with an opaque id
# (`pp0001`, ...). The patched RTL and the witness image move to `answer_key/` (provenance);
# `circuits/` never holds them.
#
# ABC restructuring (brief item (c), "rounds 4-6"): attempted and found to fail at `read_blif`
# time, before any restructuring-specific command runs, so every one of the 18 forms fails the
# same way for the same reason (measured once per base, not repeated 18 times for an identical
# outcome -- the "stated subset" the brief allows): darkriscv's lowered netlist has a genuine
# sequential loop ABC's own network builder refuses ("Network ... contains combinational loop!",
# a box encountered twice on a path to a CO -- consistent with round 6's Odin III gap note #2,
# a loop that passes through a latch) in ~35-50 s; mcu's lowered netlist has deeply parameterized
# hierarchical module names Odin III itself generates (`single_cycle_core$RESET_PC=32'b0...`,
# `dual_port_BRAM$h4141f8f055525db2`) that ABC's BLIF reader truncates at the `$`/`='`/apostrophe
# characters when resolving a `.subckt` box, so it never finds the `.model` it names a few
# characters short of ("Cannot find the model for subcircuit single_cycle_core$RESET_PC"), after
# ~5 minutes of first reading the whole 50-125 MB file. Neither is an Odin III bug (both are
# findings about ABC's BLIF reader against Odin III's own naming and the design's own RAM
# structure); recorded for the controller, not worked around here. No restructured form is
# released this round: `circuits/` holds the identity (unrestructured) lowered netlist only,
# clean and infected, per trojan.
# ===============================================================================================

NETLIST_RESTRUCTURE_TIMEOUT = 400


@dataclass(frozen=True)
class ProcRestructureAttempt:
    """One measured ABC restructuring attempt against a lowered, `--gates-as-names` netlist."""

    base: str
    role: str  # "clean" | "infected"
    form: str
    verdict: str  # "abc-failed" | "equivalent" | "unproven" | "not-equivalent" | "error"
    seconds: float
    note: str


def attempt_restructure(
    gates_blif: Path, variant: str, scratch: Path, tag: str,
    timeout: int = NETLIST_RESTRUCTURE_TIMEOUT,
) -> tuple[str, float, str]:
    """Runs one ABC restructuring script (`lemanruss.htl.restructure.RESTRUCTURINGS[variant]`)
    against `gates_blif`; returns `(verdict, seconds, note)`. Does not call
    `lemanruss.htl.restructure.restructure_one` (its `structure_of` calls `bitsim.compile_model`,
    which also refuses these netlists: `ValueError: bitsim: combinational loop or undriven net`
    -- the same structural finding as ABC's own reader, from an independent implementation)."""
    from lemanruss.htl.restructure import RESTRUCTURINGS, abc_bin

    raw = scratch / f"{tag}_{variant}.blif"
    cmd = f"read_blif {gates_blif}; {RESTRUCTURINGS[variant]}; write_blif {raw}"
    t0 = time.monotonic()
    try:
        run = subprocess.run([str(abc_bin()), "-q", cmd], capture_output=True, text=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return "abc-failed", time.monotonic() - t0, f"ABC timed out after {timeout}s"
    secs = time.monotonic() - t0
    if not raw.exists():
        lines = [ln for ln in (run.stdout + run.stderr).splitlines() if ln.strip()]
        note = lines[-1].strip()[:160] if lines else "no output written"
        return "abc-failed", secs, note
    return "ok-unverified", secs, raw.name


def lower_gates_as_names(
    odin3_bin: Path, top: str, files: list[str], cwd: Path, out: Path, timeout: int = 300,
) -> None:
    """`read_verilog <files>; proc; opt; flatten; opt; lower; write_blif --gates-as-names <out>`
    -- one flat `.model` (rc1 omitted `flatten`: darkriscv and mcu came out as several `.model`
    sections that `obfuscate.parse` merged into one invalid netlist). The plain
    dialect every gate written `.names`, so ABC (and `bitsim`) can read it (the plain
    `write_blif` of round 7's build keeps library primitives as `.subckt`, which both refuse)."""
    file_list = " ".join(files)
    run = subprocess.run(
        [str(odin3_bin), "--top", top, "-p",
         f"read_verilog {file_list}; proc; opt; flatten; opt; lower; "
         f"write_blif --gates-as-names {out}"],
        cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False,
    )
    if run.returncode != 0 or not out.exists():
        raise RuntimeError(f"lower_gates_as_names: odin3 failed: {run.stdout}\n{run.stderr}")


@dataclass(frozen=True)
class ProcCircuitSpec:
    """One clean or one infected circuit of one trojan/base: its identity lowered netlist, plus
    any restructured forms actually produced (pilot2: none -- see the module docstring)."""

    trojan_id: str  # the label; shared by the clean and the infected spec of the same trojan
    base: str  # "mcu" | "darkriscv"
    role: str  # "clean" | "infected"
    identity_text: str  # the lowered, --gates-as-names BLIF text (pre-scrub)
    restructured: list[tuple[str, str]] = field(default_factory=list)  # (form, text), pre-scrub
    # infected-only provenance (answer_key/); None/empty for a clean spec
    magic_words: list[int] = field(default_factory=list)
    trigger_kind: str = ""
    payload_kind: str = ""
    patched_text: str = ""
    patched_file: str = ""
    witness_image: dict[str, bytes] = field(default_factory=dict)


def _neutral_ids(specs: list[ProcCircuitSpec]) -> dict[tuple[str, str, str], str]:
    """`(trojan_id, role, form) -> "ppNNNN"`, assigned in a fixed, data-independent order
    (trojan id, then clean before infected, then identity before each restructured form sorted
    by name) so a release built twice from the same specs gets the same ids."""
    keys: list[tuple[str, str, str]] = []
    for spec in sorted(specs, key=lambda s: (s.trojan_id, s.role != "clean")):
        keys.append((spec.trojan_id, spec.role, "identity"))
        for form, _text in sorted(spec.restructured):
            keys.append((spec.trojan_id, spec.role, form))
    return {k: f"pp{i:04d}" for i, k in enumerate(keys, 1)}


def package_proc_pilot2(
    specs: list[ProcCircuitSpec], out_dir: Path, rareness: dict[str, dict[str, object]],
    restructure_forms_attempted: dict[str, list[ProcRestructureAttempt]], seed: int = 0,
    release_name: str = "seeker-proc-v2.0-pilot2",
) -> dict[str, object]:
    """Writes the pilot2 release directory: `circuits/<id>.blif.gz` (opaque id, clean and
    infected, identity form only -- see module docstring), `manifest.json` (no label), and
    `answer_key/` (`labels.json`, `provenance.json`, `renames.json`, `rareness.json`,
    `catalogue.json`, `restructure_attempts.json`, `patches/<trojan_id>.v.gz`,
    `witness/<trojan_id>/<image>.gz`), `SHA256SUMS`, `DATASHEET.md`."""
    from lemanruss.htl.release import gz_bytes, scrub_group, write_sha256sums

    out_dir.mkdir(parents=True, exist_ok=False)
    circuits_dir = out_dir / "circuits"
    answer_dir = out_dir / "answer_key"
    circuits_dir.mkdir()
    answer_dir.mkdir()
    (answer_dir / "patches").mkdir()
    (answer_dir / "witness").mkdir()

    ids = _neutral_ids(specs)
    labels: dict[str, str | None] = {}
    provenance: dict[str, dict[str, object]] = {}
    renames: dict[str, dict[str, str]] = {}
    manifest_circuits: list[dict[str, object]] = []
    catalogue: dict[str, dict[str, object]] = {}
    clean_twin_id = {s.trojan_id: ids[(s.trojan_id, "clean", "identity")] for s in specs}

    for spec in specs:
        identity_id = ids[(spec.trojan_id, spec.role, "identity")]
        texts = {identity_id: spec.identity_text}
        form_of = {identity_id: "identity"}
        for form, text in sorted(spec.restructured):
            cid = ids[(spec.trojan_id, spec.role, form)]
            texts[cid] = text
            form_of[cid] = form
        new_texts, mapping = scrub_group(texts, spec.identity_text, identity_id, seed)
        for cid, text in new_texts.items():
            if "__htl_" in text:
                raise RuntimeError(f"{cid}: __htl_ token survived the scrub")
            data = gz_bytes(text)
            (circuits_dir / f"{cid}.blif.gz").write_bytes(data)
            manifest_circuits.append({
                "id": cid, "base": spec.base, "file": f"circuits/{cid}.blif.gz",
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            })
            labels[cid] = spec.trojan_id if spec.role == "infected" else None
            provenance[cid] = {
                "base": spec.base, "source": identity_id, "restructuring": form_of[cid],
                "role": spec.role, "clean_twin": clean_twin_id[spec.trojan_id],
            }
            if mapping and any(k in texts[cid] for k in mapping):
                renames[cid] = {v: k for k, v in mapping.items() if k in texts[cid]}
        if spec.role == "infected":
            catalogue[spec.trojan_id] = {
                "base": spec.base, "trigger_kind": spec.trigger_kind,
                "payload_kind": spec.payload_kind,
                "magic_words": [f"0x{w:08x}" for w in spec.magic_words],
            }
            (answer_dir / "patches" / f"{spec.trojan_id}.v.gz").write_bytes(
                gzip.compress(spec.patched_text.encode(), mtime=0))
            wdir = answer_dir / "witness" / spec.trojan_id
            wdir.mkdir(parents=True)
            for name, data in spec.witness_image.items():
                (wdir / f"{name}.gz").write_bytes(gzip.compress(data, mtime=0))

    by_base: dict[str, int] = {}
    for c in manifest_circuits:
        by_base[str(c["base"])] = by_base.get(str(c["base"]), 0) + 1
    manifest = {
        "release": release_name, "family": release_name, "schema": 2,
        "restructurings_attempted": sorted({
            a.form for lst in restructure_forms_attempted.values() for a in lst
        }),
        "counts": {"circuits": len(manifest_circuits), "by_base": dict(sorted(by_base.items()))},
        "circuits": sorted(manifest_circuits, key=lambda c: str(c["id"])),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                                            encoding="utf-8")
    (answer_dir / "labels.json").write_text(json.dumps(labels, indent=1, sort_keys=True) + "\n",
                                             encoding="utf-8")
    (answer_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (answer_dir / "renames.json").write_text(json.dumps(renames, indent=1, sort_keys=True) + "\n",
                                              encoding="utf-8")
    (answer_dir / "catalogue.json").write_text(
        json.dumps(catalogue, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (answer_dir / "rareness.json").write_text(json.dumps(rareness, indent=1, sort_keys=True) + "\n",
                                               encoding="utf-8")
    (answer_dir / "restructure_attempts.json").write_text(json.dumps(
        {base: [asdict_attempt(a) for a in lst] for base, lst in
         restructure_forms_attempted.items()}, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    (out_dir / "DATASHEET.md").write_text(
        _pilot2_datasheet(manifest, catalogue, restructure_forms_attempted, release_name),
        encoding="utf-8")
    write_sha256sums(out_dir)
    return {"release": release_name, "circuits": len(manifest_circuits),
            "clean": sum(1 for v in labels.values() if v is None),
            "infected": sum(1 for v in labels.values() if v is not None),
            "renamed_circuits": len(renames)}


def asdict_attempt(a: ProcRestructureAttempt) -> dict[str, object]:
    return {"role": a.role, "form": a.form, "verdict": a.verdict, "seconds": round(a.seconds, 1),
            "note": a.note}


def _pilot2_datasheet(
    manifest: dict[str, object], catalogue: dict[str, dict[str, object]],
    restructure_forms_attempted: dict[str, list[ProcRestructureAttempt]],
    release_name: str = "seeker-proc-v2.0-pilot2",
) -> str:
    counts = manifest["counts"]
    assert isinstance(counts, dict)
    is_pilot3 = release_name == "seeker-proc-v2.0-pilot3"
    lineage = (
        f"Family: Seeker-Proc. Version {release_name.rsplit('-', 1)[-1]} (round 9, 2026-11-02; "
        "supersedes seeker-proc-v2.0-pilot2: magic-number triggers only, `t-seq-pattern` "
        "(a small FSM, adds a register) dropped from the trojan set so every infected circuit's "
        "flip-flop/latch count equals its clean twin's exactly -- see docs/results-round9.md "
        "section 'Seeker-Proc pilot3'). Produced by Leman Russ III (Yggdrasil III)."
        if is_pilot3 else
        "Family: Seeker-Proc. Version 2.0-pilot2 (fix round, 2026-11-01; supersedes "
        "seeker-proc-v2.0-pilot, which leaked circuit/trojan identity through directory names "
        "and manifest keys even though file content was leak-scanned clean -- see README entry "
        "and docs/results-round7.md section 7). Produced by Leman Russ III (Yggdrasil III)."
    )
    lines = [
        f"# {release_name} datasheet",
        "",
        lineage,
        "",
        "Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to "
        "detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.",
        "",
        "## Contents",
        "",
        f"- circuits: {counts['circuits']} in `circuits/<id>.blif.gz` (gzip, zero timestamp), "
        f"opaque ids (`pp0001`, ...); clean and infected, one trojan per base pair "
        f"({', '.join(sorted(catalogue))}).",
        "- form: the lowered netlist only (`read_verilog; proc; opt; lower; write_blif "
        "--gates-as-names`), identity (unrestructured). No ABC-restructured form is released "
        "this round: every one of the 18 forms fails at ABC's `read_blif` before the "
        "restructuring-specific commands run (restructure_attempts.json; see DATASHEET section "
        "below).",
        "- answer key: `answer_key/` (labels, provenance, renames, rareness, catalogue, the "
        "patched RTL under `patches/`, the witness program image under `witness/`); a detector "
        "must not read it. Clean circuits carry no label and infected circuits carry no label "
        "in `circuits/` or `manifest.json`.",
        "",
        "## Restructuring attempts (brief item (c))",
        "",
    ]
    for base, attempts in sorted(restructure_forms_attempted.items()):
        for a in attempts:
            lines.append(f"- {base} ({a.role}): `{a.form}` -- {a.verdict}, {a.seconds:.0f}s"
                         f"{': ' + a.note if a.note else ''}")
    lines += [
        "",
        "Every attempt above failed at ABC's own `read_blif` (before any restructuring-specific "
        "command runs), so the same outcome applies to all 18 forms without repeating it 18 "
        "times per circuit (brief: \"a stated subset\" is allowed when wall time does not): "
        "darkriscv's lowered netlist has a genuine sequential loop ABC's reader refuses; mcu's "
        "lowered netlist has Odin III's own deeply parameterized hierarchical module names "
        "(`$RESET_PC=32'b0...`, `$h<hash>`), which ABC's BLIF reader mis-parses at the `$`/`='` "
        "characters when resolving a `.subckt` box. Neither is an Odin III bug (not changed "
        "here); recorded for the controller.",
        "",
        "## Names",
        "",
        "Every net the inserter added is renamed to a neutral name in the style of the circuit's "
        "own clean twin (`lemanruss.htl.release.scrub_group`, the same mechanism the Seeker-Comb/"
        "Seq families use); `answer_key/renames.json` maps them back. No directory name, file "
        "name or manifest key carries the label vocabulary (`proc_release.NAME_VOCAB`); "
        "`lemanruss.htl.proc_release.check_name_vocabulary` checks this directly.",
        "",
        "## Fetch and check",
        "",
        "`sha256sum -c SHA256SUMS`, then `lemanruss.htl.proc_release.verify_proc_pilot2`.",
        "",
    ]
    return "\n".join(lines)


# ---- witness check on the released netlists (brief item (e)) -------------------------------

@dataclass(frozen=True)
class WitnessCheckResult:
    trojan_id: str
    fires: bool  # infected differs from clean on the witness program
    clean_trace: str
    infected_trace: str
    ok: bool
    note: str = ""


def witness_check_released(
    out_dir: Path, trojan_id: str, base: str, clean_id: str, infected_id: str, top: str,
    tb_file: Path, odin3_bin: Path, scratch: Path,
) -> WitnessCheckResult:
    """Unpacks `circuits/<clean_id>.blif.gz` and `circuits/<infected_id>.blif.gz` and runs
    `read_blif <netlist>; sim_tb --out <tag>.txt <tb_file>` on each (the same check round 7 ran
    on the pre-release netlist, now against the released, scrubbed, `--gates-as-names`
    artifact). Odin III's own `read_verilog` resolves `$readmemh` when the Verilog is first read
    (the witness program is baked into the lowered netlist's `.latch` init bits, not reloaded at
    simulation time -- measured: `sim_tb` on a packaged netlist reproduces round 7's trace with
    no witness file present at all), so no witness file needs copying here; `answer_key/witness/
    <trojan_id>/` keeps the program image for provenance only. `fires` is True when the two
    traces differ (the brief's "fire on witness"); this function does not itself judge "silent
    on shipped programs" -- a shipped-program check needs a netlist built with that program's
    memory baked in instead, and is not repeated here (carried forward from round 7's
    measurement on the same, unchanged, RTL patch; docs/results-round7.md section 4)."""
    import shutil

    scratch.mkdir(parents=True, exist_ok=True)
    shutil.copy(tb_file, scratch / tb_file.name)

    def run_one(cid: str, tag: str) -> str:
        with gzip.open(out_dir / "circuits" / f"{cid}.blif.gz", "rt", encoding="utf-8") as fh:
            (scratch / f"{tag}.blif").write_text(fh.read(), encoding="utf-8")
        res = subprocess.run(
            [str(odin3_bin), "--top", top, "-p",
             f"read_blif {tag}.blif; sim_tb --out {tag}.out.txt {tb_file.name}"],
            cwd=scratch, capture_output=True, text=True, timeout=300, check=False,
        )
        if res.returncode != 0:
            raise RuntimeError(f"witness_check_released: sim_tb failed: {res.stdout}\n{res.stderr}")
        return (scratch / f"{tag}.out.txt").read_text(encoding="utf-8")

    clean_trace = run_one(clean_id, "clean")
    infected_trace = run_one(infected_id, "infected")
    fires = clean_trace != infected_trace
    return WitnessCheckResult(trojan_id, fires, clean_trace, infected_trace, ok=fires)


# ---- pilot2 verify (brief item (d)) ----------------------------------------------------------

# A circuit holding this is pilot1's own scrub signature (`proc_release.scrub`'s `_insN`
# counter): the controller's finding (2) was that this pattern exists only in infected
# circuits, so by itself it tells a detector a circuit is infected even after the `__htl_*`
# names it replaces are gone. Pilot2 does not produce this pattern (its scrub is
# `lemanruss.htl.release.scrub_group`, styled to the circuit's own clean twin); this check is a
# regression guard, not something pilot2's own output is expected to ever trip.
_INS_PATTERN = re.compile(r"\b_ins\d+\b")


@dataclass
class ProcPilot2VerifyResult:
    integrity_ok: bool
    integrity_errors: list[str]
    name_vocab_ok: bool
    name_vocab_hits: list[str]
    content_leak_ok: bool
    content_leaks: list[str]
    infected_only_pattern_ok: bool
    infected_only_pattern_hits: list[str]
    labels_present: bool

    @property
    def ok(self) -> bool:
        return (self.integrity_ok and self.name_vocab_ok and self.content_leak_ok
                and self.infected_only_pattern_ok and self.labels_present)


def verify_proc_pilot2(out_dir: Path) -> ProcPilot2VerifyResult:
    """Independent re-check of a pilot2 release directory from disk: SHA256SUMS + manifest hash/
    size integrity, the name-vocabulary check (`check_name_vocabulary`, the same one
    `verify_proc_release` now runs), a content leak scan (`LEAK_TOKENS` plus `NAME_VOCAB`, with
    the family's native-vs-leak rule: a token the circuit's own clean twin also holds is native,
    not a leak -- see `relverify.check_leak`), a check that no circuit holds the pilot1 scrub's
    own `_insN` pattern (`_INS_PATTERN`, the controller's finding (2): a pattern that by itself
    marked a circuit infected), and that every manifest circuit has a label entry.

    Deliberately does *not* require every added net name to match its clean twin's numeric
    style: an infected identity circuit legitimately keeps a few plain, base-RTL-sourced names
    (e.g. mcu's own `flush_fetch_receive`, now also consumed by the Trojan's trigger FSM) that
    a clean build's optimiser renames or folds away differently -- spec section 10.2's own rule
    ("residual structure... is the Trojan itself, not a label") covers this; only a vocabulary
    hit or the `_insN` pattern is treated as a label leak."""
    from lemanruss.htl.release import read_blif_gz, sha256_file

    errors: list[str] = []
    sums_path = out_dir / "SHA256SUMS"
    if not sums_path.exists():
        return ProcPilot2VerifyResult(False, ["SHA256SUMS missing"], False, [], False, [], False,
                                       [], False)
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        digest, _, rel = line.partition("  ")
        path = out_dir / rel
        if not path.exists() or sha256_file(path) != digest:
            errors.append(f"hash mismatch or missing: {rel}")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    circuits = manifest["circuits"]
    for c in circuits:
        f = out_dir / str(c["file"])
        if not f.is_file() or sha256_file(f) != c["sha256"] or f.stat().st_size != c["bytes"]:
            errors.append(f"manifest hash/size mismatch: {c['file']}")

    nv = check_name_vocabulary(out_dir)

    prov = json.loads((out_dir / "answer_key" / "provenance.json").read_text(encoding="utf-8"))
    catalogue = json.loads((out_dir / "answer_key" / "catalogue.json").read_text(encoding="utf-8"))
    extra = set()
    for t in catalogue.values():
        extra.add(str(t["trigger_kind"]))
        extra.add(str(t["payload_kind"]))
    pat = re.compile("|".join(re.escape(w) for w in (*LEAK_TOKENS, *NAME_VOCAB, *extra)), re.I)

    groups: dict[str, list[str]] = {}
    for cid, p in prov.items():
        groups.setdefault(str(p["clean_twin"]), []).append(cid)
    content_leaks: list[str] = []
    pattern_hits: list[str] = []
    for clean_id, cids in sorted(groups.items()):
        clean_text = read_blif_gz(out_dir / "circuits" / f"{clean_id}.blif.gz")
        native = set(clean_text.split())
        for cid in cids:
            text = read_blif_gz(out_dir / "circuits" / f"{cid}.blif.gz")
            for tok in set(text.split()):
                if pat.search(tok) and tok not in native:
                    content_leaks.append(f"{cid}: token {tok}")
                if _INS_PATTERN.search(tok):
                    pattern_hits.append(f"{cid}: token {tok}")

    labels = json.loads((out_dir / "answer_key" / "labels.json").read_text(encoding="utf-8"))
    labels_present = all(str(c["id"]) in labels for c in circuits)

    return ProcPilot2VerifyResult(
        not errors, errors, nv.ok, nv.hits,
        not content_leaks, content_leaks, not pattern_hits, pattern_hits, labels_present,
    )
