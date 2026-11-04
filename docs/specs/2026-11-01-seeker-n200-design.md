# Seeker v2.0 at n = 200 per base: design (round 8, 2026-11-01)

Purpose (hub docs/purpose.md, Leman Russ III R1): give Seeker-Comb and Seeker-Seq the n of Seeker1
(100 infected circuits per base plus one golden) and a second set with mixed insertions, so a
detector is tested on many distinct Trojans per base, on single and multiple infections, on several
payload types, and against clean circuits that are not the golden. Measure: number of distinct
Trojans per base, rareness per Trojan (comb band p, seq P(fire <= N)), and a proof for every
claim (witness, equivalence). Seeker-Proc is not touched (PR #9 fix round is running).

Peter, 2026-11-01, verbatim: "For n, we had 100 infected or not infected and 1 golden. Make a
second of each with a mix of different insertions. So n = 200 where the first 100 are of denial and
the second are of any where there's a percent inserted between 10% and 70% infected and they could
have > 1 infection."

## 1. Reading of the request (the controller's reading; Peter may correct it)

Per base, and per restructured form:

- 1 **golden**: the clean base, unmodified.
- **Set A**: 100 circuits, every one infected with exactly one DoS Trojan (trigger + `p-dos-stuck`),
  as Seeker1.
- **Set B**: 100 circuits. A fraction f of them is infected; f is drawn once per base, uniformly
  from [0.10, 0.70], seeded, and recorded in the answer key. An infected circuit carries 1..k
  Trojans, k = 3 (P(1) = 0.5, P(2) = 0.3, P(3) = 0.2). The other (1-f) * 100 circuits are **clean
  variants** (section 4), never byte-identical to the golden.
- Per base: 201 circuits (identity form) and 201 * 19 = 3819 with the 18 ABC restructurings of
  every circuit (section 7).

## 2. Distinctness

A Trojan is identified by its key: (sorted trigger nets or, for seq, the counter condition / pattern
sequence and width, payload kind, victim net, payload parameter: stuck value, flip or force, ring
bits, chain depth). Rules, enforced when the pool is drawn and re-checked on the finished base:

- (rc3 only: no two Trojans of one base share a trigger net set; rc4: each circuit has its own
  rewrite whose internal names differ, so the rule holds inside a circuit, below);
- no two circuits of one base have the same set of Trojan keys;
- a circuit is never a copy of another circuit of the base (hash of the written file, checked);
- sets A and B do not share a Trojan key.

A base that cannot supply the Trojans a set needs (too few rare nets, too few outputs, a band that
no AND of its nets reaches, no sequential rare condition) is built with as many distinct circuits as
it can supply, **never padded with copies**; the count it reached per set is in `failures.json`, in
the datasheet and in docs/results-round8.md. For set A the build stops at the first of 100 circuits
or 600 failed proposals; for set B the infected quota is `round(f * 100)` capped by what the pool
supplies, and the clean variants fill the rest of the 100 (their count is capped by section 4).

## 3. Trojans, multi-Trojan rules and payload mix

Triggers.
- Seeker-Comb: AND of k rare-valued nets, k grown until the joint activation probability falls in a
  band drawn from p < 1e-2, 1e-3, 1e-4 (the round 3 construction), nets drawn at random from the
  base's rare-net candidates (not the SCOAP-hardest first: agent default 1), p measured on an
  independent sample (exact when the base has at most 20 inputs).
- Seeker-Seq: latch counter (time bomb) or FSM pattern (round 4), width / length drawn so that
  P(trigger within 1024 cycles) lies in a band drawn from fast / mid / slow, nets drawn at random.

Payloads. Set A: `p-dos-stuck` on a primary output (an output read inside the design gets its
isolation buffer first, so the payload cannot feed back). Set B draws per Trojan from:

| payload | netlist realisation | comb | seq |
|---|---|---|---|
| `p-dos-stuck` | victim output forced to its minority value | yes | yes |
| `p-err-hi` | flip of a victim output from the upper half of the output list | yes | yes |
| `p-err-lo` | flip of a victim output from the lower half of the output list | yes | yes |
| `p-energy` | toggle ring of `round(g * gates)` bits (g in 0.5 %..5 %, at least 2), enabled by the trigger | no (no clock) | yes |
| `p-slowdown` | buffer chain on a critical or near-critical net, depth `slack + 1 .. slack + 4` levels, always on | yes | yes |

The netlist has no output words, so "top / bottom bit" is by position in the `.outputs` list
(agent default 2). `p-slowdown` is always on (spec section 2: no activation gate), so its
"trigger" is absent and its rareness entry is `always-on`. A slowdown whose victim is not on a
path within its chain depth of the critical path does not raise the circuit depth and is not
drawn.

Multi-Trojan circuit (set B, 2..3 Trojans):
- trigger net sets pairwise disjoint; victims pairwise different; a slowdown victim is no other
  Trojan's trigger net or victim;
- every trigger and every payload carries its own net names (`__htl_*_<j>`), scrubbed at release;
- each Trojan fires on its own witness: an input sequence on which that Trojan's trigger is high
  and its payload shows (victim differs from the clean value), replayed on the finished circuit in
  Odin III's simulator. Trojans of one circuit have separate witnesses; the other Trojans of the
  circuit may or may not fire on it;
- equivalent to the golden when **all** triggers are forced inactive (ABC cec / dsec); a circuit
  with only always-on Trojans is checked as built.

Witness for the payloads without a functional difference: `p-energy`: toggle count of the ring
nets after the trigger rose (Odin III toggle counters) exceeds that of the golden-driven run;
`p-slowdown`: logic depth of the circuit (levels of `.names`) is larger than the golden's, and the
function is equal (cec).

## 4. Redesign (Peter, 2026-11-01): three obfuscated sets per golden, no provenance (rc4)

rc3 leaked its labels (clean variants had Odin III neutral edits the infected circuits lacked;
ABC removed them so every restructured clean variant equalled the restructured golden), and the
first rc4 attempt (per-circuit ABC rewrite, Odin III writer, 19 forms) still carried Odin III
file style and the Trojan footprint in the forms. Peter's redesign replaces sets A / B and the 19
forms. His words: "We obfuscated the non golden circuits by running abc scripts for different
scripting and reordering the blif ports and ordering to hide the obfuscated designs. This odiniii
version can also have lut mappings k4 and k6. So I think n=100 but now one for k=4 k=6 library and,
or, not with different sets of hts which makes the total from the golden 300. make sure it's random
how many have trojans, the range I gave previously, possibility of more than 1 Trojan (max 3),
change the abc scripting for logic optimization. And make sure there's no provenance."

Per golden (the base, unmodified apart from a canonical `.model` line and layout):

- **Three sets of 100 circuits**: set K4 (Odin III `abc --lut 4`), set K6 (`abc --lut 6`), set G
  (`abc --gates andornot`, the library `lemanruss/data/andornot.o3lib`: AND2, OR2, INV, BUF, TIE0,
  TIE1, DFFP). 300 non-golden circuits and the golden: 301 per base.
- **Infected count per set**: `n_inf ~ Uniform{10..70}` drawn per set and base, seeded (answer key
  only). The other `100 - n_inf` are clean.
- **Infected circuit**: 1..3 Trojans (P = 0.5, 0.3, 0.2), payloads drawn from stuck output
  (`p-dos-stuck`), flip of an upper-half output (`p-err-hi`), flip of a lower-half output
  (`p-err-lo`); triggers as in section 3 (comb rare AND; seq counter / FSM pattern); each set has
  its own Trojan draws (own planning context and seed). `p-energy` and `p-slowdown` are dropped:
  a toggle ring with no observer and a buffer chain are removed by any logic optimisation, so they
  would not survive the obfuscation (their witness would be a property of the pre-obfuscation
  circuit only).
- **Pipeline for every non-golden circuit, clean or infected, one process**: (1) infected only:
  insert the Trojans into the golden with the Odin III edit API (`pre` circuit; rareness measured,
  witnesses found, replayed in Odin III, forced-off equivalence proven on `pre`, exactly as rc3);
  (2) its own random ABC logic-optimisation script (`strash`, 1..8 operations drawn from balance /
  rewrite / refactor / resub / dc2 / dch with their -z -l -K -N variants, optionally `ifraig`,
  `mfs2` after the LUT mapping), one distribution for every label and every set; (3) the set's
  mapping, run by Odin III (`read_blif; abc --script F --lut K|--gates andornot; write_blif`);
  (4) a post-pass on the text: `.model top`, `.inputs` and `.outputs` shuffled, the `.names` /
  `.latch` blocks shuffled, every internal net renamed to `n<index>` with indices drawn without
  replacement from `1 .. 4 * nets`, no comment, no attribute; port and clock names stay (they are
  the interface).
- **Checks per finished circuit**: clean: ABC cec / dsec against the golden. Infected: cec /
  dsec against `pre` (the obfuscation preserved the function; `pre` with its triggers forced
  inactive equals the golden, step 1), and a fire check on the finished circuit: the stored
  witness replayed in Odin III, golden against finished circuit, shows the payload (victim equals
  the stuck value / differs from the golden). A proposal whose Trojan the optimisation removed
  fails the fire check and is redrawn. `pre` is kept in `answer_key/pre/<id>.blif.gz` so verify
  re-proves the same chain from the files.
- **Distinctness**: no two released files identical, none identical ignoring `.model` and comments,
  and none with the same structural signature (names- and order-independent hash) inside a base and
  mapping; the proposal is redrawn. A base that cannot supply 100 distinct circuits in a set has
  fewer, listed, never padded (small bases have few distinct structures after optimisation).
- **No provenance**: no Odin III edit event, `.attr`, `.cname`, comment, `$` name or inserter
  token, one `.model` name (`top`) for all circuits including the golden, file names and manifest
  without base or design names, ids opaque and shuffled. The golden is not hidden (the detector
  needs the reference); which circuits are infected, the sets, f, Trojans, scripts and `pre`
  circuits are in `answer_key/` only.
- **Forms**: the 19 ABC restructured forms are dropped (the random scripts and the three mappings
  take their place); set A (100 DoS circuits) is dropped.

What a detector can and cannot learn. Clean and infected circuits go through one pipeline whose
random choices (script, mapping, shuffle, names) do not look at the label, so style (cover shapes,
file layout, names, order) carries no label. What differs is the Trojan's logic that survives the
optimisation: its trigger cone and its payload gate. Selection effects that remain: a proposal
whose Trojan the script removed is redrawn (infected circuits are slightly biased towards scripts
that keep rare logic), and a golden's structure after a given script is the same for clean
circuits of the same script and mapping (they differ in names and order only), which the
structural-signature check prevents from being released twice.

## 5. Ids, answer key and what the detector sees

Ids are `sc` / `ss` + a number of at least four digits, assigned to the 201 circuits of a base in a
seeded random order (so the id order says nothing about golden / set A / set B / infected). The
manifest lists, per circuit, id, base and file; per base it lists the golden id (the detector needs
the reference) and nothing else. Set membership, f, Trojan lists, rareness, witnesses, edit events and
failures are in `answer_key/` (`sets.json`, `trojans.json`, `witnesses.json`, ...). No label, set
name, f or Trojan word appears in a circuit, a file name, a directory name or the manifest; this is
the leak check of `lemanruss verify`.

## 6. Build order (smallest first) and pipeline

1. bitsim: level-latch fix first (section 9).
2. Seeker-Comb, bases in ascending gate count (7 gates .. 8408), then Seeker-Seq in ascending gate
   count. One process per base in a pool (jobs <= 6, memory <= 10 GB per process).
3. Per base: plan (candidates, drawn Trojans, quotas) -> insert each circuit with the Odin III edit
   API (`recipes` over `edit_netlist`, `trig` / prefix parameters added) -> measure rareness of each
   Trojan on the finished circuit with an independent seed -> witness from the same run, replayed
   in Odin III (clean golden vs finished circuit) -> cec / dsec with all triggers forced inactive.
4. Restructure every circuit with the 18 ABC scripts, each result proven equivalent to its source.
5. Release `seeker-{comb,seq}-v2.0-rc3`: `lemanruss release` (scrub, gzip, manifest, SHA256SUMS,
   datasheet) and `lemanruss verify` (integrity, separation, leak, rareness re-measure, witness
   replay and cec re-run from the files on disk).
6. docs/results-round8.md, F: archive with its own SHA256SUMS, PR.

## 7. Size, wall time and disk estimate (before building)

Measured on this machine (12 cores, 6 jobs): ABC script + conversion + cec / dsec per restructured
circuit: s27 0.1 s, s953 0.2 s, s5378 0.4 s, s298 0.5-0.9 s, b11 1.4 s, b12 2.5-3.4 s, sha 5.5 s,
b14 5-10 s, b15 17-28 s (about 0.1 s + 0.5 ms per gate; 0.7 ms above 15000 gates). Per base the
restructuring is 201 * 18 = 3618 such runs.

| family | bases | circuits (identity) | circuits (19 forms) | restructure CPU-h | wall at 6 jobs |
|---|---|---|---|---|---|
| Seeker-Comb | 31 (7 .. 8408 gates) | at most 6231 | at most 118,389 | 22 | 3.7 h |
| Seeker-Seq, all 50 bases | 50 (27 .. 638552 gates) | at most 10,050 | 190,950 | 1090 | 182 h |
| Seeker-Seq, built (<= 12000 gates) | 36 | at most 7236 | 137,484 | 28 | 4.6 h |

Build (insert + measure + witness + cec) adds roughly the cost of 2 simulations of the infected
circuit per circuit (1 for the rareness, 1 replay in Odin III): comb under 1 s per circuit, seq
0.3 ms per gate per cycle * 1024 cycles, so about 6 CPU-h for the 36 sequential bases. `verify`
repeats the cec runs (about the same CPU as the restructuring) and the witness replays.

**Scope decision (agent default 4).** Seeker-Seq is built for the 36 bases of at most 12000 gates;
the 14 larger bases (b05, b14, b15, b17 to b22, diffeq1, diffeq2, mkPktMerge, mkSMAdapter4B,
boundtop) would cost about 1060 CPU-h of restructuring for 3618 runs each (b19 alone: ABC times out
at 300 s on every script) and are listed in the results as not built at n = 200, with the estimate
above. ch_intrinsics and boundtop stay out as in rc2 (equiv-check refuses level-sensitive latches).
The rc2 release of those bases stays valid at its old n.

Disk (guard: `df --output=avail -BG <work disk>` >= 20G, now 58 G): identity circuits as BLIF text in
`circuits/` (Comb: 201 * 31 * about 40 KB = 250 MB; Seq: 201 * 36 * about 60 KB = 430 MB), the 18
forms gzip (Comb: 118k * about 12 KB = 1.4 GB; Seq: 137k * about 15 KB = 2 GB), edit-event files
(about 3 GB uncompressed for Seq, 1 GB for Comb; written for infected identity circuits only), the
release (a second gzip copy, 1.5 + 2.5 GB). Peak about 10 GB for both families together; each
family is archived to F: and its scratch directories are overwritten, not deleted. If the guard
trips the run pauses at the end of the current base, archives the finished part and reports.

## 8. Rareness per Trojan

As rounds 4-6: Comb p, 95 % Wilson interval, band reached; Seq P(fire <= N) for N = 16, 64, 256,
1024 with intervals, band reached; SCOAP CC / SC of the trigger nets and CO / SO of the victim are
recorded as in round 3. One record per Trojan (a multi-Trojan circuit has one record per
Trojan). Always-on payloads are recorded as `always-on`. The pooled tables of the results report
the distribution over Trojans, per family and set.

## 9. bitsim level-sensitive latches (fix first)

`.latch D Q ah EN` / `al EN` are transparent latches, not flip-flops (Odin III #317 finding: Odin III
is right, `ch_intrinsics` simulates 2922/0 against iverilog). `bitsim` treated every `.latch` as an
edge flip-flop and forced the enable net to 0 as a clock. Fix: level latches are kept apart
(`Compiled.level`: Q -> (enable, active-high)); their enable nets are data nets, not clocks; a
cycle settles by re-evaluating the blocks until no level latch changes (at most 16 passes, bounded
for loops through latches), and the next state of a level latch is its settled Q. A test with a
hand-written BLIF covers hold, transparency and an active-low latch, and (when Odin III is
present) compares the cycle trace against Odin III's simulator.

## 10. Agent defaults (round 8)

1. Trigger nets are drawn at random from the rare-net candidates (round 3 took the SCOAP-hardest
   first); the SCOAP values of the drawn nets are still recorded.
2. Output "top / bottom bit" of the err payloads is the upper / lower half of the `.outputs`
   order, the flat netlist having no words.
3. (rc3, superseded by section 4) clean variants were Odin III edit-API neutral rewrites.
4. Seeker-Seq is built for bases of at most 12000 gates (section 7). The large bases are not
   built at n = 200.
5. Set membership is in the answer key only; the manifest names the golden of each base.
6. f is drawn per base with `random.Random(f"{seed}:{base}:f")` uniform in [0.10, 0.70]; the
   Trojan count per infected circuit with P = (0.5, 0.3, 0.2) for 1, 2, 3.
7. Energy ring size g in [0.5 %, 5 %] of the gates, at least 2 bits and at most 64; slowdown chain
   depth `slack + 1 .. slack + 4`.
8. Witness for energy and slowdown is the effect measure (section 3) because there is no
   functional output difference to point at.
9. The release verify re-runs witnesses by replay in Odin III from stored input sequences
   (`witnesses.json` in the answer key) instead of searching again (the search costs minutes on
   sequential bases); the rareness re-measure and every cec are recomputed from the files.
10. Selection sample for a base of at most 20 inputs is exhaustive (2^n vectors); above it 2^20
    random vectors (comb) or 2^15 scan-view vectors plus a 1024-cycle observation pass (seq).
11. ABC 300 s and cec 600 s limits as rounds 4-6; a timeout is `unproven` and listed.
12. Ids are four or more digits (`sc0001` .. `sc118389`); the opaque-id regex of `verify` accepts
    four or more digits.
13. Neutral edits (clean variants) may use output nets when a base has fewer than 6 internal gate
    nets; on the tiny `ve_*` bases Odin III's model does not list some of those nets, so the edit
    fails and that base supplies fewer variants (counted in the results).
14. Seeker-Seq excludes ch_intrinsics and boundtop by hand (equiv-check refuses level latches),
    on top of the 12000-gate cap.
15. Results of the run: docs/results-round8.md. Comb built in 3.5 min and restructured in 1.5 h;
    the measured times are well under the section 7 estimates because most bases are small.
16. rc4 (2026-11-01, Peter's redesign, section 4): 3 sets x 100 per golden (LUT k = 4, LUT k = 6,
    AND/OR/NOT), infected count Uniform{10..70} per set, 1 to 3 Trojans (dos / err-hi / err-lo),
    every non-golden circuit through a random ABC script + mapping + shuffle + fresh names; no
    provenance; the 19 forms and set A are dropped; energy and slowdown payloads are dropped.
17. Trojan plan per set is drawn on the golden (own context and seed per set); the rc3 plan
    (f, nets) is not reused because the set structure changed.

## 11. Verify gates added after the rc3 leaks

`lemanruss verify` of an n = 200 release also runs, from the files on disk (module
`lemanruss/htl/n200gates.py`):

- `f_distinct`: no two released circuits identical after decompression, and none identical
  ignoring the `.model` line and comment lines. rc3: 1208 groups (323 across labels) in Seeker-Comb.
- `g_style`: per form, for each local artefact (double inverter, double buffer, any buffer,
  any inverter, any constant driver, each cube-pattern class of cells with at most 3 inputs),
  a Cochran-Mantel-Haenszel test stratified by base and set on clean (golden left out)
  against infected; flagged when p < 0.01 / m (Bonferroni over the m tests of the release) and the
  stratified share difference exceeds 0.05. Also the AUROC of the best single style feature (the
  fraction of cells of an artefact, per base, pair-weighted); bound 0.60. In the identity form the
  answer key is used only to drop the inserted cells. The existing leak checks (c) stay.
- `h_provenance`: every file has only the directives `.model .inputs .outputs .names .latch .end`,
  no comment line, no token with `$`, `\\`, `@`, `__htl`, `odin` or `yosys`, the same `.model`
  name in every file (also the golden), `.latch` lines in one format, and net names other than
  ports and clocks of one scheme (`n<digits>`).

## 12. rc5: latch init value leak (2026-11-02)

Seeker-Seq rc4 gave the label away through the `.latch` init value. Clean circuits: every latch has
init 2 (ABC writes "unknown" as 2). Infected circuits: the Trojan's own flip-flops, inserted with
`INIT 0` through the Odin III edit API, kept init 0 through ABC and mapping (about a third of the
latches of an infected circuit). "Any latch with init 0" separated the labels with AUROC 1.0 and a
detector reached GNN AUROC 0.98 to 1.00 on it. The rc4 gates did not look at `.latch` fields
(`h_provenance` only required one format). Seeker-Comb has no latches and is not affected.

**Gate (new fields of `g_style`, `h_provenance`; module `n200gates.py`).** `g_style` features
(binary "any" and share per circuit, same CMH test, Bonferroni bound, 5-point minimum difference and
AUROC bound as before):

- `lat_init_<v>`: latches by init value (0, 1, 2, 3);
- `lat_type_<t>`: latch type (re, fe, ah, al, as);
- `lat_clock_main` / `lat_clock_other`: the latch clocks against the circuit's most used clock;
- `lat_dkind_<k>`: what drives D (primary input, another latch, buffer, inverter, constant, other);
- `info lat_selfq`: latches whose D cone through `.names` reads their own Q. Reported, not gated:
  it is the footprint of counters and FSMs and the clean circuit's own state machines have it too;
  it would be gated only if it proved an artefact of the build.

`h_provenance`: a file with more than one `type/clock/init` combination among its latches is a
trace, and one base must have one combination over all its files (golden included).

Other BLIF fields the gates did not cover, now features of `g_style` (per cell of at least one
input; binary "any" and share of cells): `cov0` (off-set cover, output column 0), `dc` (a
don't-care in a cube), `rows_unsorted` (cubes of a cell not in ascending order), `in_unsorted`
(input nets of a cell not in ascending `n<digits>` order). Already covered: buffer, inverter,
double buffer / inverter, constants, cube-pattern classes of cells up to 3 inputs (info), net
name scheme and index range, directives, comments, foreign tokens, `.model`. Not features, by
construction: line layout (one writer renders every file), block, port and net-name order
(shuffled per file), `.inputs` / `.outputs` wrapping (one writer). Result: on rc4 Seq and rc4
Comb none of the four cover fields differs beyond the bound; the only rc4 Seq leaks are the latch
fields. Seeker-Comb rc4 passes the extended gate (no latches; best feature AUROC 0.542).

**Builder.** `edit_netlist.LatchConvention` (edge and init of the circuit's own latches, the most
used `.latch` pattern of the golden; init 3 counts as 2) is passed to `insert`; the Odin III
editor and the text fallback create the Trojan's latches with that edge and `INIT`. The clock is
the circuit's own (first rising-edge latch clock, as before). `obfuscate.render` spells "unknown"
as 2 (the golden of the ITC-99 bases had 3 while ABC writes 2). No Trojan latch can differ from
the circuit's in type, clock or init.

The D-driver field then found two footprints of the recipes themselves, both an inverter in front of
a Trojan latch after ABC: (a) the sticky flag's `f | last` was built twice (flag input and trigger),
ABC shares the node, and the complemented edge to the latch needs an inverter; (b) the pattern
trigger's first stage was `net == value`, a lone inverter when the value is 0. rc5: the trigger is
the flag itself (one cycle after the last stage), and the first stage is the two-input cell
`net == value and not yet fired` (after the flag is set nothing changes). Counter and pattern
triggers are otherwise as before; `tests/test_edit_netlist.py` compares the new structure with the
old one by simulation.

**AUROC bound.** The bound of the best style feature is exceeded only when the AUROC minus 1.645
Hanley-McNeil standard errors is above it. Reason: every share-of-cells feature is diluted by the
Trojan's own cells (cell count alone separates the labels inside a base x set stratum with AUROC
0.85, the latch count with 1.0; both are footprint, not style), and the constant-cell share moved
from 0.596 (rc4) to 0.601 (rc5) against the bound 0.60 with a standard error of 0.006. The rc4
latch leak is at 1.0 with error 0.

**Start state.** Init 2 is "unknown". Every tool of the pipeline reads unknown as 0: `bitsim`
(only `1` is 1), the Odin III simulator (witness replay), ABC `cec`/`dsec` (forced-off and
obfuscation equivalence). The Trojan therefore starts from the same all-zero state as the circuit's
own latches; it depends on no init value that only Trojan latches have. A real device without a
reset starts anywhere, for the golden circuit as for the Trojan; rareness is defined, as in rc4,
as P(fire within N cycles) from the all-zero start with random inputs (N = 16, 64, 256, 1024), so
the rc5 numbers are the rc4 numbers of the same Trojans when the plan is the same (same bases, sets
and plan seeds; see the results report for the comparison).

## 13. rc5/rc6: cut-and-stitch (round 9, 2026-11-02)

Peter, 2026-11-02, verbatim: "except for our previous seeker's dilemma. We cut out what couldn't
be handled by other tools and then reinserted it by making the outputs or the inputs to the part
we can as primary outputs and the outputs as primary inputs. Could we do this for the parts that
get destroyed by ABC?" rc4 dropped `p-energy` and `p-slowdown` (section 4) because any ABC logic
optimisation removes them: the energy ring has no net that reads its state (dead-code elimination)
and the slowdown chain is a run of 1-input identity gates (buffer collapse). Purpose: restore
them, so Seeker-Comb and Seeker-Seq carry Peter's full mixed payload set again (memory
seeker-v2-families). This section does not claim the method below is how Seeker v1 was built;
it is the controller's reading of Peter's words above, applied to rc4's pipeline.

**Method (module `lemanruss/htl/cutstitch.py`).** For each payload a check shows ABC destroys,
and (so no label comes from "this circuit was cut" alone) for a dummy region of the same size
distribution on every circuit that has none: the blocks of the part are removed from the circuit;
the nets crossing the cut become, on the host's own standalone BLIF, extra primary outputs (nets
the host drives into the part, so their logic stays observed) and extra primary inputs (nets the
part drives into the host, so the host run is well-formed); the host goes through its one random
ABC script and the set's mapping, as rc4; each real or dummy part is mapped on its own the same
way, with its own boundary as its primary inputs/outputs, so ABC keeps it and it gets the set's
cell style; the host's mapped blocks and every part's mapped (or, for a part that is not run
through ABC, unmapped) blocks are put back together on the boundary net names (unchanged since
neither run renames a declared primary input or output), and the merged circuit goes through
`obfuscate.finalize` exactly once, same as every other circuit, so the boundary nets are shuffled
and renamed like any other internal net and carry no trace of where the cut was.

**Findings, tested on the smoke bases before the full rebuild (each was caught by running the
module and the gates, not assumed).**
1. Cut-and-stitch defeats dead-code elimination: the energy ring, cut out with its own bits as
   extra primary outputs of its own standalone run (nothing else reads them, so without this they
   would be dead code even inside the cut's own run), keeps its latches and XOR feedback through
   a full random ABC script and mapping; the stitched circuit is `cec`-equivalent to its
   pre-obfuscation form.
2. It does **not** defeat identity-buffer collapse. ABC's AIG (`strash`) has no node for
   `a = b`, so a run of 1-input buffers (the rc3 slowdown chain) collapses to a wire whether or
   not its ends are primary outputs. Carrying the chain through unmapped keeps its depth but is a
   label: the `g_style` gate found `buf` / `dbl_buf` at AUROC 0.74 on the smoke Comb build.
3. Agent default (the controller may override): the slowdown payload is an absorption stage.
   The victim is `tmp | (tmp & s_1) | ... | (tmp & s_m)` (= `tmp`, m = 1..4). The ANDs stay in
   the host (inputs `tmp` and primary inputs / latch outputs the golden itself reads, outside the
   victim's own cone so no term is constant); only the OR is cut. Its inputs are independent
   nets, so ABC cannot fold it, and no buffer appears. The payload adds the AND level and the OR
   level on the victim's path: a real depth increase, reported (not gated), always on.
4. A latch with a bare net on the other side of the cut gets a buffer from the gate mapping
   (smoke: 28 of 30 cut s27 circuits, 0 of 30 plain; rc5 gate `lat_dkind_buf`). The cut region is
   therefore closed over latches (`cutstitch._close_latches`): a latch in the region takes the
   block driving its D, a latch outside whose D or Q touches the region joins it, and a latch's
   D net that is also a boundary net pulls its other readers in. A cut may then be larger than
   its drawn size; the recorded size is the actual block count.
5. The two pieces each name their internal ABC nets `n1, n2, ...`; they are given private
   prefixes before stitching (gate mapping otherwise drives one net from two pieces).
6. `obfuscate.finalize` now writes every cell with its input nets ascending and its cubes
   ascending (one layout for all circuits, function unchanged): the gate `in_unsorted` showed a
   5.9-point difference once pieces were stitched.

**Checks.** Every circuit still proves `cec`-equivalent to its pre-obfuscation form (`pre/`, or
the golden for a clean/dummy-only circuit), exactly as rc4; cut-and-stitch changes how the
obfuscated text is produced, not what it must equal. Energy and slowdown get their own fire
check (`n200check.odin_fire`). `p-energy`: the first design compared whole-circuit toggle counts
of the finished circuit with the golden's and failed on its own premise (a mapped circuit has
fewer signals than the golden, so the infected total was lower in 14 of 14 smoke cases). The
witness now reads the ring itself: `cut_and_stitch` returns where each ring bit went through
`finalize`'s renaming (`answer_key/cuts.json`, field `rings`), and the fire check replays the
witness input sequence in Odin III and requires the ring nets to toggle at least once; the
detail also gives the ring's toggles under an all-zero input sequence of the same length (the
idle measure; the ring is `d = trigger xor q`, so it toggles only while the trigger is high).
`p-slowdown` has no trigger and no functional difference (spec section 2/3): it is recorded `always-on`, no
witness, and its claim is logic depth, reported (not gated) per base/set as the finished
circuit's overall `.names` depth against a reference obfuscation of the same golden under the
same set (one random script/mapping, cached per base and set, section 6's build order picking it
up once rather than once per slowdown circuit).

**Report.** `docs/results-round8.md` section "cut-and-stitch" gives, per family: the cut-size
distribution (block count) of real cuts (energy, slowdown) against dummy cuts, clean vs infected,
so the two populations can be compared directly; the energy ring toggles under the witness against the idle run; the slowdown depth delta against the per-(base, set) reference
obfuscation.

**Rebuild.** Seeker-Comb rc5 and Seeker-Seq rc6: same bases, sets and plan seeds as rc4/rc5 where
the pipeline allows it (the mix and the cut step are new, so circuit-for-circuit identity with
rc4/rc5 is not expected); rc4 (Comb) and rc5 (Seq) release directories are kept (the detector lane
reads them) and marked superseded in the README with the reason (payloads restored).
