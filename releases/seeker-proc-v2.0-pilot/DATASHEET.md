# Seeker-Proc v2.0-pilot (Leman Russ III round 7, 2026-11-01)

Pilot only (brief: "do not claim v1's taxonomy or numbers"). Three processor Trojans on the two processors Odin III already runs end to end
(`tests/mcu`, `tests/darkriscv`). Built at Odin III main 0d3d735a.

## What this release holds

A circuit here is one patched RTL source file plus a witness program image, not a BLIF catalogue
entry (the upstream design is never redistributed, per CLAUDE.md): `circuits/<trojan-id>/` holds
the patched file (`single_cycle_core.v.gz` or `darkriscv.v.gz`) and the witness image(s)
(`<n>witness.vmh.gz` for mcu's 4 byte planes, `witness.mem.gz` for darkriscv's word file). Every
identifier the patch itself introduces (`__htl_trigger`, `__htl_pc_mux`, `__htl_seq_state`, ...)
is replaced by a neutral `_insN` name (`answer_key/renames.json` holds the map). `manifest.json`
carries base, patched-file name and sha256 only -- no trigger/payload kind, no magic word.

## Bases and licences

- mcu: Arduino-on-RISC-V (`external/Arduino-on-RISC-V`, `quartus_project_revert_timer`); licence
  as recorded by the upstream repository (not re-stated here; "licence unread" per the house rule
  for a source this round did not re-check).
- darkriscv: DarkRISCV (`external/darkriscv`, commit `9555119`, the commit `tests/darkriscv/
  run.sh` pins); licence as recorded by the upstream repository.

## Trojans

| id | base | trigger | payload | magic bits | p(match) |
|---|---|---|---|---|---|
| proc-mcu-magicword-stall | mcu | t-input-pattern (1 word) | p-dos-stuck (fetch_issue's own stall encoding) | 32 | 2^-32 |
| proc-mcu-magicseq3-stall | mcu | t-seq-pattern (3 words, in order) | p-dos-stuck | 96 | 2^-96 |
| proc-dark-magicword-reset | darkriscv | t-input-pattern (1 word) | p-dos-reset (the core's own XRES) | 32 | 2^-32 |

Rareness (SCOAP CC0/CC1/CO of the trigger net, Odin III `scoap`) and the per-program stealth
results are in `answer_key/rareness.json` and docs/results-round7.md (lemanrussIII, not in this
release). Summary: all three Trojans are silent on every shipped program checked (mcu: blink,
blink_interrupt, blink_function_call, interrupt; darkriscv: the prebuilt firmware) and fire on
their own witness program, agreeing across iverilog, Odin III RTL `sim_tb` and Odin III netlist
`sim_tb`.

## Equivalence (trigger forced inactive)

Both bases `lower` their RAM/BRAM arrays to tens of thousands of per-bit latches with no target
architecture in this round (no `read_arch`, per the brief's "no VPR"). `tools/equiv-check`'s ABC
`dsec` is **unproven** on both: mcu timed out at the 300 s wrapper used to measure it, darkriscv
at ABC's own 600 s internal limit. Neither is a pass or a fail (measured once per base, on the
magic-word Trojan; the magic-sequence Trojan on mcu adds only a small FSM on top of the same
core and is expected to hit the identical RAM-latch-driven timeout, not separately measured).

## Deferred this round

Error-insertion payloads (`p-err-hi`/`p-err-lo`), netlist-level insertion, and anything beyond
`t-input-pattern`/`t-seq-pattern` triggers: out of this pilot's scope (time-boxed), recorded as a
deferred axis in docs/specs/2026-10-31-htl-design.md section 12, not attempted.
