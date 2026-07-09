"""Permutation surrogate band (design §3).

Shuffling destroys temporal ORDER while preserving the marginal delta
distribution, so observed ACF escaping this band means the structure lives
in ordering, not in binning/reconstruction/event-alignment artifacts.
Permutation, never phase randomization: phase randomization preserves the
power spectrum and hence the ACF by construction (prereg).

The mean and ACF denominator are shuffle-invariant (a permutation changes
neither the multiset of values nor its sum of squared deviations), so both
are hoisted out of the shuffle loop (stamped decision doc, decision 2).
The random.Random(seed).shuffle call sequence is unchanged from the
pure-Python implementation, so a given seed yields the same permutations
the control PASS saw.
"""
from __future__ import annotations

import random

import numpy as np


def permutation_band(series: list[float], max_lag: int,
                     n_shuffles: int = 1000, seed: int = 0) -> list[tuple[float, float]]:
    """Per-lag (2.5th, 97.5th) percentile band of shuffled-series ACF.

    The seed is the caller's to record in the report artifact (design §3).
    Raises ValueError on degenerate series exactly as numerics.acf does —
    the caller records that as a refusal, never a verdict.
    """
    n = len(series)
    if n < 2:
        raise ValueError(f"series too short for ACF: n={n}")
    x = np.asarray(series, dtype=np.float64)
    m = x.mean()
    dev0 = x - m
    denom = float(dev0 @ dev0)
    if denom == 0.0:
        raise ValueError("zero-variance series: ACF undefined")

    rng = random.Random(seed)
    work = list(series)
    per_shuffle = np.empty((n_shuffles, max_lag), dtype=np.float64)
    for i in range(n_shuffles):
        rng.shuffle(work)
        dev = np.asarray(work, dtype=np.float64) - m
        per_shuffle[i] = np.correlate(dev, dev, mode="full")[n:n + max_lag] / denom

    lo, hi = np.percentile(per_shuffle, [2.5, 97.5], axis=0, method="linear")
    return [(float(a), float(b)) for a, b in zip(lo, hi)]
