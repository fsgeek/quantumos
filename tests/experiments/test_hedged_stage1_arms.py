"""Arm selectors and outcome rules for hedged-placement Stage 1 (prereg §5).

Selector rules are tested via their lookup tables; arm outcomes are tested by
injecting explicit synthetic worlds, since the exchangeable Mix3 world law
cannot produce site-asymmetric deterministic worlds directly.
"""

import numpy as np

from scripts.hedged_placement_stage1 import (
    anchor_of_z0,
    evaluate_arms,
    late_quality_table,
    late_survival_table,
)


def world(G=0, K=0b111, C=0b111, L=0b111, H=0b111, Ehat=None, Z0=None, Z1=None):
    """One explicit world as single-element variable arrays."""
    if Ehat is None:
        Ehat = C & L
    if Z0 is None:
        Z0 = H
    if Z1 is None:
        Z1 = H
    return {
        name: np.array([val], dtype=np.int8)
        for name, val in dict(G=G, K=K, C=C, L=L, H=H, Ehat=Ehat, Z0=Z0, Z1=Z1).items()
    }


class TestAnchorOfZ0:
    def test_first_site_with_maximal_forecast_under_pi(self):
        assert anchor_of_z0(0b111) == 0
        assert anchor_of_z0(0b011) == 1
        assert anchor_of_z0(0b001) == 2
        assert anchor_of_z0(0b101) == 0

    def test_all_zero_forecast_falls_back_to_first_site(self):
        assert anchor_of_z0(0b000) == 0


class TestLateSurvivalTable:
    def test_scans_anchor_first_then_pi_order(self):
        t = late_survival_table()
        assert t[0b111, 0] == 0
        assert t[0b010, 0] == 1  # anchor unobserved, first alternate under pi
        assert t[0b110, 2] == 0  # order [2, 0, 1]: site 2 dark, site 0 lit
        assert t[0b011, 1] == 1  # anchor 1 lit, chosen first

    def test_no_observed_eligible_site_means_no_proposal(self):
        t = late_survival_table()
        assert t[0b000, 0] == -1
        assert t[0b000, 2] == -1


class TestLateQualityTable:
    def test_chooses_max_late_estimate_among_observed_eligible(self):
        t = late_quality_table()
        assert t[0b111, 0b010, 0] == 1
        assert t[0b011, 0b001, 1] == 2  # eligible {1,2}, Z1 max at 2

    def test_ties_break_anchor_first_then_pi(self):
        t = late_quality_table()
        assert t[0b111, 0b111, 1] == 1  # all tied, anchor kept
        assert t[0b101, 0b000, 0] == 0  # eligible {0,2} all-zero Z1, anchor kept
        assert t[0b011, 0b011, 2] == 2  # eligible {1,2} tied, anchor 2 kept

    def test_filtered_set_empty_means_no_proposal(self):
        t = late_quality_table()
        assert t[0b000, 0b111, 0] == -1


class TestEvaluateArmsSurvivalPass:
    def test_all_up_world_every_arm_delivers_at_anchor(self):
        v = world()
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=False)
        for arm in ("single", "prebound", "late"):
            assert r[arm]["proposed"][0] == 0
            assert r[arm]["materialized"][0]
            assert r[arm]["accepted"][0]

    def test_forced_rescue_shape_prebound_misses_late_delivers(self):
        # Key intact, anchor site 0 truly and observably down, site 2 truly
        # and observably eligible.
        v = world(C=0b011, L=0b001, Ehat=0b001)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=False)
        assert r["prebound"]["proposed"][0] == -1
        assert not r["prebound"]["materialized"][0]
        assert r["late"]["proposed"][0] == 2
        assert r["late"]["materialized"][0]

    def test_plural_arms_require_complete_key_single_does_not(self):
        v = world(K=0b110)  # one key qubit lost
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=False)
        assert r["single"]["materialized"][0]
        assert not r["prebound"]["materialized"][0]
        assert not r["late"]["materialized"][0]

    def test_false_positive_observation_yields_gate_refusal(self):
        # Site 0 observed eligible but truly down: proposal happens, gate
        # refuses, no materialization anywhere for anchored arms.
        v = world(C=0b011, Ehat=0b111)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=False)
        assert r["prebound"]["proposed"][0] == 0
        assert not r["prebound"]["materialized"][0]
        assert r["late"]["proposed"][0] == 0
        assert not r["late"]["materialized"][0]

    def test_selector_reads(self):
        v = world(Ehat=0b001)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=False)
        assert r["single"]["reads"][0] == 1
        assert r["prebound"]["reads"][0] == 1
        assert r["late"]["reads"][0] == 3  # scanned 0, 1, then found 2

    def test_no_eligible_site_scans_all_three(self):
        v = world(Ehat=0b000)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=False)
        assert r["late"]["proposed"][0] == -1
        assert r["late"]["reads"][0] == 3


class TestEvaluateArmsQualityPass:
    def test_anchor_follows_initial_forecast(self):
        v = world(H=0b010, Z0=0b010, Z1=0b010)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=True)
        assert r["single"]["proposed"][0] == 1
        assert r["prebound"]["proposed"][0] == 1

    def test_late_quality_selector_switches_on_late_signal(self):
        # Anchor forecast picked site 0; the late estimate reveals site 1.
        v = world(H=0b010, Z0=0b100, Z1=0b010)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=True)
        assert r["prebound"]["proposed"][0] == 0
        assert r["late"]["proposed"][0] == 1

    def test_recovered_quality_and_acceptance(self):
        # Site 1 latent-high, others low; everyone eligible; delta_clone=0.2.
        v = world(H=0b010, Z0=0b010, Z1=0b010)
        r = evaluate_arms(v, delta_clone=0.2, quality_pass=True)
        assert abs(r["single"]["quality"][0] - 0.8) < 1e-12  # base, no penalty
        assert abs(r["late"]["quality"][0] - 0.6) < 1e-12  # 0.8 - 0.2
        assert r["single"]["accepted"][0]
        assert r["late"]["accepted"][0]

    def test_subthreshold_materialization_consumes_without_acceptance(self):
        # All sites latent-low: plural quality 0.4 - 0.0 < 0.5.
        v = world(H=0b000, Z0=0b000, Z1=0b000)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=True)
        assert r["late"]["materialized"][0]
        assert not r["late"]["accepted"][0]

    def test_survival_comparator_present_in_quality_pass(self):
        # J_S ignores Z1: keeps anchor when anchor observed eligible.
        v = world(H=0b010, Z0=0b100, Z1=0b010)
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=True)
        assert r["late_s"]["proposed"][0] == 0
        assert r["late"]["proposed"][0] == 1

    def test_quality_selector_reads_all_sites(self):
        v = world()
        r = evaluate_arms(v, delta_clone=0.0, quality_pass=True)
        assert r["late"]["reads"][0] == 3
