# Results, round 12: Seeker-Proc rc2 and within-Proc detection (H-P2)

Purpose: Seeker v2.0 processor family, research question H-P2 (can a detector find a Trojan in a
processor core it has never seen?). Measure: AUROC per form with a 95% interval, W/L/T against the
size control, strict label. Aggregates only; no seeds, magic words or activation programs here.

## 1. Why rc2

Round 11 (rc1) reported rare, graphlet-b and gnn-a as failed, and every detector as out of range.
Two causes were found.

- **Detector failures.** Odin III was not importable in the isolated feature process (for example
  a Python environment without `cffi`). The failure was treated as "not scored", cached as NaN,
  and later surfaced as "validation fold has no clean circuit" or an IndexError. It now raises a
  `ToolchainError` that names the cause, and the follow-on errors name the real reason. Seeker-Proc
  also names the clean twin of an infected circuit `<id>-twin`, which is not a released file, so
  Method B (graphlet-b) used each circuit as its own reference; the reference is now read from the
  answer key.
- **A release defect.** 201 of the 300 rc1 circuits (all darkriscv and mcu) were not valid BLIF.
  `lower_gates_as_names` did not flatten, so the netlist held several `.model` sections that the
  form writer merged into one: duplicate ports, inputs that are also driven, and hundreds to
  thousands of multi-driven nets. Odin III `read_blif` rejected them, so no SCOAP or graphlet
  detector could score them. rc1 is superseded and archived, not deleted.

rc2 is the same design (100 logical circuits: 34 mcu, 33 picorv32, 33 darkriscv; three forms
gates, lut4, lut6; 300 circuits) rebuilt with `flatten; opt;` before `lower`, new secret seeds,
and a release gate that every circuit file must pass before it is written:

1. exactly one `.model`, no duplicate ports, no driven input, no multi-driven net;
2. Odin III `read_blif` succeeds;
3. equivalence (ABC) to the lowered netlist it was mapped from, by the first engine that proves it:
   `regmatch-cec` (latches matched through Odin's latch order and the known net renames, ABC `cec`
   on the cut netlists), then `scorr-cec` (ABC signal correspondence on the sequential miter, 15
   minute cap), then `dsec`. A timeout is reported as unproven and is a failure; the build stops.

Engines that decided: darkriscv 198 form checks, 132 `regmatch-cec` and 66 `scorr-cec` (the gates
forms: ABC merges registers there, which only the signal correspondence proves). mcu and picorv32
were gated by `dsec` (an earlier version of the gate, same standard of proof). No `dsec` fallback
was needed for darkriscv and nothing was left unproven. Initial values are read as equiv-check
reads them (2 and 3 count as 0).

Per form (clean/infected): gates 76/24, lut4 89/11, lut6 76/24. Flip-flops per base: mcu 1310,
picorv32 1615, darkriscv 2034 (RAM black-boxed).

The iverilog neutral-program trace differs for the circuits that carry a `stall` Trojan (13 of 33
picorv32 circuits): the trigger compares an unreset register that is `x` in four-state simulation
until the first fetch. With that register initialised, the clean and infected traces are equal.
It is recorded, not gating (spec section 0a); Odin III RTL and netlist traces are equal.

## 2. Protocol

Leave-one-base-out per form. For each held-out base, a detector trains on the circuits of the other
two bases of that form (a stratified fifth of them, fixed seed, is the validation set for model
selection) and scores the held-out base. Detectors: size (control), ffcount, classhist, sanity,
rare (SCOAP outliers), graphlet-b (Method B, reference-assisted), gnn-a-nosc, gnn-a (SCOAP
features), gnn-yasaei. GNNs: 50 epochs, seeds 0 to 2 averaged per circuit. Only AUROC is used, so
no threshold is involved.

Reported: AUROC of the pooled held-out scores (each circuit scored by a model that never saw its
base), with a 95% percentile bootstrap over circuits (infected and clean resampled separately),
per-base AUROC, and W/L/T against the size control over the three bases. Strict label per the CAD
reporting convention: interval above 0.5 is ABOVE CHANCE, below is BELOW CHANCE, otherwise
INCONCLUSIVE; a positive point estimate whose interval touches 0.5 is INCONCLUSIVE.

**Small-N caveat.** There are three bases. The interval resamples circuits inside those three, so
it says nothing about unseen bases beyond them, and W/L/T is a count over three. Pooling scores
from three different models mixes score scales (it favours detectors with stable scales). lut4 has
only 11 infected circuits. 27 cells are tested, so one or two intervals clear 0.5 by chance.
Training sets are two bases (about 66 circuits), far below the Comb/Seq training sets.

## 3. H-P2 table

AUROC [95% CI] pooled, then per held-out base. W/L/T against size over the three bases.

### Form gates

| detector | pooled AUROC [95% CI] | darkriscv | mcu | picorv32 | W/L/T vs size | label | scored |
|---|---|---|---|---|---|---|---|
| size | 0.525 [0.399, 0.655] | 0.473 | 0.731 | 0.654 | control | INCONCLUSIVE | 100/100 |
| ffcount | 0.431 [0.305, 0.570] | 0.500 | 0.500 | 0.500 | 1/2/0 | INCONCLUSIVE | 100/100 |
| classhist | 0.542 [0.397, 0.675] | 0.396 | 0.455 | 0.426 | 0/3/0 | INCONCLUSIVE | 100/100 |
| sanity | 0.560 [0.419, 0.678] | 0.533 | 0.304 | 0.531 | 1/2/0 | INCONCLUSIVE | 100/100 |
| rare | 0.425 [0.300, 0.568] | 0.357 | 0.518 | 0.586 | 0/3/0 | INCONCLUSIVE | 100/100 |
| graphlet-b | 1.000 [1.000, 1.000] | 1.000 | 1.000 | 1.000 | 3/0/0 | ABOVE CHANCE | 100/100 |
| gnn-a-nosc | 0.448 [0.326, 0.570] | 0.286 | 0.455 | 0.432 | 0/3/0 | INCONCLUSIVE | 100/100 |
| gnn-a | 0.486 [0.343, 0.633] | 0.780 | 0.553 | 0.426 | 1/2/0 | INCONCLUSIVE | 100/100 |
| gnn-yasaei | 0.361 [0.228, 0.510] | 0.357 | 0.265 | 0.444 | 0/3/0 | INCONCLUSIVE | 100/100 |

### Form lut4

| detector | pooled AUROC [95% CI] | darkriscv | mcu | picorv32 | W/L/T vs size | label | scored |
|---|---|---|---|---|---|---|---|
| size | 0.563 [0.370, 0.761] | 0.802 | 0.583 | 0.644 | control | INCONCLUSIVE | 100/100 |
| ffcount | 0.504 [0.329, 0.689] | 0.500 | 0.500 | 0.500 | 0/3/0 | INCONCLUSIVE | 100/100 |
| classhist | 0.519 [0.338, 0.682] | 0.431 | 0.433 | 0.511 | 0/3/0 | INCONCLUSIVE | 100/100 |
| sanity | 0.616 [0.431, 0.783] | 0.750 | 0.733 | 0.756 | 2/1/0 | INCONCLUSIVE | 100/100 |
| rare | 0.468 [0.277, 0.667] | 0.341 | 0.267 | 0.633 | 0/3/0 | INCONCLUSIVE | 100/100 |
| graphlet-b | 1.000 [1.000, 1.000] | 1.000 | 1.000 | 1.000 | 3/0/0 | ABOVE CHANCE | 100/100 |
| gnn-a-nosc | 0.418 [0.235, 0.623] | 0.276 | 0.125 | 0.356 | 0/3/0 | INCONCLUSIVE | 100/100 |
| gnn-a | 0.393 [0.197, 0.615] | 0.483 | 0.308 | 0.067 | 0/3/0 | INCONCLUSIVE | 100/100 |
| gnn-yasaei | 0.486 [0.307, 0.670] | 0.647 | 0.550 | 0.422 | 0/3/0 | INCONCLUSIVE | 100/100 |

### Form lut6

| detector | pooled AUROC [95% CI] | darkriscv | mcu | picorv32 | W/L/T vs size | label | scored |
|---|---|---|---|---|---|---|---|
| size | 0.469 [0.340, 0.614] | 0.343 | 0.530 | 0.509 | control | INCONCLUSIVE | 100/100 |
| ffcount | 0.559 [0.447, 0.681] | 0.500 | 0.500 | 0.500 | 1/2/0 | INCONCLUSIVE | 100/100 |
| classhist | 0.466 [0.342, 0.580] | 0.444 | 0.470 | 0.509 | 1/1/1 | INCONCLUSIVE | 100/100 |
| sanity | 0.491 [0.359, 0.629] | 0.336 | 0.524 | 0.569 | 1/2/0 | INCONCLUSIVE | 100/100 |
| rare | 0.543 [0.417, 0.669] | 0.255 | 0.304 | 0.764 | 1/2/0 | INCONCLUSIVE | 100/100 |
| graphlet-b | 1.000 [1.000, 1.000] | 1.000 | 1.000 | 1.000 | 3/0/0 | ABOVE CHANCE | 100/100 |
| gnn-a-nosc | 0.442 [0.310, 0.565] | 0.477 | 0.589 | 0.352 | 2/1/0 | INCONCLUSIVE | 100/100 |
| gnn-a | 0.635 [0.507, 0.761] | 0.787 | 0.577 | 0.514 | 3/0/0 | ABOVE CHANCE | 100/100 |
| gnn-yasaei | 0.550 [0.418, 0.691] | 0.574 | 0.321 | 0.495 | 1/2/0 | INCONCLUSIVE | 100/100 |


## 4. Reading

- **graphlet-b scores 1.000 on every form** (3/0/0). That is by design: it compares each circuit
  with its clean twin, and any inserted logic changes the signature. It needs the reference, so it
  is not a blind detector and is not part of the H-P2 comparison.
- Of the 24 blind cells (8 detectors, 3 forms), one has an interval above 0.5: **gnn-a on lut6,
  0.635 [0.507, 0.761], W/L/T 3/0/0** against the size control (0.469 [0.340, 0.614]). The lower
  bound is 0.007 above chance, on three bases, among 24 tested cells. The other 23 are
  INCONCLUSIVE, and none is below chance by its interval.
- The size control sits at 0.47 to 0.56 and is itself INCONCLUSIVE on all forms (per-base values
  range 0.34 to 0.80), so size alone does not explain any signal.
- **Verdict on H-P2** (as worded: no detector beats the size control with an interval above 0.5 on
  any form): **weakly not supported on lut6** (one cell, gnn-a, borderline) and **supported on
  gates and lut4**. Given the multiplicity and three bases, treat the lut6 cell as a lead to
  repeat with more bases, not a result.
- ffcount is 0.5 per base by construction (infected and clean twins have equal flip-flop counts);
  its pooled value differs from 0.5 only through the pooling of the three models' offsets.

Archive: `<archive>/2026-11-05/seeker-proc-v2.0-rc2/` (circuits-only tarball checked to hold no
answer key; answer key, full release and run records are separate; SHA256SUMS verified).
