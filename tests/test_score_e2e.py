"""End to end on Comb rc4 and Seq rc5 with a size-only detector (gate count of the circuit file).

Skipped unless the releases (read only) and the regions files built by `lemanruss regions` exist
under ~/odin3-ws/work (htl-rel, lemanruss-score-run).
"""

from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from lemanruss.score.key import load
from lemanruss.score.scorer import render, score
from lemanruss.score.subsets import build_subsets

WS = Path.home() / "odin3-ws" / "work"
CASES = [("comb", WS / "htl-rel/rc4/seeker-comb-v2.0-rc4", "Comb-K4"),
         ("seq", WS / "htl-rel/rc5/seeker-seq-v2.0-rc5", "Seq-K4")]


def gate_count(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return sum(1 for ln in fh if ln.startswith((".names", ".latch")))


class EndToEnd(unittest.TestCase):
    def run_case(self, tag: str, rel: Path, name: str) -> None:
        regions = WS / "lemanruss-score-run" / tag / "regions.json"
        if not (rel / "answer_key" / "labels.json").exists() or not regions.exists():
            self.skipTest("release or regions not present")
        with tempfile.TemporaryDirectory() as td:
            kd = Path(td)
            for f in ("labels", "sets", "trojans"):
                (kd / f"{f}.json").symlink_to(rel / "answer_key" / f"{f}.json")
            (kd / "regions.json").symlink_to(regions)
            key = load(kd)
            subs = build_subsets(key, rel.name, 0)["subsets"]
            ids = subs[name]["ids"]
            self.assertEqual(len(ids), 100)
            size = {c: gate_count(rel / "circuits" / f"{c}.blif.gz") for c in ids}
            mid = sorted(size.values())[len(ids) // 2]
            rows = [f"{c},{int(size[c] > mid)},{size[c]},," for c in ids]
            text = (f"# seeker-release: {rel.name}\n# subset: {name}\n# detector: size-only\n"
                    "# team: test\n" + "id,infected,score,count,locations\n" + "\n".join(rows))
            rep = score(text, key, rel.name, {k: v["ids"] for k, v in subs.items()}, seed=1)
            auroc = rep["primary"]["auroc"]
            self.assertIsNotNone(auroc)
            self.assertTrue(0.3 <= auroc <= 0.9, auroc)  # size-only: weak but not random noise
            self.assertEqual(rep["scored_circuits"], 70)
            blob = json.dumps(rep) + render(rep)
            self.assertFalse(any(c in blob for c in ids))
            self.assertTrue(rep["baselines"])
            # location oracle: one region net per true Trojan must hit every trial
            oracle = []
            for c in ids:
                regs = key.regions.get(c)
                nets = ";".join(t["nets"][0] for t in regs["trojans"][:10] if t["nets"]) \
                    if regs else ""
                oracle.append(f"{c},{key.infected(c)},{key.infected(c)},{key.n_trojans(c)},{nets}")
            text2 = text.split("id,infected")[0] + "id,infected,score,count,locations\n" \
                + "\n".join(oracle)
            rep2 = score(text2, key, rel.name, {k: v["ids"] for k, v in subs.items()}, seed=1)
            self.assertEqual(rep2["primary"]["auroc"], 1.0)
            loc = rep2["bonus_location"]
            self.assertFalse(loc.get("suppressed"), loc)
            self.assertGreaterEqual(loc["hit_rate"], 0.95)  # a Trojan with an empty region misses
            print(f"{tag}: size-only AUROC {auroc}, CI {rep['primary']['auroc_ci95']}, "
                  f"oracle location {loc}")

    def test_comb_rc4(self) -> None:
        self.run_case(*CASES[0])

    def test_seq_rc5(self) -> None:
        self.run_case(*CASES[1])


if __name__ == "__main__":
    unittest.main()
