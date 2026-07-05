"""S1Scheduler: S0Scheduler + AdmissionMixin + PregenMixin (design spec §8).

Both perishability mechanisms composed via Python's cooperative multiple
inheritance (MRO), not a hand-merged rewrite, so the ablation ladder
(S0, S0+admission, S0+pregen, S1) reuses these exact three classes
unmodified — S0+admission is `class(AdmissionMixin, S0Scheduler)`,
S0+pregen is `class(PregenMixin, S0Scheduler)`, both already exercised in
tests/policies/test_admission.py and tests/policies/test_pregen.py.
"""
from __future__ import annotations

from qsim.policies.admission import AdmissionMixin
from qsim.policies.pregen import PregenMixin
from qsim.policies.s0 import S0Scheduler


class S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler):
    pass
