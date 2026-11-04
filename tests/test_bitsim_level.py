"""bitsim: level-sensitive latches (`ah` / `al`) are transparent, not edge flip-flops."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.bitsim import compile_model, replay
from lemanruss.htl.blif_text import parse_single_model
from tests.helpers import odin_available

LEVEL = """\
.model lv
.inputs d en
.outputs y z w
.latch d q ah en 0
.latch d r al en 0
.latch d f re clk 0
.names q y
1 1
.names r z
1 1
.names f w
1 1
.end
"""

NO_FF = """\
.model lv
.inputs d en
.outputs y z
.latch d q ah en 0
.latch d r al en 0
.names q y
1 1
.names r z
1 1
.end
"""

STEPS = [
    {"d": 1, "en": 1},  # ah transparent: q = 1; al closed: r holds 0; ff still 0 this cycle
    {"d": 0, "en": 0},  # ah holds 1; al transparent: r = 0; ff took d of cycle 1 (1)
    {"d": 1, "en": 0},  # ah holds 1; al transparent: r = 1; ff took 0
    {"d": 0, "en": 1},  # ah transparent: q = 0; al holds 1
    {"d": 0, "en": 1},  # ah transparent: q = 0; al holds r = 1; ff took 1
]
EXPECT = [  # (y, z, w) seen in each cycle before the clock edge
    (1, 0, 0),
    (1, 0, 1),
    (1, 1, 0),
    (0, 1, 1),
    (0, 1, 0),
]


class TestLevelLatch(unittest.TestCase):
    def test_enable_is_data_not_clock(self) -> None:
        comp = compile_model(parse_single_model(LEVEL))
        self.assertEqual(comp.clocks, {"clk"})
        self.assertIn("en", comp.data_inputs)
        self.assertEqual(set(comp.level), {"q", "r"})

    def test_hold_and_transparency(self) -> None:
        comp = compile_model(parse_single_model(LEVEL))
        steps = [{**s, "clk": 0} for s in STEPS]
        got = [(v["y"], v["z"], v["w"]) for v in replay(comp, steps)]
        self.assertEqual(got, EXPECT)

    @unittest.skipUnless(odin_available(), "needs Odin III")
    def test_matches_odin_simulator(self) -> None:
        from odin3 import Design

        no_ff = NO_FF
        seen: list[tuple[int, int]] = []
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "lv.blif"
            path.write_text(no_ff, encoding="utf-8")
            with Design() as design:
                design.run_pass("read_blif", str(path))
                with design.simulate() as sim:
                    d, en = sim.signal("d"), sim.signal("en")
                    y, z = sim.signal("y"), sim.signal("z")
                    assert d is not None and en is not None and y is not None and z is not None
                    for step in STEPS:
                        sim.set(d, step["d"])
                        sim.set(en, step["en"])
                        sim.settle()
                        seen.append((sim.get(y), sim.get(z)))
                        sim.step(1)
        self.assertEqual(seen, [(a, b) for a, b, _w in EXPECT])


if __name__ == "__main__":
    unittest.main()
