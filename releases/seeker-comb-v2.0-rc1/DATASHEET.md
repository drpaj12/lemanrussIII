# seeker-comb-v2.0-rc1 datasheet

Family: Seeker-Comb. Version 2.0-rc1 (release candidate; the final v2.0 follows after later rounds add ITC-99 b15-b19, the VTR designs and Seeker-Proc). Produced by Leman Russ III (Yggdrasil III).

Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.

## Lineage

v1 = Seeker1: Sarihi, Patooghy, Badawy, Jamieson, 'The Seeker's Dilemma', arXiv 2402.17918, IPCCC 2024 (8 ISCAS-85 bases x 18 ABC restructurings = 144 HT-free and 14,400 HT-infected circuits, combinational gate-level). v2.0 keeps the formulation (the detector does not know whether a circuit is infected) and builds the infected circuits with the HTL on ISCAS-85 plus further combinational bases, with a rareness report per circuit.

## Contents

- circuits: 1596 in `circuits/<id>.blif.gz` (gzip, zero timestamp), 589 clean and 1007 infected, opaque ids.
- bases: 31; each has one clean circuit and its infected circuits.
- restructurings: identity plus 18 ABC restructurings of every circuit, 19 forms, every one checked ABC-equivalent to its source (all proven).
- variants that could not be built: 40 (`answer_key/failures.json`; a band no rare net could reach).
- answer key: `answer_key/` (labels, provenance, renames, rareness); a detector must not read it. Clean circuits carry no label and infected circuits carry no label.

Circuits per base (all forms):

C1355 76, C17 19, C1908 76, C2670 76, C3540 76, C432 76, C499 76, C5315 76, C6288 76, C7552 76, C880 76, alu4 76, apex2 76, apex4 38, cordic 76, ex5p 38, misex3 76, pdc 76, spla 76, t481 76, ve_Prob004_vector2 19, ve_Prob006_vectorr 19, ve_Prob015_vector1 19, ve_Prob023_vector100r 19, ve_Prob042_vector4 19, ve_Prob043_vector5 19, ve_Prob064_vector3 19, ve_Prob092_gatesv100 19, ve_Prob094_gatesv 19, ve_Prob150_review2015_fsmonehot 19, ve_Prob156_review2015_fancytimer 19

## Rareness bands

Seeker-Comb: the trigger is an AND of rare-valued nets grown until the joint activation probability per random vector falls in a target band: p < 1e-2, p < 1e-3, p < 1e-4 (estimated on 2^20 vectors, exact when the design has at most 20 inputs).

| band reached | circuits |
|---|---|
| p<1e-4 | 16 |
| p<1e-3 | 20 |
| p<1e-2 | 17 |
| p>=1e-2 | 0 |
| never | 0 |

Pooled: 53 infected circuits, geometric mean p = 2.979e-04 over the 53 that fired at least once, 38437632 vectors in total.

## Restructurings

identity, strash, balance, rewrite, refactor, resyn, resyn2, compress2, dc2, dc2x2, lut4, lut6, lut6mfs, resyn2a, resyn3, resyn2rs, compress, resub, lut5 (ABC standard scripts and LUT mappings; Seeker1's own list of 18 was not read, so this is the count, not the same list).

Equivalence: all restructured circuits were proven equivalent to their source.

## Bases and licences

- ISCAS-85 (11: C1355, C17, C1908, C2670, C3540, C432, C499, C5315, C6288, C7552, C880): licence unread. Mimir `licences.toml` has no ISCAS rule and the ISCAS licence has not been read.
- MCNC (9: alu4, apex2, apex4, cordic, ex5p, misex3, pdc, spla, t481): none-stated (Mimir rule mcnc). The MCNC licence itself has not been read.
- VerilogEval gate netlists (11: ve_Prob004_vector2, ve_Prob006_vectorr, ve_Prob015_vector1, ve_Prob023_vector100r, ve_Prob042_vector4, ve_Prob043_vector5, ve_Prob064_vector3, ve_Prob092_gatesv100, ve_Prob094_gatesv, ve_Prob150_review2015_fsmonehot, ve_Prob156_review2015_fancytimer): MIT (VerilogEval LICENSE, Copyright (c) 2023-2024 NVIDIA Research Projects) (Mimir rule verilogeval).
- The infected circuits are derivatives of these bases; each base's own licence applies to its derivative.

## Tools

- Odin III (build of the circuits): 7c04cfb2; checkout used for `lemanruss verify`: v1.2.0-21-g66ee88c7.
- ABC: UC Berkeley, ABC 1.01 (compiled Oct 21 2026 17:22:51).

## Names

Every net the inserter added is renamed to a neutral internal name in the style of the clean circuit (spec section 10.2); `answer_key/renames.json` maps them back.

## Fetch and check

Unpack the circuits and answer-key archives into one directory, then `sha256sum -c SHA256SUMS` and `lemanruss verify <dir>`.
