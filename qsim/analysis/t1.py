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
    # No configured positive L => the low-water oscillation mechanism cannot
    # exist; pass no withdrawal gaps rather than fabricate a cycle with L=1.
    low_water_mark = header["config"].get("pregen_low_water_mark")
    withdrawal_gaps = (
        {str(k): v for k, v in inter_withdrawal_times(events).items()}
        if low_water_mark else {}
    )
    cycles = predicted_cycles_t1(
        latency,
        withdrawal_gaps,
        retry_cadence_samples(events),
        low_water_mark=low_water_mark or 1,  # unused when gaps is empty
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
