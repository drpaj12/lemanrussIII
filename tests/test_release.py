"""Release packaging and `lemanruss verify` (spec section 10) on a three-gate family."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lemanruss.htl import relverify
from lemanruss.htl.release import (
    Tools,
    build_release,
    detect_style,
    gz_bytes,
    read_blif_gz,
    scrub_group,
    strip_comments,
    unscrub,
)
from lemanruss.htl.restructure import abc_bin
from tests.helpers import odin_available

CLEAN = (".model top\n.inputs a b c\n.outputs y\n.names a b [1]\n11 1\n"
         ".names [1] c [2]\n11 1\n.names [2] y\n1 1\n.end\n")
INFECTED = (".model top\n.inputs a b c\n.outputs y\n.names a b [1]\n11 1\n"
            ".names [1] c [2]\n11 1\n.names [2] __htl_tmp_y\n1 1\n"
            ".names a b c __htl_trigger\n111 1\n.names __htl_trigger __htl_tmp_y y\n01 1\n.end\n")
TID = "t-comb-rare__p-dos-stuck__netlist"


def make_root(root: Path) -> None:
    (root / "circuits").mkdir(parents=True)
    key = root / "answer_key"
    key.mkdir()
    (root / "circuits" / "sc0001.blif").write_text(CLEAN, encoding="utf-8")
    (root / "circuits" / "sc0002.blif").write_text(INFECTED, encoding="utf-8")
    cat = {TID: {"id": TID, "trigger": {"kind": "t-comb-rare"}, "payload": {"kind": "p-dos-stuck"}}}
    man = {"bases": ["tiny"], "seed": 0, "v1_lineage": "v1 test", "trojans": [TID],
           "trojan_catalogue": cat,
           "circuits": [{"id": "sc0001", "base": "tiny", "file": "circuits/sc0001.blif"},
                        {"id": "sc0002", "base": "tiny", "file": "circuits/sc0002.blif"}]}
    files = {
        "manifest.json": man,
        "answer_key/labels.json": {"sc0001": None, "sc0002": TID},
        "answer_key/inserts.json": {"sc0002": {"base": "tiny", "clean": "sc0001", "kind": "comb",
                                               "stuck": 0, "variant": "p<1e-2", "victim": "y",
                                               "window": 1}},
        "answer_key/restructured.json": [],
        "answer_key/rareness.json": [{"circuit": "sc0002", "p": 0.125}],
        "answer_key/insertion.json": {},
        "answer_key/failures.json": [],
    }
    for name, obj in files.items():
        (root / name).write_text(json.dumps(obj), encoding="utf-8")
    (key / "rareness.md").write_text("| band reached | circuits |\n|---|---|\n| p<1e-2 | 1 |\n",
                                     encoding="utf-8")


class TestScrub(unittest.TestCase):
    def test_reversible_and_neutral(self) -> None:
        texts = {"a": INFECTED, "b": INFECTED + ".names x__htl_pre y\n"}
        new, mp = scrub_group(texts, CLEAN, "a", 0)
        self.assertEqual(len(mp), 3)
        for k, t in new.items():
            self.assertNotIn("__htl_", t)
            self.assertEqual(unscrub(t, mp), texts[k])
        fmt, _top = detect_style(CLEAN)
        self.assertEqual(fmt, "[{}]")
        self.assertTrue(all(v.startswith("[") for v in mp.values()))
        self.assertEqual(scrub_group(texts, CLEAN, "a", 0)[1], mp)

    def test_clean_text_unchanged(self) -> None:
        new, mp = scrub_group({"a": CLEAN}, CLEAN, "a", 0)
        self.assertEqual((new["a"], mp), (CLEAN, {}))

    def test_strip_comments(self) -> None:
        self.assertEqual(strip_comments("# Benchmark x\n.model top\n.end\n"),
                         (".model top\n.end\n", 1))

    def test_gzip_deterministic(self) -> None:
        self.assertEqual(gz_bytes(CLEAN), gz_bytes(CLEAN))

    def test_unscrub_ignores_bus_substring(self) -> None:
        self.assertEqual(unscrub("q[5] [5]", {"orig": "[5]"}), "q[5] orig")


class TestSampling(unittest.TestCase):
    def test_stratified_at_least_one(self) -> None:
        s = relverify.pick_sample({"a": [f"x{i}" for i in range(25)], "b": ["y"]}, 1)
        self.assertEqual(len([x for x in s if x.startswith("x")]), 3)
        self.assertIn("y", s)

    def test_sigma(self) -> None:
        self.assertTrue(relverify._sigma_ok(0.001, 0.0011, 1 << 20, 1 << 20))
        self.assertFalse(relverify._sigma_ok(0.01, 0.001, 1 << 20, 1 << 20))


class TestRelease(unittest.TestCase):
    def build(self, tmp: Path) -> Path:
        src = tmp / "src"
        make_root(src)
        out = tmp / "rel"
        build_release(src, out, "Seeker-Comb", "sc", 0, Tools("pin", "co", "abc"), None)
        return out

    def test_package_and_static_checks(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out = self.build(Path(t))
            self.assertNotIn("__htl_", read_blif_gz(out / "circuits" / "sc0002.blif.gz"))
            self.assertTrue(relverify.check_integrity(out)["ok"])
            self.assertTrue(relverify.check_separation(out)["ok"])
            leak = relverify.check_leak(out)
            self.assertTrue(leak["ok"], leak)
            ren = json.loads((out / "answer_key" / "renames.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(ren["sc0002"].values()),
                             ["__htl_tmp_y", "__htl_trigger"])

    def test_excluded_base_is_not_released(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "src"
            make_root(src)
            (src / "circuits" / "sc0003.blif").write_text(CLEAN, encoding="utf-8")
            man = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
            man["bases"].append("other")
            man["circuits"].append({"id": "sc0003", "base": "other",
                                    "file": "circuits/sc0003.blif"})
            (src / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
            lab = json.loads((src / "answer_key" / "labels.json").read_text(encoding="utf-8"))
            lab["sc0003"] = None
            (src / "answer_key" / "labels.json").write_text(json.dumps(lab), encoding="utf-8")
            (src / "answer_key" / "failures.json").write_text(
                json.dumps([{"base": "other", "variant": "v", "reason": "r"}]), encoding="utf-8")
            out = Path(t) / "rel"
            build_release(src, out, "Seeker-Comb", "sc", 0, Tools("pin", "co", "abc"), None,
                          "2.0-rc2", {"other": "cannot be checked"})
            self.assertFalse((out / "circuits" / "sc0003.blif.gz").exists())
            self.assertTrue((out / "circuits" / "sc0002.blif.gz").exists())
            self.assertEqual(json.loads((out / "answer_key" / "failures.json").read_text(
                encoding="utf-8")), [])
            sheet = (out / "DATASHEET.md").read_text(encoding="utf-8")
            self.assertIn("Built but not released", sheet)
            self.assertIn("other: cannot be checked", sheet)
            self.assertIn("2.0-rc2", sheet)
            self.assertTrue(relverify.check_integrity(out)["ok"])

    def test_leak_catches_edit_event_text(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out = self.build(Path(t))
            leaked = read_blif_gz(out / "circuits" / "sc0002.blif.gz")
            (out / "circuits" / "sc0002.blif.gz").write_bytes(
                gz_bytes(leaked + ".attr odin3_edit added:x\n"))
            leak = relverify.check_leak(out)
            self.assertFalse(leak["ok"])
            self.assertEqual(leak["odin3_edit_circuits"], 1)

    def test_no_edit_event_text_in_clean_release(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out = self.build(Path(t))
            leak = relverify.check_leak(out)
            self.assertEqual((leak["odin3_edit_circuits"], leak["odin3_edit_manifest"]), (0, 0))

    def test_integrity_catches_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out = self.build(Path(t))
            (out / "circuits" / "sc0001.blif.gz").write_bytes(gz_bytes(CLEAN + "\n"))
            self.assertFalse(relverify.check_integrity(out)["ok"])

    def test_leak_catches_inserter_name(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out = self.build(Path(t))
            (out / "circuits" / "sc0002.blif.gz").write_bytes(gz_bytes(INFECTED))
            self.assertFalse(relverify.check_leak(out)["ok"])

    @unittest.skipUnless(odin_available() and abc_bin().exists(), "needs Odin III + ABC")
    def test_function_and_rareness(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            out = self.build(Path(t))
            fn = relverify.check_function(out, Path(t) / "scratch", 1, 5)
            self.assertTrue(fn["ok"], fn)
            self.assertEqual(fn["odin_fired"], 1)
            self.assertTrue(relverify.check_rareness(out, 1, 5)["ok"])


if __name__ == "__main__":
    unittest.main()
