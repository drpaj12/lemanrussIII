"""Buffer-free silicon rule (lemanruss.htl.obfuscate.strip_buffers)."""

from __future__ import annotations

import unittest

from lemanruss.htl.obfuscate import parse, strip_buffers


def cells(text: str) -> list[str]:
    return [b[0] for b in parse(text)[2]]


class StripBuffersTest(unittest.TestCase):
    def test_internal_buffer_is_merged(self) -> None:
        t = (".model t\n.inputs a b\n.outputs y\n.names a b n1\n11 1\n.names n1 n2\n1 1\n"
             ".names n2 y\n0 1\n.end\n")
        self.assertEqual(cells(strip_buffers(t)), [".names a b n1", ".names n1 y"])

    def test_buffer_to_output_renames_the_driver_net(self) -> None:
        t = ".model t\n.inputs a b\n.outputs y\n.names a b n1\n11 1\n.names n1 y\n1 1\n.end\n"
        self.assertEqual(cells(strip_buffers(t)), [".names a b y"])

    def test_port_to_port_buffer_stays(self) -> None:
        t = ".model t\n.inputs a\n.outputs y z\n.names a n1\n0 1\n.names n1 y\n1 1\n" \
            ".names y z\n1 1\n.end\n"
        out = cells(strip_buffers(t))
        self.assertIn(".names y z", out)
        self.assertEqual(len(out), 2)

    def test_feedthrough_stays_and_inverter_is_not_a_buffer(self) -> None:
        t = ".model t\n.inputs a b\n.outputs y z\n.names a y\n1 1\n.names b z\n0 1\n.end\n"
        self.assertEqual(sorted(cells(strip_buffers(t))), [".names a y", ".names b z"])

    def test_latch_d_buffer_and_chain(self) -> None:
        t = (".model t\n.inputs a clk\n.outputs q\n.names a n1\n1 1\n.names n1 n2\n1 1\n"
             ".latch n2 q re clk 2\n.end\n")
        out = strip_buffers(t)
        self.assertIn(".latch a q re clk 2", out)


if __name__ == "__main__":
    unittest.main()
