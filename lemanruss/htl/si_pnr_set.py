"""Place and route of a documented stratified subset of a Seeker-Si rc2 set.

Subset rule (controller 2026-11-07): about 10 % of each base, stratified by label (infected and
clean in proportion, at least one of each where the base has both), every base of the Proc set;
smallest circuits first; 30 minute cap and one retry at another utilisation (`si_pnr`); every
cap-out is a recorded flow limit with its cell count. The choice is seeded from the private
release seed; the list and the labels it used stay in the answer-key area, never in the repo.
Per circuit the outputs are pruned to the routed DEF, the netlist, the DRC report, the step log
and the record (gzip), so the local footprint stays small.

    python -m lemanruss.htl.si_pnr_set --kind tree|release --root R --out O [--max N]
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
import shutil
from pathlib import Path

from lemanruss.htl import si_pnr
from lemanruss.seedsrc import release_seed

ODIN_ROOT = Path("/home/jamiespa/odin3-ws/odin3")
FRACTION = 0.10


def _read(path: Path) -> str:
    if path.suffix == ".gz":
        return gzip.decompress(path.read_bytes()).decode("utf-8")
    return path.read_text(encoding="utf-8")


def pick(
    by_base: dict[str, list[tuple[str, bool]]], seed: int, fraction: float = FRACTION
) -> list[tuple[str, str]]:
    """[(base, id)]: per base ceil(fraction * n) circuits (at least 2), infected share in
    proportion, at least one of each label where both exist."""
    chosen: list[tuple[str, str]] = []
    for base in sorted(by_base):
        rows = sorted(by_base[base])
        rng = random.Random(f"{seed}:{base}:pnr")
        inf = [c for c, i in rows if i]
        cln = [c for c, i in rows if not i]
        k = max(2, math.ceil(fraction * len(rows)))
        k_inf = min(len(inf), max(1 if inf else 0, round(k * len(inf) / max(1, len(rows)))))
        k_cln = min(len(cln), max(1 if cln else 0, k - k_inf))
        chosen += [(base, c) for c in rng.sample(inf, k_inf) + rng.sample(cln, k_cln)]
    return chosen


def prune(out: Path) -> None:
    """Keep the routed DEF, the netlist, DRC report, steps, log and record; gzip the big ones."""
    orx = out / "or"
    for name in ("route.def", "final.v"):
        f = orx / name
        if f.is_file():
            (out / f"{name}.gz").write_bytes(gzip.compress(f.read_bytes()))
    for name in ("drc.rpt", "steps.txt"):
        if (orx / name).is_file():
            shutil.copy(orx / name, out / name)
    log = out / "openroad.log"
    if log.is_file():
        (out / "openroad.log.gz").write_bytes(gzip.compress(log.read_bytes()))
    for item in list(out.iterdir()):
        if item.name in ("route.def.gz", "final.v.gz", "drc.rpt", "steps.txt",
                         "openroad.log.gz", "pnr.json"):
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()


def load(kind: str, root: Path, family_short: str) -> tuple[dict[str, list[tuple[str, bool]]],
                                                              dict[str, Path], dict[str, Path]]:
    """(by_base, verilog path per id, blif path per id) of a tree or a release."""
    key = root / "answer_key"
    labels = json.loads((key / "labels.json").read_text(encoding="utf-8"))
    by_base: dict[str, list[tuple[str, bool]]] = {}
    vpath: dict[str, Path] = {}
    bpath: dict[str, Path] = {}
    if kind == "tree":
        man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        gold = set(man["goldens"].values()) if "goldens" in man else set()
        for c in man["circuits"]:
            cid = str(c["id"])
            if cid in gold or not (root / "circuits_v" / f"{cid}.v").is_file():
                continue
            by_base.setdefault(str(c["base"]), []).append((cid, labels.get(cid) is not None))
            vpath[cid] = root / "circuits_v" / f"{cid}.v"
            bpath[cid] = root / "circuits" / f"{cid}.blif"
    else:
        man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for c in man["circuits"]:
            cid = str(c["id"])
            by_base.setdefault(str(c["base"]), []).append((cid, labels.get(cid) is not None))
            vpath[cid] = root / "circuits_v" / f"{cid}.v.gz"
            bpath[cid] = root / "circuits" / f"{cid}.blif.gz"
    return by_base, vpath, bpath


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=("tree", "release"), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--name", default="Seeker-Si")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--fraction", type=float, default=FRACTION)
    ap.add_argument("--shard", default="0/1", help="i/n: run every n-th circuit from i")
    args = ap.parse_args(argv)
    by_base, vpath, bpath = load(args.kind, args.root, "")
    chosen = pick(by_base, release_seed(None, "default"), args.fraction)
    sized = sorted(chosen, key=lambda bc: (_read(vpath[bc[1]]).count("sky130_fd_sc_hd__"), bc[1]))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "subset.json").write_text(json.dumps(sized), encoding="utf-8")  # private: key area
    done = 0
    i, n = (int(x) for x in args.shard.split("/"))
    for base, cid in sized[i::n]:
        dest = args.out / cid
        old = dest / "pnr.json"
        if old.is_file():
            prev = json.loads(old.read_text(encoding="utf-8"))
            # redo only records killed by the superseded 300 s stall rule
            if prev["ok"] or not any(a.get("stalled") for a in prev["attempts"]):
                continue
        v = _read(vpath[cid])
        tmp = args.out / f"{cid}.v"
        tmp.write_text(v, encoding="utf-8")
        cells = v.count("sky130_fd_sc_hd__")
        rec = si_pnr.run(tmp, si_pnr.clock_of(_read(bpath[cid])), dest, cells, ODIN_ROOT)
        tmp.unlink()
        att = rec["attempts"]
        assert isinstance(att, list)
        if len(att) == 2:  # keep the last attempt only
            shutil.rmtree(dest / f"u{att[0]['util']}", ignore_errors=True)
        last = dest / f"u{att[-1]['util']}"
        for item in last.iterdir():
            shutil.move(str(item), str(dest / item.name))
        shutil.rmtree(last, ignore_errors=True)
        rec["base_index"] = base  # base name stays in the private record only
        (dest / "pnr.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        prune(dest)
        done += 1
        print(cid, cells, rec["ok"], rec["flow_limit"], flush=True)
        if args.max and done >= args.max:
            break


if __name__ == "__main__":
    main()
