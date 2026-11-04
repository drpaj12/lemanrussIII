"""Round 9 (rc7): magic-number sequential trigger (spec section 13).

(a) the trigger adds no flip-flop/latch, (b) a reachable value is found by the multi-cycle
window observation, (c) each kept payload adds no state (the FF/latch equality gate holds end
to end through `build_seq_variant`'s magic path).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl import edit_netlist as en
from lemanruss.htl.bitsim import compile_model, latches_of, reset_inputs, simulate_comb
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.edit_netlist import TextNetlist
from lemanruss.htl.payloads import DosStuckPayload
from lemanruss.htl.seeker import Built
from lemanruss.htl.seqtune import (
    _candidates_in_band_magic,
    _cond_sets,
    _state_candidates,
    build_seq_base_rc7,
    observe,
)
from lemanruss.htl.triggers import StatePatternTrigger
from lemanruss.htl.trojan import compose
from tests.helpers import odin_available

# A tiny sequential model: `q` (a register Q output) is the magic-number literal, "q==1 & b==1".
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

# No SCOAP table needed for the pure-text checks below.
NO_SC: dict[str, dict[str, int]] = {}


class StateCandidatesTest(unittest.TestCase):
    def test_state_candidates_include_latch_q_not_just_internal_nets(self) -> None:
        model = parse_single_model(SEQ)
        comp = compile_model(model)
        values = simulate_comb(comp, 1 << 12, 1, reset_inputs(model))
        cands = _state_candidates(model, values, 1 << 12, NO_SC, min_p=0.0)
        names = {c.name for c in cands}
        self.assertIn("q", names)  # the latch Q output, not a .names-block output
        self.assertTrue(names <= {"q", "a", "b", "reset"})


class MagicTriggerNoFlipFlopTest(unittest.TestCase):
    """(a) a trigger that adds no flip-flop."""

    def test_comb_rare_trigger_adds_no_latch(self) -> None:
        text = TextNetlist(parse_single_model(SEQ))
        before = len(latches_of(text.model))
        en.comb_rare_trigger(text, (("q", 1), ("b", 1)))
        en.dos_stuck(text, "z", 1)
        after = len(latches_of(text.model))
        self.assertEqual(before, after)

    @unittest.skipUnless(odin_available(), "Odin III not available")
    def test_edit_api_insert_adds_no_latch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(SEQ, encoding="utf-8")
            out = Path(td) / "o.blif"

            def recipe(ed: en.Editor) -> None:
                en.comb_rare_trigger(ed, (("q", 1), ("b", 1)))
                en.dos_stuck(ed, "z", 1)

            en.insert(base, out, "trojan:t-state-pattern__p-dos-stuck__netlist", recipe)
            clean = parse_single_model(SEQ)
            infected = parse_single_model(out.read_text(encoding="utf-8"))
            self.assertEqual(len(latches_of(clean)), len(latches_of(infected)))

    def test_trojan_id_and_compose_accept_state_pattern(self) -> None:
        trigger = StatePatternTrigger(k=2, nets=(("q", 1), ("b", 1)))
        trojan = compose(trigger, DosStuckPayload(victim="z", stuck_value=1), "netlist", site="z")
        self.assertEqual(trojan.id, "t-state-pattern__p-dos-stuck__netlist")
        self.assertIn("register/input", trojan.description())


class ReachableValueTest(unittest.TestCase):
    """(b) a reachable value: the multi-cycle window finds P(fired within N) > 0 for a magic
    combination built from register Q outputs."""

    def test_state_cond_set_is_reached_within_window(self) -> None:
        model = parse_single_model(SEQ)
        comp = compile_model(model)
        fixed = reset_inputs(model)
        values = simulate_comb(comp, 1 << 12, 1, fixed)
        cands = _state_candidates(model, values, 1 << 12, NO_SC, min_p=0.0)
        self.assertGreater(len(cands), 0)
        cond_sets = _cond_sets(cands, 1 << 12)
        self.assertGreater(len(cond_sets), 0)
        obs = observe(comp, 256, 3, fixed, cond_sets, [])
        tried = _candidates_in_band_magic(obs, 0.0, 1.0)
        self.assertGreater(len(tried), 0)
        # at least one candidate fired at least once in at least one lane
        self.assertTrue(any(h > 0 for _k, _j, h in tried))

    def test_dead_value_never_reached_is_rejected(self) -> None:
        # a cond set that can never be true (q==0 AND q==1 simultaneously) must show hits==0,
        # so it would never clear MIN_HITS / land in any non-trivial band.
        model = parse_single_model(SEQ)
        comp = compile_model(model)
        fixed = reset_inputs(model)
        obs = observe(comp, 64, 1, fixed, [(("q", 1), ("q", 0))], [])
        self.assertEqual(obs.ge[0][0].bit_count(), 0)


class PayloadStateCheckTest(unittest.TestCase):
    """(c) check each payload kind for added state; only p-energy is excluded from rc7."""

    def test_dos_stuck_err_bit_slowdown_add_no_latch(self) -> None:
        def b_dos_stuck(ed: en.Editor) -> None:
            en.dos_stuck(ed, "z", 1)

        def b_err_bit(ed: en.Editor) -> None:
            en.err_bit(ed, "y", False)

        def b_slowdown(ed: en.Editor) -> None:
            en.slowdown(ed, "z", 2)

        def b_slowdown_absorb(ed: en.Editor) -> None:
            en.slowdown_absorb(ed, "z", ["a", "b"])

        for recipe_name, builder in (
            ("dos_stuck", b_dos_stuck),
            ("err_bit", b_err_bit),
            ("slowdown", b_slowdown),
            ("slowdown_absorb", b_slowdown_absorb),
        ):
            text = TextNetlist(parse_single_model(SEQ))
            before = len(latches_of(text.model))
            builder(text)
            after = len(latches_of(text.model))
            self.assertEqual(before, after, recipe_name)

    def test_energy_payload_adds_a_latch_and_is_excluded(self) -> None:
        text = TextNetlist(parse_single_model(SEQ))
        before = len(latches_of(text.model))
        en.energy(text, "clock", 3)
        after = len(latches_of(text.model))
        self.assertGreater(after, before)  # confirms why p-energy is excluded from rc7


class BuildSeqBaseRc7Test(unittest.TestCase):
    """End-to-end smoke: every Built circuit from build_seq_base_rc7 passes the FF/latch
    equality hard gate and carries a `t-state-pattern` trojan id."""

    @unittest.skipUnless(odin_available(), "Odin III not available")
    def test_rc7_build_is_ff_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "tiny.blif"
            base.write_text(SEQ, encoding="utf-8")
            out_dir = Path(td) / "out"
            out_dir.mkdir()
            counter = iter(f"rc7{i:04d}" for i in range(1, 100))
            results = build_seq_base_rc7(base, out_dir, lambda: next(counter), seed=5,
                                         max_blocks=10000)
            self.assertEqual(len(results), 3)  # fast / mid / slow
            built = [r for r in results if isinstance(r, Built)]
            for b in built:
                self.assertTrue(b.trojan.id.startswith("t-state-pattern__"))
                self.assertEqual(b.record.ff_count_clean, b.record.ff_count_infected)


if __name__ == "__main__":
    unittest.main()
