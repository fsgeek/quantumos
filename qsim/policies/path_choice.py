"""Path-choice strategies: the B1 policy decision point (design spec §2's
'path allocation as separable mechanisms'; prereg B1: 'promote path selection
from the engine's round-robin counter to a policy decision point,
behavior-preserving by default').

The seam is a strategy object injected into `Engine.__init__`, NOT a new
`Scheduler` protocol method: the reconciliation spec deliberately DELETED the
placeholder `allocate_path` scheduler hook (core/engine.py's module
docstring), and re-adding one would reopen that deletion. The engine invokes
the chooser at the exact pre-B1 call site — per lease, at arrival, before
admission, retries included — which is what makes the default provably
bit-identical (pinned golden hashes in
tests/determinism/test_b1_path_seam_preserves_trace.py).

Choosers are deliberately OCCUPANCY-BLIND: they never see
active_reservations, so §7 conflict-then-churn stays the engine's pathway
(churn-not-defer is load-bearing S0 semantics — see the normative comment in
core/engine.py's _acquire_path). No chooser consumes RNG: a randomized choice
would be a new §10 stream and new trace content, a feature rather than a seam.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    # Same R2 type-only-import pattern as policies/protocol.py: annotations
    # are lazy, so policies/ takes no runtime dependency on entities/.
    from qsim.entities import PathId, PortId


@runtime_checkable
class PathChoice(Protocol):
    """Strategy deciding which endpoint pair a lease attempts.

    Receives only projected, read-only inputs: the synthesized port universe,
    the identity of the deciding moment (round_id, lease_ordinal), the
    PathIds already chosen within THIS round (ctx.path_to_lease is keyed by
    PathId, so per-round PathId uniqueness is structural for any chooser that
    honours `taken_path_ids`), and the epoch's per-path heralding table as a
    plain Mapping — never the CalibrationEpoch entity (§4 layering rule).
    """

    def choose_endpoints(self, *, round_id: str, lease_ordinal: int,
                         ports: Sequence[PortId],
                         taken_path_ids: frozenset[PathId],
                         heralding_p_by_path: Mapping[PathId, float],
                         ) -> tuple[PortId, PortId]: ...


class RoundRobinPathChoice:
    """The pre-B1 default: the engine's `_endpoints_for` counter arithmetic
    transplanted verbatim. One per-instance counter (engine-instance
    lifetime, like the old `_port_pair_counter`), advanced once per call —
    i.e. once per lease at EVERY arrival: admitted, deferred, or retry.

    Returns the RAW uncanonicalized pair (ports[idx], ports[idx+1 mod n]).
    Raw order is load-bearing: the herald draw key embeds lease.endpoints in
    this order and the lease's qubit handle takes module_id from endpoint a,
    so at the wrap index (n-1, 0) canonicalizing would flip trace bytes.
    Every contextual argument is ignored, exactly as _endpoints_for ignored
    its arguments; no uniqueness check is added (at len(lease_ids) >= n the
    pre-B1 counter silently degrades, and a guard would change behavior in
    exactly those configs).
    """

    def __init__(self) -> None:
        self._counter = 0

    def choose_endpoints(self, *, round_id: str, lease_ordinal: int,
                         ports: Sequence["PortId"],
                         taken_path_ids: frozenset["PathId"],
                         heralding_p_by_path: Mapping["PathId", float],
                         ) -> tuple["PortId", "PortId"]:
        n = len(ports)
        idx = self._counter % n
        self._counter += 1
        return (ports[idx], ports[(idx + 1) % n])


class BestHeraldingPathChoice:
    """The B1 comparative policy: best heralding_p among viable paths — the
    minimal CalibrationEpoch-table reader the S2 spatial-ordering test needs.

    Viable = ENUMERATED in the epoch's heralding_p_per_path table (an
    unenumerated path can never herald: the engine and the model guard both
    hold it at p=0.0), with both endpoints present in the synthesized port
    universe (an unreachable path can never be reserved), minus the PathIds
    already chosen within this round (per-round PathId uniqueness is
    structural: ctx.path_to_lease is keyed by PathId).

    Selection is argmax heralding_p; equal-p ties break to the
    lexicographically-least canonical PathId key — the minimal deterministic
    total order §16.4's trace-hash guarantee requires (a randomized tie-break
    would be a new §10 stream, a feature rather than a seam). Endpoints are
    returned in canonical PathId order: the PathId IS the ordered pair.

    Exhaustion — a round needing more distinct paths than the table
    enumerates — raises ValueError LOUDLY. No fallback: falling back to
    round-robin would silently mix two policies in one arm, and deferring
    would be covert admission control. The spec assigns no trace-producing
    meaning to 'no path available' distinct from admission/capacity failure,
    so raising is the non-invention.
    """

    def choose_endpoints(self, *, round_id: str, lease_ordinal: int,
                         ports: Sequence["PortId"],
                         taken_path_ids: frozenset["PathId"],
                         heralding_p_by_path: Mapping["PathId", float],
                         ) -> tuple["PortId", "PortId"]:
        universe = set(ports)

        def _canonical_key(path: "PathId") -> tuple:
            return tuple((p.module_id, p.port_index) for p in path)

        candidates = [
            path for path in heralding_p_by_path
            if path not in taken_path_ids
            and all(endpoint in universe for endpoint in path)
        ]
        if not candidates:
            raise ValueError(
                f"BestHeraldingPathChoice exhausted for round {round_id!r} "
                f"(lease ordinal {lease_ordinal}): the calibration epoch "
                f"enumerates {len(heralding_p_by_path)} path(s), "
                f"{len(taken_path_ids)} already taken within the round, and "
                f"no remaining enumerated path lies within the "
                f"{len(universe)}-port fabric universe")
        best = min(candidates,
                   key=lambda path: (-heralding_p_by_path[path], _canonical_key(path)))
        a, b = best
        return (a, b)
