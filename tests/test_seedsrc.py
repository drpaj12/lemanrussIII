"""Release seeds come from a private source, never a default."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lemanruss.seedsrc import ENV_FILE, ENV_SEED, release_seed


class SeedSourceTests(unittest.TestCase):
    def test_explicit_wins(self) -> None:
        with mock.patch.dict(os.environ, {ENV_SEED: "9"}):
            self.assertEqual(release_seed(3), 3)

    def test_env(self) -> None:
        with mock.patch.dict(os.environ, {ENV_SEED: "11"}):
            self.assertEqual(release_seed(None), 11)

    def test_file_by_name_then_default(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "s.json"
            f.write_text(json.dumps({"Seeker-Comb": 5, "default": 6}), encoding="utf-8")
            env = {ENV_FILE: str(f)}
            with mock.patch.dict(os.environ, env):
                os.environ.pop(ENV_SEED, None)
                self.assertEqual(release_seed(None, "Seeker-Comb"), 5)
                self.assertEqual(release_seed(None, "Seeker-Seq"), 6)

    def test_no_source_stops(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_SEED, None)
            os.environ.pop(ENV_FILE, None)
            with self.assertRaises(SystemExit):
                release_seed(None)


if __name__ == "__main__":
    unittest.main()
