# seeker-si-v2.0-rc1 datasheet

Family: Seeker-Si (`family: silicon`). Version 2.0-rc1 (2026-11-06). Produced by Leman Russ III (Yggdrasil III). Defensive hardware-Trojan detection research; the circuits are Trojans to detect, nothing here is meant to be deployed.

**This is a NEW set with its own benchmarks. It is not the same benchmarks as Seeker comb/seq/proc; do not compare per base, per form or by AUROC with those sets.**

## What it is

100 circuits, each in two files: `circuits/<id>.v` (structural Verilog of `sky130_fd_sc_hd__*_1` standard cells, flip-flop `dfxtp_1`, constants `conb_1`, one module `top`) and `circuits/<id>.blif` (the same netlist as gates-as-names BLIF, for checkers). One form only (the library is the form). Ids are opaque and shuffled across bases. A detector is not told whether a circuit is infected. Labels, Trojan catalogue, witnesses, ABC scripts, `pre` circuits and the build ids are in a separate answer key that is not published.

| base | clean | infected | Trojans |
|---|---|---|---|
| mmuart | 12 | 22 | 34 |
| simple_spi | 11 | 22 | 34 |
| verilog_cordic_core | 11 | 22 | 35 |
| total | 34 | 66 | 103 |

The number of infected circuits is drawn once, uniformly from 10 to 70 (drawn: 66, spread evenly over the bases); each infected circuit carries 1 to 3 Trojans (P = 0.5, 0.3, 0.2).

## Bases

OpenCores designs mapped to sky130_fd_sc_hd by Odin III's silicon flow (`flow/gates.blif` of the flow ladder, equivalence proved by the flow). i2c, wb_lcd, sha3_low and des were considered and are not in the set (reasons in `docs/results-si-rc1.md`).

## Trojans

Small trigger plus payload built from real standard cells on existing nets of the clean cell netlist: counter trigger (`dfxtp_1` plus half adders) or FSM pattern trigger (a few `dfxtp_1` plus a comparator tree); payloads: victim forced to its minority value, or output flip (upper or lower half of the output list). Every trigger is sequential, so **an infected circuit has more flip-flops than its base; the flip-flop count alone separates the labels inside each base** (recorded per circuit in the answer key; the `ffcount` control reaches AUROC 1.0 per base). Rare AND-tree (combinational) triggers were not drawn.

## Variety and obfuscation

Each circuit has its own random ABC script (`strash`, 1 to 8 restructuring operations, `map`), re-mapped by Odin III to the same sky130 library (`abc --gates sky130hd`, `dfflibmap sky130hd`), then text-finalized (ports and cells shuffled, every net and instance renamed `n<index>`, no comment or attribute). Port and clock names are the design's interface and stay.

## Gates every circuit passed

Format (one module, no duplicate ports, no driven input, no multi-driven net, Odin III `read_blif`); equivalence to its source by `regmatch-cec` (all 100; `scorr-cec` and `dsec` were the fallbacks and were never needed); infected `pre` with all triggers forced inactive equivalent to the base; every Trojan fires on its own witness replayed on the finished netlist; Verilog written and read back to the identical network; the design's own testbench run on the cell netlist with the sky130 models (every flip-flop starting at 0) prints its PASS line and the output trace is identical to the clean circuit's. Distinct structure per base.

## Selection bias

A draw is rejected when the design's own testbench makes the Trojan change the output trace (silence rule). 94 infected draws were rejected for this reason over the 3 bases, so the infected circuits lean to Trojans the testbench does not reach. Counts per base and trigger kind: `docs/results-si-rc1.md`.
