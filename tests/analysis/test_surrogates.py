"""Permutation surrogate band (design §3; prereg reconstruction control).

Permutation, deliberately NOT phase randomization: phase-randomized
surrogates preserve the ACF by construction (prereg, 2026-07-07 amendment).
"""
from qsim.analysis import numerics
from qsim.analysis.surrogates import permutation_band


def test_same_seed_gives_identical_band():
    series = [float(i % 5) for i in range(200)]
    a = permutation_band(series, max_lag=10, n_shuffles=50, seed=7)
    b = permutation_band(series, max_lag=10, n_shuffles=50, seed=7)
    assert a == b


def test_different_seed_gives_different_band():
    series = [float(i % 5) for i in range(200)]
    a = permutation_band(series, max_lag=10, n_shuffles=50, seed=7)
    b = permutation_band(series, max_lag=10, n_shuffles=50, seed=8)
    assert a != b


def test_real_structure_escapes_the_surrogate_band():
    series = [1.0, -1.0] * 200
    band = permutation_band(series, max_lag=5, n_shuffles=200, seed=1)
    r = numerics.acf(series, 5)
    lo, hi = band[0]
    assert r[0] < lo  # lag-1 ACF ~ -1 sits far below any shuffled band
    assert lo < 0.0 < hi  # shuffles straddle zero
