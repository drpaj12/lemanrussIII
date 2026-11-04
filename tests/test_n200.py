"""Round 8: Seeker at n = 200 per base. Pure helpers always; the end-to-end build on a generated
12-input base needs Odin III and ABC (tools/equiv-check)."""

from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.bitsim import compile_model
from lemanruss.htl.blif_text import parse_single_model
from lemanruss.htl.n200check import (
    decode_steps,
    encode_steps,
    force_off,
    trig_name,
)
from lemanruss.htl.n200plan import (
    ERR_HI,
    TSpec,
    depth_analysis,
    neutral_signatures,
    trojan_of,
)
from tests.helpers import odin_available


def generated_base(seed: int = 3, n_in: int = 12, n_gates: int = 60, n_out: int = 4) -> str:
    """A random combinational BLIF (AND / OR / XOR style 2- and 3-input gates)."""
    rng = random.Random(seed)
    ins = [f"i{k}" for k in range(n_in)]
    nets = list(ins)
    lines = [".model gen", ".inputs " + " ".join(ins)]
    gates: list[str] = []
    for g in range(n_gates):
        k = rng.choice((2, 3))
        src = rng.sample(nets, k)
        out = f"g{g}"
        rows = {2: [["11 1"], ["1- 1", "-1 1"], ["10 1", "01 1"]],
                3: [["111 1"], ["1-- 1", "-1- 1", "--1 1"], ["110 1", "001 1"]]}[k]
        gates += [".names " + " ".join([*src, out]), *rng.choice(rows)]
        nets.append(out)
    outs = [f"g{n_gates - 1 - k}" for k in range(n_out)]
    lines.append(".outputs " + " ".join(outs))
    return "\n".join(lines + gates + [".end"]) + "\n"


class TestHelpers(unittest.TestCase):
    def test_steps_roundtrip(self) -> None:
        steps = [{"a": 1, "b": 0}, {"a": 0, "b": 1}]
        self.assertEqual(decode_steps(["a", "b"], encode_steps(["a", "b"], steps)), steps)

    def test_force_off_turns_trigger_constant(self) -> None:
        text = (".model m\n.inputs a b\n.outputs y\n.names a b __htl_trigger_0\n11 1\n"
                ".names __htl_trigger_0 y\n1 1\n.end\n")
        off = force_off(parse_single_model(text), [trig_name(0)])
        self.assertIn(".names __htl_trigger_0", off.body)
        self.assertNotIn("11 1", off.body)

    def test_depth_and_slack(self) -> None:
        model = parse_single_model(generated_base())
        dep = depth_analysis(compile_model(model), model)
        self.assertGreaterEqual(dep.depth, 2)
        self.assertEqual(min(dep.slack.values()), 0)

    def test_tspec_key_distinguishes_victim(self) -> None:
        a = TSpec("comb", (("n1", 1), ("n2", 0)), 0, "p<1e-2", ERR_HI, "o1", 0, False, 0.0)
        b = TSpec("comb", (("n1", 1), ("n2", 0)), 0, "p<1e-2", ERR_HI, "o2", 0, False, 0.0)
        self.assertNotEqual(a.key(), b.key())
        self.assertEqual(a.net_set(), frozenset({"n1", "n2"}))
        self.assertEqual(trojan_of(a).id, "t-comb-rare__p-err-hi__netlist")

    def test_neutral_signatures_are_distinct(self) -> None:
        from lemanruss.htl.n200plan import Ctx

        class Fake(Ctx):
            def _draw_triggered(self, *a: object, **k: object) -> None:
                return None

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "gen.blif"
            p.write_text(generated_base(), encoding="utf-8")
            sigs = neutral_signatures(Fake(p, 0), 50, random.Random(1))
        self.assertEqual(len(sigs), len(set(sigs)))
        self.assertGreater(len(sigs), 40)


def equiv_tool_available() -> bool:
    """True when tools/equiv-check runs (needs ABC) and says a circuit equals itself."""
    try:
        from lemanruss.htl.n200check import run_cec

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.blif"
            p.write_text(generated_base(), encoding="utf-8")
            return run_cec(p, p)[0] == "equivalent"
    except Exception:
        return False


@unittest.skipUnless(odin_available() and equiv_tool_available(),
                     "needs Odin III and tools/equiv-check (ABC)")
class TestObfuscate(unittest.TestCase):
    def test_finalize_hides_names_and_order(self) -> None:
        from lemanruss.htl import obfuscate as ob

        text = generated_base()
        a = ob.finalize(text, random.Random(1))
        b = ob.finalize(text, random.Random(2))
        self.assertNotEqual(a, b)
        self.assertEqual(ob.signature(a), ob.signature(b))
        self.assertTrue(a.startswith(".model top\n"))
        self.assertNotIn("g5 ", a.replace(".outputs", ""))  # internal nets renamed
        self.assertNotIn("#", a)

    def test_canonical_golden_renames_foreign_net_names(self) -> None:
        from lemanruss.htl import obfuscate as ob

        t = ".model x\n.inputs A B\n.outputs Y\n.names A B $n5\n11 1\n.names $n5 Y\n1 1\n.end\n"
        c = ob.canonical(t)
        self.assertNotIn("$", c)
        self.assertEqual(ob.signature(c), ob.signature(t))

    def test_canonical_golden_has_common_header(self) -> None:
        from lemanruss.htl import obfuscate as ob

        self.assertTrue(ob.canonical("# c\n" + generated_base()).startswith(".model top\n"))


@unittest.skipUnless(odin_available() and equiv_tool_available(),
                     "needs Odin III and tools/equiv-check (ABC)")
class TestBuildBase(unittest.TestCase):
    def test_small_comb_base(self) -> None:
        from lemanruss.htl.n200 import build_base

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = root / "gen.blif"
            base.write_text(generated_base(), encoding="utf-8")
            out = root / "out"
            res = build_base(("Seeker-Comb", base, out, 1, 0))
            circuits = res["circuits"]
            sets = res["sets"]
            assert isinstance(circuits, list) and isinstance(sets, dict)
            files = sorted((out / "circuits").glob("*.blif"))
            self.assertEqual(len(files), 1 + len(circuits))
            texts = [f.read_text(encoding="utf-8") for f in files]
            self.assertEqual(len(texts), len(set(texts)), "a circuit repeats another")
            self.assertEqual(set(sets), {"K4", "K6", "G"})
            for name, v in sets.items():
                self.assertTrue(10 <= v["n_infected_drawn"] <= 70, name)
                self.assertLessEqual(v["infected"] + v["clean"], 100)
            self.assertTrue(circuits)
            for c in circuits:
                self.assertEqual(c["obf_cec"], "equivalent")
                # p-slowdown is always on (no trigger): no witness, so no "odin_replay" field.
                self.assertTrue(all(r.get("odin_replay", r.get("always_on")) for r in c["records"]))
            for t in texts:
                self.assertTrue(t.startswith(".model top\n"))
                self.assertNotIn("__htl", t)
            for c in circuits:
                specs = c.get("specs", [])
                self.assertLessEqual(len(specs), 3)
                victims = [s["victim"] for s in specs]
                self.assertEqual(len(victims), len(set(victims)))
                trig_nets = [n[0] for s in specs for n in s["nets"]]
                self.assertEqual(len(trig_nets), len(set(trig_nets)))


if __name__ == "__main__":
    unittest.main()
