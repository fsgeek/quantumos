"""Deterministic, keyed randomness for the qsim engine (design spec §10).

Every draw is addressed by (run_seed, stream, key) rather than drawn from a
sequential stream, so paired policy comparisons can share randomness on
matching semantic events even when policies make different numbers of draws
in different orders. Python's builtin hash() is never used here: it is
salted per-process (PYTHONHASHSEED) and would silently break determinism
across runs, forks, and sweep workers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

_UINT64_SPAN = 2 ** 64


def _canonical_bytes(run_seed: int, stream: str, key: tuple) -> bytes:
    """Canonical, deterministic serialization of the draw's identity.

    repr() of a tuple of str/int/float/tuple primitives is stable within a
    Python version and does not depend on object identity or hash order
    (unlike dict/set) — exactly the canonical encoding of
    (run_seed, stream, key) that §10 requires.
    """
    return repr((run_seed, stream, key)).encode("utf-8")


def draw_uniform(run_seed: int, stream: str, key: tuple) -> float:
    """Deterministic uniform sample in [0, 1).

    Seeded from SHA-256 over a canonical serialization of
    (run_seed, stream, key); the same semantic key always yields the same
    sample, in any process, with any PYTHONHASHSEED.
    """
    digest = hashlib.sha256(_canonical_bytes(run_seed, stream, key)).digest()
    top_64_bits = int.from_bytes(digest[:8], byteorder="big")
    return top_64_bits / _UINT64_SPAN


@dataclass(frozen=True)
class Draw:
    """A keyed uniform sample, already drawn by the engine (§10)."""
    u: float
