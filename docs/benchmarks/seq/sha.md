# sha (Seq, Seeker's Dilemma v2.0)

Benchmark key: `sha`. Family: Seq. Release: `seeker-v2.0`.

## Source and attribution

Source: VTR (OpenCores sha). OpenCores sha core as shipped in the VTR benchmark set; its permissive notice (copyright statement not removed, derivative works keep the notice) applies.

## Contents

Golden (the clean circuit): `golden.blif.gz` and `golden.silicon.blif.gz`.

| set | circuits |
|---|---|
| K4 | 100 |
| K6 | 100 |
| gates | 100 |
| silicon | 100 |

Total: 400 circuits. Circuit ids are opaque and no label is published.

## Stimulus

`stimulus/sequence.txt`: a neutral input sequence of 256 cycles from reset.

## Download

- This benchmark: [seeker-seq-v2.0-sha.tar.gz](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/seeker-seq-v2.0-sha.tar.gz)
- Whole Seq family: [seeker-seq-v2.0-all.tar.gz](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/seeker-seq-v2.0-all.tar.gz)
- Checksums: [SHA256SUMS](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/SHA256SUMS)

## How to submit

Scoring units are `sha-<set>` for each set above and `sha` for all its sets together. See [SUBMISSION.md](../../user/SUBMISSION.md).
Scoring opens when the seeker-scoring service is live; see SUBMISSION.md.
