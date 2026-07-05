import pytest

from qsim.core.rng import draw_uniform
from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.module import PortId, make_path_id
from qsim.entities.qubit import CoherenceClass
from qsim.models.heralding import BernoulliHeraldingModel


def _path():
    return make_path_id(PortId(module_id="m0", port_index=0),
                        PortId(module_id="m1", port_index=0))


def _epoch(p, fidelity, path):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class={CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 1.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={path: p},
        heralded_fidelity_per_path={path: fidelity},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1.0,
    )


def test_success_probability_reads_epoch_table():
    path = _path()
    epoch = _epoch(p=0.37, fidelity=0.9, path=path)
    model = BernoulliHeraldingModel()
    assert model.success_probability(path, epoch) == pytest.approx(0.37)


def test_heralded_fidelity_reads_epoch_table():
    path = _path()
    epoch = _epoch(p=0.37, fidelity=0.91, path=path)
    model = BernoulliHeraldingModel()
    assert model.heralded_fidelity(path, epoch) == pytest.approx(0.91)


def test_bernoulli_success_rate_over_many_keyed_draws_matches_epoch_p():
    path = _path()
    p = 0.63
    epoch = _epoch(p=p, fidelity=0.9, path=path)
    model = BernoulliHeraldingModel()
    threshold = model.success_probability(path, epoch)

    n = 5000
    run_seed = 42
    successes = 0
    for attempt_no in range(n):
        key = ("herald", "round-x", path, attempt_no)
        u = draw_uniform(run_seed, "herald", key)
        if u < threshold:
            successes += 1

    empirical_rate = successes / n
    # 5000 Bernoulli(0.63) draws: std dev ~ sqrt(0.63*0.37/5000) ~ 0.0068;
    # 5-sigma-plus tolerance avoids flakes while still catching a wrong
    # probability being plumbed through the engine's keyed-threshold contract.
    assert empirical_rate == pytest.approx(p, abs=0.035)
