"""Numerics against synthetic ground truths (design §11)."""
import math
import random

import pytest

from qsim.analysis import numerics


def test_white_noise_band_value():
    assert numerics.white_noise_band(400) == pytest.approx(1.96 / 20.0)


def test_max_estimable_lag_is_quarter_of_bins():
    assert numerics.max_estimable_lag(400) == 100
    assert numerics.max_estimable_lag(7) == 1


def test_percentile_linear_interpolation():
    xs = [1.0, 2.0, 3.0, 4.0]
    assert numerics.percentile(xs, 0) == 1.0
    assert numerics.percentile(xs, 100) == 4.0
    assert numerics.percentile(xs, 50) == pytest.approx(2.5)
    assert numerics.percentile([5.0], 75) == 5.0
    with pytest.raises(ValueError):
        numerics.percentile([], 50)


def test_acf_white_noise_mostly_inside_band():
    rng = random.Random(42)
    series = [rng.gauss(0.0, 1.0) for _ in range(2000)]
    max_lag = numerics.max_estimable_lag(len(series))
    r = numerics.acf(series, max_lag)
    band = numerics.white_noise_band(len(series))
    inside = sum(1 for v in r if abs(v) <= band)
    assert inside / max_lag >= 0.90  # ~95% expected; slack for one seed


def test_acf_alternating_series_has_strong_negative_lag1():
    series = [1.0, -1.0] * 100
    r = numerics.acf(series, 4)
    assert r[0] < -0.9


def test_acf_period_k_series_peaks_at_lag_k():
    series = [1.0, 0.0, 0.0, 0.0] * 200
    r = numerics.acf(series, 8)
    assert r[3] == max(r)
    assert r[3] > 0.5


def test_acf_refuses_degenerate_series():
    with pytest.raises(ValueError):
        numerics.acf([1.0], 1)
    with pytest.raises(ValueError):
        numerics.acf([2.0] * 50, 5)  # zero variance
