# Seeker-Proc rc1: a true Seeker's Dilemma processor benchmark, N=100 per form (2026-11-03)

Purpose (hub docs/purpose.md, Leman Russ III path: processor family; memory
lemanruss-release-each-round). RQ: can Seeker-Proc be a true SD benchmark (detector not told
whether a circuit is infected) at three forms (gates, lut4, lut6). Measures: release gates pass
rate, rareness of each Trojan, detector AUROC / W/L/T vs size control (CAD reporting convention).

Peter, 2026-11-03, verbatim: "Can we build true SD benchmarks for the Procs with N=100 in the
gate, Lut4 and Lut6?" Earlier the same day: "Can we make the proc ones triggers active by magic
number (in the Instruction Register) as in earlier work OR you can make the trojans the
same as there's" and "So why in the Lehman russ confusion matrix are the proc ones easy to find?"
(answer, round 9: ffcount flags all four pilot3 circuits, clean too, because the RAM lowered to
per-bit latches puts 67k-132k latches far above the Comb/Seq training range; every detector
scores clean vs infected twin within 0.0023).

## 0. Hypotheses

- **H-P1**: every one of the 300 circuits passes the release gates (witness fires in iverilog +
  Odin III RTL + Odin III netlist sim, silent on shipped programs, FF/latch equality, leak/name-
  vocabulary gates).
- **H-P2**: no detector of the suite beats the size control with an interval above 0.5 on any
  form (labels per memory cad-reporting-convention: headline W/L/T + win count first, then the
  strict ABOVE CHANCE / INCONCLUSIVE / BELOW CHANCE label).

## 1. Controller defaults (agent defaults, Peter can override; logged per CLAUDE.md)

1. N = 100 circuits per form: gates (lowered gate netlist, `--gates-as-names` as pilot3), lut4
   (Odin III `abc --lut 4`), lut6 (`abc --lut 6`), 300 in all. The same 100 logical circuits in
   all three forms (one id per circuit per form, opaque, not linkable across forms in the
   release; the answer key links them).
2. Bases: open-source RV32 cores already in the workspace only (`external/`): mcu and darkriscv
   (pilot3), plus tinyriscv and picorv32 if they build through Odin III.
3. Trigger: magic number in the INSTRUCTION REGISTER (darkriscv: its registered instruction,
   `IDATA` qualified by `IDACK`, as pilot3, not a raw bus sample; mcu is single-cycle, its
   `instruction` wire is the IR). One magic word per Trojan, varied per circuit (random 32-bit
   values decoding to a legal but unused-in-shipped-programs RV32I instruction, rareness
   reported). No added flip-flop (hard gate: FF count infected == clean twin, as rc7).
4. Payloads: 2 to 3 per core from the HTL vocabulary, on the core's own state (stall, reset, one
   data payload such as a register bit flip or a branch flip), each with a witness program that
   fires it and silence on every shipped program.
5. Clean variety: a clean circuit must not be a byte-copy of a public base: per circuit, vary
   synthesis (Odin III options / mapper seeds, ABC restructuring scripts of the Seq rc7 kind) and
   dummy cuts of the Seq rc7 kind. Infected circuits get the same treatment. State which forms of
   variety were possible per base (section 4).
6. RAM: keep memories as black-box hard blocks (not per-bit latches) in all three forms, so FF
   counts are in a sane range; datasheet states it. Scorer/detector: a score of a circuit outside
   a detector's training range (FF count, size) is reported as `out_of_range`, never counted as a
   flag (section 6).

## 2. Peter's decisions, 2026-11-03 (controller update, applied; logged per repo-is-source-of-truth)

Controller update from Peter (2026-11-03), re-reading defaults 4 and 6: **"1 to 3 payloads per
core; Yes for the black box ram."** Applied:

- Each infected circuit carries **1 to 3 Trojans** (count drawn as Seeker-Comb/Seq draw it:
  `docs/specs/2026-11-01-seeker-n200-design.md` section 3, P(1) = 0.5, P(2) = 0.3, P(3) = 0.2),
  so the scorer's found-rate by Trojan count 1/2/3 (`docs/specs/2026-11-02-scoring-design.md`
  section 1 tier) applies to Proc as it does to Comb/Seq. Each Trojan has its own magic word in
  the instruction register and a payload drawn from the core's own vocabulary (up to 3 payloads
  per core, per default 4 above). Multiple Trojans in one circuit must still add no flip-flop
  (hard gate, checked per circuit, not just per Trojan) and each Trojan must have its own witness
  that fires it (as Comb/Seq's multi-Trojan rule, n200-design section 3: "each Trojan fires on
  its own witness... Trojans of one circuit have separate witnesses").
- RAM as black-box hard blocks (not per-bit latches) is **confirmed** (default 6, unchanged).

## 3. Clean/infected prior (reused from Seeker-Comb/Seq, not told to the detector)

Per `docs/specs/2026-11-01-seeker-n200-design.md` section 4 (Peter's rc4 redesign, the rule this
spec reuses verbatim, not re-derived): per form, `n_inf ~ Uniform{10..70}` drawn once per form,
seeded, recorded only in the answer key. An infected circuit carries 1..3 Trojans
(P = 0.5, 0.3, 0.2, section 2 above). The other `100 - n_inf` circuits of the form are clean
variants (section 5), never byte-identical to a public base. Checks per finished circuit mirror
n200-design section 4's last bullet: clean checked against the golden (ABC cec/dsec where ABC can
read the netlist, section 4 below; Proc's own witness-replay gate otherwise), infected checked
against its own `pre` (pre-obfuscation, triggers forced inactive) which must equal the golden.

## 4. Base survey (read, not guessed; `external/` only)

| base | status | evidence |
|---|---|---|
| mcu (Arduino-on-RISC-V) | builds | pilot3: RTL=iverilog=Odin III RTL=Odin III netlist, all 4 shipped programs silent, FF 132446=132446 (`docs/results-round9.md` section 5) |
| darkriscv | builds | pilot3: same checks, FF 67638=67638 |
| tinyriscv (`external/tinyriscv`) | **does not build** | `odin3 -p read_verilog` on `tinyriscv_soc_top.v`: `error: hierarchical reference 'u_tinyriscv.u_regs.regs' is not supported`, `ODIN3_ERR_PARSE` (debug module's register-file probe uses a hierarchical path into a submodule array; not an Odin III feature this round, logged as an open question for the controller per repo CLAUDE.md, not worked around here) |
| picorv32 (`external/picorv32`, default parameters) | **builds, reduced config only** | `odin3 -p "read_verilog;proc;opt;stats"` on `picorv32.v` elaborates the top with default params (no `ENABLE_MUL`/`ENABLE_DIV`/`ENABLE_IRQ`): "not instantiated under the top, not elaborated: 'picorv32_regs', 'picorv32_pcpi_mul', 'picorv32_pcpi_fast_mul', 'picorv32_pcpi_div', 'picorv32_axi', 'picorv32_axi_adapter', 'picorv32_wb'" (635 cells). The brief's "picorv32 full core: check" is answered **no**: Q-L12's finding stands (`picorv32_pcpi_mul` unreadable) once `ENABLE_MUL`/`ENABLE_FAST_MUL` turn the multiplier submodule on; this spec uses picorv32 only in its default (no-mul, no-div, no-pcpi) configuration and states that restriction in the datasheet. |

So this round's base set is **mcu + darkriscv** for the full build (both proven end-to-end in
pilot3); **picorv32 (reduced config)** is a candidate third base, not yet run through the Proc
pilot pipeline (`proc_insert.py`/`proc_run.py` have no picorv32 patch points yet: its trigger
point (the fetched instruction word register) and a payload victim (its own state, per default 4)
need to be found by reading `picorv32.v`, the same way mcu's `next_PC_select` and darkriscv's
`XRES` were found in round 7, not guessed). tinyriscv is excluded this round (open question for
Odin III: hierarchical references into a submodule's array, as above).

**Variety per base** (default 5): with only 2 (optionally 3) working bases, "the same 100 logical
circuits in all three forms" (default 1) cannot be 100 distinct public cores; each logical
circuit is one (base, Trojan-draw, synthesis-variant) tuple. Variety available per base, read
from the existing pipeline rather than assumed:
- ABC restructuring scripts (`lemanruss/htl/obfuscate.py`, 18 scripts, Seq rc7 kind) apply to the
  **gate netlist** (`abc --gates andornot`) and to lut4/lut6 mapping scripts the same way n200
  uses them (`docs/specs/2026-11-01-seeker-n200-design.md` section 4 step 2-3): usable on all
  three forms, on both mcu and darkriscv, once the netlist is produced (pilot3's `lower_gates_as_
  names` already produces a gate-level BLIF Odin III can hand to the restructuring script).
- ABC `read_blif`-based restructuring of the *source* netlist was tried in pilot2/pilot3 and
  **fails on both cores** (`docs/results-round9.md` section 5, "ABC `read_blif` fails on both
  cores" per pilot3 note; `docs/results-round7.md` is the first record of this). Per default 5,
  Odin III's in-process ABC path (the one `lemanruss restructure`/`lemanruss n200` already use
  for `abc --lut`) is the one this spec uses for mapping and restructuring; no direct ABC CLI
  `read_blif` on these two netlists.
- Dummy cuts (Seq rc7 kind, `lemanruss/htl/cutstitch.py` / the dummy-cut generator used for Seq's
  clean variants): applicable to both cores' gate netlists the same way as Seq, since dummy cuts
  operate on the finished BLIF, not on the RTL.
- Mapper-seed / ABC-script variety (18 scripts x multiple draws) gives, per base per form,
  up to 18 distinct restructurings before any dummy-cut or ABC-script repetition is needed to
  reach 100; 2 bases x 18 scripts = 36 < 100, so reaching N=100 per form needs either (a) more
  scripts/seeds than the 18-script catalogue (repeat scripts with different random seeds, which
  `obfuscate.py` already supports per n200), or (b) a third working base (picorv32 reduced, or a
  fourth if one is found), or both. This spec uses (a) first (seeded re-draws of the 18-script
  catalogue, as n200 already does per circuit) and logs (b) as the way to grow beyond it if (a)'s
  circuits turn out insufficiently distinct (duplicate-hash gate, section 5).

## 5. Release gates (reused, not redesigned; `docs/specs/2026-10-31-htl-design.md` section 13,
`docs/results-round9.md` sections 4/7)

a. integrity (file count, checksums); b. leak words (name-vocabulary scan: `htl`, `trojan`,
`trigger`, `payload`, `__htl_*`, the ABC restructuring banner); c. function (witness replay:
iverilog, Odin III RTL, Odin III netlist, all three agree, fires on the witness, silent on every
shipped program); d. rareness (re-measured, P(match) per magic word = 2^-32 per Trojan, SCOAP
CC0/CC1/CO); e. separation (duplicate-hash check across circuits of a form); f_distinct (0
duplicate groups); g_style (clean vs infected style sanity, best-AUROC bound reported, not
tuned away); h_provenance (0 traces: no inserter-only net names, no ABC banner, no comment).
Added this round: FF/latch equality hard gate **per circuit** (not per Trojan): infected FF count
== clean twin's FF count, re-checked after every Trojan is added (section 2's multi-Trojan rule).
A circuit failing any gate is dropped and redrawn (as n200), never shipped; failures are listed in
`failures.json` and the datasheet, never padded with copies (as n200 section 2).

## 6. Scorer/detector change: `out_of_range` (default 6)

Round 9 found all four pilot3 circuits flagged by `ffcount` (clean and infected alike): their FF
count (67k-132k, RAM lowered to per-bit latches) sits far outside the Comb/Seq training range
(hundreds to low thousands of FFs), so a size/FF detector is extrapolating, not detecting. This
round keeps RAM as a black-box hard block (section 2), which should put Proc's FF counts back
inside a sane range -- but any future base, or any detector a submitter brings, can still exceed
its own training range. Fix (`lemanruss/detect`, `lemanruss/score`): a detector's score function
is unchanged; the **flag** a circuit receives is `out_of_range` (a third value, neither flagged
nor not-flagged) when the circuit's FF count falls outside `[min, max]` of the detector's own
training-fold FF counts, computed once per fold from the training records already available to
`run_proc`/`harness.run_all`. `out_of_range` circuits are excluded from the confusion matrix and
from AUROC (reported separately, as the brief's confusion-matrix note asks), never counted as a
false positive or a miss. Implementation: a pure range-check function (`lemanruss/detect/
ffrange.py`), tested without needing a built release; wired into `lemanruss/detect/proc.py`
(`run_proc`, which is the path pilot3 already uses) and `lemanruss/score/scorer.py`'s confusion
matrix. Test: `tests/test_detect_ffrange.py`.

## 7. Open questions for the controller (per repo CLAUDE.md: a missing Odin III feature is an
open question here, not a workaround)

1. tinyriscv's hierarchical reference into `u_regs.regs` (a debug-module register-file probe) is
   not supported by Odin III `read_verilog`; this spec does not patch tinyriscv's RTL to route
   around it (that would change the base, not just instrument it) and excludes tinyriscv from
   this round's base set.
2. picorv32's multiplier/divide submodules (`picorv32_pcpi_mul`, `picorv32_pcpi_fast_mul`,
   `picorv32_pcpi_div`) are read-unreadable by Odin III once their `ENABLE_*` parameters turn
   them on (Q-L12's finding, unchanged); this spec only uses picorv32's default (no-mul, no-div)
   configuration, stated in the datasheet, and does not attempt to fix Odin III's reader here.
3. Reaching N=100 per form from 2 (or 3) real bases needs either many ABC-script re-draws per
   base (section 4) or a fourth working base; this spec logs ABC-script re-draws as the agent
   default and a fourth base as the fallback, not yet exercised.

## 8. Build plan

Smoke: one circuit per base x payload-count (1, 2, 3 Trojans) x form (gates, lut4, lut6) = 2 bases
x 3 x 3 = 18 circuits, clean twin included. Full build: smallest first (mcu before darkriscv per
pilot3's own FF counts, 132446 vs 67638 -- darkriscv is the smaller netlist, built first), under
`~/odin3-ws/odin3/tools/heavy-run` (`ODIN3_HEAVY_OK=1`, jobs <= 2, <= 3 GB RSS each), commit+push
after each step. Run roots under `~/odin3-ws/work/htl-out/` (outside the worktree, per repo rule).
