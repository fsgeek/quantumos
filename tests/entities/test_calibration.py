import dataclasses

import pytest

from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.module import PortId, make_path_id
from qsim.entities.qubit import CoherenceClass


def make_epoch() -> CalibrationEpoch:
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    path = make_path_id(a, b)
    return CalibrationEpoch(
        epoch_id="epoch-1",
        decay_rate_per_class={
            CoherenceClass.MESSENGER: 0.5,
            CoherenceClass.MEMORY: 0.01,
        },
        memory_access_channel_s=0.001,
        memory_access_wear_rate=0.002,
        heralding_p_per_path={path: 0.3},
        heralded_fidelity_per_path={path: 0.98},
        round_success_logistic_midpoint=0.9,
        round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=0.05,
        decoder_service_rate=100.0,
    )


def test_calibration_epoch_holds_fields():
    epoch = make_epoch()
    assert epoch.epoch_id == "epoch-1"
    assert epoch.decay_rate_per_class[CoherenceClass.MEMORY] == 0.01
    assert epoch.decoder_service_rate == 100.0


def test_calibration_epoch_is_immutable():
    epoch = make_epoch()
    with pytest.raises(dataclasses.FrozenInstanceError):
        epoch.decoder_service_rate = 50.0  # type: ignore[misc]


def test_calibration_epoch_maps_keyed_by_domain_types():
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    epoch = make_epoch()
    assert epoch.heralding_p_per_path[make_path_id(b, a)] == 0.3
    assert epoch.heralded_fidelity_per_path[make_path_id(a, b)] == 0.98
