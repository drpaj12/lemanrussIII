"""Round 3: continuation fix, bit-parallel sim, sequential netlist triggers, rareness stats,
family manifests (pure Python; no Odin III needed)."""

from __future__ import annotations

import unittest

from lemanruss.htl.bitsim import (
    compile_model,
    exhaustive_lanes,
    simulate_comb,
    simulate_given,
    simulate_seq_pair,
)
from lemanruss.htl.blif_sim import evaluate_cycle
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.families import family_manifest
from lemanruss.htl.insert_netlist import (
    TRIGGER_NET,
    insert_seq_counter_netlist,
    insert_seq_pattern_netlist,
)
from lemanruss.htl.rareness import band_of, wilson

SEQ_BLIF = """.model top
.inputs a b clock
.outputs y
.latch d q re clock 2
.names a b d
11 1
.names q a y
1- 1
-1 1
.end
"""

CONT_BLIF = """.model top
.inputs a \\
b c
.outputs y
.names a b c y
111 1
.end
"""


class Round3Test(unittest.TestCase):
    def test_continuation_joined(self) -> None:
        m = parse_single_model(CONT_BLIF)
        self.assertEqual(m.inputs, ["a", "b", "c"])

    def test_bitsim_matches_scalar(self) -> None:
        m = parse_single_model(CONT_BLIF)
        comp = compile_model(m)
        given, nvec = exhaustive_lanes(comp.data_inputs)
        vals = simulate_given(comp, given, nvec)
        for lane in range(nvec):
            draw = {n: (given[n] >> lane) & 1 for n in comp.data_inputs}
            self.assertEqual((vals["y"] >> lane) & 1, evaluate_cycle(m, draw)["y"])

    def test_comb_random_runs(self) -> None:
        comp = compile_model(parse_single_model(CONT_BLIF))
        vals = simulate_comb(comp, 1 << 12, 1)
        self.assertIn("y", vals)

    def test_counter_fires_after_n_events(self) -> None:
        clean = parse_single_model(SEQ_BLIF)
        inf = insert_seq_counter_netlist(clean, (("a", 1),), bits=2, clock="clock")
        curve, _ = simulate_seq_pair(
            compile_model(clean), compile_model(inf), 256, 40, 3, TRIGGER_NET
        )
        self.assertEqual(curve[2], 0)  # fewer than 4 events cannot have happened by cycle 3
        self.assertGreater(curve[-1], 200)  # p(a)=0.5: 4 events well inside 40 cycles

    def test_pattern_needs_sequence(self) -> None:
        clean = parse_single_model(SEQ_BLIF)
        inf = insert_seq_pattern_netlist(clean, (("a", 1), ("b", 1), ("a", 1)), "clock")
        curve, _ = simulate_seq_pair(
            compile_model(clean), compile_model(inf), 256, 30, 5, TRIGGER_NET
        )
        self.assertEqual(curve[0], 0)
        self.assertGreater(curve[-1], 0)

    def test_wilson_and_band(self) -> None:
        lo, hi = wilson(0, 1000)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        self.assertEqual(band_of(5e-5), "p<1e-4")
        self.assertEqual(band_of(5e-3), "p<1e-2")
        self.assertEqual(band_of(0.5), "p>=1e-2")
        self.assertEqual(band_of(0.0), "never")

    def test_manifest_has_no_labels(self) -> None:
        man = family_manifest("Seeker-Comb", ["b"], [], [{"id": "sc0001", "base": "b"}], 0)
        self.assertEqual(man["version"], "2.0")
        self.assertNotIn("sc0001\": null", str(man))
        self.assertIn("answer_key", str(man["labels"]))


if __name__ == "__main__":
    unittest.main()
