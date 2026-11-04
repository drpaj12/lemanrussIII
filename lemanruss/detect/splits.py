"""Base splits of the Common protocol (s6-methods.tex): by base, five folds stratified by source,
seed 1; a second split by restructuring (the four LUT forms unseen)."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from lemanruss.detect.data import LUT_FORMS, SETS, Record

N_FOLDS = 5
FOLD_SEED = 1
MCNC = frozenset(
    {"alu4", "apex2", "apex4", "cordic", "ex5p", "misex3", "pdc", "spla", "t481"}
)
VTR = frozenset({"diffeq1", "diffeq2", "mkPktMerge", "mkSMAdapter4B", "sha"})


def source_of(base: str) -> str:
    if re.fullmatch(r"C\d+", base) or re.fullmatch(r"s\d+", base):
        return "ISCAS"
    if re.fullmatch(r"b\d+", base):
        return "ITC-99"
    if base.startswith("ve_"):
        return "VerilogEval"
    if base in MCNC:
        return "MCNC"
    if base in VTR:
        return "VTR"
    raise ValueError(f"unknown source for base {base!r}")


def make_folds(bases: list[str], n_folds: int = N_FOLDS, seed: int = FOLD_SEED) -> list[list[str]]:
    """Shuffle each source's bases with `seed` and deal them round-robin over the folds, the
    rotation continuing across sources so fold sizes differ by at most one."""
    by_source: dict[str, list[str]] = {}
    for b in sorted(bases):
        by_source.setdefault(source_of(b), []).append(b)
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    rng = random.Random(seed)
    i = 0
    for src in sorted(by_source):
        group = by_source[src]
        rng.shuffle(group)
        for b in group:
            folds[i % n_folds].append(b)
            i += 1
    return folds


@dataclass(frozen=True)
class Split:
    name: str  # "base" or "lut"
    fold: int
    train: list[Record]
    val: list[Record]
    test: list[Record]


def assert_no_overlap(split: Split) -> None:
    sides = [{r.base for r in s} for s in (split.train, split.val, split.test)]
    for a in range(3):
        for b in range(a + 1, 3):
            both = sides[a] & sides[b]
            if both:
                raise AssertionError(f"bases on two sides: {sorted(both)}")


def make_split(
    records: list[Record], name: str, fold: int, folds: list[list[str]], held: str = ""
) -> Split:
    """name 'base' (all circuits), 'lut' (rc1/rc2: the four LUT forms unseen) or 'set' (rc4:
    the obfuscation set `held` unseen; goldens are never used)."""
    n = len(folds)
    records = [r for r in records if r.set != "golden"]
    test_b, val_b = set(folds[fold]), set(folds[(fold + 1) % n])
    train_b = {b for f in folds for b in f} - test_b - val_b
    if name == "base":
        tr = [r for r in records if r.base in train_b]
        va = [r for r in records if r.base in val_b]
        te = [r for r in records if r.base in test_b]
    elif name == "lut":
        tr = [r for r in records if r.base in train_b and r.form not in LUT_FORMS]
        va = [r for r in records if r.base in val_b and r.form not in LUT_FORMS]
        te = [r for r in records if r.base in test_b and r.form in LUT_FORMS]
    elif name == "set":
        tr = [r for r in records if r.base in train_b and r.set != held]
        va = [r for r in records if r.base in val_b and r.set != held]
        te = [r for r in records if r.base in test_b and r.set == held]
    else:
        raise ValueError(name)
    split = Split(name if name != "set" else f"set-{held}", fold, tr, va, te)
    assert_no_overlap(split)
    return split


def all_splits(records: list[Record], name: str) -> list[Split]:
    """name 'set' gives the three held-out-set splits (set-K4, set-K6, set-G) per fold."""
    folds = make_folds(sorted({r.base for r in records}))
    if name == "set":
        return [make_split(records, name, k, folds, h) for h in SETS for k in range(len(folds))]
    return [make_split(records, name, k, folds) for k in range(len(folds))]
