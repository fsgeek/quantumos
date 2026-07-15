"""World-law primitives for the hedged-placement Stage 1 exact enumeration.

Governed by docs/superpowers/specs/2026-07-13-hedged-placement-stage1-prereg.md
(approved revision ca26217, OTS-stamped). These tests exercise only synthetic
world-law properties; no deciding grid is evaluated here (prereg §11).
"""

import numpy as np
import pytest

from scripts.hedged_placement_stage1 import (
    BITS,
    mix3_pmf,
    obs_pmf,
)


def site_marginal(pmf: np.ndarray, site: int) -> float:
    """P(bit_site = 1) under a pmf over the 8 three-bit vectors."""
    return float(pmf[BITS[:, site] == 1].sum())


class TestMix3Pmf:
    def test_weights_sum_to_one(self):
        pmf = mix3_pmf(0.7, 0.3)
        assert pmf.shape == (8,)
        assert abs(pmf.sum() - 1.0) < 1e-12

    def test_rho_zero_is_iid_product(self):
        p = 0.8
        pmf = mix3_pmf(p, 0.0)
        for v in range(8):
            expected = 1.0
            for i in range(3):
                expected *= p if BITS[v, i] else (1.0 - p)
            assert abs(pmf[v] - expected) < 1e-12

    def test_rho_one_is_fully_common_mode(self):
        p = 0.8
        pmf = mix3_pmf(p, 1.0)
        assert abs(pmf[0b000] - (1.0 - p)) < 1e-12
        assert abs(pmf[0b111] - p) < 1e-12
        mixed = [v for v in range(8) if v not in (0b000, 0b111)]
        assert all(pmf[v] == 0.0 for v in mixed)

    @pytest.mark.parametrize("p", [0.5, 0.8, 0.95])
    @pytest.mark.parametrize("rho", [0.0, 0.5, 1.0])
    def test_marginal_preserved_at_every_site(self, p, rho):
        pmf = mix3_pmf(p, rho)
        for site in range(3):
            assert abs(site_marginal(pmf, site) - p) < 1e-12


class TestObsPmf:
    """P(observed vector | true vector) with independent per-site accuracy a."""

    def test_rows_sum_to_one(self):
        m = obs_pmf(0.7)
        assert m.shape == (8, 8)
        assert np.all(np.abs(m.sum(axis=1) - 1.0) < 1e-12)

    def test_perfect_accuracy_is_identity(self):
        m = obs_pmf(1.0)
        assert np.allclose(m, np.eye(8))

    def test_single_site_flip_probability(self):
        a = 0.9
        m = obs_pmf(a)
        # true 000 observed as 100 (exactly one site wrong): (1-a) * a * a
        assert abs(m[0b000, 0b100] - (1 - a) * a * a) < 1e-12
        # true 101 observed exactly: a^3
        assert abs(m[0b101, 0b101] - a**3) < 1e-12
        # true 101 observed as 010 (all three wrong): (1-a)^3
        assert abs(m[0b101, 0b010] - (1 - a) ** 3) < 1e-12


from scripts.hedged_placement_stage1 import Cell, world_joint

SURVIVAL_BASE = dict(
    p_c=0.8, p_l=0.8, q_k=0.99, rho_c=0.0, rho_l=0.0, rho_k=0.0,
    g=0.0, a_e=0.9,
)


def survival_cell(**overrides):
    """Survival-pass cell: quality flat-high per prereg §6.1."""
    params = {**SURVIVAL_BASE, **overrides}
    return Cell(
        **params,
        rho_q=0.0, a_0=1.0, a_1=1.0, delta_clone=0.0, flat_high_quality=True,
    )


def quality_cell(**overrides):
    """Quality-pass cell: §6.2 fixed q_k=0.99, rho_k=0, g=0."""
    params = dict(
        p_c=0.8, p_l=0.8, rho_c=0.0, rho_l=0.0, q_k=0.99, rho_k=0.0, g=0.0,
        a_e=0.9, rho_q=0.0, a_0=0.60, a_1=0.9, delta_clone=0.0,
        flat_high_quality=False,
    )
    params.update(overrides)
    return Cell(**params)


class TestWorldJoint:
    @pytest.mark.parametrize("cell", [
        survival_cell(),
        survival_cell(g=0.10, rho_c=1.0, rho_l=1.0, rho_k=1.0),
        survival_cell(p_c=0.5, p_l=0.95, q_k=1.0, a_e=0.7),
        quality_cell(),
        quality_cell(rho_q=1.0, a_1=0.5, delta_clone=0.2),
    ])
    def test_probability_balance_within_1e_12(self, cell):
        w, _ = world_joint(cell)
        assert abs(w.sum() - 1.0) < 1e-12

    def test_catastrophe_zeroes_key_carrier_path(self):
        w, v = world_joint(survival_cell(g=0.10))
        cat = v["G"] == 1
        assert abs(w[cat].sum() - 0.10) < 1e-12
        assert np.all(v["K"][cat] == 0)
        assert np.all(v["C"][cat] == 0)
        assert np.all(v["L"][cat] == 0)

    def test_eligibility_marginal_matches_analytic_product(self):
        g = 0.10
        cell = survival_cell(g=g)
        w, v = world_joint(cell)
        for site in range(3):
            e_i = (BITS[v["C"], site] == 1) & (BITS[v["L"], site] == 1)
            expected = (1 - g) * cell.p_c * cell.p_l
            assert abs(w[e_i].sum() - expected) < 1e-12

    def test_observed_eligibility_error_rate(self):
        cell = survival_cell(a_e=0.7)
        w, v = world_joint(cell)
        for site in range(3):
            e_i = (BITS[v["C"], site] == 1) & (BITS[v["L"], site] == 1)
            ehat_i = BITS[v["Ehat"], site] == 1
            agree = e_i == ehat_i
            assert abs(w[agree].sum() - 0.7) < 1e-12

    def test_flat_high_quality_forces_h_z0_z1_all_ones(self):
        w, v = world_joint(survival_cell())
        live = w > 0
        assert np.all(v["H"][live] == 0b111)
        assert np.all(v["Z0"][live] == 0b111)
        assert np.all(v["Z1"][live] == 0b111)

    def test_quality_signal_accuracy_marginals(self):
        cell = quality_cell(a_1=0.9)
        w, v = world_joint(cell)
        for site in range(3):
            h_i = BITS[v["H"], site] == 1
            z0_agree = (BITS[v["Z0"], site] == 1) == h_i
            z1_agree = (BITS[v["Z1"], site] == 1) == h_i
            assert abs(w[z0_agree].sum() - 0.60) < 1e-12
            assert abs(w[z1_agree].sum() - 0.9) < 1e-12

    def test_latent_quality_marginal_is_half(self):
        w, v = world_joint(quality_cell(rho_q=0.5))
        for site in range(3):
            h_i = BITS[v["H"], site] == 1
            assert abs(w[h_i].sum() - 0.5) < 1e-12
