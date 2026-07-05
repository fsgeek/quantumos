"""tests/policies/test_protocol.py — Scheduler protocol and shared value types (design spec §8)."""
from __future__ import annotations

from qsim.policies.protocol import (
    AdmissionDecision,
    AdmissionOutcome,
    DispositionKind,
    LeaseDisposition,
    LeaseRequest,
    LeaseRequestPurpose,
    ProjectableLease,
    RoundProjection,
    Scheduler,
)


def test_admission_outcome_has_admit_and_defer_members():
    assert AdmissionOutcome.ADMIT is not AdmissionOutcome.DEFER


def test_admission_decision_defaults_projection_fields_to_none():
    decision = AdmissionDecision(outcome=AdmissionOutcome.DEFER)
    assert decision.projected_success_probability is None
    assert decision.theta_admit is None
    assert decision.deadline_slack_s is None
    assert decision.decoder_latency_s_estimate is None


def test_lease_request_purpose_distinguishes_round_from_pool_replenish():
    assert LeaseRequestPurpose.ROUND is not LeaseRequestPurpose.POOL_REPLENISH


def test_lease_request_carries_identity_and_purpose():
    request = LeaseRequest(
        request_id="req-1", path_id="pathA", coherence_class="electron",
        purpose=LeaseRequestPurpose.ROUND, requested_at_s=0.0, round_id="r1",
    )
    assert request.round_id == "r1"


def test_disposition_kind_distinguishes_cancelled_pooled_and_expired():
    assert len({DispositionKind.CANCELLED, DispositionKind.RETURNED_TO_POOL,
                DispositionKind.EXPIRED}) == 3


def test_lease_disposition_is_positional_path_coherence_kind():
    disposition = LeaseDisposition("pathA", "electron", DispositionKind.EXPIRED)
    assert disposition.kind is DispositionKind.EXPIRED


def test_projectable_lease_defaults_to_not_held_not_consumed():
    lease = ProjectableLease(path_id="pathA", coherence_class="electron")
    assert lease.is_held is False
    assert lease.is_consumed is False


def test_round_projection_defaults_leases_and_qubits_to_empty_lists():
    round_ = RoundProjection(round_id="r1", deadline_s=10.0)
    assert round_.leases == []
    assert round_.qubits == []


def test_scheduler_protocol_is_structurally_satisfied_by_a_minimal_implementation():
    class _MinimalScheduler:
        def decide_admission(self, round_projection, now_s, decoder_backlog=0, epoch=None):
            return AdmissionDecision(outcome=AdmissionOutcome.ADMIT)

        def next_lease_request(self, now_s):
            return None

        def on_round_terminal(self, round_projection, succeeded, now_s):
            return []

        def register_round_demand(self, round_projection, now_s):
            return None

    assert isinstance(_MinimalScheduler(), Scheduler)
