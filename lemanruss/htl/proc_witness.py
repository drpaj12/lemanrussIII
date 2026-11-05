"""Witness programs for the `alu` payload kind, and the magic-word rejection rule (rc1
Continuation 4, 2026-11-04).

Why an `alu` witness is its own program: the `alu` payload flips bit 0 of a shift-right result
while its trigger is on. The trigger is a comparator on the instruction register of the
instruction being executed (mcu `instruction`, darkriscv `XIDATA`), so the corrupted result is
the result of the magic-word instruction itself. The magic word of an `alu`-kind Trojan is
therefore a shift-right instruction (`rv32i.random_shift_right_word`), and its witness must
(1) give the shift a known operand, (2) execute the magic word, (3) store its destination
register where the testbench trace shows it. The reset/stall witnesses of `proc_pilot` do none of
that, which is why an `alu` Trojan never fired in the batch build (round 11 section 4).

Rejection rule (documented in docs/specs/2026-11-03-seeker-proc-rc1.md section 0b): a random
magic word is rejected when it equals any word of any shipped program image of its base, or any
scaffolding word the witness and neutral programs use, because a neutral program would then
legitimately drive the watched bus to the magic value and silence would fail for a legitimate
reason, not a defect.
"""

from __future__ import annotations

import random
from pathlib import Path

from lemanruss.htl.rv32i import (
    decode_shift_right,
    encode_addi,
    encode_jal,
    encode_lui,
    encode_nop,
    encode_self_loop,
    encode_srli,
    encode_sw,
    random_magic_word,
    random_shift_right_word,
)

# Store targets observable in each testbench trace: darkriscv OPORT (0x40000000 + 0x18, as
# proc_pilot.dark_witness_words), mcu PORTB (byte address 0x2014, single_cycle_BRAM_top.v
# `d_mem_address_in == 14'h2014`), picorv32 the fixed marker word (picorv32_pilot.MARKER_ADDR).
_DARK_LUI, _DARK_OFF = 0x40000, 0x18
_MCU_LUI, _MCU_OFF = 0x2, 0x14
_PICO_MARKER = 0x100
_OPERAND = -1  # all ones: every shift-right result is non-zero with bit 0 set, so the clean
# program really stores a non-default value and the LSB flip changes it
_BASE_CANDIDATES = (28, 29, 30, 31)
_GAP = 3  # nops between producer and consumer: no hazard/forwarding assumption


_PICO_SHAMT = 8  # >= 4 so the prefetch of the next word has latched before the shift completes


def alu_magic_word(base: str, rng: random.Random, exclude: set[int]) -> int:
    """The magic word of an `alu`-kind Trojan: a shift-right word on mcu and darkriscv (the
    comparator sees the executing instruction); any legal ADDI word on picorv32 (module note
    below: its watched register holds the instruction AFTER the executing shift)."""
    if base == "picorv32":
        return random_magic_word(rng, exclude)
    return random_shift_right_word(rng, exclude)


def _pico_alu_witness(word: int) -> list[int]:
    """picorv32 prefetches the next instruction while the current one executes
    (`mem_do_prefetch`, picorv32.v:1573), so `next_insn_opcode` (the watched register) already
    holds the word after a multi-cycle shift when the shift writes back. The witness is
    therefore `srli ..., 8` followed by the magic word, then a store of the shift result."""
    if (word & 0x7F) != 0b0010011 or ((word >> 12) & 7) != 0:
        raise ValueError(f"{word:#010x}: picorv32 alu magic word must be an ADDI")
    word_rd = (word >> 7) & 0x1F
    result = next(r for r in (6, 7, 8) if r != word_rd)
    return [
        encode_nop(), encode_nop(), encode_addi(5, 0, _OPERAND), *[encode_nop()] * _GAP,
        encode_srli(result, 5, _PICO_SHAMT), word, *[encode_nop()] * _GAP,
        encode_sw(0, result, _PICO_MARKER), encode_self_loop(),
    ]


def alu_witness_words(base: str, word: int) -> list[int]:
    """Program that executes the `alu` Trojan's shift-right once with defined operands and stores
    its destination register to the base's observable address."""
    if base == "picorv32":
        return _pico_alu_witness(word)
    sh = decode_shift_right(word)
    if sh is None:
        raise ValueError(f"{word:#010x} is not a shift-right instruction")
    prog: list[int] = [encode_nop(), encode_nop()]
    if sh.rs1 != 0:
        prog.append(encode_addi(sh.rs1, 0, _OPERAND))
    if not sh.imm_form and sh.src2 not in (0, sh.rs1):
        prog.append(encode_addi(sh.src2, 0, 1))
    used = {sh.rd, sh.rs1} | (set() if sh.imm_form else {sh.src2})
    store_base = next(r for r in _BASE_CANDIDATES if r not in used)
    lui, off = (_DARK_LUI, _DARK_OFF) if base == "darkriscv" else (_MCU_LUI, _MCU_OFF)
    prog.append(encode_lui(store_base, lui))
    store = encode_sw(store_base, sh.rd, off)
    prog += [encode_nop()] * _GAP + [word] + [encode_nop()] * _GAP + [store, encode_self_loop()]
    return prog


def neutral_shift_word(word: int) -> int:
    """A word that is not `word` but has the same kind: bit 20 flipped (shamt/rs2 bit 0 of a
    shift-right, imm bit 0 of an ADDI)."""
    return word ^ (1 << 20)


def scaffolding_words() -> set[int]:
    """Every fixed word the witness and neutral programs use."""
    return {
        encode_nop(), encode_self_loop(), encode_jal(0, 0), encode_lui(6, 0x40000),
        encode_addi(5, 0, 0x2A), encode_addi(5, 0, 0x37), encode_sw(6, 5, 0x18),
        encode_sw(0, 6, _PICO_MARKER),
    } | {
        encode_sw(b, r, off) for b in _BASE_CANDIDATES for r in range(1, 32)
        for off in (_DARK_OFF, _MCU_OFF)
    } | {encode_sw(0, r, _PICO_MARKER) for r in (6, 7, 8)} | {
        encode_srli(r, 5, _PICO_SHAMT) for r in (6, 7, 8)
    } | {encode_addi(r, 0, _OPERAND) for r in range(1, 32)} | {
        encode_addi(r, 0, 1) for r in range(1, 32)
    } | {encode_lui(r, _DARK_LUI) for r in _BASE_CANDIDATES} | {
        encode_lui(r, _MCU_LUI) for r in _BASE_CANDIDATES
    }


def _read_hex_words(path: Path) -> list[int]:
    out = []
    for ln in path.read_text().splitlines():
        for tok in ln.split("//")[0].split():
            if not tok.startswith("@"):
                out.append(int(tok, 16))
    return out


def shipped_words(base: str, upstream: Path) -> set[int]:
    """Every instruction word of every shipped program image of `base` under `upstream` (the
    base's own checkout). mcu: four byte-plane files `<k><name>.vmh` per program; darkriscv: the
    word-per-line `src/darksocv.mem`; picorv32: no shipped program image in the checkout."""
    words: set[int] = set()
    if base == "mcu":
        img = upstream / "quartus_project_revert_timer"
        for p0 in sorted(img.glob("0*.vmh")):
            planes = [img / f"{k}{p0.name[1:]}" for k in range(4)]
            if not all(p.exists() for p in planes):
                continue
            data = [_read_hex_words(p) for p in planes]
            for b0, b1, b2, b3 in zip(*data, strict=False):
                words.add((b3 << 24) | (b2 << 16) | (b1 << 8) | b0)
    elif base == "darkriscv":
        mem = upstream / "src" / "darksocv.mem"
        if mem.exists():
            words |= set(_read_hex_words(mem))
    return words


def forbidden_words(base: str, upstream: Path) -> set[int]:
    """The generator's rejection set for `base` (module docstring)."""
    return scaffolding_words() | shipped_words(base, upstream)


__all__ = ["alu_magic_word", "alu_witness_words", "neutral_shift_word", "scaffolding_words",
           "shipped_words", "forbidden_words"]
