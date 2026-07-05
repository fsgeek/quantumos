"""v1 DecayModel implementations (spec sec 6): exponential decay and the
required no-decay control."""
from __future__ import annotations

import math

from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.qubit import CoherenceClass


class ExponentialDecayModel:
    """retention(age) = exp(-decay_rate_per_class[coherence] * age_s)."""

    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float:
        rate = epoch.decay_rate_per_class[coherence]
        return math.exp(-rate * age_s)


class NoDecayModel:
    """Required control (spec sec 6): retention identically 1, regardless of
    age, coherence class, or epoch -- neutralizes the decay surface entirely."""

    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float:
        return 1.0
