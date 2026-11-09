"""Neutral stimulus: no infected toy circuit differs from the golden on the result."""

from __future__ import annotations

import unittest

from lemanruss.htl.stimulus import (
    comb_stimulus,
    compile_text,
    reset_trigger_hit,
    reset_trigger_prob,
    seq_check,
    seq_stimulus,
    to_text,
)
from lemanruss.htl.topup import free_ids

GOLDEN = ".model top\n.inputs a b c d e f g h i j k l m n\n.outputs y\n.names a b y\n11 1\n.end\n"
# fires when all fourteen inputs are 1 (a rare vector); the output then differs
TROJAN = (".model top\n.inputs a b c d e f g h i j k l m n\n.outputs y\n"
          ".names a b y0\n11 1\n.names a b c d e f g h i j k l m n t\n" + "1" * 14 + " 1\n"
          ".names y0 t y\n10 1\n01 1\n.end\n")
SEQ_G = (".model top\n.inputs x r\n.outputs y\n.latch d q 2\n.names x q d\n10 1\n01 1\n"
         ".names q y\n1 1\n.end\n")
# the infected twin flips y when x and r are both 1 and q is 1
SEQ_T = (".model top\n.inputs x r\n.outputs y\n.latch d q 2\n.names x q d\n10 1\n01 1\n"
         ".names q x r z\n111 1\n.names q z y\n10 1\n01 1\n.end\n")


class CombStimulus(unittest.TestCase):
    def test_firing_vector_removed(self) -> None:
        g, t = compile_text(GOLDEN), compile_text(TROJAN)
        names, rows, stats = comb_stimulus(g, [t], 64, 4096, 7)
        self.assertEqual(stats["circuits_differing_on_final"], 0)
        self.assertEqual(len(rows), 64)
        self.assertNotIn("1" * 14, rows)
        self.assertEqual(len(names), 14)
        self.assertTrue(to_text(names, rows).startswith("a b c"))

    def test_exhaustive_small(self) -> None:
        small = ".model top\n.inputs a b\n.outputs y\n.names a b y\n11 1\n.end\n"
        bad = ".model top\n.inputs a b\n.outputs y\n.names a b y\n1- 1\n.end\n"
        _n, rows, stats = comb_stimulus(compile_text(small), [compile_text(bad)], 10, 16, 1)
        self.assertTrue(stats["exhaustive"])
        self.assertEqual(sorted(rows), ["00", "01", "11"])
        self.assertEqual(stats["circuits_differing_on_final"], 0)


class SeqStimulus(unittest.TestCase):
    def test_sequence_avoids_firing(self) -> None:
        g, t = compile_text(SEQ_G), compile_text(SEQ_T)
        names, rows, stats = seq_stimulus(g, [t], 40, 16, 3)
        self.assertEqual(len(rows), 40)
        self.assertEqual(stats["circuits_differing_on_final"], 0)
        self.assertEqual(seq_check(g, [t], names, rows), 0)
        # the unfiltered check does detect a differing circuit
        self.assertEqual(seq_check(g, [t], names, ["11"] * 6), 1)


class ResetGate(unittest.TestCase):
    def test_threshold_both_sides(self) -> None:
        # FF-only trigger matching the reset state (q = 0): probability 1, rejected
        ff = (".model top\n.inputs x\n.outputs y\n.latch x q 2\n.names q t\n0 1\n"
              ".names x y\n1 1\n.end\n")
        self.assertTrue(reset_trigger_hit(compile_text(ff), ["t"], 1 << 12))
        # reset-matching FF literal plus 3 input literals: p = 1/8, rejected
        k3 = (".model top\n.inputs a b c\n.outputs y\n.latch a q 2\n"
              ".names q a b c t\n0111 1\n.names a y\n1 1\n.end\n")
        self.assertTrue(reset_trigger_hit(compile_text(k3), ["t"], 1 << 14))
        # reset-matching FF literal plus 10 input literals: p = 2^-10 < 1e-2, passes
        names = " ".join(f"i{k}" for k in range(10))
        k10 = (f".model top\n.inputs {names}\n.outputs y\n.latch i0 q 2\n"
               f".names q {names} t\n0" + "1" * 10 + " 1\n.names i0 y\n1 1\n.end\n")
        comp = compile_text(k10)
        self.assertFalse(reset_trigger_hit(comp, ["t"], 1 << 16))
        self.assertLess(reset_trigger_prob(comp, ["t"], 1 << 16), 1e-2)
        # a trigger that needs q = 1 is low in the reset state
        hi = (".model top\n.inputs x\n.outputs y\n.latch x q 2\n.names q x u\n11 1\n"
              ".names x y\n1 1\n.end\n")
        self.assertFalse(reset_trigger_hit(compile_text(hi), ["u"], 1 << 12))


class FreeIds(unittest.TestCase):
    def test_free_ids_stay_in_block(self) -> None:
        used = ["sc0302", "sc0303", "sc0600"]
        free = free_ids(used, 301, 5, "b")
        self.assertEqual(len(free), 301 - 3)
        self.assertTrue(all(302 <= n <= 602 for n in free))
        self.assertNotIn(303, free)
        with self.assertRaises(ValueError):
            free_ids(["sc0001", "sc0400"], 301, 5, "b")


if __name__ == "__main__":
    unittest.main()
