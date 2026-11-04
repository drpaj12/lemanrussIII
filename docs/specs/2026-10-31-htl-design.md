# HTL design: Hardware Trojan Library, insertion, verification (2026-10-31)

Leman Russ III purpose (`yggdrasil/docs/purpose.md`, Leman Russ III R1): detect higher-level
structure and anomalies in netlists, including hardware Trojans, on the Odin III IR, graph and
provenance. This spec is the first step: build the benchmark generator (Trojans to detect, not to
deploy). Defensive research in Peter's own line of work (Sarihi, Patooghy, Badawy, Jamieson).

## 1. Literature and taxonomy

Every citation below was checked against Crossref (DOI) or the arXiv API on 2026-10-31; no number
is quoted from memory.

| Ref | Full citation (verified) |
|---|---|
| Tehranipoor & Koushanfar 2010 | M. Tehranipoor, F. Koushanfar, "A Survey of Hardware Trojan Taxonomy and Detection," *IEEE Design & Test of Computers*, 2010. DOI 10.1109/mdt.2010.7. |
| Wolff et al. 2008 | F. Wolff, C. Papachristou, S. Bhunia, R. S. Chakraborty, "Towards Trojan-Free Trusted ICs: Problem Analysis and Detection Scheme," *DATE 2008*. DOI 10.1109/date.2008.4484928. |
| Chakraborty et al. 2009 (MERO) | R. S. Chakraborty, F. Wolff, S. Paul, C. Papachristou, S. Bhunia, "MERO: A Statistical Approach for Hardware Trojan Detection," *CHES 2009*, LNCS. DOI 10.1007/978-3-642-04138-9_28. |
| Shakya et al. 2017 (Trust-Hub benchmarks) | B. Shakya, T. He, H. Salmani, D. Forte, S. Bhunia, M. Tehranipoor, "Benchmarking of Hardware Trojans and Maliciously Affected Circuits," *Journal of Hardware and Systems Security*, 2017. DOI 10.1007/s41635-017-0001-6. |
| Goldstein & Thigpen 1980 (SCOAP) | L. H. Goldstein, E. L. Thigpen, "SCOAP: Sandia Controllability/Observability Analysis Program," *Proc. 17th Design Automation Conference (DAC)*, 1980, pp. 190-196. Verified via Crossref DOI 10.1145/62882.62929, the ACM's reprint of this paper in the "Papers on Twenty-five years of electronic design automation" DAC88 collection (`event.name`: "DAC88"; `container-title`: "Papers on Twenty-five years of electronic design automation"), confirming author list Goldstein/Thigpen and the title; the original 1980 proceedings record itself was not separately indexed by Crossref at check time. |
| Salmani 2017 (COTD) | H. Salmani, "COTD: Reference-Free Hardware Trojan Detection and Recovery Based on Controllability and Observability," *IEEE Transactions on Information Forensics and Security (TIFS)*, 2017. DOI 10.1109/tifs.2016.2613842. |
| Sarihi, Patooghy, Badawy, Jamieson 2024 (Seeker's Dilemma) | A. Sarihi, A. Patooghy, A.-H. A. Badawy, P. Jamieson, "The Seeker's Dilemma: Realistic Formulation and Benchmarking for Hardware Trojan Detection," arXiv:2402.17918; *IPCCC 2024*, DOI 10.1109/ipccc59868.2024.10850433. |
| Sarihi, Patooghy, Jamieson, Badawy 2024 (follow-up, Hiding in Plain Sight) | A. Sarihi, A. Patooghy, P. Jamieson, A.-H. A. Badawy, "Hiding in Plain Sight: Reframing Hardware Trojan Benchmarking as a Hide&Seek Modification," arXiv:2410.15550. |
| Sarihi, Patooghy, Jamieson, Badawy 2024 (Peter's other HT work, RL insertion) | A. Sarihi, A. Patooghy, P. Jamieson, A.-H. A. Badawy, "Trojan Playground: A Reinforcement Learning Framework for Hardware Trojan Insertion and Detection," *The Journal of Supercomputing*, 2024. DOI 10.1007/s11227-024-05963-8. Read, not implemented here (RL insertion is out of scope for this round: no LLM/RL calls, per brief). |

**Taxonomy axes** (Tehranipoor & Koushanfar 2010; Wolff et al. 2008 for the insertion-phase axis):

1. **Insertion phase**: specification, design, fabrication, testing, assembly, deployment. HTL
   covers *design* only (HDL source and post-synthesis netlist); fabrication/mask-level Trojans are
   out of scope (Odin III has no layout).
2. **Abstraction level**: system, development environment, register-transfer, gate, transistor,
   physical/layout. HTL covers *register-transfer* (HDL insertion) and *gate* (netlist insertion);
   no transistor or layout level (no SPICE, no VPR placement in this round).
3. **Activation characteristic**: always-on, condition-based (internal: logic/time counters, or
   external: sensors). HTL covers always-on and internal condition-based (combinational rare-value,
   sequential counter/time-bomb, sequential pattern/FSM, input-pattern). No sensor-based (physical)
   triggers: out of scope without a device model.
4. **Effect (action)**: change function, downgrade performance/reliability, leak information, deny
   service. HTL covers denial of service, function change (bit-error insertion), and performance
   downgrade (energy, delay); no information-leak payload in this round (no side channel / covert
   channel model yet).
5. **Location**: a Trojan may touch any functional unit, the I/O, the clock/power grid, etc. HTL
   locates by *role* (rare internal nets for triggers; outputs, word MSB/LSB group, near-critical
   path for payload victims), not by named functional unit, since the generator must work across
   different base designs. This is the MERO (Chakraborty et al. 2009) idea of covering rare internal
   states, applied to site *selection* rather than to test generation.

The Seeker's Dilemma benchmark style (Sarihi et al. 2024, and the follow-up) is adopted for the
*benchmark set*, not the taxonomy: a mix of HT-free and HT-infected variants of the same base
design, with labels kept out of the detector's view (§5). Trust-Hub's benchmarking paper (Shakya et
al. 2017) is the model for *what one catalogue entry records* (trigger, payload, insertion
mechanism, a stated stealth rationale): the HTL manifest schema (§2, §5) follows that shape.

## 2. HTL model

A Trojan = **trigger** x **payload** x **insertion site** x **level** (`hdl` | `netlist`), each
instance carrying a stable id (`<trigger-id>__<payload-id>__<level>`), a one-line description, and
a stealth note (why it is hard to see in simulation/structure).

### Triggers

| id | mechanism | parameters |
|---|---|---|
| `t-comb-rare` | AND of `k` rare-valued internal nets (each at its rare polarity) | `k` (default 4), the net selection rule (§3) |
| `t-seq-counter` | time-bomb: an internal counter that increments on `N` occurrences of a rare condition, fires once saturated | `N` (default 8192), the counted condition (a `t-comb-rare` AND with smaller `k`) |
| `t-seq-pattern` | small FSM that fires after a fixed sequence of `k` rare-condition cycles, in order (not just a count) | `k`, the per-step condition |
| `t-always-on` | constant 1 (no trigger logic); used only with payloads that must be continuously present (energy, delay) | — |
| `t-input-pattern` | a magic word on a chosen group of input bits | the bit group, the magic value |

### Payloads

| id | effect | parameters | effect measure |
|---|---|---|---|
| `p-dos-stuck` | force a chosen output (or internal enable/reset net) to a constant when triggered | the victim net, the stuck value | functional diff (output differs from clean design once triggered) |
| `p-dos-reset` | force the design's reset net active when triggered | — | functional diff |
| `p-err-hi` | flip (or force) the top `b` bits of a chosen output word when triggered | the word, `b` (default 1), flip-vs-force | functional diff, bit-weighted (how far the value moves) |
| `p-err-lo` | flip (or force) the bottom `b` bits of a chosen output word when triggered | as above | functional diff |
| `p-energy` | an always-toggling ring (odd-length inverter loop modelled as a free-running counter bit chain) gated on by the trigger, sized to a stated fraction `f` of the design's node count | `f` (default 0.05), ring length derived from `f` | toggle-count delta from simulation (Mimir rule: toggle count is the activity proxy; no power number is claimed) |
| `p-slowdown` | a delay chain (buffer-equivalent logic levels with no functional effect, `$and`/`$or` identity chains) spliced onto a chosen near-critical net, sized to a stated fraction `g` of its current logic-level depth; `t-always-on` or trigger-switched | `g` (default 0.1), the victim net | logic-level depth delta now (no post-route CPD in this round: VPR is out of scope, per brief; §4 records this as deferred, not as an Odin III gap, since the VTR/VPR flow already exists outside this repo) |

`p-slowdown`'s CPD measurement needs the VTR/VPR flow, which this round does not run (brief: "No
VPR in this round"); the manifest records logic-level depth as a stand-in and flags CPD as a later
measure, re-using Loki/Wyrd's existing VPR flow rather than building a new one here.

## 3. Insertion

### HDL level

Verilog source transform: Odin III's `read_verilog --parse-only` (and, where it helps, the AST
`design.ast()` the Python API exposes read-only, `docs/PASSES.md` row 2C/2D) locates the target
module, its ports and its internal nets/wires by name and declaration site; the inserter then does
a line-based text splice (insert new `wire`/`reg` declarations, an `always` block for the trigger,
and an `assign`/forced-driver for the payload) rather than regenerating Verilog from the AST, since
the Python API has no AST-to-text writer and no node-creation API (§6 gap note). After the splice,
`read_verilog --parse-only` is re-run on the result as the parse check the brief asks for; a design
that fails this check is dropped from the benchmark set and logged as a failure (§5).

### Netlist level

Odin III `read_blif` / `write_blif` round-trip the design; the Python API (`odin3.py`) exposes a
read-only object model (`Design.modules()/nodes()/nets()/pins()`, `Net.driver()/pins()`) with no
mutation method (no `add_node`, `connect`, or cell-level write — confirmed by reading
`plugins/python/odin3.py` in full; see §6). The netlist inserter therefore: (1) reads the BLIF with
`read_blif` to find the chosen victim net and its driving `.names`/`.latch`/`.gate` line by text
position (the Python object model gives the net and pin identities; the BLIF writer is Odin III's,
not reimplemented here); (2) appends new `.names`/`.latch` lines implementing the trigger and
payload logic as plain BLIF text, rewiring the one chosen net's `.names` output or a new wrapper net
per the payload; (3) re-reads the edited text with `read_blif` as the parse/structural check (this
also catches a malformed rewire: a bad `.names` line is a located Odin III parse error). This stays
inside "through the odin3 Python API" in the sense the brief intends (every check and every read of
the result goes through `odin3.py`); the *edit* step itself is text-level because the API offers no
netlist-mutation call — recorded as an agent default (§6), open question for the controller.

### Site selection

- **Trigger nets** (rare nets): signal probability from Odin III `sim` random vectors (a stated
  vector count, default 4096, seeded) — the fraction of cycles each signal is 1. A net is "rare" at
  value `v` when `P(net=v)` is below a threshold (default 0.05, i.e. SCOAP-style CC thinking without
  SCOAP: a net rarely 1 is a candidate for a rare-at-1 AND trigger, and symmetrically for 0). This is
  explicitly the brief's interim rule: "Until the Odin III `scoap` pass is on main, use signal
  probability from `sim` only." When `scoap` merges, the site-selection module's
  `RarityRule` gets a second implementation (`ScoapRarity`) using CC0/CC1/CO and the probability
  rule stays as a fallback / cross-check; no code in this repo waits on that merge.
- **Payload victims**: by role — `p-dos-*` and `p-err-*` target a top-level output (or, for
  `p-dos-reset`, the design's declared reset signal if named `rst`/`reset`/`rst_n`, else the first
  synchronous-only input); `p-err-hi`/`p-err-lo` target the top/bottom bits of the widest output
  word; `p-energy` targets any free internal node name (it adds a new always-toggling subgraph, so
  it needs no existing victim); `p-slowdown` targets the net with the deepest `sim`-walk fan-in
  chain found by walking driver pins from each output back through combinational nodes (a
  stand-in for "near-critical" until SCOAP/VPR timing is available, logged as such).

## 4. Verification

For every infected circuit, three checks, each producing one row of the results table (§5):

1. **Fires**: a testbench drives the trigger condition and the payload's effect is observed.
   - Netlist: `sim --vectors-in <file>` with a crafted vector file in the `odin3-sim-vectors`
     format (`src/sim/vectors_in.c`, `docs/PASSES.md` `sim` row: a title line, then one `# input`/
     `# clock`/`# output` line per port, then one cycle line per vector) that drives the trigger
     condition, comparing the infected design's output vector to the clean design's.
   - RTL: an `iverilog`-compiled testbench generated per Trojan (an `initial` block driving the
     trigger pattern, `$display`/`$finish`; Odin III itself is not asked to simulate RTL, per the
     brief and the testbench-gap note in §6).
2. **Stealth**: a stated count (default 4096) of random vectors (the same `sim` random-vector
   mechanism used for rarity, §3) shows no output difference between clean and infected when the
   trigger condition is not met over that run, and the measured activation probability of the
   trigger is reported (the fraction of the 4096 cycles where the trigger condition held) — this
   should be small for a stealthy Trojan, and the table (§5) reports it as a number, not a
   pass/fail, so the catalogue documents a range of stealth levels rather than only the stealthiest.
3. **Equivalence of the clean part**: with the trigger forced permanently inactive (netlist: the
   trigger's output net tied to the inactive constant before the payload's gating AND; HDL: the
   trigger's enable wire tied to 0), the infected design must be equivalent to the clean design.
   Checked with the repo's own `read_blif`/`write_blif` round trip plus Odin III's `abc`-based
   equivalence flow the same way Loki's `tools/equiv-check` uses it (ABC `cec`); for HDL, `abc cec`
   on the two designs after both pass through Odin III's `read_verilog`/elaboration/`write_blif`.

### Testbench gap (recorded for Odin III, not built here)

Odin III's own `sim` pass is a cycle-based netlist simulator with vector-file input/output and VCD
output (`docs/PASSES.md` `sim` row) — it has no Verilog-testbench capability: no `initial` block
interpretation on RTL, no `#<delay>`, no clock generation from a `always #N clk = ~clk;` idiom, no
`$display`/`$finish`, no file-based `$readmem`-style vector drive from a *testbench* module (reading
a design's own `$readmemh` is separate and already supported, `docs/PASSES.md` row 2D). A future
Odin III testbench pass would need: (a) a restricted but real `initial`/`always` interpreter with
`#delay` and event scheduling (today's elaboration only interprets `initial` statements that are
constant, `docs/PASSES.md` 2D Task 24); (b) `$display`/`$write`/`$finish`/`$stop` as simulation
side-effects, not elaboration-time constructs; (c) a way to bind a testbench module's clock/reset
generation to the `sim` pass's cycle stepping. This repo instead uses `iverilog`/`verilog` for RTL
testbenches and Odin III `sim --vectors-in` for netlist testbenches, and records this gap as a
future Odin III item per the brief ("do not build it in Odin III").

## 5. Benchmark set

A manifest per base design: the clean circuit, N infected variants (one per legal trigger x payload
x level combination the base design supports), each variant's Trojan id, insertion site, and the
verification results (§4) — but **labels (clean/infected, Trojan id) live in a separate
`labels.json`**, never in the netlist/RTL text and never in the file the detector is pointed at
(`CLAUDE.md` rule, mirroring Loki's `key.json` separation). A `mix.json` records the seeds and the
mix ratio parameter (default 0.5) for drawing a labelled-hidden test set in the Seeker's Dilemma
style (Sarihi et al. 2024): the detector sees only `circuits/`, never `labels.json`.

Base designs (first build, §"Then build" D): about 10, drawn from what is already checked out in
this workspace, no new fetch in this round:
- `external/Gate-Breaker-verilog-eval` (VerilogEval reference designs; MIT/NVIDIA via the
  NMSU-PEARL fork, as Loki's README already documents the licence for the same source).
- `external/vtr-verilog-to-routing` small Verilog designs (`odin_ii` test circuits bundled in that
  checkout), for designs that need VTR-style ports.
- MCNC BLIF designs already present under `odin3`/`golden` fixtures (for a few netlist-only base
  designs, where no RTL exists and only the netlist-level inserter runs).
No "round 4 families used by Loki" base-design set is checked out in this workspace under that name
at spec time; the plan (§ next step) substitutes the above three sources and records the deviation.

## 6. Gap notes and agent defaults (recorded, not Odin III changes)

- **Netlist mutation API** (controller note, not an Odin III change): `odin3.py`'s object model
  is read-only (no `add_node`/`connect`/per-cell write; confirmed by reading `plugins/python/
  odin3.py` in full, both rounds). The netlist inserter edits BLIF text directly and re-validates
  with `read_blif`. A replacement API, if ever wanted, would need at minimum: `Module.add_node
  (cell_type, name) -> Node` (register a new cell instance, given a registered or built-in cell
  type the way `-icells`/gate instantiation already resolves one); `Module.add_net(name) ->
  Net`; `Pin.connect(net)` / `Pin.disconnect()` to attach or detach a pin from a net (the
  existing `Pin.net()` is the read side of exactly this edge); and a way to set a `$lut`/`.names`
  cell's truth table (`Node.set_table(cover)`), since a Trojan's logic is almost always a new
  small truth table, not an instance of an existing registered cell. All four would need the
  usual IR invariants kept (provenance, IDs, hierarchy -- `odin3_three_goals` / `provenance_hier
  archy_joins` house rules): a created node/net with no provenance record, or a connect that
  skips the driver-claim check `elab2` already enforces, would silently break `write_blif`'s
  structural checks or `check`'s FULL verification. Round 2 did not need this landed to proceed
  (BLIF text edit + `read_blif` re-validation covered every Trojan this round built), so this
  stays a note, not a blocker.
- **SCOAP pending**: still signal probability only (now `lemanruss.htl.blif_sim`'s own Monte
  Carlo evaluator, not Odin III `sim`/Simulation -- round 2's rarity source, see `build.py`'s
  module docstring). The Odin III `scoap` pass (odin3 PR #307) is in a fix round as of this
  commit, not merged; per the controller's round 2 instruction, switch to SCOAP (CC1/CC0 + CO)
  and record both measures once told it has landed on `main`. No code here depends on its
  interface yet, so nothing is blocked waiting.
- **No VPR in this round**: `p-slowdown`'s effect size is logic-level depth, not post-route CPD.
- **Base design set**: round 1 used 5 tiny local fixtures (no HDL annotation needed any more,
  round 2); round 2 ran the real sources for the first time: 2 SystemVerilog `_ref.sv` designs
  from `external/Gate-Breaker-verilog-eval` (via the slang reader, registered by
  `lemanruss.htl.sv_reader`) and 3 small Verilog designs from
  `external/vtr-verilog-to-routing`'s `vtr_flow/benchmarks`. MCNC BLIF (4 real circuits --
  alu4, misex3, s298, seq -- already LUT-mapped at `work/mimir-data/msd/work/*/f1-k6/
  netlist.blif`) was found but not run this round: each file is 3800-5000 lines with a
  multi-line `.inputs`/`.outputs` header (a trailing `\` continuing onto the next line), which
  `lemanruss.htl.blif_text.parse_single_model` does not join -- a real gap, not tried and
  silently skipped, logged as the next step.
- **SCOAP citation**: Crossref indexes the original 1980 DAC paper only as its DAC88 reprint (§1);
  recorded as found rather than asserting an unindexed 1980 DOI.

## 7. Round 3: rareness-first Seeker v2.0 families (2026-10-31)

Peter: report the rareness quality of the insertion, not how well the Trojan is inserted. Two
families this round (Seeker-Proc waits for Peter's RISC-V material).

- **Site selection** (`lemanruss/htl/seeker.py`): every internal net gets (a) signal probability
  from a bit-parallel simulation (`bitsim.py`, 2^20 vectors) and (b) SCOAP from the Odin III
  `scoap` pass (`Design.scoap`, odin3 #307, plus Odin's own `sigprob` p1_ppm); both are recorded
  per chosen net. Candidates are ranked by SCOAP controllability of the rare value, then a rare-
  value AND is widened net by net (k grows) until its joint probability is inside the target band
  (p < 1e-2, 1e-3, 1e-4). A band that cannot be reached is a listed failure, not padded.
- **Rareness record** (`rareness.py`, one per infected circuit, pooled table): activation
  probability with Wilson 95% interval and the vector count (exact by enumeration when the
  circuit has <= 20 inputs), expected vectors 1/p, CC of each trigger net's rare value, CO of the
  payload victim (a primary output, so 0 by definition), SCOAP of the trigger net on the infected
  netlist, percentile rank of the chosen nets among all internal nets by rareness, band reached.
  The reported p is measured on an independent vector sample from the one used for selection.
  Insertion quality (trigger fires, stealth mismatches while the trigger is low) is a secondary
  column.
- **Sequential** (Seeker-Seq): latch-based counter (2^bits events) and FSM-pattern (L in-order
  cycles) triggers at the netlist level, sticky. Rareness is SC/SO (structural heuristic) AND
  P(trigger high within N cycles), N in {16, 64, 256, 1024}, from multi-cycle simulation with
  random inputs from reset state 0 (each lane an independent run). Odin III's sequential SCOAP
  counts register-setting depth, not elapsed cycles, and ignores set/reset/enable pins for
  controllability (Goldstein models them), so it underestimates time-bomb rareness; "-" in an SC
  cell is Odin's INF (unreachable by its rules), not a measurement.
- **Families** (`families.py`): `manifest.json` (family, version 2.0, v1 lineage, bases,
  restructurings, Trojan catalogue, circuits, mix), README, and `answer_key/` (labels, rareness,
  failures) kept apart from the circuits. Restructurings are identity only this round (Seeker1 used
  18 ABC restructurings: next step).
- **Bases**: VTR `blif/2` (2-input-LUT mapped) ISCAS-85 and MCNC combinational for Seeker-Comb,
  ISCAS-89 for Seeker-Seq. ITC-99 and VTR sequential Verilog designs, VerilogEval / VTR Verilog
  bases through `write_blif` are next. MCNC BLIF line continuation fixed in `blif_text`.
- **Testbench gap** unchanged; the Odin III netlist-edit API and the Verilog testbench simulator
  are not merged, so the text inserters and `bitsim.py` stay.

## 8. Round 4: verification, ABC restructurings, tuned Seeker-Seq (2026-10-31)

Needs neither the Odin III edit API nor the Verilog testbench simulator (round 5). The text
inserters and `bitsim.py` stay.

- **Simulator cross-check** (`r4check.crosscheck`): the bit-parallel simulator against Odin III's
  `Design.simulate` on every clean base and every infected circuit. Combinational: 512 random
  vectors; sequential: 6 independent lanes of 48 cycles from reset (latch init 1 honoured,
  init 2/3 as 0, reset-like inputs held inactive). Compared before the clock edge: every primary
  output and the trigger net where Odin III lists it. A firing witness (found by the bit-parallel
  simulator) is replayed as one more run so the trigger and payload paths are compared, not only
  the quiet random ones.
- **Authoritative fire check** (`verify.check_fires_vs_clean`): the original `check_fires` read
  one design before and after; it cannot tell a Trojan effect from a value that was already
  there. The round 4 form replays the witness in Odin III on the clean AND the infected design and
  requires trigger high, infected victim = stuck value, clean victim different. Round 3's
  bit-parallel "fires" flag (victim = 1 whenever the trigger is high) was true by construction
  after the payload; it is replaced by "the payload changes an output on at least one triggered
  vector" and `payload_visible_fraction` is recorded. Comb victim and stuck value are now chosen
  to maximise that (a rare net that implies the victim's value made a masked Trojan in round 3).
- **Equivalence** (`r4check.cec_forced_off`): `tools/equiv-check` (ABC cec; dsec with latches) of
  the clean circuit against the infected one with the trigger net driven by a constant 0.
- **Restructurings** (`restructure.py`): 12 explicit ABC scripts (ABC aliases such as resyn2 are
  in abc.rc, not built in): strash, balance, rewrite, refactor, resyn, resyn2, compress2, dc2,
  dc2x2, lut4 (`dch; if -K 4`), lut6 (`dch; if -K 6`), lut6mfs (`dch; if -K 6; mfs -a`). Seeker1
  used 18; the set here is a stated subset. Each is applied to every clean and infected circuit
  (identity circuits as sources, not chained), the latch clock that ABC drops is written back, the
  result is checked equivalent to its source with `tools/equiv-check`, and gate / latch / depth /
  cube counts are recorded. Output is gzip. Per-restructuring rareness: observable activation
  (outputs differ from the clean circuit; equal across restructurings by construction, so it is
  a consistency check), the fraction of internal nets with min(p, 1-p) < 1e-2, and the rarest
  net's p, on the restructured infected circuit.
- **Seeker-Seq tuning** (`seqtune.py`): stated window N = 1024 cycles. One pass over the clean
  design (bit-sliced event counters for four candidate condition sets, pattern chains for three
  net orderings) gives P(fire within N) for every counter width b = 1..12 and pattern length
  L = 2..8 at once. Variants: counter and pattern x fast (P in [0.5, 1]), mid ([0.05, 0.5)),
  slow ([0.003, 0.05)); the largest b or L whose selection-sample probability lands in the band
  is built and re-measured on an independent sample, and accepted only if at least 3 lanes fire
  (P >= 3 / lanes; lanes are 2048 up to 3000 gates, 1024 up to 12000, else 512, so the
  resolvable floor is 1.5e-3, 2.9e-3 or 5.9e-3). Victim by observability: toggling outputs first
  (0.02 <= P(1) <= 0.98 over the run), quiet ones first among those, stuck value the minority
  value; a read output gets its own buffer (`blif_text.isolate_output`) so the payload cannot
  feed back (this fixes s298, s526, s953).
- **Bases added**: ITC-99 from ccsl-uaegean/ITC99-RTL-Verilog (GPL-3.0 per the repository's
  LICENSE; a vhd2vl conversion of the Politecnico di Torino ITC'99 VHDL; cloned read-only to
  external/ITC99-clone), VTR sequential Verilog diffeq1, diffeq2, sha (and_latch and single_ff
  are one-gate designs, left out). Through Odin III (`read_verilog; proc; opt; lower;
  write_blif --gates-as-names`). Odin III refuses b15, b17, b18, b19 ('TEMPORARY' assigned in two
  always blocks) and ch_intrinsics, mkPktMerge, mkDelayWorker32B, mkSMAdapter4B, boundtop
  (single_port_ram / dual_port_ram not defined); b20-b22 come out as multi-model BLIF (not
  handled) and are 49k-72k gates (over the 30000-gate cap). Odin III makes asynchronous resets
  synchronous (its warning, PHASE3 decision 19): the netlist differs from the RTL on reset
  timing.

## 9. Round 5: Odin III edit API, sim_tb, toggle counts (2026-10-31)

Odin III pin 7c04cfb2 (netlist edit API #309, simulation toggle counts and `run_vectors`, Verilog
testbench simulation #308). Purpose (hub docs/purpose.md, Leman Russ III R1): benchmark circuits
whose inserted structure is recoverable from provenance, and a second simulator for the RTL
trigger check. Measures: counts of edit-API insertions and provenance separation; sim_tb vs
iverilog agreement; toggle-count agreement.

- **Insertion.** `lemanruss/htl/edit_netlist.py`: a Trojan is a *recipe* over four primitives
  (`names`, `latch`, `splice`, `isolate`) with two editors: `EditNetlist` (Odin III edit API;
  every new net and node carries the edit tag `trojan:<Trojan id>`, read back as `edit_tag`) and
  `TextNetlist` (the old BLIF text edit, a fallback whose reason is stored in
  `answer_key/insertion.json`). `splice` moves the victim net's driver to `__htl_tmp_<victim>`
  (`Pin.disconnect` + `connect`); a latch is `add_node("$_DFF_P_")` with INIT set to 0 by
  `set_param_int` (a twin node, DERIVED provenance). A recipe applied by both editors gives the
  same function (tests/test_edit_netlist.py, 5 recipes x 512 lanes x 24 cycles).
- **Provenance.** `InsertReport` is read from the in-memory design before `write_blif`: tagged
  nodes and nets, untagged (clean) nodes, whether tagged nets are named `__htl*`. The tag is not
  in the written BLIF or in `write_json --odin3` (gap, section 9.2).
- **RTL check.** `rtl_tb.py`: per Trojan a testbench in the sim_tb subset (stimulus in arrays,
  `for`, `#10`, `$display`), 64 random vectors none matching an input-pattern trigger and one
  (index 32) that does. Run on clean and infected RTL under iverilog (oracle) and `sim_tb`;
  `tools/tb-compare` gives the first clean-vs-infected difference under `sim_tb`. Agreement =
  sim_tb output equals iverilog output on both designs (numeric fields) AND both first differences
  are at the firing vector.
- **Energy.** `energy.py`: toggle ring (5% of the gates) behind an always-on trigger;
  `Simulation.set_toggle_counting` / `toggles` per net vs `toggles_python` on the same stimulus
  (200 cycles; the first cycle is compared with the power-on state settled under all-zero inputs).
  Expected extra toggles per cycle = 2 x ring bits (Q and D flip every cycle).
- **Bases.** `bases.py` through `mimir bench` (`list --suite`, `fetch --kind netlist|source`).
  VerilogEval registry netlists are Yosys `abc -g NAND,NOR` output: cell definitions (NAND, NOR,
  NOT, BUF, DFF) are prepended and the top is given with the Odin III CLI `--top RefModule`.
- **Restructurings.** 12 (round 4) + 6: resyn2a, resyn3, resyn2rs, compress, resub, lut5 = 18.
  Seeker1's own list of 18 was not read; these are ABC standard scripts plus one LUT size.

### 9.1 Agent defaults (round 5)

(24) latch = `$_DFF_P_` with INIT 0 (the text `.latch ... 0`); (25) inserted nodes anonymous,
tracked by output net and tag; (26) edit tags read from the in-memory design (not persisted);
(27) VerilogEval combinational bases need >= 8 gates, VTR Verilog has none to keep; (28) HDL
Trojans for the sim_tb check use an input-pattern trigger on 10 randomly chosen input bits and
ignore assigns inside `//` comments; (29) a design whose iverilog output contains x/z is skipped
(sim_tb is 2-state); (30) the 6 extra restructurings are ABC's standard scripts, not Seeker1's list.

### 9.2 Odin III gaps found (recorded for the controller, nothing changed in Odin III)

1. Edit tags are not persisted: `write_blif` drops them (expected) and `write_json --odin3`
   shows no `edit` provenance either, so a detector reading the exported graph cannot tell
   inserted cells from clean ones; the answer key must carry the list (it does, in
   `insertion.json`).
2. `Pin.disconnect` / `rewire` leave no mark on the nodes whose pins moved (the victim's original
   driver): provenance records created nodes and nets, not modified connectivity.
3. `add_node("$_DFF_P_")` creates INIT 3 (unset); setting 0 needs `set_param_int`, which returns a
   twin (new ID, DERIVED record). A creation-time INIT argument would avoid the twin.
4. `Design.run_script` has no way to give the top module before `read_verilog` (`hierarchy --top`
   first fails: "the design has no modules"; `--top` is only a CLI option), so a file with several
   free modules (a cell library plus the design) needs the CLI binary.
5. VTR Verilog designs that use `single_port_ram` / `dual_port_ram` (ch_intrinsics, boundtop,
   raygentop, mk*, or1200, ...) do not read (module not defined); `vtr_flow/primitives.v` defines
   only post-synthesis cells. All 31 registered VTR Verilog designs are sequential or unreadable:
   there is no combinational VTR Verilog base.
6. `sim_tb` is 2-state: designs for which iverilog prints x/z (out-of-range selects) cannot be
   compared (2 of the 60 combinational VerilogEval references).

## 12. Round 7: Seeker-Proc pilot (2026-11-01)

Odin III main 0d3d735a (library `build/rel-main/libodin3.so`). Purpose (hub docs/purpose.md,
Leman Russ III R1): the third Seeker family, processor Trojans, on the two processors Odin III
already runs end to end (`tests/mcu`, `tests/darkriscv`). Peter 2026-10-31: "the riscv is based
off this work, so the infrastructure should work"; this is a **pilot**, not v1's taxonomy or
numbers. Report
rareness, not insertion quality (unchanged house rule). Results: docs/results-round7.md.

### 12.1 RV32I encoder

No cross RISC-V toolchain is installed in this workspace. `lemanruss.htl.rv32i` hand-encodes the
handful of RV32I instructions a witness program needs (ADDI, JAL, SW, LUI), each function citing
the RISC-V Unprivileged ISA spec section (2.2 base formats, 2.3 immediate encodings) and checked
against a known encoding (the canonical NOP `addi x0,x0,0` = `0x00000013`, the `jal x0,0`
self-loop, a round-tripped S-type/J-type immediate).

### 12.2 Insertion: both cores, the core not the RAM arrays

Found by reading the RTL, not guessed. mcu (`single_cycle_core.v`): the trigger compares
`instruction` (the fetched word, `fetch_receive.v`'s output); the payload rewires the
`fetch_issue` instance's `next_PC_select` input through a new mux that forces `2'b01`,
`fetch_issue.v`'s own documented stall encoding ("2'b01: Stall (PC = PC)") -- `p-dos-stuck`
applied to the core's own stall control. darkriscv (`darkriscv.v`): the trigger compares `IDATA`
qualified by `IDACK` (IDATA is a valid fetch only when IDACK is high); the payload ORs into the
core's own synchronous self-reset register, `XRES <= RES || __htl_trigger` -- `p-dos-reset`, not
`p-dos-stuck` on `HLT`. **Agent default (44)**: a first attempt used `p-dos-stuck` on darkriscv's
own `HLT` wire, the same shape as mcu; measured that `HLT` only holds off the *next* instruction
fetch, so in this pipelined core the instruction right after the magic word had already been
fetched and still completed (a witness `sw` one slot after the magic word still wrote its value,
confirmed under iverilog). Forcing the core's own reset register is not sensitive to pipeline
depth and was verified to work (witness fire check, section 12.4).

Trigger kinds: `t-input-pattern` (one magic word, a plain comparator) and `t-seq-pattern` (a
magic sequence of k words, a small FSM that advances in order and resets to 1 if the first word
of the sequence reappears out of sequence, firing combinationally -- not sticky -- on the cycle
the last word is seen). **Agent default (45)**: error-insertion payloads (`p-err-hi`/`p-err-lo`
on register write-back or a data-bus write) and netlist-level insertion are out of this pilot's
scope (time-boxed; the Trojan's own HDL-level insertion plus full verification per base was
the round's deliverable) -- recorded as a deferred axis, not attempted and silently skipped, not
an Odin III gap.

### 12.3 Rareness

Per spec section 2 item 2, four measures, all defined for a magic-word/sequence trigger except
(iv) (a counter trigger measure; this pilot inserts none):

(i) P(fire) over the shipped programs: measured by running the infected design against mcu's
`blink`, `blink_interrupt`, `blink_function_call`, `interrupt` and darkriscv's prebuilt firmware
(`src/darksocv.mem`) and diffing the trace against the clean design under the same simulator; a
Trojan that fires there is dropped and listed (none was, section 12.5/results-round7.md). (ii)
match probability: `2**-32` per magic word, `2**-(32k)` for a k-word sequence (exact, by
construction: a uniformly random fetched word matches with that probability, independent of the
rest of the design). (iii) SCOAP CC0/CC1/CO of the trigger net, from Odin III's `scoap` pass
(schema `odin3-scoap` v2) on the written netlist. **Agent default (46)**: the trigger's own net
has no stable, predictable BLIF name (Odin III lowers the Verilog comparator into several
anonymous `$nNNN` nets); `lemanruss.htl.proc_rareness.find_trigger_net` locates it from the
`.cname __htl_trigger.<op>` tags `write_blif` attaches to every cell of that assignment, taking
the *last* such tag (always the top-level operation) and its enclosing `.model` (net names are
model-local, so the net name alone is not enough: mcu's top module happened to also hold an
unrelated net of the same auto-generated name as the trigger's inside the `single_cycle_core`
instance -- a false match was caught this way before it reached a report). (iv) not defined for
these two triggers; not reported.

### 12.4 Witness and verification

A witness program per base: a handful of `ADDI`/`NOP`/`LUI`/`SW`/`JAL` words (section 12.1),
ending in a self-loop, that carries the magic word(s) as one or more of its instructions (mcu) or
after the usual two NOPs (darkriscv). mcu's witness is observed on `PC` (stuck below the
self-loop's address when infected, vs reaching it when clean); darkriscv's writes a marker value
to `OPORT` (`darklibc/include/io.h` offset 0x18 off `darklibc/io.c`'s base 0x40000000, confirmed
against the bus decode `XADDR[31:30]==1` selects `darkio` in `darksocv.v`) after the magic word,
observed directly in `dark_tb.v`'s own trace (never written when infected). Fire check: infected
differs from clean on the witness program; with the trigger absent (the shipped-program runs) the
traces are identical. Run three ways per the brief ("both bases run under Odin III sim_tb, RTL
and netlist equal to iverilog"): iverilog (oracle), Odin III RTL (`read_verilog; proc; opt; lower;
sim_tb`), Odin III netlist (`write_blif` then a fresh `read_blif; sim_tb`); all three agree on
both the clean and the infected design (results in docs/results-round7.md).

Equivalence (trigger forced inactive, spec section 4(c)): `proc_insert.py`'s `force_inactive=True`
ties `__htl_trigger` to `1'b0` while leaving the payload's mux/OR wiring in place. Both bases
`lower` their RAM/BRAM arrays to tens of thousands of per-bit latches with no target
architecture (no `read_arch` in this round, per the brief's "no VPR"), so `tools/equiv-check`'s
ABC `dsec` run is large: **state the timeout** (spec section 4(c)) -- mcu unproven at the 300 s
wrapper used here, darkriscv `unproven: ABC dsec timed out after 600 seconds` (its own internal
limit). Neither is a pass or a fail; both are reported as unproven per the spec's rule ("never
report unproven as pass").

### 12.5 Release: Seeker-Proc v2.0-pilot

Shaped differently from the Seeker-Comb/Seq families (`lemanruss.htl.proc_release`, verbs
`proc-release`/`proc-verify`, not the family `release`/`verify`): the upstream design is never
redistributed (CLAUDE.md: never commit `external/`'s content), so a circuit here is the one
patched RTL file plus the witness program image, not a BLIF catalogue entry. **Agent default
(47)**: the label scrub (spec section 10.2's problem recurs: the patch names its own
`__htl_trigger`/`__htl_pc_mux`/`__htl_seq_state` wires) replaces every `__htl_*` identifier with
a plain `_insN` counter name, not styled to the base's own naming the way the family release's
`[N]`/`$nN` scrub is -- simpler is enough for a one-file preliminary release; the map is
reversible (`unscrub`) and `proc-verify` re-scans every detector-visible file for `htl`/`trojan`/
`odin3_edit` after unpacking.

**Superseded 2026-11-01 (fix round, docs/results-round7.md section 10):** this release leaked
circuit/trojan identity through directory names and manifest keys (`circuits/
proc-mcu-magicword-stall/`), even though the content-level checks above passed, and released no
clean circuit (every circuit was infected). `seeker-proc-v2.0-pilot2` replaces it: the
detector-visible form is the lowered netlist (`--gates-as-names`, not the patched RTL file),
clean and infected per trojan, opaque ids (`pp0001`...), scrubbed with the family's own
`scrub_group` (styled to the circuit's own clean twin); `verify_proc_release` gained
`check_name_vocabulary` (directory/file/manifest-key names against a label-word vocabulary,
folded into its `ok`), and a new `verify_proc_pilot2` checks the pilot2 schema directly. ABC
restructuring of the processor netlists (an unattempted axis in the pilot) was attempted and
found to fail deterministically at ABC's `read_blif` for both bases (a genuine sequential loop
in darkriscv's lowered netlist; a BLIF-reader/hierarchical-naming mismatch for mcu's); recorded,
not released, not an Odin III bug.

## 10. Release (v2.0-rc1, 2026-10-31)

Purpose: the Seeker v2.0 families are Leman Russ III's product (Peter 2026-10-31: test the
benchmarks and, if good, commit and back them up). A release is the unit a user fetches and
checks; it is independent of the build tree. This is release candidate rc1: the final v2.0 follows
after later rounds add ITC-99 b15-b19, the VTR designs and Seeker-Proc.

### 10.1 What a release holds

One release directory per family (`seeker-comb-v2.0-rc1`, `seeker-seq-v2.0-rc1`):

    circuits/<id>.blif.gz   every circuit the detector sees: clean and infected, the 19 forms
                            (identity + 18 ABC restructurings) of each; opaque ids; gzip with a
                            zero timestamp so the bytes are reproducible
    answer_key/             labels.json (id -> trojan id or null), provenance.json (source,
                            restructuring, clean twin, victim, stuck value, window), renames.json
                            (neutral name -> original inserter name, per circuit), rareness.json,
                            insertion.json, failures.json (variants that could not be built),
                            restructured.json (build-time equivalence verdicts), catalogue.json
                            (trojan catalogue and the clean / infected mix)
    manifest.json           family, version, seed, tool versions, counts per base and per
                            restructuring, one entry per circuit (id, base, file, bytes, sha256);
                            no label, no catalogue, no mix
    SHA256SUMS              `sha256sum -c` format over every other file of the release
    DATASHEET.md            family, lineage, bases and licences, counts, rareness bands,
                            restructurings, the unproven equivalence, tool versions

The detector may read `circuits/` and `manifest.json` only. A circuit never carries its label.

### 10.2 Label scrub (found while testing rc1)

The round 5 build output leaks the answer: every infected circuit holds inserter-named nets
(`__htl_trigger`, `__htl_tmp_<victim>`, `__htl_c_*`, `__htl_s_*`, `__htl_energy_*`,
`__htl_slow_*`, and `<victim>__htl_pre` for an isolated port), and in Seeker-Seq the ABC
restructured variants keep the latch names. `lemanruss release` therefore renames every token
containing `__htl_` to a neutral internal name in the style the clean circuit already uses
(`[N]` in Seeker-Comb, `$nN` in Seeker-Seq), N drawn at random from unused numbers. One map per
source circuit, applied identically to the source and to all its restructured variants (ABC
equivalence pairs latches by name). The map is saved in `answer_key/renames.json`; applying it
backwards must give the build file byte for byte, and `lemanruss verify` re-checks that function
and the leak scan on the packaged files. The `#` banner ABC writes into every restructured
circuit (it carries a time stamp) is dropped as well; the first verify run of rc1 flagged it as a
comment, and a time stamp is metadata a detector should not have. Residual structure (an extra mux in front of the victim,
extra latches) is the Trojan itself, not a label.

### 10.3 `lemanruss verify <release-dir>`

Re-reads everything from disk (no build state), with the answer key used only to know what to
check. The command that checked a build tree in round 4 is now `lemanruss family-verify`.

a. Integrity: `SHA256SUMS` lists exactly the files on disk and every hash matches; manifest sha256
   and size equal the files; counts per base and per restructuring equal the manifest.
b. Label leak: each circuit (decompressed) is scanned for `htl`, `trojan`, `trigger`, `payload`,
   `ht_`, `infect`, `clean` (case-insensitive), `.attr`, `#` comments, every trojan id, trigger and
   payload kind in the catalogue and the edit tag text. A hit that the clean circuit of the same base
   also holds is a name native to the base and is listed, not counted; any other hit is a leak. The
   names that exist only in infected circuits (compared with the clean twin; for restructured
   variants with the infected source) must match a name style present in the clean twin. One leak
   fails the release.
c. Function, all infected circuits of the identity form: the witness found by the bit-parallel
   simulator is replayed in Odin III on the clean and the infected circuit (trigger high, victim =
   stuck value, clean victim differs: the payload changes an output); with the trigger net driven
   by constant 0 the circuit is ABC-equivalent to its clean twin (`tools/equiv-check`, cec / dsec,
   600 s). Every restructured variant is ABC-equivalent to its source (all 5310, not a sample: the
   full run is under the 4 h limit). `unproven` (timeout) is reported as such, never as pass.
d. Rareness: 10% (at least 1 per stratum) of the infected identity circuits, stratified by target
   band / variant, are re-measured from a fresh seed: Seeker-Comb activation probability on 2^20
   vectors (exhaustive when the design has at most 20 inputs: must equal exactly), Seeker-Seq
   P(trigger high within N cycles) for N = 16, 64, 256, 1024 on the stored lane count. Pass when
   |new - manifest| <= 5 sigma of the difference of the two binomial estimates (plus 1e-9).
e. Separation: no label, catalogue or mix in `manifest.json` or `circuits/`; ids opaque; the clean
   circuits are `null` in `labels.json`; every circuit id is labelled.

### 10.4 Back-up

One `tar | xz` per family and part (`circuits/` with manifest, SHA256SUMS and DATASHEET; and
`answer_key/`) under `<archive>/2026-10-31/` with a `SHA256SUMS` checked by
`sha256sum -c`, entry counts equal to the source, `tar -d` clean, and an entry in the archive
README. Nothing on F: is deleted. A release with a failed check or a leak is not backed up.

### 10.5 Agent defaults (release)

(31) The round 4 `verify` command is renamed `family-verify`; `verify` takes a release. (32) The
release packs every form in `circuits/` as `.blif.gz` (one format for identity and restructured, so
the extension says nothing). (33) The label scrub of 10.2. (34) Manifest carries per-circuit hashes,
SHA256SUMS the rest. (35) Rareness re-measure uses a fresh seed and a statistical tolerance rather
than the build seed, so it is independent of the build's random stream. (36) Licences are quoted as
Mimir records them; ISCAS-85, ISCAS-89 and ITC-99 are not in `licences.toml` and are stated as
"licence unread"; MCNC is `none-stated`.

## 11. Round 6: new bases, edit-event provenance, release v2.0-rc2 (2026-10-31)

Odin III main 42394c3d (#310 project testbenches, #311 front-end triage, #312 edit gaps), library
`build/rel-main/libodin3.so`. Purpose (hub docs/purpose.md, Leman Russ III R1): grow Seeker-Seq with
the designs the Odin III fixes of 2026-10-31 unlocked (ITC-99 b15 to b22, five VTR designs), keep the
edit-event provenance in the answer key where a detector cannot see it, and release rc2.
Results: docs/results-round6.md.

- **API.** `add_node("$_DFF_P_", None, tag, params={"INIT": 0})` replaces the
  `set_param_int` twin (gap 3 of 9.2 closed: no DERIVED twin, the node is `added`). `Pin.disconnect`
  and `Pin.rewire` are called with the Trojan tag, so a victim's old driver and every moved reader
  carry a `removed` / `rewired` event (gap 2 closed). `InsertReport` counts them as
  `modified_nodes`; untouched + modified = clean nodes.
- **Events stay internal.** `edit_netlist.insert(..., events_dir=...)` writes the detector-visible
  circuit with plain `write_blif` and a second file with `write_blif --edit-tags` into
  `answer_key/edit_events/<id>.edit.blif` (gap 1 closed for the answer key). The release packs
  these as `answer_key/edit_events/<id>.edit.blif.gz` for the infected identity circuits only.
  `lemanruss verify` check (b) now also fails a release when any circuit or `manifest.json`
  holds the text `odin3_edit` or `odin3 edit` (counted and printed in the report); the `.attr`
  and `#` checks stay.
- **Lowering of designs that need an architecture or hierarchy** (`build.lowering_script`):
  VTR designs: `read_arch <k6_frac_N10_frac_chain_mem32K_40nm.xml>; read_verilog --vtr-compat F;
  proc; opt; flatten; opt; unmap; lower; write_blif --gates-as-names` (triage note issue 2; the
  `unmap` makes the `single_port_ram` / `dual_port_ram` hard blocks soft logic again). ITC-99:
  the same without `read_arch` / `unmap`. `flatten; opt` is added because b17 to b22 instantiate
  b15 and b14 (a `.subckt` per instance: the bit-parallel reader needs one flat model), and
  `--top <stem>` because b17.v also holds a free module b15; `write_blif` writes the top first and
  then every other module, so `bases.keep_first_model` keeps the first model only.
  `lemanruss hdl2blif --flatten --top-stem --arch X` runs it in a memory-capped subprocess.
- **Cap.** `--max-blocks` 30000 (round 4) is raised to 700000 gates. The measured costs (build,
  one process, 6 in parallel) are in docs/results-round6.md: b19 (638552 gates, 12726 flip-flops)
  needs 46 min and 3.3 GB, 33 min of it in Odin III's sequential SCOAP. mkDelayWorker32B
  (1103505 gates + 539458 flip-flops = 1.64M cells) is above the cap: a trial run reached
  9.9 GB resident in the Python reader/compiler within 3.7 minutes and was stopped (limit 10 GB).
- **Build robustness.** `run_family(..., workers=N)` runs the bases in a fork pool, largest file
  first; circuit ids depend only on the base's position (1 clean + 6 variants), so a pooled run
  equals a serial one. A base that raises (Odin III refuses boundtop's scoap) becomes one Failure
  per variant, and its result is cached in `answer_key/jobs/<base>.pkl`. The first pooled attempt
  hung because `Odin3Error` does not unpickle (see 11.2).
- **Clock of the inserted logic.** `_clock_of` takes the first rising-edge (`re`) flip-flop's
  clock, not the first latch's: ch_intrinsics and boundtop hold level-sensitive latches
  (`ah` / `al`) whose enable is logic, never a clock for the Trojan.

### 11.1 Agent defaults (round 6)

(37) `flatten; opt` and `--top <file stem>` for the new bases (the brief's script has neither;
b17 needs both). The VTR designs ch_intrinsics and boundtop have other top names (memset,
paj_boundtop_hierarchy_no_mem): Odin III's own choice is used. (38) Cap 700000 gates, 10 GB
resident per process as the stop rule; mkDelayWorker32B is not built. (39) Edit events:
`write_blif --edit-tags` for every infected identity circuit, in the answer key; the
`write_json --odin3` form is not written (same content). (40) Seeker-Comb is not re-released: no
unlocked design is combinational, so rc1 stays the current Comb release. (41) Restructuring,
equivalence and rareness exactly as round 5 (ABC 300 s, cec 600 s, 512 / 1024 / 2048 lanes by
size). (42) `lanes_for` (512 lanes above 12000 gates) and the candidate / band search of `seqtune` are
unchanged for the big designs; the counter bands are then unreachable on all of them (see
results). (43) A base is released only when all 19 forms exist and each has a proof or a stated
timeout: b19 (ABC timeout on every restructuring), boundtop and ch_intrinsics (equiv-check refuses
level-sensitive latches) are built but left out (`lemanruss release --exclude-base`).

### 11.2 Odin III gaps found in round 6 (recorded for the controller, nothing changed)

1. `Odin3Error` cannot be unpickled (`TypeError: Odin3Error.__init__() missing 2 required
   positional arguments: 'status' and 'name'`). An Odin III error raised in a
   `multiprocessing` worker kills the pool's result thread in the parent and the pool hangs.
   Leman Russ now catches it in the worker; the class needs `__reduce__` or a single-argument
   constructor.
2. `scoap` (sequential) on boundtop: `boundtop.blif:53878: cannot simulate: combinational loop
   through net $n25718`. `bitsim` finds no loop in the same file (it breaks loops only at latches),
   so the loop passes a latch; the lowered netlist keeps 878 level-sensitive `ah` / `al` latches
   of its 35015 (not traced further).
3. `scoap --seq` on b19 (651325 nets) took 33 to 44 minutes (1226 sweeps, 603741 unreachable).
4. `write_blif` after `--top` still writes every unused module after the top.
5. `lower` warns "asynchronous reset/set/load made synchronous" on ITC-99 (3760 bits in 178 cells
   for b17), as expected (PHASE3 decision 19); the netlists differ from the RTL on reset timing.

## 13. Round 9: rc7 magic-number triggers (2026-11-02)

Peter 2026-11-02, verbatim: "Make the sequential triggers simple magic number triggers. Then we
don't have to worry about the FF hiding". Replaces the retiming plan
(`briefs/lemanruss-seq-rc7-retime.md`, cancelled). Purpose (hub docs/purpose.md, Seeker v2.0 Seq
family, RQ: detector AUROC vs the size control, leak gates): on Seq rc5/rc6 the class-only
detectors reach AUROC 0.98-1.00 because infected circuits carry the Trojan's own counter/FSM
flip-flops (`t-seq-counter`, `t-seq-pattern`; flip-flop count AUROC 0.948 on rc6, memory
seeker-v2-families). rc7's Trojan adds ZERO flip-flops and zero latches, Seq and Proc alike.

### 13.1 Trigger

`StatePatternTrigger` (`t-state-pattern`, `lemanruss/htl/triggers.py`): an AND of `k` literals
over EXISTING signals of the host -- register (flip-flop) Q outputs and/or primary inputs, each
at a chosen value -- same shape as `CombRareTrigger` (`t-comb-rare`), but its candidate pool is
host state and inputs, not combinational-internal nets, and its own kind id keeps it distinct in
every report/label. The comparator is purely combinational: at netlist level it is
`lemanruss.htl.edit_netlist.comb_rare_trigger` unchanged (an AND SOP of literals, `ed.names`,
never `ed.latch`); `InputPatternTrigger`/`insert_input_pattern_trigger` already has the same
shape at HDL level and is reused as-is for any HDL-level rc7 work, per the brief ("reuse
InputPatternTrigger... or add a sibling"). `t-seq-counter` and `t-seq-pattern` stay in
`triggers.py`/`edit_netlist.py`/`seqtune.py`, unused by the rc7 build path.

Candidate literals: `lemanruss.htl.seqtune._state_candidates` reads every latch Q net
(`lemanruss.htl.bitsim.latches_of`) and every primary input, ranks by SCOAP difficulty (the
sequential `scoap_table` already computed for the base) then by rareness over a scan-view random
sample (`simulate_comb`, which already randomises latch Q values -- SCOAP's own combinational
mode, used unchanged), exactly the `_Cand`/`widen_trigger` pipeline `seeker._candidates` already
uses for `t-comb-rare`, just over a different net pool. `lemanruss.htl.seqtune._cond_sets` widens
these into AND combinations at several quantiles (unchanged).

### 13.2 Reachability and rareness

The scan-view selection sample approximates independence; the real figure comes from the
existing multi-cycle window observation (`lemanruss.htl.seqtune.observe`, N = WINDOW = 1024
cycles, the band `lemanruss.htl.seqtune.SEQ_BANDS` rc6 used: fast [0.5, 1.0), mid [0.05, 0.5),
slow [0.003, 0.05)). `observe`'s bit-sliced counter per condition set already accumulates "this
bit of the count has been seen" (`ge[j][b] |= pl[b]`) for b in 1..12; extended to b = 0 too (a
counter's bit 0 goes high, and stays OR'd true, the first time the condition is ever seen, so
`ge[j][0]` is exactly "fired at least once by cycle N" -- purely additive, the existing b in
1..12 readers (`_candidates_in_band`, the `t-seq-counter` kind) are untouched). A magic-number
Trojan is dead if the chosen value is never reached (`ge[j][0]` all-zero): rejected before build,
same as rc6 rejected an unreachable counter/pattern. `_candidates_in_band_magic` picks, per band,
the LARGEST k (rarest) AND combination whose `ge[j][0]` hit rate over the selection sample lands
in the band, re-measured on an independent sample exactly as `t-seq-counter`/`t-seq-pattern` are
(`build_seq_variant`'s existing re-measure-and-accept-or-retry loop, kind `"magic"` added
alongside `"ctr"`/`"pat"`). SCOAP and the simulated probability are reported the same way
(`RarenessRecord`, `seq_table_rows`).

Victim exclusion (found in the first full build, 17 of 36 bases): when the payload's victim is
itself a register Q or input that is also a trigger literal (b02's output `u` is a flip-flop),
the inserted payload re-drives that net and the trigger would read the payload's own output, a
combinational loop (`bitsim: combinational loop or undriven net`). `SeqCtxRc7._draw_triggered`
therefore redraws (up to 24 times) when the victim is in the trigger's net set.

### 13.3 Payloads

Checked against `edit_netlist.py`'s recipes (the netlist-level editor the Seq build uses):
`dos_stuck`, `err_bit`, `slowdown`, `slowdown_absorb` use only `ed.names` (no `ed.latch`) -- zero
added state, kept for rc7. `energy` calls `ed.latch` once per toggle bit (a free-running register
chain) -- `p-energy` is EXCLUDED from Seeker-Seq rc7 (and Seeker-Proc pilot3): the one payload
kind in `payloads.py` that adds flip-flops. `p-dos-reset` (`insert_dos_reset_payload`/the
netlist equivalent) reduces to `dos_stuck` on the reset net -- no added state either, kept.
Seeker-Seq rc7 keeps the family's existing payload choice (`DosStuckPayload` on an
observability-chosen victim, `lemanruss.htl.seqtune.choose_victim`) unchanged.

### 13.4 FF/latch equality hard gate

Per infected circuit, before ABC: `len(lemanruss.htl.bitsim.latches_of(infected_model)) ==
len(lemanruss.htl.bitsim.latches_of(clean_model))`, exact. `RarenessRecord` gains
`ff_count_clean`/`ff_count_infected`; a mismatch is a build Failure (not a Built circuit), logged
with the counts -- this is a correctness invariant for the `t-state-pattern`/`comb_rare_trigger`
+ kept-payload combination (section 13.3), expected never to trip, not a tuned target.

### 13.5 Seeker-Proc pilot3 (brief "ADDED 2026-11-02: Seeker-Proc too")

Seeker-Proc's own `t-input-pattern` (one magic fetched word, `lemanruss/htl/proc_insert.py`
`_trigger_decl` with `len(magic_words) == 1`) is already combinational and adds no state; it is
kept unchanged. Its sibling `t-seq-pattern` (`len(magic_words) > 1`, a small FSM,
`__htl_seq_state`) DOES add a register and is DROPPED from the pilot3 trojan set (stays in the
code, per the brief, unused by the pilot3 plan): pilot2's `proc-mcu-magicseq3-stall` trojan is
not rebuilt for pilot3. pilot3 keeps `proc-mcu-magicword-stall` (mcu, `p-dos-stuck` on the core's
own stall mux) and `proc-dark-magicword-reset` (darkriscv, `p-dos-reset` ORed into the core's own
`XRES`): both payloads reuse an existing register/mux input, add no state (checked against the
RTL patch text in `proc_insert.py`, not assumed). A second magic-number kind on an existing data
value (e.g. a register write-back or data-bus write value) was looked at and not added this round
(time-boxed, same axis `docs/results-round7.md` section 12.2's agent default 45 already deferred
for the error-insertion payloads) -- recorded, not silently skipped. Same FF/latch equality hard
gate as section 13.4, per circuit, against each base's clean twin.
