"""Run an Odin III feature extraction in a child process with a time limit (a very large netlist
must cost one circuit, not the run). A timeout or crash gives None: "not scored", never imputed."""

from __future__ import annotations

import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_S = 90


def isolated(kind: str, path: Path, timeout: int = TIMEOUT_S) -> object | None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.pkl"
        try:
            subprocess.run(
                [sys.executable, "-m", "lemanruss.detect.isolated", kind, str(path), str(out)],
                cwd=tmp, timeout=timeout, check=True, capture_output=True,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return None
        with out.open("rb") as fh:
            val: object = pickle.load(fh)
        return val


def main() -> None:
    kind, src, dst = sys.argv[1:4]
    if kind == "scoap":
        from lemanruss.detect.scoap_feat import scoap_arrays

        val: object = scoap_arrays(Path(src))
    elif kind == "glet":
        from lemanruss.detect.graphlet_b import signature

        val = signature(Path(src))
    else:
        raise SystemExit(kind)
    with open(dst, "wb") as fh:
        pickle.dump(val, fh)


if __name__ == "__main__":
    main()
