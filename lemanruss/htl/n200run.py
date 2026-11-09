"""Seeker v2.0 at n = 300 per base (rc4): family runner, answer-key assembly and report tables.

Spec: docs/specs/2026-11-01-seeker-n200-design.md. `run_family` builds the bases smallest first in
a fork pool; `assemble` writes the family-level files from the per-base results.
"""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

from lemanruss.htl.families import ADDS, LINEAGE, VERSION
from lemanruss.htl.n200 import build_base
from lemanruss.htl.n200check import Json
from lemanruss.htl.n200plan import TSpec, trojan_of
from lemanruss.htl.seqoc import source_of

BLOCK = 301  # ids reserved per base: golden + 3 sets of 100


def gate_count(path: Path) -> int:
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines()
               if ln.startswith(".names"))


def run_family(
    family: str, bases: list[Path], out: Path, seed: int = 0, workers: int = 1,
    max_gates: int = 10**9,
) -> list[Json]:
    """Builds every base (smallest first) and writes the family files; returns the per-base
    results. Bases above `max_gates` are recorded as not built."""
    order = sorted(bases, key=lambda p: (gate_count(p), p.stem))
    jobs = [(family, p, out, i * BLOCK + 1, seed) for i, p in enumerate(order)
            if gate_count(p) <= max_gates]
    skipped = [p.stem for p in order if gate_count(p) > max_gates]
    (out / "answer_key").mkdir(parents=True, exist_ok=True)
    if workers <= 1:
        results = [build_base(j) for j in jobs]
    else:
        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(workers) as pool:
            results = list(pool.imap(build_base, jobs, chunksize=1))
    assemble(family, out, results, skipped, seed)
    return results


def _tid(spec: Json) -> str:
    return trojan_of(_spec(spec)).id


def _spec(d: Json) -> TSpec:
    nets = d["nets"]
    assert isinstance(nets, list)
    return TSpec(str(d["trig"]), tuple((str(n[0]), int(n[1])) for n in nets), int(str(d["size"])),
                 str(d["band"]), str(d["payload"]), str(d["victim"]), int(str(d["param"])),
                 bool(d["isolate"]), float(str(d["sel_p"])))


def assemble(
    family: str, out: Path, results: list[Json], skipped: list[str], seed: int
) -> None:
    key = out / "answer_key"
    circuits: list[dict[str, str]] = []
    labels: dict[str, str | None] = {}
    sets: dict[str, Json] = {}
    trojans: dict[str, list[Json]] = {}
    scripts: dict[str, Json] = {}
    cuts: dict[str, Json] = {}
    records: list[Json] = []
    failures: list[Json] = []
    goldens: dict[str, str] = {}
    catalogue: dict[str, Json] = {}
    for r in results:
        base = str(r["base"])
        gid = str(r["golden"])
        goldens[base] = gid
        circuits.append({"id": gid, "base": base, "file": f"circuits/{gid}.blif"})
        labels[gid] = None
        failures += [f for f in r["failures"]] if isinstance(r["failures"], list) else []
        per_set: dict[str, Json] = {}
        rsets = r.get("sets")
        assert isinstance(rsets, dict)
        for name, v in rsets.items():
            per_set[name] = {**v, "infected_ids": [], "clean_ids": []}
        cs = r["circuits"]
        assert isinstance(cs, list)
        for c in cs:
            cid = str(c["id"])
            circuits.append({"id": cid, "base": base, "file": f"circuits/{cid}.blif"})
            scripts[cid] = {"set": c["set"], "map": c["map"], "script": c["script"]}
            cuts[cid] = {"sizes": c.get("cut_sizes", []), "labels": c.get("cut_labels", []),
                         "rings": c.get("rings", {}), "slow_depth": c.get("slow_depth"),
                         "slow_depth_ref": c.get("slow_depth_ref")}
            specs = c.get("specs")
            if isinstance(specs, list):
                tids = [_tid(sp) for sp in specs]
                labels[cid] = "+".join(tids)
                trojans[cid] = specs
                for sp, tid in zip(specs, tids, strict=True):
                    catalogue.setdefault(tid, trojan_of(_spec(sp)).to_dict())
                records += c["records"]
                _lst_of(per_set[str(c["set"])], "infected_ids").append(cid)
            else:
                labels[cid] = None
                _lst_of(per_set[str(c["set"])], "clean_ids").append(cid)
        sets[base] = {"golden": gid, "kind": r.get("kind"), "gates": r.get("gates"),
                      "sets": per_set}
    for name in skipped:
        failures.append({"base": name, "set": "all", "reason": "not built (size cap)"})
    infected = sum(1 for v in labels.values() if v is not None)
    manifest: Json = {
        "family": family, "version": VERSION, "schema": 4, "v1_lineage": LINEAGE[family],
        "adds": ADDS[family],
        "bases": sorted(goldens), "goldens": goldens,
        "trojans": sorted(catalogue), "trojan_catalogue": catalogue,
        "circuits": sorted(circuits, key=lambda c: c["id"]),
        "mix": {"clean": len(labels) - infected, "infected": infected,
                "infected_fraction": infected / len(labels) if labels else 0},
        "seed": seed,
        "labels": "answer_key/labels.json (separate; a detector must not read answer_key/)",
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, obj in (("labels", labels), ("scripts", scripts), ("sets", sets),
                      ("trojans", trojans), ("rareness", records), ("failures", failures),
                      ("cuts", cuts)):
        (key / f"{name}.json").write_text(
            json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _lst_of(d: Json, k: str) -> list[str]:
    v = d[k]
    assert isinstance(v, list)
    return v


DESIGN_MD = (
    "## Design (round 8, rc4; rc5 latch fix; rc5 Comb / rc6 Seq cut-and-stitch)\n\n"
    "Per base: the golden (its id is in `manifest.json` under `goldens`) and three sets of 100 "
    "circuits: LUT k = 4, LUT k = 6, and an AND / OR / NOT gate library. In each set a random "
    "number between 10 and 70 of the circuits is infected, with 1 to 3 Trojans each (stuck "
    "output, bit error on an upper-half or lower-half output, and in rc5 / rc6 energy ring and "
    "slowdown); the others are clean. Every "
    "circuit other than the golden, clean or infected, is one Trojan insertion (infected only), "
    "then its own random ABC logic-optimisation script, then the set's mapping by Odin III, then "
    "shuffled ports and blocks and fresh net names; there is no provenance in the files. Which "
    "circuits are infected, the set, the script and the Trojans are in the answer key only. A "
    "base that cannot supply 100 distinct circuits in a set has fewer (never padded with "
    "copies); the counts are in `answer_key/sets.json` and in the tables below. Every infected "
    "circuit has, per Trojan, a witness input sequence (`answer_key/witnesses/`) replayed in "
    "Odin III's simulator on the finished circuit against the golden, and is equivalent to its "
    "pre-obfuscation form (`answer_key/pre/`), which equals the golden with all triggers forced "
    "inactive (ABC cec / dsec). Energy-ring (Seq only) and slowdown payloads are in the "
    "releases rc5 (Comb) and rc6 (Seq) through cut-and-stitch: the part ABC would destroy is cut "
    "out, its boundary exposed as primary inputs/outputs, host and part are each optimised and "
    "mapped, and the pieces are stitched back; every circuit, clean or infected, is cut (a clean "
    "or payload-free circuit on a dummy region of the same size distribution). The slowdown is "
    "an absorption stage `tmp | (tmp & s) ...` (equal to `tmp`, adds depth, always on), not a "
    "buffer chain. Spec section 13. rc5: the Trojan's flip-flops carry the circuit's own "
    "`.latch` type, clock and init value (rc4 gave them init 0 where every other latch has 2, "
    "which separated the labels); a pattern trigger's first stage is a two-input cell and the "
    "trigger is the sticky flag itself, so no inverter or duplicated node sits in front of a "
    "Trojan latch. All latches start unknown (init 2), read as 0 by every tool of the pipeline.")


# ---- tables ----------------------------------------------------------------------------------

def _within(r: Json, n: str = "1024") -> float:
    w = r["p_fire_within"]
    assert isinstance(w, dict)
    return float(w[n][0])


def _fmt(p: float | None) -> str:
    return "-" if p is None else f"{p:.2e}"


def _quant(vals: list[float]) -> str:
    if not vals:
        return "- | - | -"
    v = sorted(vals)
    return f"{_fmt(v[0])} | {_fmt(v[len(v) // 2])} | {_fmt(v[-1])}"


def tables(root: Path) -> list[str]:
    """Markdown: per base the three sets, per set the payload mix, Trojans per circuit and the
    rareness distribution, failures. Read from the answer key of a build tree or a release."""
    key = root / "answer_key"
    sets: dict[str, Json] = json.loads((key / "sets.json").read_text(encoding="utf-8"))
    recs: list[Json] = json.loads((key / "rareness.json").read_text(encoding="utf-8"))
    scripts: dict[str, Json] = json.loads((key / "scripts.json").read_text(encoding="utf-8"))
    trojans: dict[str, list[Json]] = json.loads((key / "trojans.json").read_text(encoding="utf-8"))
    fails: list[Json] = json.loads((key / "failures.json").read_text(encoding="utf-8"))
    out = ["### Bases and sets", "",
           "| base | source | gates | K4 drawn / infected / clean | "
           "K6 drawn / infected / clean | G drawn / infected / clean |",
           "|---|---|---|---|---|---|"]
    for base, s in sorted(sets.items(), key=lambda kv: (int(str(kv[1].get("gates") or 0)),
                                                         kv[0])):
        ps = s["sets"]
        assert isinstance(ps, dict)
        cells = []
        for name in ("K4", "K6", "G"):
            v = ps.get(name)
            cells.append("- " if v is None else
                         f"{v['n_infected_drawn']} / {len(v['infected_ids'])} / "
                         f"{len(v['clean_ids'])}")
        out.append(f"| {base} | {source_of(base)} | {s.get('gates')} | " + " | ".join(cells) + " |")
    for name in ("K4", "K6", "G"):
        rs = [r for r in recs if scripts[str(r["circuit"])]["set"] == name]
        circ = [c for c, v in scripts.items() if v["set"] == name and c in trojans]
        out += ["", f"### Set {name}: {len(circ)} infected circuits, {len(rs)} Trojans", ""]
        per: dict[int, int] = {}
        for c in circ:
            per[len(trojans[c])] = per.get(len(trojans[c]), 0) + 1
        out.append("Trojans per circuit: " + ", ".join(f"{n}: {c}" for n, c in sorted(per.items())))
        mix: dict[str, int] = {}
        for r in rs:
            mix[str(r["payload"])] = mix.get(str(r["payload"]), 0) + 1
        out += ["", "Payload mix: " + ", ".join(f"{k} {v}" for k, v in sorted(mix.items())), "",
                "| trigger | band | Trojans | stat | min | median | max |",
                "|---|---|---|---|---|---|---|"]
        for trig in sorted({str(r["trigger"]) for r in rs
                            if "p_fire_within" in r or r["trigger"] == "comb"}):
            for band in sorted({str(r["target_band"]) for r in rs if r["trigger"] == trig}):
                sel = [r for r in rs if r["trigger"] == trig and r["target_band"] == band]
                if trig == "comb":
                    out.append(f"| {trig} | {band} | {len(sel)} | p | "
                               f"{_quant([float(str(r['p'])) for r in sel])} |")
                else:
                    out.append(f"| {trig} | {band} | {len(sel)} | P(fire<=1024) | "
                               f"{_quant([_within(r) for r in sel])} |")
    out += ["", "### Failures and short sets", ""]
    seen: dict[str, int] = {}
    for f in fails:
        k = f"{f['base']} [{f['set']}]: {str(f['reason'])[:110]}"
        seen[k] = seen.get(k, 0) + 1
    out += [f"- {k}" + (f" (x{n})" if n > 1 else "") for k, n in sorted(seen.items())]
    return out


def _label_kind(labels: list[object]) -> str:
    for lb in labels:
        s = str(lb)
        if s.startswith("energy"):
            return "energy"
        if s.startswith("slow"):
            return "slow"
    return "dummy"


def cut_table(root: Path) -> list[str]:
    """Markdown (spec section 13): the cut-size distribution of real cuts (energy, slowdown)
    against dummy cuts, clean vs infected, and the slowdown depth delta against the
    per-(base, set) reference obfuscation. Read from the answer key of a build tree or release."""
    key = root / "answer_key"
    labels: dict[str, str | None] = json.loads((key / "labels.json").read_text(encoding="utf-8"))
    cuts: dict[str, Json] = json.loads((key / "cuts.json").read_text(encoding="utf-8"))
    out = ["### Cut-size distribution (blocks), clean vs infected", "",
           "| status | cut kind | n | min | median | max |", "|---|---|---|---|---|---|"]
    for status, want_infected in (("clean", False), ("infected", True)):
        by_kind: dict[str, list[int]] = {}
        for cid, c in cuts.items():
            if (labels.get(cid) is not None) != want_infected:
                continue
            sizes = c.get("sizes")
            lbls = c.get("labels")
            if not isinstance(sizes, list) or not sizes or not isinstance(lbls, list):
                continue
            by_kind.setdefault(_label_kind(lbls), []).extend(int(str(s)) for s in sizes)
        for kind, sizes in sorted(by_kind.items()):
            out.append(f"| {status} | {kind} | {len(sizes)} | "
                       f"{_quant([float(s) for s in sizes])} |")
    deltas = []
    for c in cuts.values():
        d, r = c.get("slow_depth"), c.get("slow_depth_ref")
        if isinstance(d, int) and isinstance(r, int) and r >= 0:
            deltas.append(float(d - r))
    out += ["", "### Slowdown depth delta against the per-(base, set) reference obfuscation", "",
            f"n {len(deltas)}, min / median / max: {_quant(deltas)}"]
    return out
