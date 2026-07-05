"""tests/policies/test_s1.py — S1Scheduler composability and joint behavior."""
from dataclasses import dataclass, field

from qsim.policies.admission import AdmissionMixin
from qsim.policies.pregen import PregenMixin
from qsim.policies.protocol import AdmissionOutcome, LeaseRequestPurpose
from qsim.policies.s0 import S0Scheduler
from qsim.policies.s1 import S1Scheduler


@dataclass
class _FakeAccessCost:
    electron_channel_s: float
    retention_factor: float


class _ConstantDecay:
    def __init__(self, retention: float) -> None:
        self._retention = retention

    def retention(self, age_s, coherence_class, epoch):
        return self._retention


class _ConstantHeralding:
    def __init__(self, fidelity: float) -> None:
        self._fidelity = fidelity

    def heralded_fidelity(self, path, epoch):
        return self._fidelity

    def success_probability(self, path, epoch):
        return 1.0


class _ConstantMemoryAccess:
    def access_cost(self, qubit, epoch):
        return _FakeAccessCost(electron_channel_s=0.0, retention_factor=1.0)


class _MinFidelityRoundSuccess:
    def success_probability(self, lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s):
        if deadline_slack_s <= 0:
            return 0.0
        return min(lease_fidelities) if lease_fidelities else 1.0


class _ZeroLatencyDecoderService:
    def expected_service_time_s(self, backlog, epoch):
        return 0.0

    def service_time_s(self, job, backlog, draw):
        return 0.0


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


KEY = ("pathA", "electron")


def _make_s1(theta_admit: float, heralded_fidelity: float, low_water_mark: int) -> S1Scheduler:
    return S1Scheduler(
        theta_admit=theta_admit,
        decay_model=_ConstantDecay(1.0),
        heralding_model=_ConstantHeralding(heralded_fidelity),
        memory_access_model=_ConstantMemoryAccess(),
        round_success_model=_MinFidelityRoundSuccess(),
        decoder_service_model=_ZeroLatencyDecoderService(),
        low_water_mark=low_water_mark,
        tracked_keys=[KEY],
    )


def test_s1_is_composed_from_the_three_named_classes_not_a_rewrite():
    assert S0Scheduler in S1Scheduler.__mro__
    assert AdmissionMixin in S1Scheduler.__mro__
    assert PregenMixin in S1Scheduler.__mro__


def test_s1_admission_gate_matches_standalone_admission_mixin_behavior():
    admits = _make_s1(theta_admit=0.9, heralded_fidelity=0.95, low_water_mark=0)
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = admits.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)
    assert decision.outcome is AdmissionOutcome.ADMIT

    defers = _make_s1(theta_admit=0.9, heralded_fidelity=0.5, low_water_mark=0)
    decision2 = defers.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)
    assert decision2.outcome is AdmissionOutcome.DEFER


def test_s1_pool_replenish_triggers_when_no_round_bound_demand_pending():
    scheduler = _make_s1(theta_admit=0.0, heralded_fidelity=1.0, low_water_mark=1)

    request = scheduler.next_lease_request(now_s=0.0)

    assert request is not None
    assert request.purpose is LeaseRequestPurpose.POOL_REPLENISH


def test_s1_round_terminal_disposal_cascade_returns_fresh_lease_to_pool():
    scheduler = _make_s1(theta_admit=0.0, heralded_fidelity=1.0, low_water_mark=1)
    fresh = _FakeLease(path_id="pathA", coherence_class="electron",
                        is_held=True, is_consumed=False,
                        state_held_since=0.0, freshness_bound_s=10.0)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[fresh])

    scheduler.on_round_terminal(round_, succeeded=False, now_s=1.0)

    assert scheduler.pool_depth(KEY) == 1
