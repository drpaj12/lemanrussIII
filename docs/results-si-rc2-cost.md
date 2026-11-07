# Seeker-Si rc2: per-circuit cost (2026-11-07)

Purpose: decide how much of the silicon form can be mapped and placed-and-routed (spec
`docs/specs/2026-11-07-seeker-si-rc2.md`, RQ1.1 at standard-cell level). Measure: wall time and peak RSS
per circuit. No seeds, labels or Trojan data here: the circuits are release goldens (Comb rc5, Seq rc7)
and Proc rc3 release circuits (gates form, clean or infected not looked at; cost does not depend on it).

Setup: Odin III `build/rel-main3`; mapping = `obfuscate_traced(..., "silicon")` plus
`si_cells.blif_to_verilog`; P&R = `odin3/tools/silicon/openroad_flow.tcl` (OpenROAD from `work/tools`,
floorplan to fill, 10 ns clock, 25% utilisation), 1 thread, 3600 s cap, under `tools/heavy-run`.
GDS, Magic extraction and LVS were NOT run (ladder: mmuart whole flow 163 s; des flat extraction > 1 h).
Random ABC script fixed (one draw) for all circuits; one run per circuit.

## Mapping only (Odin III + ABC sky130, plus Verilog write)

| family | circuit (source cells / FFs) | sky130 cells | map s | notes |
|---|---|---|---|---|
| Comb | 7 / 0 | 6 | 0.2 | |
| Comb | 327 / 0 | 215 | 0.1 | |
| Comb | 854 / 0 | 280 | 0.1 | |
| Comb | 1,781 / 0 | 929 | 0.3 | |
| Comb | 1,820 / 0 | 1,459 | 0.2 | |
| Comb | 8,408 / 0 | 3,261 | 1.7 | |
| Seq | 17 / 3 | 12 | 0.0 | |
| Seq | 149 / 5 | 38 | 0.0 | |
| Seq | 483 / 18 | 308 | 0.1 | |
| Seq | 989 / 160 | 789 | 0.1 | |
| Seq | 4,268 / 8 | 1,061 | 0.4 | |
| Seq | 11,294 / 911 | 6,319 | 0.7 | |
| Proc mips_16 | 2,547 / 268 | 1,825 | 0.4 | |
| Proc mcu | 17,157 / 1,292 | 10,065 | 10.5 | provenance-budget warning only |
| Proc picorv32 | 17,196 / 1,615 | 11,010 | 2.7 | |
| Proc darkriscv | 23,639 / 2,032 | 14,485 | 4.7 | dfflibmap: 837 FFs lose INIT 0/1 |

Peak RSS of mapping is below 1 GB everywhere. Flip-flop counts are unchanged by mapping in all 16.
Mapping is not the cost; the release gate (cec against the source, fire and silence replay, Verilog round
trip) was not measured here and dominates (Proc: ABC miters about 90 of 110 s per circuit, round 11).

## OpenROAD place and route (cells include flip-flops)

| circuit | cells | wall s | peak RSS MB | result |
|---|---|---|---|---|
| Seq 3 FF | 12 | 2 | 505 | ok, 0 DRC |
| Seq 5 FF | 38 | 4 | 506 | ok |
| Comb | 215 | 11 | 522 | ok |
| Seq 18 FF | 308 | 67 | 531 | ok |
| Comb | 929 | 36 | 541 | ok |
| Seq 160 FF | 789 | 64 | 555 | ok |
| Comb | 1,459 | 60 | 550 | ok |
| Seq 8 FF | 1,061 | 3600 cap | 731 | HANG in detailed route (`DRT-0179 Init gr pin query`, no progress for 1 h) |
| Comb | 3,261 | 3600 cap | 722 | HANG, same line |
| Seq 911 FF | 6,319 | 856 | 842 | ok |
| Proc mips_16 | 1,825 | 428 | 624 | ok |
| Proc picorv32 | 11,010 | 1,966 | 1,368 | ok |
| Proc mcu | 10,065 | 2,723 | 1,361 | ok |
| Proc darkriscv | 14,485 | 3600 cap | 1,746 | stopped at `s09_global_route` after 15 s; detailed route did not finish in 1 h |

10 of 14 ran to fill with 0 DRC violations; 3 hit the cap in detailed route (two of them on small
circuits, as the ladder saw on des: a flow limit, not a design limit); no per-circuit memory problem
(under 2 GB). Time is not monotone in cell count (1,061 cells hung, 6,319 cells took 14 min).

## Extrapolation (not measured)

Silicon circuits at 100 per base: Comb 31 bases = 3,100, Seq 36 = 3,600, Proc 133 logical = 133; total
about 6,830. Mapping plus gate at a few seconds to a few minutes each: tens of hours in total on one slot
for the large Seq and Proc bases, hours for the rest (gate cost to be measured in the pilot). Full P&R of
all 6,830 at a median of about 1 min (small bases) up to 30-60 min (Proc, large Seq), with about 20% of
runs needing a cap or a retry: several hundred slot-hours (order 500 h) before GDS, extraction and LVS.
Too costly for the whole set.
