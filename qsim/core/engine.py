"""The DES run loop implementing §4's end-to-end data flow.

Engine unit E1 covers Task 1 (DES loop, reconciled admission, arrival
dispatch) and Task 2 (path allocation and switch-reservation lifecycle).

This module is written against the AUTHORITATIVE reconciliation spec
(.superpowers/sdd/engine-reconciliation-spec.md), which OVERRIDES the
engine-task briefs wherever they conflict. Concretely, the engine no longer
calls the placeholder scheduler methods (`on_round_request`,
`allocate_path`, `on_lease_heralded`); it builds a `RoundProjection` and
calls the real Scheduler protocol (`decide_admission`,
`register_round_demand`, `next_lease_request`, `on_round_terminal`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from qsim.core.event_heap import EventHeap
from qsim.core.invariants import InvariantChecker
from qsim.core.rng import Draw, draw_uniform
from qsim.core.state import EngineState, ModelBundle
from qsim.core.trace import Event, EventId, TraceBus
from qsim.entities import (
    CoherenceClass,
    DecoderJob,
    EntanglementLease,
    LeaseState,
    PathId,
    PortId,
    QubitHandle,
    ReservationState,
    RoundState,
    SwitchPathReservation,
    SyndromeRound,
    make_path_id,
)
from qsim.policies.protocol import (
    AdmissionOutcome,
    DispositionKind,
    LeaseRequest,
    ProjectableLease,
    RoundProjection,
    Scheduler,
)
from qsim.workload.generator import WorkloadGenerator

if TYPE_CHECKING:
    from qsim.experiments.config import RunConfig

# M0 minimal: entanglement leases are all messenger-class. Memory-role qubits
# (which would be MEMORY) are not modelled as round leases in M0 — the
# projection's `qubits` list is left empty. Flagged for the task that
# introduces memory-role qubits.
_LEASE_COHERENCE = CoherenceClass.MESSENGER

# M0 minimal freshness bound for a synthesized lease. RunConfig carries no
# per-lease freshness field, so we fall back to the round's deadline slack as a
# sensible bound (S0 ignores it; it only matters once AdmissionMixin/S1 is
# wired, which is out of scope for this unit). Flagged as a contract gap.
_RETRY_STREAM = "retry"

# Task-local (engine-task-3 brief): the gap between two failed heralding
# attempts on the same path. Heralding is Bernoulli-per-attempt; a failed
# attempt reschedules the next one a short positive interval later so the DES
# makes forward progress (a zero-delay retry loop would busy-spin under p<1).
HERALD_RETRY_INTERVAL_S = 1e-4


def _synthesize_ports(switch_capacity_c: int) -> list[PortId]:
    """Task-local topology synthesis. The frozen contract's RunConfig has no
    port/module topology field; this fills that gap deterministically so §7
    endpoint-exclusivity has something concrete to contend over. Flagged as
    a contract gap for the experiments/entities sections to reconcile."""
    count = max(2, switch_capacity_c * 2)
    return [PortId(module_id=f"M{i}", port_index=0) for i in range(count)]


@dataclass(frozen=True)
class _ArrivalPayload:
    round: SyndromeRound
    causal_parent_id: EventId | None
    is_retry: bool = False


@dataclass(frozen=True)
class _ReservationActivatePayload:
    path_id: PathId
    round_id: str
    lease_id: str
    causal_parent_id: EventId | None
    # The exact reservation this activation belongs to. Held so the handler can
    # verify by IDENTITY that the reservation still occupying the path is the
    # one this payload was scheduled for — a released-then-re-acquired path
    # otherwise lets a stale activation flip a DIFFERENT round's reservation.
    reservation: SwitchPathReservation


@dataclass(frozen=True)
class _HeraldAttemptPayload:
    round_id: str
    lease_id: str
    path_id: PathId
    endpoints: tuple[PortId, PortId]
    attempt_no: int
    causal_parent_id: EventId | None


@dataclass(frozen=True)
class _DecoderCompletionPayload:
    job_id: str
    round_id: str
    causal_parent_id: EventId | None


@dataclass
class _RoundContext:
    round: SyndromeRound
    causal_parent_id: EventId | None
    leases: dict[str, EntanglementLease] = field(default_factory=dict)
    path_to_lease: dict[PathId, str] = field(default_factory=dict)
    reservations: dict[str, SwitchPathReservation] = field(default_factory=dict)
    # Lease ids that have actually had a lease.requested event published (in
    # _acquire_path). A lease is synthesized per lease_id at admission
    # (_build_round_context) but only emits None->requested once the scheduler
    # hands it back and the fabric hosts it. The §5 terminal cascade disposes
    # ONLY requested leases: cancelling a synthesized-but-never-requested lease
    # would be an illegal None->cancelled transition the invariant rejects.
    requested: set[str] = field(default_factory=set)
    # Task 4: one synthesized memory-role QubitHandle per lease, keyed by
    # lease_id. SyndromeRound.qubit_ids is empty in M0 (the frozen
    # WorkloadGenerator emits no qubit ids), so the engine synthesizes a handle
    # per lease at arrival time. Flagged as a contract gap: no QubitHandle
    # source is wired anywhere else in M0.
    qubit_handles: dict[str, QubitHandle] = field(default_factory=dict)
    # Task 5: the single decoder job this round enqueues once all its leases
    # have heralded (None until assembly readiness).
    decoder_job: DecoderJob | None = None


class Engine:
    def __init__(self, config: "RunConfig", scheduler: Scheduler,
                 models: ModelBundle, workload: WorkloadGenerator,
                 trace: TraceBus, invariants: InvariantChecker) -> None:
        self._config = config
        self._scheduler = scheduler
        self._workload = workload
        self._trace = trace
        self._invariants = invariants
        # The TraceBus stamps every event's sim_time from the clock it was
        # constructed with, so the engine adopts THAT clock rather than
        # creating its own — otherwise published events would carry a
        # frozen-at-zero time. (Reconciliation: the frozen Engine signature
        # receives an already-constructed trace, so the clock flows in via it.)
        self._clock = trace._clock
        self._heap = EventHeap()
        self._state = EngineState(
            now=0.0,
            epoch=config.epoch,
            models=models,
            decoder_backlog=0,
            active_reservations={},
            pool={},
            switch_capacity_c=config.switch_capacity_c,
            hold_until_consumption=config.hold_until_consumption,
        )
        self._ports = _synthesize_ports(config.switch_capacity_c)
        self._port_pair_counter = 0
        self._arrival_index = 0
        self._round_contexts: dict[str, _RoundContext] = {}
        # Single-server (M/M/1) decoder: the wall-clock instant the decoder
        # becomes free. A job cannot begin service before this (see
        # _enqueue_decoder_job). Without it the decoder would be infinite-server
        # and could never become the bottleneck the design doc requires (§16.2).
        self._decoder_free_at = 0.0

    # ---- trace/invariant plumbing -------------------------------------------

    def _publish(self, event_type: str, entity_id: str,
                 causal_parent_id: EventId | None, payload: dict) -> EventId:
        event_id = self._trace.publish(event_type, entity_id, causal_parent_id, payload)
        event = Event(
            run_id=event_id[0], seq=event_id[1], sim_time=self._state.now,
            event_type=event_type, entity_id=entity_id,
            causal_parent_id=causal_parent_id, payload=payload,
        )
        self._invariants.observe(event, self._state)
        return event_id

    # ---- DES loop -----------------------------------------------------------

    def _schedule_next_arrival(self, after_time: float) -> None:
        self._arrival_index += 1
        next_round = self._workload.next_arrival(after_time, self._arrival_index)
        self._heap.push(next_round.arrival_time, _ArrivalPayload(next_round, None))

    def run_to(self, max_sim_time_s: float) -> None:
        self._schedule_next_arrival(0.0)
        while len(self._heap) > 0:
            entry = self._heap.pop()
            if entry.time > max_sim_time_s:
                break
            self._clock.advance_to(entry.time)
            self._state.now = entry.time
            self._dispatch(entry.payload)

    def _dispatch(self, payload: object) -> None:
        if isinstance(payload, _ArrivalPayload):
            self._on_arrival(payload)
        elif isinstance(payload, _ReservationActivatePayload):
            self._on_reservation_active(payload)
        elif isinstance(payload, _HeraldAttemptPayload):
            self._on_herald_attempt(payload)
        elif isinstance(payload, _DecoderCompletionPayload):
            self._on_decoder_completion(payload)
        else:
            raise TypeError(f"unknown event payload type: {type(payload)!r}")

    # ---- arrival + admission (Task 1, reconciled) ---------------------------

    def _on_arrival(self, payload: _ArrivalPayload) -> None:
        round_ = payload.round
        arrived_id = self._publish(
            "round.arrived", round_.round_id, payload.causal_parent_id,
            {"deadline": round_.deadline, "retry_ordinal": round_.retry_ordinal},
        )
        # Only genuine fresh arrivals drive the Poisson arrival stream forward;
        # a retry is the SAME round re-attempting, not a new offered arrival.
        if not payload.is_retry:
            self._schedule_next_arrival(round_.arrival_time)

        ctx = self._build_round_context(round_, arrived_id)
        self._round_contexts[round_.round_id] = ctx

        projection = self._project(ctx)
        decision = self._scheduler.decide_admission(
            projection, self._state.now, self._state.decoder_backlog, self._state.epoch,
        )
        if decision.outcome is AdmissionOutcome.ADMIT:
            round_.state = RoundState.ADMITTED
            admitted_id = self._publish("round.admitted", round_.round_id, arrived_id,
                                        {"reason": decision.reason})
            # Enqueue this round's lease requests into the scheduler's queue,
            # then drain the queue honouring the scheduler's ordering.
            self._scheduler.register_round_demand(projection, self._state.now)
            self._begin_lease_acquisition(round_, admitted_id)
        else:
            round_.state = RoundState.DEFERRED
            deferred_id = self._publish("round.deferred", round_.round_id, arrived_id,
                                        {"reason": decision.reason})
            self._retry_or_drop(round_, deferred_id)

    def _build_round_context(self, round_: SyndromeRound, arrived_id: EventId) -> _RoundContext:
        """Pre-select a path per lease at arrival time so the RoundProjection
        handed to `decide_admission` names concrete paths, and the same paths
        are reserved when the scheduler hands the requests back via
        `next_lease_request`."""
        ctx = _RoundContext(round=round_, causal_parent_id=arrived_id)
        for ordinal, lease_id in enumerate(round_.lease_ids):
            a, b = self._endpoints_for(round_.round_id, ordinal)
            path_id = make_path_id(a, b)
            lease = EntanglementLease(
                lease_id=lease_id,
                endpoints=(a, b),
                path_id=path_id,
                created_at=self._state.now,
                freshness_bound_s=self._config.deadline_slack_s,
                state=LeaseState.REQUESTED,
            )
            ctx.leases[lease_id] = lease
            ctx.path_to_lease[path_id] = lease_id
            # Task 4: synthesize the memory-role qubit this lease's state will be
            # held on. Module = the lease endpoint's module; coherence class =
            # MEMORY (the round holds heralded state in memory while it waits for
            # the rest of the round to assemble). Keyed by lease_id because M0
            # rounds carry no qubit_ids.
            ctx.qubit_handles[lease_id] = QubitHandle(
                qubit_id=f"{lease_id}:q",
                module_id=a.module_id,
                coherence_class=CoherenceClass.MEMORY,
                calibration_epoch=self._state.epoch,
            )
        return ctx

    def _project(self, ctx: _RoundContext) -> RoundProjection:
        """Rebuild the projection fresh from current lease state (is_held /
        is_consumed change over the round's life)."""
        leases = [
            ProjectableLease(
                path_id=lease.path_id,
                coherence_class=_LEASE_COHERENCE,
                is_held=(lease.state == LeaseState.HERALDED),
                is_consumed=(lease.state == LeaseState.CONSUMED),
                state_held_since=lease.heralded_at,
                freshness_bound_s=lease.freshness_bound_s,
                heralded_fidelity_estimate=lease.fidelity_at_herald,
            )
            for lease in ctx.leases.values()
        ]
        return RoundProjection(
            round_id=ctx.round.round_id,
            deadline_s=ctx.round.deadline,
            leases=leases,
            qubits=[],
        )

    # ---- path allocation + reservation lifecycle (Task 2, reconciled) -------

    def _endpoints_for(self, round_id: str, ordinal: int) -> tuple[PortId, PortId]:
        n = len(self._ports)
        idx = self._port_pair_counter % n
        self._port_pair_counter += 1
        return (self._ports[idx], self._ports[(idx + 1) % n])

    def _begin_lease_acquisition(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        ctx = self._round_contexts[round_.round_id]
        ctx.causal_parent_id = causal_parent_id
        # Drive acquisition from the scheduler's queue (EDF-ordered in S0).
        while True:
            request = self._scheduler.next_lease_request(self._state.now)
            if request is None:
                break
            target_ctx = self._round_contexts.get(request.round_id)
            if target_ctx is None:
                # R4: the request's round is already terminal (e.g. an earlier
                # lease of a multi-lease round failed and dropped the context).
                # Do not reserve for it.
                continue
            self._acquire_path(target_ctx, request)

    def _acquire_path(self, ctx: _RoundContext, request: LeaseRequest) -> None:
        round_ = ctx.round
        path_id = request.path_id
        causal_parent_id = ctx.causal_parent_id
        lease_id = ctx.path_to_lease.get(path_id, request.request_id)

        # §7 capacity check.
        if len(self._state.active_reservations) >= self._state.switch_capacity_c:
            # SEMANTIC DECISION (reconciliation spec): S0 CHURNS here — it fails
            # the round and lets the workload retry. It does NOT defer.
            #
            # DO NOT "helpfully" make S0 defer to reduce churn:
            #  - Deferral-on-projected-failure IS admission control, which is
            #    definitionally the insight S1 adds (§8). An S0 that defers is
            #    S0 secretly borrowing S1's mechanism and understating the gap.
            #  - S0's admit->fail->retry churn is the behavioral PATHWAY by which
            #    fabric contention couples to lease aging: the churn re-enters a
            #    contended fabric while already-heralded leases age. That is what
            #    gives the decay-on/decay-off negative control something to
            #    measure; remove it and the control goes quiet.
            self._fail_round(round_, "switch_capacity_exhausted", causal_parent_id)
            return

        # §7 endpoint-exclusivity check against live reservations.
        a, b = path_id
        for other in self._state.active_reservations.values():
            if other.state == ReservationState.RELEASED:
                continue
            oa, ob = other.path_id
            if a in (oa, ob) or b in (oa, ob):
                self._fail_round(round_, "endpoint_conflict", causal_parent_id)
                return

        # The scheduler has handed this lease back for acquisition and the fabric
        # can host it: the lease is now genuinely REQUESTED. Publish it here (not
        # at round arrival) so a round that fails the capacity/endpoint checks
        # above never emits a phantom lease.requested — and so the lease-
        # transition invariant sees None -> requested -> heralded in order (a
        # bare None -> heralded at herald time would be an illegal transition).
        lease = ctx.leases.get(lease_id)
        if lease is not None:
            lease.state = LeaseState.REQUESTED
        ctx.requested.add(lease_id)
        self._publish("lease.requested", lease_id, causal_parent_id,
                      {"round_id": round_.round_id})

        reservation = SwitchPathReservation(
            path_id=path_id, holder_id=round_.round_id,
            acquired_at=self._state.now, state=ReservationState.ACQUIRED,
        )
        self._state.active_reservations[path_id] = reservation
        ctx.reservations[lease_id] = reservation

        entity_id = self._reservation_entity_id(path_id)
        path_payload = self._path_id_payload(path_id)
        acquired_id = self._publish("reservation.acquired", entity_id, causal_parent_id,
                                    {"round_id": round_.round_id, "lease_id": lease_id,
                                     "path_id": path_payload})
        reservation.state = ReservationState.CONFIGURING
        configuring_id = self._publish("reservation.configuring", entity_id, acquired_id,
                                       {"round_id": round_.round_id, "lease_id": lease_id,
                                        "path_id": path_payload})
        activate_at = self._state.now + self._config.reconfig_delay_s
        self._heap.push(activate_at, _ReservationActivatePayload(
            path_id=path_id, round_id=round_.round_id, lease_id=lease_id,
            causal_parent_id=configuring_id, reservation=reservation,
        ))

    def _on_reservation_active(self, payload: _ReservationActivatePayload) -> None:
        reservation = self._state.active_reservations.get(payload.path_id)
        if reservation is not payload.reservation:
            # The reservation this activation was scheduled for is no longer the
            # one holding the path. Either it was released before it finished
            # configuring (its round failed on a later lease) and the path is now
            # free (get() -> None), OR the path was released and RE-ACQUIRED by a
            # different round's reservation in the interim. Identity comparison
            # (not merely `is None`) is required so a stale activation cannot flip
            # a re-acquired path's NEW reservation to ACTIVE and emit
            # reservation.active with the wrong round_id/lease_id.
            return
        reservation.state = ReservationState.ACTIVE
        entity_id = self._reservation_entity_id(payload.path_id)
        active_id = self._publish("reservation.active", entity_id, payload.causal_parent_id,
                                  {"round_id": payload.round_id, "lease_id": payload.lease_id,
                                   "path_id": self._path_id_payload(payload.path_id)})
        # Task 3: the path is live — begin heralding on it now.
        self._start_heralding(payload.round_id, payload.lease_id, payload.path_id, active_id)

    def _reservation_entity_id(self, path_id: PathId) -> str:
        a, b = path_id
        return f"{a.module_id}:{a.port_index}->{b.module_id}:{b.port_index}"

    @staticmethod
    def _path_id_payload(path_id: PathId) -> list:
        # Structured, JSON-serializable path identity in the trace payload so
        # observe.resource_utilization can key on payload["path_id"] instead of
        # parsing the entity_id string. Each element is [module_id, port_index].
        return [[p.module_id, p.port_index] for p in path_id]

    # ---- heralding attempt loop (Task 3) ------------------------------------

    def _start_heralding(self, round_id: str, lease_id: str, path_id: PathId,
                         causal_parent_id: EventId) -> None:
        ctx = self._round_contexts.get(round_id)
        if ctx is None:
            return  # round already terminal; the §5 cascade released the path
        lease = ctx.leases.get(lease_id)
        # PathId IS the canonical endpoint pair, so it doubles as endpoints if
        # the lease record is somehow absent (defensive; normally present).
        endpoints = lease.endpoints if lease is not None else path_id
        attempt = _HeraldAttemptPayload(
            round_id=round_id, lease_id=lease_id, path_id=path_id,
            endpoints=endpoints, attempt_no=1, causal_parent_id=causal_parent_id,
        )
        self._heap.push(self._state.now, attempt)

    def _on_herald_attempt(self, payload: _HeraldAttemptPayload) -> None:
        ctx = self._round_contexts.get(payload.round_id)
        if ctx is None:
            return  # round already failed/cancelled; §5 cascade released the path
        round_ = ctx.round
        if self._state.now > round_.deadline:
            self._fail_round(round_, "heralding_deadline_exceeded", payload.causal_parent_id)
            return

        # §10: threshold a keyed uniform against the model's probability. The key
        # is semantic (round id, endpoints, attempt ordinal) — never event-heap
        # order — so paired policy comparisons share randomness per attempt.
        key = ("herald", round_.round_id, payload.endpoints, payload.attempt_no)
        u = draw_uniform(self._config.run_seed, "herald", key)
        draw_id = self._publish("draw.sampled", payload.lease_id, payload.causal_parent_id,
                                {"stream": "herald", "key": key, "uniform": u})
        # The engine synthesizes PathIds (_synthesize_ports/_endpoints_for) that a
        # partial CalibrationEpoch need not enumerate; BernoulliHeraldingModel does
        # a bare `epoch.heralding_p_per_path[path]` lookup that KeyErrors on such a
        # path. An uncalibrated path cannot herald: default to p=0.0 (the round then
        # spins until it fails its deadline — an honest, trace-visible outcome) rather
        # than crashing run_to(). This is real-epoch safety, not a test convenience —
        # a defaultdict-backed epoch still resolves via the model's __getitem__ (no
        # KeyError) and is unaffected. heralded_fidelity is only read on the u<p branch,
        # unreachable when p=0.0, so it needs no equivalent guard.
        try:
            p = self._state.models.heralding.success_probability(payload.path_id, self._state.epoch)
        except KeyError:
            p = 0.0

        if u < p:
            fidelity = self._state.models.heralding.heralded_fidelity(
                payload.path_id, self._state.epoch)
            lease = ctx.leases[payload.lease_id]
            lease.fidelity_at_herald = fidelity
            lease.heralded_at = self._state.now
            lease.state = LeaseState.HERALDED
            heralded_id = self._publish("lease.heralded", payload.lease_id, draw_id,
                                        {"round_id": round_.round_id,
                                         "fidelity_at_herald": fidelity})
            # Reconciliation spec §3: there is NO scheduler herald callback. The
            # engine tracks heralding in _RoundContext itself (the lease's state
            # above); the placeholder brief's on_lease_heralded call is deleted.
            self._release_reservation(payload.path_id, heralded_id)
            self._check_assembly(round_, heralded_id)
        else:
            next_attempt = _HeraldAttemptPayload(
                round_id=payload.round_id, lease_id=payload.lease_id,
                path_id=payload.path_id, endpoints=payload.endpoints,
                attempt_no=payload.attempt_no + 1, causal_parent_id=draw_id,
            )
            self._heap.push(self._state.now + HERALD_RETRY_INTERVAL_S, next_attempt)

    def _release_reservation(self, path_id: PathId, causal_parent_id: EventId) -> None:
        if self._state.hold_until_consumption:
            return  # hold the path until the round consumes the lease (S1 knob)
        reservation = self._state.active_reservations.pop(path_id, None)
        if reservation is None:
            return
        reservation.state = ReservationState.RELEASED
        reservation.released_at = self._state.now
        entity_id = self._reservation_entity_id(path_id)
        self._publish("reservation.released", entity_id, causal_parent_id,
                      {"round_id": reservation.holder_id,
                       "path_id": self._path_id_payload(path_id)})

    # ---- round assembly: decay aging + memory-access costing (Task 4) -------

    def _assemble_round(self, round_: SyndromeRound) -> tuple[list[float], list[float]]:
        """Compose each lease's decayed fidelity and each memory qubit's
        retention at the current instant. Decay ages the heralded fidelity from
        `lease.heralded_at`; the memory-access cost charges one read of wear.
        Returns (lease_fidelities, memory_retentions) — the two vectors the
        RoundSuccessModel scores (round-success scoring itself is Task 6)."""
        ctx = self._round_contexts[round_.round_id]
        lease_fidelities: list[float] = []
        memory_retentions: list[float] = []
        for lease_id in round_.lease_ids:
            lease = ctx.leases[lease_id]
            qubit = ctx.qubit_handles[lease_id]
            age_s = self._state.now - lease.heralded_at
            decay_factor = self._state.models.decay.retention(
                age_s, qubit.coherence_class, self._state.epoch,
            )
            decayed_fidelity = lease.fidelity_at_herald * decay_factor
            # Charge one memory access, then read the resulting cost so the wear
            # of THIS access is reflected in the retention we report.
            qubit.access_count += 1
            access_cost = self._state.models.memory_access.access_cost(
                qubit, self._state.epoch)
            lease_fidelities.append(decayed_fidelity)
            memory_retentions.append(decay_factor * access_cost.retention_factor)
        return lease_fidelities, memory_retentions

    # ---- decoder job lifecycle (Task 5) -------------------------------------

    def _check_assembly(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        ctx = self._round_contexts[round_.round_id]
        heralded = [lease for lease in ctx.leases.values()
                    if lease.state == LeaseState.HERALDED]
        if len(heralded) < len(round_.lease_ids):
            return  # still waiting on other leases of the round to herald
        self._enqueue_decoder_job(round_, causal_parent_id)

    def _enqueue_decoder_job(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        ctx = self._round_contexts[round_.round_id]
        job = DecoderJob(job_id=f"{round_.round_id}:D", round_id=round_.round_id,
                         priority=0, enqueue_time=self._state.now)
        ctx.decoder_job = job
        self._state.decoder_backlog += 1
        enqueued_id = self._publish("decoder.enqueued", job.job_id, causal_parent_id,
                                    {"round_id": round_.round_id})
        # §10: keyed service-time draw (job id is the semantic key).
        key = ("decode", job.job_id)
        u = draw_uniform(self._config.run_seed, "decode", key)
        self._publish("draw.sampled", job.job_id, enqueued_id,
                      {"stream": "decode", "key": key, "uniform": u})
        service_time_s = self._state.models.decoder_service.service_time_s(
            job, self._state.decoder_backlog, Draw(u=u),
        )
        # Single-server (M/M/1) serialization: service STARTS when the decoder is
        # free, i.e. max(now, _decoder_free_at); the server is then busy until
        # start + service_time. sojourn = wait + service, so a backed-up decoder
        # can push rounds late (decoder-bound) — the behavior §16.2's M/M/1 gate
        # checks. (M0 imprecision, flagged: a job cancelled mid-service via the
        # §5 cascade still holds its reserved server window; benign for the
        # decoupled M/M/1 regime, which has no round failures.)
        start_s = max(self._state.now, self._decoder_free_at)
        self._decoder_free_at = start_s + service_time_s
        job.dequeue_time = start_s
        self._heap.push(start_s + service_time_s, _DecoderCompletionPayload(
            job_id=job.job_id, round_id=round_.round_id, causal_parent_id=enqueued_id,
        ))

    def _on_decoder_completion(self, payload: _DecoderCompletionPayload) -> None:
        ctx = self._round_contexts.get(payload.round_id)
        if ctx is None or ctx.decoder_job is None or ctx.decoder_job.job_id != payload.job_id:
            return  # round already failed/cancelled; §5 cascade cancelled the job
        ctx.decoder_job.completion_time = self._state.now
        self._state.decoder_backlog -= 1
        completed_id = self._publish("decoder.completed", payload.job_id,
                                     payload.causal_parent_id,
                                     {"round_id": payload.round_id})
        self._score_round(ctx, completed_id)

    # ---- round-success scoring + terminal outcomes (Task 6) -----------------

    def _score_round(self, ctx: "_RoundContext", causal_parent_id: EventId) -> None:
        """Score the round with the RoundSuccessModel, publish its terminal
        outcome, and dispose its leases/reservations via the §5 cascade.

        The disposition cascade (`_terminate_round`) runs BEFORE the round.*
        terminal event is published so no still-active reservation ever outlives
        its terminated holder (the reservation-leak invariant). On a scoring
        FAILURE the workload retries; on either COMPLETED_* outcome the round is
        done — the workload's on_outcome returns no retry for a success, so the
        engine does not re-inject it."""
        round_ = ctx.round
        job = ctx.decoder_job
        lease_fidelities, memory_retentions = self._assemble_round(round_)
        decoder_latency_s = job.completion_time - job.enqueue_time
        deadline_slack_s = round_.deadline - job.completion_time
        p = self._state.models.round_success.success_probability(
            lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s,
        )
        # §10: threshold a keyed uniform on the task-local `round_outcome` stream
        # (engine-task-6 brief's documented binding convention for this stream).
        key = ("round_outcome", round_.round_id)
        u = draw_uniform(self._config.run_seed, "round_outcome", key)
        draw_id = self._publish("draw.sampled", round_.round_id, causal_parent_id,
                                {"stream": "round_outcome", "key": list(key), "uniform": u})
        succeeded = u < p

        # On SUCCESS the round USES (consumes) its held leases: consume them
        # BEFORE the §5 terminal cascade so on_round_terminal sees them consumed
        # (is_consumed) and does not cancel them. Failed/unused leases are
        # disposed by the scheduler inside _terminate_round.
        if succeeded:
            draw_id = self._consume_round_leases(ctx, draw_id)
        parent = self._terminate_round(ctx, succeeded, draw_id)
        if succeeded and deadline_slack_s >= 0.0:
            round_.state = RoundState.COMPLETED_IN_DEADLINE
            self._publish("round.completed_in_deadline", round_.round_id, parent,
                          {"success_probability": p})
        elif succeeded:
            round_.state = RoundState.COMPLETED_LATE
            self._publish("round.completed_late", round_.round_id, parent,
                          {"success_probability": p})
        else:
            round_.state = RoundState.FAILED
            failed_id = self._publish("round.failed", round_.round_id, parent,
                                      {"success_probability": p, "reason": "scoring_failure"})
            self._retry_or_drop(round_, failed_id)

    def _consume_round_leases(self, ctx: "_RoundContext", causal_parent_id: EventId) -> EventId:
        """A successful round consumes each held lease: publish lease.consumed
        with the fidelity at the moment of use (heralded fidelity decayed over
        the hold, matching _assemble_round). requested->heralded->CONSUMED is the
        terminal the freshness_at_consumption view reads; cancellation is
        reserved for failed/unused leases (§5)."""
        last_id = causal_parent_id
        for lease_id, lease in ctx.leases.items():
            if lease.state != LeaseState.HERALDED:
                continue
            qubit = ctx.qubit_handles[lease_id]
            age_s = self._state.now - lease.heralded_at
            decay_factor = self._state.models.decay.retention(
                age_s, qubit.coherence_class, self._state.epoch)
            fidelity_at_consumption = lease.fidelity_at_herald * decay_factor
            lease.state = LeaseState.CONSUMED
            last_id = self._publish(
                "lease.consumed", lease_id, last_id,
                {"round_id": ctx.round.round_id,
                 "fidelity_at_consumption": fidelity_at_consumption})
        return last_id

    # ---- failure / retry ----------------------------------------------------

    def _fail_round(self, round_: SyndromeRound, reason: str, causal_parent_id: EventId) -> None:
        # Run the §5 cleanup cascade (decoder-job cancellation, scheduler lease
        # disposition, reservation release) BEFORE publishing round.failed, so
        # the reservation-leak invariant (a reservation outliving its terminated
        # holder) never trips and the cascade events causally precede the
        # terminal event.
        ctx = self._round_contexts.get(round_.round_id)
        if ctx is not None:
            causal_parent_id = self._terminate_round(ctx, False, causal_parent_id)
        round_.state = RoundState.FAILED
        # Pre-scoring (resource) failure: no round-success probability exists.
        # success_probability is carried as None so round.failed's payload is
        # schema-consistent; logical_error_proxy skips None (a resource denial
        # is not a logical error).
        failed_id = self._publish("round.failed", round_.round_id, causal_parent_id,
                                  {"reason": reason, "success_probability": None})
        self._retry_or_drop(round_, failed_id)

    # ---- §5 failure-cleanup cascade + scheduler disposition (Task 7) --------

    def _terminate_round(self, ctx: "_RoundContext", succeeded: bool,
                         causal_parent_id: EventId) -> EventId:
        """§5's terminal cleanup cascade, run at EVERY round terminal (success
        or fail) before the round.* terminal event. Each step is a distinct,
        causally-chained trace event; returns the last event id so the caller
        chains the terminal event off it.

        Steps:
          1. cancel a still-pending decoder job (decoder.cancelled);
          2. ask the scheduler how to dispose the round's HELD leases
             (on_round_terminal -> LeaseDispositions) and apply each — CANCELLED
             -> lease.cancelled, RETURNED_TO_POOL -> lease.pool_returned, EXPIRED
             -> lease.expired; a requested-but-unheralded lease the scheduler
             returns no disposition for is cancelled round-bound;
          3. release every still-active reservation the round holds
             (reservation.released).
        The round context is released here."""
        round_ = ctx.round
        last_id = causal_parent_id

        job = ctx.decoder_job
        if job is not None and job.completion_time is None:
            self._state.decoder_backlog -= 1
            last_id = self._publish("decoder.cancelled", job.job_id, last_id,
                                    {"round_id": round_.round_id})

        # The scheduler decides the disposition KIND for the round's held leases.
        # S0 (round-bound) returns CANCELLED for every held-and-unconsumed lease;
        # a pooling policy (S1) would return RETURNED_TO_POOL / EXPIRED. Rebuild
        # the projection fresh so is_held/is_consumed reflect current state.
        projection = self._project(ctx)
        dispositions = self._scheduler.on_round_terminal(
            projection, succeeded, self._state.now)
        kind_by_path = {d.path_id: d.kind for d in dispositions}

        for lease_id, lease in ctx.leases.items():
            # Dispose only leases whose lease.requested was actually published,
            # and only if not already in a terminal lease state.
            if lease_id not in ctx.requested:
                continue
            if lease.state in (LeaseState.CONSUMED, LeaseState.EXPIRED, LeaseState.CANCELLED):
                continue
            last_id = self._apply_lease_disposition(
                lease, kind_by_path.get(lease.path_id), round_, last_id)

        last_id = self._release_round_reservations(ctx, last_id)
        self._round_contexts.pop(round_.round_id, None)
        return last_id

    def _apply_lease_disposition(self, lease: EntanglementLease,
                                 kind: "DispositionKind | None",
                                 round_: SyndromeRound, causal_parent_id: EventId) -> EventId:
        if kind is DispositionKind.RETURNED_TO_POOL:
            # Pregen pool-return path (S1). The frozen LeaseState has no POOLED
            # member, so mark the lease CANCELLED to keep THIS round from
            # re-consuming it while EngineState.pool holds the live reference for
            # future reuse. lease.pool_returned is accounted separately (§5/§11)
            # and is deliberately not a LeaseState transition the invariant
            # tracks. (Not exercised in M0's S0 runs; see reconciliation R3.)
            lease.state = LeaseState.CANCELLED
            self._state.pool.setdefault((lease.path_id, _LEASE_COHERENCE), []).append(lease)
            return self._publish("lease.pool_returned", lease.lease_id, causal_parent_id,
                                 {"round_id": round_.round_id})
        if kind is DispositionKind.EXPIRED:
            lease.state = LeaseState.EXPIRED
            return self._publish("lease.expired", lease.lease_id, causal_parent_id,
                                 {"round_id": round_.round_id})
        # CANCELLED, or no scheduler disposition (round-bound default for S0, and
        # the only legal disposition of an unheralded lease: it can only cancel).
        lease.state = LeaseState.CANCELLED
        return self._publish("lease.cancelled", lease.lease_id, causal_parent_id,
                             {"round_id": round_.round_id})

    def _release_round_reservations(self, ctx: _RoundContext,
                                    causal_parent_id: EventId) -> EventId:
        """Release every still-active reservation held by this round, keyed off
        the authoritative active_reservations map (holder_id == round_id), and
        return the last event id. Reservations already released (e.g. freed at
        herald time under hold_until_consumption=False) are skipped."""
        round_id = ctx.round.round_id
        last_id = causal_parent_id
        for path_id, reservation in list(self._state.active_reservations.items()):
            if reservation.holder_id != round_id:
                continue
            if reservation.state == ReservationState.RELEASED:
                continue
            reservation.state = ReservationState.RELEASED
            reservation.released_at = self._state.now
            del self._state.active_reservations[path_id]
            entity_id = self._reservation_entity_id(path_id)
            last_id = self._publish("reservation.released", entity_id, last_id,
                                    {"round_id": round_id,
                                     "path_id": self._path_id_payload(path_id)})
        return last_id

    def _retry_or_drop(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        retry_round = self._workload.on_outcome(round_, False)
        self._round_contexts.pop(round_.round_id, None)
        if retry_round is None:
            round_.state = RoundState.DROPPED
            self._publish("round.dropped", round_.round_id, causal_parent_id, {})
            return
        # Re-inject the retry after a keyed `retry`-stream interarrival delay so
        # the DES makes forward progress (immediate/zero-delay retry would
        # non-terminate under permanent contention, e.g. capacity 0). Retry
        # BACKOFF as a tuned knob is deferred (reconciliation spec); this is the
        # minimal positive reinjection delay needed for a well-defined sim.
        key = (round_.round_id, retry_round.retry_ordinal)
        u = draw_uniform(self._config.run_seed, _RETRY_STREAM, key)
        self._publish("draw.sampled", round_.round_id, causal_parent_id,
                      {"stream": _RETRY_STREAM, "key": list(key), "uniform": u})
        delay = -math.log(1.0 - u) / self._config.arrival_rate_hz
        retry_at = self._state.now + delay
        self._heap.push(retry_at, _ArrivalPayload(retry_round, causal_parent_id, is_retry=True))
