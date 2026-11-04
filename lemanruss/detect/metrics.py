"""Metrics of the Common protocol: AUROC, threshold at FPR <= 5% on validation, TPR/FPR, F1 at
release prevalence and re-weighted, bootstrap over bases, W/L/T."""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence

import numpy as np

FPR_TARGET = 0.05
PREVALENCES = (0.1, 0.3, 0.5, 0.7)
EPS = 1e-6


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    """P(random positive scores above random negative), ties 0.5; None if a class is missing."""
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s))
    sorted_s = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    u = ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def threshold_at_fpr(clean_scores: Sequence[float], target: float = FPR_TARGET) -> float:
    """Lowest threshold t such that the share of clean scores >= t is <= target (flag s >= t).
    If even the top score exceeds the allowance (ties), t is just above the maximum."""
    if len(clean_scores) == 0:
        raise ValueError("validation fold has no clean circuit")
    s = np.asarray(clean_scores, dtype=float)
    allowed = int(np.floor(target * len(s) + 1e-9))
    best = float(np.nextafter(s.max(), np.inf))
    for v in sorted(set(s.tolist()), reverse=True):
        if int((s >= v).sum()) <= allowed:
            best = v
        else:
            break
    return best


def rates(
    scores: Sequence[float], labels: Sequence[int], threshold: float
) -> tuple[float | None, float | None]:
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    pos, neg = s[y == 1], s[y == 0]
    tpr = float((pos >= threshold).mean()) if len(pos) else None
    fpr = float((neg >= threshold).mean()) if len(neg) else None
    return tpr, fpr


def f1_at_prevalence(tpr: float, fpr: float, prevalence: float) -> float:
    tp = prevalence * tpr
    fp = (1 - prevalence) * fpr
    prec = tp / (tp + fp) if tp + fp > 0 else 0.0
    return 2 * prec * tpr / (prec + tpr) if prec + tpr > 0 else 0.0


Pairs = list[tuple[float, int]]


def bootstrap_ci(
    folds: list[dict[str, Pairs]],
    stat: Callable[[Pairs], float | None],
    reps: int = 1000,
    seed: int = 0,
) -> tuple[float, float] | None:
    """95% interval of the fold-mean of `stat`, resampling whole bases with replacement inside
    each test fold. `folds[k]` maps base -> its (score, label) pairs."""
    rng = random.Random(seed)
    keyed = [(sorted(f), f) for f in folds if f]
    vals: list[float] = []
    for _ in range(reps):
        per_fold: list[float] = []
        for bases, f in keyed:
            pairs: Pairs = []
            for _i in bases:
                pairs += f[rng.choice(bases)]
            v = stat(pairs)
            if v is not None:
                per_fold.append(v)
        if per_fold:
            vals.append(sum(per_fold) / len(per_fold))
    if not vals:
        return None
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def pair_auroc(pairs: list[tuple[float, int]]) -> float | None:
    return auroc([p[0] for p in pairs], [p[1] for p in pairs])


def wlt(
    method: Mapping[str, float | None], control: Mapping[str, float | None]
) -> tuple[int, int, int]:
    """Win/loss/tie over bases (AUROC higher/lower/equal within EPS); bases lacking a value skip."""
    w = lo = t = 0
    for b, m in method.items():
        c = control.get(b)
        if m is None or c is None:
            continue
        if m > c + EPS:
            w += 1
        elif m < c - EPS:
            lo += 1
        else:
            t += 1
    return w, lo, t
