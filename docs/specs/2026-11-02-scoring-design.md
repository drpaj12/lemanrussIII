# Seeker v2.0 formal submission and scoring: design (2026-11-02)

Purpose (hub docs/purpose.md, Leman Russ III R1): let outside groups get a trustworthy rating of
their Trojan detector on Seeker v2.0 without the answer key being public. Measure: confusion
matrix, TPR, FPR, precision, F1, accuracy and AUROC (with a bootstrap interval over bases), plus a
comparison with the size-only control, so a submitter sees whether the detector beats circuit size.

Peter, 2026-11-02, verbatim: "Is there a way of making a web version to check if a seeker's dilemma
subset, so 100 for different things, when it's submitted, gives you the false positive or the
confusion matrix? I know you can figure things out, but I think it's something we need to submit.
Someone could hack it by repeatedly submitting things, but I would like a way for others to check
if their detector has a reasonable rating. So generate a report based on a way of submitting it,
such that the way is formalized either in the Git or website."

Scope: everything that does not depend on the hosting choice. Peter decides hosting (a public
GitHub repo with an Actions scorer, or his web host). This lane creates no public repo, no secret
and no upload, and enables no workflow.

Peter's decisions, 2026-11-02, verbatim: "The training should be done using the golden circuit, not
necessarily what is hidden. So I don't even know if they should know the type of functions. Also,
make sure the benchmarks with multiple Trojans has to be found, as in you can answer if there's
one or more Trojans. The accuracy is a bonus, and also if you can tell us where it roughly is in
the circuit, that is also a bigger bonus." Folded in:

1. Hosting will be a public GitHub repo with the Actions scorer (the controller creates it
   later); the packaging stays hosting-agnostic.
2. No label of any circuit is ever published. The setting is reference-based: each base's golden
   is the only training material a detector gets. There is no public dev pool with labels; every
   subset is scored only through the service.
3. Base function names are anonymised in the public evaluation release (`b001`...), mapping in the
   answer key (`base_names.json`). Default ON. **Peter undecided**: switch off with
   `lemanruss anonymise` not run (the release then keeps the source names).
4. Rows are `id,infected,score,count,locations` (section 2).
5. The report has tiers (section 4): PRIMARY detection; multi-Trojan circuits must be found
   (found-rate by true Trojan count); BONUS count accuracy; BIGGER BONUS localisation, against
   Trojan regions defined in section 9.

## 1. Pieces

| piece | file | public |
|---|---|---|
| submission format | `docs/user/SUBMISSION.md`, `docs/user/submission.schema.json` | yes |
| subset lists (ids only) | `subsets.json` per release, from `lemanruss subsets` | yes |
| Trojan regions | `regions.json` in the key, from `lemanruss regions` | **no** |
| anonymised base names | `base_names.json` in the key, from `lemanruss anonymise` | **no** |
| scorer | `lemanruss score` (`lemanruss/score/`, standard library only) | yes |
| answer key | `answer_key/` of the release (labels, sets) | **no** |
| ledger | `ledger.jsonl` beside the key | **no** |
| baselines | `lemanruss/data/baselines.json` (aggregate AUROC only) | yes |
| GitHub packaging | `docs/user/scoring-workflow.yml.example`, `docs/user/scoring-issue-form.yml.example` | example only |
| manual packaging | `docs/user/SCORING-MANUAL.md` | yes |

## 2. Submission

One CSV per submission. Header lines `# key: value` (first, any order, each key once):
`seeker-release` (release name, must equal the scorer's release), `subset` (a name from
`subsets.json`), `detector`, `team`, `contact` (optional). Then the line
`id,infected,score,count,locations` and one row per circuit:

- `infected`: 0 or 1, the decision at the submitter's own threshold. PRIMARY. A circuit holding
  one or more Trojans is infected.
- `score`: finite float, higher means more likely infected; for AUROC.
- `count`: BONUS. Number of Trojans claimed, 0 to 3; 0 exactly when `infected` is 0 (a mismatch
  is a hard error). May be left empty (not answered).
- `locations`: BIGGER BONUS. Optional, `;`-separated **released net names**, at most **m = 10**
  per circuit (more is a hard error). Names are the net names of the released circuit.

Every id of the subset appears exactly once. Goldens are not in any subset and are not scored.
Each detector sees one circuit at a time, may train on the base golden (published in the
manifest) and nothing else of the labels.

Hard errors (the whole submission is refused, nothing is scored, nothing is written to the
ledger): missing, repeated or unknown header, wrong release, unknown subset, wrong column header,
a row with the wrong number of fields, infected not 0 or 1, count outside 0..3 or disagreeing
with `infected`, score not a float or NaN or infinite, more than 10 locations, a malformed net
name, an id not in the subset, a repeated id, a missing id, no rows, file larger than 5 MiB, a
non-ASCII byte in the headers. Each message names the line and the offending value (ids are
public, so an error message is not a leak). The error text never depends on a label.

## 3. Subsets

Per release the maintainer runs `lemanruss subsets --key KEY --release NAME --seed S --out
subsets.json`. Subsets are drawn from the whole release (no label is public, 6d). Drawing is seeded
(`random.Random(f"{S}/{subset}")`), stratified by source: the allocation is equal over the bases
that have a circuit in the pool, handed out round-robin in a seeded base order, capped by what
each base has, so a large base cannot dominate; inside a base circuits are drawn uniformly.

Named subsets (family prefix Comb or Seq from the release family):

- `<Fam>-K4`, `<Fam>-K6`, `<Fam>-G`: 100 circuits of one mapping set.
- `<Fam>-prev-low`, `-prev-mid`, `-prev-high`: 100 circuits from base/set cells whose infected
  share (drawn per cell, 10 to 70 %) is at most 30, 31 to 50, above 50 percent.
- `<Fam>-trojans-1`, `-2`, `-3`: 50 infected circuits with exactly that many Trojans plus 50 clean
  circuits (prevalence fixed at 50 %, stratified by base inside each class).
- `<Fam>-mix100`: 100 circuits over all sets.
- `all`: every non-golden circuit (not 100).

A subset that cannot reach 100 (a pool too small) holds fewer and records `n`. The lists are ids
only. Known leaks of the public lists, accepted: a prevalence or Trojan-count name gives a prior
on the share infected (it is a design choice of the subset, not a per-circuit label).

## 4. Scorer

`lemanruss score SUBMISSION.csv --key ANSWER_KEY_DIR [--subsets FILE] [--ledger FILE]
[--submitter ID] [--hidden-sample N] [--seed S] [--out-dir DIR]` writes `report.md` and
`report.json` and prints the Markdown.

1. Validate (section 2). 2. Rate limit (section 6c). 3. Draw the hidden sample (6b). 4. Report on
the sample, in tiers:

**Primary: detection.** TP, FP, TN, FN; TPR, FPR, precision, F1, accuracy; AUROC (Mann-Whitney,
ties one half) with a 95 % percentile bootstrap interval that resamples **bases** (1000
resamples), because circuits of one base are not independent. Multi-Trojan circuits must be found:
the found-rate of infected circuits by true Trojan count (1, 2, 3). Per mapping set (K4, K6, G)
breakdown. Baselines: the AUROC of the size-only control and of the sanity detector on the full
release (aggregates from `baselines.json`, same set) with a verdict: `above` if the interval's
lower bound exceeds the baseline, `below` if the upper bound is under it, else `not
distinguishable`. Undefined values print `n/a`.

**Bonus: count.** Over the sampled infected circuits that carry a count: exact-count accuracy, mean
absolute error and the confusion matrix claimed (0..3) against true (1..3). Cells are rounded to
multiples of 5 (limits what the matrix says about single circuits).

**Bigger bonus: location.** Over the sampled infected circuits that carry locations: one trial per
true Trojan; a trial is a **hit** if any submitted net lies in that Trojan's region (section 9).
Reported: trials, hit rate, and the **chance level**: the hit rate expected if the same number of
nets per circuit were drawn at random from the circuit's nets, computed from region sizes. A hit
rate near the chance level means no localisation skill (regions are an over-approximation, 9).

Suppression: any breakdown cell (set, Trojan count, count tier, location tier) with fewer than 10
sampled circuits or trials is shown as `suppressed`. All numbers print to two decimals; counts as
integers.

The report holds aggregates only: no id, no net name, no per-circuit correctness, no seed, no
sampled ids.

## 5. Threat model

Attacker: submits many files to learn labels of the key (to overfit, or to publish the key).
Capabilities: unlimited choice of `score` and `label` vectors, adaptive, any number of valid
identities up to what the host allows; reads every report; knows the public subset lists and the
scorer code; does not know the key or the scorer's random seed. Goal: recover k labels of a
subset. Out of scope: a compromised scorer host, a stolen secret, a malicious maintainer.
In scope for the workflow: a submission that tries to run code (the CSV is data only).

## 6. Anti-gaming

(a) Aggregate-only reports (section 4).
(b) Hidden sample. The scorer draws a seed (`secrets`, or `--seed` for tests and audit), samples
`N` of the `n` subset circuits uniformly without replacement (default `N = round(0.7 n)`), and
scores only those. `N` is printed, the sample is not, and the seed is kept only in the ledger.
Every submission gets a fresh sample, so two submissions that differ in one label are scored on
different circuits.
(c) Rate limit. Per submitter (the authenticated identity the host provides, passed as
`--submitter`; the self-declared `team` is used only when none is passed, in manual mode) per
release: default **1 scored submission per 24 hours and 5 in total**, all subsets of the release
together. A refused submission says when the next one is allowed and is not scored. The ledger is a
JSON-lines file the scorer reads and appends (time, submitter, release, subset, n, N, seed).
Invalid submissions (section 2) are not counted.
(d) No public labels. No label of any circuit is published (Peter, decision 2), so there is no dev
pool to leak and no train/test overlap to police: the only training material is each base's
golden. The hidden sample (b) and the ledger (c) are the only barriers; every subset is drawn from
the whole release.

### Queries an adaptive attacker needs

Let `n` = subset size (100), `N` = sample size (70), `q = N/n = 0.7`, `T` = ledger cap (5), `h` the
entropy of a label (at most 1 bit; the prevalence of the sets is 10 to 70 %, so about 0.9).

Practical attacks.
1. Single probe. Label exactly circuit `i` as 1, all others 0. The report holds TP in {0, 1}.
   TP = 1 proves `i` infected; TP = 0 means clean, or infected but not sampled (probability
   1 - q). Cost: one query per circuit tested. Under `T = 5` one identity tests at most
   **5 circuits** and needs **5 days** (one per 24 h).
2. Flip test. Two submissions that differ in the label of `i`. TP shifts by `q` in expectation but
   each count has hypergeometric noise: with `m = 50` positives and `N = 70`, sigma = 2.3, so the
   difference of two counts has sigma = 3.3. A decision at 1.64 sigma needs
   `M = (1.64 * 3.3 / 0.7)^2 = 60` submissions **per label**, i.e. 12 identities per label under T = 5.
3. Location probe. A net listed on circuit `i` hits only if `i` is infected and the net is in a
   Trojan region, so one hit proves `i` infected; one query tests up to `100 * 10` net claims,
   but the report returns only the aggregate hit count (a noisy count, same channel as 4).
4. Group testing. Positives `A` (|A| = g) in one submission, the report gives a noisy count of
   infected in `A`. Noise caps what a query reveals (below).

Information bound. A report depends on the key through sampled counts and AUROC. Counts: TP, FP,
the found-rate by Trojan count (two more independent counts, the third follows from TP), the
location hits (one) = 5 counts; the count matrix has 12 cells, rounded to multiples of 5. Each
count is a hypergeometric draw `Y = |S ∩ A|`, `K = |A ∩ infected|`; the most one count can say
about `K` is the capacity `C` of that channel (Blahut-Arimoto, `lemanruss.score.bounds`,
`n = 100`, group size up to 100):

| N | 100 (no sampling) | 80 | 70 | 50 |
|---|---|---|---|---|
| C, bits per count | 6.66 | 3.97 | 3.61 | 3.06 |

A rounded matrix cell carries at most `C - log2 5 = 1.29` bits (N = 70). AUROC at two decimals adds
at most log2 101 = 6.7 bits; the interval is a seeded function of the same sample and is not
counted as independent (assumption). With N = 70: `b = 5 * 3.61 + 12 * 1.29 + 6.7 = 40.3` bits per
query at most, so recovering `k` labels needs `Q >= k * h / b` queries: **k = 100 labels need at
least 3 queries** (`bounds.min_queries`). The bound is loose and does **not** protect by itself:
five queries could in principle carry 200 bits, more than the key of one subset. It ignores that
the attacker does not know which circuits a count concerns. The tiers added in this round raise
`b` from 13.9 to 40.3 bits, and the practical rate stays attack 1: one label per query. So the
ledger and the host's identity rule are the real limits, not information theory; the numbers
below say how real.

Consequences. (i) The ledger, not the sample, is the main limit: the sample multiplies the cost of
attack 2 by about 60 and cuts the per-count capacity from 6.66 to 3.61 bits. The 5-query cap leaves
an identity at most the 5 certain labels of attack 1 plus the noisy group-test information of the
bound; to keep the key useful the maintainer should redraw the subsets for every release candidate. (ii) A host that lets one person open many identities multiplies `T` by the number of
identities: testing all 100 circuits by attack 1 takes 100 queries, i.e. 20 identities at T = 5,
and 5 days at one per 24 h each. The host should therefore bind identity to something costly
(account age, one request per team, maintainer approval for the first submission).
(iii) Even a recovered subset only burns that subset; `all` and the other subsets overlap it
only through shared circuits (the subsets are drawn independently), and the maintainer can redraw
subsets with a new seed or move to the next release (rc to final) at no cost to the scorer.
(iv) What the scorer cannot stop: overfitting by honest repeated use is bounded by T; a team that
publishes a detector tuned on 5 reports gains at most the 69 bits above.

## 7. Packaging

GitHub: an issue form collects release, subset, detector, team, contact and the CSV as an attached
file or a fenced block. A workflow triggered by `issues: opened` runs only code from the default
branch (`actions/checkout` with the default ref, never the issue's or any PR's code), treats the
issue body as data (passed through an environment variable, parsed by Python, never interpolated
into a shell line), reads the key from an encrypted secret (a tarball, base64) into a runner temp
directory, runs `lemanruss score` with `--submitter ${{ github.event.issue.user.login }}`, posts
`report.md` as a comment, and closes the issue. The ledger lives in a private repo or an artifact
the maintainer controls; the example shows a cache-less `git` write to a private ledger branch.
No `pull_request_target`, no checkout of submitter code, minimal `permissions`. Examples only; not
enabled. Manual: the maintainer runs the same command on emailed CSVs
(`docs/user/SCORING-MANUAL.md`), with `--submitter` set to the sender address.

## 9. Trojan regions (answer key only)

After obfuscation the Trojan cells are remapped (ABC restructuring, LUT or gate mapping) and every
internal net is renamed, so there is no name or cell correspondence with the insertion step. The
region of Trojan `j` of circuit `R` is defined by function (`lemanruss/score/regions.py`):

    region_j = { net x of R, not a primary input : x is in the transitive fan-in of Trojan j's
                 victim output (through gates and latches), and no net of the clean golden, and
                 no complement of one, has the same signature }

The signature of a net is its value over 64 random input lanes plus one lane that replays the
stored witness of Trojan `j` (answer_key/witnesses: the input sequence on which that Trojan's
trigger is high and its payload shows), over `max(16, witness length)` cycles, golden and `R`
driven by identical inputs by port name. The witness lane is what makes the payload cell and the
logic downstream of a firing trigger differ from the golden although the trigger is too rare to
fire on random lanes. Stored as `answer_key/regions.json`:
`{id: {"n_nets": N, "trojans": [{"victim", "victim_found", "nets": [...], "cone": size}]}}`,
built by `lemanruss regions RELEASE --key KEY`; never part of the public release.

Limits, stated: the region over-approximates (logic that ABC restructured also lacks a golden
twin, so a region can include benign cells; measured sizes: Comb rc4 3630 Trojans in 2218 infected circuits, median region 4.1 % of the circuit's nets, mean 9.4 %, 19 empty; Seq rc5 6439 Trojans in 3966 circuits, median 14 %, mean 16 %, none empty; every victim output was found), and a
trigger that equals some golden net on all lanes is missed. A hit therefore means "inside the
region", and the chance level (4) is printed next to the hit rate so an over-wide region cannot
flatter a detector unnoticed.

## 10. Anonymised base names

`lemanruss anonymise RELEASE --key KEY --out PUBLIC_DIR [--seed S]` writes the public evaluation
release: `circuits/`, a manifest whose `base` fields are `b001`... (shuffled, seeded), goldens by
id, and a minimal datasheet with **no** per-base or per-set prevalence or Trojan data (the
current rc DATASHEET.md lists them; it is answer-key content and must not be published). The
mapping goes to `KEY/base_names.json`; the scorer reads it, so stratification and the bootstrap
use the anonymised names. Port names are the circuit interface and stay: a reader may still
recognise a well-known benchmark (for example an ISCAS name) from them. Peter undecided whether
to also rename ports (that would break the golden-as-training-material link only for named
bases, not for function).

## 11. Tests

`tests/test_score.py` (no Odin III needed): every validation error; metrics against hand
computed confusion matrices and AUROC; subset size, determinism, stratification, no labels in the subset file;
hidden sample size and determinism for a fixed seed, and difference across seeds; ledger window and
total cap; a report scanned for ids, net names and the seed; count matrix rounding; the schema
agrees with the parser; the region definition on a hand-built Trojan; the bound table; an end to end run on Comb rc4 and Seq rc5 with a size-only score (gate count of the circuit
file) when the release and key are present under `work/htl-rel`, else a toy release.
