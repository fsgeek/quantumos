"""Series arithmetic for the analysis package (design §3).

numpy-backed since the 2026-07-09 swap (stamped decision doc
docs/superpowers/specs/2026-07-09-open-run-decisions.md, decision 2):
direct correlation via np.correlate, never FFT — numerically closest to
the pure-Python loops that produced the T1 control PASS. Those loops live
on verbatim in reference.py; a cross-validation test holds the two
backends to ~1e-12 agreement, and the calibration bridge measures the
instrument change on the control run itself.

This module remains the numpy seam: NOTHING else in qsim does series
statistics, so backend changes never touch gate or verdict logic.
"""
from __future__ import annotations

import math

import numpy as np

BACKEND = "numpy"


def mean(xs: list[float]) -> float:
    if not len(xs):
        raise ValueError("mean of empty list")
    return float(np.mean(np.asarray(xs, dtype=np.float64)))


def percentile(xs: list[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0, 100]."""
    if not len(xs):
        raise ValueError("percentile of empty list")
    return float(np.percentile(np.asarray(xs, dtype=np.float64), q,
                               method="linear"))


def max_estimable_lag(n_bins: int) -> int:
    """Standard reliability bound for the ACF estimator (design §4.4)."""
    return n_bins // 4


def white_noise_band(n_bins: int) -> float:
    """95% white-noise band 1.96/sqrt(n) (prereg T1 pass criterion)."""
    return 1.96 / math.sqrt(n_bins)


def acf(series: list[float], max_lag: int) -> list[float]:
    """Biased-normalization autocorrelation r_k for k = 1..max_lag.

    Returns a list where index k-1 holds r_k. Raises ValueError on a series
    too short or with zero variance — the caller records that as an
    'insufficient data' refusal (design §10), never a verdict.
    """
    n = len(series)
    if n < 2:
        raise ValueError(f"series too short for ACF: n={n}")
    x = np.asarray(series, dtype=np.float64)
    dev = x - x.mean()
    denom = float(dev @ dev)
    if denom == 0.0:
        raise ValueError("zero-variance series: ACF undefined")
    # full correlation index n-1 is lag 0, so lags 1..max_lag are the next
    # max_lag entries
    num = np.correlate(dev, dev, mode="full")[n:n + max_lag]
    return [float(v) / denom for v in num]
