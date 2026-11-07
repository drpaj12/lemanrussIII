# seeker-proc-v2.0-rc3 datasheet

Family: Seeker-Proc. Version 2.0-rc3. Produced by Leman Russ III (Yggdrasil III). Defensive hardware-Trojan detection research; the circuits are Trojans to detect, nothing here is meant to be deployed.

## What it is

399 circuits: the same 133 logical circuits in three forms (gates: AND/OR/NOT gate netlist; lut4 and lut6: ABC `if` mapped to 4- and 6-input LUTs), each form a gzip BLIF (`circuits/<id>.blif.gz`, zero timestamp, no comment lines). Ids are opaque and shuffled across forms and bases. A detector is not told whether a circuit is infected.

| form | clean | infected |
|---|---|---|
| gates | 102 | 31 |
| lut4 | 83 | 50 |
| lut6 | 108 | 25 |

Per form the number of infected circuits is drawn once, uniformly from 10 to 70, as Seeker-Comb and Seeker-Seq do; the rest are clean variants. An infected circuit carries 1 to 3 Trojans (P = 0.5, 0.3, 0.2).

## Bases (open source, no flip-flop added by any Trojan)

| base | licence | flip-flops | logical circuits |
|---|---|---|---|
| darkriscv | BSD 3-Clause (darkriscv) | 2034 | 33 |
| mcu | MIT (Arduino-on-RISC-V) | 1310 | 34 |
| mips_16 | OpenCores mips_16 (16-bit, 5-stage; x don't-cares resolved to 0, memories black-boxed) | 268 | 33 |
| picorv32 | ISC (YosysHQ picorv32, default parameters: no multiplier, divider or IRQ) | 1615 | 33 |

mips_16 is the OpenCores 16-bit, 5-stage core with its do-not-care values resolved to 0 (`ALU_NC`, the decoder `1'bx` values and the first ALU case arm that matched every command), so that four-state and two-state simulators agree; its ALU Trojan's magic word is the instruction after a shift-right.

Memories are black-box hard blocks in all three forms, so flip-flop counts are the cores' own (not per-bit RAM latches). Infected and clean twins have equal flip-flop counts (hard gate, per circuit).

## Triggers and payloads

Trigger: a 32-bit magic word on the core's instruction register (mcu `instruction`, single cycle; darkriscv `XIDATA`, its registered instruction; picorv32 `next_insn_opcode`; mips_16 `instruction_reg`, a 16-bit word, so a mips_16 Trojan's random-match probability is 2^-16 per instruction, not 2^-32). Payload kinds: reset DoS, stall DoS, and ALU data corruption (flip the LSB of a shift-right result). RV32I has no rotate instruction. Each Trojan has its own random legal word; words equal to a word of a shipped program image or of a witness scaffold are never drawn. The activation programs are in the answer key only.

## Variety

Each logical circuit is one (base, Trojan draw) built once, then mapped per form with its own random ABC script from the 18-script catalogue (`obfuscate`), clean and infected separately. Odin III's in-process ABC path is used; ABC `read_blif` on the source netlists fails on these cores. Dummy cuts were not applied.

## Gates every circuit passed

Release gate (rc2): every file is one flat `.model`, declares no port twice, drives no net twice, is read by Odin III `read_blif`, and is equivalent (ABC) to the lowered netlist it was mapped from. rc1 lacked this and its darkriscv and mcu files were malformed (several `.model` sections merged); rc1 is superseded.

Flip-flop equality with the clean twin; every Trojan's activation program changes the trace on iverilog, Odin III RTL and Odin III netlist simulation; Odin III RTL and netlist traces equal the clean twin's on the neutral program, on a non-magic shift-right (ALU Trojans) and on every shipped program of the base (mcu: 4, darkriscv: 1, picorv32: none in the checkout). iverilog is recorded on shipped programs, not gating (four-state `x` difference on darkriscv, spec section 0a).

- gate pass (circuits): mips_16 33, mcu 34, picorv32 33, darkriscv 33
- redraws: 0 (a gate failure would have stopped the build)
- history: rc3 = the rc2 circuits of the three RISC-V bases plus a fourth base, mips_16 (16-bit instruction words; Trojan words are 16 bits, match probability 2^-16 per random instruction). Labels and ids are redrawn with new secret seeds.

## Out of range

A detector's score on a circuit whose flip-flop count lies outside the detector's own training range is reported `out_of_range`, never as a flag.

## Check

`sha256sum -c SHA256SUMS`, then `lemanruss.htl.proc_rc1_release.verify_proc_rc1`.
