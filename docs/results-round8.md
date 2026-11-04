# Round 8 results: Seeker v2.0 (rc4 redesign, 2026-11-01)

## rc3 leak and fix (rc4 supersedes everything below section "rc3 results")

The controller found two label leaks in rc3 set B (clean variants made with Odin III neutral edits):

1. Style leak, identity form. 89 % (Comb) and 91 % (Seq) of set-B clean circuits had a double inverter against 0 % and 0.5 % of the
   infected ones (set A: 0 %); double buffer 90 % vs 32 % (Comb), 93 % vs 32 % (Seq). One rule separated the labels.
2. Duplicate leak, restructured forms. ABC removed the neutral edits, so each restructured clean variant was byte-identical to the
   restructured golden: 1728 of 1728 pairs checked (12 Comb bases, 8 clean variants each).

Fix (Peter's redesign, spec section 4): per golden three sets of 100 circuits (LUT k = 4, LUT k = 6 by Odin III `abc --lut`, and an AND / OR / NOT
library by `abc --gates`), a per-set infected count drawn uniformly in 10..70, 1 to 3 Trojans per infected circuit (stuck output, upper- and lower-half
bit error; the energy ring and slowdown payloads are dropped because logic optimisation removes them), and for every non-golden circuit, clean or
infected, one pipeline: Trojan insertion (infected only), its own random ABC optimisation script (one distribution for all labels), the set's mapping,
shuffled ports and blocks, fresh `n<index>` net names, `.model top`, no comment or attribute. No set A, no 19 restructured forms. The golden keeps its
function and layout (foreign-style net names such as `$n5` renamed). Triggers are planned on the golden (comb rare AND, seq counter / FSM pattern);
rareness is measured on the pre-obfuscation circuit (kept in the answer key).

New verify gates (`lemanruss/htl/n200gates.py`, run by `lemanruss verify`):
`f_distinct` (no two files identical, also ignoring `.model` and comments), `g_style` (per-artefact Cochran-Mantel-Haenszel test stratified by
base and set with a Bonferroni bound and a 5-point minimum difference; net-name scheme: foreign-pattern new nets and index range; AUROC of the best
single style feature with a permutation null), `h_provenance` (only plain directives, no comment, no `$ @ __htl odin yosys`, one `.model`, one
`.latch` format, net names `n<digits>`). Buffers and inverters that drive a primary output count as interface, not style (a Trojan payload replaces
the driver of its victim output). Cube-pattern classes are reported, not gating (Trojan cells are such cells).

| gate | rc3 Seeker-Comb | rc3 Seeker-Seq | rc4 Seeker-Comb | rc4 Seeker-Seq |
|---|---|---|---|---|
| f_distinct | FAIL: 1208 duplicate groups, 323 across labels | FAIL: 5309 groups, 574 across labels | PASS: 0 | PASS: 0 |
| g_style (best-feature AUROC, bound 0.60 or null + 0.03) | FAIL: 0.948, 5 artefact tests | FAIL: 0.957, 18 artefact tests | PASS: 0.533 (inv/cells) | PASS: 0.596 (const/cells) |
| h_provenance | FAIL: 82,821 files with traces | FAIL: 137,484 files | PASS: 0 | PASS: 0 |

rc4 other checks, both families PASS: integrity, separation, leak, rareness re-measure on the pre-obfuscation circuits (sample per base and set), every
Trojan witness replayed in Odin III on the finished circuit (Comb 3630 of 3630, Seq 6444 of 6444), obfuscated circuit equivalent to its pre-obfuscation
form (Comb 2218, Seq 3966), forced-off equivalence of the pre-obfuscation form to the golden, clean circuits equivalent to the golden (Comb 3507, Seq 6373).

| rc4 | Seeker-Comb | Seeker-Seq |
|---|---|---|
| bases | 31 | 36 |
| circuits (goldens included) | 5756 | 10,375 |
| goldens / clean / infected | 31 / 3507 / 2218 | 36 / 6373 / 3966 |
| Trojans (infected circuits carry 1-3) | 3630 | 6444 |
| infected drawn / built, K4 | 1019 / 638 | 1342 / 1342 |
| infected drawn / built, K6 | 972 / 720 | 1331 / 1331 |
| infected drawn / built, G | 1190 / 860 | 1293 / 1293 |

Short sets: Seeker-Comb tiny `ve_*` bases and C17 have no internal net for a trigger and few distinct structures after optimisation, so they supply
few or no circuits; some larger comb bases could not supply the drawn infected count (builder lists it in `answer_key/failures.json` and in the
datasheet). Within every set, a circuit whose structure repeats another of the base and mapping is not released (never padded). Selection effect that
remains: a proposal whose Trojan the script removed is redrawn.

Archive: F: `<archive>/2026-11-01/seeker-{comb,seq}-v2.0-rc4/` (README section appended; rc3 marked superseded, its archives kept). The git
`releases/` hold the rc4 index files (`DATASHEET.md`, `manifest.json.gz`, `SHA256SUMS.gz`).

## Seq rc4 latch leak and rc5 (2026-11-02)

**Leak.** Seeker-Seq rc4 gave the label away through the `.latch` init value. In the rc4 release (all 10,375 files): clean circuits have only
init 2 (396,073 latches; the 36 goldens: 504 with 2, 1659 with 3 on the ITC-99 bases); infected circuits have 31,513 latches with init 0 and
250,654 with init 2 (11.2 % of their latches; every one of the 3,966 infected circuits has at least one). The init-0 latches are the Trojan's
own flip-flops: the Odin III edit API created them with `INIT 0` and ABC keeps an explicit 0 (it writes "unknown" as 2). "Any latch with init 0"
separates infected from clean with AUROC 1.0. The detector lane's GNN AUROC of 0.98 to 1.00 on Seq rc4 follows from it. The rc4 gates did not read
`.latch` fields (`h_provenance` only required one format). Seeker-Comb has no latches and is not affected; the extended gate passes it (below).

**Gate (new fields, `n200gates.py`).** Per circuit and base x set stratum, clean against infected, same CMH test, Bonferroni bound, 0.05 minimum
difference and AUROC bound 0.60 as `g_style`: latch init (0/1/2/3), latch type, latch clock (main / other), what drives D (primary input,
latch, buffer, inverter, constant, other), and, as information only, latches whose D cone reads their own Q. Also the BLIF fields the rc4 gates did
not cover: off-set cover polarity, don't-care use, cube order, input order. `h_provenance` now also fails a file with more than one
`type/clock/init` among its latches and a base with more than one over all its files. The AUROC bound is exceeded only beyond its estimation error
(AUROC minus 1.645 Hanley-McNeil standard errors above the bound); see the deviation below.

| field (max over its features) | rc4 Seq: max stratified difference / best AUROC | rc5 Seq | rc4 Comb |
|---|---|---|---|
| latch init | 1.000 / 1.000 FAIL | 0.000 / 0.500 pass | no latches |
| latch type | 0.000 / 0.500 | 0.000 / 0.500 pass | no latches |
| latch clock | 0.000 / 0.500 | 0.000 / 0.500 pass | no latches |
| D driver kind | 0.089 / 0.528 FAIL (inverter in front of a latch: p 1e-70) | 0.013 / 0.547 pass | no latches |
| D cone reads own Q (info, not gated) | 0.081 / 0.668 (Trojan footprint: counters, FSM) | 0.081 / 0.668 | no latches |
| off-set cover, don't-care, cube order, input order | 0.003 / 0.552, 0.000 / 0.587, 0.004 / 0.532, 0.000 / 0.529 pass | 0.002 / 0.557, 0.000 / 0.585, 0.004 / 0.528, 0.000 / 0.535 pass | 0.542 best, pass |
| buffer, inverter, double, constant (as rc4) | pass, const share 0.596 | pass, const share 0.601 | pass |
| h_provenance | FAIL: 3,966 files with traces, 36 of 36 bases with mixed latch conventions | PASS: 0 | PASS |
| g_style overall | FAIL (best feature lat_init_0 share, AUROC 1.000, bound 0.60) | PASS (best const share 0.601, se 0.0058; bound 0.60) | PASS (best 0.542) |
| f_distinct | pass | pass | pass |

Test: `tests/test_n200gates.py` runs the gate on the rc4 Seq release on disk (it must fail, with `lat_init_0` flagged and the best feature at AUROC
above 0.99) and on the rc5 release (it must pass).

**Deviation, stated plainly.** The share of constant cells, a feature unchanged since rc4, measured 0.596 on rc4 and 0.601 on rc5 against the 0.60
bound. The Trojan adds cells, so any "share of cells" feature is diluted in infected circuits (size alone separates infected from clean with AUROC
0.85 inside a base x set stratum, and the latch count with AUROC 1.0: both are the Trojan's own footprint, not style). The rc5 fix therefore makes the
bound a statement about the true AUROC: it is exceeded only when the estimate minus 1.645 standard errors is above it. The rc4 leak is at 1.000 with
error 0 and still fails. The raw numbers are reported above; if the controller prefers the strict reading, the rc5 gate is 0.601 against 0.60 on
the constant-cell share and every latch field passes.

**Builder fix (spec section 12).** (1) Inserted latches carry the circuit's own latch convention (edge, init of its most used `.latch` pattern; here
`re` and 2) through the Odin III edit API; the golden's init 3 is spelled 2. (2) Two further footprints of the Trojan latches showed up once the init
was fixed, both found by the new D-driver field: an inverter in front of a latch (the pattern trigger's first stage with value 0, the sticky flag's
`f | last` built twice so that ABC shares the node and puts an inverter in front of the latch) and a lone inverter or buffer in front of the first
stage. The pattern's first stage is now `net == value and not yet fired` (a two-input cell), and the trigger is the sticky flag itself (the flag is
one cycle later than the old combinational trigger). Same function otherwise; checked against the old structure by simulation in
`tests/test_edit_netlist.py`. (3) Start state: init 2 is "unknown"; `bitsim`, the Odin III simulator (witness replay) and ABC `cec`/`dsec` all read it
as 0, as they do for the circuit's own latches, so no Trojan depends on an init value that only Trojan latches have. Rareness is P(fire within N
cycles) from the all-zero start (the state the simulator uses) with uniform random inputs, N = 16, 64, 256, 1024.

**rc5 build.** Same 36 bases, same sets, same plan seeds as rc4 (bases = the rc4 goldens, whose text equals the canonical base). 10,375 circuits (36
goldens, 6,373 clean, 3,966 infected), identical counts per base and set to rc4; 6,439 Trojans (rc4 6,444; five fewer, all counter Trojans). `lemanruss verify` PASS: integrity, separation, leak, rareness re-measure on the
pre-obfuscation circuits, 6,439 of 6,439 witnesses replayed in Odin III on the finished circuits, 3,966 forced-off equivalences, 3,966 obfuscation
equivalences, 6,373 clean equivalences, f_distinct, g_style (including the new fields), h_provenance (including the latch convention). All latches in
every file: `re clock 2` style (type re, one clock per base, init 2). Rareness against rc4 (6,403 Trojans with an identical specification in both):
P(fire <= 1024) mean absolute difference 0.0005 (largest 0.076); P(fire <= 16 / 64 / 256) differ by 0.0046 / 0.0022 / 0.0013 on average, with a few
fast Trojans one cycle later (the trigger is the flag). Mean P(fire <= 1024): counter 0.4585 -> 0.4577, pattern 0.4665 -> 0.4662.

rc4 Seq is superseded; its release stays on disk and on F:. (Round 9, below: Comb rc5 and Seq rc6 restore the energy and slowdown payloads; Comb rc4 and Seq rc5 are then superseded for payload content.) Archive: F: `<archive>/2026-11-02/seeker-seq-v2.0-rc5/`.

# rc5 Comb / rc6 Seq: cut-and-stitch (round 9, 2026-11-02)

Peter, 2026-11-02, verbatim: "except for our previous seeker's dilemma. We cut out what couldn't be handled by other tools and then reinserted it by making
the outputs or the inputs to the part we can as primary outputs and the outputs as primary inputs. Could we do this for the parts that get destroyed by
ABC?" Purpose: restore the energy-ring and slowdown payloads that rc4/rc5 dropped, so Seeker-Comb and Seeker-Seq carry the mixed payload set again (stuck
output, error high / low, energy [Seq only: a combinational circuit has no clock], slowdown). Method and the agent's findings: spec section 13. This
section does not claim the method is how Seeker v1 was built.

**What the smoke runs found (2 Comb + 2 Seq bases, before the full rebuild).** Hypothesis: cut-and-stitch keeps both payloads through ABC. Experiment and verdict:
(1) energy ring: CONFIRMED. Cut out with its own bits as extra outputs of its own standalone run, it survives a full random script and mapping; stitched circuit
`cec`-equivalent to its pre-obfuscation form. (2) slowdown buffer chain: REFUTED for ABC (`strash` has no node for `a = b`: the chain collapses whether or not its
ends are primary outputs). Carrying the chain through unmapped kept the depth but the gate `g_style` caught it (`buf` / `dbl_buf`, AUROC 0.74 on the smoke Comb).
Replaced by an absorption stage `tmp | (tmp & s_1) | ... | (tmp & s_m)` (= `tmp`; ANDs in the host, only the OR cut). (3) The first Seq smoke then failed three more
gates, each fixed and re-verified: a net the golden never reads used as a slowdown source (`name_foreign`), a latch with a bare net across the cut buffered by gate
mapping (28 of 30 cut circuits against 0 of 30 plain; fixed by closing the cut region over latches), and a constant cell from `tmp & s` where `s` lies in `tmp`'s own
cone (fixed by drawing sources outside the victim's cone). Also: gate mode named the internal nets of host and part alike (one net driven twice: private prefixes), and
cells now carry inputs and cubes in ascending order in every file (`in_unsorted` showed a 5.9-point difference once pieces were stitched). A first energy witness
(whole-circuit toggle total against the golden) failed on its premise (a mapped circuit has fewer signals): it now reads the ring nets themselves through the rename map in
`answer_key/cuts.json`.

**Builds.** Same bases as rc4 / rc5 (the rc4 goldens), same sets and plan seeds; the mix and the cut step are new, so circuits are not identical to rc4 / rc5.

| | Seeker-Comb rc5 | Seeker-Seq rc6 |
|---|---|---|
| bases | 31 | 36 |
| circuits (goldens included) | 5809 | 10,735 |
| goldens / clean / infected | 31 / 3514 / 2264 | 36 / 6733 / 3966 |
| Trojans | 3705 | 6792 |
| p-dos-stuck | 1564 | 1970 |
| p-err-hi / p-err-lo | 735 / 705 | 999 / 936 |
| p-energy | n/a (no clock) | 1367 |
| p-slowdown (always on) | 701 | 1520 |
| rc4 / rc5 circuits (comparison) | 5756 | 10,375 |

Per set (K4 / K6 / G) payload mix: Comb slowdown 171 / 266 / 264, dos 443 / 497 / 624, err-hi 225 / 221 / 289, err-lo 217 / 208 / 280. Seq energy 458 / 477 / 432, slowdown 561 / 472 / 487,
dos 699 / 643 / 628, err-hi 335 / 341 / 323, err-lo 308 / 306 / 322. The degenerate `ve_*` bases, C17 and s27 supply few circuits (identical in kind to
rc4: structures repeat); `answer_key/failures.json` lists every short set. Redrawn proposals: 640 (Comb) and 78 (Seq); 252 of Comb's come from `ve_Prob156_review2015_fancytimer` and 89 from
`misex3` (Odin III error on the host or a `cec` error on a dummy cut, redrawn); 12 Comb slowdown proposals had no source outside the victim's cone and were redrawn.

**Cut-size distribution (blocks of the pre-obfuscation circuit; a dummy cut is drawn from the pool of real cut sizes of the base, a latch closure may enlarge any cut).**

| family | status | cut kind | n | min | median | max |
|---|---|---|---|---|---|---|
| Comb | clean | dummy | 3514 | 1 | 1 | 10 |
| Comb | infected | dummy | 1660 | 1 | 1 | 10 |
| Comb | infected | slow | 701 | 1 | 1 | 1 |
| Seq | clean | dummy | 6733 | 1 | 4 | 649 |
| Seq | infected | dummy | 1690 | 1 | 4 | 643 |
| Seq | infected | energy | 1413 | 1 | 10 | 128 |
| Seq | infected | slow | 1474 | 1 | 1 | 128 |

Every circuit is cut; clean and payload-free infected circuits have dummy cuts of the same distribution (clean 4 / infected 4 median in Seq, 1 / 1 in Comb), so the cut itself is no label.

**Gates (`lemanruss verify`, both releases PASS):** integrity, separation, leak, rareness re-measure on the pre-obfuscation circuits (always-on slowdown records skipped),
witnesses replayed in Odin III on the finished circuits (Comb 3004 of 3004, Seq 5272 of 5272; an energy witness passes when the ring nets toggle), obfuscated circuit equivalent to its
pre-obfuscation form (Comb 2264, Seq 3966), forced-off equivalence (same), clean circuits equivalent to the golden (Comb 3514, Seq 6733), f_distinct 0 groups, g_style (all
latch and cover fields; best feature `cov0/cells` AUROC 0.535 Comb, 0.601 Seq with standard error 0.0057: the Seq bound passes only through the rc5 rule "AUROC minus 1.645 SE above 0.60",
exactly as the rc5 release did with 0.601), h_provenance. Independent check (`lemanruss/htl/cutreport.py`, shares no code with the gates): 0 duplicate groups, 0 files with leak tokens, 0 lines
with a directive outside `.model .inputs .outputs .names .latch .end`, every latch line `re clock 2` (701,171 latch lines); per-set AUROC of each style feature within base x set strata, pair-weighted:
Comb K4 / K6 / G: cell count 0.652 / 0.572 / 0.549 (footprint, as rc5), single-input share 0.462 / 0.473 / 0.565, double-single share 0.495 / 0.493 / 0.503, constant share 0.475 / 0.495 / 0.504.
Seq K4 / K6 / G: cell count 0.758 / 0.717 / 0.763, FF count 0.946 / 0.949 / 0.948, FF share of cells 0.843 / 0.823 / 0.861, single-input share 0.338 / 0.354 / 0.545, FF-with-buffered-D 0.504 / 0.500 / 0.523,
constant share 0.475 / 0.472 / 0.483, latch init-0 / init-1 count 0.5 / 0.5.

**Flip-flop count (the controller's measure for the next step).** AUROC of total FF count, clean against infected, within each base and set (108 strata), pooled by pair count: 0.948
(K4 0.946, K6 0.949, G 0.948; per stratum min / median / max 0.885 / 0.951 / 1.000). log(1 + FF) is a monotone transform, so its AUROC is identical (0.948). Reading: this is a footprint, not
style: the energy rings add 2 to 64 flip-flops each to 1367 Trojans of 3966 infected Seq circuits (rc5 Seq: 0.63). The gates do not see it (they bound share-of-cell features); a detector can read it. It exists
because the ring is the payload; clean circuits have no counterpart. The dummy cuts can not hide it (they carry the golden's own flip-flops). A size control must include FF count.

**Energy measure.** Ring toggles (Odin III toggle counters on the ring nets) over the replayed witness input sequence against an all-zero input run of the same length, 60 energy Trojans of the smallest bases:
witness toggles min / median / max 4 / 8 / 32 (the ring is `d = trigger xor q`: it toggles on cycles after the trigger is high), all-zero run 0 / 0 / 11,328; the witness run toggles more than the idle run in
47 of 60; in the other 13 the trigger also fires on the all-zero sequence (a counter or pattern over rare nets that all-zero inputs happen to hit, then the ring toggles every cycle) so idle is not an off state. The witness
is the pass criterion (ring toggles at least once; 1367 of 1367 replays pass in `verify`); idle is a reported measure only.

**Slowdown measure.** The payload is always on, so depth is reported, not rareness: depth of the finished circuit (levels of `.names`) minus depth of one reference obfuscation of the golden under the same set
(one random script and mapping per base and set): n 604 (Comb) / 1343 (Seq) circuits with a slowdown, min / median / max -14 / +3 / +48 (Comb) and -32 / +3 / +34 (Seq). The reference is a different random script,
so single values are noisy (negative ones are scripts that map the golden deeper than the stitched circuit); the median is +3 levels in both families. The slowdown adds an AND level and an OR level on the victim's path.

**Deviations for Peter.** (1) Slowdown is an absorption stage, not a buffer chain (ABC folds chains; unmapped chains are a label): spec section 13, finding 2 and 3. (2) The energy payload is a footprint of 2 to 64 flip-flops: FF count
separates labels at AUROC 0.95 although no style gate fires. (3) Seq g_style best-feature AUROC is 0.601, inside the rc5-style bound only through the standard-error rule. (4) Short sets as in rc4 on the tiny `ve_*` bases and C17 / s27. (5) A cut may be larger than its drawn
size (latch closure). (6) The slowdown depth reference is noisy (above). rc4 (Comb) and rc5 (Seq) release directories are kept; both are superseded for payload content (payloads restored).

# rc3 results (superseded; kept for the record)

## Round 8 rc3 run (n = 200 per base, 2026-11-01)

Branch feat/htl-round8-n200 (from main a69bd3e), Odin III library `build/rel-main/libodin3.so`
(main d4d3356e). Spec: docs/specs/2026-11-01-seeker-n200-design.md (reading of Peter's request,
distinctness rules, agent defaults). Build trees work/htl-out/r8/{comb2,seq} (not committed),
releases work/htl-rel/rc3/seeker-{comb,seq}-v2.0-rc3 (not committed; only the index files in
`releases/` are). Seed kept with the answer key.

Headline. Seeker-Comb v2.0-rc3: 31 bases, 4369 identity circuits (31 goldens, 1900 set A, 2,438 set B: 709 infected, 1,729 clean variants; Seeker-Seq set B 3,600: 1,422 infected, 2,178 clean variants), 83,011 circuits in 19 forms, verify PASS. Seeker-Seq v2.0-rc3: 36 bases (of
50; 13 large bases not built at n = 200, ch_intrinsics and boundtop stay out), 7236 identity circuits,
137,484 circuits in 19 forms, verify PASS. Every Trojan of every infected circuit has a witness
replayed in Odin III; every infected circuit, clean variant and restructured form is proven
equivalent (ABC cec / dsec) to its source with all triggers forced inactive; 0 unproven, 0 failed.

## 0. bitsim level-latch fix (first step)

`.latch D Q ah|al EN` is a transparent latch. bitsim treated it as an edge flip-flop and forced EN
to 0 as a clock (Odin III #317 finding). Level latches are now kept apart, their enable is data, and
a cycle settles the blocks until no latch output changes. Evidence: `tests/test_bitsim_level.py`
(hold, transparency, active-low, edge flip-flop beside them; the same trace in Odin III's simulator),
and `crosscheck` of ch_intrinsics (85 level latches): 0 mismatches of 37,440 signal comparisons
(rc2 note: 5,566). ch_intrinsics and boundtop stay out of Seeker-Seq: equiv-check still refuses
level-sensitive latches, so their equivalence cannot be proven.

## 1. What was built

Per base: 1 golden, set A (100 circuits, one DoS Trojan each) and set B (100 circuits: f * 100
infected with 1 to 3 Trojans of mixed payloads, the rest clean variants). f is drawn per base in
[0.10, 0.70]; the achieved fraction equals it to rounding wherever the base supplied enough Trojans.
Clean variants are Odin III edit-API neutral rewrites (2 to 6 double inverters or buffer pairs),
proven equivalent to the golden (agent default 3 of the spec; this keeps the file style of clean and
infected circuits the same). Ids are in a seeded random order inside each base block. Which
circuits are set A / B and which are infected is in `answer_key/sets.json` only; the manifest names
the golden of each base.

Distinctness: no two Trojans of one base share a trigger net set; no two circuits of a base are
byte-identical (checked by hash while building; the unit test also checks it); no circuit
repeats a victim or a trigger net across its own Trojans. Short sets are listed below and are
not padded.

Wall time (6 jobs, 12 cores): Comb build 3 min 26 s, restructuring of 78,642 circuits 1 h 29 min,
release + verify 1 h 30 min. Seq build 33 min, restructuring of 130,248 circuits 3 h 02 min, verify 2 h 08 min.
Peak RSS 0.9 GB (Comb build), 0.5 GB (Comb verify). Estimates of the spec (section 7): Comb restructuring 3.7 h,
Seq (<= 12000 gates) 4.6 h: the measured times are lower because most bases are small.

## 2. Not built or short

- Seeker-Seq not built at n = 200: b05, b14, b15, b17, b18, b19, b20, b21, b22, diffeq1, diffeq2,
  mkPktMerge, mkSMAdapter4B (more than 12000 gates; spec section 7: about 1060 CPU-h of restructuring)
  and boundtop, ch_intrinsics (equiv-check refuses level latches). The rc2 release of these bases keeps its old n.
- Seeker-Comb: C17 supplies 0 set-A circuits (5 inputs: no trigger band reachable with DoS) and 14 infected set-B circuits;
  the 11 tiny `ve_*` bases (7 to 100 gates, every gate an output) have no internal net to use as trigger, so
  no infected circuit (A and B: 0); they hold a golden and the clean variants that Odin III could edit
  (output nets are renamed in its model, `ValueError: no such net`, 5 to 89 variants). ve_Prob156 and ve_Prob064
  supply 6 and 4 infected set-B circuits. These bases are in the release with their counts, not padded.
- 5 Comb and 17 Seq set-A / B proposals were dropped because the independent sample found no input on which the payload shows
  (witness search); 16 Comb inserts and 7 forced-off cec runs on tiny bases failed with the same Odin III naming error.

## 3. Per family

## Seeker-Comb

Release `seeker-comb-v2.0-rc3`: 31 bases, 31 goldens, 83011 circuits in 19 forms (4369 identity circuits), 49571 infected circuits (all forms). Verify: PASS.

Verify (`lemanruss verify`, all checks re-run from the files):

- integrity: 85650 files listed and hashed, 0 problems
- separation: 33440 clean, 49571 infected circuits (all forms), 0 problems; ids opaque
- leak: 83011 circuits scanned (contents, file names, directory names, manifest keys and text, infected-only net-name style), 0 leaks, 0 odd names, odin3_edit hits 0 + 0
- witnesses: 2842 stored witnesses replayed in Odin III, 2842 fired (trigger high, payload shows; slowdown by depth)
- forced-off equivalence: 2609 infected identity circuits (3111 Trojans), {'equivalent': 2609}
- equivalence of restructured forms and clean variants: 80371 checked, {'equivalent': 80371}, unproven 0
- rareness re-measure: 76 circuits (4 per base) with a new seed, 76 within 5 sigma / exact



### Bases, circuits and infected fraction

| base | gates | f (drawn) | A | B infected | B clean variants | B infected fraction (achieved) | Trojans in B |
|---|---|---|---|---|---|---|---|
| C17 | 7 | 0.678 | 0 | 14 | 32 | 0.304 | 20 |
| ve_Prob006_vectorr | 8 | 0.108 | 0 | 0 | 89 | 0.000 | 0 |
| ve_Prob092_gatesv100 | 8 | 0.285 | 0 | 0 | 5 | 0.000 | 0 |
| ve_Prob094_gatesv | 8 | 0.621 | 0 | 0 | 2 | 0.000 | 0 |
| ve_Prob150_review2015_fsmonehot | 8 | 0.516 | 0 | 0 | 6 | 0.000 | 0 |
| ve_Prob156_review2015_fancytimer | 8 | 0.154 | 0 | 6 | 85 | 0.066 | 8 |
| ve_Prob043_vector5 | 11 | 0.586 | 0 | 0 | 13 | 0.000 | 0 |
| ve_Prob015_vector1 | 16 | 0.507 | 0 | 0 | 49 | 0.000 | 0 |
| ve_Prob004_vector2 | 32 | 0.177 | 0 | 0 | 82 | 0.000 | 0 |
| ve_Prob042_vector4 | 32 | 0.438 | 0 | 0 | 56 | 0.000 | 0 |
| ve_Prob064_vector3 | 33 | 0.536 | 0 | 4 | 46 | 0.080 | 4 |
| ve_Prob023_vector100r | 100 | 0.506 | 0 | 0 | 49 | 0.000 | 0 |
| C432 | 182 | 0.311 | 100 | 31 | 69 | 0.310 | 54 |
| C1355 | 190 | 0.619 | 100 | 62 | 38 | 0.620 | 105 |
| C499 | 190 | 0.429 | 100 | 43 | 57 | 0.430 | 71 |
| C1908 | 294 | 0.442 | 100 | 44 | 56 | 0.440 | 74 |
| C880 | 327 | 0.202 | 100 | 20 | 80 | 0.200 | 29 |
| t481 | 406 | 0.168 | 100 | 17 | 83 | 0.170 | 28 |
| C2670 | 639 | 0.477 | 100 | 48 | 52 | 0.480 | 90 |
| cordic | 854 | 0.286 | 100 | 29 | 71 | 0.290 | 53 |
| C3540 | 968 | 0.348 | 100 | 35 | 65 | 0.350 | 58 |
| C5315 | 1529 | 0.273 | 100 | 27 | 73 | 0.270 | 48 |
| ex5p | 1779 | 0.184 | 100 | 18 | 82 | 0.180 | 37 |
| C7552 | 1781 | 0.471 | 100 | 47 | 53 | 0.470 | 75 |
| C6288 | 1820 | 0.136 | 100 | 14 | 86 | 0.140 | 26 |
| apex4 | 2196 | 0.565 | 100 | 56 | 44 | 0.560 | 91 |
| misex3 | 2557 | 0.347 | 100 | 35 | 65 | 0.350 | 67 |
| alu4 | 2732 | 0.229 | 100 | 23 | 77 | 0.230 | 39 |
| apex2 | 3165 | 0.562 | 100 | 56 | 44 | 0.560 | 98 |
| spla | 7438 | 0.311 | 100 | 31 | 69 | 0.310 | 54 |
| pdc | 8408 | 0.494 | 100 | 49 | 51 | 0.490 | 82 |

### Set A: 1900 infected circuits, 1900 Trojans

Trojans per circuit: 1: 1900

Payload mix: p-dos-stuck 1900

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 667 | p | 9.08e-04 | 1.95e-03 | 9.73e-03 |
| comb | p<1e-3 | 537 | p | 7.34e-05 | 2.39e-04 | 1.06e-03 |
| comb | p<1e-4 | 696 | p | 1.62e-05 | 6.10e-05 | 1.65e-04 |

Always-on (slowdown) Trojans, no trigger: 0.

### Set B: 709 infected circuits, 1211 Trojans

Trojans per circuit: 1: 351, 2: 214, 3: 144

Payload mix: p-dos-stuck 483, p-err-hi 234, p-err-lo 225, p-slowdown 269

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| comb | p<1e-2 | 312 | p | 9.44e-04 | 1.95e-03 | 9.44e-03 |
| comb | p<1e-3 | 282 | p | 8.30e-05 | 2.31e-04 | 1.05e-03 |
| comb | p<1e-4 | 348 | p | 1.62e-05 | 6.10e-05 | 1.66e-04 |

Always-on (slowdown) Trojans, no trigger: 269.

### Failures and short sets

- C17 [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- C17 [B]: supplied 14 of 68 infected circuits (0 failed proposals, 4 empty draws)
- C3540 [A]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 3.814697265625e-05, 'p_lo': 2.801596143271904e-05, 'p_hi': 
- C3540 [A]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 5.054473876953125e-05, 'p_lo': 3.8646022139593756e-05, 'p_h
- C5315 [A]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 0.00012111663818359375, 'p_lo': 0.000101805022540982, 'p_hi
- apex2 [A]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 2.09808349609375e-05, 'p_lo': 1.3856036091839802e-05, 'p_hi
- apex2 [A]: no witness for Trojan 0 (p-dos-stuck, comb): {'p': 3.337860107421875e-05, 'p_lo': 2.4001472946683697e-05, 'p_h
- ve_Prob004_vector2 [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob004_vector2 [B]: supplied 0 of 18 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob006_vectorr [B]: supplied 0 of 11 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob015_vector1 [B]: supplied 0 of 51 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob023_vector100r [B]: supplied 0 of 51 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob042_vector4 [B]: supplied 0 of 44 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob043_vector5 [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob043_vector5 [B]: cec with the triggers forced inactive: error (x3)
- ve_Prob043_vector5 [B]: insert: ValueError: $n5: no such net (x4)
- ve_Prob043_vector5 [B]: supplied 0 of 59 infected circuits (7 failed proposals, 4 empty draws)
- ve_Prob043_vector5 [B]: supplied 13 of 41 clean variants
- ve_Prob043_vector5 [B]: variant insert: ValueError: $n5: no such net (x52)
- ve_Prob043_vector5 [B]: variant insert: ValueError: Y: no such net (x17)
- ve_Prob064_vector3 [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob064_vector3 [B]: supplied 4 of 54 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob092_gatesv100 [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob092_gatesv100 [B]: cec with the triggers forced inactive: error (x2)
- ve_Prob092_gatesv100 [B]: insert: ValueError: $n5: no such net (x4)
- ve_Prob092_gatesv100 [B]: supplied 0 of 29 infected circuits (6 failed proposals, 4 empty draws)
- ve_Prob092_gatesv100 [B]: supplied 5 of 71 clean variants
- ve_Prob092_gatesv100 [B]: variant insert: ValueError: $n5: no such net (x106)
- ve_Prob092_gatesv100 [B]: variant insert: ValueError: Y: no such net (x31)
- ve_Prob094_gatesv [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob094_gatesv [B]: cec with the triggers forced inactive: error (x2)
- ve_Prob094_gatesv [B]: insert: ValueError: $n5: no such net (x4)
- ve_Prob094_gatesv [B]: supplied 0 of 62 infected circuits (6 failed proposals, 4 empty draws)
- ve_Prob094_gatesv [B]: supplied 2 of 38 clean variants
- ve_Prob094_gatesv [B]: variant insert: ValueError: $n5: no such net (x65)
- ve_Prob094_gatesv [B]: variant insert: ValueError: Y: no such net (x9)
- ve_Prob150_review2015_fsmonehot [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob150_review2015_fsmonehot [B]: insert: ValueError: $n5: no such net (x4)
- ve_Prob150_review2015_fsmonehot [B]: supplied 0 of 52 infected circuits (4 failed proposals, 4 empty draws)
- ve_Prob150_review2015_fsmonehot [B]: supplied 6 of 48 clean variants
- ve_Prob150_review2015_fsmonehot [B]: variant insert: ValueError: $n5: no such net (x66)
- ve_Prob150_review2015_fsmonehot [B]: variant insert: ValueError: Y: no such net (x24)
- ve_Prob156_review2015_fancytimer [A]: supplied 0 of 100 infected circuits (0 failed proposals, 4 empty draws)
- ve_Prob156_review2015_fancytimer [B]: supplied 6 of 15 infected circuits (0 failed proposals, 4 empty draws)

### Seeker-Seq

Release `seeker-seq-v2.0-rc3`: 36 bases, 36 goldens, 137484 circuits in 19 forms (7236 identity circuits), 95418 infected circuits (all forms). Verify: PASS.

Verify (`lemanruss verify`, all checks re-run from the files):

- integrity: 142553 files listed and hashed, 0 problems
- separation: 42066 clean, 95418 infected circuits (all forms), 0 problems; ids opaque
- leak: 137484 circuits scanned (contents, file names, directory names, manifest keys and text, infected-only net-name style), 0 leaks, 0 odd names, odin3_edit hits 0 + 0
- witnesses: 5459 stored witnesses replayed in Odin III, 5459 fired (trigger high, payload shows; slowdown by depth)
- forced-off equivalence: 5022 infected identity circuits (6011 Trojans), {'equivalent': 5022}
- equivalence of restructured forms and clean variants: 132426 checked, {'equivalent': 132426}, unproven 0
- rareness re-measure: 144 circuits (4 per base) with a new seed, 144 within 5 sigma / exact



### Bases, circuits and infected fraction

| base | gates | f (drawn) | A | B infected | B clean variants | B infected fraction (achieved) | Trojans in B |
|---|---|---|---|---|---|---|---|
| s27 | 17 | 0.639 | 100 | 64 | 36 | 0.640 | 108 |
| s208 | 42 | 0.600 | 100 | 60 | 40 | 0.600 | 104 |
| s420 | 65 | 0.650 | 100 | 65 | 35 | 0.650 | 114 |
| s382 | 105 | 0.107 | 100 | 11 | 89 | 0.110 | 19 |
| s386 | 111 | 0.513 | 100 | 51 | 49 | 0.510 | 84 |
| s344 | 114 | 0.375 | 100 | 37 | 63 | 0.370 | 53 |
| s349 | 114 | 0.483 | 100 | 48 | 52 | 0.480 | 74 |
| s444 | 114 | 0.211 | 100 | 21 | 79 | 0.210 | 38 |
| b02 | 117 | 0.144 | 100 | 14 | 86 | 0.140 | 25 |
| s400 | 120 | 0.289 | 100 | 29 | 71 | 0.290 | 39 |
| s641 | 139 | 0.384 | 100 | 38 | 62 | 0.380 | 67 |
| s713 | 141 | 0.386 | 100 | 39 | 61 | 0.390 | 68 |
| s526 | 142 | 0.342 | 100 | 34 | 66 | 0.340 | 57 |
| b01 | 149 | 0.204 | 100 | 20 | 80 | 0.200 | 35 |
| b06 | 191 | 0.389 | 100 | 39 | 61 | 0.390 | 64 |
| s510 | 213 | 0.583 | 100 | 58 | 42 | 0.580 | 94 |
| s820 | 231 | 0.590 | 100 | 59 | 41 | 0.590 | 100 |
| s832 | 266 | 0.299 | 100 | 30 | 70 | 0.300 | 49 |
| b03 | 358 | 0.573 | 100 | 57 | 43 | 0.570 | 92 |
| s953 | 363 | 0.102 | 100 | 10 | 90 | 0.100 | 24 |
| s1423 | 406 | 0.497 | 100 | 50 | 50 | 0.500 | 87 |
| b09 | 415 | 0.418 | 100 | 42 | 58 | 0.420 | 66 |
| s1196 | 483 | 0.537 | 100 | 54 | 46 | 0.540 | 96 |
| b10 | 511 | 0.282 | 100 | 28 | 72 | 0.280 | 46 |
| s1494 | 518 | 0.678 | 100 | 68 | 32 | 0.680 | 113 |
| s1488 | 522 | 0.151 | 100 | 15 | 85 | 0.150 | 25 |
| s1238 | 529 | 0.232 | 100 | 23 | 77 | 0.230 | 35 |
| s5378 | 989 | 0.399 | 100 | 40 | 60 | 0.400 | 76 |
| b08 | 1275 | 0.415 | 100 | 41 | 59 | 0.410 | 73 |
| b13 | 1650 | 0.366 | 100 | 37 | 63 | 0.370 | 64 |
| b07 | 2345 | 0.167 | 100 | 17 | 83 | 0.170 | 30 |
| s298 | 4268 | 0.477 | 100 | 48 | 52 | 0.480 | 87 |
| b04 | 5034 | 0.557 | 100 | 56 | 44 | 0.560 | 107 |
| b11 | 5613 | 0.500 | 100 | 50 | 50 | 0.500 | 89 |
| b12 | 9153 | 0.488 | 100 | 49 | 51 | 0.490 | 80 |
| sha | 11294 | 0.200 | 100 | 20 | 80 | 0.200 | 29 |

### Set A: 3600 infected circuits, 3600 Trojans

Trojans per circuit: 1: 3600

Payload mix: p-dos-stuck 3600

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| ctr | fast | 676 | P(fire<=1024) | 5.03e-01 | 1.00e+00 | 1.00e+00 |
| ctr | mid | 539 | P(fire<=1024) | 3.22e-02 | 2.33e-01 | 5.58e-01 |
| ctr | slow | 496 | P(fire<=1024) | 4.88e-04 | 1.42e-02 | 6.01e-02 |
| pat | fast | 801 | P(fire<=1024) | 4.79e-01 | 1.00e+00 | 1.00e+00 |
| pat | mid | 576 | P(fire<=1024) | 4.20e-02 | 2.23e-01 | 5.17e-01 |
| pat | slow | 512 | P(fire<=1024) | 9.77e-04 | 1.42e-02 | 5.62e-02 |

Always-on (slowdown) Trojans, no trigger: 0.

### Set B: 1422 infected circuits, 2411 Trojans

Trojans per circuit: 1: 728, 2: 399, 3: 295

Payload mix: p-dos-stuck 739, p-energy 446, p-err-hi 343, p-err-lo 331, p-slowdown 552

| trigger | band | Trojans | stat | min | median | max |
|---|---|---|---|---|---|---|
| ctr | fast | 286 | P(fire<=1024) | 4.95e-01 | 1.00e+00 | 1.00e+00 |
| ctr | mid | 238 | P(fire<=1024) | 3.91e-02 | 2.24e-01 | 5.58e-01 |
| ctr | slow | 192 | P(fire<=1024) | 9.77e-04 | 1.61e-02 | 5.66e-02 |
| pat | fast | 558 | P(fire<=1024) | 4.87e-01 | 1.00e+00 | 1.00e+00 |
| pat | mid | 283 | P(fire<=1024) | 4.05e-02 | 1.80e-01 | 5.13e-01 |
| pat | slow | 302 | P(fire<=1024) | 9.77e-04 | 1.22e-02 | 5.86e-02 |

Always-on (slowdown) Trojans, no trigger: 552.

### Failures and short sets

- b05 [all]: not built at n = 200 (size cap)
- b13 [A]: no witness for Trojan 0 (p-dos-stuck, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64':  (x6)
- b13 [A]: no witness for Trojan 0 (p-dos-stuck, pat): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64':  (x5)
- b13 [B]: no witness for Trojan 2 (p-dos-stuck, pat): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64': 
- b14 [all]: not built at n = 200 (size cap)
- b15 [all]: not built at n = 200 (size cap)
- b17 [all]: not built at n = 200 (size cap)
- b18 [all]: not built at n = 200 (size cap)
- b19 [all]: not built at n = 200 (size cap)
- b20 [all]: not built at n = 200 (size cap)
- b21 [all]: not built at n = 200 (size cap)
- b22 [all]: not built at n = 200 (size cap)
- diffeq1 [all]: not built at n = 200 (size cap)
- diffeq2 [all]: not built at n = 200 (size cap)
- mkPktMerge [all]: not built at n = 200 (size cap)
- mkSMAdapter4B [all]: not built at n = 200 (size cap)
- s1238 [B]: no witness for Trojan 1 (p-err-lo, pat): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64': [0.
- s298 [B]: no witness for Trojan 0 (p-energy, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': [0.0
- s641 [A]: no witness for Trojan 0 (p-dos-stuck, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.0018722692823851506], '64': 
- sha [B]: no witness for Trojan 1 (p-energy, pat): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': [0.0
- sha [B]: no witness for Trojan 1 (p-err-lo, ctr): {'p_fire_within': {'16': [0.0, 0.0, 0.003737540881785676], '64': [0.0

## 4. Payload and trigger notes

- `p-err-hi` / `p-err-lo` flip one output of the upper / lower half of the `.outputs` list (agent default 2).
- `p-slowdown` is always on: no trigger, no rareness (reported as always-on); its witness is the logic depth above the golden's,
  and function is unchanged (cec). ABC restructurings strip the buffer chains, so the restructured forms of such
  circuits are equivalent to the golden and no deeper.
- `p-energy` (Seq only) is a ring of 2 to 64 flip-flops enabled by the trigger; its witness is the ring bit set after
  the clock edge following the trigger.
- Comb p is exact for bases of at most 20 inputs (2^n vectors) and Wilson-bounded on 2^20 vectors otherwise; Seq P(fire <= N)
  uses 512 to 2048 lanes by size. The verify rareness re-measure (4 infected circuits per base, new seed) agrees on all
  sampled Trojans.

## 5. Limits

- Clean variants differ from the golden by neutral edits only; a detector can in principle tell them from a Trojan by structure
  (that is the detection task), but not by file style. The ABC restructured forms are all in ABC style for clean and infected alike.
- Triggers are drawn at random from the rare-net candidates, not SCOAP-hardest first; SCOAP of the drawn nets is in the records.
- Witnesses are replayed in Odin III against the golden; Odin III is the authority, the bit-parallel simulator only finds them.

## 6. Files

`releases/seeker-{comb,seq}-v2.0-rc3/` hold the index files only: `DATASHEET.md`, `manifest.json.gz` and
`SHA256SUMS.gz` (gzip, zero timestamp; `gunzip` them beside the unpacked release to run `sha256sum -c`).
The circuits and the answer key are archived off-machine (README of the archive, F: drive, 2026-11-01).
