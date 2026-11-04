"""Tests for lemanruss.htl.build: the first benchmark build, on this repo's tiny fixtures."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.build import BuildFailure, build_benchmark
from tests.helpers import odin_available

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@unittest.skipUnless(odin_available(), "Odin III not available (set ODIN3_LIB/PYTHONPATH)")
class TestBuildBenchmark(unittest.TestCase):
    def test_builds_two_and(self) -> None:
        # two_and.v has two AND terms, each rare at 1 (P=0.25 under uniform random a, b, c, d).
        # Round 1 needed them marked (* keep *) for Odin III's Simulation API to list them;
        # round 2's blif_sim evaluator needs no such marking (kept here only as a fixture that
        # also still exercises the (* keep *) path in tests/test_sites.py).
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            entries, failures = build_benchmark([FIXTURES / "two_and.v"], out_dir)
            self.assertEqual(failures, [], f"unexpected failures: {failures}")
            self.assertEqual(len(entries), 1)
            self.assertTrue(entries[0].verification["fires"])
            self.assertTrue(entries[0].verification["equivalent_clean_part"])

            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], 1)
            self.assertEqual(len(manifest["entries"]), 1)
            labels = json.loads((out_dir / "labels.json").read_text(encoding="utf-8"))
            self.assertEqual(len(labels), 1)

    def test_buffer_has_no_rare_net(self) -> None:
        # buffer.v has only a pass-through bit (P(y=1)=0.5, no internal cell at all, and no
        # (* keep *) wire to expose even if it did); the build should record this as a failure,
        # not raise.
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            entries, failures = build_benchmark([FIXTURES / "buffer.v"], out_dir)
            self.assertEqual(entries, [])
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], BuildFailure)
            self.assertIn("rare", failures[0].reason)

    def test_rare_and_has_too_few_rare_nets(self) -> None:
        # rare_and.v has exactly one gate, so its output y is the only non-input signal: not
        # enough for a k=2 trigger. A real, documented limitation of a 1-gate design, not a bug.
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            entries, failures = build_benchmark([FIXTURES / "rare_and.v"], out_dir)
            self.assertEqual(entries, [])
            self.assertEqual(len(failures), 1)
            self.assertIn("rare", failures[0].reason)

    def test_ripple_adder4_equivalence_excludes_every_firing_combination(self) -> None:
        # A carry net can be realised by more than one input combination; the equivalence check
        # must exclude every one the trigger fires on, not just the single witness
        # find_driving_inputs returns (round 2's first attempt wrongly said "not equivalent"
        # here against the real adder_4bit.v).
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            entries, failures = build_benchmark([FIXTURES / "ripple_adder4.v"], out_dir)
            self.assertEqual(failures, [], f"unexpected failures: {failures}")
            self.assertEqual(len(entries), 1)
            self.assertTrue(entries[0].verification["fires"])
            self.assertTrue(entries[0].verification["equivalent_clean_part"])
            self.assertEqual(
                entries[0].verification["equivalence_method"], "exhaustive-input-comparison"
            )
            self.assertIn("stealth_mismatches", entries[0].verification)
            self.assertIn("activation_probability", entries[0].verification)

            mix = json.loads((out_dir / "mix.json").read_text(encoding="utf-8"))
            self.assertEqual(mix["schema"], 1)
            self.assertIn(entries[0].base_design, mix["draw"])
            self.assertIn(mix["draw"][entries[0].base_design], ("clean", "infected"))

    def test_norgate_like_excludes_output_from_trigger_candidates(self) -> None:
        # Two gates, so exactly one internal net plus the output -- without excluding the
        # output, this used to pick the output as a trigger input and crash Simulation.open on
        # the resulting combinational loop (found against the real Prob011_norgate_ref.sv); it
        # must now fail cleanly with "fewer than 2 rare nets", never raise.
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            entries, failures = build_benchmark([FIXTURES / "norgate_like.v"], out_dir)
            self.assertEqual(entries, [])
            self.assertEqual(len(failures), 1)
            self.assertIn("rare", failures[0].reason)


if __name__ == "__main__":
    unittest.main()


def _rand_seq_blif(name: str, seed: int, n_latch: int = 24, n_gate: int = 90) -> str:
    """A small random sequential design (fixed seed): inputs a0-a5 and reset, `n_latch` flip-flops
    fed by random 2-3 input gates, three outputs."""
    import random

    rng = random.Random(seed)
    srcs = [f"a{i}" for i in range(6)] + [f"q{i}" for i in range(n_latch)]
    lines = [f".model {name}", ".inputs clock reset " + " ".join(f"a{i}" for i in range(6)),
             ".outputs o0 o1 o2"]
    gates: list[str] = []
    for g in range(n_gate):
        k = rng.choice((2, 3))
        ins = rng.sample(srcs, k)
        row = "".join(rng.choice("01") for _ in range(k))
        gates += [f".names {' '.join(ins)} g{g}", f"{row} 1"]
        srcs.append(f"g{g}")
    lines += gates
    for i in range(n_latch):
        d = f"g{n_gate - 1 - i}"
        lines += [f".names {d} reset d{i}", "10 1", f".latch d{i} q{i} re clock 0"]
    for k in range(3):
        lines += [f".names g{n_gate - 30 - k} g{n_gate - 40 - k} o{k}", "11 1"]
    lines.append(".end")
    return "\n".join(lines) + "\n"


class TestLowering(unittest.TestCase):
    def test_lowering_script_forms(self) -> None:
        from lemanruss.htl.build import lowering_script

        f = Path("x.v")
        self.assertEqual(lowering_script(f, None), 'read_verilog "x.v"; proc; opt; lower')
        self.assertIn("flatten; opt; lower", lowering_script(f, None, True))
        arch = lowering_script(f, Path("a.xml"), True)
        self.assertTrue(arch.startswith('read_arch "a.xml"; read_verilog --vtr-compat "x.v"'))
        self.assertTrue(arch.endswith("flatten; opt; unmap; lower"))

    def test_keep_first_model(self) -> None:
        from lemanruss.htl.bases import keep_first_model

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.blif"
            p.write_text(".model top\n.inputs a\n.outputs a\n.end\n.model dead\n.end\n",
                         encoding="utf-8")
            self.assertEqual(keep_first_model(p), "")
            self.assertEqual(p.read_text(encoding="utf-8"),
                             ".model top\n.inputs a\n.outputs a\n.end\n")
            p.write_text(".model top\n.subckt m a=a\n.end\n", encoding="utf-8")
            self.assertIn("sub-circuits", keep_first_model(p))


@unittest.skipUnless(odin_available(), "odin3 not available")
class TestRunFamilyWorkers(unittest.TestCase):
    def test_pool_equals_serial(self) -> None:
        from lemanruss.htl.seeker import run_family

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bases = []
            for i in range(3):
                p = root / f"rs{i}.blif"
                p.write_text(_rand_seq_blif(f"rs{i}", i + 1), encoding="utf-8")
                bases.append(p)
            ser, ser_fail = run_family("Seeker-Seq", bases, root / "s", 0, 30000, 1)
            par, par_fail = run_family("Seeker-Seq", bases, root / "p", 0, 30000, 2)
            self.assertEqual([b.circuit_id for b in ser], [b.circuit_id for b in par])
            self.assertEqual([(f.base, f.variant, f.reason) for f in ser_fail],
                             [(f.base, f.variant, f.reason) for f in par_fail])
            self.assertEqual(len(ser) + len(ser_fail), 3 * 6)
            for b in ser:
                other = root / "p" / "circuits" / b.infected_path.name
                self.assertEqual(b.infected_path.read_bytes(), other.read_bytes())
            clean = sorted(p.name for p in (root / "s" / "circuits").glob("ss00[0-9][0-9].blif"))
            self.assertIn("ss0008.blif", clean)  # base 2's clean copy: 1 + 6 ids per base

    def test_failing_base_becomes_failures_and_is_cached(self) -> None:
        from lemanruss.htl.seeker import run_family

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bad = root / "bad.blif"
            bad.write_text(".model bad\n.inputs a\n.outputs y\n.names q y\n1 1\n.end\n",
                           encoding="utf-8")  # y reads an undriven net
            good = root / "rs.blif"
            good.write_text(_rand_seq_blif("rs", 2), encoding="utf-8")
            built, fails = run_family("Seeker-Seq", [bad, good], root / "o", 0, 30000, 2)
            self.assertEqual(len([f for f in fails if f.base == "bad"]), 6)
            self.assertGreaterEqual(len(built), 1)
            self.assertTrue((root / "o" / "answer_key" / "jobs" / "bad.pkl").exists())
            again, again_fails = run_family("Seeker-Seq", [bad, good], root / "o", 0, 30000, 1)
            self.assertEqual([b.circuit_id for b in built], [b.circuit_id for b in again])
            self.assertEqual(len(fails), len(again_fails))
