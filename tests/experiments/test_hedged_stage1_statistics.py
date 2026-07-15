"""Per-cell recorded outcomes for hedged-placement Stage 1 (prereg §7).

Each test pins a statistic to a hand-derived analytic value on a cell simple
enough to compute on paper, so the enumeration machinery is checked against
independent arithmetic rather than against itself.
"""

import numpy as np

from scripts.hedged_placement_stage1 import Cell, cell_statistics


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


PERFECT = dict(p_c=1.0, p_l=1.0, q_k=1.0, a_e=1.0)


class TestSurvivalPassStatistics:
    def test_perfect_world_every_arm_delivers(self):
        s = cell_statistics(survival_cell(**PERFECT), quality_pass=False)
        for arm in ("single", "prebound", "late"):
            assert abs(s[f"{arm}.p_accepted"] - 1.0) < 1e-12
        assert abs(s["delta_m"]) < 1e-12
        assert abs(s["pair.both"] - 1.0) < 1e-12

    def test_carrier_scarce_rescue_arithmetic(self):
        # p_c=0.5, everything else perfect, independent sites.
        s = cell_statistics(
            survival_cell(p_c=0.5, p_l=1.0, q_k=1.0, a_e=1.0),
            quality_pass=False,
        )
        assert abs(s["single.p_accepted"] - 0.5) < 1e-12
        assert abs(s["prebound.p_accepted"] - 0.5) < 1e-12
        assert abs(s["late.p_accepted"] - 0.875) < 1e-12
        assert abs(s["delta_m"] - 0.375) < 1e-12
        assert abs(s["pair.late_only"] - 0.375) < 1e-12
        assert abs(s["pair.prebound_only"] - 0.0) < 1e-12
        assert abs(s["pair.neither"] - 0.125) < 1e-12
        # Prebound misses a live alternate whenever its anchor is dark but a
        # carrier survives elsewhere; late-bound never does (a_e = 1).
        assert abs(s["prebound.p_exercise_opportunity_miss"] - 0.375) < 1e-12
        assert abs(s["late.p_exercise_opportunity_miss"] - 0.0) < 1e-12
        # Physical recoverability before request.
        assert abs(s["plural.p_claim_recoverable"] - 0.875) < 1e-12
        assert abs(s["single.p_claim_recoverable"] - 0.5) < 1e-12

    def test_direct_key_fragility_arithmetic(self):
        # q_k=0.9 independent: P(K_complete) = 0.729 caps both plural arms.
        s = cell_statistics(
            survival_cell(p_c=1.0, p_l=1.0, q_k=0.9, a_e=1.0),
            quality_pass=False,
        )
        assert abs(s["single.p_accepted"] - 1.0) < 1e-12
        assert abs(s["prebound.p_accepted"] - 0.729) < 1e-12
        assert abs(s["late.p_accepted"] - 0.729) < 1e-12
        # Key loss is physical unavailability, not a policy miss.
        assert abs(s["late.p_exercise_opportunity_miss"] - 0.0) < 1e-12

    def test_catastrophe_scales_all_arms(self):
        s = cell_statistics(
            survival_cell(**PERFECT, g=0.10), quality_pass=False
        )
        assert abs(s["single.p_accepted"] - 0.9) < 1e-12
        assert abs(s["late.p_accepted"] - 0.9) < 1e-12

    def test_quality_conditional_is_flat_high(self):
        s = cell_statistics(survival_cell(), quality_pass=False)
        assert abs(s["late.q_mean_given_materialized"] - 0.8) < 1e-12

    def test_cost_coordinates(self):
        s = cell_statistics(
            survival_cell(p_c=0.5, p_l=1.0, q_k=1.0, a_e=1.0),
            quality_pass=False,
        )
        assert s["single.cost.allocated_carrier_qubits"] == 1
        assert s["prebound.cost.allocated_carrier_qubits"] == 3
        assert s["prebound.cost.allocated_key_qubits"] == 3
        assert s["single.cost.allocated_key_qubits"] == 0
        assert s["prebound.cost.construction_module_calls"] == 1
        assert s["prebound.cost.decryption_participants_if_admitted"] == 4
        assert s["single.cost.decryption_participants_if_admitted"] == 1
        assert s["prebound.cost.residue_qubits_after_materialization"] == 5
        assert s["single.cost.residue_qubits_after_materialization"] == 0
        assert abs(s["single.cost.selector_site_reads_mean"] - 1.0) < 1e-12
        # Late scan: anchor lit (p=.5) reads 1; else site 1 lit (.5*.5) reads 2;
        # else reads 3 -> 1*.5 + 2*.25 + 3*.25 = 1.75.
        assert abs(s["late.cost.selector_site_reads_mean"] - 1.75) < 1e-12
        # Forced cleanup, late arm: no materialization iff all carriers dark
        # (P=.125); surviving held = 0 carriers + 3 key qubits.
        assert abs(s["late.cost.forced_cleanup_qubits_mean"] - 0.375) < 1e-12
        # Prebound: anchor dark (P=.5); surviving = E[C_1+C_2] + 3 key.
        assert abs(s["prebound.cost.forced_cleanup_qubits_mean"] - 2.0) < 1e-12


class TestQualityPassStatistics:
    def test_perfect_late_signal_option_value(self):
        # All sites always eligible, key certain, Z0 uninformative (a_0=0.5),
        # Z1 perfect: V_Q = E[max-H quality] - E[anchor quality]
        #            = (0.8*(7/8) + 0.4/8) - 0.6 = 0.15.
        s = cell_statistics(
            quality_cell(**PERFECT, a_0=0.5, a_1=1.0), quality_pass=True
        )
        assert abs(s["v_q.pooled"] - 0.15) < 1e-12
        assert abs(s["v_q.mass_pooled"] - 1.0) < 1e-12
        assert abs(s["v_q.mass_n2"] - 0.0) < 1e-12
        assert abs(s["v_q.mass_n3"] - 1.0) < 1e-12

    def test_perfect_initial_forecast_leaves_no_headroom(self):
        # a_0=1: the anchor already sits on a high site whenever one exists.
        s = cell_statistics(
            quality_cell(**PERFECT, a_0=1.0, a_1=1.0), quality_pass=True
        )
        assert abs(s["v_q.pooled"]) < 1e-12

    def test_delta_clone_moves_quality_not_selection(self):
        base = cell_statistics(
            quality_cell(**PERFECT, a_0=0.5, a_1=1.0, delta_clone=0.0),
            quality_pass=True,
        )
        taxed = cell_statistics(
            quality_cell(**PERFECT, a_0=0.5, a_1=1.0, delta_clone=0.2),
            quality_pass=True,
        )
        assert abs(
            taxed["late.q_mean_given_materialized"]
            - (base["late.q_mean_given_materialized"] - 0.2)
        ) < 1e-12
        assert abs(taxed["delta_m"] - base["delta_m"]) < 1e-12
        assert abs(taxed["v_q.pooled"] - base["v_q.pooled"]) < 1e-12

    def test_subthreshold_delivery_separates_materialized_from_accepted(self):
        # Perfect world, uninformative anchor: late always materializes, but
        # acceptance requires a high site under plural penalty.
        s = cell_statistics(
            quality_cell(**PERFECT, a_0=0.5, a_1=1.0, delta_clone=0.2),
            quality_pass=True,
        )
        assert abs(s["late.p_materialized"] - 1.0) < 1e-12
        # Accepted iff chosen site is high: late finds a high site when any
        # exists (a_1=1): P = 7/8.
        assert abs(s["late.p_accepted"] - 7 / 8) < 1e-12

    def test_accepted_delivery_miss_arithmetic(self):
        # delta_clone=0.2: only high sites clear the threshold. Prebound sits
        # on an uninformative anchor: it misses an accepted delivery whenever
        # its site is low but some site is high: P(H_b=0, any H=1)
        # = 0.5 - P(all low)/2 ... with iid H: P(H_b=0 & any high) = 3/8.
        s = cell_statistics(
            quality_cell(**PERFECT, a_0=0.5, a_1=1.0, delta_clone=0.2),
            quality_pass=True,
        )
        assert abs(s["prebound.p_accepted_delivery_miss"] - 3 / 8) < 1e-12
        assert abs(s["late.p_accepted_delivery_miss"] - 0.0) < 1e-12

    def test_paired_quality_difference_on_both_materialize(self):
        s = cell_statistics(
            quality_cell(**PERFECT, a_0=0.5, a_1=1.0), quality_pass=True
        )
        # Both always materialize; difference = V_Q here.
        assert abs(s["pair.q_diff_both_materialized"] - 0.15) < 1e-12
        assert abs(s["pair.p_both_materialized"] - 1.0) < 1e-12
