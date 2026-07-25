# Literature surveillance protocol — question-indexed, invalidation-first

*Established 2026-07-25. Governs the recurring arXiv sweep and any ad-hoc
literature pass. Read this before adding a citation that came from a search
rather than from a read.*

## What this is designed against

The naive version of literature surveillance is a summary factory. It emits
digests of unread papers, the digests accumulate in notes, and the notes are
later requoted as fact. Every drift incident this project has recorded has
that exact shape:

- The RL-QEC claim entered the draft in the wrong tense from a partial read
  (front matter and mechanism sections only); the full read corrected it to
  "steered during repeated short executions with the state re-prepared every
  shot," reaching uninterrupted computation only in simulation.
- The HSD transfer note's own header line said reads consume future *write
  capacity*; the paper says reads consume future *readability* (addendum
  0d17539).
- On 2026-07-25 a popular summary of the ORNL/IBM molten-salt work described
  "multiple quantum nodes"; the primary (arXiv 2606.30402) uses one QPU,
  `ibm_boston`.

Automating summary production would industrialize this. The protocol below
therefore emits **debts, not conclusions**.

## The four rules

**1. Query by question, not by topic.** The seven questions in
`2026-07-09-physicist-question-list.md` are the queries. A result is a hit
only if it bears on a named question or on the novelty fence. Topic sweeps
over quant-ph return everything and settle nothing.

**2. Emit claims about our claims, never summaries of theirs.** The unit of
output is a queue entry naming the question touched, the primary identifier,
and one line on what it would change *for us* if true. Never a digest of the
paper's contents. A digest is a corpse waiting to be requoted.

**3. Nothing enters the draft from a sweep.** A sweep produces reading debt.
Only a first-hand read of the primary discharges an entry, and the discharge
is recorded as a dated, stamped event — not an edit. This is the standing
rule (`corrections carry the correction, not the corpse`) applied upstream.

**4. Hunt invalidation, not support.** The seven questions are addressed to
physicists. A published answer to one is not a citation to add; it deletes or
ratifies one of our objects. Finding that before submission is strictly better
than after. Supporting citations are a by-product; contradiction is the
product.

## Query set

Run each against arXiv (quant-ph primarily; cs.NI, cs.OS, physics.optics
secondary). Listings and the arXiv API are openly fetchable; corporate blogs
are not — treat vendor posts as pointers to be resolved to a preprint.

| Q | What would count as a hit |
|---|---|
| Q1 | Photonic/optical switch reconfiguration latency **distributions** (not means); tail behavior, multimodality, or state dependence of switching time; replenishment cadence variance in networked quantum testbeds |
| Q2 | Cross-sectional fidelity spread across **simultaneously available** links at one instant; path-conditioned fidelity estimates with published uncertainty and age; calibration-published vs true fidelity |
| Q3 | Repeated QND / nondemolition readout of a stored qubit; per-readout fidelity cost; whether degradation is graded or cliff-shaped; state dependence of the damage law |
| Q4 | Cost of a **failed** heralding attempt: port/slot blocking, resource destruction, failure-to-next-attempt cycle time; retain-and-retry vs release-and-reacquire on a configured path |
| Q5 | Simultaneous entangling links per memory module; switch radix; reconfiguration granularity (per-port / per-bank / global) in multiplexed network nodes |
| Q6 | Whether switch actuation is rationed: duty cycle, power, thermal transients, component wear, fabric occupancy, controller traffic, cross-path contention, calibration disturbance |
| Q7 | Persistence of comparative link quality: rank-inversion rate or autocorrelation time of path quality at OS-actionable lead times; calibration drift timescales |
| Fence | Distributed quantum OS / entanglement-aware scheduling / quantum network resource management occupying the **full form** (perishable good + custody + admission), not a component of it |

## Known false-positive: the entanglement vocabulary trap

"Entanglement" in quantum-chemistry papers frequently denotes a Schmidt
decomposition inside a classical embedding — e.g. the DMET *entanglement
bath* of arXiv 2606.30402 — not a networked resource. Any keyword sweep will
false-positive on these. A hit must involve entanglement that must **survive a
scheduling decision**; if the quantum state is measured out before any
scheduling occurs, the work is at most a foil (see the molten-salt entry in
the reading queue), never prior art.

## Output contract

Append entries to `docs/surveillance/reading-queue.md`. Never modify the
draft, the question list, or any transfer note from a sweep. If a sweep
believes a question has been answered, that belief goes in the queue with
status `UNREAD` and a `would change:` line — it does not go in the paper.
