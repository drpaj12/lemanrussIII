# Round 10 results: Seeker-Proc rc1 start (2026-11-03)

Brief `work/controller-scripts/briefs/lemanruss-proc-sd-rc1.md`; spec
`docs/specs/2026-11-03-seeker-proc-rc1.md` (hypotheses H-P1, H-P2; agent defaults; Peter's
2026-11-03 decisions: 1-3 payloads/circuit, RAM black-box confirmed). This round is a start, not
a finish: the full N=100 x 3 forms = 300-circuit release, its detector run, archive and PR are
**not** in this round (section 5). What is done, and what each finding is evidence of, below.

## 1. Base survey (spec section 4)

Read, not guessed, against `external/`:

| base | status | evidence |
|---|---|---|
| mcu | builds | pilot3 (`docs/results-round9.md` section 5): RTL = iverilog = Odin III RTL = Odin III netlist, 4/4 shipped programs silent, FF 132446 = 132446 |
| darkriscv | builds | pilot3: same checks, FF 67638 = 67638 |
| tinyriscv | fails | `odin3 -p read_verilog` on `tinyriscv_soc_top.v`: `error: hierarchical reference 'u_tinyriscv.u_regs.regs' is not supported`, `ODIN3_ERR_PARSE` (debug module's register-file probe; open question, spec section 7) |
| picorv32 | builds, default config only | `odin3 -p "read_verilog;proc;opt;stats"` elaborates the top with `ENABLE_MUL`/`ENABLE_DIV`/`ENABLE_IRQ` off (635 cells); with them on, `picorv32_pcpi_mul` is unreadable (Q-L12's finding stands) |

This round's Proc base set stays mcu + darkriscv (both proven end to end); picorv32 (reduced
config) is a candidate third base not yet run through the Proc pipeline (no patch point found
for it yet, spec section 4).

## 2. `out_of_range`: the fix for round 9's "proc ones are easy to find" (spec section 6)

Peter 2026-11-03: "So why in the Lehman russ confusion matrix are the proc ones easy to find?"
Round 9's answer: `ffcount` flagged all four pilot3 circuits, clean too, because RAM lowered to
per-bit latches (67k-132k FFs) sits far above the Comb/Seq training range (hundreds to low
thousands). Fix: `lemanruss/detect/ffrange.py` (pure, tested without a built release) + wiring
into `lemanruss/detect/proc.py`'s `run_proc`: a circuit's flag is `out_of_range` when its FF
count falls outside `[min, max]` of the detector's own training-fold FF counts, computed from
the training records `run_proc` already builds. `out_of_range` is a third flag value, never
counted as a true/false flag. `tests/test_detect_ffrange.py` (7 tests, including the round 9
scenario itself: training FFs in the hundreds, Proc pilot3's 67638/132446 FF pairs both
`out_of_range`). Not yet wired into the external submission scorer (`lemanruss/score/scorer.py`):
that scorer's "flag" is the submitter's own claim, not a score-plus-threshold the detector
computes against its own training fold, so `out_of_range` as specified does not apply there the
same way; left for the controller to confirm before any submission-format change.

## 3. Multi-Trojan (1-3) insertion (Peter 2026-11-03, section 2 of the spec)

`lemanruss/htl/proc_insert.py`: `insert_mcu_multitrojan`/`insert_dark_multitrojan`, 1 to 3
independent magic-word Trojans per circuit, each its own comparator wire `__htl_trigger_<j>`
OR'd into the one payload trigger already proven in pilot3 (`p-dos-stuck` on mcu,
`p-dos-reset` on darkriscv). Purely combinational OR: no added flip-flop by construction.
`patch_mcu_multicore`/`patch_dark_multicore` wire this into the existing build pipeline
(`lemanruss/htl/proc_run.py`). 17 tests in `tests/test_proc_insert.py` (10 new), including a real
Odin III `--parse-only` re-validation of a 3-Trojan patched source (not just a text-splice
check).

A second payload kind per core (stall + reset + one data payload, as the brief's default 4 asks)
needs a new RTL patch point per core, found by reading the RTL (as `next_PC_select` and `XRES`
were found in round 7) and then build-verified; **not done this round** (open question, spec
section 7). This round's multi-Trojan circuits therefore carry 1-3 Trojans that share one
payload kind per core, not 1-3 distinct payload kinds.

## 4. Darkriscv multi-Trojan smoke (2 Trojans; spec section 8's smoke step, partial; updated
2026-11-04, continuation round)

`lemanruss/htl/proc_multi_pilot.py` `run_dark_multi_smoke`: darkriscv (smaller netlist, run
first), 2 independent magic words (<kept with the answer key>), `work/htl-out/rc1/smoke-dark-
multi/` (outside the worktree, per repo rule).

### 4.0 Continuation 2026-11-04: two controller-directed changes, re-run

Peter 2026-11-04: "for the dark riscv could we magic off another net instead of finding the
reason, comment the behavior in the rtl." Separately, the controller found the RAM was still
67638 FFs in the run below, contradicting the confirmed spec section 6 decision ("Yes for the
black box ram"), and directed black-boxing it before re-running. Both are done, in order:

1. **Trigger net moved off `IDATA`/`IDACK` to `XIDATA`** (`lemanruss/htl/proc_insert.py`,
   commit `e113ab2`): `darkriscv.v`'s own eXecute-stage instruction register (`reg [31:0] XIDATA`
   under `` `__3STAGE__ ``, the config's default) replaces the raw fetch-bus comparator. `XIDATA
   <= HLT ? XIDATA : IDATAX` updates only on a cycle whose fetch was acknowledged and holds its
   value otherwise, so (reasoned, not re-derived by a trace read) it should never sample the bus
   while idle, unlike `IDATA` gated by `IDACK` (both of which can themselves read `x` in the idle
   bubble). No `valid_wire` gate is needed; the magic-sequence FSM's advance signal is `!HLT`,
   mirroring mcu's `!flush_fetch_receive`. A neutral Verilog comment is emitted at the trigger
   declaration (`DARK_TRIGGER_COMMENT`), worded to avoid the leak/name-vocabulary gate's banned
   words (checked against `NAME_VOCAB`/`LEAK_TOKENS`/`WORDS`, `lemanruss/htl/proc_release.py` and
   `lemanruss/htl/relverify.py`).
2. **RAM made a black-box hard block** (`lemanruss/htl/dark_ram_blackbox.py`, commit `782b414`):
   the controller's finding that this smoke's own FF counts (below) were still 67638 — Odin III's
   `hardmap`/`partial_map` cannot bind `darkram`'s inferred memory to `vtr.o3lib`'s hard RAM
   cells because its write is byte-enable-split (`docs/PASSES.md`'s `partial_map` row, R-8..R-12
   explicitly leaves a split write enable soft for `lower`), so `lower` was still expanding the
   2048x32 array into per-bit latches. Fix: the `darkram` instance moves out of the lemanruss
   build's own copy of `darksocv.v` (never `external/darkriscv` or the Odin III repo) into 8
   bundled `RAM_*` ports (`sim_tb` refuses a DUT instance with more than 16 port connections, and
   darksocv already has 8 of its own); `darkram.v` is dropped from Odin III's own `read_verilog`
   file list (`dark_odin_files`); `dark_tb.v` gains a hand-written behavioural replica of
   `darkram`'s *active* configuration (`__HARVARD__` defined, `__ICACHE__`/`__RMW_CYCLE__`/
   `__WAITSTATE__` undefined: single-cycle-latency synchronous read, `IDACK == IDREQ`, no RMW),
   written as whole-word reads/writes (`sim_tb`'s testbench subset also refuses a part-select on
   an array-indexed expression, read or write: two more parse errors hit and fixed before this
   built at all, `dark_ram_blackbox.py`'s module docstring has the full account). The iverilog
   copy (`iv/`) is untouched and keeps the real `darkram.v` instance, so both engines still
   simulate the same design. The Odin III binary matters here: `build/release/odin3` (the one
   the brief names) cannot simulate this config at all (`the clock ... is not a primary input`
   on the derived `CLK` net, an existing Odin III limit unrelated to this round's changes, logged
   as an open question); `build/rel-main2/odin3` (used in round 9/10 already, see its own notes)
   sim_tb's this design correctly and is what every run below uses.

- **FF count** (clean build, no Trojan): **2034** (was 67638) -- a real structural change, not a
  metric fudge: the released BLIF no longer contains the RAM's per-bit latches at all. The
  remaining FFs are the core's own state: `darkriscv`'s own 32x32 register file (1024 FFs, a
  `partial_map`-left-soft `$mem` the pass's own warning names) plus pipeline/control registers
  across `darksocv`/`darkbridge`/`darkio`/`darkpll`/`darkuart`. This is the spec section 6 range
  ("hundreds to low thousands"); `out_of_range` no longer applies to darkriscv once a release is
  built this way.
- **Build speed**: the same build (clean, 500-cycle witness, three engines: iverilog + Odin III
  RTL + Odin III netlist) now takes **0.5 s** (was 30+ minutes before the RAM fix, confirmed by
  two timed-out attempts at 600 s and 1800 s on the *unpatched* RAM, both on the clean copy, so
  not caused by the Trojan construction).
- **FF/latch equality hard gate, whole circuit (2-Trojan build)**: PASS. `ff_clean = ff_infected
  = 2034` (checked after both Trojans are added, not per Trojan, per spec section 2).
- **Per-Trojan witness**: PASS for both, on the `XIDATA`-based trigger. A witness carrying only
  Trojan 0's word fires (clean and infected traces differ, all three engines); a witness
  carrying only Trojan 1's word fires. Each Trojan's own comparator is independently provable
  without the other's word ever appearing in the instruction stream.
- **Silent on a witness with neither magic word**: still **not established at the iverilog
  engine**, by the same symptom as before the `XIDATA` change, now measured precisely: the
  infected trace (iverilog, both the 2-Trojan build and, separately, *each* single-witness
  variant `w-t0`/`w-t1`, even the ones whose own magic word fires) goes to `x` on `DEBUG[3]`
  (`= XRES` directly in `darkriscv.v`) and `DEBUG[2]` (`= |FLUSH`) from cycle 366 of 500 onward,
  identical in every infected variant regardless of which (or whether any) magic word appears;
  the matching **clean** build (same RAM black-box construction, no Trojan) never goes `x`
  anywhere in the same 500 cycles. This rules out the RAM black-box construction itself as the
  cause (clean uses the identical RAM model and stays fully defined) and rules out the specific
  magic word's bit pattern (every infected variant fails at the same cycle regardless of its own
  word). It does not, on its own, rule out the OR-of-independent-triggers construction, which
  round 10's original finding already flagged as the suspect difference from single-Trojan
  pilot3 (proven silent, docs/results-round9.md section 5). **Not root-caused further, per the
  brief.**
- **The gate that actually governs the release and its detectors is clean**: `run_dark_multi_smoke`
  additionally compares Odin III's own RTL and netlist traces (the two-state engines that build
  and simulate the released BLIF; iverilog's four-state trace is never part of the release
  pipeline) of the clean vs. the 2-Trojan infected build on the same neutral witness: **0 lines
  differ**, either RTL or netlist. Odin III's two-state simulator necessarily resolves the same
  four-state hazard iverilog reports as `x` to some concrete 0/1 value on each run, and that
  value matches the clean build's deterministic value every time measured. H-P1 as the spec
  literally states it ("witness fires in iverilog + Odin III RTL + Odin III netlist sim, silent
  on shipped programs") still names iverilog, so this is reported as a real, unresolved gap
  against that wording, not quietly narrowed to "the release artifact passes" -- but it is also
  reported, accurately, that the artifact the release and detectors actually consume shows no
  difference on this check.
- **mcu multi-Trojan smoke, run this round** (not run in the original round 10 pass): 2 magic
  words (<kept with the answer key>), `work/htl-out/rc1/smoke-mcu-multi/`. FF/latch equality
  PASS (`132446 = 132446`; mcu's own RAM is still per-bit latches, out of this round's scope --
  the controller named darkriscv specifically; mcu's `out_of_range` flag from section 2 still
  applies to it until mcu gets the same treatment). Per-Trojan witness PASS for both. **Silent on
  the neutral witness: PASS** (`all_silent_on_no_witness = true`) -- mcu does not show the
  darkriscv-specific `x` hazard above; this matches round 9's single-Trojan mcu result (4/4
  shipped programs silent) extending cleanly to the multi-Trojan construction.

### 4.1 Continuation 2 (2026-11-04): mcu RAM black box, shipped-program gate

**mcu RAM black box** (`lemanruss/htl/mcu_ram_blackbox.py`, commit `b49638e`; Peter's "Yes for the
black box ram" applies to every base). Same construction as darkriscv: the `dual_port_BRAM_byte_en`
instance (4 byte lanes x 4096 x 8 = 131072 per-bit latches after `lower`) leaves
`dual_port_BRAM_memory_subsystem`; the subsystem and `single_cycle_BRAM_top` gain 7 `RAM_*` ports
(15 ports on the testbench's DUT, under `sim_tb`'s 16 limit); `mcu_tb.v` carries a behavioural replica
(reads sample before the write, port 1 never writes, zeros overlaid by the program's four `.vmh`
planes). The two RAM modules are dropped from Odin III's `read_verilog` list; the `iv/` copy keeps
the real RAM. Verification that the replica is faithful: clean traces of the old (per-bit RAM) and new
builds are identical on all three engines for the neutral and both per-Trojan witnesses (0 differing
lines in 9 comparisons).

| mcu | before | after |
|---|---|---|
| FF count (clean = infected) | 132446 | **1310** |

mcu 2-Trojan smoke (<kept with the answer key>), black-boxed build:

| gate | iverilog | Odin III RTL | Odin III netlist |
|---|---|---|---|
| FF equality (whole circuit) | PASS 1310 = 1310 (netlist level) | n/a | n/a |
| Trojan t0 witness fires (clean vs infected differ) | 32 lines differ | 32 | 32 |
| Trojan t1 witness fires | 32 | 32 | 32 |
| neutral witness silent (clean vs infected) | 0 differ | 0 | 0 |

darkriscv 2-Trojan smoke, from 4.0 (not re-run: unchanged code), on the same three engines:

| gate | iverilog | Odin III RTL | Odin III netlist |
|---|---|---|---|
| FF equality | PASS 2034 = 2034 | n/a | n/a |
| each Trojan's witness fires | yes (both) | yes | yes |
| neutral witness silent | **FAIL** (x on `DEBUG[3]`, `DEBUG[2]` from cycle 366) | 0 differ | 0 differ |

**Silent on every shipped program, multi-Trojan builds** (3 Trojans per base, the maximum; clean vs
infected, number of differing trace lines; 0 = silent). mcu and darkriscv words <kept with the answer key>.

| base, program | cycles | iverilog | Odin III RTL | Odin III netlist |
|---|---|---|---|---|
| mcu blink | 2000 | 0 | 0 | 0 |
| mcu blink_interrupt | 2000 | 0 | 0 | 0 |
| mcu blink_function_call | 2000 | 0 | 0 | 0 |
| mcu interrupt | 2000 | 0 | 0 | 0 |
| darkriscv prebuilt firmware (`darksocv.mem`) | 4000 | 0 | 0 | 0 |

15 of 15 comparisons silent (5 programs x 3 engines).

**darkriscv iverilog `x` on shipped programs** (recorded, not root-caused, per the brief): the
darkriscv prebuilt firmware, 4000 cycles, 3-Trojan infected build: **no `x` on any trace line** in
the iverilog trace, clean or infected (0 and 0 lines containing `x`), and none in the Odin III RTL
trace. The `x` of 4.0 therefore appears only on the synthetic neutral witness (a few instruction
words, then uninitialised memory), not on the shipped program. mcu iverilog traces carry one line with
an `x` in both clean and infected builds of every program (the reset-window line, identical).

**Left for the full build**: Peter's H-P1 wording decision (iverilog neutral-witness `x` on
darkriscv; shipped-program gate is clean); per-circuit variety (ABC re-draws, dummy cuts) on a Proc
netlist; the second and third payload kinds per core (stall, reset, data) with their patch points;
per-circuit random magic words and legal-instruction decoding; `lut4`/`lut6` forms; picorv32 reduced
config (not attempted this round); release, answer key, datasheet, archive, detectors, paper rows.

## 5. What is not in this round (honest scope, not a silent drop)

- The full N=100 circuits x 3 forms (gates, lut4, lut6) = 300-circuit release: **not built**.
  Reaching N=100 per form from 2 real bases needs either many ABC-script re-draws (spec section
  4's variety plan) or a third working base (picorv32 reduced config, patch point not found yet)
  — real engineering, not a smoke-scale task. The continuation round's RAM black-box fix removes
  one blocker (darkriscv's FF count and build speed); the iverilog-side silence gap (section 4.0)
  is still open and is logged as a real gap against H-P1's literal wording, not treated as
  blocking by itself given Odin III's own two-state engines (what the release and detectors
  consume) already show silence -- the controller's call on whether to proceed to the full build
  with that gap open and documented, or close it first, is listed in the final report's open
  questions.
- (Superseded by 4.1: mcu's RAM is now a black box, 1310 FFs.)
- `lemanruss restructure` / dummy-cut variety has not been exercised on a Proc netlist this
  round.
- No release, no archive, no detector table beyond the `out_of_range` unit test, no PR for this
  work beyond the branch itself (brief step 6: PR opened, not merged, see the final report).
- H-P2 (no detector beats size control on any form) is untested: there is no release yet to run
  detectors against.

## 6. Verdict (CAD convention: counts first, then the label)

1. Base survey: 2 of 4 candidate bases build end to end (mcu, darkriscv, both already proven in
   pilot3); 1 builds in a reduced configuration only (picorv32); 1 does not build (tinyriscv).
   **Not a detector result**, a build-capability finding.
2. `out_of_range`: implemented and unit-tested (7/7 tests), reproducing round 9's exact failure
   mode (training FFs in the hundreds, Proc FF counts in the tens of thousands) as a test case.
   Not yet run against a Proc release's actual circuits (there is none yet).
3. Multi-Trojan insertion: implemented, unit-tested (10/10 new tests passing, including a real
   Odin III parse check), and smoke-built on darkriscv: the FF/latch gate holds and each of
   2 Trojans fires on its own witness. The silent-on-no-trigger check still does not pass at the
   iverilog engine after moving the trigger to `XIDATA` (section 4.0); this is reported as an
   open finding, not glossed over.
4. (2026-11-04 continuation) The trigger net move (`IDATA`/`IDACK` -> `XIDATA`) and the RAM
   black-box fix are both done and verified: FF count 67638 -> 2034, build+sim time 30+ min ->
   0.5 s, FF/witness gates still hold on the black-boxed build. The iverilog silence gap persists
   under a different root (not the RAM, not the specific magic word -- every infected variant
   fails identically regardless of its own word, and the matching clean build never fails), still
   not root-caused per the brief; Odin III's own RTL and netlist engines (what the release and
   detectors consume) show 0 differing lines on the same check. mcu's multi-Trojan smoke (not run
   in the original round 10 pass) is clean on all three gates including silence.
5. **This round's status is "infrastructure, two real fixes, and one still-open honest finding,"
   not "a benchmark."** The full build (section 5) needs a controller decision on the iverilog
   gap before or alongside it.
