"""Unit tests for lemanruss.htl: triggers, payloads, composition, manifest (no Odin III needed)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.manifest import CatalogueEntry, write_labels, write_manifest
from lemanruss.htl.payloads import DosStuckPayload, EnergyPayload, ErrHiPayload, SlowdownPayload
from lemanruss.htl.triggers import AlwaysOnTrigger, CombRareTrigger, InputPatternTrigger
from lemanruss.htl.trojan import IllegalCombination, compose


class TestTriggers(unittest.TestCase):
    def test_comb_rare_description_mentions_k(self) -> None:
        trig = CombRareTrigger(k=3)
        self.assertIn("3", trig.description())

    def test_input_pattern_activation_is_named_in_stealth_note(self) -> None:
        trig = InputPatternTrigger(bits=("a", "b"), magic_value=0b10)
        self.assertIn("width", trig.stealth_note())
        self.assertIn("0x2", trig.description())


class TestPayloads(unittest.TestCase):
    def test_dos_stuck_effect_measure(self) -> None:
        payload = DosStuckPayload(victim="out", stuck_value=1)
        self.assertEqual(payload.effect_measure(), "functional-diff")

    def test_energy_effect_measure(self) -> None:
        self.assertEqual(EnergyPayload().effect_measure(), "toggle-count-delta")

    def test_slowdown_effect_measure(self) -> None:
        self.assertEqual(SlowdownPayload(victim="n1").effect_measure(), "logic-level-depth-delta")


class TestCompose(unittest.TestCase):
    def test_legal_combination(self) -> None:
        trig = CombRareTrigger(k=4, nets=(("n1", 1), ("n2", 0)))
        payload = DosStuckPayload(victim="out", stuck_value=1)
        trojan = compose(trig, payload, "netlist", site="out")
        self.assertEqual(trojan.id, "t-comb-rare__p-dos-stuck__netlist")
        self.assertEqual(trojan.level, "netlist")

    def test_always_on_rejects_functional_payload(self) -> None:
        with self.assertRaises(IllegalCombination):
            compose(AlwaysOnTrigger(), DosStuckPayload(victim="out"), "hdl")

    def test_always_on_accepts_energy_payload(self) -> None:
        trojan = compose(AlwaysOnTrigger(), EnergyPayload(), "hdl")
        self.assertEqual(trojan.id, "t-always-on__p-energy__hdl")

    def test_always_on_accepts_slowdown_payload(self) -> None:
        trojan = compose(AlwaysOnTrigger(), SlowdownPayload(victim="n1"), "netlist")
        self.assertEqual(trojan.id, "t-always-on__p-slowdown__netlist")

    def test_to_dict_is_json_serialisable(self) -> None:
        trojan = compose(CombRareTrigger(k=2), ErrHiPayload(word="out", bits=2), "hdl")
        json.dumps(trojan.to_dict())  # must not raise


class TestManifest(unittest.TestCase):
    def test_write_manifest_and_labels_round_trip(self) -> None:
        payload = DosStuckPayload(victim="out", stuck_value=0)
        trojan = compose(CombRareTrigger(k=2), payload, "netlist")
        entry = CatalogueEntry(base_design="design_a", trojan=trojan, verification={"fires": True})
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            labels_path = Path(tmp) / "labels.json"
            write_manifest([entry], manifest_path)
            write_labels([entry], labels_path)

            doc = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(doc["schema"], 1)
            self.assertEqual(doc["entries"][0]["base_design"], "design_a")
            self.assertEqual(doc["entries"][0]["trojan"]["id"], trojan.id)

            labels = json.loads(labels_path.read_text(encoding="utf-8"))
            self.assertEqual(labels[f"design_a::{trojan.id}"], trojan.id)

    def test_manifest_file_ends_with_newline(self) -> None:
        trojan = compose(CombRareTrigger(k=2), DosStuckPayload(victim="out"), "netlist")
        entry = CatalogueEntry(base_design="d", trojan=trojan)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.json"
            write_manifest([entry], path)
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))


if __name__ == "__main__":
    unittest.main()
