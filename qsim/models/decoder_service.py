"""v1 DecoderServiceModel implementation (spec sec 6): exponential service time.

The frozen protocol gives service_time_s no CalibrationEpoch parameter (it is
called at actual decode time, per attempt), so the sampling rate is a
config-parameterized constructor argument, consistent with spec sec 6's "one
analytic, config-parameterized implementation of each" -- wiring code
constructs this model from the run's CalibrationEpoch.decoder_service_rate
once. expected_service_time_s *is* given the epoch (it's the sec 8.1
admission-control projection, which always has a live epoch in hand) and
reads the rate from it directly, independent of the model's own constructor
rate.

v1 has no backlog penalty (sec 6 table calls it optional); backlog is
accepted per the frozen signatures and ignored, reserved for a future
congestion-aware extension.
"""
from __future__ import annotations

import math

from qsim.core.rng import Draw
from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.decoder import DecoderJob


class ExponentialDecoderServiceModel:
    def __init__(self, service_rate: float):
        self._service_rate = service_rate

    def service_time_s(self, job: DecoderJob, backlog: int,
                       draw: Draw) -> float:
        # Inverse-CDF sampling: X = -ln(1-U)/rate ~ Exponential(rate).
        return -math.log(1.0 - draw.u) / self._service_rate

    def expected_service_time_s(self, backlog: int,
                                epoch: CalibrationEpoch) -> float:
        return 1.0 / epoch.decoder_service_rate
