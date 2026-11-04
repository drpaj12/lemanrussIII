# seeker-comb-v2.0-rc5 datasheet

Family: Seeker-Comb. Version 2.0-rc5 (release candidate). Produced by Leman Russ III (Yggdrasil III).

Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.

## Lineage

v1 = Seeker1: Sarihi, Patooghy, Badawy, Jamieson, 'The Seeker's Dilemma', arXiv 2402.17918, IPCCC 2024 (8 ISCAS-85 bases x 18 ABC restructurings = 144 HT-free and 14,400 HT-infected circuits, combinational gate-level). v2.0 keeps the formulation (the detector does not know whether a circuit is infected) and builds the infected circuits with the HTL on ISCAS-85 plus further combinational bases, with a rareness report per circuit.

## Contents

- circuits: 5809 in `circuits/<id>.blif.gz` (gzip, zero timestamp), 3545 clean and 2264 infected, opaque ids.
- bases: 31; per base one golden and up to three sets of 100 circuits (LUT k = 4, LUT k = 6, AND/OR/NOT gates).
- answer key: `answer_key/` (labels, sets, Trojans, ABC scripts, rareness, witnesses, and `pre/<id>.blif.gz`, each infected circuit before obfuscation); a detector must not read it.

Circuits per base:

C1355 301, C17 41, C1908 301, C2670 301, C3540 301, C432 301, C499 301, C5315 301, C6288 301, C7552 301, C880 301, alu4 301, apex2 301, apex4 301, cordic 301, ex5p 301, misex3 301, pdc 301, spla 301, t481 301, ve_Prob004_vector2 4, ve_Prob006_vectorr 4, ve_Prob015_vector1 4, ve_Prob023_vector100r 4, ve_Prob042_vector4 4, ve_Prob043_vector5 1, ve_Prob064_vector3 17, ve_Prob092_gatesv100 1, ve_Prob094_gatesv 1, ve_Prob150_review2015_fsmonehot 1, ve_Prob156_review2015_fancytimer 8

## Design (round 8, rc4; rc5 latch fix; rc5 Comb / rc6 Seq cut-and-stitch)

Per base: the golden (its id is in `manifest.json` under `goldens`) and three sets of 100 circuits: LUT k = 4, LUT k = 6, and an AND / OR / NOT gate library. In each set a random number between 10 and 70 of the circuits is infected, with 1 to 3 Trojans each (stuck output, bit error on an upper-half or lower-half output, and in rc5 / rc6 energy ring and slowdown); the others are clean. Every circuit other than the golden, clean or infected, is one Trojan insertion (infected only), then its own random ABC logic-optimisation script, then the set's mapping by Odin III, then shuffled ports and blocks and fresh net names; there is no provenance in the files. Which circuits are infected, the set, the script and the Trojans are in the answer key only. A base that cannot supply 100 distinct circuits in a set has fewer (never padded with copies); the counts are in `answer_key/sets.json` and in the tables below. Every infected circuit has, per Trojan, a witness input sequence (`answer_key/witnesses/`) replayed in Odin III's simulator on the finished circuit against the golden, and is equivalent to its pre-obfuscation form (`answer_key/pre/`), which equals the golden with all triggers forced inactive (ABC cec / dsec). Energy-ring (Seq only) and slowdown payloads are in the releases rc5 (Comb) and rc6 (Seq) through cut-and-stitch: the part ABC would destroy is cut out, its boundary exposed as primary inputs/outputs, host and part are each optimised and mapped, and the pieces are stitched back; every circuit, clean or infected, is cut (a clean or payload-free circuit on a dummy region of the same size distribution). The slowdown is an absorption stage `tmp | (tmp & s) ...` (equal to `tmp`, adds depth, always on), not a buffer chain. Spec section 13. rc5: the Trojan's flip-flops carry the circuit's own `.latch` type, clock and init value (rc4 gave them init 0 where every other latch has 2, which separated the labels); a pattern trigger's first stage is a two-input cell and the trigger is the sticky flag itself, so no inverter or duplicated node sits in front of a Trojan latch. All latches start unknown (init 2), read as 0 by every tool of the pipeline.

## Rareness

Seeker-Comb: the trigger is an AND of rare-valued nets grown until the joint activation probability per random vector falls in a target band (p < 1e-2, 1e-3, 1e-4; exact when the design has at most 20 inputs, else 2^20 vectors).
Rareness is measured on the circuit before obfuscation (`pre/`), where the trigger net exists.

### Bases and sets

| base | gates | K4 drawn / infected / clean | K6 drawn / infected / clean | G drawn / infected / clean |
|---|---|---|---|---|
| ve_Prob043_vector5 | None | -  | -  | -  |
| ve_Prob092_gatesv100 | None | -  | -  | -  |
| ve_Prob094_gatesv | None | -  | -  | -  |
| ve_Prob150_review2015_fsmonehot | None | -  | -  | -  |
| C17 | 7 | 51 / 10 / 2 | 46 / 11 / 2 | 25 / 13 / 2 |
| ve_Prob006_vectorr | 8 | 49 / 0 / 1 | 13 / 0 / 1 | 46 / 0 / 1 |
| ve_Prob156_review2015_fancytimer | 8 | 69 / 0 / 1 | 23 / 0 / 1 | 62 / 0 / 5 |
| ve_Prob015_vector1 | 16 | 10 / 0 / 1 | 15 / 0 / 1 | 18 / 0 / 1 |
| ve_Prob004_vector2 | 32 | 29 / 0 / 1 | 23 / 0 / 1 | 58 / 0 / 1 |
| ve_Prob042_vector4 | 32 | 61 / 0 / 1 | 69 / 0 / 1 | 40 / 0 / 1 |
| ve_Prob064_vector3 | 33 | 52 / 4 / 1 | 36 / 4 / 1 | 56 / 4 / 2 |
| ve_Prob023_vector100r | 100 | 60 / 0 / 1 | 27 / 0 / 1 | 25 / 0 / 1 |
| C432 | 182 | 45 / 45 / 55 | 33 / 33 / 67 | 70 / 70 / 30 |
| C1355 | 190 | 24 / 24 / 76 | 16 / 16 / 84 | 31 / 31 / 69 |
| C499 | 190 | 42 / 42 / 58 | 65 / 65 / 35 | 34 / 34 / 66 |
| C1908 | 294 | 51 / 51 / 49 | 54 / 54 / 46 | 50 / 50 / 50 |
| C880 | 327 | 54 / 54 / 46 | 26 / 26 / 74 | 70 / 70 / 30 |
| t481 | 406 | 19 / 19 / 81 | 60 / 60 / 40 | 52 / 52 / 48 |
| C2670 | 639 | 66 / 66 / 34 | 10 / 10 / 90 | 45 / 45 / 55 |
| cordic | 854 | 16 / 16 / 84 | 32 / 32 / 68 | 45 / 45 / 55 |
| C3540 | 968 | 33 / 33 / 67 | 38 / 38 / 62 | 44 / 44 / 56 |
| C5315 | 1529 | 44 / 44 / 56 | 42 / 42 / 58 | 28 / 28 / 72 |
| ex5p | 1779 | 28 / 28 / 72 | 16 / 16 / 84 | 59 / 59 / 41 |
| C7552 | 1781 | 10 / 10 / 90 | 40 / 40 / 60 | 37 / 37 / 63 |
| C6288 | 1820 | 17 / 17 / 83 | 51 / 51 / 49 | 13 / 13 / 87 |
| apex4 | 2196 | 34 / 34 / 66 | 37 / 37 / 63 | 55 / 55 / 45 |
| misex3 | 2557 | 32 / 32 / 68 | 48 / 48 / 52 | 22 / 22 / 78 |
| alu4 | 2732 | 20 / 20 / 80 | 63 / 63 / 37 | 32 / 32 / 68 |
| apex2 | 3165 | 15 / 15 / 85 | 12 / 12 / 88 | 49 / 49 / 51 |
| spla | 7438 | 26 / 26 / 74 | 34 / 34 / 66 | 68 / 68 / 32 |
| pdc | 8408 | 62 / 62 / 38 | 43 / 43 / 57 | 56 / 56 / 44 |

### Set K4: 652 infected circuits, 1056 Trojans

Trojans per circuit: 1: 354, 2: 192, 3: 106

Payload mix: p-dos-stuck 443, p-err-hi 225, p-err-lo 217, p-slowdown 171

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 317 | p | 9.29e-04 | 1.95e-03 | 9.73e-03 |
| comb | p<1e-3 | 264 | p | 7.53e-05 | 1.94e-04 | 1.05e-03 |
| comb | p<1e-4 | 304 | p | 1.43e-05 | 6.10e-05 | 1.50e-04 |

### Set K6: 735 infected circuits, 1192 Trojans

Trojans per circuit: 1: 402, 2: 209, 3: 124

Payload mix: p-dos-stuck 497, p-err-hi 221, p-err-lo 208, p-slowdown 266

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 316 | p | 9.17e-04 | 1.95e-03 | 9.73e-03 |
| comb | p<1e-3 | 274 | p | 8.77e-05 | 2.44e-04 | 1.03e-03 |
| comb | p<1e-4 | 336 | p | 2.00e-05 | 6.10e-05 | 1.54e-04 |

### Set G: 877 infected circuits, 1457 Trojans

Trojans per circuit: 1: 455, 2: 264, 3: 158

Payload mix: p-dos-stuck 624, p-err-hi 289, p-err-lo 280, p-slowdown 264

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 439 | p | 8.97e-04 | 1.95e-03 | 9.32e-03 |
| comb | p<1e-3 | 341 | p | 7.34e-05 | 1.58e-04 | 1.02e-03 |
| comb | p<1e-4 | 413 | p | 1.53e-05 | 6.10e-05 | 1.38e-04 |

### Failures and short sets

- C1355 [G]: insert: ValueError: no free source for the slowdown on [64]
- C1355 [G]: insert: ValueError: no free source for the slowdown on [71]
- C1355 [G]: insert: ValueError: no free source for the slowdown on [91]
- C1355 [G]: insert: ValueError: no free source for the slowdown on n_n591
- C1355 [K4]: insert: ValueError: no free source for the slowdown on [68]
- C1355 [K4]: insert: ValueError: no free source for the slowdown on [72]
- C1355 [K6]: insert: ValueError: no free source for the slowdown on [92]
- C1355 [K6]: insert: ValueError: no free source for the slowdown on n_n589
- C17 [G]: supplied 13 of 25 infected circuits (0 failed proposals, 4 empty draws)
- C17 [G]: supplied 2 of 75 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [K4]: supplied 10 of 51 infected circuits (2 failed proposals, 4 empty draws)
- C17 [K4]: supplied 2 of 49 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [K6]: supplied 11 of 46 infected circuits (0 failed proposals, 4 empty draws)
- C17 [K6]: supplied 2 of 54 clean circuits (structures repeat: 60 in a row, 0 failed)
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
- C2670 [G]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 3.4332275390625e-05, 'p_lo': 2.4800368410867768e-05, 'p_hi'
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
- C499 [G]: insert: ValueError: no free source for the slowdown on n_n389
- C499 [K4]: insert: ValueError: no free source for the slowdown on [66]
- C499 [K4]: insert: ValueError: no free source for the slowdown on [68]
- C499 [K4]: insert: ValueError: no free source for the slowdown on [71]
- C499 [K4]: insert: ValueError: no free source for the slowdown on n_n393
- C499 [K6]: insert: ValueError: no free source for the slowdown on [67]
- C499 [K6]: insert: ValueError: no free source for the slowdown on [82]
- C499 [K6]: insert: ValueError: no free source for the slowdown on [85]
- C6288 [G]: insert: ValueError: no free source for the slowdown on [559]
- C6288 [G]: insert: ValueError: no free source for the slowdown on [585]
- C6288 [K4]: insert: ValueError: no free source for the slowdown on [595]
- C6288 [K4]: insert: ValueError: no free source for the slowdown on [609]
- C6288 [K6]: insert: ValueError: no free source for the slowdown on [628]
- C6288 [K6]: insert: ValueError: no free source for the slowdown on n_n2394
- C6288 [K6]: insert: ValueError: no free source for the slowdown on n_n2429
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
- ve_Prob004_vector2 [G]: supplied 0 of 58 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [G]: supplied 1 of 42 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob004_vector2 [K4]: supplied 0 of 29 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [K4]: supplied 1 of 71 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob004_vector2 [K6]: supplied 0 of 23 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [K6]: supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob006_vectorr [G]: supplied 0 of 46 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [G]: supplied 1 of 54 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob006_vectorr [K4]: supplied 0 of 49 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [K4]: supplied 1 of 51 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob006_vectorr [K6]: supplied 0 of 13 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [K6]: supplied 1 of 87 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob015_vector1 [G]: supplied 0 of 18 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [G]: supplied 1 of 82 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob015_vector1 [K4]: supplied 0 of 10 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [K4]: supplied 1 of 90 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob015_vector1 [K6]: supplied 0 of 15 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [K6]: supplied 1 of 85 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob023_vector100r [G]: supplied 0 of 25 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [G]: supplied 1 of 75 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob023_vector100r [K4]: supplied 0 of 60 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [K4]: supplied 1 of 40 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob023_vector100r [K6]: supplied 0 of 27 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [K6]: supplied 1 of 73 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob042_vector4 [G]: supplied 0 of 40 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [G]: supplied 1 of 60 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob042_vector4 [K4]: supplied 0 of 61 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [K4]: supplied 1 of 39 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob042_vector4 [K6]: supplied 0 of 69 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [K6]: supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob043_vector5 [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE
- ve_Prob043_vector5 [all]: canonical golden: error
- ve_Prob064_vector3 [G]: supplied 2 of 44 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [G]: supplied 4 of 56 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K4]: supplied 1 of 48 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [K4]: supplied 4 of 52 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K6]: supplied 1 of 64 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [K6]: supplied 4 of 36 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob092_gatesv100 [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE
- ve_Prob092_gatesv100 [all]: canonical golden: error
- ve_Prob094_gatesv [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE
- ve_Prob094_gatesv [all]: canonical golden: error
- ve_Prob150_review2015_fsmonehot [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE
- ve_Prob150_review2015_fsmonehot [all]: canonical golden: error
- ve_Prob156_review2015_fancytimer [G]: insert: ValueError: no free source for the slowdown on gnd (x2)
- ve_Prob156_review2015_fancytimer [G]: insert: ValueError: no free source for the slowdown on unconn (x4)
- ve_Prob156_review2015_fancytimer [G]: supplied 0 of 62 infected circuits (6 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [G]: supplied 5 of 38 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob156_review2015_fancytimer [K4]: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x143)
- ve_Prob156_review2015_fancytimer [K4]: insert: ValueError: no free source for the slowdown on gnd (x2)
- ve_Prob156_review2015_fancytimer [K4]: insert: ValueError: no free source for the slowdown on unconn (x4)
- ve_Prob156_review2015_fancytimer [K4]: supplied 0 of 69 infected circuits (6 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K4]: supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 143 failed)
- ve_Prob156_review2015_fancytimer [K6]: cut-stitch host: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x109)
- ve_Prob156_review2015_fancytimer [K6]: insert: ValueError: no free source for the slowdown on gnd (x3)
- ve_Prob156_review2015_fancytimer [K6]: insert: ValueError: no free source for the slowdown on unconn (x4)
- ve_Prob156_review2015_fancytimer [K6]: supplied 0 of 23 infected circuits (7 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K6]: supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 109 failed)

## Bases and licences

- ISCAS-85 (11: C1355, C17, C1908, C2670, C3540, C432, C499, C5315, C6288, C7552, C880): licence unread. Mimir `licences.toml` has no ISCAS rule and the ISCAS licence has not been read.
- MCNC (9: alu4, apex2, apex4, cordic, ex5p, misex3, pdc, spla, t481): none-stated (Mimir rule mcnc). The MCNC licence itself has not been read.
- VerilogEval gate netlists (11: ve_Prob004_vector2, ve_Prob006_vectorr, ve_Prob015_vector1, ve_Prob023_vector100r, ve_Prob042_vector4, ve_Prob043_vector5, ve_Prob064_vector3, ve_Prob092_gatesv100, ve_Prob094_gatesv, ve_Prob150_review2015_fsmonehot, ve_Prob156_review2015_fancytimer): MIT (VerilogEval LICENSE, Copyright (c) 2023-2024 NVIDIA Research Projects) (Mimir rule verilogeval).
- The infected circuits are derivatives of these bases; each base's own licence applies to its derivative.

## Tools

- Odin III (build of the circuits): 4c91edff (libodin3 build rel-main2); checkout used for `lemanruss verify`: main 4c91edff (tools, Python plugin and library).
- ABC: UC Berkeley, ABC 1.01 (compiled Oct 21 2026 17:22:51).

## Fetch and check

Unpack the circuits and answer-key archives into one directory, then `sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.
