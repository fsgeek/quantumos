import pytest

from qsim.entities.lease import EntanglementLease, LeaseState
from qsim.entities.module import PortId, make_path_id


def make_lease(freshness_bound_s: float = 5.0) -> EntanglementLease:
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    return EntanglementLease(
        lease_id="lease-1",
        endpoints=(a, b),
        path_id=make_path_id(a, b),
        created_at=0.0,
        freshness_bound_s=freshness_bound_s,
    )


def test_lease_starts_requested():
    lease = make_lease()
    assert lease.state is LeaseState.REQUESTED
    assert lease.heralded_at is None
    assert lease.fidelity_at_herald is None


def test_mark_heralded_sets_fields_and_state():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    assert lease.state is LeaseState.HERALDED
    assert lease.heralded_at == 1.0
    assert lease.fidelity_at_herald == 0.99


def test_mark_heralded_twice_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    with pytest.raises(ValueError):
        lease.mark_heralded(at=2.0, fidelity=0.9)


def test_consume_from_heralded_succeeds():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.consume()
    assert lease.state is LeaseState.CONSUMED


def test_consume_without_heralding_raises():
    lease = make_lease()
    with pytest.raises(ValueError):
        lease.consume()


def test_double_consume_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.consume()
    with pytest.raises(ValueError):
        lease.consume()


def test_consume_after_expiry_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.expire()
    with pytest.raises(ValueError):
        lease.consume()


def test_expire_from_requested_and_heralded_succeeds():
    requested = make_lease()
    requested.expire()
    assert requested.state is LeaseState.EXPIRED

    heralded = make_lease()
    heralded.mark_heralded(at=1.0, fidelity=0.99)
    heralded.expire()
    assert heralded.state is LeaseState.EXPIRED


def test_expire_from_terminal_state_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.cancel()
    with pytest.raises(ValueError):
        lease.expire()


def test_cancel_from_requested_and_heralded_succeeds():
    requested = make_lease()
    requested.cancel()
    assert requested.state is LeaseState.CANCELLED

    heralded = make_lease()
    heralded.mark_heralded(at=1.0, fidelity=0.99)
    heralded.cancel()
    assert heralded.state is LeaseState.CANCELLED


def test_cancel_from_terminal_state_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.consume()
    with pytest.raises(ValueError):
        lease.cancel()


def test_is_fresh_true_within_bound():
    lease = make_lease(freshness_bound_s=5.0)
    lease.mark_heralded(at=1.0, fidelity=0.99)
    assert lease.is_fresh(now=5.0) is True


def test_is_fresh_false_after_bound():
    lease = make_lease(freshness_bound_s=5.0)
    lease.mark_heralded(at=1.0, fidelity=0.99)
    assert lease.is_fresh(now=7.0) is False


def test_is_fresh_false_if_never_heralded():
    lease = make_lease()
    assert lease.is_fresh(now=1.0) is False
