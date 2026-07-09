"""Pure-Python reference numerics — the implementations that produced the
T1 control PASS (run f230668e, git 264b684).

Kept VERBATIM as the cross-validation reference for the numpy-backed
numerics.py (stamped decision doc docs/superpowers/specs/
2026-07-09-open-run-decisions.md, decision 2). Production code imports
numerics; only tests and the calibration bridge import this module.
"""
from __future__ import annotations

import math

BACKEND = "pure-python"


def mean(xs: list[float]) -> float:
    if not xs:
        raise ValueError("mean of empty list")
    return sum(xs) / len(xs)


def percentile(xs: list[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0, 100]."""
    if not xs:
        raise ValueError("percentile of empty list")
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = (q / 100.0) * (len(s) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    frac = pos - lo
    return s[lo] * (1.0 - frac) + s[hi] * frac


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
    m = sum(series) / n
    dev = [x - m for x in series]
    denom = sum(d * d for d in dev)
    if denom == 0.0:
        raise ValueError("zero-variance series: ACF undefined")
    out = []
    for k in range(1, max_lag + 1):
        num = sum(dev[t] * dev[t + k] for t in range(n - k))
        out.append(num / denom)
    return out
