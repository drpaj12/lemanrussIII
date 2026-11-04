"""Tests for lemanruss.htl.blif_text and insert_netlist: text-level edits, then an Odin III
read_blif re-validation of the edited result (the parse check the brief asks for)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.blif_text import find_names_block, parse_single_model, render
from lemanruss.htl.insert_netlist import (
    NoDriver,
    insert_always_on_trigger,
    insert_comb_rare_trigger,
    insert_dos_reset_payload,
    insert_dos_stuck_payload,
    insert_energy_payload,
    insert_err_bit_payload,
    insert_input_pattern_trigger,
    insert_slowdown_payload,
)
from lemanruss.htl.payloads import DosResetPayload, DosStuckPayload, EnergyPayload, ErrHiPayload
from lemanruss.htl.triggers import CombRareTrigger, InputPatternTrigger
from tests.helpers import odin_available

SAMPLE = """\
.model netnames
.inputs clk a b
.outputs y
.names a b n1
11 1
.latch n1 q re clk 0
.names q y
1 1
.end
"""


class TestBlifText(unittest.TestCase):
    def test_parse_single_model(self) -> None:
        model = parse_single_model(SAMPLE)
        self.assertEqual(model.name, "netnames")
        self.assertEqual(model.inputs, ["clk", "a", "b"])
        self.assertEqual(model.outputs, ["y"])
        self.assertIn(".names a b n1", model.body)

    def test_find_names_block(self) -> None:
        model = parse_single_model(SAMPLE)
        found = find_names_block(model, "y")
        self.assertIsNotNone(found)
        index, inputs, rows = found  # type: ignore[misc]
        self.assertEqual(inputs, ["q"])
        self.assertEqual(rows, ["1 1"])

    def test_find_names_block_none_for_primary_input(self) -> None:
        model = parse_single_model(SAMPLE)
        self.assertIsNone(find_names_block(model, "a"))  # a primary input, no .names drives it

    def test_render_round_trips_model_shape(self) -> None:
        model = parse_single_model(SAMPLE)
        rendered = render(model)
        self.assertTrue(rendered.startswith(".model netnames\n"))
        self.assertTrue(rendered.endswith(".end\n"))


class TestInsertCombRareTrigger(unittest.TestCase):
    def test_appends_and_line(self) -> None:
        model = parse_single_model(SAMPLE)
        trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 0)))
        edited = insert_comb_rare_trigger(model, trigger)
        self.assertIn(".names a b __htl_trigger", edited.body)
        self.assertIn("10 1", edited.body)

    def test_empty_nets_raises(self) -> None:
        model = parse_single_model(SAMPLE)
        with self.assertRaises(ValueError):
            insert_comb_rare_trigger(model, CombRareTrigger(k=2, nets=()))


class TestInsertDosStuckPayload(unittest.TestCase):
    def test_renames_driver_and_adds_mux(self) -> None:
        model = parse_single_model(SAMPLE)
        trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 0)))
        with_trigger = insert_comb_rare_trigger(model, trigger)
        payload = DosStuckPayload(victim="y", stuck_value=1)
        edited = insert_dos_stuck_payload(with_trigger, payload)
        self.assertIn(".names q __htl_tmp_y", edited.body)
        self.assertIn(".names __htl_trigger __htl_tmp_y y", edited.body)
        self.assertIn("1- 1", edited.body)

    def test_no_driver_raises(self) -> None:
        model = parse_single_model(SAMPLE)
        payload = DosStuckPayload(victim="a", stuck_value=1)  # a primary input, not .names-driven
        with self.assertRaises(NoDriver):
            insert_dos_stuck_payload(model, payload)


class TestInsertErrBitPayload(unittest.TestCase):
    def test_force_adds_mux(self) -> None:
        model = parse_single_model(SAMPLE)
        trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 0)))
        with_trigger = insert_comb_rare_trigger(model, trigger)
        payload = ErrHiPayload(word="y", bits=1, force=True)
        edited = insert_err_bit_payload(with_trigger, payload, "y")
        self.assertIn(".names __htl_trigger __htl_tmp_y y", edited.body)

    def test_flip_adds_xor_mux(self) -> None:
        model = parse_single_model(SAMPLE)
        trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 0)))
        with_trigger = insert_comb_rare_trigger(model, trigger)
        payload = ErrHiPayload(word="y", bits=1, force=False)
        edited = insert_err_bit_payload(with_trigger, payload, "y")
        self.assertIn("10 1", edited.body)


@unittest.skipUnless(odin_available(), "Odin III not available (set ODIN3_LIB/PYTHONPATH)")
class TestReadBlifValidation(unittest.TestCase):
    def test_edited_blif_parses_and_simulates(self) -> None:
        from odin3 import Design

        model = parse_single_model(SAMPLE)
        trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 0)))
        with_trigger = insert_comb_rare_trigger(model, trigger)
        payload = DosStuckPayload(victim="y", stuck_value=1)
        edited = insert_dos_stuck_payload(with_trigger, payload)
        text = render(edited)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "edited.blif"
            path.write_text(text, encoding="utf-8")
            with Design() as design:
                design.run_pass("read_blif", str(path))  # a bad edit is a located parse error
                top = design.top()
                self.assertIsNotNone(top)
                assert top is not None
                self.assertIsNotNone(top.net("__htl_trigger"))


class TestInsertAlwaysOnTrigger(unittest.TestCase):
    def test_appends_constant_block(self) -> None:
        model = parse_single_model(SAMPLE)
        edited = insert_always_on_trigger(model)
        self.assertIn(".names __htl_trigger", edited.body)
        self.assertIn("1", edited.body)


class TestInsertInputPatternTrigger(unittest.TestCase):
    def test_appends_pattern_and_line(self) -> None:
        model = parse_single_model(SAMPLE)
        trigger = InputPatternTrigger(bits=("a", "b"), magic_value=0b10)
        edited = insert_input_pattern_trigger(model, trigger)
        self.assertIn(".names a b __htl_trigger", edited.body)
        self.assertIn("10 1", edited.body)

    def test_empty_bits_raises(self) -> None:
        model = parse_single_model(SAMPLE)
        with self.assertRaises(ValueError):
            insert_input_pattern_trigger(model, InputPatternTrigger(bits=(), magic_value=0))


class TestInsertDosResetPayload(unittest.TestCase):
    def test_forces_reset_net(self) -> None:
        model = parse_single_model(SAMPLE)
        with_trigger = insert_always_on_trigger(model)
        edited = insert_dos_reset_payload(with_trigger, DosResetPayload(reset_net="y"))
        self.assertIn(".names __htl_trigger __htl_tmp_y y", edited.body)


class TestInsertEnergyPayload(unittest.TestCase):
    def test_adds_latch_per_toggle_bit(self) -> None:
        model = parse_single_model(SAMPLE)
        with_trigger = insert_always_on_trigger(model)
        edited = insert_energy_payload(with_trigger, EnergyPayload(fraction=0.5), "clk", 4)
        latches = [line for line in edited.body if line.startswith(".latch __htl_energy_d")]
        self.assertEqual(len(latches), 2)  # round(0.5 * 4) = 2


class TestInsertSlowdownPayloadNetlist(unittest.TestCase):
    def test_adds_depth_buffer_stages(self) -> None:
        model = parse_single_model(SAMPLE)
        from lemanruss.htl.payloads import SlowdownPayload

        edited = insert_slowdown_payload(model, SlowdownPayload(victim="y"), depth=3)
        buffer_rows = [line for line in edited.body if line == "1 1"]
        # 1 original ".names q y" row plus 3 new buffer-stage rows
        self.assertEqual(len(buffer_rows), 4)


@unittest.skipUnless(odin_available(), "Odin III not available (set ODIN3_LIB/PYTHONPATH)")
class TestRound2ReadBlifValidation(unittest.TestCase):
    def test_energy_payload_parses_and_latches(self) -> None:
        from odin3 import Design

        model = parse_single_model(SAMPLE)
        with_trigger = insert_always_on_trigger(model)
        edited = insert_energy_payload(with_trigger, EnergyPayload(fraction=1.0), "clk", 2)
        text = render(edited)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "energy.blif"
            path.write_text(text, encoding="utf-8")
            with Design() as design:
                design.run_pass("read_blif", str(path))
                top = design.top()
                assert top is not None
                self.assertIsNotNone(top.net("__htl_energy_q0"))
                self.assertIsNotNone(top.net("__htl_energy_q1"))

    def test_input_pattern_trigger_parses(self) -> None:
        from odin3 import Design

        model = parse_single_model(SAMPLE)
        trigger = InputPatternTrigger(bits=("a", "b"), magic_value=0b10)
        edited = insert_input_pattern_trigger(model, trigger)
        text = render(edited)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pattern.blif"
            path.write_text(text, encoding="utf-8")
            with Design() as design:
                design.run_pass("read_blif", str(path))

    def test_slowdown_payload_parses(self) -> None:
        from odin3 import Design

        from lemanruss.htl.payloads import SlowdownPayload

        model = parse_single_model(SAMPLE)
        edited = insert_slowdown_payload(model, SlowdownPayload(victim="y"), depth=3)
        text = render(edited)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "slowdown.blif"
            path.write_text(text, encoding="utf-8")
            with Design() as design:
                design.run_pass("read_blif", str(path))


if __name__ == "__main__":
    unittest.main()
