import math

import pytest

from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.qubit import CoherenceClass
from qsim.models.decay import ExponentialDecayModel, NoDecayModel


def _epoch(decay_rate_per_class):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class=decay_rate_per_class,
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={},
        heralded_fidelity_per_path={},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1.0,
    )


def test_exponential_decay_retention_at_age_zero_is_one():
    epoch = _epoch({CoherenceClass.MESSENGER: 10.0, CoherenceClass.MEMORY: 1.0})
    model = ExponentialDecayModel()
    assert model.retention(0.0, CoherenceClass.MESSENGER, epoch) == pytest.approx(1.0)


def test_exponential_decay_retention_at_half_life_is_one_half():
    rate = 2.0
    half_life = math.log(2) / rate
    epoch = _epoch({CoherenceClass.MESSENGER: rate, CoherenceClass.MEMORY: rate})
    model = ExponentialDecayModel()
    assert model.retention(half_life, CoherenceClass.MESSENGER, epoch) == pytest.approx(0.5, rel=1e-9)


def test_exponential_decay_uses_per_coherence_class_rate():
    epoch = _epoch({CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 5.0})
    model = ExponentialDecayModel()
    age = 1.0
    messenger_retention = model.retention(age, CoherenceClass.MESSENGER, epoch)
    memory_retention = model.retention(age, CoherenceClass.MEMORY, epoch)
    assert messenger_retention == pytest.approx(math.exp(-1.0))
    assert memory_retention == pytest.approx(math.exp(-5.0))
    assert messenger_retention != memory_retention


def test_no_decay_control_is_always_one():
    epoch = _epoch({CoherenceClass.MESSENGER: 999.0, CoherenceClass.MEMORY: 999.0})
    model = NoDecayModel()
    assert model.retention(0.0, CoherenceClass.MESSENGER, epoch) == 1.0
    assert model.retention(1e6, CoherenceClass.MEMORY, epoch) == 1.0
