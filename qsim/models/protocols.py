"""Model surface protocols and shared value types (spec sec 6, verbatim).

All model surfaces are pure functions of their arguments plus a CalibrationEpoch:
no mutable state, no random draws. Where a sample is unavoidable
(DecoderServiceModel.service_time_s), the engine supplies a keyed Draw (sec 10);
the model never draws itself.

RoundSuccessModel.success_probability and DecoderServiceModel.service_time_s
deliberately take no CalibrationEpoch: sec 8.1 reuses success_probability for
admission-control projection over purely numeric projected inputs, and
service_time_s is called per decode attempt without epoch plumbing. Their v1
implementations are config-parameterized at construction time instead (see
models/round_success.py, models/decoder_service.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from qsim.core.rng import Draw
from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.decoder import DecoderJob
from qsim.entities.module import PathId
from qsim.entities.qubit import CoherenceClass, QubitHandle


@dataclass(frozen=True)
class AccessCost:
    electron_channel_s: float
    retention_factor: float


class DecayModel(Protocol):
    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float:
        """Multiplicative retention in [0,1].
        fidelity(t) = fidelity_at_herald * retention(t - t_herald, class, epoch)."""
        ...


class MemoryAccessModel(Protocol):
    def access_cost(self, qubit: QubitHandle,
                    epoch: CalibrationEpoch) -> AccessCost:
        """Composes AFTER passive decay is applied up to the access instant:
        f_after = f_decayed_to_now * retention_factor."""
        ...


class HeraldingModel(Protocol):
    def success_probability(self, path: PathId,
                            epoch: CalibrationEpoch) -> float:
        """Per-attempt heralding success probability."""
        ...

    def heralded_fidelity(self, path: PathId,
                          epoch: CalibrationEpoch) -> float:
        """Initial fidelity of a successfully heralded pair on this path."""
        ...


class RoundSuccessModel(Protocol):
    def success_probability(self, lease_fidelities: Sequence[float],
                            memory_retentions: Sequence[float],
                            decoder_latency_s: float,
                            deadline_slack_s: float) -> float:
        """Round success given inputs at execution time. decoder_latency_s is the
        raw duration; deadline_slack_s = deadline - completion time (may be
        negative)."""
        ...


class DecoderServiceModel(Protocol):
    def service_time_s(self, job: DecoderJob, backlog: int,
                       draw: Draw) -> float:
        """Sampled service time; draw is an engine-supplied keyed source."""
        ...

    def expected_service_time_s(self, backlog: int,
                                epoch: CalibrationEpoch) -> float:
        """Closed-form mean service time at the given backlog, no draw."""
        ...
