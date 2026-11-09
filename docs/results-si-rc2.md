# Seeker-Si rc2 results (2026-11-08)

Purpose: Leman Russ III RQ1.1 (which structures do not belong to the claimed design) at the standard-cell
level, with the silicon form built exactly like the other forms (spec `docs/specs/2026-11-07-seeker-si-rc2.md`).
Measure: gated releases scored by the nine detectors at levels 1 to 3, flip-flop-count control at chance
within base, place-and-route of a stratified subset. Reported per the CAD convention: W/L/T and strict label.
No seeds, magic words or per-circuit labels appear here. Private sets and answer keys: `/mnt/f/yggdrasil-archive/2026-11-07/seeker-si-rc2/` only.

## 1. What was built

| family | bases | circuits | infected | Trojans | failed proposals (redrawn) |
|---|---|---|---|---|---|
| Comb silicon | 27 | 1,955 | 905 | 1,524 | 301: 182 cut-stitch host mapping errors, 70 insert errors, 23 equivalence-tool errors (misex3), 16 short supply, 4 goldens that already fail to parse |
| Seq silicon | 36 | 3,597 | 1,219 | 2,031 | 279: 255 insert errors, 9 equivalence-tool errors, 11 missing witnesses, 2 short supply |
| Proc silicon | 4 | 133 | 52 | see key | 0 rejected by the silicon-netlist gates |

- `labels.json` has the same ids as the manifest in each release and its infected count equals the infected
  circuits (905, 1,219, 52; provenance agrees).
- Comb bases with fewer than 100 circuits: C17 18, ve_Prob064_vector3 6, six tiny VerilogEval bases 2 each
  (one golden plus one clean: their structures repeat or their infected draws find no site; rc5 also had
  2 to 17 circuits for them). Four tiny VerilogEval bases whose golden Odin III cannot parse are dropped
  from the Comb release (`dropped_bases` in the tree manifest). Seq: s208 95, s27 68.
- Verification (`lemanruss verify`): Comb and Seq pass every check (integrity, separation, leak, rareness,
  function with equivalence of all infected and 1,023 / 2,342 clean circuits and Odin III replay of 1,184 / 967
  witnesses, distinctness, style, provenance). Proc: release check passes (133 files, no leaks, flip-flops equal).
- Odin III `build/rel-main3`, ABC `a3001b72edc5`, library `lib/sky130hd.o3lib`, no Yosys.

## 2. Gates specific to the silicon form

- Buffer-free rule (spec 3a): the first Seq build failed the style check on buffer share (z = 9). Buffers came from
  cut-and-stitch (whole-circuit mapping gave none in 12 of 12 trials); the rule strips non-inverting buffers by
  merging nets after every silicon mapping step and after stitching, for all families and labels. After the
  change Comb and Seq pass `g_style`. Proc keeps only port-joining buffers (picorv32 103 per circuit in both
  labels, mcu and mips_16 none, darkriscv one feedthrough per circuit and 0.57 / 0.37 port-to-port per circuit clean / infected).
- Proc silicon-netlist gates: every Trojan fires and the neutral program and neutral shift stay silent on the
  silicon BLIF itself (Odin III sim, clean twin against infected twin); 0 circuits rejected and redrawn.
- Equivalence to the source: strict for mips_16 (33 of 33), mcu (34 of 34), picorv32 (33 of 33); darkriscv 33 of 33 needed the
  init-reset reference (every initial value of that circuit's own source reset, clean and infected twins alike) because
  `dfxtp_1` has no initial value. darkriscv source: 815 flip-flops with initial value 0, 22 with 1, 1,195 unknown.
  Recorded per base in `answer_key/build_meta.json`.
- Flip-flop control, within base (AUROC of the flip-flop count with the label): exactly 0.500 in all 21 scored Comb bases (all with
  zero flip-flops, so vacuous), all 36 Seq bases and all 4 Proc bases (constant count per base).

### darkriscv at power-on (from the source)

The silicon darkriscv can start in a different state from the source at power-on. In the source, `darksocv.v`
declares `IRES = -1` and `darkriscv.v` declares `XRES = 1`, so simulation starts with reset asserted; the 22
flip-flops with initial value 1 (whose names the lowered netlist does not keep) are consistent with these reset
registers and `RAM_CTL0`. `dfxtp_1` has no initial value, so on silicon these power up unknown and the core is not
guaranteed to be in reset. Only the external reset pin recovers it: asserting `XRES` reloads `IRES`, which raises `RES`,
and `XRES <= RES` then clears the CSR registers (MTVEC, MEPC, MIE, MCAUSE, MSTATUS, MSCRATCH and the supervisor set), writes zero
into the register file, loads the program counter with `__RESETPC__` (32'd0) and starts the pipeline flush. State
that has an initialiser of 0 but no reset term (for example the cycle and instruction counters `CSRCLK` and `CSRINS`
that only count while not in reset) is not cleared by reset and starts unknown on silicon; I did not check every one of the
815 flip-flops with initial value 0. The equivalence proof for darkriscv holds from the common all-zero state only,
and the fire and silence gates on the silicon netlist start from zero.

## 3. Detector settings

Proc: `procrun`, 50 epochs, no training cap, seeds 0, 1, 2, leave-one-base-out on four cores, range check (as rc3).
Comb and Seq: the PR #3 localisation settings: 12 epochs, batch 32, training cap 1,500; `locrun` (base split, five
folds, seed 0) for the localising detectors, `detect.run --splits base --seeds 0` for the others.

## 4. Detector results

### Proc (silicon, four cores): see `tex/si_rc2_proc_levels.tex`

Only `graphlet-b` (reference-assisted) is ABOVE chance (AUROC 1.000; level 3 W/L/T 2/0/0 on the two scored cores).
All eight others are INCONCLUSIVE at levels 1 to 3. With the range check only 67 circuits are scored (66 out of range), as in rc3.

### Seq (silicon, base split)

Level 3: `gnn-a` ABOVE (0.648 against chance 0.631, W/L/T 11/2/23); `gnn-a-nosc`, `gnn-yasaei`, `rare` INCONCLUSIVE.
Base-split AUROC [95% CI]: size 0.648 [0.602, 0.684], classhist 0.669 [0.612, 0.733], graphlet-b 0.565 [0.510, 0.623] (all ABOVE),
ffcount 0.455 [0.403, 0.515], sanity 0.478 [0.433, 0.543] (INCONCLUSIVE).

### Comb (silicon, base split)

All four localising detectors are INCONCLUSIVE at level 3; `gnn-a` is ABOVE at levels 1 and 2 (0.544 against chance 0.529;
0.515 against 0.502).

### Seq silicon against the other Seq rc7 forms (rc7 values from the paper table, not rerun)

See `tex/si_rc2_seq_vs_rc7.tex`. `size` and `classhist` are within error of the other forms (0.648 vs 0.593 [0.562, 0.650];
0.669 vs 0.660 [0.620, 0.716]). Within base, the cell count separates infected from clean equally in all four forms: AUROC 0.763
(silicon), 0.778 (gates), 0.759 (lut4), 0.738 (lut6); infected circuits hold 9.9 %, 6.6 %, 9.9 % and 10.5 % more cells.
The Trojan's own trigger and payload cells cause it (cell types that grow in silicon: a21oi +2.8, nand2 +2.3, xor2 +1.8,
o21ai +1.4, inv +1.0 per circuit; no single type above within-base AUROC 0.6; area gives the same signal as cell count).
That is a result, the signal the `size` detector measures, not a build artefact. `gnn-a` is clearly higher on silicon (0.637 vs 0.482 [0.440, 0.535]),
within 0.011 of the size-only control; the likely cause is that the network learns cell count here, not tested further.

### Proc within-base size and buffers (controller option 1)

| base | infected / clean | AUROC buffers | AUROC total cells | permutation p (cells) |
|---|---|---|---|---|
| darkriscv | 19 / 14 | 0.398 | 0.323 | 0.088 |
| mcu | 11 / 23 | 0.500 | 0.411 | 0.429 |
| mips_16 | 11 / 22 | 0.500 | 0.690 | 0.080 |
| picorv32 | 11 / 22 | 0.500 | 0.634 | 0.217 |

Cell count differs because infected circuits contain the Trojan's own cells; none is significant, and the rc3 forms show
the same range (cell-count AUROC within base 0.35 to 0.75, lut4 p = 0.026 to 0.033 on three bases). The Proc style check passes
(51 tests, none flagged; best single feature 0.657, se 0.05, under the bound after the standard error).

## 5. Place and route (OpenROAD, `tools/silicon/openroad_flow.tcl`, utilisation 25 %)

Subset: about 10 % of each Comb and Seq base (label-stratified, smallest first; Comb 201, Seq 357 circuits), 30 % of each
Proc base (41 circuits, every base). Wall cap 60 min per circuit; a flow error gets one retry at 18 % utilisation; a cap-out is
recorded as a flow limit with its cell count and not retried (retries after cap-outs never succeeded in the trials). Deviation from
the controller's one-retry rule, logged. A 300 s silent-log stall rule used at first killed a 5,758-cell run that finishes in
985 s without it (the other three stalled circuits tried hit the 60 min cap), so it was switched off and every run it affected was redone.

Bias of the routed subset: the cap-outs are not a function of size alone. In Comb, 8 of 71 circuits above 1,000 cells routed (hangs at `DRT-0179`), and 0 of 20 above 2,000; in Seq, 9 of 30 circuits of 1,000 to 1,999 cells (all of 977 to 1,077 cells) and none of the 10 circuits above 5,000 cells hit the cap; in Proc 13 of 31 cores above 5,000 cells (picorv32 and darkriscv sizes) hit the cap and all 10 mips_16 circuits routed. A routed-only reading therefore leans to small Comb circuits; read the table by family and bucket.

| family | cells | circuits | routed (0 DRC violations unless noted) | flow limit: cap-out | flow limit: other error | median wall s (routed) |
|---|---|---|---|---|---|---|
| comb | <100 | 17 | 9 (DRC 0) | 0 | 8 | 4 |
| comb | 100-499 | 75 | 74 (DRC 0) | 0 | 1 | 14 |
| comb | 500-999 | 38 | 36 (DRC 0) | 2 | 0 | 80 |
| comb | 1000-1999 | 51 | 8 (DRC 0) | 42 | 1 | 2345 |
| comb | 2000-4999 | 20 | 0 (DRC 0) | 20 | 0 | -- |
| seq | <100 | 93 | 93 (DRC 0) | 0 | 0 | 4 |
| seq | 100-499 | 204 | 204 (DRC 0) | 0 | 0 | 18 |
| seq | 500-999 | 20 | 19 (DRC 0) | 1 | 0 | 53 |
| seq | 1000-1999 | 30 | 21 (DRC 0) | 9 | 0 | 171 |
| seq | >=5000 | 10 | 10 (DRC 0) | 0 | 0 | 1164 |
| proc | 1000-1999 | 10 | 10 (DRC 0) | 0 | 0 | 251 |
| proc | >=5000 | 31 | 18 (DRC 0) | 13 | 0 | 2883 |

Flow limits (cell counts of every circuit that did not route):

- comb: 74 flow limits, cell counts [5, 8, 16, 32, 32, 32, 33, 35, 100, 887, 929, 1005, 1027, 1048, 1078, 1103, 1115, 1121, 1132, 1132, 1133, 1134, 1138, 1144, 1196, 1198, 1215, 1232, 1247, 1249, 1252, 1253, 1254, 1259, 1295, 1305, 1308, 1321, 1346, 1359, 1388, 1406, 1408, 1408, 1412, 1437, 1449, 1452, 1493, 1524, 1533, 1549, 1564, 1567, 2457, 2481, 2499, 2630, 2760, 2795, 2917, 2932, 3010, 3017, 3303, 3371, 3441, 3487, 3501, 3542, 3556, 3761, 3813, 3859]
- seq: 10 flow limits, cell counts [977, 1025, 1034, 1048, 1049, 1057, 1057, 1065, 1073, 1077]
- proc: 13 flow limits, cell counts [9416, 9863, 10083, 10967, 15043, 15121, 15175, 15303, 15387, 15496, 15521, 15542, 15628]

Diagnosis of the stalls (one Comb circuit, 1,078 cells, 28 IO): IO density does not separate stalled from routed circuits; a larger die
(utilisation 10), looser pin spacing, default global-route iterations and a global-routing layer adjustment all still hang at detailed routing
(`DRT-0179 Init gr pin query`); routing from metal 2 upward fails (GRT-0118 / DRT-0155). No flow parameter was changed.
Of the Comb circuits under 100 cells, 8 of 17 fail earlier, in global placement (`GPL-0307` divergence); the flow
handles only designs of one cell or none specially.

## 6. Cost

Mapping per circuit 0.1 to 11 s (Comb, Seq about 0.4 to 1.7 s per circuit with every gate; Proc 2 s mips_16 to 29 s mcu with the
silicon forms alone; darkriscv about 100 s with the equivalence fallback). Local disk peak well under 5 GB (three releases 203 MB, place-and-route
outputs pruned to the routed DEF, netlist, DRC report and logs).

## 7. Agent defaults and deviations

1. Proc silicon release is its own silicon-only release (133 circuits), the other forms are not rebuilt.
2. darkriscv equivalence by the init-reset reference (strict first; controller condition, recorded per circuit).
3. Buffer-free rule for every family (controller instruction after the style failure).
4. P&R: no retry after a cap-out; 60 min cap; stall rule off.
5. Comb and Seq detector settings as PR #3; Proc as rc3.
6. Four Comb bases dropped (golden does not parse), small bases below 100 circuits documented above.
