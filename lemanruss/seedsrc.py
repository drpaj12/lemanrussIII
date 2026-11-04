"""Where a release build gets its generator seed.

The seed of a released build, together with the public code, regenerates the answer key.
So it is never committed, never written into a released manifest and never given a default.
Order of lookup:

1. an explicit ``--seed`` on the command line (tests, audits, throwaway builds);
2. the environment variable ``LEMANRUSS_RELEASE_SEED`` (an integer);
3. the JSON file named by ``LEMANRUSS_SEED_FILE``:
   ``{"<family name>": <int>, "default": <int>}``.

If none gives a seed the build stops with an error.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ENV_SEED = "LEMANRUSS_RELEASE_SEED"
ENV_FILE = "LEMANRUSS_SEED_FILE"


def release_seed(explicit: int | None, name: str = "default") -> int:
    """Return the generator seed for ``name``; raise SystemExit if no private source gives one."""
    if explicit is not None:
        return explicit
    env = os.environ.get(ENV_SEED)
    if env is not None and env.strip():
        return int(env)
    path = os.environ.get(ENV_FILE)
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for key in (name, "default"):
            if key in data:
                return int(data[key])
    raise SystemExit(
        f"no release seed: pass --seed, set {ENV_SEED}, or set {ENV_FILE} to a private JSON file "
        "(the seed of a released build is never committed)")


ENV_MAGIC_FILE = "LEMANRUSS_PROC_MAGIC_FILE"


def private_words(name: str) -> list[int]:
    """Trigger (magic) instruction words of a processor Trojan build, from a private JSON file.

    ``LEMANRUSS_PROC_MAGIC_FILE`` names ``{"<name>": [<int>, ...]}``. The words of released
    circuits are activation programs and stay with the answer key, never in the source.
    """
    path = os.environ.get(ENV_MAGIC_FILE)
    if not path:
        raise SystemExit(f"no magic words: set {ENV_MAGIC_FILE} to a private JSON file")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [int(w) for w in data[name]]
