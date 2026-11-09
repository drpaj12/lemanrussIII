# Seeker-Seq rc8 results: OpenCores bases (2026-11-08)

rc8 = the 36 rc7 bases (circuits byte-identical, sha256 checked) + OpenCores ca_prng and i2c.
Candidates (12, two waves), licences and the reason for each exclusion: `releases/seeker-seq-v2.0-rc8/DATASHEET.md`,
section "OpenCores candidates". Rule (Peter 2026-11-08): des left out; only licences that clearly permit
redistribution of derived netlists without copyleft terms are included.

Build: Odin III rel-v150 for the OpenCores bases, rc7 construction and gates. ca_prng 524 s, i2c 668 s.
Shortfall: i2c K6 raised `bitsim: combinational loop or undriven net` and the set was dropped (not padded);
i2c G lost one proposal with no witness.
`lemanruss verify`: PASS (11005 circuits, 4192 infected, 6994 Trojans; forced-off, obfuscation and clean
equivalence all equivalent; f_distinct, g_style, h_provenance clean). Archive: F: 2026-11-08/seeker-seq-v2.0-rc8.
