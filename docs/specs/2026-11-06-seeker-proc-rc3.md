# Seeker-Proc rc3: a fourth base, mips_16 (2026-11-06)

Purpose (hub docs/purpose.md, Leman Russ III, processor family; RQ1.1 at processor level).
Peter 2026-11-06: "add 8 [mips_16 as a 4th Proc base]". Measure: release gates (functional gates
of rc1/rc2 plus the rc2 release gate), detector leave-one-base-out on four cores with the
flip-flop range check, levels 1 to 3 (CAD reporting convention: geomean/W-L-T first, then label).

## Why
The outside-the-training-range test and processor level 3 need at least four cores, one smaller
than the smallest (mcu) and one larger than the largest (darkriscv). mips_16 (268 flip-flops after
the memories are taken out) is smaller than mcu (1,310).

## The base
OpenCores `mips_16` (`external/opencores/mips_16/rtl`, 16-bit data and instruction words, 5-stage
pipeline, 13 instructions, 8 registers, instruction ROM and data RAM inside). The build patches a
scratch copy (never committed) in `lemanruss/htl/mips16.py`:
1. Deterministic variant: `ALU_NC` (`3'bxxx`) becomes `3'b000`; the first ALU case arm
   (`ALU_NC: r = 16'bx`, which matches every command in synthesis and folds the datapath, the
   Mimir row note) is removed; the decoder `1'bx` don't-cares (including the XOR operand select)
   become `1'b0`; `CODE_FOR_SYNTHESIS` is defined. Four-state iverilog and the two-state Odin III
   simulator then agree on every program.
2. ROM and RAM become ports (`imem_instruction`, `dmem_*`), modelled in the hand-written
   `mips_tb.v`; three write-back observation ports keep the datapath alive. Memories are black
   boxes in all three forms, as for the other bases.

## Trojans
Trigger: the 16-bit instruction register `instruction_reg` of `ID_stage` equals a per-Trojan magic
word (a register-writing ALU or ADDI instruction with a destination r1..r7, about 7,000 words;
match probability 2^-16 per random instruction). Payloads: reset (program counter restarts at 0),
stall (fetch and decode frozen), alu (bit 0 of a shift-right result flips; its magic word is the
instruction after the shift-right, because the register already holds the next word while the
shift is in the execute stage, as for picorv32). No flip-flop is added (hard gate per circuit).
Witness programs are hand-assembled; the activation program is in the answer key only. Rejection
rule: a magic word never equals a word of the project's shipped programs (`test1`, `test2`) or a
scaffold word. Shipped programs `test1` and `test2` are run clean vs infected as silence gates on
Odin III RTL and netlist (iverilog recorded).

## Release
rc3 = the 100 logical rc2 circuits (mcu 34, picorv32 33, darkriscv 33) plus 33 mips_16 circuits =
133 logical circuits x 3 forms = 399. Clean/infected draw per form, ids, shuffle: redrawn with new
secret seeds. Regions and levels: scoring spec section 9a.
