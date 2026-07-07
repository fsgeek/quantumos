import hashlib
import json
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run


def _canonical_trace_hash(events_path: Path) -> str:
    """SHA-256 over a run's events, normalized so the guarantee (§13's
    trace-hash scope) is independent of the fresh run_id every run gets:
    run_id is replaced by a fixed placeholder wherever it appears, including
    inside causal_parent_id's (run_id, seq) pair, before hashing. Content must
    be identical across runs with the same config+run_seed - not the file's
    mtime or its embedded run_id."""
    digest = hashlib.sha256()
    for line in events_path.read_text().splitlines():
        if not line:
            continue
        event = json.loads(line)
        event["run_id"] = "RUN_ID"
        parent = event.get("causal_parent_id")
        if parent is not None:
            event["causal_parent_id"] = ["RUN_ID", parent[1]]
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        digest.update(canonical.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _config(run_seed: int) -> RunConfig:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    epoch = CalibrationEpoch(
        epoch_id="determinism-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.02, CoherenceClass.MEMORY: 0.005},
        memory_access_channel_s=0.002,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.6},
        heralded_fidelity_per_path={path: 0.9},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=8.0,
        round_success_slack_penalty_per_s=0.5,
        decoder_service_rate=4.0,
    )
    return RunConfig(
        run_seed=run_seed,
        scheduler="S0",
        epoch=epoch,
        arrival_rate_hz=2.0,
        leases_per_round=2,
        deadline_slack_s=3.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.02,
        max_sim_time_s=200.0,
    )


def _s1_pooling_config(run_seed: int) -> RunConfig:
    # Calibrate every path the engine synthesizes at switch_capacity_c=2
    # (M0..M3 adjacent pairs) so heralding — round AND pool replenish — is
    # actually reachable; see the paired-draw test for why a mismatched epoch
    # silently degenerates the run into a busy-retry storm.
    ports = [PortId(module_id=f"M{i}", port_index=0) for i in range(4)]
    paths = [make_path_id(ports[i], ports[(i + 1) % len(ports)]) for i in range(len(ports))]
    epoch = CalibrationEpoch(
        epoch_id="s1-pool-determinism-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.02, CoherenceClass.MEMORY: 0.005},
        memory_access_channel_s=0.002,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.6 for path in paths},
        heralded_fidelity_per_path={path: 0.9 for path in paths},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=8.0,
        round_success_slack_penalty_per_s=0.5,
        decoder_service_rate=4.0,
    )
    return RunConfig(
        run_seed=run_seed,
        scheduler="S1",
        epoch=epoch,
        arrival_rate_hz=1.0,
        leases_per_round=1,
        deadline_slack_s=3.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.02,
        max_sim_time_s=60.0,
        admission_theta=0.0,
        pregen_low_water_mark=1,
    )


def test_s1_run_with_live_pool_produces_identical_trace_hash(tmp_path):
    # B3: the pool going live must not cost S1 its determinism — same config +
    # run_seed gives a bit-identical trace, pool traffic included.
    config = _s1_pooling_config(run_seed=2026)

    run_dir_a = run(config, tmp_path / "run-a")
    run_dir_b = run(config, tmp_path / "run-b")

    events_a = (run_dir_a / "events.jsonl").read_text()
    assert '"pool.' in events_a, "the S1 determinism run must exercise the live pool"
    assert _canonical_trace_hash(run_dir_a / "events.jsonl") == _canonical_trace_hash(
        run_dir_b / "events.jsonl")


def test_same_config_and_run_seed_produce_identical_trace_hash(tmp_path):
    config = _config(run_seed=2024)

    run_dir_a = run(config, tmp_path / "run-a")
    run_dir_b = run(config, tmp_path / "run-b")

    hash_a = _canonical_trace_hash(run_dir_a / "events.jsonl")
    hash_b = _canonical_trace_hash(run_dir_b / "events.jsonl")

    assert hash_a == hash_b


def test_different_run_seed_produces_a_different_trace_hash(tmp_path):
    # Sanity check on the canonicalization itself: it must not be trivially
    # constant (e.g. hashing away everything that varies between runs).
    run_dir_a = run(_config(run_seed=1), tmp_path / "run-a")
    run_dir_b = run(_config(run_seed=2), tmp_path / "run-b")

    hash_a = _canonical_trace_hash(run_dir_a / "events.jsonl")
    hash_b = _canonical_trace_hash(run_dir_b / "events.jsonl")

    assert hash_a != hash_b
