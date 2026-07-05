"""qsim.policies: Scheduler protocol and implementations (design spec §8).

Re-exports the public value types and the `Scheduler` Protocol from
`qsim.policies.protocol` so downstream packages (e.g. `core.engine`) can
import them package-level, e.g. `from qsim.policies import Scheduler`.
"""
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

__all__ = [
    "AdmissionDecision",
    "AdmissionOutcome",
    "DispositionKind",
    "LeaseDisposition",
    "LeaseRequest",
    "LeaseRequestPurpose",
    "ProjectableLease",
    "RoundProjection",
    "Scheduler",
]
