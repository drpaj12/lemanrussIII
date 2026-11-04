"""Cut-and-stitch (round 9, spec section 13). Pure helpers always; the end-to-end cut/map/stitch
needs Odin III and tools/equiv-check (ABC)."""

from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl import cutstitch as cs
from lemanruss.htl import edit_netlist as en
from lemanruss.htl import obfuscate as ob
from lemanruss.htl.blif_text import parse_single_model
from tests.helpers import odin_available


def _seq_base() -> str:
    """A tiny sequential circuit (one latch, a handful of gates) for cut-and-stitch smoke runs."""
    return (
        ".model gen\n.inputs i0 i1 i2 i3 clk\n.outputs y0 y1\n"
        ".names i0 i1 g0\n11 1\n"
        ".names i2 i3 g1\n10 1\n01 1\n"
        ".names g0 g1 g2\n11 1\n"
        ".names g0 g1 ql_d\n11 1\n"
        ".latch ql_d ql_q re clk 2\n"
        ".names g2 ql_q y0\n11 1\n"
        ".names g0 y0 y1\n11 1\n"
        ".end\n"
    )


def equiv_tool_available() -> bool:
    try:
        from lemanruss.htl.n200check import run_cec

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.blif"
            p.write_text(_seq_base(), encoding="utf-8")
            return run_cec(p, p)[0] == "equivalent"
    except Exception:
        return False


class TestPureHelpers(unittest.TestCase):
    def test_io_names_and_latch(self) -> None:
        self.assertEqual(cs._io([".names a b c", "11 1"]), (["a", "b"], "c"))
        self.assertEqual(cs._io([".latch d q re clk 0"]), (["d"], "q"))

    def test_energy_cut_boundary(self) -> None:
        inputs, outputs, blocks = ob.parse(
            ".model m\n.inputs t\n.outputs z\n"
            ".names t __htl_energy0_q0 __htl_energy0_d0\n10 1\n01 1\n"
            ".latch __htl_energy0_d0 __htl_energy0_q0 re clk 2\n"
            ".names __htl_energy0_q0 z\n1 1\n.end\n")
        del inputs
        cut = cs.energy_cut(blocks, 0, 1)
        self.assertEqual(cut.boundary_in, ["__htl_trigger_0"])
        self.assertEqual(cut.boundary_out, [])
        self.assertEqual(cut.extra_out, ["__htl_energy0_q0"])
        self.assertEqual(len(cut.idx), 2)
        del outputs

    def test_slowdown_cut_boundary(self) -> None:
        _inputs, _outputs, blocks = ob.parse(
            ".model m\n.inputs a s\n.outputs z\n"
            ".names a __htl_tmp_v\n1 1\n"
            ".names __htl_tmp_v s __htl_slow_u0_v\n11 1\n"
            ".names __htl_tmp_v __htl_slow_u0_v v\n1- 1\n-1 1\n"
            ".names v z\n1 1\n.end\n")
        cut = cs.slowdown_cut(blocks, "v")
        self.assertEqual(cut.boundary_in, ["__htl_tmp_v", "__htl_slow_u0_v"])
        self.assertEqual(cut.boundary_out, ["v"])
        self.assertEqual(len(cut.idx), 1)  # only the OR; the AND terms stay in the host

    def test_dummy_cut_boundary_out_is_nonempty(self) -> None:
        inputs, outputs, blocks = ob.parse(_seq_base())
        cut = cs.dummy_cut(inputs, outputs, blocks, random.Random(1), 3)
        assert cut is not None
        self.assertTrue(cut.boundary_out)
        self.assertGreaterEqual(len(cut.idx), 1)  # the latch closure may exceed the drawn size

    def test_dummy_cut_none_without_a_driven_output(self) -> None:
        _inputs, outputs, blocks = ob.parse(".model m\n.inputs a\n.outputs a\n.end\n")
        self.assertIsNone(cs.dummy_cut([], outputs, blocks, random.Random(1), 2))


@unittest.skipUnless(odin_available() and equiv_tool_available(),
                     "needs Odin III and tools/equiv-check (ABC)")
class TestCutAndStitch(unittest.TestCase):
    def test_energy_and_slowdown_survive_mapping(self) -> None:
        from lemanruss.htl.n200check import run_cec

        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            base = work / "base.blif"
            base.write_text(_seq_base(), encoding="utf-8")
            pre = work / "pre.blif"

            def recipe(ed: en.Editor) -> None:
                en.always_on_trigger(ed, "__htl_trigger_0")
                en.energy(ed, "clk", 3, "__htl_trigger_0", "__htl_energy0")
                en.slowdown_absorb(ed, "y0", ["i0", "i1"])

            rep = en.insert(base, pre, "trojan:test", recipe, allow_fallback=False)
            self.assertEqual(rep.method, "odin3-edit")

            _inputs, _outputs, blocks = ob.parse(pre.read_text(encoding="utf-8"))
            energy = cs.energy_cut(blocks, 0, 3)
            slow = cs.slowdown_cut(blocks, "y0")
            self.assertTrue(energy.idx and slow.idx)
            cuts = [cs.CutSpec(energy, True, "energy0"), cs.CutSpec(slow, True, "slow0")]
            got = cs.cut_and_stitch(pre, "k4", random.Random(7), work, "test", cuts)
            self.assertIsInstance(got, tuple, got if isinstance(got, str) else "")
            assert isinstance(got, tuple)
            text, _script = got
            final = work / "final.blif"
            final.write_text(text, encoding="utf-8")

            self.assertEqual(run_cec(pre, final)[0], "equivalent")
            self.assertTrue(text.startswith(".model top\n"))
            self.assertNotIn("__htl", text)
            final_model = parse_single_model(text)
            pre_model = parse_single_model(pre.read_text(encoding="utf-8"))
            n_latch_final = sum(1 for ln in final_model.body if ln.startswith(".latch"))
            n_latch_pre = sum(1 for ln in pre_model.body if ln.startswith(".latch"))
            self.assertEqual(n_latch_final, n_latch_pre)  # the ring's latches survived mapping

    def test_dummy_cut_on_a_clean_circuit_is_equivalent(self) -> None:
        from lemanruss.htl.n200check import run_cec

        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            base = work / "base.blif"
            base.write_text(_seq_base(), encoding="utf-8")
            inputs, outputs, blocks = ob.parse(_seq_base())
            for seed in range(6):  # gates mode names internal nets n1, n2 ... in both pieces
                rng = random.Random(seed)
                dummy = cs.dummy_cut(inputs, outputs, blocks, rng, 1 + seed % 3)
                assert dummy is not None
                got = cs.cut_and_stitch(base, "gates", rng, work, f"clean{seed}",
                                        [cs.CutSpec(dummy, True, "dummy")])
                self.assertIsInstance(got, tuple, got if isinstance(got, str) else "")
                assert isinstance(got, tuple)
                final = work / f"final{seed}.blif"
                final.write_text(got[0], encoding="utf-8")
                self.assertEqual(run_cec(base, final)[0], "equivalent", seed)


if __name__ == "__main__":
    unittest.main()
