# lemanrussIII
Leman Russ III is the hardware Trojan side branch of Yggdrasil III (hub: <https://github.com/drpaj12/YggdrasilIII>). It builds
benchmarks for the Seeker's Dilemma, finding Trojans when the detector does not know whether a circuit is infected, on Odin III.
It is defensive research: the circuits are Trojans to detect.

Stages, in order:

1. **Hardware Trojan Library (HTL):** triggers and payloads, composed with legality checks.
2. **Insertion** at HDL level and at netlist level (Odin III edit API, each new object tagged `trojan:<id>`).
3. **Pipeline:** a random ABC optimisation script, mapping (LUT k=4, LUT k=6, AND/OR/NOT), shuffling and renaming, so no file carries a label;
   cut-and-stitch keeps the energy and slow-down payloads through ABC.
4. **Gates and releases:** witness replay in Odin III, equivalence by ABC to the source, label-leak gates, then datasheets and checksums.
5. **Detector baselines and scoring:** a submission format and a scorer that does not publish the answer key.

Releases: Seeker-Comb v2.0-rc5 (5809 circuits, 31 bases), Seeker-Seq v2.0-rc7 (10503 circuits, 36 bases; magic-number triggers, no Trojan
flip-flops) and a Seeker-Proc pilot3 of four circuits. Seeker-Seq v2.0-rc6 (10735 circuits) is superseded by rc7: on rc6 the flip-flop count
alone separated the labels (AUROC 0.948) because the counter and pattern triggers and the energy ring add flip-flops; rc7 adds none (exact
flip-flop equality with the golden before ABC; AUROC 0.500 after), and the class-only GNNs that reached 0.98 to 1.00 on Seq rc5 / rc6 fall to
0.48 and 0.53 (size control 0.59). Headline (from the paper, kept locally by the author): detectors run on the
earlier releases find nothing on Seeker-Comb (AUROC 0.48 to 0.55); on Seeker-Seq they found almost everything through the Trojans' own
flip-flops, and rc7 removes that footprint. Release gates caught six kinds of label leak. Results: `docs/results-round9.md`.

## Features

Status: **works** = a `lemanruss` command or module on `main` with tests; **released** = a release candidate
checked in under `releases/`; **in progress** = specified or on a branch, not merged. Defensive research: the
circuits are Trojans to detect. Design and numbers: `docs/specs/`, `docs/results-*.md`. The paper is kept locally by the author.

| Feature | Status | Where |
|---|---|---|
| Hardware Trojan Library: triggers (rare-value AND, counter, FSM pattern, always-on, input pattern) and payloads (denial of service, error insertion, energy, slow-down), composed with legality checks | works | `lemanruss/htl/triggers.py`, `payloads.py`, `trojan.py`; `docs/user/README.md` |
| Insertion at HDL level and at netlist level (netlist Trojans as edit-API recipes, each new object tagged `trojan:<id>`) | works | `lemanruss/htl/insert_hdl.py`, `edit_netlist.py`, `insert_netlist.py`; `lemanruss insertion`, `lemanruss prov-demo` |
| Rare-site selection from signal probability and SCOAP | works | `lemanruss/htl/blif_sim.py`, `sites.py`, `lemanruss/detect/scoap_feat.py` |
| Seeker v2.0 families: Seeker-Comb and Seeker-Seq (a golden and three mapping sets per base: LUT k=4, LUT k=6, AND/OR/NOT gates; 10% to 70% infected, one to three Trojans) | works | `lemanruss family`, `lemanruss n200`; `lemanruss/htl/families.py`, `n200*.py` |
| Obfuscation: ABC restructurings (18 scripts) and mapping to the three sets, so structure does not betray the Trojan | works | `lemanruss restructure`, `lemanruss/htl/obfuscate.py`, `restructure.py` |
| Verification and release gates: witness replay in Odin III, equivalence by ABC to the source and to the golden with triggers off, label-leak gates (rejected draws are listed, never shipped) | works | `lemanruss verify`, `family-verify`, `release-report`; `lemanruss/htl/relverify.py` |
| Releases: Seeker-Comb v2.0-rc5 (5809 circuits, 31 bases) and Seeker-Seq v2.0-rc7 (10503 circuits, 36 bases) with datasheets and checksums; earlier candidates (rc1, rc2, rc4, Seq rc5, Seq rc6 (superseded by rc7: Trojan flip-flops separated its labels), Proc pilot, pilot2) kept under `releases/` as superseded | released | `releases/`, `lemanruss release` |
| Seeker-Proc: processor images (RV32I) lowered to netlists, pilot3 with four circuits (magic-word triggers only, no added flip-flop) | released (pilot) | `releases/seeker-proc-v2.0-pilot3`, `lemanruss/htl/proc_*.py`, `rv32i.py` |
| Rareness report: per-circuit and pooled tables of trigger activation probability | works | `lemanruss/htl/rareness.py`, `answer_key/rareness.md` in each release |
| RTL testbenches and `sim_tb` against iverilog; energy payload toggle counts; bases from the Mimir registry | works | `lemanruss rtl-tb`, `lemanruss energy`, `lemanruss bases` |
| Detector baselines: size-only control, rare-signal score, graphlet drift, exact-duplicate/style sanity check, GNNs (gnn-a, gnn-yasaei) on Comb rc4 and Seq rc5 | works | `lemanruss/detect/`, `docs/results-detectors.md`, `docs/specs/2026-11-01-detector-baselines-design.md` |
| Submission format and scorer: CSV per subset (id, infected, score, optional count and locations), aggregate report without publishing the answer key (confusion matrix, AUROC, found-rate by Trojan count, bonuses); subsets, regions and anonymisation tools. Hosting of the scoring service is not decided; the GitHub Actions packaging is an example only | works (scorer); hosting open | `lemanruss score`, `subsets`, `regions`, `anonymise`, `extract-csv`; `docs/user/SUBMISSION.md`, `docs/user/SCORING-MANUAL.md` |
| Cut-and-stitch: protect the energy and slow-down payloads from ABC by cutting them out of the host, optimising the host, mapping the part alone and stitching it back | works (in rc5 Comb and rc6 Seq; merged in PR 17) | `lemanruss/htl/cutstitch.py` (Round 9) |


## Release seeds and answer keys

The generator seed of a released build, with this code, regenerates its answer key, so it is not published. Released
manifests carry no seed. `lemanruss family` and `lemanruss n200` take the seed from `--seed` (throwaway builds), the
environment variable `LEMANRUSS_RELEASE_SEED`, or a private JSON file named by `LEMANRUSS_SEED_FILE`; with none of them
the build stops. Processor Trojan trigger words for `lemanruss/htl/proc_pilot3.py` come from the private file named by
`LEMANRUSS_PROC_MAGIC_FILE`. Answer keys ship as separate archives and are not in this repository.
