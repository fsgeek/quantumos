"""Controls, channel activation, labels, and battery readings (prereg §8-9).

Build verification exercises only these synthetic controls and label
mechanics; the deciding grids are never evaluated here (prereg §11).
"""

import numpy as np

from scripts.hedged_placement_stage1 import (
    Cell,
    battery_readings,
    label_delta_m,
    label_v_q,
    permute_sites,
    quality_activation,
    run_controls,
    survival_activation,
)


def survival_cell(**overrides):
    params = dict(
        p_c=0.8, p_l=0.8, q_k=0.99, rho_c=0.0, rho_l=0.0, rho_k=0.0,
        g=0.0, a_e=0.9,
    )
    params.update(overrides)
    return Cell(
        **params,
        rho_q=0.0, a_0=1.0, a_1=1.0, delta_clone=0.0, flat_high_quality=True,
    )


def quality_cell(**overrides):
    params = dict(
        p_c=0.8, p_l=0.8, rho_c=0.0, rho_l=0.0, q_k=0.99, rho_k=0.0, g=0.0,
        a_e=0.9, rho_q=0.0, a_0=0.60, a_1=0.9, delta_clone=0.0,
        flat_high_quality=False,
    )
    params.update(overrides)
    return Cell(**params)


class TestEightControls:
    def test_all_controls_pass(self):
        controls = run_controls()
        expected = {
            "same_site_identity",
            "forced_rescue",
            "direct_key_loss",
            "flat_quality",
            "uninformative_signal",
            "permutation_equivariance",
            "probability_balance",
            "shared_penalty_invariance",
        }
        assert set(controls) == expected
        for name, result in controls.items():
            assert result["passed"], f"control {name} failed: {result}"


class TestPermuteSites:
    def test_bit_relabeling(self):
        v = {"C": np.array([0b100], dtype=np.int8), "G": np.array([0])}
        out = permute_sites(v, (2, 0, 1))  # site s -> sigma[s]
        # site 0's bit moves to site 2: 0b100 -> 0b001
        assert out["C"][0] == 0b001
        assert out["G"][0] == 0  # G is not a site vector

    def test_identity_permutation(self):
        v = {"C": np.array([0b101], dtype=np.int8)}
        assert permute_sites(v, (0, 1, 2))["C"][0] == 0b101


class TestSurvivalActivation:
    def test_independent_scarce_cell_activates(self):
        activated, reason = survival_activation(
            survival_cell(p_c=0.5, p_l=1.0, q_k=1.0, a_e=1.0)
        )
        assert activated and reason is None

    def test_fully_common_mode_is_silenced(self):
        # rho_c = rho_l = 1: all sites live or die together; there is never
        # an unavailable anchor with an exercisable alternate.
        activated, reason = survival_activation(
            survival_cell(rho_c=1.0, rho_l=1.0)
        )
        assert not activated
        assert reason.startswith("CHANNEL_SILENCED")

    def test_certain_world_is_silenced(self):
        # p_c = p_l = 1 with perfect observation: nothing ever fails, the
        # decision never moves.
        activated, reason = survival_activation(
            survival_cell(p_c=1.0, p_l=1.0, q_k=1.0, a_e=1.0)
        )
        assert not activated
        assert reason.startswith("CHANNEL_SILENCED")


class TestQualityActivation:
    def test_standard_cell_activates(self):
        activated, reason = quality_activation(quality_cell())
        assert activated and reason is None

    def test_uninformative_late_signal_is_silenced(self):
        activated, reason = quality_activation(quality_cell(a_1=0.5))
        assert not activated
        assert reason == "CHANNEL_SILENCED.INFORMATION"

    def test_flat_within_world_quality_is_silenced(self):
        activated, reason = quality_activation(quality_cell(rho_q=1.0))
        assert not activated
        assert reason == "CHANNEL_SILENCED.QUALITY"


class TestLabels:
    def test_delta_m_thresholds_inclusive(self):
        assert label_delta_m(0.01) == "POSITIVE"
        assert label_delta_m(0.0099) == "NEUTRAL"
        assert label_delta_m(-0.01) == "NEGATIVE"
        assert label_delta_m(-0.0099) == "NEUTRAL"

    def test_v_q_labels_and_stratum_mass_floor(self):
        assert label_v_q(0.01, mass=0.05) == "QUALITY_POSITIVE"
        assert label_v_q(0.01, mass=0.049) == "QUALITY_UNIDENTIFIED"
        assert label_v_q(-0.01, mass=0.5) == "QUALITY_NEGATIVE"
        assert label_v_q(0.005, mass=0.5) == "QUALITY_NEUTRAL"


class TestBatteryReadings:
    def test_site_choice_earned_when_any_activated_positive(self):
        readings = battery_readings(
            survival_labels=[("POSITIVE", True), ("NEUTRAL", True)],
            quality_labels=[("QUALITY_NEUTRAL", True)],
            survival_max_abs=0.2,
            quality_max_abs=0.001,
            controls_passed=True,
        )
        assert readings["site_choice"] == "SITE_CHOICE_DECISION_EARNED"
        assert readings["quality_choice"] == "REGION_THIN"
        # No battery-level reading is defined by the prereg for the earned
        # case; the per-channel readings are the index.
        assert readings["battery"] == ""

    def test_vocabulary_is_prereg_only(self):
        # Every emitted reading is drawn from the prereg §9 set (or empty).
        allowed = {
            "SITE_CHOICE_DECISION_EARNED", "QUALITY_CHOICE_DECISION_EARNED",
            "REGION_THIN", "NOT_DECISION_EARNED_IN_TESTED_ENVELOPE",
            "REFUSED", "",
        }
        for s_labs, q_labs, s_max, q_max in [
            ([("POSITIVE", True)], [("QUALITY_NEUTRAL", True)], 0.2, 0.0),
            ([("NEUTRAL", True)], [("QUALITY_NEUTRAL", True)], 0.0, 0.0),
            ([], [("QUALITY_POSITIVE", True)], 0.0, 0.5),
            ([("NEGATIVE", True)], [], 0.5, 0.0),
        ]:
            readings = battery_readings(s_labs, q_labs, s_max, q_max, True)
            assert set(readings.values()) <= allowed, readings

    def test_material_negative_region_is_not_thin(self):
        # Prereg §9: REGION_THIN means no value reaches its materiality
        # threshold; a material NEGATIVE region reached it.
        readings = battery_readings(
            survival_labels=[("NEGATIVE", True), ("NEUTRAL", True)],
            quality_labels=[("QUALITY_NEGATIVE", True)],
            survival_max_abs=0.3,
            quality_max_abs=0.2,
            controls_passed=True,
        )
        assert readings["site_choice"] == ""
        assert readings["quality_choice"] == ""
        assert readings["battery"] == "NOT_DECISION_EARNED_IN_TESTED_ENVELOPE"

    def test_not_earned_requires_both_channels_activated_and_controls(self):
        readings = battery_readings(
            survival_labels=[("NEUTRAL", True)],
            quality_labels=[("QUALITY_NEUTRAL", True)],
            survival_max_abs=0.0,
            quality_max_abs=0.0,
            controls_passed=True,
        )
        assert readings["battery"] == "NOT_DECISION_EARNED_IN_TESTED_ENVELOPE"

    def test_channel_never_activated_gives_no_battery_reading(self):
        readings = battery_readings(
            survival_labels=[("NEUTRAL", True)],
            quality_labels=[("", False)],
            survival_max_abs=0.0,
            quality_max_abs=0.0,
            controls_passed=True,
        )
        assert readings["battery"] == ""

    def test_control_failure_refuses_battery(self):
        readings = battery_readings(
            survival_labels=[("POSITIVE", True)],
            quality_labels=[("QUALITY_POSITIVE", True)],
            survival_max_abs=0.5,
            quality_max_abs=0.5,
            controls_passed=False,
        )
        assert readings["battery"] == "REFUSED"
        assert readings["refusal_reason"] == "CONTROL_FAILED"
