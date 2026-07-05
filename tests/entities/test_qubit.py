import pytest

from qsim.entities.qubit import CoherenceClass, QubitHandle


def make_handle() -> QubitHandle:
    return QubitHandle(
        qubit_id="q-1",
        module_id="mod-a",
        coherence_class=CoherenceClass.MEMORY,
        calibration_epoch=None,  # forward-ref type only; not exercised here
    )


def test_coherence_class_values():
    assert CoherenceClass.MESSENGER.value == "messenger"
    assert CoherenceClass.MEMORY.value == "memory"


def test_qubit_handle_starts_unheld():
    handle = make_handle()
    assert handle.state_held_since is None
    assert handle.fidelity_at_hold_start is None
    assert handle.access_count == 0


def test_hold_sets_timestamp_and_fidelity():
    handle = make_handle()
    handle.hold(at=10.0, fidelity=0.95)
    assert handle.state_held_since == 10.0
    assert handle.fidelity_at_hold_start == 0.95


def test_hold_while_already_held_raises():
    handle = make_handle()
    handle.hold(at=10.0, fidelity=0.95)
    with pytest.raises(ValueError):
        handle.hold(at=11.0, fidelity=0.9)


def test_release_clears_held_state():
    handle = make_handle()
    handle.hold(at=10.0, fidelity=0.95)
    handle.release()
    assert handle.state_held_since is None
    assert handle.fidelity_at_hold_start is None


def test_release_without_hold_raises():
    handle = make_handle()
    with pytest.raises(ValueError):
        handle.release()


def test_record_access_increments_count():
    handle = make_handle()
    handle.record_access()
    handle.record_access()
    assert handle.access_count == 2
