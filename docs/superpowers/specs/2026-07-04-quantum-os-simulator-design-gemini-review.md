# Review and Feedback: Quantum OS Simulator Design Spec

**Reviewer:** Antigravity (AI Coding Assistant)  
**Date:** 2026-07-04  
**Target Document:** [2026-07-04-quantum-os-simulator-design.md](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md)

---

## Executive Summary

The revised design is solid, addressing previous feedback regarding reproducibility (common random numbers), instrumentation boundaries, metrics, and simulator lifecycle. However, several critical technical issues, semantic ambiguities, and mathematical assumptions should be addressed before moving into implementation.

---

## 1. Technical & Implementation Risks

### 1.1 Non-Deterministic Hashing in Python (`hash()` warning)
* **Reference:** Section 10 ([Randomness and the common-random-numbers contract](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L206-L228))
* **Issue:** The spec states that key-addressed randomness is seeded from `hash(run_seed, stream, key)`. By default in Python (3.3+), the built-in `hash()` function is salted with a random value per-process. This means hash values for identical inputs will change between runs/processes, breaking determinism and paired-policy comparisons across sweeps or forks.
* **Recommendation:** Do not use Python's built-in `hash()`. Specify a deterministic hashing function (such as `hashlib.sha256` or `hashlib.md5`, or a fast non-cryptographic hash like MurmurHash3) to derive the seed from the key tuple or string.

### 1.2 Initial Heralded Fidelity Definition
* **Reference:** Section 6 ([Model surfaces](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L99-L145))
* **Issue:** The `DecayModel` defines fidelity decay as `fidelity(t) = fidelity_at_herald * retention(t - t_herald, class, epoch)`. However, the `HeraldingModel` only returns a success probability; it does not return the initial fidelity of the heralded pair (`fidelity_at_herald`).
* **Recommendation:** Define how `fidelity_at_herald` is determined. Should the `HeraldingModel` return a tuple of `(success_probability, initial_fidelity)` or is there a separate model/calibration property for the initial heralded fidelity of a path?

---

## 2. Structural & Model Ambiguities

### 2.1 Lack of Port Representation in the Entity Model
* **Reference:** Section 5 ([Entity model](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L78-L97)) & Section 7 ([Switch fabric](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L166-L183))
* **Issue:** Section 7 introduces "endpoint port exclusivity" (each module optical port carries at most one active path) as the primary switch conflict. However, Section 5 does not list a `Port` entity, nor does `QubitHandle` define its port mapping.
* **Recommendation:** Add a representation of module optical ports to the entity model (either as dedicated entities or explicit properties on `QubitHandle` locations) to avoid ad-hoc coupling during engine implementation.

### 2.2 Switch Path Reservation Release Timing
* **Reference:** Section 7 ([Switch fabric](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L166-L183))
* **Issue:** It is unclear when switch paths are released. Are they released immediately once a heralding attempt succeeds (since the heralded state is transferred to memory, freeing the optical path), or are they held until the lease is consumed or expired? Holding them until consumption drastically restricts system concurrency and should be parameterized.
* **Recommendation:** Explicitly specify the lifecycle of a `SwitchPathReservation` relative to heralding success and lease consumption/expiration.

### 2.3 Memory Qubit Passive Decay
* **Reference:** Section 5 ([Entity model](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L78-L97)) & Section 6 ([MemoryAccessModel](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L119-L124))
* **Issue:** Memory qubits are physical resources that decay over time. However, the entity model tracks them as inert `QubitHandle`s, and the `MemoryAccessModel` charges a cost only at the instant of access. If memory qubits hold state across multiple rounds, their passive decay is unmodeled.
* **Recommendation:** Clarify if memory qubits decay passively between accesses, and if so, how their last-access time or current fidelity state is tracked.

### 2.4 Resource Cleanup on Round Cancellation
* **Reference:** Section 4 ([Architecture - Data Flow](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L69-L77)) & Section 5 ([Entity model](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L78-L97))
* **Issue:** When a `SyndromeRound` fails (e.g., due to a lease expiring or heralding deadline miss), what happens to other active leases in that round? If not cancelled and cleaned up immediately, ports and global path capacity could leak, poisoning subsequent runs.
* **Recommendation:** Explicitly define the resource cancellation and cleanup sequence for aborted/failed rounds.

---

## 3. Validation & Testing Logic

### 3.1 Flawed Metamorphic Relation: Heralding Success vs. Expirations
* **Reference:** Section 16 ([Testing strategy](file:///home/tony/projects/quantumos/docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md#L324-L344))
* **Issue:** The spec states: *"raising heralding success must not increase lease-expiry counts"*. Under high congestion (e.g., decoder backlog), raising heralding success increases the rate at which leases are successfully heralded. These leases will then wait longer in memory for their rounds to execute, potentially leading to *more* lease expirations rather than fewer.
* **Recommendation:** Replace this check with a monotonic relation that holds under congestion, e.g., *"raising heralding success must not decrease the overall count of successfully completed rounds"* or *"must not increase the mean heralding duration per attempt"*.
