"""Permutation surrogate band (design §3).

Shuffling destroys temporal ORDER while preserving the marginal delta
distribution, so observed ACF escaping this band means the structure lives
in ordering, not in binning/reconstruction/event-alignment artifacts.
Permutation, never phase randomization: phase randomization preserves the
power spectrum and hence the ACF by construction (prereg).
"""
from __future__ import annotations

import random

from qsim.analysis import numerics


def permutation_band(series: list[float], max_lag: int,
                     n_shuffles: int = 1000, seed: int = 0) -> list[tuple[float, float]]:
    """Per-lag (2.5th, 97.5th) percentile band of shuffled-series ACF.

    The seed is the caller's to record in the report artifact (design §3).
    """
    rng = random.Random(seed)
    per_lag: list[list[float]] = [[] for _ in range(max_lag)]
    work = list(series)
    for _ in range(n_shuffles):
        rng.shuffle(work)
        r = numerics.acf(work, max_lag)
        for i, v in enumerate(r):
            per_lag[i].append(v)
    return [
        (numerics.percentile(vals, 2.5), numerics.percentile(vals, 97.5))
        for vals in per_lag
    ]
