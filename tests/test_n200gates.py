"""Verify gates of the round 8 fix: distinct files and style parity (synthetic releases, and the
rc3 release on disk, which must FAIL both gates)."""

from __future__ import annotations

import gzip
import json
import os
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.n200gates import (
    cmh,
    gate_distinct,
    gate_provenance,
    scan_release,
    style_features,
    style_parity,
)

PLAIN = ".model m\n.inputs a b\n.outputs y\n.names a b y\n11 1\n.end\n"
DBL_INV = (".model m\n.inputs a b\n.outputs y\n.names a t\n0 1\n.names t u\n0 1\n"
           ".names u b y\n11 1\n.end\n")
DBL_BUF = (".model m\n.inputs a b\n.outputs y\n.names a t\n1 1\n.names t u\n1 1\n"
           ".names u b y\n11 1\n.end\n")


def make_release(root: Path, circuits: dict[str, tuple[str, str, str]]) -> None:
    """circuits: id -> (text, role, base); golden = c0."""
    (root / "circuits").mkdir(parents=True)
    (root / "answer_key").mkdir()
    prov = {}
    for cid, (text, role, base) in circuits.items():
        with gzip.open(root / "circuits" / f"{cid}.blif.gz", "wt", encoding="utf-8") as fh:
            fh.write(text)
        prov[cid] = {"base": base, "source": cid, "restructuring": "identity", "role": role,
                     "clean_twin": "c0", "insert": None}
    (root / "answer_key" / "provenance.json").write_text(json.dumps(prov), encoding="utf-8")
    (root / "answer_key" / "labels.json").write_text(
        json.dumps({c: None if v[1] == "clean" else "t" for c, v in circuits.items()}),
        encoding="utf-8")
    (root / "answer_key" / "renames.json").write_text("{}", encoding="utf-8")


def run(circuits: dict[str, tuple[str, str, str]]) -> tuple[dict[str, object], dict[str, object]]:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "rel"
        make_release(root, circuits)
        recs, prov, _lab = scan_release(root, workers=1)
        return gate_distinct(recs, prov), style_parity(recs, prov)


def _dd(x: object) -> dict[str, object]:
    assert isinstance(x, dict)
    return x


def _dl(x: object) -> list[dict[str, object]]:
    assert isinstance(x, list)
    return x


def _n(text: str, drop: frozenset[str] = frozenset()) -> dict[str, object]:
    return _dd(style_features(text, drop)["n"])


class TestFeatures(unittest.TestCase):
    def test_artefacts(self) -> None:
        self.assertEqual(_n(DBL_INV).get("dbl_inv"), 1)
        self.assertEqual(_n(DBL_BUF).get("dbl_buf"), 1)
        self.assertNotIn("dbl_inv", _n(PLAIN))

    def test_drop_ignores_inserted_cells(self) -> None:
        n = _n(DBL_INV, frozenset({"u"}))
        self.assertNotIn("dbl_inv", n)

    def test_cmh_detects_and_ignores(self) -> None:
        _z, delta, p = cmh([(0, 50, 50, 0), (0, 40, 40, 0)])
        self.assertGreater(delta, 0.9)
        self.assertLess(p, 1e-6)
        _z, delta, p = cmh([(25, 25, 25, 25)])
        self.assertAlmostEqual(delta, 0.0)
        self.assertGreater(p, 0.5)


class TestNames(unittest.TestCase):
    def test_name_features(self) -> None:
        from lemanruss.htl.n200gates import name_features

        ok = (".model m\n.inputs a\n.outputs y\n.names a n1\n1 1\n.names n1 n2\n1 1\n"
              ".names n2 y\n1 1\n")
        odd = ok + ".names n2 $abc99 \n1 1\n.names $abc99 z\n1 1\n"
        self.assertEqual(name_features(ok)["fit"], 0.5)
        self.assertEqual(name_features(ok, frozenset({"a", "y"}))["foreign"], 0)
        far = ok.replace("n2", "n900")
        self.assertGreater(float(str(name_features(far)["idx"])), 1.0)
        self.assertLess(float(str(name_features(odd)["fit"])), 0.5)

    def test_name_style_leak_fails(self) -> None:
        base = {"c0": (PLAIN, "clean", "B")}
        for k in range(1, 41):
            nets = " ".join(f"n{j}" for j in range(1, 5))
            clean = (f".model m\n.inputs a\n.outputs y\n.names a n1\n1 1\n.names n1 n2\n1 1\n"
                     f".names n2 y\n1 1\n# {k}\n")
            inf = clean.replace("n2", "n5000")  # index far above the range
            base[f"c{k}"] = (clean, "clean", "B")
            base[f"d{k}"] = (inf, "infected", "B")
            del nets
        _, st = run(base)
        self.assertFalse(st["ok"])


class TestProvenance(unittest.TestCase):
    def test_traces_detected(self) -> None:
        from lemanruss.htl.n200gates import provenance_problems

        clean = ".model top\n.inputs a\n.outputs y\n.names a n3\n1 1\n.names n3 y\n1 1\n.end\n"
        self.assertEqual(provenance_problems(clean, False), [])
        self.assertTrue(provenance_problems(clean.replace(".end", "# c\n.end"), False))
        self.assertTrue(provenance_problems(clean.replace("n3", "$n3"), False))
        self.assertTrue(provenance_problems(clean.replace(".model top", ".model s27"), False))
        self.assertTrue(provenance_problems(clean.replace(".names a", ".attr x\n.names a"), False))
        self.assertTrue(provenance_problems(clean.replace("n3", "new_n3"), False))
        self.assertEqual(provenance_problems(clean.replace("n3", "new_n3"), True), [])


class TestScrubRange(unittest.TestCase):
    def test_inserted_names_stay_in_range(self) -> None:
        import re

        from lemanruss.htl.release import scrub_group

        nets = [f"n{2 * k}" for k in range(1, 51)]  # gap ratio about 2
        text = " ".join(nets) + " " + " ".join(f"__htl_x{j}" for j in range(10))
        _out, mapping = scrub_group({"c": text}, text, "k", 0)
        nums = [int(re.sub(r"\D", "", v)) for v in mapping.values()]
        self.assertEqual(len(nums), 10)
        self.assertLessEqual(max(nums), 100 + 10 * 2 + 1 + 40)
        self.assertTrue(all(n not in {2 * k for k in range(1, 51)} for n in nums))


class TestGates(unittest.TestCase):
    def test_duplicates_fail(self) -> None:
        c = {"c0": (PLAIN, "clean", "B"), "c1": (DBL_INV, "clean", "B"),
             "c2": (DBL_INV.replace(".model m", ".model other"), "infected", "B")}
        dist, _ = run(c)
        self.assertFalse(dist["ok"])
        self.assertEqual(_dd(dist["norm"])["groups_across_labels"], 1)
        self.assertEqual(_dd(dist["sha"])["groups"], 0)

    def test_distinct_pass(self) -> None:
        c = {"c0": (PLAIN, "clean", "B"), "c1": (DBL_INV, "clean", "B"),
             "c2": (DBL_BUF, "infected", "B")}
        dist, _ = run(c)
        self.assertTrue(dist["ok"])

    def test_style_leak_fails_and_parity_passes(self) -> None:
        leak = {"c0": (PLAIN, "clean", "B")}
        for k in range(1, 41):
            leak[f"c{k}"] = (DBL_INV + f"# {k}\n", "clean", "B")
            leak[f"d{k}"] = (PLAIN + f"# {k}\n", "infected", "B")
        _, st = run(leak)
        self.assertFalse(st["ok"])
        self.assertGreater(float(str(_dd(_dd(st["auroc_by_form"])["identity"])["auroc"])), 0.9)
        same = {"c0": (PLAIN, "clean", "B")}
        for k in range(1, 41):
            same[f"c{k}"] = (DBL_INV if k % 2 else PLAIN, "clean", "B")
            same[f"d{k}"] = (DBL_INV if k % 2 else PLAIN, "infected", "B")
        _, st = run(same)
        self.assertTrue(st["ok"], st["problems"])


def seq_text(k: int, init_extra: str) -> str:
    """Two original latches (init 2) and, when `init_extra` is set, one more with that init."""
    lines = [".model top", ".inputs a b clock", ".outputs y",
             ".names a b t\n11 1", ".latch t q0 re clock 2", ".names q0 a u\n10 1",
             ".latch u q1 re clock 2", ".names q1 q0 y\n11 1"]
    if init_extra:
        lines += [".names q1 a v\n01 1", f".latch v q2 re clock {init_extra}"]
    lines += [f".names b w{k}\n1 1", ".end"]
    return "\n".join(lines) + "\n"


class TestLatchFields(unittest.TestCase):
    def test_features(self) -> None:
        lat = _dd(style_features(seq_text(1, "0"))["lat"])
        self.assertEqual(lat["latches"], 3)
        self.assertEqual(lat["init"], {"2": 2, "0": 1})
        self.assertEqual(lat["clock"], {"main": 3})

    def test_init_leak_fails_and_same_convention_passes(self) -> None:
        leak = {"c0": (seq_text(0, ""), "clean", "B")}
        for k in range(1, 41):
            leak[f"c{k}"] = (seq_text(k, ""), "clean", "B")
            leak[f"d{k}"] = (seq_text(k, "0" if k % 5 else ""), "infected", "B")
        _, st = run(leak)
        self.assertFalse(st["ok"])
        self.assertGreater(float(str(_dd(_dd(st["auroc_by_form"])["identity"])["auroc"])), 0.7)
        ok = {"c0": (seq_text(0, ""), "clean", "B")}
        for k in range(1, 41):
            ok[f"c{k}"] = (seq_text(k, "2" if k % 2 else ""), "clean", "B")
            ok[f"d{k}"] = (seq_text(k, "2" if k % 2 else ""), "infected", "B")
        _, st = run(ok)
        self.assertTrue(st["ok"], st["problems"])

    def test_mixed_convention_is_a_trace(self) -> None:
        from lemanruss.htl.n200gates import provenance_problems

        self.assertEqual(provenance_problems(seq_text(1, "2"), True), [])
        self.assertTrue(provenance_problems(seq_text(1, "0"), True))

    def test_other_cover_fields(self) -> None:
        n = _n(".model m\n.inputs a b\n.outputs y\n.names n5 n2 t\n11 1\n0- 0\n"
               ".names t y\n1 1\n.end\n")
        self.assertEqual((n["cov0"], n["dc"], n["rows_unsorted"], n["in_unsorted"]), (1, 1, 1, 1))


RC4 = Path(os.environ.get("LEMANRUSS_RC4_SEQ", str(
    Path(__file__).resolve().parents[2] / "htl-rel" / "rc4b" / "seeker-seq-v2.0-rc4")))


@unittest.skipUnless((RC4 / "answer_key" / "provenance.json").exists(), "rc4 seq not on disk")
class TestRc4SeqFails(unittest.TestCase):
    def test_rc4_seq_latch_init_leak_is_caught(self) -> None:
        recs, prov, _lab = scan_release(RC4, workers=4, bases={"s27", "s298", "b01"})
        st = style_parity(recs, prov)
        self.assertFalse(st["ok"])
        feats = {str(t["feature"]) for t in _dl(st["flagged"])}
        self.assertIn("lat_init_0_any", feats)
        au = _dd(_dd(st["auroc_by_form"])["identity"])
        self.assertEqual(au["best_feature"], "lat_init_0/latches")
        self.assertGreater(float(str(au["auroc"])), 0.99)
        self.assertFalse(gate_provenance(recs, prov)["ok"])


RC5 = Path(os.environ.get("LEMANRUSS_RC5_SEQ", str(
    Path(__file__).resolve().parents[2] / "htl-rel" / "rc5" / "seeker-seq-v2.0-rc5")))


@unittest.skipUnless((RC5 / "answer_key" / "provenance.json").exists(), "rc5 seq not on disk")
class TestRc5SeqPasses(unittest.TestCase):
    def test_rc5_seq_passes_the_latch_gate(self) -> None:
        recs, prov, _lab = scan_release(RC5, workers=4)
        st = style_parity(recs, prov)
        self.assertTrue(st["ok"], st["problems"])
        self.assertTrue(gate_provenance(recs, prov)["ok"])
        self.assertTrue(gate_distinct(recs, prov)["ok"])


RC3 = Path(os.environ.get("LEMANRUSS_RC3_COMB", str(
    Path(__file__).resolve().parents[2] / "htl-rel" / "rc3" / "seeker-comb-v2.0-rc3")))


@unittest.skipUnless((RC3 / "answer_key" / "provenance.json").exists(), "rc3 not on disk")
class TestRc3Fails(unittest.TestCase):
    def test_rc3_comb_fails_both_gates(self) -> None:
        recs, prov, _lab = scan_release(RC3, workers=4, bases={"C17", "C432"})
        self.assertFalse(gate_distinct(recs, prov)["ok"])
        self.assertFalse(style_parity(recs, prov)["ok"])
        self.assertFalse(gate_provenance(recs)["ok"])


if __name__ == "__main__":
    unittest.main()
