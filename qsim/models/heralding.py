"""v1 HeraldingModel implementation (spec sec 6): Bernoulli(p) per attempt,
looked up directly from the calibration epoch's per-path tables. The model
returns a probability only -- it never draws; the engine thresholds a keyed
uniform against it per sec 10's contract."""
from __future__ import annotations

from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.module import PathId


class BernoulliHeraldingModel:
    def success_probability(self, path: PathId,
                            epoch: CalibrationEpoch) -> float:
        return epoch.heralding_p_per_path[path]

    def heralded_fidelity(self, path: PathId,
                          epoch: CalibrationEpoch) -> float:
        return epoch.heralded_fidelity_per_path[path]
