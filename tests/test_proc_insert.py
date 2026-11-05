"""Tests for lemanruss.htl.proc_insert: text splice on the real upstream core files, then an
Odin III read_verilog --parse-only re-validation (the brief's parse check) of the patched module
in isolation plus its dependency stubs."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.proc_insert import (
    PatchNotFound,
    insert_dark_kinded_multitrojan,
    insert_dark_multitrojan,
    insert_dark_trojan,
    insert_mcu_kinded_multitrojan,
    insert_mcu_multitrojan,
    insert_mcu_trojan,
    insert_picorv32_kinded_multitrojan,
)
from tests.helpers import odin_available

WS = Path(os.environ.get("ODIN3_WS", "~/odin3-ws")).expanduser()  # holds odin3/, external/
MCU_CORE = WS / "external/Arduino-on-RISC-V/quartus_project_revert_timer/single_cycle_core.v"
DARK_RTL_DIR = WS / "external/darkriscv/rtl"
DARK_CORE = DARK_RTL_DIR / "darkriscv.v"
PICO_CORE = WS / "external" / "picorv32" / "picorv32.v"

MAGIC_WORD = 0x2a500293  # addi x5, x0, 0x2a5 (lemanruss.htl.rv32i.encode_addi(5, 0, 0x2a5))
MAGIC_SEQ = [0x00500293, 0x00600313, 0x00700393]  # addi x5,x0,5; addi x6,x0,6; addi x7,x0,7


@unittest.skipUnless(MCU_CORE.is_file(), "needs the external/Arduino-on-RISC-V checkout "
                     "(CLAUDE.md: never committed; not present e.g. in CI)")
class TestMcuPatch(unittest.TestCase):
    def setUp(self) -> None:
        self.source = MCU_CORE.read_text()

    def test_magic_word_patches_fi_connection(self) -> None:
        patched = insert_mcu_trojan(self.source, [MAGIC_WORD])
        self.assertIn("__htl_pc_mux", patched)
        self.assertNotIn(".next_PC_select(next_PC_select),", patched)
        self.assertIn(f"32'h{MAGIC_WORD:08x}", patched)
        self.assertEqual(patched.count("endmodule"), self.source.count("endmodule"))

    def test_magic_sequence_has_fsm(self) -> None:
        patched = insert_mcu_trojan(self.source, MAGIC_SEQ)
        self.assertIn("__htl_seq_state", patched)
        for w in MAGIC_SEQ:
            self.assertIn(f"32'h{w:08x}", patched)

    def test_missing_patch_point_raises(self) -> None:
        with self.assertRaises(PatchNotFound):
            insert_mcu_trojan("module m; endmodule", [MAGIC_WORD])

    def test_force_inactive_ties_trigger_to_zero(self) -> None:
        patched = insert_mcu_trojan(self.source, [MAGIC_WORD], force_inactive=True)
        self.assertIn("wire __htl_trigger = 1'b0;", patched)
        self.assertNotIn(f"32'h{MAGIC_WORD:08x}", patched)
        self.assertIn("__htl_pc_mux", patched)  # payload wiring is still present

    @unittest.skipUnless(odin_available(), "needs ODIN3_LIB/PYTHONPATH")
    def test_patched_core_still_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        patched = insert_mcu_trojan(self.source, [MAGIC_WORD])
        # single_cycle_core.v on its own (no instances resolved) parses standalone under
        # --parse-only, same as the clean file; a syntax error in the splice would fail here.
        verilog_parses(patched)
        verilog_parses(self.source)  # control: the unpatched file also parses standalone

    def test_multitrojan_independent_triggers(self) -> None:
        words = [MAGIC_WORD, 0x00500293, 0x00600313]  # 3 distinct magic words, one per Trojan
        patched, names = insert_mcu_multitrojan(self.source, words)
        self.assertEqual(names, ["__htl_trigger_0", "__htl_trigger_1", "__htl_trigger_2"])
        for w in words:
            self.assertIn(f"32'h{w:08x}", patched)
        self.assertIn(
            "wire __htl_trigger = __htl_trigger_0 | __htl_trigger_1 | __htl_trigger_2;", patched)
        self.assertEqual(patched.count("endmodule"), self.source.count("endmodule"))

    def test_multitrojan_rejects_duplicate_words(self) -> None:
        with self.assertRaises(ValueError):
            insert_mcu_multitrojan(self.source, [MAGIC_WORD, MAGIC_WORD])

    def test_multitrojan_force_inactive(self) -> None:
        patched, names = insert_mcu_multitrojan(
            self.source, [MAGIC_WORD, 0x00500293], force_inactive=True)
        for n in names:
            self.assertIn(f"wire {n} = 1'b0;", patched)
        self.assertNotIn(f"32'h{MAGIC_WORD:08x}", patched)

    @unittest.skipUnless(odin_available(), "needs ODIN3_LIB/PYTHONPATH")
    def test_multitrojan_still_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        patched, _ = insert_mcu_multitrojan(self.source, [MAGIC_WORD, 0x00500293, 0x00600313])
        verilog_parses(patched)


@unittest.skipUnless(DARK_CORE.is_file(), "needs the external/darkriscv checkout (CLAUDE.md: "
                     "never committed; not present e.g. in CI)")
class TestDarkPatch(unittest.TestCase):
    def setUp(self) -> None:
        self.source = DARK_CORE.read_text()

    def test_magic_word_patches_xres(self) -> None:
        patched = insert_dark_trojan(self.source, [MAGIC_WORD])
        self.assertIn("__htl_trigger", patched)
        self.assertIn("XRES <= RES || __htl_trigger;", patched)
        self.assertIn("wire __htl_trigger = (XIDATA ==", patched)
        # the new trigger line itself must not gate on IDACK any more (IDACK is still a normal
        # port/signal elsewhere in the base RTL, so it is not absent from the whole file).
        trigger_line = next(ln for ln in patched.splitlines() if "wire __htl_trigger =" in ln)
        self.assertNotIn("IDACK", trigger_line)
        self.assertIn("sample the execute-stage latched instruction", patched)
        self.assertEqual(patched.count("endmodule"), 1)

    def test_magic_sequence_has_fsm(self) -> None:
        patched = insert_dark_trojan(self.source, MAGIC_SEQ)
        self.assertIn("__htl_seq_state", patched)
        self.assertIn("if (!HLT) case (__htl_seq_state)", patched)
        self.assertIn("wire __htl_trigger = (__htl_seq_state == 2) && (XIDATA == "
                      "__htl_seq_2);", patched)

    def test_missing_patch_point_raises(self) -> None:
        with self.assertRaises(PatchNotFound):
            insert_dark_trojan("module m; endmodule", [MAGIC_WORD])

    def test_force_inactive_ties_trigger_to_zero(self) -> None:
        patched = insert_dark_trojan(self.source, [MAGIC_WORD], force_inactive=True)
        self.assertIn("wire __htl_trigger = 1'b0;", patched)
        self.assertNotIn(f"32'h{MAGIC_WORD:08x}", patched)

    @unittest.skipUnless(odin_available(), "needs ODIN3_LIB/PYTHONPATH")
    def test_patched_core_still_parses(self) -> None:
        patched = insert_dark_trojan(self.source, [MAGIC_WORD])
        # darkriscv.v does `` `include "../rtl/config.vh" `` (a self-referential relative path
        # from its own directory, as the real tree has it: rtl/darkriscv.v including
        # rtl/../rtl/config.vh); re-create a one-level rtl/ dir with config.vh alongside so
        # --parse-only can resolve the include the same way prepare.sh's copy does.
        from odin3 import Design

        with tempfile.TemporaryDirectory() as tmp:
            rtl = Path(tmp) / "rtl"
            rtl.mkdir()
            shutil.copy(DARK_RTL_DIR / "config.vh", rtl / "config.vh")
            (rtl / "patched.v").write_text(patched)
            (rtl / "clean.v").write_text(self.source)
            with Design() as design:
                design.run_pass("read_verilog", f'--parse-only "{rtl / "patched.v"}"')
            with Design() as design:
                design.run_pass("read_verilog", f'--parse-only "{rtl / "clean.v"}"')

    def test_multitrojan_independent_triggers(self) -> None:
        words = [MAGIC_WORD, 0x00500293, 0x00600313]
        patched, names = insert_dark_multitrojan(self.source, words)
        self.assertEqual(names, ["__htl_trigger_0", "__htl_trigger_1", "__htl_trigger_2"])
        for w in words:
            self.assertIn(f"32'h{w:08x}", patched)
            self.assertIn(f"(XIDATA == 32'h{w:08x});", patched)
            trig_line = next(
                ln for ln in patched.splitlines()
                if f"32'h{w:08x}" in ln and "wire __htl_trigger_" in ln
            )
            self.assertNotIn("IDACK", trig_line)
        self.assertIn("XRES <= RES || __htl_trigger;", patched)
        self.assertIn("sample the execute-stage latched instruction", patched)
        self.assertEqual(patched.count("endmodule"), 1)

    def test_multitrojan_rejects_duplicate_words(self) -> None:
        with self.assertRaises(ValueError):
            insert_dark_multitrojan(self.source, [MAGIC_WORD, MAGIC_WORD])

    def test_multitrojan_force_inactive(self) -> None:
        patched, names = insert_dark_multitrojan(
            self.source, [MAGIC_WORD, 0x00500293], force_inactive=True)
        for n in names:
            self.assertIn(f"wire {n} = 1'b0;", patched)


# rc1 Continuation 3 (2026-11-04): per-Trojan payload kind (reset/stall/alu), on all three bases.
KINDS = ["reset", "stall", "alu"]
KIND_WORDS = [MAGIC_WORD, 0x00100293, 0x00200313]


@unittest.skipUnless(MCU_CORE.is_file(), "needs the external/Arduino-on-RISC-V checkout")
class TestMcuKindedPatch(unittest.TestCase):
    def setUp(self) -> None:
        self.source = MCU_CORE.read_text()

    def test_three_kinds_wire_up(self) -> None:
        patched, names = insert_mcu_kinded_multitrojan(self.source, KIND_WORDS, KINDS)
        self.assertEqual(names, ["__htl_trigger_0", "__htl_trigger_1", "__htl_trigger_2"])
        self.assertIn("wire __htl_trigger_reset = __htl_trigger_0;", patched)
        self.assertIn("wire __htl_trigger_stall = __htl_trigger_1;", patched)
        self.assertIn("wire __htl_trigger_alu = __htl_trigger_2;", patched)
        self.assertIn("__htl_pc_mux", patched)
        self.assertIn("__htl_alu_raw", patched)
        self.assertIn("ALU_operation==6'd12 || ALU_operation==6'd13", patched)
        self.assertEqual(patched.count("endmodule"), self.source.count("endmodule"))

    def test_only_alu_kind_present_others_zero(self) -> None:
        patched, _ = insert_mcu_kinded_multitrojan(self.source, [MAGIC_WORD], ["alu"])
        self.assertIn("wire __htl_trigger_reset = 1'b0;", patched)
        self.assertIn("wire __htl_trigger_stall = 1'b0;", patched)

    def test_rejects_bad_kind(self) -> None:
        with self.assertRaises(ValueError):
            insert_mcu_kinded_multitrojan(self.source, [MAGIC_WORD], ["rotate"])

    def test_force_inactive(self) -> None:
        patched, names = insert_mcu_kinded_multitrojan(
            self.source, KIND_WORDS, KINDS, force_inactive=True)
        for n in names:
            self.assertIn(f"wire {n} = 1'b0;", patched)

    @unittest.skipUnless(odin_available(), "needs ODIN3_LIB/PYTHONPATH")
    def test_patched_core_still_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        patched, _ = insert_mcu_kinded_multitrojan(self.source, KIND_WORDS, KINDS)
        verilog_parses(patched)


@unittest.skipUnless(DARK_CORE.is_file(), "needs the external/darkriscv checkout")
class TestDarkKindedPatch(unittest.TestCase):
    def setUp(self) -> None:
        self.source = DARK_CORE.read_text()

    def test_three_kinds_wire_up(self) -> None:
        patched, names = insert_dark_kinded_multitrojan(self.source, KIND_WORDS, KINDS)
        self.assertEqual(names, ["__htl_trigger_0", "__htl_trigger_1", "__htl_trigger_2"])
        self.assertIn("XRES <= RES || __htl_trigger_reset;", patched)
        self.assertIn("__htl_trigger_stall ||", patched)
        self.assertIn("__htl_rmdata", patched)
        self.assertIn("FCT3==3'd5", patched)
        self.assertEqual(patched.count("endmodule"), 1)

    def test_rejects_bad_kind(self) -> None:
        with self.assertRaises(ValueError):
            insert_dark_kinded_multitrojan(self.source, [MAGIC_WORD], ["rotate"])

    def test_force_inactive(self) -> None:
        patched, names = insert_dark_kinded_multitrojan(
            self.source, KIND_WORDS, KINDS, force_inactive=True)
        for n in names:
            self.assertIn(f"wire {n} = 1'b0;", patched)

    @unittest.skipUnless(odin_available(), "needs ODIN3_LIB/PYTHONPATH")
    def test_patched_core_still_parses(self) -> None:
        from odin3 import Design

        patched, _ = insert_dark_kinded_multitrojan(self.source, KIND_WORDS, KINDS)
        with tempfile.TemporaryDirectory() as tmp:
            rtl = Path(tmp) / "rtl"
            rtl.mkdir()
            shutil.copy(DARK_RTL_DIR / "config.vh", rtl / "config.vh")
            (rtl / "patched.v").write_text(patched)
            with Design() as design:
                design.run_pass("read_verilog", f'--parse-only "{rtl / "patched.v"}"')


@unittest.skipUnless(PICO_CORE.is_file(), "needs the external/picorv32 checkout (CLAUDE.md: "
                     "never committed; not present e.g. in CI)")
class TestPicorv32KindedPatch(unittest.TestCase):
    def setUp(self) -> None:
        self.source = PICO_CORE.read_text()

    def test_three_kinds_wire_up(self) -> None:
        patched, names = insert_picorv32_kinded_multitrojan(self.source, KIND_WORDS, KINDS)
        self.assertEqual(names, ["__htl_trigger_0", "__htl_trigger_1", "__htl_trigger_2"])
        self.assertIn("if (!resetn || __htl_trigger_reset) begin", patched)
        self.assertIn(
            "decoder_trigger <= !__htl_trigger_stall && mem_do_rinst && mem_done;", patched)
        self.assertIn("instr_srli || instr_srl", patched)
        self.assertIn("next_insn_opcode == 32'h", patched)
        self.assertEqual(patched.count("endmodule"), self.source.count("endmodule"))

    def test_rejects_bad_kind(self) -> None:
        with self.assertRaises(ValueError):
            insert_picorv32_kinded_multitrojan(self.source, [MAGIC_WORD], ["rotate"])

    def test_force_inactive(self) -> None:
        patched, names = insert_picorv32_kinded_multitrojan(
            self.source, KIND_WORDS, KINDS, force_inactive=True)
        for n in names:
            self.assertIn(f"wire {n} = 1'b0;", patched)

    @unittest.skipUnless(odin_available(), "needs ODIN3_LIB/PYTHONPATH")
    def test_patched_core_still_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        patched, _ = insert_picorv32_kinded_multitrojan(self.source, KIND_WORDS, KINDS)
        verilog_parses(patched)


if __name__ == "__main__":
    unittest.main()
