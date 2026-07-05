"""v1 RoundSuccessModel implementation (spec sec 6): logistic curve on
aggregate fidelity with a linear deadline-slack penalty.

The frozen protocol gives success_probability no CalibrationEpoch parameter
(sec 8.1 reuses this exact surface for admission-control projection against
*projected* inputs, so it must be a pure function of its numeric arguments
alone). The logistic midpoint/slope and slack penalty are therefore
config-parameterized constructor arguments; wiring code constructs this model
from the run's CalibrationEpoch.round_success_logistic_midpoint /
.round_success_logistic_slope / .round_success_slack_penalty_per_s once.
"""
from __future__ import annotations

import math
from typing import Sequence


class LogisticRoundSuccessModel:
    def __init__(self, logistic_midpoint: float, logistic_slope: float,
                 slack_penalty_per_s: float):
        self._midpoint = logistic_midpoint
        self._slope = logistic_slope
        self._slack_penalty_per_s = slack_penalty_per_s

    def success_probability(self, lease_fidelities: Sequence[float],
                            memory_retentions: Sequence[float],
                            decoder_latency_s: float,
                            deadline_slack_s: float) -> float:
        # decoder_latency_s is accepted per the frozen signature but unused by
        # v1's formula; the caller's projection (sec 8.1) already folds
        # decoder latency into deadline_slack_s. Reserved for a future
        # service-time-sensitive extension.
        aggregate_fidelity = 1.0
        for f in lease_fidelities:
            aggregate_fidelity *= f
        for r in memory_retentions:
            aggregate_fidelity *= r

        z = self._slope * (aggregate_fidelity - self._midpoint)
        raw_p = 1.0 / (1.0 + math.exp(-z))

        if deadline_slack_s < 0.0:
            raw_p -= self._slack_penalty_per_s * abs(deadline_slack_s)

        return min(1.0, max(0.0, raw_p))
