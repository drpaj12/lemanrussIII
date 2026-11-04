# Release v2.0-rc1: verify report (2026-10-31)

Produced by `lemanruss verify` (spec section 10.3) on the packaged release directories; every number comes from the files on disk.

## seeker-comb-v2.0-rc1: PASS

- (a) integrity: 1606 files in SHA256SUMS, 1596 circuits in the manifest; hashes, sizes, counts per base and per restructuring: all equal.
- (b) label leak: 1596 circuits scanned for htl, trojan, trigger, payload, ht_, infect, clean, .attr, #, p-dos-stuck, t-comb-rare, t-comb-rare__p-dos-stuck__netlist, trojan:; leaks 0, infected-only names not in the clean style 0, hits native to a base (also in its clean circuit, not counted) 0. Result: NO LEAK.
- (c) function: 53 infected circuits: witness found 53, Odin III confirms trigger high and payload changes the output 53; ABC equivalence to the clean twin with the trigger held at 0: {'equivalent': 53}; 1512 restructured circuits against their source: {'equivalent': 1512}; unproven: [].
- (d) rareness: 6 infected circuits re-measured (strata {'p<1e-2': 19, 'p<1e-3': 17, 'p<1e-4': 17}); within tolerance 6/6.
- (e) separation: 589 clean, 1007 infected labels in `answer_key/labels.json` only; no problems.

Inserter name patterns that were scrubbed (digits as N, count of names in the key):

- `__htl_tmp__N_N_`: 6
- `__htl_tmp__Ngat_N_`: 9
- `__htl_tmp_d`: 3
- `__htl_tmp_o_N_`: 17
- `__htl_tmp_odN_N_`: 3
- `__htl_tmp_p_N_N_`: 9
- `__htl_tmp_p_Ngat_N_`: 3
- `__htl_tmp_rN`: 3
- `__htl_trigger`: 53

## seeker-seq-v2.0-rc1: PASS

- (a) integrity: 4019 files in SHA256SUMS, 4009 circuits in the manifest; hashes, sizes, counts per base and per restructuring: all equal.
- (b) label leak: 4009 circuits scanned for htl, trojan, trigger, payload, ht_, infect, clean, .attr, #, p-dos-stuck, t-seq-counter, t-seq-counter__p-dos-stuck__netlist, t-seq-pattern, t-seq-pattern__p-dos-stuck__netlist, trojan:; leaks 0, infected-only names not in the clean style 0, hits native to a base (also in its clean circuit, not counted) 0. Result: NO LEAK.
- (c) function: 171 infected circuits: witness found 171, Odin III confirms trigger high and payload changes the output 171; ABC equivalence to the clean twin with the trigger held at 0: {'equivalent': 171}; 3798 restructured circuits against their source: {'equivalent': 3797, 'unproven': 1}; unproven: ['ss1403'].
- (d) rareness: 20 infected circuits re-measured (strata {'ctr-fast': 32, 'ctr-mid': 30, 'ctr-slow': 25, 'pat-fast': 38, 'pat-mid': 24, 'pat-slow': 22}); within tolerance 20/20.
- (e) separation: 760 clean, 3249 infected labels in `answer_key/labels.json` only; no problems.

Inserter name patterns that were scrubbed (digits as N, count of names in the key):

- `DATA_OUT[N]__htl_pre`: 95
- `O[N]__htl_pre`: 57
- `Xoutport[N]__htl_pre`: 114
- `__htl_c_dN`: 482
- `__htl_c_e`: 87
- `__htl_c_f`: 1653
- `__htl_c_fd`: 87
- `__htl_c_kN`: 482
- `__htl_c_qN`: 9158
- `__htl_s_dN`: 504
- `__htl_s_f`: 1596
- `__htl_s_fd`: 84
- `__htl_s_qN`: 9576
- `__htl_tmp_DATA_OUT[N]`: 5
- `__htl_tmp_DISPMAXN[N]`: 1
- `__htl_tmp_O[N]`: 3
- `__htl_tmp_Xoutport[N]`: 6
- `__htl_tmp_ackout`: 4
- `__htl_tmp_cmd_o[N]`: 2
- `__htl_tmp_ctr`: 6
- `__htl_tmp_gN`: 6
- `__htl_tmp_grant_o[N]`: 4
- `__htl_tmp_load_dato`: 3
- `__htl_tmp_nloss`: 1
- `__htl_tmp_overflw`: 3
- `__htl_tmp_pgN`: 29
- `__htl_tmp_pnNgat`: 5
- `__htl_tmp_pready`: 12
- `__htl_tmp_predN`: 7
- `__htl_tmp_punti_retta[N]`: 2
- `__htl_tmp_sN_out`: 5
- `__htl_tmp_sN_out_N_`: 48
- `__htl_tmp_shftirhsN`: 5
- `__htl_tmp_u`: 3
- `__htl_tmp_wr`: 2
- `__htl_tmp_x_out[N]`: 4
- `__htl_tmp_y`: 5
- `__htl_trigger`: 171
- `cmd_o[N]__htl_pre`: 38
- `ctr__htl_pre`: 114
- `grant_o[N]__htl_pre`: 76
- `load_dato__htl_pre`: 57
- `nloss__htl_pre`: 19
- `overflw__htl_pre`: 57
- `pgN__htl_pre`: 76
- `punti_retta[N]__htl_pre`: 38
- `sN_out_N___htl_pre`: 6
- `shftirhsN__htl_pre`: 95
- `u__htl_pre`: 57
- `wr__htl_pre`: 38
- `x_out[N]__htl_pre`: 76
- `y__htl_pre`: 95

## Notes

- Raw round 5 output leaks the answer key: all 53 Seeker-Comb and all 171 Seeker-Seq infected
  identity circuits contain `__htl_*` names, and the Seeker-Seq restructured infected circuits keep
  the `__htl_*` latch names (25159 names in 3249 circuits, listed above). The release scrubs them
  (spec 10.2); the packaged files pass the leak scan. A first verify run of the packaged Seeker-Comb
  failed on the ABC `#` banner (time stamp) in the 1512 restructured circuits; the banners (1512 +
  3798 lines) are dropped from the package.
- The one unproven equivalence is ss1403 (compress2 of ss0101, diffeq1 infected): ABC timeout
  600 s, as in the build; not known to be non-equivalent.
- Sample for (d): 10% per stratum, at least 1 (Seeker-Comb 2 per band = 6; Seeker-Seq 20), fresh
  seed 7777 for the measurement, 5 sigma tolerance (exact match for exhaustive designs).
- Odin III checkout for verify: v1.2.0-21-g66ee88c7 (circuits built with pin 7c04cfb2).
