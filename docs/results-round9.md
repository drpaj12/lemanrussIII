# Round 9 results: rc7 magic-number triggers (2026-11-02)

Peter 2026-11-02, verbatim: "Make the sequential triggers simple magic number triggers. Then we
don't have to worry about the FF hiding." Replaces the retiming plan
(`briefs/lemanruss-seq-rc7-retime.md`, cancelled). Design: `docs/specs/2026-10-31-htl-design.md`
section 13. HW2VEC is dropped from this round's detector suite (Peter 2026-11-02): no HW2VEC arm,
no HW2VEC number anywhere in this document.

## 1. Design recap

`StatePatternTrigger` (`t-state-pattern`): an AND of `k` literals over register (flip-flop) Q
outputs and/or primary inputs, the same combinational-AND shape as `t-comb-rare`
(`lemanruss.htl.edit_netlist.comb_rare_trigger`, no `ed.latch`). Candidate literals come from
`lemanruss.htl.seqtune._state_candidates` (latch Q nets + primary inputs, SCOAP-ranked, a scan-
view random sample); reachability and the target band (fast/mid/slow, `P(fire<=1024 cycles)`,
same bands rc6 used) come from the existing multi-cycle window observation
(`lemanruss.htl.seqtune.observe`), extended to report "fired at least once by cycle N"
(`ge[j][0]`) alongside the existing counter-bit readers. `t-seq-counter`/`t-seq-pattern` stay in
the code, unused by rc7.

Payloads checked against `lemanruss/htl/edit_netlist.py`'s recipes: `dos_stuck`, `err_bit`,
`slowdown`, `slowdown_absorb` use only `ed.names` (no state added), kept; `energy` calls
`ed.latch` once per toggle bit, EXCLUDED from rc7 (the one payload kind that adds a flip-flop).

FF/latch equality hard gate (spec section 13.4): per infected circuit, before ABC,
`len(latches_of(infected)) == len(latches_of(clean golden))`, exact; a mismatch is a build
Failure, not a Built circuit.

## 2. Smoke (2 Seq bases: s27, s208)

`lemanruss.htl.n200rc7.run_family_rc7` on `s27.blif`/`s208.blif` (the same two bases rc6's own
smoke used), K4/K6/G sets: 383 rareness records, 383/383 `ff_count_clean == ff_count_infected`
(0 mismatches), every `trojan_id` `t-state-pattern__*__netlist`, mix 226 clean / 228 infected.
Output: `work/htl-out/rc7/smoke-seq/`.

## 3. Full Seeker-Seq rc7 build

The 36 Seeker-Seq bases rc6 used (`work/htl-out/rc5/bases/`), K4/K6/G sets,
`lemanruss.htl.n200rc7.run_family_rc7`, seed kept with the answer key, 4 workers. Output `work/htl-out/rc7/seq/`.

**First attempt failed twice (root causes, fixed).**

1. Assembly `KeyError: 'K6'` (`n200run.assemble`, `per_set[c["set"]]`). Cause: in
   `build_base_rc7` the `try` wrapped the loop over all three sets. On 17 of 36 bases a set
   raised `ValueError: bitsim: combinational loop or undriven net` mid-build, after some of its
   circuits had been appended to the base's circuit list; the except clause ended the whole
   base, so `sets` had no entry for that set but `circuits` still held its circuits (s382: 100
   K4 and 3 K6 circuits, only K4 in `sets`). The loop itself is a Trojan bug (next point), the
   KeyError was the symptom. The per-base outputs were therefore NOT complete: the 17 affected
   per-base job files (b01-b04, b06-b13, s382, s444, s526, s953, s1238) were moved to
   `answer_key/jobs-bad/` and rebuilt; the other 19 (valid) were reused from the first run.
   Fix: the `try` is now per set; a set that raises is dropped whole (its circuits removed, a
   failure recorded for that set), the other sets of the base still build.
2. The combinational loop. Cause: a trigger literal on the same net as the payload's victim.
   b02's output `u` is a flip-flop Q; the payload re-drives `u`, and a trigger that also reads
   `u` reads the payload's own output. Fix: `SeqCtxRc7._draw_triggered` redraws when the victim
   is in the trigger's net set (spec section 13.2).
   Tests: `tests/test_rc7_victim_loop.py` (fails without the fix, passes with it; assembly of a
   result whose set raised).

Rebuilt result (second run): 36 bases, **10503 circuits** (6583 clean, 3920 infected), 6546
Trojans on 3920 infected circuits; K4 3539, K6 3353, G 3575 circuits.

| payload | Trojans | trigger |
|---|---|---|
| p-slowdown (absorption stage, always on) | 3709 | none (t-always-on) |
| p-dos-stuck | 1397 | t-state-pattern |
| p-err-lo | 728 | t-state-pattern |
| p-err-hi | 712 | t-state-pattern |

(`p-energy` is not used, so no payload in rc7 adds state; `p-dos-reset` is not in the Seq mix.)

**Reachability and rareness (2837 magic-number Trojans).** N = 1024 cycles; bands as rc6 on
P(trigger high at least once within N): fast 0.5-1.0 (2252 Trojans), mid 0.05-0.5 (412), slow
0.003-0.05 (173); the band is the target the draw selects on the selection sample, `MIN_HITS` =
4. Trigger width k (literals): 1: 223, 2: 360, 3: 393, 4: 423, 5: 672, 6: 381, 7: 384, 8: 1.
All 2837 are reached (the Trojan is not dead): re-measured P(fire within 1024) minimum 0.0010,
median 1.0, maximum 1.0 (within 16 / 64 / 256 cycles: median 0.33 / 0.81 / 1.00; reached in
2567 / 2764 / 2818 Trojans). Reading: the fast band dominates and most fast values are hit in
nearly every lane, because state bits of small sequential benchmarks take most values; the mid
and slow bands exist but are smaller than in rc6 (rc6 counters could be tuned to any rate).
Sequential SCOAP (`trigger_sc`, max over literals): median 5, maximum 2257185 (the large values
are literals SCOAP finds nearly uncontrollable), victim observability `co` 0 for every Trojan
(Odin III's sequential SCOAP, as in rc6). Independent re-measure by `lemanruss verify` (216
circuits, 732 checks): all within tolerance.

Failures recorded in `answer_key/failures.json` (543 rejected draws, never shipped): 460 `no
free source for the slowdown` (small bases), 49 `no witness` (a magic value reached in the
random window but no input sequence that also flips an output, `shows` false), 24 `obfuscated
circuit vs its source: error (rc 2)` (a stitched slow-down cut ABC could not compare), 10
`supplied fewer circuits than drawn`.

**FF gate, before ABC (hard).** `ff_count_clean == ff_count_infected` on 6546 / 6546 records,
0 mismatches (`lemanruss.htl.ffgate`, `n200rc7.build_pre_rc7`).

## 4. Release and archive

`seeker-seq-v2.0-rc7` packaged with `lemanruss release --n200` (same tool pin as rc6: Odin III
main 4c91edff, build `rel-main2`; ABC 1.01), 10503 circuits, `htl-rel/rc7/seeker-seq-v2.0-rc7`.
`lemanruss verify` **PASS**: a integrity (14471 files), b leak words 0, c function (2837
witnesses replayed and fired in Odin III, 3920 forced-off equivalent, 3920 obfuscation-
equivalent, 6547 clean equivalent, 0 failures), d rareness (216 circuits re-measured, all ok),
e separation (no problems), f_distinct (0 duplicate groups), g_style (255 tests, 0 flagged,
best AUROC bound 0.60), h_provenance (0 traces). The datasheet text was corrected after the
verify run (the text still said counter and FSM-pattern triggers); only `DATASHEET.md` and
`SHA256SUMS` changed, a directory diff against the verified tree shows no other change.
Archive: `<archive>/2026-11-03/seeker-seq-v2.0-rc7/` (circuits and answer-key
tar.xz, `SHA256SUMS` verified, `tar -d` no differences);
circuits `089e055b4e2df8bcb322714d244ee84b69767b9c5688b713c0c53aceedbad20a`,
answer key `78e7d7a1ac7dd59732fc4aa29a73e2e87d32c84cde23bbb6a2a3f4f407e5a369`.
`releases/seeker-seq-v2.0-rc7/` holds datasheet, manifest, checksums. README marks rc6 as
superseded by rc7 for the Seq family (reason: the Trojan flip-flop count separated rc6's labels
at AUROC 0.948 by construction; rc7 adds no flip-flop). No Mimir repo PR (rc6 had none).


## 5. Seeker-Proc pilot3

Brief "ADDED 2026-11-02: Seeker-Proc too." `t-input-pattern` (one magic fetched word) kept on
both public cores (mcu, darkriscv); `t-seq-pattern` (the magic-sequence FSM, adds a register)
DROPPED -- `proc-mcu-magicseq3-stall` (pilot2) is not rebuilt for pilot3. Kept trojans:
`proc-mcu-magicword-stall` (mcu, `p-dos-stuck` on the core's own stall mux) and
`proc-dark-magicword-reset` (darkriscv, `p-dos-reset` ORed into the core's own `XRES`); both
payloads reuse an existing register/mux input (checked against the RTL patch text, not assumed).
A second magic-number kind on an existing data value was looked at and not added this round
(time-boxed, recorded, not silently skipped). Same FF/latch equality hard gate as section 1, per
circuit against its clean twin.


**Pilot3 build** (`lemanruss.htl.proc_pilot3`, `work/htl-out/rc7/proc-pilot3/`,
release `htl-rel/rc7/seeker-proc-v2.0-pilot3`, 4 circuits: clean and infected for each core).
The first run crashed with `FileNotFoundError: .../mcu-infected/blink.vmh`. Cause: the scratch
build script read a single `blink.vmh` from the infected build dir; the MCU program image is
four byte planes `0blink.vmh` .. `3blink.vmh`, and the witness image to ship is the one
`run_mcu_pilot` wrote into its own pilot work dir, not the shipped program. Fix:
`proc_pilot3.mcu_witness_image` (test `tests/test_proc_pilot3.py`). A second run then failed for
darkriscv (`missing_file: 'darksocv.v'`): `prepare_dark`'s file list is relative to `<build>/rtl`
and Odin III was run in `<build>`; fix `dark_rtl_dir`. Third run completed. The script is now
in the repo (paths from the environment), no longer a scratch file.

| Trojan | core | trigger | payload | witness fires | iverilog = Odin RTL = Odin netlist | shipped-program no-fire | P(match) | SCOAP CC0 / CC1 / CO | FF clean = infected |
|---|---|---|---|---|---|---|---|---|---|
| proc-mcu-magicword-stall | mcu | t-input-pattern, 1 word (32 bits) | p-dos-stuck on `next_PC_select` | yes | yes (clean, infected, netlist) | yes, 4 of 4 programs (blink, blink_interrupt, blink_function_call, interrupt) | 2.3e-10 | 9 / 128 / 3 | 132446 = 132446 |
| proc-dark-magicword-reset | darkriscv | t-input-pattern, 1 word (IDATA qualified by IDACK) | p-dos-reset ORed into `XRES` | yes | yes | yes, prebuilt firmware | 2.3e-10 | 2 / 130 / 2 | 67638 = 67638 |

`lemanruss.htl.proc_release.verify_proc_pilot2` on the release: integrity, name vocabulary,
content leak scan and infected-only pattern all pass. Rareness items i-iii as pilot2 (match
probability 2^-32, SCOAP, witness); item iv (P(fire within N)) is undefined for a combinational
trigger. Equivalence with the trigger forced inactive was NOT re-run: pilot2's ABC `dsec` was
`unproven` on both cores (mcu timed out at the 300 s wrapper, darkriscv at ABC's 600 s limit,
RAM lowered to tens of thousands of latches), and the pilot3 Trojans are the same RTL patches
as pilot2's magic-word Trojans, so the verdict stands as `unproven`, stated rather than hidden.
No second magic-number kind (data value) was added; no `t-seq-pattern`. Archive:
`<archive>/2026-11-03/seeker-proc-v2.0-pilot3/seeker-proc-v2.0-pilot3.tar.xz`,
sha256 `ebf83ec507c2c392a5f855b4c462fd28ad3e8a802daeafa5abec57ce561251d5` (verified, `tar -d`
no differences).


## 6. Detector cache fix

Peter 2026-11-02: before the detector runs, a generic fix in `lemanruss.detect` so the GNN graph
cache is keyed by the circuit file's own sha256 (not circuit id) -- circuit ids collide across
releases/styles. `lemanruss/detect/features.py` `cache_path` now keys on `sha256_of(cf.path)`
(every `cached()`/`fill()` kind, including the GNN detector's own in-memory `self.graphs`);
`tests/test_detect_cache.py` (same id, different content -> different cache entries; different
id, same content -> one shared entry).

## 7. Leak table (FF/latch gate, post-ABC)

Hard gate (before ABC): 6546 of 6546 Trojans have infected FF/latch count equal to the golden's,
0 mismatches. After ABC, on the 10503 released circuits, AUROC clean vs infected within each base
and set (108 strata, pooled by pair count), percentile bootstrap CI over bases (2000 draws, seed
0), `lemanruss.htl.ffgate`:

| measure | all | K4 | K6 | G |
|---|---|---|---|---|
| total FF count | 0.500 [0.500, 0.500] | 0.500 | 0.500 | 0.500 |
| log(1 + FF) | 0.500 [0.500, 0.500] | 0.500 | 0.500 | 0.500 |
| latch share (FF / cells) | 0.242 [0.199, 0.288] | 0.241 | 0.262 | 0.222 |

rc6 for comparison: FF count 0.948. FF count and log(1 + FF) are exactly 0.5 with a degenerate
CI: within every base and set the flip-flop count is the same for clean and infected (ABC
here does not change it), so the measure carries no information. The latch share is below 0.5
(i.e. 0.76 if inverted) for a different reason: the infected circuits have more combinational
cells (the trigger comparator, the payload and especially the always-on absorption stage), so
FF / cells is lower. That is a size effect, not a state effect; it is the same signal the size
control sees (section 8). It is reported, not tuned away. Other leak gates are in section 4
(f_distinct, g_style, h_provenance: all clean).


## 8. Detector table

PR #12's headline budget (12 epochs, batch 32, seed 0, 1500-circuit training cap), base split,
`lemanruss.detect` unchanged: size, classhist, FF count (section 7's measure, reused here as a
detector-style signal), gnn-a, gnn-a-nosc. Same "is it detecting size" check as rc5/rc6
(size-only AUROC and oracle-location check). W/L/T vs the size control, per set and per payload
where the sample supports it.

Seq rc7 (36 bases, 10503 circuits). PR #12's headline budget: 12 epochs, batch 32, seed 0, at
most 1500 training circuits per fold-run (a seeded random subset of the training side), five
folds, `lemanruss.detect.run` unchanged except one added control detector, `ffcount`
(score = log(1 + flip-flop count), no training; `lemanruss/detect/ffcount.py`). No HW2VEC arm.
Odin III `build/rel-main2`. Also run: sanity, rare (rare-signal score), graphlet-b (cheap).
Budget printed next to every number: this is a reduced budget, not the protocol's 200 epochs.
"W/L/T vs size" counts test bases on which the method's within-base AUROC is higher / lower /
equal than the size control's. Raw outputs: `work/htl-out/rc7/det/`.

### Headline (means over folds and seeds; AUROC with 95% base-bootstrap)

| detector | split | AUROC [95% CI] | TPR | FPR | F1 rel | F1 10% | F1 30% | F1 50% | F1 70% | W/L/T vs size | label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| size | base | 0.593 [0.562, 0.650] | 0.089 | 0.048 | 0.142 | 0.107 | 0.136 | 0.146 | 0.150 | control | ABOVE CHANCE |
| ffcount | base | 0.492 [0.458, 0.531] | 0.131 | 0.122 | 0.096 | 0.037 | 0.085 | 0.116 | 0.137 | 7/29/0 | INCONCLUSIVE |
| classhist | base | 0.660 [0.620, 0.716] | 0.185 | 0.085 | 0.256 | 0.172 | 0.243 | 0.268 | 0.280 | 23/13/0 | ABOVE CHANCE |
| sanity | base | 0.481 [0.445, 0.513] | 0.074 | 0.078 | 0.103 | 0.060 | 0.098 | 0.112 | 0.120 | 5/31/0 | INCONCLUSIVE |
| rare | base | 0.497 [0.463, 0.542] | 0.059 | 0.034 | 0.091 | 0.062 | 0.088 | 0.096 | 0.100 | 13/23/0 | INCONCLUSIVE |
| graphlet-b | base | 0.504 [0.465, 0.536] | 0.124 | 0.084 | 0.148 | 0.086 | 0.140 | 0.163 | 0.176 | 10/26/0 | INCONCLUSIVE |
| gnn-a | base | 0.482 [0.440, 0.535] | 0.106 | 0.088 | 0.136 | 0.078 | 0.127 | 0.148 | 0.160 | 8/28/0 | INCONCLUSIVE |
| gnn-a-nosc | base | 0.532 [0.499, 0.580] | 0.055 | 0.043 | 0.089 | 0.063 | 0.086 | 0.093 | 0.097 | 12/24/0 | INCONCLUSIVE |
| size | set-K4 | 0.617 [0.562, 0.695] | 0.089 | 0.011 | 0.141 | 0.122 | 0.139 | 0.143 | 0.145 | control | ABOVE CHANCE |
| ffcount | set-K4 | 0.458 [0.404, 0.523] | 0.125 | 0.125 | 0.101 | 0.034 | 0.081 | 0.111 | 0.132 | 6/30/0 | INCONCLUSIVE |
| classhist | set-K4 | 0.685 [0.624, 0.769] | 0.221 | 0.118 | 0.291 | 0.176 | 0.274 | 0.309 | 0.328 | 22/13/1 | ABOVE CHANCE |
| sanity | set-K4 | 0.459 [0.399, 0.511] | 0.065 | 0.135 | 0.084 | 0.040 | 0.075 | 0.093 | 0.103 | 7/29/0 | INCONCLUSIVE |
| rare | set-K4 | 0.469 [0.412, 0.536] | 0.054 | 0.045 | 0.087 | 0.059 | 0.083 | 0.091 | 0.094 | 8/28/0 | INCONCLUSIVE |
| graphlet-b | set-K4 | 0.490 [0.424, 0.557] | 0.073 | 0.052 | 0.080 | 0.043 | 0.076 | 0.092 | 0.101 | 8/28/0 | INCONCLUSIVE |
| gnn-a | set-K4 | 0.469 [0.400, 0.552] | 0.072 | 0.062 | 0.093 | 0.051 | 0.083 | 0.097 | 0.106 | 9/27/0 | INCONCLUSIVE |
| gnn-a-nosc | set-K4 | 0.426 [0.381, 0.492] | 0.042 | 0.078 | 0.055 | 0.030 | 0.053 | 0.063 | 0.069 | 7/29/0 | BELOW CHANCE |
| size | set-K6 | 0.649 [0.606, 0.707] | 0.045 | 0.010 | 0.079 | 0.069 | 0.078 | 0.080 | 0.081 | control | ABOVE CHANCE |
| ffcount | set-K6 | 0.479 [0.433, 0.535] | 0.138 | 0.116 | 0.109 | 0.040 | 0.091 | 0.121 | 0.142 | 3/32/1 | INCONCLUSIVE |
| classhist | set-K6 | 0.675 [0.628, 0.743] | 0.141 | 0.046 | 0.219 | 0.167 | 0.211 | 0.224 | 0.230 | 26/10/0 | ABOVE CHANCE |
| sanity | set-K6 | 0.489 [0.437, 0.542] | 0.029 | 0.014 | 0.046 | 0.033 | 0.045 | 0.048 | 0.050 | 9/27/0 | INCONCLUSIVE |
| rare | set-K6 | 0.511 [0.447, 0.579] | 0.048 | 0.067 | 0.072 | 0.046 | 0.068 | 0.076 | 0.080 | 7/29/0 | INCONCLUSIVE |
| graphlet-b | set-K6 | 0.548 [0.492, 0.606] | 0.177 | 0.108 | 0.195 | 0.105 | 0.178 | 0.209 | 0.227 | 7/29/0 | INCONCLUSIVE |
| gnn-a | set-K6 | 0.531 [0.467, 0.599] | 0.238 | 0.190 | 0.292 | 0.156 | 0.262 | 0.311 | 0.339 | 11/25/0 | INCONCLUSIVE |
| gnn-a-nosc | set-K6 | 0.477 [0.419, 0.545] | 0.122 | 0.128 | 0.125 | 0.053 | 0.108 | 0.137 | 0.155 | 9/27/0 | INCONCLUSIVE |
| size | set-G | 0.640 [0.598, 0.696] | 0.834 | 0.758 | 0.519 | 0.195 | 0.463 | 0.641 | 0.768 | control | ABOVE CHANCE |
| ffcount | set-G | 0.535 [0.463, 0.594] | 0.130 | 0.123 | 0.076 | 0.036 | 0.084 | 0.115 | 0.136 | 7/29/0 | INCONCLUSIVE |
| classhist | set-G | 0.571 [0.522, 0.646] | 1.000 | 1.000 | 0.524 | 0.182 | 0.462 | 0.667 | 0.824 | 18/18/0 | ABOVE CHANCE |
| sanity | set-G | 0.509 [0.424, 0.574] | 0.162 | 0.152 | 0.205 | 0.120 | 0.199 | 0.232 | 0.251 | 5/31/0 | INCONCLUSIVE |
| rare | set-G | 0.505 [0.439, 0.583] | 0.080 | 0.029 | 0.117 | 0.086 | 0.116 | 0.125 | 0.129 | 8/28/0 | INCONCLUSIVE |
| graphlet-b | set-G | 0.476 [0.405, 0.533] | 0.110 | 0.103 | 0.134 | 0.075 | 0.128 | 0.151 | 0.164 | 8/28/0 | INCONCLUSIVE |
| gnn-a | set-G | 0.546 [0.470, 0.600] | 0.267 | 0.249 | 0.219 | 0.122 | 0.217 | 0.273 | 0.311 | 7/29/0 | INCONCLUSIVE |
| gnn-a-nosc | set-G | 0.526 [0.467, 0.591] | 0.267 | 0.258 | 0.179 | 0.077 | 0.165 | 0.221 | 0.260 | 13/23/0 | INCONCLUSIVE |


### AUROC by rareness band / variant, base split

| detector | magic-fast | magic-mid | magic-slow | none-always-on |
|---|---|---|---|---|
| size | 0.52 | 0.55 | 0.46 | 0.65 |
| ffcount | 0.52 | 0.61 | 0.65 | 0.45 |
| classhist | 0.57 | 0.60 | 0.58 | 0.73 |
| sanity | 0.47 | 0.44 | 0.47 | 0.50 |
| rare | 0.45 | 0.56 | 0.56 | 0.53 |
| graphlet-b | 0.51 | 0.51 | 0.45 | 0.52 |
| gnn-a | 0.47 | 0.58 | 0.40 | 0.51 |
| gnn-a-nosc | 0.54 | 0.55 | 0.53 | 0.51 |

### AUROC by set, base split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | 0.58 | 0.63 | 0.64 |
| ffcount | 0.53 | 0.46 | 0.48 |
| classhist | 0.59 | 0.67 | 0.72 |
| sanity | 0.54 | 0.44 | 0.50 |
| rare | 0.50 | 0.47 | 0.51 |
| graphlet-b | 0.48 | 0.49 | 0.55 |
| gnn-a | 0.50 | 0.44 | 0.48 |
| gnn-a-nosc | 0.47 | 0.55 | 0.52 |

### AUROC by Trojan count, base split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.57 | 0.61 | 0.63 |
| ffcount | 0.48 | 0.50 | 0.51 |
| classhist | 0.62 | 0.67 | 0.74 |
| sanity | 0.49 | 0.47 | 0.48 |
| rare | 0.48 | 0.50 | 0.53 |
| graphlet-b | 0.50 | 0.50 | 0.51 |
| gnn-a | 0.48 | 0.46 | 0.50 |
| gnn-a-nosc | 0.53 | 0.54 | 0.53 |

### AUROC and W/L/T vs size by payload, base split

| payload | infected | detector | AUROC | W/L/T vs size |
|---|---|---|---|---|
| p-dos-stuck | 1194 | size | 0.530 | control |
| p-dos-stuck | 1194 | ffcount | 0.558 | 13/23/0 |
| p-dos-stuck | 1194 | classhist | 0.581 | 26/9/1 |
| p-dos-stuck | 1194 | sanity | 0.463 | 8/28/0 |
| p-dos-stuck | 1194 | rare | 0.475 | 13/23/0 |
| p-dos-stuck | 1194 | graphlet-b | 0.505 | 16/20/0 |
| p-dos-stuck | 1194 | gnn-a | 0.492 | 11/25/0 |
| p-dos-stuck | 1194 | gnn-a-nosc | 0.545 | 18/18/0 |
| p-err-hi | 662 | size | 0.543 | control |
| p-err-hi | 662 | ffcount | 0.552 | 14/21/0 |
| p-err-hi | 662 | classhist | 0.593 | 24/10/1 |
| p-err-hi | 662 | sanity | 0.472 | 9/26/0 |
| p-err-hi | 662 | rare | 0.475 | 16/19/0 |
| p-err-hi | 662 | graphlet-b | 0.509 | 14/20/1 |
| p-err-hi | 662 | gnn-a | 0.508 | 11/24/0 |
| p-err-hi | 662 | gnn-a-nosc | 0.552 | 13/22/0 |
| p-err-lo | 674 | size | 0.528 | control |
| p-err-lo | 674 | ffcount | 0.561 | 13/23/0 |
| p-err-lo | 674 | classhist | 0.596 | 27/9/0 |
| p-err-lo | 674 | sanity | 0.456 | 11/25/0 |
| p-err-lo | 674 | rare | 0.462 | 16/20/0 |
| p-err-lo | 674 | graphlet-b | 0.512 | 14/22/0 |
| p-err-lo | 674 | gnn-a | 0.475 | 12/24/0 |
| p-err-lo | 674 | gnn-a-nosc | 0.559 | 19/17/0 |
| p-slowdown | 2483 | size | 0.645 | control |
| p-slowdown | 2483 | ffcount | 0.455 | 3/33/0 |
| p-slowdown | 2483 | classhist | 0.729 | 24/12/0 |
| p-slowdown | 2483 | sanity | 0.487 | 4/32/0 |
| p-slowdown | 2483 | rare | 0.520 | 8/28/0 |
| p-slowdown | 2483 | graphlet-b | 0.510 | 7/29/0 |
| p-slowdown | 2483 | gnn-a | 0.494 | 4/32/0 |
| p-slowdown | 2483 | gnn-a-nosc | 0.518 | 11/25/0 |


**Proc pilot3** (4 circuits; detectors trained on the identity forms of Comb rc5 and Seq rc7,
threshold at FPR 5% on validation, `lemanruss.detect.run --proc`; raw outcomes, no statistics):

| detector | pp0001 clean dark | pp0002 infected dark | pp0003 clean mcu | pp0004 infected mcu | flags |
|---|---|---|---|---|---|
| size | -1.2783 | -1.2784 | -1.8665 | -1.8665 | - - - - |
| ffcount | 11.1219 | 11.1219 | 11.7939 | 11.7939 | F F F F |
| classhist | -4.3557 | -4.3559 | -5.6396 | -5.6397 | - - - - |
| gnn-a | -0.0537 | -0.0524 | not scored | not scored | - - n/a n/a |
| gnn-a-nosc | -0.1795 | -0.1772 | -0.2294 | -0.2294 | - - - - |

gnn-a could not score the mcu pair (its SCOAP columns cannot see inside the hierarchical
netlist's submodules, as in pilot2); never imputed.

Every detector scores a clean circuit and its infected twin within 0.0023 (all detectors) or
exactly equal (ffcount, gnn-a-nosc on mcu): the Trojan adds no flip-flop and a handful of gates to a netlist of
tens of thousands of cells. FF count flags all four (these netlists have 67 to 132 thousand
latches because RAM is lowered to per-bit latches, far above the Comb/Seq training range), a
false positive on the clean twins. This is a smoke set: 2 clean, 2 infected, no AUROC.


Comb rc5 numbers are unchanged (no rerun this round; see `docs/results-detectors.md`).

## 9. Verdict

Headline (CAD convention: win/loss counts first, then the strict label).

1. FF gate (the design target). Hard gate 6546/6546 exact; post-ABC FF-count AUROC 0.500
   [0.500, 0.500] (rc6: 0.948). **SUPPORTED**: the Trojan's flip-flops no longer separate the
   labels.
2. Class-only GNN (gnn-a, gnn-a-nosc), which reached 0.98 to 1.00 on Seq rc5 / rc6, now:
   gnn-a 0.482 [0.440, 0.535], W/L/T vs size 8/28/0, INCONCLUSIVE; gnn-a-nosc 0.532 [0.499,
   0.580], 12/24/0, INCONCLUSIVE. Both lose to the size control on most bases. **The rc6
   separation was the Trojan's state, as hypothesised: SUPPORTED.**
3. Not hidden: the size control reaches 0.593 [0.562, 0.650] (ABOVE CHANCE, a small effect) and
   `classhist` (cell-class histogram) 0.660 [0.620, 0.716] (ABOVE CHANCE; W/L/T vs size
   23/13/0, so it wins over size). The always-on absorption slowdown is the main carrier (size
   0.645, classhist 0.729 on circuits with that payload; 0.52-0.55 for the triggered payloads
   alone). Nothing else separates: FF count, sanity, rare, graphlet-b and both GNNs are all
   INCONCLUSIVE or lose to size.
4. No detector reaches the rc6 level. Seeker-Seq rc7 is a harder, size-limited benchmark; it
   is not "solved" or "unsolvable": the remaining signal is cell count and class mix, which the
   slowdown payload (not the trigger) introduces. Whether that is a fair footprint of the
   Trojan or a generator artefact is open (the clean circuits carry dummy cuts of the same size
   distribution, so size is matched in distribution, not per circuit).
5. Proc pilot3: 4 circuits; no detector separates a clean core from its infected twin.
6. Reduced GNN budget (12 epochs, 1500 cap, seed 0): a longer budget could move the GNNs;
   not run this round.

