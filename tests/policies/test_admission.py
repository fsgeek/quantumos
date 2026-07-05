"""tests/policies/test_admission.py — AdmissionMixin projection gate (design spec §8.1)."""
from __future__ import annotations

from dataclasses import dataclass, field

from qsim.entities import CoherenceClass, PortId, make_path_id
from qsim.policies.admission import AdmissionMixin
from qsim.policies.protocol import AdmissionOutcome
from qsim.policies.s0 import S0Scheduler

# Real PathId/CoherenceClass values, not arbitrary placeholder strings: the
# real v1 models (qsim.models.heralding, qsim.models.decay) key their
# calibration-epoch dict lookups on these types, so exercising AdmissionMixin
# with them (rather than with strings that happen not to collide with the
# real CoherenceClass enum values) verifies the mixin forwards them correctly
# and doesn't accidentally assume `str`. See admission.py's module docstring
# for the associated type-contract flag.
_PATH_A = make_path_id(PortId("m0", 0), PortId("m1", 0))
_MESSENGER = CoherenceClass.MESSENGER


@dataclass
class _FakeLease:
    path_id: object
    coherence_class: object
    is_held: bool = False
    state_held_since: float | None = None
    heralded_fidelity_estimate: float | None = None


@dataclass
class _FakeRound:
    round_id: str
    deadline_s: float
    leases: list = field(default_factory=list)
    qubits: list = field(default_factory=list)


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


@dataclass
class _FakeAccessCost:
    electron_channel_s: float
    retention_factor: float


class _ConstantMemoryAccess:
    def __init__(self, retention_factor: float) -> None:
        self._retention_factor = retention_factor

    def access_cost(self, qubit, epoch):
        return _FakeAccessCost(electron_channel_s=0.0, retention_factor=self._retention_factor)


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


def _make_scheduler(*, theta_admit: float, heralded_fidelity: float) -> AdmissionMixin:
    class _Scheduler(AdmissionMixin, S0Scheduler):
        pass

    return _Scheduler(
        theta_admit=theta_admit,
        decay_model=_ConstantDecay(1.0),
        heralding_model=_ConstantHeralding(heralded_fidelity),
        memory_access_model=_ConstantMemoryAccess(1.0),
        round_success_model=_MinFidelityRoundSuccess(),
        decoder_service_model=_ZeroLatencyDecoderService(),
    )


def test_admits_when_projected_success_probability_exceeds_theta_admit():
    scheduler = _make_scheduler(theta_admit=0.9, heralded_fidelity=0.95)
    lease = _FakeLease(path_id=_PATH_A, coherence_class=_MESSENGER, is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.ADMIT
    assert decision.projected_success_probability == 0.95
    assert decision.theta_admit == 0.9


def test_defers_when_projected_success_probability_is_below_theta_admit():
    scheduler = _make_scheduler(theta_admit=0.9, heralded_fidelity=0.5)
    lease = _FakeLease(path_id=_PATH_A, coherence_class=_MESSENGER, is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER
    assert decision.projected_success_probability == 0.5


def test_projection_uses_held_lease_age_from_state_held_since_not_heralding_model():
    # Already-held lease: fidelity must come from heralded_fidelity_estimate
    # decayed from state_held_since, NOT re-queried from HeraldingModel.
    scheduler = _make_scheduler(theta_admit=0.5, heralded_fidelity=0.1)  # would fail if (mis)used
    lease = _FakeLease(
        path_id=_PATH_A, coherence_class=_MESSENGER,
        is_held=True, state_held_since=0.0, heralded_fidelity_estimate=0.99,
    )
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.projected_success_probability == 0.99


def test_defers_at_theta_admit_boundary_when_strictly_below():
    scheduler = _make_scheduler(theta_admit=0.95, heralded_fidelity=0.9499999999999999)
    lease = _FakeLease(path_id=_PATH_A, coherence_class=_MESSENGER, is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER


def test_admits_exactly_at_theta_admit_boundary():
    scheduler = _make_scheduler(theta_admit=0.9, heralded_fidelity=0.9)
    lease = _FakeLease(path_id=_PATH_A, coherence_class=_MESSENGER, is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.ADMIT


def test_base_scheduler_deadline_defer_short_circuits_before_projection():
    scheduler = _make_scheduler(theta_admit=0.0, heralded_fidelity=1.0)  # would always admit if projected
    lease = _FakeLease(path_id=_PATH_A, coherence_class=_MESSENGER, is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=10.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER
    assert decision.projected_success_probability is None  # never computed


# --- memory-qubit projection branch (§8.1): round_projection.qubits ---------
# The above fixtures all leave qubits empty, so the MemoryAccessModel +
# DecayModel-on-qubits path of decide_admission never runs. These exercise it
# and prove a memory qubit's retention actually enters the projection and can
# change the admission outcome.


@dataclass
class _FakeQubit:
    coherence_class: object


class _MinAllRoundSuccess:
    """Success = min over BOTH lease fidelities and memory retentions, so a
    low memory retention can dominate the projection (unlike
    _MinFidelityRoundSuccess, which ignores memory_retentions)."""

    def success_probability(self, lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s):
        if deadline_slack_s <= 0:
            return 0.0
        vals = list(lease_fidelities) + list(memory_retentions)
        return min(vals) if vals else 1.0


def _make_scheduler_with_memory(*, theta_admit: float, heralded_fidelity: float,
                                mem_retention_factor: float) -> AdmissionMixin:
    class _Scheduler(AdmissionMixin, S0Scheduler):
        pass

    return _Scheduler(
        theta_admit=theta_admit,
        decay_model=_ConstantDecay(1.0),
        heralding_model=_ConstantHeralding(heralded_fidelity),
        memory_access_model=_ConstantMemoryAccess(mem_retention_factor),
        round_success_model=_MinAllRoundSuccess(),
        decoder_service_model=_ZeroLatencyDecoderService(),
    )


def test_memory_qubit_low_retention_enters_projection_and_forces_defer():
    # lease fidelity is fine (0.95) but the memory qubit retention (0.3) must
    # drag the projected probability down through the qubits branch.
    scheduler = _make_scheduler_with_memory(theta_admit=0.5, heralded_fidelity=0.95, mem_retention_factor=0.3)
    lease = _FakeLease(path_id=_PATH_A, coherence_class=_MESSENGER, is_held=False)
    qubit = _FakeQubit(coherence_class=CoherenceClass.MEMORY)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease], qubits=[qubit])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER
    assert decision.projected_success_probability == 0.3


def test_memory_qubit_high_retention_does_not_block_admission():
    scheduler = _make_scheduler_with_memory(theta_admit=0.5, heralded_fidelity=0.95, mem_retention_factor=0.9)
    lease = _FakeLease(path_id=_PATH_A, coherence_class=_MESSENGER, is_held=False)
    qubit = _FakeQubit(coherence_class=CoherenceClass.MEMORY)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease], qubits=[qubit])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.ADMIT
    assert decision.projected_success_probability == 0.9
