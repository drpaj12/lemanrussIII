"""Units, quotas, intervals and key packing of the public Seeker v2.0 tester (no Odin III)."""

from __future__ import annotations

import io
import json
import random
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lemanruss.score import keypack, ledger
from lemanruss.score.key import Key, load
from lemanruss.score.scorer import render, score, unit_of
from lemanruss.score.submission import SubmissionError
from lemanruss.score.subsets import load_subsets

REL = "seeker-comb-v2.0"
SETS = ("K4", "K6", "gates")
BENCH = ("alpha", "beta", "gamma")


def toy_release(root: Path) -> tuple[Path, Path]:
    """answer_key dir (with private extras and ids outside the public sets) and public tree."""
    rng = random.Random(4)
    key_dir, pub = root / "answer_key", root / "public"
    key_dir.mkdir()
    labels: dict[str, Any] = {}
    trojans: dict[str, Any] = {}
    k = 0
    for b in BENCH:
        (pub / b).mkdir(parents=True)
        lines = []
        for s in SETS:
            ids = []
            for i in range(100):
                cid = f"sc{k:05d}"
                k += 1
                ids.append(cid)
                if i < 30 + 10 * SETS.index(s):
                    n = 1 + i % 3
                    labels[cid] = [f"t{j}" for j in range(n)]
                    trojans[cid] = [{"victim": "secret"}] * n
                else:
                    labels[cid] = None
            lines.append(f"{s}: " + " ".join(rng.sample(ids, 100)))
        (pub / b / "sets.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for extra in range(5):  # private circuits outside every public set
        labels[f"zz{extra}"] = ["x"]
        trojans[f"zz{extra}"] = [{}]
    for name, obj in (("labels", labels), ("trojans", trojans), ("scripts", {"a": 1}),
                      ("rareness", {"a": 1})):
        (key_dir / f"{name}.json").write_text(json.dumps(obj), encoding="utf-8")
    return key_dir, pub


class UnitBase(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.key_dir, self.pub = toy_release(self.root)
        self.archive = self.root / "k.tar.gz"
        keypack.pack(self.key_dir, self.pub, REL, "comb", self.archive)
        self.packed = keypack.unpack(self.archive, self.root / "out")
        self.key: Key = load(self.packed)
        _, self.subs = load_subsets(self.packed / "subsets.json")

    def csv(self, unit: str, perfect: bool = True, rel: str = REL) -> str:
        rows = []
        for c in self.subs[unit]:
            inf = self.key.infected(c) if perfect else 0
            n = self.key.n_trojans(c) if perfect else 0
            rows.append(f"{c},{inf},{0.9 if inf else 0.1},{n},")
        return (f"# seeker-release: {rel}\n# subset: {unit}\n# detector: d\n# team: t\n"
                "id,infected,score,count,locations\n" + "\n".join(rows) + "\n")

    def run_score(self, unit: str, **kw: Any) -> dict[str, Any]:
        return score(self.csv(unit), self.key, REL, self.subs, **kw)


class KeyPackTests(UnitBase):
    def test_units_and_set_names(self) -> None:
        self.assertEqual(
            set(self.subs),
            {f"{b}-{s}" for b in BENCH for s in SETS} | set(BENCH) | {"Comb"})
        self.assertEqual(len(self.subs["alpha-K4"]), 100)
        self.assertEqual(len(self.subs["alpha"]), 300)
        self.assertEqual(len(self.subs["Comb"]), 900)
        self.assertEqual(set(self.key.set_of.values()), set(SETS))

    def test_only_public_ids_and_files(self) -> None:
        with tarfile.open(self.archive) as tf:
            names = sorted(m.name for m in tf)
        self.assertEqual(names, sorted(f"{REL}-key/{n}" for n in keypack.FILES))
        self.assertEqual(len(self.key.labels), 900)
        self.assertFalse(any(c.startswith("zz") for c in self.key.labels))
        blob = "".join(p.read_text() for p in self.packed.iterdir())
        for word in ("secret", "scripts", "rareness"):
            self.assertNotIn(word, blob)

    def test_deterministic(self) -> None:
        other = self.root / "k2.tar.gz"
        keypack.pack(self.key_dir, self.pub, REL, "comb", other)
        self.assertEqual(self.archive.read_bytes(), other.read_bytes())

    def test_reports_equal_full_key(self) -> None:
        full = self.root / "full"
        full.mkdir()
        for n in ("labels", "trojans"):
            (full / f"{n}.json").write_text(
                (self.key_dir / f"{n}.json").read_text(encoding="utf-8"), encoding="utf-8")
        sets = json.loads((self.packed / "sets.json").read_text(encoding="utf-8"))
        (full / "sets.json").write_text(json.dumps(sets), encoding="utf-8")
        a = self.run_score("beta", seed=3)
        b = score(self.csv("beta"), load(full), REL, self.subs, seed=3)
        self.assertEqual(a, b)

    def test_size_report_matches(self) -> None:
        out = self.root / "k3.tar.gz"
        sizes = keypack.pack(self.key_dir, self.pub, REL, "comb", out)
        self.assertEqual(sizes["archive"], out.stat().st_size)
        self.assertEqual(sizes["labels.json"], (self.packed / "labels.json").stat().st_size)

    def test_pack_errors(self) -> None:
        bad = self.pub / "alpha" / "sets.txt"
        bad.write_text(bad.read_text().replace("K4: ", "K4: nosuchid ", 1), encoding="utf-8")
        with self.assertRaises(keypack.KeyPackError):
            keypack.build(self.key_dir, self.pub, REL, "comb")

    def test_unpack_refuses_bad_members(self) -> None:
        evil = self.root / "evil.tar.gz"
        with tarfile.open(evil, "w:gz") as tf:
            ti = tarfile.TarInfo("../outside.json")
            ti.size = 2
            tf.addfile(ti, io.BytesIO(b"{}"))
        with self.assertRaises(keypack.KeyPackError):
            keypack.unpack(evil, self.root / "o2")
        self.assertFalse((self.root / "outside.json").exists())


class UnitScoreTests(UnitBase):
    def test_unit_kinds(self) -> None:
        self.assertEqual(unit_of("alpha-K6", self.key, self.subs), ("cell", "alpha"))
        self.assertEqual(unit_of("alpha", self.key, self.subs), ("benchmark", "alpha"))
        self.assertEqual(unit_of("Comb", self.key, self.subs), ("family", None))

    def test_hidden_sample_per_set(self) -> None:
        self.assertEqual(self.run_score("alpha-K4", seed=1)["scored_circuits"], 70)
        self.assertEqual(self.run_score("alpha", seed=1)["scored_circuits"], 210)
        self.assertEqual(self.run_score("Comb", seed=1)["scored_circuits"], 630)
        self.assertEqual(self.run_score("alpha", seed=2), self.run_score("alpha", seed=2))
        a = self.run_score("alpha-K4", seed=1)["primary"]["confusion"]
        self.assertNotEqual(a, self.run_score("alpha-K4", seed=9)["primary"]["confusion"])

    def test_intervals(self) -> None:
        cell = self.run_score("alpha-K4", seed=1)
        self.assertEqual(cell["primary"]["auroc_ci95_over"], "circuits")
        self.assertIsNotNone(cell["primary"]["auroc_ci95"])
        self.assertIn("optimistic", render(cell))
        fam = self.run_score("Comb", seed=1)
        self.assertEqual(fam["primary"]["auroc_ci95_over"], "bases")
        self.assertNotIn("optimistic", render(fam))

    def test_family_report_has_no_benchmark_table(self) -> None:
        fam = self.run_score("Comb", seed=1)
        blob = json.dumps(fam) + render(fam)
        for b in BENCH:
            self.assertNotIn(b, blob)
        self.assertEqual(set(fam["primary"]["by_set"]), set(SETS))

    def test_set_names_in_report(self) -> None:
        rep = self.run_score("alpha", seed=1)
        self.assertEqual(set(rep["primary"]["by_set"]), set(SETS))

    def test_per_benchmark_baseline(self) -> None:
        from unittest import mock

        from lemanruss.score import scorer

        bl = self.root / "bl.json"
        bl.write_text(json.dumps({REL: {"size-only": {"gates": 0.5, "alpha-gates": 0.6,
                                                      "G": 0.4}}}), encoding="utf-8")
        with mock.patch.object(scorer, "BASELINES", bl):
            rep = self.run_score("alpha-gates", seed=1)
            other = self.run_score("beta-gates", seed=1)
        self.assertEqual(rep["baselines"][0]["auroc"], 0.6)
        self.assertEqual(rep["baselines"][0]["scope"], "unit alpha-gates")
        self.assertEqual(other["baselines"][0]["auroc"], 0.4)

    def test_invalid_uses_no_quota(self) -> None:
        led = self.root / "ledger.jsonl"
        for text in ("junk", self.csv("alpha-K4", rel="seeker-seq-v2.0")):
            with self.assertRaises(SubmissionError):
                score(text, self.key, REL, self.subs, ledger_path=led, submitter="u", now=1.0)
        self.assertFalse(led.exists())


class QuotaTests(UnitBase):
    DAY = 24 * 3600

    def go(self, unit: str, who: str, t: float, lim: ledger.Limits | None = None) -> None:
        self.run_score(unit, ledger_path=self.root / "led.jsonl", submitter=who,
                       now=t, seed=1, limits=lim)

    def refused(self, unit: str, who: str, t: float, msg: str) -> None:
        with self.assertRaises(ledger.RateLimitError) as cm:
            self.go(unit, who, t)
        self.assertIn(msg, str(cm.exception))

    def test_one_per_24h_states_retry(self) -> None:
        self.go("alpha-K4", "u", 1000.0)
        self.refused("beta-K4", "u", 1000.0 + 3600, "retry in 1380 minutes")
        self.go("beta-K4", "u", 1000.0 + self.DAY)
        self.go("alpha-K4", "v", 1000.0 + 3600)  # another identity is free

    def test_per_benchmark_cap_of_three(self) -> None:
        for i, u in enumerate(("alpha-K4", "alpha-K6", "alpha")):
            self.go(u, "u", 1000.0 + i * self.DAY)
        self.refused("alpha-gates", "u", 1000.0 + 3 * self.DAY, "per benchmark")
        self.go("beta-gates", "u", 1000.0 + 3 * self.DAY)

    def test_total_cap_of_ten(self) -> None:
        names = [f"{b}-{s}" for b in BENCH for s in SETS][:9]
        for i, u in enumerate(names):
            self.go(u, "u", 1000.0 + i * self.DAY)
        self.go("Comb", "u", 1000.0 + 9 * self.DAY)
        self.refused("Comb", "u", 1000.0 + 10 * self.DAY, "10 scored submissions")

    def test_family_cap_of_three(self) -> None:
        for i in range(3):
            self.go("Comb", "u", 1000.0 + i * self.DAY)
        self.refused("Comb", "u", 1000.0 + 3 * self.DAY, "3 family bundles")
        self.go("alpha-K4", "u", 1000.0 + 3 * self.DAY)  # other units still allowed

    def test_ledger_line_has_unit_and_no_labels(self) -> None:
        self.go("alpha", "u", 5.0)
        line = json.loads((self.root / "led.jsonl").read_text().splitlines()[0])
        self.assertEqual((line["unit"], line["benchmark"]), ("benchmark", "alpha"))

    def test_failed_ledger_write_raises(self) -> None:
        with self.assertRaises(OSError):
            self.run_score("alpha-K4", ledger_path=self.root / "nodir" / "l.jsonl",
                           submitter="u", now=1.0, seed=1)


class DocExampleTests(unittest.TestCase):
    def test_submission_md_example_parses(self) -> None:
        import re

        from lemanruss.score.submission import parse

        doc = (Path(__file__).resolve().parents[1] / "docs/user/SUBMISSION.md").read_text()
        block = re.search(r"\n((?:    #.*\n)+    id,infected.*\n(?:    .*\n)+)", doc)
        assert block
        text = "".join(ln[4:] + "\n" for ln in block.group(1).splitlines())
        ids = re.findall(r"^(sc\d+),", text, re.M)
        sub = parse(text, "seeker-comb-v2.0", {"C432-K4": ids})
        self.assertEqual(len(sub.rows), len(ids))


class ShippedBaselines(unittest.TestCase):
    """The shipped baselines.json is keyed by the release names the scorer looks up."""

    def test_every_release_has_baselines_for_every_scope(self) -> None:
        from lemanruss.score import scorer

        det: dict[str, Any] = {"auroc": 0.55, "ci": (0.5, 0.6)}
        for rel in ("seeker-comb-v2.0", "seeker-seq-v2.0", "seeker-proc-v2.0"):
            for subset in ("x-K4", "x-K6", "x-gates", "x-silicon", "x"):
                got = scorer._baseline(rel, subset, det)
                self.assertEqual({b["detector"] for b in got}, {"size-only", "sanity"},
                                 (rel, subset))
