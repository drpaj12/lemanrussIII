# Round 7 results: Seeker-Proc pilot (2026-11-01)

Branch feat/htl-round7-proc (from main a69bd3e), Odin III main 0d3d735a (library
`build/rel-main/libodin3.so`). Output under work/htl-out/r7 (not committed); release
work/htl-out/r7/seeker-proc-v2.0-pilot (index files in `releases/seeker-proc-v2.0-pilot`).
Spec section 12.

Headline: **3 processor Trojans, 2 bases, all fire on their own witness, all silent on every
shipped program checked, all three agree across iverilog / Odin III RTL sim_tb / Odin III
netlist sim_tb.** Equivalence (trigger forced inactive) is **unproven** on both bases (not a
pass, not a fail -- ABC `dsec` timed out on the RAM-expanded netlist). Pilot only: not v1's
taxonomy or numbers.

## 1. Bases

| base | source | top | commit/version pinned |
|---|---|---|---|
| mcu | `external/Arduino-on-RISC-V`, `quartus_project_revert_timer` | `single_cycle_BRAM_top` | as checked out (Odin III #313's own test fixture) |
| darkriscv | `external/darkriscv` | `darksocv` | `9555119` (`tests/darkriscv/run.sh`'s own pin) |

## 2. Trojans, triggers, payloads

Insertion found by reading the RTL (spec section 12.2): mcu's trigger compares `instruction`
(the fetched word); payload rewires `fetch_issue`'s `next_PC_select` input through a new mux
forcing `2'b01`, `fetch_issue.v`'s own documented stall encoding. darkriscv's trigger compares
`IDATA` qualified by `IDACK`; payload ORs into the core's own synchronous self-reset register
`XRES` (`p-dos-reset`, not `p-dos-stuck` on `HLT`: `HLT` only holds off the *next* fetch, so in
this pipelined core the instruction right after the magic word had already been fetched and
still completed -- measured with a witness `sw` one slot later still writing its value under
iverilog before the fix).

| trojan id | base | trigger | payload | magic word(s) |
|---|---|---|---|---|
| proc-mcu-magicword-stall | mcu | t-input-pattern | p-dos-stuck | <kept with the answer key> |
| proc-mcu-magicseq3-stall | mcu | t-seq-pattern (k=3) | p-dos-stuck | <kept with the answer key> |
| proc-dark-magicword-reset | darkriscv | t-input-pattern | p-dos-reset | <kept with the answer key> |

## 3. Witness and verification

A short RV32I program per base (`lemanruss.htl.rv32i`: hand-encoded ADDI/JAL/LUI/SW, cited
against the RISC-V Unprivileged ISA spec, unit-tested against known encodings). mcu's witness
is observed on `PC` (the infected design's PC lands one instruction short of the clean design's
self-loop address); darkriscv's writes a marker (`0x2a`) to `OPORT` (darklibc's io base
`0x40000000` + offset `0x18`, confirmed against the bus decode `XADDR[31:30]==1` selects
`darkio` in `darksocv.v`) after the magic word, visible directly in `dark_tb.v`'s trace (never
written when infected).

| trojan id | witness fires | RTL = iverilog (clean) | RTL = iverilog (infected) | RTL = netlist (infected) |
|---|---|---|---|---|
| proc-mcu-magicword-stall | yes | yes | yes | yes |
| proc-mcu-magicseq3-stall | yes | yes | yes | yes |
| proc-dark-magicword-reset | yes | yes | yes | yes |

The mcu "RTL = iverilog" columns use `lemanruss.htl.proc_run.traces_agree` (iverilog's BRAM
starts at `x`, Odin III's at `0`, reset window only -- `tests/mcu/compare.py`'s own masking
rule); the other comparisons are exact.

### Failures and fix rounds found while building this

Three bugs, found and fixed, not papered over (listed so the numbers above are checked, not
assumed):

1. **mcu's magic-sequence FSM never fired at first** (`witness_fires: false`). mcu's
   `fetch_receive.v` inserts a one-cycle NOP bubble between every two real fetches (`assign
   instruction = flush ? NOP : i_mem_data`); a first FSM design that advanced on "instruction
   changed since last cycle" read each bubble's NOP as the wrong next word and reset the
   sequence before the real next word arrived. Fixed by gating the FSM's advance on the core's
   own `flush_fetch_receive` wire (negated), found by instrumenting a live iverilog run with
   `$monitor`. Confirmed with a 30-cycle trace: infected PC reaches the self-loop address one
   cycle later than clean (cycle 19 vs 18).
2. **darkriscv's first payload choice (`p-dos-stuck` on `HLT`) did not actually stop anything**:
   `HLT` only holds off the pipeline's *next* instruction fetch; the instruction already in
   flight when the magic word is seen still completes. Measured with a witness `sw` one slot
   after the magic word still writing `OPORT` under iverilog. Switched to `p-dos-reset`
   (`XRES <= RES || __htl_trigger`), confirmed to work.
3. **mcu's shared Odin III checkout moved under this round**: `tests/mcu/prepare.sh` (in
   `~/odin3-ws/odin3`, read by this repo, shared with other concurrent sessions on this
   workspace) dropped its own derived-clock patch for `8bit_TC.v` mid-round, with a comment that
   Odin III's `sim_tb` takes derived clocks "since 2026-11-01" -- a fix that landed on main after
   the commit this repo is pinned to (0d3d735a). A previously green witness run started failing
   ("the clock of `$_DFF_P_` node ... is not a primary input") once the shared file changed.
   `lemanruss.htl.proc_run.prepare_mcu` now re-applies the patch itself (idempotent), decoupling
   this round from the moving target.

## 4. Stealth (P(fire) over the shipped programs; brief item 2(i))

A Trojan that fires on a shipped program is dropped and listed. None was.

| trojan id | blink | blink_interrupt | blink_function_call | interrupt | darkriscv prebuilt firmware | dropped |
|---|---|---|---|---|---|---|
| proc-mcu-magicword-stall | silent | silent | silent | silent | n/a | none |
| proc-mcu-magicseq3-stall | silent | silent | silent | silent | n/a | none |
| proc-dark-magicword-reset | n/a | n/a | n/a | n/a | silent | none |

## 5. Rareness (brief item 2)

| trojan id | magic bits | p(match), exact | SCOAP CC0 | SCOAP CC1 | SCOAP CO | trigger net |
|---|---|---|---|---|---|---|
| proc-mcu-magicword-stall | 32 | 2^-32 = 2.33e-10 | 9 | 128 | 3 | `single_cycle_core...`:`$n874` |
| proc-mcu-magicseq3-stall | 96 | 2^-96 = 1.26e-29 | 6 | 137 | 3 | `single_cycle_core...`:`$n1065` |
| proc-dark-magicword-reset | 32 | 2^-32 = 2.33e-10 | 2 | 130 | 2 | `darkriscv`:`$n16067` |

(ii) is exact by construction (a uniformly random 32-bit fetched word matches with probability
`2**-32`; a k-word sequence `2**-(32k)`). (iii) is Odin III `scoap` (schema `odin3-scoap` v2) on
the trigger net, read back from the net that write_blif tags `.cname __htl_trigger.<op>`, taking
the last such tag (the top-level operation) and its enclosing `.model` (BLIF net names are
model-local: mcu's top module happened to also hold an unrelated net of the same auto-generated
name inside the `single_cycle_core` instance; the caught false match is why `find_trigger_net`
tracks the owning module, not just the net name). CC1 >> CC0 in all three, consistent with a
rare-at-this-value AND condition; CO is small (3, 3, 2), consistent with the trigger feeding the
payload mux/OR directly, few logic levels from a primary output. (iv) (P(fire within N cycles),
a counter-trigger measure) is not defined for these two trigger kinds and is not reported.

## 6. Equivalence (trigger forced inactive; brief item 3)

Both bases `lower` their RAM/BRAM arrays to tens of thousands of per-bit latches with no target
architecture in this round (no `read_arch`, per the brief's "no VPR"): mcu's netlist carries
102558 latches (clean and infected-forced-off alike -- the Trojan's own handful of gates do not
change this); darkriscv's infected-forced-off netlist carries 66507. (darkriscv's *clean*
netlist measured 3019 in one run and is not reconciled with the 66507 figure above within this
round's time budget -- a build-configuration difference between the two runs, not re-traced; the
`unproven` equivalence verdict below does not depend on which of the two is right.)
`tools/equiv-check` ABC `dsec` is **unproven** on both: mcu timed out at the 300 s wrapper used
here (exit 124), darkriscv `unproven: ABC dsec timed out after 600 seconds` (ABC's own internal
limit, exit 4). Measured once per base (the magic-word Trojan); the magic-sequence Trojan's
extra FSM is a handful of gates on top of the same core and is not expected to change this
outcome, so it was not separately measured (stated, not assumed pass). Neither unproven result
is reported as a pass (spec section 4(c): "unproven is reported as such, never as pass").

## 7. Release: Seeker-Proc v2.0-pilot

Packaged by `lemanruss.htl.proc_release.package_proc_release` (verbs `proc-release`/
`proc-verify`, not the family `release`/`verify`: see spec section 12.5 for why). `circuits/`
holds the one patched RTL file plus the witness image per Trojan; `answer_key/` holds
`labels.json` (trigger/payload kind, magic words), `renames.json` (the `__htl_*` -> `_insN`
scrub map) and `rareness.json` (section 5's table, machine form). `verify_proc_release`:
integrity (SHA256SUMS) PASS, leak-free (no `htl`/`trojan`/`odin3_edit` in any detector-visible
file) PASS, every circuit labelled PASS.

Backed up to `<archive>/2026-11-01/seeker-proc-v2.0-pilot.tar.xz` (17 KB; one
archive, no circuits/answer_key split needed at this size), SHA256SUMS checked
(`35193688c91a9904f654c1c83dd529927ed57e002b2ce19ecbcfcc82defc4b69`), entry count 24 = source (18
files + 6 dirs), `tar -d` clean, README entry added. Index files (`manifest.json`, `SHA256SUMS`,
`DATASHEET.md`) committed under `releases/seeker-proc-v2.0-pilot/`; `circuits/`/`answer_key/`
stay out of git (as the other release index entries do).

## 8. Deferred this round (agent defaults, spec section 12)

- Netlist-level insertion and error-insertion payloads (`p-err-hi`/`p-err-lo`): not attempted
  (time-boxed; recorded as a deferred axis, not an Odin III gap).
- Equivalence checked once per base, not once per Trojan (section 6).
- The label scrub is a plain `_insN` counter, not styled to the base's own naming (unlike the
  family release's `[N]`/`$nN` scrub): simpler is enough for a one-file preliminary release.
- darkriscv's clean-vs-infected-forced-off latch count discrepancy (section 6) is not retraced
  this round: recorded as found, not silently dropped.

## 9. Agent defaults (round 7, numbered 44-47; spec section 12 carries the full text)

44. darkriscv's payload is `p-dos-reset` on `XRES`, not `p-dos-stuck` on `HLT` (section 2 item
    2 above).
45. Error-insertion payloads and netlist-level insertion are out of this pilot's scope.
46. `find_trigger_net` locates the trigger net by its `.cname __htl_trigger.*` tag and its
    enclosing `.model`, not by net name alone (BLIF net names are model-local).
47. The label scrub is a plain `_insN` counter (section 8).

Not an agent default, a found-and-fixed bug class: the mcu sequence-FSM advance signal and the
mcu derived-clock patch (section 3, items 1 and 3) -- both measured wrong first, then fixed and
re-verified, not assumed correct from the design alone.

## 10. Fix round: seeker-proc-v2.0-pilot2 (2026-11-01, PR #9 controller finding)

The controller found seeker-proc-v2.0-pilot (section 7) leaked circuit/trojan identity even
though `verify_proc_release` said PASS: directory names and manifest keys were the trojan id
(`circuits/proc-mcu-magicword-stall/`), no clean circuit was released at all (every circuit was
infected, so "a circuit exists" already answers the Seeker formulation), and the detector-visible
file was the patched upstream RTL itself (a diff against the public upstream reveals the Trojan
line by line). Fix brief: `work/controller-scripts/briefs/lemanruss-proc-pilot-fix.md`.

**Form change.** `lemanruss.htl.proc_release` pilot2 packaging (`ProcCircuitSpec`,
`package_proc_pilot2`): the detector-visible form is now the lowered netlist, both bases' own
build flow plus `--gates-as-names` (`read_verilog <files>; proc; opt; lower; write_blif
--gates-as-names`) -- round 7's plain `write_blif` keeps library primitives as `.subckt`, which
both ABC's own reader and `bitsim.compile_model` refuse (`Cannot find the model for subcircuit
$_AND_`/`ValueError: bitsim: combinational loop or undriven net`); `--gates-as-names` writes
every gate `.names`, which both tools read. One clean and one infected circuit per trojan (6
total), opaque ids (`pp0001`..`pp0006`), scrubbed with `lemanruss.htl.release.scrub_group` (the
family's own mechanism: styled to the circuit's own clean twin, not pilot1's plain `_insN`
counter). Confirmed: `__htl_trigger` reached the released artifact as a `.cname` tag even in
round 7's content-leak-scanned netlist (`grep -c __htl proc-mcu-magicword-stall-infected/
w.nl.blif` = 66) -- `write_blif` always tags the cell it builds for a named wire, independent of
the dialect; the scrub removes these too (`__htl_\S*` matches the dotted `.cname` form). The
patched RTL and the witness program image moved to `answer_key/patches/` and
`answer_key/witness/` (provenance only); `circuits/` never holds them.

**Restructuring (brief item (c), "rounds 4-6").** Attempted per base (`attempt_restructure`,
the cheapest script, `strash`, as a representative). Both bases fail at ABC's own `read_blif`,
before any restructuring-specific command runs, so the same outcome applies to every one of the
18 forms without repeating an identical failure 18 times (the brief's "stated subset" when wall
time does not allow all 18):

| base | role | verdict | wall time | reason |
|---|---|---|---|---|
| darkriscv | clean | abc-failed | 36s | `Network "darksocv" contains combinational loop!` (a box encountered twice on a path to a CO) |
| darkriscv | infected | abc-failed | 50s | same |
| mcu (magicword) | clean | abc-failed | 290s | `Cannot find the model for subcircuit single_cycle_core$RESET_PC` |
| mcu (magicword) | infected | abc-failed | 532s | same |
| mcu (magicseq3) | clean | abc-failed | 531s | same |
| mcu (magicseq3) | infected | abc-failed | 532s | same |

darkriscv's finding is consistent with round 6's Odin III gap note #2 (a sequential loop that
passes through a latch; `bitsim` also refuses the same netlist with "combinational loop or
undriven net", an independent implementation finding the same thing). mcu's finding is a BLIF
reader gap in ABC against Odin III's own naming: Odin III's `lower` keeps the design
hierarchical (`single_cycle_core$RESET_PC=32'b0...0`, `dual_port_BRAM$h4141f8f055525db2`, one
`.model` per specialized submodule -- 28 in mcu's case), and adding Odin III's own `flatten`
before `lower` (`proc; opt; flatten; opt; lower`) did not collapse them (still 28 `.model`
blocks; not pursued further here, out of scope for a release-format fix round). ABC's own
`read_blif` resolves a `.subckt` box by looking up its model name, and truncates the name a few
characters short at the `$`/`='`/apostrophe characters of Odin III's own name, so it never finds
the model it is looking for. Neither finding is an Odin III bug and neither is worked around
here (CLAUDE.md: never edit the Odin III repo); recorded for the controller. No restructured
form is released this round: `circuits/` holds the identity (unrestructured) lowered netlist
only, clean and infected, per trojan.

**Verify (brief item (d)).** `verify_proc_release` (the pilot1 verb, kept) now also runs
`check_name_vocabulary`: every directory/file name under `circuits/` and every key of
`manifest.json`, scanned case-insensitively against `NAME_VOCAB` (trigger, payload, magic, seq,
word, stall, reset, dos, trojan, htl, infect, clean). Re-run against the pilot1 release still on
disk: **FAIL**, 54 hits (`circuits/proc-mcu-magicword-stall: name contains 'magic'`, ...) --
confirmed the fix catches the exact leak found, and `tests/test_proc_release.py`'s
`test_old_trojan_named_layout_fails` reproduces it as a unit test (content-leak-scanned clean,
name-vocabulary-scanned not: `leak_free` True, `name_vocab_ok` False). A new `verify_proc_pilot2`
checks the pilot2 schema directly: integrity (SHA256SUMS + manifest hash/size), the same
name-vocabulary check, a content leak scan (`LEAK_TOKENS` plus `NAME_VOCAB`, with the family's
native-vs-leak rule -- a token the circuit's own clean twin also holds is native, not a leak),
the pilot1 `_insN` pattern (the controller's finding (2): a pattern that by itself marked a
circuit infected -- a regression guard, since pilot2's own scrub never produces it), and that
every manifest circuit has a label. **PASS** on the released seeker-proc-v2.0-pilot2 directory
(all five sub-checks green).

**Witness check on the released netlists (brief item (e)).** `witness_check_released`:
`read_blif <packaged netlist>; sim_tb --out <tag>.txt <tb-file>` on `circuits/<clean-id>.blif.gz`
and `circuits/<infected-id>.blif.gz` directly (no rebuild from Verilog). All three trojans fire:

| trojan id | clean id | infected id | fires |
|---|---|---|---|
| proc-mcu-magicword-stall | pp0005 | pp0006 | yes |
| proc-mcu-magicseq3-stall | pp0003 | pp0004 | yes |
| proc-dark-magicword-reset | pp0001 | pp0002 | yes |

Confirms the witness property on the artifact actually shipped, not only on the pre-release
build tree. "Silent on shipped programs" is not re-run here: the released netlist's memory holds
only the witness program (Odin III resolves `$readmemh` when the Verilog is first read, baking
the program into the lowered netlist's `.latch` init bits -- a shipped-program check needs a
different build with that program's memory baked in instead); carried forward from round 7's
measurement (section 4) on the same, unchanged, RTL patch -- the Trojan insertion logic itself
did not change this round, only the release form.

**Re-package.** `seeker-proc-v2.0-pilot2`: 6 circuits (3 clean, 3 infected; `pp0001`..`pp0006`),
`verify_proc_pilot2` PASS. Index files (`manifest.json`, `SHA256SUMS`, `DATASHEET.md`) committed
under `releases/seeker-proc-v2.0-pilot2/`; `circuits/`/`answer_key/` stay out of git. Backed up
to `<archive>/2026-11-01/seeker-proc-v2.0-pilot2/` in its own directory with its
own `SHA256SUMS` (the existing top-level `2026-11-01/SHA256SUMS` entry for pilot1 is left as is,
per the brief: never delete on F:). README entry added, saying pilot1 leaked labels and is
superseded.

### 10.1 Agent defaults (round 7 fix, numbered 48-50)

48. The detector-visible form for Seeker-Proc moves from the patched RTL file to the lowered,
    `--gates-as-names` netlist (section 10 above); `proc_release.scrub`/`leak_scan`/
    `verify_proc_release` (pilot1) are kept for compatibility and strengthened in place
    (`check_name_vocabulary`), not replaced, since pilot1's content-level checks were correct as
    far as they went.
49. ABC restructuring of the processor netlists is attempted once per base (the cheapest script)
    rather than all 18 forms independently: both bases fail at `read_blif`, before any
    restructuring-specific command runs, so every form fails identically and re-running 18 times
    would only re-measure the same read-time failure (section 10 above).
50. "Silent on shipped programs" is carried forward from round 7 rather than re-run against the
    released netlist: the released netlist's memory holds only the witness program, baked in at
    build time, so a shipped-program check needs its own build (section 10 above).
