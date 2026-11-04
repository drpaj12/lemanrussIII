# seeker-proc-v2.0-pilot2 datasheet

Family: Seeker-Proc. Version 2.0-pilot2 (fix round, 2026-11-01; supersedes seeker-proc-v2.0-pilot, which leaked circuit/trojan identity through directory names and manifest keys even though file content was leak-scanned clean -- see README entry and docs/results-round7.md section 7). Produced by Leman Russ III (Yggdrasil III).

Purpose: defensive hardware-Trojan detection research. The circuits are Trojans to detect, built with the Hardware Trojan Library; nothing here is meant to be deployed.

## Contents

- circuits: 6 in `circuits/<id>.blif.gz` (gzip, zero timestamp), opaque ids (`pp0001`, ...); clean and infected, one trojan per base pair (proc-dark-magicword-reset, proc-mcu-magicseq3-stall, proc-mcu-magicword-stall).
- form: the lowered netlist only (`read_verilog; proc; opt; lower; write_blif --gates-as-names`), identity (unrestructured). No ABC-restructured form is released this round: every one of the 18 forms fails at ABC's `read_blif` before the restructuring-specific commands run (restructure_attempts.json; see DATASHEET section below).
- answer key: `answer_key/` (labels, provenance, renames, rareness, catalogue, the patched RTL under `patches/`, the witness program image under `witness/`); a detector must not read it. Clean circuits carry no label and infected circuits carry no label in `circuits/` or `manifest.json`.

## Restructuring attempts (brief item (c))

- proc-dark-magicword-reset (clean): `strash` -- abc-failed, 36s: Network "darksocv" contains combinational loop! Box "n2788" encountered twice on a path to the COs
- proc-dark-magicword-reset (infected): `strash` -- abc-failed, 50s: Network "darksocv" contains combinational loop! Box "n2788" encountered twice on a path to the COs
- proc-mcu-magicseq3-stall (clean): `strash` -- abc-failed, 531s: Cannot find the model for subcircuit single_cycle_core$RESET_PC
- proc-mcu-magicseq3-stall (infected): `strash` -- abc-failed, 532s: Cannot find the model for subcircuit single_cycle_core$RESET_PC
- proc-mcu-magicword-stall (clean): `strash` -- abc-failed, 290s: Cannot find the model for subcircuit single_cycle_core$RESET_PC
- proc-mcu-magicword-stall (infected): `strash` -- abc-failed, 532s: Cannot find the model for subcircuit single_cycle_core$RESET_PC

Every attempt above failed at ABC's own `read_blif` (before any restructuring-specific command runs), so the same outcome applies to all 18 forms without repeating it 18 times per circuit (brief: "a stated subset" is allowed when wall time does not): darkriscv's lowered netlist has a genuine sequential loop ABC's reader refuses; mcu's lowered netlist has Odin III's own deeply parameterized hierarchical module names (`$RESET_PC=32'b0...`, `$h<hash>`), which ABC's BLIF reader mis-parses at the `$`/`='` characters when resolving a `.subckt` box. Neither is an Odin III bug (not changed here); recorded for the controller.

## Names

Every net the inserter added is renamed to a neutral name in the style of the circuit's own clean twin (`lemanruss.htl.release.scrub_group`, the same mechanism the Seeker-Comb/Seq families use); `answer_key/renames.json` maps them back. No directory name, file name or manifest key carries the label vocabulary (`proc_release.NAME_VOCAB`); `lemanruss.htl.proc_release.check_name_vocabulary` checks this directly.

## Fetch and check

`sha256sum -c SHA256SUMS`, then `lemanruss.htl.proc_release.verify_proc_pilot2`.
