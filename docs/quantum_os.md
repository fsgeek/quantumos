# A Constraint-First Quantum OS for Photonic's Entanglement First™ Architecture

## Overview

The right quantum OS for Photonic is not best understood as a cloud scheduler for noisy quantum jobs, but as a distributed real-time runtime whose core task is to manage entanglement, memory, decoding, and switch fabric resources under coherence and fidelity constraints.[cite:101][cite:13][cite:140] The decisive systems fact is that congestion in the entanglement fabric is not merely a throughput problem: because entanglement is probabilistically generated and perishable, queueing and contention can directly degrade quantum state quality and raise logical error rates.[cite:47][cite:48]

That observation is the architectural hinge. A Photonic-scale OS must treat entanglement leases, syndrome rounds, decoder capacity, and calibration state as first-class schedulable resources, rather than assuming that networking, compilation, and control can be layered independently.[cite:101][cite:140][cite:130]

## Constraints from the physics

### Perishable, probabilistic entanglement

Photonic's Entanglement First™ architecture connects silicon T-centre modules in cryostats through telecom optical I/O and a room-temperature photonic switching fabric.[cite:101][cite:13] Distributed entanglement is created by synchronized optical emission and heralded detection, which means each attempt succeeds with some probability less than 1, and successful states must be consumed before decoherence erodes their value.[cite:13][cite:129]

This creates a resource model unlike any classical OS abstraction. Classical packets can usually wait in queues with bounded performance penalties, but entangled states degrade while waiting, so network congestion couples directly to correctness rather than merely to latency or throughput.[cite:47][cite:48] That coupling is what makes a quantum OS for Photonic fundamentally different from an RTOS with a quantum-themed API.

### Distributed, low-shot QLDPC execution

Photonic positions SHYPS as a QLDPC family that exploits non-local connectivity, can encode multiple logical qubits in a single code block, and can reduce physical-qubit overhead by up to 20× relative to conventional approaches.[cite:138][cite:132][cite:139] Photonic's materials on SHYPS and its "Computing Efficiently in QLDPC Codes" work further frame the code family as one that enables efficient quantum logic and error correction using non-local connectivity rather than local surface-code geometry.[cite:140][cite:139]

For operating-system purposes, the important point is not just lower overhead but execution structure. If logical operations depend on distributed parity checks or low-shot syndrome extraction spanning multiple modules, then each syndrome round becomes a real-time task whose deadline is jointly determined by link success, switch contention, decoder service time, and the coherence budget of the qubits carrying state.[cite:140][cite:47]

### Messenger versus memory qubits

The public T-centre silicon photonics result demonstrates a three-qubit register consisting of an electron spin plus hydrogen and silicon nuclear spins.[cite:129] The reported spin-echo coherence times are about 0.41 ms for the electron spin, 112 ms for the hydrogen nuclear spin, and 67 ms for the silicon nuclear spin; the work also reports nuclear-spin entanglement within the register.[cite:129]

These numbers should not be collapsed into a single "device coherence time." The electron spin is best interpreted as the fast communication or messenger qubit because it couples to telecom-band photons, while the nuclear spins are the longer-lived memories that can hold logical information across more extended control intervals.[cite:2][cite:129] As a result, the OS must be qubit-role aware: fast-path deadlines are constrained by the electron channel, but global scheduling and decoder pipelines can exploit the much longer nuclear-memory windows, subject to how frequently the protocol re-entangles or interrogates those memories.[cite:129][cite:140]

## Architecture forced by those constraints

### Real-time resources

A minimum sufficient OS abstraction for Photonic should expose at least five real-time resource classes:

| Resource | Why it must be first-class |
|---|---|
| Entanglement lease | A Bell pair or pending Bell-pair request has endpoints, freshness, fidelity, and retry semantics; it is not interchangeable with a static link.[cite:47][cite:48] |
| Syndrome round | Distributed measurement and correction is a deadline-bearing unit of work, not a background event.[cite:140] |
| Decoder job | Classical decoding capacity is limited and can become part of the critical path.[cite:47] |
| Switch-path reservation | The room-temperature optical fabric is a contended shared resource that shapes which remote operations are even possible at a given instant.[cite:101][cite:13] |
| Calibration epoch | Schedulers need current information about drift, loss, detector quality, and path fidelity to avoid making stale decisions.[cite:101][cite:140] |

A classical OS might treat these as metadata or push them upward into middleware. In Photonic's stack they belong in the runtime contract itself, because correctness depends on them.[cite:47][cite:48]

### Fast path, runtime, and supervisory control

The most defensible architecture is layered rather than monolithic. The nanosecond-to-microsecond fast path belongs near the hardware, on FPGA or RFSoC-style controllers handling pulse timing, heralding, detector windows, and local feed-forward.[cite:25][cite:30] Photonic's own architecture places QPUs in a 1 K cryostat and routes optical I/O to a room-temperature switch network, which strongly suggests a split control plane between local device timing and wider distributed orchestration.[cite:101]

Above that sits the real-time runtime: the layer responsible for entanglement-lease allocation, syndrome-round scheduling, decoder dispatch, admission control, and switch-path reservation.[cite:47][cite:81] Above that again sits a slower supervisory plane that handles placement, calibration publication, congestion policy, and recovery actions, while compile-time tooling maps logical circuits into SHYPS-aware distributed execution plans.[cite:140][cite:139] The term "quantum OS" is most usefully reserved for the contract coordinating these layers, rather than for any single executable component.[cite:130][cite:52]

### Why QOS and QNodeOS are comparators, not templates

QOS, the TUM OSDI paper, is best understood as a quantum cloud resource manager for IBM-hosted NISQ systems, optimizing fidelity, utilization, and waiting time across heterogeneous backends.[cite:16][cite:20] That is a legitimate and useful operating-systems contribution, but it does not attempt to solve the Photonic problem of managing live entanglement generation, distributed low-shot QLDPC execution, and real-time correctness under perishable-state constraints.[cite:16][cite:20][cite:47]

QNodeOS is a closer precedent because it is explicitly an operating system for quantum network nodes and introduces ideas such as CNPU/QNPU separation, network processes, and a quantum memory manager.[cite:52][cite:130] But QNodeOS targets small quantum-network nodes and programmability across network hardware classes, whereas Photonic's challenge is to push those ideas into a much tighter, fault-tolerant, silicon-integrated distributed runtime where the scheduler must reason directly about coherence classes, switch contention, and code-level correctness envelopes.[cite:130][cite:101][cite:140]

## OS object model

### QubitHandle

A `QubitHandle` names a physical, virtual, or logical qubit and carries at least its location, role class, calibration epoch, and coherence class.[cite:129][cite:101] The essential distinction is between messenger qubits, which couple to photons and have tighter fast-path budgets, and memory qubits, which hold longer-lived state across distributed coordination intervals.[cite:2][cite:129]

### EntanglementLease

An `EntanglementLease` represents either a pending request for remote entanglement or a successfully heralded entangled state. It should minimally contain endpoint identities, creation time, expiry or freshness bound, fidelity estimate, path identity, heralding metadata, and retry policy.[cite:47][cite:48] This object is the heart of the runtime, because it captures the fact that remote quantum connectivity is both stochastic and time-sensitive.

### SyndromeRound

A `SyndromeRound` groups the distributed measurements, associated entanglement leases, participating qubits, and completion deadline for one error-detection or logical-operation phase.[cite:140] Treating syndrome handling as an explicit object lets the scheduler reason about end-to-end correctness instead of separately scheduling links, pulses, and decoder tasks with no common deadline.[cite:47]

### DecoderJob

A `DecoderJob` models classical decoding as a schedulable resource with service time, priority, and backlog semantics.[cite:47] This matters because a Photonic-scale machine could become decoder-bound even when physical hardware remains available, and because delayed decoder results can consume freshness margin on entangled states or force additional rounds.[cite:47][cite:140]

### SwitchPathReservation

A `SwitchPathReservation` models occupancy and contention on the room-temperature photonic switch fabric that Photonic uses for any-to-any connectivity.[cite:101][cite:13] Remote operations that appear adjacent at the circuit level may still conflict at the optical-fabric level, so switch usage cannot be treated as an implementation detail hidden below the scheduler.[cite:13][cite:48]

### CalibrationEpoch

A `CalibrationEpoch` versions the live hardware model used by compiler and runtime. It should cover at least detector performance, optical loss, path stability, qubit drift, and fidelity estimates relevant to lease and decoder scheduling.[cite:101][cite:140] Without such a mechanism, the runtime risks making correct decisions against an outdated model of the device.

### PauliFrameToken

A `PauliFrameToken` represents deferred correction state tracked classically rather than immediately emitted as a physical pulse. This is useful because some corrections can be absorbed into the logical frame, reducing pressure on the fast path and shortening physical critical sections.[cite:140] Including this object in the OS model sharpens the boundary between hard real-time control and logically equivalent deferred action.

## Revised hypothesis and falsification

The strongest falsifiable claim is not that a batch scheduler like QOS performs poorly on real-time work, because that is already implicit in its problem statement.[cite:16][cite:20] The real claim is that even a naive real-time scheduler fails once it treats entanglement as an on-demand resource rather than as a perishable one.[cite:47][cite:48]

A stronger working hypothesis is therefore: a Photonic-scale quantum OS must model entanglement leases, syndrome rounds, decoder capacity, switch paths, and calibration state as schedulable real-time resources, and its correctness should be judged by whether it maintains deadline compliance, bounded decoder backlog, entanglement freshness, and logical-error targets under stochastic link generation and switch contention.[cite:47][cite:48][cite:140]

This hypothesis can be tested by comparing two schedulers. Scheduler S0 provides best-effort real-time scheduling without explicit freshness or admission control for entanglement; Scheduler S1 models lease expiry, pre-generation, admission control, and decoder pressure.[cite:47][cite:75] The key experiment is to increase distributed workload until S0 enters a regime where queued but aging entanglement pushes logical error above threshold, then test whether S1 extends the feasible region by trading throughput for freshness and correctness.[cite:47][cite:48][cite:75]

## Implications

The result of this reframing is that the phrase "quantum OS" becomes more precise. For Photonic, it should mean the distributed runtime contract that turns a silicon T-centre, 1 K cryostat, telecom-fibre, photonic-switch, SHYPS-based machine into a schedulable computer.[cite:101][cite:13][cite:140] The key design problem is not simply low latency, nor simply distributed control, but preserving correctness in the presence of perishable entanglement and distributed code execution.[cite:47][cite:48]

Under that framing, prior systems fall into place. QOS remains relevant prior art for cloud-level quantum resource management, and QNodeOS remains the closest OS-like precedent for quantum networking.[cite:16][cite:20][cite:52] But the Photonic problem is narrower and harder: derive a runtime whose abstractions are forced by the physics of messenger-versus-memory qubits, the stochasticity of heralded entanglement, and the real-time demands of distributed QLDPC execution.[cite:129][cite:140][cite:101]
