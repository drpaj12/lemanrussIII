# Seeker v2.0 public download and public tester: spec (2026-11-09)

Status: SPEC ONLY, for Peter's review. Nothing in this document has been built. No public repo, secret,
release, upload or workflow exists because of it. Plan: `docs/plans/2026-11-09-public-download-tester-plan.md`.

Purpose (hub `docs/purpose.md`, Leman Russ III, RQ "Leman Russ benchmark release"): make Seeker's Dilemma
v2.0 usable by outside detector authors. Measure: detector TPR, FPR and AUROC, obtained through the
scorer of `docs/specs/2026-11-02-scoring-design.md` (called "scoring design" below).

Peter's decisions, 2026-11-09 (brief, folded in):

1. Layout per benchmark: golden, then a set of 100 gates (AND/OR/NOT), 100 LUT k=4, 100 LUT k=6. Comb and
   Seq first; Proc and Si later in their own layout.
2. The 9 MCNC Comb bases are left out of the public download.
3. Real benchmark names are shown (base-name anonymisation off for the public release).
4. Tester: a new PUBLIC GitHub repo with the issue-form and Actions scorer of scoring design section 7
   (answer key as an encrypted secret, ledger in a private repo).
5. Downloads as GitHub releases on `drpaj12/lemanrussIII`: one tarball per benchmark plus one per family,
   and an index page per benchmark in the repo docs.

Data was read from the rc5 (Comb) and rc8 (Seq) answer keys on the archive drive (read-only, copied to a
scratch directory outside the repo). Only counts and aggregates appear here: no circuit id, label, seed
or answer-key file is quoted or committed.

## 1. Headline findings

1. **Set membership gives away the prevalence of short cells.** A cell (base x mapping set) that holds fewer
   than 100 circuits is mostly infected: the mean infected share is 0.85 for short Comb cells and 0.58 for
   short Seq cells, against 0.39 and 0.37 for full cells. Publishing short cells as sets hands every
   submitter a strong prior. Smallest fix: publish only cells of exactly 100 circuits (section 2.2).
2. **Licences decide the product more than layout does.** All 10 Comb bases that survive are ISCAS-85, and
   ISCAS-85/89 files carry no licence text and no licence was found. 12 Seq bases are ITC-99 (GPL-3.0 on the
   conversion, original terms unread). Under the rule already used for OpenCores ("licence none stated, so
   not redistributed") Comb would be empty. This needs Peter's decision before any build (section 4, Q1).
3. **Per-benchmark sets break two assumptions of the scoring design**: the AUROC bootstrap over bases
   (one base per benchmark) and the 5-per-release quota (126 or more sets). Both have small fixes
   (section 3).
4. **The answer key does not fit a GitHub secret.** The labels alone fit (Comb 11.7 KB, Seq 40.6 KB base64
   of the gzip, limit 48 KB, Seq with 7 KB spare); the Trojan regions for the location bonus are 0.5 to 0.8
   MB. Use an encrypted file in the private ledger repo plus a passphrase secret (section 6).
5. **Scoring is cheap**: 0.05 s for 100 rows, 2.0 s for the whole Seq family (10,967 rows), 37 MB peak.

## 2. Public contents

### 2.1 Counts after dropping MCNC

| | Comb | Seq |
|---|---|---|
| bases in the release | 31 | 38 |
| MCNC bases dropped | 9 | 0 |
| bases left | 22 (11 ISCAS-85, 11 VerilogEval gate netlists) | 38 |
| scored (non-golden) circuits left | 3078 | 10,967 |
| of those in cells of exactly 100 | 3000 | 10,400 |
| bases with at least one cell of 100 | 10 | 37 |
| cells of exactly 100 (public sets) | 30 | 104 |
| public circuits incl. goldens (option A, section 2.2) | 3010 | 10,437 |

Comb: 10 bases have all three cells of 100 (C1355, C1908, C2670, C3540, C432, C499, C5315, C6288, C7552,
C880). C17 has three short cells (12 to 15 circuits). The 11 `ve_*` bases are tiny: 1 circuit per set for
five of them, 1 to 5 for `ve_Prob156`, 5 or 6 for `ve_Prob064`, and four have no set at all (golden only).
Seq: 31 bases have three full cells. Short or missing cells: b01, b02, b06 (K6 short), i2c (K6 absent), s208
(G, K4 short), s27 (all three short), s298 (K6 99). 7 bases have a short cell; s27 has no full cell.

### 2.2 Short cells and the tiny `ve_*` bases

Option A (recommended): a benchmark is published with its full cells only. A short cell, and any base with
no full cell (Comb: C17 and 11 `ve_*`; Seq: s27), contributes no circuits to the public release. Cost:
78 Comb and 567 Seq scored circuits stay private. Gain: no prevalence prior (finding 1) and no
single-circuit set that a one-row submission would reveal outright (a 1-circuit cell scored alone is a
direct label probe, and every `ve_*` cell is all clean).
Option B: publish short cells as "partial" sets and state the prior leak. Not recommended.
The goldens of the dropped bases are not published either (nothing to score against them).

### 2.3 Per-benchmark content

For each benchmark the public package holds:

- `golden/`: the one clean golden circuit (its id comes from the release manifest `goldens`).
- three set folders `gates/`, `lut4/`, `lut6/`, each 100 `.blif.gz` files (a benchmark may have only some).
  Set names map to the key's `G`, `K4`, `K6`.
- `sets.txt`: for each set folder the list of circuit ids (membership only; no label, no order that
  carries information: ids are opaque, and a check of id against label over every full cell showed no
  usable correlation).
- `submission-template.csv`: header lines filled for this benchmark and one row per circuit with the
  `infected,score,count,locations` columns empty.
- `README.md` (per-benchmark page): what the benchmark is, source and licence notice, the golden and sets,
  how to submit, links. It never carries per-base or per-set prevalence, infected counts, Trojan counts,
  rareness or any figure of the current rc `DATASHEET.md` tables (those are answer-key content, as scoring
  design section 10 already says).
- `SHA256SUMS`.

Shared by every tarball: `LICENSES/` (the notices of section 4 that apply) and `SUBMIT.md`.

### 2.4 Release name

Recommend public names `seeker-comb-v2.0` and `seeker-seq-v2.0`. The circuits stay byte-identical to rc5
and rc8, so the existing keys stay valid, and `seeker-release` in a submission equals the public name.
Keeping rc5/rc8 in the public name would advertise "candidate". Tag: `seeker-v2.0` on `lemanrussIII`
(releases are shared by both families); asset names carry the family.

### 2.5 Tarballs, sizes, sums, index

Circuit files are already gzip, so a second compression gains almost nothing; use `.tar.gz`.

| asset | content | approx. size |
|---|---|---|
| `seeker-comb-v2.0-<benchmark>.tar.gz` | one benchmark, 301 files max | 0.5 MB (C17-sized) up to 4.5 MB (C6288) |
| `seeker-comb-v2.0-all.tar.gz` | all 10 Comb benchmarks, 3010 circuits | 18.0 MB |
| `seeker-seq-v2.0-<benchmark>.tar.gz` | one benchmark | 0.05 MB up to 18.4 MB (sha) |
| `seeker-seq-v2.0-all.tar.gz` | all 37 Seq benchmarks (option A, with ITC-99) | 50.6 MB |
| `seeker-seq-v2.0-all.tar.gz` without ITC-99 (Q1 option 3) | 25 benchmarks, 7125 circuits | 36.8 MB |

Sizes are the sums of the gzip member sizes read from the archive listings; the minimum per-benchmark
size has not been tabulated for every benchmark (the plan's packaging step prints the real table). All are
far below the GitHub release asset limit.
Per release: one `SHA256SUMS` over every asset, a `MANIFEST.md`, and the `index` pages
`docs/benchmarks/<family>/<benchmark>.md` in the repo (golden id, set sizes, download link, how to submit)
plus `docs/benchmarks/README.md` (the table of all benchmarks with links). Index pages are generated from
the packaging step so they cannot drift from the tarballs.

### 2.6 The "how to submit" page

`docs/user/SUBMISSION.md` adjusted (the plan edits it): new subset names (section 3.1), the bundle unit,
the new quotas, the CSV header `seeker-release: seeker-comb-v2.0`, a worked example that uses the template
file, and the issue form link of the tester repo. The report section is unchanged except for the
per-benchmark interval note (section 3.3).

## 3. Scorer consequences of per-benchmark sets

### 3.1 Subsets

The old `subsets.json` (stratified draws across bases, `prev-*`, `trojans-*`, `mix100`) is replaced by
public cell lists. Names a submission may use:

- `<benchmark>-gates`, `<benchmark>-lut4`, `<benchmark>-lut6`: one cell, 100 circuits.
- `<benchmark>`: the benchmark's full cells together (100 to 300 circuits).
- `Comb` or `Seq`: every public circuit of the family (family bundle).

`prev-low/mid/high` and `trojans-1/2/3` are dropped: with per-benchmark cells they would name a prior
on the share infected, and the cell structure already gives the same analytic breakdown by set. The report
keeps found-rate by true Trojan count inside every submission.

### 3.2 Does grouping plus real names leak what the threat model assumed hidden?

Scoring design section 6(d) and section 10 assume: the only training material is the golden of each base; no
label is published; nothing but aggregate reports reaches an attacker; base names are hidden, the
mapping lives in `base_names.json`. Checked against the new public data:

| item | verdict |
|---|---|
| Real names | No new leak of labels. A base is recognisable from its port names anyway (scoring design section 10). It makes the golden-as-training link obvious, which is intended. |
| Set membership (which circuits are in a 100-set) | The mapping set of a circuit is visible from the file (gates against LUT). Membership therefore adds no per-circuit label. It adds one thing: the size of a cell (finding 1). Fixed by option A. |
| Per-cell prevalence | Each full cell has an infected share between 10 and 70 percent that is not published. Membership alone does not reveal it. Hidden sample and aggregate-only reports keep that. |
| Short cells | Leak a prior (0.85 and 0.58 infected share). Removed by option A. |
| Id order | Ids of one base lie in a contiguous range of about 300 (already visible in the existing manifest, which carries `base`). The difference of mean id between infected and clean circuits inside every full cell has mean 4 (Comb) and 1 (Seq) with a spread near the range width: no usable signal. The plan keeps a test that rechecks this on the release before packaging. |
| Anonymisation | The existing `lemanruss anonymise` is not run. The old `base_names.json` mapping is not needed. |
| Per-base DATASHEET tables (drawn / infected / clean) | Answer-key content; must stay out of the public tarballs and pages. The packaging step rejects a public file that contains the strings of the current rc tables (test in the plan). |

Weakened guarantees, stated plainly:

(a) Quota (scoring design 6c). A limit of "5 scored submissions per identity and release" cannot cover 30
Comb and 104 Seq cells. Raising it per cell multiplies what one identity can probe: attack 1 (single probe)
gives one certain label per query, so the count of certain labels per identity rises from 5 to the new cap.
Smallest fix: the unit of submission is a benchmark or a family bundle, not a cell, and the ledger keeps
three counters per identity and release: total scored submissions at most **10**, at most **3 per
benchmark**, at most **1 per 24 hours** (any unit), plus at most **3 family bundles**. Worst case an identity
gets 13 queries against the previous 5. Honest result: the single-probe bound goes from 5 to 13 certain
labels per identity (still 13 of about 10,000), and the host-identity argument of scoring design 6(ii)
applies more strongly, so the maintainer keeps the rule "one first submission per account needs the maintainer's
approval label" as an option (Q3).
(b) Bundles and report detail. A family bundle report is limited to family-level aggregates (the report
shape of scoring design section 4 plus the by-set table): no per-benchmark table, because 37 more
AUROC numbers per query would multiply the channel by 37. Per-benchmark ratings come from per-benchmark
submissions, which are metered by the cap in (a). The information bound of scoring design section 6 is
per report and does not change; it already says the bound alone is loose and the ledger is the real limit.
(c) Hidden sample. Drawn per set inside the submission (70 of 100, fresh seed each time), so a benchmark
bundle samples 210 of 300. Same property as before, now stratified by cell.
(d) Separate cells have independent keys, so learning labels in one cell tells nothing about another; a
recovered cell burns only that cell. The maintainer can re-draw by moving to a new release name.

### 3.3 AUROC interval and baselines

One base per benchmark: the bootstrap over bases of scoring design section 4 is undefined. For a
benchmark or cell submission resample circuits (1000 resamples) and print "interval over circuits,
optimistic: circuits of one base share a golden". The family bundle keeps the bootstrap over bases, now
10 (Comb) or 25 to 37 (Seq) bases, the headline number. `baselines.json` holds per-release, per-set
AUROCs (size-only, sanity detector) for the old full release; per-benchmark baselines must be computed
(size-only is the gate count of the circuit file, no Odin III needed) and the family baseline recomputed
over the public subset. Plan steps cover both.

### 3.4 Quota rules mapped

Ledger line: time, submitter, release, unit (cell, benchmark or family), n, sample, seed. Checks, in
order: 1 per 24 h across all units, 10 total, 3 per benchmark, 3 family bundles. An invalid submission
counts for nothing, as before. A refused submission states when the next is allowed.

## 4. Licences per base family

Read from the sources in the workspace; nothing is a legal opinion.

| family | bases | licence read | verdict |
|---|---|---|---|
| ISCAS-85 | 11 Comb (10 with full cells) | The VTR `blif/2` files that feed the builds carry no header or licence text (C17, s27 checked). VTR `LICENSE.md` says benchmark circuits "each have their own individual terms ... in the source code of each benchmark"; there are none in these files. A web search found no formal licence for the ISCAS-85 or ISCAS-89 netlists; the original distribution was by tape from MCNC, and mirrors host them as test material. Mimir `licences.toml` has no ISCAS rule. | none stated; terms unread |
| ISCAS-89 | 23 Seq | same | none stated; terms unread |
| ITC-99 | 12 Seq (b01 to b13 without b05) | Source: the `ccsl-uaegean/ITC99-RTL-Verilog` conversion of the Politecnico di Torino VHDL. Its `LICENSE` is GPL-3.0 (674 lines read). The licence of the original VHDL has not been read. | copyleft on the conversion; original unread |
| VerilogEval | 11 Comb `ve_*` | MIT, Copyright (c) 2023-2024 NVIDIA Research Projects (and OpenAI human-eval MIT notice in the same file). Redistributable with the notice. | MIT, but no full cell (section 2.2), so not shipped |
| OpenCores `ca_prng` | 1 Seq | BSD-3-Clause style (InformAsic AB), COPYING.txt and file header (from the rc8 datasheet). | redistributable with the notice kept |
| OpenCores `i2c` | 1 Seq | permissive notice (Herveille, 2001): "may be used and distributed without restriction provided that this copyright statement is not removed ... and that any derivative work contains the original copyright notice" (rc8 datasheet). | redistributable with the notice kept |
| VTR `sha` | 1 Seq | OpenCores permissive notice (marsgod), same wording; Mimir rule `vtr-sha`, `sha.v:14-21`. | redistributable with the notice kept |

Every circuit is a derivative of its base (insertion, ABC restructuring, mapping); each base's licence
applies to its derivatives, and the per-benchmark package carries the notice.

Outcome by decision (Q1): Seq with everything is 37 benchmarks and 104 sets; without ITC-99 it is 25
benchmarks, 71 sets, 7125 circuits. Comb with ISCAS-85 is 10 benchmarks and 30 sets; without it nothing
public is left. The rc8 datasheet already left out OpenCores projects that were copyleft or unclear; the
same rule applied literally to "none stated" would remove ISCAS and, with it, Comb. That is why Q1 is Peter's
call and why the build plan does not start before it is answered.

## 5. Tester repo

Name proposal: `drpaj12/seeker-scoring` (public). Contents:

- `lemanruss/score/` pinned as a vendored copy of the scorer (standard library only) at a recorded
  `lemanrussIII` commit; `PIN.md` states the commit and a hash of the tree. No Odin III needed.
- `.github/ISSUE_TEMPLATE/score-submission.yml` and `.github/workflows/score.yml`, from the examples in
  `docs/user/`, extended with the bundle units and family names.
- `public/cells.json`: the public cell lists (ids only, section 3.1).
- `docs/`: the how-to-submit page, mirrored from section 2.6, and `SECURITY.md`.
- Nothing else: no key, no ledger, no labels, no seeds, no regions.

Safety rules (scoring design section 7, kept): trigger `issues: opened` only; the workflow runs code from
the default branch only; never `pull_request_target`; never check out anything from an issue or PR; the issue
body is data, passed through an environment variable to a Python extractor, never interpolated in a shell
line; minimal `permissions` (`issues: write`, `contents: read`); the key is decrypted into the runner temp
directory, never printed, never uploaded as an artifact; concurrency group so the ledger has one writer;
`set -x` never used; the scorer's error text never depends on a label. Additions: the scorer step runs
before any network call that uses the ledger token is exposed to the issue text (the issue text is parsed
only inside the Python step); a fork or a non-collaborator cannot read secrets by any trigger the workflow
uses (the `issues` event runs in the base repo context); issue edits do not re-trigger (`opened` only); the
report is posted as a comment and the issue is closed and locked.

Ledger: private repo `drpaj12/seeker-ledger` (name proposal) holding `ledger.jsonl` and the encrypted key
files. A fine-grained token limited to that one repository (contents read and write) is stored as a secret
of the tester repo. The workflow pushes the ledger line after scoring and treats a failed push as a failed
run (the plan changes the example, whose `|| true` would let a submission through unrecorded).

Actions cost per submission. A local `lemanruss score` run on fake submissions (random scores) against the
real rc5 and rc8 key files (labels, sets and Trojan counts only), measured on this machine:

| submission | rows | wall time | peak memory |
|---|---|---|---|
| one cell (Comb, 100 circuits) | 100 | 0.06 s | 26 MB |
| one benchmark (Comb, 300) | 300 | 0.05 s | 25 MB |
| Comb family, 5778 rows (includes the MCNC bases; test only) | 5778 | 1.2 s | 29 MB |
| one cell (Seq, 100) | 100 | 0.05 s | 31 MB |
| one benchmark (Seq `sha`, 300) | 300 | 0.06 s | 31 MB |
| Seq family bundle | 10,967 | 2.0 s | 37 MB |

Not included: regions (the location bonus; the runs had none). The workflow's fixed steps (checkout,
setup-python, editable install, ledger clone, decrypt, comment, close) are not measured here; I estimate
30 to 60 s per run, billed as one minute per job. GitHub documentation states that standard hosted
runners are free in public repositories; I did not re-verify that today, so the plan's first step checks
the billing page. If the repo were private: 2000 free minutes a month would cover about 2000 submissions,
and the quota caps one identity at 13.

## 6. Answer key handling

What the scorer needs per release: labels (infected or not), set and base per circuit, number of
Trojans per infected circuit, and, for the location bonus only, the Trojan regions. All of it restricted to
the public circuits (Comb 3078, Seq 10,967 scored ids).

Sizes, measured:

| item | Comb | Seq |
|---|---|---|
| minimal table (id, base, set, Trojan count), gzip | 8.8 KB | 30.5 KB |
| same, base64 | 11.7 KB | 40.6 KB |
| regions of the previous builds (rc4 / rc5 files; to be rebuilt for rc5 / rc8), gzip | 0.40 MB | 0.58 MB |
| regions, base64 | 0.54 MB | 0.78 MB |
| full answer-key archive as released (xz; includes `pre/` and witnesses) | 8.1 MB | 11.1 MB |

GitHub secret limit 48 KB. The minimal table alone fits (Seq with 7 KB spare); it does not carry regions,
and a secret holding the Seq table leaves no room to grow. Recommendation: one encrypted archive per
family in the private ledger repo (symmetric `gpg`, AES256), and one repository secret holding the
passphrase. The workflow clones the private repo anyway for the ledger. The archive holds `labels`-derived
`key.json` (trimmed to public ids by a new `lemanruss key-pack` command, plan step), `trojans`-count
data, and `regions.json` when it exists. It never holds `pre/`, witnesses, scripts, rareness or
provenance. Fallback if the passphrase route is refused: labels-only secret (no location bonus).

Loss of the passphrase or the key archive means rebuilding the key from the F: archive; the archive copy of
the full answer key already exists and is the source of truth.

## 7. What only Peter can do

1. Decide Q1 (licences) and the open questions below.
2. Create the public tester repo `drpaj12/seeker-scoring` and the private ledger repo `drpaj12/seeker-ledger`.
3. Create the fine-grained token for the ledger repo and store it, with the repo name, as secrets of the tester repo.
4. Generate the passphrase (outside any chat), store it as a secret, and run the encryption on the packed key; put
   the encrypted archives in the ledger repo.
5. Enable Actions on the tester repo (the workflow is added disabled until he says so) and protect `main`.
6. Publish the GitHub release on `drpaj12/lemanrussIII` after reviewing the staged assets (the plan produces
   them locally on the archive drive only).
7. Open one test issue with a fake submission and check the report, the ledger line and the closed issue.
8. Check the GitHub Actions billing page (public repos are expected to be free).

## 8. Open questions for Peter

1. **Licences.** ISCAS-85/89 carry no stated licence and no formal terms were found; ITC-99 is a
   GPL-3.0 conversion with unread original terms. Options: (1) publish all with notices; (2) publish ISCAS and
   leave out ITC-99; (3) apply the OpenCores rule literally (leave out everything "none stated"): Comb is
   empty. Recommendation: option 2 now, with attribution to the original ISCAS authors, a takedown contact on
   the release page, and a note that terms are unread; ITC-99 could return later as a separate GPL-3.0
   tarball. Seq then has 25 benchmarks and 71 sets.
2. **Short cells.** Publish only exact-100 cells (option A, no prior leak, 78 Comb and 567 Seq circuits
   stay private) or also partial cells. Recommendation: A.
3. **Quotas.** 1 per 24 h, 10 total, 3 per benchmark, 3 family bundles, per GitHub account and release, with
   maintainer approval for an account's first submission. Recommendation: as written, approval label optional.
4. **Family bundle report.** Family-level aggregates only. Recommendation: yes.
5. **Key storage.** Encrypted file in the private ledger repo plus passphrase secret.
   Recommendation: yes.
6. **Release names** `seeker-comb-v2.0`, `seeker-seq-v2.0`, tag `seeker-v2.0`; circuits byte-identical to
   rc5 and rc8. Recommendation: yes. Related: were the rc5 or rc8 circuits or key shared with anyone outside
   (the notes say results by email only)? If any key left the building, that release's key is burned and the
   public release needs fresh keys.
7. **Location bonus in the first tester release.** It needs the Trojan regions rebuilt for rc5 and rc8
   (long compute, Odin III). Recommendation: ship detection and count first; add location after.
8. **Tester repo name** `seeker-scoring` and ledger repo name `seeker-ledger`. Recommendation: yes.
9. **Proc and Si** keep their own layout later; nothing in this spec constrains them.
