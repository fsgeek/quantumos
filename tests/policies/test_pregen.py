"""tests/policies/test_pregen.py — PregenMixin pool + §5 cascade (design spec §8.2)."""
from dataclasses import dataclass, field

from qsim.policies.protocol import DispositionKind, LeaseRequestPurpose
from qsim.policies.pregen import PregenMixin
from qsim.policies.s0 import S0Scheduler


@dataclass
class _FakeLease:
    path_id: str
    coherence_class: str
    is_held: bool = False
    is_consumed: bool = False
    state_held_since: float | None = None
    freshness_bound_s: float = 1.0
    heralded_fidelity_estimate: float | None = None


@dataclass
class _FakeRound:
    round_id: str
    deadline_s: float
    leases: list = field(default_factory=list)
    qubits: list = field(default_factory=list)


class _S0WithPregen(PregenMixin, S0Scheduler):
    pass


KEY = ("pathA", "electron")


def test_next_lease_request_triggers_pool_replenish_below_low_water_mark():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])

    request = scheduler.next_lease_request(now_s=0.0)

    assert request is not None
    assert request.purpose is LeaseRequestPurpose.POOL_REPLENISH
    assert request.path_id == "pathA"
    assert request.coherence_class == "electron"
    assert request.round_id is None


def test_next_lease_request_does_not_trigger_at_exactly_low_water_mark():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])
    scheduler.deposit_to_pool(_FakeLease(path_id="pathA", coherence_class="electron", is_held=True))
    scheduler.deposit_to_pool(_FakeLease(path_id="pathA", coherence_class="electron", is_held=True))

    assert scheduler.pool_depth(KEY) == 2
    assert scheduler.next_lease_request(now_s=0.0) is None


def test_round_bound_demand_takes_priority_over_pool_replenish():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])
    lease = _FakeLease(path_id="pathB", coherence_class="nuclear", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[lease])
    scheduler.register_round_demand(round_, now_s=0.0)

    request = scheduler.next_lease_request(now_s=0.0)

    assert request.purpose is LeaseRequestPurpose.ROUND
    assert request.path_id == "pathB"


def test_on_round_terminal_returns_fresh_leases_to_pool():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    fresh = _FakeLease(path_id="pathA", coherence_class="electron",
                        is_held=True, is_consumed=False,
                        state_held_since=4.0, freshness_bound_s=1.0)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[fresh])

    dispositions = scheduler.on_round_terminal(round_, succeeded=False, now_s=4.5)  # age 0.5 <= 1.0

    assert len(dispositions) == 1
    assert dispositions[0].kind is DispositionKind.RETURNED_TO_POOL
    assert scheduler.pool_depth(KEY) == 1


def test_on_round_terminal_expires_stale_leases_without_pooling_them():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    stale = _FakeLease(path_id="pathA", coherence_class="electron",
                        is_held=True, is_consumed=False,
                        state_held_since=0.0, freshness_bound_s=1.0)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[stale])

    dispositions = scheduler.on_round_terminal(round_, succeeded=False, now_s=5.0)  # age 5.0 > 1.0

    assert len(dispositions) == 1
    assert dispositions[0].kind is DispositionKind.EXPIRED
    assert scheduler.pool_depth(KEY) == 0


def test_on_round_terminal_never_makes_an_undeclared_key_actively_replenished():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])
    scheduler.deposit_to_pool(_FakeLease(path_id="pathA", coherence_class="electron", is_held=True))
    scheduler.deposit_to_pool(_FakeLease(path_id="pathA", coherence_class="electron", is_held=True))
    assert scheduler.next_lease_request(now_s=0.0) is None  # tracked KEY already at its mark

    untracked = _FakeLease(path_id="pathB", coherence_class="nuclear",
                            is_held=True, is_consumed=False,
                            state_held_since=4.0, freshness_bound_s=1.0)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[untracked])

    dispositions = scheduler.on_round_terminal(round_, succeeded=False, now_s=4.5)  # fresh: age 0.5 <= 1.0

    assert len(dispositions) == 1
    assert dispositions[0].path_id == "pathB"
    assert dispositions[0].coherence_class == "nuclear"
    assert dispositions[0].kind is DispositionKind.CANCELLED  # deferred to the base scheduler, not pooled

    # An undeclared (path, coherence) pair must never become an actively
    # low-water-mark-replenished pool, even after a fresh lease for it passes
    # through on_round_terminal.
    assert scheduler.next_lease_request(now_s=5.0) is None


def test_deposit_to_pool_ignores_undeclared_keys():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    scheduler.deposit_to_pool(_FakeLease(path_id="pathB", coherence_class="nuclear", is_held=True))

    assert scheduler.pool_depth(("pathB", "nuclear")) == 0
    assert scheduler.withdraw_from_pool(("pathB", "nuclear")) is None


def test_withdraw_from_pool_returns_leases_in_fifo_order_and_decrements_depth():
    scheduler = _S0WithPregen(low_water_mark=0, tracked_keys=[KEY])
    first = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True)
    second = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True)
    scheduler.deposit_to_pool(first)
    scheduler.deposit_to_pool(second)
    assert scheduler.pool_depth(KEY) == 2

    withdrawn_first = scheduler.withdraw_from_pool(KEY)

    assert withdrawn_first is first
    assert scheduler.pool_depth(KEY) == 1

    withdrawn_second = scheduler.withdraw_from_pool(KEY)

    assert withdrawn_second is second
    assert scheduler.pool_depth(KEY) == 0


def test_withdraw_from_pool_returns_none_when_pool_is_empty():
    scheduler = _S0WithPregen(low_water_mark=0, tracked_keys=[KEY])

    assert scheduler.withdraw_from_pool(KEY) is None


def test_withdraw_from_pool_returns_none_for_undeclared_key():
    scheduler = _S0WithPregen(low_water_mark=0, tracked_keys=[KEY])

    assert scheduler.withdraw_from_pool(("pathZ", "nuclear")) is None


def test_below_low_water_mark_mints_exactly_one_replenish_per_key_while_in_flight():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])

    first = scheduler.next_lease_request(now_s=0.0)
    assert first is not None
    assert first.purpose is LeaseRequestPurpose.POOL_REPLENISH

    # The attempt is in flight: depth(0) + in_flight(1) == L(1), so no second
    # mint — the unbounded-drain hazard (run.py:24-30) is bounded by L itself.
    assert scheduler.next_lease_request(now_s=0.0) is None


def test_trigger_is_depth_plus_in_flight_strictly_below_low_water_mark():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])
    scheduler.deposit_to_pool(_FakeLease(path_id="pathA", coherence_class="electron", is_held=True))

    # depth(1) + in_flight(0) == 1 < 2: mints once...
    assert scheduler.next_lease_request(now_s=0.0) is not None
    # ...then depth(1) + in_flight(1) == 2 == L: no trigger at exactly L.
    assert scheduler.next_lease_request(now_s=0.0) is None


def test_on_pool_replenish_outcome_success_deposits_and_decrements_in_flight():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    assert scheduler.next_lease_request(now_s=0.0) is not None  # in flight

    lease = _FakeLease(path_id="pathA", coherence_class="electron",
                       is_held=True, state_held_since=0.5)
    scheduler.on_pool_replenish_outcome(KEY, True, lease, now_s=0.5)

    assert scheduler.pool_depth(KEY) == 1
    # depth(1) + in_flight(0) == 1 == L: satisfied, no further mint.
    assert scheduler.next_lease_request(now_s=0.5) is None


def test_on_pool_replenish_outcome_failure_decrements_and_re_arms_minting():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    assert scheduler.next_lease_request(now_s=0.0) is not None  # in flight
    assert scheduler.next_lease_request(now_s=0.0) is None

    scheduler.on_pool_replenish_outcome(KEY, False, None, now_s=0.5)

    assert scheduler.pool_depth(KEY) == 0
    # The failed attempt released its in-flight slot: the low-water condition
    # re-fires at the next drain opportunity.
    request = scheduler.next_lease_request(now_s=0.5)
    assert request is not None
    assert request.purpose is LeaseRequestPurpose.POOL_REPLENISH


def test_round_bound_demand_still_takes_priority_while_replenish_is_in_flight():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])
    assert scheduler.next_lease_request(now_s=0.0).purpose is LeaseRequestPurpose.POOL_REPLENISH

    lease = _FakeLease(path_id="pathB", coherence_class="nuclear", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[lease])
    scheduler.register_round_demand(round_, now_s=0.0)

    assert scheduler.next_lease_request(now_s=0.0).purpose is LeaseRequestPurpose.ROUND


def test_on_round_terminal_skips_consumed_and_never_held_leases():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    consumed = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True, is_consumed=True)
    never_held = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False, is_consumed=False)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[consumed, never_held])

    dispositions = scheduler.on_round_terminal(round_, succeeded=True, now_s=1.0)

    assert dispositions == []
    assert scheduler.pool_depth(KEY) == 0
