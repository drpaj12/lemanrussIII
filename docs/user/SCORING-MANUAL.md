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
