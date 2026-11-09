# Seeker v2.0 public download and tester: implementation plan (2026-11-09)

Spec: `docs/specs/2026-11-09-public-download-tester.md`. Nothing starts before Peter answers the spec's
open questions 1 to 6 (licences and short cells change the counts). Each step is one lane: one branch, one
PR, tests listed. Steps P1 to P5 are code in `lemanrussIII` (no Odin III build needed except P9). P6 to
P8 produce files locally only. Nothing is published, uploaded or enabled by any step: publication is
Peter's (spec section 7).

Rules for every step: unittest under `tests/`, ruff and `mypy --strict` clean, line length 100; no circuit,
label, seed or key committed; tests use toy keys built in the test; commit and push after each green
sub-step (`git push origin HEAD:<branch>`); draft PR while working, ready at the end.

## P0 Pre-checks (controller, no code)

- Peter's decisions Q1 to Q6 recorded in the ledger.
- Check the GitHub billing page for public-repo Actions minutes (Peter).
- Test: none.

## P1 Public selection (`lemanruss pubselect`)

Reads a release key and the licence decision (a small `public-bases.toml` in the repo: per base, family
licence tag, `include = true/false`, reason) and writes a private selection file (outside the repo): per
benchmark the golden id and the ids of every cell of exactly 100.
- Drops MCNC and every base marked out; drops cells with fewer than 100 circuits (option A).
- Test: toy key with a full cell, a short cell, a base without a full cell, an excluded base: output holds only
  the full cells; a golden of a dropped base is absent; counts printed (cells, circuits, benchmarks).
- Test: check the id-against-label statistic of spec 3.2 on the toy key (function returns the difference of
  means and the id range).

## P2 Packaging (`lemanruss pubpack`)

From a release directory and the P1 selection, writes the staging tree outside the repo: per benchmark
`golden/`, `gates/`, `lut4/`, `lut6/`, `sets.txt`, `submission-template.csv`, `README.md`, `LICENSES/`,
`SHA256SUMS`; the per-benchmark and per-family `.tar.gz` files (deterministic: sorted names, zero mtime and
owner); a release `SHA256SUMS` and `MANIFEST.md`; the index pages `docs/benchmarks/<family>/<benchmark>.md`
and `docs/benchmarks/README.md`, with the real size table.
- Test: toy release, two benchmarks; the tarballs unpack to the layout; two runs give identical bytes; the
  template CSV parses with the scorer's parser for the matching subset name.
- Test (leak): a public file may not contain a label file name, `answer_key`, a seed, a per-base prevalence table or any of the rc
  DATASHEET table headings; the packer fails if one appears. A manifest in the package lists id, base and
  sha256 only.
- Test: every cell folder holds exactly the ids of `sets.txt`; no file outside the selection is packed.

## P3 Scorer: units, quotas, intervals

Changes in `lemanruss/score/` (standard library only):
- `subsets`: load the public cell lists; names `<benchmark>-gates|lut4|lut6`, `<benchmark>`, `Comb`/`Seq`;
  the hidden sample is drawn per set.
- `ledger`: counters of spec 3.4 (24 h, 10 total, 3 per benchmark, 3 family bundles); `unit` field in the
  line; a failed write raises.
- `scorer`: interval over circuits for cell and benchmark units, over bases for the family unit; family
  bundle report with no per-benchmark table; per-benchmark baseline lookup.
- Tests: every counter hits its limit and states the retry time; an invalid submission uses no quota; hidden
  sample size per set and determinism for a fixed seed; a family report contains no benchmark name beyond the
  header; a one-base interval uses the circuit bootstrap and prints the optimism note; existing tests
  updated, none deleted.

## P4 Baselines per benchmark

`lemanruss baselines-pub`: size-only AUROC (gate count of the circuit file) per benchmark and per family on
the public set, and the sanity detector where its inputs are public; writes `data/baselines.json` entries.
- Test: toy release with known sizes gives the hand-computed AUROC; undefined cases print `n/a`.

## P5 Key packing

`lemanruss key-pack KEY SELECTION --out DIR` writes the trimmed key (table of spec 6, regions if present, public ids
only) and prints sizes; `lemanruss key-unpack` for the runner.
- Test: the packed key scores a toy submission to the same report as the full toy key; the packed key holds no
  id outside the selection and none of `scripts`, `rareness`, `provenance`, witnesses.
- Test: size report matches the files.

## P6 Stage the public assets (local, on the archive drive only)

Run P1, P2, P4 on the rc5 and rc8 releases (unpacked from the archive copies) into a staging directory under
`work/`, then copy the finished assets to the dated archive folder on F: with `SHA256SUMS` verified (no
live data). Nothing leaves the machine. Controller reviews the staged index pages and the tarball list.
- Test: `sha256sum -c`; each tarball listed with its size; the leak scan of P2 passes on the staged tree; a
  fresh unpack of one family bundle and one benchmark scores a fake submission without error.
- The step ends with the counts table of the spec filled in with real numbers (Comb 10 benchmarks, 30 sets,
  and so on, or the numbers after Peter's licence decision).

## P7 Tester repo content (draft, local)

In a local scratch directory (not a GitHub repo): the vendored scorer at a recorded commit with `PIN.md`,
`cells.json`, the issue form, the workflow (with `|| true` removed from the ledger push; ledger failure fails
the run), `SECURITY.md`, and the docs page. The workflow carries `if: false` at the job level until Peter
removes it.
- Tests: a YAML lint of the workflow; a script check that no `${{ }}` expression appears inside any `run:`
  block except values passed through `env:`; that `pull_request_target` and `actions/checkout` of a PR ref do not
  appear; that `permissions` is minimal.
- Dry run with `act`-free simulation: a script that replays the workflow steps by hand on a fake issue body, a
  toy encrypted key and a toy ledger directory: the report appears, the ledger gets one line, a second call
  inside 24 h is refused with the retry message.

## P8 `SUBMISSION.md` and README updates

Edit `docs/user/SUBMISSION.md`, `docs/user/README.md`, `docs/user/SCORING-MANUAL.md`, `README.md` for the new
subset names, quotas, release names, links to the downloads and to the tester repo (links filled in after
Peter creates them). The old `scoring-*.example` files stay as references and point to P7.
- Test: the example CSV in `SUBMISSION.md` parses with the scorer for its stated release and subset; link check
  of relative links.

## P9 Trojan regions for rc5 and rc8 (optional, long compute)

`lemanruss regions` on the two releases (needs Odin III, per the existing command), then `key-pack` including
regions. One Odin III build, one lane (workspace rule), run roots outside the worktree.
- Test: the existing region tests; on the built regions the hit-rate against chance level is printed for a random-net
  submission and is near the chance level.
- Skipped if Peter chooses detection and count only (spec Q7).

## P10 Handover to Peter (controller)

Controller prepares the checklist of spec section 7 with the final names and the exact commands (encrypt the
key with `gpg`, upload secret names, create repos, enable workflow, publish release). Peter performs them,
then opens one test issue; the lane that built P7 verifies the report, the ledger line and the closed issue.

## Order and dependencies

P0 -> P1 -> P2; P3 and P5 can run beside P1/P2 (different files); P4 after P2; P6 after P1, P2, P4;
P7 after P3, P5, P6 (needs the final cell lists); P8 after P3; P9 independent; P10 last.
Estimated lanes: 8 small (P1 to P8), 1 long (P9), 1 controller step.
