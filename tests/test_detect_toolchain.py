"""Regression (Proc detectors, round 11): rare, graphlet-b and gnn-a scored every circuit NaN
because Odin III was not importable in the isolated child. The failure was swallowed as 'not
scored' and cached, then surfaced as 'validation fold has no clean circuit' / IndexError."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lemanruss.detect import isolated, metrics


def _odin3_installed() -> bool:
    """True when odin3 imports without PYTHONPATH (pip -e install): the test cannot hide it."""
    import subprocess
    import sys
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run([sys.executable, "-c", "import odin3"], env=env,
                          capture_output=True).returncode == 0


class ToolchainFaultTest(unittest.TestCase):
    @unittest.skipIf(_odin3_installed(), "odin3 is pip-installed here, cannot hide it")
    def test_missing_odin3_is_an_error_not_a_nan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            blif = Path(td) / "c.blif"
            blif.write_text(".model m\n.end\n", encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
            with mock.patch.dict(os.environ, env, clear=True), \
                    self.assertRaises(isolated.ToolchainError):
                isolated.isolated("scoap", blif)

    def test_unknown_odin3_fault_other_than_import_is_not_scored(self) -> None:
        # a crash after Odin III loaded (exit 1) stays a per-circuit 'not scored'
        import subprocess
        err = subprocess.CalledProcessError(1, "x", stderr=b"boom")
        with mock.patch("subprocess.run", side_effect=err):
            self.assertIsNone(isolated.isolated("scoap", Path("nonexistent")))


class ValThresholdTest(unittest.TestCase):
    def test_all_nan_clean_names_the_cause(self) -> None:
        nan = float("nan")
        with self.assertRaisesRegex(ValueError, "2 of 3 validation circuits scored NaN"):
            metrics.val_threshold([nan, nan, 1.0], [False, False, True])

    def test_ignores_nan_and_infected(self) -> None:
        self.assertGreaterEqual(
            metrics.val_threshold([float("nan"), 0.1, 0.2, 5.0], [False, False, False, True]), 0.1)


if __name__ == "__main__":
    unittest.main()


class ProcTwinReferenceTest(unittest.TestCase):
    """Seeker-Proc names the twin of an infected circuit `<id>-twin`, which is not a released
    file; Method B then got the infected circuit as its own reference (drift 0 for all)."""

    def test_reference_is_the_answer_key_twin(self) -> None:
        import gzip
        import json

        from lemanruss.detect.data import Release
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for d in ("circuits", "answer_key/twins"):
                (root / d).mkdir(parents=True)
            for cid in ("pr0001", "pr0002"):
                (root / "circuits" / f"{cid}.blif.gz").write_bytes(gzip.compress(b".model m\n"))
            (root / "answer_key/twins/pr0002.blif.gz").write_bytes(gzip.compress(b".model t\n"))
            (root / "manifest.json").write_text(json.dumps({"circuits": [
                {"id": "pr0001", "file": "circuits/pr0001.blif.gz"},
                {"id": "pr0002", "file": "circuits/pr0002.blif.gz"}]}))
            prov = {
                "pr0001": {"base": "b", "source": "pr0001", "restructuring": "gates",
                           "role": "clean", "clean_twin": "pr0001", "insert": {}},
                "pr0002": {"base": "b", "source": "pr0002", "restructuring": "gates",
                           "role": "infected", "clean_twin": "pr0002-twin",
                           "insert": {"n_trojans": 1}}}
            (root / "answer_key/provenance.json").write_text(json.dumps(prov))
            recs = {r.id: r for r in Release(root, "Proc").records}
            self.assertEqual(recs["pr0001"].reference, recs["pr0001"].path)
            self.assertEqual(recs["pr0002"].reference, root / "answer_key/twins/pr0002.blif.gz")
