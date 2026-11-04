"""Checks the RV32I encoder against known encodings (RISC-V Unprivileged ISA spec, chapter 2)."""

from __future__ import annotations

import unittest

from lemanruss.htl.rv32i import (
    encode_addi,
    encode_jal,
    encode_lui,
    encode_nop,
    encode_self_loop,
    encode_sw,
)


class TestAddi(unittest.TestCase):
    def test_nop(self) -> None:
        # ADDI x0, x0, 0 is RV32I's canonical NOP, encoding 0x00000013 (widely documented, e.g.
        # the mcu test fixture's own NOP constant, tests/mcu/mcu_tb.v neighbour fetch_receive.v
        # localparam NOP = 32'h00000013).
        self.assertEqual(encode_nop(), 0x00000013)
        self.assertEqual(encode_addi(0, 0, 0), 0x00000013)

    def test_addi_x5_x0_1(self) -> None:
        # addi x5, x0, 1: imm=1 -> 0x001, rs1=0, funct3=0, rd=5, opcode=0x13
        # word = 0x001_00000_000_00101_0010011 = 0x00100293
        self.assertEqual(encode_addi(5, 0, 1), 0x00100293)

    def test_addi_known_disassembly(self) -> None:
        # 0x00050513 disassembles to "addi a0, a0, 0" = addi x10, x10, 0 (a0 is x10 in the
        # standard RISC-V ABI register names, spec chapter 25 calling convention table).
        self.assertEqual(encode_addi(10, 10, 0), 0x00050513)

    def test_negative_immediate(self) -> None:
        # addi x1, x0, -1: imm two's complement 0xFFF -> word 0xFFF00093
        self.assertEqual(encode_addi(1, 0, -1), 0xFFF00093)

    def test_imm_range(self) -> None:
        with self.assertRaises(AssertionError):
            encode_addi(1, 0, 2048)
        with self.assertRaises(AssertionError):
            encode_addi(1, 0, -2049)


class TestJal(unittest.TestCase):
    def test_self_loop(self) -> None:
        # jal x0, 0: a documented infinite-loop idiom; opcode 0x6f, all other fields 0 since
        # offset 0 and rd = x0, giving word 0x0000006f (matches the mcu fixture's own 'EF'/'6F'-
        # style byte values already present in 0blink.vmh for jump instructions).
        self.assertEqual(encode_self_loop(), 0x0000006F)
        self.assertEqual(encode_jal(0, 0), 0x0000006F)

    def test_jal_ra_offset(self) -> None:
        # jal x1, 4 (call the next instruction's successor): im20=0 im19_12=0 im11=0 im10_1=2
        # (offset 4 -> imm field value 4, bit1=1 of the 21-bit immediate) rd=1 opcode=0x6f
        word = encode_jal(1, 4)
        # Decode it back by the same field layout and check round trip.
        im20 = (word >> 31) & 0x1
        im19_12 = (word >> 12) & 0xFF
        im11 = (word >> 20) & 0x1
        im10_1 = (word >> 21) & 0x3FF
        imm = (im20 << 20) | (im19_12 << 12) | (im11 << 11) | (im10_1 << 1)
        self.assertEqual(imm, 4)
        self.assertEqual((word >> 7) & 0x1F, 1)
        self.assertEqual(word & 0x7F, 0b1101111)

    def test_offset_must_be_even(self) -> None:
        with self.assertRaises(AssertionError):
            encode_jal(0, 1)


class TestLui(unittest.TestCase):
    def test_lui_oport_base(self) -> None:
        # lui x6, 0x40000 -> x6 = 0x40000000 (darklibc's io base address). imm20=0x40000,
        # rd=6, opcode=0x37: word = (0x40000 << 12) | (6 << 7) | 0x37 = 0x40000337
        self.assertEqual(encode_lui(6, 0x40000), 0x40000337)

    def test_imm20_range(self) -> None:
        with self.assertRaises(AssertionError):
            encode_lui(6, 1 << 20)
        with self.assertRaises(AssertionError):
            encode_lui(6, -1)


class TestSw(unittest.TestCase):
    def test_sw_zero_offset(self) -> None:
        # sw x5, 0(x10): imm=0 -> imm_hi=0 imm_lo=0, rs2=5, rs1=10, funct3=2, opcode=0x23
        word = encode_sw(10, 5, 0)
        self.assertEqual((word >> 25) & 0x7F, 0)
        self.assertEqual((word >> 20) & 0x1F, 5)
        self.assertEqual((word >> 15) & 0x1F, 10)
        self.assertEqual((word >> 12) & 0x7, 0b010)
        self.assertEqual((word >> 7) & 0x1F, 0)
        self.assertEqual(word & 0x7F, 0b0100011)

    def test_sw_negative_offset_round_trip(self) -> None:
        word = encode_sw(2, 3, -4)
        imm_hi = (word >> 25) & 0x7F
        imm_lo = (word >> 7) & 0x1F
        imm = (imm_hi << 5) | imm_lo
        # sign-extend from 12 bits
        if imm & 0x800:
            imm -= 1 << 12
        self.assertEqual(imm, -4)


if __name__ == "__main__":
    unittest.main()
