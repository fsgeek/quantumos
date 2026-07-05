"""tests/policies/test_s0.py — S0Scheduler, the competent baseline (design spec §8)."""
from __future__ import annotations

from dataclasses import dataclass, field

from qsim.policies.protocol import (
    AdmissionOutcome,
    DispositionKind,
    LeaseRequestPurpose,
    Scheduler,
)
from qsim.policies.s0 import S0Scheduler


@dataclass
class _FakeLease:
    path_id: str
    coherence_class: str
    is_held: bool = False
    is_consumed: bool = False


@dataclass
class _FakeRound:
    round_id: str
    deadline_s: float
    leases: list = field(default_factory=list)
    qubits: list = field(default_factory=list)


def test_s0_scheduler_requires_no_constructor_arguments():
    assert isinstance(S0Scheduler(), Scheduler)


def test_s0_scheduler_swallows_stray_kwargs_as_the_mro_chains_terminal_init():
    # S0Scheduler is the terminal __init__ in the mixin MRO chain; it must
    # not forward unexpected kwargs to object.__init__, which would raise.
    assert isinstance(S0Scheduler(unexpected_kwarg="ignored"), S0Scheduler)


def test_decide_admission_defers_at_or_after_deadline_with_no_projection_fields():
    scheduler = S0Scheduler()
    round_ = _FakeRound(round_id="r1", deadline_s=10.0)

    decision = scheduler.decide_admission(round_, now_s=10.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER
    assert decision.projected_success_probability is None


def test_decide_admission_admits_before_deadline():
    scheduler = S0Scheduler()
    round_ = _FakeRound(round_id="r1", deadline_s=10.0)

    decision = scheduler.decide_admission(round_, now_s=1.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.ADMIT


def test_next_lease_request_is_none_with_no_registered_demand():
    assert S0Scheduler().next_lease_request(now_s=0.0) is None


def test_next_lease_request_serves_unheld_leases_in_earliest_deadline_first_order():
    scheduler = S0Scheduler()
    urgent = _FakeRound(round_id="urgent", deadline_s=5.0,
                         leases=[_FakeLease(path_id="pathA", coherence_class="electron")])
    relaxed = _FakeRound(round_id="relaxed", deadline_s=50.0,
                          leases=[_FakeLease(path_id="pathB", coherence_class="nuclear")])
    scheduler.register_round_demand(relaxed, now_s=0.0)
    scheduler.register_round_demand(urgent, now_s=0.0)

    first = scheduler.next_lease_request(now_s=0.0)

    assert first.path_id == "pathA"
    assert first.purpose is LeaseRequestPurpose.ROUND
    assert first.round_id == "urgent"


def test_register_round_demand_does_not_request_already_held_leases():
    scheduler = S0Scheduler()
    round_ = _FakeRound(round_id="r1", deadline_s=5.0,
                         leases=[_FakeLease(path_id="pathA", coherence_class="electron", is_held=True)])
    scheduler.register_round_demand(round_, now_s=0.0)

    assert scheduler.next_lease_request(now_s=0.0) is None


def test_on_round_terminal_cancels_held_unconsumed_leases():
    scheduler = S0Scheduler()
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True, is_consumed=False)
    round_ = _FakeRound(round_id="r1", deadline_s=5.0, leases=[lease])

    dispositions = scheduler.on_round_terminal(round_, succeeded=False, now_s=1.0)

    assert len(dispositions) == 1
    assert dispositions[0].kind is DispositionKind.CANCELLED


def test_on_round_terminal_skips_consumed_and_never_held_leases():
    scheduler = S0Scheduler()
    consumed = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True, is_consumed=True)
    never_held = _FakeLease(path_id="pathB", coherence_class="nuclear", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=5.0, leases=[consumed, never_held])

    assert scheduler.on_round_terminal(round_, succeeded=True, now_s=1.0) == []
