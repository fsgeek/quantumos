# Hedged-Placement Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone exact-enumeration instrument preregistered for the three-arm hedged-placement Stage 1 battery without running the deciding grids.

**Architecture:** One importable script owns finite probability kernels, vectorized selectors, exact reducers, controls, cell labelling, and deterministic artifacts. Focused tests are split by responsibility. The ordinary build path exposes only a `controls` command; the `decide` command requires an explicit acknowledgement and is not executed during implementation.

**Tech Stack:** Python 3.14, NumPy 2.5.1+, stdlib `argparse`/`csv`/`dataclasses`/`hashlib`/`json`/`pathlib`, pytest.

## Global Constraints

- Governing preregistration: `docs/superpowers/specs/2026-07-13-hedged-placement-stage1-prereg.md` at commit `ca262178b327d5657973054cb06049c0050a568f`.
- Direct protocol only: exactly 3 signal carriers and 3 all-required key qubits.
- Exact enumeration only; no random seed, Monte Carlo, DES, steady-state, or confidence intervals.
- No `qsim` engine, CLI, entity, policy, or persistent-ontology integration.
- No deciding grid may run during implementation or build verification.
- Build verification may execute only the eight preregistered controls and synthetic unit fixtures.
- Floating probability balance and identity tolerance: `1e-12`.
- Materiality: `epsilon_M=0.01`, `epsilon_Q=0.01`, minimum quality-stratum mass `0.05`.
- Output coordinates remain typed counts; no scalar utility or weighted net-benefit statistic.
- Default to ASCII in code and artifacts.

---

## File Structure

- Create `scripts/hedged_placement_stage1.py`: the only production module; finite kernels, selectors, reducers, controls, grids, labels, deterministic writers, and guarded CLI.
- Create `tests/experiments/test_hedged_placement_kernel.py`: probability kernels, grid definitions, and vector construction.
- Create `tests/experiments/test_hedged_placement_selectors.py`: anchor, survival selector, quality selector, and gate semantics.
- Create `tests/experiments/test_hedged_placement_controls.py`: all eight preregistered controls.
- Create `tests/experiments/test_hedged_placement_survival.py`: survival grid count, analytic cells, correlation boundaries, and key fragility.
- Create `tests/experiments/test_hedged_placement_quality.py`: quality grid count, `V_Q`, activation, stratum handling, and clone-penalty invariance.
- Create `tests/experiments/test_hedged_placement_artifacts.py`: deterministic JSON/CSV, manifest provenance, output-dir refusal, and CLI guard.

## Task 1: Finite Probability Kernel and Frozen Grids

**Files:**
- Create: `scripts/hedged_placement_stage1.py`
- Create: `tests/experiments/test_hedged_placement_kernel.py`

**Interfaces:**
- Consumes: NumPy only.
- Produces: `BITS3`, `SurvivalCell`, `QualityProfile`, `QualityCell`, `mix3_weights`, `signal_matrix`, `survival_cells`, `quality_cells`.

- [ ] **Step 1: Write failing kernel and grid tests**

```python
# tests/experiments/test_hedged_placement_kernel.py
import numpy as np

from scripts.hedged_placement_stage1 import (
    BITS3,
    mix3_weights,
    quality_cells,
    signal_matrix,
    survival_cells,
)


def test_bits3_is_canonical_binary_order():
    assert BITS3.shape == (8, 3)
    assert BITS3.dtype == np.bool_
    assert BITS3[0].tolist() == [False, False, False]
    assert BITS3[-1].tolist() == [True, True, True]


def test_mix3_preserves_marginal_and_probability_balance():
    weights = mix3_weights(0.8, 0.5)
    assert np.isclose(weights.sum(), 1.0, atol=1e-12)
    assert np.allclose(weights @ BITS3.astype(float), [0.8, 0.8, 0.8])


def test_mix3_boundaries_are_independent_and_common_mode():
    independent = mix3_weights(0.5, 0.0)
    assert np.allclose(independent, np.full(8, 0.125))
    common = mix3_weights(0.5, 1.0)
    assert np.allclose(common[[0, 7]], [0.5, 0.5])
    assert np.allclose(common[1:7], 0.0)


def test_signal_matrix_rows_balance_and_match_accuracy():
    matrix = signal_matrix(0.7)
    assert matrix.shape == (8, 8)
    assert np.allclose(matrix.sum(axis=1), 1.0, atol=1e-12)
    assert np.isclose(matrix[0, 0], 0.7**3)
    assert np.isclose(matrix[7, 7], 0.7**3)


def test_preregistered_grid_sizes_are_frozen():
    assert len(survival_cells()) == 1620
    assert len(quality_cells()) == 540
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest tests/experiments/test_hedged_placement_kernel.py -v`

Expected: collection fails because `scripts.hedged_placement_stage1` does not exist.

- [ ] **Step 3: Implement constants, dataclasses, probability kernels, and grids**

```python
# scripts/hedged_placement_stage1.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product

import numpy as np

PREREG_COMMIT = "ca262178b327d5657973054cb06049c0050a568f"
TOL = 1e-12
EPSILON_M = 0.01
EPSILON_Q = 0.01
MIN_QUALITY_STRATUM_MASS = 0.05

BITS3 = np.asarray(tuple(product((False, True), repeat=3)), dtype=np.bool_)


@dataclass(frozen=True, slots=True)
class SurvivalCell:
    p_c: float
    p_l: float
    q_k: float
    rho_c: float
    rho_l: float
    rho_k: float
    g: float
    a_e: float


@dataclass(frozen=True, slots=True)
class QualityProfile:
    name: str
    p_c: float
    p_l: float
    rho_c: float
    rho_l: float


@dataclass(frozen=True, slots=True)
class QualityCell:
    profile: QualityProfile
    a_e: float
    rho_q: float
    a_1: float
    delta_clone: float


QUALITY_PROFILES = (
    QualityProfile("carrier-scarce", 0.50, 0.90, 0.0, 0.0),
    QualityProfile("path-scarce", 0.90, 0.50, 0.0, 0.0),
    QualityProfile("balanced-independent", 0.80, 0.80, 0.0, 0.0),
    QualityProfile("balanced-common", 0.80, 0.80, 1.0, 1.0),
    QualityProfile("abundant-independent", 0.95, 0.95, 0.0, 0.0),
)


def mix3_weights(p: float, rho: float) -> np.ndarray:
    if not 0.0 <= p <= 1.0 or not 0.0 <= rho <= 1.0:
        raise ValueError("p and rho must lie in [0, 1]")
    ones = BITS3.sum(axis=1)
    iid = np.power(p, ones) * np.power(1.0 - p, 3 - ones)
    common = np.zeros(8, dtype=float)
    common[0] = 1.0 - p
    common[7] = p
    weights = (1.0 - rho) * iid + rho * common
    if not np.isclose(weights.sum(), 1.0, atol=TOL):
        raise ArithmeticError("Mix3 probability imbalance")
    return weights


def signal_matrix(accuracy: float) -> np.ndarray:
    if not 0.0 <= accuracy <= 1.0:
        raise ValueError("accuracy must lie in [0, 1]")
    matches = (BITS3[:, None, :] == BITS3[None, :, :]).sum(axis=2)
    matrix = np.power(accuracy, matches) * np.power(1.0 - accuracy, 3 - matches)
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=TOL):
        raise ArithmeticError("signal probability imbalance")
    return matrix


def survival_cells() -> tuple[SurvivalCell, ...]:
    correlations = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.5, 0.5), (1.0, 1.0))
    return tuple(
        SurvivalCell(p_c, p_l, q_k, rho_c, rho_l, rho_k, g, a_e)
        for p_c, p_l, q_k, (rho_c, rho_l), rho_k, g, a_e in product(
            (0.50, 0.80, 0.95),
            (0.50, 0.80, 0.95),
            (0.90, 0.99, 1.00),
            correlations,
            (0.0, 1.0),
            (0.0, 0.10),
            (0.70, 0.90, 1.00),
        )
    )


def quality_cells() -> tuple[QualityCell, ...]:
    return tuple(
        QualityCell(profile, a_e, rho_q, a_1, delta_clone)
        for profile, a_e, rho_q, a_1, delta_clone in product(
            QUALITY_PROFILES,
            (0.70, 0.90, 1.00),
            (0.0, 0.5, 1.0),
            (0.50, 0.70, 0.90, 1.00),
            (0.00, 0.10, 0.20),
        )
    )
```

- [ ] **Step 4: Run kernel tests and verify GREEN**

Run: `pytest tests/experiments/test_hedged_placement_kernel.py -v`

Expected: 5 passed.

- [ ] **Step 5: Commit the probability kernel**

```bash
git add scripts/hedged_placement_stage1.py tests/experiments/test_hedged_placement_kernel.py
git commit -m "feat: add hedged-placement finite probability kernel"
```

## Task 2: Vectorized Selectors and Physical Evaluation

**Files:**
- Modify: `scripts/hedged_placement_stage1.py`
- Create: `tests/experiments/test_hedged_placement_selectors.py`

**Interfaces:**
- Consumes: `BITS3`, NumPy arrays shaped `(n, 3)`.
- Produces: `anchor_from_z0`, `select_prebound`, `select_survival`, `select_quality`, `selected_truth`, `quality_values`.

- [ ] **Step 1: Write failing selector tests**

```python
# tests/experiments/test_hedged_placement_selectors.py
import numpy as np

from scripts.hedged_placement_stage1 import (
    anchor_from_z0,
    quality_values,
    select_prebound,
    select_quality,
    select_survival,
    selected_truth,
)


def test_anchor_uses_first_maximum_in_canonical_order():
    z0 = np.asarray([[0, 1, 1], [0, 0, 0], [1, 1, 0]], dtype=bool)
    assert anchor_from_z0(z0).tolist() == [1, 0, 0]


def test_prebound_proposes_only_observed_anchor():
    e_hat = np.asarray([[0, 1, 1], [1, 0, 1]], dtype=bool)
    anchor = np.asarray([1, 1])
    assert select_prebound(e_hat, anchor).tolist() == [1, -1]


def test_survival_selector_prefers_anchor_then_canonical_order():
    e_hat = np.asarray([[1, 1, 1], [1, 0, 1], [0, 0, 0]], dtype=bool)
    anchor = np.asarray([2, 1, 0])
    assert select_survival(e_hat, anchor).tolist() == [2, 0, -1]


def test_quality_selector_maximizes_signal_and_keeps_anchor_on_tie():
    e_hat = np.asarray([[1, 1, 1], [1, 1, 0], [0, 0, 0]], dtype=bool)
    z1 = np.asarray([[1, 1, 0], [1, 1, 1], [1, 1, 1]], dtype=bool)
    anchor = np.asarray([1, 0, 2])
    assert select_quality(e_hat, z1, anchor).tolist() == [1, 0, -1]


def test_selected_truth_rejects_no_proposal_and_false_positive():
    truth = np.asarray([[1, 0, 1], [0, 1, 0], [1, 1, 1]], dtype=bool)
    selected = np.asarray([2, 0, -1])
    assert selected_truth(truth, selected).tolist() == [True, False, False]


def test_quality_values_apply_shared_plural_penalty():
    high = np.asarray([[1, 0, 1]], dtype=bool)
    single, plural = quality_values(high, 0.2)
    assert np.allclose(single, [[0.8, 0.4, 0.8]])
    assert np.allclose(plural, [[0.6, 0.2, 0.6]])
```

- [ ] **Step 2: Run selector tests and verify RED**

Run: `pytest tests/experiments/test_hedged_placement_selectors.py -v`

Expected: import fails for the new selector functions.

- [ ] **Step 3: Implement vectorized selectors and selected-site access**

```python
# append to scripts/hedged_placement_stage1.py
def anchor_from_z0(z0: np.ndarray) -> np.ndarray:
    return np.argmax(z0, axis=1).astype(np.int8)


def _anchor_is_candidate(candidates: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    rows = np.arange(candidates.shape[0])
    return candidates[rows, anchor]


def _first_candidate(candidates: np.ndarray) -> np.ndarray:
    any_candidate = candidates.any(axis=1)
    first = np.argmax(candidates, axis=1).astype(np.int8)
    return np.where(any_candidate, first, -1).astype(np.int8)


def select_prebound(e_hat: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    return np.where(_anchor_is_candidate(e_hat, anchor), anchor, -1).astype(np.int8)


def select_survival(e_hat: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    first = _first_candidate(e_hat)
    return np.where(_anchor_is_candidate(e_hat, anchor), anchor, first).astype(np.int8)


def select_quality(e_hat: np.ndarray, z1: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    high = e_hat & z1
    candidates = np.where(high.any(axis=1)[:, None], high, e_hat)
    first = _first_candidate(candidates)
    return np.where(_anchor_is_candidate(candidates, anchor), anchor, first).astype(np.int8)


def selected_truth(truth: np.ndarray, selected: np.ndarray) -> np.ndarray:
    valid = selected >= 0
    safe = np.where(valid, selected, 0)
    values = truth[np.arange(truth.shape[0]), safe]
    return valid & values


def selected_value(values: np.ndarray, selected: np.ndarray) -> np.ndarray:
    valid = selected >= 0
    safe = np.where(valid, selected, 0)
    return np.where(valid, values[np.arange(values.shape[0]), safe], np.nan)


def quality_values(high: np.ndarray, delta_clone: float) -> tuple[np.ndarray, np.ndarray]:
    single = np.where(high, 0.8, 0.4)
    plural = np.maximum(0.0, single - delta_clone)
    return single, plural
```

- [ ] **Step 4: Run selector tests and verify GREEN**

Run: `pytest tests/experiments/test_hedged_placement_selectors.py -v`

Expected: 6 passed.

- [ ] **Step 5: Commit selectors**

```bash
git add scripts/hedged_placement_stage1.py tests/experiments/test_hedged_placement_selectors.py
git commit -m "feat: add non-clairvoyant hedged-placement selectors"
```

## Task 3: Exact Row Tables, Arm Metrics, and Controls

**Files:**
- Modify: `scripts/hedged_placement_stage1.py`
- Create: `tests/experiments/test_hedged_placement_controls.py`

**Interfaces:**
- Consumes: selectors from Task 2.
- Produces: `AssignmentRows`, `assignment_rows`, `weighted_sum`,
  `quality_information_activated`, `run_controls`.

- [ ] **Step 1: Write failing control tests**

```python
# tests/experiments/test_hedged_placement_controls.py
from scripts.hedged_placement_stage1 import run_controls


EXPECTED_CONTROLS = {
    "same_site_identity",
    "forced_rescue",
    "direct_key_loss",
    "flat_quality",
    "uninformative_signal",
    "permutation_equivariance",
    "probability_balance",
    "shared_penalty_invariance",
}


def test_all_and_only_preregistered_controls_pass():
    controls = run_controls()
    assert set(controls) == EXPECTED_CONTROLS
    assert all(item["passed"] for item in controls.values())


def test_controls_include_machine_readable_evidence():
    controls = run_controls()
    for result in controls.values():
        assert result["evidence"]
        assert result["tolerance"] == 1e-12
```

- [ ] **Step 2: Run control tests and verify RED**

Run: `pytest tests/experiments/test_hedged_placement_controls.py -v`

Expected: import fails for `run_controls`.

- [ ] **Step 3: Add canonical assignment rows and weighted reduction**

```python
# append to scripts/hedged_placement_stage1.py
@dataclass(frozen=True, slots=True)
class AssignmentRows:
    c_idx: np.ndarray
    l_idx: np.ndarray
    e_hat_idx: np.ndarray
    h_idx: np.ndarray
    z0_idx: np.ndarray
    z1_idx: np.ndarray


def assignment_rows(include_quality: bool) -> AssignmentRows:
    shape = (8, 8, 8, 8, 8, 8) if include_quality else (8, 8, 8, 1, 1, 1)
    indices = np.indices(shape, dtype=np.int8).reshape(6, -1)
    return AssignmentRows(*(indices[i] for i in range(6)))


def weighted_sum(weights: np.ndarray, values: np.ndarray) -> float:
    result = float(np.dot(weights, values.astype(float)))
    if not np.isfinite(result):
        raise ArithmeticError("non-finite weighted reduction")
    return result


def _control(passed: bool, evidence: dict[str, object]) -> dict[str, object]:
    return {"passed": bool(passed), "tolerance": TOL, "evidence": evidence}


def quality_information_activated(a_1: float) -> bool:
    return a_1 > 0.5 + TOL
```

- [ ] **Step 4: Implement eight controls as direct synthetic fixtures**

Add `run_controls()` with one explicit block per preregistered control. Use the
Task 2 selectors directly, compute expected booleans/numbers, and return:

```python
def run_controls() -> dict[str, dict[str, object]]:
    controls: dict[str, dict[str, object]] = {}

    e = np.asarray([[True, False, True]])
    b = np.asarray([0])
    same_pre = select_prebound(e, b)
    same_late = select_survival(e, b)
    same_pre_materialized = bool(selected_truth(e, same_pre)[0])
    same_late_materialized = bool(selected_truth(e, same_late)[0])
    same_pre_cost = {
        "allocated_carrier_qubits": 3,
        "allocated_key_qubits": 3,
        "construction_module_calls": 1,
        "selector_site_reads": 0,
        "decryption_participants_if_admitted": 4,
        "residue_qubits_after_materialization": 5,
        "forced_cleanup_qubits_after_no_materialization": 0,
    }
    same_late_cost = dict(same_pre_cost)
    controls["same_site_identity"] = _control(
        (
            np.array_equal(same_pre, same_late)
            and same_pre_materialized == same_late_materialized
            and same_pre_cost == same_late_cost
        ),
        {
            "prebound": same_pre.tolist(),
            "late": same_late.tolist(),
            "prebound_materialized": same_pre_materialized,
            "late_materialized": same_late_materialized,
            "prebound_cost": same_pre_cost,
            "late_cost": same_late_cost,
        },
    )

    rescue_e = np.asarray([[False, True, False]])
    rescue_pre = select_prebound(rescue_e, b)
    rescue_late = select_survival(rescue_e, b)
    rescue_pre_delivers = bool(selected_truth(rescue_e, rescue_pre)[0])
    rescue_late_delivers = bool(selected_truth(rescue_e, rescue_late)[0])
    controls["forced_rescue"] = _control(
        not rescue_pre_delivers and rescue_late_delivers,
        {
            "prebound": int(rescue_pre[0]),
            "late": int(rescue_late[0]),
            "prebound_delivers": rescue_pre_delivers,
            "late_delivers": rescue_late_delivers,
        },
    )

    all_live = np.asarray([[True, True, True]])
    selected = select_prebound(all_live, b)
    selected_site_live = bool(selected_truth(all_live, selected)[0])
    key_complete = False
    plural_materialized = key_complete and selected_site_live
    single_materialized = selected_site_live
    controls["direct_key_loss"] = _control(
        not plural_materialized and single_materialized,
        {
            "key_complete": key_complete,
            "plural_materialized": plural_materialized,
            "single_materialized": single_materialized,
        },
    )

    flat_z = np.asarray([[True, True, True]])
    flat_e = np.ones((1, 3), dtype=bool)
    flat_anchor = np.asarray([2])
    flat_quality = select_quality(flat_e, flat_z, flat_anchor)
    flat_survival = select_survival(flat_e, flat_anchor)
    _, flat_values = quality_values(flat_z, 0.0)
    flat_option_value = float(
        selected_value(flat_values, flat_quality)[0]
        - selected_value(flat_values, flat_survival)[0]
    )
    controls["flat_quality"] = _control(
        flat_quality[0] == 2 and abs(flat_option_value) <= TOL,
        {"selected": int(flat_quality[0]), "quality_option_value": flat_option_value},
    )

    moved_quality = select_quality(flat_e, np.asarray([[True, False, False]]), flat_anchor)
    moved_survival = select_survival(flat_e, flat_anchor)
    information_activated = quality_information_activated(0.5)
    controls["uninformative_signal"] = _control(
        not information_activated and moved_quality[0] != moved_survival[0],
        {
            "a_1": 0.5,
            "information_activated": information_activated,
            "decision_changed": bool(moved_quality[0] != moved_survival[0]),
            "required_label": "CHANNEL_SILENCED",
        },
    )

    permuted_e = e[:, [2, 1, 0]]
    permuted_b = np.asarray([2])
    permuted = select_survival(permuted_e, permuted_b)
    controls["permutation_equivariance"] = _control(
        same_late[0] == 0 and permuted[0] == 2,
        {"original": int(same_late[0]), "permuted": int(permuted[0])},
    )

    balance_error = abs(float(mix3_weights(0.8, 0.5).sum()) - 1.0)
    controls["probability_balance"] = _control(
        balance_error <= TOL,
        {"absolute_error": balance_error},
    )

    penalty_high = np.asarray([[True, False, False]])
    penalty_anchor = np.asarray([1])
    quality_selected = select_quality(flat_e, penalty_high, penalty_anchor)
    survival_selected = select_survival(flat_e, penalty_anchor)
    _, p0 = quality_values(penalty_high, 0.0)
    _, p2 = quality_values(penalty_high, 0.2)
    gap_0 = float(
        selected_value(p0, quality_selected)[0]
        - selected_value(p0, survival_selected)[0]
    )
    gap_2 = float(
        selected_value(p2, quality_selected)[0]
        - selected_value(p2, survival_selected)[0]
    )
    controls["shared_penalty_invariance"] = _control(
        np.isclose(gap_0, gap_2, atol=TOL) and p2[0, 0] < p0[0, 0],
        {
            "delta_0_high_low_gap": gap_0,
            "delta_2_high_low_gap": gap_2,
            "delta_0_absolute_high": float(p0[0, 0]),
            "delta_2_absolute_high": float(p2[0, 0]),
        },
    )

    return controls
```

Task 4 and Task 5 add reducer-level regression tests for direct key loss,
uninformative signal, and shared-penalty invariance. The controls above remain
small synthetic worlds so build verification does not evaluate a deciding grid.

- [ ] **Step 5: Run control tests and verify GREEN**

Run: `pytest tests/experiments/test_hedged_placement_controls.py -v`

Expected: 2 passed.

- [ ] **Step 6: Commit row tables and controls**

```bash
git add scripts/hedged_placement_stage1.py tests/experiments/test_hedged_placement_controls.py
git commit -m "feat: add hedged-placement assignment controls"
```

## Task 4: Survival/Path Exact Reducer

**Files:**
- Modify: `scripts/hedged_placement_stage1.py`
- Create: `tests/experiments/test_hedged_placement_survival.py`

**Interfaces:**
- Consumes: `SurvivalCell`, probability kernels, selectors.
- Produces: `reduce_survival_cell(cell) -> dict[str, object]`, `run_survival_grid() -> list[dict[str, object]]`.

- [ ] **Step 1: Write failing analytic-cell tests**

```python
# tests/experiments/test_hedged_placement_survival.py
import numpy as np

from scripts.hedged_placement_stage1 import (
    SurvivalCell,
    reduce_survival_cell,
    run_survival_grid,
)


def _cell(**overrides):
    values = dict(p_c=0.5, p_l=0.8, q_k=1.0, rho_c=0.0, rho_l=0.0,
                  rho_k=0.0, g=0.0, a_e=1.0)
    values.update(overrides)
    return SurvivalCell(**values)


def test_perfect_observation_matches_closed_form_rescue_probability():
    row = reduce_survival_cell(_cell())
    e = 0.5 * 0.8
    expected_prebound = e
    expected_late = 1.0 - (1.0 - e) ** 3
    assert np.isclose(row["accepted_prebound"], expected_prebound, atol=1e-12)
    assert np.isclose(row["accepted_late"], expected_late, atol=1e-12)
    assert np.isclose(row["delta_m"], expected_late - expected_prebound, atol=1e-12)


def test_fully_common_site_channels_have_no_site_option():
    row = reduce_survival_cell(_cell(rho_c=1.0, rho_l=1.0))
    assert np.isclose(row["delta_m"], 0.0, atol=1e-12)


def test_distributed_direct_key_applies_all_required_survival():
    row = reduce_survival_cell(_cell(q_k=0.9, rho_k=0.0))
    assert np.isclose(row["key_complete_probability_no_catastrophe"], 0.9**3)
    assert row["accepted_prebound"] < row["accepted_single"]


def test_survival_grid_has_frozen_order_and_size():
    rows = run_survival_grid()
    assert len(rows) == 1620
    assert rows[0]["cell_index"] == 0
    assert rows[-1]["cell_index"] == 1619
```

- [ ] **Step 2: Run survival tests and verify RED**

Run: `pytest tests/experiments/test_hedged_placement_survival.py -v`

Expected: import fails for survival reducers.

- [ ] **Step 3: Implement survival row weights and arm reductions**

Implement `reduce_survival_cell` over `g x C x L x E_hat` rows. Use:

```python
def key_complete_probability(q_k: float, rho_k: float) -> float:
    return float(mix3_weights(q_k, rho_k)[7])


def classify_delta(value: float, epsilon: float = EPSILON_M) -> str:
    if value >= epsilon:
        return "POSITIVE"
    if value <= -epsilon:
        return "NEGATIVE"
    return "NEUTRAL"
```

For `G=0`, row weight is:

```text
(1-g) * P(C) * P(L) * P(E_hat | C and L)
```

For `G=1`, physical `C=L=K=0`; enumerate all `E_hat` patterns against all-false
truth with total branch weight `g`. For each row:

- anchor is zero;
- prebound/single use `select_prebound`;
- late uses `select_survival`;
- single materializes on selected true `E`;
- plural materialization is multiplied by conditional `P(K_complete | G=0)`;
- accepted equals materialized because the pass fixes high quality and zero clone
  penalty;
- plural exercise-opportunity miss requires complete key, some true `E`, and no
  materialization;
- structural cost expectations use `E[sum K | G=0]=3*q_k` and the selected-site
  materialization indicator; do not enumerate key vectors.

Return a flat row containing `asdict(cell)`, cell metrics, activation booleans,
`delta_m`, `cell_label`, and typed cost deltas. `run_survival_grid` enumerates
`survival_cells()` in tuple order and assigns `cell_index`.

- [ ] **Step 4: Run survival tests and verify GREEN**

Run: `pytest tests/experiments/test_hedged_placement_survival.py -v`

Expected: 4 passed.

- [ ] **Step 5: Commit survival reducer**

```bash
git add scripts/hedged_placement_stage1.py tests/experiments/test_hedged_placement_survival.py
git commit -m "feat: add exact hedged-placement survival reducer"
```

## Task 5: Quality Exact Reducer and Verdict Assembly

**Files:**
- Modify: `scripts/hedged_placement_stage1.py`
- Create: `tests/experiments/test_hedged_placement_quality.py`

**Interfaces:**
- Consumes: `QualityCell`, quality assignment rows, selectors.
- Produces: `reduce_quality_cell(cell) -> dict[str, object]`, `run_quality_grid()`, `assemble_summary(survival, quality, controls)`.

- [ ] **Step 1: Write failing quality and verdict tests**

```python
# tests/experiments/test_hedged_placement_quality.py
import numpy as np

from scripts.hedged_placement_stage1 import (
    QUALITY_PROFILES,
    QualityCell,
    assemble_summary,
    reduce_quality_cell,
    run_quality_grid,
)


def _cell(**overrides):
    values = dict(profile=QUALITY_PROFILES[2], a_e=1.0, rho_q=0.0,
                  a_1=1.0, delta_clone=0.0)
    values.update(overrides)
    return QualityCell(**values)


def test_perfect_late_signal_has_positive_quality_value():
    row = reduce_quality_cell(_cell())
    assert row["quality_activated"] is True
    assert row["v_q"] >= 0.01
    assert row["quality_label"] == "QUALITY_POSITIVE"


def test_flat_quality_refuses_quality_channel():
    row = reduce_quality_cell(_cell(rho_q=1.0))
    assert row["quality_activated"] is False
    assert row["quality_label"] == "CHANNEL_SILENCED"


def test_uninformative_signal_refuses_even_if_choices_move():
    row = reduce_quality_cell(_cell(a_1=0.5))
    assert row["information_activated"] is False
    assert row["quality_label"] == "CHANNEL_SILENCED"


def test_shared_clone_penalty_does_not_change_plural_contrasts():
    zero = reduce_quality_cell(_cell(delta_clone=0.0))
    two = reduce_quality_cell(_cell(delta_clone=0.2))
    assert np.isclose(zero["delta_m"], two["delta_m"], atol=1e-12)
    assert np.isclose(zero["v_q"], two["v_q"], atol=1e-12)
    assert two["mean_plural_quality"] < zero["mean_plural_quality"]


def test_quality_grid_size_is_frozen():
    assert len(run_quality_grid()) == 540


def test_summary_uses_region_map_without_erasing_coexisting_harm():
    controls = {"c": {"passed": True, "evidence": {}, "tolerance": 1e-12}}
    summary = assemble_summary(
        [{"activated": True, "delta_m": 0.02, "cell_label": "POSITIVE"},
         {"activated": True, "delta_m": -0.02, "cell_label": "NEGATIVE"}],
        [{"quality_activated": True, "v_q": 0.02,
          "quality_label": "QUALITY_POSITIVE"}],
        controls,
    )
    assert "SITE_CHOICE_DECISION_EARNED" in summary["readings"]
    assert "QUALITY_CHOICE_DECISION_EARNED" in summary["readings"]
    assert summary["survival_cell_counts"]["NEGATIVE"] == 1
```

- [ ] **Step 2: Run quality tests and verify RED**

Run: `pytest tests/experiments/test_hedged_placement_quality.py -v`

Expected: import fails for quality reducers.

- [ ] **Step 3: Implement exact quality weights and selector comparisons**

Build one canonical `AssignmentRows(include_quality=True)` table with 262,144 rows
over `C,L,E_hat,H,Z0,Z1`. For each cell, compute weights as indexed products of:

```text
P(C) * P(L) * P(E_hat | C and L)
     * P(H) * P(Z0 | H, a_0=0.60) * P(Z1 | H, a_1)
```

The quality pass fixes `g=0`, `q_k=0.99`, and `rho_k=0`; therefore:

```python
QUALITY_KEY_COMPLETE = 0.99**3
QUALITY_EXPECTED_LIVE_KEY_QUBITS = 3 * 0.99
```

Use `anchor_from_z0`, `select_prebound`, `select_survival`, and `select_quality` on
the row arrays. Materialization probabilities multiply deterministic true selected-
site eligibility by `QUALITY_KEY_COMPLETE`. For the paired cross-table, incomplete
key mass belongs to `neither`; because both plural arms share the same key, it can
never create a one-sided success.

Compute:

- accepted late-minus-prebound `delta_m`;
- `V_Q` on complete-key, both-selector-materialize, `|A_star|>=2` rows;
- `V_Q` for `|A_star|=2` and `3` separately;
- every conditioning mass before division;
- `QUALITY_UNIDENTIFIED` below mass `0.05`;
- `CHANNEL_SILENCED` for `rho_q=1`, `a_1=0.5`, absent decision movement, or absent
  both-materialize stratum;
- exact accepted-delivery and exercise-opportunity miss metrics;
- structural counts and shared-penalty invariance fields.

Reject a row with `NUMERIC_INVALID` if any result is NaN/inf or weights fail balance.

- [ ] **Step 4: Implement battery summary assembly**

```python
def assemble_summary(
    survival: list[dict[str, object]],
    quality: list[dict[str, object]],
    controls: dict[str, dict[str, object]],
) -> dict[str, object]:
    from collections import Counter

    controls_pass = all(bool(item["passed"]) for item in controls.values())
    survival_counts = Counter(str(row["cell_label"]) for row in survival)
    quality_counts = Counter(str(row["quality_label"]) for row in quality)
    readings: list[str] = []
    if not controls_pass:
        readings.append("REFUSED")
    else:
        thin_channels: list[str] = []
        if survival_counts["POSITIVE"]:
            readings.append("SITE_CHOICE_DECISION_EARNED")
        elif any(float(row["delta_m"]) > TOL for row in survival):
            thin_channels.append("site_choice")
        if quality_counts["QUALITY_POSITIVE"]:
            readings.append("QUALITY_CHOICE_DECISION_EARNED")
        elif any(float(row["v_q"]) > TOL for row in quality if row["v_q"] is not None):
            thin_channels.append("quality_choice")
        if thin_channels:
            readings.append("REGION_THIN")
        if not readings:
            both_activated = (
                any(bool(row["activated"]) for row in survival)
                and any(bool(row["quality_activated"]) for row in quality)
            )
            readings.append(
                "NOT_DECISION_EARNED_IN_TESTED_ENVELOPE" if both_activated else "REFUSED"
            )
    return {
        "controls_pass": controls_pass,
        "survival_cell_counts": dict(sorted(survival_counts.items())),
        "quality_cell_counts": dict(sorted(quality_counts.items())),
        "thin_channels": thin_channels if controls_pass else [],
        "readings": readings,
    }
```

- [ ] **Step 5: Run quality tests and verify GREEN**

Run: `pytest tests/experiments/test_hedged_placement_quality.py -v`

Expected: 6 passed. Runtime should remain suitable for one local build check; if it
exceeds 60 seconds, optimize array reuse without changing formulas or grid.

- [ ] **Step 6: Commit quality reducer and summary**

```bash
git add scripts/hedged_placement_stage1.py tests/experiments/test_hedged_placement_quality.py
git commit -m "feat: add exact hedged-placement quality reducer"
```

## Task 6: Deterministic Artifacts and Guarded CLI

**Files:**
- Modify: `scripts/hedged_placement_stage1.py`
- Create: `tests/experiments/test_hedged_placement_artifacts.py`

**Interfaces:**
- Consumes: controls, survival rows, quality rows, summary.
- Produces: `write_json`, `write_csv`, `script_sha256`, `implementation_commit`, `write_deciding_artifacts`, `build_parser`, `main`.

- [ ] **Step 1: Write failing artifact and guard tests**

```python
# tests/experiments/test_hedged_placement_artifacts.py
import json
from pathlib import Path

import pytest

from scripts.hedged_placement_stage1 import (
    PREREG_COMMIT,
    build_parser,
    main,
    write_deciding_artifacts,
)


def test_controls_command_writes_only_controls(tmp_path):
    output = tmp_path / "controls"
    assert main(["controls", "--output", str(output)]) == 0
    assert sorted(path.name for path in output.iterdir()) == ["controls.json"]
    payload = json.loads((output / "controls.json").read_text())
    assert all(item["passed"] for item in payload.values())


def test_decide_requires_explicit_acknowledgement():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["decide", "--output", "unused"])


def test_artifact_writer_refuses_existing_output(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    with pytest.raises(FileExistsError):
        write_deciding_artifacts(output, [], [], {}, {}, "deadbeef")


def test_synthetic_artifacts_are_deterministic_and_embed_prereg(tmp_path):
    args = dict(
        survival=[{"cell_index": 0, "delta_m": 0.1}],
        quality=[{"cell_index": 0, "v_q": 0.2}],
        controls={"c": {"passed": True}},
        summary={"readings": ["SITE_CHOICE_DECISION_EARNED"]},
        impl_commit="0123456789abcdef",
    )
    left = tmp_path / "left"
    right = tmp_path / "right"
    write_deciding_artifacts(left, **args)
    write_deciding_artifacts(right, **args)
    for name in ("manifest.json", "controls.json", "survival.csv", "quality.csv", "summary.json"):
        assert (left / name).read_bytes() == (right / name).read_bytes()
    manifest = json.loads((left / "manifest.json").read_text())
    assert manifest["prereg_commit"] == PREREG_COMMIT
```

- [ ] **Step 2: Run artifact tests and verify RED**

Run: `pytest tests/experiments/test_hedged_placement_artifacts.py -v`

Expected: import fails for artifact and CLI functions.

- [ ] **Step 3: Implement deterministic writers and provenance**

Use UTF-8, LF, sorted JSON keys, fixed CSV field ordering from sorted union of row
keys, and no wall-clock or output-path field. Refuse an existing output directory.

```python
# add to the import block in scripts/hedged_placement_stage1.py
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def implementation_commit() -> str:
    root = Path(subprocess.run(
        ("git", "rev-parse", "--show-toplevel"),
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip())
    script = Path(__file__).resolve().relative_to(root)
    status = subprocess.run(
        ("git", "status", "--porcelain", "--", str(script)),
        check=True,
        text=True,
        capture_output=True,
        cwd=root,
    ).stdout
    if status:
        raise RuntimeError("implementation script must be committed before deciding run")
    return subprocess.run(
        ("git", "rev-parse", "HEAD"),
        check=True,
        text=True,
        capture_output=True,
        cwd=root,
    ).stdout.strip()


def write_deciding_artifacts(
    output: Path,
    survival: list[dict[str, object]],
    quality: list[dict[str, object]],
    controls: dict[str, dict[str, object]],
    summary: dict[str, object],
    impl_commit: str,
) -> None:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    write_json(output / "controls.json", controls)
    write_csv(output / "survival.csv", survival)
    write_csv(output / "quality.csv", quality)
    write_json(output / "summary.json", summary)
    manifest = {
        "prereg_commit": PREREG_COMMIT,
        "implementation_commit": impl_commit,
        "script_sha256": script_sha256(),
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "survival_grid_size": len(survival_cells()),
        "quality_grid_size": len(quality_cells()),
        "epsilon_m": EPSILON_M,
        "epsilon_q": EPSILON_Q,
        "min_quality_stratum_mass": MIN_QUALITY_STRATUM_MASS,
        "survival_cells": [asdict(cell) for cell in survival_cells()],
        "quality_cells": [
            {**asdict(cell), "profile": asdict(cell.profile)} for cell in quality_cells()
        ],
    }
    write_json(output / "manifest.json", manifest)
```

The manifest must not contain wall time or output path. `implementation_commit()`
refuses a deciding run when the instrument itself differs from `HEAD`; unrelated
working-tree changes do not alter the recorded implementation identity.

- [ ] **Step 4: Implement guarded `controls` and `decide` commands**

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exact hedged-placement Stage 1 instrument")
    sub = parser.add_subparsers(dest="command", required=True)
    controls = sub.add_parser("controls")
    controls.add_argument("--output", required=True, type=Path)
    decide = sub.add_parser("decide")
    decide.add_argument("--output", required=True, type=Path)
    decide.add_argument(
        "--acknowledge-deciding-run",
        required=True,
        choices=("RUN-STAMPED-STAGE1",),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "controls":
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.mkdir(parents=True)
        write_json(args.output / "controls.json", run_controls())
        return 0
    controls = run_controls()
    if not all(bool(item["passed"]) for item in controls.values()):
        raise RuntimeError("CONTROL_FAILED: deciding run refused")
    survival = run_survival_grid()
    quality = run_quality_grid()
    summary = assemble_summary(survival, quality, controls)
    write_deciding_artifacts(
        args.output, survival, quality, controls, summary, implementation_commit()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run artifact tests and verify GREEN**

Run: `pytest tests/experiments/test_hedged_placement_artifacts.py -v`

Expected: 4 passed. This command exercises synthetic artifact fixtures and controls
only; it must not call `run_survival_grid` or `run_quality_grid` through the CLI.

- [ ] **Step 6: Commit guarded artifacts and CLI**

```bash
git add scripts/hedged_placement_stage1.py tests/experiments/test_hedged_placement_artifacts.py
git commit -m "feat: add guarded hedged-placement artifact runner"
```

## Task 7: Control-Only Build Verification and Implementation Handoff

**Files:**
- Modify only if verification exposes a defect in files created by Tasks 1-6.

**Interfaces:**
- Consumes: complete instrument and focused tests.
- Produces: reviewed implementation commit; no deciding artifacts.

- [ ] **Step 1: Run all focused tests**

Run:

```bash
pytest \
  tests/experiments/test_hedged_placement_kernel.py \
  tests/experiments/test_hedged_placement_selectors.py \
  tests/experiments/test_hedged_placement_controls.py \
  tests/experiments/test_hedged_placement_survival.py \
  tests/experiments/test_hedged_placement_quality.py \
  tests/experiments/test_hedged_placement_artifacts.py \
  -v
```

Expected: all focused tests pass. Although reducer tests evaluate synthetic cells,
no full preregistered grid artifact is produced and no battery reading is recorded.

- [ ] **Step 2: Run the full regression suite**

Run: `pytest -q`

Expected: all repository tests pass.

- [ ] **Step 3: Run the control-only command twice**

Run:

```bash
controls_a="$(mktemp -d)/output"
controls_b="$(mktemp -d)/output"
python scripts/hedged_placement_stage1.py controls --output "$controls_a"
python scripts/hedged_placement_stage1.py controls --output "$controls_b"
cmp "$controls_a/controls.json" "$controls_b/controls.json"
```

Expected: both commands exit 0 and `cmp` exits 0. Do not run the `decide` command.

- [ ] **Step 4: Inspect scope and provenance**

Run:

```bash
git diff --check
git status --short
git diff --stat ca262178b327d5657973054cb06049c0050a568f..HEAD
```

Expected: no whitespace errors; only the standalone script, focused tests, plan,
preregistration status/stamp, and task commits are in scope. No `runs/hedged-*`
deciding directory exists.

- [ ] **Step 5: Request code review before any deciding run**

Review must check formulas against every preregistration section, verify that the
eight controls are substantive, inspect exact cell ordering and artifact
determinism, and confirm that no build command executed `decide`. Any correction is
committed before the implementation commit is named for the deciding run.

The deciding command remains deliberately unexecuted:

```bash
python scripts/hedged_placement_stage1.py decide \
  --output runs/hedged-placement-stage1/deciding-run-001 \
  --acknowledge-deciding-run RUN-STAMPED-STAGE1
```

That command is shown only to define the later reviewed action. It must not be run
during plan execution.
