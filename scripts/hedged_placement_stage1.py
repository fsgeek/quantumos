"""Hedged-placement Stage 1: exact finite enumeration of an authored model.

Preregistration: docs/superpowers/specs/2026-07-13-hedged-placement-stage1-prereg.md
(approved revision ca26217, OTS-stamped). Boundary contract:
docs/superpowers/specs/2026-07-13-hedged-placement-boundary-contract.md.

The deciding instrument is exact enumeration over binary worlds with analytic
probabilities — no seeds, no sampling, no DES. Results are exact under the
declared finite model; they are not hardware estimates.

Site-vector convention: a three-site binary vector is an integer v in 0..7,
where site i holds bit (v >> (2 - i)) & 1, so the literal 0b101 reads
left-to-right as sites (0, 1, 2) = (1, 0, 1).
"""

from dataclasses import dataclass

import numpy as np

# BITS[v, i] is site i's bit of vector v under the module convention.
BITS = np.array([[(v >> (2 - i)) & 1 for i in range(3)] for v in range(8)])


def mix3_pmf(p: float, rho: float) -> np.ndarray:
    """Prereg §4 Mix3(p, rho): common-mode mixture preserving each site marginal.

    With probability rho all three sites share one Bernoulli(p) draw; with
    probability 1-rho the sites are iid Bernoulli(p). Returns the exact pmf
    over the 8 site vectors.
    """
    iid = np.prod(np.where(BITS == 1, p, 1.0 - p), axis=1)
    common = np.zeros(8)
    common[0b000] = 1.0 - p
    common[0b111] = p
    return rho * common + (1.0 - rho) * iid


def obs_pmf(a: float) -> np.ndarray:
    """P(observed vector | true vector) with independent per-site accuracy a.

    Returns an (8, 8) matrix M[true, observed] (prereg §4.1-4.2).
    """
    agree = BITS[:, None, :] == BITS[None, :, :]
    return np.prod(np.where(agree, a, 1.0 - a), axis=2)


@dataclass(frozen=True)
class Cell:
    """One parameter cell of the prereg §6 envelopes."""

    p_c: float
    p_l: float
    q_k: float
    rho_c: float
    rho_l: float
    rho_k: float
    g: float
    a_e: float
    rho_q: float
    a_0: float
    a_1: float
    delta_clone: float
    flat_high_quality: bool


_DELTA_ZERO = np.zeros(8)
_DELTA_ZERO[0b000] = 1.0

_WORLD_AXES = ("G", "K", "C", "L", "H", "Ehat", "Z0", "Z1")


def world_joint(cell: Cell) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Exact joint distribution over all binary worlds of one cell (prereg §4).

    Returns (weights, vars) where weights is a 1-D array of analytic world
    probabilities (zero-weight worlds removed) and vars maps each axis name to
    the vector index (0..7, or 0/1 for G) of that world. If G=1, key, carrier,
    and path vectors are forced to zero; otherwise the four mixtures are
    conditionally independent. Observations are conditioned per prereg
    §4.1-4.2: Ehat on E = C AND L, and Z0/Z1 on H.
    """
    # Axis supports: zero-weight slices are skipped up front. With g = 0 the
    # catastrophe branch has no mass; in the flat-high survival pass (prereg
    # §6.1, which fixes H = Z0 = Z1 = 1 via a_0 = a_1 = 1) the quality axes
    # are deltas at 0b111. The per-cell probability-balance control still
    # verifies that no live mass was dropped.
    full = np.arange(8, dtype=np.int8)
    g_axis = np.arange(2 if cell.g > 0 else 1, dtype=np.int8)
    hzz_axis = np.array([0b111], dtype=np.int8) if cell.flat_high_quality else full
    G, K, C, L, H, Ehat, Z0, Z1 = np.meshgrid(
        g_axis, full, full, full, hzz_axis, full, hzz_axis, hzz_axis,
        indexing="ij",
    )

    p_h = 1.0 if cell.flat_high_quality else 0.5
    k_pmf = mix3_pmf(cell.q_k, cell.rho_k)
    c_pmf = mix3_pmf(cell.p_c, cell.rho_c)
    l_pmf = mix3_pmf(cell.p_l, cell.rho_l)
    h_pmf = mix3_pmf(p_h, cell.rho_q)
    m_e = obs_pmf(cell.a_e)
    m_z0 = obs_pmf(cell.a_0)
    m_z1 = obs_pmf(cell.a_1)

    E = C & L  # bitwise AND of aligned site bits
    w = np.where(G == 1, cell.g, 1.0 - cell.g)
    w = w * np.where(G == 1, _DELTA_ZERO[K], k_pmf[K])
    w = w * np.where(G == 1, _DELTA_ZERO[C], c_pmf[C])
    w = w * np.where(G == 1, _DELTA_ZERO[L], l_pmf[L])
    w = w * h_pmf[H]
    w = w * m_e[E, Ehat]
    w = w * m_z0[H, Z0]
    w = w * m_z1[H, Z1]

    flat = w.reshape(-1)
    live = flat > 0.0
    axes = dict(zip(_WORLD_AXES, (G, K, C, L, H, Ehat, Z0, Z1)))
    return flat[live], {name: arr.reshape(-1)[live] for name, arr in axes.items()}


# --- Arm selectors (prereg §5) --------------------------------------------

PI = (0, 1, 2)
Q_MIN = 0.50
Q_HIGH, Q_LOW = 0.80, 0.40


def _scan_order(b: int, pi: tuple = PI) -> list[int]:
    """Canonical proposal order [b, pi_without_b]."""
    return [b] + [s for s in pi if s != b]


def anchor_of_z0(z0: int, pi: tuple = PI) -> int:
    """First site under pi with maximal initial forecast Z0 (prereg §5.2)."""
    bits = BITS[z0]
    best = bits.max()
    return next(s for s in pi if bits[s] == best)


def late_survival_table(pi: tuple = PI) -> np.ndarray:
    """T[ehat, b]: first site under [b, pi_without_b] observed eligible, else -1."""
    t = np.full((8, 3), -1, dtype=np.int8)
    for ehat in range(8):
        for b in range(3):
            for s in _scan_order(b, pi):
                if BITS[ehat, s]:
                    t[ehat, b] = s
                    break
    return t


def late_survival_reads(pi: tuple = PI) -> np.ndarray:
    """R[ehat, b]: site records inspected by the survival scan (3 if none lit)."""
    r = np.full((8, 3), 3, dtype=np.int8)
    for ehat in range(8):
        for b in range(3):
            for pos, s in enumerate(_scan_order(b, pi)):
                if BITS[ehat, s]:
                    r[ehat, b] = pos + 1
                    break
    return r


def late_quality_table(pi: tuple = PI) -> np.ndarray:
    """T[ehat, z1, b]: max late estimate among observed-eligible sites,
    ties under [b, pi_without_b]; -1 when the filtered set is empty."""
    t = np.full((8, 8, 3), -1, dtype=np.int8)
    for ehat in range(8):
        eligible = [s for s in pi if BITS[ehat, s]]
        if not eligible:
            continue
        for z1 in range(8):
            best = max(BITS[z1, s] for s in eligible)
            for b in range(3):
                t[ehat, z1, b] = next(
                    s for s in _scan_order(b, pi)
                    if s in eligible and BITS[z1, s] == best
                )
    return t


_TABLE_CACHE: dict[tuple, tuple] = {}


def _tables(pi: tuple):
    if pi not in _TABLE_CACHE:
        _TABLE_CACHE[pi] = (
            late_survival_table(pi),
            late_survival_reads(pi),
            late_quality_table(pi),
            np.array([anchor_of_z0(z0, pi) for z0 in range(8)], dtype=np.int8),
        )
    return _TABLE_CACHE[pi]


def _site_bit(vec: np.ndarray, site: np.ndarray) -> np.ndarray:
    """Bit of each world's vector at each world's site; 0 where site == -1."""
    return np.where(site >= 0, (vec >> (2 - np.maximum(site, 0))) & 1, 0)


def evaluate_arms(
    v: dict[str, np.ndarray],
    delta_clone: float,
    quality_pass: bool,
    pi: tuple = PI,
    force_late_to_anchor: bool = False,
) -> dict[str, dict[str, np.ndarray]]:
    """Per-world arm outcomes (prereg §5): proposal, gate result, quality.

    Returns, for arms single / prebound / late / late_s: proposed site (-1 for
    no proposal), materialized, accepted, recovered quality (NaN when not
    materialized), and selector site reads. In the quality pass, `late` is the
    quality selector J_Q and `late_s` the survival comparator J_S; in the
    survival pass both coincide (§5.1-5.2). `force_late_to_anchor` implements
    the same-site identity control (§8.1); `pi` exists for the permutation-
    equivariance control (§8.6).
    """
    ls_table, ls_reads, lq_table, anchor_table = _tables(pi)
    ehat, z1 = v["Ehat"], v["Z1"]
    e_true = v["C"] & v["L"]
    k_complete = v["K"] == 0b111
    b = anchor_table[v["Z0"]] if quality_pass else np.full(len(ehat), pi[0], dtype=np.int8)

    anchored = np.where(_site_bit(ehat, b) == 1, b, -1)
    late_s = ls_table[ehat, b]
    late_q = lq_table[ehat, z1, b] if quality_pass else late_s
    if force_late_to_anchor:
        late_s = anchored
        late_q = anchored
    n = len(ehat)

    def outcomes(proposed, needs_key, reads):
        gate_ok = (proposed >= 0) & (_site_bit(e_true, proposed) == 1)
        if needs_key:
            gate_ok &= k_complete
        q_base = np.where(_site_bit(v["H"], proposed) == 1, Q_HIGH, Q_LOW)
        q = q_base - delta_clone if needs_key else q_base
        q = np.maximum(q, 0.0)
        quality = np.where(gate_ok, q, np.nan)
        accepted = gate_ok & (q >= Q_MIN)
        return {
            "proposed": proposed,
            "materialized": gate_ok,
            "accepted": accepted,
            "quality": quality,
            "reads": np.broadcast_to(reads, (n,)) if np.isscalar(reads) else reads,
        }

    return {
        "single": outcomes(anchored, needs_key=False, reads=1),
        "prebound": outcomes(anchored, needs_key=True, reads=1),
        "late": outcomes(
            late_q, needs_key=True,
            reads=np.full(n, 3, dtype=np.int8) if quality_pass else ls_reads[ehat, b],
        ),
        "late_s": outcomes(late_s, needs_key=True, reads=ls_reads[ehat, b]),
    }


# --- Recorded outcomes per cell (prereg §7) --------------------------------

_POPCOUNT = BITS.sum(axis=1)

_COSTS_SINGLE = {
    "allocated_carrier_qubits": 1,
    "allocated_key_qubits": 0,
    "construction_module_calls": 0,
    "decryption_participants_if_admitted": 1,
    "residue_qubits_after_materialization": 0,
}
_COSTS_PLURAL = {
    "allocated_carrier_qubits": 3,
    "allocated_key_qubits": 3,
    "construction_module_calls": 1,
    "decryption_participants_if_admitted": 4,
    "residue_qubits_after_materialization": 5,
}


def cell_statistics(
    cell: Cell, quality_pass: bool, world: tuple | None = None
) -> dict[str, float]:
    """Exact recorded outcomes and cost coordinates for one cell (prereg §7).

    All values are exact probabilities or expectations under the authored
    world law; conditional statistics carry their conditioning-event
    probability and are NaN when that event has zero mass. Cost coordinates
    are counts, never a scalar utility. `world` accepts a precomputed
    (weights, vars) pair so a cell is enumerated once per run.
    """
    w, v = world if world is not None else world_joint(cell)
    arms = evaluate_arms(v, cell.delta_clone, quality_pass)

    def p(mask):
        return float(w[mask].sum()) if mask.any() else 0.0

    def cond_mean(x, mask):
        mass = p(mask)
        return (float((w * x)[mask].sum()) / mass if mass > 0 else float("nan")), mass

    e_true = v["C"] & v["L"]
    k_complete = v["K"] == 0b111
    any_e = e_true > 0
    any_c = v["C"] > 0
    sum_c = _POPCOUNT[v["C"]]
    sum_k = _POPCOUNT[v["K"]]
    a_star_size = np.where(k_complete, _POPCOUNT[e_true], 0)
    anchor_table = _tables(PI)[3]
    anchor = anchor_table[v["Z0"]] if quality_pass else np.zeros(len(w), dtype=np.int8)
    c_at_anchor = _site_bit(v["C"], anchor) == 1

    # Per-site plural acceptability for the accepted-delivery miss (§7).
    q_base_site = np.where(BITS[v["H"]] == 1, Q_HIGH, Q_LOW)
    q_plural_site = np.maximum(q_base_site - cell.delta_clone, 0.0)
    e_site = BITS[e_true] == 1
    any_acceptable = (e_site & (q_plural_site >= Q_MIN)).any(axis=1)

    stats: dict[str, float] = {
        "plural.p_claim_recoverable": p(k_complete & any_c),
        "single.p_claim_recoverable": p(c_at_anchor),
    }

    for name, arm in arms.items():
        mat = arm["materialized"]
        q_filled = np.where(mat, np.nan_to_num(arm["quality"]), 0.0)
        stats[f"{name}.p_proposed"] = p(arm["proposed"] >= 0)
        stats[f"{name}.p_gate_admitted"] = p(mat)
        stats[f"{name}.p_materialized"] = p(mat)
        stats[f"{name}.p_accepted"] = p(arm["accepted"])
        q_mean, q_mass = cond_mean(q_filled, mat)
        stats[f"{name}.q_mean_given_materialized"] = q_mean
        stats[f"{name}.p_materialized_mass"] = q_mass
        stats[f"{name}.cost.selector_site_reads_mean"] = float(
            (w * arm["reads"]).sum()
        )
        consts = _COSTS_SINGLE if name == "single" else _COSTS_PLURAL
        for key, val in consts.items():
            stats[f"{name}.cost.{key}"] = val
        held = (
            _site_bit(v["C"], anchor)
            if name == "single"
            else (sum_c + sum_k)
        )
        stats[f"{name}.cost.forced_cleanup_qubits_mean"] = float(
            (w * held * ~mat).sum()
        )
        if name != "single":  # §7: single owns no alternate carrier
            stats[f"{name}.p_exercise_opportunity_miss"] = p(
                ~mat & k_complete & any_e
            )
            stats[f"{name}.p_accepted_delivery_miss"] = p(
                ~arm["accepted"] & k_complete & any_acceptable
            )

    late_acc = arms["late"]["accepted"]
    pre_acc = arms["prebound"]["accepted"]
    stats["pair.both"] = p(late_acc & pre_acc)
    stats["pair.late_only"] = p(late_acc & ~pre_acc)
    stats["pair.prebound_only"] = p(~late_acc & pre_acc)
    stats["pair.neither"] = p(~late_acc & ~pre_acc)
    stats["delta_m"] = stats["late.p_accepted"] - stats["prebound.p_accepted"]

    both_mat = arms["late"]["materialized"] & arms["prebound"]["materialized"]
    q_late = np.where(arms["late"]["materialized"], np.nan_to_num(arms["late"]["quality"]), 0.0)
    q_pre = np.where(arms["prebound"]["materialized"], np.nan_to_num(arms["prebound"]["quality"]), 0.0)
    diff, mass = cond_mean(q_late - q_pre, both_mat)
    stats["pair.q_diff_both_materialized"] = diff
    stats["pair.p_both_materialized"] = mass

    # Quality option value V_Q: quality selector J_Q (late) versus survival
    # selector J_S (late_s), conditional on an intact key, both selectors
    # materializing, and the stated survivor stratum (§7).
    q_ls = np.where(arms["late_s"]["materialized"], np.nan_to_num(arms["late_s"]["quality"]), 0.0)
    both_sel = arms["late"]["materialized"] & arms["late_s"]["materialized"]
    for label, stratum in (
        ("pooled", a_star_size >= 2),
        ("n2", a_star_size == 2),
        ("n3", a_star_size == 3),
    ):
        mask = k_complete & both_sel & stratum
        val, mass = cond_mean(q_late - q_ls, mask)
        stats[f"v_q.{label}"] = val
        stats[f"v_q.mass_{label}"] = mass

    return stats


# --- Controls, activation, labels (prereg §8-9) ----------------------------

EPS_M = 0.01
EPS_Q = 0.01
MIN_QUALITY_STRATUM_MASS = 0.05
BALANCE_TOL = 1e-12


def permute_sites(v: dict[str, np.ndarray], sigma: tuple) -> dict[str, np.ndarray]:
    """Relabel sites: old site s becomes sigma[s]. G is not a site vector."""
    table = np.zeros(8, dtype=np.int8)
    for vec in range(8):
        for s in range(3):
            table[vec] |= BITS[vec, s] << (2 - sigma[s])
    return {
        name: (arr if name == "G" else table[arr]) for name, arr in v.items()
    }


def _weighted(w, mask):
    return float(w[mask].sum()) if mask.any() else 0.0


def survival_activation(
    cell: Cell, world: tuple | None = None
) -> tuple[bool, str | None]:
    """Prereg §8 survival/path channel activation for one cell.

    The causal chain latent spread -> observable spread -> decision change ->
    outcome/cost change must be live, and there must be positive probability
    of an intact plural claim with an unavailable anchor and an exercisable
    alternate. Returns (activated, refusal_reason)."""
    w, v = world if world is not None else world_joint(cell)
    arms = evaluate_arms(v, cell.delta_clone, quality_pass=False)
    e_true = v["C"] & v["L"]
    k_complete = v["K"] == 0b111

    c_spread = _weighted(w, ~np.isin(v["C"], (0b000, 0b111))) > 0
    e_spread = _weighted(w, ~np.isin(e_true, (0b000, 0b111))) > 0
    if not e_spread:
        return False, (
            "CHANNEL_SILENCED.PATH" if c_spread else "CHANNEL_SILENCED.CARRIER"
        )

    anchor_dark = _site_bit(e_true, np.zeros(len(w), dtype=np.int8)) == 0
    alt_lit = (BITS[e_true][:, 1:] == 1).any(axis=1)
    if _weighted(w, k_complete & anchor_dark & alt_lit) == 0:
        return False, "CHANNEL_SILENCED.KERNEL"

    ehat_spread = _weighted(w, ~np.isin(v["Ehat"], (0b000, 0b111))) > 0
    if not ehat_spread:
        return False, "CHANNEL_SILENCED.INFORMATION"

    decision_moves = (
        _weighted(w, arms["late"]["proposed"] != arms["prebound"]["proposed"]) > 0
    )
    if not decision_moves:
        return False, "CHANNEL_SILENCED.DECISION"

    discordant = arms["late"]["accepted"] != arms["prebound"]["accepted"]
    reads_differ = float(
        (w * (arms["late"]["reads"] - arms["prebound"]["reads"])).sum()
    )
    if _weighted(w, discordant) == 0 and abs(reads_differ) == 0:
        return False, "CHANNEL_SILENCED.DECISION"
    return True, None


def quality_activation(
    cell: Cell, world: tuple | None = None
) -> tuple[bool, str | None]:
    """Prereg §8 quality channel activation for one cell.

    Requires at least two exercisable sites with different latent qualities,
    an informative late signal (a_1 > 0.5), a quality-driven decision change,
    and a both-materialize comparison stratum."""
    w, v = world if world is not None else world_joint(cell)
    arms = evaluate_arms(v, cell.delta_clone, quality_pass=True)
    e_true = v["C"] & v["L"]
    k_complete = v["K"] == 0b111

    e_site = BITS[e_true] == 1
    h_site = BITS[v["H"]] == 1
    exercisable = e_site & k_complete[:, None]
    two_plus = exercisable.sum(axis=1) >= 2
    high_among = (exercisable & h_site).any(axis=1)
    low_among = (exercisable & ~h_site).any(axis=1)
    if _weighted(w, two_plus & high_among & low_among) == 0:
        return False, "CHANNEL_SILENCED.QUALITY"

    if cell.a_1 <= 0.5:
        return False, "CHANNEL_SILENCED.INFORMATION"

    if _weighted(w, arms["late"]["proposed"] != arms["late_s"]["proposed"]) == 0:
        return False, "CHANNEL_SILENCED.DECISION"

    both_mat = arms["late"]["materialized"] & arms["late_s"]["materialized"]
    if _weighted(w, k_complete & both_mat) == 0:
        return False, "CHANNEL_SILENCED.KERNEL"
    return True, None


def label_delta_m(delta_m: float) -> str:
    """Prereg §9 accepted-delivery label for an activated cell."""
    if delta_m >= EPS_M:
        return "POSITIVE"
    if delta_m <= -EPS_M:
        return "NEGATIVE"
    return "NEUTRAL"


def label_v_q(v_q: float, mass: float) -> str:
    """Prereg §9 quality-option label; mass below the stratum floor cannot
    earn (or reject) the mechanism."""
    if not np.isfinite(v_q) or mass < MIN_QUALITY_STRATUM_MASS:
        return "QUALITY_UNIDENTIFIED"
    if v_q >= EPS_Q:
        return "QUALITY_POSITIVE"
    if v_q <= -EPS_Q:
        return "QUALITY_NEGATIVE"
    return "QUALITY_NEUTRAL"


def battery_readings(
    survival_labels: list,
    quality_labels: list,
    survival_max_abs: float,
    quality_max_abs: float,
    controls_passed: bool,
) -> dict[str, str]:
    """Prereg §9 battery-level readings from per-cell (label, activated)
    pairs. The full map is primary; these are only an index into it."""
    if not controls_passed:
        return {"battery": "REFUSED", "refusal_reason": "CONTROL_FAILED"}

    def channel(labels, max_abs, positive, negative, earned):
        if any(lab == positive and act for lab, act in labels):
            return earned
        material_negative = any(lab == negative and act for lab, act in labels)
        if max_abs > 1e-12 and not material_negative:
            return "REGION_THIN"
        return ""  # no prereg reading applies; the per-cell map carries it

    site = channel(
        survival_labels, survival_max_abs, "POSITIVE", "NEGATIVE",
        "SITE_CHOICE_DECISION_EARNED",
    )
    quality = channel(
        quality_labels, quality_max_abs, "QUALITY_POSITIVE", "QUALITY_NEGATIVE",
        "QUALITY_CHOICE_DECISION_EARNED",
    )
    survival_active = any(act for _, act in survival_labels)
    quality_active = any(act for _, act in quality_labels)
    earned = "DECISION_EARNED" in site or "DECISION_EARNED" in quality
    if not earned and survival_active and quality_active:
        battery = "NOT_DECISION_EARNED_IN_TESTED_ENVELOPE"
    else:
        battery = ""  # earned or incomplete: the channel readings are the index
    return {"site_choice": site, "quality_choice": quality, "battery": battery}


# --- The eight synthetic controls (prereg §8) ------------------------------


def _control_world(**kw):
    base = dict(G=0, K=0b111, C=0b111, L=0b111, H=0b111, Z0=0b111, Z1=0b111)
    base.update(kw)
    if "Ehat" not in base:
        base["Ehat"] = base["C"] & base["L"]
    return {k: np.array([val], dtype=np.int8) for k, val in base.items()}


def _survival_control_cell(**overrides):
    params = dict(
        p_c=0.8, p_l=0.8, q_k=0.9, rho_c=0.0, rho_l=0.0, rho_k=0.0,
        g=0.0, a_e=0.9, rho_q=0.0, a_0=1.0, a_1=1.0, delta_clone=0.0,
        flat_high_quality=True,
    )
    params.update(overrides)
    return Cell(**params)


def _quality_control_cell(**overrides):
    params = dict(
        p_c=0.8, p_l=0.8, q_k=0.99, rho_c=0.0, rho_l=0.0, rho_k=0.0,
        g=0.0, a_e=0.9, rho_q=0.5, a_0=0.60, a_1=0.9, delta_clone=0.1,
        flat_high_quality=False,
    )
    params.update(overrides)
    return Cell(**params)


def _arm_fields_equal(a, b) -> bool:
    same = np.array_equal(a["proposed"], b["proposed"])
    same &= np.array_equal(a["materialized"], b["materialized"])
    same &= np.array_equal(a["accepted"], b["accepted"])
    same &= np.array_equal(
        np.nan_to_num(a["quality"], nan=-1.0),
        np.nan_to_num(b["quality"], nan=-1.0),
    )
    return bool(same)


def run_controls() -> dict[str, dict]:
    """Execute the eight synthetic controls (prereg §8). All must pass before
    any deciding grid is evaluated; results are recorded in controls.json."""
    controls: dict[str, dict] = {}

    # 1. Same-site identity: late forced to the prebound site must match
    # prebound exactly on outcomes (selector reads excluded).
    ok = True
    for cell, qp in (
        (_survival_control_cell(), False),
        (_quality_control_cell(), True),
    ):
        _, v = world_joint(cell)
        arms = evaluate_arms(v, cell.delta_clone, qp, force_late_to_anchor=True)
        ok &= _arm_fields_equal(arms["late"], arms["prebound"])
    controls["same_site_identity"] = {"passed": ok}

    # 2. Forced rescue: key intact, anchor down, exactly one alternate truly
    # and observably eligible, quality high.
    v = _control_world(C=0b011, L=0b001, Ehat=0b001)
    arms = evaluate_arms(v, 0.0, quality_pass=False)
    controls["forced_rescue"] = {
        "passed": bool(
            not arms["prebound"]["materialized"][0]
            and arms["late"]["materialized"][0]
            and arms["late"]["accepted"][0]
            and arms["late"]["proposed"][0] == 2
        )
    }

    # 3. Direct-key loss: carriers and paths live, key incomplete; both
    # plural claims physically unrecoverable while single delivers.
    v = _control_world(K=0b110)
    arms = evaluate_arms(v, 0.0, quality_pass=False)
    controls["direct_key_loss"] = {
        "passed": bool(
            arms["single"]["materialized"][0]
            and not arms["prebound"]["materialized"][0]
            and not arms["late"]["materialized"][0]
        )
    }

    # 4. Flat quality: all eligible qualities and signals equal; the quality
    # selector retains the anchor and has zero quality option value.
    ok = True
    for flat in (0b111, 0b000):
        v = _control_world(H=flat, Z0=flat, Z1=flat)
        arms = evaluate_arms(v, 0.0, quality_pass=True)
        anchor = arms["prebound"]["proposed"][0]
        ok &= arms["late"]["proposed"][0] == anchor
        ok &= arms["late_s"]["proposed"][0] == anchor
    controls["flat_quality"] = {"passed": bool(ok)}

    # 5. Uninformative signal: a_1 = 0.5 is information-silenced regardless
    # of decision movement or observed outcome.
    activated, reason = quality_activation(_quality_control_cell(a_1=0.5))
    controls["uninformative_signal"] = {
        "passed": bool(not activated and reason == "CHANNEL_SILENCED.INFORMATION")
    }

    # 6. Permutation equivariance: jointly permuting site labels and pi
    # preserves every aggregate result.
    cell = _quality_control_cell()
    w, v = world_joint(cell)
    ref = evaluate_arms(v, cell.delta_clone, quality_pass=True)
    ok = True
    for sigma in ((1, 2, 0), (2, 1, 0)):
        v_p = permute_sites(v, sigma)
        pi_p = tuple(sigma)
        alt = evaluate_arms(v_p, cell.delta_clone, quality_pass=True, pi=pi_p)
        for arm in ("single", "prebound", "late", "late_s"):
            for field in ("materialized", "accepted"):
                ok &= (
                    abs(
                        float((w * ref[arm][field]).sum())
                        - float((w * alt[arm][field]).sum())
                    )
                    < BALANCE_TOL
                )
            q_ref = np.where(ref[arm]["materialized"], np.nan_to_num(ref[arm]["quality"]), 0.0)
            q_alt = np.where(alt[arm]["materialized"], np.nan_to_num(alt[arm]["quality"]), 0.0)
            ok &= abs(float((w * q_ref).sum()) - float((w * q_alt).sum())) < BALANCE_TOL
    controls["permutation_equivariance"] = {"passed": bool(ok)}

    # 7. Probability balance: enumerated world weights sum to one within
    # 1e-12 on representative cells of both envelopes.
    ok = True
    for cell in (
        _survival_control_cell(),
        _survival_control_cell(g=0.10, rho_c=1.0, rho_l=1.0, rho_k=1.0),
        _survival_control_cell(p_c=0.5, p_l=0.95, q_k=1.0, a_e=0.7),
        _quality_control_cell(),
        _quality_control_cell(rho_q=1.0, a_1=0.5, delta_clone=0.2),
    ):
        w, _ = world_joint(cell)
        ok &= abs(float(w.sum()) - 1.0) < BALANCE_TOL
    controls["probability_balance"] = {"passed": bool(ok)}

    # 8. Shared-penalty invariance: delta_clone moves absolute plural quality
    # but not late-minus-prebound selection, Delta_M, or V_Q.
    stats = {
        d: cell_statistics(_quality_control_cell(delta_clone=d), quality_pass=True)
        for d in (0.0, 0.10, 0.20)
    }
    base = stats[0.0]
    ok = True
    for d in (0.10, 0.20):
        s = stats[d]
        ok &= abs(s["delta_m"] - base["delta_m"]) < BALANCE_TOL
        both_nan = not (np.isfinite(s["v_q.pooled"]) or np.isfinite(base["v_q.pooled"]))
        ok &= both_nan or abs(s["v_q.pooled"] - base["v_q.pooled"]) < BALANCE_TOL
        ok &= abs(s["late.p_proposed"] - base["late.p_proposed"]) < BALANCE_TOL
        ok &= (
            abs(
                s["late.q_mean_given_materialized"]
                - (base["late.q_mean_given_materialized"] - d)
            )
            < BALANCE_TOL
        )
    controls["shared_penalty_invariance"] = {"passed": bool(ok)}

    return controls


# --- Grids and artifacts (prereg §6, §11) ----------------------------------

import csv
import hashlib
import json
import subprocess
from dataclasses import fields as dataclass_fields
from pathlib import Path

PREREG_COMMIT = "ca262178b327d5657973054cb06049c0050a568f"
PREREG_PATH = "docs/superpowers/specs/2026-07-13-hedged-placement-stage1-prereg.md"

SURVIVAL_AXES = {
    "p_c": (0.50, 0.80, 0.95),
    "p_l": (0.50, 0.80, 0.95),
    "q_k": (0.90, 0.99, 1.00),
    "rho_c_rho_l": ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.5, 0.5), (1.0, 1.0)),
    "rho_k": (0.0, 1.0),
    "g": (0.0, 0.10),
    "a_e": (0.70, 0.90, 1.00),
}

QUALITY_PROFILES = {
    "carrier-scarce": (0.50, 0.90, 0.0, 0.0),
    "path-scarce": (0.90, 0.50, 0.0, 0.0),
    "balanced-independent": (0.80, 0.80, 0.0, 0.0),
    "balanced-common": (0.80, 0.80, 1.0, 1.0),
    "abundant-independent": (0.95, 0.95, 0.0, 0.0),
}

QUALITY_AXES = {
    "a_e": (0.70, 0.90, 1.00),
    "rho_q": (0.0, 0.5, 1.0),
    "a_1": (0.50, 0.70, 0.90, 1.00),
    "delta_clone": (0.00, 0.10, 0.20),
}


def survival_grid() -> list[Cell]:
    """Prereg §6.1: the 1,620-cell survival/path envelope, quality flat-high."""
    cells = []
    for p_c in SURVIVAL_AXES["p_c"]:
        for p_l in SURVIVAL_AXES["p_l"]:
            for q_k in SURVIVAL_AXES["q_k"]:
                for rho_c, rho_l in SURVIVAL_AXES["rho_c_rho_l"]:
                    for rho_k in SURVIVAL_AXES["rho_k"]:
                        for g in SURVIVAL_AXES["g"]:
                            for a_e in SURVIVAL_AXES["a_e"]:
                                cells.append(Cell(
                                    p_c=p_c, p_l=p_l, q_k=q_k,
                                    rho_c=rho_c, rho_l=rho_l, rho_k=rho_k,
                                    g=g, a_e=a_e,
                                    rho_q=0.0, a_0=1.0, a_1=1.0,
                                    delta_clone=0.0, flat_high_quality=True,
                                ))
    return cells


def quality_grid() -> list[Cell]:
    """Prereg §6.2: the 540-cell quality envelope over five named profiles."""
    cells = []
    for p_c, p_l, rho_c, rho_l in QUALITY_PROFILES.values():
        for a_e in QUALITY_AXES["a_e"]:
            for rho_q in QUALITY_AXES["rho_q"]:
                for a_1 in QUALITY_AXES["a_1"]:
                    for delta_clone in QUALITY_AXES["delta_clone"]:
                        cells.append(Cell(
                            p_c=p_c, p_l=p_l, q_k=0.99,
                            rho_c=rho_c, rho_l=rho_l, rho_k=0.0,
                            g=0.0, a_e=a_e,
                            rho_q=rho_q, a_0=0.60, a_1=a_1,
                            delta_clone=delta_clone, flat_high_quality=False,
                        ))
    return cells


# Conditional statistics may be NaN when their conditioning event has zero
# mass (the mass is always reported beside them); NaN anywhere else is a
# NUMERIC_INVALID refusal.
_NAN_ALLOWED = (
    "q_mean_given_materialized",
    "pair.q_diff_both_materialized",
    "v_q.pooled",
    "v_q.n2",
    "v_q.n3",
)


def battery_rows(cells: list[Cell], quality_pass: bool) -> list[dict]:
    """Evaluate cells into recorded rows with activation, refusal, and label
    (prereg §7-9). Refusals are data: silenced cells appear with reasons."""
    rows = []
    for cell in cells:
        world = world_joint(cell)
        balance_error = abs(float(world[0].sum()) - 1.0)
        stats = cell_statistics(cell, quality_pass, world=world)
        activate = quality_activation if quality_pass else survival_activation
        activated, reason = activate(cell, world=world)

        numeric_ok = all(
            np.isfinite(val)
            for key, val in stats.items()
            if not any(key.endswith(suffix) for suffix in _NAN_ALLOWED)
        )
        if balance_error > BALANCE_TOL:
            activated, refusal = False, "PROBABILITY_IMBALANCE"
        elif not numeric_ok:
            activated, refusal = False, "NUMERIC_INVALID"
        elif not activated:
            refusal = reason
        else:
            refusal = ""

        if not activated:
            label = ""
        elif quality_pass:
            label = label_v_q(stats["v_q.pooled"], stats["v_q.mass_pooled"])
        else:
            label = label_delta_m(stats["delta_m"])

        row = {
            f"param.{f.name}": getattr(cell, f.name)
            for f in dataclass_fields(Cell)
        }
        row.update(stats)
        if quality_pass:
            row["label_delta_m"] = label_delta_m(stats["delta_m"]) if activated else ""
        row["activated"] = bool(activated)
        row["refusal_reason"] = refusal
        row["label"] = label
        row["balance_error"] = balance_error
        rows.append(row)
    return rows


def summarize(survival_rows, quality_rows, controls) -> dict:
    """summary.json content: activation, refusal, cell counts, extrema, and
    battery readings (prereg §11)."""
    controls_passed = all(c["passed"] for c in controls.values())

    def counts_of(rows, key):
        counts: dict[str, int] = {}
        for r in rows:
            if r[key]:
                counts[r[key]] = counts.get(r[key], 0) + 1
        return counts

    s_act = [r for r in survival_rows if r["activated"]]
    q_act = [r for r in quality_rows if r["activated"]]
    survival_max_abs = max((abs(r["delta_m"]) for r in s_act), default=0.0)
    quality_finite = [
        r for r in q_act
        if np.isfinite(r["v_q.pooled"])
        and r["v_q.mass_pooled"] >= MIN_QUALITY_STRATUM_MASS
    ]
    quality_max_abs = max(
        (abs(r["v_q.pooled"]) for r in quality_finite), default=0.0
    )

    def with_params(row, value):
        return {"value": value, **{k: row[k] for k in row if k.startswith("param.")}}

    extrema = {}
    if s_act:
        best = max(s_act, key=lambda r: r["delta_m"])
        worst = min(s_act, key=lambda r: r["delta_m"])
        extrema["survival_delta_m_max"] = with_params(best, best["delta_m"])
        extrema["survival_delta_m_min"] = with_params(worst, worst["delta_m"])
    if quality_finite:
        best = max(quality_finite, key=lambda r: r["v_q.pooled"])
        worst = min(quality_finite, key=lambda r: r["v_q.pooled"])
        extrema["quality_v_q_max"] = with_params(best, best["v_q.pooled"])
        extrema["quality_v_q_min"] = with_params(worst, worst["v_q.pooled"])

    readings = battery_readings(
        [(r["label"], r["activated"]) for r in survival_rows],
        [(r["label"], r["activated"]) for r in quality_rows],
        survival_max_abs,
        quality_max_abs,
        controls_passed,
    )
    return {
        "battery_readings": readings,
        "controls_passed": controls_passed,
        "cells": {
            "survival_total": len(survival_rows),
            "survival_activated": len(s_act),
            "quality_total": len(quality_rows),
            "quality_activated": len(q_act),
        },
        "refusals": {
            "survival": counts_of(survival_rows, "refusal_reason"),
            "quality": counts_of(quality_rows, "refusal_reason"),
        },
        "labels": {
            "survival": counts_of(survival_rows, "label"),
            "quality": counts_of(quality_rows, "label"),
        },
        "extrema": extrema,
    }


def _sanitize(obj):
    """JSON-safe deep copy: numpy scalars to python, non-finite to None."""
    if isinstance(obj, dict):
        return {k: _sanitize(x) for k, x in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(x) for x in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return f if np.isfinite(f) else None
    return obj


def _write_json(path: Path, obj) -> None:
    path.write_text(
        json.dumps(_sanitize(obj), indent=2, sort_keys=True) + "\n"
    )


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    param_cols = sorted({k for r in rows for k in r if k.startswith("param.")})
    other_cols = sorted({k for r in rows for k in r if not k.startswith("param.")})
    columns = param_cols + other_cols
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in columns})


def resolve_run_dir(root: Path, base: str) -> Path:
    """First run gets the base name; later runs are labelled replications
    (prereg §11). Directory identity is excluded from byte-identity."""
    candidate = root / base
    n = 0
    while candidate.exists():
        n += 1
        candidate = root / f"{base}-replication-{n}"
    return candidate


def write_artifacts(
    run_dir: Path, manifest, controls, survival_rows, quality_rows, summary
) -> None:
    """Write the five prereg §11 artifacts. Content carries no wall-clock
    metadata, so a valid rerun is byte-identical."""
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_json(run_dir / "manifest.json", manifest)
    _write_json(run_dir / "controls.json", controls)
    _write_csv(run_dir / "survival.csv", survival_rows)
    _write_csv(run_dir / "quality.csv", quality_rows)
    _write_json(run_dir / "summary.json", summary)


def build_manifest() -> dict:
    """Prereg commit, implementation commit, source hash, and exact grids
    (prereg §11). The grids are given as axis specifications; every CSV row
    also carries its full cell parameters, so the grids are exact in the
    artifacts."""
    src = Path(__file__).read_bytes()
    try:
        impl_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        impl_commit = "UNKNOWN"
    return {
        "preregistration_commit": PREREG_COMMIT,
        "preregistration_path": PREREG_PATH,
        "implementation_commit": impl_commit,
        "source_sha256": hashlib.sha256(src).hexdigest(),
        "grids": {
            "survival_axes": {k: list(v) for k, v in SURVIVAL_AXES.items()},
            "survival_fixed": {
                "rho_q": 0.0, "a_0": 1.0, "a_1": 1.0, "delta_clone": 0.0,
                "flat_high_quality": True,
            },
            "survival_cells": 1620,
            "quality_profiles": {k: list(v) for k, v in QUALITY_PROFILES.items()},
            "quality_axes": {k: list(v) for k, v in QUALITY_AXES.items()},
            "quality_fixed": {"q_k": 0.99, "rho_k": 0.0, "g": 0.0, "a_0": 0.60},
            "quality_cells": 540,
        },
        "thresholds": {
            "epsilon_m": EPS_M,
            "epsilon_q": EPS_Q,
            "min_quality_stratum_mass": MIN_QUALITY_STRATUM_MASS,
            "balance_tol": BALANCE_TOL,
            "q_min": Q_MIN,
        },
    }


def main(out_root: Path = Path("runs")) -> Path:
    """The deciding run (prereg §11): controls first; the grids are evaluated
    only when all eight controls pass. Writes one immutable directory."""
    controls = run_controls()
    controls_passed = all(c["passed"] for c in controls.values())
    if controls_passed:
        survival_rows = battery_rows(survival_grid(), quality_pass=False)
        quality_rows = battery_rows(quality_grid(), quality_pass=True)
    else:
        survival_rows, quality_rows = [], []
    summary = summarize(survival_rows, quality_rows, controls)
    run_dir = resolve_run_dir(out_root, "hedged-stage1")
    write_artifacts(
        run_dir, build_manifest(), controls, survival_rows, quality_rows, summary
    )
    return run_dir


if __name__ == "__main__":
    print(main())
