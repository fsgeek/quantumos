# Reading note: Chertov 2008 — method transfer to the QuantumOS program

**Date:** 2026-07-09
**Source:** Roman Chertov, *A Device Independent Router Model: From Measurements
to Simulations* (PhD dissertation, Purdue, 2008; advisors Fahmy/Shroff).
Full text: `../research-program/references/A_device_independent_router_mo.txt` (+ PDF).
**Occasion:** read in-session 2026-07-09, ahead of Tony's conversation with the
author. Ruling from that session: **this changes the program, not the
experiment** — no prereg amendment, no plan change. Everything below is
downstream of the battery.

## The method, in one paragraph

Refuse to model device internals (infeasible: device diversity, software
variance, per-device validation burden, simulator scalability). Fix a minimal
device-independent structure — multi-queue/multi-server, round-robin service,
serialized per-port TX — with five parameters: **M** (effective service
parallelism ≈ contention), **Q** (aggregate queue slots per output port),
**DelayTbl** (packet size → intra-device delay), **QueueReq** (size → slots
occupied), **ServReq** (size → servers required). Infer all five by an
autonomous black-box probing protocol (CBR flows, ~hours), the *same procedure
for every device*. Validated on Cisco 3660/7206VXR/12410 + Juniper M7i in ns-2
with no overhead over the default queue model. Two empirical findings that
matter to us: (a) **QueueReq was forced by data** — fixed-size slots failed;
his four routers used three different queue-sizing strategies (packet-, slot-,
byte-based); (b) **shared-fabric (backplane) contention must be modeled** —
flows that share no output still interfere; finite M is the minimal
representation.

His design criteria (a spec, quoted near-verbatim): (1) accurate, but allowed
to miss special cases for the sake of scalability; (2) not computationally
expensive; (3) parameter inference process identical regardless of device;
(4) parameters inferred with no knowledge of device internals; (5) reflects
behavior under changing workloads.

## Where the analogy breaks (the quantum deltas)

1. **The queued item is inert in his model** — nothing happens to a packet
   while it waits; that inertness is what licenses collapsing all internal
   buffers into one aggregate Q. Our pooled lease decays during residency.
   The thing his abstraction may omit is exactly our unnamed perishable-good
   abstraction (see `2026-07-05-perishable-good-lifecycle-parked.md`).
2. **His probes are free** — the profiler blasts CBR traffic for hours,
   consequence-free. Quantum profiling pays a wear/measurement tax (the QND
   read-wear finding): black-box inference itself consumes the resource.
3. **His servers never fail-and-consume-the-work** — heralding is
   probabilistic service with a loss on failure.

qsim's knob surface ≈ Chertov's five + {decay rate per class, heralding p per
path, wear per readout}. Independent convergence on the same minimal-surface
shape.

## Capture, by point of future use

### 1. Battery write-up (first consumer — after the runs)
The battery's customer is the **second simulator's parameter surface**. Read
verdicts as surface-admission decisions: FIELD-EARNED → in the surface;
DECISION-EARNED / REPRESENTATION-CHEAP → derived from the surface (his
DelayTbl move: compute, don't represent); FIELD-BLOCKED → omitted at this
operating point. The stamped gate cascade IS a parameter-surface admission
protocol with a published precedent.
Add to the ayni payload at write-up time (questions are not predictions; no
pre-run stamp needed): the **inferability question class** — for each
candidate parameter, not "what are the internals" but "what black-box probing
protocol, at what probe budget (wear tax), could infer it?"

### 2. Second simulator (paper-data tool; separate future work)
Design from Chertov's five criteria + a standard inference protocol, extended
across the three quantum deltas above. Do not design from scratch. The
device-independence criterion (3)+(4) is what makes the model an OS-usable
abstraction: the OS can't know internals either.

### 3. Position paper
- **Port-topology section** gains independent support: his
  backplane-contention finding (model shared-fabric interference or the model
  is wrong under load) is the router version of what qsim demanded three ways.
- **Candidate new section:** "the scheduler's model of the device must be
  inferable by the OS itself" — calibration-as-profiling, as a recurring OS
  service with a wear budget, not a one-shot bench procedure.
- His Chapter 2 (same experiment, drastically different results across
  simulators/testbeds, divergence appearing only under overload) is citable
  license for the qsim/second-simulator split.

### 4. Naming session (deferred to a fresh instance — this is a TEST, not a name)
Any candidate name for the perishable-good abstraction must make it obvious
why Chertov's aggregate-queue collapse works for packets and fails for leases:
the name carries "what happens to the item while it waits, and where it
waits." Negative image only; no candidate names were generated (deferral
honored).

### 5. T4 design (when B2 unblocks on Q7/Q8)
Drift = **the parameter table has a freshness bound**. The profiler is a
recurring service; parameter inference under drift is T4's shape. The model's
own parameters are themselves a perishable good — the abstraction one level up.

## Author-conversation questions (2026-07-09, for the record)
1. Which parameters did he expect vs. discover? (QueueReq looks
   instrument-forced.)
2. How does black-box inference restructure under a probe budget — when
   profiling traffic degrades the device?
3. Did parameter tables drift across profiling sessions; do they have a
   freshness bound?
4. Where did the aggregate-queue abstraction break — the failure boundary of
   device-independence?
5. Round-robin fabric scheduling was assumed (future work flagged): did
   scheduling policy ever dominate the results?
