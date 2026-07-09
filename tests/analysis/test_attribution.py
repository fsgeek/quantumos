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
