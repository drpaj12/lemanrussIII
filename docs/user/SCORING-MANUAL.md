# Scoring by hand (maintainer, no hosting needed)

For emailed CSVs. The same scorer as the automated workflow; nothing is enabled.

Once per release (private key directory `KEY/`: labels.json, sets.json, trojans.json):

    lemanruss regions RELEASE_DIR --key KEY --out KEY/regions.json   # location tier (slow)
    lemanruss subsets --key KEY --release NAME --seed 0 --out subsets.json
    cp subsets.json KEY/subsets.json
    lemanruss anonymise RELEASE_DIR --key KEY --out PUBLIC_DIR       # public release (default on)

`subsets.json` and `PUBLIC_DIR` are public; `KEY/` and its `ledger.jsonl` are not. Run `regions`
before `anonymise` (anonymise only adds `base_names.json`). Check `PUBLIC_DIR` holds no
`answer_key/`.

For each emailed file, save it outside the repo and run:

    lemanruss score SUBMISSION.csv --key KEY --submitter "sender@example.org" --out-dir OUT/

- `--submitter` must be the sender address (the rate limit key); without it the self-declared
  `team` is used, which a sender can change.
- Exit 2 and `REFUSED: ...` means the file was invalid or over quota; send the message back.
  Nothing is written to the ledger then.
- Send back `OUT/report.md` only. Never send `report.json` fields beyond it, the ledger or the
  seed. For an audit re-run use `--seed S` with the seed from the ledger line.
- Never open the CSV as code; treat it as data (the scorer does).

## Three-level score (finer than yes or no)

A detector that names claims (one claim per Trojan it says it found, with the cells where it says
the Trojan sits) can be scored at three levels with `lemanruss.score.levels`. Per circuit the score
is `|matched| / |C u T|` (1 if both empty): level 1 presence, level 2 count (`min` over `max` of
the claim and Trojan counts), level 3 location.

**Location match rule.** A claim hits a Trojan when a cell it names lies in that Trojan's region
(logic that feeds the victim output with no equal counterpart in the golden; `lemanruss regions`).
Matching is one to one: a Trojan is hit by at most one claim and a claim hits at most one Trojan.
Wrong claims are punished: two claims that both miss on an infected circuit score 1 at level 1 and
0 at level 3. TP/FP/FN/TN are counted over claims (TN: a clean circuit with no claim). A chance
control (same claims, random cells) is reported next to every result because regions are generous.
Specification: `docs/specs/2026-11-02-scoring-design.md` section 10.
