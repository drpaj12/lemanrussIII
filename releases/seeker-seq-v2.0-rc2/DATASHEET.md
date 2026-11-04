# seeker-seq-v2.0-rc2 datasheet

Family: Seeker-Seq. Version 2.0-rc2 (release candidate; the final v2.0 follows after later rounds add the remaining bases and Seeker-Proc). Produced by Leman Russ III (Yggdrasil III).

Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.

## Lineage

v1 = Caroline van Neste's master's thesis (in progress; no unpublished results are cited). v2.0: sequential bases (ISCAS-89, ITC-99 and VTR sequential designs), counter and FSM-pattern triggers, multi-cycle rareness.

## Contents

- circuits: 4389 in `circuits/<id>.blif.gz` (gzip, zero timestamp), 912 clean and 3477 infected, opaque ids.
- bases: 48; each has one clean circuit and its infected circuits.
- restructurings: identity plus 18 ABC restructurings of every circuit, 19 forms, every one checked ABC-equivalent to its source (3 unproven by timeout: ss1719 (lut6mfs of ss0145), ss1736 (lut6 of ss0146), ss1840 (compress2 of ss0164)).
- variants that could not be built: 105 (`answer_key/failures.json`; a band no rare net could reach).
- answer key: `answer_key/` (labels, provenance, renames, rareness, and for the infected identity circuits `edit_events/<id>.edit.blif.gz`: the circuit written with Odin III edit events, `write_blif --edit-tags`, which mark every inserted or moved cell); a detector must not read it. Clean circuits carry no label and infected circuits carry no label.

Circuits per base (all forms):

b01 76, b02 76, b03 95, b04 114, b05 38, b06 95, b07 57, b08 76, b09 114, b10 133, b11 95, b12 38, b13 76, b14 57, b15 76, b17 38, b18 19, b20 76, b21 38, b22 57, diffeq1 133, diffeq2 19, mkPktMerge 38, mkSMAdapter4B 38, s1196 133, s1238 133, s1423 133, s1488 133, s1494 133, s208 114, s27 114, s298 133, s344 133, s349 133, s382 76, s386 133, s400 95, s420 95, s444 76, s510 114, s526 95, s5378 114, s641 114, s713 114, s820 95, s832 133, s953 114, sha 57

## Rareness bands

Seeker-Seq: counter (time bomb) and FSM-pattern triggers, three speed bands each (fast, mid, slow) defined by P(trigger high within 1024 cycles): fast 0.5-1, mid 0.05-0.5, slow 0.003-0.05. P(fire within N) for N = 16, 64, 256, 1024 is in `answer_key/rareness.json`. Odin III's sequential SCOAP underestimates time-bomb rareness, so P(fire within N) is the primary measure.

| N cycles | circuits | with P(fire<=N)>0 | min | median | max |
|---|---|---|---|---|---|
| 16 | 183 | 63 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 64 | 183 | 88 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 256 | 183 | 109 | 0.00e+00 | 3.91e-03 | 1.00e+00 |
| 1024 | 183 | 183 | 1.46e-03 | 2.85e-01 | 1.00e+00 |

## Built but not released

- b19: its 638552-gate netlist builds (no trigger band reachable, so no infected circuit) but ABC times out (300 s) on every one of the 18 restructurings, so it has no restructured forms
- boundtop: Odin III scoap refuses it (combinational loop through its level-sensitive latches), so no infected circuit; its 18 restructurings cannot be equivalence-checked (equiv-check does not support level-sensitive latches)
- ch_intrinsics: level-sensitive latches (ah, al): the bit-parallel simulator disagrees with Odin III (5566 mismatching signal comparisons on the clean base) and equiv-check refuses it (unsupported latch type), so neither its infected circuit nor its restructurings can be verified

## Restructurings

identity, strash, balance, rewrite, refactor, resyn, resyn2, compress2, dc2, dc2x2, lut4, lut6, lut6mfs, resyn2a, resyn3, resyn2rs, compress, resub, lut5 (ABC standard scripts and LUT mappings; Seeker1's own list of 18 was not read, so this is the count, not the same list).

Equivalence: all but 3 restructured circuit(s) were proven equivalent to their source by ABC; the unproven one: ss1719 (lut6mfs of ss0145), ss1736 (lut6 of ss0146), ss1840 (compress2 of ss0164) (ABC equivalence timeout, 600 s; it is not known to be non-equivalent).

## Bases and licences

- ISCAS-89 (23: s1196, s1238, s1423, s1488, s1494, s208, s27, s298, s344, s349, s382, s386, s400, s420, s444, s510, s526, s5378, s641, s713, s820, s832, s953): licence unread (the ISCAS licence has not been read).
- ITC-99 (20: b01 to b22): not in Mimir `licences.toml`. Source: ccsl-uaegean/ITC99-RTL-Verilog, a vhd2vl conversion of the Politecnico di Torino ITC'99 VHDL; the repository's LICENSE says GPL-3.0 (spec section 8); the licence of the original VHDL has not been read.
- VTR Verilog `diffeq1`: none-stated (Mimir rule vtr-other-verilog).
- VTR Verilog `diffeq2`: none-stated (the header has a no-warranty disclaimer only) (Mimir rule vtr-diffeq2).
- VTR Verilog `mkPktMerge`: none-stated for the file as a whole; its embedded generic_fifos block carries an opencores permissive notice (Mimir rule vtr-mkPktMerge).
- VTR Verilog `mkSMAdapter4B`: none-stated for the file as a whole; its embedded generic_fifos block carries an opencores permissive notice (Mimir rule vtr-mkSMAdapter4B).
- VTR Verilog `sha`: opencores permissive notice: may be used and distributed without restriction provided the copyright statement is not removed (Mimir rule vtr-sha).
- The infected circuits are derivatives of these bases; each base's own licence applies to its derivative.

## Tools

- Odin III (build of the circuits): 42394c3d (libodin3 build rel-main); checkout used for `lemanruss verify`: v1.2.0-24-g40ea7b9d (tools and Python plugin; library built at 42394c3d).
- ABC: UC Berkeley, ABC 1.01 (compiled Oct 21 2026 17:22:51).

## Names

Every net the inserter added is renamed to a neutral internal name in the style of the clean circuit (spec section 10.2); `answer_key/renames.json` maps them back.

## Fetch and check

Unpack the circuits and answer-key archives into one directory, then `sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.
