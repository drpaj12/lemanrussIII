# Leman Russ III: Hardware Trojan Library (HTL)

Leman Russ III builds a defensive benchmark generator: Hardware Trojans (HTL), inserted at HDL
and netlist level on Odin III, with Seeker's Dilemma style (clean + infected) benchmark sets for
hardware Trojan detection research. This is defensive research (Trust-Hub / Seeker's Dilemma
style), not a deployment tool.

Full design: `docs/specs/2026-10-31-htl-design.md` (literature, taxonomy, the trigger/payload
model, insertion, verification). Status and next step: `docs/plans/2026-10-31-htl-plan.md`.

## Features at a glance

The full table, with status (works, released, in progress) and code locations, is in the repository
`README.md`. In short: the HTL (triggers, payloads, composition); HDL and netlist insertion; Seeker-Comb
and Seeker-Seq v2.0 families with obfuscation and release gates; releases (Comb rc4, Seq rc5, Proc
pilot2) with datasheets and rareness reports; detector baselines (size-only, rare-signal, graphlet drift,
GNNs); a submission format and scorer (hosting not decided). In progress: cut-and-stitch.

## Quick start

    python3 -m venv .venv && .venv/bin/pip install -e . --no-deps
    export ODIN3_ROOT=<odin3 checkout> ODIN3_LIB=$ODIN3_ROOT/build/release/libodin3.so
    export PYTHONPATH=$ODIN3_ROOT/plugins/python

    .venv/bin/lemanruss build --base-dir tests/fixtures --out work/htl-out

Prints a results table (fires / equivalent / activation probability per Trojan, failures with
reasons) and writes `work/htl-out/manifest.json` (the catalogue) and `work/htl-out/labels.json`
(the answer key, kept separate -- a detector must never be pointed at `labels.json`).

## What is in the HTL

- **Triggers** (`lemanruss.htl.triggers`): combinational rare-value AND, sequential counter
  (time-bomb), sequential pattern (FSM), always-on, input-pattern.
- **Payloads** (`lemanruss.htl.payloads`): denial of service (stuck output, forced reset), error
  insertion (flip/force high or low bits of a word), energy (a toggling ring), slow-down (a delay
  chain).
- **Composition** (`lemanruss.htl.trojan`): `compose(trigger, payload, level, site)` builds a
  `Trojan`, refusing an illegal pairing (a functional payload needs a real trigger, not
  always-on).
- **Insertion**: `lemanruss.htl.insert_netlist` edits BLIF text (needs `write_blif
  --gates-as-names`); `lemanruss.htl.insert_hdl` edits Verilog text. Both re-validate through
  Odin III (`lemanruss.htl.odin_check`).
- **Site selection**: `lemanruss.htl.blif_sim` (round 2) is a pure-Python BLIF evaluator giving
  signal probability and an exhaustive driving-input search directly on the written BLIF, with
  no HDL annotation needed -- the current path `build.py` uses, so it works on a real base
  design under `external/` unmodified. `lemanruss.htl.sites` (round 1) is the Odin III
  Simulation-based alternative, still tested, still used by anything that marks its candidate
  nets `(* keep *)`. Both are interim rules until the Odin III `scoap` pass merges (PR #307, in
  a fix round as of round 2).
- **SystemVerilog** (`lemanruss.htl.sv_reader`, round 2): registers Odin III's slang reader so
  `build.py` can read `.sv` base designs (e.g. `external/Gate-Breaker-verilog-eval`'s `_ref.sv`
  files) without modifying them.
- **Verification** (`lemanruss.htl.verify`): fires (a real `odin3.Design`/`Simulation`), stealth
  (random-vector mismatch rate and measured activation probability, `blif_sim`-based in
  `build.py`), and equivalence (exhaustive below a brute-force cap, else the repo's own
  `tools/equiv-check`, ABC cec).
- **Testbenches** (`lemanruss.htl.testbench`): an `odin3-sim-vectors` file for the netlist level,
  a self-checking `iverilog` testbench for the RTL level.
- **Build** (`lemanruss.htl.build`): ties all of the above together per base design and writes
  the manifest, labels (the answer key, kept separate) and `mix.json` (a Seeker's Dilemma style
  clean/infected draw).

## Known gaps this round (see spec section 6 for the full list)

- (Round 5) Netlist insertion now uses the Odin III edit API (`edit_netlist.py`); the BLIF text
  inserters stay as a recorded fallback.
- Rarity uses `sim`/`blif_sim` signal probability only; SCOAP CC/CO lands when the separate
  `scoap` pass lane (PR #307) merges.
- No VPR this round: the slow-down payload's effect size is logic-level depth, not post-route
  critical-path delay.
- `build.py` brute-forces every primary-input combination up to a cap (so it is scoped to small
  to medium, mostly combinational designs); a wider build needs ATPG/SAT for "drive the
  trigger", not enumeration, though equivalence itself already falls back to `tools/equiv-check`
  above the cap.
- MCNC BLIF base designs (found, not yet run: a multi-line BLIF header is not something the text
  parser joins yet) and `SeqCounter`/`SeqPattern` at the netlist level are the next step
  (`docs/plans/2026-10-31-htl-plan.md`).

## Seeker v2.0 families (round 3)

    lemanruss family Seeker-Comb --bases <blif...> --out <dir>
    lemanruss family Seeker-Seq  --bases <blif...> --out <dir>

Writes `circuits/`, `manifest.json`, `README.md` and `answer_key/{labels,rareness,failures}.json`
plus `answer_key/rareness.md` (per-circuit and pooled rareness tables). See spec section 7.

## Round 4: verification, restructurings, ITC-99 and VTR bases

    lemanruss hdl2blif --out <dir> <verilog...>        # Verilog base to .names-only BLIF (Odin III)
    lemanruss family-verify <family dir> [--workers 4] # Odin III cross-check, fire check, ABC cec
    lemanruss restructure <family dir> --short sc|ss   # 12 ABC restructurings, equivalence-checked

`verify` writes `answer_key/verification.{json,md}`; `restructure` writes `circuits_r/*.blif.gz`,
`answer_key/restructured.{json,md}` and extends `manifest.json` / `labels.json`. `family`
Seeker-Seq now takes `--max-blocks` (default 30000 gates) and tunes each variant (counter and
pattern, fast / mid / slow) to fire within N = 1024 cycles. See spec section 8 and
`docs/results-round4.md`.

## Round 5: edit API, sim_tb, toggle counts, more bases

    lemanruss insertion <family dir...>                  # edit-API insertion + provenance counts
    lemanruss prov-demo <base.blif> --out <file>         # what edit_tag says about each object
    lemanruss rtl-tb --mimir-root <mimir> --out <dir> --odin3-bin <odin3> --tb-compare <tool>
    lemanruss energy --out <dir> <seq base blif...>      # toggle counts: Odin III vs Python
    lemanruss bases verilogeval|vtr-verilog --mimir-root <mimir> --out <dir>

Netlist Trojans are written once as recipes (`edit_netlist.py`: names, latch, splice, isolate) and
applied with `Module.add_sop` / `add_node` / `add_net` and `Pin.connect` / `disconnect`; every new
object carries the edit tag `trojan:<id>`, readable as `edit_tag`. `restructure` now applies 18 ABC
scripts. See spec section 9 and `docs/results-round5.md`.

## Scoring a detector (Seeker v2.0)

Detector authors get an aggregate rating (confusion matrix, AUROC, found-rate by Trojan count, and
optional count and location bonuses) without the answer key being public: see
`docs/user/SUBMISSION.md` (format), `docs/user/SCORING-MANUAL.md` (maintainer by hand) and
`docs/specs/2026-11-02-scoring-design.md` (design, threat model). The scorer is
`lemanruss score`; the GitHub Actions packaging is an example only
(`docs/user/scoring-workflow.yml.example`) and is not enabled.
