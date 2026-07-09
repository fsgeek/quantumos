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
    if reused and committed != predictions:
        report["refusals"].append(
            "predicted_lags_t2.json reused verbatim; freshly derived values "
            "differ and are DISCARDED (write-once, design §4.3)")
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
