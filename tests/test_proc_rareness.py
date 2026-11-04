"""Tests for lemanruss.htl.proc_rareness: trigger-net lookup and magic-word probability."""

from __future__ import annotations

import unittest

from lemanruss.htl.proc_rareness import find_trigger_net, magic_match_probability

# Real fragments copied from Odin III `write_blif` output of the two patched cores (round 7
# prototyping): mcu's ungated single magic word (NOT(OR(XOR bits)), no AND) and darkriscv's
# IDACK-gated magic word (one more AND on top).
MCU_FRAGMENT = """\
.model single_cycle_core$RESET_PC=0
.subckt $_OR_ A=$n872 B=$n873 Y=$n873b
.cname __htl_trigger.or61
.subckt $_NOT_ A=$n873b Y=$n874
.cname __htl_trigger.not63
.subckt $_MUX_ A=next_PC_select[0] B=vcc S=$n874 Y=$n875
.cname __htl_pc_mux.mux0
.end
"""

DARK_FRAGMENT = """\
.model darkriscv
.subckt $_NOT_ A=$n16065 Y=$n16066
.cname $c266.not63
.subckt $_AND_ A=IDACK B=$n16066 Y=$n16067
.cname __htl_trigger.and0
.subckt $_OR_ A=RES B=$n16067 Y=$n16068
.cname $c268.or0
.end
"""


class TestFindTriggerNet(unittest.TestCase):
    def test_mcu_ungated(self) -> None:
        self.assertEqual(
            find_trigger_net(MCU_FRAGMENT), ("single_cycle_core$RESET_PC=0", "$n874")
        )

    def test_dark_gated(self) -> None:
        self.assertEqual(find_trigger_net(DARK_FRAGMENT), ("darkriscv", "$n16067"))

    def test_no_trigger_raises(self) -> None:
        with self.assertRaises(ValueError):
            find_trigger_net(".subckt $_AND_ A=a B=b Y=c\n.cname foo.and0\n")


class TestMagicMatchProbability(unittest.TestCase):
    def test_single_word(self) -> None:
        self.assertEqual(magic_match_probability(1), 2.0**-32)

    def test_sequence(self) -> None:
        self.assertEqual(magic_match_probability(3), 2.0**-96)


if __name__ == "__main__":
    unittest.main()
