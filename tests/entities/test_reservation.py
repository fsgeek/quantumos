import pytest

from qsim.entities.module import PortId, make_path_id
from qsim.entities.reservation import ReservationState, SwitchPathReservation


def make_reservation() -> SwitchPathReservation:
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    return SwitchPathReservation(
        path_id=make_path_id(a, b), holder_id="round-1", acquired_at=0.0
    )


def test_reservation_starts_acquired():
    r = make_reservation()
    assert r.state is ReservationState.ACQUIRED
    assert r.released_at is None


def test_configure_from_acquired_succeeds():
    r = make_reservation()
    r.configure()
    assert r.state is ReservationState.CONFIGURING


def test_configure_twice_raises():
    r = make_reservation()
    r.configure()
    with pytest.raises(ValueError):
        r.configure()


def test_activate_requires_configuring():
    r = make_reservation()
    with pytest.raises(ValueError):
        r.activate()
    r.configure()
    r.activate()
    assert r.state is ReservationState.ACTIVE


def test_activate_twice_raises():
    r = make_reservation()
    r.configure()
    r.activate()
    with pytest.raises(ValueError):
        r.activate()


def test_release_from_acquired_succeeds():
    # Round cancelled while reservation was still being negotiated.
    r = make_reservation()
    r.release(at=1.0)
    assert r.state is ReservationState.RELEASED
    assert r.released_at == 1.0


def test_release_from_configuring_succeeds():
    r = make_reservation()
    r.configure()
    r.release(at=1.0)
    assert r.state is ReservationState.RELEASED


def test_release_from_active_succeeds():
    r = make_reservation()
    r.configure()
    r.activate()
    r.release(at=2.0)
    assert r.state is ReservationState.RELEASED


def test_release_twice_raises():
    r = make_reservation()
    r.release(at=1.0)
    with pytest.raises(ValueError):
        r.release(at=2.0)


def test_configure_after_release_raises():
    r = make_reservation()
    r.release(at=1.0)
    with pytest.raises(ValueError):
        r.configure()
