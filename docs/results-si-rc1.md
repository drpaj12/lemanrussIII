# Seeker-Si rc1: 100 standard-cell circuits (2026-11-06)

Purpose: Leman Russ III RQ1.1 (which structures do not belong to the claimed design) at the standard-cell level, the form a fab or a scanned chip is checked in (spec `docs/specs/2026-11-05-seeker-si.md`). Measure: a gated release of 100 circuits with a hidden clean/infected mix. Release: `releases/seeker-si-v2.0-rc1/` (datasheet, manifest). Peter's go: 2026-11-05.

**Seeker-Si is a NEW set. Its bases are OpenCores designs mapped to sky130_fd_sc_hd standard cells. It is not the same benchmarks as Seeker comb/seq/proc; do not compare per base, per form or by AUROC with those sets.**

## Result

100 circuits (34 clean, 66 infected with 103 Trojans) on three bases, all through the full gate. No detector was run except the `ffcount` control. Answer key, circuits and seed stay off GitHub (circuits and key archived on F:, see the PR).

| base | cells in the base netlist | clean | infected (1 / 2 / 3 Trojans) | Trojans |
|---|---|---|---|---|
| mmuart | 408 cells + 96 FF | 12 | 22 (14 / 4 / 4) | 34 |
| simple_spi | 555 cells + 130 FF | 11 | 22 (13 / 6 / 3) | 34 |
| verilog_cordic_core | 6784 cells + 750 FF | 11 | 22 (12 / 7 / 3) | 35 |
| total | | 34 | 66 | 103 |

Infected count drawn uniformly from 10 to 70 once for the release (66), spread evenly over the bases (22 each); 1 to 3 Trojans per infected circuit (P = 0.5, 0.3, 0.2). Trigger kinds in the 103 Trojans: counter 51, FSM pattern 52; payloads: stuck 56, flip-high 27, flip-low 20. Rare AND-tree triggers were not drawn (the sequential draw of the Seq family was reused). Every trigger kind that was drawn is kept.

## Bases and what was left out

Set bases: mmuart, simple_spi, verilog_cordic_core (34 / 33 / 33). The gate cost and yield of each candidate:

- **des**: passed the one-circuit check (clean circuit 14 s, whole clean+1 Trojan check 217 s, 460 MB peak). In the build, yield failed: with the design's own testbench as silence reference, 2 of 11 one-Trojan draws passed and **0 of 25 two-Trojan draws**; the 3-Trojan share would be worse. Dropped; the circuits it produced are not in the set.
- **i2c**: left out. 0 of 80 consecutive one-Trojan draws passed the silence rule (38 no-PASS, 28 trace differs, 13 hang, 1 Verilog round trip unproven, which is fixed since): the i2c testbench runs 165835 cycles through nearly every net. An i2c share would be clean-only, so the base would give away the label.
- **wb_lcd**: out (equivalence UNDECIDED). **sha3_low**: out (silicon tail still running, too large).
- simple_spi was not in the ladder rerun; its `gates.blif` is from the first ladder (equivalent there) and every circuit here was re-proved by the gate.
- 25 per base from an earlier build (4 bases, including des) were discarded when des was dropped; that build had an unsorted-port trace bug (see below) and is not counted here.

## Gate (per circuit)

| step | result |
|---|---|
| format (one module, no duplicate ports, no driven input, no multi-driven net, Odin III `read_blif`) | 100 of 100 |
| equivalence to source: `regmatch-cec` / `scorr-cec` / `dsec` | 100 / 0 / 0 (mmuart 34, simple_spi 33, verilog_cordic_core 33 by regmatch-cec) |
| `pre` with triggers forced off equals the base | 66 of 66 |
| every Trojan fires on its witness, replayed on the finished netlist | 103 of 103 |
| Verilog read back = the BLIF network (structural proof, ABC cec as fallback) | 100 of 100 |
| design testbench on the cell netlist, flip-flops at 0: PASS line, and output trace equal to the clean circuit's | 100 of 100 |
| leak scan of the circuit files (`htl`, `trojan`, `$`, attributes, comments) | none |

Silence: the trace is the design-under-test's output ports (sorted by name) sampled with `$strobe` at each rising edge; mmuart 94433 cycles, simple_spi 51722, cordic 220. Compared as a digest with the clean reference of the same base. A draw whose simulation runs longer than 4 times the clean one plus 30 s is a hang and counts as testbench-fires.

## Rejections (draws replaced; infected draws only, clean circuits had none)

| base | draws rejected | testbench fires the Trojan (silence rule) | no witness | accepted infected |
|---|---|---|---|---|
| mmuart | 31 | 30 | 1 | 22 |
| simple_spi | 61 | 60 | 1 | 22 |
| verilog_cordic_core | 4 | 4 | 0 | 22 |
| total | 96 | 94 | 2 | 66 |

Silence rejections by trigger kind (a draw with two kinds counts once for each): mmuart counter 26, pattern 20; simple_spi counter 49, pattern 49; cordic counter 2, pattern 3. Kinds in all draws (rejected and accepted): mmuart counter 44, pattern 38; simple_spi 69, 64; cordic 17, 23. By reason: 75 no PASS from a 0 start, 15 hang, 4 trace differs. Equivalence, fire and forced-off checks rejected nothing in this build.

**Bias:** the rule keeps only Trojans the design's own testbench does not reach, so the set leans to Trojans that testbench-style stimulus does not excite. The rejection rate depends on how thoroughly the testbench exercises the base (cordic 4 rejections for 22 infected circuits; simple_spi 61). This is stated in the datasheet and the manifest notes too.

## Flip-flop counts (the label leaks)

Every Trojan trigger here is sequential, so every infected circuit has more flip-flops than the clean ones of its base. Clean circuits all have the base count (the ABC mapping keeps every flip-flop). Counted from the `dfxtp_1` cells in the shipped `.v`, equal to the BLIF `.latch` count in all 100.

| base | base / clean FF | 1 Trojan: n, FF range | 2 Trojans | 3 Trojans |
|---|---|---|---|---|
| mmuart | 96 | 96 | 14: 98 to 104 | 4: 102 to 109 | 4: 107 to 119 |
| simple_spi | 130 | 130 | 13: 132 to 135 | 6: 135 to 142 | 3: 141 to 146 |
| verilog_cordic_core | 750 | 750 | 12: 753 to 759 | 7: 762 to 767 | 3: 767 to 775 |

`ffcount` control (rank by flip-flop count, equal to the log(1+FF) detector in `lemanruss/detect/ffcount.py`): AUROC 1.000 on mmuart, 1.000 on simple_spi, 1.000 on verilog_cordic_core, 0.676 pooled (pooled is lower only because the bases differ in size). A detector scored per base can read the label from the flip-flop count; this set therefore measures more than that count only if a detector is judged against `ffcount`.

## Cost

Final builds, wall: mmuart 163 s, simple_spi 723 s, verilog_cordic_core 442 s (22 minutes); peak RSS of the largest child 173 MB (cordic), 75 and 68 MB for mmuart and simple_spi, python parent 169 MB at most. Run under `heavy-run` (one slot; queueing for the slot was longer than the builds). Exploratory runs (checks, the discarded 4-base build, the i2c and des probes) added about 3 hours of wall, mostly des and i2c rejections.

## Method notes and bugs found on the way

- The trace order depended on the shuffled port order of each circuit; it is now sorted by name. Before the fix, equivalent clean circuits failed against each other and the first 4-base build was thrown away.
- `$display` at the clock edge races the flip-flop update; `$strobe` (one net) is used.
- A hung simulation (a Trojan stalling the testbench) is cut off by a timer; the earlier code waited for output and could hang the build.
- Verilog round trip: ABC cec on the sequential cordic netlists returned unproven; the writer's truth-table match makes the two networks identical, so the check is now a structural comparison (`si_cells.same_network`), with ABC as fallback.
- Silence now requires the clean reference to pass its testbench from a 0 start; a simulation with no trace line is an error (an earlier edit let 0-cycle traces pass vacuously for one run, which was found and discarded).
