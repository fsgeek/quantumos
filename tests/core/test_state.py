# tests/core/test_state.py
import dataclasses

import pytest

from qsim.core.state import EngineState, ModelBundle


def test_model_bundle_holds_all_five_surfaces():
    bundle = ModelBundle(
        decay="decay-model", memory_access="memory-model", heralding="heralding-model",
        round_success="round-success-model", decoder_service="decoder-service-model",
    )
    assert bundle.decay == "decay-model"
    assert bundle.memory_access == "memory-model"
    assert bundle.heralding == "heralding-model"
    assert bundle.round_success == "round-success-model"
    assert bundle.decoder_service == "decoder-service-model"


def test_model_bundle_is_frozen():
    bundle = ModelBundle(
        decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        bundle.decay = "other"


def test_engine_state_construction_exposes_all_fields():
    bundle = ModelBundle(decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s")
    state = EngineState(
        now=0.0,
        epoch="epoch-0",
        models=bundle,
        decoder_backlog=0,
        active_reservations={},
        pool={},
        switch_capacity_c=4,
        hold_until_consumption=False,
    )
    assert state.now == 0.0
    assert state.epoch == "epoch-0"
    assert state.models is bundle
    assert state.decoder_backlog == 0
    assert state.active_reservations == {}
    assert state.pool == {}
    assert state.switch_capacity_c == 4
    assert state.hold_until_consumption is False


def test_engine_state_is_mutable_for_engine_updates():
    bundle = ModelBundle(decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s")
    state = EngineState(
        now=0.0, epoch="epoch-0", models=bundle, decoder_backlog=0,
        active_reservations={}, pool={}, switch_capacity_c=4, hold_until_consumption=False,
    )
    state.now = 12.5
    state.decoder_backlog = 3
    state.active_reservations["path-a"] = "reservation-a"
    assert state.now == 12.5
    assert state.decoder_backlog == 3
    assert state.active_reservations == {"path-a": "reservation-a"}
