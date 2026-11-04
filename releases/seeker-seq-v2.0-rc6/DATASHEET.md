# seeker-seq-v2.0-rc6 datasheet

Family: Seeker-Seq. Version 2.0-rc6 (release candidate). Produced by Leman Russ III (Yggdrasil III).

Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.

## Lineage

v1 = Caroline van Neste's master's thesis (in progress; no unpublished results are cited). v2.0: sequential bases (ISCAS-89, ITC-99 and VTR sequential designs), counter and FSM-pattern triggers, multi-cycle rareness.

## Contents

- circuits: 10735 in `circuits/<id>.blif.gz` (gzip, zero timestamp), 6769 clean and 3966 infected, opaque ids.
- bases: 36; per base one golden and up to three sets of 100 circuits (LUT k = 4, LUT k = 6, AND/OR/NOT gates).
- answer key: `answer_key/` (labels, sets, Trojans, ABC scripts, rareness, witnesses, and `pre/<id>.blif.gz`, each infected circuit before obfuscation); a detector must not read it.

Circuits per base:

b01 301, b02 301, b03 301, b04 301, b06 301, b07 301, b08 301, b09 301, b10 301, b11 301, b12 301, b13 301, s1196 301, s1238 301, s1423 301, s1488 301, s1494 301, s208 301, s27 200, s298 301, s344 301, s349 301, s382 301, s386 301, s400 301, s420 301, s444 301, s510 301, s526 301, s5378 301, s641 301, s713 301, s820 301, s832 301, s953 301, sha 301

## Design (round 8, rc4; rc5 latch fix; rc5 Comb / rc6 Seq cut-and-stitch)

Per base: the golden (its id is in `manifest.json` under `goldens`) and three sets of 100 circuits: LUT k = 4, LUT k = 6, and an AND / OR / NOT gate library. In each set a random number between 10 and 70 of the circuits is infected, with 1 to 3 Trojans each (stuck output, bit error on an upper-half or lower-half output, and in rc5 / rc6 energy ring and slowdown); the others are clean. Every circuit other than the golden, clean or infected, is one Trojan insertion (infected only), then its own random ABC logic-optimisation script, then the set's mapping by Odin III, then shuffled ports and blocks and fresh net names; there is no provenance in the files. Which circuits are infected, the set, the script and the Trojans are in the answer key only. A base that cannot supply 100 distinct circuits in a set has fewer (never padded with copies); the counts are in `answer_key/sets.json` and in the tables below. Every infected circuit has, per Trojan, a witness input sequence (`answer_key/witnesses/`) replayed in Odin III's simulator on the finished circuit against the golden, and is equivalent to its pre-obfuscation form (`answer_key/pre/`), which equals the golden with all triggers forced inactive (ABC cec / dsec). Energy-ring (Seq only) and slowdown payloads are in the releases rc5 (Comb) and rc6 (Seq) through cut-and-stitch: the part ABC would destroy is cut out, its boundary exposed as primary inputs/outputs, host and part are each optimised and mapped, and the pieces are stitched back; every circuit, clean or infected, is cut (a clean or payload-free circuit on a dummy region of the same size distribution). The slowdown is an absorption stage `tmp | (tmp & s) ...` (equal to `tmp`, adds depth, always on), not a buffer chain. Spec section 13. rc5: the Trojan's flip-flops carry the circuit's own `.latch` type, clock and init value (rc4 gave them init 0 where every other latch has 2, which separated the labels); a pattern trigger's first stage is a two-input cell and the trigger is the sticky flag itself, so no inverter or duplicated node sits in front of a Trojan latch. All latches start unknown (init 2), read as 0 by every tool of the pipeline.

## Rareness

Seeker-Seq: counter and FSM-pattern triggers, three speed bands each defined by P(trigger high within 1024 cycles): fast 0.5-1, mid 0.05-0.5, slow 0.003-0.05.
Rareness is measured on the circuit before obfuscation (`pre/`), where the trigger net exists.

### Bases and sets

| base | gates | K4 drawn / infected / clean | K6 drawn / infected / clean | G drawn / infected / clean |
|---|---|---|---|---|
| s27 | 17 | 43 / 43 / 18 | 24 / 24 / 14 | 50 / 50 / 50 |
| s208 | 42 | 59 / 59 / 41 | 30 / 30 / 70 | 67 / 67 / 33 |
| s420 | 65 | 55 / 55 / 45 | 49 / 49 / 51 | 11 / 11 / 89 |
| s382 | 105 | 20 / 20 / 80 | 22 / 22 / 78 | 44 / 44 / 56 |
| s386 | 111 | 60 / 60 / 40 | 34 / 34 / 66 | 43 / 43 / 57 |
| s344 | 114 | 25 / 25 / 75 | 23 / 23 / 77 | 34 / 34 / 66 |
| s349 | 114 | 46 / 46 / 54 | 28 / 28 / 72 | 67 / 67 / 33 |
| s444 | 114 | 36 / 36 / 64 | 52 / 52 / 48 | 67 / 67 / 33 |
| b02 | 117 | 11 / 11 / 89 | 14 / 14 / 86 | 21 / 21 / 79 |
| s400 | 120 | 70 / 70 / 30 | 22 / 22 / 78 | 17 / 17 / 83 |
| s641 | 139 | 40 / 40 / 60 | 36 / 36 / 64 | 49 / 49 / 51 |
| s713 | 141 | 48 / 48 / 52 | 68 / 68 / 32 | 32 / 32 / 68 |
| s526 | 142 | 11 / 11 / 89 | 40 / 40 / 60 | 29 / 29 / 71 |
| b01 | 149 | 56 / 56 / 44 | 34 / 34 / 66 | 38 / 38 / 62 |
| b06 | 191 | 28 / 28 / 72 | 14 / 14 / 86 | 66 / 66 / 34 |
| s510 | 213 | 56 / 56 / 44 | 55 / 55 / 45 | 63 / 63 / 37 |
| s820 | 231 | 40 / 40 / 60 | 26 / 26 / 74 | 13 / 13 / 87 |
| s832 | 266 | 20 / 20 / 80 | 23 / 23 / 77 | 17 / 17 / 83 |
| b03 | 358 | 18 / 18 / 82 | 53 / 53 / 47 | 48 / 48 / 52 |
| s953 | 363 | 35 / 35 / 65 | 40 / 40 / 60 | 18 / 18 / 82 |
| s1423 | 406 | 22 / 22 / 78 | 26 / 26 / 74 | 28 / 28 / 72 |
| b09 | 415 | 45 / 45 / 55 | 48 / 48 / 52 | 11 / 11 / 89 |
| s1196 | 483 | 12 / 12 / 88 | 20 / 20 / 80 | 19 / 19 / 81 |
| b10 | 511 | 57 / 57 / 43 | 46 / 46 / 54 | 34 / 34 / 66 |
| s1494 | 518 | 26 / 26 / 74 | 44 / 44 / 56 | 23 / 23 / 77 |
| s1488 | 522 | 56 / 56 / 44 | 55 / 55 / 45 | 42 / 42 / 58 |
| s1238 | 529 | 30 / 30 / 70 | 30 / 30 / 70 | 25 / 25 / 75 |
| s5378 | 989 | 61 / 61 / 39 | 38 / 38 / 62 | 29 / 29 / 71 |
| b08 | 1275 | 16 / 16 / 84 | 62 / 62 / 38 | 16 / 16 / 84 |
| b13 | 1650 | 35 / 35 / 65 | 11 / 11 / 89 | 68 / 68 / 32 |
| b07 | 2345 | 15 / 15 / 85 | 37 / 37 / 63 | 47 / 47 / 53 |
| s298 | 4268 | 26 / 26 / 74 | 59 / 59 / 41 | 24 / 24 / 76 |
| b04 | 5034 | 54 / 54 / 46 | 36 / 36 / 64 | 27 / 27 / 73 |
| b11 | 5613 | 17 / 17 / 83 | 10 / 10 / 90 | 47 / 47 / 53 |
| b12 | 9153 | 52 / 52 / 48 | 60 / 60 / 40 | 47 / 47 / 53 |
| sha | 11294 | 41 / 41 / 59 | 62 / 62 / 38 | 12 / 12 / 88 |

### Set K4: 1342 infected circuits, 2361 Trojans

Trojans per circuit: 1: 637, 2: 391, 3: 314

Payload mix: p-dos-stuck 699, p-energy 458, p-err-hi 335, p-err-lo 308, p-slowdown 561

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| ctr | fast | 317 | P(fire<=1024) | 5.05e-01 | 1.00e+00 | 1.00e+00 |
| ctr | mid | 288 | P(fire<=1024) | 4.44e-02 | 2.33e-01 | 5.52e-01 |
| ctr | slow | 269 | P(fire<=1024) | 4.88e-04 | 1.27e-02 | 5.57e-02 |
| pat | fast | 367 | P(fire<=1024) | 5.08e-01 | 1.00e+00 | 1.00e+00 |
| pat | mid | 269 | P(fire<=1024) | 4.20e-02 | 2.07e-01 | 5.30e-01 |
| pat | slow | 290 | P(fire<=1024) | 4.88e-04 | 1.66e-02 | 6.54e-02 |

### Set K6: 1331 infected circuits, 2239 Trojans

Trojans per circuit: 1: 678, 2: 398, 3: 255

Payload mix: p-dos-stuck 643, p-energy 477, p-err-hi 341, p-err-lo 306, p-slowdown 472

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| ctr | fast | 353 | P(fire<=1024) | 4.83e-01 | 1.00e+00 | 1.00e+00 |
| ctr | mid | 279 | P(fire<=1024) | 3.86e-02 | 2.15e-01 | 5.17e-01 |
| ctr | slow | 287 | P(fire<=1024) | 4.88e-04 | 1.46e-02 | 5.86e-02 |
| pat | fast | 345 | P(fire<=1024) | 4.83e-01 | 1.00e+00 | 1.00e+00 |
| pat | mid | 255 | P(fire<=1024) | 4.39e-02 | 2.33e-01 | 5.21e-01 |
| pat | slow | 248 | P(fire<=1024) | 9.77e-04 | 1.32e-02 | 6.15e-02 |

### Set G: 1293 infected circuits, 2192 Trojans

Trojans per circuit: 1: 646, 2: 395, 3: 252

Payload mix: p-dos-stuck 628, p-energy 432, p-err-hi 323, p-err-lo 322, p-slowdown 487

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| ctr | fast | 340 | P(fire<=1024) | 4.89e-01 | 1.00e+00 | 1.00e+00 |
| ctr | mid | 266 | P(fire<=1024) | 4.54e-02 | 2.39e-01 | 4.98e-01 |
| ctr | slow | 237 | P(fire<=1024) | 4.88e-04 | 1.32e-02 | 6.20e-02 |
| pat | fast | 353 | P(fire<=1024) | 4.87e-01 | 1.00e+00 | 1.00e+00 |
| pat | mid | 266 | P(fire<=1024) | 4.20e-02 | 2.24e-01 | 5.16e-01 |
| pat | slow | 243 | P(fire<=1024) | 9.77e-04 | 1.56e-02 | 6.10e-02 |

### Failures and short sets

- b01 [K4]: insert: ValueError: no free source for the slowdown on n26
- b04 [K4]: cut-stitch dummy: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG
- b04 [K4]: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x4)
- b04 [K6]: cut-stitch host: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x3)
- b07 [K4]: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG
- b11 [K4]: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG
- b11 [K6]: cut-stitch dummy: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG
- b11 [K6]: cut-stitch host: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG
- b12 [K4]: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x3)
- b12 [K6]: cut-stitch host: obfuscate k6: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG (x5)
- b12 [K6]: no witness for Trojan 0 (p-err-lo, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': [0.0 (x2)
- b13 [G]: no witness for Trojan 0 (p-dos-stuck, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64':  (x2)
- b13 [K4]: no witness for Trojan 1 (p-dos-stuck, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64': 
- b13 [K4]: no witness for Trojan 1 (p-err-lo, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64': [0.
- b13 [K6]: no witness for Trojan 0 (p-dos-stuck, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64': 
- s1494 [K6]: insert: ValueError: no free source for the slowdown on [382]
- s27 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['energy0', 'slow1', 'slow2'], k4)
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'energy1'], k4)
- s27 [K4]: supplied 18 of 57 clean circuits (structures repeat: 60 in a row, 0 failed)
- s27 [K6]: supplied 14 of 76 clean circuits (structures repeat: 60 in a row, 0 failed)
- s298 [G]: insert: ValueError: no free source for the slowdown on [37]
- s298 [G]: insert: ValueError: no free source for the slowdown on [48]
- s298 [G]: insert: ValueError: no free source for the slowdown on [541]
- s298 [G]: insert: ValueError: no free source for the slowdown on [5704]
- s298 [G]: insert: ValueError: no free source for the slowdown on [57]
- s298 [G]: insert: ValueError: no free source for the slowdown on [8748]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [265]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8740]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [169]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [190]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [219]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [291]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [377]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [418]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [457]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [462]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [476]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [50]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5694]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [569]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5784]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5991]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6016]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6347]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6368]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [70]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7202]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7207]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7973]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8001]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8687]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8698]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8737]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9120]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9141]
- s298 [K6]: insert: ValueError: no free source for the slowdown on n_n45
- s298 [K6]: insert: ValueError: no free source for the slowdown on n_n46
- s298 [K6]: insert: ValueError: no free source for the slowdown on n_n52
- s444 [K6]: no witness for Trojan 0 (p-err-hi, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64': [0.
- s641 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- s641 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k6)
- s713 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k6)
- s713 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k6)
- sha [K4]: cut-stitch host: obfuscate k4: Odin3Error: odin3_design_run_script: ODIN3_ERR_INVALID_ARG

## Bases and licences

- ISCAS-89 (23: s1196, s1238, s1423, s1488, s1494, s208, s27, s298, s344, s349, s382, s386, s400, s420, s444, s510, s526, s5378, s641, s713, s820, s832, s953): licence unread (the ISCAS licence has not been read).
- ITC-99 (12: b01 to b13): not in Mimir `licences.toml`. Source: ccsl-uaegean/ITC99-RTL-Verilog, a vhd2vl conversion of the Politecnico di Torino ITC'99 VHDL; the repository's LICENSE says GPL-3.0 (spec section 8); the licence of the original VHDL has not been read.
- VTR Verilog `sha`: opencores permissive notice: may be used and distributed without restriction provided the copyright statement is not removed (Mimir rule vtr-sha).
- The infected circuits are derivatives of these bases; each base's own licence applies to its derivative.

## Tools

- Odin III (build of the circuits): 4c91edff (libodin3 build rel-main2); checkout used for `lemanruss verify`: main 4c91edff (tools, Python plugin and library).
- ABC: UC Berkeley, ABC 1.01 (compiled Oct 21 2026 17:22:51).

## Fetch and check

Unpack the circuits and answer-key archives into one directory, then `sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.
