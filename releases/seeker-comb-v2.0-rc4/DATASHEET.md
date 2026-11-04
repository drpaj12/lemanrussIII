# seeker-comb-v2.0-rc4 datasheet

Family: Seeker-Comb. Version 2.0-rc4 (release candidate). Produced by Leman Russ III (Yggdrasil III).

Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.

## Lineage

v1 = Seeker1: Sarihi, Patooghy, Badawy, Jamieson, 'The Seeker's Dilemma', arXiv 2402.17918, IPCCC 2024 (8 ISCAS-85 bases x 18 ABC restructurings = 144 HT-free and 14,400 HT-infected circuits, combinational gate-level). v2.0 keeps the formulation (the detector does not know whether a circuit is infected) and builds the infected circuits with the HTL on ISCAS-85 plus further combinational bases, with a rareness report per circuit.

## Contents

- circuits: 5756 in `circuits/<id>.blif.gz` (gzip, zero timestamp), 3538 clean and 2218 infected, opaque ids.
- bases: 31; per base one golden and up to three sets of 100 circuits (LUT k = 4, LUT k = 6, AND/OR/NOT gates).
- answer key: `answer_key/` (labels, sets, Trojans, ABC scripts, rareness, witnesses, and `pre/<id>.blif.gz`, each infected circuit before obfuscation); a detector must not read it.

Circuits per base:

C1355 301, C17 5, C1908 301, C2670 301, C3540 301, C432 301, C499 301, C5315 301, C6288 301, C7552 301, C880 301, alu4 301, apex2 301, apex4 301, cordic 301, ex5p 301, misex3 301, pdc 301, spla 301, t481 301, ve_Prob004_vector2 4, ve_Prob006_vectorr 4, ve_Prob015_vector1 4, ve_Prob023_vector100r 4, ve_Prob042_vector4 4, ve_Prob043_vector5 1, ve_Prob064_vector3 4, ve_Prob092_gatesv100 1, ve_Prob094_gatesv 1, ve_Prob150_review2015_fsmonehot 1, ve_Prob156_review2015_fancytimer 4

## Design (round 8, rc4)

Per base: the golden (its id is in `manifest.json` under `goldens`) and three sets of 100 circuits: LUT k = 4, LUT k = 6, and an AND / OR / NOT gate library. In each set a random number between 10 and 70 of the circuits is infected, with 1 to 3 Trojans each (stuck output, bit error on an upper-half or lower-half output); the others are clean. Every circuit other than the golden, clean or infected, is one Trojan insertion (infected only), then its own random ABC logic-optimisation script, then the set's mapping by Odin III, then shuffled ports and blocks and fresh net names; there is no provenance in the files. Which circuits are infected, the set, the script and the Trojans are in the answer key only. A base that cannot supply 100 distinct circuits in a set has fewer (never padded with copies); the counts are in `answer_key/sets.json` and in the tables below. Every infected circuit has, per Trojan, a witness input sequence (`answer_key/witnesses/`) replayed in Odin III's simulator on the finished circuit against the golden, and is equivalent to its pre-obfuscation form (`answer_key/pre/`), which equals the golden with all triggers forced inactive (ABC cec / dsec). Energy-ring and slowdown payloads are not in this release: logic optimisation removes them.

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
| C17 | 7 | 51 / 0 / 1 | 46 / 0 / 1 | 25 / 0 / 2 |
| ve_Prob006_vectorr | 8 | 49 / 0 / 1 | 13 / 0 / 1 | 46 / 0 / 1 |
| ve_Prob156_review2015_fancytimer | 8 | 69 / 0 / 1 | 23 / 0 / 1 | 62 / 0 / 1 |
| ve_Prob015_vector1 | 16 | 10 / 0 / 1 | 15 / 0 / 1 | 18 / 0 / 1 |
| ve_Prob004_vector2 | 32 | 29 / 0 / 1 | 23 / 0 / 1 | 58 / 0 / 1 |
| ve_Prob042_vector4 | 32 | 61 / 0 / 1 | 69 / 0 / 1 | 40 / 0 / 1 |
| ve_Prob064_vector3 | 33 | 52 / 0 / 1 | 36 / 0 / 1 | 56 / 0 / 1 |
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

### Set K4: 638 infected circuits, 1044 Trojans

Trojans per circuit: 1: 339, 2: 192, 3: 107

Payload mix: p-dos-stuck 506, p-err-hi 279, p-err-lo 259

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 380 | p | 9.29e-04 | 1.95e-03 | 9.88e-03 |
| comb | p<1e-3 | 310 | p | 7.53e-05 | 2.40e-04 | 1.06e-03 |
| comb | p<1e-4 | 354 | p | 1.62e-05 | 6.10e-05 | 1.54e-04 |

### Set K6: 720 infected circuits, 1192 Trojans

Trojans per circuit: 1: 381, 2: 206, 3: 133

Payload mix: p-dos-stuck 628, p-err-hi 278, p-err-lo 286

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 411 | p | 9.11e-04 | 1.95e-03 | 9.73e-03 |
| comb | p<1e-3 | 381 | p | 7.34e-05 | 2.44e-04 | 1.05e-03 |
| comb | p<1e-4 | 400 | p | 1.62e-05 | 6.10e-05 | 1.49e-04 |

### Set G: 860 infected circuits, 1394 Trojans

Trojans per circuit: 1: 474, 2: 238, 3: 148

Payload mix: p-dos-stuck 718, p-err-hi 340, p-err-lo 336

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 517 | p | 2.44e-04 | 1.95e-03 | 9.51e-03 |
| comb | p<1e-3 | 396 | p | 7.34e-05 | 1.83e-04 | 1.06e-03 |
| comb | p<1e-4 | 481 | p | 2.19e-05 | 6.10e-05 | 1.45e-04 |

### Failures and short sets

- C17 [G]: supplied 0 of 25 infected circuits (0 failed proposals, 4 empty draws)
- C17 [G]: supplied 2 of 75 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [K4]: supplied 0 of 51 infected circuits (0 failed proposals, 4 empty draws)
- C17 [K4]: supplied 1 of 49 clean circuits (structures repeat: 60 in a row, 0 failed)
- C17 [K6]: supplied 0 of 46 infected circuits (0 failed proposals, 4 empty draws)
- C17 [K6]: supplied 1 of 54 clean circuits (structures repeat: 60 in a row, 0 failed)
- C432 [G]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 2.193450927734375e-05, 'p_lo': 1.461674688382831e-05, 'p_hi
- C432 [G]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 3.4332275390625e-05, 'p_lo': 2.4800368410867768e-05, 'p_hi'
- C5315 [G]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 0.000186920166015625, 'p_lo': 0.00016252096959696555, 'p_hi
- apex2 [G]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 2.574920654296875e-05, 'p_lo': 1.7697193472615367e-05, 'p_h
- apex2 [K4]: no witness for Trojan 2 (p-dos-stuck, comb): {'p': 2.288818359375e-05, 'p_lo': 1.5381444300322784e-05, 'p_hi':
- misex3 [G]: obfuscated circuit vs its source: error (x28)
- misex3 [K4]: obfuscated circuit vs its source: error (x25)
- misex3 [K6]: obfuscated circuit vs its source: error (x36)
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
- ve_Prob064_vector3 [G]: supplied 0 of 56 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [G]: supplied 1 of 44 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [K4]: supplied 0 of 52 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K4]: supplied 1 of 48 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob064_vector3 [K6]: supplied 0 of 36 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [K6]: supplied 1 of 64 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob092_gatesv100 [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE
- ve_Prob092_gatesv100 [all]: canonical golden: error
- ve_Prob094_gatesv [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE
- ve_Prob094_gatesv [all]: canonical golden: error
- ve_Prob150_review2015_fsmonehot [all]: Odin3Error: odin3_design_run_pass: ODIN3_ERR_PARSE
- ve_Prob150_review2015_fsmonehot [all]: canonical golden: error
- ve_Prob156_review2015_fancytimer [G]: supplied 0 of 62 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [G]: supplied 1 of 38 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob156_review2015_fancytimer [K4]: supplied 0 of 69 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K4]: supplied 1 of 31 clean circuits (structures repeat: 60 in a row, 0 failed)
- ve_Prob156_review2015_fancytimer [K6]: supplied 0 of 23 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [K6]: supplied 1 of 77 clean circuits (structures repeat: 60 in a row, 0 failed)

## Bases and licences

- ISCAS-85 (11: C1355, C17, C1908, C2670, C3540, C432, C499, C5315, C6288, C7552, C880): licence unread. Mimir `licences.toml` has no ISCAS rule and the ISCAS licence has not been read.
- MCNC (9: alu4, apex2, apex4, cordic, ex5p, misex3, pdc, spla, t481): none-stated (Mimir rule mcnc). The MCNC licence itself has not been read.
- VerilogEval gate netlists (11: ve_Prob004_vector2, ve_Prob006_vectorr, ve_Prob015_vector1, ve_Prob023_vector100r, ve_Prob042_vector4, ve_Prob043_vector5, ve_Prob064_vector3, ve_Prob092_gatesv100, ve_Prob094_gatesv, ve_Prob150_review2015_fsmonehot, ve_Prob156_review2015_fancytimer): MIT (VerilogEval LICENSE, Copyright (c) 2023-2024 NVIDIA Research Projects) (Mimir rule verilogeval).
- The infected circuits are derivatives of these bases; each base's own licence applies to its derivative.

## Tools

- Odin III (build of the circuits): d4d3356e (libodin3 build rel-main); checkout used for `lemanruss verify`: v1.2.0-27-g8d5721c0 (tools and Python plugin; library built at d4d3356e).
- ABC: UC Berkeley, ABC 1.01 (compiled Oct 21 2026 17:22:51).

## Fetch and check

Unpack the circuits and answer-key archives into one directory, then `sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.
