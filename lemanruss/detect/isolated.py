"""Run an Odin III feature extraction in a child process with a time limit (a very large netlist
must cost one circuit, not the run). A timeout or crash gives None: "not scored", never imputed."""

from __future__ import annotations

import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_S = 90
TOOLCHAIN_EXIT = 3  # child exit code: Odin III could not be imported or loaded


class ToolchainError(RuntimeError):
    """Odin III is not importable in the child process (PYTHONPATH/ODIN3_LIB wrong). This is an
    environment fault, not a property of the circuit, so it must stop the run: scoring every
    circuit NaN and caching that hides the cause (Proc detector failures, round 11)."""


def isolated(kind: str, path: Path, timeout: int = TIMEOUT_S) -> object | None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.pkl"
        try:
            subprocess.run(
                [sys.executable, "-m", "lemanruss.detect.isolated", kind, str(path), str(out)],
                cwd=tmp, timeout=timeout, check=True, capture_output=True,
            )
        except subprocess.TimeoutExpired:
            return None
        except subprocess.CalledProcessError as exc:
            if exc.returncode == TOOLCHAIN_EXIT:
                msg = exc.stderr.decode("utf-8", "replace").strip().splitlines()
                raise ToolchainError(
                    "Odin III cannot be loaded for feature extraction "
                    "(set PYTHONPATH to <odin3>/plugins/python and ODIN3_LIB): "
                    + (msg[-1] if msg else "no message")) from exc
            return None  # Odin III refused or crashed on this circuit: not scored
        with out.open("rb") as fh:
            val: object = pickle.load(fh)
        return val


def main() -> None:
    kind, src, dst = sys.argv[1:4]
    if kind in ("scoap", "glet"):
        try:
            import odin3

            with odin3.Design():
                pass
        except Exception as exc:  # ImportError, or the shared library failing to load
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
            raise SystemExit(TOOLCHAIN_EXIT) from exc
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
