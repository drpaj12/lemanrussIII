"""Register-matched equivalence (rc2 gate engine): a finalize-renamed, reordered netlist is
proved equal through the order and rename hints; a changed function is not."""

from __future__ import annotations

import os
import random
import unittest
from pathlib import Path

from lemanruss.htl.obfuscate import finalize
from lemanruss.htl.proc_gate import equivalence_check
from lemanruss.htl.regmatch import NotApplicable, chain_equivalent, parse_flat

SOURCE = """.model top
.inputs a b clk
.outputs y q0
.names a b n1
11 1
.names n1 s1 n2
10 1
01 1
.latch n1 s0 re clk 3
.latch n2 s1 re clk 3
.names s0 s1 y
1- 1
-1 1
.names s0 q0
1 1
.end
"""
ROOT = os.environ.get("ODIN3_ROOT")


def traced(text: str, seed: int) -> tuple[str, dict[str, str], str]:
    ren: dict[str, str] = {}
    return finalize(text, random.Random(seed), ren), ren, text


@unittest.skipUnless(ROOT and Path(ROOT, "tools/equiv-check/equiv-check").is_file(),
                     "needs ODIN3_ROOT with tools/equiv-check")
class RegMatchTest(unittest.TestCase):
    def test_chain_proves_renamed_and_shuffled(self) -> None:
        form, ren, mapped = traced(SOURCE, 3)
        self.assertNotEqual([ln for ln in form.splitlines() if ln.startswith(".latch")],
                            [ln for ln in SOURCE.splitlines() if ln.startswith(".latch")])
        chain_equivalent(form, mapped, ren, SOURCE)
        self.assertEqual(equivalence_check(form, SOURCE, 60, (mapped, ren)), (None, "regmatch-cec"))

    def test_changed_function_is_not_proved(self) -> None:
        form, ren, mapped = traced(SOURCE, 3)
        broken = form.replace("11 1", "10 1", 1)
        with self.assertRaises(NotApplicable):
            chain_equivalent(broken, mapped, ren, SOURCE)

    def test_falls_back_to_dsec_and_still_catches_a_difference(self) -> None:
        form, ren, mapped = traced(SOURCE, 3)
        broken = form.replace("11 1", "10 1", 1)
        problem, engine = equivalence_check(broken, SOURCE, 60, (mapped, ren))
        self.assertEqual(engine, "dsec")
        assert problem is not None
        self.assertIn("NOT equivalent", problem)

    def test_flat_parser_rejects_subcircuits(self) -> None:
        with self.assertRaises(NotApplicable):
            parse_flat(".model m\n.subckt x a=b\n.end\n")


if __name__ == "__main__":
    unittest.main()
