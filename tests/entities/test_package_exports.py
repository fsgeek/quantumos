"""Smoke test: the frozen contract's package-level import path resolves.

Downstream layers (models, policies, engine, experiments) import the entity
public API as ``from qsim.entities import <Name>``. This pins that path so a
future edit to ``qsim/entities/__init__.py`` cannot silently break every
downstream layer's imports (which is exactly what happened before re-exports
were added — see the models layer's per-agent import workarounds).
"""

import qsim.entities as entities


def test_public_api_is_importable_at_package_level():
    from qsim.entities import (  # noqa: F401
        CalibrationEpoch,
        CoherenceClass,
        DecoderJob,
        EntanglementLease,
        LeaseState,
        Module,
        PathId,
        PauliFrameToken,
        PortId,
        QubitHandle,
        ReservationState,
        RoundState,
        SwitchPathReservation,
        make_path_id,
    )


def test_all_names_in_dunder_all_are_present():
    for name in entities.__all__:
        assert hasattr(entities, name), f"{name} listed in __all__ but not re-exported"
