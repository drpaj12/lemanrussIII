"""Seeker-Proc rc3 fourth base, OpenCores mips_16: encoder, magic words, patches, and (when the
upstream checkout and a built Odin III exist) one real build per payload kind."""

from __future__ import annotations

import os
import random
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl import mips16
from lemanruss.htl.proc_insert import PatchNotFound
from lemanruss.htl.proc_witness import alu_magic_word, forbidden_words

WS = Path(os.environ.get("ODIN3_WS", "~/odin3-ws")).expanduser()
UP = WS / "external" / "opencores" / "mips_16" / "rtl"
ODIN = Path(os.environ.get("ODIN3_BIN", str(WS / "odin3" / "build" / "rel-main3" / "odin3")))


class TestEncoder(unittest.TestCase):
    def test_known_words(self) -> None:
        # ADDI R1,R0,8 and SUB R6,R4,R5 as in the project's test1.asm
        self.assertEqual(mips16.enc_i("ADDI", 1, 0, 8), 0b1001001000001000)
        self.assertEqual(mips16.enc_r("SUB", 6, 4, 5), 0b0010110100101000)

    def test_magic_words_are_legal_register_writers(self) -> None:
        rng = random.Random(3)
        seen: set[int] = set()
        for _ in range(300):
            w = mips16.random_magic_word(rng, seen)
            seen.add(w)
            self.assertTrue(0 < w < 1 << 16)
            self.assertIn(w >> 12, {1, 2, 3, 4, 5, 6, 7, 8, 9})
            self.assertNotEqual((w >> 9) & 7, 0)
        self.assertEqual(len(seen), 300)

    def test_alu_magic_word_dispatch_and_rejection(self) -> None:
        rng = random.Random(1)
        bad = {mips16.enc_i("ADDI", 1, 0, 21)}
        for _ in range(100):
            self.assertNotIn(alu_magic_word("mips_16", rng, bad), bad)

    def test_witnesses_fit_the_rom(self) -> None:
        w = mips16.alu_witness_words(mips16.enc_i("ADDI", 5, 0, 3))
        self.assertLess(len(w), mips16.PROG_DEPTH)
        self.assertIn(mips16.enc_r("SRU", 3, 1, 2), w)
        self.assertEqual(mips16.witness_words([])[-2:], mips16.STOP)

    def test_neutral_word_differs(self) -> None:
        self.assertNotEqual(mips16.neutral_word(0x9208), 0x9208)

    def test_bad_trigger_declarations(self) -> None:
        with self.assertRaises(ValueError):
            mips16.insert_mips16({}, [1, 1], ["reset", "stall"])


@unittest.skipUnless(UP.is_dir(), "needs external/opencores/mips_16")
class TestPatches(unittest.TestCase):
    def test_variant_has_no_x_and_no_memories(self) -> None:
        f = mips16._variant(mips16.load_upstream(UP))
        self.assertNotIn("1'bx", f["ID_stage.v"])
        self.assertNotIn("ALU_NC", f["alu.v"])
        self.assertNotIn("data_mem", f["MEM_stage.v"])
        self.assertNotIn("instruction_mem", f["IF_stage.v"])

    def test_forbidden_words_include_shipped(self) -> None:
        self.assertGreater(len(forbidden_words("mips_16", UP)), 20)

    def test_moved_upstream_text_fails_loudly(self) -> None:
        f = mips16.load_upstream(UP)
        f["alu.v"] = f["alu.v"].replace("ALU_NC", "ALU_XX")
        with self.assertRaises(PatchNotFound):
            mips16._variant(f)

    def test_infected_files_differ_only_by_tap_ports(self) -> None:
        f = mips16._variant(mips16.load_upstream(UP))
        g = mips16.insert_mips16(f, [mips16.enc_i("ADDI", 2, 1, 7)], ["alu"])
        self.assertIn("__htl_ir", g["ID_stage.v"])
        self.assertEqual(f["WB_stage.v"], g["WB_stage.v"])


@unittest.skipUnless(UP.is_dir() and ODIN.is_file(), "needs mips_16 checkout and ODIN3_BIN")
class TestEngines(unittest.TestCase):
    def test_each_kind_fires_and_neutral_is_silent(self) -> None:
        rng = random.Random(5)
        ex = forbidden_words("mips_16", UP)
        kinds = ["reset", "stall", "alu"]
        words = [mips16.random_magic_word(rng, ex | {0}) for _ in kinds]
        with tempfile.TemporaryDirectory() as td:
            w = Path(td)
            files = mips16.prepare_mips16(UP, w / "c")
            mips16.prepare_mips16(UP, w / "i", magic_words=words, kinds=kinds)
            for kind, wd in zip(kinds, words, strict=True):
                prog = (mips16.alu_witness_words(wd) if kind == "alu"
                        else mips16.witness_words([wd]))
                for d in ("c", "i"):
                    mips16.write_program(w / d, prog)
                c = mips16.run_once(w / "c", files, ODIN, 100, "t")
                i = mips16.run_once(w / "i", files, ODIN, 100, "t")
                for e in ("ref", "rtl", "nl"):
                    self.assertNotEqual(c[e], i[e], f"{kind} did not fire on {e}")
            for d in ("c", "i"):
                mips16.write_program(w / d, mips16.witness_words([]))
            c = mips16.run_once(w / "c", files, ODIN, 100, "n")
            i = mips16.run_once(w / "i", files, ODIN, 100, "n")
            for e in ("ref", "rtl", "nl"):
                self.assertEqual(c[e], i[e])


if __name__ == "__main__":
    unittest.main()
