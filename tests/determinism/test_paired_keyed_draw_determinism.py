import json
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run


def _canonicalize(value):
    """Recursively converts JSON-decoded lists/dicts into hashable tuples, so a
    semantic draw key (which may embed nested structures like a PathId's
    endpoint dicts) can be used as a dict key. Dict items are sorted by key so
    the canonical form does not depend on JSON field order."""
    if isinstance(value, list):
        return tuple(_canonicalize(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _canonicalize(v)) for k, v in value.items()))
    return value


def _extract_keyed_draws(events_path: Path) -> dict[tuple, float]:
    """Maps every draw.sampled event to its semantic (stream, key) identity and
    the uniform it drew, so paired runs can be compared key-by-key (§10)."""
    draws: dict[tuple, float] = {}
    for line in events_path.read_text().splitlines():
        if not line:
            continue
        event = json.loads(line)
        if event["event_type"] != "draw.sampled":
            continue
        payload = event["payload"]
        semantic_key = (payload["stream"], _canonicalize(payload["key"]))
        draws[semantic_key] = payload["uniform"]
    return draws


def _epoch() -> CalibrationEpoch:
    # Matches qsim.core.engine._synthesize_ports / _endpoints_for: for the
    # switch_capacity_c=2 used by both s0_config and s1_config below, the
    # engine synthesizes 4 ports (M0..M3) and cycles lease-endpoint requests
    # through the 4 adjacent pairs -- (M0,M1), (M1,M2), (M2,M3), (M3,M0) --
    # never just one fixed pair. A single-path epoch (e.g. one keyed on
    # "mod-a"/"mod-b", which never matches the engine's synthesized module
    # ids at all) leaves every requested path uncalibrated:
    # BernoulliHeraldingModel.success_probability then KeyErrors, the engine's
    # guard defaults p to 0.0, and heralding never succeeds for the whole run.
    # That silently limits this test's coverage to only the "herald"/"retry"
    # draw streams (never "decode" or "round_outcome"), and -- with
    # HERALD_RETRY_INTERVAL_S=1e-4s racing a 5s deadline_slack_s -- blows up
    # each round into tens of thousands of busy-retries and a multi-minute,
    # multi-GB trace. Calibrate every path the engine can actually synthesize
    # for this switch_capacity_c instead.
    ports = [PortId(module_id=f"M{i}", port_index=0) for i in range(4)]
    paths = [make_path_id(ports[i], ports[(i + 1) % len(ports)]) for i in range(len(ports))]
    return CalibrationEpoch(
        epoch_id="paired-draw-epoch",
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


def test_paired_s0_and_s1_runs_agree_on_every_shared_semantic_draw(tmp_path):
    """§10's common-random-numbers contract: two runs sharing run_seed but using
    different policies (S0 vs S1) must draw the *same* uniform for any semantic
    key (stream, key) both runs happen to touch, even though the policies make
    different numbers of draws in different orders (§16.4)."""
    run_seed = 7
    epoch = _epoch()

    s0_config = RunConfig(
        run_seed=run_seed,
        scheduler="S0",
        epoch=epoch,
        arrival_rate_hz=1.0,
        leases_per_round=1,
        deadline_slack_s=5.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.01,
        max_sim_time_s=100.0,
    )
    s1_config = RunConfig(
        run_seed=run_seed,
        scheduler="S1",
        epoch=epoch,
        arrival_rate_hz=1.0,
        leases_per_round=1,
        deadline_slack_s=5.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.01,
        max_sim_time_s=100.0,
        admission_theta=0.0,  # admit everything: keeps S1's admission decisions
                              # identical to S0's over this light load, so the
                              # two runs' round processing stays aligned and the
                              # shared-key fraction (§10) stays high enough to
                              # give this test a non-trivial sample.
        pregen_low_water_mark=1,
    )

    s0_dir = run(s0_config, tmp_path / "s0")
    s1_dir = run(s1_config, tmp_path / "s1")

    draws_s0 = _extract_keyed_draws(s0_dir / "events.jsonl")
    draws_s1 = _extract_keyed_draws(s1_dir / "events.jsonl")

    shared_keys = set(draws_s0) & set(draws_s1)
    assert len(shared_keys) > 0, "paired runs shared no semantic draw keys at all"

    mismatches = [
        (key, draws_s0[key], draws_s1[key])
        for key in shared_keys
        if draws_s0[key] != draws_s1[key]
    ]
    assert mismatches == [], (
        f"{len(mismatches)}/{len(shared_keys)} shared semantic keys received "
        f"different uniforms across paired S0/S1 runs: {mismatches[:5]}"
    )
