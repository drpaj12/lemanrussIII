# Round 6 results (2026-11-01)

Branch feat/htl-round6 (from main 3ff8cb4), Odin III 42394c3d (library `build/rel-main/libodin3.so`;
CI pin bumped to the same commit). Output under work/htl-out/r6 (not committed); release
work/htl-rel/seeker-seq-v2.0-rc2 (index files in `releases/`). Spec section 11.

Headline: Seeker-Seq v2.0-rc2 has **48 clean bases, 183 infected circuits** (231 with clean copies; 4389
circuits with the 18 restructurings each), against rc1's 40 bases and 171 infected (211; 4009
circuits). 12 infected circuits came from 8 new bases; 3 of the 11 new bases that built are not
released (reasons below). **Seeker-Comb is unchanged** (31 bases, 53 infected, rc1): none of the
designs the Odin III fixes unlocked is combinational, so no Comb rc2 was built.

## 1. API: edit events stay in the answer key

`add_node("$_DFF_P_", None, tag, params={"INIT": 0})` replaces the `set_param_int` twin. `Pin.disconnect`
and `Pin.rewire` take the Trojan tag, so a victim's old driver and the readers moved by output
isolation carry `removed` / `rewired` events. Per infected circuit the circuit the detector sees is
written with plain `write_blif`; a second file with `write_blif --edit-tags` goes to
`answer_key/edit_events/<id>.edit.blif` (59 MB for 184 circuits; packed as `.edit.blif.gz` in the
release). Edit-API insertion on the 51-base build (`lemanruss insertion`):

- 184 infected circuits inserted, 184 by the Odin III edit API, 0 by the text fallback.
- 184/184: untouched nodes + nodes with moved pins == clean nodes, and tagged nodes == added nodes;
  184/184 have every tagged net named `__htl*`.
- Inserted nodes 3484 (= nets 3484); clean nodes carried unchanged 1022405; clean nodes with moved pins
  (events `removed` / `rewired`) 363, which round 5 could not see (gap 2 of 9.2 closed).
- Each edit-event file holds `.attr odin3_edit added:trojan:<id>` on every inserted cell and `removed:` /
  `rewired:` on the moved ones (checked on one file); the matching circuit holds no `odin3_edit` text.
- All 211 circuits of the round 5 build (clean and infected) are **byte-identical** to the same
  circuits built in round 6 (sha256 of the files compared): the new API changes how provenance is
  recorded, not the netlist.

`lemanruss verify` check (b) gained the `odin3_edit` word and a whole-text scan of every circuit and of
`manifest.json`: 0 circuits and 0 manifest hits in rc2 (unit tests: a planted `.attr odin3_edit` line
fails the check; a clean release counts 0 + 0).

## 2. New bases

Odin III script and sizes (gates = `.names` blocks after `lower`; cells = gates + flip-flops). ITC-99
sources are the `ccsl-uaegean/ITC99-RTL-Verilog` files (`external/ITC99-clone`), VTR sources the registry
`vtr-verilog` files (`mimir bench fetch --kind source`). The async-to-sync WARNING of `lower` appeared on
every ITC-99 design (decision 19), as expected.

| base | gates | flip-flops | cells | clocks | notes |
|---|---|---|---|---|---|
| b15 | 40704 | 923 | 41627 | 1 | cell count equals the triage note |
| b17 | 124047 | 2837 | 126884 | 1 | three b15 + glue, flattened |
| b18 | 316048 | 6362 | 322410 | 1 | |
| b19 | 638552 | 12726 | 651278 | 1 | |
| b20 | 48932 | 688 | 49620 | 1 | two b14, flattened; b20 to b22 are not in rc1 (cap, hierarchy) |
| b21 | 49682 | 688 | 50370 | 1 | |
| b22 | 72074 | 1000 | 73074 | 1 | |
| ch_intrinsics | 1443 | 549 | 1992 | 1 + level latch enables | 85 level-sensitive latches (`ah`, `al`) |
| mkPktMerge | 15077 | 7839 | 22916 | 1 | |
| mkSMAdapter4B | 19640 | 5405 | 25045 | 1 | |
| boundtop | 86251 | 35015 | 121266 | 145 clock-like nets | 878 level-sensitive latches |
| mkDelayWorker32B | 1104505 | 539458 | 1643963 | 1 | not built, see below |

The brief's script for the VTR designs (`read_arch; read_verilog --vtr-compat; proc; opt; unmap; lower`)
reads all five and lowers them to gate level; it left b17 (three instances of b15) and the other
hierarchical files with `.subckt` instances, so `flatten; opt` and `--top <stem>` were added (spec 11).

Cap and cost. The Round 4 cap was 30000 gates; it is now 700000. Build wall times below were measured
with 6 bases in parallel on 12 cores (`max RSS` is the worker's high-water mark, an upper bound for
the base). The largest, b19, needs 46 min (33 min of it in Odin III's sequential SCOAP, 1226 sweeps) and
3.3 GB. **mkDelayWorker32B (1.64M cells) is not built**: its BLIF is 126 MB and the Python
reader/compiler alone passed 9.9 GB resident in 3 min 41 s (trial run stopped at the 10 GB limit).

Seeker-Seq: 48 clean bases, 183 infected circuits (231 with clean copies); old set 171 infected, new set 12 infected on 7 of 11 new bases.

#### Rareness, old bases (round 5 set)

| N cycles | circuits | with P(fire<=N)>0 | min | median | max |
|---|---|---|---|---|---|
| 16 | 171 | 57 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 64 | 171 | 77 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 256 | 171 | 97 | 0.00e+00 | 1.95e-03 | 1.00e+00 |
| 1024 | 171 | 171 | 1.46e-03 | 2.75e-01 | 1.00e+00 |

| variant | built | band not reachable | min | median | max |
|---|---|---|---|---|---|
| ctr-fast | 32 | 7 | 7.01e-01 | 1.00e+00 | 1.00e+00 |
| ctr-mid | 30 | 9 | 5.62e-02 | 2.06e-01 | 5.06e-01 |
| ctr-slow | 25 | 14 | 1.95e-03 | 7.81e-03 | 5.32e-02 |
| pat-fast | 38 | 1 | 5.11e-01 | 9.88e-01 | 1.00e+00 |
| pat-mid | 24 | 15 | 4.79e-02 | 1.31e-01 | 4.04e-01 |
| pat-slow | 22 | 17 | 1.46e-03 | 1.17e-02 | 4.88e-02 |

#### Rareness, new bases (round 6)

| N cycles | circuits | with P(fire<=N)>0 | min | median | max |
|---|---|---|---|---|---|
| 16 | 12 | 6 | 0.00e+00 | 1.95e-03 | 1.00e+00 |
| 64 | 12 | 11 | 0.00e+00 | 8.79e-02 | 1.00e+00 |
| 256 | 12 | 12 | 3.91e-03 | 2.56e-01 | 1.00e+00 |
| 1024 | 12 | 12 | 1.37e-02 | 8.22e-01 | 1.00e+00 |

| variant | built | band not reachable | min | median | max |
|---|---|---|---|---|---|
| ctr-fast | 0 | 8 | - | - | - |
| ctr-mid | 0 | 8 | - | - | - |
| ctr-slow | 0 | 8 | - | - | - |
| pat-fast | 7 | 1 | 7.01e-01 | 9.90e-01 | 1.00e+00 |
| pat-mid | 3 | 5 | 1.35e-01 | 2.27e-01 | 3.61e-01 |
| pat-slow | 2 | 6 | 1.37e-02 | 1.76e-02 | 1.76e-02 |

#### Rareness, all bases

| N cycles | circuits | with P(fire<=N)>0 | min | median | max |
|---|---|---|---|---|---|
| 16 | 183 | 63 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 64 | 183 | 88 | 0.00e+00 | 0.00e+00 | 1.00e+00 |
| 256 | 183 | 109 | 0.00e+00 | 3.91e-03 | 1.00e+00 |
| 1024 | 183 | 183 | 1.46e-03 | 2.85e-01 | 1.00e+00 |

| variant | built | band not reachable | min | median | max |
|---|---|---|---|---|---|
| ctr-fast | 32 | 14 | 7.01e-01 | 1.00e+00 | 1.00e+00 |
| ctr-mid | 30 | 16 | 5.62e-02 | 2.06e-01 | 5.06e-01 |
| ctr-slow | 25 | 21 | 1.95e-03 | 7.81e-03 | 5.32e-02 |
| pat-fast | 45 | 1 | 5.11e-01 | 9.88e-01 | 1.00e+00 |
| pat-mid | 27 | 19 | 4.79e-02 | 1.35e-01 | 4.04e-01 |
| pat-slow | 24 | 22 | 1.46e-03 | 1.17e-02 | 4.88e-02 |

#### New bases: outcome and build wall time

| base | released | infected built | variants failed | wall time | max RSS | failure reasons |
|---|---|---|---|---|---|---|
| b15 | yes | 3 | 3 | 581 s | 379 MB | band not reachable, ctr: fast mid slow |
| b17 | yes | 1 | 5 | 962 s | 877 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: mid slow |
| b18 | yes | 0 | 6 | 1507 s | 1656 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: fast mid slow |
| b19 | no | 0 | 6 | 2779 s | 3343 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: fast mid slow |
| b20 | yes | 3 | 3 | 659 s | 736 MB | band not reachable, ctr: fast mid slow |
| b21 | yes | 1 | 5 | 380 s | 379 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: mid slow |
| b22 | yes | 2 | 4 | 789 s | 546 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: slow |
| boundtop | no | 0 | 6 | 2 s | 736 MB | Odin3Error: odin3_design_run_pass: ODIN3_ERR_INVALID_ARG |
| ch_intrinsics | no | 1 | 5 | 8 s | 379 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: mid slow |
| mkPktMerge | yes | 1 | 5 | 94 s | 736 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: mid slow |
| mkSMAdapter4B | yes | 1 | 5 | 109 s | 736 MB | band not reachable, ctr: fast mid slow; band not reachable, pat: mid slow |

"max RSS" in the last table: the worker's high-water mark when the base finished.

Reading the table. The counter bands (ctr-fast, ctr-mid, ctr-slow) are not reachable on any new base:
no condition set the selection pass finds counts enough events in 1024 cycles to land in a band on
512 lanes. Pattern triggers reach the fast band on all 7 released new bases that built any infected circuit (b15, b17, b20, b21, b22, mkPktMerge, mkSMAdapter4B); mid and slow on 3 and 2 of them. b18 and b19
reach no band at all. The selection logic is unchanged from round 5 (brief item 3c), so this is a
measured limit of that logic on large designs, not a tuned result.

## 3. Failures (new bases)

- **boundtop**: Odin III `scoap` fails, `boundtop.blif:53878: cannot simulate: combinational loop through
  net $n25718`. `bitsim` finds no loop in the same file (it breaks loops only at latches), so the loop
  must pass through a latch; the 878 level-sensitive `ah` / `al` latches are the candidates (not
  traced further). No infected circuit.
- **ch_intrinsics**: one infected circuit (pat-fast) builds and Odin III confirms it fires (witness 1/1),
  but the bit-parallel simulator and Odin III disagree on the level-sensitive latches (5566 of 37440
  signal comparisons on the clean base mismatch; every other base: 0) and `equiv-check` refuses the
  latch type (`unsupported: level-sensitive latch type 'ah'`), so neither the infected circuit nor its
  restructurings can be verified.
- **b19**: builds, no band reachable, so no infected circuit; ABC times out (300 s) on all 18
  restructurings of its clean circuit.
- **mkDelayWorker32B**: above the cap (memory), not built.
- Other variants that did not reach their band are in `answer_key/failures.json` (105 in the release).

b19, boundtop and ch_intrinsics are built (the files are in work/htl-out/r6/seq) but not in rc2: a
release circuit must have all 19 forms and a proof or a stated timeout for each (spec 11.1).

## 4. Counts and rareness (released bases)

Verification of 183 infected circuits:
- bit-parallel vs Odin III simulator, clean base: 52704 points, 972288 signal comparisons, 0 mismatches, 0 circuits errored
- bit-parallel vs Odin III simulator, infected: 107168 points, 1851339 signal comparisons, 0 mismatches, 0 circuits errored
- Odin III fire check: witness found 183/183, Odin III confirms 183/183
- ABC equivalence (trigger forced inactive): equivalent 183

Seeker-Seq restructurings, 4158 restructured circuits (4155 equivalent at build, 3 unproven at build:
ss1719, ss1736, ss1840 under 600 s; `verify` reran all of them and proved two, so the release has
4157 equivalent and 1 unproven; the DATASHEET lists the three of the build):

| restructuring | circuits | equivalent | unproven | not equiv / error | gates (geomean ratio) | depth (geomean ratio) | infected: observable P (geomean) | infected: rare-net fraction (mean) | infected: rarest net p (median) |
|---|---|---|---|---|---|---|---|---|---|
| strash | 231 | 231 | 0 | 0 | 0.838 | 0.960 | 9.48e-02 | 0.090 | 4.88e-04 |
| balance | 231 | 231 | 0 | 0 | 0.809 | 0.915 | 9.48e-02 | 0.089 | 4.88e-04 |
| rewrite | 231 | 231 | 0 | 0 | 0.699 | 0.879 | 9.48e-02 | 0.082 | 4.88e-04 |
| refactor | 231 | 231 | 0 | 0 | 0.719 | 0.900 | 9.48e-02 | 0.073 | 7.93e-04 |
| resyn | 231 | 231 | 0 | 0 | 0.691 | 0.837 | 9.48e-02 | 0.083 | 5.49e-04 |
| resyn2 | 231 | 231 | 0 | 0 | 0.655 | 0.826 | 9.48e-02 | 0.072 | 6.71e-04 |
| compress2 | 231 | 230 | 1 | 0 | 0.611 | 0.934 | 9.48e-02 | 0.071 | 6.71e-04 |
| dc2 | 231 | 231 | 0 | 0 | 0.636 | 0.940 | 9.48e-02 | 0.072 | 5.49e-04 |
| dc2x2 | 231 | 231 | 0 | 0 | 0.622 | 0.961 | 9.48e-02 | 0.072 | 6.71e-04 |
| lut4 | 231 | 231 | 0 | 0 | 0.280 | 0.297 | 9.48e-02 | 0.073 | 1.28e-03 |
| lut6 | 231 | 230 | 1 | 0 | 0.199 | 0.198 | 9.52e-02 | 0.067 | 2.81e-03 |
| lut6mfs | 231 | 230 | 1 | 0 | 0.196 | 0.198 | 9.44e-02 | 0.066 | 2.87e-03 |
| resyn2a | 231 | 231 | 0 | 0 | 0.688 | 0.836 | 9.48e-02 | 0.083 | 5.49e-04 |
| resyn3 | 231 | 231 | 0 | 0 | 0.735 | 0.879 | 9.48e-02 | 0.090 | 5.49e-04 |
| resyn2rs | 231 | 231 | 0 | 0 | 0.623 | 0.813 | 9.48e-02 | 0.072 | 6.71e-04 |
| compress | 231 | 231 | 0 | 0 | 0.685 | 0.930 | 9.48e-02 | 0.084 | 5.49e-04 |
| resub | 231 | 231 | 0 | 0 | 0.760 | 0.925 | 9.48e-02 | 0.092 | 5.49e-04 |
| lut5 | 231 | 231 | 0 | 0 | 0.228 | 0.243 | 9.48e-02 | 0.072 | 1.65e-03 |

## 5. Release v2.0-rc2 and verify

`lemanruss release` then `lemanruss verify` (all checks, full equivalence of all 4158 restructured
circuits, 10% rareness sample): **PASS** (docs/results-release-v2.0-rc2.md; 44 min 32 s). Label leak:
0 leaks, 0 infected-only names outside the clean style, 0 circuits and 0 manifest hits for `odin3_edit`.
One restructured circuit is unproven (ss1840, compress2, 600 s). Package sizes: circuits 134 MB,
answer key 13 MB (the 183 edit-event files are 9 MB of it, gzip).

Back-up: <archive>/2026-11-01/seeker-seq-v2.0-rc2/ (two tar.xz and SHA256SUMS,
`sha256sum -c` OK, tar entries 4393 / 193 equal to the source, `tar -d` clean; README entry added).

## 6. Resume point

Next: a counter-band search that works on the large designs (the selection pass sees too few events in
1024 cycles on 512 lanes), level-latch support in `bitsim` and `equiv-check` (ch_intrinsics, boundtop),
and a cheaper sequential SCOAP for b19-sized designs. Seeker-Proc waits for a processor benchmark base.
