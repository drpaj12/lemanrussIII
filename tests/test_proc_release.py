"""Tests for lemanruss.htl.proc_release: label scrub round trip, package + verify."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lemanruss.htl.proc_release import (
    _INS_PATTERN,
    ProcCircuitSpec,
    ProcTrojanSpec,
    leak_scan,
    package_proc_pilot2,
    package_proc_release,
    scrub,
    unscrub,
    verify_proc_pilot2,
    verify_proc_release,
)

CLEAN_BLIF = """\
.model top
.inputs a b
.outputs y
.names a b $n1
11 1
.names $n1 y
1 1
.end
"""

INFECTED_BLIF = """\
.model top
.inputs a b
.outputs y
.names a b $n1
11 1
.names a __htl_trigger
1 1
.names $n1 __htl_trigger y
11 1
.end
"""

SAMPLE_PATCH = """\
module m(input clk, output [1:0] q);
  wire __htl_trigger = (a == 32'h2a500293);
  wire [1:0] __htl_pc_mux = __htl_trigger ? 2'b01 : q;
endmodule
"""


class TestScrub(unittest.TestCase):
    def test_removes_htl_tokens(self) -> None:
        scrubbed, rename = scrub(SAMPLE_PATCH)
        self.assertEqual(leak_scan(scrubbed), [])
        self.assertEqual(len(rename), 2)  # __htl_trigger, __htl_pc_mux

    def test_round_trip(self) -> None:
        scrubbed, rename = scrub(SAMPLE_PATCH)
        self.assertEqual(unscrub(scrubbed, rename), SAMPLE_PATCH)

    def test_leak_scan_catches_trojan_word(self) -> None:
        self.assertEqual(leak_scan("a Trojan lives here"), ["trojan"])
        self.assertEqual(leak_scan("clean verilog"), [])


class TestPackageVerify(unittest.TestCase):
    def test_package_and_verify_round_trip(self) -> None:
        # Fix round (2026-11-01): an opaque id, not the trojan id, is the directory/file/
        # manifest-key name (NAME_VOCAB is scanned by `verify_proc_release` now -- see
        # `test_old_trojan_named_layout_fails` below for why this changed).
        spec = ProcTrojanSpec(
            trojan_id="pp0001",
            base="mcu",
            patched_file="single_cycle_core.v",
            patched_text=SAMPLE_PATCH,
            magic_words=[0x2a500293],
            trigger_kind="t-input-pattern",
            payload_kind="p-dos-stuck",
            witness_image={"0blink.vmh": b"@00000000\n13\n"},
        )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "release"
            package_proc_release([spec], out, rareness={"pp0001": {"p": 1}})
            result = verify_proc_release(out)
            self.assertTrue(result.ok, result)

    def test_unscrubbed_patch_is_rejected(self) -> None:
        spec = ProcTrojanSpec(
            trojan_id="pp0002",
            base="mcu",
            patched_file="single_cycle_core.v",
            patched_text=SAMPLE_PATCH,
            magic_words=[1],
            trigger_kind="t-input-pattern",
            payload_kind="p-dos-stuck",
            witness_image={},
        )
        # Simulate a packaging bug: if scrub() were skipped, package_proc_release must still
        # refuse (leak_scan would catch "htl" case-insensitively in the raw text).
        self.assertIn("htl", leak_scan(spec.patched_text))

    def test_old_trojan_named_layout_fails(self) -> None:
        """The pilot1 layout the controller found (2026-11-01): the circuit's directory and the
        manifest key are the trojan id itself (`circuits/proc-mcu-magicword-stall/`), even
        though the file content is leak-scanned clean. `verify_proc_release` must now fail it
        (brief item (d)): this reproduces the leak exactly and checks the new
        `check_name_vocabulary` is what catches it."""
        spec = ProcTrojanSpec(
            trojan_id="proc-mcu-magicword-stall",
            base="mcu",
            patched_file="single_cycle_core.v",
            patched_text=SAMPLE_PATCH,
            magic_words=[0x2a500293],
            trigger_kind="t-input-pattern",
            payload_kind="p-dos-stuck",
            witness_image={"0witness.vmh": b"@00000000\n13\n"},
        )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "release"
            package_proc_release([spec], out,
                                  rareness={"proc-mcu-magicword-stall": {"p": 1}})
            result = verify_proc_release(out)
            self.assertFalse(result.ok, result)
            self.assertFalse(result.name_vocab_ok)
            self.assertTrue(any("magic" in h or "word" in h or "stall" in h
                                 for h in result.name_vocab_hits), result.name_vocab_hits)
            # The leak that pilot1 actually shipped with (content clean, name leaked): the old
            # content-level checks alone must NOT have caught it, or this would not be a new bug.
            self.assertTrue(result.leak_free)
            self.assertTrue(result.labels_present)


class TestNameVocabulary(unittest.TestCase):
    def test_opaque_id_has_no_hits(self) -> None:
        from lemanruss.htl.proc_release import NAME_VOCAB

        for cid in ("pp0001", "pp0002", "pp9999"):
            low = cid.lower()
            self.assertFalse(any(w in low for w in NAME_VOCAB), cid)

    def test_trojan_id_has_hits(self) -> None:
        from lemanruss.htl.proc_release import NAME_VOCAB

        for trojan_id in ("proc-mcu-magicword-stall", "proc-mcu-magicseq3-stall",
                           "proc-dark-magicword-reset"):
            low = trojan_id.lower()
            self.assertTrue(any(w in low for w in NAME_VOCAB), trojan_id)


class TestPilot2(unittest.TestCase):
    def test_round_trip(self) -> None:
        clean = ProcCircuitSpec(
            trojan_id="pp-trojan-1", base="mcu", role="clean", identity_text=CLEAN_BLIF,
        )
        infected = ProcCircuitSpec(
            trojan_id="pp-trojan-1", base="mcu", role="infected", identity_text=INFECTED_BLIF,
            magic_words=[0x2a500293], trigger_kind="t-input-pattern",
            payload_kind="p-dos-stuck", patched_text=SAMPLE_PATCH,
            patched_file="single_cycle_core.v",
            witness_image={"0blink.vmh": b"@00000000\n13\n"},
        )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "release"
            info = package_proc_pilot2(
                [clean, infected], out, rareness={"pp-trojan-1": {"p": 1}},
                restructure_forms_attempted={},
            )
            self.assertEqual(info["circuits"], 2)
            self.assertEqual(info["clean"], 1)
            self.assertEqual(info["infected"], 1)
            result = verify_proc_pilot2(out)
            self.assertTrue(result.ok, result)
            # No circuit id, file name or manifest key is the trojan id (brief item (a)).
            for p in (out / "circuits").iterdir():
                self.assertNotIn("trojan", p.name)
            manifest = (out / "manifest.json").read_text()
            self.assertNotIn("pp-trojan-1", manifest)


class TestInsPattern(unittest.TestCase):
    def test_matches_pilot1_scrub_names(self) -> None:
        self.assertTrue(_INS_PATTERN.search("_ins0"))
        self.assertTrue(_INS_PATTERN.search("foo _ins12 bar"))

    def test_does_not_match_ordinary_net_names(self) -> None:
        self.assertFalse(_INS_PATTERN.search("$n15"))
        self.assertFalse(_INS_PATTERN.search("flush_fetch_receive"))
        self.assertFalse(_INS_PATTERN.search("instance_0"))


if __name__ == "__main__":
    unittest.main()
