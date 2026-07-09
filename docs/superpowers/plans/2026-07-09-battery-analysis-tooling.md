# Field-Battery Analysis Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `qsim/analysis/` plus the new observe views so the stamped field-battery prereg (T1/T2/T3 + S1 sweep) can be run and read: trace→series reconstruction in `observe/`, series→statistic→verdict in `analysis/`, artifacts under each run's `analysis/` dir, wired to `quantumos analyze` / `quantumos sweep s1`.

**Architecture:** Views join `qsim/observe/` (same `events_path: Path` + `iter_events` streaming contract; delta-derived, payload fields reserved as self-checks). New package `qsim/analysis/` owns statistics/surrogates/attribution/artifacts/verdicts; it consumes views and `header.json`, never parses `events.jsonl` itself. All statistic arithmetic lives in `analysis/numerics.py` (the numpy-swap seam). Design doc: `docs/superpowers/specs/2026-07-07-battery-analysis-tooling-design.md`; prereg: `docs/superpowers/specs/2026-07-06-field-battery-prereg.md`.

**Tech Stack:** Python ≥3.11, stdlib only (no numpy). Tests: pytest via `uv run pytest`.

## Global Constraints

- Dependencies stay **stdlib-only** (design §1). numpy is a later swap inside `numerics.py` internals only.
- `qsim/analysis/` never reads `events.jsonl` directly — only via `qsim.observe` views and `header.json` (design §1).
- Series arithmetic (ACF, bands, percentiles) lives ONLY in `analysis/numerics.py`. The trivial delta-binning loop is reconstruction and lives in `observe/` (`_bin_deltas`) — disclosed deviation so observe never imports analysis.
- Views are delta-derived; payload `depth` fields are reserved as independent test self-checks (the `pool_depth_series` convention, `qsim/observe/views.py:140`).
- Refusals are data (design §10): every refusal is recorded in the report artifact, not just stderr.
- Write-then-look is binding (design §4.3): predicted lags are derived and written **before** any ACF is computed; the file is write-once.
- Prereg criteria are implemented verbatim where pinned; every mechanical definition the prereg does NOT pin is a **disclosed convention** stated in the report artifact.
- TDD per task: failing test → run → minimal impl → run → commit. Full suite (`uv run pytest`) green before each commit.
- Commit messages: `qsim: <what>` matching repo convention; end with the Claude Co-Authored-By line.

## Findings from planning (deviations + veto points, surfaced 2026-07-09)

1. **`round.retried` is in the trace taxonomy (`qsim/core/trace.py:37`) but never published.** Retries appear as fresh `round.arrived` events with incremented `payload.retry_ordinal` on a stable round_id (`entity_id`). `retry_cadence_samples` binds to that lineage; the design table's mention of `round.retried` is corrected here.
2. **S1 grid δ=0.4 is infeasible:** prereg's own example (δ=0.2 → {0.5, 0.633, 0.767, 0.9}) fixes δ as half-spread, so δ=0.4 at p̄=0.7 yields heralding_p=1.1 > 1. The sweep runner records that arm as an in-manifest refusal and runs the feasible arms. Recommended prereg amendment (pre-run gap closing, legitimate per design posture note): replace δ=0.4 with δ=0.3 → {0.4, 0.6, 0.8, 1.0}.
3. **T3 projection-time convention (Tony veto point):** projected fidelity for a co-pending lease = `fidelity_at_herald · exp(−rate·(t_terminal − heralded_at))` where `t_terminal` is that lease's own terminal event time from the trace (consumed/expired/cancelled/pool_returned). The TIME is observed; the FIDELITY is analytic (never read from an outcome event) — satisfying "analytic from trace, projected never observed." Leases with no terminal in the trace are excluded from ordering and counted as censored in the report.
4. **Pool-sourced herald time:** `lease.heralded(source="pool")` fires at withdrawal time, not the original herald; the true `heralded_at` is the pooled lease's generation instant = sim_time of `pool.deposited(lease_id=<pooled_lease_id>)` (herald resolution and deposit are the same instant, `engine.py:803`). The T3 view binds to that.
5. **Per-test predicted-lags filenames:** `predicted_lags_t1.json` / `predicted_lags_t2.json` (design says one `predicted_lags.json`; T1 and T2 can analyze the same run dir, and write-once must not collide across tests).
6. **Warmup trim:** T1/T2 series drop bins that start before the header's `steady_state.warmup_cutoff_s` (the steady-state module records it "so downstream metric consumers can trim the transient consistently"). Disclosed in the report.
7. **T2 window/bin convention (prereg pins neither):** bin_s = service time (1/μ) rounded to one significant figure; window = [service-time lag, busy-period-relaxation lag], widened to ≥3 bins, min lag 1. Disclosed in the report.
8. **T3 "degenerate-dominated" convention:** nondegenerate fraction < 0.5 → NON-FIELD at this operating point. Disclosed.
9. **Replenish-issue binding:** issue = `reservation.acquired` with `payload.round_id == None` and a `request_id` (holder is the replenish request, `engine.py:711-716`); its `lease_id` is `"<request_id>:L"`, matched to `pool.deposited(source="replenish", lease_id=…)`.

## File Structure

- Create `qsim/analysis/__init__.py` — package marker, re-exports nothing (explicit module imports).
- Create `qsim/analysis/numerics.py` — percentile, mean, ACF, white-noise band, max estimable lag.
- Create `qsim/analysis/surrogates.py` — permutation surrogate band.
- Create `qsim/analysis/attribution.py` — named-cycle predicted lags + assignment.
- Create `qsim/analysis/artifacts.py` — write-once file, sha256, git ancestry check, report writer; `STAMPED_COMMIT` constant.
- Create `qsim/analysis/t1.py`, `qsim/analysis/t2.py`, `qsim/analysis/t3.py` — verdict assembly.
- Modify `qsim/observe/views.py` — add `_bin_deltas`, `pool_flux_series`, `backlog_slope_series`, `replenishment_latency_samples`, `inter_withdrawal_times`, `retry_cadence_samples`.
- Create `qsim/observe/decision_points.py` — `t3_decision_points` (big enough to own a module).
- Create `qsim/experiments/sweep.py` — S1 sweep runner.
- Modify `qsim/cli.py` — `analyze` and `sweep` subcommands.
- Create `examples/t1-open-companion.toml` — knob-motion companion config.
- Tests: `tests/analysis/` (new dir, with `__init__.py`), additions under `tests/observe/`, `tests/experiments/`.

---

### Task 1: `analysis/numerics.py`

**Files:**
- Create: `qsim/analysis/__init__.py`
- Create: `qsim/analysis/numerics.py`
- Create: `tests/analysis/__init__.py`
- Test: `tests/analysis/test_numerics.py`

**Interfaces:**
- Produces: `mean(xs: list[float]) -> float`; `percentile(xs: list[float], q: float) -> float` (linear interpolation, q in [0,100]); `acf(series: list[float], max_lag: int) -> list[float]` (index k−1 holds r_k for k=1..max_lag; raises `ValueError` on len<2 or zero variance); `max_estimable_lag(n_bins: int) -> int` (= n_bins // 4); `white_noise_band(n_bins: int) -> float` (= 1.96/√n_bins).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_numerics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.analysis'`

- [ ] **Step 3: Write minimal implementation**

`qsim/analysis/__init__.py`:

```python
"""Series→statistic→verdict layer for the field battery (analysis-tooling
design §1). Consumes qsim.observe views and header.json; NEVER parses
events.jsonl itself. Stdlib-only; series arithmetic lives in numerics.py
(the numpy-swap seam)."""
```

`tests/analysis/__init__.py`: empty file.

`qsim/analysis/numerics.py`:

```python
"""Series arithmetic for the analysis package (design §3).

Pure stdlib. This module is the numpy-swap seam: NOTHING else in qsim does
series statistics, so numpy can replace these internals later without
touching gate or verdict logic.
"""
from __future__ import annotations

import math


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_numerics.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/__init__.py qsim/analysis/numerics.py tests/analysis/__init__.py tests/analysis/test_numerics.py
git commit -m "qsim: analysis numerics (ACF, bands, percentiles) — the numpy-swap seam"
```

---

### Task 2: `analysis/surrogates.py`

**Files:**
- Create: `qsim/analysis/surrogates.py`
- Test: `tests/analysis/test_surrogates.py`

**Interfaces:**
- Consumes: `numerics.acf`, `numerics.percentile`.
- Produces: `permutation_band(series: list[float], max_lag: int, n_shuffles: int = 1000, seed: int = 0) -> list[tuple[float, float]]` — per-lag (2.5th, 97.5th) percentiles of shuffled-series ACF; index k−1 for lag k.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_surrogates.py -v`
Expected: FAIL with `ModuleNotFoundError` (surrogates)

- [ ] **Step 3: Write minimal implementation**

`qsim/analysis/surrogates.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_surrogates.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/surrogates.py tests/analysis/test_surrogates.py
git commit -m "qsim: permutation surrogate band (seeded, deterministic)"
```

---

### Task 3: flux + backlog-slope views

**Files:**
- Modify: `qsim/observe/views.py` (append after `pool_depth_series` / `_to_hashable`)
- Test: `tests/observe/test_views_pool_flux.py`

**Interfaces:**
- Consumes: `iter_events`, `_POOL_DEPTH_DELTAS`, `_to_hashable` (all already in `views.py`).
- Produces: `pool_flux_series(events_path: Path, bin_s: float) -> dict[tuple, list[float]]` — per-(path, coherence) key, net depth delta per bin divided by bin_s (a d(pool)/dt rate); bins span [0, horizon) where horizon = max sim_time over ALL events. `backlog_slope_series(events_path: Path, bin_s: float) -> list[float]` — decoder backlog slope per bin. `_bin_deltas(deltas: list[tuple[float, float]], bin_s: float, horizon: float) -> list[float]`.

- [ ] **Step 1: Write the failing test**

```python
"""Flux + backlog-slope views: delta-derived, payload depth reserved as
self-check (design §2)."""
import json

import pytest

from qsim.observe.views import backlog_slope_series, pool_flux_series

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]
KEY_B = [[["M1", 0], ["M2", 0]], "messenger"]


def _write_events(path, rows):
    with open(path, "w") as f:
        for seq, (t, event_type, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": f"e{seq}",
                "causal_parent_id": None, "payload": payload,
            }) + "\n")


def test_pool_flux_bins_net_deltas_per_key_as_rate(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.05, "pool.deposited", {"key": KEY_A, "depth": 1}),
        (0.15, "pool.deposited", {"key": KEY_A, "depth": 2}),
        (0.18, "pool.deposited", {"key": KEY_B, "depth": 1}),
        (0.25, "pool.withdrawn", {"key": KEY_A, "depth": 1}),
        (0.27, "pool.expired", {"key": KEY_A, "depth": 0}),
        (0.29, "lease.pool_returned", {"key": KEY_A}),  # annotation: must NOT count
    ])
    flux = pool_flux_series(events, bin_s=0.1)
    key_a = (((("M0", 0), ("M1", 0))), "messenger")
    key_b = (((("M1", 0), ("M2", 0))), "messenger")
    assert flux[key_a] == pytest.approx([10.0, 10.0, -20.0])
    assert flux[key_b] == pytest.approx([0.0, 10.0, 0.0])


def test_pool_flux_empty_trace_is_empty(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text("")
    assert pool_flux_series(events, bin_s=0.1) == {}


def test_backlog_slope_bins_enqueue_complete_deltas(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.05, "decoder.enqueued", {}),
        (0.12, "decoder.enqueued", {}),
        (0.28, "decoder.completed", {}),
    ])
    assert backlog_slope_series(events, bin_s=0.1) == pytest.approx([10.0, 10.0, -10.0])


def test_backlog_slope_counts_cancelled_as_exit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.02, "decoder.enqueued", {}),
        (0.05, "decoder.cancelled", {}),
    ])
    assert backlog_slope_series(events, bin_s=0.1) == pytest.approx([0.0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/observe/test_views_pool_flux.py -v`
Expected: FAIL with `ImportError: cannot import name 'pool_flux_series'`

- [ ] **Step 3: Write minimal implementation**

Append to `qsim/observe/views.py` (after `_to_hashable`; add `import math` at top):

```python
def _bin_deltas(deltas: list[tuple[float, float]], bin_s: float,
                horizon: float) -> list[float]:
    """Net delta per bin over [0, horizon). Reconstruction granularity, not
    statistics — series arithmetic proper lives in qsim.analysis.numerics
    (disclosed deviation in the 2026-07-09 plan: keeping this loop here means
    observe never imports analysis)."""
    n = max(1, math.ceil(horizon / bin_s))
    bins = [0.0] * n
    for t, d in deltas:
        i = min(int(t // bin_s), n - 1)
        bins[i] += d
    return bins


def pool_flux_series(events_path: Path, bin_s: float) -> dict[tuple, list[float]]:
    """Binned d(pool)/dt per (path, coherence) key, from depth-moving pool.*
    deltas ALONE (design §2; prereg T1 statistic). Values are rates
    (net delta / bin_s). Bin span is [0, horizon) with horizon = max
    sim_time over ALL events, so every key's series is index-aligned."""
    deltas_by_key: dict[tuple, list[tuple[float, float]]] = {}
    horizon = 0.0
    for record in iter_events(events_path):
        t = float(record["sim_time"])
        if t > horizon:
            horizon = t
        delta = _POOL_DEPTH_DELTAS.get(record["event_type"])
        if delta is None:
            continue
        key = _to_hashable(record["payload"]["key"])
        deltas_by_key.setdefault(key, []).append((t, float(delta)))
    return {
        key: [v / bin_s for v in _bin_deltas(deltas, bin_s, horizon)]
        for key, deltas in deltas_by_key.items()
    }


_BACKLOG_DELTAS = {
    "decoder.enqueued": 1.0,
    "decoder.completed": -1.0,
    "decoder.cancelled": -1.0,
}


def backlog_slope_series(events_path: Path, bin_s: float) -> list[float]:
    """Binned slope of decoder backlog (design §2; T2 statistic): net
    enqueue/complete/cancel delta per bin / bin_s — exactly the per-bin
    slope of the `decoder_backlog_series` step function."""
    deltas: list[tuple[float, float]] = []
    horizon = 0.0
    for record in iter_events(events_path):
        t = float(record["sim_time"])
        if t > horizon:
            horizon = t
        delta = _BACKLOG_DELTAS.get(record["event_type"])
        if delta is not None:
            deltas.append((t, delta))
    if not deltas:
        return []
    return [v / bin_s for v in _bin_deltas(deltas, bin_s, horizon)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/observe/test_views_pool_flux.py tests/observe -v`
Expected: new tests PASS; no existing observe test broken

- [ ] **Step 5: Commit**

```bash
git add qsim/observe/views.py tests/observe/test_views_pool_flux.py
git commit -m "qsim: pool-flux and backlog-slope views (binned delta rates)"
```

---

### Task 4: lineage views (replenishment latency, inter-withdrawal, retry cadence)

**Files:**
- Modify: `qsim/observe/views.py` (append)
- Test: `tests/observe/test_views_lineage.py`

**Interfaces:**
- Produces: `replenishment_latency_samples(events_path: Path) -> list[float]`; `inter_withdrawal_times(events_path: Path) -> dict[tuple, list[float]]`; `retry_cadence_samples(events_path: Path) -> list[float]`.
- Bindings (findings #1, #9): replenish issue = `reservation.acquired` with `payload["round_id"] is None` and `"request_id" in payload`, keyed by `payload["lease_id"]`; deposit = `pool.deposited` with `payload["source"] == "replenish"`, same `lease_id`. Retry cadence = per `entity_id` gaps between consecutive `round.arrived` where the later arrival's `retry_ordinal >= 1`. `round.retried` is never published — do not bind to it.

- [ ] **Step 1: Write the failing test**

```python
"""Lineage views: replenish issue→deposit latency, withdrawal gaps, retry
cadence (design §2 with plan finding #1: round.retried is taxonomy-only,
never published — retries are fresh round.arrived with retry_ordinal)."""
import json

import pytest

from qsim.observe.views import (
    inter_withdrawal_times,
    replenishment_latency_samples,
    retry_cadence_samples,
)

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]


def _write_events(path, rows):
    with open(path, "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")


def test_replenishment_latency_matches_issue_to_deposit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        # replenish issue: round_id None + request_id, lease_id "<req>:L"
        (1.0, "reservation.acquired", "res:M0:0|M1:0",
         {"round_id": None, "lease_id": "R1:L", "request_id": "R1",
          "path_id": [["M0", 0], ["M1", 0]]}),
        # a ROUND-holder acquisition must be ignored
        (1.1, "reservation.acquired", "res:M1:0|M2:0",
         {"round_id": "round-1", "lease_id": "L9",
          "path_id": [["M1", 0], ["M2", 0]]}),
        (1.35, "pool.deposited", "R1:L",
         {"key": KEY_A, "depth": 1, "lease_id": "R1:L", "round_id": None,
          "source": "replenish"}),
        # round_return deposit must NOT produce a sample
        (2.0, "pool.deposited", "L9",
         {"key": KEY_A, "depth": 2, "lease_id": "L9", "round_id": "round-1",
          "source": "round_return"}),
    ])
    assert replenishment_latency_samples(events) == pytest.approx([0.35])


def test_replenishment_latency_skips_unmatched_deposit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "pool.deposited", "RX:L",
         {"key": KEY_A, "depth": 1, "lease_id": "RX:L", "round_id": None,
          "source": "replenish"}),
    ])
    assert replenishment_latency_samples(events) == []


def test_inter_withdrawal_times_per_key(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "pool.withdrawn", "p1", {"key": KEY_A, "depth": 1,
                                        "pooled_lease_id": "p1", "lease_id": "l1",
                                        "round_id": "r1"}),
        (1.5, "pool.withdrawn", "p2", {"key": KEY_A, "depth": 0,
                                        "pooled_lease_id": "p2", "lease_id": "l2",
                                        "round_id": "r2"}),
        (2.5, "pool.withdrawn", "p3", {"key": KEY_A, "depth": 0,
                                        "pooled_lease_id": "p3", "lease_id": "l3",
                                        "round_id": "r3"}),
    ])
    key_a = (((("M0", 0), ("M1", 0))), "messenger")
    assert inter_withdrawal_times(events)[key_a] == pytest.approx([0.5, 1.0])


def test_retry_cadence_gaps_within_round_lineage(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "round.arrived", "round-1", {"deadline": 3.0, "retry_ordinal": 0}),
        (1.2, "round.arrived", "round-2", {"deadline": 3.2, "retry_ordinal": 0}),
        (3.0, "round.arrived", "round-1", {"deadline": 5.0, "retry_ordinal": 1}),
        (5.5, "round.arrived", "round-1", {"deadline": 7.5, "retry_ordinal": 2}),
    ])
    assert retry_cadence_samples(events) == pytest.approx([2.0, 2.5])


def test_retry_cadence_empty_when_no_retries(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "round.arrived", "round-1", {"deadline": 3.0, "retry_ordinal": 0}),
    ])
    assert retry_cadence_samples(events) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/observe/test_views_lineage.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Append to `qsim/observe/views.py`:

```python
def replenishment_latency_samples(events_path: Path) -> list[float]:
    """POOL_REPLENISH issue → pool deposit latency samples (prereg T1 lag
    definition). Issue is the replenish reservation acquisition: the ONLY
    reservation.acquired with round_id=None is the §8.2 replenish holder
    (engine.py: holder_id is the request id, lease_id "<request_id>:L");
    the matching deposit is pool.deposited(source="replenish") with the
    same lease_id. Measured from events that are NOT the ACF (prereg
    attribution rule)."""
    issued_at: dict[str, float] = {}
    samples: list[float] = []
    for record in iter_events(events_path):
        event_type = record["event_type"]
        payload = record["payload"]
        if (event_type == "reservation.acquired"
                and payload.get("round_id") is None
                and "request_id" in payload):
            issued_at[payload["lease_id"]] = record["sim_time"]
        elif (event_type == "pool.deposited"
                and payload.get("source") == "replenish"):
            t0 = issued_at.pop(payload["lease_id"], None)
            if t0 is not None:
                samples.append(record["sim_time"] - t0)
    return samples


def inter_withdrawal_times(events_path: Path) -> dict[tuple, list[float]]:
    """Per-pool-key gaps between successive pool.withdrawn events (the
    low-water oscillation cycle basis: mean gap x L, prereg attribution)."""
    last_at: dict[tuple, float] = {}
    gaps: dict[tuple, list[float]] = {}
    for record in iter_events(events_path):
        if record["event_type"] != "pool.withdrawn":
            continue
        key = _to_hashable(record["payload"]["key"])
        t = record["sim_time"]
        prev = last_at.get(key)
        if prev is not None:
            gaps.setdefault(key, []).append(t - prev)
        last_at[key] = t
    return gaps


def retry_cadence_samples(events_path: Path) -> list[float]:
    """Retry lineage cycle times. `round.retried` exists in the taxonomy but
    is NEVER published (2026-07-09 plan finding #1): a retry is a fresh
    round.arrived with incremented payload.retry_ordinal on the SAME
    entity_id (the stable round_id). A sample is the gap between consecutive
    arrivals of one lineage where the later arrival is a retry."""
    last_arrival: dict[str, float] = {}
    samples: list[float] = []
    for record in iter_events(events_path):
        if record["event_type"] != "round.arrived":
            continue
        round_id = record["entity_id"]
        t = record["sim_time"]
        prev = last_arrival.get(round_id)
        if prev is not None and record["payload"].get("retry_ordinal", 0) >= 1:
            samples.append(t - prev)
        last_arrival[round_id] = t
    return samples
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/observe/test_views_lineage.py tests/observe -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/observe/views.py tests/observe/test_views_lineage.py
git commit -m "qsim: lineage views — replenish latency, withdrawal gaps, retry cadence"
```

---

### Task 5: `observe/decision_points.py` (T3 reconstruction)

**Files:**
- Create: `qsim/observe/decision_points.py`
- Test: `tests/observe/test_decision_points.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class LeaseAtDecision:
    lease_id: str
    incarnation: int          # bumps on each lease.requested for this id
    heralded_at: float        # true herald instant (finding #4 for pool source)
    fidelity_at_herald: float
    terminal_type: str | None   # lease.consumed|lease.expired|lease.cancelled|lease.pool_returned
    terminal_time: float | None

@dataclass(frozen=True)
class DecisionPoint:
    sim_time: float
    consumed_lease_id: str
    co_pending: tuple[LeaseAtDecision, ...]  # all HERALDED-not-terminal at sim_time, incl. the consumed one

def t3_decision_points(events_path: Path) -> list[DecisionPoint]
```

- Semantics: two passes. Pass 1 indexes per-incarnation herald info + first terminal, and `pool.deposited` sim_times by `lease_id` (for pool-sourced herald backdating). Pass 2 replays: `lease.heralded` adds the incarnation to the live set; its terminal removes it; each `lease.consumed` emits a DecisionPoint snapshotting the live set. Episodes are segmented by incarnation (lease_ids recur across retries; envelope `seq` orders same-time events — `iter_events` yields file order, which is seq order).

- [ ] **Step 1: Write the failing test**

```python
"""T3 decision-point reconstruction (design §2 last row; prereg T3).

Hand-built traces with known co-pending sets (design §11)."""
import json

import pytest

from qsim.observe.decision_points import t3_decision_points

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]


def _write_events(path, rows):
    with open(path, "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")


def test_decision_point_snapshots_co_pending_set_with_terminals(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.0, "lease.requested", "L1", {"round_id": "r1"}),
        (0.5, "lease.requested", "L2", {"round_id": "r2"}),
        (1.0, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (2.0, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (5.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.85}),
        (6.0, "lease.expired", "L2", {"round_id": "r2"}),
    ])
    points = t3_decision_points(events)
    assert len(points) == 1
    dp = points[0]
    assert dp.sim_time == 5.0
    assert dp.consumed_lease_id == "L1"
    by_id = {l.lease_id: l for l in dp.co_pending}
    assert set(by_id) == {"L1", "L2"}
    assert by_id["L1"].heralded_at == 1.0
    assert by_id["L1"].fidelity_at_herald == 0.9
    assert by_id["L1"].terminal_type == "lease.consumed"
    assert by_id["L1"].terminal_time == 5.0
    assert by_id["L2"].terminal_type == "lease.expired"
    assert by_id["L2"].terminal_time == 6.0


def test_pool_sourced_lease_backdates_heralded_at_to_deposit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (2.5, "pool.deposited", "P1", {"key": KEY_A, "depth": 1, "lease_id": "P1",
                                        "round_id": None, "source": "replenish"}),
        (4.0, "lease.requested", "L1", {"round_id": "r1"}),
        (4.0, "pool.withdrawn", "P1", {"key": KEY_A, "depth": 0,
                                        "pooled_lease_id": "P1", "lease_id": "L1",
                                        "round_id": "r1"}),
        (4.0, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.95,
                                        "source": "pool", "pooled_lease_id": "P1"}),
        (4.5, "lease.requested", "L2", {"round_id": "r2"}),
        (4.6, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.7}),
        (5.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.9}),
        (5.5, "lease.consumed", "L2", {"round_id": "r2", "fidelity_at_consumption": 0.65}),
    ])
    points = t3_decision_points(events)
    assert len(points) == 2
    by_id = {l.lease_id: l for l in points[0].co_pending}
    assert by_id["L1"].heralded_at == 2.5  # deposit instant, not withdrawal
    # second decision point: only L2 remains co-pending (degenerate set)
    assert [l.lease_id for l in points[1].co_pending] == ["L2"]


def test_lease_id_reuse_across_retries_is_segmented(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "lease.requested", "L1", {"round_id": "r1"}),
        (1.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (2.0, "lease.cancelled", "L1", {"round_id": "r1"}),
        # retry: same lease_id, fresh incarnation
        (3.0, "lease.requested", "L1", {"round_id": "r1"}),
        (3.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.6}),
        (4.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.55}),
    ])
    points = t3_decision_points(events)
    assert len(points) == 1
    (lease,) = points[0].co_pending
    assert lease.incarnation == 2
    assert lease.fidelity_at_herald == 0.6
    assert lease.heralded_at == 3.5


def test_censored_lease_has_none_terminal(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "lease.requested", "L1", {"round_id": "r1"}),
        (1.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (2.0, "lease.requested", "L2", {"round_id": "r2"}),
        (2.5, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (3.0, "lease.consumed", "L2", {"round_id": "r2", "fidelity_at_consumption": 0.75}),
        # L1 never reaches a terminal (horizon censoring)
    ])
    points = t3_decision_points(events)
    by_id = {l.lease_id: l for l in points[0].co_pending}
    assert by_id["L1"].terminal_type is None
    assert by_id["L1"].terminal_time is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/observe/test_decision_points.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

`qsim/observe/decision_points.py`:

```python
"""Co-pending lease sets at scheduling decision points (design §2; prereg T3).

Reconstruction only: this module emits RAW decision-point records
(herald instant, herald fidelity, eventual terminal from the trace).
Fidelity projection and the inversion verdict live in qsim.analysis.t3 —
the physics constants come from header.json, which views never read.

Episode segmentation: lease_ids recur across retries (prereg T3 feasibility
note), so each lease.requested opens a fresh INCARNATION of its lease_id and
all herald/terminal state is keyed by (lease_id, incarnation). Envelope seq
orders same-sim-time events; iter_events yields file order, which is seq
order, so replay order is exact.

Pool-sourced heralds (plan finding #4): lease.heralded(source="pool") fires
at WITHDRAWAL time, but the pair's true herald instant is its generation —
the sim_time of pool.deposited(lease_id=<pooled_lease_id>), which is the
herald-resolution instant (engine.py pool.deposited publication).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qsim.observe.work_accounting import iter_events

_TERMINAL_LEASE_EVENTS = frozenset({
    "lease.consumed", "lease.expired", "lease.cancelled", "lease.pool_returned",
})


@dataclass(frozen=True)
class LeaseAtDecision:
    lease_id: str
    incarnation: int
    heralded_at: float
    fidelity_at_herald: float
    terminal_type: str | None
    terminal_time: float | None


@dataclass(frozen=True)
class DecisionPoint:
    sim_time: float
    consumed_lease_id: str
    co_pending: tuple[LeaseAtDecision, ...]


def t3_decision_points(events_path: Path) -> list[DecisionPoint]:
    records = list(iter_events(events_path))

    # Pass 1: index deposits, incarnations, heralds, first terminals.
    deposit_time: dict[str, float] = {}
    incarnation: dict[str, int] = {}
    herald: dict[tuple[str, int], tuple[float, float]] = {}
    terminal: dict[tuple[str, int], tuple[str, float]] = {}
    incarnation_of_event: list[int | None] = []
    for record in records:
        event_type = record["event_type"]
        lease_id = record["entity_id"]
        if event_type == "pool.deposited":
            deposit_time[record["payload"]["lease_id"]] = record["sim_time"]
        if event_type == "lease.requested":
            incarnation[lease_id] = incarnation.get(lease_id, 0) + 1
        if event_type == "lease.heralded":
            inc = incarnation.get(lease_id, 1)
            payload = record["payload"]
            if payload.get("source") == "pool":
                heralded_at = deposit_time.get(
                    payload["pooled_lease_id"], record["sim_time"])
            else:
                heralded_at = record["sim_time"]
            herald[(lease_id, inc)] = (heralded_at, payload["fidelity_at_herald"])
        if event_type in _TERMINAL_LEASE_EVENTS:
            key = (lease_id, incarnation.get(lease_id, 1))
            terminal.setdefault(key, (event_type, record["sim_time"]))
        incarnation_of_event.append(incarnation.get(lease_id))

    # Pass 2: replay live-heralded set; snapshot at each lease.consumed.
    def _lease_record(key: tuple[str, int]) -> LeaseAtDecision:
        heralded_at, fidelity = herald[key]
        term = terminal.get(key)
        return LeaseAtDecision(
            lease_id=key[0], incarnation=key[1],
            heralded_at=heralded_at, fidelity_at_herald=fidelity,
            terminal_type=term[0] if term else None,
            terminal_time=term[1] if term else None,
        )

    live: set[tuple[str, int]] = set()
    points: list[DecisionPoint] = []
    for i, record in enumerate(records):
        event_type = record["event_type"]
        lease_id = record["entity_id"]
        inc = incarnation_of_event[i]
        if inc is None:
            continue
        key = (lease_id, inc)
        if event_type == "lease.heralded" and key in herald:
            live.add(key)
        if event_type == "lease.consumed" and key in live:
            points.append(DecisionPoint(
                sim_time=record["sim_time"],
                consumed_lease_id=lease_id,
                co_pending=tuple(sorted(
                    (_lease_record(k) for k in live),
                    key=lambda l: (l.lease_id, l.incarnation))),
            ))
        if event_type in _TERMINAL_LEASE_EVENTS:
            live.discard(key)
    return points
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/observe/test_decision_points.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/observe/decision_points.py tests/observe/test_decision_points.py
git commit -m "qsim: T3 decision-point reconstruction (incarnation-segmented co-pending sets)"
```

---

### Task 6: `analysis/attribution.py`

**Files:**
- Create: `qsim/analysis/attribution.py`
- Test: `tests/analysis/test_attribution.py`

**Interfaces:**
- Consumes: `numerics.mean`, `numerics.percentile`.
- Produces: `predicted_cycles_t1(latency_samples: list[float], inter_withdrawals_by_key: dict, retry_samples: list[float], low_water_mark: int) -> dict[str, float]` (cycle name → seconds; empty inputs skipped; low-water keys named `"low_water_oscillation:<key>"` with `key` stringified via `str()`); `predicted_cycles_t2(decoder_service_rate: float, decoder_arrival_rate: float) -> tuple[dict[str, float], list[str]]` (cycles, refusals — busy-period dropped with a refusal string when utilization ≥ 1); `to_lag_bins(cycles_s: dict[str, float], bin_s: float) -> dict[str, int]` (round(seconds/bin_s), floor 1); `assign(significant_lags: list[int], predicted_bins: dict[str, int], tolerance: int = 1) -> dict` returning `{"assigned": {lag: [cycle names]}, "unattributed": [lags]}`.

- [ ] **Step 1: Write the failing test**

```python
"""Predicted-lag derivation + one-bin assignment (design §3; prereg
attribution rule: write-then-look, tolerance one bin)."""
import pytest

from qsim.analysis.attribution import (
    assign,
    predicted_cycles_t1,
    predicted_cycles_t2,
    to_lag_bins,
)


def test_t1_cycles_from_measured_distributions():
    cycles = predicted_cycles_t1(
        latency_samples=[0.3, 0.4, 0.5],
        inter_withdrawals_by_key={"A": [1.0, 2.0]},
        retry_samples=[1.0],
        low_water_mark=2,
    )
    assert cycles["replenishment_cycle"] == pytest.approx(0.4)   # median
    assert cycles["low_water_oscillation:A"] == pytest.approx(3.0)  # mean x L
    assert cycles["retry_cadence"] == pytest.approx(1.0)


def test_t1_cycles_skip_empty_inputs():
    cycles = predicted_cycles_t1([0.1], {}, [], low_water_mark=2)
    assert set(cycles) == {"replenishment_cycle"}


def test_t2_cycles_and_busy_period_refusal():
    cycles, refusals = predicted_cycles_t2(decoder_service_rate=5.0,
                                           decoder_arrival_rate=1.0)
    assert cycles["decoder_service_time"] == pytest.approx(0.2)
    assert cycles["busy_period_relaxation"] == pytest.approx(0.25)  # 1/(5-1)
    assert refusals == []
    cycles, refusals = predicted_cycles_t2(decoder_service_rate=5.0,
                                           decoder_arrival_rate=6.0)
    assert "busy_period_relaxation" not in cycles
    assert len(refusals) == 1 and "utilization" in refusals[0]


def test_to_lag_bins_rounds_with_floor_one():
    bins = to_lag_bins({"a": 0.4, "b": 3.0, "c": 0.01}, bin_s=0.5)
    assert bins == {"a": 1, "b": 6, "c": 1}


def test_assign_within_one_bin_tolerance():
    result = assign([1, 2, 6, 9], {"repl": 1, "lw": 6, "retry": 2})
    assert result["assigned"][1] == ["repl", "retry"]
    assert result["assigned"][2] == ["repl", "retry"]
    assert result["assigned"][6] == ["lw"]
    assert result["unattributed"] == [9]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_attribution.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

`qsim/analysis/attribution.py`:

```python
"""Predicted-lag derivation per named mechanism cycle (design §3; prereg
attribution rule). Predictions are derived from events that are NOT the
ACF; the caller writes them to the write-once artifact BEFORE any ACF is
computed (write-then-look, design §4.3)."""
from __future__ import annotations

from qsim.analysis import numerics


def predicted_cycles_t1(latency_samples: list[float],
                        inter_withdrawals_by_key: dict,
                        retry_samples: list[float],
                        low_water_mark: int) -> dict[str, float]:
    """T1's named cycles (prereg attribution amendment): (i) replenishment
    cycle = median replenish latency; (ii) low-water oscillation per pool =
    mean inter-withdrawal time x L; (iii) retry cadence = median retry
    lineage cycle, where retries are active. Empty inputs are skipped —
    a cycle that cannot be estimated is not silently zero."""
    cycles: dict[str, float] = {}
    if latency_samples:
        cycles["replenishment_cycle"] = numerics.percentile(latency_samples, 50)
    for key, gaps in inter_withdrawals_by_key.items():
        if gaps:
            cycles[f"low_water_oscillation:{key}"] = numerics.mean(gaps) * low_water_mark
    if retry_samples:
        cycles["retry_cadence"] = numerics.percentile(retry_samples, 50)
    return cycles


def predicted_cycles_t2(decoder_service_rate: float,
                        decoder_arrival_rate: float) -> tuple[dict[str, float], list[str]]:
    """T2's named cycles (prereg): decoder service time 1/mu; M/M/1
    busy-period relaxation 1/(mu - lambda) at the operating point's
    utilization. Utilization >= 1 makes the relaxation undefined — recorded
    as a refusal string, not silently dropped (design §10)."""
    cycles: dict[str, float] = {}
    refusals: list[str] = []
    cycles["decoder_service_time"] = 1.0 / decoder_service_rate
    utilization = decoder_arrival_rate / decoder_service_rate
    if utilization < 1.0:
        cycles["busy_period_relaxation"] = 1.0 / (decoder_service_rate - decoder_arrival_rate)
    else:
        refusals.append(
            f"busy_period_relaxation undefined: utilization {utilization:.3f} >= 1"
        )
    return cycles, refusals


def to_lag_bins(cycles_s: dict[str, float], bin_s: float) -> dict[str, int]:
    """Cycle seconds → lag bins, floor 1 (lag 0 is not an ACF lag)."""
    return {name: max(1, round(seconds / bin_s)) for name, seconds in cycles_s.items()}


def assign(significant_lags: list[int], predicted_bins: dict[str, int],
           tolerance: int = 1) -> dict:
    """Assign each significant lag to every named cycle within `tolerance`
    bins (prereg: one bin). Lags no cycle predicts land in `unattributed` —
    the ATTRIBUTION-FAILED trigger."""
    assigned: dict[int, list[str]] = {}
    unattributed: list[int] = []
    for lag in significant_lags:
        names = sorted(name for name, b in predicted_bins.items()
                       if abs(lag - b) <= tolerance)
        if names:
            assigned[lag] = names
        else:
            unattributed.append(lag)
    return {"assigned": assigned, "unattributed": unattributed}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_attribution.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/attribution.py tests/analysis/test_attribution.py
git commit -m "qsim: attribution — named-cycle predicted lags + one-bin assignment"
```

---

### Task 7: `analysis/artifacts.py`

**Files:**
- Create: `qsim/analysis/artifacts.py`
- Test: `tests/analysis/test_artifacts.py`

**Interfaces:**
- Produces: `STAMPED_COMMIT = "06b0bd4feb0ca97d5b8f0245b8cbdf5bda10721d"` (the prereg stamp, design §9); `analysis_dir(run_dir: Path) -> Path` (creates `<run_dir>/analysis/`); `write_once(path: Path, payload: dict) -> tuple[dict, bool]` — writes JSON if absent, else returns existing content verbatim; second element True when reused; `sha256_of(path: Path) -> str`; `ancestry(run_git_sha: str) -> dict` — best-effort `git merge-base --is-ancestor STAMPED_COMMIT <sha>`: `{"stamped_commit", "run_git_sha", "is_descendant": True|False|None, "note"}` (None + note when git is unavailable or the sha is unknown); `write_report(run_dir: Path, name: str, payload: dict) -> Path` — writes `<run_dir>/analysis/<name>.json`, indent=2, sort_keys.

- [ ] **Step 1: Write the failing test**

```python
"""Write-once gate + provenance (design §4.3, §9)."""
import json
import subprocess

from qsim.analysis.artifacts import (
    STAMPED_COMMIT,
    ancestry,
    analysis_dir,
    sha256_of,
    write_once,
    write_report,
)


def test_write_once_first_write_lands(tmp_path):
    path = tmp_path / "predicted_lags_t1.json"
    content, reused = write_once(path, {"a": 1})
    assert content == {"a": 1}
    assert reused is False
    assert json.loads(path.read_text()) == {"a": 1}


def test_write_once_never_rewrites(tmp_path):
    path = tmp_path / "predicted_lags_t1.json"
    write_once(path, {"a": 1})
    content, reused = write_once(path, {"a": 2})
    assert content == {"a": 1}  # original, verbatim
    assert reused is True
    assert json.loads(path.read_text()) == {"a": 1}


def test_sha256_is_stable_over_bytes(tmp_path):
    p = tmp_path / "f.json"
    p.write_text('{"a": 1}')
    assert sha256_of(p) == sha256_of(p)
    q = tmp_path / "g.json"
    q.write_text('{"a": 2}')
    assert sha256_of(p) != sha256_of(q)


def test_ancestry_head_is_descendant_of_stamp():
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    result = ancestry(head)
    assert result["stamped_commit"] == STAMPED_COMMIT
    assert result["is_descendant"] is True


def test_ancestry_unknown_sha_is_recorded_not_raised():
    result = ancestry("0" * 40)
    assert result["is_descendant"] in (False, None)
    assert "note" in result


def test_write_report_creates_analysis_dir(tmp_path):
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    path = write_report(run_dir, "t1_report", {"verdict": "X"})
    assert path == run_dir / "analysis" / "t1_report.json"
    assert json.loads(path.read_text())["verdict"] == "X"
    assert analysis_dir(run_dir).is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_artifacts.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

`qsim/analysis/artifacts.py`:

```python
"""Write-once gate, provenance, and report writing (design §4.3, §9).

The write-once predicted-lags file is the honesty mechanism: re-running an
analysis can never re-derive predictions after the ACF has been seen;
deleting the file leaves a hole the git/OTS discipline makes visible.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

# The prereg's OTS-stamped commit (docs/superpowers/specs/
# 2026-07-06-field-battery-prereg.md). Every presentable result must come
# from a run whose header git SHA is a descendant of this commit.
STAMPED_COMMIT = "06b0bd4feb0ca97d5b8f0245b8cbdf5bda10721d"


def analysis_dir(run_dir: Path) -> Path:
    d = Path(run_dir) / "analysis"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_once(path: Path, payload: dict) -> tuple[dict, bool]:
    """Write payload as JSON iff `path` does not exist; otherwise return the
    existing content VERBATIM and never rewrite (design §4.3)."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text()), True
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload, False


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ancestry(run_git_sha: str) -> dict:
    """Best-effort forward-provability check (design §9): is the run's git
    SHA a descendant of the stamped commit? Recorded either way; git being
    unavailable is a note, never a crash."""
    result = {"stamped_commit": STAMPED_COMMIT, "run_git_sha": run_git_sha}
    try:
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", STAMPED_COMMIT, run_git_sha],
            capture_output=True, text=True,
        )
    except OSError as exc:
        result["is_descendant"] = None
        result["note"] = f"git unavailable: {exc}"
        return result
    if proc.returncode == 0:
        result["is_descendant"] = True
        result["note"] = "run sha is a descendant of the stamped commit"
    elif proc.returncode == 1:
        result["is_descendant"] = False
        result["note"] = "run sha is NOT a descendant of the stamped commit"
    else:
        result["is_descendant"] = None
        result["note"] = f"ancestry undecidable: {proc.stderr.strip()}"
    return result


def write_report(run_dir: Path, name: str, payload: dict) -> Path:
    """Write `<run_dir>/analysis/<name>.json` — the JSON artifact is the
    record; stdout summaries are a courtesy (design §9)."""
    path = analysis_dir(run_dir) / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_artifacts.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/artifacts.py tests/analysis/test_artifacts.py
git commit -m "qsim: analysis artifacts — write-once gate, sha256, stamped-commit ancestry"
```

---

### Task 8: `analysis/t1.py` — shared pipeline + control verdict

**Files:**
- Create: `qsim/analysis/t1.py`
- Test: `tests/analysis/test_t1_control.py`

**Interfaces:**
- Consumes: everything from Tasks 1–7; `qsim.observe.views.{pool_flux_series, pool_depth_series, replenishment_latency_samples, inter_withdrawal_times, retry_cadence_samples}`.
- Produces:

```python
class AnalysisRefusal(Exception): ...   # report already written when raised

def choose_bin_s(latency_samples: list[float], override: float | None = None) -> float
    # median latency rounded to ONE significant figure (reproduces prereg's 0.1 s
    # control bin from its 0.1 s-dominated latency); disclosed convention.
def lag_window(latency_samples: list[float], bin_s: float,
               lo_q: float = 25, hi_q: float = 75) -> tuple[int, int]
    # [max(1, floor(p_lo/bin_s)), ceil(p_hi/bin_s)], hi extended until width >= 3 bins.
def analyze_t1(run_dir: Path, mode: str, companion_dir: Path | None = None,
               bin_s_override: float | None = None, surrogate_seed: int = 0,
               n_shuffles: int = 1000) -> dict
    # mode "control" in this task; "open" completed in Task 9.
```

- Pipeline order (design §4, strict): steady-state gate → latency/lag window → **write-once predictions** → ACF/bands → attribution → report. Warmup trim per finding #6. Verdicts this task: `"TRANSIENT"`, `"PASS"`, `"INSENSITIVE"` (with `report["directive"] = "do not run the open regime"`).
- Control PASS (prereg verbatim): EVERY tracked pool shows ≥1 significant in-window lag (|ACF| > white-noise band AND outside the surrogate 95% band) AND ≥1 such lag within ±1 bin of the replenishment-cycle predicted lag with negative sign. A pool refusal (zero variance / too few bins) → INSENSITIVE with the refusal recorded.
- Report (`t1_report.json` in the analyzed run dir) embeds: full ACF curve + both bands per pool, window + `[p10,p90]` sensitivity sets, `expected_false_exceedances = 0.05 × window_width`, every criterion component, operating point (header `config`) + `git_sha` + `ancestry(...)`, `predicted_lags_sha256`, surrogate seed, refusals, warmup-trim + bin-rule disclosures.
- Write-once reuse: if `predicted_lags_t1.json` exists, its content is used verbatim (including its `bin_s`); a `"reused": true` note plus any mismatch with freshly derived values goes in the report.

- [ ] **Step 1: Write the failing test**

```python
"""T1 control pipeline on synthetic run dirs with engineered ACF ground
truth (design §4, §6, §11)."""
import json

import pytest

from qsim.analysis.t1 import AnalysisRefusal, analyze_t1, choose_bin_s, lag_window

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]
PATH_A = [["M0", 0], ["M1", 0]]


def _write_run_dir(tmp_path, rows, steady_status="CONVERGED", warmup=0.0):
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 7, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": steady_status, "warmup_cutoff_s": warmup,
                          "evidence": {"horizon_s": 80.0}},
        "config": {"pregen_low_water_mark": 2, "arrival_rate_hz": 5.0,
                    "scheduler": "S1", "epoch": {"decoder_service_rate": 1000.0,
                                                  "decay_rate_per_class": {"messenger": 0.0}}},
    }))
    return run_dir


def _loud_rows(n=100):
    """Deposit in even 0.4s bins, withdraw in odd bins: flux alternates
    +/-, lag-1 ACF ~ -1, replenishment latency exactly 0.4 -> bin 0.4,
    replenishment predicted lag 1, in window, negative. Control PASS."""
    rows = []
    for i in range(n):
        base = 0.8 * i
        rows.append((base - 0.2 if i else 0.0, "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((base + 0.2, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": 1, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
        rows.append((base + 0.6, "pool.withdrawn", f"R{i}:L",
                     {"key": KEY_A, "depth": 0, "pooled_lease_id": f"R{i}:L",
                      "lease_id": f"L{i}", "round_id": f"r{i}"}))
    return sorted(rows, key=lambda r: r[0])


def test_choose_bin_s_one_significant_figure():
    assert choose_bin_s([0.09, 0.11, 0.12]) == pytest.approx(0.1)
    assert choose_bin_s([2.0, 2.6]) == pytest.approx(2.0)
    assert choose_bin_s([0.5], override=0.25) == 0.25


def test_lag_window_covers_p25_p75_min_three_bins():
    assert lag_window([0.4] * 10, bin_s=0.4) == (1, 3)      # widened to 3
    assert lag_window([1.0, 2.0, 3.0, 4.0], bin_s=0.5) == (3, 7)


def test_divergent_run_is_transient_and_unread(tmp_path):
    run_dir = _write_run_dir(tmp_path, _loud_rows(), steady_status="DIVERGENT")
    report = analyze_t1(run_dir, mode="control")
    assert report["verdict"] == "TRANSIENT"
    assert "pools" not in report  # a transient is not read


def test_control_pass_on_loud_structure(tmp_path):
    run_dir = _write_run_dir(tmp_path, _loud_rows())
    report = analyze_t1(run_dir, mode="control")
    assert report["verdict"] == "PASS"
    assert (run_dir / "analysis" / "predicted_lags_t1.json").exists()
    assert (run_dir / "analysis" / "t1_report.json").exists()
    (pool_stats,) = report["pools"].values()
    assert 1 in pool_stats["significant_in_window"]
    assert pool_stats["acf"][0] < 0


def test_control_insensitive_on_flat_series(tmp_path):
    """Deposits only, perfectly regular: constant flux -> zero variance ->
    per-pool refusal -> INSENSITIVE (refusals are data, design §10)."""
    rows = []
    for i in range(200):
        # deposit at bin CENTER (i*0.4 + 0.2): exactly one deposit per 0.4s
        # bin, so the flux series is truly constant (zero variance) — a
        # deposit on a bin EDGE would leave an empty first bin and give the
        # series spurious variance.
        rows.append((max(0.0, i * 0.4 - 0.2), "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((i * 0.4 + 0.2, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": i, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
    run_dir = _write_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]))
    report = analyze_t1(run_dir, mode="control")
    assert report["verdict"] == "INSENSITIVE"
    assert report["directive"] == "do not run the open regime"
    assert report["refusals"]


def test_no_replenishment_samples_is_hard_refusal(tmp_path):
    rows = [(0.5, "pool.deposited", "X", {"key": KEY_A, "depth": 1,
             "lease_id": "X", "round_id": "r0", "source": "round_return"})]
    run_dir = _write_run_dir(tmp_path, rows)
    with pytest.raises(AnalysisRefusal):
        analyze_t1(run_dir, mode="control")
    report = json.loads((run_dir / "analysis" / "t1_report.json").read_text())
    assert report["verdict"] is None
    assert report["refusals"]  # recorded in the artifact, not just stderr


def test_write_once_predictions_survive_rerun(tmp_path):
    run_dir = _write_run_dir(tmp_path, _loud_rows())
    analyze_t1(run_dir, mode="control")
    first = (run_dir / "analysis" / "predicted_lags_t1.json").read_text()
    report = analyze_t1(run_dir, mode="control")
    assert (run_dir / "analysis" / "predicted_lags_t1.json").read_text() == first
    assert report["predicted_lags_reused"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_t1_control.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

`qsim/analysis/t1.py`:

```python
"""T1 verdict assembly (design §4–§7; prereg T1 + amendments).

Strict pipeline order (design §4): steady-state gate -> lag window from
non-ACF events -> WRITE-ONCE predicted lags -> ACF + bands -> attribution
-> report. The JSON artifact is the record; stdout is a courtesy.
"""
from __future__ import annotations

import math
from pathlib import Path

from qsim.analysis import numerics
from qsim.analysis.artifacts import (
    analysis_dir,
    ancestry,
    sha256_of,
    write_once,
    write_report,
)
from qsim.analysis.attribution import assign, predicted_cycles_t1, to_lag_bins
from qsim.analysis.surrogates import permutation_band
from qsim.observe.views import (
    inter_withdrawal_times,
    pool_depth_series,
    pool_flux_series,
    replenishment_latency_samples,
    retry_cadence_samples,
)


class AnalysisRefusal(Exception):
    """Raised after the refusal has been recorded in the report artifact."""


# Prereg, verbatim (T1 precommitted readings): the transfer caveat that
# rides every FIELD-EARNED verdict.
ATTRIBUTION_CAVEAT = (
    "Structure present under (P) -> field-earned at this operating point; "
    "transfers as Simmons Q4 (subject to the attribution requirement)."
)
# Standing flat-sweep lesson (design §7): no threshold is pinned for
# "visibly moved", so the knob-motion comparison emits statistics only.
FLAT_SWEEP_CAVEAT = (
    "A flat result reads as 'no effect' when it may be 'effect masked by a "
    "bad operating point'. The knob-motion companion statistics are reported "
    "side-by-side; the prereg pins no threshold for 'visibly moved', so no "
    "verdict word attaches to the comparison itself."
)
MECHANISM_PROBE_NOTE = (
    "Transfer blocked: mandatory adversarial mechanism probe before any "
    "interpretation (the 75206ce serialization-bug playbook)."
)


def choose_bin_s(latency_samples: list[float], override: float | None = None) -> float:
    """Disclosed convention (design §4.2): bin at the measured replenishment
    latency's scale — median rounded to one significant figure. Reproduces
    the prereg's 0.1 s control bin from its reconfig-dominated latency."""
    if override is not None:
        return override
    med = numerics.percentile(latency_samples, 50)
    if med <= 0:
        raise ValueError("non-positive median replenishment latency")
    exponent = math.floor(math.log10(med))
    return round(med, -exponent)


def lag_window(latency_samples: list[float], bin_s: float,
               lo_q: float = 25, hi_q: float = 75) -> tuple[int, int]:
    """Disclosed convention (design §5): bins covering [p25, p75] of the
    latency distribution, minimum width 3 bins, minimum lag 1. The 3-bin
    floor exists because a one-bin window hinges on bin phase alignment."""
    lo = max(1, math.floor(numerics.percentile(latency_samples, lo_q) / bin_s))
    hi = max(lo, math.ceil(numerics.percentile(latency_samples, hi_q) / bin_s))
    while hi - lo + 1 < 3:
        hi += 1
    return lo, hi


def _load_header(run_dir: Path) -> dict:
    import json
    return json.loads((Path(run_dir) / "header.json").read_text())


def _trim_warmup(bins: list[float], bin_s: float, warmup_cutoff_s: float) -> list[float]:
    return bins[math.ceil(warmup_cutoff_s / bin_s):]


def _series_stats(bins: list[float], window: tuple[int, int],
                  sensitivity_window: tuple[int, int],
                  surrogate_seed: int, n_shuffles: int) -> dict:
    """Full-curve statistics for one pool's flux series. Refusals come back
    as {'refusal': msg} — the caller records them, never invents a verdict."""
    n = len(bins)
    max_lag = numerics.max_estimable_lag(n)
    if max_lag < 1:
        return {"refusal": f"insufficient data: {n} bins post-warmup"}
    try:
        r = numerics.acf(bins, max_lag)
    except ValueError as exc:
        return {"refusal": str(exc)}
    band = numerics.white_noise_band(n)
    surrogate = permutation_band(bins, max_lag, n_shuffles=n_shuffles,
                                 seed=surrogate_seed)
    significant = [
        k for k in range(1, max_lag + 1)
        if abs(r[k - 1]) > band
        and (r[k - 1] < surrogate[k - 1][0] or r[k - 1] > surrogate[k - 1][1])
    ]
    lo, hi = window
    slo, shi = sensitivity_window
    return {
        "n_bins": n,
        "max_lag": max_lag,
        "acf": r,
        "white_noise_band": band,
        "surrogate_band": surrogate,
        "significant_lags": significant,
        "significant_in_window": [k for k in significant if lo <= k <= hi],
        "significant_in_sensitivity_window": [k for k in significant
                                              if slo <= k <= shi],
        "expected_false_exceedances": 0.05 * (hi - lo + 1),
    }


def analyze_t1(run_dir: Path, mode: str, companion_dir: Path | None = None,
               bin_s_override: float | None = None, surrogate_seed: int = 0,
               n_shuffles: int = 1000) -> dict:
    if mode not in ("control", "open"):
        raise ValueError(f"mode must be 'control' or 'open', got {mode!r}")
    run_dir = Path(run_dir)
    events = run_dir / "events.jsonl"
    header = _load_header(run_dir)
    report: dict = {
        "test": "t1", "mode": mode, "verdict": None, "refusals": [],
        "operating_point": header.get("config"),
        "git_sha": header.get("git_sha"),
        "ancestry": ancestry(header.get("git_sha", "")),
        "surrogate_seed": surrogate_seed,
        "conventions": {
            "bin_rule": "median replenishment latency, one significant figure",
            "window_rule": "[p25,p75] of replenishment latency, min 3 bins, min lag 1",
            "warmup_trim": "bins starting before header steady_state.warmup_cutoff_s dropped",
            "max_lag_rule": "floor(n_bins/4)",
        },
    }

    # 1. Steady-state gate (design §4.1): a transient is not read.
    steady = header.get("steady_state", {})
    report["steady_state"] = steady
    if steady.get("status") == "DIVERGENT":
        report["verdict"] = "TRANSIENT"
        report["refusals"].append("steady-state DIVERGENT: verdict withheld")
        write_report(run_dir, "t1_report", report)
        return report

    # 2. Lag window from non-ACF events (design §4.2).
    latency = replenishment_latency_samples(events)
    report["n_latency_samples"] = len(latency)
    if not latency:
        report["refusals"].append(
            "no replenishment-latency samples: lag window undefined (design §10)")
        write_report(run_dir, "t1_report", report)
        raise AnalysisRefusal(report["refusals"][-1])
    bin_s = choose_bin_s(latency, bin_s_override)
    window = lag_window(latency, bin_s)
    sensitivity_window = lag_window(latency, bin_s, lo_q=10, hi_q=90)

    # 3. Predicted lags, WRITE-ONCE, before any ACF (design §4.3).
    cycles = predicted_cycles_t1(
        latency,
        {str(k): v for k, v in inter_withdrawal_times(events).items()},
        retry_cadence_samples(events),
        low_water_mark=header["config"].get("pregen_low_water_mark") or 1,
    )
    predictions = {
        "bin_s": bin_s, "window": list(window),
        "sensitivity_window": list(sensitivity_window),
        "cycles_s": cycles, "lag_bins": to_lag_bins(cycles, bin_s),
        "run_id": header.get("run_id"),
    }
    lags_path = analysis_dir(run_dir) / "predicted_lags_t1.json"
    committed, reused = write_once(lags_path, predictions)
    report["predicted_lags"] = committed
    report["predicted_lags_reused"] = reused
    report["predicted_lags_sha256"] = sha256_of(lags_path)
    if reused and committed != predictions:
        report["refusals"].append(
            "predicted_lags_t1.json reused verbatim; freshly derived values "
            "differ and are DISCARDED (write-once, design §4.3)")
    bin_s = committed["bin_s"]
    window = tuple(committed["window"])
    sensitivity_window = tuple(committed["sensitivity_window"])
    predicted_bins = committed["lag_bins"]
    report["bin_s"] = bin_s
    report["window"] = list(window)

    # 4. Statistics: full curve, all estimable lags (design §4.4).
    warmup = steady.get("warmup_cutoff_s", 0.0)
    flux = pool_flux_series(events, bin_s)
    if not flux:
        report["refusals"].append("no pool events: flux series empty")
        write_report(run_dir, "t1_report", report)
        raise AnalysisRefusal(report["refusals"][-1])
    pools = {}
    for key, bins in sorted(flux.items(), key=lambda kv: str(kv[0])):
        trimmed = _trim_warmup(bins, bin_s, warmup)
        stats = _series_stats(trimmed, window, sensitivity_window,
                              surrogate_seed, n_shuffles)
        if "refusal" in stats:
            report["refusals"].append(f"pool {key}: {stats['refusal']}")
        pools[str(key)] = stats
    report["pools"] = pools

    # 5.-6. Attribution + verdict (design §6).
    repl_lag = predicted_bins.get("replenishment_cycle")
    if mode == "control":
        ok = bool(pools)
        for stats in pools.values():
            if "refusal" in stats:
                ok = False
                continue
            in_window = stats["significant_in_window"]
            negative_at_repl = repl_lag is not None and any(
                abs(k - repl_lag) <= 1 and stats["acf"][k - 1] < 0
                for k in in_window)
            stats["negative_at_replenishment_lag"] = negative_at_repl
            if not in_window or not negative_at_repl:
                ok = False
        report["verdict"] = "PASS" if ok else "INSENSITIVE"
        if not ok:
            report["directive"] = "do not run the open regime"
    else:
        _open_verdict(report, pools, predicted_bins, run_dir, companion_dir,
                      bin_s, surrogate_seed)

    write_report(run_dir, "t1_report", report)
    return report


def _open_verdict(report, pools, predicted_bins, run_dir, companion_dir,
                  bin_s, surrogate_seed) -> None:
    """Completed in the next task (open regime + knob-motion companion)."""
    raise NotImplementedError("open mode lands in Task 9")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_t1_control.py tests/analysis -v`
Expected: all PASS (control tests; open mode untested until Task 9)

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/t1.py tests/analysis/test_t1_control.py
git commit -m "qsim: T1 pipeline — steady gate, write-once predictions, control verdict"
```

---

### Task 9: T1 open regime + knob-motion companion + companion config

**Files:**
- Modify: `qsim/analysis/t1.py` (replace `_open_verdict` stub)
- Create: `examples/t1-open-companion.toml`
- Test: `tests/analysis/test_t1_open.py`

**Interfaces:**
- Consumes: Task 8's pipeline; `pool_depth_series`, `pool_flux_series`, `numerics.mean`.
- Produces: open-mode verdicts `"FIELD-EARNED"` (+ `ATTRIBUTION_CAVEAT`), `"ATTRIBUTION-FAILED"` (+ `MECHANISM_PROBE_NOTE`), `"FIELD-BLOCKED"` (+ `FLAT_SWEEP_CAVEAT`); `report["knob_motion"]` — per-run (primary/companion), per-pool-key: `{"mean_depth", "flux_variance", "n_depth_events"}` side-by-side, statistics only, no verdict word (design §7). Open mode without a companion dir → recorded refusal + `AnalysisRefusal` (the protocol is two runs; no PROVISIONAL state exists).

- [ ] **Step 1: Write the failing test**

```python
"""T1 open regime: attribution-gated verdicts + knob-motion companion
(design §6-§7)."""
import json

import pytest

from qsim.analysis.t1 import AnalysisRefusal, analyze_t1

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]
PATH_A = [["M0", 0], ["M1", 0]]


def _write_run_dir(tmp_path, name, rows, warmup=0.0):
    run_dir = tmp_path / name
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": name, "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": name, "run_seed": 11, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": warmup,
                          "evidence": {"horizon_s": 80.0}},
        "config": {"pregen_low_water_mark": 2, "arrival_rate_hz": 1.0,
                    "scheduler": "S1", "epoch": {"decoder_service_rate": 5.0,
                                                  "decay_rate_per_class": {"messenger": 0.01}}},
    }))
    return run_dir


def _periodic_rows(n, period_s, deposit_offset, withdraw_offset, latency=0.4):
    rows = []
    for i in range(n):
        base = period_s * i
        rows.append((max(0.0, base + deposit_offset - latency),
                     "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((base + deposit_offset, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": 1, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
        rows.append((base + withdraw_offset, "pool.withdrawn", f"R{i}:L",
                     {"key": KEY_A, "depth": 0, "pooled_lease_id": f"R{i}:L",
                      "lease_id": f"L{i}", "round_id": f"r{i}"}))
    return sorted(rows, key=lambda r: r[0])


def test_open_requires_companion(tmp_path):
    primary = _write_run_dir(tmp_path, "primary",
                             _periodic_rows(100, 0.8, 0.2, 0.6))
    with pytest.raises(AnalysisRefusal):
        analyze_t1(primary, mode="open")
    report = json.loads((primary / "analysis" / "t1_report.json").read_text())
    assert any("companion" in r for r in report["refusals"])


def test_open_field_earned_when_all_lags_attributed(tmp_path):
    # lag-1 structure; replenishment cycle 0.4s / bin 0.4 -> predicted lag 1.
    primary = _write_run_dir(tmp_path, "primary",
                             _periodic_rows(100, 0.8, 0.2, 0.6))
    companion = _write_run_dir(tmp_path, "companion",
                               _periodic_rows(50, 1.6, 0.2, 0.6))
    report = analyze_t1(primary, mode="open", companion_dir=companion)
    assert report["verdict"] == "FIELD-EARNED"
    assert "field-earned at this operating point" in report["caveat"]
    assert "knob_motion" in report
    km = report["knob_motion"]
    assert set(km) == {"primary", "companion"}
    (primary_stats,) = km["primary"].values()
    assert {"mean_depth", "flux_variance", "n_depth_events"} <= set(primary_stats)


def test_open_attribution_failed_on_unpredicted_lag(tmp_path):
    # Period 6 bins (2.4s): significant lag 3 in window [1,3]; predicted
    # cycles: replenishment=1, low-water = mean gap 2.4 x 2 = 4.8s -> lag 12.
    # Lag 3 is >1 bin from both -> ATTRIBUTION-FAILED.
    primary = _write_run_dir(tmp_path, "primary",
                             _periodic_rows(100, 2.4, 0.2, 1.4))
    companion = _write_run_dir(tmp_path, "companion",
                               _periodic_rows(50, 2.4, 0.2, 1.4))
    report = analyze_t1(primary, mode="open", companion_dir=companion)
    assert report["verdict"] == "ATTRIBUTION-FAILED"
    assert "mechanism probe" in report["caveat"]
    assert report["unattributed_lags"]


def test_open_field_blocked_carries_flat_sweep_caveat(tmp_path):
    """No temporal structure: deposits at seeded-uniform times (white flux).
    If this seed flukes a significant in-window lag, bump the seed and note
    it here — the test needs a WHITE series, the seed is test data."""
    import random
    rng = random.Random(5)
    rows = []
    for i, t in enumerate(sorted(rng.uniform(0.5, 80.0) for _ in range(120))):
        rows.append((t - 0.4, "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((t, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": 1, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
    primary = _write_run_dir(tmp_path, "primary", sorted(rows, key=lambda r: r[0]))
    companion = _write_run_dir(tmp_path, "companion", sorted(rows, key=lambda r: r[0]))
    report = analyze_t1(primary, mode="open", companion_dir=companion)
    assert report["verdict"] == "FIELD-BLOCKED"
    assert "flat" in report["caveat"].lower()


def test_companion_config_differs_only_in_arrival_rate():
    from dataclasses import fields
    from qsim.cli import load_config
    open_cfg = load_config("examples/t1-open.toml")
    companion_cfg = load_config("examples/t1-open-companion.toml")
    assert companion_cfg.arrival_rate_hz == 0.5
    for f in fields(open_cfg):
        if f.name == "arrival_rate_hz":
            continue
        assert getattr(open_cfg, f.name) == getattr(companion_cfg, f.name), f.name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_t1_open.py -v`
Expected: FAIL — `NotImplementedError: open mode lands in Task 9` and missing companion TOML

- [ ] **Step 3: Write the implementation**

Replace `_open_verdict` in `qsim/analysis/t1.py`:

```python
def _open_verdict(report, pools, predicted_bins, run_dir, companion_dir,
                  bin_s, surrogate_seed) -> None:
    """Open-regime verdict (design §6) + knob-motion companion (design §7).

    The protocol is TWO runs; no PROVISIONAL state exists. The companion
    comparison emits statistics only — the prereg pins no threshold for
    'visibly moved', so no verdict word attaches to it."""
    if companion_dir is None:
        report["refusals"].append(
            "open mode requires the knob-motion companion run dir "
            "(design §7: the protocol is two runs; no PROVISIONAL state)")
        write_report(run_dir, "t1_report", report)
        raise AnalysisRefusal(report["refusals"][-1])

    report["knob_motion"] = {
        "primary": _knob_motion_stats(run_dir, bin_s),
        "companion": _knob_motion_stats(Path(companion_dir), bin_s),
        "companion_steady_state": _load_header(Path(companion_dir)).get("steady_state"),
    }

    significant, unattributed = [], []
    for stats in pools.values():
        if "refusal" in stats:
            continue
        in_window = stats["significant_in_window"]
        significant.extend(in_window)
        result = assign(in_window, predicted_bins)
        stats["attribution"] = result
        unattributed.extend(result["unattributed"])
    report["unattributed_lags"] = sorted(set(unattributed))

    if not significant:
        report["verdict"] = "FIELD-BLOCKED"
        report["caveat"] = FLAT_SWEEP_CAVEAT
    elif unattributed:
        report["verdict"] = "ATTRIBUTION-FAILED"
        report["caveat"] = MECHANISM_PROBE_NOTE
    else:
        report["verdict"] = "FIELD-EARNED"
        report["caveat"] = ATTRIBUTION_CAVEAT


def _knob_motion_stats(run_dir: Path, bin_s: float) -> dict:
    """Per-pool depth/flux summaries (design §7): exploratory two-point
    dose-response of pool dynamics on load. Statistics only."""
    events = run_dir / "events.jsonl"
    depth = pool_depth_series(events)
    flux = pool_flux_series(events, bin_s)
    out = {}
    for key in sorted(depth, key=str):
        values = [v for _, v in depth[key]]
        bins = flux.get(key, [])
        m = numerics.mean(bins) if bins else 0.0
        out[str(key)] = {
            "mean_depth": numerics.mean([float(v) for v in values]),
            "n_depth_events": len(values),
            "flux_variance": (numerics.mean([(b - m) ** 2 for b in bins])
                               if bins else 0.0),
        }
    return out
```

`examples/t1-open-companion.toml` — byte-identical copy of `examples/t1-open.toml` except the header comment and `arrival_rate_hz`:

```toml
# T1 OPEN knob-motion COMPANION (design §7; prereg standing discipline):
# identical to examples/t1-open.toml except arrival_rate_hz 1.0 -> 0.5 —
# the prereg's own named knob-motion knob. `analyze t1 --mode open` takes
# both run dirs and emits ONE verdict; no PROVISIONAL state exists.
run_seed = 11
scheduler = "S1"
path_policy = "round_robin"
arrival_rate_hz = 0.5
leases_per_round = 1
deadline_slack_s = 5.0
switch_capacity_c = 2
reconfig_delay_s = 0.01
max_sim_time_s = 400.0
admission_theta = 0.5
pregen_low_water_mark = 2
retry_cap = 4

[epoch]
epoch_id = "t1-open"
memory_access_channel_s = 0.001
memory_access_wear_rate = 0.01
round_success_logistic_midpoint = 0.5
round_success_logistic_slope = 10.0
round_success_slack_penalty_per_s = 1.0
decoder_service_rate = 5.0

[epoch.decay_rate_per_class]
messenger = 0.01
memory = 0.001

[[epoch.paths]]
a = "M0:0"
b = "M1:0"
heralding_p = 0.7
heralded_fidelity = 0.95

[[epoch.paths]]
a = "M1:0"
b = "M2:0"
heralding_p = 0.7
heralded_fidelity = 0.95

[[epoch.paths]]
a = "M2:0"
b = "M3:0"
heralding_p = 0.7
heralded_fidelity = 0.95

[[epoch.paths]]
a = "M0:0"
b = "M3:0"
heralding_p = 0.7
heralded_fidelity = 0.95
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/ -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/t1.py examples/t1-open-companion.toml tests/analysis/test_t1_open.py
git commit -m "qsim: T1 open verdicts + knob-motion companion (two-run protocol)"
```

---

### Task 10: `analysis/t2.py`

**Files:**
- Create: `qsim/analysis/t2.py`
- Test: `tests/analysis/test_t2.py`

**Interfaces:**
- Consumes: `backlog_slope_series`, `decoder_backlog_series` (existing view — arrival-rate measurement), `predicted_cycles_t2`, Task 8's `_series_stats`/`_trim_warmup`/`_load_header` (import from `qsim.analysis.t1`).
- Produces: `analyze_t2(run_dir: Path, bin_s_override: float | None = None, surrogate_seed: int = 0, n_shuffles: int = 1000) -> dict`. Verdicts: `"TRANSIENT"`, `"T2-NO-STRUCTURE"`, `"T2-STRUCTURE-ATTRIBUTED"`, `"T2-ATTRIBUTION-FAILED"`. Report `t2_report.json` carries the prereg inheritance note **verbatim**.
- Conventions (finding #7, disclosed in report): bin_s = decoder service time (1/μ, μ from header `config.epoch.decoder_service_rate`) rounded to one significant figure; window = [service-time lag, busy-period-relaxation lag] widened to ≥3 bins, min lag 1 (service lag only, widened, when utilization ≥ 1); λ = count of backlog increments / `steady_state.evidence.horizon_s`. Predictions write-once to `predicted_lags_t2.json` BEFORE ACF.

- [ ] **Step 1: Write the failing test**

```python
"""T2: identical machinery on backlog slope, decoder-side named cycles
(design §4 last para; prereg T2)."""
import json

import pytest

from qsim.analysis.t2 import INHERITANCE_NOTE, analyze_t2


def _write_run_dir(tmp_path, rows, service_rate=5.0, horizon=80.0):
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": f"j{seq}",
                "causal_parent_id": None, "payload": {},
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 1, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": 0.0,
                          "evidence": {"horizon_s": horizon}},
        "config": {"scheduler": "S1",
                    "epoch": {"decoder_service_rate": service_rate}},
    }))
    return run_dir


def test_t2_structure_attributed_at_service_lag(tmp_path):
    # mu=5 -> bin 0.2s. Enqueue in even bins, complete in odd bins:
    # slope alternates -> lag-1 structure; service lag = round(0.2/0.2) = 1.
    rows = []
    for i in range(200):
        rows.append((0.4 * i + 0.1, "decoder.enqueued"))
        rows.append((0.4 * i + 0.3, "decoder.completed"))
    run_dir = _write_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]))
    report = analyze_t2(run_dir)
    assert report["verdict"] == "T2-STRUCTURE-ATTRIBUTED"
    assert report["inheritance_note"] == INHERITANCE_NOTE
    assert (run_dir / "analysis" / "predicted_lags_t2.json").exists()
    assert (run_dir / "analysis" / "t2_report.json").exists()


def test_t2_no_structure_on_constant_slope(tmp_path):
    # One enqueue per bin, never completed: constant slope -> zero variance
    # -> refusal -> T2-NO-STRUCTURE is NOT declared; verdict withheld.
    rows = [(0.2 * i + 0.1, "decoder.enqueued") for i in range(400)]
    run_dir = _write_run_dir(tmp_path, rows)
    report = analyze_t2(run_dir)
    assert report["verdict"] is None
    assert report["refusals"]


def test_t2_empty_series_is_refusal_not_verdict(tmp_path):
    run_dir = _write_run_dir(tmp_path, [(1.0, "round.arrived")])
    report = analyze_t2(run_dir)
    assert report["verdict"] is None
    assert any("insufficient" in r or "empty" in r for r in report["refusals"])


def test_t2_busy_period_refusal_recorded_when_saturated(tmp_path):
    # lambda ~ 10/s vs mu=5 -> utilization >= 1: relaxation cycle refused.
    rows = [(0.1 * i, "decoder.enqueued") for i in range(800)]
    rows += [(0.1 * i + 0.05, "decoder.completed") for i in range(400)]
    run_dir = _write_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]))
    report = analyze_t2(run_dir)
    assert any("utilization" in r for r in report["refusals"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_t2.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

`qsim/analysis/t2.py`:

```python
"""T2 verdict assembly: identical machinery on backlog slope with the
decoder's named cycles (design §4; prereg T2). A T2 result is recorded, not
interpreted against the inheritance question, until T1 runs."""
from __future__ import annotations

import math
from pathlib import Path

from qsim.analysis.artifacts import (
    analysis_dir,
    ancestry,
    sha256_of,
    write_once,
    write_report,
)
from qsim.analysis.attribution import assign, predicted_cycles_t2, to_lag_bins
from qsim.analysis.t1 import _load_header, _series_stats, _trim_warmup
from qsim.observe.views import backlog_slope_series, decoder_backlog_series

# Prereg T2, verbatim.
INHERITANCE_NOTE = (
    "A T2 result obtained before T1 exists is recorded but not interpreted "
    "against the inheritance question until T1 runs. T1 blocked & T2 blocked "
    "-> consistent inheritance. T1 blocked & T2 earned -> independent "
    "classical structure (service dynamics). T1 earned -> decompose "
    "inherited vs. intrinsic structure before crediting T2 independently."
)


def _one_sig_fig(x: float) -> float:
    return round(x, -math.floor(math.log10(x)))


def analyze_t2(run_dir: Path, bin_s_override: float | None = None,
               surrogate_seed: int = 0, n_shuffles: int = 1000) -> dict:
    run_dir = Path(run_dir)
    events = run_dir / "events.jsonl"
    header = _load_header(run_dir)
    steady = header.get("steady_state", {})
    report: dict = {
        "test": "t2", "verdict": None, "refusals": [],
        "operating_point": header.get("config"),
        "git_sha": header.get("git_sha"),
        "ancestry": ancestry(header.get("git_sha", "")),
        "surrogate_seed": surrogate_seed,
        "steady_state": steady,
        "inheritance_note": INHERITANCE_NOTE,
        "conventions": {
            "bin_rule": "decoder service time 1/mu, one significant figure",
            "window_rule": "[service-time lag, busy-period-relaxation lag], "
                           "min 3 bins, min lag 1; service lag only when "
                           "utilization >= 1",
            "arrival_rate_rule": "backlog increments / steady_state horizon",
            "warmup_trim": "bins before steady_state.warmup_cutoff_s dropped",
        },
    }
    if steady.get("status") == "DIVERGENT":
        report["verdict"] = "TRANSIENT"
        report["refusals"].append("steady-state DIVERGENT: verdict withheld")
        write_report(run_dir, "t2_report", report)
        return report

    mu = header["config"]["epoch"]["decoder_service_rate"]
    backlog = decoder_backlog_series(events)
    horizon = steady.get("evidence", {}).get("horizon_s") or (
        backlog[-1][0] if backlog else 0.0)
    n_enqueued = 0
    prev = 0
    for _, level in backlog:
        if level > prev:
            n_enqueued += 1
        prev = level
    lam = n_enqueued / horizon if horizon > 0 else 0.0
    report["measured_arrival_rate_hz"] = lam
    report["decoder_service_rate_hz"] = mu

    cycles, cycle_refusals = predicted_cycles_t2(mu, lam)
    report["refusals"].extend(cycle_refusals)
    bin_s = bin_s_override if bin_s_override is not None else _one_sig_fig(1.0 / mu)
    lag_bins = to_lag_bins(cycles, bin_s)
    lo = lag_bins["decoder_service_time"]
    hi = max(lag_bins.values())
    while hi - lo + 1 < 3:
        hi += 1
    window = (lo, hi)

    predictions = {"bin_s": bin_s, "window": list(window),
                   "cycles_s": cycles, "lag_bins": lag_bins,
                   "run_id": header.get("run_id")}
    lags_path = analysis_dir(run_dir) / "predicted_lags_t2.json"
    committed, reused = write_once(lags_path, predictions)
    report["predicted_lags"] = committed
    report["predicted_lags_reused"] = reused
    report["predicted_lags_sha256"] = sha256_of(lags_path)
    bin_s = committed["bin_s"]
    window = tuple(committed["window"])
    report["bin_s"] = bin_s
    report["window"] = list(window)

    series = _trim_warmup(backlog_slope_series(events, bin_s), bin_s,
                          steady.get("warmup_cutoff_s", 0.0))
    if not series:
        report["refusals"].append("empty backlog-slope series: insufficient data")
        write_report(run_dir, "t2_report", report)
        return report
    stats = _series_stats(series, window, window, surrogate_seed, n_shuffles)
    report["series"] = stats
    if "refusal" in stats:
        report["refusals"].append(stats["refusal"])
        write_report(run_dir, "t2_report", report)
        return report

    in_window = stats["significant_in_window"]
    if not in_window:
        report["verdict"] = "T2-NO-STRUCTURE"
    else:
        result = assign(in_window, committed["lag_bins"])
        report["attribution"] = result
        report["verdict"] = ("T2-ATTRIBUTION-FAILED" if result["unattributed"]
                              else "T2-STRUCTURE-ATTRIBUTED")
    write_report(run_dir, "t2_report", report)
    return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_t2.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/t2.py tests/analysis/test_t2.py
git commit -m "qsim: T2 backlog-slope analysis with inheritance-conditional note"
```

---

### Task 11: `analysis/t3.py`

**Files:**
- Create: `qsim/analysis/t3.py`
- Test: `tests/analysis/test_t3.py`

**Interfaces:**
- Consumes: `t3_decision_points` (Task 5), header `config.epoch.decay_rate_per_class["messenger"]` (the engine's single lease coherence class), `artifacts`.
- Produces: `analyze_t3(run_dir: Path) -> dict`; verdicts (prereg four-outcome space): `"INVERSIONS-RARE"`, `"INVERSIONS-FREQUENT (DECISION-EARNED, REPRESENTATION-CHEAP)"`, `"INVERSIONS-FREQUENT-BUT-IMMATERIAL (demotion stands)"`, `"NON-FIELD-AT-OPERATING-POINT (degenerate-dominated)"`. Report `t3_report.json`.
- Thresholds (prereg verbatim): nondegenerate = ≥2 co-pending leases (with observed terminals — censored excluded, finding #3); FREQUENT iff inversion-point rate > 0.10 AND median projected retention delta over inverted pairs > 0.01. Degenerate-dominated (finding #8, disclosed): nondegenerate fraction < 0.5. Zero decision points → refusal, no verdict.
- Fidelity math: `current_i = f_h,i · exp(−rate·(t_d − h_i))`; `projected_i = f_h,i · exp(−rate·(t_terminal,i − h_i))` — projection TIME observed from the trace, fidelity analytic, never read from an outcome event.

- [ ] **Step 1: Write the failing test**

```python
"""T3 verdicts on hand-built traces with known inversion counts and known
projected deltas (design §11; prereg T3 thresholds)."""
import json

import pytest

from qsim.analysis.t3 import analyze_t3


def _run_dir(tmp_path, rows, rate=0.1):
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 1, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": 0.0,
                          "evidence": {"horizon_s": 30.0}},
        "config": {"scheduler": "S1",
                    "epoch": {"decay_rate_per_class": {"messenger": rate,
                                                        "memory": 0.001}}},
    }))
    return run_dir


def _pair(hi_f, hi_h, lo_f, lo_h, consume_at, other_terminal_at,
          other_terminal="lease.expired"):
    """Two co-pending leases; L1 consumed at `consume_at` (the decision
    point), L2 reaches `other_terminal` later."""
    return [
        (hi_h - 0.5, "lease.requested", "L1", {"round_id": "r1"}),
        (hi_h, "lease.heralded", "L1", {"round_id": "r1",
                                         "fidelity_at_herald": hi_f}),
        (lo_h - 0.4, "lease.requested", "L2", {"round_id": "r2"}),
        (lo_h, "lease.heralded", "L2", {"round_id": "r2",
                                         "fidelity_at_herald": lo_f}),
        (consume_at, "lease.consumed", "L1",
         {"round_id": "r1", "fidelity_at_consumption": 0.0}),
        (other_terminal_at, other_terminal, "L2", {"round_id": "r2"}),
    ]


def test_material_inversion_is_decision_earned(tmp_path):
    # rate 0.1: current(L1)=0.9*e^-0.5=0.546 < current(L2)=0.85*e^-0.1=0.769
    # projected(L1)=0.546 (consumed at decision) > projected(L2)=0.85*e^-1.6=0.172
    # -> inversion, delta ~0.374 > 0.01 -> FREQUENT + material.
    rows = _pair(0.9, 0.0, 0.85, 4.0, consume_at=5.0, other_terminal_at=20.0)
    report = analyze_t3(_run_dir(tmp_path, sorted(rows, key=lambda r: r[0])))
    assert report["verdict"].startswith("INVERSIONS-FREQUENT (DECISION-EARNED")
    assert report["inversion_point_rate"] == 1.0
    assert report["median_projected_delta"] > 0.01


def test_aligned_orderings_are_rare(tmp_path):
    # L2 consumed shortly after: both orderings agree -> no inversion.
    rows = _pair(0.9, 0.0, 0.85, 4.0, consume_at=5.0, other_terminal_at=5.2,
                 other_terminal="lease.consumed")
    report = analyze_t3(_run_dir(tmp_path, sorted(rows, key=lambda r: r[0])))
    assert report["verdict"] == "INVERSIONS-RARE"


def test_immaterial_inversion_demotion_stands(tmp_path):
    # rate 1e-3, near-tied fidelities: inversion with delta < 0.01.
    rows = _pair(0.9, 0.0, 0.896, 5.0, consume_at=5.0, other_terminal_at=6.0)
    report = analyze_t3(_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]),
                                  rate=0.001))
    assert report["verdict"] == "INVERSIONS-FREQUENT-BUT-IMMATERIAL (demotion stands)"


def test_degenerate_dominated_is_non_field(tmp_path):
    rows = []
    for i in range(3):  # three singleton decision points, zero nondegenerate
        t = 10.0 * i
        rows += [
            (t, "lease.requested", f"L{i}", {"round_id": f"r{i}"}),
            (t + 0.5, "lease.heralded", f"L{i}", {"round_id": f"r{i}",
                                                   "fidelity_at_herald": 0.9}),
            (t + 1.0, "lease.consumed", f"L{i}",
             {"round_id": f"r{i}", "fidelity_at_consumption": 0.0}),
        ]
    report = analyze_t3(_run_dir(tmp_path, rows))
    assert report["verdict"].startswith("NON-FIELD-AT-OPERATING-POINT")
    assert report["nondegenerate_fraction"] == 0.0


def test_censored_leases_are_excluded_and_counted(tmp_path):
    rows = [
        (0.0, "lease.requested", "L1", {"round_id": "r1"}),
        (0.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (1.0, "lease.requested", "L2", {"round_id": "r2"}),
        (1.5, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (2.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.0}),
        # L2 never terminates: censored -> point degenerates to size 1
    ]
    report = analyze_t3(_run_dir(tmp_path, rows))
    assert report["n_censored_leases"] == 1
    assert report["nondegenerate_fraction"] == 0.0


def test_no_decision_points_is_refusal(tmp_path):
    report = analyze_t3(_run_dir(tmp_path, [
        (1.0, "round.arrived", "r1", {"retry_ordinal": 0, "deadline": 2.0})]))
    assert report["verdict"] is None
    assert report["refusals"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/analysis/test_t3.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

`qsim/analysis/t3.py`:

```python
"""T3 lease-freshness rank inversion (design §6; prereg T3, thresholds
verbatim). Disclosed conventions (2026-07-09 plan findings #3, #8):

* Projection time for each co-pending lease is its OWN terminal event time
  from the trace; the fidelity at that time is ANALYTIC —
  f_herald * exp(-rate * (t_terminal - heralded_at)) — never read from an
  observed outcome event ("analytic from trace, projected never observed").
* Leases with no terminal in the trace (horizon-censored) are excluded from
  the ordering and counted in the report.
* "Degenerate batches dominate" = nondegenerate fraction < 0.5.
"""
from __future__ import annotations

import math
from itertools import combinations
from pathlib import Path

from qsim.analysis import numerics
from qsim.analysis.artifacts import ancestry, write_report
from qsim.analysis.t1 import _load_header
from qsim.observe.decision_points import t3_decision_points

INVERSION_RATE_THRESHOLD = 0.10   # prereg: "more than 10%"
MATERIALITY_THRESHOLD = 0.01      # prereg: median projected delta, absolute
DEGENERATE_DOMINANCE = 0.5        # plan finding #8, disclosed convention


def analyze_t3(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    header = _load_header(run_dir)
    rate = float(header["config"]["epoch"]["decay_rate_per_class"]["messenger"])
    report: dict = {
        "test": "t3", "verdict": None, "refusals": [],
        "operating_point": header.get("config"),
        "git_sha": header.get("git_sha"),
        "ancestry": ancestry(header.get("git_sha", "")),
        "decay_rate": rate,
        "thresholds": {
            "inversion_point_rate": INVERSION_RATE_THRESHOLD,
            "median_projected_delta": MATERIALITY_THRESHOLD,
            "degenerate_dominance": DEGENERATE_DOMINANCE,
        },
        "conventions": {
            "projection_time": "each lease's own terminal event time from the "
                                "trace; fidelity analytic, never observed",
            "censoring": "leases without a terminal are excluded and counted",
        },
    }

    points = t3_decision_points(run_dir / "events.jsonl")
    report["n_decision_points"] = len(points)
    if not points:
        report["refusals"].append("no decision points: insufficient data")
        write_report(run_dir, "t3_report", report)
        return report

    n_censored = 0
    n_nondegenerate = 0
    n_inverted_points = 0
    inverted_deltas: list[float] = []
    for dp in points:
        eligible = [l for l in dp.co_pending if l.terminal_time is not None]
        n_censored += len(dp.co_pending) - len(eligible)
        if len(eligible) < 2:
            continue
        n_nondegenerate += 1
        scored = [
            (l.fidelity_at_herald * math.exp(-rate * (dp.sim_time - l.heralded_at)),
             l.fidelity_at_herald * math.exp(-rate * (l.terminal_time - l.heralded_at)))
            for l in eligible
        ]
        point_inverted = False
        for (cur_i, proj_i), (cur_j, proj_j) in combinations(scored, 2):
            if (cur_i - cur_j) * (proj_i - proj_j) < 0:
                point_inverted = True
                inverted_deltas.append(abs(proj_i - proj_j))
        if point_inverted:
            n_inverted_points += 1

    nondeg_fraction = n_nondegenerate / len(points)
    report["n_censored_leases"] = n_censored
    report["n_nondegenerate"] = n_nondegenerate
    report["nondegenerate_fraction"] = nondeg_fraction

    if nondeg_fraction < DEGENERATE_DOMINANCE:
        report["verdict"] = ("NON-FIELD-AT-OPERATING-POINT (degenerate-dominated); "
                              "retest under higher concurrency")
        write_report(run_dir, "t3_report", report)
        return report

    rate_points = n_inverted_points / n_nondegenerate
    median_delta = numerics.percentile(inverted_deltas, 50) if inverted_deltas else 0.0
    report["inversion_point_rate"] = rate_points
    report["median_projected_delta"] = median_delta

    if rate_points > INVERSION_RATE_THRESHOLD and median_delta > MATERIALITY_THRESHOLD:
        report["verdict"] = ("INVERSIONS-FREQUENT (DECISION-EARNED, "
                              "REPRESENTATION-CHEAP): the fix is a projection from "
                              "existing scalars, NOT a field; frequent inversions do "
                              "NOT re-promote lease freshness to field")
    elif rate_points > INVERSION_RATE_THRESHOLD:
        report["verdict"] = "INVERSIONS-FREQUENT-BUT-IMMATERIAL (demotion stands)"
    else:
        report["verdict"] = "INVERSIONS-RARE"
    write_report(run_dir, "t3_report", report)
    return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_t3.py -v`
Expected: all PASS. Verify the arithmetic in test 1 by hand if it fails: current(L1) = 0.9·e^(−0.1·5) ≈ 0.5459, current(L2) = 0.85·e^(−0.1·1) ≈ 0.7691, projected(L2) = 0.85·e^(−0.1·16) ≈ 0.1716.

- [ ] **Step 5: Commit**

```bash
git add qsim/analysis/t3.py tests/analysis/test_t3.py
git commit -m "qsim: T3 rank-inversion verdicts (four-outcome space, censoring counted)"
```

---

### Task 12: CLI `analyze` subcommand

**Files:**
- Modify: `qsim/cli.py` (new subparser + command functions; extend imports)
- Test: `tests/experiments/test_cli_analyze.py`

**Interfaces:**
- Produces: `quantumos analyze t1 RUN_DIR --mode {control,open} [--companion DIR] [--bin-s F] [--seed N]`; `quantumos analyze t2 RUN_DIR [--bin-s F] [--seed N]`; `quantumos analyze t3 RUN_DIR`. Prints verdict, refusals, and report path; the JSON artifact is the record. `AnalysisRefusal` propagates to the existing `main()` handler (stderr + exit 1) — the report is already on disk by then.

- [ ] **Step 1: Write the failing test**

```python
"""CLI wiring for analyze (design §3 CLI)."""
import json

from qsim.cli import main


def _t3_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rows = [
        (0.0, "lease.requested", "L1", {"round_id": "r1"}),
        (0.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (1.0, "lease.requested", "L2", {"round_id": "r2"}),
        (1.5, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (2.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.0}),
        (3.0, "lease.consumed", "L2", {"round_id": "r2", "fidelity_at_consumption": 0.0}),
    ]
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 1, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": 0.0,
                          "evidence": {"horizon_s": 3.0}},
        "config": {"scheduler": "S1",
                    "epoch": {"decay_rate_per_class": {"messenger": 0.01}}},
    }))
    return run_dir


def test_analyze_t3_end_to_end(tmp_path, capsys):
    run_dir = _t3_run_dir(tmp_path)
    assert main(["analyze", "t3", str(run_dir)]) == 0
    out = capsys.readouterr().out
    assert "verdict" in out.lower()
    assert (run_dir / "analysis" / "t3_report.json").exists()


def test_analyze_t1_open_without_companion_exits_nonzero(tmp_path):
    run_dir = _t3_run_dir(tmp_path)  # any run dir; refusal fires first
    assert main(["analyze", "t1", str(run_dir), "--mode", "open"]) == 1


def test_analyze_parser_rejects_bad_mode(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        main(["analyze", "t1", str(tmp_path), "--mode", "sideways"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/experiments/test_cli_analyze.py -v`
Expected: FAIL — argparse error, `analyze` unknown command

- [ ] **Step 3: Write the implementation**

In `qsim/cli.py`, add imports near the top:

```python
from qsim.analysis.t1 import analyze_t1
from qsim.analysis.t2 import analyze_t2
from qsim.analysis.t3 import analyze_t3
```

Add command functions (after `_validate_config_command`):

```python
def _print_analysis(report: dict) -> None:
    print(f"test: {report['test']}")
    print(f"verdict: {report['verdict']}")
    if report.get("directive"):
        print(f"DIRECTIVE: **{report['directive']}**")
    if report.get("caveat"):
        print(f"caveat: {report['caveat']}")
    for refusal in report.get("refusals", []):
        print(f"refusal: {refusal}")


def _analyze_command(args: argparse.Namespace) -> int:
    if args.test == "t1":
        report = analyze_t1(args.run_dir, mode=args.mode,
                            companion_dir=args.companion,
                            bin_s_override=args.bin_s,
                            surrogate_seed=args.seed)
    elif args.test == "t2":
        report = analyze_t2(args.run_dir, bin_s_override=args.bin_s,
                            surrogate_seed=args.seed)
    else:
        report = analyze_t3(args.run_dir)
    _print_analysis(report)
    print(f"report: {Path(args.run_dir) / 'analysis'}")
    return 0
```

In `build_parser()`, before `return parser`:

```python
    analyze_parser = subparsers.add_parser(
        "analyze", help="run a field-battery analysis over a run directory"
    )
    analyze_sub = analyze_parser.add_subparsers(dest="test", required=True)
    t1_parser = analyze_sub.add_parser("t1", help="pool-flux ACF (prereg T1)")
    t1_parser.add_argument("run_dir", type=Path)
    t1_parser.add_argument("--mode", choices=("control", "open"), required=True)
    t1_parser.add_argument("--companion", type=Path, default=None,
                           help="knob-motion companion run dir (open mode)")
    t1_parser.add_argument("--bin-s", dest="bin_s", type=float, default=None)
    t1_parser.add_argument("--seed", type=int, default=0,
                           help="surrogate shuffle seed (recorded in report)")
    t1_parser.set_defaults(func=_analyze_command)
    t2_parser = analyze_sub.add_parser("t2", help="backlog-slope ACF (prereg T2)")
    t2_parser.add_argument("run_dir", type=Path)
    t2_parser.add_argument("--bin-s", dest="bin_s", type=float, default=None)
    t2_parser.add_argument("--seed", type=int, default=0)
    t2_parser.set_defaults(func=_analyze_command)
    t3_parser = analyze_sub.add_parser("t3", help="rank inversions (prereg T3)")
    t3_parser.add_argument("run_dir", type=Path)
    t3_parser.set_defaults(func=_analyze_command)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/experiments/test_cli_analyze.py tests/experiments/test_cli.py -v`
Expected: all PASS (existing CLI tests untouched)

- [ ] **Step 5: Commit**

```bash
git add qsim/cli.py tests/experiments/test_cli_analyze.py
git commit -m "qsim: CLI analyze t1|t2|t3"
```

---

### Task 13: S1 sweep runner + CLI `sweep s1`

**Files:**
- Create: `qsim/experiments/sweep.py`
- Modify: `qsim/cli.py` (sweep subcommand)
- Test: `tests/experiments/test_sweep.py`

**Interfaces:**
- Consumes: `qsim.cli.load_config`, `qsim.experiments.run.run`, `qsim.observe.views.{deadline_compliance, fidelity_at_outcome, resource_utilization}`, `qsim.observe.run_dir._json_safe`.
- Produces:

```python
S1_DELTAS = (0.0, 0.1, 0.2, 0.4)   # prereg grid verbatim; 0.4 records as infeasible (finding #2)

def heralding_spread(p_bar: float, delta: float) -> tuple[float, float, float, float]
    # 4 evenly spaced values on [p_bar - delta, p_bar + delta] (prereg example:
    # delta=0.2 -> 0.5, 0.6333, 0.7667, 0.9). Raises InfeasibleArm if any value
    # falls outside [0, 1].
class InfeasibleArm(ValueError): ...
def build_arm_config(base: RunConfig, delta: float) -> RunConfig
    # epoch heralding_p_per_path reassigned: spread values assigned to paths in
    # sorted-path-key order (deterministic, disclosed).
def config_sha256(config: RunConfig) -> str
def run_sweep(base_config_path: Path, out_root: Path,
              deltas: tuple[float, ...] = S1_DELTAS,
              max_sim_time_s: float | None = None) -> dict
    # writes <out_root>/sweep_manifest.json + <out_root>/dose_response.json.
    # max_sim_time_s is an EXPLICIT override only (never a silent default —
    # the test-convenience-default lesson).
```

- Manifest per arm: `{"delta", "status": "ran"|"infeasible", "run_id", "run_dir", "config_sha256", "steady_state", "reason"?}`. Infeasible arms carry `"recommend": "prereg amendment: replace delta=0.4 (heralding_p 1.1 > 1) with a feasible arm, e.g. delta=0.3"`. Refusals are data — feasible arms still run.
- Dose-response per ran arm: `deadline_compliance` dict, `fidelity_at_outcome` summarized as `{f"{outcome}|{cause}": {"n", "mean"}}`, `resource_utilization`. δ=0 homogeneity anchor: warning recorded if max−min per-path utilization > 0.1 (any effect at δ=0 is a bug, not a curve). Monotonicity block: for `completed_in_deadline` across ran arms ascending in δ, `{"metric", "values", "monotone_nonincreasing": bool}` — reported, never failed.

- [ ] **Step 1: Write the failing test**

```python
"""S1 sweep: pinned grid, infeasible-arm refusal, dose-response artifact
(design §8; prereg S1 + plan finding #2)."""
import json

import pytest

from qsim.cli import load_config
from qsim.experiments.sweep import (
    InfeasibleArm,
    S1_DELTAS,
    build_arm_config,
    heralding_spread,
    run_sweep,
)


def test_heralding_spread_matches_prereg_example():
    assert heralding_spread(0.7, 0.2) == pytest.approx((0.5, 0.6333333333333333,
                                                         0.7666666666666666, 0.9))
    assert heralding_spread(0.7, 0.0) == pytest.approx((0.7, 0.7, 0.7, 0.7))


def test_heralding_spread_delta_04_is_infeasible():
    with pytest.raises(InfeasibleArm):
        heralding_spread(0.7, 0.4)  # 1.1 > 1 (plan finding #2)


def test_build_arm_config_keeps_mean_and_reassigns_paths():
    base = load_config("examples/t1-open.toml")
    arm = build_arm_config(base, 0.2)
    ps = sorted(arm.epoch.heralding_p_per_path.values())
    assert ps == pytest.approx([0.5, 0.6333333333333333, 0.7666666666666666, 0.9])
    assert sum(ps) / 4 == pytest.approx(0.7)
    assert arm.run_seed == base.run_seed  # everything else untouched
    assert arm.epoch.heralded_fidelity_per_path == base.epoch.heralded_fidelity_per_path


def test_run_sweep_records_infeasible_arm_and_runs_feasible(tmp_path):
    manifest = run_sweep("examples/t1-open.toml", tmp_path,
                         deltas=(0.0, 0.4), max_sim_time_s=5.0)
    arms = {arm["delta"]: arm for arm in manifest["arms"]}
    assert arms[0.4]["status"] == "infeasible"
    assert "amendment" in arms[0.4]["recommend"]
    assert arms[0.0]["status"] == "ran"
    assert (tmp_path / "sweep_manifest.json").exists()
    dose = json.loads((tmp_path / "dose_response.json").read_text())
    (row,) = [r for r in dose["rows"] if r["delta"] == 0.0]
    assert "deadline_compliance" in row
    assert "fidelity_at_outcome" in row
    assert "monotonicity" in dose


def test_default_grid_is_the_prereg_grid():
    assert S1_DELTAS == (0.0, 0.1, 0.2, 0.4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/experiments/test_sweep.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

`qsim/experiments/sweep.py`:

```python
"""S1 sweep runner — minimal and battery-specific (design §8; grid-sweep
proper stays M1 work). Four pinned heralding-spread arms over the T1-open
physics; delta=0 is the homogeneity anchor (any effect there is a bug, not
a curve). Non-monotonicity is reported, not failed (prereg: it triggers a
mechanism audit under the attribution rule).

Plan finding #2: the prereg's delta=0.4 arm is infeasible at p_bar=0.7
(heralding_p 1.1 > 1, by the prereg's own delta=0.2 example fixing delta as
half-spread). The arm is recorded in the manifest as an in-artifact refusal
with a recommended amendment; feasible arms still run.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

from qsim.experiments.config import RunConfig
from qsim.experiments.run import run
from qsim.observe.run_dir import _json_safe
from qsim.observe.views import (
    deadline_compliance,
    fidelity_at_outcome,
    resource_utilization,
)

S1_DELTAS = (0.0, 0.1, 0.2, 0.4)
HOMOGENEITY_UTILIZATION_TOLERANCE = 0.1  # disclosed convention (delta=0 anchor)


class InfeasibleArm(ValueError):
    """A spread arm whose heralding_p leaves [0, 1]."""


def heralding_spread(p_bar: float, delta: float) -> tuple[float, ...]:
    """Four evenly spaced heralding_p values on [p_bar-delta, p_bar+delta]
    (prereg example: delta=0.2 -> {0.5, 0.633, 0.767, 0.9})."""
    if delta == 0.0:
        values = (p_bar,) * 4
    else:
        values = tuple(p_bar - delta + i * (2 * delta / 3) for i in range(4))
    for v in values:
        if not 0.0 <= v <= 1.0:
            raise InfeasibleArm(
                f"delta={delta} at p_bar={p_bar} yields heralding_p={v:.3f} "
                f"outside [0, 1]")
    return values


def build_arm_config(base: RunConfig, delta: float) -> RunConfig:
    ps = set(base.epoch.heralding_p_per_path.values())
    if len(ps) != 1:
        raise ValueError("sweep base config must have homogeneous heralding_p")
    (p_bar,) = ps
    spread = heralding_spread(p_bar, delta)
    paths = sorted(base.epoch.heralding_p_per_path, key=str)
    epoch = dataclasses.replace(
        base.epoch,
        heralding_p_per_path={path: spread[i] for i, path in enumerate(paths)},
    )
    return dataclasses.replace(base, epoch=epoch)


def config_sha256(config: RunConfig) -> str:
    payload = json.dumps(_json_safe(config), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def run_sweep(base_config_path: Path, out_root: Path,
              deltas: tuple[float, ...] = S1_DELTAS,
              max_sim_time_s: float | None = None) -> dict:
    from qsim.cli import load_config  # local import: cli imports analysis

    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    base = load_config(base_config_path)
    if max_sim_time_s is not None:
        # EXPLICIT override only — never a silent test-convenience default
        # (the swept-mechanism-silencing lesson).
        base = dataclasses.replace(base, max_sim_time_s=max_sim_time_s)

    arms = []
    rows = []
    for delta in deltas:
        try:
            config = build_arm_config(base, delta)
        except InfeasibleArm as exc:
            arms.append({
                "delta": delta, "status": "infeasible", "reason": str(exc),
                "recommend": ("prereg amendment: replace delta=0.4 "
                               "(heralding_p 1.1 > 1) with a feasible arm, "
                               "e.g. delta=0.3"),
            })
            continue
        run_dir = run(config, out_root)
        events = run_dir / "events.jsonl"
        header = json.loads((run_dir / "header.json").read_text())
        arms.append({
            "delta": delta, "status": "ran",
            "run_id": header["run_id"], "run_dir": str(run_dir),
            "config_sha256": config_sha256(config),
            "steady_state": header.get("steady_state"),
        })
        utilization = resource_utilization(events)
        row = {
            "delta": delta,
            "deadline_compliance": deadline_compliance(events),
            "fidelity_at_outcome": {
                f"{outcome}|{cause}": {"n": len(vals),
                                        "mean": sum(vals) / len(vals)}
                for (outcome, cause), vals in sorted(
                    fidelity_at_outcome(events).items())
            },
            "resource_utilization": utilization,
        }
        if delta == 0.0 and utilization:
            spread_u = max(utilization.values()) - min(utilization.values())
            if spread_u > HOMOGENEITY_UTILIZATION_TOLERANCE:
                row["homogeneity_warning"] = (
                    f"per-path utilization spread {spread_u:.3f} > "
                    f"{HOMOGENEITY_UTILIZATION_TOLERANCE} at delta=0: "
                    "any effect at the anchor is a bug, not a curve")
        rows.append(row)

    values = [r["deadline_compliance"]["completed_in_deadline"] for r in rows]
    dose = {
        "rows": rows,
        "monotonicity": {
            "metric": "completed_in_deadline",
            "values": values,
            "monotone_nonincreasing": all(a >= b for a, b in zip(values, values[1:])),
            "note": "non-monotonicity triggers a mechanism audit under the "
                    "attribution rule, not automatic failure (prereg S1)",
        },
    }
    manifest = {"base_config": str(base_config_path), "arms": arms}
    (out_root / "sweep_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True))
    (out_root / "dose_response.json").write_text(
        json.dumps(dose, indent=2, sort_keys=True))
    return manifest
```

In `qsim/cli.py`, add the subcommand (before `return parser`) and command function:

```python
def _sweep_command(args: argparse.Namespace) -> int:
    from qsim.experiments.sweep import S1_DELTAS, run_sweep

    deltas = tuple(args.deltas) if args.deltas else S1_DELTAS
    manifest = run_sweep(args.base_config, args.out, deltas=deltas,
                         max_sim_time_s=args.max_sim_time)
    for arm in manifest["arms"]:
        print(f"delta={arm['delta']}: {arm['status']}"
              + (f" run_dir={arm['run_dir']}" if arm["status"] == "ran" else
                 f" ({arm['reason']})"))
    print(f"artifacts: {args.out}/sweep_manifest.json, {args.out}/dose_response.json")
    return 0
```

```python
    sweep_parser = subparsers.add_parser("sweep", help="run a pinned battery sweep")
    sweep_sub = sweep_parser.add_subparsers(dest="sweep_name", required=True)
    s1_parser = sweep_sub.add_parser("s1", help="spatial-blindness dose-response (prereg S1)")
    s1_parser.add_argument("base_config", type=Path,
                           help="T1-open base config (examples/t1-open.toml)")
    s1_parser.add_argument("--out", type=Path, default=Path("runs/sweep-s1"))
    s1_parser.add_argument("--deltas", type=float, nargs="+", default=None)
    s1_parser.add_argument("--max-sim-time", dest="max_sim_time", type=float,
                           default=None, help="EXPLICIT horizon override")
    s1_parser.set_defaults(func=_sweep_command)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/experiments/test_sweep.py -v`
Expected: all PASS (the run_sweep test executes one real 5 s S1 run; a few seconds of wall clock)

- [ ] **Step 5: Commit**

```bash
git add qsim/experiments/sweep.py qsim/cli.py tests/experiments/test_sweep.py
git commit -m "qsim: S1 sweep runner — pinned grid, infeasible-arm refusal, dose-response"
```

---

### Task 14: integration gate — real run through `analyze t1`

**Files:**
- Test: `tests/experiments/test_analyze_t1_integration.py`

**Interfaces:**
- Consumes: `qsim.cli.load_config`, `qsim.experiments.run.run`, `analyze_t1`, `sha256_of`.
- Gate (design §11, consumer-side full-taxonomy lesson): one real short-horizon T1-control run (stamped config, horizon shortened to 40 s — the prereg's own declared-loss smoke horizon, seed 7) piped through the complete control pipeline. Asserts the artifact chain (predictions file, hash embed, report), the write-once semantics on re-run, the control verdict PASS (the prereg's declared smoke run measured lag-1 ACF −0.25..−0.35 against a ±0.098 band at exactly this horizon and seed), and that every event type the pipeline consumes occurs in the gate run. `pool.expired` may legitimately be absent at this operating point (freshness bound 2 s vs. fast withdrawal); it is covered by the Task 3 unit tests and asserted here only if present — the assertion set is measured, not assumed.

- [ ] **Step 1: Write the failing test**

```python
"""Integration gate: stamped T1-control config -> real run -> full analyze
t1 pipeline (design §11). The gate covers the CONSUMER side of the trace
contract: every event type the pipeline reads must occur in the gate run."""
import json
from dataclasses import replace

from qsim.analysis.artifacts import sha256_of
from qsim.analysis.t1 import analyze_t1
from qsim.cli import load_config
from qsim.experiments.run import run

# Event types the T1 pipeline consumes (views: flux, latency, withdrawals,
# retry cadence; steady state is read from the header, which the run stamps).
_CONSUMED = {
    "pool.deposited",
    "pool.withdrawn",
    "reservation.acquired",
    "round.arrived",
}


def test_t1_control_gate(tmp_path):
    config = replace(load_config("examples/t1-control.toml"), max_sim_time_s=40.0)
    run_dir = run(config, tmp_path)

    report = analyze_t1(run_dir, mode="control")

    # Verdict: the prereg's declared-loss smoke run at this horizon/seed was
    # loud (lag-1 ACF -0.25..-0.35 vs ±0.098 band) — the control must PASS.
    assert report["verdict"] == "PASS"

    # Artifact chain (design §9).
    lags_path = run_dir / "analysis" / "predicted_lags_t1.json"
    report_path = run_dir / "analysis" / "t1_report.json"
    assert lags_path.exists() and report_path.exists()
    assert report["predicted_lags_sha256"] == sha256_of(lags_path)
    on_disk = json.loads(report_path.read_text())
    assert on_disk["verdict"] == "PASS"
    assert on_disk["ancestry"]["stamped_commit"]

    # Consumer-side taxonomy: every consumed type occurs in the gate run.
    present = {json.loads(line)["event_type"]
               for line in (run_dir / "events.jsonl").read_text().splitlines()}
    missing = _CONSUMED - present
    assert not missing, f"gate run never emits consumed types: {missing}"

    # Write-once survives a re-run of the analysis.
    before = lags_path.read_text()
    rerun = analyze_t1(run_dir, mode="control")
    assert lags_path.read_text() == before
    assert rerun["predicted_lags_reused"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/experiments/test_analyze_t1_integration.py -v`
Expected: with Tasks 1–13 complete this may already PASS — that is the point of a gate. If it fails, the failure is a real producer/consumer contract break: debug the binding (payload field names, replenish lineage), not the test.

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest`
Expected: all tests green (365 pre-existing + all new)

- [ ] **Step 4: Commit**

```bash
git add tests/experiments/test_analyze_t1_integration.py
git commit -m "qsim: integration gate — stamped T1-control config through analyze t1"
```

---

## Self-Review (run before handoff)

1. **Spec coverage** — design §2 views: flux ✓(T3), latency ✓(T4), inter-withdrawal ✓(T4), retry cadence ✓(T4), backlog slope ✓(T3), t3 decision points ✓(T5). §3 modules: numerics ✓(T1), surrogates ✓(T2), attribution ✓(T6), artifacts ✓(T7), t1 ✓(T8-9), t2 ✓(T10), t3 ✓(T11), CLI ✓(T12). §4 pipeline order ✓(T8). §5 window ✓(T8). §6 verdicts ✓(T8-11). §7 companion ✓(T9). §8 sweep ✓(T13). §9 artifacts/provenance ✓(T7-9). §10 refusals ✓(throughout). §11 testing ✓(unit per task + T14 gate). §12 out of scope respected (no T4 tooling, no plotting, no engine changes).
2. **Placeholder scan** — one deliberate stub: `_open_verdict` raises NotImplementedError inside Task 8 and is replaced in Task 9 (declared, tested at both ends). The FIELD-BLOCKED test's seed note is instructions-to-executor about test data, not implementation TBD.
3. **Type consistency** — `_series_stats`, `_trim_warmup`, `_load_header` defined in Task 8 and imported by Task 10 with matching signatures; `write_once` returns `(dict, bool)` everywhere; `assign` returns `{"assigned", "unattributed"}` consumed by T9/T10 accordingly; pool keys stringified via `str()` at every report boundary.

## Execution notes

- Run full suite (`uv run pytest`) before every commit, not just the task's file.
- The integration gate (T14) is the arbiter for payload-binding guesses (findings #1, #4, #9): if it disagrees with a unit-test binding, the trace is the sole source of truth — fix the view, then the unit test.
- After all tasks: run `uv run quantumos analyze t1 --help` once as a smoke check of parser wiring.
