"""PregenMixin: lease pre-generation pool policy (design spec §8.2).

Maintains a pool of not-yet-consumed leases keyed by (path, coherence
class); triggers a POOL_REPLENISH LeaseRequest whenever a tracked pool's
depth falls strictly below its low-water mark L. Composes with any base
Scheduler via cooperative multiple inheritance: round-bound LeaseRequests
from the base class (S0Scheduler) always take priority over pool
replenishment in `next_lease_request`.

Implements the §5 cleanup cascade for pooling policies: on round-terminal,
still-fresh unconsumed leases are returned to the pool; stale ones expire.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from qsim.policies.protocol import DispositionKind, LeaseDisposition, LeaseRequest, LeaseRequestPurpose

if TYPE_CHECKING:
    from qsim.policies.protocol import ProjectableLease, RoundProjection


class PregenMixin:
    def __init__(self, *, low_water_mark: int, tracked_keys, **kwargs) -> None:
        super().__init__(**kwargs)
        self._low_water_mark = low_water_mark
        self._pool: dict[tuple, list[ProjectableLease]] = {key: [] for key in tracked_keys}
        # Per-key count of minted-but-unresolved POOL_REPLENISH attempts (B3).
        # Without this term in the trigger, minting-while-below-L makes the
        # engine's acquisition drain loop non-terminating for a perpetually
        # empty pool (the documented run.py unbounded-drain hazard): L itself
        # bounds outstanding attempts per key, no extra config knob.
        self._in_flight: dict[tuple, int] = {key: 0 for key in tracked_keys}
        self._pool_request_seq = 0

    def pool_depth(self, key: tuple) -> int:
        return len(self._pool.get(key, []))

    def deposit_to_pool(self, lease: ProjectableLease) -> None:
        key = (lease.path_id, lease.coherence_class)
        if key not in self._pool:
            # Out-of-scope key: this pool only manages the (path, coherence)
            # pairs declared via `tracked_keys` at construction time. Silently
            # accepting an undeclared key here would let pool scope grow at
            # runtime and make it low-water-mark-replenished without ever
            # having been declared.
            return
        self._pool[key].append(lease)

    def withdraw_from_pool(self, key: tuple) -> ProjectableLease | None:
        pool = self._pool.get(key)
        return pool.pop(0) if pool else None

    def next_lease_request(self, now_s: float) -> LeaseRequest | None:
        base_request = super().next_lease_request(now_s)
        if base_request is not None:
            return base_request
        for key, pool in self._pool.items():
            if len(pool) + self._in_flight[key] < self._low_water_mark:
                self._in_flight[key] += 1
                self._pool_request_seq += 1
                path_id, coherence_class = key
                return LeaseRequest(
                    request_id=f"pool-{path_id}-{coherence_class}-{self._pool_request_seq}",
                    path_id=path_id,
                    coherence_class=coherence_class,
                    purpose=LeaseRequestPurpose.POOL_REPLENISH,
                    requested_at_s=now_s,
                    round_id=None,
                )
        return None

    def on_pool_replenish_outcome(self, key: tuple, succeeded: bool,
                                   lease: ProjectableLease | None, now_s: float) -> None:
        """Engine callback at replenish-attempt resolution (B3): every attempt
        — heralded, herald-failed, or denied at reservation time — releases its
        in-flight slot exactly once, so the low-water trigger re-arms. A
        successful attempt deposits the engine's projection of the new pooled
        lease, keeping this mirror in lockstep with EngineState.pool."""
        if self._in_flight.get(key, 0) > 0:
            self._in_flight[key] -= 1
        if succeeded and lease is not None:
            self.deposit_to_pool(lease)

    def on_round_terminal(self, round_projection: RoundProjection, succeeded: bool,
                           now_s: float) -> list[LeaseDisposition]:
        base_dispositions = super().on_round_terminal(round_projection, succeeded, now_s)
        base_by_key = {(d.path_id, d.coherence_class): d for d in base_dispositions}
        dispositions: list[LeaseDisposition] = []
        for lease in round_projection.leases:
            if not (lease.is_held and not lease.is_consumed):
                continue
            key = (lease.path_id, lease.coherence_class)
            if key not in self._pool:
                # Undeclared (path, coherence) pair: not this pool's to manage.
                # Defer to whatever the base scheduler already decided for it
                # (e.g. S0Scheduler's CANCELLED) instead of pooling it, which
                # would silently grow the pool's tracked scope at runtime.
                fallback = base_by_key.get(key)
                if fallback is not None:
                    dispositions.append(fallback)
                continue
            age_s = now_s - (lease.state_held_since if lease.state_held_since is not None else now_s)
            if age_s <= lease.freshness_bound_s:
                self.deposit_to_pool(lease)
                dispositions.append(LeaseDisposition(lease.path_id, lease.coherence_class, DispositionKind.RETURNED_TO_POOL))
            else:
                dispositions.append(LeaseDisposition(lease.path_id, lease.coherence_class, DispositionKind.EXPIRED))
        return dispositions
