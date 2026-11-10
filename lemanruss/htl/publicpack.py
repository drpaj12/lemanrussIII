"""Public Seeker v2.0 packages: family README text, deterministic tarballs, index pages.

Everything a reader sees about a public benchmark (family README, `docs/benchmarks/` pages,
`MANIFEST.md`) is generated here from the staged package tree, so pages cannot drift from the
tarballs. Nothing here reads an answer key: only file names and counts of the public tree.

    python -m lemanruss.htl.publicpack readmes PUBLIC     # rewrite <family>/README.md
    python -m lemanruss.htl.publicpack retar PUBLIC FAMILY  # rebuild <family> -all tarball + sums
    python -m lemanruss.htl.publicpack docs PUBLIC DOCS_DIR  # docs/benchmarks pages
    python -m lemanruss.htl.publicpack manifest PUBLIC    # tarballs/MANIFEST.md
    python -m lemanruss.htl.publicpack datasheet IN OUT   # public form of a private datasheet
"""

from __future__ import annotations

import hashlib
import re
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

RELEASE_TAG = "seeker-v2.0"
RELEASE_URL = f"https://github.com/drpaj12/lemanrussIII/releases/download/{RELEASE_TAG}"
FAMILIES = ("comb", "seq", "proc")
FAMILY_TITLE = {"comb": "Comb", "seq": "Seq", "proc": "Proc"}
SET_ORDER = ("K4", "K6", "gates", "silicon")
STIM_FILES = ("vectors.txt", "sequence.txt", "neutral-program.hex")
SHORT_SEQ_NOTE = (
    "The neutral sequence is shorter than 64 cycles: it has to stay neutral (no Trojan of this "
    "benchmark's sets reacts to it) and no longer neutral sequence was found."
)
NOTICE = {
    "ISCAS-85": (
        "ISCAS-85 benchmark circuit (Brglez and Fujiwara, 1985), distributed as VTR/MCNC test "
        "material; no licence text is attached to the netlists. Attribution to the original "
        "authors; takedown contact: the repository owner."
    ),
    "ISCAS-89": (
        "ISCAS-89 benchmark circuit (Brglez, Bryan and Kozminski, 1989); no licence text is "
        "attached to the netlists. Attribution to the original authors; takedown contact: the "
        "repository owner."
    ),
    "OpenCores": (
        "OpenCores project; the project's own copyright notice and licence terms apply to the "
        "derived circuits and are kept with this package (see the family datasheet)."
    ),
    "VTR (OpenCores sha)": (
        "OpenCores sha core as shipped in the VTR benchmark set; its permissive notice (copyright "
        "statement not removed, derivative works keep the notice) applies."
    ),
    "core": (
        "Open-source processor core; its licence applies to the derived circuits (see the "
        "family datasheet)."
    ),
}
CORE_LABEL = {
    "mcu": "BRISC-V mcu (Arduino-on-RISC-V, MIT)",
    "picorv32": "PicoRV32 (YosysHQ, ISC)",
    "mips_16": "OpenCores mips_16",
}
_SUBMIT = """# How to submit (summary)

Per benchmark you get a golden and sets of exactly 100 circuits (K4, K6, gates, and silicon \
where it exists).
Each set is one scoring unit named `<benchmark>-K4`, `<benchmark>-K6`, `<benchmark>-gates`, \
`<benchmark>-silicon`;
`<benchmark>` is all its sets together. Fill one CSV per unit: header lines \
`# seeker-release: seeker-{fam}-v2.0`,
`# subset: <unit>`, `# detector:`, `# team:`; then `id,infected,score,count,locations` and one \
row per circuit.
`infected` is 0/1, `score` a finite number (higher = more likely infected), `count` 0..3 \
(optional), `locations` up to
10 net names (optional). The scorer returns aggregates only (confusion matrix, TPR, FPR, AUROC, \
found-rate by Trojan
count). The circuits of a set carry no label. Details: docs/user/SUBMISSION.md in the repository.
"""


def source_of(family: str, bench: str) -> str:
    """Source collection of a public benchmark (same rule as the packaging run)."""
    if family == "proc":
        return "core"
    if re.fullmatch(r"s\d+", bench):
        return "ISCAS-89"
    if re.fullmatch(r"C\d+", bench):
        return "ISCAS-85"
    if bench in ("ca_prng", "i2c"):
        return "OpenCores"
    if bench == "sha":
        return "VTR (OpenCores sha)"
    return "other"


def submit_text(family: str) -> str:
    """The 'How to submit (summary)' block, ending in a newline."""
    return _SUBMIT.format(fam=family)


def family_readme(family: str) -> str:
    """Family README: title, one sentence, blank line, then the submit block."""
    return (
        f"# Seeker's Dilemma v2.0, family {family}: public package\n\n"
        "One directory per benchmark (see each README).\n\n" + submit_text(family)
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def det_tar(src: Path, dst: Path) -> None:
    """Deterministic .tar.gz of `src` (members named relative to src.parent, mtime 0)."""
    files = sorted(p for p in src.rglob("*") if p.is_file())
    with tarfile.open(dst, "w:gz", compresslevel=9, format=tarfile.PAX_FORMAT) as tf:
        for p in files:
            ti = tarfile.TarInfo(str(p.relative_to(src.parent)))
            ti.size = p.stat().st_size
            ti.mtime = 0
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            ti.mode = 0o644
            with p.open("rb") as fh:
                tf.addfile(ti, fh)
    raw = bytearray(dst.read_bytes())
    raw[4:8] = b"\0\0\0\0"  # gzip header mtime
    dst.write_bytes(bytes(raw))


def write_tar_sums(tars: Path) -> None:
    lines = [f"{sha256_file(p)}  {p.name}\n" for p in sorted(tars.glob("*.tar.gz"))]
    (tars / "SHA256SUMS").write_text("".join(lines))


@dataclass(frozen=True)
class Bench:
    family: str
    name: str
    source: str
    sets: tuple[tuple[str, int], ...]
    stimulus: str
    cycles: int | None
    has_silicon_golden: bool

    @property
    def circuits(self) -> int:
        return sum(n for _, n in self.sets)

    @property
    def asset(self) -> str:
        return f"seeker-{self.family}-v2.0-{self.name}.tar.gz"

    @property
    def label(self) -> str:
        return CORE_LABEL.get(self.name, self.name)


def scan_bench(public: Path, family: str, name: str) -> Bench:
    d = public / family / name
    sets = tuple(
        (s, len(list((d / s).glob("*.blif.gz")))) for s in SET_ORDER if (d / s).is_dir()
    )
    stim = ""
    cycles: int | None = None
    for f in STIM_FILES:
        if (d / "stimulus" / f).is_file():
            stim = f
            lines = (d / "stimulus" / f).read_text().splitlines()
            if family in ("comb", "seq"):
                cycles = len(lines) - 1  # first line names the inputs
    return Bench(
        family,
        name,
        source_of(family, name),
        sets,
        stim,
        cycles,
        (d / "golden.silicon.blif.gz").is_file(),
    )


def scan_public(public: Path) -> list[Bench]:
    out: list[Bench] = []
    for fam in FAMILIES:
        fdir = public / fam
        if fdir.is_dir():
            out += [scan_bench(public, fam, p.name) for p in sorted(fdir.iterdir()) if p.is_dir()]
    return out


def _stimulus_text(b: Bench) -> str:
    if b.family == "comb":
        return f"`stimulus/vectors.txt`: {b.cycles} neutral input vectors."
    if b.family == "seq":
        text = f"`stimulus/sequence.txt`: a neutral input sequence of {b.cycles} cycles from reset."
        if b.cycles is not None and b.cycles < 64:
            text += " " + SHORT_SEQ_NOTE
        return text
    return "`stimulus/neutral-program.hex`: the neutral program."


def _sets_text(b: Bench) -> str:
    return ", ".join(f"{s} ({n})" for s, n in b.sets)


def index_page(b: Bench) -> str:
    """One `docs/benchmarks/<family>/<benchmark>.md` page."""
    fam_asset = f"seeker-{b.family}-v2.0-all.tar.gz"
    golden = "`golden.blif.gz`" + (
        " and `golden.silicon.blif.gz`" if b.has_silicon_golden else ""
    )
    rows = "".join(f"| {s} | {n} |\n" for s, n in b.sets)
    return (
        f"# {b.label} ({FAMILY_TITLE[b.family]}, Seeker's Dilemma v2.0)\n\n"
        f"Benchmark key: `{b.name}`. Family: {FAMILY_TITLE[b.family]}. "
        f"Release: `{RELEASE_TAG}`.\n\n"
        "## Source and attribution\n\n"
        f"Source: {b.source}. {NOTICE.get(b.source, '')}\n\n"
        "## Contents\n\n"
        f"Golden (the clean circuit): {golden}.\n\n"
        f"| set | circuits |\n|---|---|\n{rows}\n"
        f"Total: {b.circuits} circuits. Circuit ids are opaque and no label is published.\n\n"
        "## Stimulus\n\n" + _stimulus_text(b) + "\n\n"
        "## Download\n\n"
        f"- This benchmark: [{b.asset}]({RELEASE_URL}/{b.asset})\n"
        f"- Whole {FAMILY_TITLE[b.family]} family: [{fam_asset}]({RELEASE_URL}/{fam_asset})\n"
        f"- Checksums: [SHA256SUMS]({RELEASE_URL}/SHA256SUMS)\n\n"
        "## How to submit\n\n"
        "Scoring units are `" + f"{b.name}-<set>" + "` for each set above and `" + b.name + "`"
        " for all its sets together. See [SUBMISSION.md](../../user/SUBMISSION.md).\n"
        "Scoring opens when the seeker-scoring service is live; see SUBMISSION.md.\n"
    )


def index_readme(benches: list[Bench]) -> str:
    """`docs/benchmarks/README.md`: the table of all public benchmarks."""
    out = [
        "# Seeker's Dilemma v2.0: public benchmarks\n\n",
        f"Release tag `{RELEASE_TAG}` on drpaj12/lemanrussIII. Downloads: "
        f"`{RELEASE_URL}/<asset>`; `SHA256SUMS` and `MANIFEST.md` list every asset.\n\n",
        "Scoring opens when the seeker-scoring service is live; see SUBMISSION.md "
        "([docs/user/SUBMISSION.md](../user/SUBMISSION.md)).\n\n",
        "Whole-family downloads: "
        + ", ".join(
            f"[{FAMILY_TITLE[f]}]({RELEASE_URL}/seeker-{f}-v2.0-all.tar.gz)" for f in FAMILIES
        )
        + ".\n\n",
        "| family | benchmark | source | sets (circuits) | download |\n|---|---|---|---|---|\n",
    ]
    for b in benches:
        link = f"[{b.name}]({b.family}/{b.name}.md)"
        dl = f"[{b.asset}]({RELEASE_URL}/{b.asset})"
        out.append(
            f"| {FAMILY_TITLE[b.family]} | {link} | {b.source} | {_sets_text(b)} | {dl} |\n"
        )
    return "".join(out)


def manifest_md(public: Path) -> str:
    """`tarballs/MANIFEST.md`: asset, size, sha256, content, for the release body."""
    tars = public / "tarballs"
    benches = {(b.family, b.name): b for b in scan_public(public)}
    out = [
        f"# Seeker's Dilemma v2.0 assets ({RELEASE_TAG})\n\n",
        "| asset | size (bytes) | sha256 | content |\n|---|---|---|---|\n",
    ]
    for p in sorted(tars.glob("*.tar.gz")):
        m = re.fullmatch(r"seeker-(\w+)-v2\.0-(.+)\.tar\.gz", p.name)
        assert m is not None, p.name
        fam, name = m.group(1), m.group(2)
        if name == "all":
            fb = [b for (f, _), b in benches.items() if f == fam]
            content = (
                f"family {FAMILY_TITLE[fam]}: {len(fb)} benchmarks, "
                f"{sum(b.circuits for b in fb)} circuits"
            )
        else:
            b = benches[(fam, name)]
            content = f"{FAMILY_TITLE[fam]} {name}: {b.circuits} circuits ({_sets_text(b)})"
        out.append(f"| {p.name} | {p.stat().st_size} | {sha256_file(p)} | {content} |\n")
    out.append("\n`SHA256SUMS` lists the same checksums for `sha256sum -c`.\n")
    return "".join(out)


PER_SET_SENTENCE = (
    "Per-set infected counts are part of the answer key; each set has a random 10 to 70 of 100 "
    "infected."
)
_INF_CLEAN_HEAD = re.compile(r"\binf/clean\b")
_DRAWN_HEAD = re.compile(r"drawn / infected / clean")
_PER_FORM = re.compile(r"\b(gates|lut4|lut6|silicon) \d+ infected, (\d+) differing")


def _table_end(lines: list[str], start: int) -> int:
    i = start
    while i < len(lines) and lines[i].startswith("|"):
        i += 1
    return i


def _keep_columns(row: str, keep: list[int]) -> str:
    cells = row.strip().strip("|").split("|")
    return "|" + "|".join(cells[i] for i in keep if i < len(cells)) + "|"


def public_datasheet(text: str) -> str:
    """Public form of a (private) datasheet: no per-set or per-benchmark infected/clean counts.

    Drops `inf/clean` tables (replaced by one sentence), removes the `drawn / infected / clean`
    columns of the bases table, removes per-form infected counts from the stimulus check and the
    per-benchmark Trojan counts paragraph. Dropped-cell causes stay.
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and _INF_CLEAN_HEAD.search(ln):
            out.append(PER_SET_SENTENCE)
            i = _table_end(lines, i)
            continue
        if ln.startswith("|") and _DRAWN_HEAD.search(ln):
            end = _table_end(lines, i)
            head = ln.strip().strip("|").split("|")
            keep = [k for k, c in enumerate(head) if "infected" not in c]
            out += [_keep_columns(r, keep) for r in lines[i:end]]
            i = end
            continue
        if ln.startswith("Data only, no rejection:"):
            i += 1
            continue
        out.append(_PER_FORM.sub(r"\1 \2 differing", ln))
        i += 1
    return "\n".join(out)


def has_per_set_counts(text: str) -> list[str]:
    """Lines of a datasheet or page that still carry per-set or per-benchmark infected counts."""
    bad = [r"\binf/clean\b", r"drawn / infected / clean", r"\d+ infected, \d+ differing",
           r"^Data only, no rejection", r"\d+ / \d+ \| \d+ / \d+"]
    return [ln for ln in text.split("\n") if any(re.search(b, ln) for b in bad)]


def write_readmes(public: Path) -> None:
    for fam in FAMILIES:
        if (public / fam).is_dir():
            (public / fam / "README.md").write_text(family_readme(fam))


def write_docs(public: Path, docs_dir: Path) -> int:
    benches = scan_public(public)
    for b in benches:
        page = docs_dir / b.family / f"{b.name}.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(index_page(b))
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "README.md").write_text(index_readme(benches))
    return len(benches)


def retar_family(public: Path, family: str) -> Path:
    tars = public / "tarballs"
    dst = tars / f"seeker-{family}-v2.0-all.tar.gz"
    det_tar(public / family, dst)
    write_tar_sums(tars)
    return dst


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "readmes" and len(argv) == 3:
        write_readmes(Path(argv[2]))
    elif cmd == "retar" and len(argv) == 4:
        print(retar_family(Path(argv[2]), argv[3]))
    elif cmd == "docs" and len(argv) == 4:
        print(write_docs(Path(argv[2]), Path(argv[3])), "pages")
    elif cmd == "datasheet" and len(argv) == 4:
        Path(argv[3]).write_text(public_datasheet(Path(argv[2]).read_text()))
    elif cmd == "manifest" and len(argv) == 3:
        pub = Path(argv[2])
        (pub / "tarballs" / "MANIFEST.md").write_text(manifest_md(pub))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
