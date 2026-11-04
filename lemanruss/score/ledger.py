"""Rate-limit ledger: a JSON-lines file the scorer reads and appends. Private, beside the key."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

WINDOW_S = 24 * 3600
MAX_TOTAL = 5


class RateLimitError(RuntimeError):
    """The submitter used up the window or the total; the message says when to retry."""


@dataclass(frozen=True)
class Limits:
    window_s: int = WINDOW_S
    max_total: int = MAX_TOTAL


def _entries(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def check(path: Path, submitter: str, release: str, now: float,
          lim: Limits | None = None) -> None:
    lim = lim or Limits()
    mine = [e for e in _entries(path) if e["submitter"] == submitter and e["release"] == release]
    if len(mine) >= lim.max_total:
        raise RateLimitError(
            f"limit reached: {lim.max_total} scored submissions per submitter for {release}")
    if mine:
        last = max(float(str(e["t"])) for e in mine)
        if now - last < lim.window_s:
            wait = int(lim.window_s - (now - last))
            raise RateLimitError(
                f"one submission per {lim.window_s // 3600} h: retry in {wait // 60} minutes")


def record(path: Path, submitter: str, release: str, subset: str, n: int, n_sample: int,
           seed: int, now: float | None = None) -> None:
    entry = {"t": time.time() if now is None else now, "submitter": submitter,
             "release": release, "subset": subset, "n": n, "sample": n_sample, "seed": seed}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
