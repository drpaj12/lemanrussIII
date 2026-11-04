# Detector baselines on Seeker v2.0: design (2026-11-01)

Question (Peter, 2026-11-01): how do the current hardware Trojan detectors do on Seeker v2.0.
Purpose: Leman Russ benchmark validity (a benchmark is useful when it separates detectors).
Measure: the Common protocol of the paper's methods section (kept locally by the author) (TPR, FPR at FPR <= 5% on
validation, F1 at release prevalence and re-weighted, AUROC, W/L/T against the size-only
control, bootstrap over bases). Code: `lemanruss/detect/`. Results: `docs/results-detectors.md`.

## 1. Rules carried from the brief

- A detector sees one circuit at a time: the released `circuits/<id>.blif.gz` only. Never the
  answer key, never the raw `htl-out`. Labels, bases, forms, sets and Trojan counts come from the
  answer key and are used by the harness for splitting and scoring only.
- The detector interface enforces this: `fit` and `score` receive `CircuitFile(id, path)`; no
  base, no form, no clean twin. The one exception is Method B (reference-assisted by definition),
  which declares `needs_reference = True` and receives a `ReferencedFile` (adds the form and the
  path of the identity-form clean reference of the circuit's base).
- No LLM, no VPR. CPU only. Jobs <= 4, memory <= 10 GB.

## 2. Data

| Family | Release | Circuits | Bases | Notes |
|---|---|---|---|---|
| Seeker-Comb | rc1 | 1596 (589 clean, 1007 infected) | 31 | 19 forms, one Trojan per circuit |
| Seeker-Seq | rc2 | 4389 (912 clean, 3477 infected) | 48 | 19 forms, one Trojan per circuit |
| Seeker-Proc | pilot2 | 6 | 2 | identity only; held-out challenge, raw outcomes |
| Seeker-Comb | rc4 (round 8) | 5756 (31 goldens) | 31 | n = 300 per golden: three obfuscated sets K4, K6, G; 10-70% infected per set; 1-3 Trojans; no forms, no set A. rc3 is NOT used (label leaks, see section 8) |
| Seeker-Seq | rc4 (round 8, superseded) | 10375 (36 goldens) | 36 | as Comb |
| Seeker-Seq | rc5 | 10375 (36 goldens) | 36 | as rc4 with the latch init leak fixed (lemanrussIII #13); the headline Seq release |

Release trees are read where the release tooling leaves them (`work/htl-rel/<release>`,
`work/htl-out/det/data/<release>` for pilot2, extracted from the F: archive). The metadata the
harness reads from the answer key: `provenance.json` (`base`, `restructuring`, `role`,
`clean_twin`, `insert`), `labels.json` (cross-check only), `sets.json` (rc3).

## 3. Common protocol (s6-methods.tex, exactly)

- Unit: the circuit; positive class infected (at least one Trojan).
- Splits by base: bases of a family shuffled with `random.Random(1)`, cut into five folds of
  near-equal size, stratified by source (ISCAS, MCNC, VerilogEval, ITC-99, VTR): the bases of each
  source are shuffled with seed 1 and dealt round-robin over the five folds, continuing the
  rotation across sources so fold sizes differ by at most one. Fold `k` is test, fold `(k+1) mod 5`
  is validation, the other three train. The source of a base comes from a name rule
  (`C<digits>` ISCAS-85, `s<digits>` ISCAS-89, `b<digits>` ITC-99, `ve_*` VerilogEval, the nine
  MCNC names, the VTR names); an unknown name is an error, not a silent default.
- Seeds 0 to 4 fix model initialisation and mini-batch order; folds are fixed by seed 1. Detectors
  with no randomness (size-only, rare-signal, Method B) run once and the same numbers stand for
  every seed.
- LUT-form split: train forms are the 15 forms other than `lut4`, `lut5`, `lut6`, `lut6mfs`; the
  test forms are those four, on the test-fold bases. Validation = the validation-fold bases in the
  15 training forms (the unseen form cannot be used for tuning without leaking it).
- Seeker-Proc: not split; a model trained on all Comb and Seq circuits (the detector's
  full-training fit) scores the six circuits; raw outcomes printed.
- Metrics per (detector, family, split, fold, seed): AUROC (rank based, ties 0.5); threshold =
  lowest score such that the validation clean circuits at or above it are <= 5% (flag when
  `score >= threshold`); TPR and FPR at that threshold on the test fold; F1 at release prevalence
  (the test fold's own) and re-weighted to 10, 30, 50, 70 percent infected
  (`P = pi*TPR / (pi*TPR + (1-pi)*FPR)`, `F1 = 2PR/(P+R)`, with TPR and FPR as measured, so
  the re-weighting needs no resampling). Means over the five folds and the seeds.
- Intervals: 95% bootstrap (1000 replicates, seed 0) resampling bases with replacement inside each
  test fold, recomputing the fold AUROC, averaging over folds.
- W/L/T: for every base (each is a test base once) the AUROC of the method versus the AUROC of
  the size-only control, within the base, seed-averaged score; W if higher by more than 1e-6, L if
  lower by more than 1e-6, else T. Bases that lack either class are skipped and counted.
- Breakdowns: family; rareness band (Comb `insert.variant`, Seq the six variants and
  P(fire<=N) buckets from `rareness.json`, Proc the three Trojans); the 19 forms; set A/B and
  Trojan count (1, 2, >=3) for rc3. Cell AUROC: positives = infected circuits in the cell,
  negatives = clean circuits of the same test folds (restricted to the same form when the
  breakdown is by form); cells lacking a class are reported as n/a.
- Reporting follows the project convention: headline geometric-style summary first (W/L/T and
  AUROC), then the strict label. An AUROC interval touching 0.5 is INCONCLUSIVE, not DISMISSED.

## 4. Detectors

| id | module | What | Seeds |
|---|---|---|---|
| `sanity` | `detect/sanity.py` | exact-duplicate lookup (sha256 of the decompressed BLIF against the rest of the release) plus local style counts (double inverter, double buffer, buffer share, constant-driver share), logistic regression. Controller addition 2026-11-01: on a good release it must sit near chance; reported next to every detector, because a detector that beats it only by style is not detecting Trojans | none |
| `size` | `detect/size_only.py` | logistic regression on log1p(gates), log1p(depth), log1p(FFs), standardised, L2 (lambda 1), class-balanced, IRLS in numpy | none |
| `rare` | `detect/rare_scoap.py` | rare-signal / SCOAP score in the line of COTD | none |
| `gnn-yasaei` | `detect/gnn.py` | gate-level GNN as read in yasaei2022gnn | 0-4 |
| `gnn-a` | `detect/gnn.py` | Method A of s6-methods.tex (SAGE, SCOAP and probability features) | 0-4 |
| `graphlet-b` | `detect/graphlet_b.py` | Method B, directed graphlet drift against the clean identity reference | none |

Netlist features common to all (`detect/netlist.py`): a BLIF parser over the released file. Gates =
`.names` with at least one input (constants and buffers of constant excluded), FFs = `.latch`,
depth = longest combinational path in gates from primary inputs and latch outputs. For hierarchical
netlists (Proc) gates and FFs sum over all models, and the graph is the top model with every
`.subckt` as one node.

### 4.1 size-only
As specified in s6. Uses gates, depth, FFs of the circuit only.

### 4.2 rare / SCOAP (COTD line)
COTD (salmani2017cotd, TIFS 2017, title: reference-free Trojan detection from controllability and
observability in a gate-level netlist). The full text of COTD was not read (paywalled); this is
not a reproduction, it is a rare-signal baseline built on the same two quantities. Score: from
Odin III `scoap` (combinational for Comb; `--sequential` for Seq, signal probability on 4096
vectors seed 1) take per net the controllability to its harder value `c = max(cc0, cc1)` and
`co`, both capped at 1e9 and log1p-transformed; the score of a circuit is the share of nets whose
robust z (median and MAD within the circuit) exceeds 3 in both `c` and `co`, plus the share of nets
with `min(p1, 1-p1) < 0.01` when the simulation ran (a netlist the simulator refuses keeps only the
first term). An Odin III failure on a circuit is recorded as "not scored", never imputed.
Circularity: the benchmark's site selection
ranks nets by SCOAP and signal probability to place triggers (s6 Section Method B, "Which second
method"), so this score can see the trigger by construction. Reported next to every number.

### 4.3 GNN
Data-flow graph from the BLIF: node per `.names`, latch, primary input, primary output, edge from a
net's driver to each reader.
- `gnn-yasaei` (read in yasaei2022gnn arXiv 2204.11431: node feature = one-hot of a normalised
  node class, 17 classes; three graph-convolution layers, 55 hidden units; self-attention graph
  pooling, ratio 0.6; readout then MLP; dropout 0.5 after each layer; 200 epochs, batch size 2,
  learning rate 0.001; leave-one-base-out). Our classes (17): input, output, latch, constant, buffer,
  inverter, AND, NAND, OR, NOR, XOR, XNOR, MUX-like, other 2-input, other 3-input, other >=4-input
  or LUT, subckt. Layers `GCNConv`, pooling `SAGPooling`, readout max (the RTL model's readout; the
  paper says the netlist model's readout is the same). The paper's exact 17 classes are not
  listed in the text we read; ours are a stated reconstruction. The base split replaces
  leave-one-base-out (protocol).
- `gnn-a`: Method A as in s6: GraphSAGE mean x3, 64 hidden, ReLU, dropout 0.5, mean+max readout,
  two-layer head, class-weighted cross-entropy, Adam 1e-3, best-validation-AUROC epoch kept;
  features: cell class one-hot, LUT input count, truth-table size, fan-in, fan-out, CC0, CC1, CO
  (log1p, INF capped), signal probability from 4096 vectors seed 1.
- Budget deviation: the protocol default is 200 epochs. On CPU (jobs <= 4) epochs, batch size
  and the number of seeds are reduced where needed to fit; every reduction is stated in the
  results next to the number. If a reduction is needed, folds and splits are kept, never base
  leakage.
- HW2VEC (yu2021hw2vec, MIT, AICPS/hw2vec): source read (`graph2vec/models.py`: `GCNConv`,
  `SAGPooling`, readout max/mean/add, the same family as the model above). Not run as released:
  its graph generation takes Verilog through Pyverilog (RTL DFG or netlist Verilog), our
  releases are BLIF, and its pinned requirements (numpy 1.16.5, scikit-learn 0.23.1, Python 3.6
  era) do not install on Python 3.12. The model family is covered by `gnn-yasaei`.
- TrojanSAINT (lashen2023trojansaint, DfX-NYUAD/TrojanSAINT): repository read; it carries no
  licence file and the GitHub API reports no licence, so the code is not run or copied. Not run.

### 4.4 Method B (graphlets vs reference)
As s6: Odin III `graphlets` pass, directed, `orbit_totals` per circuit via
`Design.graphlets(directed=True, exclude_global=True, global_fanout=16)` (no second counter). Nets with fanout above 16 (clock, reset, constants) are left out of the graph: with them in, directed counting on a 23k-node s1196 form did not finish in 100 s (one net of fanout 1076); without, 0.3 s. This is Odin III's own option, applied to every circuit and the reference alike. Reference = identity-form clean circuit of
the base (rc3: the base's golden). `d = ||s(c)-s(r)||_1 / ||s(r)||_1`. Non-identity forms: z per
form from the clean circuits of the training bases. Identity: flagged when `d > 0` (exact); for
pooled AUROC across forms identity circuits use sigma floored at 1e-3. Headline for B =
the 18 non-identity forms; the identity row is the setup check (H-B1). Graph level only; a
multi-Trojan circuit is scored once.

## 5. Components

- `detect/data.py`: `Release` (loads manifest + answer key), `Record` (id, base, family, form, role,
  trojans, set, variant), `CircuitFile`, `ReferencedFile`, path resolution, gzip BLIF reading.
- `detect/splits.py`: `source_of`, `make_folds`, `base_split`, `lut_split`, `assert_no_overlap`.
- `detect/metrics.py`: `auroc`, `threshold_at_fpr`, `rates`, `f1_at_prevalence`, `bootstrap_ci`,
  `wlt`.
- `detect/harness.py`: runs a detector over every split/fold/seed, stores scores as JSON under
  `work/htl-out/det/runs/<detector>/<family>-<release>/...`, builds the report tables.
- `detect/features.py`: per-circuit feature cache (netlist stats, SCOAP, graph arrays) in
  `work/htl-out/det/feat/<release>/<id>.npz`; process pool, 4 jobs, resumable.
- `detect/report.py`: markdown tables for `docs/results-detectors.md`.

## 6. Tests (unittest)

Splits: no base on both sides in any fold or LUT split; every base appears in test exactly once;
source stratification; determinism with seed 1. Metrics on toy sets with known AUROC, thresholds,
F1 re-weighting, W/L/T. Detector interface: a detector never receives base/form (type check).
Size-only on a toy set learns a size rule. Odin III tests `skipUnless(odin_available())`. Torch
tests `skipUnless` torch present (CI test job does not install torch).

## 7. Open points and defaults (agent defaults, logged)

1. Validation threshold when a validation fold has no clean circuit: error.
2. W/L/T tolerance 1e-6.
3. Bootstrap pools nothing across folds (resample inside each fold).
4. `rare` and `gnn-a` use SCOAP from the released circuit only (Odin III reads the BLIF);
   Seq uses `--sequential`, whose rareness for time bombs is known to be underestimated
   (datasheet).
5. Proc circuits are large (up to 67k cells): SCOAP/GNN may be refused; a refusal is recorded as
   "not run" with the reason, never imputed.

## 8. rc4 (n = 300 per golden, Peter's redesign 2026-11-01; controller note)

rc3 is not used: set B had two label leaks (clean variants carried double inverters and buffer
pairs that infected circuits lacked; restructured clean variants equalled the restructured
golden). rc4 (docs/specs/2026-11-01-seeker-n200-design.md section 4): per golden, three sets of
100 circuits, set K4 (Odin III `abc --lut 4`), set K6 (`--lut 6`) and set G (`--gates andornot`);
per set a random 10 to 70% are infected, each infected circuit has 1 to 3 Trojans; every
non-golden circuit, clean or infected, goes through its own random ABC script, ports and blocks
shuffled, nets renamed; no restructured forms and no set A.

Consequences for the Common protocol (this replaces the form and set A/B parts for rc4; rc1 and
rc2 keep the form protocol and stay as the earlier baseline):

- Base split: unchanged (five folds by base, seed 1, stratified by source). All three sets of a
  base go to the same side. The golden of each base is never scored or trained on (it is not
  obfuscated, so it would carry its own style); it is the reference of Method B.
- The per-form / LUT-form split becomes the per-set split: for each fold and each held-out set
  S in {K4, K6, G}, train on the other two sets of the training bases, validate on the other two
  sets of the validation-fold bases, test on set S of the test-fold bases. Both the base and the
  set (mapping library) are unseen. Fifteen test cells per seed.
- Breakdowns: per set (K4, K6, G) and per Trojan count (1, 2, >=3) replace per form and set A/B;
  per rareness band stays (Comb: band of the first Trojan; Seq: trigger kind x speed). F1
  re-weighting is applied as before (the release prevalence per set is a random 10 to 70%).
- Method B: the reference is the base's golden; the per-form z-score becomes per-set (mu and
  sigma over the training bases' clean circuits of that set; the held-out set uses the pooled
  statistics of the other sets). There is no identity form, so there is no exact `d > 0` check.
- The sanity detector is unchanged and, on a good release, sits near chance.
- GNN budget for rc4: 12 epochs, batch 32, one seed (0), at most 1500 training circuits per
  fold-run (a seeded random subset of the training side); stated next to every number.

Run commands: `python -m lemanruss.detect.run --detector D --family Comb|Seq --release <rc4 dir>
--out <dir> --seeds 0`.

## 9. rc5 rerun and extended GNN budget (2026-11-02)

- Seq rc4 had Trojan latches with init 0 and every other latch init 2. Seq rc5 (lemanrussIII #13)
  fixes that; Comb stays rc4. All detectors were rerun on Seq rc5 with the rc4 protocol and per-set
  split unchanged (12 epochs, batch 32, seed 0, at most 1500 training circuits per fold-run), Odin III
  from `build/rel-main2`. The sanity detector runs next to each. Seq rc4 stays in the results as a
  documented leak case (results-detectors.md section 8): the detectors' AUROC did not change with
  the fix, because the parser never reads the latch init field.
- Extended GNN budget (gnn-yasaei, gnn-a; Comb rc4 and Seq rc5; base split only): 30 epochs, batch 32,
  seeds 0, 1, 2, at most 1500 training circuits per fold-run. This is still below the protocol
  (200 epochs, seeds 0 to 4, no training-subset cap); the budget is printed next to each number.
  Outputs go to a separate output directory so the 12-epoch runs are kept.
