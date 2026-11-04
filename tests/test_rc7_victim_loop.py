"""rc7 regression: a magic-trigger bit must never be the payload's victim net (that reads the
payload's own output: `bitsim: combinational loop`), and a set that raises must not leave a
half-built set in a base result (`n200run.assemble` KeyError 'K6')."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.n200plan import make_ctx_rc7
from lemanruss.htl.n200run import assemble

# Output `u` is itself a register Q (as b02): a trigger on `u` with victim `u` loops.
REG_OUT = """.model top
.inputs a b reset clock
.outputs u
.latch d1 u re clock 3
.latch d2 r1 re clock 3
.latch d3 r2 re clock 3
.names a r1 d1
10 1
01 1
.names b r2 d2
10 1
01 1
.names u r1 d3
10 1
01 1
.end
"""


class VictimNotInTriggerTest(unittest.TestCase):
    def test_victim_never_in_trigger_nets(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(REG_OUT, encoding="utf-8")
            ctx = make_ctx_rc7(base, 0)
            assert not isinstance(ctx, str)
            drawn = 0
            for payload in ("p-err-hi", "p-err-lo", "p-dos-stuck", "p-dos-reset"):
                for _ in range(40):
                    spec = ctx.draw(payload, set(), set())
                    if spec is None or spec.trig == "none":
                        continue
                    drawn += 1
                    self.assertNotIn(spec.victim, {n for n, _v in spec.nets})
            self.assertGreater(drawn, 0)


class AssembleTest(unittest.TestCase):
    def test_assemble_set_without_entry_is_a_failure_not_a_crash_after_fix(self) -> None:
        # a base result as `build_base_rc7` now returns it when K6 raised: no K6 circuits, no K6 set
        r: dict[str, object] = {
             "base": "x", "golden": "g1",
             "failures": [{"base": "x", "set": "K6", "reason": "e"}],
             "sets": {"K4": {"map": "k4", "n_infected_drawn": 0, "infected": 0, "clean": 1}},
             "circuits": [{"id": "c1", "set": "K4", "map": "k4", "script": "s"}]}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / "answer_key").mkdir()
            assemble("Seeker-Seq", out, [r], [], 0)
            self.assertTrue((out / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
