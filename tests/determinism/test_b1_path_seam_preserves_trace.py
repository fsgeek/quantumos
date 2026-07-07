"""B1 bit-identity oracle: pinned pre-refactor golden trace hashes.

The B1 seam promotes path selection from the engine-private round-robin
counter to an injected PathChoice strategy, behavior-preserving BY DEFAULT
(prereg B1). "Behavior-preserving" is asserted mechanically (spec §16.4:
same config + run_seed => identical trace hash): the hashes below were
captured against unmodified pre-B1 HEAD (commit ada7f87, branch
feat/field-battery-builds) and MUST stay green after the refactor. A red
here means the default chooser is not bit-identical to the old counter —
stop and fix, never re-pin.

Two pinned configs, because the round-robin counter makes their coverage
disjoint: at leases_per_round=2 the round's two consecutive counter pairs
ALWAYS share the middle port, so every round endpoint-conflicts before any
herald (conflict/retry/deferral coverage); the leases_per_round=1 variant
actually heralds, completes, scores, and still conflicts across overlapping
rounds (herald/scoring/completion coverage). Together they exercise every
path-choice-adjacent engine pathway on calibrated, distinct-p paths — unlike
the existing determinism config, whose uncalibrated single path never
heralds at all.
"""
from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run

from tests.determinism.test_trace_hash_determinism import _canonical_trace_hash

# Captured 2026-07-06 at pre-B1 HEAD ada7f87 by running these exact configs.
_GOLDEN_HASH_TWO_LEASES = (
    "b8a466a0985e295e85f1f045bae04d7b35e378befe83af675bbdaea1d4f5c41a"
)
_GOLDEN_HASH_ONE_LEASE = (
    "194e2bebc15e55f75b5c0c7de6c204650127212126983fd8438c765b38a588ef"
)


def _reference_config(leases_per_round: int) -> RunConfig:
    # The epoch ENUMERATES the engine's synthesized consecutive port pairs at
    # switch_capacity_c=2 (M0..M3 adjacent pairs, wrap included) with DISTINCT
    # p values, so heralding is reachable and a p-ranking policy would pick
    # differently — making this hash sensitive to any accidental policy swap.
    ports = [PortId(module_id=f"M{i}", port_index=0) for i in range(4)]
    paths = [make_path_id(ports[i], ports[(i + 1) % 4]) for i in range(4)]
    epoch = CalibrationEpoch(
        epoch_id="b1-golden-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.02, CoherenceClass.MEMORY: 0.005},
        memory_access_channel_s=0.002,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={paths[0]: 0.9, paths[1]: 0.7, paths[2]: 0.5, paths[3]: 0.3},
        heralded_fidelity_per_path={p: 0.9 for p in paths},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=8.0,
        round_success_slack_penalty_per_s=0.5,
        decoder_service_rate=4.0,
    )
    return RunConfig(
        run_seed=20260706,
        scheduler="S0",
        epoch=epoch,
        arrival_rate_hz=2.0,
        leases_per_round=leases_per_round,
        deadline_slack_s=3.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.02,
        max_sim_time_s=120.0,
    )


def test_default_path_choice_reproduces_pre_b1_conflict_and_retry_trace(tmp_path):
    run_dir = run(_reference_config(leases_per_round=2), tmp_path / "run")
    assert _canonical_trace_hash(run_dir / "events.jsonl") == _GOLDEN_HASH_TWO_LEASES


def test_default_path_choice_reproduces_pre_b1_heralding_trace(tmp_path):
    run_dir = run(_reference_config(leases_per_round=1), tmp_path / "run")
    assert _canonical_trace_hash(run_dir / "events.jsonl") == _GOLDEN_HASH_ONE_LEASE
