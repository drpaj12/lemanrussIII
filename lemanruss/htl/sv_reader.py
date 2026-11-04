"""Registers Odin III's SystemVerilog reader (the slang adapter) for `.sv` files.

The odin3 CLI registers this at start-up (`src/cli/*.c`'s `init_linked_slang`); the Python
binding does the equivalent for `abc` (`Odin3._register_abc`) but not for the SV reader, so a
plain `design.run_script('read_verilog "x.sv"; ...')` fails with "no SystemVerilog reader
registered" until this runs once per process. Confirmed by calling
`odin3_sv_reader_register` directly, not assumed: `odin3_read_slang`'s symbol
(`libodin3_slang.so`, built alongside `libodin3.so`) is not declared in `odin3.py`'s own cdef
(it comes from `adapters/slang/odin3_slang.h`, not the public `odin3.h`), so this module adds
one extra `cdef` line for it, `dlopen`s the slang adapter with the same `cffi.FFI`, casts the
symbol to the `odin3_sv_read_fn` typedef the public header already declares, and registers it.
Needed so lemanruss.htl.build can read the SystemVerilog `_ref.sv` reference designs under
external/Gate-Breaker-verilog-eval without modifying them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odin3 import Design, Odin3

_REGISTERED = False

_SV_READ_CDEF = (
    "odin3_status odin3_read_slang(odin3_design *design, uint32_t run, "
    "const odin3_sv_options *opts);"
)


class SlangNotFound(RuntimeError):
    """Raised when libodin3_slang.so is not found beside the loaded libodin3."""


def register_slang_reader(design: Design) -> None:
    """Registers the slang SystemVerilog reader for this process (idempotent: a second call,
    here or anywhere else in the process, is a silent no-op, matching
    `odin3_sv_reader_register`'s own "already registered" rule, which this module treats as
    success rather than an error)."""
    global _REGISTERED
    if _REGISTERED:
        return
    odin3 = design.odin3
    slang_path = odin3._library.resolve().parent / "libodin3_slang.so"
    if not slang_path.is_file():
        raise SlangNotFound(f"{slang_path}: not found (built alongside libodin3.so)")
    odin3.ffi.cdef(_SV_READ_CDEF)
    slang_lib = odin3.ffi.dlopen(str(slang_path))
    read_fn = odin3.ffi.cast("odin3_sv_read_fn", slang_lib.odin3_read_slang)
    status = odin3.lib.odin3_sv_reader_register(read_fn)
    if status != 0 and status != _already_registered_status(odin3):
        raise RuntimeError(f"odin3_sv_reader_register: status {status}")
    _REGISTERED = True


def _already_registered_status(odin3: Odin3) -> int:
    """ODIN3_ERR_INVALID_ARG: the status a second registration from elsewhere in the process
    would also return (odin3.h: "a second call with a different function is
    ODIN3_ERR_INVALID_ARG"); accepted here as already-done, not a failure."""
    return int(odin3.lib.ODIN3_ERR_INVALID_ARG)
