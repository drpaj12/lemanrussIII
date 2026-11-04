"""Round 5: recipes through the Odin III edit API agree with the text editor; provenance tags."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl import edit_netlist as en
from lemanruss.htl.bitsim import compile_model, simulate_diff
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.edit_netlist import Editor, TextNetlist
from tests.helpers import odin_available

SEQ = """.model top
.inputs a b c reset clock
.outputs y z
.latch d q re clock 1
.names a b d
11 1
.names q a y
1- 1
-1 1
.names y b c z
1-1 1
.end
"""


def _recipes() -> dict[str, en.RecipeFn]:
    nets = (("d", 1), ("b", 1))

    def r1(ed: Editor) -> None:
        en.comb_rare_trigger(ed, nets)
        en.dos_stuck(ed, "z", 1)

    def r2(ed: Editor) -> None:
        en.seq_counter(ed, nets, 2, "clock")
        en.err_bit(ed, "y", False)

    def r3(ed: Editor) -> None:
        en.seq_pattern(ed, nets, "clock")
        en.dos_stuck(ed, "z", 0)

    def r4(ed: Editor) -> None:
        en.input_pattern_trigger(ed, ("a", "b", "c"), 5)
        en.energy(ed, "clock", 3)
        en.slowdown(ed, "z", 2)
        en.err_bit(ed, "y", True)

    def r5(ed: Editor) -> None:
        en.always_on_trigger(ed)
        ed.isolate("y")
        en.dos_stuck(ed, "y", 1)

    return {"comb": r1, "ctr": r2, "pat": r3, "misc": r4, "iso": r5}


@unittest.skipUnless(odin_available(), "odin3 not available")
class EditNetlistTest(unittest.TestCase):
    def test_edit_equals_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(SEQ, encoding="utf-8")
            for name, recipe in _recipes().items():
                out = Path(td) / f"{name}.blif"
                rep = en.insert(base, out, f"trojan:{name}", recipe, allow_fallback=False)
                self.assertEqual(rep.method, "odin3-edit", name)
                text = TextNetlist(parse_single_model(SEQ))
                recipe(text)
                a = compile_model(parse_single_model(out.read_text(encoding="utf-8")))
                b = compile_model(text.model)
                curve = simulate_diff(a, b, 512, 24, 3, {"reset": 0})
                self.assertEqual(curve[-1], 0, name)

    def test_inserted_latches_carry_the_circuit_convention(self) -> None:
        text = SEQ.replace("re clock 1", "re clock 2")
        conv = en.convention_of(text)
        self.assertEqual((conv.edge, conv.init), ("re", 2))
        self.assertEqual(en.convention_of(text.replace("clock 2", "clock 3")).init, 2)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(text, encoding="utf-8")
            out = Path(td) / "o.blif"
            en.insert(base, out, "trojan:t9", _recipes()["ctr"], allow_fallback=False, conv=conv)
            lat = [ln.split() for ln in out.read_text(encoding="utf-8").splitlines()
                   if ln.startswith(".latch")]
            self.assertGreater(len(lat), 2)
            self.assertEqual({w[3] + " " + w[5] for w in lat}, {"re 2"})

    def test_pattern_first_stage_is_a_two_input_cell_and_same_signal(self) -> None:
        for cond in ((("d", 1), ("b", 1), ("a", 0)), (("d", 0), ("b", 1)), (("a", 0),)):

            def legacy(ed: Editor, cond: tuple[tuple[str, int], ...] = cond) -> None:
                # rc4 stages: the value is applied before the first latch; trigger is the flag
                prev = None
                for i, (net, val) in enumerate(cond):
                    d, q = f"s_d{i}", f"s_q{i}"
                    if prev is None:
                        ed.names([net], d, [f"{val} 1"])
                    else:
                        ed.names([prev, net], d, [f"1{val} 1"])
                    ed.latch(d, q, "clock")
                    prev = q
                ed.names(["s_f", str(prev)], "s_fd", ["1- 1", "-1 1"])
                ed.latch("s_fd", "s_f", "clock")
                ed.names(["s_f"], "__htl_trigger", ["1 1"])
                en.dos_stuck(ed, "z", 0)

            def new(ed: Editor, cond: tuple[tuple[str, int], ...] = cond) -> None:
                en.seq_pattern(ed, cond, "clock", p="s")
                en.dos_stuck(ed, "z", 0)

            a = TextNetlist(parse_single_model(SEQ))
            b = TextNetlist(parse_single_model(SEQ))
            legacy(a)
            new(b)
            lat = {w[1] for w in (ln.split() for ln in b.model.body if ln.startswith(".latch"))}
            self.assertIn("s_d0", lat)
            curve = simulate_diff(compile_model(a.model), compile_model(b.model), 512, 24, 3,
                                  {"reset": 0})
            self.assertEqual(curve[-1], 0, cond)

    def test_provenance_separates_inserted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(SEQ, encoding="utf-8")
            rep = en.insert(base, Path(td) / "o.blif", "trojan:t9", _recipes()["ctr"])
            self.assertEqual(rep.untagged_nodes + rep.modified_nodes, rep.base_nodes)
            self.assertEqual(rep.tagged_nodes, rep.nodes - rep.base_nodes)
            self.assertGreater(rep.tagged_nodes, 5)
            self.assertTrue(rep.tagged_all_htl)

    def test_events_only_in_internal_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(SEQ, encoding="utf-8")
            out = Path(td) / "circuits" / "o.blif"
            out.parent.mkdir()
            rep = en.insert(base, out, "trojan:t9", _recipes()["comb"],
                            events_dir=en.events_dir_of(out))
            self.assertNotIn("odin3_edit", out.read_text(encoding="utf-8"))
            ev = Path(td) / "answer_key" / "edit_events" / "o.edit.blif"
            self.assertEqual(rep.edit_blif, "o.edit.blif")
            self.assertIn("odin3_edit added:trojan:t9", ev.read_text(encoding="utf-8"))
            self.assertGreaterEqual(rep.modified_nodes, 1)

    def test_both_editors_fail_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "b.blif"
            base.write_text(SEQ, encoding="utf-8")

            def bad(ed: Editor) -> None:
                ed.splice("nonexistent")

            with self.assertRaises(ValueError):
                en.insert(base, Path(td) / "o.blif", "t", bad)
