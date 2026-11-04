"""Scoring tests: no Odin III needed. A toy key stands in for an answer key."""

from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lemanruss.score import bounds, ledger
from lemanruss.score.key import Key, load
from lemanruss.score.metrics import Confusion, auroc, bootstrap_auroc, rates
from lemanruss.score.regions import parse_blif, region_of
from lemanruss.score.scorer import chance_hit, render, score
from lemanruss.score.submission import SubmissionError, parse
from lemanruss.score.subsets import build_subsets

REL = "toy-v1"
HDR = f"# seeker-release: {REL}\n# subset: S\n# detector: d\n# team: t\n"
COLS = "id,infected,score,count,locations\n"


def toy_key(root: Path, n_bases: int = 8) -> Path:
    """Bases x sets K4/K6/G, 20 circuits per cell, 5 infected, Trojan counts 1..3."""
    rng = random.Random(1)
    labels: dict[str, Any] = {}
    sets: dict[str, Any] = {}
    trojans: dict[str, Any] = {}
    regions: dict[str, Any] = {}
    k = 0
    for b in range(n_bases):
        base = f"base{b}"
        gold = f"g{b}"
        labels[gold] = None
        cell: dict[str, Any] = {}
        for s in ("K4", "K6", "G"):
            inf, cln = [], []
            for i in range(20):
                cid = f"c{k:05d}"
                k += 1
                if i < 5:
                    t = 1 + i % 3
                    labels[cid] = [f"t{j}" for j in range(t)]
                    trojans[cid] = [{"victim": f"o{j}"} for j in range(t)]
                    regions[cid] = {"n_nets": 50, "trojans": [
                        {"nets": [f"n{j * 3}", f"n{j * 3 + 1}"]} for j in range(t)]}
                    inf.append(cid)
                else:
                    labels[cid] = None
                    cln.append(cid)
            cell[s] = {"infected_ids": inf, "clean_ids": cln, "n_infected_drawn": 10 + 10 * (b % 4)}
        sets[base] = {"golden": gold, "kind": "comb", "sets": cell}
    for name, obj in (("labels", labels), ("sets", sets), ("trojans", trojans),
                      ("regions", regions)):
        (root / f"{name}.json").write_text(json.dumps(obj), encoding="utf-8")
    rng.random()
    return root


def csv_for(ids: list[str], key: Key, perfect: bool = True, loc: bool = False) -> str:
    rows = []
    for c in ids:
        inf = key.infected(c) if perfect else 0
        n = key.n_trojans(c) if perfect else 0
        locs = ";".join(f"n{j * 3}" for j in range(n)) if loc and inf else ""
        rows.append(f"{c},{inf},{0.9 if inf else 0.1},{n},{locs}")
    return HDR + COLS + "\n".join(rows) + "\n"


class ParseTests(unittest.TestCase):
    subs = {"S": ["a", "b", "c"]}

    def ok(self, body: str) -> str:
        return HDR + COLS + body

    def bad(self, text: str, msg: str) -> None:
        with self.assertRaises(SubmissionError) as cm:
            parse(text, REL, self.subs)
        self.assertIn(msg, str(cm.exception))

    def test_valid(self) -> None:
        s = parse(self.ok("a,1,0.5,2,x;y\nb,0,0.1,,\nc,1,3,1,\n"), REL, self.subs)
        self.assertEqual(s.rows["a"].locations, ["x", "y"])
        self.assertIsNone(s.rows["b"].count)

    def test_errors(self) -> None:
        self.bad(self.ok("a,1,0.5,1,\nb,0,1,0,\n"), "missing")
        self.bad(self.ok("a,1,0.5,1,\na,1,0.5,1,\nb,0,1,0,\nc,0,1,0,\n"), "twice")
        self.bad(self.ok("zz,1,0.5,1,\n"), "not in subset")
        self.bad(self.ok("a,1,nan,1,\n"), "finite")
        self.bad(self.ok("a,1,inf,1,\n"), "finite")
        self.bad(self.ok("a,1,x,1,\n"), "not a number")
        self.bad(self.ok("a,2,1,1,\n"), "infected must be")
        self.bad(self.ok("a,1,1,4,\n"), "count must be")
        self.bad(self.ok("a,1,1,0,\n"), "disagrees")
        self.bad(self.ok("a,0,1,1,\n"), "disagrees")
        self.bad(self.ok("a,1,1\n"), "fields")
        self.bad(self.ok("a,1,1,1," + ";".join(f"n{i}" for i in range(11)) + "\n"), "at most 10")
        self.bad(self.ok("a,1,1,1,bad net\n"), "bad net")
        self.bad(HDR + "id,score,label\n", "column header")
        self.bad(HDR + COLS, "no rows")
        self.bad(HDR.replace(REL, "other") + COLS + "a,1,1,1,\n", "wrong release")
        self.bad(HDR.replace("subset: S", "subset: Q") + COLS, "unknown subset")
        self.bad(HDR.replace("# team: t\n", "") + COLS, "missing header")
        self.bad(HDR + "# team: u\n" + COLS, "twice")
        self.bad(HDR + "# colour: red\n" + COLS, "unknown header")
        self.bad(HDR + "x" * (5 * 1024 * 1024 + 1), "larger")

    def test_schema_agrees(self) -> None:
        schema = json.loads(
            (Path(__file__).parents[1] / "docs/user/submission.schema.json").read_text())
        row = schema["properties"]["rows"]["items"]
        from lemanruss.score import submission as sm
        self.assertEqual(list(row["properties"]), sm.COLUMNS)
        self.assertEqual(row["properties"]["locations"]["maxItems"], sm.MAX_LOCATIONS)
        self.assertEqual(row["properties"]["count"]["maximum"], sm.MAX_COUNT)
        self.assertEqual(set(schema["properties"]["headers"]["required"]), set(sm.REQUIRED_HEADERS))


class MetricTests(unittest.TestCase):
    def test_confusion_and_rates(self) -> None:
        c = Confusion.of([(1, 1), (1, 1), (1, 0), (0, 1), (0, 0), (0, 0), (0, 0)])
        self.assertEqual((c.tp, c.fp, c.tn, c.fn), (2, 1, 3, 1))
        r = rates(c)
        self.assertAlmostEqual(r["tpr"] or 0, 2 / 3)
        self.assertAlmostEqual(r["fpr"] or 0, 1 / 4)
        self.assertAlmostEqual(r["precision"] or 0, 2 / 3)
        self.assertAlmostEqual(r["f1"] or 0, 2 / 3)
        self.assertAlmostEqual(r["accuracy"] or 0, 5 / 7)
        self.assertIsNone(rates(Confusion(0, 0, 0, 0))["tpr"])

    def test_auroc_hand_computed(self) -> None:
        # positives 0.8 0.4, negatives 0.6 0.2: pairs above = 0.8>0.6,0.8>0.2,0.4>0.2 = 3 of 4
        self.assertAlmostEqual(auroc([(1, .8), (1, .4), (0, .6), (0, .2)]) or 0, 0.75)
        self.assertAlmostEqual(auroc([(1, .5), (0, .5)]) or 0, 0.5)  # a tie counts one half
        self.assertEqual(auroc([(1, 1.0), (0, 0.0)]), 1.0)
        self.assertEqual(auroc([(0, 1.0), (1, 0.0)]), 0.0)
        self.assertIsNone(auroc([(1, 1.0), (1, 0.0)]))

    def test_bootstrap_resamples_bases(self) -> None:
        by = {f"b{i}": [(1, 0.9), (0, 0.1)] for i in range(6)}
        self.assertEqual(bootstrap_auroc(by, 1), (1.0, 1.0))
        self.assertIsNone(bootstrap_auroc({"b": [(1, 1.0), (0, 0.0)]}, 1))

    def test_chance(self) -> None:
        self.assertAlmostEqual(chance_hit(10, 2, 1), 0.2)
        self.assertAlmostEqual(chance_hit(4, 2, 2), 1 - 1 / 6)
        self.assertEqual(chance_hit(5, 2, 4), 1.0)
        self.assertEqual(chance_hit(5, 0, 2), 0.0)


class SubsetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.dir = toy_key(Path(self.td.name))
        self.key = load(self.dir)

    def test_subsets(self) -> None:
        a = build_subsets(self.key, REL, 7)["subsets"]
        b = build_subsets(self.key, REL, 7)["subsets"]
        self.assertEqual(a, b)
        self.assertNotEqual(a, build_subsets(self.key, REL, 8)["subsets"])
        self.assertEqual(a["Comb-K4"]["n"], 100)
        self.assertEqual(len(set(a["Comb-K4"]["ids"])), 100)
        self.assertTrue(all(self.key.set_of[c] == "K4" for c in a["Comb-K4"]["ids"]))
        self.assertEqual(a["all"]["n"], 8 * 3 * 20)
        self.assertNotIn("g0", a["all"]["ids"])  # goldens are not scored
        per_base: dict[str, int] = {}
        for c in a["Comb-K6"]["ids"]:
            per_base[self.key.base_of[c]] = per_base.get(self.key.base_of[c], 0) + 1
        self.assertLessEqual(max(per_base.values()) - min(per_base.values()), 1)  # stratified
        t2 = a["Comb-trojans-2"]["ids"]
        self.assertEqual(sum(1 for c in t2 if self.key.n_trojans(c) == 2), 48)  # pool has 48
        self.assertEqual(a["Comb-trojans-2"]["n"], 98)  # fewer, never padded
        self.assertTrue(all(self.key.n_trojans(c) in (0, 2) for c in t2))
        self.assertEqual(sum(1 for c in a["Comb-prev-low"]["ids"]
                             if self.key.cell_prevalence[(self.key.base_of[c],
                                                          self.key.set_of[c])] > 30), 0)

    def test_no_labels_in_subsets(self) -> None:
        blob = json.dumps(build_subsets(self.key, REL, 7))
        for word in ("infected", "clean", "label", "t0", "o0"):
            self.assertNotIn(word, blob)


class ScoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.dir = toy_key(Path(self.td.name))
        self.key = load(self.dir)
        ids = build_subsets(self.key, REL, 3)["subsets"]["Comb-mix100"]["ids"]
        self.ids = ids
        self.subs = {"S": ids}

    def run_score(self, text: str, **kw: Any) -> dict[str, Any]:
        return score(text, self.key, REL, self.subs, **kw)

    def test_perfect_detector(self) -> None:
        rep = self.run_score(csv_for(self.ids, self.key, loc=True), seed=5)
        p = rep["primary"]
        self.assertEqual(rep["scored_circuits"], 70)
        self.assertEqual(p["tpr"], 1.0)
        self.assertEqual(p["fpr"], 0.0)
        self.assertEqual(p["auroc"], 1.0)
        c = p["confusion"]
        self.assertEqual(c["tp"] + c["fn"] + c["fp"] + c["tn"], 70)
        self.assertEqual(rep["bonus_count"]["exact"], 1.0)
        self.assertEqual(rep["bonus_location"]["hit_rate"], 1.0)
        self.assertLess(rep["bonus_location"]["chance_rate"], 0.5)
        for t, v in p["found_by_true_trojan_count"].items():
            self.assertTrue(v.get("suppressed") or v["found"] == 1.0, t)

    def test_all_clean_detector(self) -> None:
        rep = self.run_score(csv_for(self.ids, self.key, perfect=False), seed=5)
        p = rep["primary"]
        self.assertEqual(p["tpr"], 0.0)
        self.assertEqual(p["confusion"]["tp"], 0)
        self.assertEqual(rep["bonus_location"].get("suppressed"), True)

    def test_hidden_sample(self) -> None:
        text = csv_for(self.ids, self.key)
        a = self.run_score(text, seed=1, hidden_sample=50)
        self.assertEqual(a["scored_circuits"], 50)
        self.assertEqual(a, self.run_score(text, seed=1, hidden_sample=50))
        flip = text.replace(f"{self.ids[0]},", f"{self.ids[0]},", 1)
        self.assertEqual(flip, text)
        other = {self.run_score(text, seed=s, hidden_sample=50)["primary"]["confusion"]["tp"]
                 for s in range(2, 12)}
        self.assertGreater(len(other), 1)  # a fresh sample changes the counts
        with self.assertRaises(ValueError):
            self.run_score(text, hidden_sample=1000)

    def test_report_has_no_per_circuit_data(self) -> None:
        text = csv_for(self.ids, self.key, loc=True)
        rep = self.run_score(text, seed=123456789)
        blob = json.dumps(rep) + render(rep)
        for cid in self.ids[:100]:
            self.assertNotIn(cid, blob)
        self.assertNotIn("123456789", blob)
        self.assertNotIn("c000", blob)
        self.assertNotIn("n0", blob.replace("n0.", ""))  # no net names

    def test_rate_limit(self) -> None:
        led = Path(self.td.name) / "ledger.jsonl"
        text = csv_for(self.ids, self.key)
        lim = ledger.Limits(window_s=3600, max_total=2)
        self.run_score(text, ledger_path=led, submitter="u", now=1000.0, seed=1, limits=lim)
        with self.assertRaises(ledger.RateLimitError) as cm:
            self.run_score(text, ledger_path=led, submitter="u", now=1500.0, seed=1, limits=lim)
        self.assertIn("retry in", str(cm.exception))
        self.run_score(text, ledger_path=led, submitter="v", now=1500.0, seed=1, limits=lim)
        self.run_score(text, ledger_path=led, submitter="u", now=5000.0, seed=1, limits=lim)
        with self.assertRaises(ledger.RateLimitError) as cm:
            self.run_score(text, ledger_path=led, submitter="u", now=99999.0, seed=1, limits=lim)
        self.assertIn("limit reached", str(cm.exception))
        # an invalid submission neither scores nor counts
        n = len(led.read_text().splitlines())
        with self.assertRaises(SubmissionError):
            self.run_score("junk", ledger_path=led, submitter="w", now=1.0)
        self.assertEqual(len(led.read_text().splitlines()), n)

    def test_count_matrix_rounded(self) -> None:
        rep = self.run_score(csv_for(self.ids, self.key), seed=9)
        m = rep["bonus_count"]["matrix_claimed_by_true_rounded"]
        self.assertTrue(all(v % 5 == 0 for row in m.values() for v in row.values()))


class ExtractTests(unittest.TestCase):
    def test_fenced_and_plain(self) -> None:
        from lemanruss.score.extract import extract_csv
        csv_text = "# a: b\nid,x\n1,2"
        self.assertEqual(extract_csv(f"### Submission CSV\n\n```text\n{csv_text}\n```\n"),
                         csv_text + "\n")
        self.assertEqual(extract_csv(f"### Submission CSV\n\n{csv_text}\n"), csv_text + "\n")
        self.assertEqual(extract_csv(csv_text), csv_text + "\n")


class BoundsAndRegionTests(unittest.TestCase):
    def test_capacity_values(self) -> None:
        c70 = bounds.count_capacity(100, 70)
        self.assertAlmostEqual(c70, 3.61, delta=0.05)
        self.assertGreater(bounds.count_capacity(100, 100), c70)
        self.assertLess(bounds.count_capacity(100, 50), c70)
        self.assertEqual(bounds.min_queries(100, 40.0), 3)

    def test_region_by_function(self) -> None:
        gold = parse_blif(
            ".model g\n.inputs a b c\n.outputs o\n.names a b x\n11 1\n.names x c o\n10 1\n.end\n")
        # trojan: payload flips o when a&b&c (trigger t), t is not in the golden
        troj = parse_blif(
            ".model r\n.inputs a b c\n.outputs o\n.names a b x\n11 1\n.names a b c t\n000 1\n"
            ".names x c y\n10 1\n.names y t o\n10 1\n01 1\n.end\n")
        wit = [(["a", "b", "c"], ["000"])]
        reg = region_of(gold, troj, wit, ["o"], "s")[0]
        self.assertTrue(reg["victim_found"])
        self.assertIn("t", reg["nets"])
        self.assertIn("o", reg["nets"])
        self.assertNotIn("x", reg["nets"])
        self.assertNotIn("a", reg["nets"])


if __name__ == "__main__":
    unittest.main()
