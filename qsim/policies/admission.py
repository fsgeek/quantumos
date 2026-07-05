"""AdmissionMixin: freshness-aware admission control (design spec §8.1).

Composes with any base Scheduler that implements `decide_admission`
(policies/s0.py's S0Scheduler in v1) via cooperative multiple inheritance:
this mixin defers to the base class's decision first (e.g. S0's
already-past-deadline check) and only computes the §8.1 projection when the
base class has not already deferred.

Type-contract note (flagged for Task 8 Scheduler-protocol reconciliation):
`ProjectableLease.path_id`/`coherence_class` (qsim.policies.protocol, Task 1)
are declared `str`, but this mixin forwards them verbatim as the `path`/
`coherence` arguments of `HeraldingModel.heralded_fidelity` and
`DecayModel.retention`. The real v1 model implementations
(qsim.models.heralding, qsim.models.decay) key their calibration-epoch
lookups by `PathId` tuples and `CoherenceClass` enum members, not by str.
This mixin makes no assumption about the concrete type of `path_id`/
`coherence_class` — it only forwards whatever it is given — so it will
work correctly once the engine populates `ProjectableLease` with the real
`PathId`/`CoherenceClass` values; but if it is populated with plain `str`
(per the field's current declared type), every real admission call will
KeyError inside the v1 models. Whoever reconciles the Scheduler protocol at
Task 8 must ensure `ProjectableLease` instances are built with the real
`PathId`/`CoherenceClass` values, not strings (and update the field types in
protocol.py accordingly).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from qsim.policies.protocol import AdmissionDecision, AdmissionOutcome

if TYPE_CHECKING:
    from qsim.entities import CalibrationEpoch
    from qsim.models.protocols import (
        DecayModel,
        DecoderServiceModel,
        HeraldingModel,
        MemoryAccessModel,
        RoundSuccessModel,
    )
    from qsim.policies.protocol import RoundProjection


class AdmissionMixin:
    def __init__(self, *, theta_admit: float, decay_model: DecayModel,
                 heralding_model: HeraldingModel,
                 memory_access_model: MemoryAccessModel,
                 round_success_model: RoundSuccessModel,
                 decoder_service_model: DecoderServiceModel,
                 **kwargs) -> None:
        super().__init__(decoder_service_model=decoder_service_model, **kwargs)
        self._theta_admit = theta_admit
        self._decay_model = decay_model
        self._heralding_model = heralding_model
        self._memory_access_model = memory_access_model
        self._round_success_model = round_success_model
        self._admission_decoder_service_model = decoder_service_model

    def decide_admission(self, round_projection: RoundProjection, now_s: float,
                          decoder_backlog: int = 0,
                          epoch: CalibrationEpoch | None = None) -> AdmissionDecision:
        base = super().decide_admission(round_projection, now_s, decoder_backlog, epoch)
        if base.outcome is AdmissionOutcome.DEFER:
            return base

        decoder_latency_s = self._admission_decoder_service_model.expected_service_time_s(decoder_backlog, epoch)
        # v1 simplification (flagged, not specified by §8.1): projected time
        # from `now_s` to consumption is approximated as decoder_latency_s
        # alone; a richer projected_time_to_consumption term (heralding
        # attempt time, queueing ahead of decode) is future work.
        consumption_instant_s = now_s + decoder_latency_s

        lease_fidelities: list[float] = []
        for lease in round_projection.leases:
            if lease.is_held and lease.state_held_since is not None:
                age_s = consumption_instant_s - lease.state_held_since
                base_fidelity = lease.heralded_fidelity_estimate
            else:
                age_s = consumption_instant_s - now_s
                # lease.path_id is forwarded verbatim: must be the real PathId
                # the wired HeraldingModel keys on, not a str (see module docstring).
                base_fidelity = self._heralding_model.heralded_fidelity(lease.path_id, epoch)
            # lease.coherence_class is forwarded verbatim: must be the real
            # CoherenceClass the wired DecayModel keys on, not a str (see
            # module docstring).
            retention = self._decay_model.retention(max(age_s, 0.0), lease.coherence_class, epoch)
            lease_fidelities.append(base_fidelity * retention)

        memory_retentions: list[float] = []
        for qubit in round_projection.qubits:
            access_cost = self._memory_access_model.access_cost(qubit, epoch)
            # qubit.coherence_class is forwarded verbatim: same type-contract
            # caveat as lease.coherence_class above.
            decay_to_access = self._decay_model.retention(
                max(consumption_instant_s - now_s, 0.0), qubit.coherence_class, epoch)
            memory_retentions.append(access_cost.retention_factor * decay_to_access)

        deadline_slack_s = round_projection.deadline_s - consumption_instant_s
        projected_p = self._round_success_model.success_probability(
            lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s)

        outcome = AdmissionOutcome.ADMIT if projected_p >= self._theta_admit else AdmissionOutcome.DEFER
        return AdmissionDecision(
            outcome=outcome,
            projected_success_probability=projected_p,
            theta_admit=self._theta_admit,
            deadline_slack_s=deadline_slack_s,
            decoder_latency_s_estimate=decoder_latency_s,
            reason=f"projected p={projected_p!r} vs theta_admit={self._theta_admit!r}",
        )
