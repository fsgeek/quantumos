"""Integration gate for the cause-tagged fidelity-at-outcome observable.

The defect: freshness_at_consumption reads fidelity_at_consumption ONLY from
lease.consumed, which the engine emits ONLY on round SUCCESS. So the observable
is blind on the failure side — it systematically excludes the aged-out leases
that CAUSED failures (survivor bias). The fix records per-lease fidelity at
EVERY round terminal, tagged by failure cause, since failure sub-types are
physically distinct and must NOT be averaged together.

This runs the REAL pipeline (qsim.experiments.run.run) on configs producing
(a) successes, (b) scoring failures, (c) capacity failures, and asserts the
real producer's lease.outcome_fidelity output is consumable by the real
fidelity_at_outcome view — the producer/consumer contract, integration-tested
against real producer output, not a hand-built fixture.
"""
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.observe import views
from qsim.observe.work_accounting import iter_events
from qsim.experiments.run import run

_PA = make_path_id(PortId("M0", 0), PortId("M1", 0))


def _epoch(**over):
    base = dict(
        epoch_id="e",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0, memory_access_wear_rate=0.0,
        heralding_p_per_path={_PA: 1.0}, heralded_fidelity_per_path={_PA: 0.9},
        round_success_logistic_midpoint=-10.0, round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=0.0, decoder_service_rate=1000.0,
    )
    base.update(over)
    return CalibrationEpoch(**base)


def _config(**over):
    base = dict(
        run_seed=7, scheduler="S0", epoch=_epoch(), arrival_rate_hz=1.0,
        leases_per_round=1, deadline_slack_s=100.0, switch_capacity_c=1,
        reconfig_delay_s=0.0, max_sim_time_s=40.0,
    )
    base.update(over)
    return RunConfig(**base)


def _outcome_events(ep: Path) -> list[dict]:
    return [e for e in iter_events(ep) if e["event_type"] == "lease.outcome_fidelity"]


# ---- (a) success side -----------------------------------------------------

def test_success_leases_tagged_outcome_success(tmp_path):
    ep = run(_config(), tmp_path / "run") / "events.jsonl"
    outcomes = _outcome_events(ep)
    assert outcomes, "a successful run must emit lease.outcome_fidelity events"

    consumed = [e for e in iter_events(ep) if e["event_type"] == "lease.consumed"]
    success = [e for e in outcomes if e["payload"]["outcome"] == "success"]
    assert success, "successful rounds must produce outcome=success records"
    # Exactly one outcome_fidelity per consumed lease, carrying the same fidelity.
    assert len(success) == len(consumed)
    for e in success:
        p = e["payload"]
        assert p["cause"] == "consumed"
        assert p["fidelity"] is not None and 0.0 <= p["fidelity"] <= 1.0

    dist = views.fidelity_at_outcome(ep)
    assert ("success", "consumed") in dist
    assert dist[("success", "consumed")], "success distribution must be non-empty"
    assert all(0.0 <= f <= 1.0 for f in dist[("success", "consumed")])


# ---- (b) scoring-failure side ---------------------------------------------

def _scoring_config(**over):
    # Heavy decay + a logistic that fails once fidelity has aged forces rounds
    # to herald, assemble, then FAIL the round_success scoring — the aged-out
    # leases the success-only observable was blind to.
    base = dict(
        epoch=_epoch(
            decay_rate_per_class={CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 1.0},
            round_success_logistic_midpoint=0.5, round_success_logistic_slope=20.0,
            decoder_service_rate=5.0,
        ),
        arrival_rate_hz=2.0, switch_capacity_c=1, max_sim_time_s=200.0,
        decay_control_enabled=True,
    )
    base.update(over)
    return _config(**base)


def test_scoring_failure_leases_have_cause_and_real_fidelity(tmp_path):
    ep = run(_scoring_config(), tmp_path / "run") / "events.jsonl"
    reasons = {e["payload"].get("reason")
               for e in iter_events(ep) if e["event_type"] == "round.failed"}
    assert "scoring_failure" in reasons, "config must actually produce scoring failures"

    failures = [e for e in _outcome_events(ep)
                if e["payload"]["outcome"] == "failure"
                and e["payload"]["cause"] == "scoring_failure"]
    assert failures, "scoring failures must emit failure/scoring_failure records"
    for e in failures:
        p = e["payload"]
        assert p["cause"] == "scoring_failure"
        # A heralded-then-aged lease has a REAL fidelity, not null.
        assert p["fidelity"] is not None and 0.0 <= p["fidelity"] <= 1.0

    dist = views.fidelity_at_outcome(ep)
    assert ("failure", "scoring_failure") in dist
    assert dist[("failure", "scoring_failure")]


# ---- (c) capacity-failure side --------------------------------------------

def test_capacity_failure_leases_are_null_and_no_herald(tmp_path):
    ep = run(
        _config(arrival_rate_hz=10.0, reconfig_delay_s=0.5, switch_capacity_c=1,
                max_sim_time_s=20.0),
        tmp_path / "run",
    ) / "events.jsonl"
    reasons = {e["payload"].get("reason")
               for e in iter_events(ep) if e["event_type"] == "round.failed"}
    assert "switch_capacity_exhausted" in reasons, "config must produce capacity failures"

    no_herald = [e for e in _outcome_events(ep)
                 if e["payload"]["cause"] == "no_herald"]
    assert no_herald, "capacity failures must emit cause=no_herald records"
    for e in no_herald:
        p = e["payload"]
        assert p["outcome"] == "failure"
        # CRITICAL: never existed (null), NOT rotted to zero.
        assert p["fidelity"] is None

    # The view EXCLUDES nulls, so a no_herald-only key never appears as a
    # populated distribution — the null side does not pollute the aggregate.
    dist = views.fidelity_at_outcome(ep)
    assert ("failure", "no_herald") not in dist


# ---- cause separation is the whole point ----------------------------------

def test_view_returns_cause_separated_distributions(tmp_path):
    ep = run(_scoring_config(), tmp_path / "run") / "events.jsonl"
    dist = views.fidelity_at_outcome(ep)
    # Both success and scoring-failure distributions are present and separable.
    assert ("success", "consumed") in dist
    assert ("failure", "scoring_failure") in dist
    # They are distinct lists (the fix's raison d'etre: do not average
    # success survivors with the aged-out failures).
    assert dist[("success", "consumed")] is not dist[("failure", "scoring_failure")]
    for values in dist.values():
        assert values, "no key should hold an empty list (nulls are excluded upstream)"
        assert all(0.0 <= f <= 1.0 for f in values)


def test_freshness_at_consumption_still_works(tmp_path):
    # The new observable must not disturb the existing success-only view.
    ep = run(_config(), tmp_path / "run") / "events.jsonl"
    fresh = views.freshness_at_consumption(ep)
    assert fresh
    assert all(0.0 <= f <= 1.0 for f in fresh)
