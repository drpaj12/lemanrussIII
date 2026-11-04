"""End-to-end: Verilog -> write_blif --gates-as-names -> insert_netlist -> read_blif -> verify.

Needs Odin III (ODIN3_LIB/PYTHONPATH); skipped otherwise. Exercises the full netlist pipeline on
the rare_and fixture: trigger = (a==1, b==1), payload = force y to 1 when triggered.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.blif_text import parse_single_model, render
from lemanruss.htl.insert_netlist import insert_comb_rare_trigger, insert_dos_stuck_payload
from lemanruss.htl.payloads import DosStuckPayload
from lemanruss.htl.triggers import CombRareTrigger
from tests.helpers import odin_available

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _write_infected_blif(tmp: Path) -> Path:
    from odin3 import Design

    clean_path = FIXTURES / "rare_and.v"
    blif_path = tmp / "clean.blif"
    with Design() as design:
        design.run_script(f'read_verilog "{clean_path}"; proc; opt; lower')
        design.run_pass("write_blif", f"--gates-as-names {blif_path}")

    model = parse_single_model(blif_path.read_text(encoding="utf-8"))
    trigger = CombRareTrigger(k=2, nets=(("a", 1), ("b", 1)))
    with_trigger = insert_comb_rare_trigger(model, trigger)
    payload = DosStuckPayload(victim="y", stuck_value=1)
    infected = insert_dos_stuck_payload(with_trigger, payload)

    infected_path = tmp / "infected.blif"
    infected_path.write_text(render(infected), encoding="utf-8")
    return infected_path


@unittest.skipUnless(odin_available(), "Odin III not available (set ODIN3_LIB/PYTHONPATH)")
class TestVerifyFires(unittest.TestCase):
    def test_fires_on_trigger_condition(self) -> None:
        from odin3 import Design

        from lemanruss.htl.verify import check_fires

        with tempfile.TemporaryDirectory() as tmp:
            infected_path = _write_infected_blif(Path(tmp))
            with Design() as design:
                design.run_pass("read_blif", str(infected_path))
                result = check_fires(design, drive={"a": 1, "b": 1}, victim="y")
                self.assertTrue(result.fired)
                self.assertEqual(result.victim_after, 1)

    def test_does_not_fire_off_trigger(self) -> None:
        from odin3 import Design

        from lemanruss.htl.verify import check_fires

        with tempfile.TemporaryDirectory() as tmp:
            infected_path = _write_infected_blif(Path(tmp))
            with Design() as design:
                design.run_pass("read_blif", str(infected_path))
                result = check_fires(design, drive={"a": 1, "b": 0}, victim="y")
                self.assertFalse(result.fired)
                self.assertEqual(result.victim_after, 0)  # a&b with a=1,b=0 is 0, unforced


if __name__ == "__main__":
    unittest.main()
