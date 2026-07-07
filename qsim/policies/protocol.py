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
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    # R2 (reconciliation spec): the projected/request models key on the REAL
    # entity types the engine passes, not `str`. Annotations are lazy
    # (`from __future__ import annotations`), so this import is type-only and
    # adds no runtime dependency of policies/ on entities/.
    from qsim.entities import CoherenceClass, PathId


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
    path_id: PathId
    coherence_class: CoherenceClass
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

    path_id: PathId
    coherence_class: CoherenceClass
    kind: DispositionKind


@dataclass
class ProjectableLease:
    """A lease's projectable state (design spec §8.1, §8.2)."""

    path_id: PathId
    coherence_class: CoherenceClass
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


@runtime_checkable
class PoolingScheduler(Scheduler, Protocol):
    """A Scheduler that additionally custodies a pregen pool projection (§8.2,
    B3). The engine gates every pool code path on
    `isinstance(scheduler, PoolingScheduler)`, so a plain S0Scheduler run
    executes zero pool code and stays bit-identical (RNG draws included).

    R3 resolution: EngineState.pool is authoritative for the real
    EntanglementLease objects; the implementations behind this protocol
    (PregenMixin) hold only the policy-side ProjectableLease mirror — §4's
    layering rule forbids policies custodying real entities — and the engine
    pairs every mutation across the two."""

    def pool_depth(self, key: tuple) -> int: ...

    def deposit_to_pool(self, lease: ProjectableLease) -> None: ...

    def withdraw_from_pool(self, key: tuple) -> ProjectableLease | None: ...

    def on_pool_replenish_outcome(self, key: tuple, succeeded: bool,
                                   lease: ProjectableLease | None, now_s: float) -> None: ...
