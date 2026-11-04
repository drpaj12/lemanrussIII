"""Re-validation helpers: the parse/structural check the brief asks for after every text edit.

Both the HDL and the netlist inserter produce text; this module is the one place that opens
Odin III to check the result, so insert_hdl.py and insert_netlist.py stay importable (and unit
testable) without ODIN3_LIB/PYTHONPATH set.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def verilog_parses(source: str, top: str | None = None) -> None:
    """Raises odin3.Odin3Error (via Design.run_pass) when `source` fails
    `read_verilog --parse-only`; returns normally when it parses."""
    from odin3 import Design

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "edited.v"
        path.write_text(source, encoding="utf-8")
        with Design() as design:
            words = f'--parse-only "{path}"' + (f" --top {top}" if top else "")
            design.run_pass("read_verilog", words)


def blif_parses(text: str) -> None:
    """Raises odin3.Odin3Error (via Design.run_pass) when `text` fails `read_blif`."""
    from odin3 import Design

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "edited.blif"
        path.write_text(text, encoding="utf-8")
        with Design() as design:
            design.run_pass("read_blif", str(path))
