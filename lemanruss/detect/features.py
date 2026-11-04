"""Per-circuit feature cache (pickle under $LEMANRUSS_FEAT/<kind>/<sha256>.pkl) and a process
pool to fill it (resumable, jobs <= 4).

Keyed by the circuit file's own content hash (`sha256_of`), not its id: an opaque id such as
`ss0139` is assigned per release/style and is not unique across them (a different release, or a
different restructured-form style of the same release, can and does reuse the same id for a
different circuit) -- Peter 2026-11-02. A content hash cannot collide this way (two different
circuits sharing a hash would be an actual sha256 collision, not a label leak), and two circuits
that are byte-identical correctly do share one cache entry."""

from __future__ import annotations

import hashlib
import os
import pickle
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import TypeVar

from lemanruss.detect.data import CircuitFile

T = TypeVar("T")
DEFAULT_ROOT = "work/htl-out/det/feat"


def feat_root() -> Path:
    return Path(os.environ.get("LEMANRUSS_FEAT", DEFAULT_ROOT))


def sha256_of(path: Path) -> str:
    """Streamed content hash of `path`'s bytes: the generic cache key (spec/brief: the GNN graph
    cache and every `features.cached` kind key on this, not on the circuit id)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_path(kind: str, cf: CircuitFile) -> Path:
    return feat_root() / kind / f"{sha256_of(cf.path)}.pkl"


def cached(kind: str, cf: CircuitFile, fn: Callable[[Path], T]) -> T:
    p = cache_path(kind, cf)
    if p.is_file():
        with p.open("rb") as fh:
            out: T = pickle.load(fh)
        return out
    val = fn(cf.path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.tmp")
    with tmp.open("wb") as fh:
        pickle.dump(val, fh)
    tmp.replace(p)
    return val


def _one(args: tuple[str, CircuitFile, Callable[[Path], object]]) -> None:
    kind, cf, fn = args
    cached(kind, cf, fn)


def fill(kind: str, files: Sequence[CircuitFile], fn: Callable[[Path], object],
         jobs: int = 4) -> None:
    """Compute the missing cache entries with `fn` (a module-level function, picklable)."""
    todo = [(kind, f, fn) for f in files if not cache_path(kind, f).is_file()]
    if not todo:
        return
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(_one, todo, chunksize=8))
