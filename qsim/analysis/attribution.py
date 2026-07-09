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
