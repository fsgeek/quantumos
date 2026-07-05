import pytest

from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.qubit import CoherenceClass, QubitHandle
from qsim.models.memory_access import LinearMemoryAccessModel, ZeroCostMemoryAccessModel


def _epoch(channel_s, wear_rate):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class={CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 1.0},
        memory_access_channel_s=channel_s,
        memory_access_wear_rate=wear_rate,
        heralding_p_per_path={},
        heralded_fidelity_per_path={},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1.0,
    )


def _qubit(epoch, access_count):
    return QubitHandle(qubit_id="q0", module_id="m0",
                       coherence_class=CoherenceClass.MEMORY,
                       calibration_epoch=epoch, access_count=access_count)


def test_linear_memory_access_no_prior_accesses_is_full_retention():
    epoch = _epoch(channel_s=0.002, wear_rate=0.1)
    model = LinearMemoryAccessModel()
    cost = model.access_cost(_qubit(epoch, access_count=0), epoch)
    assert cost.electron_channel_s == pytest.approx(0.002)
    assert cost.retention_factor == pytest.approx(1.0)


def test_linear_memory_access_wears_linearly_with_access_count():
    epoch = _epoch(channel_s=0.002, wear_rate=0.1)
    model = LinearMemoryAccessModel()
    cost = model.access_cost(_qubit(epoch, access_count=3), epoch)
    assert cost.retention_factor == pytest.approx(0.7)


def test_linear_memory_access_retention_floors_at_zero():
    epoch = _epoch(channel_s=0.002, wear_rate=0.5)
    model = LinearMemoryAccessModel()
    cost = model.access_cost(_qubit(epoch, access_count=100), epoch)
    assert cost.retention_factor == 0.0


def test_zero_cost_control_is_always_free_and_full_retention():
    epoch = _epoch(channel_s=0.002, wear_rate=0.9)
    model = ZeroCostMemoryAccessModel()
    for access_count in (0, 1, 1000):
        cost = model.access_cost(_qubit(epoch, access_count=access_count), epoch)
        assert cost.electron_channel_s == 0.0
        assert cost.retention_factor == 1.0
