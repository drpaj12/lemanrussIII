"""Regression tests for rc1 Continuation 4 (docs/results-round11.md section 7): the alu witness
programs, the alu magic words, the magic-word rejection rule, and (when the externals and a
built Odin III exist) one real build per base on the draws that exposed each defect."""

from __future__ import annotations

import os
import random
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.proc_insert import insert_dark_kinded_multitrojan
from lemanruss.htl.proc_witness import (
    alu_magic_word,
    alu_witness_words,
    forbidden_words,
    neutral_shift_word,
    scaffolding_words,
    shipped_words,
)
from lemanruss.htl.rv32i import (
    decode_shift_right,
    encode_sra,
    encode_srai,
    encode_srl,
    encode_srli,
    random_shift_right_word,
)

WS = Path(os.environ.get("ODIN3_WS", "~/odin3-ws")).expanduser()
MCU_UP = WS / "external" / "Arduino-on-RISC-V"
DARK_UP = WS / "external" / "darkriscv"
PICO_UP = WS / "external" / "picorv32"
SLOW = os.environ.get("LEMANRUSS_SLOW") == "1"
ODIN_BIN = Path(os.environ.get("ODIN3_BIN", str(WS / "odin3" / "build" / "rel-main3" / "odin3")))


class TestShiftRightCodec(unittest.TestCase):
    def test_known_encodings(self) -> None:
        # srli x6,x5,1 / srai x6,x5,1 / srl x6,x5,x7 / sra x6,x5,x7 (RISC-V ISA spec ch. 2.4)
        self.assertEqual(encode_srli(6, 5, 1), 0x0012D313)
        self.assertEqual(encode_srai(6, 5, 1), 0x4012D313)
        self.assertEqual(encode_srl(6, 5, 7), 0x0072D333)
        self.assertEqual(encode_sra(6, 5, 7), 0x4072D333)

    def test_decode_round_trip_and_rejects_others(self) -> None:
        sh = decode_shift_right(encode_sra(9, 3, 4))
        assert sh is not None
        self.assertEqual(
            (sh.rd, sh.rs1, sh.src2, sh.imm_form, sh.arithmetic), (9, 3, 4, False, True))
        self.assertIsNone(decode_shift_right(0x00000013))  # nop
        self.assertIsNone(decode_shift_right(0x0012C313))  # xori: funct3 100

    def test_random_shift_words_decode_and_have_visible_rd(self) -> None:
        rng = random.Random(7)
        seen: set[int] = set()
        for _ in range(200):
            w = random_shift_right_word(rng, seen)
            seen.add(w)
            sh = decode_shift_right(w)
            assert sh is not None
            self.assertGreaterEqual(sh.rd, 1)


class TestAluWitness(unittest.TestCase):
    def test_mcu_dark_program_shape(self) -> None:
        w = encode_srli(9, 4, 3)
        for base in ("mcu", "darkriscv"):
            prog = alu_witness_words(base, w)
            self.assertIn(w, prog)
            self.assertEqual(prog.count(w), 1)
            self.assertEqual(prog[-1], 0x0000006F)  # self-loop
            # the store base register is none of rd/rs1 (it would clobber the stored value)
            lui = [p for p in prog if (p & 0x7F) == 0x37]
            self.assertEqual(len(lui), 1)
            self.assertNotIn((lui[0] >> 7) & 0x1F, (9, 4))

    def test_register_form_initialises_rs2(self) -> None:
        prog = alu_witness_words("mcu", encode_sra(9, 4, 5))
        self.assertIn(0x00100293, prog)  # addi x5, x0, 1

    def test_picorv32_needs_addi_and_follows_a_shift(self) -> None:
        magic = 0x12300293  # addi x5, x0, 0x123
        prog = alu_witness_words("picorv32", magic)
        i = prog.index(magic)
        sh = decode_shift_right(prog[i - 1])
        assert sh is not None  # the word before the magic word is the shift being corrupted
        self.assertNotEqual(sh.rd, 5)  # magic word's rd (5) must not clobber the stored result
        with self.assertRaises(ValueError):
            alu_witness_words("picorv32", encode_srli(9, 4, 3))

    def test_non_shift_rejected_on_shift_bases(self) -> None:
        with self.assertRaises(ValueError):
            alu_witness_words("darkriscv", 0x12300293)

    def test_alu_magic_word_kind_per_base(self) -> None:
        rng = random.Random(3)
        self.assertIsNotNone(decode_shift_right(alu_magic_word("mcu", rng, set())))
        self.assertIsNotNone(decode_shift_right(alu_magic_word("darkriscv", rng, set())))
        w = alu_magic_word("picorv32", rng, set())
        self.assertEqual(w & 0x7F, 0b0010011)
        self.assertIsNone(decode_shift_right(w))

    def test_neutral_shift_word_differs_but_same_kind(self) -> None:
        w = encode_srai(9, 4, 3)
        n = neutral_shift_word(w)
        self.assertNotEqual(n, w)
        self.assertIsNotNone(decode_shift_right(n))


class TestRejectionRule(unittest.TestCase):
    def test_scaffolding_covers_witness_words(self) -> None:
        sc = scaffolding_words()
        self.assertIn(0x00000013, sc)
        self.assertIn(0x40000337, sc)
        self.assertIn(0x02A00293, sc)

    def test_every_alu_witness_scaffold_word_is_rejected(self) -> None:
        # every non-magic word an alu witness emits must be in the rejection set, so no random
        # magic word can equal one and make a neutral program legitimately fire
        sc = scaffolding_words()
        magic = encode_srli(9, 4, 3)
        for base in ("mcu", "darkriscv"):
            for word in alu_witness_words(base, magic):
                if word != magic:
                    self.assertIn(word, sc)

    @unittest.skipUnless(MCU_UP.is_dir() and DARK_UP.is_dir(), "needs the external checkouts")
    def test_shipped_words_in_rejection_set(self) -> None:
        mcu = shipped_words("mcu", MCU_UP)
        dark = shipped_words("darkriscv", DARK_UP)
        self.assertGreater(len(mcu), 100)
        self.assertGreater(len(dark), 100)
        self.assertTrue(mcu <= forbidden_words("mcu", MCU_UP))
        self.assertTrue(dark <= forbidden_words("darkriscv", DARK_UP))


@unittest.skipUnless((DARK_UP / "rtl" / "darkriscv.v").is_file(), "needs external/darkriscv")
class TestDarkRmdataWidth(unittest.TestCase):
    def test_rmdata_wire_is_32_bits(self) -> None:
        """Root cause 1: `wire __htl_rmdata` had no range, so the forward-referenced use in the
        write-back mux truncated RMDATA to one bit and the infected core differed from clean on
        every program, trigger or not."""
        src = (DARK_UP / "rtl" / "darkriscv.v").read_text()
        patched, _ = insert_dark_kinded_multitrojan(src, [0x7DA38493], ["reset"])
        self.assertIn("wire [31:0] __htl_rmdata =", patched)
        self.assertNotIn("wire __htl_rmdata", patched)


@unittest.skipUnless(
    ODIN_BIN.is_file() and all(p.is_dir() for p in (MCU_UP, DARK_UP, PICO_UP)),
    "needs a built Odin III and the three external checkouts",
)
class TestBuildOneCircuitDraws(unittest.TestCase):
    """The draws that failed in the round 11 section 4 batch, replayed through the real gates.

    The functional gates (FF equality, per-Trojan witness, neutral silence, shipped silence) run
    by default. The release gate (form mapping plus ABC miter equivalence, about 90 of 110 s for
    a darkriscv circuit) is an end-to-end check that only runs with LEMANRUSS_SLOW=1."""

    def _run(self, base: str, kinds: list[str], words: list[int]) -> None:
        from lemanruss.htl.proc_build import build_one_circuit

        with tempfile.TemporaryDirectory() as tmp:
            b = build_one_circuit("t-0001", base, random.Random(0), set(), ODIN_BIN, Path(tmp),
                                  forced=(kinds, words), functional_only=not SLOW)
            self.assertTrue(b.gate_pass, (b.error, b.per_trojan_fires, b.silent_on_neutral,
                                          b.silent_on_neutral_shift))

    def test_dark_reset_only_random_word(self) -> None:
        self._run("darkriscv", ["reset"], [0x7DA38493])  # failed neutral silence before the fix

    def test_dark_alu_and_stall(self) -> None:
        self._run("darkriscv", ["stall", "alu"], [0x9DC80F93, encode_srai(31, 5, 10)])

    def test_mcu_alu(self) -> None:
        self._run("mcu", ["alu", "alu"], [encode_srai(4, 3, 9), encode_srl(24, 30, 31)])

    def test_picorv32_alu(self) -> None:
        self._run("picorv32", ["alu"], [0x2E280493])  # addi x9, x16, 0x2e2


class TestShippedPrograms(unittest.TestCase):
    """Continuation 5 step 2: the shipped-program silence gate's program list per base."""

    def test_mcu_shipped_list(self) -> None:
        from lemanruss.htl.proc_build import shipped_programs

        self.assertEqual(
            shipped_programs("mcu"),
            ("blink", "blink_interrupt", "blink_function_call", "interrupt"))

    def test_darkriscv_shipped_list(self) -> None:
        from lemanruss.htl.proc_build import shipped_programs

        self.assertEqual(shipped_programs("darkriscv"), ("firmware",))

    def test_picorv32_has_no_shipped_program(self) -> None:
        """Spec section 4: picorv32 has no shipped firmware in the checkout."""
        from lemanruss.htl.proc_build import shipped_programs

        self.assertEqual(shipped_programs("picorv32"), ())

    def test_shipped_silence_ok_vacuous_for_empty(self) -> None:
        from lemanruss.htl.proc_build import shipped_silence_ok

        self.assertTrue(shipped_silence_ok({}))

    def test_shipped_silence_ok_gates_on_rtl_and_nl_only(self) -> None:
        from lemanruss.htl.proc_build import shipped_silence_ok

        # iverilog disagreeing alone (the recorded, non-gating four-state difference) must not
        # fail the gate; rtl or nl disagreeing must.
        self.assertTrue(shipped_silence_ok(
            {"firmware": {"rtl": True, "nl": True, "iverilog": False}}))
        self.assertFalse(shipped_silence_ok(
            {"firmware": {"rtl": False, "nl": True, "iverilog": True}}))
        self.assertFalse(shipped_silence_ok(
            {"firmware": {"rtl": True, "nl": False, "iverilog": True}}))


@unittest.skipUnless(
    ODIN_BIN.is_file() and all(p.is_dir() for p in (MCU_UP, DARK_UP)),
    "needs a built Odin III and the mcu/darkriscv external checkouts",
)
class TestShippedSilenceReal(unittest.TestCase):
    """Real build: a known-clean fixed-word circuit must be silent on every shipped program of
    its base (Continuation 5 step 2's own gate, exercised end to end)."""

    def test_mcu_fixed_word_silent_on_shipped(self) -> None:
        from lemanruss.htl.proc_build import check_shipped_silence, shipped_silence_ok

        with tempfile.TemporaryDirectory() as tmp:
            silence = check_shipped_silence(
                "mcu", [0x12300293], ["reset"], ODIN_BIN, Path(tmp), "t-ship-mcu")
            self.assertTrue(shipped_silence_ok(silence), silence)

    def test_darkriscv_fixed_word_silent_on_shipped(self) -> None:
        from lemanruss.htl.proc_build import check_shipped_silence, shipped_silence_ok

        with tempfile.TemporaryDirectory() as tmp:
            silence = check_shipped_silence(
                "darkriscv", [0x12300393], ["reset"], ODIN_BIN, Path(tmp), "t-ship-dark")
            self.assertTrue(shipped_silence_ok(silence), silence)


if __name__ == "__main__":
    unittest.main()
