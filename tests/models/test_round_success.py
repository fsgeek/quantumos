import math

import pytest

from qsim.models.round_success import LogisticRoundSuccessModel


def test_success_probability_at_aggregate_fidelity_equal_to_midpoint_is_one_half():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=0.1)
    # single lease fidelity == midpoint, single memory retention == 1.0 =>
    # aggregate_fidelity == midpoint exactly; non-negative slack => no penalty.
    p = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                  decoder_latency_s=0.01, deadline_slack_s=0.0)
    assert p == pytest.approx(0.5)


def test_success_probability_composes_fidelities_multiplicatively():
    midpoint, slope = 0.5, 4.0
    model = LogisticRoundSuccessModel(logistic_midpoint=midpoint, logistic_slope=slope,
                                      slack_penalty_per_s=0.0)
    lease_fidelities = [0.9, 0.8]
    memory_retentions = [0.95]
    aggregate = 0.9 * 0.8 * 0.95
    expected = 1.0 / (1.0 + math.exp(-slope * (aggregate - midpoint)))
    p = model.success_probability(lease_fidelities=lease_fidelities,
                                  memory_retentions=memory_retentions,
                                  decoder_latency_s=0.0, deadline_slack_s=0.0)
    assert p == pytest.approx(expected)


def test_negative_deadline_slack_applies_linear_penalty():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=0.1)
    p = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                  decoder_latency_s=0.0, deadline_slack_s=-2.0)
    assert p == pytest.approx(0.5 - 0.1 * 2.0)


def test_success_probability_floors_at_zero_when_penalty_exceeds_raw_probability():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=10.0)
    p = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                  decoder_latency_s=0.0, deadline_slack_s=-5.0)
    assert p == 0.0


def test_positive_deadline_slack_applies_no_penalty():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=0.1)
    p_no_slack = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                           decoder_latency_s=0.0, deadline_slack_s=0.0)
    p_positive_slack = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                                 decoder_latency_s=0.0, deadline_slack_s=5.0)
    assert p_no_slack == pytest.approx(p_positive_slack)
