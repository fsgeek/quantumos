import inspect
from dataclasses import FrozenInstanceError

import pytest

from qsim.models.protocols import (
    AccessCost, DecayModel, MemoryAccessModel, HeraldingModel,
    RoundSuccessModel, DecoderServiceModel,
)


def test_access_cost_holds_electron_channel_and_retention_fields():
    cost = AccessCost(electron_channel_s=0.002, retention_factor=0.95)
    assert cost.electron_channel_s == 0.002
    assert cost.retention_factor == 0.95


def test_access_cost_is_frozen():
    cost = AccessCost(electron_channel_s=0.002, retention_factor=0.95)
    with pytest.raises(FrozenInstanceError):
        cost.retention_factor = 1.0


@pytest.mark.parametrize("protocol_cls,method_names", [
    (DecayModel, ["retention"]),
    (MemoryAccessModel, ["access_cost"]),
    (HeraldingModel, ["success_probability", "heralded_fidelity"]),
    (RoundSuccessModel, ["success_probability"]),
    (DecoderServiceModel, ["service_time_s", "expected_service_time_s"]),
])
def test_protocol_declares_expected_methods(protocol_cls, method_names):
    for name in method_names:
        assert hasattr(protocol_cls, name), f"{protocol_cls.__name__} missing {name}"
        assert inspect.isfunction(getattr(protocol_cls, name))


def test_round_success_protocol_has_no_epoch_parameter():
    sig = inspect.signature(RoundSuccessModel.success_probability)
    assert "epoch" not in sig.parameters


def test_decoder_service_time_s_protocol_has_no_epoch_parameter():
    sig = inspect.signature(DecoderServiceModel.service_time_s)
    assert "epoch" not in sig.parameters
