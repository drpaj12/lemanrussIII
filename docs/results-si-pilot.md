# Seeker-Si pilot: 3 circuits on mmuart (2026-11-05)

Purpose: Leman Russ III RQ1.1 at the standard-cell level (spec `docs/specs/2026-11-05-seeker-si.md`).
Measure: does one clean and two infected mmuart cell netlists pass the release gate. **Seeker-Si is a
new set with its own bases (OpenCores designs mapped to sky130_fd_sc_hd). It is not the same
benchmarks as Seeker comb/seq/proc; do not compare per base.** Aggregates only: no seeds, magic words
or witnesses here.

## Setup

- Base: mmuart, `flow/gates.blif` of the silicon-fix ladder rerun (408 cells, 96 flip-flops).
- Odin III: `odin3/build/rel-main3` (not rebuilt). Mapping per circuit: random ABC script, then
  `read_techlib lib/sky130hd.o3lib; read_blif; abc --gates sky130hd --script S; dfflibmap sky130hd;
  write_blif --gates-as-names` (the silicon flow's `map` step with its default ABC script replaced).
  Then `finalize` (shuffle, `n<index>` renames). New code: `obfuscate` kind `silicon`,
  `lemanruss/htl/si_cells.py` (Verilog writer and reader), `lemanruss/htl/si_build.py` (pilot driver
  reusing `n200.BaseBuild` / `n200.build_pre`; trigger and payload draws as Seeker-Seq with the
  energy and slowdown payloads dropped).
- Verilog route: truth-table match of each cover against the o3lib (spec section 4 step 6), not
  `write_verilog`, which carries the design's paths and names.
- Run under `ODIN3_HEAVY_OK=1 tools/heavy-run`, slot 0. Seed from a private file, not committed.

## Gate per circuit (all three passed; 5 infected proposals were rejected and redrawn)

| circuit | label | Trojans | cells | FF (golden 96) | Trojans fire (Odin III replay of the finished netlist) | equivalence engine | forced-off vs golden | Verilog round trip | iverilog, sky130 models, 0-start |
|---|---|---|---|---|---|---|---|---|---|
| si0202 | clean | 0 | 392 | 96 | n/a | regmatch-cec | n/a | equivalent | PASS, reference trace |
| si0005 | infected | 1 (counter trigger, output flip) | 412 | 101 | 1 of 1 | regmatch-cec | equivalent | equivalent | PASS, trace equal to clean |
| si0055 | infected | 2 (pattern triggers, output flip and stuck) | 412 | 106 | 2 of 2 | regmatch-cec | equivalent | equivalent | PASS, trace equal to clean |

Gate steps as the spec: one `.model`, no duplicate ports, no driven input, no multi-driven net; Odin III
`read_blif`; equivalence of the finished netlist to its source (`pre` for infected, golden for clean)
by `regmatch-cec` for all three (no `scorr-cec` or `dsec` fallback needed); `pre` with triggers forced
off equivalent to the golden; each Trojan's witness replayed on the finished netlist; the cell Verilog
read back and proven equivalent to the BLIF; the design's testbench run on the cell Verilog with the
sky130 models and every flip-flop starting at 0, printing PASS, and the 94433-cycle output trace
(csr_do, rx_irq, tx_irq, uart_tx at each clock edge) identical to the clean circuit's. Distinctness by
structural signature. Leak scan of the circuit files: no `htl`, no `$` names; port names are the
design's interface (csr_*, uart_*, sys_*).

Rejected proposals (5 of 7 infected draws): "testbench did not print PASS (0-start)", i.e. the
Trojan fired on the design's own testbench stimulus (dos-stuck or flip on a read-data output). That
is the silence gate working; those are redrawn, not shipped. This biases infected circuits toward
Trojans whose trigger the testbench does not reach, as for the other sets.

## Findings and risks

- **FF count differs by label**: 96 clean, 101 and 106 infected (counter and pattern triggers add
  flip-flops). A detector can read this; ffcount is the control for it, as in the Seq set. The
  spec's FF equality is not a gate for sequential-trigger Trojans; recorded per circuit.
- Mapping shrinks the design (408 covers to 353 gates in the first trial); ABC keeps all 96 flops.
- mmuart `final.v` from the flow has x-pessimism at X start; the testbench passes only from a 0
  start, so silence is judged on the 0-start trace.
- Only the testbench stimulus is used for silence on mmuart; no synthetic neutral vectors yet.
- Only mmuart, the smallest base, was exercised. Larger bases untested (spec section 3).

## Cost

Whole pilot (3 circuits, 5 rejected draws, every gate step): 30.9 s wall; peak RSS 78 MB (python
process) and 76 MB for the largest child. Per circuit 2 to 4 s of gate time.

Release metadata: `releases/seeker-si-v2.0-pilot/` (manifest without labels or seed, SHA256SUMS,
DATASHEET). Circuits stay under `work/si2-run/p1` until Peter decides the full set.
