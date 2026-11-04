# Round 4 results (2026-10-31)

Branch feat/htl-round4. Output under work/htl-out/r4 (not committed). Seeker-Comb v2.0: 20 bases,
53 infected circuits on 20 bases (73 with clean copies). Seeker-Seq v2.0: 171 infected on 39 of 40
bases. All numbers come from the runs described in
spec section 8.

## 1. Simulator cross-check and fire check (Odin III authoritative)

Seeker-Comb (53 infected, 20 clean bases): bit-parallel simulator vs Odin III simulator, clean
27136 points / 939008 signal comparisons / 0 mismatches; infected 27189 points / 968031 / 0
mismatches; Odin III fire check: witness found 53/53, Odin III confirms 53/53 (trigger high,
infected victim = stuck value, clean victim different).

Seeker-Seq (171 infected, 40 clean bases incl. ITC-99 b01-b14 with latch init 1): clean 49248
points / 739584 comparisons / 0 mismatches; infected 103315 points / 1593343 / 0 mismatches; fire
check 171/171 witnessed and confirmed by Odin III.

Round 3's own "fires" flag was true by construction; with the stricter definition 7 of 53 round-3
comb circuits had a masked payload (the rare trigger net implied the victim's clean value).
Round 4 picks victim and stuck value for visibility and these now fire.

## 2. ABC equivalence, trigger forced inactive (clean part)

Seeker-Comb 53/53 equivalent. Seeker-Seq 171/171 equivalent (dsec). No unproven, no failures.

## 3. ABC restructurings (12): equivalence after each

Set: strash, balance, rewrite, refactor, resyn, resyn2, compress2, dc2, dc2x2, lut4, lut6, lut6mfs
(Seeker1 used 18). Each applied to every clean and infected circuit; the result is checked against
its own source with tools/equiv-check. Gates and depth are geometric-mean ratios to the source;
"observable P" is the geometric mean over infected circuits of P(outputs differ from the clean
circuit) (comb: 131072 vectors; seq: 256 lanes x 256 cycles), the same for every restructuring, as
it must be for an equivalence-preserving rewrite; "rare-net fraction" is the mean share of
internal nets with min(p, 1-p) < 1e-2; "rarest net p" the median over circuits of the smallest
min(p, 1-p) (a restructuring that raises it hides rare structure from a rareness-based detector).

Seeker-Comb (876 restructured circuits, 876 equivalent):

| restructuring | circuits | equivalent | unproven | not equiv / error | gates (geomean ratio) | depth (geomean ratio) | infected: observable P (geomean) | infected: rare-net fraction (mean) | infected: rarest net p (median) |
|---|---|---|---|---|---|---|---|---|---|
| strash | 73 | 73 | 0 | 0 | 1.118 | 1.096 | 2.66e-04 | 0.263 | 6.10e-05 |
| balance | 73 | 73 | 0 | 0 | 1.110 | 1.067 | 2.66e-04 | 0.261 | 6.10e-05 |
| rewrite | 73 | 73 | 0 | 0 | 0.989 | 1.059 | 2.66e-04 | 0.253 | 6.10e-05 |
| refactor | 73 | 73 | 0 | 0 | 1.021 | 1.074 | 2.66e-04 | 0.218 | 6.10e-05 |
| resyn | 73 | 73 | 0 | 0 | 0.966 | 0.992 | 2.66e-04 | 0.248 | 1.22e-04 |
| resyn2 | 73 | 73 | 0 | 0 | 0.941 | 0.996 | 2.66e-04 | 0.234 | 1.22e-04 |
| compress2 | 73 | 73 | 0 | 0 | 0.881 | 1.103 | 2.66e-04 | 0.227 | 1.22e-04 |
| dc2 | 73 | 73 | 0 | 0 | 0.895 | 1.095 | 2.66e-04 | 0.207 | 6.10e-05 |
| dc2x2 | 73 | 73 | 0 | 0 | 0.859 | 1.116 | 2.66e-04 | 0.197 | 1.22e-04 |
| lut4 | 73 | 73 | 0 | 0 | 0.366 | 0.379 | 2.66e-04 | 0.215 | 7.93e-04 |
| lut6 | 73 | 73 | 0 | 0 | 0.293 | 0.286 | 2.66e-04 | 0.226 | 8.54e-04 |
| lut6mfs | 73 | 73 | 0 | 0 | 0.271 | 0.286 | 2.66e-04 | 0.221 | 1.10e-03 |

Seeker-Seq (2532 restructured circuits, 2531 equivalent, 1 unproven: ss0262 diffeq1 infected
under compress2 hit the 600 s equiv-check timeout):

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

## 4. Rareness per family (pooled; per-circuit tables are in each build's answer_key/rareness.md)

Seeker-Comb v2.0, target band vs band reached by the independent measurement:

| band reached | circuits |
|---|---|
| p<1e-4 | 16 |
| p<1e-3 | 20 |
| p<1e-2 | 17 |
| p>=1e-2 | 0 |
| never | 0 |

Pooled: 53 infected circuits, geometric mean p = 2.979e-04 over the 53 that fired at least once, 38437632 vectors in total.

Failures / band unreachable:
- C17 [p<1e-2]: band unreachable: best joint p 3.11e-02 with k=3 (design too small for this band)
- C17 [p<1e-3]: band unreachable: best joint p 3.11e-02 with k=3 (design too small for this band)
- C17 [p<1e-4]: band unreachable: best joint p 3.11e-02 with k=3 (design too small for this band)
- apex4 [p<1e-3]: band unreachable: best joint p 1.84e-03 with k=1 (design too small for this band)
- apex4 [p<1e-4]: band unreachable: best joint p 1.84e-03 with k=1 (design too small for this band)
- ex5p [p<1e-3]: band unreachable: best joint p 3.91e-03 with k=1 (design too small for this band)
- ex5p [p<1e-4]: band unreachable: best joint p 3.91e-03 with k=1 (design too small for this band)

Seeker-Seq v2.0, P(trigger high within N cycles), lanes 2048 / 1024 / 512 by design size:

| N cycles | circuits | with P(fire<=N)>0 | min | median | max |
|---|---|---|---|---|---|
| 16 | 171 | 57 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 64 | 171 | 77 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 256 | 171 | 97 | 0.00e+00 | 1.95e-03 | 1.00e+00 |
| 1024 | 171 | 171 | 1.46e-03 | 2.75e-01 | 1.00e+00 |

Per variant, P(fire within N = 1024) (every built circuit is inside [1e-3, 1]; minimum 1.46e-3):

| variant | built | band not reachable | min | median | max |
|---|---|---|---|---|---|
| ctr-fast | 32 | 8 | 7.01e-01 | 1.00e+00 | 1.00e+00 |
| ctr-mid | 30 | 10 | 5.62e-02 | 2.06e-01 | 5.06e-01 |
| ctr-slow | 25 | 15 | 1.95e-03 | 7.81e-03 | 5.32e-02 |
| pat-fast | 38 | 2 | 5.11e-01 | 9.88e-01 | 1.00e+00 |
| pat-mid | 24 | 16 | 4.79e-02 | 1.31e-01 | 4.04e-01 |
| pat-slow | 22 | 18 | 1.46e-03 | 1.17e-02 | 4.88e-02 |

Bands not reachable (listed, not padded): 69 of 240 sequential
variants. diffeq2 builds none (no condition net or event rate that reaches any band); the others
fail only in the bands listed in the build's answer_key/failures.json. Counter widths give factor-2
steps and pattern lengths factor-p steps, so the mid and slow bands are skipped on some designs.
s298, s526 and s953, which failed in round 3, now build (victim by observability, buffered).

## 5. Bases

Seeker-Comb: ISCAS-85 (C17, C432, C499, C880, C1355, C1908, C2670, C3540, C5315, C6288, C7552) and
MCNC combinational (alu4, apex2, apex4, cordic, ex5p, misex3, pdc, spla, t481), VTR blif/2.
Seeker-Seq: ISCAS-89 (23 designs, VTR blif/2), ITC-99 b01-b14 (ccsl-uaegean/ITC99-RTL-Verilog,
GPL-3.0, vhd2vl conversion of the Politecnico di Torino ITC'99 VHDL, cloned read-only to
external/ITC99-clone), VTR diffeq1, diffeq2, sha (Odin III `write_blif --gates-as-names`).
Not built: b15, b17, b18, b19 (Odin III: 'TEMPORARY' assigned in two always blocks); b20-b22
(multi-model BLIF, 49k-72k gates, over the 30000-gate cap); VTR ch_intrinsics, mkPktMerge,
mkDelayWorker32B, mkSMAdapter4B, boundtop (single_port_ram / dual_port_ram undefined); and_latch,
single_ff (one gate); VerilogEval / VTR Verilog combinational bases (next round).

## 6. Failures and caveats

- Comb bands unreachable (design too small): see list in section 4.
- diffeq2: no Seeker-Seq variant; several others build fewer than 6 of 6 (counts per base in
  answer_key/failures.json).
- Odin III makes asynchronous resets synchronous (its warning) when reading ITC-99; the BLIF
  differs from the RTL on reset timing. Reset-like inputs are held inactive in simulation.
- Restructured circuits are gzip BLIF; ABC drops latch clocks and they are written back.
- Sequential SCOAP (Odin III) is reported but is the structural heuristic only (see spec 7).
- Round 3 numbers for Seeker-Comb are unchanged in band counts; victim and stuck value differ.

## 7. Output size

Not committed (work/htl-out/r4). Deliverable circuits: comb-final 4.9 MB plain + 9.3 MB gzip
restructured, seq-final 27 MB plain + 21 MB gzip restructured, bases 18 MB. The directories also
hold plain-text scratch files (comb-final 108 MB, seq-final 283 MB: forced-off BLIFs and ABC
intermediates, overwritten per call, git-ignored) and the superseded first restructure pass
`circuits_r` (37 MB, colliding ids; replaced by `restructured/`); nothing was deleted. Total of
work/htl-out/r4 is the `du` figure in the PR description.
