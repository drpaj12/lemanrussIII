# Seeker-Si rc2: pilot (2026-11-07)

Purpose: measure the silicon form as a fourth set of Comb rc5, Seq rc7 and Proc rc3 before the long
build (spec `docs/specs/2026-11-07-seeker-si-rc2.md`, RQ1.1 at standard-cell level). Measure: gate
seconds per circuit per family, disk bytes per circuit, cap-outs, and a detector parse check.
No detection result is claimed; no seeds, labels or Trojan data appear here. Pilot circuits stay under
`work/si3-run/pilot` (not committed). The pilot seed is in a private file outside the repo.

Code: `n200.active_sets()` (env `LEMANRUSS_SETS=S` builds the silicon set only, default unchanged),
`si_gates.check` (structure, cell match, Verilog round trip, FF count equal to the golden),
`proc_build.build_one_circuit(forms=("si",))` with `ALL_FORMS`, `si_pnr.run` (OpenROAD, 30 min cap,
retry at 18 % utilisation instead of 25 %). Odin III is `build/rel-main3`, not rebuilt.

## Gates (all passed)

| family | base (source cells / FFs) | circuits built | gate failures | wall per circuit | `finish` s (map, cec, fire, silicon gates) |
|---|---|---|---|---|---|
| Comb | smallest (6 gates) | 7 of 10 | clean twins repeat (60 in a row) | 0.8 s | 0.1 to 1.1 |
| Comb | mid (327) | 10 | 0 | 0.4 s | 0.2 |
| Seq | smallest (17 / 3) | 10 | 0 | 0.35 s | 0.1 to 0.9 |
| Seq | mid (483 / 18) | 10 | 0 | 0.8 s | 0.2 |
| Seq | larger (989 / 160) | 10 | 0 | 1.7 s | 0.4 to 2.4 |
| Proc | mips_16 (268 FFs), 4 logical circuits | 4 | 0 | 2.1 s (0.7 functional, 1.4 silicon forms) | |
| Proc | mcu (1,292 FFs), 1 logical circuit | 1 | 0 | 29 s (10.8 functional, 18.3 silicon forms) | |

- The smallest Comb base cannot supply 100 distinct clean circuits (same limit as the other three
  forms); it will be recorded as "supplied N of M" as before.
- Equivalence engine for every Proc silicon circuit: `regmatch-cec` (no dsec fallback). Flip-flop
  counts equal the netlist counts (268/268, 1,292/1,292) in every circuit, clean and infected.
- Seq/Comb FF count after mapping equals the golden's in all 37 circuits (gate 6 holds).
- Verilog round trip passed for every circuit.
- Not measured: darkriscv and picorv32 gate time (estimated from mcu, 20 to 60 s each plus the
  functional replay of round 11 of about 110 s).

## Disk per circuit (one silicon circuit = BLIF + cell Verilog + its answer-key share)

| family / base | BLIF plain / gz | Verilog plain / gz | answer key per circuit |
|---|---|---|---|
| Comb mid (327 cells) | 9.0 KB / 2.4 KB | 18 KB / 3.9 KB | 2.0 KB |
| Seq 17 FFs | 0.7 KB / 0.3 KB | 1.6 KB / 0.5 KB | 1.6 KB |
| Seq 483 | 10.6 KB / 3.1 KB | 25 KB / 5.2 KB | 4.8 KB |
| Seq 989 | 29 KB / 7.7 KB | 67 KB / 13 KB | 6.9 KB |
| Proc mips_16 | 66 KB / 18 KB | 158 KB / 31 KB | not measured |
| Proc mcu | 407 KB / 113 KB | 937 KB / 186 KB | not measured |

## Place and route on pilot circuits (2 per base, first try at 25 % utilisation)

| base | cells | wall s | peak RSS MB | result |
|---|---|---|---|---|
| Comb mid | 192, 193 | 9.9, 9.0 | 516 | ok, 0 DRC |
| Seq 483 | 287, 306 | 60.9, 60.4 | 536 | ok, 0 DRC |
| Seq 989 | 805, 790 | 87.7, 79.6 | 556 | ok, 0 DRC |
| Proc mips_16 | 1,847, 1,827 | 292.9, 283.6 | 594 | ok, 0 DRC |

Cap-outs in the pilot: 0 of 8. The retry path was tested separately with a 4 s cap: both tries are
killed (process group), the record gives `flow_limit: cap`, cells and both attempts, and no OpenROAD
process is left. Earlier cost runs (cost doc) had 4 of 14 cap-outs on larger circuits (three at 3,600 s
in detailed route, one Proc darkriscv at 14,485 cells), so the cap path will be used on the big bases.
P&R output per circuit before pruning: 2 to 59 MB (cost-doc sizes; `final.odb` and per-step csv
snapshots dominate; keep `route.def`, `final.v`, `drc.rpt`, `steps.txt`, `pnr.json`, gzip).

## Detector parse check

Nine detectors (size, ffcount, classhist, sanity, rare, graphlet-b, gnn-a-nosc, gnn-yasaei, gnn-a) were
fitted on dummy alternating labels and scored 22 silicon circuits (Comb, Seq, Proc mixed): all nine
return finite scores for all 22. This shows the files parse and the code runs; no score is a result.

## Projection for the long build (extrapolated from the above; to be replaced by measured numbers)

Silicon circuits: Comb 31 bases x 100, Seq 36 x 100, Proc 133 logical = about 6,830.

| step | per heavy slot | basis |
|---|---|---|
| Comb set (3,100) | 1 to 2 h | 0.4 to 1 s per circuit, round 8 Comb build was 3.5 min for 3 sets |
| Seq set (3,600) | 2 to 4 h | 0.35 to 1.7 s per circuit measured; largest bases (sha, b12) a few s each; round 8 Seq build 33 min |
| Proc, 133 logical circuits, 4 forms | 3 to 6 h | mips 2 s, mcu 29 s (silicon form only); darkriscv, picorv32 estimated 60 to 150 s with the other three forms |
| answer key, regions, verify pass | 2 to 4 h | round 8 verify was 2 h for 130k restructured Seq circuits |
| total mapped build | 8 to 16 h on one slot, 4 to 8 h on two | |
| P&R subset: about 700 circuits (10 %, all four Proc bases, about 40 Proc circuits) | about 70 slot-hours, 35 h on two slots | 500 small x 1.5 min, 160 mid x 10 min (with caps), 40 Proc x 35 to 60 min |

Disk (local), mapped sets: Comb and Seq about 5 to 100 KB per circuit gzipped with both files and key
(about 0.3 GB total, scratch per base under 2 MB), Proc about 50 KB to 600 KB per form: all under 1 GB.
P&R subset after pruning and gzip: about 1 to 7 MB per circuit, about 3 to 5 GB for 700 circuits
(8 to 9 GB if the raw per-circuit directories were kept). GDS, extraction and LVS are not in this
projection (not measured). Total local peak estimate under 15 GB, below the 25 GB limit; each finished
batch is archived to `/mnt/f` (new dated directory) and its scratch removed.
