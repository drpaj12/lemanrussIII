"""Tests for lemanruss.htl.insert_hdl: text splice, then an Odin III read_verilog --parse-only
re-validation of the edited result (the parse check the brief asks for)."""

from __future__ import annotations

import unittest

from lemanruss.htl.insert_hdl import (
    NoAssignDriver,
    insert_always_on_trigger,
    insert_comb_rare_trigger,
    insert_dos_reset_payload,
    insert_dos_stuck_payload,
    insert_energy_payload,
    insert_err_bit_payload,
    insert_input_pattern_trigger,
    insert_seq_counter_trigger,
    insert_slowdown_payload,
)
from lemanruss.htl.payloads import (
    DosResetPayload,
    DosStuckPayload,
    EnergyPayload,
    ErrHiPayload,
    ErrLoPayload,
    SlowdownPayload,
)
from lemanruss.htl.triggers import CombRareTrigger, InputPatternTrigger, SeqCounterTrigger
from tests.helpers import odin_available

SAMPLE = """\
module rare_and(input a, input b, output y, output [3:0] word);
    assign y = a & b;
    assign word = {a, b, a, b};
endmodule
"""

CLOCKED_SAMPLE = """\
module ticker(input clk, input a, input b, output y);
    assign y = a & b;
endmodule
"""


class TestInsertCombRareTrigger(unittest.TestCase):
    def test_declares_wire_before_endmodule(self) -> None:
        trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 0)))
        edited = insert_comb_rare_trigger(SAMPLE, trigger)
        self.assertIn("wire __htl_trigger = (a == 1) && (b == 0);", edited)
        self.assertLess(edited.index("__htl_trigger"), edited.index("endmodule"))

    def test_empty_nets_raises(self) -> None:
        with self.assertRaises(ValueError):
            insert_comb_rare_trigger(SAMPLE, CombRareTrigger(k=2, nets=()))


class TestInsertDosStuckPayload(unittest.TestCase):
    def test_rewrites_assign(self) -> None:
        payload = DosStuckPayload(victim="y", stuck_value=1)
        edited = insert_dos_stuck_payload(SAMPLE, payload)
        self.assertIn("assign y = __htl_trigger ? 1 : (a & b);", edited)

    def test_no_assign_driver_raises(self) -> None:
        payload = DosStuckPayload(victim="nope", stuck_value=1)
        with self.assertRaises(NoAssignDriver):
            insert_dos_stuck_payload(SAMPLE, payload)


class TestInsertErrBitPayload(unittest.TestCase):
    def test_force_hi_bits_uses_or(self) -> None:
        payload = ErrHiPayload(word="word", bits=2, force=True)
        edited = insert_err_bit_payload(SAMPLE, payload, width=4)
        self.assertIn("4'd12", edited)  # top 2 bits of a 4-bit word: 0b1100 = 12
        self.assertIn(" | (", edited)

    def test_flip_lo_bits_uses_xor(self) -> None:
        payload = ErrLoPayload(word="word", bits=2, force=False)
        edited = insert_err_bit_payload(SAMPLE, payload, width=4)
        self.assertIn("4'd3", edited)  # bottom 2 bits: 0b0011 = 3
        self.assertIn(" ^ (", edited)


class TestInsertAlwaysOnTrigger(unittest.TestCase):
    def test_declares_constant_wire(self) -> None:
        edited = insert_always_on_trigger(SAMPLE)
        self.assertIn("wire __htl_trigger = 1'b1;", edited)


class TestInsertInputPatternTrigger(unittest.TestCase):
    def test_declares_comparator(self) -> None:
        trigger = InputPatternTrigger(bits=("a", "b"), magic_value=0b10)
        edited = insert_input_pattern_trigger(SAMPLE, trigger)
        self.assertIn("{a, b} == 2'd2", edited)

    def test_empty_bits_raises(self) -> None:
        with self.assertRaises(ValueError):
            insert_input_pattern_trigger(SAMPLE, InputPatternTrigger(bits=(), magic_value=0))


class TestInsertSeqCounterTrigger(unittest.TestCase):
    def test_declares_counter_and_sticky_reg(self) -> None:
        trigger = SeqCounterTrigger(n=8, condition_k=2, nets=(("a", 1), ("b", 1)))
        edited = insert_seq_counter_trigger(CLOCKED_SAMPLE, trigger, clock="clk")
        self.assertIn("reg __htl_trigger;", edited)
        self.assertIn("__htl_trigger_counter", edited)
        self.assertIn("posedge clk", edited)

    def test_empty_nets_raises(self) -> None:
        with self.assertRaises(ValueError):
            insert_seq_counter_trigger(
                CLOCKED_SAMPLE, SeqCounterTrigger(n=8, nets=()), clock="clk"
            )


class TestInsertDosResetPayload(unittest.TestCase):
    def test_forces_reset_net_to_one(self) -> None:
        payload = DosResetPayload(reset_net="y")
        edited = insert_dos_reset_payload(SAMPLE, payload)
        self.assertIn("assign y = __htl_trigger ? 1 : (a & b);", edited)


class TestInsertEnergyPayload(unittest.TestCase):
    def test_declares_toggle_register(self) -> None:
        payload = EnergyPayload(fraction=0.5)
        edited = insert_energy_payload(CLOCKED_SAMPLE, payload, clock="clk", node_count=4)
        self.assertIn("reg [1:0] __htl_trigger_energy;", edited)  # round(0.5*4) = 2 bits
        self.assertIn("<= ~__htl_trigger_energy;", edited)


class TestInsertSlowdownPayload(unittest.TestCase):
    def test_adds_depth_levels(self) -> None:
        payload = SlowdownPayload(victim="y")
        edited = insert_slowdown_payload(SAMPLE, payload, depth=3)
        self.assertEqual(edited.count("| 1'b0"), 3)


@unittest.skipUnless(odin_available(), "Odin III not available (set ODIN3_LIB/PYTHONPATH)")
class TestVerilogParses(unittest.TestCase):
    def test_edited_source_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 0)))
        with_trigger = insert_comb_rare_trigger(SAMPLE, trigger)
        payload = DosStuckPayload(victim="y", stuck_value=1)
        edited = insert_dos_stuck_payload(with_trigger, payload)
        verilog_parses(edited)  # raises on a parse error; nothing to assert on success

    def test_err_bit_edit_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        payload = ErrHiPayload(word="word", bits=2, force=True)
        edited = insert_err_bit_payload(SAMPLE, payload, width=4)
        verilog_parses(edited)

    def test_always_on_trigger_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        verilog_parses(insert_always_on_trigger(SAMPLE))

    def test_input_pattern_trigger_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        trigger = InputPatternTrigger(bits=("a", "b"), magic_value=0b10)
        verilog_parses(insert_input_pattern_trigger(SAMPLE, trigger))

    def test_seq_counter_trigger_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        trigger = SeqCounterTrigger(n=8, condition_k=1, nets=(("a", 1),))
        edited = insert_seq_counter_trigger(CLOCKED_SAMPLE, trigger, clock="clk")
        verilog_parses(edited)

    def test_dos_reset_payload_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        with_trigger = insert_always_on_trigger(SAMPLE)
        edited = insert_dos_reset_payload(with_trigger, DosResetPayload(reset_net="y"))
        verilog_parses(edited)

    def test_energy_payload_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        with_trigger = insert_always_on_trigger(CLOCKED_SAMPLE)
        edited = insert_energy_payload(with_trigger, EnergyPayload(fraction=0.5), "clk", 4)
        verilog_parses(edited)

    def test_slowdown_payload_parses(self) -> None:
        from lemanruss.htl.odin_check import verilog_parses

        edited = insert_slowdown_payload(SAMPLE, SlowdownPayload(victim="y"), depth=3)
        verilog_parses(edited)


if __name__ == "__main__":
    unittest.main()
