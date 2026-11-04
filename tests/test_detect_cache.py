"""The feature cache keys on the circuit file's own content hash, not its id (Peter 2026-11-02):
an id is assigned per release/style and is not unique across them."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from lemanruss.detect.data import CircuitFile
from lemanruss.detect.features import cache_path, cached, sha256_of


class Sha256CacheKeyTest(unittest.TestCase):
    def test_same_id_different_content_gets_different_cache_entries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "rel-a" / "circuits" / "ss0001.blif.gz"
            p2 = Path(td) / "rel-b" / "circuits" / "ss0001.blif.gz"
            p1.parent.mkdir(parents=True)
            p2.parent.mkdir(parents=True)
            p1.write_bytes(b"circuit one content")
            p2.write_bytes(b"circuit two, a different circuit entirely")
            cf1 = CircuitFile("ss0001", p1)
            cf2 = CircuitFile("ss0001", p2)
            self.assertEqual(cf1.id, cf2.id)
            path1, path2 = cache_path("nl", cf1), cache_path("nl", cf2)
            self.assertNotEqual(path1, path2)

    def test_same_content_different_id_shares_one_cache_entry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "rel-a" / "circuits" / "ss0001.blif.gz"
            p2 = Path(td) / "rel-b" / "circuits" / "ss0099.blif.gz"
            p1.parent.mkdir(parents=True)
            p2.parent.mkdir(parents=True)
            p1.write_bytes(b"byte-identical circuit")
            p2.write_bytes(b"byte-identical circuit")
            cf1 = CircuitFile("ss0001", p1)
            cf2 = CircuitFile("ss0099", p2)
            self.assertEqual(cache_path("nl", cf1), cache_path("nl", cf2))

    def test_cached_round_trips_through_the_sha256_path(self) -> None:
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as feat:
            os.environ["LEMANRUSS_FEAT"] = feat
            p = Path(td) / "rel" / "circuits" / "ss0001.blif.gz"
            p.parent.mkdir(parents=True)
            p.write_bytes(b"some circuit text")
            cf = CircuitFile("ss0001", p)
            calls = []

            def fn(path: Path) -> str:
                calls.append(path)
                return path.read_text()

            first = cached("nl", cf, fn)
            second = cached("nl", cf, fn)
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 1)  # second call was a cache hit
            self.assertTrue(cache_path("nl", cf).name.startswith(sha256_of(p)[:8]))
            del os.environ["LEMANRUSS_FEAT"]


if __name__ == "__main__":
    unittest.main()
