# Release v2.0-rc2: verify report (2026-11-01)

Produced by `lemanruss verify` (spec section 10.3) on the packaged release directories; every number comes from the files on disk.

## seeker-seq-v2.0-rc2: PASS

- (a) integrity: 4582 files in SHA256SUMS, 4389 circuits in the manifest; hashes, sizes, counts per base and per restructuring: all equal.
- (b) label leak: 4389 circuits scanned for htl, trojan, trigger, payload, ht_, infect, clean, odin3_edit, .attr, #, p-dos-stuck, t-seq-counter, t-seq-counter__p-dos-stuck__netlist, t-seq-pattern, t-seq-pattern__p-dos-stuck__netlist, trojan:; leaks 0, infected-only names not in the clean style 0, hits native to a base (also in its clean circuit, not counted) 0; circuits or manifest holding `odin3_edit` event text 0 + 0. Result: NO LEAK.
- (c) function: 183 infected circuits: witness found 183, Odin III confirms trigger high and payload changes the output 183; ABC equivalence to the clean twin with the trigger held at 0: {'equivalent': 183}; 4158 restructured circuits against their source: {'equivalent': 4157, 'unproven': 1}; unproven: ['ss1840'].
- (d) rareness: 21 infected circuits re-measured (strata {'ctr-fast': 32, 'ctr-mid': 30, 'ctr-slow': 25, 'pat-fast': 45, 'pat-mid': 27, 'pat-slow': 24}); within tolerance 21/21.
- (e) separation: 912 clean, 3477 infected labels in `answer_key/labels.json` only; no problems.

Inserter name patterns that were scrubbed (digits as N, count of names in the key):

- `DATA_OUT[N]__htl_pre`: 95
- `Datao[N]__htl_pre`: 57
- `O[N]__htl_pre`: 57
- `RDY_iportN_put__htl_pre`: 19
- `Xoutport[N]__htl_pre`: 114
- `__htl_c_dN`: 482
- `__htl_c_e`: 87
- `__htl_c_f`: 1653
- `__htl_c_fd`: 87
- `__htl_c_kN`: 482
- `__htl_c_qN`: 9158
- `__htl_s_dN`: 568
- `__htl_s_f`: 1824
- `__htl_s_fd`: 96
- `__htl_s_qN`: 10792
- `__htl_tmp_DATA_OUT[N]`: 5
- `__htl_tmp_DISPMAXN[N]`: 1
- `__htl_tmp_Datao[N]`: 3
- `__htl_tmp_O[N]`: 3
- `__htl_tmp_RDY_iportN_put`: 1
- `__htl_tmp_Xoutport[N]`: 6
- `__htl_tmp_ackout`: 4
- `__htl_tmp_addressN[N]`: 1
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
- `__htl_tmp_wciSN_SThreadBusy`: 1
- `__htl_tmp_wr`: 8
- `__htl_tmp_x_out[N]`: 4
- `__htl_tmp_y`: 5
- `__htl_trigger`: 183
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
