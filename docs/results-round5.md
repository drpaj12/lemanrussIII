# Round 5 results (2026-10-31)

Branch feat/htl-round5 (from main 991b868), Odin III pin 7c04cfb2. Output under work/htl-out/r5
(not committed). Seeker-Comb v2.0: 31 clean bases, 53 infected circuits (84 with clean copies).
Seeker-Seq v2.0: 40 clean bases, 171 infected (211 with clean copies).

## 1. Insertion through the Odin III edit API

Every infected circuit is built by `edit_netlist.insert`: the base BLIF is read into Odin III,
the Trojan is added with `Module.add_sop` / `add_node` / `add_net` and `Pin.connect` /
`disconnect` (victim driver moved to `__htl_tmp_<victim>`, a mux added; output isolation by
`rewire`), and the result written with `write_blif`.

| family | infected | by edit API | by text fallback | untagged nodes == clean nodes and tagged == added | inserted nodes | inserted nets |
|---|---|---|---|---|---|---|
| Seeker-Comb | 53 | 53 | 0 | 53/53 | 106 | 106 |
| Seeker-Seq | 171 | 171 | 0 | 171/171 | 3289 | 3289 |

Provenance demo (`lemanruss prov-demo work/htl-out/r5/bases-seq/b01.blif`, always-on trigger plus
a one-bit toggle ring): of 157 non-port nodes, the 154 clean nodes have `edit_tag = None` and
provenance kind `imported`; the 3 inserted nodes (`__htl_trigger`, `__htl_energy_d0` sop, the
`$_DFF_P_`) have `edit_tag = 'trojan:demo'`; the latch is kind `derived` (it is a `set_param_int`
twin). `edit_tag` therefore separates inserted cells from clean ones, and names the Trojan id.
The tag is in memory only (gap 1 in spec 9.2); the answer key `insertion.json` carries the counts.

Equivalence and fire checks, as round 4, on every circuit; counts compared with round 4:

| check | round 4 comb | round 5 comb | round 4 seq | round 5 seq |
|---|---|---|---|---|
| bit-parallel vs Odin III, clean base (points / comparisons / mismatches) | 27136 / 939008 / 0 | 27136 / 939008 / 0 | 49248 / 739584 / 0 | 49248 / 739584 / 0 |
| same, infected | 27189 / 968031 / 0 | 27189 / 968031 / 0 | 103315 / 1593343 / 0 | 103315 / 1593343 / 0 |
| Odin III fire check (witness / confirmed) | 53 / 53 | 53 / 53 | 171 / 171 | 171 / 171 |
| ABC equivalence, trigger forced inactive | 53 / 53 | 53 / 53 | 171 / 171 | 171 / 171 |

Same counts as round 4: the site selection is unchanged, only the way the circuit is written.
The new VerilogEval bases (section 4) add clean circuits but no infected ones.

## 2. RTL trigger testbenches through `sim_tb` (iverilog is the oracle)

60 combinational VerilogEval references (registry `verilogeval`, source path from
`mimir bench fetch --kind source`); per base three Trojans (input-pattern trigger on 10 input bits
plus DosStuck, ErrHi flip, ErrLo flip). 111 Trojans on 37 bases were run: **sim_tb agrees with
iverilog on 111 of 111** (output of sim_tb equals iverilog on clean and infected RTL, and both
put the first clean-vs-infected difference at the firing vector 32, so nothing differs on the 64
non-triggering vectors; the sim_tb difference is the one `tools/tb-compare` reports). Skipped
bases (23): 10 with no output driven by a plain `assign`, 6 with fewer than 2 input bits, 5 with a
port wider than 64 bits, 2 whose iverilog output has x/z (sim_tb is 2-state). One bug found and
fixed on the way: the text splice matched an `assign` inside a `//` comment (Prob062).

## 3. Energy payload: toggle counts from the Odin III simulator

Toggle ring of 5% of the gates behind an always-on trigger on 34 sequential bases (ITC-99 and
ISCAS-89 under 300 kB; 6 larger designs not run), 200 random cycles. Odin III
(`set_toggle_counting`, `toggles`) against the Python proxy (`toggles_python`): **60998 of 60998
per-net toggle counts equal** over the clean and infected circuits (after aligning the first
cycle: Odin III compares it with the power-on state settled under zero inputs). Extra toggles per
cycle, infected minus clean, equal the expected 2 x ring bits on 34 of 34 circuits (for example
b01 14, b04 504, s298 426). The ring is the energy payload; no power claim (activity proxy only).

## 4. New bases and the 18 restructurings

VerilogEval (registry suite `verilogeval`, netlist refs `verilogeval:<design>@yosys-0.51-vereval`,
Yosys `abc -g NAND,NOR` gate netlists, 156 designs): 82 are combinational, 11 have >= 8 gates and
are kept as Seeker-Comb bases (Prob004, 006, 015, 023, 042, 043, 064, 092, 094, 150, 156;
ve_ prefix); the rest are under 8 gates, sequential or use DFFSR. None reaches a rare band: all 11
bases give 33 listed failures and no infected circuit (7 with no rare net with joint hits in the
selection sample: Prob004, 006, 015, 023, 042, 064, 156; 4 with best joint p 0.25 at k = 1:
Prob043, 092, 094, 150). VerilogEval
designs are too small for the p < 1e-2 band; they are listed, not padded.

VTR Verilog (suite `vtr-verilog`, 31 designs): none usable as a combinational base. 15 do not
read (`single_port_ram` / `dual_port_ram` undefined or other Odin III errors), 8 are sequential,
7 give a BLIF with an undriven net, single_wire has 1 gate (spec 9.2, gap 5). The VTR-derived bases remain the round 4
ones (blif/2 MCNC and ISCAS, diffeq1, diffeq2, sha).

The 6 added restructurings, to reach Seeker1's 18 in count: resyn2a, resyn3, resyn2rs, compress,
resub, lut5 (ABC standard scripts plus a 5-LUT mapping; Seeker1's own list of 18 was not read, so
this is the count, not the same list). All 18 are equivalence-checked against their source.

Seeker-Comb restructurings (1512 circuits, 1512 equivalent):

| restructuring | circuits | equivalent | unproven | not equiv / error | gates (geomean ratio) | depth (geomean ratio) | infected: observable P (geomean) | infected: rare-net fraction (mean) | infected: rarest net p (median) |
|---|---|---|---|---|---|---|---|---|---|
| strash | 84 | 84 | 0 | 0 | 1.184 | 1.080 | 2.66e-04 | 0.263 | 6.10e-05 |
| balance | 84 | 84 | 0 | 0 | 1.176 | 1.055 | 2.66e-04 | 0.261 | 6.10e-05 |
| rewrite | 84 | 84 | 0 | 0 | 1.064 | 1.047 | 2.66e-04 | 0.253 | 6.10e-05 |
| refactor | 84 | 84 | 0 | 0 | 1.094 | 1.060 | 2.66e-04 | 0.218 | 6.10e-05 |
| resyn | 84 | 84 | 0 | 0 | 1.043 | 0.989 | 2.66e-04 | 0.248 | 1.22e-04 |
| resyn2 | 84 | 84 | 0 | 0 | 1.019 | 0.993 | 2.66e-04 | 0.234 | 1.22e-04 |
| compress2 | 84 | 84 | 0 | 0 | 0.962 | 1.085 | 2.66e-04 | 0.227 | 1.22e-04 |
| dc2 | 84 | 84 | 0 | 0 | 0.976 | 1.078 | 2.66e-04 | 0.207 | 6.10e-05 |
| dc2x2 | 84 | 84 | 0 | 0 | 0.942 | 1.097 | 2.66e-04 | 0.197 | 1.22e-04 |
| lut4 | 84 | 84 | 0 | 0 | 0.442 | 0.413 | 2.66e-04 | 0.215 | 7.93e-04 |
| lut6 | 84 | 84 | 0 | 0 | 0.363 | 0.321 | 2.66e-04 | 0.226 | 8.54e-04 |
| lut6mfs | 84 | 84 | 0 | 0 | 0.340 | 0.321 | 2.66e-04 | 0.221 | 1.10e-03 |
| resyn2a | 84 | 84 | 0 | 0 | 1.040 | 0.993 | 2.66e-04 | 0.245 | 1.22e-04 |
| resyn3 | 84 | 84 | 0 | 0 | 1.097 | 1.046 | 2.66e-04 | 0.266 | 6.10e-05 |
| resyn2rs | 84 | 84 | 0 | 0 | 0.983 | 0.999 | 2.66e-04 | 0.241 | 1.22e-04 |
| compress | 84 | 84 | 0 | 0 | 1.033 | 1.027 | 2.66e-04 | 0.246 | 1.22e-04 |
| resub | 84 | 84 | 0 | 0 | 1.112 | 1.076 | 2.66e-04 | 0.270 | 6.10e-05 |
| lut5 | 84 | 84 | 0 | 0 | 0.394 | 0.370 | 2.66e-04 | 0.211 | 1.04e-03 |

Seeker-Seq restructurings (3798 circuits, 3797 equivalent, 1 unproven: ss0101, diffeq1 infected,
under compress2, equiv-check timeout 600 s; round 4 had one unproven too, diffeq1 under compress2):

| restructuring | circuits | equivalent | unproven | not equiv / error | gates (geomean ratio) | depth (geomean ratio) | infected: observable P (geomean) | infected: rare-net fraction (mean) | infected: rarest net p (median) |
|---|---|---|---|---|---|---|---|---|---|
| strash | 211 | 211 | 0 | 0 | 0.837 | 0.969 | 8.79e-02 | 0.078 | 6.10e-04 |
| balance | 211 | 211 | 0 | 0 | 0.815 | 0.935 | 8.79e-02 | 0.077 | 6.10e-04 |
| rewrite | 211 | 211 | 0 | 0 | 0.710 | 0.903 | 8.79e-02 | 0.071 | 6.10e-04 |
| refactor | 211 | 211 | 0 | 0 | 0.732 | 0.919 | 8.79e-02 | 0.062 | 8.54e-04 |
| resyn | 211 | 211 | 0 | 0 | 0.703 | 0.861 | 8.79e-02 | 0.072 | 6.10e-04 |
| resyn2 | 211 | 211 | 0 | 0 | 0.670 | 0.847 | 8.79e-02 | 0.060 | 7.93e-04 |
| compress2 | 211 | 210 | 1 | 0 | 0.625 | 0.930 | 8.79e-02 | 0.060 | 7.93e-04 |
| dc2 | 211 | 211 | 0 | 0 | 0.652 | 0.941 | 8.79e-02 | 0.061 | 7.93e-04 |
| dc2x2 | 211 | 211 | 0 | 0 | 0.640 | 0.959 | 8.79e-02 | 0.061 | 7.93e-04 |
| lut4 | 211 | 211 | 0 | 0 | 0.289 | 0.312 | 8.79e-02 | 0.060 | 1.28e-03 |
| lut6 | 211 | 211 | 0 | 0 | 0.204 | 0.206 | 8.79e-02 | 0.055 | 3.05e-03 |
| lut6mfs | 211 | 211 | 0 | 0 | 0.201 | 0.206 | 8.79e-02 | 0.055 | 3.17e-03 |
| resyn2a | 211 | 211 | 0 | 0 | 0.699 | 0.857 | 8.79e-02 | 0.072 | 6.10e-04 |
| resyn3 | 211 | 211 | 0 | 0 | 0.740 | 0.903 | 8.79e-02 | 0.078 | 6.71e-04 |
| resyn2rs | 211 | 211 | 0 | 0 | 0.635 | 0.839 | 8.79e-02 | 0.061 | 7.93e-04 |
| compress | 211 | 211 | 0 | 0 | 0.696 | 0.934 | 8.79e-02 | 0.072 | 6.71e-04 |
| resub | 211 | 211 | 0 | 0 | 0.758 | 0.946 | 8.79e-02 | 0.081 | 6.71e-04 |
| lut5 | 211 | 211 | 0 | 0 | 0.235 | 0.255 | 8.79e-02 | 0.059 | 1.95e-03 |

## 5. Rareness (pooled; per-circuit tables in each build's answer_key/rareness.md)

Seeker-Comb v2.0: identical to round 4 (same site selection and seeds): 53 infected circuits,
bands reached by the independent measurement p<1e-4: 16, p<1e-3: 20, p<1e-2: 17, never 0;
geometric mean p = 2.979e-04, 38437632 vectors. The new bases add the failure lines above and
the round 4 list (C17 all bands; apex4 and ex5p in the smaller bands).

Seeker-Seq v2.0, P(trigger high within N cycles):

| N cycles | circuits | with P(fire<=N)>0 | min | median | max |
|---|---|---|---|---|---|
| 16 | 171 | 57 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 64 | 171 | 77 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 256 | 171 | 97 | 0.00e+00 | 1.95e-03 | 1.00e+00 |
| 1024 | 171 | 171 | 1.46e-03 | 2.75e-01 | 1.00e+00 |

| variant | built | band not reachable | min | median | max |
|---|---|---|---|---|---|
| ctr-fast | 32 | 8 | 7.01e-01 | 1.00e+00 | 1.00e+00 |
| ctr-mid | 30 | 10 | 5.62e-02 | 2.00e-01 | 5.06e-01 |
| ctr-slow | 25 | 15 | 1.95e-03 | 7.81e-03 | 5.32e-02 |
| pat-fast | 38 | 2 | 5.11e-01 | 9.85e-01 | 1.00e+00 |
| pat-mid | 24 | 16 | 4.79e-02 | 1.28e-01 | 4.04e-01 |
| pat-slow | 22 | 18 | 1.46e-03 | 1.17e-02 | 4.88e-02 |

69 of 240 sequential variants are not reachable (listed). Per restructuring rareness is in the
tables of section 4 (observable P, rare-net fraction, rarest net p).

## 6. Failures and caveats

- Text fallback was never needed (0 of 224 insertions).
- VerilogEval bases: 33 band failures (too small); VTR Verilog: no combinational base.
- 2 of 60 VerilogEval references print x in iverilog and were skipped in the sim_tb check.
- Seq restructure: 1 unproven of 3798 (equiv-check timeout 600 s); round 4 also had 1.
- Odin III gaps: spec 9.2.

## 7. Output size

Not committed (work/htl-out/r5): 782 MB in total (`du -sh`; seq 490 MB, comb 188 MB, the rest bases, RTL and energy runs). Scratch and the superseded `bases-ve`, `bases-ve2`,
`bases-ve3`, `bases-vtr`, `rtl-tb`, `energy-smoke` directories are kept (nothing deleted).

## Next step (resume point, round 5)

Seeker-Proc waits for a processor benchmark base (testbenches that run programs need
`sim_tb` with `$readmemh`, supported). Then: tag-carrying export of inserted cells (Odin III gap
1), sequential HDL Trojans in the sim_tb check (2-state init needs an initialised Trojan state),
bigger combinational bases (ISCAS-85 and MCNC are the only ones reaching the bands).
