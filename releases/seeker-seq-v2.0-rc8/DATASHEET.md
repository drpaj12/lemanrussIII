# seeker-seq-v2.0-rc8 datasheet

Family: Seeker-Seq. Version 2.0-rc8 (release candidate). Produced by Leman Russ III (Yggdrasil III).

Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.

## Lineage

v1 = Caroline van Neste's master's thesis (in progress; no unpublished results are cited). v2.0: sequential bases (ISCAS-89, ITC-99, VTR and OpenCores sequential designs), magic-number triggers (rc7), multi-cycle rareness.

## Contents

- circuits: 11005 in `circuits/<id>.blif.gz` (gzip, zero timestamp), 6813 clean and 4192 infected, opaque ids.
- bases: 38; per base one golden and up to three sets of 100 circuits (LUT k = 4, LUT k = 6, AND/OR/NOT gates).
- answer key: `answer_key/` (labels, sets, Trojans, ABC scripts, rareness, witnesses, and `pre/<id>.blif.gz`, each infected circuit before obfuscation); a detector must not read it.

Circuits per base:

b01 247, b02 221, b03 301, b04 301, b06 251, b07 301, b08 301, b09 301, b10 301, b11 301, b12 301, b13 301, ca_prng 301, i2c 201, s1196 301, s1238 301, s1423 301, s1488 301, s1494 301, s208 280, s27 174, s298 300, s344 301, s349 301, s382 301, s386 301, s400 301, s420 301, s444 301, s510 301, s526 301, s5378 301, s641 301, s713 301, s820 301, s832 301, s953 301, sha 301

## Design (round 8, rc4; rc5 latch fix; rc5 Comb / rc6 Seq cut-and-stitch)

Per base: the golden (its id is in `manifest.json` under `goldens`) and three sets of 100 circuits: LUT k = 4, LUT k = 6, and an AND / OR / NOT gate library. In each set a random number between 10 and 70 of the circuits is infected, with 1 to 3 Trojans each (stuck output, bit error on an upper-half or lower-half output, and in rc5 / rc6 energy ring and slowdown); the others are clean. Every circuit other than the golden, clean or infected, is one Trojan insertion (infected only), then its own random ABC logic-optimisation script, then the set's mapping by Odin III, then shuffled ports and blocks and fresh net names; there is no provenance in the files. Which circuits are infected, the set, the script and the Trojans are in the answer key only. A base that cannot supply 100 distinct circuits in a set has fewer (never padded with copies); the counts are in `answer_key/sets.json` and in the tables below. Every infected circuit has, per Trojan, a witness input sequence (`answer_key/witnesses/`) replayed in Odin III's simulator on the finished circuit against the golden, and is equivalent to its pre-obfuscation form (`answer_key/pre/`), which equals the golden with all triggers forced inactive (ABC cec / dsec). Energy-ring (Seq only) and slowdown payloads are in the releases rc5 (Comb) and rc6 (Seq) through cut-and-stitch: the part ABC would destroy is cut out, its boundary exposed as primary inputs/outputs, host and part are each optimised and mapped, and the pieces are stitched back; every circuit, clean or infected, is cut (a clean or payload-free circuit on a dummy region of the same size distribution). The slowdown is an absorption stage `tmp | (tmp & s) ...` (equal to `tmp`, adds depth, always on), not a buffer chain. Spec section 13. rc5: the Trojan's flip-flops carry the circuit's own `.latch` type, clock and init value (rc4 gave them init 0 where every other latch has 2, which separated the labels); a pattern trigger's first stage is a two-input cell and the trigger is the sticky flag itself, so no inverter or duplicated node sits in front of a Trojan latch. All latches start unknown (init 2), read as 0 by every tool of the pipeline.

## rc7 (round 9): magic-number triggers (rc8: unchanged)

Every Trojan trigger is a magic-number comparator: an AND of literals on nets that already exist in the host (flip-flop outputs and primary inputs). It adds no flip-flop and no latch, and the energy payload (the one payload that adds flip-flops) is not used. Before ABC, each infected circuit has exactly the flip-flop and latch count of its golden (a hard build gate). The value is drawn from the golden's random multi-cycle simulation: it is reached at least once and its probability of being high within 1024 cycles lies in the fast, mid or slow band. Payloads: stuck output, bit error on an upper-half or lower-half output, and the always-on slowdown. Spec section 13.

## rc8: OpenCores bases

The 36 rc7 bases (circuits, answer key and witnesses) are carried over byte for byte; rc8 adds 2 OpenCores bases (ca_prng, i2c) built as rc7 builds them (same construction and gates), with Odin III rel-v150 reading the RTL (`read_verilog; proc; opt; flatten; opt; lower`). The set stays flip-flops only, no memories. Reset style: Odin III lowers asynchronous reset / set to synchronous logic (its warning is kept in the run record), so the netlists differ from the RTL on reset timing. Only projects whose licence clearly permits redistribution of derived netlists without copyleft terms are included; the others are listed below with their licence and left out.

### OpenCores candidates

| base | wave | licence | read at | verdict |
|---|---|---|---|---|
| ca_prng | 1 | BSD-3-Clause style (InformAsic AB) | COPYING.txt:1-5; src/rtl/ca_prng.v:16-19 | included |
| mmuart | 1 | GPL-3.0 | rtl/uart.v:6-7 | excluded, licence: copyleft: GPL-3.0, left out with the licence noted |
| simple_spi | 1 | permissive notice in the file headers: 'This source file may be used and distributed without restriction provided that this copyright statement is not removed from the file and that any derivative work contains the original copyright notice and the associated disclaimer.' | rtl/verilog/simple_spi_top.v:11-20 | excluded, memory: memory: rtl/verilog/fifo4.v:77 `reg [dw:1] mem[0:3]` (a 4-entry FIFO array; lowered to flip-flops it is still a memory) |
| i2cslave | 1 | LGPL-2.1+ per file header (the OpenCores page says GPL: mismatch; either licence permits redistribution) | rtl/i2cSlave.v:27-30 | excluded, licence: copyleft: LGPL-2.1+, left out with the licence noted |
| sdram_16bit | 1 | GPL-2.0+ | rtl/sdram.v:9,15-17 | excluded, memory: memory: rtl/sdram.v:151 `reg [SDRAM_ROW_W-1:0] active_row_q[0:SDRAM_BANKS-1]` (Odin III: 'replacing memory active_row_q with list of registers'); also vendor primitives ODDR2 / IOBUF (rtl/sdram.v:689,709) and an inout top port |
| i2c | 1 | permissive notice in the file headers: 'This source file may be used and distributed without restriction provided that this copyright statement is not removed from the file and that any derivative work contains the original copyright notice and the associated disclaimer.' (Richard Herveille, 2001) | rtl/verilog/i2c_master_top.v:17-20 | included |
| spi | 1 | LGPL-2.1+ per file header | rtl/verilog/spi_top.v:24-26 | excluded, licence: copyleft: LGPL-2.1+, left out with the licence noted |
| uart2spi | 1 | LGPL-2.1+ per file header (top.v) | rtl/top/top.v header | excluded, licence: copyleft: LGPL-2.1+, left out with the licence noted |
| wb_lcd | 2 | LGPL-3.0+ per file header | verilog/wb_lcd/rtl/wb_lcd.v:27-30 | excluded, memory: memory: verilog/wb_lcd/rtl/lcd_display.v:114 `reg [`DAT_WIDTH-1:0] ram [0:`MEM_LENGTH-1]` (the character RAM; it is in the 660 flip-flops) |
| verilog_cordic_core | 2 | none stated (no licence text in cordic.v or the project; the OpenCores page has none) | cordic.v:1-12 | excluded, licence: none stated: licence unclear (none stated), so not redistributed; also cordic.v:178 has a non-constant for-loop bound that Odin III rejects (Mimir builds a patched variant) |
| sdr_ctrl | 2 | LGPL-2.1+ per file header | rtl/top/sdrc_top.v:44-46 | excluded, licence: copyleft: LGPL-2.1+, left out with the licence noted |
| des | 2 | permissive notice in the file headers: 'This source file may be used and distributed without restriction provided that this copyright statement is not removed from the file and that any derivative work contains the original copyright notice and the associated disclaimer.' (Rudolf Usselmann, 2001) | rtl/verilog/perf_opt/des.v:11-20 | excluded, size: des, left out per owner: left out per owner (size: 124035 gates, 1984 flip-flops) |

## Rareness

Seeker-Seq rc7 / rc8: magic-number triggers (an AND of literals on existing register outputs and primary inputs, no added flip-flop), three speed bands each defined by P(trigger high at least once within 1024 cycles) over random multi-cycle simulation of the golden: fast 0.5-1, mid 0.05-0.5, slow 0.003-0.05.
Rareness is measured on the circuit before obfuscation (`pre/`), where the trigger net exists.

### Bases and sets

| base | source | gates | K4 drawn / infected / clean | K6 drawn / infected / clean | G drawn / infected / clean |
|---|---|---|---|---|---|
| s27 | ISCAS-89 | 17 | 43 / 31 / 16 | 24 / 24 / 14 | 50 / 38 / 50 |
| s208 | ISCAS-89 | 42 | 59 / 51 / 41 | 30 / 30 / 70 | 67 / 54 / 33 |
| s420 | ISCAS-89 | 65 | 55 / 55 / 45 | 49 / 49 / 51 | 11 / 11 / 89 |
| s382 | ISCAS-89 | 105 | 20 / 20 / 80 | 22 / 22 / 78 | 44 / 44 / 56 |
| s386 | ISCAS-89 | 111 | 60 / 60 / 40 | 34 / 34 / 66 | 43 / 43 / 57 |
| s344 | ISCAS-89 | 114 | 25 / 25 / 75 | 23 / 23 / 77 | 34 / 34 / 66 |
| s349 | ISCAS-89 | 114 | 46 / 46 / 54 | 28 / 28 / 72 | 67 / 67 / 33 |
| s444 | ISCAS-89 | 114 | 36 / 36 / 64 | 52 / 52 / 48 | 67 / 67 / 33 |
| b02 | ITC-99 | 117 | 11 / 11 / 89 | 14 / 14 / 6 | 21 / 21 / 79 |
| s400 | ISCAS-89 | 120 | 70 / 70 / 30 | 22 / 22 / 78 | 17 / 17 / 83 |
| s641 | ISCAS-89 | 139 | 40 / 40 / 60 | 36 / 36 / 64 | 49 / 49 / 51 |
| s713 | ISCAS-89 | 141 | 48 / 48 / 52 | 68 / 68 / 32 | 32 / 32 / 68 |
| s526 | ISCAS-89 | 142 | 11 / 11 / 89 | 40 / 40 / 60 | 29 / 29 / 71 |
| b01 | ITC-99 | 149 | 56 / 56 / 44 | 34 / 34 / 12 | 38 / 38 / 62 |
| b06 | ITC-99 | 191 | 28 / 28 / 72 | 14 / 14 / 36 | 66 / 66 / 34 |
| s510 | ISCAS-89 | 213 | 56 / 56 / 44 | 55 / 55 / 45 | 63 / 63 / 37 |
| s820 | ISCAS-89 | 231 | 40 / 40 / 60 | 26 / 26 / 74 | 13 / 13 / 87 |
| s832 | ISCAS-89 | 266 | 20 / 20 / 80 | 23 / 23 / 77 | 17 / 17 / 83 |
| b03 | ITC-99 | 358 | 18 / 18 / 82 | 53 / 53 / 47 | 48 / 48 / 52 |
| s953 | ISCAS-89 | 363 | 35 / 35 / 65 | 40 / 40 / 60 | 18 / 18 / 82 |
| s1423 | ISCAS-89 | 406 | 22 / 22 / 78 | 26 / 26 / 74 | 28 / 28 / 72 |
| b09 | ITC-99 | 415 | 45 / 45 / 55 | 48 / 48 / 52 | 11 / 11 / 89 |
| s1196 | ISCAS-89 | 483 | 12 / 12 / 88 | 20 / 20 / 80 | 19 / 19 / 81 |
| b10 | ITC-99 | 511 | 57 / 57 / 43 | 46 / 46 / 54 | 34 / 34 / 66 |
| s1494 | ISCAS-89 | 518 | 26 / 26 / 74 | 44 / 44 / 56 | 23 / 23 / 77 |
| s1488 | ISCAS-89 | 522 | 56 / 56 / 44 | 55 / 55 / 45 | 42 / 42 / 58 |
| s1238 | ISCAS-89 | 529 | 30 / 30 / 70 | 30 / 30 / 70 | 25 / 25 / 75 |
| s5378 | ISCAS-89 | 989 | 61 / 61 / 39 | 38 / 38 / 62 | 29 / 29 / 71 |
| b08 | ITC-99 | 1275 | 16 / 16 / 84 | 62 / 62 / 38 | 16 / 16 / 84 |
| b13 | ITC-99 | 1650 | 35 / 35 / 65 | 11 / 11 / 89 | 68 / 68 / 32 |
| ca_prng | OpenCores | 2293 | 64 / 64 / 36 | 43 / 43 / 57 | 46 / 46 / 54 |
| b07 | ITC-99 | 2345 | 15 / 15 / 85 | 37 / 37 / 63 | 47 / 47 / 53 |
| i2c | OpenCores | 4193 | 70 / 70 / 30 | -  | 49 / 49 / 51 |
| s298 | ISCAS-89 | 4268 | 26 / 26 / 74 | 59 / 58 / 41 | 24 / 24 / 76 |
| b04 | ITC-99 | 5034 | 54 / 54 / 46 | 36 / 36 / 64 | 27 / 27 / 73 |
| b11 | ITC-99 | 5613 | 17 / 17 / 83 | 10 / 10 / 90 | 47 / 47 / 53 |
| b12 | ITC-99 | 9153 | 52 / 52 / 48 | 60 / 60 / 40 | 47 / 47 / 53 |
| sha | VTR | 11294 | 41 / 41 / 59 | 62 / 62 / 38 | 12 / 12 / 88 |

### Set K4: 1456 infected circuits, 2435 Trojans

Trojans per circuit: 1: 753, 2: 427, 3: 276

Payload mix: p-dos-stuck 569, p-err-hi 276, p-err-lo 272, p-slowdown 1318

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| magic | fast | 909 | P(fire<=1024) | 4.79e-01 | 1.00e+00 | 1.00e+00 |
| magic | mid | 154 | P(fire<=1024) | 6.35e-02 | 2.89e-01 | 5.17e-01 |
| magic | slow | 54 | P(fire<=1024) | 9.77e-04 | 1.76e-02 | 5.03e-02 |

### Set K6: 1373 infected circuits, 2313 Trojans

Trojans per circuit: 1: 696, 2: 414, 3: 263

Payload mix: p-dos-stuck 532, p-err-hi 288, p-err-lo 282, p-slowdown 1211

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| magic | fast | 908 | P(fire<=1024) | 2.18e-01 | 1.00e+00 | 1.00e+00 |
| magic | mid | 112 | P(fire<=1024) | 4.83e-02 | 2.66e-01 | 5.07e-01 |
| magic | slow | 82 | P(fire<=1024) | 9.77e-04 | 1.56e-02 | 5.27e-02 |

### Set G: 1363 infected circuits, 2246 Trojans

Trojans per circuit: 1: 723, 2: 397, 3: 243

Payload mix: p-dos-stuck 468, p-err-hi 224, p-err-lo 254, p-slowdown 1300

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| magic | fast | 721 | P(fire<=1024) | 4.98e-01 | 1.00e+00 | 1.00e+00 |
| magic | mid | 169 | P(fire<=1024) | 5.37e-02 | 2.72e-01 | 5.23e-01 |
| magic | slow | 56 | P(fire<=1024) | 1.95e-03 | 1.27e-02 | 6.45e-02 |

### Failures and short sets

- b01 [G]: insert: ValueError: no free source for the slowdown on n26
- b01 [G]: insert: ValueError: no free source for the slowdown on n32 (x2)
- b01 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- b01 [K4]: insert: ValueError: no free source for the slowdown on n26
- b01 [K4]: insert: ValueError: no free source for the slowdown on n29
- b01 [K4]: insert: ValueError: no free source for the slowdown on n32 (x2)
- b01 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k4)
- b01 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- b01 [K6]: insert: ValueError: no free source for the slowdown on n26
- b01 [K6]: insert: ValueError: no free source for the slowdown on n29
- b01 [K6]: insert: ValueError: no free source for the slowdown on n32
- b01 [K6]: supplied 12 of 66 clean circuits (structures repeat: 60 in a row, 0 failed)
- b02 [K6]: supplied 6 of 86 clean circuits (structures repeat: 60 in a row, 0 failed)
- b06 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.59228515625, 0.5708485098887093, 0.6
- b06 [K6]: supplied 36 of 86 clean circuits (structures repeat: 60 in a row, 0 failed)
- b08 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64' (x2)
- b08 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- b09 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.05322265625, 0.04431012481960964, 0.
- b09 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.06884765625, 0.05866951646525928, 0.
- b09 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.13232421875, 0.11833481485897701, 0.
- b13 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64' (x2)
- b13 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.24853515625, 0.2303004363824766, 0.2
- b13 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.99951171875, 0.9972391932191893, 0.9
- b13 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- b13 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1025390625, 0.09013601224478063, 0.1
- b13 [G]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.5048828125, 0.48323983673917914, 0.5
- b13 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- b13 [K4]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0634765625, 0.05371229749069399, 0.0
- b13 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- i2c [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0009765625, 0.00017240363051574184, 
- i2c [K6]: ValueError: bitsim: combinational loop or undriven net
- s1196 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.03076171875, 0.02411733705645737, 0.
- s1488 [G]: insert: ValueError: no free source for the slowdown on [1358]
- s1494 [G]: insert: ValueError: no free source for the slowdown on [306]
- s1494 [K4]: insert: ValueError: no free source for the slowdown on n_n87
- s1494 [K6]: insert: ValueError: no free source for the slowdown on [382]
- s1494 [K6]: insert: ValueError: no free source for the slowdown on [400]
- s1494 [K6]: insert: ValueError: no free source for the slowdown on n_n86
- s1494 [K6]: insert: ValueError: no free source for the slowdown on n_n87
- s208 [G]: supplied 54 of 67 infected circuits (0 failed proposals, 4 empty draws)
- s208 [K4]: supplied 51 of 59 infected circuits (0 failed proposals, 4 empty draws)
- s27 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1201171875, 0.1067435368825137, 0.13
- s27 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], gates)
- s27 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], gates)
- s27 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- s27 [G]: supplied 38 of 50 infected circuits (4 failed proposals, 4 empty draws)
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], k4)
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k4) (x2)
- s27 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- s27 [K4]: supplied 16 of 57 clean circuits (structures repeat: 60 in a row, 0 failed)
- s27 [K4]: supplied 31 of 43 infected circuits (5 failed proposals, 4 empty draws)
- s27 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1', 'slow2'], k6) (x2)
- s27 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k6)
- s27 [K6]: supplied 14 of 76 clean circuits (structures repeat: 60 in a row, 0 failed)
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
- s298 [G]: insert: ValueError: no free source for the slowdown on [6350]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6360]
- s298 [G]: insert: ValueError: no free source for the slowdown on [6367]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7189]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7196]
- s298 [G]: insert: ValueError: no free source for the slowdown on [72]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7544]
- s298 [G]: insert: ValueError: no free source for the slowdown on [7966]
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
- s344 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.10791015625, 0.09519903405030236, 0.
- s344 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.27783203125, 0.25886171242357475, 0.
- s344 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.11572265625, 0.10258179928839385, 0.
- s344 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.01904296875, 0.013961353046915825, 0
- s344 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.09228515625, 0.08050179174781386, 0.
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.02001953125, 0.014791263102419317, 0
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.16162109375, 0.14631432516343038, 0.
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1728515625, 0.15709150977171654, 0.1
- s349 [G]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.82470703125, 0.8076359563870672, 0.8
- s349 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00830078125, 0.005189032228861925, 0
- s382 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates)
- s382 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s382 [K4]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s400 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s400 [K4]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [1.0, 0.9981277307176147, 0.99999999999
- s510 [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s5378 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow2'], gates)
- s5378 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64'
- s641 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], gates)
- s641 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1'], gates)
- s641 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- s713 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k4)
- s820 [G]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.400390625, 0.37937510666579893, 0.42
- s820 [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00732421875, 0.004443571288938689, 0
- s820 [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.1591796875, 0.14397498777923215, 0.1
- s820 [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.74462890625, 0.7252967243747811, 0.7
- s832 [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.00048828125, 8.619661360354078e-05, 
- s953 [G]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], gates) (x2)
- s953 [K4]: obfuscated circuit vs its source: error (rc 2, cuts ['slow1', 'slow2'], k4)
- s953 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0', 'slow1'], k6)
- s953 [K6]: obfuscated circuit vs its source: error (rc 2, cuts ['slow0'], k6)
- sha [G]: no witness for Trojan 2 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64':
- sha [K4]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': (x3)
- sha [K6]: no witness for Trojan 0 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': (x2)
- sha [K6]: no witness for Trojan 1 (p-dos-stuck, magic): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64':

## Bases and licences

- ISCAS-89 (23: s1196, s1238, s1423, s1488, s1494, s208, s27, s298, s344, s349, s382, s386, s400, s420, s444, s510, s526, s5378, s641, s713, s820, s832, s953): licence unread (the ISCAS licence has not been read).
- ITC-99 (12: b01 to b13): not in Mimir `licences.toml`. Source: ccsl-uaegean/ITC99-RTL-Verilog, a vhd2vl conversion of the Politecnico di Torino ITC'99 VHDL; the repository's LICENSE says GPL-3.0 (spec section 8); the licence of the original VHDL has not been read.
- VTR Verilog `sha`: opencores permissive notice: may be used and distributed without restriction provided the copyright statement is not removed (Mimir rule vtr-sha).
- The infected circuits are derivatives of these bases; each base's own licence applies to its derivative.
- OpenCores (2: ca_prng, i2c), per project:
  - ca_prng: BSD-3-Clause style (InformAsic AB) (COPYING.txt:1-5; src/rtl/ca_prng.v:16-19). no memory, no tri-state; redistribution allowed with the notice kept.
  - i2c: permissive notice in the file headers: 'This source file may be used and distributed without restriction provided that this copyright statement is not removed from the file and that any derivative work contains the original copyright notice and the associated disclaimer.' (Richard Herveille, 2001) (rtl/verilog/i2c_master_top.v:17-20). no memory, no tri-state.
  The circuits derived from an OpenCores project are derivative works of its RTL: each project's own licence applies to them, and the notices above are kept with this release.

## Tools

- Odin III (build of the circuits): rc7 bases: 4c91edff (libodin3 build rel-main2); OpenCores bases: 78ab7e2c (libodin3 1.5.0 build rel-v150); checkout used for `lemanruss verify`: 78ab7e2c (build rel-v150).
- ABC: rc7 bases: UC Berkeley ABC 1.01 (compiled Oct 21 2026 17:22:51); OpenCores bases: ABC a3001b72edc5 linked in libodin3 1.5.0.

## Fetch and check

Unpack the circuits and answer-key archives into one directory, then `sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.
