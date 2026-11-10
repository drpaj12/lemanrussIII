# seeker-comb-v2.0 datasheet

Family: Seeker-Comb. Version 2.0 (supersedes the release candidates). Produced by Leman Russ III (Yggdrasil III). Defensive hardware-Trojan detection research; the circuits are Trojans to detect, nothing here is meant to be deployed.

## Contents

- circuits: 7638 in `circuits/<id>.blif.gz`, 3107 infected and 4531 clean, opaque ids; silicon cell Verilog in `circuits_v/<id>.v.gz`.
- benchmarks: 19; per benchmark a golden (plus a silicon golden), and every target with exactly 100 circuits: K4 (LUT k=4), K6 (LUT k=6), G (AND/OR/NOT gates), S (sky130_fd_sc_hd silicon). A random 10 to 70 of each 100 are infected with 1 to 3 Trojans (P = 0.5, 0.3, 0.2). A target short of 100 distinct, gated circuits is not shipped (below).
- rc circuits of the earlier candidates are kept byte for byte (same ids); circuits added to fill cells were built with the same pipeline and gates, distinct from every earlier circuit of the base; silicon circuits are those of Seeker-Si rc2 under new ids.
- answer key: `answer_key/` (labels, sets, Trojans, scripts, rareness, witnesses, `pre/`, `dropped_cells.json`); a detector must not read it.

Circuits per benchmark: C1355 402, C1908 402, C2670 402, C3540 402, C432 402, C499 402, C5315 402, C6288 402, C7552 402, C880 402, alu4 402, apex2 402, apex4 402, cordic 402, ex5p 402, misex3 402, pdc 402, spla 402, t481 402

## Reset-state Trojans replaced (Seq)

Not applicable: combinational circuits have no reset state.

None (the family has no reset-state offender).

## Dropped cells (never padded, distinctness never relaxed)

| benchmark | target | built | cause |
|---|---|---|---|
| C17 | G | 26 | supplied 13 of 25 infected circuits (0 failed proposals, 4 empty draws); supplied 2 of 75 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 73 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 11 of 12 missing infected circuits (2 failed proposals, 4 empty draws) |
| C17 | K4 | 18 | supplied 10 of 51 infected circuits (2 failed proposals, 4 empty draws); supplied 2 of 49 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 47 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 6 of 41 missing infected circuits (7 failed proposals, 4 empty draws) |
| C17 | K6 | 20 | supplied 11 of 46 infected circuits (0 failed proposals, 4 empty draws); supplied 2 of 54 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 52 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 7 of 35 missing infected circuits (6 failed proposals, 4 empty draws) |
| C17 | S | 26 | supplied 12 of 38 infected circuits (0 failed proposals, 4 empty draws); supplied 5 of 62 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 57 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 9 of 26 missing infected circuits (1 failed proposals, 4 empty draws) |
| ve_Prob004_vector2 | G | 1 | supplied 0 of 58 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 42 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 41 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 58 missing infected circuits (0 failed proposals, 4 empty draws) |
| ve_Prob004_vector2 | K4 | 1 | supplied 0 of 29 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 71 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 29 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 70 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob004_vector2 | K6 | 1 | supplied 0 of 23 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 23 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 76 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob004_vector2 | S | 1 | supplied 0 of 47 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 53 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 47 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 52 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob006_vectorr | G | 1 | supplied 0 of 46 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 54 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 46 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 53 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob006_vectorr | K4 | 1 | supplied 0 of 49 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 51 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 49 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 50 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob006_vectorr | K6 | 1 | supplied 0 of 13 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 87 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 13 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 86 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob006_vectorr | S | 1 | supplied 0 of 17 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 83 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 17 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 82 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob015_vector1 | G | 1 | supplied 0 of 18 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 82 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 18 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 81 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob015_vector1 | K4 | 1 | supplied 0 of 10 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 90 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 10 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 89 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob015_vector1 | K6 | 1 | supplied 0 of 15 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 85 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 15 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 84 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob015_vector1 | S | 1 | supplied 0 of 55 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 45 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 44 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 55 missing infected circuits (0 failed proposals, 4 empty draws) |
| ve_Prob023_vector100r | G | 1 | supplied 0 of 25 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 75 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 25 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 74 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob023_vector100r | K4 | 1 | supplied 0 of 60 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 40 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 39 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 60 missing infected circuits (0 failed proposals, 4 empty draws) |
| ve_Prob023_vector100r | K6 | 1 | supplied 0 of 27 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 73 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 27 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 72 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob023_vector100r | S | 1 | supplied 0 of 51 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 49 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 48 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 51 missing infected circuits (0 failed proposals, 4 empty draws) |
| ve_Prob042_vector4 | G | 1 | supplied 0 of 40 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 60 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 40 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 59 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob042_vector4 | K4 | 1 | supplied 0 of 61 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 39 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 38 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 61 missing infected circuits (0 failed proposals, 4 empty draws) |
| ve_Prob042_vector4 | K6 | 1 | supplied 0 of 69 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 30 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 69 missing infected circuits (0 failed proposals, 4 empty draws) |
| ve_Prob042_vector4 | S | 1 | supplied 0 of 69 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 30 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 69 missing infected circuits (0 failed proposals, 4 empty draws) |
| ve_Prob064_vector3 | G | 8 | supplied 2 of 44 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 4 of 56 infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 42 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 2 of 52 missing infected circuits (2 failed proposals, 4 empty draws) |
| ve_Prob064_vector3 | K4 | 6 | supplied 1 of 48 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 4 of 52 infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 47 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 1 of 48 missing infected circuits (3 failed proposals, 4 empty draws) |
| ve_Prob064_vector3 | K6 | 5 | supplied 1 of 64 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 4 of 36 infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 32 missing infected circuits (4 failed proposals, 4 empty draws); top-up supplied 0 of 63 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob064_vector3 | S | 6 | supplied 1 of 60 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 4 of 40 infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 36 missing infected circuits (4 failed proposals, 4 empty draws); top-up supplied 1 of 59 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob156_review2015_fancytimer | G | 5 | insert (x10); supplied 0 of 62 infected circuits (6 failed proposals, 4 empty draws); supplied 5 of 38 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 33 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 62 missing infected circuits (4 failed proposals, 4 empty draws) |
| ve_Prob156_review2015_fancytimer | K4 | 1 | cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x443); insert (x11); supplied 0 of 69 infected circuits (6 failed proposals, 4 empty draws); supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 143 failed); top-up supplied 0 of 30 missing clean circuits (structures repeat: 151 in a row, 300 failed); top-up supplied 0 of 69 missing infected circuits (5 failed proposals, 4 empty draws) |
| ve_Prob156_review2015_fancytimer | K6 | 1 | cut-stitch host: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x409); insert (x12); supplied 0 of 23 infected circuits (7 failed proposals, 4 empty draws); supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 109 failed); top-up supplied 0 of 23 missing infected circuits (5 failed proposals, 4 empty draws); top-up supplied 0 of 76 missing clean circuits (structures repeat: 149 in a row, 300 failed) |
| ve_Prob156_review2015_fancytimer | S | 1 | cut-stitch host: obfuscate silicon: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x482); insert (x11); supplied 0 of 10 infected circuits (6 failed proposals, 4 empty draws); supplied 1 of 90 clean circuits (structures repeat: 60 in a row, 182 failed); top-up supplied 0 of 10 missing infected circuits (5 failed proposals, 4 empty draws); top-up supplied 0 of 89 missing clean circuits (structures repeat: 120 in a row, 300 failed) |
| C17 | all | 0 | no complete cell: supplied 10 of 51 infected circuits (2 failed proposals, 4 empty draws); supplied 11 of 46 infected circuits (0 failed proposals, 4 empty draws); supplied 12 of 38 infected circuits (0 failed proposals, 4 empty draws); supplied 13 of 25 infected circuits (0 failed proposals, 4 empty draws); supplied 2 of 49 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 2 of 54 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 2 of 75 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 5 of 62 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 47 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 52 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 57 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 73 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 11 of 12 missing infected circuits (2 failed proposals, 4 empty draws); top-up supplied 6 of 41 missing infected circuits (7 failed proposals, 4 empty draws); top-up supplied 7 of 35 missing infected circuits (6 failed proposals, 4 empty draws); top-up supplied 9 of 26 missing infected circuits (1 failed proposals, 4 empty draws) |
| ve_Prob004_vector2 | all | 0 | no complete cell: supplied 0 of 23 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 29 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 47 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 58 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 42 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 53 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 71 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 23 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 29 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 41 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 47 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 52 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 58 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 70 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 76 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob006_vectorr | all | 0 | no complete cell: supplied 0 of 13 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 17 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 46 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 49 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 51 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 54 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 83 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 87 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 13 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 17 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 46 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 49 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 50 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 53 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 82 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 86 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob015_vector1 | all | 0 | no complete cell: supplied 0 of 10 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 15 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 18 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 55 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 45 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 82 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 85 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 90 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 10 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 15 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 18 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 44 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 55 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 81 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 84 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 89 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob023_vector100r | all | 0 | no complete cell: supplied 0 of 25 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 27 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 51 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 60 infected circuits (0 failed proposals, 4 empty draws); supplied 1 of 40 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 49 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 73 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 75 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 25 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 27 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 39 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 48 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 51 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 60 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 72 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 74 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| ve_Prob042_vector4 | all | 0 | no complete cell: supplied 0 of 40 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 61 infected circuits (0 failed proposals, 4 empty draws); supplied 0 of 69 infected circuits (0 failed proposals, 4 empty draws) (x2); supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 0 failed) (x2); supplied 1 of 39 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 60 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 30 missing clean circuits (structures repeat: 300 in a row, 0 failed) (x2); top-up supplied 0 of 38 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 40 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 59 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 61 missing infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 69 missing infected circuits (0 failed proposals, 4 empty draws) (x2) |
| ve_Prob043_vector5 | all | 0 | no complete cell: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2); canonical golden: error (x2) |
| ve_Prob064_vector3 | all | 0 | no complete cell: supplied 1 of 48 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 60 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 1 of 64 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 2 of 44 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 4 of 36 infected circuits (0 failed proposals, 4 empty draws); supplied 4 of 40 infected circuits (0 failed proposals, 4 empty draws); supplied 4 of 52 infected circuits (0 failed proposals, 4 empty draws); supplied 4 of 56 infected circuits (0 failed proposals, 4 empty draws); top-up supplied 0 of 32 missing infected circuits (4 failed proposals, 4 empty draws); top-up supplied 0 of 36 missing infected circuits (4 failed proposals, 4 empty draws); top-up supplied 0 of 42 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 47 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 63 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 1 of 48 missing infected circuits (3 failed proposals, 4 empty draws); top-up supplied 1 of 59 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 2 of 52 missing infected circuits (2 failed proposals, 4 empty draws) |
| ve_Prob092_gatesv100 | all | 0 | no complete cell: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2); canonical golden: error (x2) |
| ve_Prob094_gatesv | all | 0 | no complete cell: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2); canonical golden: error (x2) |
| ve_Prob150_review2015_fsmonehot | all | 0 | no complete cell: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2); canonical golden: error (x2) |
| ve_Prob156_review2015_fancytimer | all | 0 | no complete cell: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x443); cut-stitch host: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x409); cut-stitch host: obfuscate silicon: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x482); insert (x44); supplied 0 of 10 infected circuits (6 failed proposals, 4 empty draws); supplied 0 of 23 infected circuits (7 failed proposals, 4 empty draws); supplied 0 of 62 infected circuits (6 failed proposals, 4 empty draws); supplied 0 of 69 infected circuits (6 failed proposals, 4 empty draws); supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 143 failed); supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 109 failed); supplied 1 of 90 clean circuits (structures repeat: 60 in a row, 182 failed); supplied 5 of 38 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 10 missing infected circuits (5 failed proposals, 4 empty draws); top-up supplied 0 of 23 missing infected circuits (5 failed proposals, 4 empty draws); top-up supplied 0 of 30 missing clean circuits (structures repeat: 151 in a row, 300 failed); top-up supplied 0 of 33 missing clean circuits (structures repeat: 300 in a row, 0 failed); top-up supplied 0 of 62 missing infected circuits (4 failed proposals, 4 empty draws); top-up supplied 0 of 69 missing infected circuits (5 failed proposals, 4 empty draws); top-up supplied 0 of 76 missing clean circuits (structures repeat: 149 in a row, 300 failed); top-up supplied 0 of 89 missing clean circuits (structures repeat: 120 in a row, 300 failed) |

## Neutral stimulus (public, per benchmark)

A set of random input vectors per benchmark (`<benchmark>/stimulus/vectors.txt`: first line the input names, then one 0/1 row per vector). Pool of 16,384 random vectors (all assignments up to 12 inputs); every vector on which any infected circuit of the benchmark, in any target, differs from the golden at a primary output is removed; 1,024 of the rest are kept and the whole set is checked again.

Result: 19 benchmarks, vectors per benchmark min 121, median 1024, max 1024; infected circuits checked 3107; circuits differing from the golden on the final stimulus: 0; infected circuits excluded from the check: 0.

Benchmarks with a shorter stimulus (every candidate fired a Trojan beyond that point): ex5p 121, apex4 357.

Which circuits the stimulus was checked against stays in the answer key.

## Tools

- Odin III 1.6.0 builds the added circuits (rc circuits: rel-v160 (Odin III 1.6.0) for the added circuits; rc circuits: see their datasheets); ABC: ABC a3001b72edc5.

## Bases

C1355 (ISCAS-85), C1908 (ISCAS-85), C2670 (ISCAS-85), C3540 (ISCAS-85), C432 (ISCAS-85), C499 (ISCAS-85), C5315 (ISCAS-85), C6288 (ISCAS-85), C7552 (ISCAS-85), C880 (ISCAS-85), alu4 (MCNC), apex2 (MCNC), apex4 (MCNC), cordic (MCNC), ex5p (MCNC), misex3 (MCNC), pdc (MCNC), spla (MCNC), t481 (MCNC)

## Tables

### Bases and sets

| base | source | gates |
|---|---|---|
| C432 | ISCAS-85 | 182 |
| C1355 | ISCAS-85 | 190 |
| C499 | ISCAS-85 | 190 |
| C1908 | ISCAS-85 | 294 |
| C880 | ISCAS-85 | 327 |
| t481 | MCNC | 406 |
| C2670 | ISCAS-85 | 639 |
| cordic | MCNC | 854 |
| C3540 | ISCAS-85 | 968 |
| C5315 | ISCAS-85 | 1529 |
| ex5p | MCNC | 1779 |
| C7552 | ISCAS-85 | 1781 |
| C6288 | ISCAS-85 | 1820 |
| apex4 | MCNC | 2196 |
| misex3 | MCNC | 2557 |
| alu4 | MCNC | 2732 |
| apex2 | MCNC | 3165 |
| spla | MCNC | 7438 |
| pdc | MCNC | 8408 |

### Set K4: 638 infected circuits, 1034 Trojans

Trojans per circuit: 1: 345, 2: 190, 3: 103

Payload mix: p-dos-stuck 443, p-err-hi 225, p-err-lo 217, p-slowdown 149

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 317 | p | 9.29e-04 | 1.95e-03 | 9.73e-03 |
| comb | p<1e-3 | 264 | p | 7.53e-05 | 1.94e-04 | 1.05e-03 |
| comb | p<1e-4 | 304 | p | 1.43e-05 | 6.10e-05 | 1.50e-04 |

### Set K6: 720 infected circuits, 1168 Trojans

Trojans per circuit: 1: 393, 2: 206, 3: 121

Payload mix: p-dos-stuck 497, p-err-hi 221, p-err-lo 208, p-slowdown 242

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 316 | p | 9.17e-04 | 1.95e-03 | 9.73e-03 |
| comb | p<1e-3 | 274 | p | 8.77e-05 | 2.44e-04 | 1.03e-03 |
| comb | p<1e-4 | 336 | p | 2.00e-05 | 6.10e-05 | 1.54e-04 |

### Set G: 860 infected circuits, 1433 Trojans

Trojans per circuit: 1: 444, 2: 259, 3: 157

Payload mix: p-dos-stuck 624, p-err-hi 289, p-err-lo 280, p-slowdown 240

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 439 | p | 8.97e-04 | 1.95e-03 | 9.32e-03 |
| comb | p<1e-3 | 341 | p | 7.34e-05 | 1.58e-04 | 1.02e-03 |
| comb | p<1e-4 | 413 | p | 1.53e-05 | 6.10e-05 | 1.38e-04 |

### Set S: 889 infected circuits, 1500 Trojans

Trojans per circuit: 1: 448, 2: 271, 3: 170

Payload mix: p-dos-stuck 583, p-err-hi 297, p-err-lo 304, p-slowdown 316

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 370 | p | 9.27e-04 | 1.95e-03 | 9.95e-03 |
| comb | p<1e-3 | 357 | p | 8.01e-05 | 2.21e-04 | 1.07e-03 |
| comb | p<1e-4 | 457 | p | 1.81e-05 | 6.10e-05 | 1.45e-04 |

### Failures and short sets

- C1355 [G]: insert: ValueError: no free source for the slowdown on [64]
- C1355 [G]: insert: ValueError: no free source for the slowdown on [71]
- C1355 [G]: insert: ValueError: no free source for the slowdown on [91]
- C1355 [G]: insert: ValueError: no free source for the slowdown on n_n591
- C1355 [K4]: insert: ValueError: no free source for the slowdown on [68]
- C1355 [K4]: insert: ValueError: no free source for the slowdown on [72]
- C1355 [K6]: insert: ValueError: no free source for the slowdown on [92]
- C1355 [K6]: insert: ValueError: no free source for the slowdown on n_n589
- C1355 [S]: insert: ValueError: no free source for the slowdown on [65]
- C1355 [S]: insert: ValueError: no free source for the slowdown on [76]
- C1355 [S]: insert: ValueError: no free source for the slowdown on [77]
- C1355 [S]: insert: ValueError: no free source for the slowdown on [88]
- C1355 [S]: insert: ValueError: no free source for the slowdown on [89] (x2)
- C1355 [S]: insert: ValueError: no free source for the slowdown on n_n593
- C17 [G]: supplied 13 of 25 infected circuits (0 failed proposals, 4 empty draws)
- C17 [G]: supplied 2 of 75 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [G]: top-up supplied 0 of 73 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- C17 [G]: top-up supplied 11 of 12 missing infected circuits (2 failed proposals, 4 empty draws)
- C17 [K4]: supplied 10 of 51 infected circuits (2 failed proposals, 4 empty draws)
- C17 [K4]: supplied 2 of 49 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [K4]: top-up supplied 0 of 47 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- C17 [K4]: top-up supplied 6 of 41 missing infected circuits (7 failed proposals, 4 empty draws)
- C17 [K6]: supplied 11 of 46 infected circuits (0 failed proposals, 4 empty draws)
- C17 [K6]: supplied 2 of 54 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [K6]: top-up supplied 0 of 52 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- C17 [K6]: top-up supplied 7 of 35 missing infected circuits (6 failed proposals, 4 empty draws)
- C17 [S]: supplied 12 of 38 infected circuits (0 failed proposals, 4 empty draws)
- C17 [S]: supplied 5 of 62 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [S]: top-up supplied 0 of 57 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- C17 [S]: top-up supplied 9 of 26 missing infected circuits (1 failed proposals, 4 empty draws)
- C1908 [G]: insert: ValueError: no free source for the slowdown on [133]
- C1908 [G]: insert: ValueError: no free source for the slowdown on [26]
- C1908 [G]: insert: ValueError: no free source for the slowdown on [51]
- C1908 [G]: insert: ValueError: no free source for the slowdown on [97]
- C1908 [G]: insert: ValueError: no free source for the slowdown on [98]
- C1908 [G]: insert: ValueError: no free source for the slowdown on n_n338
- C1908 [K4]: insert: ValueError: no free source for the slowdown on [1073]
- C1908 [K4]: insert: ValueError: no free source for the slowdown on [98]
- C1908 [K6]: insert: ValueError: no free source for the slowdown on [133]
- C1908 [K6]: insert: ValueError: no free source for the slowdown on [51]
- C1908 [K6]: insert: ValueError: no free source for the slowdown on [93]
- C1908 [K6]: insert: ValueError: no free source for the slowdown on [97]
- C1908 [K6]: insert: ValueError: no free source for the slowdown on n_n336
- C1908 [S]: insert: ValueError: no free source for the slowdown on [100]
- C1908 [S]: insert: ValueError: no free source for the slowdown on n_n335
- C2670 [G]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 3.4332275390625e-05, 'p_lo': 2.4800368410867768e-05, 'p_hi'
- C2670 [S]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 5.340576171875e-05, 'p_lo': 4.113053892740849e-05, 'p_hi': 
- C3540 [S]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 0.00010204315185546875, 'p_lo': 8.445389037632214e-05, 'p_h
- C432 [G]: insert: ValueError: no free source for the slowdown on [52]
- C432 [G]: insert: ValueError: no free source for the slowdown on [541]
- C432 [G]: insert: ValueError: no free source for the slowdown on [554]
- C432 [G]: insert: ValueError: no free source for the slowdown on [555]
- C432 [G]: insert: ValueError: no free source for the slowdown on [73]
- C432 [K4]: insert: ValueError: no free source for the slowdown on [23]
- C432 [K4]: insert: ValueError: no free source for the slowdown on [548]
- C432 [K4]: insert: ValueError: no free source for the slowdown on [551]
- C432 [K4]: insert: ValueError: no free source for the slowdown on [556]
- C432 [K4]: insert: ValueError: no free source for the slowdown on [66]
- C432 [K4]: insert: ValueError: no free source for the slowdown on [70] (x2)
- C432 [K4]: insert: ValueError: no free source for the slowdown on [73]
- C432 [K4]: insert: ValueError: no free source for the slowdown on n_n62
- C432 [K6]: insert: ValueError: no free source for the slowdown on [48] (x2)
- C432 [K6]: insert: ValueError: no free source for the slowdown on [555]
- C432 [K6]: insert: ValueError: no free source for the slowdown on [556]
- C432 [K6]: insert: ValueError: no free source for the slowdown on [70]
- C432 [K6]: insert: ValueError: no free source for the slowdown on [86]
- C432 [K6]: insert: ValueError: no free source for the slowdown on n_n55
- C432 [K6]: insert: ValueError: no free source for the slowdown on n_n60
- C432 [S]: insert: ValueError: no free source for the slowdown on [556] (x2)
- C432 [S]: insert: ValueError: no free source for the slowdown on [89]
- C432 [S]: insert: ValueError: no free source for the slowdown on n_n60
- C499 [G]: insert: ValueError: no free source for the slowdown on n_n389
- C499 [K4]: insert: ValueError: no free source for the slowdown on [66]
- C499 [K4]: insert: ValueError: no free source for the slowdown on [68]
- C499 [K4]: insert: ValueError: no free source for the slowdown on [71]
- C499 [K4]: insert: ValueError: no free source for the slowdown on n_n393
- C499 [K6]: insert: ValueError: no free source for the slowdown on [67]
- C499 [K6]: insert: ValueError: no free source for the slowdown on [82]
- C499 [K6]: insert: ValueError: no free source for the slowdown on [85]
- C499 [S]: insert: ValueError: no free source for the slowdown on [69]
- C499 [S]: insert: ValueError: no free source for the slowdown on [70]
- C499 [S]: insert: ValueError: no free source for the slowdown on [80]
- C499 [S]: insert: ValueError: no free source for the slowdown on [86]
- C499 [S]: insert: ValueError: no free source for the slowdown on [87]
- C499 [S]: insert: ValueError: no free source for the slowdown on [91]
- C499 [S]: insert: ValueError: no free source for the slowdown on [92]
- C6288 [G]: insert: ValueError: no free source for the slowdown on [559]
- C6288 [G]: insert: ValueError: no free source for the slowdown on [585]
- C6288 [K4]: insert: ValueError: no free source for the slowdown on [595]
- C6288 [K4]: insert: ValueError: no free source for the slowdown on [609]
- C6288 [K6]: insert: ValueError: no free source for the slowdown on [628]
- C6288 [K6]: insert: ValueError: no free source for the slowdown on n_n2394
- C6288 [K6]: insert: ValueError: no free source for the slowdown on n_n2429
- C6288 [S]: insert: ValueError: no free source for the slowdown on n_n2399
- C6288 [S]: insert: ValueError: no free source for the slowdown on n_n2432
- C7552 [G]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 3.147125244140625e-05, 'p_lo': 2.2410278608210772e-05, 'p_h
- alu4 [K6]: insert: ValueError: no free source for the slowdown on [6757]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [116]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [1417]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [1522]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [4915]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [4942]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5201]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5401]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5465]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5491]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5504]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5516]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5751]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5796]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5900]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5935]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [5954]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [6005]
- apex4 [G]: insert: ValueError: no free source for the slowdown on [647]
- apex4 [G]: insert: ValueError: no free source for the slowdown on n_n421
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [114]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [1351]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [1527]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [1594]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [4919]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [5147]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [5248]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [6007]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [6014]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [873]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on [911]
- apex4 [K4]: insert: ValueError: no free source for the slowdown on n_n1324
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [137]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [1381]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [4845]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [4908]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [4960]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [5048]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [5307]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [5531]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [5841]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [5933]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [6025]
- apex4 [K6]: insert: ValueError: no free source for the slowdown on [87]
- apex4 [S]: insert: ValueError: no free source for the slowdown on [1599]
- apex4 [S]: insert: ValueError: no free source for the slowdown on [5092]
- apex4 [S]: insert: ValueError: no free source for the slowdown on [5186]
- apex4 [S]: insert: ValueError: no free source for the slowdown on [5677]
- apex4 [S]: insert: ValueError: no free source for the slowdown on [5867]
- apex4 [S]: insert: ValueError: no free source for the slowdown on [5912]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [197]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [293]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3264]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3295]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3378]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3417]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3552]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3607]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3744]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3797]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3814]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3851]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [3939]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [4029]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [4088]
- ex5p [G]: insert: ValueError: no free source for the slowdown on [447]
- ex5p [G]: insert: ValueError: no free source for the slowdown on n_n1015
- ex5p [G]: insert: ValueError: no free source for the slowdown on n_n1017
- ex5p [G]: insert: ValueError: no free source for the slowdown on n_n1271
- ex5p [G]: insert: ValueError: no free source for the slowdown on n_n935
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [107]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [158]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [278]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [3296]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [3310]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [3486]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [3535]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [3642]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [3655]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on [3960]
- ex5p [K4]: insert: ValueError: no free source for the slowdown on n_n1028
- ex5p [K4]: insert: ValueError: no free source for the slowdown on n_n1166
- ex5p [K4]: insert: ValueError: no free source for the slowdown on n_n1208
- ex5p [K4]: insert: ValueError: no free source for the slowdown on n_n1321
- ex5p [K4]: insert: ValueError: no free source for the slowdown on n_n858
- ex5p [K6]: insert: ValueError: no free source for the slowdown on [3288]
- ex5p [K6]: insert: ValueError: no free source for the slowdown on [3312]
- ex5p [K6]: insert: ValueError: no free source for the slowdown on [3438]
- ex5p [K6]: insert: ValueError: no free source for the slowdown on [3835]
- ex5p [K6]: insert: ValueError: no free source for the slowdown on [3911]
- ex5p [K6]: insert: ValueError: no free source for the slowdown on [3971]
- ex5p [K6]: insert: ValueError: no free source for the slowdown on n_n1059
- ex5p [K6]: insert: ValueError: no free source for the slowdown on n_n1330
- ex5p [K6]: insert: ValueError: no free source for the slowdown on n_n136
- ex5p [K6]: insert: ValueError: no free source for the slowdown on n_n862
- ex5p [S]: insert: ValueError: no free source for the slowdown on [3272]
- ex5p [S]: insert: ValueError: no free source for the slowdown on [3329]
- ex5p [S]: insert: ValueError: no free source for the slowdown on [3877]
- ex5p [S]: insert: ValueError: no free source for the slowdown on [4051]
- ex5p [S]: insert: ValueError: no free source for the slowdown on [496]
- ex5p [S]: insert: ValueError: no free source for the slowdown on [566]
- ex5p [S]: insert: ValueError: no free source for the slowdown on n_n1203
- misex3 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['dummy'], gates) (x29)
- misex3 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- misex3 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['dummy'], k4) (x17)
- misex3 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k4)
- misex3 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4) (x3)
- misex3 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1'], k4)
- misex3 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow2'], k4) (x2)
- misex3 [K6]: insert: ValueError: no free source for the slowdown on [6303]
- misex3 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['dummy'], k6) (x29)
- misex3 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k6) (x4)
- misex3 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1'], k6)
- misex3 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow2'], k6)
- misex3 [S]: insert: ValueError: no free source for the slowdown on [5392]
- misex3 [S]: insert: ValueError: no free source for the slowdown on [5756]
- misex3 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['dummy'], silicon) (x21)
- misex3 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], silicon) (x2)
- pdc [G]: insert: ValueError: no free source for the slowdown on [20153]
- pdc [G]: insert: ValueError: no free source for the slowdown on [21440]
- pdc [G]: insert: ValueError: no free source for the slowdown on [21595]
- pdc [G]: insert: ValueError: no free source for the slowdown on [21686]
- pdc [G]: insert: ValueError: no free source for the slowdown on [22812]
- pdc [G]: insert: ValueError: no free source for the slowdown on [3661]
- pdc [G]: insert: ValueError: no free source for the slowdown on [4435]
- pdc [G]: insert: ValueError: no free source for the slowdown on [4655]
- pdc [G]: insert: ValueError: no free source for the slowdown on n_n3757
- pdc [G]: insert: ValueError: no free source for the slowdown on n_n6492
- pdc [K4]: insert: ValueError: no free source for the slowdown on [19435]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [19438]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [20122]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [20474]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [20957]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [21556]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [2224]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [2465]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [2665]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [3121]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [4998]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [5221]
- pdc [K4]: insert: ValueError: no free source for the slowdown on [878]
- pdc [K4]: insert: ValueError: no free source for the slowdown on n_n1093
- pdc [K4]: insert: ValueError: no free source for the slowdown on n_n1255
- pdc [K4]: insert: ValueError: no free source for the slowdown on n_n1555
- pdc [K4]: insert: ValueError: no free source for the slowdown on n_n2272
- pdc [K4]: insert: ValueError: no free source for the slowdown on n_n3982
- pdc [K4]: insert: ValueError: no free source for the slowdown on n_n7354
- pdc [K6]: insert: ValueError: no free source for the slowdown on [20708]
- pdc [K6]: insert: ValueError: no free source for the slowdown on [21669]
- pdc [K6]: insert: ValueError: no free source for the slowdown on [3198]
- pdc [K6]: insert: ValueError: no free source for the slowdown on [5201]
- pdc [K6]: insert: ValueError: no free source for the slowdown on [855]
- pdc [K6]: insert: ValueError: no free source for the slowdown on n_n2927
- pdc [K6]: insert: ValueError: no free source for the slowdown on n_n6872
- pdc [S]: insert: ValueError: no free source for the slowdown on [19456]
- pdc [S]: insert: ValueError: no free source for the slowdown on [19972]
- pdc [S]: insert: ValueError: no free source for the slowdown on [20199]
- pdc [S]: insert: ValueError: no free source for the slowdown on [20250]
- pdc [S]: insert: ValueError: no free source for the slowdown on [20341]
- pdc [S]: insert: ValueError: no free source for the slowdown on [20447]
- pdc [S]: insert: ValueError: no free source for the slowdown on [20481]
- pdc [S]: insert: ValueError: no free source for the slowdown on [22547]
- pdc [S]: insert: ValueError: no free source for the slowdown on [3219]
- pdc [S]: insert: ValueError: no free source for the slowdown on [466]
- pdc [S]: insert: ValueError: no free source for the slowdown on [633]
- pdc [S]: insert: ValueError: no free source for the slowdown on [864]
- pdc [S]: insert: ValueError: no free source for the slowdown on n_n1791
- pdc [S]: insert: ValueError: no free source for the slowdown on n_n3392
- pdc [S]: insert: ValueError: no free source for the slowdown on n_n4251
- pdc [S]: insert: ValueError: no free source for the slowdown on n_n5041
- spla [G]: insert: ValueError: no free source for the slowdown on [17156]
- spla [G]: insert: ValueError: no free source for the slowdown on [17546]
- spla [G]: insert: ValueError: no free source for the slowdown on [17640]
- spla [G]: insert: ValueError: no free source for the slowdown on [19355]
- spla [G]: insert: ValueError: no free source for the slowdown on [19737]
- spla [G]: insert: ValueError: no free source for the slowdown on [19842]
- spla [G]: insert: ValueError: no free source for the slowdown on [3295]
- spla [G]: insert: ValueError: no free source for the slowdown on n_n3808
- spla [G]: insert: ValueError: no free source for the slowdown on n_n4265
- spla [G]: insert: ValueError: no free source for the slowdown on n_n4395
- spla [G]: insert: ValueError: no free source for the slowdown on n_n4860
- spla [G]: insert: ValueError: no free source for the slowdown on n_n4986
- spla [K4]: insert: ValueError: no free source for the slowdown on [17338]
- spla [K4]: insert: ValueError: no free source for the slowdown on [18134]
- spla [K4]: insert: ValueError: no free source for the slowdown on [2910]
- spla [K4]: insert: ValueError: no free source for the slowdown on [3602]
- spla [K4]: insert: ValueError: no free source for the slowdown on [4991]
- spla [K4]: insert: ValueError: no free source for the slowdown on n_n1188
- spla [K4]: insert: ValueError: no free source for the slowdown on n_n4268
- spla [K6]: insert: ValueError: no free source for the slowdown on [18192]
- spla [K6]: insert: ValueError: no free source for the slowdown on [4698]
- spla [K6]: insert: ValueError: no free source for the slowdown on [597]
- spla [K6]: insert: ValueError: no free source for the slowdown on n_n3895
- spla [S]: insert: ValueError: no free source for the slowdown on [17077]
- spla [S]: insert: ValueError: no free source for the slowdown on [17512]
- spla [S]: insert: ValueError: no free source for the slowdown on [17514]
- spla [S]: insert: ValueError: no free source for the slowdown on [18654]
- spla [S]: insert: ValueError: no free source for the slowdown on [2232]
- spla [S]: insert: ValueError: no free source for the slowdown on [595]
- spla [S]: insert: ValueError: no free source for the slowdown on [697]
- t481 [G]: insert: ValueError: no free source for the slowdown on [1016]
- t481 [G]: insert: ValueError: no free source for the slowdown on [994]
- t481 [G]: insert: ValueError: no free source for the slowdown on [997]
- t481 [K4]: insert: ValueError: no free source for the slowdown on [1020]
- t481 [K4]: insert: ValueError: no free source for the slowdown on [1035]
- t481 [K4]: insert: ValueError: no free source for the slowdown on [908]
- t481 [K4]: insert: ValueError: no free source for the slowdown on [996]
- t481 [K4]: insert: ValueError: no free source for the slowdown on n_n323
- t481 [K6]: insert: ValueError: no free source for the slowdown on [1035]
- t481 [K6]: insert: ValueError: no free source for the slowdown on [1036]
- t481 [K6]: insert: ValueError: no free source for the slowdown on [907]
- t481 [K6]: insert: ValueError: no free source for the slowdown on [910]
- t481 [K6]: insert: ValueError: no free source for the slowdown on [911]
- t481 [K6]: insert: ValueError: no free source for the slowdown on [943]
- t481 [K6]: insert: ValueError: no free source for the slowdown on [970]
- t481 [S]: insert: ValueError: no free source for the slowdown on [1016]
- t481 [S]: insert: ValueError: no free source for the slowdown on [909]
- t481 [S]: insert: ValueError: no free source for the slowdown on n_n323
- t481 [S]: insert: ValueError: no free source for the slowdown on n_n326
- ve_Prob004_vector2 [G]: supplied 0 of 58 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [G]: supplied 1 of 42 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob004_vector2 [G]: top-up supplied 0 of 41 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob004_vector2 [G]: top-up supplied 0 of 58 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [K4]: supplied 0 of 29 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [K4]: supplied 1 of 71 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob004_vector2 [K4]: top-up supplied 0 of 29 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [K4]: top-up supplied 0 of 70 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob004_vector2 [K6]: supplied 0 of 23 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [K6]: supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob004_vector2 [K6]: top-up supplied 0 of 23 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [K6]: top-up supplied 0 of 76 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob004_vector2 [S]: supplied 0 of 47 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [S]: supplied 1 of 53 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob004_vector2 [S]: top-up supplied 0 of 47 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [S]: top-up supplied 0 of 52 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob006_vectorr [G]: supplied 0 of 46 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [G]: supplied 1 of 54 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob006_vectorr [G]: top-up supplied 0 of 46 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [G]: top-up supplied 0 of 53 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob006_vectorr [K4]: supplied 0 of 49 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [K4]: supplied 1 of 51 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob006_vectorr [K4]: top-up supplied 0 of 49 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [K4]: top-up supplied 0 of 50 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob006_vectorr [K6]: supplied 0 of 13 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [K6]: supplied 1 of 87 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob006_vectorr [K6]: top-up supplied 0 of 13 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [K6]: top-up supplied 0 of 86 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob006_vectorr [S]: supplied 0 of 17 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [S]: supplied 1 of 83 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob006_vectorr [S]: top-up supplied 0 of 17 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [S]: top-up supplied 0 of 82 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob015_vector1 [G]: supplied 0 of 18 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [G]: supplied 1 of 82 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob015_vector1 [G]: top-up supplied 0 of 18 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [G]: top-up supplied 0 of 81 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob015_vector1 [K4]: supplied 0 of 10 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [K4]: supplied 1 of 90 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob015_vector1 [K4]: top-up supplied 0 of 10 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [K4]: top-up supplied 0 of 89 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob015_vector1 [K6]: supplied 0 of 15 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [K6]: supplied 1 of 85 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob015_vector1 [K6]: top-up supplied 0 of 15 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [K6]: top-up supplied 0 of 84 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob015_vector1 [S]: supplied 0 of 55 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [S]: supplied 1 of 45 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob015_vector1 [S]: top-up supplied 0 of 44 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob015_vector1 [S]: top-up supplied 0 of 55 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [G]: supplied 0 of 25 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [G]: supplied 1 of 75 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob023_vector100r [G]: top-up supplied 0 of 25 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [G]: top-up supplied 0 of 74 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob023_vector100r [K4]: supplied 0 of 60 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [K4]: supplied 1 of 40 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob023_vector100r [K4]: top-up supplied 0 of 39 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob023_vector100r [K4]: top-up supplied 0 of 60 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [K6]: supplied 0 of 27 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [K6]: supplied 1 of 73 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob023_vector100r [K6]: top-up supplied 0 of 27 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [K6]: top-up supplied 0 of 72 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob023_vector100r [S]: supplied 0 of 51 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [S]: supplied 1 of 49 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob023_vector100r [S]: top-up supplied 0 of 48 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob023_vector100r [S]: top-up supplied 0 of 51 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [G]: supplied 0 of 40 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [G]: supplied 1 of 60 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob042_vector4 [G]: top-up supplied 0 of 40 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [G]: top-up supplied 0 of 59 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob042_vector4 [K4]: supplied 0 of 61 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [K4]: supplied 1 of 39 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob042_vector4 [K4]: top-up supplied 0 of 38 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob042_vector4 [K4]: top-up supplied 0 of 61 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [K6]: supplied 0 of 69 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [K6]: supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob042_vector4 [K6]: top-up supplied 0 of 30 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob042_vector4 [K6]: top-up supplied 0 of 69 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [S]: supplied 0 of 69 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [S]: supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob042_vector4 [S]: top-up supplied 0 of 30 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob042_vector4 [S]: top-up supplied 0 of 69 missing infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob043_vector5 [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2)
- ve_Prob043_vector5 [all]: canonical golden: error (x2)
- ve_Prob064_vector3 [G]: supplied 2 of 44 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [G]: supplied 4 of 56 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [G]: top-up supplied 0 of 42 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob064_vector3 [G]: top-up supplied 2 of 52 missing infected circuits (2 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K4]: supplied 1 of 48 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [K4]: supplied 4 of 52 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K4]: top-up supplied 0 of 47 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob064_vector3 [K4]: top-up supplied 1 of 48 missing infected circuits (3 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K6]: supplied 1 of 64 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [K6]: supplied 4 of 36 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K6]: top-up supplied 0 of 32 missing infected circuits (4 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K6]: top-up supplied 0 of 63 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob064_vector3 [S]: supplied 1 of 60 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [S]: supplied 4 of 40 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [S]: top-up supplied 0 of 36 missing infected circuits (4 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [S]: top-up supplied 1 of 59 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob092_gatesv100 [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2)
- ve_Prob092_gatesv100 [all]: canonical golden: error (x2)
- ve_Prob094_gatesv [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2)
- ve_Prob094_gatesv [all]: canonical golden: error (x2)
- ve_Prob150_review2015_fsmonehot [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE (x2)
- ve_Prob150_review2015_fsmonehot [all]: canonical golden: error (x2)
- ve_Prob156_review2015_fancytimer [G]: insert: ValueError: no free source for the slowdown on gnd (x5)
- ve_Prob156_review2015_fancytimer [G]: insert: ValueError: no free source for the slowdown on unconn (x5)
- ve_Prob156_review2015_fancytimer [G]: supplied 0 of 62 infected circuits (6 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [G]: supplied 5 of 38 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob156_review2015_fancytimer [G]: top-up supplied 0 of 33 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- ve_Prob156_review2015_fancytimer [G]: top-up supplied 0 of 62 missing infected circuits (4 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K4]: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x443)
- ve_Prob156_review2015_fancytimer [K4]: insert: ValueError: no free source for the slowdown on gnd (x4)
- ve_Prob156_review2015_fancytimer [K4]: insert: ValueError: no free source for the slowdown on unconn (x7)
- ve_Prob156_review2015_fancytimer [K4]: supplied 0 of 69 infected circuits (6 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K4]: supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 143 failed)
- ve_Prob156_review2015_fancytimer [K4]: top-up supplied 0 of 30 missing clean circuits (structures repeat: 151 in a row, 300 failed)
- ve_Prob156_review2015_fancytimer [K4]: top-up supplied 0 of 69 missing infected circuits (5 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K6]: cut-stitch host: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x409)
- ve_Prob156_review2015_fancytimer [K6]: insert: ValueError: no free source for the slowdown on gnd (x5)
- ve_Prob156_review2015_fancytimer [K6]: insert: ValueError: no free source for the slowdown on unconn (x7)
- ve_Prob156_review2015_fancytimer [K6]: supplied 0 of 23 infected circuits (7 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K6]: supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 109 failed)
- ve_Prob156_review2015_fancytimer [K6]: top-up supplied 0 of 23 missing infected circuits (5 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K6]: top-up supplied 0 of 76 missing clean circuits (structures repeat: 149 in a row, 300 failed)
- ve_Prob156_review2015_fancytimer [S]: cut-stitch host: obfuscate silicon: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x482)
- ve_Prob156_review2015_fancytimer [S]: insert: ValueError: no free source for the slowdown on gnd (x5)
- ve_Prob156_review2015_fancytimer [S]: insert: ValueError: no free source for the slowdown on unconn (x6)
- ve_Prob156_review2015_fancytimer [S]: supplied 0 of 10 infected circuits (6 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [S]: supplied 1 of 90 clean circuits (structures repeat: 60 in a row, 182 failed)
- ve_Prob156_review2015_fancytimer [S]: top-up supplied 0 of 10 missing infected circuits (5 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [S]: top-up supplied 0 of 89 missing clean circuits (structures repeat: 120 in a row, 300 failed)

## Check

`sha256sum -c SHA256SUMS`, then `lemanruss verify <dir>`.
