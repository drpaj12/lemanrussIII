# OpenCores mips_16 (Proc, Seeker's Dilemma v2.0)

Benchmark key: `mips_16`. Family: Proc. Release: `seeker-v2.0`.

## Source and attribution

Source: core. Open-source processor core; its licence applies to the derived circuits (see the family datasheet).

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

`stimulus/neutral-program.hex`: the neutral program.

## Download

- This benchmark: [seeker-proc-v2.0-mips_16.tar.gz](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/seeker-proc-v2.0-mips_16.tar.gz)
- Whole Proc family: [seeker-proc-v2.0-all.tar.gz](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/seeker-proc-v2.0-all.tar.gz)
- Checksums: [SHA256SUMS](https://github.com/drpaj12/lemanrussIII/releases/download/seeker-v2.0/SHA256SUMS)

## How to submit

Scoring units are `mips_16-<set>` for each set above and `mips_16` for all its sets together. See [SUBMISSION.md](../../user/SUBMISSION.md).
Scoring opens when the seeker-scoring service is live; see SUBMISSION.md.
