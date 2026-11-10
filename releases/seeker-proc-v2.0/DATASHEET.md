# seeker-proc-v2.0 datasheet

Family: Seeker-Proc. Version 2.0 (supersedes rc3 and the Si rc2 processor set). Produced by Leman Russ III (Yggdrasil III). Defensive hardware-Trojan detection research; the circuits are Trojans to detect, nothing here is meant to be deployed.

## Contents

1,200 circuits: three processor cores, each with four SeekerSets of exactly 100 circuits: gates (AND/OR/NOT), lut4 (K4), lut6 (K6) and silicon (sky130_fd_sc_hd standard cells, with cell Verilog in `circuits_v/`). A random 10 to 70 of each 100 are infected with 1 to 3 Trojans (P = 0.5, 0.3, 0.2); a detector is not told which. Ids are opaque and shuffled. Answer key in `answer_key/` (labels, provenance, catalogue, clean twins, activation programs); a detector must not read it.

| core | gates inf/clean | lut4 inf/clean | lut6 inf/clean | silicon inf/clean |
|---|---|---|---|---|
| BRISC-V mcu (Arduino-on-RISC-V, MIT) | 21 / 79 | 57 / 43 | 18 / 82 | 27 / 73 |
| OpenCores mips_16 (16-bit, 5-stage) | 62 / 38 | 48 / 52 | 28 / 72 | 50 / 50 |
| PicoRV32 (YosysHQ, ISC) | 27 / 73 | 49 / 51 | 36 / 64 | 62 / 38 |

The benchmark key of the BRISC-V mcu (Arduino-on-RISC-V) is `mcu`.

## Origin of the circuits

| core | rc3 logical circuits kept | Si rc2 logical circuits kept | rc3 failed the four-state gate | Si rc2 failed | new logical circuits built |
|---|---|---|---|---|---|
| mcu | 34 | 34 | 0 of 34 | 0 of 34 | 66 |
| mips_16 | 33 | 33 | 0 of 33 | 0 of 33 | 67 |
| picorv32 | 10 | 7 | 23 of 33 | 26 of 33 | 93 |

Circuits kept from rc3 and Si rc2 keep their bytes; their ids are unchanged (rc3) or new (Si rc2). Each circuit that failed the four-state gate was replaced by a new draw of the same core with the same Trojan count; the number of infected circuits per cell was then drawn once from the values 10..70 that the kept circuits allow. For the record (paper): darkriscv, dropped below, failed 12 of 33 (rc3) and 19 of 33 (Si rc2).

## Dropped core: darkriscv

darkriscv is not part of v2.0. Its reset and stall Trojans locked a register that has no reset (the registered instruction) at the unknown value x under four-state simulation, so a clean core and an infected core differed in the very first cycles for a reason a detector could read off the simulation, not off the structure; and the program prefetch past the end of a program read uninitialised memory, which put x into the trigger comparator. The maintainer dropped the core rather than redesigning its Trojans.

## Odin III build and simulation

One Odin III build for all Proc circuits and gates: Odin III 1.6.0 (`build/rel-v160`, commit d0649167, four-state simulation by default), with iverilog as the second four-state engine. Earlier Odin III builds (rel-main3, Odin 1.4) simulate two-state with all registers at zero and hid the unknown-value problem above.

## Trigger masking rule (v2.0)

Every Trojan trigger is masked while the core's own reset is active: `trigger_eff = trigger & ~reset_active`, with the core's own reset net and polarity (mcu `reset`, mips_16 `rst`, picorv32 `!resetn`). The host's hold logic then sees its original signals during reset and its registers load known values. picorv32's reset and stall triggers additionally read the instruction bus in the cycle the fetch is valid (`mem_valid && mem_ready && mem_instr`) instead of the register `next_insn_opcode`, which is x until the first fetch completes; its alu trigger still reads `next_insn_opcode`. No flip-flop is added by any Trojan (hard gate per circuit).

## Gates every logical circuit passed

Strict four-state: flip-flop equality with the clean twin; each Trojan's activation program changes the trace on iverilog, Odin III RTL and Odin III netlist simulation; the neutral program, a non-magic shift-right (alu Trojans) and every shipped program of the core give traces equal to the clean twin on all three engines, where an x or z in the infected trace against 0 or 1 in the clean one is a failure (the traces are compared as exact text); the release gate of rc2 on every mapped file (one flat model, equivalent to the lowered netlist); for silicon, the mapped flip-flop count equals the netlist count and every Trojan fires and the neutral stimuli stay silent on the silicon netlist itself. The gate was applied to every circuit, including the kept rc3 and Si rc2 circuits (re-run with the unmasked construction they were built with). The program images in the test harness are padded with 64 NOPs after the final self-loop so that the prefetch never reads an undefined word.

## Neutral stimulus (public)

Per core, `stimulus/neutral-program.hex`: the neutral program of the gates (no magic word). On Odin III 1.6.0 netlist simulation every infected circuit of the core, in every form, gives a trace equal to a clean circuit of the same form: mips_16: gates 62 infected, 0 differing, lut4 48 infected, 0 differing, lut6 28 infected, 0 differing, silicon 50 infected, 0 differing; mcu: gates 21 infected, 0 differing, lut4 57 infected, 0 differing, lut6 18 infected, 0 differing, silicon 27 infected, 0 differing; picorv32: gates 27 infected, 0 differing, lut4 49 infected, 0 differing, lut6 36 infected, 0 differing, silicon 62 infected, 0 differing. Which circuits it was checked against stays in the key.

## Bases

- BRISC-V mcu (Arduino-on-RISC-V): MIT.
- PicoRV32 (YosysHQ), default parameters (no multiplier, divider or IRQ): ISC.
- OpenCores mips_16: 16-bit instruction words (match probability 2^-16 per random instruction), do-not-care values resolved to 0, memories black-boxed.

## Check

`sha256sum -c SHA256SUMS`, then `lemanruss verify <dir>` (runs the Proc release check).
