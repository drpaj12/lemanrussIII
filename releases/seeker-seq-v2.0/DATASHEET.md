# seeker-seq-v2.0 datasheet

Family: Seeker-Seq. Version 2.0 (supersedes the release candidates). Produced by Leman Russ III (Yggdrasil III). Defensive hardware-Trojan detection research; the circuits are Trojans to detect, nothing here is meant to be deployed.

## Contents

- circuits: 14474 in `circuits/<id>.blif.gz`, 5379 infected and 9095 clean, opaque ids; silicon cell Verilog in `circuits_v/<id>.v.gz`.
- benchmarks: 38; per benchmark a golden (plus a silicon golden), and every target with exactly 100 circuits: K4 (LUT k=4), K6 (LUT k=6), G (AND/OR/NOT gates), S (sky130_fd_sc_hd silicon). A random 10 to 70 of each 100 are infected with 1 to 3 Trojans (P = 0.5, 0.3, 0.2). A target short of 100 distinct, gated circuits is not shipped (below).
- rc circuits of the earlier candidates are kept byte for byte (same ids); circuits added to fill cells were built with the same pipeline and gates, distinct from every earlier circuit of the base; silicon circuits are those of Seeker-Si rc2 under new ids.
- answer key: `answer_key/` (labels, sets, Trojans, scripts, rareness, witnesses, `pre/`, `dropped_cells.json`); a detector must not read it.

Circuits per benchmark: b01 302, b02 302, b03 402, b04 402, b06 302, b07 402, b08 402, b09 402, b10 402, b11 402, b12 402, b13 402, ca_prng 301, i2c 301, s1196 402, s1238 402, s1423 402, s1488 402, s1494 402, s208 402, s27 202, s298 402, s344 402, s349 402, s382 402, s386 402, s400 402, s420 402, s444 402, s510 402, s526 402, s5378 402, s641 402, s713 402, s820 402, s832 402, s953 302, sha 402

## Reset-state Trojans replaced (Seq)

A Trojan whose trigger fires in the reset state for more than 1 percent of random inputs (the loosest rareness band; estimated on 65,536 vectors at cycle 0) fires at cycle 0 for almost any input: it is not a rare-triggered Trojan. A trigger that matches the reset state only with a rare input pattern passes. Seeker-Seq v2.0-rc8 and the silicon rc2 set carried such circuits (rc8 stays as the record). v2.0 has a build gate against them; each offender was removed and replaced by a new draw of the same cell with the same Trojan count that passes every gate, so the infected count and the Trojan-count mix of the cell are unchanged. Per cell (removed and replaced):

1527 circuits in 144 cells: b01/G 4, b01/K6 4, b01/S 2, b02/G 4, b02/K6 1, b02/S 1, b03/G 7, b03/K4 11, b03/K6 14, b03/S 5, b04/G 2, b04/K4 6, b04/K6 7, b04/S 11, b06/G 2, b06/K4 2, b06/K6 3, b06/S 4, b07/G 10, b07/K4 11, b07/K6 17, b07/S 7, b08/G 4, b08/K4 8, b08/K6 7, b08/S 3, b09/G 1, b09/K4 5, b09/K6 6, b10/G 12, b10/K4 22, b10/K6 12, b10/S 13, b11/G 16, b11/K4 5, b11/K6 5, b11/S 7, b12/G 17, b12/K4 20, b12/K6 15, b12/S 20, b13/G 10, b13/K4 26, b13/K6 6, b13/S 3, ca_prng/G 21, ca_prng/K4 32, ca_prng/K6 27, i2c/G 14, i2c/K4 56, i2c/K6 21, s1196/G 12, s1196/K4 6, s1196/K6 7, s1196/S 13, s1238/G 7, s1238/K4 17, s1238/K6 11, s1238/S 29, s1423/G 8, s1423/K4 3, s1423/K6 10, s1423/S 5, s1488/G 1, s1488/K4 4, s1488/S 2, s1494/G 1, s1494/K4 4, s1494/S 2, s208/G 10, s208/K4 9, s208/K6 3, s208/S 7, s27/G 6, s27/K4 6, s27/K6 4, s27/S 10, s298/G 1, s298/K4 1, s298/K6 2, s298/S 2, s344/G 9, s344/K4 14, s344/K6 8, s344/S 9, s349/G 10, s349/K4 17, s349/K6 10, s349/S 5, s382/G 3, s382/K4 2, s382/K6 3, s382/S 4, s386/G 1, s386/K4 6, s386/K6 7, s386/S 2, s400/G 2, s400/K4 1, s400/K6 6, s400/S 4, s420/G 6, s420/K4 23, s420/K6 16, s420/S 20, s444/G 3, s444/K4 4, s444/K6 5, s444/S 5, s510/G 16, s510/K4 27, s510/K6 18, s510/S 17, s526/G 2, s526/K4 2, s526/K6 1, s526/S 3, s5378/G 14, s5378/K4 21, s5378/K6 14, s5378/S 10, s641/G 31, s641/K4 25, s641/K6 30, s641/S 39, s713/G 25, s713/K4 38, s713/K6 51, s713/S 17, s820/G 9, s820/K4 14, s820/K6 16, s820/S 11, s832/G 11, s832/K4 14, s832/K6 10, s832/S 10, s953/G 10, s953/K4 17, s953/K6 15, s953/S 5, sha/G 3, sha/K4 4, sha/K6 20.

## Dropped cells (never padded, distinctness never relaxed)

| benchmark | target | built | cause |
|---|---|---|---|
| b01 | K6 | 46 | insert (x3); supplied 12 of 66 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 54 missing clean circuits (structures repeat: 300 in a row, 0 failed); trigger satisfied in the reset state (x3) |
| b02 | K6 | 20 | supplied 6 of 86 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 80 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| b06 | K6 | 50 | no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.2919921875, 0.272703955259; supplied 36 of 86 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 0 of 50 missing clean circuits (structures repeat: 300 in a row, 0 failed) |
| s27 | K4 | 61 | no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.11669921875, 0.10350609235; obfuscated circuit vs its source (x7); supplied 16 of 57 clean circuits (structures repeat: 60 in a row, 0 failed); supplied 31 of 43 infected circuits (5 failed proposals, 4 empty draws); top-up supplied 2 of 41 missing clean circuits (structures repeat: 300 in a row, 0 failed); trigger satisfied in the reset state (x4) |
| s27 | K6 | 40 | obfuscated circuit vs its source (x3); supplied 14 of 76 clean circuits (structures repeat: 60 in a row, 0 failed); top-up supplied 2 of 62 missing clean circuits (structures repeat: 300 in a row, 0 failed); trigger satisfied in the reset state (x7) |
| s953 | G | 90 | ValueError: bitsim: combinational loop or undriven net; no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00244140625, 0.00104324435; obfuscated circuit vs its source (x2); trigger satisfied in the reset state (x7) |

## Neutral stimulus (public, per benchmark)

One input sequence from reset per benchmark (`<benchmark>/stimulus/sequence.txt`: first line the input names, then one 0/1 row per cycle). 256 cycles requested; at each cycle 64 candidate vectors are tried from the current state of the golden and of every infected circuit of the benchmark, one on which no output differs is taken (backtracking one cycle when none exists); the finished sequence is replayed on every circuit. Inputs named reset or rst are 1 with probability 1/16.

Result: 38 benchmarks, cycles per benchmark min 4, median 256, max 256; infected circuits checked 5379; circuits differing from the golden on the final stimulus: 0; infected circuits excluded from the check: 0.

Benchmarks with a shorter stimulus (every candidate fired a Trojan beyond that point): s382 4, s349 44, s444 14, s400 102, s5378 38, s298 222.

Which circuits the stimulus was checked against stays in the answer key.

### Seq build gates against early triggers

Two gates keep Trojans that fire at the start out of the release (rc8 stays as the record). (1) Reset state: the trigger fires in the reset state for more than 1 percent of random input vectors. (2) Early trigger: the trigger is high within the first 8 cycles from reset for more than 50 percent of random input sequences (no stimulus can stay silent against it). Replaced in v2.0: round 1 (gate 1) 1,247 circuits (rc8 970, Seq top-ups 24, Si rc2 246, Si top-ups 7); round 2 (gate 2) 280 circuits (rc8 136, Si rc2 43, earlier replacement and top-up trees 101). Each replacement keeps the cell and the Trojan count of the circuit it replaced; the infected count of each cell is unchanged.


Benchmarks with a stimulus under 64 cycles: s382 4, s349 44, s444 14, s5378 38. Every candidate vector fires some Trojan beyond that point (the Trojans of the benchmark are fast-band magic triggers on registers that most paths set).

## Tools

- Odin III 1.6.0 builds the added circuits (rc circuits: rel-v160 (Odin III 1.6.0) for the added circuits; rc circuits: see their datasheets); ABC: ABC a3001b72edc5.

## Bases

b01 (ITC-99), b02 (ITC-99), b03 (ITC-99), b04 (ITC-99), b06 (ITC-99), b07 (ITC-99), b08 (ITC-99), b09 (ITC-99), b10 (ITC-99), b11 (ITC-99), b12 (ITC-99), b13 (ITC-99), ca_prng (OpenCores), i2c (OpenCores), s1196 (ISCAS-89), s1238 (ISCAS-89), s1423 (ISCAS-89), s1488 (ISCAS-89), s1494 (ISCAS-89), s208 (ISCAS-89), s27 (ISCAS-89), s298 (ISCAS-89), s344 (ISCAS-89), s349 (ISCAS-89), s382 (ISCAS-89), s386 (ISCAS-89), s400 (ISCAS-89), s420 (ISCAS-89), s444 (ISCAS-89), s510 (ISCAS-89), s526 (ISCAS-89), s5378 (ISCAS-89), s641 (ISCAS-89), s713 (ISCAS-89), s820 (ISCAS-89), s832 (ISCAS-89), s953 (ISCAS-89), sha (VTR)

## Tables

### Bases and sets

| base | source | gates |
|---|---|---|
| s27 | ISCAS-89 | 17 |
| s208 | ISCAS-89 | 42 |
| s420 | ISCAS-89 | 65 |
| s382 | ISCAS-89 | 105 |
| s386 | ISCAS-89 | 111 |
| s344 | ISCAS-89 | 114 |
| s349 | ISCAS-89 | 114 |
| s444 | ISCAS-89 | 114 |
| b02 | ITC-99 | 117 |
| s400 | ISCAS-89 | 120 |
| s641 | ISCAS-89 | 139 |
| s713 | ISCAS-89 | 141 |
| s526 | ISCAS-89 | 142 |
| b01 | ITC-99 | 149 |
| b06 | ITC-99 | 191 |
| s510 | ISCAS-89 | 213 |
| s820 | ISCAS-89 | 231 |
| s832 | ISCAS-89 | 266 |
| b03 | ITC-99 | 358 |
| s953 | ISCAS-89 | 363 |
| s1423 | ISCAS-89 | 406 |
| b09 | ITC-99 | 415 |
| s1196 | ISCAS-89 | 483 |
| b10 | ITC-99 | 511 |
| s1494 | ISCAS-89 | 518 |
| s1488 | ISCAS-89 | 522 |
| s1238 | ISCAS-89 | 529 |
| s5378 | ISCAS-89 | 989 |
| b08 | ITC-99 | 1275 |
| b13 | ITC-99 | 1650 |
| ca_prng | OpenCores | 2293 |
| b07 | ITC-99 | 2345 |
| i2c | OpenCores | 4193 |
| s298 | ISCAS-89 | 4268 |
| b04 | ITC-99 | 5034 |
| b11 | ITC-99 | 5613 |
| b12 | ITC-99 | 9153 |
| sha | VTR | 11294 |

### Set K4: 1433 infected circuits, 2390 Trojans

Trojans per circuit: 1: 746, 2: 417, 3: 270

Payload mix: p-dos-stuck 407, p-err-hi 181, p-err-lo 197, p-slowdown 1605

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| magic | fast | 513 | P(fire<=1024) | 4.79e-01 | 1.00e+00 | 1.00e+00 |
| magic | mid | 198 | P(fire<=1024) | 5.03e-02 | 2.59e-01 | 5.17e-01 |
| magic | slow | 74 | P(fire<=1024) | 9.77e-04 | 1.86e-02 | 5.91e-02 |

### Set K6: 1318 infected circuits, 2227 Trojans

Trojans per circuit: 1: 667, 2: 393, 3: 258

Payload mix: p-dos-stuck 451, p-err-hi 245, p-err-lo 223, p-slowdown 1308

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| magic | fast | 586 | P(fire<=1024) | 4.84e-01 | 1.00e+00 | 1.00e+00 |
| magic | mid | 226 | P(fire<=1024) | 4.83e-02 | 2.71e-01 | 5.07e-01 |
| magic | slow | 107 | P(fire<=1024) | 1.95e-03 | 1.86e-02 | 5.27e-02 |

### Set G: 1370 infected circuits, 2258 Trojans

Trojans per circuit: 1: 729, 2: 394, 3: 247

Payload mix: p-dos-stuck 364, p-err-hi 196, p-err-lo 196, p-slowdown 1502

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| magic | fast | 484 | P(fire<=1024) | 4.98e-01 | 1.00e+00 | 1.00e+00 |
| magic | mid | 205 | P(fire<=1024) | 5.37e-02 | 2.69e-01 | 5.23e-01 |
| magic | slow | 67 | P(fire<=1024) | 9.77e-04 | 1.17e-02 | 6.45e-02 |

### Set S: 1258 infected circuits, 2100 Trojans

Trojans per circuit: 1: 657, 2: 360, 3: 241

Payload mix: p-dos-stuck 381, p-err-hi 203, p-err-lo 217, p-slowdown 1299

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| magic | fast | 536 | P(fire<=1024) | 4.73e-01 | 1.00e+00 | 1.00e+00 |
| magic | mid | 188 | P(fire<=1024) | 4.79e-02 | 2.61e-01 | 5.18e-01 |
| magic | slow | 77 | P(fire<=1024) | 1.95e-03 | 1.66e-02 | 5.86e-02 |

### Failures and short sets

- b01 [G]: insert: ValueError: no free source for the slowdown on n26
- b01 [G]: insert: ValueError: no free source for the slowdown on n32 (x2)
- b01 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- b01 [G]: trigger satisfied in the reset state (x2)
- b01 [K4]: insert: ValueError: no free source for the slowdown on n26
- b01 [K4]: insert: ValueError: no free source for the slowdown on n29
- b01 [K4]: insert: ValueError: no free source for the slowdown on n32 (x2)
- b01 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k4)
- b01 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- b01 [K6]: insert: ValueError: no free source for the slowdown on n26
- b01 [K6]: insert: ValueError: no free source for the slowdown on n29
- b01 [K6]: insert: ValueError: no free source for the slowdown on n32
- b01 [K6]: supplied 12 of 66 clean circuits (structures repeat: 60 in a row, 0 failed)
- b01 [K6]: top-up supplied 0 of 54 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- b01 [K6]: trigger satisfied in the reset state (x3)
- b01 [S]: trigger satisfied in the reset state (x6)
- b02 [G]: trigger satisfied in the reset state
- b02 [K6]: supplied 6 of 86 clean circuits (structures repeat: 60 in a row, 0 failed)
- b02 [K6]: top-up supplied 0 of 80 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- b02 [S]: trigger satisfied in the reset state
- b03 [G]: trigger satisfied in the reset state (x4)
- b03 [K4]: trigger satisfied in the reset state (x15)
- b03 [K6]: trigger satisfied in the reset state (x9)
- b03 [S]: trigger satisfied in the reset state (x4)
- b04 [S]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.2431640625, 0.2178797420056776, 0.27
- b04 [S]: trigger satisfied in the reset state
- b06 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.59228515625, 0.5708485098887093, 0.6
- b06 [G]: trigger satisfied in the reset state
- b06 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.236328125, 0.21843305639037094, 0.25
- b06 [K4]: trigger satisfied in the reset state (x2)
- b06 [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.2919921875, 0.2727039552590325, 0.31
- b06 [K6]: supplied 36 of 86 clean circuits (structures repeat: 60 in a row, 0 failed)
- b06 [K6]: top-up supplied 0 of 50 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- b06 [S]: trigger satisfied in the reset state (x2)
- b07 [G]: trigger satisfied in the reset state (x7)
- b07 [K4]: trigger satisfied in the reset state (x16)
- b07 [K6]: trigger satisfied in the reset state (x12)
- b07 [S]: trigger satisfied in the reset state (x22)
- b08 [G]: trigger satisfied in the reset state (x2)
- b08 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64' (x2)
- b08 [K4]: trigger satisfied in the reset state (x3)
- b08 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- b08 [S]: trigger satisfied in the reset state (x6)
- b09 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.05322265625, 0.04431012481960964, 0.
- b09 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.06884765625, 0.05866951646525928, 0.
- b09 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.13232421875, 0.11833481485897701, 0.
- b10 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.2177734375, 0.20043520086249458, 0.2
- b10 [G]: trigger satisfied in the reset state (x4)
- b10 [K4]: trigger satisfied in the reset state (x16)
- b10 [K6]: trigger satisfied in the reset state (x7)
- b10 [S]: trigger satisfied in the reset state (x6)
- b11 [G]: trigger satisfied in the reset state (x43)
- b11 [K4]: trigger satisfied in the reset state (x13)
- b11 [S]: trigger satisfied in the reset state (x9)
- b12 [G]: trigger satisfied in the reset state (x17)
- b12 [K4]: trigger satisfied in the reset state (x15)
- b12 [K6]: trigger satisfied in the reset state (x9)
- b12 [S]: trigger satisfied in the reset state (x16)
- b13 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64' (x3)
- b13 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.24853515625, 0.2303004363824766, 0.2
- b13 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.99951171875, 0.9972391932191893, 0.9
- b13 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- b13 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1025390625, 0.09013601224478063, 0.1
- b13 [G]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.5048828125, 0.48323983673917914, 0.5
- b13 [G]: trigger satisfied in the reset state (x13)
- b13 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64' (x3)
- b13 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.5126953125, 0.4910436417983998, 0.53
- b13 [K4]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0634765625, 0.05371229749069399, 0.0
- b13 [K4]: trigger satisfied in the reset state (x43)
- b13 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- b13 [S]: trigger satisfied in the reset state (x5)
- ca_prng [G]: trigger satisfied in the reset state (x20)
- ca_prng [K4]: trigger satisfied in the reset state (x38)
- ca_prng [K6]: trigger satisfied in the reset state (x18)
- i2c [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64':
- i2c [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0009765625, 0.00017240363051574184, 
- i2c [G]: trigger satisfied in the reset state (x4)
- i2c [K4]: trigger satisfied in the reset state (x57)
- i2c [K6]: ValueError: bitsim: combinational loop or undriven net
- i2c [K6]: obfuscated circuit vs its source: unproven (rc 4, cuts ['dummy'], k6) (x4)
- i2c [K6]: trigger satisfied in the reset state (x21)
- s1196 [G]: trigger satisfied in the reset state (x17)
- s1196 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.03076171875, 0.02411733705645737, 0.
- s1196 [K4]: trigger satisfied in the reset state (x7)
- s1196 [K6]: trigger satisfied in the reset state (x7)
- s1196 [S]: trigger satisfied in the reset state (x11)
- s1238 [G]: trigger satisfied in the reset state (x2)
- s1238 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.02099609375, 0.015624802576243376, 0
- s1238 [K4]: trigger satisfied in the reset state (x23)
- s1238 [K6]: trigger satisfied in the reset state (x11)
- s1238 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0322265625, 0.025410847018616248, 0.
- s1238 [S]: trigger satisfied in the reset state (x14)
- s1423 [K6]: trigger satisfied in the reset state (x5)
- s1488 [G]: insert: ValueError: no free source for the slowdown on [1358]
- s1488 [K4]: trigger satisfied in the reset state (x2)
- s1488 [S]: insert: ValueError: no free source for the slowdown on n_n84 (x2)
- s1488 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s1488 [S]: trigger satisfied in the reset state (x5)
- s1494 [G]: insert: ValueError: no free source for the slowdown on [306]
- s1494 [K4]: insert: ValueError: no free source for the slowdown on n_n87
- s1494 [K4]: trigger satisfied in the reset state (x2)
- s1494 [K6]: insert: ValueError: no free source for the slowdown on [382]
- s1494 [K6]: insert: ValueError: no free source for the slowdown on [400]
- s1494 [K6]: insert: ValueError: no free source for the slowdown on n_n86
- s1494 [K6]: insert: ValueError: no free source for the slowdown on n_n87
- s1494 [S]: insert: ValueError: no free source for the slowdown on n_n87
- s1494 [S]: trigger satisfied in the reset state (x5)
- s208 [G]: supplied 54 of 67 infected circuits (0 failed proposals, 4 empty draws)
- s208 [G]: trigger satisfied in the reset state (x12)
- s208 [K4]: supplied 51 of 59 infected circuits (0 failed proposals, 4 empty draws)
- s208 [K4]: trigger satisfied in the reset state (x2)
- s208 [K6]: trigger satisfied in the reset state (x5)
- s208 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.3515625, 0.3311790608598752, 0.37250
- s208 [S]: supplied 57 of 63 infected circuits (1 failed proposals, 4 empty draws)
- s208 [S]: trigger satisfied in the reset state (x3)
- s27 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1201171875, 0.1067435368825137, 0.13
- s27 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], gates) (x2)
- s27 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], gates) (x3)
- s27 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- s27 [G]: supplied 38 of 50 infected circuits (4 failed proposals, 4 empty draws)
- s27 [G]: trigger satisfied in the reset state (x2)
- s27 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.11669921875, 0.10350609235929206, 0.
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], k4) (x2)
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k4) (x3)
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4) (x2)
- s27 [K4]: supplied 16 of 57 clean circuits (structures repeat: 60 in a row, 0 failed)
- s27 [K4]: supplied 31 of 43 infected circuits (5 failed proposals, 4 empty draws)
- s27 [K4]: top-up supplied 2 of 41 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- s27 [K4]: trigger satisfied in the reset state (x4)
- s27 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], k6) (x2)
- s27 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k6)
- s27 [K6]: supplied 14 of 76 clean circuits (structures repeat: 60 in a row, 0 failed)
- s27 [K6]: top-up supplied 2 of 62 missing clean circuits (structures repeat: 300 in a row, 0 failed)
- s27 [K6]: trigger satisfied in the reset state (x7)
- s27 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], silicon) (x3)
- s27 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], silicon) (x2)
- s27 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], silicon) (x2)
- s27 [S]: supplied 30 of 63 infected circuits (4 failed proposals, 4 empty draws)
- s27 [S]: trigger satisfied in the reset state (x8)
- s298 [G]: insert: ValueError: no free source for the slowdown on [119]
- s298 [G]: insert: ValueError: no free source for the slowdown on [135]
- s298 [G]: insert: ValueError: no free source for the slowdown on [137]
- s298 [G]: insert: ValueError: no free source for the slowdown on [138]
- s298 [G]: insert: ValueError: no free source for the slowdown on [140]
- s298 [G]: insert: ValueError: no free source for the slowdown on [168]
- s298 [G]: insert: ValueError: no free source for the slowdown on [174]
- s298 [G]: insert: ValueError: no free source for the slowdown on [175]
- s298 [G]: insert: ValueError: no free source for the slowdown on [193]
- s298 [G]: insert: ValueError: no free source for the slowdown on [210]
- s298 [G]: insert: ValueError: no free source for the slowdown on [237]
- s298 [G]: insert: ValueError: no free source for the slowdown on [256]
- s298 [G]: insert: ValueError: no free source for the slowdown on [265]
- s298 [G]: insert: ValueError: no free source for the slowdown on [287]
- s298 [G]: insert: ValueError: no free source for the slowdown on [303]
- s298 [G]: insert: ValueError: no free source for the slowdown on [317] (x2)
- s298 [G]: insert: ValueError: no free source for the slowdown on [333]
- s298 [G]: insert: ValueError: no free source for the slowdown on [340]
- s298 [G]: insert: ValueError: no free source for the slowdown on [344]
- s298 [G]: insert: ValueError: no free source for the slowdown on [35]
- s298 [G]: insert: ValueError: no free source for the slowdown on [37]
- s298 [G]: insert: ValueError: no free source for the slowdown on [382]
- s298 [G]: insert: ValueError: no free source for the slowdown on [384]
- s298 [G]: insert: ValueError: no free source for the slowdown on [416]
- s298 [G]: insert: ValueError: no free source for the slowdown on [419]
- s298 [G]: insert: ValueError: no free source for the slowdown on [428]
- s298 [G]: insert: ValueError: no free source for the slowdown on [431]
- s298 [G]: insert: ValueError: no free source for the slowdown on [455]
- s298 [G]: insert: ValueError: no free source for the slowdown on [49]
- s298 [G]: insert: ValueError: no free source for the slowdown on [510]
- s298 [G]: insert: ValueError: no free source for the slowdown on [534]
- s298 [G]: insert: ValueError: no free source for the slowdown on [5760]
- s298 [G]: insert: ValueError: no free source for the slowdown on [5964]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6009]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6341]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6347]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6350]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6360]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6367]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7189]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7195]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7196]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7219]
- s298 [G]: insert: ValueError: no free source for the slowdown on [72]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7544]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7966]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7983]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7989]
- s298 [G]: insert: ValueError: no free source for the slowdown on [8696] (x2)
- s298 [G]: insert: ValueError: no free source for the slowdown on [8699]
- s298 [G]: insert: ValueError: no free source for the slowdown on [86]
- s298 [G]: insert: ValueError: no free source for the slowdown on [8712]
- s298 [G]: insert: ValueError: no free source for the slowdown on [8717]
- s298 [G]: insert: ValueError: no free source for the slowdown on [8728]
- s298 [G]: insert: ValueError: no free source for the slowdown on [8741]
- s298 [G]: insert: ValueError: no free source for the slowdown on [9116]
- s298 [G]: insert: ValueError: no free source for the slowdown on [9138]
- s298 [G]: insert: ValueError: no free source for the slowdown on [9142]
- s298 [G]: insert: ValueError: no free source for the slowdown on [9146]
- s298 [G]: insert: ValueError: no free source for the slowdown on [9149]
- s298 [G]: insert: ValueError: no free source for the slowdown on [9159]
- s298 [G]: insert: ValueError: no free source for the slowdown on [9161]
- s298 [G]: insert: ValueError: no free source for the slowdown on n_n47 (x2)
- s298 [G]: insert: ValueError: no free source for the slowdown on n_n50
- s298 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00390625, 0.0015200565834699161, 0.0
- s298 [G]: trigger satisfied in the reset state
- s298 [K4]: insert: ValueError: no free source for the slowdown on [104]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [110]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [139]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [163]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [176]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [179]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [197]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [278]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [308]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [323]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [351]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [355]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [378]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [380]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [387]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [38]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [397]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [413]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [428]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [472]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [473]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [476]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [480]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [494]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [504]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [541]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [54]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [552]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [569]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [5792]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6004]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6018]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [61]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [62]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6327]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6328]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6329]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6347]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6372]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [6374]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7157]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7172]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7197]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7215]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7221]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [73]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7930]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7936]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7941]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7952]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7956]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7959]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7962]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7966]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7967] (x2)
- s298 [K4]: insert: ValueError: no free source for the slowdown on [7976]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [79]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [82]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [84]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8699]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [86]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8704]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8706] (x2)
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8718]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8730]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8739]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [8741]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [88]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9109]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9112]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9121]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9126]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9130]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9132]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9141]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9147]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9151]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [9159]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [92]
- s298 [K4]: insert: ValueError: no free source for the slowdown on [98]
- s298 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64':
- s298 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.01171875, 0.0067160895006905435, 0.0
- s298 [K6]: insert: ValueError: no free source for the slowdown on [108] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [110] (x3)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [128] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [129]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [134]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [162]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [164]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [169]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [172]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [173]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [177]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [180]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [182]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [189]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [192]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [194]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [197]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [206]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [219]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [226]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [235] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [237]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [239]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [242]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [243]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [244] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [246]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [249]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [252]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [255]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [256]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [25] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [267]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [290]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [295] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [29]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [300] (x3)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [301]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [302]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [304]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [312]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [314]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [315]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [317]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [31] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [323]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [324]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [328]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [330]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [340] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [343]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [34] (x3)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [351]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [355]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [357] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [36]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [370]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [379]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [384]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [388]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [397]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [398]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [39]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [413]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [420]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [422]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [428]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [429]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [439]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [445]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [449]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [452]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [457]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [458]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [462]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [469]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [473]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [476]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [477]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [478]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [47]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [483]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [490] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [499]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [508]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [511]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [51] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [524]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [526]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [52] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [533]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [536]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [53]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [541]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [544]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [545]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [546]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [54]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5694]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [569]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5742]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5760]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5777]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5784]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5792]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5964] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5990]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [5991]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6000]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6001]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6004]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6013]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6014]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6018] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6327]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6332]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6333]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6335]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6340]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6343]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6345]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6346]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6349]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6351] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6352]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6353]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6361]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6363]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6364] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6365]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6368]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6371]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6373]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [6375]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7148]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7149]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7155] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7156]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7166]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7169]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7173]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7174]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7180]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7181]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7184] (x3)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7185] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7191]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7195] (x3)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7197]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7198]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7199] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7200]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7204]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7205]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7208] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7213]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7214]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7217]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7221]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7229] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7231]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7233]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7235]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [76]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [77] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7921]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7931]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7936]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7946]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7951]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7954]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7958]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7960]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7965] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7966]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7967]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7968]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7969]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7973]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7974]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7975]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7976]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7977]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7978]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7982]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7983]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7985]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7987]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7988]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7989]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7990]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [7993]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8000] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8002]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8005]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [82]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [83]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8681] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8684]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8696]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8697]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8699]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8700] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8701]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8702] (x3)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8704]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8708] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8709]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8713] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8714]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8719]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8720]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8726]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8727]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8728]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8735]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8737]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8741]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8748]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [8749]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [87]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [88]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [89]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9106]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9107] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9109]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9116]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9119]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9127]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9128]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9130] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9132]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9133]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9136]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9140]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9141] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9143] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9147]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9148]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9150] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9155] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9159]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9160] (x2)
- s298 [K6]: insert: ValueError: no free source for the slowdown on [9161]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [95]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [98]
- s298 [K6]: insert: ValueError: no free source for the slowdown on [99]
- s298 [K6]: insert: ValueError: no free source for the slowdown on n_n45
- s298 [K6]: insert: ValueError: no free source for the slowdown on n_n47 (x3)
- s298 [K6]: insert: ValueError: no free source for the slowdown on n_n50 (x2)
- s298 [K6]: supplied 58 of 59 infected circuits (300 failed proposals, 0 empty draws)
- s298 [S]: insert: ValueError: no free source for the slowdown on [110]
- s298 [S]: insert: ValueError: no free source for the slowdown on [124]
- s298 [S]: insert: ValueError: no free source for the slowdown on [132]
- s298 [S]: insert: ValueError: no free source for the slowdown on [135]
- s298 [S]: insert: ValueError: no free source for the slowdown on [140]
- s298 [S]: insert: ValueError: no free source for the slowdown on [167]
- s298 [S]: insert: ValueError: no free source for the slowdown on [168]
- s298 [S]: insert: ValueError: no free source for the slowdown on [169]
- s298 [S]: insert: ValueError: no free source for the slowdown on [173]
- s298 [S]: insert: ValueError: no free source for the slowdown on [175]
- s298 [S]: insert: ValueError: no free source for the slowdown on [176]
- s298 [S]: insert: ValueError: no free source for the slowdown on [177] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [180]
- s298 [S]: insert: ValueError: no free source for the slowdown on [190]
- s298 [S]: insert: ValueError: no free source for the slowdown on [198]
- s298 [S]: insert: ValueError: no free source for the slowdown on [204]
- s298 [S]: insert: ValueError: no free source for the slowdown on [211]
- s298 [S]: insert: ValueError: no free source for the slowdown on [212]
- s298 [S]: insert: ValueError: no free source for the slowdown on [219] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [228]
- s298 [S]: insert: ValueError: no free source for the slowdown on [235]
- s298 [S]: insert: ValueError: no free source for the slowdown on [236]
- s298 [S]: insert: ValueError: no free source for the slowdown on [237]
- s298 [S]: insert: ValueError: no free source for the slowdown on [239]
- s298 [S]: insert: ValueError: no free source for the slowdown on [240]
- s298 [S]: insert: ValueError: no free source for the slowdown on [243]
- s298 [S]: insert: ValueError: no free source for the slowdown on [244]
- s298 [S]: insert: ValueError: no free source for the slowdown on [245] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [246]
- s298 [S]: insert: ValueError: no free source for the slowdown on [249]
- s298 [S]: insert: ValueError: no free source for the slowdown on [251]
- s298 [S]: insert: ValueError: no free source for the slowdown on [254]
- s298 [S]: insert: ValueError: no free source for the slowdown on [258]
- s298 [S]: insert: ValueError: no free source for the slowdown on [259]
- s298 [S]: insert: ValueError: no free source for the slowdown on [278]
- s298 [S]: insert: ValueError: no free source for the slowdown on [286]
- s298 [S]: insert: ValueError: no free source for the slowdown on [292] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [296]
- s298 [S]: insert: ValueError: no free source for the slowdown on [299]
- s298 [S]: insert: ValueError: no free source for the slowdown on [29]
- s298 [S]: insert: ValueError: no free source for the slowdown on [307]
- s298 [S]: insert: ValueError: no free source for the slowdown on [311]
- s298 [S]: insert: ValueError: no free source for the slowdown on [312]
- s298 [S]: insert: ValueError: no free source for the slowdown on [315]
- s298 [S]: insert: ValueError: no free source for the slowdown on [317]
- s298 [S]: insert: ValueError: no free source for the slowdown on [322]
- s298 [S]: insert: ValueError: no free source for the slowdown on [326] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [327]
- s298 [S]: insert: ValueError: no free source for the slowdown on [331]
- s298 [S]: insert: ValueError: no free source for the slowdown on [343] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [353]
- s298 [S]: insert: ValueError: no free source for the slowdown on [371]
- s298 [S]: insert: ValueError: no free source for the slowdown on [374]
- s298 [S]: insert: ValueError: no free source for the slowdown on [37]
- s298 [S]: insert: ValueError: no free source for the slowdown on [380]
- s298 [S]: insert: ValueError: no free source for the slowdown on [384]
- s298 [S]: insert: ValueError: no free source for the slowdown on [389]
- s298 [S]: insert: ValueError: no free source for the slowdown on [39]
- s298 [S]: insert: ValueError: no free source for the slowdown on [400]
- s298 [S]: insert: ValueError: no free source for the slowdown on [414] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [419]
- s298 [S]: insert: ValueError: no free source for the slowdown on [422]
- s298 [S]: insert: ValueError: no free source for the slowdown on [429]
- s298 [S]: insert: ValueError: no free source for the slowdown on [432]
- s298 [S]: insert: ValueError: no free source for the slowdown on [441]
- s298 [S]: insert: ValueError: no free source for the slowdown on [445]
- s298 [S]: insert: ValueError: no free source for the slowdown on [448]
- s298 [S]: insert: ValueError: no free source for the slowdown on [449]
- s298 [S]: insert: ValueError: no free source for the slowdown on [454]
- s298 [S]: insert: ValueError: no free source for the slowdown on [469]
- s298 [S]: insert: ValueError: no free source for the slowdown on [46]
- s298 [S]: insert: ValueError: no free source for the slowdown on [472] (x3)
- s298 [S]: insert: ValueError: no free source for the slowdown on [473]
- s298 [S]: insert: ValueError: no free source for the slowdown on [474]
- s298 [S]: insert: ValueError: no free source for the slowdown on [476]
- s298 [S]: insert: ValueError: no free source for the slowdown on [478]
- s298 [S]: insert: ValueError: no free source for the slowdown on [47]
- s298 [S]: insert: ValueError: no free source for the slowdown on [484]
- s298 [S]: insert: ValueError: no free source for the slowdown on [48]
- s298 [S]: insert: ValueError: no free source for the slowdown on [490]
- s298 [S]: insert: ValueError: no free source for the slowdown on [494]
- s298 [S]: insert: ValueError: no free source for the slowdown on [49]
- s298 [S]: insert: ValueError: no free source for the slowdown on [504]
- s298 [S]: insert: ValueError: no free source for the slowdown on [505]
- s298 [S]: insert: ValueError: no free source for the slowdown on [522]
- s298 [S]: insert: ValueError: no free source for the slowdown on [52]
- s298 [S]: insert: ValueError: no free source for the slowdown on [536]
- s298 [S]: insert: ValueError: no free source for the slowdown on [545]
- s298 [S]: insert: ValueError: no free source for the slowdown on [563] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [569]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5700]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5742]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5778]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5784]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5786]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5863]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5958]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5986]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5991]
- s298 [S]: insert: ValueError: no free source for the slowdown on [5999]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6001]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6005]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6006]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6007] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [6015]
- s298 [S]: insert: ValueError: no free source for the slowdown on [60]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6317]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6344]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6345]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6352]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6353] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [6363]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6364]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6371]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6373]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6374]
- s298 [S]: insert: ValueError: no free source for the slowdown on [6376]
- s298 [S]: insert: ValueError: no free source for the slowdown on [70]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7148] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [7149] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [7163]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7165]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7166]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7170]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7175]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7176]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7177]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7178]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7181]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7184]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7185]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7186]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7188]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7189]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7199]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7202]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7203]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7207]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7210]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7215]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7219]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7222]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7231]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7232]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7233]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7234]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7562]
- s298 [S]: insert: ValueError: no free source for the slowdown on [76]
- s298 [S]: insert: ValueError: no free source for the slowdown on [77]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7920]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7921]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7922]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7935]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7936]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7938]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7939]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7940]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7941]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7944]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7947]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7950]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7960]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7964]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7969]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7972]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7973]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7977]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7978]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7979]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7980]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7981]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7984]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7986]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7987]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7988]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7989]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7991]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7992]
- s298 [S]: insert: ValueError: no free source for the slowdown on [7995] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [8003]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8004]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8007] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [82]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8682]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8683]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8691] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [8694]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8697]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8705]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8706]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8709]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8711]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8714]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8716] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [8721]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8723]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8724] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [8733]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8738] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [8740]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8741]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8744]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8748]
- s298 [S]: insert: ValueError: no free source for the slowdown on [8749]
- s298 [S]: insert: ValueError: no free source for the slowdown on [87]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9107] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [9109]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9111] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [9112] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [9115]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9116]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9121]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9131]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9132]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9134] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [9136]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9138] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [9139]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9140]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9141]
- s298 [S]: insert: ValueError: no free source for the slowdown on [9152]
- s298 [S]: insert: ValueError: no free source for the slowdown on [92] (x2)
- s298 [S]: insert: ValueError: no free source for the slowdown on [93]
- s298 [S]: insert: ValueError: no free source for the slowdown on n_n46
- s298 [S]: insert: ValueError: no free source for the slowdown on n_n48
- s298 [S]: insert: ValueError: no free source for the slowdown on n_n49
- s298 [S]: insert: ValueError: no free source for the slowdown on n_n52
- s344 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.10791015625, 0.09519903405030236, 0.
- s344 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.27783203125, 0.25886171242357475, 0.
- s344 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.11572265625, 0.10258179928839385, 0.
- s344 [G]: trigger satisfied in the reset state (x12)
- s344 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.01904296875, 0.013961353046915825, 0
- s344 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0791015625, 0.0681846616121859, 0.09
- s344 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.34814453125, 0.32781396092168197, 0.
- s344 [K4]: trigger satisfied in the reset state (x11)
- s344 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.09228515625, 0.08050179174781386, 0.
- s344 [K6]: trigger satisfied in the reset state (x5)
- s344 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.009765625, 0.006330571418592489, 0.0
- s344 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0234375, 0.01772301744316744, 0.0309
- s344 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.95361328125, 0.9436239128679698, 0.9
- s344 [S]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.03125, 0.02454803158681001, 0.039707
- s344 [S]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.5654296875, 0.5438580116256874, 0.58
- s344 [S]: trigger satisfied in the reset state (x11)
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.02001953125, 0.014791263102419317, 0
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.16162109375, 0.14631432516343038, 0.
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1728515625, 0.15709150977171654, 0.1
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.82470703125, 0.8076359563870672, 0.8
- s349 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00830078125, 0.005189032228861925, 0
- s349 [G]: trigger satisfied in the reset state (x8)
- s349 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.03125, 0.02454803158681001, 0.039707
- s349 [K4]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.087890625, 0.07638672436128222, 0.10
- s349 [K4]: trigger satisfied in the reset state (x14)
- s349 [K6]: trigger satisfied in the reset state (x8)
- s349 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.19091796875, 0.17448074553124598, 0.
- s349 [S]: trigger satisfied in the reset state (x9)
- s382 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- s382 [G]: trigger satisfied in the reset state (x4)
- s382 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s382 [K4]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s382 [K4]: trigger satisfied in the reset state (x2)
- s382 [K6]: trigger satisfied in the reset state
- s382 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.49951171875, 0.4778777796963146, 0.5
- s382 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], silicon)
- s382 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], silicon)
- s382 [S]: trigger satisfied in the reset state (x2)
- s386 [G]: trigger satisfied in the reset state (x7)
- s386 [K4]: trigger satisfied in the reset state (x2)
- s386 [K6]: trigger satisfied in the reset state
- s386 [S]: trigger satisfied in the reset state (x4)
- s400 [G]: trigger satisfied in the reset state (x2)
- s400 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s400 [K4]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s400 [K4]: trigger satisfied in the reset state
- s400 [K6]: trigger satisfied in the reset state (x6)
- s400 [S]: trigger satisfied in the reset state (x4)
- s420 [G]: trigger satisfied in the reset state (x4)
- s420 [K4]: trigger satisfied in the reset state (x19)
- s420 [K6]: trigger satisfied in the reset state (x11)
- s420 [S]: trigger satisfied in the reset state (x18)
- s444 [K4]: trigger satisfied in the reset state (x7)
- s444 [K6]: trigger satisfied in the reset state (x15)
- s444 [S]: trigger satisfied in the reset state (x8)
- s510 [G]: trigger satisfied in the reset state (x14)
- s510 [K4]: trigger satisfied in the reset state (x26)
- s510 [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s510 [K6]: trigger satisfied in the reset state (x14)
- s510 [S]: trigger satisfied in the reset state (x19)
- s526 [G]: trigger satisfied in the reset state (x3)
- s526 [K4]: trigger satisfied in the reset state (x2)
- s526 [S]: trigger satisfied in the reset state
- s5378 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow2'], gates)
- s5378 [G]: trigger satisfied in the reset state (x7)
- s5378 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s5378 [K4]: trigger satisfied in the reset state (x18)
- s5378 [K6]: trigger satisfied in the reset state (x4)
- s5378 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s5378 [S]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.2529296875, 0.23457762151117248, 0.2
- s5378 [S]: trigger satisfied in the reset state (x5)
- s641 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], gates)
- s641 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- s641 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1'], gates)
- s641 [G]: trigger satisfied in the reset state (x86)
- s641 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], k4)
- s641 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- s641 [K4]: trigger satisfied in the reset state (x47)
- s641 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1'], k6) (x2)
- s641 [K6]: trigger satisfied in the reset state (x25)
- s641 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], silicon)
- s641 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], silicon) (x2)
- s641 [S]: trigger satisfied in the reset state (x56)
- s713 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow2'], gates)
- s713 [G]: trigger satisfied in the reset state (x89)
- s713 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], k4)
- s713 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k4)
- s713 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- s713 [K4]: trigger satisfied in the reset state (x43)
- s713 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1'], k6)
- s713 [K6]: trigger satisfied in the reset state (x57)
- s713 [S]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], silicon)
- s713 [S]: trigger satisfied in the reset state (x45)
- s820 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.400390625, 0.37937510666579893, 0.42
- s820 [G]: trigger satisfied in the reset state (x4)
- s820 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00732421875, 0.004443571288938689, 0
- s820 [K4]: trigger satisfied in the reset state (x17)
- s820 [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1591796875, 0.14397498777923215, 0.1
- s820 [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.74462890625, 0.7252967243747811, 0.7
- s820 [K6]: trigger satisfied in the reset state (x10)
- s820 [S]: trigger satisfied in the reset state (x12)
- s832 [G]: trigger satisfied in the reset state (x5)
- s832 [K4]: trigger satisfied in the reset state (x18)
- s832 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00048828125, 8.619661360354078e-05, 
- s832 [K6]: trigger satisfied in the reset state (x5)
- s832 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s832 [S]: trigger satisfied in the reset state (x6)
- s953 [G]: ValueError: bitsim: combinational loop or undriven net
- s953 [G]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00244140625, 0.001043244356575213, 0
- s953 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates) (x2)
- s953 [G]: trigger satisfied in the reset state (x7)
- s953 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1', 'slow2'], k4)
- s953 [K4]: trigger satisfied in the reset state (x13)
- s953 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s953 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k6)
- s953 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow2'], k6)
- s953 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k6)
- s953 [K6]: trigger satisfied in the reset state (x4)
- s953 [S]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.001953125, 0.000759773904391043, 0.0
- s953 [S]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00146484375, 0.0004982923261750531, 
- s953 [S]: trigger satisfied in the reset state (x5)
- sha [G]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64':
- sha [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': (x3)
- sha [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': (x6)
- sha [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64':
- sha [K6]: trigger satisfied in the reset state (x6)

## Check

`sha256sum -c SHA256SUMS`, then `lemanruss verify <dir>`.
