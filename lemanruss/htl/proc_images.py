"""Program-image writers for the two processor bases (round 7).

MCU (Arduino-on-RISC-V, `tests/mcu`): a 32-bit instruction word is split over 4 `.vmh` files
(`0<name>.vmh` .. `3<name>.vmh`, one byte per line, `@00000000` address header), byte N of every
word in file N (little-endian byte order, read from the existing fixtures in
external/Arduino-on-RISC-V, e.g. 0blink.vmh/1blink.vmh/2blink.vmh/3blink.vmh).

DarkRISCV (`tests/darkriscv`): one `$readmemh`-format file, one 32-bit hex word per line
(`external/darkriscv/src/darksocv.mem`).
"""

from __future__ import annotations

from pathlib import Path


def write_mcu_vmh(words: list[int], out_dir: Path, name: str) -> list[Path]:
    """Writes `<out_dir>/{0,1,2,3}<name>.vmh`; returns the 4 paths (plane 0 = LSB byte)."""
    paths = []
    for plane in range(4):
        lines = ["@00000000"]
        lines += [f"{(w >> (plane * 8)) & 0xFF:02X}" for w in words]
        path = out_dir / f"{plane}{name}.vmh"
        path.write_text("\n".join(lines) + "\n")
        paths.append(path)
    return paths


def write_dark_mem(words: list[int], out_path: Path) -> Path:
    """Writes a `$readmemh` word-per-line file in the style of darksocv.mem."""
    out_path.write_text("\n".join(f"{w & 0xFFFFFFFF:08x}" for w in words) + "\n")
    return out_path


def read_dark_mem(path: Path) -> list[int]:
    """Reads a `$readmemh` word-per-line file back into a word list (round-trip check)."""
    return [int(ln.strip(), 16) for ln in path.read_text().splitlines() if ln.strip()]
