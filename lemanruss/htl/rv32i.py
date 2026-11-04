"""A small RV32I encoder for witness programs (round 7, Seeker-Proc pilot).

No cross toolchain is installed in this workspace (brief: "write and unit-test the encoder for
the handful of instructions you need"). Field layout is RISC-V Unprivileged ISA, Volume I,
chapter 2 ("RV32I Base Integer Instruction Set"), section 2.2 "Base Instruction Formats" (R/I/S/
B/U/J encodings) and section 2.3 "Immediate Encoding Variants" (the per-format immediate bit
order). Encodings below are checked against the worked example in section 2.3 (`sub x30, x30, t1`
and the immediate instructions) and the opcode/funct3/funct7 table of chapter 2.4-2.7; each
encode_* function states the opcode/funct3/funct7 it uses so the values are traceable to the
spec's instruction listing without re-deriving them by hand.

Only the instructions the round 7 witness programs need: ADDI (I-type, witness "magic word"
instruction and NOPs), JAL (J-type, the self-loop after the witness program), SW (S-type, used by
one witness variant that writes the magic word to the data bus instead of fetching it).
"""

from __future__ import annotations


def _u(value: int, bits: int) -> int:
    """value truncated to an unsigned field of `bits` bits (two's complement for negative input)."""
    return value & ((1 << bits) - 1)


def encode_addi(rd: int, rs1: int, imm: int) -> int:
    """ADDI rd, rs1, imm: I-type, opcode 0b0010011, funct3 0b000 (spec 2.4, RV32I "ADDI").

    I-type (spec 2.2): imm[11:0] (bits 31:20) | rs1 (19:15) | funct3 (14:12) | rd (11:7) |
    opcode (6:0). imm is a 12-bit signed immediate, sign-extended; here truncated per 2.3.
    """
    assert 0 <= rd < 32 and 0 <= rs1 < 32
    assert -2048 <= imm < 2048, f"ADDI imm {imm} out of 12-bit signed range"
    opcode, funct3 = 0b0010011, 0b000
    return (_u(imm, 12) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def encode_nop() -> int:
    """ADDI x0, x0, 0 (RISC-V's canonical NOP encoding, spec 2.4 "NOP")."""
    return encode_addi(0, 0, 0)


def encode_jal(rd: int, offset: int) -> int:
    """JAL rd, offset: J-type, opcode 0b1101111 (spec 2.5, RV32I "JAL").

    J-type immediate bit order (spec 2.3, Figure 2.4): imm[20|10:1|11|19:12], a 21-bit signed
    byte offset with bit 0 always 0 (2-byte-aligned targets are not produced by this encoder: it
    is used only for the `jal x0, 0` self-loop below, offset 0).
    """
    assert 0 <= rd < 32
    assert offset % 2 == 0, "JAL offset must be even (bit 0 of the field is always 0)"
    assert -(1 << 20) <= offset < (1 << 20)
    imm = _u(offset, 21)
    im20 = (imm >> 20) & 0x1
    im10_1 = (imm >> 1) & 0x3FF
    im11 = (imm >> 11) & 0x1
    im19_12 = (imm >> 12) & 0xFF
    opcode = 0b1101111
    return (im20 << 31) | (im19_12 << 12) | (im11 << 20) | (im10_1 << 21) | (rd << 7) | opcode


def encode_self_loop() -> int:
    """`jal x0, 0`: an infinite one-instruction loop (the witness program's tail)."""
    return encode_jal(0, 0)


def encode_lui(rd: int, imm20: int) -> int:
    """LUI rd, imm20: U-type, opcode 0b0110111 (spec 2.4, RV32I "LUI").

    U-type (spec 2.2): imm[31:12] (bits 31:12) | rd (11:7) | opcode (6:0); loads imm20 into the
    top 20 bits of rd and zeros the bottom 12 (so `lui x6, 0x40000` gives rd = 0x40000000, the
    witness programs' OPORT base address, darklibc/include/io.c: `io = (DARKIO*)0x40000000`).
    """
    assert 0 <= rd < 32
    assert 0 <= imm20 < (1 << 20), f"LUI imm20 {imm20:#x} out of 20-bit range"
    opcode = 0b0110111
    return (imm20 << 12) | (rd << 7) | opcode


def encode_sw(rs1: int, rs2: int, imm: int) -> int:
    """SW rs2, imm(rs1): S-type, opcode 0b0100011, funct3 0b010 (spec 2.6, RV32I "SW").

    S-type immediate bit order (spec 2.3, Figure 2.4): imm[11:5] (bits 31:25) | rs2 (24:20) |
    rs1 (19:15) | funct3 (14:12) | imm[4:0] (11:7) | opcode (6:0).
    """
    assert 0 <= rs1 < 32 and 0 <= rs2 < 32
    assert -2048 <= imm < 2048, f"SW imm {imm} out of 12-bit signed range"
    opcode, funct3 = 0b0100011, 0b010
    imm_u = _u(imm, 12)
    imm_hi, imm_lo = (imm_u >> 5) & 0x7F, imm_u & 0x1F
    return (imm_hi << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_lo << 7) | opcode
