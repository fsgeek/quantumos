import pytest

from qsim.entities.round import RoundState, SyndromeRound


def make_round() -> SyndromeRound:
    return SyndromeRound(
        round_id="round-1",
        lease_ids=["lease-1", "lease-2"],
        qubit_ids=["q-1", "q-2"],
        arrival_time=0.0,
        deadline=10.0,
    )


def test_round_starts_pending():
    r = make_round()
    assert r.state is RoundState.PENDING
    assert r.retry_ordinal == 0


def test_admit_from_pending_succeeds():
    r = make_round()
    r.admit()
    assert r.state is RoundState.ADMITTED


def test_admit_twice_raises():
    r = make_round()
    r.admit()
    with pytest.raises(ValueError):
        r.admit()


def test_defer_from_pending_succeeds():
    r = make_round()
    r.defer()
    assert r.state is RoundState.DEFERRED


def test_drop_from_pending_succeeds():
    r = make_round()
    r.drop()
    assert r.state is RoundState.DROPPED


def test_defer_from_non_pending_raises():
    r = make_round()
    r.admit()
    with pytest.raises(ValueError):
        r.defer()


def test_complete_in_deadline_requires_admitted():
    r = make_round()
    with pytest.raises(ValueError):
        r.complete_in_deadline()
    r.admit()
    r.complete_in_deadline()
    assert r.state is RoundState.COMPLETED_IN_DEADLINE


def test_complete_late_requires_admitted():
    r = make_round()
    with pytest.raises(ValueError):
        r.complete_late()
    r.admit()
    r.complete_late()
    assert r.state is RoundState.COMPLETED_LATE


def test_fail_requires_admitted():
    r = make_round()
    with pytest.raises(ValueError):
        r.fail()
    r.admit()
    r.fail()
    assert r.state is RoundState.FAILED


def test_is_terminal_for_terminal_and_nonterminal_states():
    pending = make_round()
    assert pending.is_terminal() is False

    admitted = make_round()
    admitted.admit()
    assert admitted.is_terminal() is False

    dropped = make_round()
    dropped.drop()
    assert dropped.is_terminal() is True

    failed = make_round()
    failed.admit()
    failed.fail()
    assert failed.is_terminal() is True
