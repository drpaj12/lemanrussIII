# Round 11 results: Seeker-Proc rc1 Continuation 3 -- payload kinds, picorv32, batch-build gap
(2026-11-04)

Brief `work/controller-scripts/briefs/lemanruss-proc-sd-rc1.md`, "Continuation 3 2026-11-04: full
build" (PR #21 merged on main, `8c4b06e`). Spec `docs/specs/2026-11-03-seeker-proc-rc1.md`
section 0a (H-P1 amendment, committed before any build per the brief, quoting Peter's 2026-11-04
decisions). Mid-task controller addition: "Why can't we use picorv32? It looks usable?" --
picorv32 added as a third base.

This round delivers the payload-kind engine and picorv32 for all three bases, smoke-proven with
fixed inputs; it does **not** deliver the N=100 x 3 forms release. A batch build with the
required *random* per-circuit magic words surfaced a reproducible silence-gate failure that this
round's remaining time did not root-cause. Honest status below, in the round-10 style.

## 1. H-P1 amendment (spec section 0a, committed before any build)

Peter 2026-11-04, verbatim: "1a with a secret program that activates trojans (right?)"; "2 that's
fine, but why not a trojan that messes up the lsb of an alu operation (maybe shift right) or
rotate"; "4) sure" (PR #21 merged). Committed as spec section 0a (`lemanruss` commit `88b58e7`)
before any Continuation-3 build step, as required: silence on a non-shipped program (the
synthetic neutral witness) is judged by Odin III RTL + netlist sim; iverilog is named only for
shipped programs; the darkriscv iverilog `x` on the neutral witness (round 10 sections 4.0/4.1)
is a recorded four-state-simulator difference, not a gate. Witness programs are each infected
circuit's own secret activation program, in the answer key only.

RV32I has no rotate instruction (checked against the RV32I base integer opcode table, chapter 2
of the Unprivileged ISA spec): only the shift-right LSB-flip ALU payload is built, as the
amendment states.

## 2. Payload-kind engine: reset / stall / alu-srl-lsb, all three bases (commit `66958f8`)

`lemanruss.htl.proc_insert.insert_{mcu,dark,picorv32}_kinded_multitrojan`: 1-3 independent
Trojans per circuit, each its own magic word and its own payload **kind**, drawn per Trojan
(spec section 0a point 2). Three combined per-kind wires per circuit
(`__htl_trigger_{reset,stall,alu}`), each the OR of that circuit's Trojans assigned that kind,
built on top of the existing per-Trojan trigger wires (round 10's `_independent_triggers_decl`).

Patch points, found by reading each core's own RTL (not guessed):

| base | reset | stall | alu (flip bit 0 of a completed SRL/SRA/SRLI/SRAI result) |
|---|---|---|---|
| mcu | `__htl_pc_mux` 2nd encoding (`2'b11`, `fetch_issue.v`'s own case default: jump to address 0) | `__htl_pc_mux` existing encoding (`2'b01`, stall) | new: the EX instance's `ALU_result` port, tapped via `__htl_alu_raw` |
| darkriscv | existing: OR into `XRES` | new: OR into `HLT`'s own definition | new: `RMDATA`'s one write-back use, tapped via `__htl_rmdata` |
| picorv32 | new: OR into the FSM's own `if (!resetn)` branch | new: gate `decoder_trigger` so decode never launches again | new: `cpu_state_shift`'s own `reg_sh==0` write-back line |

49 unit tests (new/updated), ruff + `mypy --strict` clean, every patched source re-validated with
a real Odin III `read_verilog --parse-only`.

## 3. picorv32 (external/picorv32, YosysHQ, ISC license; default params -- no ENABLE_MUL/DIV/IRQ)
added as a third base (commit `bb6dc13`)

Controller, Peter 2026-11-04: "Why can't we use picorv32?" picorv32 has no RAM of its own (its
memory bus is external by design, unlike mcu/darkriscv); `lemanruss.htl.picorv32_tb` writes this
round's own hand-written port-only testbench (`pico_tb.v`, not copied from upstream's own
`testbench_ez.v`, per CLAUDE.md) with a 256-word behavioural memory array. The byte-merge logic
goes through a plain scratch reg (`mem_next`), not a part-select on `memory[idx][...]` directly --
the same `sim_tb` limit round 10 hit building darkriscv's RAM black-box.

Trigger: `next_insn_opcode`, the FSM's own register that updates only on a completed memory
transfer and holds its value otherwise (same intent as darkriscv's `XIDATA`).

First smoke run (three fixed smoke-test words, redacted, one of each kind) hit one
bug, found and fixed before any result was trusted: `insert_picorv32_kinded_multitrojan` inserted
the new declarations before the file's *last* `endmodule` (`str.rindex`); `picorv32.v` holds 8
modules (`picorv32`, `picorv32_regs`, two multiplier variants, divider, `picorv32_axi`,
`picorv32_axi_adapter`, `picorv32_wb`), so the declarations landed in `picorv32_wb`, not
`picorv32` -- `next_insn_opcode`/`__htl_trigger_*` were then undeclared in the actual DUT and
iverilog failed to elaborate. Fixed: insert before the first `endmodule` *after* `picorv32`'s own
`module` line (Verilog modules do not nest, so that is always the right one).

With the fix, the fixed-word smoke (reset + stall + alu, 3 Trojans) passed cleanly: FF/latch
equality **1615 = 1615**, every Trojan's own witness fires, silence on the neutral witness
**PASS** on Odin III RTL + netlist (the H-P1 amendment's own governing gate); only iverilog
differs on the neutral witness (recorded, not gating, the same shape as darkriscv's own
documented gap, not root-caused here either, per the brief).

picorv32 joins mcu and darkriscv as a third base for the full build, per this smoke.

## 3a. Smaller-to-bigger ordering correction (Peter's standing rule, restated by the controller
2026-11-04: "every pass goes from smaller to bigger designs, because size can be a stop
condition")

`proc_build.BASES` originally read `(darkriscv, picorv32, mcu)`, carried over from pilot3's
pre-black-box FF counts (darkriscv 67638 < mcu 132446, docs/results-round9.md section 5).
Section 3's black-boxed counts invert that: **mcu 1310 < picorv32 1615 < darkriscv 2034**
(docs/results-round10.md section 4.1; picorv32's own count, section 3 above). Fixed to
`(mcu, picorv32, darkriscv)`; `build_n_circuits`'s own per-slot loop already builds circuits in
ascending id order within a base. A circuit that hits a time/memory limit is recorded in its
`BuiltCircuit.error` field (the existing generic-exception path already catches a subprocess
timeout the same way) and the pass continues to the next circuit, never aborting the batch.

## 4. Batch build: random per-circuit draws expose a silence-gate failure not seen in the fixed-
word smokes (new finding, not root-caused this round)

`lemanruss.htl.proc_build` generalises the three bases' smoke machinery into one driver
(`build_one_circuit`/`build_n_circuits`): draws a Trojan count (1-3, P = 0.5/0.3/0.2, the
Comb/Seq prior reused per spec section 2), a payload kind per Trojan, and a random legal magic
word per Trojan (`rv32i.random_magic_word`, seeded, excludes already-used words); runs the same
FF-equality / per-Trojan-witness / H-P1-amended-silence gates as the fixed-word smokes; on a
pass, maps the clean and infected gate-level BLIF to all three release forms (gates/k4/k6) with
`lemanruss.htl.obfuscate.obfuscate` (the same per-circuit ABC-script variety n200/Comb-Seq already
use, satisfying spec section 4's "vary synthesis" default without a fourth base).

A small batch (`build_n_circuits(3, base, seed=1, ...)`, so up to 4 draws per base slot) gave:

| base | passing | failed (redraws) | failing circuits' kinds |
|---|---|---|---|
| darkriscv | 0 / 3 | 15 | every combination drawn, including `['reset']` alone |
| picorv32 | 3 / 3 | 1 | every failure carries an `alu`-kind Trojan; every pass is `['reset']` only |
| mcu | 3 / 7 | 4 | every failure carries an `alu`-kind Trojan; every pass is `reset`/`stall`-only |

Read together with section 3's fixed-word smoke (which passed on all three kinds, all three
bases, with specific hand-picked magic words): the payload-kind construction is not broken in
general -- it is correct for the exact inputs each smoke used -- but the *random* magic-word
space the full build needs hits a silence-gate failure far more often than the fixed smoke
suggested, concentrated in `alu`-kind Trojans (mcu, picorv32: every batch failure carries one;
every batch pass does not) and, for darkriscv specifically, in nearly every draw regardless of
kind (a result the section-3-style fixed smoke, run on reset+stall+alu together with specific
words, did not show).

A quick isolation pass on the `alu`-kind, single-Trojan, darkriscv case (one magic word, neutral
witness, no other kind present) found that removing *only* the `alu` patch (`RMDATA` ->
`__htl_rmdata`) restores silence, while removing the `stall` patch (`HLT` ->
`__htl_trigger_stall || ...`) does not change the outcome. That narrows the fault to the `alu`
payload's own construction (not an interaction with the `stall` patch, and not purely the
already-documented `IDATA`/`XIDATA`-idle-bubble class of artifact, since this reproduces on
Odin III's own two-state RTL and netlist engines, not only iverilog) -- but the isolation stopped
there: **not root-caused further this round**, per the time this continuation had left, and
flagged here as a real engineering defect in this repo's own insertion code (not an Odin III
gap, so not logged as an open question for the controller; CLAUDE.md's "never edit Odin III" rule
does not apply to a bug in `lemanruss`'s own patch text).

## 5. What is not in this round (honest scope, not a silent drop)

- **The N=100 x 3 forms = 300-circuit release: not built.** Section 4's failure rate on random
  draws makes shipping at N=100 irresponsible before the `alu`-kind defect is fixed (H-P1 itself
  demands every shipped circuit pass every gate; redrawing past it, as `build_n_circuits` already
  does, would either silently exclude `alu`-kind Trojans from the released mix -- which the
  answer key and detector tables would then misrepresent as "every kind represented" -- or burn
  far more redraws than `max_redraws` on darkriscv, which this round's data says fails almost
  every draw regardless of kind.
- No release, no archive, no detector table, no updated paper rows: downstream of the release
  above, not attempted.
- `lemanruss.htl.proc_build` (committed, unit-test-clean at the module level via its own imports,
  lint/mypy clean) is ready to drive the full build *once* the `alu`-kind defect (section 4) is
  fixed and darkriscv's much higher failure rate is understood; it is not itself the blocker.
- H-P2 (no detector beats size control) is untested: there is no release to run detectors
  against.

## 6. Verdict (CAD convention: counts first, then the label)

1. Payload-kind engine (reset/stall/alu) on mcu, darkriscv and picorv32: implemented, unit-tested
   (49 tests), lint/mypy clean, and smoke-proven with fixed, hand-picked inputs on all three
   bases and all three kinds together. **Not a detector result**, a construction finding.
2. picorv32 added as a third base: smoke passes (FF equality, every Trojan's witness, H-P1-
   amended silence) with fixed inputs, after fixing a multi-module `endmodule` insertion bug
   found before trusting the first result.
3. The random-draw batch build (section 4) is the round's central finding: the payload-kind
   construction that passed every fixed-word smoke fails the silence gate far more often once
   magic words are drawn randomly, overwhelmingly on `alu`-kind Trojans (mcu, picorv32) and on
   nearly every draw for darkriscv. Isolated to the `alu` payload's own construction for the
   single-Trojan darkriscv case, not fully root-caused.
4. **This round's status is "the payload-kind and picorv32 infrastructure is built and smoke-
   proven, but the full build is blocked by a newly found, not-yet-fixed silence-gate defect,"
   not "a 300-circuit benchmark."** Fixing section 4's defect, and re-running `build_n_circuits`
   at a larger N to measure the fixed failure rate, is the next continuation's first job before
   any release/archive/detector/paper-rows step.

## 7. Continuation 4 (2026-11-04): silence-gate defect root-caused and fixed

Method: deterministic repro per base (`build_n_circuits(..., seed=1)` draws replayed), minimise by
variant runs on a copy of the infected tree (one source substitution per run, Odin III RTL +
netlist compared with clean), one hypothesis at a time. Section 4's diagnosis ("silence-gate
failure, alu-kind") was two different defects, neither in the alu LSB-flip text itself.

**Root cause 1, darkriscv (every draw, any kind, including reset alone).**
`lemanruss/htl/proc_insert.py:408` declared `wire __htl_rmdata` with no range. The write-back mux
uses it 240 lines before the declaration (`MCC||RCC ? __htl_rmdata:`), so it was a one-bit net and
truncated RMDATA in every infected circuit whether or not `alu` was drawn; the infected core wrote
0 to every ALU-fed register and never reached the OPORT store. Evidence: the unmodified infected
tree differs from clean on the neutral witness (Odin RTL and netlist); the same tree with only
`wire [31:0] __htl_rmdata` is equal; with the use inlined as
`(__htl_trigger_alu && FCT3==3'd5) ? {RMDATA[31:1], ~RMDATA[0]} : RMDATA` is equal; with the
`__htl_rmdata` use reverted to `RMDATA` is equal. It also explains why the fixed-word smoke
"passed": "fires" was a trace difference from clean, which the truncation produced for any
program. The fixed-word smokes never proved that the alu payload does what it says.
Fix: commit `3da3e01`.

**Root cause 2, all bases (alu kind): the alu Trojans never fired.** `proc_build.py` replayed the
reset/stall witness (`mcu_witness_words`, `dark_witness_words`: nops, magic word, store/self-loop)
for every kind. That program has no shift and the magic word was always an ADDI, and the trigger
watches the instruction being executed (mcu `instruction`, darkriscv `XIDATA`), so the
payload's `ALU_operation==12/13` / `FCT3==5` condition could never hold at the same time as the
trigger. mcu and picorv32 failed the "witness fires" gate, not the silence gate. Fix
(`proc_witness.py`, `proc_build.py:draw_trojans`, `rv32i.py`): alu magic words are
shift-right words on mcu/darkriscv with a witness that sets the operand, runs the word and stores
rd; on picorv32 the watched `next_insn_opcode` holds the prefetched next word during a multi-cycle
shift (`mem_do_prefetch`), so the witness is `srli ...,8` followed by the ADDI magic word. Commit
`9660baa`. Spec section 0b records the rule.

**Weaknesses of the gates found on the way, fixed in the same commit.** "Fires" was iverilog-only
and so true for any darkriscv infected core (iverilog `x`); it now requires a trace difference on
all three engines. Added a neutral-shift gate (a non-magic shift-right must leave Odin III RTL and
netlist equal to clean) so an alu patch not gated by its trigger would be caught. Added the
rejection rule (shipped program words and witness scaffolding words are never drawn; no draw in
the N=10 runs was rejected after the fact, the set is applied before drawing).

Tests added (`tests/test_proc_witness.py`, 17): shift encoders vs ISA spec words, decode round
trip, witness shapes per base, picorv32 ADDI-after-shift witness, rejection set covers every
scaffolding word, shipped words in the rejection set, darkriscv `__htl_rmdata` is `[31:0]`
(root cause 1), and four real-gate replays through `build_one_circuit(forced=...)` (darkriscv
reset-only random word, darkriscv stall+alu, mcu alu+alu, picorv32 alu) that skip without the
externals or a built Odin III.

N=10 per base, `build_n_circuits(10, base, seed=1, max_redraws=0)` (a failed draw is a reported
failure, no redraw), `build/rel-main2/odin3`, gates: FF equality, every Trojan fires on iverilog +
Odin III RTL + netlist, silent on the neutral witness (Odin RTL + netlist), alu neutral-shift
silence.

| base | circuits pass / 10 | Trojans by kind in the 10 circuits (all fire, all silent) | circuits with >=1 alu |
|---|---|---|---|
| mcu | 10 / 10 | reset 4, stall 6, alu 9 | 6 |
| picorv32 | 10 / 10 | reset 5, stall 8, alu 5 | 4 |
| darkriscv | 10 / 10 | reset 6, stall 5, alu 5 | 4 |

30 / 30 circuits, 0 failures, 0 redraws; 56 Trojans. The iverilog neutral-witness difference on
darkriscv and picorv32 (recorded, not gating, spec 0a) still appears on 15 of the 20 picorv32 and darkriscv draws (darkriscv 9 of 10, picorv32 6 of 10)
and is unchanged by this fix. Not done: the shipped-program silence gate is still not part of
`build_one_circuit` (brief Continuation 2 step 2 ran it for the smoke builds); the 300-circuit
build must add it. The N=10 run dirs are under `work/htl-out/rc1fix/` (outside the worktree).


## 8. Continuation 5: full build, release, archive, detectors (2026-11-04)

Branch `feat/proc-sd-rc1-build` (private repo; PR #23, draft). Local checks only (CI disabled by the
controller). Papers are not touched (Peter: papers live only locally); these numbers are for the
controller to port.

### 8.1 Shipped-program silence gate (brief step 2)

`proc_build.check_shipped_silence` now runs inside `build_one_circuit`: every shipped program of
the base, clean vs infected: mcu 4 programs, darkriscv 1 prebuilt firmware, picorv32 none in the
checkout (n/a). Odin III RTL and netlist traces must equal clean (gating); iverilog is recorded,
not gating (spec 0a). `gate_pass` requires it. 7 tests in `tests/test_proc_witness.py`.

### 8.2 Build (smallest first: mcu, picorv32, darkriscv)

Agent default (spec gives no split): the 100 logical circuits are split 34 mcu / 33 picorv32 /
33 darkriscv. Each logical circuit is built once (clean twin + infected twin, 1-3 Trojans), then
mapped to gates, lut4 and lut6, clean and infected, each with its own random ABC script
(`obfuscate`). Driver: draws one circuit per slot and stops the whole build at the first gate
failure (it never redraws). Magic-word rejection is by construction of the draw, so redraws: **0**.
Gate failures: **0** of 100. The first driver run lacked the odin3 Python path, so no form was
mapped; its functional gates all passed, it was discarded for the release and rerun (records kept
under `run1-noenv` in the run records).

| base | circuits | Trojans | fire on all 3 engines | neutral silent (RTL, netlist) | neutral silent (iverilog) | neutral-shift silent | shipped silent (RTL, netlist) | FF equal |
|---|---|---|---|---|---|---|---|---|
| mcu | 34 | 62 | 62 | 34 | 34 | 34 | 34 | 34 |
| picorv32 | 33 | 58 | 58 | 33 | 12 | 33 | 33 (n/a: no shipped program) | 33 |
| darkriscv | 33 | 54 | 54 | 33 | 5 | 33 | 33 | 33 |

Recorded, not gating: iverilog differs from clean on the neutral program in 21 of 33 picorv32 and
28 of 33 darkriscv circuits, and on the darkriscv shipped firmware in 19 of 33 (mcu: 0 of 34 on
all 4 programs). Section 4.0/4.1 of round 10 already recorded the four-state `x`; it is not
specific to the Trojans and Odin III's two-state engines agree. FF counts: mcu 1310, picorv32
1615, darkriscv 2034, each equal to the clean twin.

Variety possible per base: ABC script re-draws (18-script catalogue, seeded) on all three forms for
all three bases; dummy cuts not applied this round; ABC `read_blif` of the source netlists still
fails. No duplicate circuits in the release (0 duplicate hashes).

### 8.3 Release

`seeker-proc-v2.0-rc1`: 300 circuits (3 forms x the same 100 logical circuits), ids opaque and
shuffled; answer key separate (labels, provenance, catalogue, clean twins of infected circuits,
secret activation programs); DATASHEET committed under `releases/seeker-proc-v2.0-rc1/`. Per form
n_inf ~ Uniform{10..70} (Seeker-Comb/Seq rule), seeded, kept private. `lemanruss verify` PASS
(integrity, name vocabulary, content leak against the clean twin, no comment lines or inserter
names, label presence, 0 duplicates, latch counts equal). Size 58 MB. SCOAP of the trigger was not
re-measured for rc1; P(match) is 2^-32 per Trojan.

Counts per base, form and kind (kinds are Trojans in released infected circuits):

| base | form | circuits | clean | infected | Trojans reset | stall | alu | 1/2/3 Trojans |
|---|---|---|---|---|---|---|---|---|
| mcu | gates | 34 | 11 | 23 | 12 | 17 | 13 | 10/7/6 |
| mcu | lut4 | 34 | 23 | 11 | 8 | 8 | 6 | 4/3/4 |
| mcu | lut6 | 34 | 22 | 12 | 7 | 8 | 4 | 7/3/2 |
| picorv32 | gates | 33 | 13 | 20 | 7 | 16 | 8 | 12/5/3 |
| picorv32 | lut4 | 33 | 24 | 9 | 5 | 9 | 4 | 2/5/2 |
| picorv32 | lut6 | 33 | 24 | 9 | 4 | 9 | 2 | 4/4/1 |
| darkriscv | gates | 33 | 14 | 19 | 7 | 12 | 8 | 13/4/2 |
| darkriscv | lut4 | 33 | 25 | 8 | 4 | 8 | 3 | 4/1/3 |
| darkriscv | lut6 | 33 | 19 | 14 | 9 | 8 | 5 | 8/4/2 |


Totals per form (clean/infected): gates 38/62, lut4 72/28, lut6 65/35.

### 8.4 Archive

`<archive>/seeker-proc-v2.0-rc1/`, SHA256SUMS verified, README section added,
`tar -d` against source clean. sha256: circuits `904d9832dbf8339c97d9137055ac28a69828069172e982a0fda20a08267a85da`,
answer_key `990e5b97543b1171909be0e9cd7f426f9d32caf8d23290aa2a3abff6188c147d`, full release
`7b51918591177d5c20b2f62d05038a995fc0f3206bb7e5f32b6a7051072da6a4` (first tarball, made with a wrong
`--exclude`, so it holds the answer key too; kept, never deleted), run records
`cf866a43f88b7f772233efdfb1588865755852b65f7a3ed84c8ffe2a1bfafbe0`.

### 8.5 Detectors (round 9 suite, trained on Comb rc5 + Seq rc7 identity forms, `detect.proc.run_proc`)

Headline: **every one of the 300 circuits is `out_of_range` for every detector.** The training FF range
is [0, 210]; Proc circuits have 1310 to 2034 flip-flops (RAM black-boxed, so this is no longer the
per-bit-latch effect of pilot3, the cores are simply far larger than any Comb/Seq training circuit).
Per spec section 6 no circuit is a flag, a miss or in the AUROC, so the strict result is: confusion
matrix empty (all in `out_of_range`: gates 38 clean/62 infected, lut4 72/28, lut6 65/35),
AUROC n/a, labels n/a. Detectors run: size, ffcount, classhist, sanity, gnn-a-nosc, gnn-yasaei.
**Not run / failed**: rare and graphlet-b (every validation score NaN, "validation fold has no clean
circuit"), gnn-a (no graphs built, IndexError); the SCOAP path is the common factor, not diagnosed.
Within-Proc training (train on two bases, test on the third) was not done.

Secondary, extrapolated scores (out-of-range scores used anyway; AUROC pooled over a form, 95%
interval from a bootstrap over only 3 bases, so very coarse; W/L/T is over the 3 bases against the
size control; 1 seed, default GNN budget):

### Detectors, form gates

| detector | AUROC [95% CI over bases] | W/L/T vs size | label | out_of_range (clean/infected) | not scored |
|---|---|---|---|---|---|---|
| size | 0.464 [0.423, 0.647] | control | INCONCLUSIVE | 38/62 | 0 |
| ffcount | 0.452 [0.452, 0.500] | 2/1/0 | INCONCLUSIVE | 38/62 | 0 |
| classhist | 0.474 [0.428, 0.688] | 3/0/0 | INCONCLUSIVE | 38/62 | 0 |
| sanity | 0.454 [0.352, 0.699] | 1/2/0 | INCONCLUSIVE | 38/62 | 0 |
| gnn-a-nosc | 0.512 [0.399, 0.557] | 1/2/0 | INCONCLUSIVE | 38/62 | 0 |
| gnn-yasaei | 0.574 [0.530, 0.672] | 2/1/0 | ABOVE CHANCE | 38/62 | 0 |

### Detectors, form lut4

| detector | AUROC [95% CI over bases] | W/L/T vs size | label | out_of_range (clean/infected) | not scored |
|---|---|---|---|---|---|---|
| size | 0.516 [0.494, 0.670] | control | INCONCLUSIVE | 72/28 | 0 |
| ffcount | 0.455 [0.454, 0.500] | 1/2/0 | INCONCLUSIVE | 72/28 | 0 |
| classhist | 0.531 [0.521, 0.705] | 3/0/0 | ABOVE CHANCE | 72/28 | 0 |
| sanity | 0.483 [0.450, 0.620] | 1/2/0 | INCONCLUSIVE | 72/28 | 0 |
| gnn-a-nosc | 0.485 [0.450, 0.597] | 2/1/0 | INCONCLUSIVE | 72/28 | 0 |
| gnn-yasaei | 0.556 [0.525, 0.597] | 2/1/0 | ABOVE CHANCE | 72/28 | 0 |

### Detectors, form lut6

| detector | AUROC [95% CI over bases] | W/L/T vs size | label | out_of_range (clean/infected) | not scored |
|---|---|---|---|---|---|---|
| size | 0.473 [0.360, 0.549] | control | INCONCLUSIVE | 65/35 | 0 |
| ffcount | 0.534 [0.457, 0.577] | 3/0/0 | INCONCLUSIVE | 65/35 | 0 |
| classhist | 0.504 [0.402, 0.584] | 2/1/0 | INCONCLUSIVE | 65/35 | 0 |
| sanity | 0.478 [0.418, 0.658] | 3/0/0 | INCONCLUSIVE | 65/35 | 0 |
| gnn-a-nosc | 0.524 [0.510, 0.586] | 3/0/0 | ABOVE CHANCE | 65/35 | 0 |
| gnn-yasaei | 0.480 [0.418, 0.628] | 3/0/0 | INCONCLUSIVE | 65/35 | 0 |


Reading (counts first): the size control sits at 0.46 to 0.52. Four cells carry an interval above
0.5: gnn-yasaei gates 0.574 [0.530, 0.672] (W/L/T 2/1/0) and lut4 0.556 [0.525, 0.597] (2/1/0),
classhist lut4 0.531 [0.521, 0.705] (3/0/0), gnn-a-nosc lut6 0.524 [0.510, 0.586] (3/0/0); the
other 14 cells are INCONCLUSIVE. These are extrapolations on 3 bases, so the strict label stays
n/a. H-P2 as worded (no detector beats the size control with an interval above 0.5 on any form) is
therefore **not supported on the extrapolated scores** (weak signal, 0.52 to 0.57), and **untestable
strictly** because every circuit is out of range.

### 8.6 H-P1 / H-P2 verdicts

- H-P1 (amended, spec 0a): **supported**, 100 of 100 logical circuits (300 of 300 released) pass all gates,
  0 redraws, 0 failures. The iverilog neutral-program difference is recorded, not a failure.
- H-P2: strict **untestable** (all out of range); extrapolated **not supported** (four weak cells above 0.5).
- Open for the controller: a Proc-trained or size-matched detector protocol; GNN SCOAP path in this
  environment; dummy cuts for more variety; SCOAP re-measure of the triggers.
