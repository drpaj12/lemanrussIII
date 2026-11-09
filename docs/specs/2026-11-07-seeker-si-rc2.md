# Seeker-Si rc2: silicon as a fourth target form of Comb, Seq and Proc (2026-11-07)

Status: spec only (step 1 of Part B of the build-out brief). No set is built. Supersedes the rc1 design
(`2026-11-05-seeker-si.md`) except its cell library, mapping recipe, Verilog writer and iverilog notes
(its sections 1, 4, 6.1 to 6.4), which stay in force. Cost measurements: `docs/results-si-rc2-cost.md`.

Purpose (hub docs/purpose.md, Leman Russ III; RQ1.1, which structures do not belong to the claimed
design, asked at the standard-cell level, the form a fab or a scanned chip is checked in). Measure: a
gated release whose silicon circuits are scored by the same nine detectors and levels 1 to 3 as
Comb rc5, Seq rc7 and Proc rc3, with the flip-flop-count control at chance within base.

Peter, 2026-11-06 (reported by the controller): "why not make the silicon ones the same as each of the
other ones so we don't have to worry about a simple FF matching?" So Seeker-Si rc2 is not a separate
Trojan design and not a separate base list. It is one more form, `silicon`, next to `gates`, `lut4`
and `lut6`, of the pipeline that already builds those.

## 0. What changes against rc1, in one table

| | rc1 (record only) | rc2 |
|---|---|---|
| bases | own list (mmuart, simple_spi, cordic, des) | the bases of Comb rc5, Seq rc7, Proc rc3 |
| Trojan insertion | cell-level, counter and pattern triggers (add flip-flops) | the family's own insertion; Seq and Proc triggers add no flip-flop (rc7 magic trigger, Proc hard gate) |
| optimisation | random ABC script, then sky130 map | the same random script distribution, then sky130 map |
| FF count | leaked the label (AUROC 1.0 within base) | equal between clean and infected by construction; control reported |
| answer key | own format | the family's format, regions included |
| detectors | `lemanruss.detect.sirelease` only | the nine detectors and levels 1 to 3, unchanged |

Comparability. Because the bases are now the same, the silicon form of a base IS comparable base for
base with its gates, lut4 and lut6 forms (this reverses the rc1 statement that Seeker-Si must not be
compared per base; that statement still holds for the rc1 record). It is NOT comparable per circuit:
each form has its own Trojan draws and its own random script, as the lut4, lut6 and gates sets already
have.

## 1. The form

`silicon`: a netlist of `sky130_fd_sc_hd__*_1` cells, one `.model top`. Cell library = `odin3/lib/sky130hd.o3lib`
(84 entries: 83 combinational cells including `conb_1`, and `dfxtp_1`, the only flip-flop; generated
from the SKY130 Liberty, only `_1` drive strengths). Released as two files per circuit with identical
net names:

- `circuits/<id>.blif.gz`: gates-as-names BLIF, one `.names` cover per cell (the form every detector
  reads; a cover has at most 5 inputs for the library's complex cells, so it is a LUT-like node with a
  different size distribution than lut4 and lut6), `.latch` per `dfxtp_1`, constants as `.names` ties.
- `circuits_v/<id>.v.gz`: structural Verilog of the cells (`si_cells.blif_to_verilog`, truth-table match
  of each cover against the library; no `write_verilog`, which would carry paths). Cell types are
  visible only here, which is the form a layout tool reads.

Detectors that use a cell vocabulary (classhist) read the Verilog form for silicon circuits and report
cell-type histograms; the BLIF form gives them cover-shape classes as for lut4 and lut6. The choice is
made per detector in the harness (`lemanruss/detect/data.py`), and the table names which one each used.

## 2. How the form plugs into each family

All three families end in the same call, `obfuscate.map_with_odin(src, kind, script, work, tag)`; the
`silicon` kind already exists (`read_techlib sky130hd.o3lib; read_blif; abc --gates sky130hd --script S;
dfflibmap sky130hd; write_blif --gates-as-names`; no Yosys; Odin III is `build/rel-main3`, not rebuilt).
`random_script(rng, "silicon")` draws the same ABC operations as the gates kind, ending in `map` or
`map -a`. `finalize` shuffles and renames as for every form.

### 2.1 Comb rc5 and Seq rc7 (`lemanruss/htl/n200.py`, `n200rc7.py`)

- `SETS = (("K4","k4"), ("K6","k6"), ("G","gates"))` gets a fourth entry `("S","silicon")`. `build_set`,
  `finish`, `build_pre`, the cut-and-stitch of `cutstitch.py` (its `_map_part` calls
  `map_with_odin` with the kind) and the rc7 triggers need no change.
- Per base the set is 100 circuits, `n_inf ~ Uniform{10..70}` drawn per set from `seed:base:set:ninf` as
  today; the set has its own Trojan draws (as K4, K6 and G have), through the same planner (`make_ctx`
  or `make_ctx_rc7`) so rareness bands, payload kinds and the 1 to 3 Trojan mix are the same.
- Id block per base grows from 301 to 401 (`BLOCK` in `n200run.py`). The silicon ids are redrawn, not
  appended to rc5 and rc7 files, so a detector trained on a release sees ids that say nothing.
- Seq rc7 gate (`n200rc7.py`): the FF/latch equality of the pre-obfuscation infected circuit and the
  golden stays (hard). New, after mapping: `ff(final) == ff(golden)` for every silicon circuit, clean
  and infected, checked on the finalized BLIF. ABC `--gates` keeps flip-flops (it does not retime and
  the random OPS list contains no `scorr`), so within a base every silicon circuit has the same
  count; the check is cheap and stops a build if a script ever changes it.
- Comb has no flip-flops; the control is vacuous there and is reported as such, not as a pass.
- The release gate (cec of the finalized circuit against its source, fire check by Odin III simulation
  against the golden, `dup` signature check) runs on the BLIF form unchanged. Added for silicon:
  Verilog round trip (`si_cells.verilog_to_blif`, `same_network`) and a structural cell check (every
  cover matches a library cell).

### 2.2 Proc rc3 (`lemanruss/htl/proc_build.py`, `proc_rc1_release.py`)

- `FORMS = ("gates","k4","k6")` gets `"si"`; `FORM_NAMES` gets `"si": "silicon"`. `build_one_circuit`
  maps `clean_nl` and `inf_nl` once per form with `obfuscate_traced`, which already handles the kind;
  the release gate (`gate_problems`, regmatch-cec then scorr-cec then dsec) is the same call with the
  form key.
- The logical circuit (base, kinds, magic words, witnesses, FF equality at RTL and netlist, silence on
  the neutral witness and the shipped programs) is built once and shared by all four forms, so the
  functional gates are not repeated. The silicon form adds one gate: mapped FF count equals the
  netlist FF count.
- Slot arithmetic: `proc_rc1_release` makes `len(circuits) x len(FORM_NAMES)` slots, so rc3 (133
  logical circuits) goes from 399 to 532 files; the clean/infected draw per form, ids and shuffle are
  redrawn with new secret seeds.
- Known item to check in the pilot: `dfflibmap` warns that flip-flops with INIT 0 or 1 become cells with
  an unknown initial value (darkriscv: 837 of 2,032). Simulation of the silicon form therefore starts
  from the netlist's reset sequence or the 0-start used in the rc1 pilot; the gate keeps comparing the
  silicon form to its source by equivalence, not by simulation from reset.
- Black boxes: the Proc netlists have memories as ports (no `.subckt`), so mapping needs no hard-block
  handling. Measured on one circuit per base (cost doc): all four map.

### 2.3 What stays outside the pipeline

- `lemanruss/htl/si_build.py`, `si_set.py` and `detect/sirelease.py` (rc1) stay as the record of rc1
  and are not extended. `si_cells.py` and the `silicon` kind of `obfuscate.py` are reused.

### 2.4 As built (amendments of 2026-11-07, after the long-build go)

- Comb and Seq: `LEMANRUSS_SETS=S` builds the silicon set alone (`n200.active_sets`); the golden of
  each base is also mapped to cells (`si_golden.silicon_goldens`) so a release holds one form. A
  base whose golden Odin III cannot map (four tiny VerilogEval bases that already fail to parse) is
  dropped from the manifest and listed in `dropped_bases`.
- Proc: the silicon release is its own release (`seeker-si-proc-v2.0-rc2`, 133 circuits, silicon
  form only, new seeds). The gates/lut4/lut6 forms are not rebuilt (this amends section 2.2, which
  counted 532 files).
- Proc gate on the silicon netlists themselves (controller condition): every Trojan must fire and the
  neutral stimuli (neutral program, neutral shift) must stay silent on the silicon BLIF simulated by
  Odin III (clean twin against infected twin, their own initial-value semantics). A circuit that fails
  is rejected, counted and redrawn (`n_rejected` in the build metadata). Shipped-program silence is
  not repeated on the silicon netlist.
- Equivalence of a silicon circuit to its source: strict first. `dfxtp_1` carries no initial value,
  so when the strict check fails on equivalence, the same check runs against the source with every
  `.latch` initial value reset (read as 0); clean and infected twins use the same procedure, each
  against its own source, and the gate used is recorded per circuit (`answer_key/build_meta.json`).
  Result: mips_16, mcu and picorv32 strict for every circuit; darkriscv init-reset for every circuit
  (its source has 815 flip-flops with initial value 0, 22 with 1 and 1,195 unknown).
- Place and route (`si_pnr_set`): about 10 % of each Comb and Seq base (label-stratified), 30 % of each Proc base
  (every base represented), smallest first; flow = `odin3/tools/silicon/openroad_flow.tcl` unchanged (utilisation 25 %),
  60 minute wall cap per circuit, retry at 18 % utilisation only after a flow error (a cap-out is recorded as a flow limit
  with its cell count and not retried: retries never helped; deviation from the controller's one-retry rule, logged). A
  silent-log stall rule (300 s at `DRT-0179`) was tried and switched off: it killed a 5,758-cell run that routes in 985 s.
  Diagnosis of the hangs (one Comb circuit, 1,078 cells): IO density does not separate them; a larger die (utilisation 10),
  looser pin spacing, default global-route iterations and a global-routing layer adjustment all still hang; routing from
  metal 2 upward fails (GRT-0118 or DRT-0155). No flow parameter changed. Results by size bucket: `docs/results-si-rc2.md`.
- Detectors: Proc as rc3 (`procrun`, 50 epochs, no training cap, seeds 0, 1, 2, range check);
  Comb and Seq as the localisation runs of PR #3 (12 epochs, batch 32, training cap 1,500,
  `locrun` for the localising detectors and `detect.run --splits base` for the others).

## 3. The gate set for the new form

Applied per silicon circuit before it is written; any failure redraws (infected) or stops (clean).

1. Format: one `.model`, no duplicate port, no driven input, no multi-driven net (`proc_gate.
   structural_problems`); Odin III `read_blif` succeeds.
2. Cell check: every `.names` cover equals a library cell function over some pin order (smallest area on
   ties); every `.latch` is a `dfxtp_1`; no cover of more than 5 inputs.
3. Equivalence of the finalized circuit to its source: `regmatch-cec`, else `scorr-cec` (15 minute
   cap), else `dsec`; unproven is a failure. Source = the golden or lowered netlist (clean) or `pre`
   (infected); `pre` with all triggers forced inactive against the golden stays as in the family.
4. Fire: every Trojan fires on its own witness on the finished circuit (Odin III simulation for Comb and
   Seq; the three-engine replay for Proc), payload visible.
5. Silent on the family's neutral stimulus (Seq: neutral vectors; Proc: neutral witness, neutral shift
   word, shipped programs).
6. Flip-flop count: equal to the golden's, for every circuit (section 2.1); recorded in the key.
7. Verilog round trip: the cell Verilog read back equals the BLIF (`same_network`).
8. Leaks: no seed, magic word, inserter name, `$` name, `.attr`, comment or design name in either file;
   ids opaque; port and clock names are the design's interface names, as in the other forms.
9. Distinct structure within a base and form (`obfuscate.signature`).

Iverilog on the cell Verilog is a recorded check (twin-vs-twin trace equality where a testbench exists),
not a gate, as in rc1 (flip-flops without reset give x).

### 3a. Buffer-free silicon netlists (rule added 2026-11-07 after the first Seq verification)

The first Seq silicon build failed the style check `g_style`: infected circuits held more `buf`
cells than clean ones (z = 9 over 36 bases, difference 0.105; best single feature AUROC 0.585, under
the bound but a count leak). Source: cut-and-stitch. The pieces of a circuit are mapped separately
and joined, and the mapper puts a buffer where a boundary net is both a port of a piece and an input
elsewhere; plain mapping of a whole circuit gave 0 buffers in 12 of 12 trials (6 scripts, golden and
infected pre-circuit). How many cuts and how many boundary nets a circuit has differs by draw, hence
a label-correlated count. Rule, applied after every silicon mapping step and after stitching, to
every family and both labels (`obfuscate.strip_buffers`): a non-inverting buffer cell is removed by
merging its nets (its output is replaced by its input; if its output is a port and its input an
internal net, that net is renamed to the port name). Port names never change. A buffer that joins two
ports, or an input port to an output port, stays, because a port cannot alias another port. Equivalence
of every circuit to its source is proven after the rule by the same gate. After the change: Comb and
Seq pass all verification checks including `g_style` and contain no internal buffers; the Proc cores
keep only port-joining buffers that belong to the core interface and are the same for clean and
infected circuits of a base (picorv32: 103 per circuit in both labels; mcu and mips_16: none;
darkriscv: one input-to-output feedthrough per circuit and 0.4 to 0.6 port-to-port per circuit,
0.57 clean against 0.37 infected).

## 4. Answer key

Same files and schema as the family (`labels.json`, `sets`, Trojan catalogue, `pre/<id>.blif.gz`,
witnesses, rareness, `regions.json`), plus per silicon circuit: the ABC script, the net rename map and the
pre-finalize mapped text (needed to take a region from the pre-obfuscation Trojan cells to final
names, as for the other forms), the cell-type histogram, and `ff_count`. Labels, scripts, `pre` circuits
and renames live in the answer key only, on `/mnt/f` in a new dated directory; nothing private is
committed. Regions: Comb and Seq by `lemanruss.score.regions` (function on random lanes), Proc by
`proc_regions` against the clean twin (spec rc3 section 9a); both work on `.names` covers, so the
BLIF form of the silicon circuit is their input and the hit test uses the same net names as the
submission. A silicon cover is a function of up to 5 nets, so a region on a silicon circuit is a set
of cells; the chance control of the scoring spec section 4 is unchanged.

## 5. FF-count control

`ffcount` (detector 2 of 9) is run on the silicon form like every other detector, within base and
leave-one-base-out. Expected: within base every silicon circuit has the golden's count, so the score is
a constant and AUROC is 0.5 exactly (reported with W/L/T and the permutation interval, CAD convention).
This is the control Peter asked for; it must be measured, not asserted. Across bases `ffcount` still
separates bases by size, which the `ffrange` check of Proc already handles.

## 6. Size and cost of the silicon sets

Per-circuit mapping cost, full OpenROAD place and route, and the stratified-subset proposal are in the
cost doc and in the controller report; the build is gated on the controller's go for any run longer than
12 hours. Pilot (shorter): 3 to 5 bases, a few circuits each, all gates, detectors run on the pilot for
parse sanity only (no results claimed from it).

## 7. Layout-level research: a Seeker-GDS set (spec only, not built)

Grant direction (Peter; memory silicon-provenance-vision). Odin III to OpenROAD to GDS keeps a provenance
chain from HDL to cell to placement (`silicon_flow.py recover` joins extracted cells to DEF placements by
cell type and location, without names). A fab-time Trojan is an edit to the layout after the design
house signed off: the netlist is not touched, so everything in sections 1 to 5 is blind to it by
construction. The research question is: given a GDS and the design house's golden netlist and provenance
chain, which structures do not belong, and which edits can a check see at all?

### 7.1 What a Seeker-GDS set would need

1. Layouts. P&R of each base (cost doc; the ladder shows OpenROAD stops on `wb_lcd` and `des`, flow
   limits not design limits), GDS via KLayout, taps and fill included.
2. Edits (the Trojan catalogue at layout level), each a script on DEF/GDS with a witness in layout
   coordinates:
   - E1 add cells in free sites or in place of fill (rare-input trigger tree plus a payload gate on a
     victim net, wired by new short segments);
   - E2 resize or swap a cell (drive strength `_1` to `_2`, or a footprint-compatible cell of other
     function), no new net;
   - E3 reroute: add, cut or detour a wire (open, short, a net moved to a different driver pin);
   - E4 below the netlist: dopant or contact changes that alter a cell's function while the metal
     stack and the cell outline are identical (outside GDS editing of metal layers; listed because
     it is the case no netlist or LVS check sees, only physical inspection or test).
3. Extraction: Magic flat extraction to SPICE (the flow's `magic_extract.tcl`; the ladder notes flat
   extraction of des took more than an hour, so a hierarchical or windowed extraction is part of the
   plan for large designs) and the `recover` join to DEF.
4. Checks (the detector side): LVS of the extracted netlist against the golden netlist (Netgen,
   `netgen_lvs.py`), cell-by-cell join with the provenance chain (unjoined cells, joined cells whose
   type or position changed), and structural anomaly detection on the extracted netlist exactly as the
   nine detectors do on rc2 circuits (this is where the Si form of this spec feeds the layout work).
5. Scoring: levels 1 to 3 as the scoring spec, with regions defined as the layout shapes (cells and
   nets) touched by the edit, in the answer key only.

### 7.2 Which edits LVS cannot see (hypotheses to test, not results)

| edit | cell-level LVS (hierarchical) | flat device LVS | provenance join |
|---|---|---|---|
| E1 new cells wired in | sees extra cells and nets, unless placed where the golden has fill and the check ignores filler | same | sees unjoined cells |
| E1 cells hidden as tap, decap or fill type | not seen if physical-only cells are filtered out of the comparison (the flow filters them: `PHYS_RE`) | same | not seen if filtered |
| E2 drive-strength swap | sees a cell-type mismatch | sees changed W/L only if device sizes are compared (Netgen default ignores some properties) | sees type change |
| E2 footprint-compatible swap | sees type mismatch | sees changed devices | sees type change |
| E3 reroute that keeps connectivity (detour) | not seen | not seen | not seen (no net names) |
| E3 reroute that changes connectivity | sees | sees | partly |
| parasitic (capacitive) triggers | not seen | not seen | not seen |
| E4 doping changes | not seen | not seen | not seen |

Each cell of this table becomes a measured row once a set exists; until then it is a prediction to
refute. The point of the Seeker-GDS idea is the third column: with provenance the design house can say,
for every placed cell, which HDL construct it came from, which turns "extra cell" and "type changed" from
heuristics into checks, and shows exactly where the checkable region ends.

### 7.3 Dependencies and order

Needs: P&R on a stratified subset (cost doc), a stable `recover` on the subset, an edit tool
(KLayout Python), and a decision from Peter on the set's size and edit classes. Not before the rc2 netlist
sets are released and scored. Nothing in this section is built or run in rc2.

## 8. Agent defaults (log, not blockers)

1. Silicon sets are 100 circuits per base, the same as the other three forms; the id block grows to 401.
2. The silicon form is compared per base with the other forms of the same base, not per circuit.
3. classhist on silicon reads cell types from the Verilog form; the other detectors read BLIF.
4. Mapped FF count is a hard per-circuit gate, in addition to the family's pre-obfuscation FF gate.
5. Comb flip-flop control reported as vacuous (no flip-flops), not as a pass.
6. Layout-level work (section 7) is spec only.
