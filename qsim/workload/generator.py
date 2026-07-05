"""Workload generation for the qsim engine: Poisson arrivals and closed-loop
retries (design spec §9, §10).

Every stochastic draw is keyed by a semantic identity (arrival_index, never
event-heap or call order) and routed through qsim.core.rng.draw_uniform on
the `workload` stream, per §10's CRN (common random numbers) guarantee.
"""

import math

from qsim.core.rng import draw_uniform
from qsim.entities import RoundState, SyndromeRound


class WorkloadGenerator:
    STREAM = "workload"

    def __init__(self, run_seed: int, arrival_rate_hz: float,
                 leases_per_round: int, deadline_slack_s: float,
                 retry_cap: int | None = None):
        self.run_seed = run_seed
        self.arrival_rate_hz = arrival_rate_hz
        self.leases_per_round = leases_per_round
        self.deadline_slack_s = deadline_slack_s
        # None => unlimited retries (current closed-loop behaviour); N => stop
        # retrying (return None -> engine drops) once a lineage has been retried
        # N times. A sweep knob for the spiral-vs-overload question.
        self.retry_cap = retry_cap

    def next_arrival(self, after_time: float, arrival_index: int) -> SyndromeRound:
        # arrival_index is the semantic key for the interarrival draw — never event-heap order (§10).
        u = draw_uniform(self.run_seed, self.STREAM, ("arrival", arrival_index))
        interarrival_s = -math.log(1.0 - u) / self.arrival_rate_hz
        arrival_time = after_time + interarrival_s
        round_id = f"round-{arrival_index}"
        lease_ids = [f"{round_id}-lease-{i}" for i in range(self.leases_per_round)]
        return SyndromeRound(
            round_id=round_id,
            lease_ids=lease_ids,
            qubit_ids=[],
            arrival_time=arrival_time,
            deadline=arrival_time + self.deadline_slack_s,
            retry_ordinal=0,
            state=RoundState.PENDING,
        )

    def on_outcome(self, round: SyndromeRound, succeeded: bool) -> SyndromeRound | None:
        if succeeded:
            return None
        # Retry cap: a lineage already retried `retry_cap` times is not retried
        # again (None => engine drops it). retry_cap=0 disables retries entirely
        # (first failure drops). None => unlimited (default closed-loop policy).
        if self.retry_cap is not None and round.retry_ordinal >= self.retry_cap:
            return None
        # Failures otherwise retry. Same round_id preserves lineage across the retry chain.
        return SyndromeRound(
            round_id=round.round_id,
            lease_ids=list(round.lease_ids),
            qubit_ids=list(round.qubit_ids),
            arrival_time=round.arrival_time,
            deadline=round.deadline,
            retry_ordinal=round.retry_ordinal + 1,
            state=RoundState.PENDING,
        )
