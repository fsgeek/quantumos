"""Shared scheduler protocol and value types (design spec §8).

`Scheduler` is a Protocol: S0Scheduler, AdmissionMixin, and PregenMixin all
satisfy it structurally via cooperative multiple inheritance, so the §8
ablation ladder (S0, S0+admission, S0+pregen, S1) is expressed as
composition, not a family of hand-written subclasses.

`ProjectableLease`/`RoundProjection` are the projected view of a round the
engine builds for a `Scheduler` to score and dispose of — distinct from the
real `EntanglementLease`/`SyndromeRound` entities so `policies/` stays
decoupled from the entity/engine internals (§4 separation rule).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol, runtime_checkable


class AdmissionOutcome(Enum):
    ADMIT = auto()
    DEFER = auto()


@dataclass(frozen=True)
class AdmissionDecision:
    """Outcome of `Scheduler.decide_admission` (design spec §8.1).

    The projection fields are populated only when a projection was actually
    computed — a scheduler that defers before projecting (e.g. S0's
    past-deadline check) leaves them `None`.
    """

    outcome: AdmissionOutcome
    projected_success_probability: float | None = None
    theta_admit: float | None = None
    deadline_slack_s: float | None = None
    decoder_latency_s_estimate: float | None = None
    reason: str | None = None


class LeaseRequestPurpose(Enum):
    """Why a scheduler is requesting a lease (design spec §8)."""

    ROUND = auto()
    POOL_REPLENISH = auto()


@dataclass(frozen=True)
class LeaseRequest:
    """A scheduler's request to acquire a lease on a path/coherence class."""

    request_id: str
    path_id: str
    coherence_class: str
    purpose: LeaseRequestPurpose
    requested_at_s: float
    round_id: str | None = None


class DispositionKind(Enum):
    """What happened to a lease at round-terminal time (design spec §5)."""

    CANCELLED = auto()          # round-bound (S0): unconsumed lease discarded
    RETURNED_TO_POOL = auto()   # pooling (pregen): still-fresh, returned
    EXPIRED = auto()            # pooling (pregen): stale, discarded


@dataclass(frozen=True)
class LeaseDisposition:
    """A scheduler's disposition of one lease at round-terminal time."""

    path_id: str
    coherence_class: str
    kind: DispositionKind


@dataclass
class ProjectableLease:
    """A lease's projectable state (design spec §8.1, §8.2)."""

    path_id: str
    coherence_class: str
    is_held: bool = False
    is_consumed: bool = False
    state_held_since: float | None = None
    freshness_bound_s: float = 1.0
    heralded_fidelity_estimate: float | None = None


@dataclass
class RoundProjection:
    """A round's projectable state, as built by the engine for a Scheduler."""

    round_id: str
    deadline_s: float
    leases: list[ProjectableLease] = field(default_factory=list)
    qubits: list = field(default_factory=list)


@runtime_checkable
class Scheduler(Protocol):
    """The scheduling interface every policy (S0, mixins, S1) implements."""

    def decide_admission(self, round_projection: RoundProjection, now_s: float,
                          decoder_backlog: int = 0, epoch: object | None = None) -> AdmissionDecision: ...

    def next_lease_request(self, now_s: float) -> LeaseRequest | None: ...

    def on_round_terminal(self, round_projection: RoundProjection, succeeded: bool,
                           now_s: float) -> list[LeaseDisposition]: ...

    def register_round_demand(self, round_projection: RoundProjection, now_s: float) -> None: ...
