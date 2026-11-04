# Current detectors on Seeker v2.0 (2026-11-01, rerun 2026-11-02 on Seq rc5)

Spec: `docs/specs/2026-11-01-detector-baselines-design.md`. Code: `lemanruss/detect/`.
Purpose: Leman Russ benchmark validity (R1: a benchmark is useful when it separates detectors).
Measure: the Common protocol of the paper's methods section (kept locally by the author) (AUROC, TPR and FPR at FPR <= 5% on
validation, F1 at release prevalence and at 10/30/50/70%, W/L/T against the size-only control,
95% bootstrap over bases). Per-base summaries: `docs/results-detectors-summary.json`.

## 1. In plain words

We ran the current detectors on the current releases: Seeker-Comb rc4 and Seeker-Seq rc5 (the
headline), with the superseded Seq rc4 kept as a documented case (section 8). Seq rc5 is the
release that fixed the latch init value difference of rc4 (every latch now has init 2).

- Seeker-Comb rc4 (combinational): no detector tells infected from clean. Every AUROC is 0.48 to
  0.55, no better than the size-only control (win/loss/tie 4/15/0 to 10/9/0), and the exact-duplicate
  / style detector (sanity) is at chance, as it should be on a clean release.
- Seeker-Seq rc5 (sequential): the graph neural networks detect the Trojans almost perfectly
  (gnn-a AUROC 0.999, gnn-yasaei 0.980, gnn-a without SCOAP and probability columns 0.990; win/loss/tie
  against the size control 33/2/1, 33/3/0, 34/2/0), and still 0.84 to 0.96 on a mapping library held
  out of training (set G). The classical rare-signal score (0.59) and the graphlet drift method
  (0.50) do not detect anything useful.
- The Seq rc4 result and the Seq rc5 result are the same (section 8). The latch init difference
  was a real label leak in the files, but it is not what the detectors found: our parser never reads
  the init field, and removing the difference changed no AUROC outside noise. What the detectors
  see is that infected circuits carry about 48% more flip-flops (and 2.8 points more latch share)
  than the clean circuits of the same base and set, which is the Trojan's own counter or pattern
  state. Whether that is too easy a signal for a benchmark is open (section 5).

So Comb and Seq separate detectors in opposite ways: Comb separates none (hard, or the Trojans
are invisible to these detectors at this training budget), Seq is solved by a learned graph model.

The earlier releases (Comb rc1, Seq rc2) are kept as the baseline and show why the sanity detector
was asked for: on Comb rc1 the sanity detector alone reaches AUROC 0.69 and the size control 0.71,
because clean circuits are duplicated across restructurings while infected ones are unique
(264 circuits are exact duplicates, 36 of them infected). rc4 removed that.

Training budget behind every learned-detector number: 12 epochs, batch 32, 1 seed, at most 1500
training circuits per fold (protocol: 200 epochs, 5 seeds). Section 9 repeats the two GNNs with 30
epochs and 3 seeds on the base split; the budget is printed next to each number there.

## 2. Hypothesis, experiment, verdict

| H | Hypothesis (s6) | Experiment | Verdict |
|---|---|---|---|
| H-A1 | Comb graph-level AUROC near 0.5, below Seq | gnn-a, gnn-yasaei, Comb rc4 and Seq rc5 base split | SUPPORTED: Comb 0.52 to 0.53 [CIs include 0.5], Seq 0.98 to 1.00 (same on the superseded Seq rc4) |
| H-A2 | Seq detected better than Comb (state) | same | SUPPORTED, by a wide margin |
| H-A3 | unseen LUT forms cost TPR | rc1/rc2 lut split; rc4 per-set split | MIXED: Comb rc1 gnn-yasaei 0.70 to 0.59, gnn-a unchanged; Seq rc2 gnn-a 0.97 to 0.95; Seq rc5 held-out set G costs gnn-yasaei (0.98 to 0.84) and gnn-a (1.00 to 0.95), gnn-a-nosc 0.99 to 0.96; sets K4/K6 do not |
| H-A4 | no fall with rarer bands | per-band AUROC | SUPPORTED: no trend with band on Comb rc4 (0.46 to 0.57 across detectors and bands) and flat on Seq rc5 (0.97 to 1.00 for the GNNs over the six variants) |
| H-B1 | identity form: TPR near 1, FPR near 0 | graphlet-b rc1/rc2 identity form | CONFIRMED: AUROC 1.00 (rc1 and rc2); rc4 has no identity form, so not repeatable there |
| H-B2 | restructured forms fall to 0.5 | graphlet-b, 18 forms | SUPPORTED: 0.53 to 0.66 (Comb rc1), 0.43 to 0.54 (Seq rc2); rc4 per-set 0.46 to 0.51 |
| H-B3 | Seq stays detectable at larger drift than Comb | graphlet-b | REFUTED: Seq is no better than Comb (0.50 vs 0.48 to 0.61) |
| H-B4 | B beats A on identity | rc1/rc2 identity | SUPPORTED: B 1.00 on the identity form against gnn-a 0.73 (Comb rc1) and 0.98 (Seq rc2); the identity form exists only in rc1/rc2 |

Strict labels per cell are in the tables (ABOVE CHANCE / INCONCLUSIVE / BELOW CHANCE from the AUROC
interval; INCONCLUSIVE means the interval touches 0.5, not DISMISSED).

## 3. What was run, and how

- Releases: Comb rc1 (1596 circuits, 31 bases), Seq rc2 (4389, 48), Comb rc4 (5756 incl. 31
  goldens, 31 bases), Seq rc4 (10375 incl. 36 goldens, 36 bases; superseded, kept as the leak case, section 8), Seq rc5
  (same sizes, merged lemanrussIII #13; the headline Seq release), Proc pilot2 (6). rc3 was never
  used (label leaks, controller note). rc4 splits: base, and the per-set split (train two of
  K4 / K6 / G, test the third; spec section 8). rc1/rc2: base and LUT-form splits.
- Detectors: size (logistic regression on gates, depth, FFs), sanity (sha256 duplicate count +
  double inverter / double buffer / buffer / constant-driver shares), classhist (diagnostic: the 17
  node-class shares + size), rare (rare-signal / SCOAP score in the line of COTD, Odin III
  `scoap`), gnn-yasaei (as read in arXiv 2204.11431: one-hot class, 3 GCN layers of 55, SAG
  pooling 0.6, max readout), gnn-a (s6 Method A: 3 GraphSAGE layers of 64, SCOAP + probability
  features), gnn-a-nosc (gnn-a without the SCOAP and probability columns, rc4 only), graphlet-b
  (s6 Method B, directed graphlets, Odin III `graphlets`, nets of fanout above 16 excluded).
- **Budget deviations from the protocol defaults (200 epochs, batch 2 / 32, seeds 0 to 4):**
  Comb rc1: 20 epochs, batch 32, seeds 0 to 2. Seq rc2 and everything on rc4 and rc5: 12 epochs, batch 32,
  seed 0 only; rc4 trains each fold-run on a seeded random subset of at most 1500 training
  circuits (and validates on the full validation side). Best-validation-AUROC epoch kept. The
  non-learning detectors run once (no seeds). Confidence intervals are over bases only, so GNN
  seed variance is not in them.
- Not scored (Odin III timed out at 90 s or refused; recorded, never imputed): rc2 Seq rare 15
  and gnn-a 15 circuits (large circuits that exceeded the 90 s limit), graphlet-b 23. rc4 and rc5: none.
- Hardware: CPU only, jobs <= 4.

### Not run, and why

- HW2VEC (yu2021hw2vec, MIT): source read (`graph2vec/models.py` uses `GCNConv`, `SAGPooling`,
  max/mean/add readout, the same family as gnn-yasaei). Not run as released: its graph builder
  takes Verilog through Pyverilog, our releases are BLIF, and its pinned requirements (numpy
  1.16.5, scikit-learn 0.23.1) do not install on Python 3.12. The model family is covered by
  gnn-yasaei.
- TrojanSAINT (lashen2023trojansaint, DfX-NYUAD/TrojanSAINT): the repository has no licence file
  and GitHub reports none; not run, not copied.
- GNN4TJ (RTL level) and the COTD full text were not read; rare is a baseline built on the same
  two quantities, not a reproduction.
- Published numbers of other papers are not quoted here. (The Yasaei netlist model's own
  reported figures are in s6, from the arXiv text.)

- Odin III for the rc5 runs: `build/rel-main2` (rc4 runs used `build/rel-main`); feature caches are keyed by the
  hash of the circuit file, so no rc4 feature is reused for an rc5 circuit.
- Extended GNN budget (30 epochs, seeds 0 to 2, base split): section 9.

## 4. Circularity and controls

- `rare` is partly circular: the benchmark's site selection ranks nets by SCOAP and signal
  probability to place the trigger (s6). It nevertheless sits near chance on Seq (0.59 on rc5,
  0.53 on rc4) and only weakly above chance on Comb rc4 (0.55, set G 0.60), which is the opposite of
  what circularity alone would give.
- gnn-a uses SCOAP too. The ablation gnn-a-nosc (class, degree, LUT size only) reaches nearly the same
  Seq rc5 AUROC (0.990 vs 0.999), so the SCOAP columns are not what separates Seq.
- sanity (duplicates + style) is at chance on Comb rc4 (0.52 base) and Seq rc5 (0.51 base).
  On rc1 it was 0.69 (duplicates).
- classhist (class shares + size) reaches 0.745 on the Seq rc5 base split but 0.45 on held-out set G
  (BELOW CHANCE): a class-mix signature works inside a mapping, not across mappings. The GNNs
  generalise to set G (0.84 to 0.96), so they use more than the class mix.
- Within-base check of what separates Seq (section 8): infected circuits carry more flip-flops than
  clean ones of the same base and set. The size control pools circuits of different bases, where
  base size varies far more than the Trojan adds, so it is weak (0.63) although the within-base
  effect is large.

## 5. What is not established

- Whether the Seq signal is "too easy". The Trojan adds counter or pattern flip-flop structure;
  ABC obfuscation cannot hide state, so a detector that sees the latch count and mix relative to a
  circuit's size class finds it. This is the s6 prediction H-A2, plausibly a real structural
  signal, but the benchmark does not yet include a Trojan that adds no net state. A node-level
  localisation test on the edit-event files, or a held-out Trojan family, would separate "detects the
  Trojan" from "detects the extra flip-flops".
- Whether another leak remains. rc5 removed the init difference and the inverter / duplicated
  node in front of Trojan latches; the detectors' AUROC did not move, so these two features were not
  being used. We have not found a further generator artefact (sanity and classhist do not).
- Comb: no detector has signal, so the benchmark cannot yet rank detectors on Comb. Either the
  Comb Trojans (about 2 inserted nodes) are below what these detectors resolve (H-A1), or the
  detectors are under-trained. Section 9 raises the budget for the two GNNs and states what changed.
- Seed variance: 1 seed on the main tables; 3 seeds only in section 9.

## 6. Seeker-Proc pilot2 (raw outcomes, no statistics)

Detectors trained on the identity forms of Comb rc1 and Seq rc2 (bases of fold 0 left out,
fold 1 as validation), threshold at FPR 5% on validation, scoring the six circuits.

| detector | pp0001 (clean) | pp0002 (infected) | pp0003 (clean) | pp0004 (infected) | pp0005 (clean) | pp0006 (infected) |
|---|---|---|---|---|---|---|
| size | -0.779 (no flag) | -0.779 (no flag) | -1.26 (no flag) | -1.26 (no flag) | -1.26 (no flag) | -1.26 (no flag) |
| sanity | 0.216 (no flag) | 0.216 (no flag) | 0.214 (no flag) | 0.214 (no flag) | 0.214 (no flag) | 0.214 (no flag) |
| rare | not run | not run | not run | not run | not run | not run |
| gnn-yasaei | 0.081 (flag) | 0.081 (flag) | 0.583 (flag) | 0.55 (flag) | 0.583 (flag) | 0.55 (flag) |
| gnn-a | not run | not run | not run | not run | not run | not run |
| graphlet-b | not run | not run | 0 (no flag) | 0 (no flag) | 0 (no flag) | 0 (no flag) |

Note: Odin III `scoap` and `graphlets` read the top module of a hierarchical BLIF only (a
`flatten` before `graphlets` fails with ODIN3_ERR_INVALID_ARG), and the Proc Trojans live in
submodules, so rare, gnn-a and graphlet-b cannot see them here: not a result about those
methods. size and sanity see identical scores for the clean and infected twin (the Trojans do not
change gate, depth, FF counts or the style counts). gnn-yasaei (parsing all models) flags every
circuit, clean ones included.

## 8. Seq rc4 latch init leak (documented case)

Seq rc4 (lemanrussIII #11) gave the Trojan's flip-flops init 0 where every other latch has init 2,
so the label could in principle be read from the files. Seq rc5 (#13) fixed it (every latch init 2;
Trojan latches carry the circuit's own latch type, clock and init; a pattern trigger's first stage is
a two-input cell, so no inverter or duplicated node sits in front of a Trojan latch) and added
latch-field gates. The full rc4 tables are in section 10 ("superseded").

What the detectors found on rc4 (base split, AUROC, 12 epochs, 1 seed) against rc5 (same protocol):

| detector | Seq rc4 (leak) | Seq rc5 (fixed) |
|---|---|---|
| size | 0.63 | 0.63 |
| sanity | 0.51 | 0.51 |
| classhist | 0.74 | 0.74 |
| rare | 0.53 | 0.59 |
| gnn-yasaei | 0.98 | 0.98 |
| gnn-a | 1.00 | 1.00 |
| gnn-a-nosc | 0.98 | 0.99 |
| graphlet-b | 0.50 | 0.50 |

Why, as far as it is established:

1. The detectors did not read the init field. The parser (`lemanruss/detect/netlist.py`) takes the
   latch output net and input net only; the class-only models (gnn-yasaei, classhist) therefore could
   not use it. gnn-a and rare take SCOAP and signal probability from Odin III, whose simulator does see
   the init value, but gnn-a-nosc has no such column and scored the same.
2. The rc5 fix therefore did not remove the GNN signal: the headline moved by at most 0.01 (rare
   by +0.06, interval from [0.50, 0.60] to [0.56, 0.66], the only change outside noise, and in the
   direction of a small gain). The rc4 AUROC of 0.98 to 1.00 was not the init leak.
3. What does differ, within each base and set (103 base-set pairs, infected mean minus clean mean,
   `classhist` features, t over base-set pairs): latch share +2.8 points (t = 11.9) on rc4 and
   +2.8 points (t = 11.7) on rc5; log(1 + flip-flops) +0.39 on both (about 48% more (1 + flip-flops); t = 14.8
   both); log(1 + gates) +0.14 (rc4) and +0.14 (rc5); log depth +0.06 and +0.045. The Trojan's counter or
   pattern state is a large relative addition in these circuits, and class-only graph models see it.
   (Diagnostic script not committed; it uses the stored `classhist` feature cache and takes minutes.)

So the rc4 leak was real in the files but is not what the detectors used; a benchmark user
reading the rc4 result as "GNNs exploit the init leak" would have been wrong, and the rc5 result
shows the benchmark still separates the GNNs from everything else on Seq for a different reason.

## 9. Extended GNN budget (gnn-yasaei, gnn-a; base split only)

Budget of the extended runs: 30 epochs, batch 32, seeds 0, 1, 2, at most 1500 training circuits per
fold-run, best-validation-AUROC epoch kept. The protocol is 200 epochs, seeds 0 to 4 and no cap, so
this is still well below it. The main tables (section 10) stay at 12 epochs, 1 seed. Only the base
split was run (the set splits would triple the cost); the size control is the 1-seed run.
AUROC is the mean over the 15 fold-seed runs; the interval is the base bootstrap over seed-averaged
scores (so it does not contain the seed variance, see the note).

| family and release | detector | budget | AUROC [95% CI] | W/L/T vs size | label | same detector at 12 epochs, 1 seed |
|---|---|---|---|---|---|---|
| Comb rc4 | gnn-yasaei | 30 ep, 3 seeds | 0.526 [0.511, 0.601] | 8/11/0 | ABOVE CHANCE | 0.517 [0.456, 0.582] |
| Comb rc4 | gnn-a | 30 ep, 3 seeds | 0.565 [0.536, 0.627] | 13/6/0 | ABOVE CHANCE | 0.533 [0.489, 0.584] |
| Seq rc5 | gnn-yasaei | 30 ep, 3 seeds | 0.855 [0.961, 0.996] | 34/2/0 | ABOVE CHANCE | 0.980 [0.959, 0.994] |
| Seq rc5 | gnn-a | 30 ep, 3 seeds | 0.999 [0.999, 1.000] | 35/0/1 | ABOVE CHANCE | 0.999 [0.995, 1.000] |

Notes.

- Comb: more training moves gnn-a from 0.533 to 0.565 (CI above 0.5, W/L/T 13/6/0 against the size
  control, per-fold AUROC 0.42 to 0.67, best on folds 3 and 4). gnn-yasaei stays at 0.53. This is a
  small gain, not a separation: H-A1 (Comb near 0.5) still holds at this budget, with the first
  hint that more epochs help the SAGE model with SCOAP features. Not an established detection.
- Seq: gnn-a is saturated (0.999 at both budgets). gnn-yasaei's mean of 0.855 is below its 12-epoch
  0.980 because seed 1 collapsed in four of five folds (per-run AUROC 0.43 to 0.60, against 0.93 to
  0.997 for seeds 0 and 2 in every fold); the interval in the table is computed on seed-averaged scores
  and so sits above the per-run mean. The collapse is training instability of this model (cause not investigated), not a property of the release. The 12-epoch, one-seed result of
  section 10 is therefore not stable across seeds for this detector; we did not tune it.
- The per-run AUROC values are in the stored fold-run files under the extended output directory
  (not committed); the summary is in `docs/results-detectors-summary.json` under
  `_extended_gnn_budget`.

## 10. Tables

All numbers are means over folds (and seeds where several) with 95% intervals from resampling
bases. "W/L/T vs size" counts test bases on which the method's within-base AUROC is higher,
lower or equal to the size control's. The `rc4` per-set rows hold one set out (spec section 8).
Per-form tables apply to rc1/rc2 only; rc4 has per-set and per-Trojan-count tables.

## Comb (seeker-comb-v2.0-rc4)

Circuits 5756, bases 31.

### Headline (means over folds and seeds; AUROC with 95% base-bootstrap)

| detector | split | AUROC [95% CI] | TPR | FPR | F1 rel | F1 10% | F1 30% | F1 50% | F1 70% | W/L/T vs size | label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| size | base | 0.538 [0.496, 0.609] | 0.052 | 0.046 | 0.082 | 0.060 | 0.080 | 0.086 | 0.089 | control | INCONCLUSIVE |
| sanity | base | 0.522 [0.491, 0.548] | 0.080 | 0.059 | 0.082 | 0.039 | 0.076 | 0.094 | 0.105 | 8/11/0 | INCONCLUSIVE |
| classhist | base | 0.534 [0.487, 0.580] | 0.120 | 0.105 | 0.169 | 0.101 | 0.160 | 0.182 | 0.195 | 5/14/0 | INCONCLUSIVE |
| rare | base | 0.551 [0.522, 0.635] | 0.242 | 0.213 | 0.231 | 0.108 | 0.211 | 0.265 | 0.300 | 10/9/0 | ABOVE CHANCE |
| gnn-yasaei | base | 0.517 [0.456, 0.582] | 0.153 | 0.095 | 0.167 | 0.099 | 0.159 | 0.187 | 0.203 | 9/10/0 | INCONCLUSIVE |
| gnn-a | base | 0.533 [0.489, 0.584] | 0.125 | 0.085 | 0.173 | 0.110 | 0.166 | 0.187 | 0.199 | 7/12/0 | INCONCLUSIVE |
| gnn-a-nosc | base | 0.546 [0.504, 0.601] | 0.093 | 0.061 | 0.138 | 0.090 | 0.132 | 0.146 | 0.153 | 9/10/0 | ABOVE CHANCE |
| graphlet-b | base | 0.479 [0.447, 0.507] | 0.082 | 0.111 | 0.105 | 0.058 | 0.100 | 0.119 | 0.130 | 4/15/0 | INCONCLUSIVE |
| size | set-K4 | 0.472 [0.437, 0.561] | 0.105 | 0.144 | 0.067 | 0.026 | 0.066 | 0.094 | 0.115 | control | INCONCLUSIVE |
| sanity | set-K4 | 0.508 [0.476, 0.570] | 0.073 | 0.063 | 0.070 | 0.035 | 0.070 | 0.087 | 0.097 | 10/9/0 | INCONCLUSIVE |
| classhist | set-K4 | 0.444 [0.424, 0.541] | 0.410 | 0.475 | 0.271 | 0.126 | 0.283 | 0.382 | 0.452 | 13/6/0 | INCONCLUSIVE |
| rare | set-K4 | 0.528 [0.504, 0.654] | 0.218 | 0.234 | 0.196 | 0.095 | 0.190 | 0.243 | 0.278 | 12/7/0 | ABOVE CHANCE |
| gnn-yasaei | set-K4 | 0.484 [0.428, 0.558] | 0.001 | 0.016 | 0.002 | 0.001 | 0.002 | 0.002 | 0.002 | 8/11/0 | INCONCLUSIVE |
| gnn-a | set-K4 | 0.533 [0.472, 0.618] | 0.097 | 0.060 | 0.131 | 0.077 | 0.122 | 0.139 | 0.148 | 9/10/0 | INCONCLUSIVE |
| gnn-a-nosc | set-K4 | 0.541 [0.482, 0.633] | 0.066 | 0.048 | 0.072 | 0.052 | 0.080 | 0.093 | 0.100 | 10/9/0 | INCONCLUSIVE |
| graphlet-b | set-K4 | 0.510 [0.455, 0.577] | 0.097 | 0.096 | 0.116 | 0.075 | 0.114 | 0.134 | 0.146 | 10/9/0 | INCONCLUSIVE |
| size | set-K6 | 0.544 [0.455, 0.600] | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | control | INCONCLUSIVE |
| sanity | set-K6 | 0.499 [0.458, 0.572] | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 12/7/0 | INCONCLUSIVE |
| classhist | set-K6 | 0.531 [0.418, 0.582] | 0.038 | 0.069 | 0.065 | 0.048 | 0.062 | 0.066 | 0.068 | 7/12/0 | INCONCLUSIVE |
| rare | set-K6 | 0.536 [0.480, 0.643] | 0.161 | 0.218 | 0.164 | 0.073 | 0.150 | 0.194 | 0.222 | 14/5/0 | INCONCLUSIVE |
| gnn-yasaei | set-K6 | 0.481 [0.418, 0.566] | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 13/6/0 | INCONCLUSIVE |
| gnn-a | set-K6 | 0.486 [0.439, 0.559] | 0.002 | 0.004 | 0.005 | 0.005 | 0.005 | 0.005 | 0.005 | 11/8/0 | INCONCLUSIVE |
| gnn-a-nosc | set-K6 | 0.449 [0.388, 0.532] | 0.000 | 0.003 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 11/7/1 | INCONCLUSIVE |
| graphlet-b | set-K6 | 0.494 [0.413, 0.586] | 0.284 | 0.307 | 0.241 | 0.098 | 0.207 | 0.274 | 0.320 | 11/8/0 | INCONCLUSIVE |
| size | set-G | 0.483 [0.437, 0.588] | 0.651 | 0.614 | 0.432 | 0.153 | 0.346 | 0.477 | 0.574 | control | INCONCLUSIVE |
| sanity | set-G | 0.548 [0.508, 0.569] | 0.113 | 0.079 | 0.140 | 0.069 | 0.122 | 0.145 | 0.157 | 5/14/0 | ABOVE CHANCE |
| classhist | set-G | 0.469 [0.423, 0.549] | 0.064 | 0.062 | 0.080 | 0.031 | 0.063 | 0.078 | 0.088 | 9/10/0 | INCONCLUSIVE |
| rare | set-G | 0.598 [0.533, 0.722] | 0.303 | 0.167 | 0.308 | 0.158 | 0.272 | 0.325 | 0.356 | 12/7/0 | ABOVE CHANCE |
| gnn-yasaei | set-G | 0.478 [0.395, 0.544] | 0.085 | 0.090 | 0.113 | 0.052 | 0.096 | 0.116 | 0.128 | 4/15/0 | INCONCLUSIVE |
| gnn-a | set-G | 0.528 [0.463, 0.601] | 0.353 | 0.336 | 0.230 | 0.075 | 0.183 | 0.258 | 0.313 | 10/9/0 | INCONCLUSIVE |
| gnn-a-nosc | set-G | 0.595 [0.519, 0.640] | 0.353 | 0.351 | 0.224 | 0.074 | 0.181 | 0.257 | 0.313 | 9/10/0 | ABOVE CHANCE |
| graphlet-b | set-G | 0.465 [0.435, 0.519] | 0.038 | 0.075 | 0.051 | 0.025 | 0.047 | 0.057 | 0.062 | 5/14/0 | INCONCLUSIVE |

### AUROC by rareness band / variant, base split

| detector | p<1e-2 | p<1e-3 | p<1e-4 |
|---|---|---|---|
| size | 0.53 | 0.53 | 0.56 |
| sanity | 0.55 | 0.47 | 0.47 |
| classhist | 0.54 | 0.52 | 0.53 |
| rare | 0.57 | 0.54 | 0.53 |
| gnn-yasaei | 0.55 | 0.47 | 0.49 |
| gnn-a | 0.53 | 0.53 | 0.54 |
| gnn-a-nosc | 0.55 | 0.51 | 0.55 |
| graphlet-b | 0.47 | 0.46 | 0.48 |

### AUROC by set, base split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | 0.47 | 0.50 | 0.51 |
| sanity | 0.55 | 0.51 | 0.52 |
| classhist | 0.56 | 0.47 | 0.52 |
| rare | 0.60 | 0.53 | 0.54 |
| gnn-yasaei | 0.54 | 0.51 | 0.48 |
| gnn-a | 0.55 | 0.50 | 0.43 |
| gnn-a-nosc | 0.60 | 0.55 | 0.46 |
| graphlet-b | 0.46 | 0.51 | 0.49 |

### AUROC by Trojan count, base split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.53 | 0.54 | 0.56 |
| sanity | 0.53 | 0.52 | 0.50 |
| classhist | 0.55 | 0.51 | 0.51 |
| rare | 0.54 | 0.56 | 0.56 |
| gnn-yasaei | 0.52 | 0.52 | 0.50 |
| gnn-a | 0.54 | 0.52 | 0.54 |
| gnn-a-nosc | 0.54 | 0.55 | 0.56 |
| graphlet-b | 0.49 | 0.47 | 0.45 |

### AUROC by rareness band / variant, set-K4 split

| detector | p<1e-2 | p<1e-3 | p<1e-4 |
|---|---|---|---|
| size | 0.54 | 0.41 | 0.40 |
| sanity | 0.53 | 0.46 | 0.48 |
| classhist | 0.45 | 0.45 | 0.46 |
| rare | 0.55 | 0.51 | 0.52 |
| gnn-yasaei | 0.44 | 0.54 | 0.52 |
| gnn-a | 0.60 | 0.46 | 0.47 |
| gnn-a-nosc | 0.53 | 0.55 | 0.56 |
| graphlet-b | 0.51 | 0.47 | 0.52 |

### AUROC by set, set-K4 split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | n/a | 0.47 | n/a |
| sanity | n/a | 0.51 | n/a |
| classhist | n/a | 0.44 | n/a |
| rare | n/a | 0.53 | n/a |
| gnn-yasaei | n/a | 0.48 | n/a |
| gnn-a | n/a | 0.53 | n/a |
| gnn-a-nosc | n/a | 0.54 | n/a |
| graphlet-b | n/a | 0.51 | n/a |

### AUROC by Trojan count, set-K4 split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.46 | 0.49 | 0.51 |
| sanity | 0.51 | 0.51 | 0.50 |
| classhist | 0.46 | 0.42 | 0.45 |
| rare | 0.53 | 0.50 | 0.58 |
| gnn-yasaei | 0.48 | 0.48 | 0.51 |
| gnn-a | 0.51 | 0.55 | 0.58 |
| gnn-a-nosc | 0.54 | 0.53 | 0.54 |
| graphlet-b | 0.53 | 0.49 | 0.48 |

### AUROC by rareness band / variant, set-K6 split

| detector | p<1e-2 | p<1e-3 | p<1e-4 |
|---|---|---|---|
| size | 0.48 | 0.60 | 0.61 |
| sanity | 0.51 | 0.50 | 0.46 |
| classhist | 0.47 | 0.55 | 0.59 |
| rare | 0.55 | 0.54 | 0.51 |
| gnn-yasaei | 0.53 | 0.43 | 0.41 |
| gnn-a | 0.43 | 0.53 | 0.53 |
| gnn-a-nosc | 0.38 | 0.52 | 0.52 |
| graphlet-b | 0.50 | 0.46 | 0.44 |

### AUROC by set, set-K6 split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | n/a | n/a | 0.54 |
| sanity | n/a | n/a | 0.50 |
| classhist | n/a | n/a | 0.53 |
| rare | n/a | n/a | 0.54 |
| gnn-yasaei | n/a | n/a | 0.48 |
| gnn-a | n/a | n/a | 0.49 |
| gnn-a-nosc | n/a | n/a | 0.45 |
| graphlet-b | n/a | n/a | 0.49 |

### AUROC by Trojan count, set-K6 split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.51 | 0.60 | 0.60 |
| sanity | 0.49 | 0.52 | 0.48 |
| classhist | 0.55 | 0.48 | 0.49 |
| rare | 0.53 | 0.57 | 0.51 |
| gnn-yasaei | 0.49 | 0.46 | 0.48 |
| gnn-a | 0.48 | 0.47 | 0.52 |
| gnn-a-nosc | 0.44 | 0.44 | 0.48 |
| graphlet-b | 0.48 | 0.54 | 0.48 |

### AUROC by rareness band / variant, set-G split

| detector | p<1e-2 | p<1e-3 | p<1e-4 |
|---|---|---|---|
| size | 0.41 | 0.55 | 0.56 |
| sanity | 0.58 | 0.52 | 0.49 |
| classhist | 0.41 | 0.53 | 0.54 |
| rare | 0.61 | 0.60 | 0.59 |
| gnn-yasaei | 0.48 | 0.48 | 0.48 |
| gnn-a | 0.52 | 0.56 | 0.56 |
| gnn-a-nosc | 0.64 | 0.55 | 0.54 |
| graphlet-b | 0.43 | 0.45 | 0.51 |

### AUROC by set, set-G split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | 0.48 | n/a | n/a |
| sanity | 0.55 | n/a | n/a |
| classhist | 0.47 | n/a | n/a |
| rare | 0.60 | n/a | n/a |
| gnn-yasaei | 0.48 | n/a | n/a |
| gnn-a | 0.53 | n/a | n/a |
| gnn-a-nosc | 0.59 | n/a | n/a |
| graphlet-b | 0.46 | n/a | n/a |

### AUROC by Trojan count, set-G split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.46 | 0.51 | 0.53 |
| sanity | 0.56 | 0.54 | 0.53 |
| classhist | 0.45 | 0.50 | 0.50 |
| rare | 0.58 | 0.62 | 0.60 |
| gnn-yasaei | 0.48 | 0.49 | 0.48 |
| gnn-a | 0.53 | 0.51 | 0.54 |
| gnn-a-nosc | 0.59 | 0.58 | 0.66 |
| graphlet-b | 0.48 | 0.44 | 0.42 |

## Seq (seeker-seq-v2.0-rc5)

Circuits 10375, bases 36.

### Headline (means over folds and seeds; AUROC with 95% base-bootstrap)

| detector | split | AUROC [95% CI] | TPR | FPR | F1 rel | F1 10% | F1 30% | F1 50% | F1 70% | W/L/T vs size | label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| size | base | 0.626 [0.594, 0.700] | 0.149 | 0.095 | 0.128 | 0.064 | 0.117 | 0.146 | 0.164 | control | ABOVE CHANCE |
| sanity | base | 0.510 [0.478, 0.562] | 0.024 | 0.025 | 0.036 | 0.021 | 0.034 | 0.038 | 0.041 | 5/31/0 | INCONCLUSIVE |
| classhist | base | 0.745 [0.717, 0.797] | 0.321 | 0.072 | 0.414 | 0.296 | 0.396 | 0.427 | 0.443 | 19/17/0 | ABOVE CHANCE |
| rare | base | 0.588 [0.560, 0.661] | 0.086 | 0.039 | 0.137 | 0.105 | 0.133 | 0.141 | 0.146 | 16/20/0 | ABOVE CHANCE |
| gnn-yasaei | base | 0.980 [0.959, 0.994] | 0.802 | 0.097 | 0.760 | 0.609 | 0.738 | 0.784 | 0.808 | 33/3/0 | ABOVE CHANCE |
| gnn-a | base | 0.999 [0.995, 1.000] | 0.991 | 0.111 | 0.922 | 0.781 | 0.902 | 0.948 | 0.973 | 33/2/1 | ABOVE CHANCE |
| gnn-a-nosc | base | 0.990 [0.980, 0.996] | 0.835 | 0.063 | 0.825 | 0.691 | 0.808 | 0.842 | 0.858 | 34/2/0 | ABOVE CHANCE |
| graphlet-b | base | 0.502 [0.457, 0.544] | 0.130 | 0.080 | 0.158 | 0.094 | 0.150 | 0.173 | 0.185 | 2/34/0 | INCONCLUSIVE |
| size | set-K4 | 0.647 [0.608, 0.763] | 0.131 | 0.097 | 0.113 | 0.043 | 0.094 | 0.122 | 0.140 | control | ABOVE CHANCE |
| sanity | set-K4 | 0.508 [0.431, 0.564] | 0.069 | 0.091 | 0.091 | 0.050 | 0.081 | 0.097 | 0.107 | 0/34/2 | INCONCLUSIVE |
| classhist | set-K4 | 0.781 [0.746, 0.836] | 0.590 | 0.262 | 0.528 | 0.278 | 0.474 | 0.567 | 0.621 | 2/34/0 | ABOVE CHANCE |
| rare | set-K4 | 0.584 [0.532, 0.679] | 0.066 | 0.038 | 0.107 | 0.078 | 0.102 | 0.110 | 0.113 | 3/31/2 | ABOVE CHANCE |
| gnn-yasaei | set-K4 | 0.980 [0.954, 0.997] | 0.895 | 0.121 | 0.863 | 0.708 | 0.834 | 0.882 | 0.909 | 13/8/15 | ABOVE CHANCE |
| gnn-a | set-K4 | 1.000 [0.998, 1.000] | 0.977 | 0.118 | 0.922 | 0.786 | 0.894 | 0.939 | 0.965 | 13/2/21 | ABOVE CHANCE |
| gnn-a-nosc | set-K4 | 0.983 [0.960, 0.999] | 0.791 | 0.088 | 0.740 | 0.580 | 0.712 | 0.755 | 0.777 | 13/5/18 | ABOVE CHANCE |
| graphlet-b | set-K4 | 0.480 [0.404, 0.555] | 0.076 | 0.050 | 0.085 | 0.047 | 0.082 | 0.097 | 0.106 | 0/36/0 | INCONCLUSIVE |
| size | set-K6 | 0.616 [0.593, 0.737] | 0.474 | 0.308 | 0.440 | 0.188 | 0.377 | 0.474 | 0.532 | control | ABOVE CHANCE |
| sanity | set-K6 | 0.495 [0.437, 0.574] | 0.063 | 0.029 | 0.082 | 0.049 | 0.077 | 0.087 | 0.092 | 6/29/1 | INCONCLUSIVE |
| classhist | set-K6 | 0.736 [0.690, 0.826] | 0.373 | 0.066 | 0.467 | 0.361 | 0.448 | 0.476 | 0.490 | 10/26/0 | ABOVE CHANCE |
| rare | set-K6 | 0.592 [0.515, 0.707] | 0.083 | 0.070 | 0.131 | 0.107 | 0.127 | 0.134 | 0.137 | 5/29/2 | ABOVE CHANCE |
| gnn-yasaei | set-K6 | 0.954 [0.914, 0.982] | 0.942 | 0.058 | 0.936 | 0.857 | 0.920 | 0.945 | 0.959 | 17/17/2 | ABOVE CHANCE |
| gnn-a | set-K6 | 1.000 [0.999, 1.000] | 0.997 | 0.106 | 0.937 | 0.796 | 0.908 | 0.953 | 0.977 | 21/1/14 | ABOVE CHANCE |
| gnn-a-nosc | set-K6 | 0.967 [0.937, 0.991] | 0.964 | 0.029 | 0.963 | 0.900 | 0.953 | 0.968 | 0.976 | 18/16/2 | ABOVE CHANCE |
| graphlet-b | set-K6 | 0.520 [0.458, 0.585] | 0.181 | 0.119 | 0.197 | 0.104 | 0.178 | 0.210 | 0.229 | 0/36/0 | INCONCLUSIVE |
| size | set-G | 0.667 [0.621, 0.749] | 0.012 | 0.001 | 0.022 | 0.021 | 0.022 | 0.022 | 0.022 | control | ABOVE CHANCE |
| sanity | set-G | 0.488 [0.418, 0.574] | 0.082 | 0.123 | 0.102 | 0.058 | 0.092 | 0.112 | 0.125 | 12/24/0 | INCONCLUSIVE |
| classhist | set-G | 0.448 [0.393, 0.494] | 0.983 | 0.987 | 0.525 | 0.181 | 0.458 | 0.662 | 0.817 | 2/34/0 | BELOW CHANCE |
| rare | set-G | 0.584 [0.543, 0.661] | 0.090 | 0.031 | 0.138 | 0.107 | 0.137 | 0.146 | 0.150 | 14/22/0 | ABOVE CHANCE |
| gnn-yasaei | set-G | 0.839 [0.788, 0.902] | 0.808 | 0.559 | 0.521 | 0.217 | 0.466 | 0.614 | 0.714 | 26/9/1 | ABOVE CHANCE |
| gnn-a | set-G | 0.949 [0.903, 0.988] | 0.999 | 0.244 | 0.811 | 0.567 | 0.800 | 0.897 | 0.951 | 29/3/4 | ABOVE CHANCE |
| gnn-a-nosc | set-G | 0.964 [0.948, 0.980] | 0.955 | 0.827 | 0.580 | 0.242 | 0.515 | 0.695 | 0.828 | 27/4/5 | ABOVE CHANCE |
| graphlet-b | set-G | 0.489 [0.413, 0.558] | 0.109 | 0.114 | 0.134 | 0.073 | 0.128 | 0.151 | 0.165 | 3/33/0 | INCONCLUSIVE |

### AUROC by rareness band / variant, base split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.63 | 0.61 | 0.61 | 0.64 | 0.63 | 0.62 |
| sanity | 0.52 | 0.49 | 0.52 | 0.52 | 0.51 | 0.50 |
| classhist | 0.79 | 0.77 | 0.78 | 0.71 | 0.73 | 0.70 |
| rare | 0.55 | 0.54 | 0.54 | 0.64 | 0.59 | 0.63 |
| gnn-yasaei | 0.97 | 0.97 | 0.97 | 0.99 | 0.99 | 0.99 |
| gnn-a | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.99 | 0.98 | 0.97 | 1.00 | 1.00 | 1.00 |
| graphlet-b | 0.53 | 0.50 | 0.48 | 0.50 | 0.52 | 0.48 |

### AUROC by set, base split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | 0.70 | 0.65 | 0.61 |
| sanity | 0.59 | 0.46 | 0.50 |
| classhist | 0.65 | 0.80 | 0.76 |
| rare | 0.58 | 0.58 | 0.59 |
| gnn-yasaei | 1.00 | 0.98 | 0.96 |
| gnn-a | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.99 | 1.00 | 0.98 |
| graphlet-b | 0.49 | 0.48 | 0.52 |

### AUROC by Trojan count, base split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.61 | 0.64 | 0.66 |
| sanity | 0.51 | 0.51 | 0.51 |
| classhist | 0.71 | 0.77 | 0.82 |
| rare | 0.58 | 0.58 | 0.63 |
| gnn-yasaei | 0.97 | 0.99 | 0.99 |
| gnn-a | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.98 | 0.99 | 1.00 |
| graphlet-b | 0.51 | 0.50 | 0.49 |

### AUROC by rareness band / variant, set-K4 split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.64 | 0.62 | 0.64 | 0.65 | 0.67 | 0.65 |
| sanity | 0.54 | 0.52 | 0.50 | 0.50 | 0.51 | 0.47 |
| classhist | 0.84 | 0.82 | 0.85 | 0.71 | 0.74 | 0.75 |
| rare | 0.54 | 0.58 | 0.55 | 0.62 | 0.55 | 0.64 |
| gnn-yasaei | 0.98 | 0.98 | 0.97 | 0.98 | 0.98 | 0.98 |
| gnn-a | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.99 | 0.97 | 0.97 | 0.99 | 0.99 | 0.99 |
| graphlet-b | 0.50 | 0.48 | 0.44 | 0.46 | 0.52 | 0.48 |

### AUROC by set, set-K4 split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | n/a | 0.65 | n/a |
| sanity | n/a | 0.51 | n/a |
| classhist | n/a | 0.78 | n/a |
| rare | n/a | 0.58 | n/a |
| gnn-yasaei | n/a | 0.98 | n/a |
| gnn-a | n/a | 1.00 | n/a |
| gnn-a-nosc | n/a | 0.98 | n/a |
| graphlet-b | n/a | 0.48 | n/a |

### AUROC by Trojan count, set-K4 split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.65 | 0.63 | 0.67 |
| sanity | 0.53 | 0.48 | 0.45 |
| classhist | 0.75 | 0.81 | 0.84 |
| rare | 0.58 | 0.56 | 0.64 |
| gnn-yasaei | 0.98 | 0.98 | 0.99 |
| gnn-a | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.98 | 0.99 | 0.99 |
| graphlet-b | 0.49 | 0.47 | 0.45 |

### AUROC by rareness band / variant, set-K6 split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.61 | 0.58 | 0.58 | 0.67 | 0.64 | 0.59 |
| sanity | 0.53 | 0.44 | 0.49 | 0.54 | 0.46 | 0.45 |
| classhist | 0.77 | 0.78 | 0.73 | 0.71 | 0.73 | 0.68 |
| rare | 0.59 | 0.51 | 0.53 | 0.66 | 0.61 | 0.63 |
| gnn-yasaei | 0.93 | 0.95 | 0.92 | 0.98 | 0.98 | 0.98 |
| gnn-a | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.96 | 0.95 | 0.93 | 0.98 | 0.98 | 0.99 |
| graphlet-b | 0.54 | 0.49 | 0.52 | 0.52 | 0.50 | 0.51 |

### AUROC by set, set-K6 split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | n/a | n/a | 0.62 |
| sanity | n/a | n/a | 0.50 |
| classhist | n/a | n/a | 0.74 |
| rare | n/a | n/a | 0.59 |
| gnn-yasaei | n/a | n/a | 0.95 |
| gnn-a | n/a | n/a | 1.00 |
| gnn-a-nosc | n/a | n/a | 0.97 |
| graphlet-b | n/a | n/a | 0.52 |

### AUROC by Trojan count, set-K6 split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.60 | 0.62 | 0.65 |
| sanity | 0.50 | 0.49 | 0.50 |
| classhist | 0.68 | 0.78 | 0.84 |
| rare | 0.60 | 0.57 | 0.61 |
| gnn-yasaei | 0.94 | 0.97 | 0.98 |
| gnn-a | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.96 | 0.98 | 0.98 |
| graphlet-b | 0.52 | 0.53 | 0.49 |

### AUROC by rareness band / variant, set-G split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.68 | 0.65 | 0.62 | 0.71 | 0.64 | 0.66 |
| sanity | 0.49 | 0.45 | 0.50 | 0.46 | 0.53 | 0.53 |
| classhist | 0.47 | 0.50 | 0.50 | 0.43 | 0.45 | 0.35 |
| rare | 0.52 | 0.53 | 0.54 | 0.66 | 0.59 | 0.62 |
| gnn-yasaei | 0.79 | 0.82 | 0.80 | 0.88 | 0.86 | 0.87 |
| gnn-a | 0.94 | 0.94 | 0.93 | 0.97 | 0.96 | 0.96 |
| gnn-a-nosc | 0.93 | 0.94 | 0.92 | 1.00 | 1.00 | 1.00 |
| graphlet-b | 0.50 | 0.48 | 0.49 | 0.50 | 0.52 | 0.45 |

### AUROC by set, set-G split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | 0.67 | n/a | n/a |
| sanity | 0.49 | n/a | n/a |
| classhist | 0.45 | n/a | n/a |
| rare | 0.58 | n/a | n/a |
| gnn-yasaei | 0.84 | n/a | n/a |
| gnn-a | 0.95 | n/a | n/a |
| gnn-a-nosc | 0.96 | n/a | n/a |
| graphlet-b | 0.49 | n/a | n/a |

### AUROC by Trojan count, set-G split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.64 | 0.68 | 0.73 |
| sanity | 0.50 | 0.45 | 0.51 |
| classhist | 0.45 | 0.44 | 0.47 |
| rare | 0.56 | 0.61 | 0.62 |
| gnn-yasaei | 0.83 | 0.85 | 0.87 |
| gnn-a | 0.94 | 0.96 | 0.96 |
| gnn-a-nosc | 0.94 | 0.98 | 0.99 |
| graphlet-b | 0.50 | 0.47 | 0.49 |

## Seq (seeker-seq-v2.0-rc4): superseded, the latch init leak case (section 8)

Circuits 10375, bases 36.

### Headline (means over folds and seeds; AUROC with 95% base-bootstrap)

| detector | split | AUROC [95% CI] | TPR | FPR | F1 rel | F1 10% | F1 30% | F1 50% | F1 70% | W/L/T vs size | label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| size | base | 0.634 [0.605, 0.707] | 0.145 | 0.095 | 0.133 | 0.072 | 0.123 | 0.151 | 0.168 | control | ABOVE CHANCE |
| sanity | base | 0.505 [0.475, 0.557] | 0.022 | 0.025 | 0.034 | 0.020 | 0.032 | 0.036 | 0.038 | 5/31/0 | INCONCLUSIVE |
| classhist | base | 0.745 [0.718, 0.796] | 0.317 | 0.062 | 0.417 | 0.310 | 0.402 | 0.429 | 0.443 | 17/19/0 | ABOVE CHANCE |
| rare | base | 0.533 [0.503, 0.598] | 0.062 | 0.039 | 0.098 | 0.069 | 0.094 | 0.102 | 0.106 | 5/31/0 | ABOVE CHANCE |
| gnn-yasaei | base | 0.980 [0.960, 0.994] | 0.828 | 0.078 | 0.808 | 0.661 | 0.789 | 0.829 | 0.848 | 32/4/0 | ABOVE CHANCE |
| gnn-a | base | 0.999 [0.997, 1.000] | 0.993 | 0.143 | 0.903 | 0.732 | 0.879 | 0.936 | 0.968 | 33/2/1 | ABOVE CHANCE |
| gnn-a-nosc | base | 0.981 [0.959, 0.996] | 0.924 | 0.106 | 0.880 | 0.662 | 0.849 | 0.906 | 0.933 | 33/2/1 | ABOVE CHANCE |
| graphlet-b | base | 0.498 [0.452, 0.538] | 0.128 | 0.080 | 0.155 | 0.092 | 0.147 | 0.170 | 0.183 | 2/34/0 | INCONCLUSIVE |
| size | set-K4 | 0.654 [0.613, 0.765] | 0.130 | 0.097 | 0.113 | 0.043 | 0.094 | 0.122 | 0.140 | control | ABOVE CHANCE |
| sanity | set-K4 | 0.516 [0.434, 0.581] | 0.069 | 0.091 | 0.091 | 0.050 | 0.081 | 0.097 | 0.107 | 0/34/2 | INCONCLUSIVE |
| classhist | set-K4 | 0.777 [0.743, 0.835] | 0.584 | 0.270 | 0.529 | 0.294 | 0.477 | 0.566 | 0.620 | 5/31/0 | ABOVE CHANCE |
| rare | set-K4 | 0.522 [0.471, 0.606] | 0.045 | 0.038 | 0.073 | 0.050 | 0.069 | 0.075 | 0.078 | 3/33/0 | INCONCLUSIVE |
| gnn-yasaei | set-K4 | 0.982 [0.956, 0.998] | 0.891 | 0.099 | 0.870 | 0.722 | 0.844 | 0.887 | 0.910 | 15/7/14 | ABOVE CHANCE |
| gnn-a | set-K4 | 0.988 [0.958, 0.999] | 1.000 | 0.129 | 0.920 | 0.758 | 0.890 | 0.944 | 0.974 | 15/3/18 | ABOVE CHANCE |
| gnn-a-nosc | set-K4 | 0.984 [0.968, 0.999] | 0.771 | 0.103 | 0.715 | 0.505 | 0.683 | 0.737 | 0.764 | 15/5/16 | ABOVE CHANCE |
| graphlet-b | set-K4 | 0.472 [0.396, 0.546] | 0.076 | 0.050 | 0.084 | 0.047 | 0.081 | 0.096 | 0.105 | 0/36/0 | INCONCLUSIVE |
| size | set-K6 | 0.622 [0.599, 0.736] | 0.451 | 0.307 | 0.426 | 0.181 | 0.365 | 0.459 | 0.516 | control | ABOVE CHANCE |
| sanity | set-K6 | 0.493 [0.437, 0.568] | 0.065 | 0.029 | 0.084 | 0.050 | 0.079 | 0.089 | 0.094 | 6/29/1 | INCONCLUSIVE |
| classhist | set-K6 | 0.739 [0.693, 0.830] | 0.377 | 0.060 | 0.472 | 0.382 | 0.456 | 0.481 | 0.494 | 11/24/1 | ABOVE CHANCE |
| rare | set-K6 | 0.538 [0.454, 0.642] | 0.053 | 0.070 | 0.083 | 0.060 | 0.079 | 0.086 | 0.090 | 3/33/0 | INCONCLUSIVE |
| gnn-yasaei | set-K6 | 0.955 [0.921, 0.981] | 0.943 | 0.056 | 0.936 | 0.843 | 0.919 | 0.945 | 0.959 | 18/17/1 | ABOVE CHANCE |
| gnn-a | set-K6 | 1.000 [0.999, 1.000] | 0.985 | 0.170 | 0.901 | 0.729 | 0.860 | 0.922 | 0.959 | 23/1/12 | ABOVE CHANCE |
| gnn-a-nosc | set-K6 | 0.957 [0.925, 0.983] | 0.946 | 0.075 | 0.926 | 0.789 | 0.900 | 0.938 | 0.957 | 17/17/2 | ABOVE CHANCE |
| graphlet-b | set-K6 | 0.512 [0.450, 0.579] | 0.179 | 0.119 | 0.194 | 0.101 | 0.175 | 0.208 | 0.227 | 0/36/0 | INCONCLUSIVE |
| size | set-G | 0.666 [0.624, 0.753] | 0.087 | 0.071 | 0.071 | 0.038 | 0.077 | 0.097 | 0.110 | control | ABOVE CHANCE |
| sanity | set-G | 0.489 [0.420, 0.573] | 0.083 | 0.118 | 0.102 | 0.057 | 0.093 | 0.113 | 0.126 | 11/25/0 | INCONCLUSIVE |
| classhist | set-G | 0.451 [0.397, 0.497] | 0.984 | 0.985 | 0.526 | 0.181 | 0.459 | 0.662 | 0.817 | 0/36/0 | BELOW CHANCE |
| rare | set-G | 0.532 [0.477, 0.599] | 0.070 | 0.031 | 0.103 | 0.074 | 0.102 | 0.111 | 0.115 | 6/30/0 | INCONCLUSIVE |
| gnn-yasaei | set-G | 0.785 [0.727, 0.854] | 0.830 | 0.780 | 0.486 | 0.176 | 0.423 | 0.593 | 0.717 | 17/17/2 | ABOVE CHANCE |
| gnn-a | set-G | 0.926 [0.865, 0.974] | 0.997 | 0.645 | 0.634 | 0.265 | 0.576 | 0.758 | 0.878 | 24/5/7 | ABOVE CHANCE |
| gnn-a-nosc | set-G | 0.973 [0.960, 0.986] | 0.932 | 0.796 | 0.593 | 0.305 | 0.529 | 0.693 | 0.819 | 25/5/6 | ABOVE CHANCE |
| graphlet-b | set-G | 0.492 [0.420, 0.561] | 0.110 | 0.114 | 0.133 | 0.073 | 0.127 | 0.151 | 0.164 | 1/35/0 | INCONCLUSIVE |

### AUROC by rareness band / variant, base split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.64 | 0.62 | 0.62 | 0.65 | 0.64 | 0.63 |
| sanity | 0.51 | 0.48 | 0.52 | 0.51 | 0.51 | 0.49 |
| classhist | 0.79 | 0.77 | 0.78 | 0.71 | 0.73 | 0.70 |
| rare | 0.54 | 0.53 | 0.53 | 0.53 | 0.51 | 0.55 |
| gnn-yasaei | 0.97 | 0.97 | 0.97 | 0.99 | 0.99 | 0.99 |
| gnn-a | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.98 | 0.98 | 0.97 | 0.99 | 0.99 | 0.99 |
| graphlet-b | 0.53 | 0.49 | 0.49 | 0.50 | 0.51 | 0.47 |

### AUROC by set, base split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | 0.71 | 0.65 | 0.62 |
| sanity | 0.57 | 0.46 | 0.50 |
| classhist | 0.64 | 0.80 | 0.76 |
| rare | 0.53 | 0.52 | 0.54 |
| gnn-yasaei | 1.00 | 0.98 | 0.96 |
| gnn-a | 0.99 | 1.00 | 1.00 |
| gnn-a-nosc | 1.00 | 0.98 | 0.96 |
| graphlet-b | 0.49 | 0.47 | 0.51 |

### AUROC by Trojan count, base split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.62 | 0.65 | 0.67 |
| sanity | 0.50 | 0.51 | 0.51 |
| classhist | 0.71 | 0.77 | 0.82 |
| rare | 0.53 | 0.53 | 0.57 |
| gnn-yasaei | 0.97 | 0.99 | 0.99 |
| gnn-a | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.98 | 0.99 | 0.99 |
| graphlet-b | 0.50 | 0.50 | 0.48 |

### AUROC by rareness band / variant, set-K4 split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.65 | 0.63 | 0.64 | 0.65 | 0.68 | 0.66 |
| sanity | 0.54 | 0.53 | 0.52 | 0.51 | 0.52 | 0.47 |
| classhist | 0.83 | 0.82 | 0.83 | 0.72 | 0.74 | 0.74 |
| rare | 0.52 | 0.56 | 0.56 | 0.48 | 0.48 | 0.57 |
| gnn-yasaei | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 |
| gnn-a | 0.99 | 0.99 | 0.99 | 0.99 | 0.99 | 0.98 |
| gnn-a-nosc | 0.97 | 0.97 | 0.97 | 1.00 | 1.00 | 1.00 |
| graphlet-b | 0.50 | 0.46 | 0.44 | 0.45 | 0.51 | 0.46 |

### AUROC by set, set-K4 split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | n/a | 0.65 | n/a |
| sanity | n/a | 0.52 | n/a |
| classhist | n/a | 0.78 | n/a |
| rare | n/a | 0.52 | n/a |
| gnn-yasaei | n/a | 0.98 | n/a |
| gnn-a | n/a | 0.99 | n/a |
| gnn-a-nosc | n/a | 0.98 | n/a |
| graphlet-b | n/a | 0.47 | n/a |

### AUROC by Trojan count, set-K4 split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.65 | 0.64 | 0.67 |
| sanity | 0.54 | 0.49 | 0.46 |
| classhist | 0.75 | 0.80 | 0.83 |
| rare | 0.52 | 0.50 | 0.57 |
| gnn-yasaei | 0.98 | 0.98 | 0.99 |
| gnn-a | 0.99 | 0.99 | 0.99 |
| gnn-a-nosc | 0.98 | 0.99 | 0.99 |
| graphlet-b | 0.48 | 0.47 | 0.43 |

### AUROC by rareness band / variant, set-K6 split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.62 | 0.58 | 0.58 | 0.67 | 0.64 | 0.60 |
| sanity | 0.53 | 0.44 | 0.49 | 0.54 | 0.46 | 0.45 |
| classhist | 0.79 | 0.78 | 0.76 | 0.69 | 0.75 | 0.67 |
| rare | 0.58 | 0.50 | 0.52 | 0.54 | 0.53 | 0.56 |
| gnn-yasaei | 0.92 | 0.95 | 0.93 | 0.98 | 0.98 | 0.98 |
| gnn-a | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.94 | 0.94 | 0.92 | 0.98 | 0.98 | 0.98 |
| graphlet-b | 0.53 | 0.48 | 0.52 | 0.51 | 0.50 | 0.50 |

### AUROC by set, set-K6 split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | n/a | n/a | 0.62 |
| sanity | n/a | n/a | 0.49 |
| classhist | n/a | n/a | 0.74 |
| rare | n/a | n/a | 0.54 |
| gnn-yasaei | n/a | n/a | 0.96 |
| gnn-a | n/a | n/a | 1.00 |
| gnn-a-nosc | n/a | n/a | 0.96 |
| graphlet-b | n/a | n/a | 0.51 |

### AUROC by Trojan count, set-K6 split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.60 | 0.62 | 0.66 |
| sanity | 0.50 | 0.48 | 0.50 |
| classhist | 0.68 | 0.78 | 0.87 |
| rare | 0.54 | 0.53 | 0.56 |
| gnn-yasaei | 0.94 | 0.97 | 0.98 |
| gnn-a | 1.00 | 1.00 | 1.00 |
| gnn-a-nosc | 0.94 | 0.98 | 0.98 |
| graphlet-b | 0.51 | 0.53 | 0.48 |

### AUROC by rareness band / variant, set-G split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.67 | 0.63 | 0.61 | 0.73 | 0.65 | 0.66 |
| sanity | 0.49 | 0.45 | 0.50 | 0.46 | 0.53 | 0.53 |
| classhist | 0.46 | 0.49 | 0.50 | 0.45 | 0.45 | 0.37 |
| rare | 0.51 | 0.51 | 0.52 | 0.58 | 0.51 | 0.53 |
| gnn-yasaei | 0.73 | 0.76 | 0.76 | 0.82 | 0.82 | 0.83 |
| gnn-a | 0.94 | 0.93 | 0.93 | 0.92 | 0.92 | 0.91 |
| gnn-a-nosc | 0.94 | 0.96 | 0.94 | 1.00 | 1.00 | 1.00 |
| graphlet-b | 0.51 | 0.49 | 0.50 | 0.50 | 0.52 | 0.45 |

### AUROC by set, set-G split

| detector | G | K4 | K6 |
|---|---|---|---|
| size | 0.67 | n/a | n/a |
| sanity | 0.49 | n/a | n/a |
| classhist | 0.45 | n/a | n/a |
| rare | 0.53 | n/a | n/a |
| gnn-yasaei | 0.79 | n/a | n/a |
| gnn-a | 0.93 | n/a | n/a |
| gnn-a-nosc | 0.97 | n/a | n/a |
| graphlet-b | 0.49 | n/a | n/a |

### AUROC by Trojan count, set-G split

| detector | 1 | 2 | 3 |
|---|---|---|---|
| size | 0.64 | 0.68 | 0.72 |
| sanity | 0.50 | 0.46 | 0.51 |
| classhist | 0.46 | 0.44 | 0.47 |
| rare | 0.52 | 0.55 | 0.58 |
| gnn-yasaei | 0.77 | 0.79 | 0.81 |
| gnn-a | 0.91 | 0.94 | 0.94 |
| gnn-a-nosc | 0.96 | 0.98 | 0.99 |
| graphlet-b | 0.50 | 0.48 | 0.50 |

## Comb (seeker-comb-v2.0-rc1)

Circuits 1596, bases 31.

### Headline (means over folds and seeds; AUROC with 95% base-bootstrap)

| detector | split | AUROC [95% CI] | TPR | FPR | F1 rel | F1 10% | F1 30% | F1 50% | F1 70% | W/L/T vs size | label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| size | base | 0.709 [0.634, 0.791] | 0.071 | 0.037 | 0.115 | 0.072 | 0.102 | 0.112 | 0.116 | control | ABOVE CHANCE |
| sanity | base | 0.686 [0.601, 0.767] | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 4/15/0 | ABOVE CHANCE |
| classhist | base | 0.688 [0.597, 0.772] | 0.165 | 0.100 | 0.219 | 0.101 | 0.172 | 0.203 | 0.221 | 9/10/0 | ABOVE CHANCE |
| rare | base | 0.639 [0.561, 0.731] | 0.156 | 0.079 | 0.225 | 0.124 | 0.193 | 0.218 | 0.231 | 7/12/0 | ABOVE CHANCE |
| gnn-yasaei | base | 0.703 [0.625, 0.784] | 0.126 | 0.073 | 0.198 | 0.122 | 0.173 | 0.192 | 0.201 | 6/13/0 | ABOVE CHANCE |
| gnn-a | base | 0.700 [0.615, 0.779] | 0.137 | 0.085 | 0.209 | 0.119 | 0.179 | 0.201 | 0.212 | 6/13/0 | ABOVE CHANCE |
| graphlet-b | base | 0.611 [0.536, 0.688] | 0.125 | 0.090 | 0.191 | 0.105 | 0.159 | 0.181 | 0.193 | 3/16/0 | ABOVE CHANCE |
| size | lut | 0.706 [0.627, 0.795] | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | control | ABOVE CHANCE |
| sanity | lut | 0.701 [0.621, 0.782] | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 7/11/1 | ABOVE CHANCE |
| classhist | lut | 0.684 [0.594, 0.762] | 0.800 | 0.567 | 0.657 | 0.192 | 0.439 | 0.591 | 0.695 | 4/15/0 | ABOVE CHANCE |
| rare | lut | 0.616 [0.523, 0.708] | 0.093 | 0.042 | 0.144 | 0.090 | 0.126 | 0.139 | 0.145 | 5/12/2 | ABOVE CHANCE |
| gnn-yasaei | lut | 0.593 [0.522, 0.709] | 0.214 | 0.146 | 0.198 | 0.068 | 0.141 | 0.182 | 0.208 | 8/8/3 | ABOVE CHANCE |
| gnn-a | lut | 0.706 [0.635, 0.801] | 0.100 | 0.052 | 0.139 | 0.076 | 0.119 | 0.135 | 0.144 | 13/5/1 | ABOVE CHANCE |
| graphlet-b | lut | 0.581 [0.493, 0.687] | 0.687 | 0.595 | 0.652 | 0.191 | 0.433 | 0.582 | 0.684 | 7/12/0 | INCONCLUSIVE |

### AUROC by form, base split

| detector | balance | compress | compress2 | dc2 | dc2x2 | identity | lut4 | lut5 | lut6 | lut6mfs | refactor | resub | resyn | resyn2 | resyn2a | resyn2rs | resyn3 | rewrite | strash |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size | 0.77 | 0.76 | 0.72 | 0.71 | 0.72 | 0.78 | 0.74 | 0.72 | 0.70 | 0.71 | 0.77 | 0.78 | 0.75 | 0.75 | 0.76 | 0.73 | 0.76 | 0.78 | 0.78 |
| sanity | 0.71 | 0.71 | 0.70 | 0.70 | 0.70 | 0.54 | 0.70 | 0.69 | 0.70 | 0.71 | 0.68 | 0.71 | 0.70 | 0.70 | 0.70 | 0.70 | 0.71 | 0.71 | 0.71 |
| classhist | 0.73 | 0.69 | 0.70 | 0.67 | 0.66 | 0.67 | 0.71 | 0.75 | 0.67 | 0.67 | 0.71 | 0.72 | 0.72 | 0.72 | 0.72 | 0.70 | 0.71 | 0.73 | 0.74 |
| rare | 0.64 | 0.66 | 0.65 | 0.64 | 0.63 | 0.65 | 0.65 | 0.62 | 0.59 | 0.59 | 0.62 | 0.64 | 0.64 | 0.65 | 0.66 | 0.66 | 0.65 | 0.67 | 0.62 |
| gnn-yasaei | 0.71 | 0.73 | 0.74 | 0.68 | 0.69 | 0.68 | 0.69 | 0.69 | 0.71 | 0.71 | 0.71 | 0.71 | 0.73 | 0.71 | 0.73 | 0.75 | 0.71 | 0.70 | 0.71 |
| gnn-a | 0.72 | 0.70 | 0.73 | 0.71 | 0.69 | 0.73 | 0.74 | 0.70 | 0.71 | 0.71 | 0.71 | 0.71 | 0.71 | 0.69 | 0.70 | 0.70 | 0.70 | 0.73 | 0.72 |
| graphlet-b | 0.60 | 0.60 | 0.63 | 0.65 | 0.66 | 1.00 | 0.53 | 0.59 | 0.60 | 0.59 | 0.56 | 0.55 | 0.60 | 0.62 | 0.59 | 0.65 | 0.60 | 0.64 | 0.58 |

### AUROC by rareness band / variant, base split

| detector | p<1e-2 | p<1e-3 | p<1e-4 |
|---|---|---|---|
| size | 0.70 | 0.71 | 0.71 |
| sanity | 0.69 | 0.68 | 0.69 |
| classhist | 0.68 | 0.69 | 0.70 |
| rare | 0.64 | 0.64 | 0.64 |
| gnn-yasaei | 0.69 | 0.71 | 0.71 |
| gnn-a | 0.70 | 0.70 | 0.70 |
| graphlet-b | 0.61 | 0.61 | 0.61 |

### AUROC by form, lut split

| detector | balance | compress | compress2 | dc2 | dc2x2 | identity | lut4 | lut5 | lut6 | lut6mfs | refactor | resub | resyn | resyn2 | resyn2a | resyn2rs | resyn3 | rewrite | strash |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size | n/a | n/a | n/a | n/a | n/a | n/a | 0.74 | 0.72 | 0.71 | 0.71 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| sanity | n/a | n/a | n/a | n/a | n/a | n/a | 0.70 | 0.69 | 0.70 | 0.71 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| classhist | n/a | n/a | n/a | n/a | n/a | n/a | 0.69 | 0.67 | 0.67 | 0.68 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rare | n/a | n/a | n/a | n/a | n/a | n/a | 0.65 | 0.62 | 0.59 | 0.59 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| gnn-yasaei | n/a | n/a | n/a | n/a | n/a | n/a | 0.63 | 0.59 | 0.59 | 0.60 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| gnn-a | n/a | n/a | n/a | n/a | n/a | n/a | 0.71 | 0.72 | 0.71 | 0.71 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| graphlet-b | n/a | n/a | n/a | n/a | n/a | n/a | 0.53 | 0.59 | 0.60 | 0.59 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### AUROC by rareness band / variant, lut split

| detector | p<1e-2 | p<1e-3 | p<1e-4 |
|---|---|---|---|
| size | 0.70 | 0.70 | 0.71 |
| sanity | 0.70 | 0.70 | 0.70 |
| classhist | 0.68 | 0.68 | 0.69 |
| rare | 0.61 | 0.62 | 0.62 |
| gnn-yasaei | 0.59 | 0.59 | 0.59 |
| gnn-a | 0.71 | 0.70 | 0.70 |
| graphlet-b | 0.60 | 0.56 | 0.57 |

## Seq (seeker-seq-v2.0-rc2)

Circuits 4389, bases 48.

### Headline (means over folds and seeds; AUROC with 95% base-bootstrap)

| detector | split | AUROC [95% CI] | TPR | FPR | F1 rel | F1 10% | F1 30% | F1 50% | F1 70% | W/L/T vs size | label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| size | base | 0.591 [0.563, 0.650] | 0.125 | 0.083 | 0.197 | 0.099 | 0.159 | 0.181 | 0.193 | control | ABOVE CHANCE |
| sanity | base | 0.510 [0.478, 0.549] | 0.051 | 0.053 | 0.092 | 0.056 | 0.079 | 0.086 | 0.090 | 6/40/0 | INCONCLUSIVE |
| classhist | base | 0.575 [0.547, 0.637] | 0.100 | 0.085 | 0.156 | 0.077 | 0.121 | 0.141 | 0.152 | 30/16/0 | ABOVE CHANCE |
| rare | base | 0.452 [0.420, 0.524] | 0.010 | 0.046 | 0.020 | 0.013 | 0.017 | 0.019 | 0.020 | 19/27/0 | INCONCLUSIVE |
| gnn-yasaei | base | 0.624 [0.574, 0.674] | 0.081 | 0.074 | 0.144 | 0.089 | 0.125 | 0.136 | 0.142 | 22/24/0 | ABOVE CHANCE |
| gnn-a | base | 0.974 [0.946, 0.994] | 0.812 | 0.096 | 0.812 | 0.594 | 0.732 | 0.779 | 0.803 | 45/1/0 | ABOVE CHANCE |
| graphlet-b | base | 0.495 [0.453, 0.541] | 0.113 | 0.075 | 0.191 | 0.121 | 0.163 | 0.179 | 0.188 | 11/34/1 | INCONCLUSIVE |
| size | lut | 0.563 [0.527, 0.624] | 0.213 | 0.162 | 0.283 | 0.109 | 0.202 | 0.247 | 0.274 | control | ABOVE CHANCE |
| sanity | lut | 0.501 [0.461, 0.541] | 0.141 | 0.158 | 0.228 | 0.111 | 0.177 | 0.205 | 0.222 | 18/24/4 | INCONCLUSIVE |
| classhist | lut | 0.551 [0.511, 0.640] | 0.207 | 0.223 | 0.302 | 0.105 | 0.208 | 0.260 | 0.291 | 28/15/3 | ABOVE CHANCE |
| rare | lut | 0.456 [0.412, 0.536] | 0.006 | 0.089 | 0.011 | 0.004 | 0.008 | 0.010 | 0.011 | 27/18/1 | INCONCLUSIVE |
| gnn-yasaei | lut | 0.591 [0.542, 0.625] | 0.374 | 0.334 | 0.445 | 0.132 | 0.284 | 0.369 | 0.425 | 14/32/0 | ABOVE CHANCE |
| gnn-a | lut | 0.947 [0.899, 0.992] | 0.803 | 0.097 | 0.813 | 0.625 | 0.739 | 0.782 | 0.805 | 44/2/0 | ABOVE CHANCE |
| graphlet-b | lut | 0.483 [0.427, 0.537] | 0.135 | 0.108 | 0.216 | 0.127 | 0.175 | 0.198 | 0.211 | 14/32/0 | INCONCLUSIVE |

### AUROC by form, base split

| detector | balance | compress | compress2 | dc2 | dc2x2 | identity | lut4 | lut5 | lut6 | lut6mfs | refactor | resub | resyn | resyn2 | resyn2a | resyn2rs | resyn3 | rewrite | strash |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size | 0.62 | 0.59 | 0.59 | 0.60 | 0.59 | 0.64 | 0.58 | 0.55 | 0.56 | 0.56 | 0.61 | 0.61 | 0.61 | 0.61 | 0.61 | 0.61 | 0.61 | 0.60 | 0.62 |
| sanity | 0.50 | 0.52 | 0.53 | 0.48 | 0.48 | 0.53 | 0.48 | 0.48 | 0.54 | 0.53 | 0.50 | 0.51 | 0.54 | 0.51 | 0.53 | 0.53 | 0.52 | 0.50 | 0.50 |
| classhist | 0.65 | 0.63 | 0.58 | 0.58 | 0.56 | 0.62 | 0.54 | 0.55 | 0.55 | 0.55 | 0.59 | 0.65 | 0.64 | 0.59 | 0.63 | 0.59 | 0.65 | 0.63 | 0.64 |
| rare | 0.47 | 0.46 | 0.44 | 0.44 | 0.44 | 0.49 | 0.46 | 0.46 | 0.45 | 0.45 | 0.45 | 0.46 | 0.46 | 0.44 | 0.47 | 0.45 | 0.46 | 0.47 | 0.47 |
| gnn-yasaei | 0.66 | 0.66 | 0.65 | 0.66 | 0.65 | 0.61 | 0.58 | 0.60 | 0.55 | 0.55 | 0.66 | 0.65 | 0.67 | 0.66 | 0.66 | 0.65 | 0.64 | 0.67 | 0.66 |
| gnn-a | 0.98 | 0.98 | 0.98 | 0.94 | 0.94 | 0.98 | 0.98 | 0.99 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0.97 | 0.98 | 0.98 |
| graphlet-b | 0.54 | 0.45 | 0.46 | 0.43 | 0.43 | 1.00 | 0.45 | 0.45 | 0.49 | 0.50 | 0.46 | 0.50 | 0.45 | 0.45 | 0.46 | 0.45 | 0.48 | 0.46 | 0.53 |

### AUROC by rareness band / variant, base split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.66 | 0.63 | 0.64 | 0.54 | 0.52 | 0.57 |
| sanity | 0.51 | 0.51 | 0.54 | 0.50 | 0.50 | 0.50 |
| classhist | 0.60 | 0.56 | 0.59 | 0.58 | 0.54 | 0.55 |
| rare | 0.41 | 0.42 | 0.45 | 0.51 | 0.44 | 0.44 |
| gnn-yasaei | 0.67 | 0.64 | 0.66 | 0.59 | 0.61 | 0.61 |
| gnn-a | 0.97 | 0.97 | 0.97 | 0.98 | 0.99 | 0.99 |
| graphlet-b | 0.51 | 0.50 | 0.48 | 0.52 | 0.50 | 0.40 |

### AUROC by form, lut split

| detector | balance | compress | compress2 | dc2 | dc2x2 | identity | lut4 | lut5 | lut6 | lut6mfs | refactor | resub | resyn | resyn2 | resyn2a | resyn2rs | resyn3 | rewrite | strash |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| size | n/a | n/a | n/a | n/a | n/a | n/a | 0.58 | 0.55 | 0.56 | 0.55 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| sanity | n/a | n/a | n/a | n/a | n/a | n/a | 0.48 | 0.47 | 0.54 | 0.53 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| classhist | n/a | n/a | n/a | n/a | n/a | n/a | 0.58 | 0.55 | 0.54 | 0.55 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rare | n/a | n/a | n/a | n/a | n/a | n/a | 0.46 | 0.46 | 0.45 | 0.45 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| gnn-yasaei | n/a | n/a | n/a | n/a | n/a | n/a | 0.59 | 0.60 | 0.59 | 0.59 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| gnn-a | n/a | n/a | n/a | n/a | n/a | n/a | 0.94 | 0.95 | 0.95 | 0.95 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| graphlet-b | n/a | n/a | n/a | n/a | n/a | n/a | 0.45 | 0.45 | 0.49 | 0.50 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### AUROC by rareness band / variant, lut split

| detector | ctr-fast | ctr-mid | ctr-slow | pat-fast | pat-mid | pat-slow |
|---|---|---|---|---|---|---|
| size | 0.63 | 0.60 | 0.63 | 0.52 | 0.47 | 0.54 |
| sanity | 0.52 | 0.53 | 0.51 | 0.50 | 0.44 | 0.50 |
| classhist | 0.54 | 0.53 | 0.52 | 0.61 | 0.53 | 0.51 |
| rare | 0.41 | 0.43 | 0.45 | 0.50 | 0.45 | 0.46 |
| gnn-yasaei | 0.63 | 0.64 | 0.61 | 0.52 | 0.58 | 0.62 |
| gnn-a | 0.93 | 0.93 | 0.93 | 0.96 | 0.96 | 0.98 |
| graphlet-b | 0.49 | 0.47 | 0.44 | 0.49 | 0.52 | 0.44 |

Circuits not scored (Odin III timeout or refusal; never imputed): rare 15, gnn-a 15, graphlet-b 23.
