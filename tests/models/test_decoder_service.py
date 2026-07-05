import math

import pytest

from qsim.core.rng import Draw
from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.decoder import DecoderJob
from qsim.entities.qubit import CoherenceClass
from qsim.models.decoder_service import ExponentialDecoderServiceModel


def _epoch(decoder_service_rate):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class={CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 1.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={},
        heralded_fidelity_per_path={},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=decoder_service_rate,
    )


def _job():
    return DecoderJob(job_id="j0", round_id="r0", priority=0, enqueue_time=0.0)


def test_expected_service_time_equals_closed_form_mean_independent_of_backlog():
    epoch = _epoch(decoder_service_rate=4.0)
    # Constructor rate deliberately differs from the epoch's rate:
    # expected_service_time_s must read the epoch, not the constructor arg.
    model = ExponentialDecoderServiceModel(service_rate=999.0)
    for backlog in (0, 1, 50):
        assert model.expected_service_time_s(backlog, epoch) == pytest.approx(1.0 / 4.0)


def test_service_time_s_matches_exponential_inverse_cdf_for_fixed_draw():
    rate = 2.5
    model = ExponentialDecoderServiceModel(service_rate=rate)
    draw = Draw(u=0.7)
    expected = -math.log(1.0 - 0.7) / rate
    assert model.service_time_s(_job(), backlog=0, draw=draw) == pytest.approx(expected)


def test_service_time_s_is_deterministic_given_the_same_draw_regardless_of_backlog():
    model = ExponentialDecoderServiceModel(service_rate=1.0)
    draw = Draw(u=0.42)
    t1 = model.service_time_s(_job(), backlog=0, draw=draw)
    t2 = model.service_time_s(_job(), backlog=10, draw=draw)
    assert t1 == pytest.approx(t2)  # v1 has no backlog penalty
