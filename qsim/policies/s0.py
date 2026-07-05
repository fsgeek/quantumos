"""S0Scheduler: the competent baseline (design spec §8).

Deadline-based admission, earliest-deadline-first lease-request ordering,
and round-bound lease cancellation on termination (§5's cleanup cascade for
non-pooling policies) — everything a good real-time engineer builds without
the perishability insight. Composes as the terminal base class in the mixin
chain: `S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler)`.
`S0Scheduler.__init__` is the MRO chain's terminus: it accepts and discards
any stray `**kwargs` the mixins pass down, rather than forwarding them to
`object.__init__`, which raises on unexpected keyword arguments.
"""
from __future__ import annotations

import heapq
import itertools
from typing import TYPE_CHECKING

from qsim.policies.protocol import (
    AdmissionDecision,
    AdmissionOutcome,
    DispositionKind,
    LeaseDisposition,
    LeaseRequest,
    LeaseRequestPurpose,
)

if TYPE_CHECKING:
    from qsim.entities import CalibrationEpoch
    from qsim.policies.protocol import RoundProjection


class S0Scheduler:
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self._pending: list[tuple[float, int, LeaseRequest]] = []
        self._sequence = itertools.count()

    def decide_admission(self, round_projection: RoundProjection, now_s: float,
                          decoder_backlog: int = 0,
                          epoch: CalibrationEpoch | None = None) -> AdmissionDecision:
        if now_s >= round_projection.deadline_s:
            return AdmissionDecision(outcome=AdmissionOutcome.DEFER,
                                      reason="past deadline at admission time")
        return AdmissionDecision(outcome=AdmissionOutcome.ADMIT)

    def register_round_demand(self, round_projection: RoundProjection, now_s: float) -> None:
        for lease in round_projection.leases:
            if lease.is_held:
                continue
            self._enqueue(round_projection.round_id, round_projection.deadline_s,
                          lease.path_id, lease.coherence_class, now_s)

    def next_lease_request(self, now_s: float) -> LeaseRequest | None:
        if not self._pending:
            return None
        _, _, request = heapq.heappop(self._pending)
        return request

    def on_round_terminal(self, round_projection: RoundProjection, succeeded: bool,
                           now_s: float) -> list[LeaseDisposition]:
        dispositions: list[LeaseDisposition] = []
        for lease in round_projection.leases:
            if lease.is_held and not lease.is_consumed:
                dispositions.append(LeaseDisposition(
                    lease.path_id, lease.coherence_class, DispositionKind.CANCELLED))
        return dispositions

    def _enqueue(self, round_id: str, deadline_s: float, path_id: str,
                 coherence_class: str, now_s: float) -> None:
        seq = next(self._sequence)
        request = LeaseRequest(
            request_id=f"round-{round_id}-{path_id}-{coherence_class}-{seq}",
            path_id=path_id,
            coherence_class=coherence_class,
            purpose=LeaseRequestPurpose.ROUND,
            requested_at_s=now_s,
            round_id=round_id,
        )
        heapq.heappush(self._pending, (deadline_s, seq, request))
