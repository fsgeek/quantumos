"""Cross-validation: numpy-backed numerics vs the pure-Python reference.

The pure-Python implementations produced the T1 control PASS (run f230668e),
so they are the calibrated instrument; numpy is the challenger. Contract
(docs/superpowers/specs/2026-07-09-open-run-decisions.md, decision 2):
direct correlation not FFT, agreement to ~1e-12 on random series, refusal
semantics preserved, pure-Python kept as reference.
"""
import math
import random

import pytest

from qsim.analysis import numerics, reference
from qsim.analysis.surrogates import permutation_band

TOL = 1e-12


def test_backend_is_numpy():
    assert numerics.BACKEND == "numpy"


def test_reference_backend_is_pure_python():
    assert reference.BACKEND == "pure-python"


def _random_series(seed: int, n: int) -> list[float]:
    rng = random.Random(seed)
    return [rng.gauss(0.0, 1.0) for _ in range(n)]


@pytest.mark.parametrize("seed,n", [(1, 50), (2, 500), (3, 2000)])
def test_acf_agrees_with_reference_on_random_series(seed, n):
    series = _random_series(seed, n)
    max_lag = reference.max_estimable_lag(n)
    got = numerics.acf(series, max_lag)
    want = reference.acf(series, max_lag)
    assert len(got) == len(want) == max_lag
    assert max(abs(g - w) for g, w in zip(got, want)) < TOL


def test_acf_agrees_on_structured_series():
    # Structure, not noise: the alternating series that anchors the
    # synthetic ground-truth tests.
    series = [1.0, -1.0] * 100
    assert max(abs(g - w) for g, w in
               zip(numerics.acf(series, 10), reference.acf(series, 10))) < TOL


def test_mean_agrees_with_reference():
    series = _random_series(7, 313)
    assert abs(numerics.mean(series) - reference.mean(series)) < TOL


@pytest.mark.parametrize("q", [0.0, 2.5, 10, 25, 50, 75, 90, 97.5, 100.0])
def test_percentile_agrees_with_reference(q):
    series = _random_series(11, 401)
    assert abs(numerics.percentile(series, q)
               - reference.percentile(series, q)) < TOL


def test_scalar_helpers_agree():
    for n in (7, 400, 20000):
        assert numerics.max_estimable_lag(n) == reference.max_estimable_lag(n)
        assert math.isclose(numerics.white_noise_band(n),
                            reference.white_noise_band(n), rel_tol=0, abs_tol=TOL)


def test_refusal_semantics_preserved():
    """Refusals are recorded, never invented (design §10): the numpy path
    must raise the same ValueError class on the same degenerate inputs."""
    for mod in (numerics, reference):
        with pytest.raises(ValueError):
            mod.mean([])
        with pytest.raises(ValueError):
            mod.percentile([], 50)
        with pytest.raises(ValueError):
            mod.acf([1.0], 1)  # too short
        with pytest.raises(ValueError):
            mod.acf([2.0] * 50, 5)  # zero variance


def test_permutation_band_agrees_with_reference_pipeline():
    """The surrogate band after the hoist must match the band the ORIGINAL
    pipeline computes: same random.Random(seed) shuffle sequence, reference
    ACF and percentile at every step."""
    series = _random_series(5, 240)
    max_lag, n_shuffles, seed = 12, 60, 9

    got = permutation_band(series, max_lag, n_shuffles=n_shuffles, seed=seed)

    # Original (pre-hoist) construction, reference numerics throughout.
    rng = random.Random(seed)
    per_lag = [[] for _ in range(max_lag)]
    work = list(series)
    for _ in range(n_shuffles):
        rng.shuffle(work)
        r = reference.acf(work, max_lag)
        for i, v in enumerate(r):
            per_lag[i].append(v)
    want = [(reference.percentile(vals, 2.5), reference.percentile(vals, 97.5))
            for vals in per_lag]

    for (glo, ghi), (wlo, whi) in zip(got, want):
        assert abs(glo - wlo) < TOL
        assert abs(ghi - whi) < TOL
