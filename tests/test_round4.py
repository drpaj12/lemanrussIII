"""Round 4: latch init, reset inputs, output isolation, tuned sequential observation, forced-off
trigger, ABC restructuring, Odin III cross-check."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.bitsim import (
    compile_model,
    replay,
    reset_inputs,
    simulate_diff,
    simulate_seq_pair,
)
from lemanruss.htl.blif_text import isolate_output, parse_single_model, render
from lemanruss.htl.insert_netlist import (
    TRIGGER_NET,
    insert_dos_stuck_payload,
    insert_seq_counter_netlist,
)
from lemanruss.htl.payloads import DosStuckPayload
from lemanruss.htl.r4check import crosscheck, force_trigger_off
from lemanruss.htl.restructure import RESTRUCTURINGS, restore_clock, structure_of
from lemanruss.htl.seqtune import WINDOW, observe
from tests.helpers import odin_available

SEQ = """.model top
.inputs a b reset clock
.outputs y z
.latch d q re clock 1
.names a b d
11 1
.names q a y
1- 1
-1 1
.names y b z
10 1
.end
"""


class Round4Test(unittest.TestCase):
    def test_latch_init_one_and_reset_inputs(self) -> None:
        m = parse_single_model(SEQ)
        c = compile_model(m)
        self.assertEqual(c.latch_init, [1])
        self.assertEqual(reset_inputs(m), {"reset": 0})
        run = replay(c, [{"a": 0, "b": 0, "reset": 0}, {"a": 0, "b": 0, "reset": 0}])
        self.assertEqual(run[0]["y"], 1)  # q starts at 1
        self.assertEqual(run[1]["y"], 0)  # d = a&b = 0 was latched

    def test_isolate_output_is_identity_and_quiet(self) -> None:
        m = parse_single_model(SEQ)
        iso = isolate_output(m, "y")  # y is read by z
        a, b = compile_model(m), compile_model(iso)
        curve = simulate_diff(a, b, 64, 8, 1)
        self.assertEqual(curve[-1], 0)
        victim_driver = [ln for ln in iso.body if ln.endswith(" y")]
        self.assertEqual(victim_driver, [".names y__htl_pre y"])
        with self.assertRaises(ValueError):
            isolate_output(m, "a")

    def test_isolated_payload_does_not_change_other_output(self) -> None:
        m = parse_single_model(SEQ)
        iso = isolate_output(m, "y")
        inf = insert_dos_stuck_payload(
            insert_seq_counter_netlist(iso, (("a", 1),), 1, "clock"),
            DosStuckPayload(victim="y", stuck_value=1))
        curve, _ = simulate_seq_pair(compile_model(m), compile_model(inf), 128, 40, 2, TRIGGER_NET)
        self.assertGreater(curve[-1], 100)
        a, b = compile_model(m), compile_model(inf)
        out_z = simulate_diff(
            type(a)(a.data_inputs, ["z"], a.blocks, a.latches, a.clocks, a.latch_init),
            type(b)(b.data_inputs, ["z"], b.blocks, b.latches, b.clocks, b.latch_init),
            128, 40, 2)
        self.assertEqual(out_z[-1], 0)  # z (reads y inside the design) is untouched

    def test_force_trigger_off(self) -> None:
        m = parse_single_model(SEQ)
        inf = insert_dos_stuck_payload(
            insert_seq_counter_netlist(m, (("a", 1),), 1, "clock"),
            DosStuckPayload(victim="z", stuck_value=1))
        off = force_trigger_off(inf)
        curve = simulate_diff(compile_model(m), compile_model(off), 128, 30, 4)
        self.assertEqual(curve[-1], 0)
        self.assertIn(f".names {TRIGGER_NET}", off.body)

    def test_observe_counter_planes_match_direct_sim(self) -> None:
        m = parse_single_model(SEQ)
        comp = compile_model(m)
        obs = observe(comp, 256, 3, {}, [(("a", 1),)], [(("a", 1), ("b", 1))])
        inf = insert_seq_counter_netlist(m, (("a", 1),), 3, "clock")
        curve, _ = simulate_seq_pair(comp, compile_model(inf), 256, WINDOW, 3, TRIGGER_NET)
        self.assertEqual(obs.ge[0][3].bit_count(), curve[-1])
        pat = obs.ever[0][1].bit_count()
        self.assertGreater(pat, 0)

    def test_restructure_set_and_clock_restore(self) -> None:
        self.assertEqual(len(RESTRUCTURINGS), 18)
        src = parse_single_model(SEQ)
        abc_like = ".model top\n.inputs a b reset clock\n.outputs y z\n.latch d q 1\n" \
                   ".names a b d\n11 1\n.names q a y\n1- 1\n.end\n"
        back = restore_clock(abc_like, src)
        self.assertIn(".latch d q re clock 1", back.body)
        self.assertGreater(structure_of(src).depth, 0)
        self.assertIn("re clock", render(back))

    @unittest.skipUnless(odin_available(), "Odin III not available")
    def test_crosscheck_against_odin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.blif"
            path.write_text(SEQ, encoding="utf-8")
            res = crosscheck(path, "s", 32, 1)
        self.assertEqual(res.error, "")
        self.assertEqual(res.mismatches, 0)
        self.assertGreater(res.compares, 100)


if __name__ == "__main__":
    unittest.main()
