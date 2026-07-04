# Review comments on `2026-07-04-quantum-os-simulator-design.md`

Reviewer: Codex
Date: 2026-07-04

Overall: strong design direction. The spec is unusually clear about the simulator's role as a sensitivity instrument rather than a prediction engine, and the negative-control framing is the right guardrail against self-fulfilling policy results. I would address the points below before treating it as implementation-ready.

## Comments

1. **Python 3.14 may be a reproducibility and iteration risk for v1**  
   Reference: lines 26-28; `pyproject.toml` also requires `>=3.14`.  
   The simulator is meant to be an iteration-speed research tool, but pinning v1 to Python 3.14 can make collaborator machines, CI images, and scientific tooling harder to use. If 3.14 is intentional, the spec should name the feature that requires it. Otherwise, consider targeting the oldest practical supported version, or document that 3.14 is a repository-wide constraint rather than a simulator design requirement.

2. **The "capture everything" requirement conflicts with checkpointing and trace replay unless event schema boundaries are specified**  
   Reference: lines 146-164 and 154-157.  
   `events.jsonl` is described as every state transition with causal parents, and checkpoints are full simulator snapshots. That is the right ambition, but the spec does not say what is authoritative after restore: the checkpoint state, the event log, or both. Please define restore semantics and event identity across forked runs from a warm checkpoint. Otherwise trace hashes, causal walks, and paired-run comparisons can become ambiguous once sweeps fork from the same warmed state.

3. **Common-random-number comparisons need a stronger contract than "named streams"**  
   Reference: lines 43-44, 137-138, and 211-213.  
   Paired S0/S1 runs will diverge structurally because admission, pre-generation, and retries change the number and order of stochastic calls. If stream consumption is event-driven, using the same named streams is not enough to guarantee a fair paired comparison. The spec should require counter-based or key-addressed random draws keyed by stable semantic IDs, or explicitly define where common random numbers are expected to remain valid and where divergence is accepted.

4. **The model Protocols need minimal method signatures and units before implementation starts**  
   Reference: lines 94-105.  
   The surfaces are listed conceptually, but not enough to prevent incompatible implementations. For example, `DecayModel.fidelity(age, coherence_class)` needs time units, whether it returns absolute fidelity or multiplicative retention, how calibration epochs enter, and whether memory-access spend composes before or after passive decay. `RoundSuccessModel` likewise needs to specify whether decoder latency is a raw duration, deadline miss flag, or continuous penalty. A small Protocol sketch would remove a lot of downstream interpretation risk.

5. **The baseline/control expectations may be too strong for all workloads**  
   Reference: lines 185-189 and 206-210.  
   The no-decay control says the S1-S0 gap should collapse. That is plausible for the perishability claim, but S1 also includes admission control and pre-generation, which can affect congestion, switch contention, and decoder backlog even when decay is disabled. Similarly, "faster decay must not improve outcomes" can fail under adaptive admission if stricter decay causes the scheduler to reject work earlier and improves compliance among admitted rounds. The spec should define metrics over offered workload versus admitted workload, and qualify these properties with the policy/workload conditions under which they must hold.

6. **Closed-loop workload feedback needs a stable definition of "demand" for sensitivity results**  
   Reference: lines 39-41 and 133-138.  
   Because failed rounds retry and demand responds to system state, policy changes can alter the workload presented to the system. That is realistic, but it can confound policy comparisons unless the trace records offered arrivals, retries, admissions, deferrals, drops, and completions as separate quantities. The spec should require those counters/views, and should say whether primary metrics are normalized by initial offered work, total attempts, admitted work, or completed logical rounds.

7. **V1 scope is broad relative to the stated "minimal observability + minimal sweep" goal**  
   Reference: lines 42 and 215-220.  
   V1 includes the DES core, seven packages, five model surfaces, four scheduler rungs, full traces, checkpointing, grid sweeps, negative controls, and four test tiers. That is coherent, but not very minimal. If this is the first implementation pass, consider splitting V1 into a smaller acceptance milestone: deterministic single-run engine plus trace schema plus one baseline and one freshness-aware policy, then add checkpoints/sweeps/intermediate rungs after the trace contract is proven.

8. **Switch fabric abstraction is deferred too far for a central contention claim**  
   Reference: lines 64-68 and 222-225.  
   The data flow depends on switch-path reservations, while V1 defers all topologies beyond a single contended any-to-any switch with capacity `C` and reconfiguration delay. That may be enough, but the spec should state exactly what conflicts in that abstraction: per-path capacity, global switch capacity, endpoint exclusivity, reconfiguration blocking, or some combination. Without that, scheduler conclusions about path allocation and pre-generation may be artifacts of an underspecified switch model.

## Suggested acceptance additions

- Add a short "Run identity and replay semantics" section covering run IDs, fork IDs, checkpoint provenance, event IDs, and trace hash scope.
- Add Protocol sketches with units for all five model surfaces.
- Add a "comparison metrics" section that distinguishes offered, admitted, attempted, completed, failed, retried, and dropped work.
- Add one explicit CRN design choice: counter-based RNG keyed by semantic draw IDs, or an explicit statement that paired runs only share streams until policy-induced divergence.
