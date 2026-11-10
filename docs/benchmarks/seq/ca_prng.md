# ca_prng (Seq, Seeker's Dilemma v2.0)

Benchmark key: `ca_prng`. Family: Seq. Release: `seeker-v2.0`.

## Source and attribution

Source: OpenCores. OpenCores project; the project's own copyright notice and licence terms apply to the derived circuits and are kept with this package (see the family datasheet).

## Contents

Golden (the clean circuit): `golden.blif.gz`.

| set | circuits |
|---|---|
| K4 | 100 |
| K6 | 100 |
| gates | 100 |

Total: 300 circuits. Circuit ids are opaque and no label is published.

## Stimulus

`stimulus/sequence.txt`: a neutral input sequence of 256 cycles from reset.

## Download

- This benchmark: [seeker-seq-v2.0-ca_prng.tar.gz](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/seeker-seq-v2.0-ca_prng.tar.gz)
- Whole Seq family: [seeker-seq-v2.0-all.tar.gz](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/seeker-seq-v2.0-all.tar.gz)
- Checksums: [SHA256SUMS](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/SHA256SUMS)

## How to submit

Scoring units are `ca_prng-<set>` for each set above and `ca_prng` for all its sets together. See [SUBMISSION.md](../../user/SUBMISSION.md).
Scoring opens when the seeker-scoring service is live; see SUBMISSION.md.
