# Reading queue — literature surveillance debts

*Governed by `docs/superpowers/specs/2026-07-25-literature-surveillance-protocol.md`.
Sweeps append `UNREAD` entries. Only a first-hand read of the primary
discharges one. Nothing here is citable until discharged.*

## Entry schema

```
### <arXiv id or DOI> — <title>
- **status:** UNREAD | READ (yyyy-mm-dd, by <thread>) | DISCARDED (reason)
- **touches:** Q1..Q7 | fence
- **would change:** one line — what happens to OUR claim if this is true
- **disposition:** (only after READ) what it actually did
```

`would change:` is written by the sweep and is a *hypothesis about us*, not a
report about the paper. It is expected to be wrong sometimes; that is why the
entry is a debt and not a finding.

---

## Discharged

### arXiv 2606.30402 — Quantum Computations on Fusion Blanket Molten Salts
- **status:** READ 2026-07-25 (primary read in full; PDF + text in `docs/references/`)
- **touches:** fence
- **would change:** if this were multi-node entanglement-networked computation
  under a classical orchestrator, it would occupy part of the form the
  literature matrix (1ef0c38) fenced as unoccupied.
- **disposition:** Not prior art — it is the **demarcation foil**. One QPU
  (`ibm_boston`, Heron r3), not multiple nodes; EWF/DMET fragmentation with
  ext-SQD; the paper's own framing is that "the quantum device thus acts as a
  configuration generator, while classical post-processing recovers the
  fragment ground-state energy and reduced density matrices." Bitstrings cross
  the boundary, never quantum state. Cold chain of length one: measurement
  precedes every scheduling decision, which is exactly why no OS machinery is
  needed. Secondary find: Figure 2 contains a **static, structural placement
  policy** — fragments with ≥13 spatial orbitals dispatch to the QPU, shot
  budget 10⁵ below 20 orbitals and 10⁶ at or above. Routed to §8 as the first
  rung of the keying-basis argument (problem structure → resource history →
  perishable-good state). Fence conclusion undisturbed.

### arXiv 2608.24152 — A Dynamic-Kernel/QPacket Executable for Quantum Repeater Chains in Q2NS/ns-3
*Pearson, Caleffi, Cacciapuoti. Submitted 2026-08-25; revised (v2) 2026-08-26.*
- **status:** READ 2026-09-18 (primary read in full by this thread; PDF + text in `docs/references/`)
- **touches:** fence, Q6 — and *possibly* Q1, Q5
- **would change:** The fence excludes work unless it occupies the full form
  (perishable good + custody + admission), not a component. This paper builds
  a "Dynamic Kernel" — literally named as a kernel — organized as a
  Planner-Executor-Engine pipeline processing "QPacket" meta-headers carrying
  service intent and append-only action-commit stamps, managing entanglement
  as "a non-local, non-copyable, stateful network resource," including
  pre-distributed entanglement and forwarding/delegation across nodes with
  uneven generation support. If the full paper's kernel adjudicates admission
  among competing service requests over a held, decaying entanglement
  resource — not just the single scoped linear-chain demonstration the
  abstract describes — this would be the closest occupant of the fence's full
  form seen in this project's surveillance to date, and the fence's
  "unoccupied" conclusion would need re-examining. As abstracted ("deliberately
  scoped to an analytically verifiable service and policy" on a "linear
  quantum repeater chain"), it reads as a protocol-architecture demonstration
  rather than a full multi-request scheduler — that narrowness is exactly what
  the full read must check. For Q6: the abstract explicitly reports measuring
  "signaling load, forwarding behavior, and QPacket meta-header growth" as a
  function of policy choices and available network resources — controller/
  signaling traffic is one of the constrained-resource classes Q6 names
  directly. If the full paper shows signaling/controller load scaling with
  reconfiguration or actuation decisions rather than only header encoding, it
  could give Q6 a first real number for that resource class.
- **mapping note:** *possibly* Q1 — the link-preparation policy accounting for
  pre-distributed entanglement is adjacent to replenishment cadence, but no
  cadence distribution is claimed, so this is inference. *Possibly* Q5 — the
  linear-chain topology is a specific, non-switched topology and does not
  address port-level multiplexing or reconfiguration granularity; also
  inference. Whoever pays this debt should check the fence and Q6 first.
- **disposition:** **Not the fence, and not Q6.** The executable is a
  single-request, noiseless, linear-chain protocol demonstration. One QPacket
  is injected at Alice (Algorithm 1, line 2); there is never a second request,
  so nothing is admitted, deferred, or arbitrated. The physical model is
  "noiseless operations" (Table 1) and Kernel/MP execution is instantaneous;
  the authors defer decay to future work in so many words ("particularly
  important in noisy scenarios where the quality of distributed entanglement
  decreases over time"). The entanglement inventory (FTQ) is a presence set —
  a node either holds an adjacent ebit half or it does not — with no age, no
  fidelity, no exposure. So of the fence's three parts (perishable good,
  custody, admission) the paper has none: it is the **inverse demarcation foil**
  to the molten-salt entry — full control-plane machinery over a good that
  never spoils, where molten-salt had a good that spoils and no control plane.
  For Q6, the "signaling load" is a count of classical UDP messages per
  request as a function of pre-distribution probability and generator
  placement (Fig. 4, N=100, ~50–300 messages); there is no switch, no
  actuation, no rationed resource — it measures how far a request progresses
  before failing, not whether anything is budgeted. Q1/Q5: nothing (no
  replenishment cadence; no switch; linear chain only). **What it does give
  us, unlooked-for:** (i) the append-only stamp history is a *rhyme* for the
  custody record — provenance carried in-band with the good, single-writer,
  certified at commit boundaries — but it records actions, not exposure, and
  carries no clock; (ii) it prices that record: stamps grow linearly with hops
  and the accumulated forwarding cost quadratically (Sec. 3.3, fit degree
  1.99), because the ledger rides the quantum channel. That is a citable
  "custody records have a carrying cost" datum for the HotOS cost axis,
  cited as a repeater-chain simulation result under their abstract encoding
  model, never as a hardware number. Fence stands.

### arXiv 2609.04920 — QUASAR: Quantum Satellite Architecture and Routing Simulator
*Shi, Wang, Yuan, Wu, Zhao. Submitted 2026-09-04.*
- **status:** READ 2026-09-18 (primary read in full by this thread; PDF + text in `docs/references/`)
- **touches:** fence — and *possibly* Q5
- **would change:** The fence excludes work unless it occupies the full form
  of perishable good + custody + admission, not a component of it. This
  paper's abstract states the simulator "integrates dynamic orbital
  topologies, time-varying optical transmittance, and quantum memory
  decoherence into network-layer attributes," evaluates "concurrent
  requests," and introduces an "Entanglement Distribution Rate (EDR)-Aware
  Spatiotemporal Routing (EASR) heuristic" — decoherence (perishable good)
  and routing under concurrency (admission-shaped) are both explicit claims
  in the same system. If the full paper's EASR heuristic actually arbitrates
  competing requests for memory/downlink resources against a decoherence
  clock — custody, not just point-to-point link scheduling — this would be
  another candidate (alongside PR #4's arXiv 2608.24152) that plausibly
  occupies the fence's full form rather than a component of it, and the
  position paper's novelty claim would need to be checked against it
  directly. Whether the
  abstract's "concurrent requests" language rises to genuine custody
  (queued, competing holds) or is just parallel independent routing runs is
  inference, not stated outright — that is the specific thing the full read
  must settle. *Possibly* Q5: "dynamic orbital topologies" is a
  reconfiguring topology envelope, but it reconfigures by satellite motion
  (visibility windows), a different physical mechanism from the photonic
  switch fabric Q5 asks about, so this mapping is thin and should be
  checked, not assumed, on the full read.
- **mapping note:** this is a simulation-platform paper, not a hardware
  characterization — it cannot answer any of Q1-Q7's hardware thresholds
  (those ask for measured distributions), so fence is the only question
  mapped. Whoever pays this debt should first determine whether EASR models
  contention for a held resource or only routes already-available links.
- **disposition:** **Not the fence; ratifies the provocation.** EASR is
  Dijkstra over time-varying edge weights (Algorithm 1; Listing 1.3 is
  literally `graph.dijkstra(src, dst, weight_fn=easr_cost)`). The perishable
  good is represented as one scalar, F(Δτ) = 1/4 + (F0 − 1/4)·exp(−Δτ/τc)
  (eq. 4), against one clock (τc), and that clock is *summed into the route
  cost* as −ln η − ln ζ + Δτ/τc (eq. 6); a fidelity floor F* acts as a hard
  prune on path search. There is no application deadline anywhere — F* is a
  physics threshold, not an appointment — so the second date does not exist
  to be co-enforced. "Concurrent requests" means independent origin-
  destination routing runs whose EDR is summed (Fig. 5b), and the authors say
  so: "not intended as a standalone algorithmic benchmark or a full
  resource-contention scheduling model" (Sec. 6.4). No held resource is
  contended, no custody, no admission. Q5: orbital visibility windows
  reconfigure the contact graph by satellite motion, not by a switch; nothing
  about radix, per-port granularity, or simultaneous links per memory —
  mapping withdrawn. **Value to us:** this is a clean 2026 instance of the
  exact representation the HotOS paper argues against — decay as a scalar
  folded into a path weight, one clock, no custody — from a routing-layer
  simulator that positions itself between NetSquid/SeQUeNCe and optimization
  studies. Citable (as a simulator design choice, not a claim about hardware)
  in the "this is the current model" sentence the provocation needs. Fence
  stands.

### arXiv 2608.04093 — An optical-fibre-integrated buffer for packet-switched quantum networks
*Spegel-Lexne, Argillander, Clason, Claesson, Hey Tow, Lima, Pereira, Xavier. Submitted 2026-08-04.*
- **status:** READ 2026-09-18 (primary read in full by this thread; PDF + text in `docs/references/`)
- **touches:** fence — and *possibly* Q1
- **would change:** The fence excludes work unless it occupies the full form
  of perishable good + custody + admission, not a component of it. This
  paper demonstrates a fibre-integrated recirculating-loop buffer that holds
  a polarisation-encoded qubit payload in custody for storage times up to
  47 μs, with a measured cost of that custody (1.8% average QBER) and
  releases the payload on a routing decision read from an attached packet
  header — a physical custody primitive gated by a header-triggered
  admission signal, at packet granularity. As described, it holds and
  releases a single payload rather than arbitrating among competing holds,
  so this looks like a component (custody + a trigger), not an occupant of
  the fence's full form; but if the full paper's header logic turns out to
  arbitrate between multiple buffered payloads under contention, that would
  push it toward occupying more of the form and the fence would need
  re-examining — that check is the reason this entry exists. *Possibly* Q1:
  the "ultra-low-loss poled fibre phase modulator" is described only as
  providing "fast, polarisation-insensitive switching," with no latency
  distribution reported, so a Q1 reading is inference, not a claim.
- **disposition:** **Not the fence; Q1 mapping withdrawn; one unlooked-for
  datum for the type argument.** This is a device paper: a recirculating
  fibre loop (Sagnac switch + 100 m storage line + FBG mirror) driven by a
  poled-fibre phase modulator, storing a 16-pulse weak-coherent-state
  polarisation payload and retrieving it after a header-selected number of
  ~6 µs cycles. The "central node decides the delay from the header" scenario
  (Fig. 1) is described, but the demonstration stores one packet at a time;
  no competing packets, no held-resource arbitration, no custody record — a
  component, not the form. For Q1: the modulator's rise/fall times are single
  measured values (22.4 ns / 26.4 ns, Fig. 2c), not a distribution, and the
  device is a store/retrieve gate, not a fabric reconfiguration; nothing on
  tails or state dependence. Q1 stays unanswered. **What it gives us:** a
  clean hardware instance of the "decay law differs by kind" axis. The loop
  buffer loses *presence*, not *quality*: per-cycle efficiency ≈ 56% (0.4 dB
  modulator + 0.3 + 0.5 + 0.1 + 1.2 dB connectors/splices), so survival is
  geometric in cycles (retrieval still seen after 10 cycles ≈ 60 µs), while
  QBER stays flat-ish at 1.06–2.74% out to 47 µs. A matter memory with the
  same retrieval fidelity decays the opposite way. Two offers of equal
  fidelity, different terminal cause (erasure vs. depolarisation) — exactly
  the claim the HotOS provocation makes, from a 2026 experiment, citable as
  such. Also a *calibration-pause* datum, unrated: over 12 h the buffer
  auto-recalibrates polarisation whenever QBER > 5%, taking "a few minutes"
  each time (Fig. 6, text); the trigger rate is not reported, so it is a
  Q7-shaped observation (drift forces maintenance downtime at the hours
  scale) without the number Q7 asks for. Not a Q6 actuation-budget datum — the
  pause is drift compensation, not switch rationing. Fence stands.

### arXiv 2608.22766 — Spatio-temporal Path Optimization for Stabilizer-Code-Protected Quantum Networks
*Zhang, Wang, Zhao, Chen, Guo. Submitted 2026-08-24; revised (v2) 2026-08-25.*
- **status:** READ 2026-09-18 (primary read in full by this thread; PDF + text in `docs/references/`)
- **touches:** fence
- **would change:** This paper jointly optimizes, for a logical qubit
  traversing multiple hops, the path, the QEC-recovery locations, and the
  protection scheme, under "logical-error and logical-lifetime constraints,"
  with a multi-flow variant reducing "throughput-normalized congestion"
  relative to greedy assignment. "Logical-lifetime constraints" is a
  perishability model (the encoded state has decaying validity); the choice
  of recovery location is a custody-like decision (where the state is held
  and reconstituted along the route); multi-flow congestion reduction implies
  resource contention resolved across competing flows — the three elements
  the fence names (perishable good + custody + admission). If the full
  paper's multi-flow algorithm is actually adjudicating admission among
  contending requests for a shared, decaying network resource, rather than
  optimizing a single flow's static route in isolation, it would occupy more
  of the fence's full form than anything read so far in this project's
  surveillance, and the fence's "unoccupied" conclusion would need
  re-examining. As abstracted, it is framed as a routing-algorithm
  contribution ("algorithmic building block for QEC-aware routing"), not as a
  scheduler or OS — that framing is exactly what the full read must check.
- **mapping note:** no fidelity-spread or path-persistence data is claimed
  (Q2, Q7 not mapped — the abstract reports routing-cost and congestion
  reductions, not fidelity measurements or temporal rank data), so this entry
  is filed under the fence alone rather than padded with inferential question
  mappings.
- **disposition:** **Not the fence — wrong paradigm, wrong tense.** The
  paper is QEC-protected *direct transmission* of encoded logical qubits and
  says outright that "entanglement distribution is not used as a
  network-level communication primitive in our model" (Sec. III-A). The
  perishable object is a code block in flight, and its "logical lifetime" is
  a per-scheme budget on inter-recovery propagation time (T_log = 50/100/200/
  600 µs for surface d=3/5/7/9, Table I) — a segment-time constraint in an
  offline path computation, not a decaying held good. The single-flow
  algorithm is a label-correcting search over an auxiliary graph (cost,
  discretised error, elapsed time; Pareto dominance); the multi-flow variant
  builds ≤M candidate strategies per flow and solves a min-max-congestion ILP
  over a *static* demand set. Nothing arrives at runtime, nothing is held,
  nothing is admitted or refused against other work — "algorithmic building
  block" is the paper's own description and it is accurate. Fence untouched.
  **What it gives us, unlooked-for, two things.** (i) Its central formal
  claim is that validity is "segment-dependent rather than channel-additive":
  a recovery resets the clock, so a path's feasibility cannot be a sum of
  fixed link weights, and the NP-hardness proof (App. C) locates the hardness
  in the *time budget* constraint, not in the error model. That is the
  physical-clock half of the two-dates argument, stated as a routing theorem
  in a neighbouring paradigm — citable as such, with the caveat that there is
  no second (institutional) date here: rθ is an error threshold, not an
  appointment. (ii) The "scheme profile" φσ = (cost, lifetime budget,
  error-map) is a *typed protection offer*, and letting the router choose the
  type per segment cuts cost 55–75% versus always-strongest at equal
  acceptance (Sec. VII-C, Fig. 2b/e). That is a "typed offers pay" result
  from a simulator, in a paradigm without entanglement — usable as a
  motivating neighbour for the HotOS provocation, never as evidence about our
  object model. Q2/Q7: nothing (no measured spreads or persistence; parameters
  are drawn from a 2 km-mean exponential and a 0.15 dB/km loss law).

### arXiv 2609.09805 — Electrically tunable, two-photon interference from remote silicon-vacancy centers in industrial silicon carbide
*Hrunski, Scheller, Hollendonner, Ullerich, Parthasarathy, Fu, Pointner, Knolle, Kaiser, Dasari, Nagy. Submitted 2026-09-09.*
- **status:** READ 2026-09-18 (primary read in full by this thread; PDF + text in `docs/references/`)
- **touches:** Q7 — and *possibly* Q2, Q6
- **would change:** Q7 asks how long comparative path/link quality stays
  valid at OS-actionable lead times. This paper reports a 26-day continuous
  measurement campaign on two-photon interference between remote SiV
  centers, with raw visibilities of 82% sustained over that period, and
  states that recalibrating the diode bias is needed "only every 8.4 hours"
  to maintain spectral overlap. If the full paper's 8.4-hour figure is the
  actual drift timescale forcing recalibration (not a conservative safety
  margin), it gives Q7 a first real number for calibration-drift
  persistence — long relative to plausible OS decision lead times, arguing
  against the "chasing a ghost" failure mode for this platform, the opposite
  direction from arXiv 2608.07163 already in this queue. *Possibly* Q2: the
  paper demonstrates spectral overlap of 19 randomly selected SiV centers in
  different diodes, a cross-sectional measurement across many emitters, but
  the abstract reports that overlap was achieved, not the magnitude of any
  residual spread — thin evidence for Q2's instantaneous-spread threshold.
  *Possibly* Q6: the 8.4-hour rebias cadence is a maintenance-actuation duty
  cycle on a quantum-network component, adjacent to Q6's constrained-resource
  ask but not a switch actuation.
- **mapping note:** whoever pays this debt should check Q7 first — the
  8.4-hour figure and the 26-day stability claim are the paper's strongest,
  most explicit data.
- **disposition:** **Q7: the 8.4 h figure is a measured mean interval
  between threshold crossings, not a safety margin — and it is
  emitter-specific. Q2 gets an unlooked-for cross-sectional datum. Q6
  thin.** Mechanism (SI7): every 2 h of *active* correlation time a resonant
  PLE scan measures each emitter's absolute A₂ frequency; if it lies outside
  a preset ±20 MHz window around ν_T the diode reverse bias is corrected
  (6.30 GHz/V). Uncorrected drift is "up to ±40 MHz/h". Across 244
  verification sessions in 628 h, correction was needed in 12.7% of sessions
  for one emitter (mean interval 19.4 h, longest 50 h) and 30.7% for the
  other (8.4 h, longest 32 h); the authors attribute the difference to the
  two cryostats' thermal/vibration environments. So for this platform the
  calibration-drift persistence relevant to Q7 is hours to tens of hours,
  set by the *environment of the node*, not the emitter class — same lesson
  as the Naples fibre paper (2609.11359): persistence is route/site-class
  specific. At OS-actionable lead times it is persistent. **Q2:** 19
  randomly selected centres all tune to a common ν_T, but their linewidths
  differ 2–4× (27–59 MHz resonant; 30 vs 127 MHz deconvolved under the
  off-resonant excitation actually used), and the paper computes that
  linewidth mismatch alone caps HOM visibility at 93% (σ = 0), with
  session-to-session spectral diffusion σ = 15.5 MHz taking it to the
  measured 82%. That is a cross-sectional spread across *simultaneously
  available, nominally equivalent* emitters in which frequency-matched
  offers differ materially in the quality they can deliver — the Q2 premise,
  from hardware, though for emitters rather than fabric paths. **Q6:** the
  fast cavity lock (every 10 s, error signal = transmitted counts) costs no
  downtime; the slow loop pauses accumulation for a PLE scan every 2 h
  active time, nodes stabilised consecutively while the other idles —
  a rationed calibration actuation, but no budget figure. Fence: not
  touched.

### arXiv 2608.07163 — Rate-Fidelity Control for Wide-Area Quantum Links
*Clayton, Nunn, Carmack, McKenzie, Richards, Wu, Bhattacharjee. Submitted 2026-08-07.*
- **status:** READ 2026-09-18 (primary read in full by this thread; PDF + text in `docs/references/`)
- **touches:** Q7 — and *possibly* Q6
- **would change:** Q7 asks how long "the best path" stays best at
  OS-actionable lead times. This paper reports a 24-hour trace-driven
  evaluation on a 64 km deployed fibre link where polarization drift
  "destabilizes end-to-end fidelity and forces periodic compensation," and a
  software controller that re-adapts pump power and polarization
  compensation to hold a 14% mean-rate improvement over static policy. If
  the full paper's drift autocorrelation time is short relative to our
  modeled scheduling lead times, it ratifies Q7's "chasing a ghost" failure
  mode for comparative routing; if long, a comparative read stays durable
  and Q7 resolves the other way. *Possibly* Q6: the abstract describes
  continuous actuation (pump power, polarization compensation) against
  "uncontrollable link drift," which could carry a duty-cycle or wear cost,
  but no such figure is stated — this is inference from "active
  stabilization with fixed control policies," not a claim.
- **mapping note:** this is a single link's fidelity drifting over time, not
  a cross-sectional spread across simultaneously available paths — it
  answers Q7's temporal-persistence framing, not Q2's instantaneous-spread
  framing, even though both quantities are "fidelity."
- **disposition:** **Q7 answered for the aerial route class — at seconds,
  the opposite pole from buried fibre — and Q6 gets a second measured datum,
  this one involving an actual switch. Fence not touched.** The link is 64 km,
  > 70% aerial (DC-QNet, LTS→UMD switch→NIST). A 48 h Stokes trace at 100 ms
  resolution shows drift rates "strongly correlated with time of day," up to
  ~0.06 rad/s by day; the empirical drift predictor rests on the observation
  that "polarization drift over a short period of time is strongly
  correlated with drift over a subsequent short period" — positive
  short-lag autocorrelation, i.e. predictable, not a ghost, but the
  actionable horizon is seconds: the best *static* fidelity-check interval
  is ~1 s by day and ~10 s at night (Sec. 6.2). So Q7 now has two measured
  poles: buried metro ≈ hours (2609.11359), aerial ≈ seconds (this). Both
  say comparative quality persists across ms-scale decisions; they differ by
  three orders of magnitude in how often the OS must pay to keep it so.
  **Q6:** compensation is in-band classical light, so "the path must be
  fully switched away from the entanglement source and detector while the
  APC is in use" (Fig. 1a, two-way switches at both ends) — a calibration
  actuation that consumes *fabric occupancy* and link downtime, measured: a
  fidelity check costs 44 ms, compensation is fixed at 1 s, and over 24 h
  ~9% of time goes to probes and compensation (3.4% at night). Cite as the
  second rationed-actuation class in the queue, and the first that occupies
  a switch. **On the provocation:** the paper's control abstraction is
  F(t) ≈ F_sd·F_pol with pump power as a knob — fidelity traded
  continuously against rate, pairs discarded when F < F_min, no second date
  — a clean 2026 instance of fidelity-as-scalar at the link layer; and its
  Sec. 7.3 proposes that each link expose "a feasible set of rate–fidelity
  operating points" upward — a per-link offer *frontier*, which is one step
  short of a typed offer (no carrier, decay law, cardinality or residue
  axes). Ratifies the framing the HotOS paper argues past; multi-link
  arbitration ("Opt-3") is explicitly future work, so no custody or
  admission. Q1/Q4/Q5: nothing.

### arXiv 2607.15262 — Dynamic Entanglement Distribution for Multi-User and Multi-Protocol Quantum Networking
*Wang, Clark, Alia, Bahrani, Aktas, Peranić, Stipčević, Lončarić, Rarity, Joshi, Simeonidou. Submitted 2026-07-16.*
- **status:** READ 2026-09-18 (primary read in full by this thread; PDF + text in `docs/references/`)
- **touches:** Q1, Q5, Q6 — and *possibly* Q7
- **would change:** A deployed, reconfigurable q-ROADM distributing entanglement
  to six users over metro fibre, supporting programmable full-mesh, partial-mesh
  and sliced configurations, with >150 h of continuous operation and an explicit
  comparison of full-mesh against time-shared partial-mesh under varying source
  and detector conditions. If reconfiguration timings are reported, Q1's
  spectral-line-vs-heavy-tail threshold may have a first real measurement, and
  Q6's "is actuation budgeted" may be answerable from 150 h of duty cycle. The
  mesh/slice granularity is directly Q5's reconfiguration-granularity ask
  (per-port / per-bank / global). Most consequential if true: this is a fabric
  whose reconfiguration is *programmable and in service*, which is the premise
  §6 argues must be first-class.
- **mapping note:** the sweep filed this under Q7 alone. The abstract does not
  claim rank-persistence or quality-autocorrelation data; "allocation according
  to link condition" implies varying link quality is acted on, but that is an
  inference, not a claim. Q7 retained as *possible*; Q1/Q5/Q6 added as the
  better-evidenced targets. Whoever pays this debt should check Q1 first.
- **disposition:** **Fence stands (memoryless; photons consumed in
  flight). Q1 unanswered. Q5 and Q6 get real but memoryless data; Q7 weak.**
  The q-ROADM is a 30-slice 100 GHz DEMUX → per-channel fibre polarisation
  controllers → a 192×192 Polatis optical fibre switch → 1×16 MUXs (Alice,
  Bob) and 4×16 WaveShaper WSSs (C/D, F/G). **Q1:** no reconfiguration
  timing of any kind is reported; configurations are compared over
  20–40 min windows. Unanswered. **Q5:** reconfiguration granularity is per
  100 GHz wavelength channel per user port; in full mesh each of six users
  holds 5 simultaneous links on the same two SNSPDs — links-per-endpoint > 1,
  with the concurrency living in the spectrum, as the sweep suspected. The
  finding that matters: concurrency has a *cost*, because all channels share
  the user's detector pair and accidentals rise with channel count, so under
  poor source/detector conditions (3% HE, 300–350 ps jitter) time-shared
  partial meshes out-key the full mesh on many links (Fig. 6b), while under
  good conditions full mesh wins (Fig. 5d). The optimum "depends strongly on
  source brightness, heralding efficiency, detector timing jitter and link
  loss" — a hardware demonstration that an offer's delivered quality depends
  on what else is co-scheduled through the same endpoint, i.e. quality is
  contextual, not intrinsic to the offer. Directly usable for the HotOS
  "typed offers" argument as a memoryless neighbour. **Q6:** polarisation
  neutralisation flips the source out (flip mirror) and injects reference
  light per channel per path — network-wide quantum downtime — but it was
  needed once at 18.4 h and the mesh then ran > 140 h; the other two
  interruptions were SNSPD cycling. A maintenance actuation with a
  hours-to-days cadence, no budget figure. **Q7:** > 140 h of stable SKR on
  campus/metro fibre after one neutralisation is consistent with the
  hours-scale persistence of 2609.11359; weak because SKR, not path rank,
  is what was tracked. **Fence:** no memory, no held good, no admission; the
  "allocation according to link condition" is experimental comparison of
  topologies, and the storable good is *classical key* ("accumulate secret
  keys… and consume them later"), which is exactly not perishable. Note for
  the related-work map: "quantum network slicing" and "temporary service
  federation" via an added interconnection link (Sec. 3.3) is a federation
  vocabulary neighbour for the HotOS hostile-federation section — occupied
  at the topology level, unoccupied at the custody level.

---

## Open (UNREAD)

*Sweep of 2026-07-25 (first run, fired manually to validate the routine). The
sweep found these two and correctly excluded arXiv 2607.16394 (condensed-matter
"entanglement entropy" — the vocabulary trap the protocol names) and arXiv
2607.05642 (metrics taxonomy, no data answering any threshold). Its own commit
was stranded in an ephemeral cloud checkout with read-only credentials; these
entries were rewritten locally from the arXiv abstracts read first-hand, not
transcribed from the sweep's summary. Question mapping revised on the first
entry — see note.*

### arXiv 2607.19849 — Distributed Entanglement Distribution Using Multiple Entanglement Sources in WDM-based Quantum Optical Networks
*Agrawal, Dulta, Kanseri. Submitted 2026-07-22.*
- **status:** UNREAD (abstract read 2026-07-25; the paper itself is the debt)
- **touches:** Q5, fence
- **would change:** Multi-source WDM entanglement distribution over multi-hop
  repeaterless mesh, with heterogeneous demands differentiated by required ebit
  rate *and* visibility, solved by EPPS placement/selection, wavelength-pair
  assignment and routing against degradation with fibre length and hop count.
  For Q5: if wavelength multiplexing at the source layer substitutes for
  per-module link concurrency, the links-per-module threshold may be answerable
  at the wrong layer — i.e. our object model could be asking about ports when
  the concurrency actually lives in the spectrum.
- **fence note:** this is the closest approach to our problem yet seen — it
  performs admission and placement against quality-differentiated demands. The
  fence still holds on the abstract's own terms: repeaterless and memoryless,
  photons routed and consumed in flight, so there is no good held in custody and
  no aging in place. It is flow allocation, not a cold chain. If the paper turns
  out to model any holding time, the fence needs re-examining, and that check is
  the reason this entry exists.

---

*Sweep of 2026-08-03 (second scheduled run). Window: submissions/revisions
2026-07-25 through 2026-08-03, query table run against quant-ph primarily,
cs.NI/cs.OS/physics.optics secondary. **Provenance caveat:** direct arXiv
access (WebFetch, and curl to export.arxiv.org) is blocked outright by this
session's network egress policy — confirmed via repeated 403s and the local
proxy's own relay log ("gateway answered 403 to CONNECT", host
`export.arxiv.org:443`), not a transient failure. Per the proxy's own
instructions, a policy denial is reported, not routed around. All candidate
identification and abstract-level reading this sweep was therefore done
through the WebSearch tool, which fetches and paraphrases page content
server-side rather than through this session's blocked egress path;
technical phrasing repeated verbatim across independent queries was treated
as a reliable proxy for the abstract, but this is one step further from the
primary than the previous sweep's direct abstract reads. Two candidates were
checked against the query table and rejected as non-hits: arXiv 2607.25501
("Automated discovery of high-probability heralded schemes for path-entangled
states", submitted 2026-07-28) raises heralding *success probability* via
automated linear-optics circuit search but reports no failure-cost or
blocking data, so it does not answer Q4's threshold; arXiv 2607.28572
("Quantum Fidelity-per-Cost: A Metric for Evaluation of Quantum Computing
Systems") is a cross-provider cost/fidelity benchmarking metric for cloud QPU
access with no networked-entanglement or custody content — a metrics-paper
foil in the same shape as last sweep's excluded 2607.05642.*

### arXiv 2607.18387 — Remote entanglement need not be the bottleneck for modular trapped-ion quantum computing
*Knollmann, Nadlinger, Blue, Corsetti, Bishop, Martinez, Notaros, Bruzewicz,
McConnell, Chuang. Submitted 2026-07-20; revised (v2) 2026-07-30.*
- **status:** UNREAD (abstract read via search 2026-08-03, see provenance
  caveat above; the paper itself is the debt)
- **touches:** Q5 — and *possibly* Q4, Q1
- **would change:** Our Q5 threshold (links-per-module = 1 vs > 1) is
  currently open. The abstract as summarized says trapped-ion photonic links
  are today capped in density by bulky collection optics, and proposes
  trap-integrated photonics as part of an architecture for denser,
  parallelizable channels. If that holds up on a full read, it pushes toward
  links-per-module > 1 and licenses overlapping replenishment/consumption
  within one module; if the packing gain turns out to be about parallel
  *modules* rather than parallel *links within* a module, Q5 stays open.
  *Possibly* Q4: the paper's rate/fidelity gains (single-photon heralding,
  coherent recoil correction, projective distillation) could carry a
  hardware-measured failure-to-next-attempt cycle time, which would give Q4
  its first real number — but the summarized abstract claims a rate/fidelity
  improvement, not failure-cost data, so this is inference. *Possibly* Q1:
  "saturating the entanglement rate at a local-operation limit" could imply a
  narrow, near-deterministic cadence bearing on Q1's CoV threshold, but no
  cadence distribution is claimed, so this is inference too.
- **mapping note:** the strongest, best-evidenced claim in the summarized
  abstract is the link-density one (Q5); Q4 and Q1 are plausible readings of
  adjacent claims about rate and heralding, not things the abstract states
  outright. Whoever pays this debt should check Q5 first, and should treat
  the abstract text itself (not this paraphrase) as the source of record.
- **provenance upgrade (2026-08-05):** the abstract was fetched directly
  from arxiv.org/abs/2607.18387 in a session with arXiv access and checked
  against this entry. The sweep's paraphrase is faithful: the Q5
  link-density claim is verbatim in the abstract ("dense,
  easy-to-parallelize channels" vs "bulky collection optics that cap how
  densely links can be packed"); the abstract reports NO failure-cost or
  retry-cycle data (Q4 stays inference, correctly marked); the Q1 reading
  rests on "saturating the entanglement rate at a local-operation limit,"
  claimed with no cadence distribution (thin, as recorded). Projected
  headline for the eventual read: Bell-pair fidelity of 99.9% at
  fault-tolerance-compatible rates and densities — a projection from a
  synthesized architecture, not a measurement. The scrutiny caveat above is
  discharged for the ABSTRACT only; the full paper remains UNREAD and is
  still the debt. (Egress note: the scheduled job now has *.arxiv.org
  access, so future sweeps read abstracts directly and this caveat class
  should not recur.)

---

*Sweep of 2026-08-31 (fifth scheduled run). Window: submissions 2026-08-24
through 2026-08-31 (default 8-day window; prior sweep was 2026-08-24). Direct
arXiv access (export.arxiv.org API and arxiv.org/abs pages) worked this run;
all abstracts below were read first-hand via WebFetch against the primary.
Query table run against quant-ph, cs.NI, cs.OS and physics.optics per the
protocol; a broad topic-only category listing (424 results) was fetched first,
recognized as the topic-sweep failure mode the protocol warns against
("topic sweeps... return everything and settle nothing"), and abandoned in
favor of per-question keyword queries. Candidates checked and rejected as
non-hits: arXiv 2608.23681 ("Bang-bang protocol for nondispersive qubit
readout") reports a QND readout scheme for superconducting qubits with error
decreasing as 1/N, but the abstract describes only a **single-shot**
projective measurement with no discussion of repeated successive readouts of
a stored qubit, cumulative back-action, or a per-readout fidelity cost — it
does not answer Q3's graded-vs-cliff wear threshold. arXiv 2608.24299
("Distributed Resource Theory of Entanglement and Magic") uses "entanglement"
as a resource-theoretic quantity (distributed LOCC-type protocols), not a
networked, scheduled resource surviving a scheduling decision — the
protocol's named vocabulary trap, applied to a resource-theory rather than
quantum-chemistry paper this time. arXiv 2608.26886 ("Quantum Interconnects
Part I: Strategic Quantum Network Formation") proposes a hierarchical
utility-function abstraction (Physical Platforms/Functionalities/Services/
Applications/Use-Cases) for game-theoretic network formation — an economic/
incentive framework for *why* networks form, with no perishability, custody,
or admission content; too thin for the fence. arXiv 2608.27171 ("Conditional
contraction coefficients and their applications to quantum networks") is an
information-theoretic contraction-coefficient result, not scheduling or
resource-management content.*

---

*Sweep of 2026-08-24 (fourth scheduled run). Window: submissions 2026-08-17
through 2026-08-24 (default 8-day window; prior sweep was 2026-08-17). Direct
arXiv access (export.arxiv.org API and arxiv.org/abs pages) worked this run;
all abstracts below were read first-hand via WebFetch against the primary.
Query table run against quant-ph, cs.NI, cs.OS and physics.optics per the
protocol. Candidates checked and rejected as non-hits: arXiv 2608.18666
("Experimental zero-added-loss multiplexing Bell-pair source for long-haul
quantum networks") demonstrates entanglement swapping across 16 parallel
frequency modes from a single ZALM source — this is source-layer spectral
multiplexing of generation rate, not memory-module link concurrency or
switch/topology reconfiguration granularity, so a Q5 reading is too thin to
carry (no switch, no module, no per-port data). arXiv 2608.20291
("Programmable cavity QED with a fiber-integrated atomic array") reports
"cavity-based non-destructive readout of the number of coupled atoms" — this
is atom-count readout in a tweezer array, not repeated QND readout of a
stored qubit's state with a per-readout fidelity cost, so it does not answer
Q3's threshold. arXiv 2608.20443 ("Granthi: Higher-Order Quantum Programming
via Unitary Wiring") states the language "directly supports the quantum
switch, compiled to a static circuit" — a second vocabulary trap alongside
the protocol's named entanglement trap: this "quantum switch" is a
computational control-flow primitive (coherent branching), not a physical
photonic switch fabric, so it is excluded on the same principle. arXiv
2608.17470 ("Absorption-emission quantum repeater using diamond quantum
memories") reports single-node process fidelity (78%) for one
absorb-store-teleport cycle via quantum process tomography — no repeated-
readout wear data and no networked/scheduling content, so it does not answer
Q3 or any other threshold.*

### arXiv 2608.20954 — Tools for Reducing Service Time in Near-Term Quantum Networks
*Smith, Beauchamp, Gauthier, Bouchmal, Wehner. Submitted 2026-08-21.*
- **status:** UNREAD (abstract read 2026-08-24; the paper itself is the debt)
- **touches:** Q1, Q4 — and *possibly* Q6
- **would change:** Our Q4 in-place-herald-retry threshold (failure-to-next-
  attempt cycle time vs deadline slack) and Q1's operational quantile ask
  (is the upper-tail configuration-plus-generation latency small enough
  that a replenishment completes before its reserve margin expires?) are
  both currently answered only by invented numbers in our simulator. This
  paper's entire object is the same quantity from the other direction: the
  abstract states that existing multi-user entanglement architectures
  insert "fixed separations between consecutive batches of entanglement
  generation attempts" after failures, that this separation leaves the
  network "idle" when attempts fail, and that their method shortens it
  "while respecting hardware constraints," using an analytical execution
  model evaluated within the Arqon architecture (service-time reductions of
  up to 7.6% single-application, 26-30% co-scheduled). If the full paper's
  execution model exposes the actual minimum safe separation and what
  hardware constraint floors it, that could replace our invented
  failure-to-next-attempt figure and settle whether our simulator's
  retain-and-retry vs release-and-reacquire asymmetry (Q4) is physics-earned
  or just a design choice. *Possibly* Q6: "respecting hardware constraints"
  when shortening the separation is an explicit claim that some constraint
  bounds achievable cadence, but the abstract does not name the constrained
  resource (thermal, calibration, controller traffic, or something else),
  so whether it ratifies Q6's "does an actuation/reservation consume ANY
  constrained resource" ask is inference pending the full read.
- **mapping note:** the paper is framed as a scheduling/service-time
  optimization over an existing hardware-constrained separation, not as a
  hardware characterization paper — so the debt is whether its analytical
  execution model contains a hardware-measured (vs assumed) cycle-time
  distribution. Whoever pays this debt should check whether the "hardware
  constraints" the abstract references are cited to a measurement or
  simply asserted.

---

*Sweep of 2026-08-17 (third scheduled run). Window: submissions 2026-08-03
through 2026-08-17 (last sweep was 2026-08-03; the default 8-day window was
widened to cover the full 14-day gap). Direct arXiv access (export.arxiv.org
API and arxiv.org/abs pages) worked this run, confirming the prior egress
note; all abstracts below were read first-hand via WebFetch against the
primary, not paraphrased from a search engine. Query table run against
quant-ph, cs.NI, cs.OS and physics.optics per the protocol. Candidates
checked and rejected as non-hits: arXiv 2608.11630 ("Full-Stack High-Volume
Quantum Networking Architecture based on Photonic-Integrated Tin Vacancy
Centers in Diamond") describes spectral tuning to overcome emitter
inhomogeneity and a projected 99.96% connectivity of ~1000 emitters — a
physical-layer indistinguishability fix, not switch/topology/scheduling
data; its "multi-channel quantum repeater node" phrase is too thin to
support a Q5 reading. arXiv 2608.11501 ("Multi-Pair Fidelity-Aware Rate
Allocation in a Quantum Network: Approximation Schemes") proves NP-hardness
and gives FPTAS for fidelity-aware rate allocation, but treats link
fidelities as exogenous inputs rather than measuring spread or calibration
error, and models neither custody (holding) nor perishability (decay) — a
rate-allocation component, not an occupant of the fence's full form. arXiv
2608.12636 ("Free-Space Quantum Networks and Optimized Fiber-Reinforcement")
optimizes macro-scale backbone-node placement (Voronoi tessellation) across
a random-graph network model — topology at the wrong grain for Q5's
per-module/per-port reconfiguration-granularity ask. arXiv 2608.04476
("Heralded Non-Gaussian Squeezed-State Inputs for Parity-Detection SU(1,1)
Interferometry") uses "heralding" for a continuous-variable metrology
protocol, not networked entanglement generation, and reports no
failure-cost or blocking data against Q4's threshold.*

### arXiv 2608.09364 — Quantum-Classical Coexistence Network Tomography
*Wang, Chapman, Ramaswamy, Guedes de Andrade, Chen, Lukens, Vardoyan, Towsley. Submitted 2026-08-10.*
- **status:** UNREAD (abstract read 2026-08-17; the paper itself is the debt)
- **touches:** Q2
- **would change:** Q2 asks whether the instantaneous gap between
  calibration-published and true fidelity is large enough to be OS-visible.
  This paper builds a tomography framework that infers per-link channel
  parameters of a fibre-shared quantum-classical network from end-to-end
  measurements, and on single-link testbed data reports estimated process
  fidelities "closely tracking the Bayesian-process-tomography baseline...
  residual gaps reflect the depolarization-only approximation." If those
  residual gaps are read against the full paper and turn out small relative
  to scheduler decision resolution, that weakens the case for carrying a
  calibration-uncertainty field at all; if large or systematic, it ratifies
  Q2's premise that a calibration-published number needs an attached
  uncertainty (and age) before the OS can trust it.

---

*Sweep of 2026-09-07 (sixth scheduled run). Window: submissions 2026-08-31
through 2026-09-07. **Provenance note:** the previous sweep's entries
(2026-08-24) are the last ones merged to main, but a fifth sweep dated
2026-08-31 was in fact already run and is sitting in open, unmerged PR #4
("Literature surveillance: 2 new debts (2026-08-31 sweep)") with two
entries — arXiv 2608.24152 and arXiv 2608.22766 — plus four non-hits
(2608.23681, 2608.24299, 2608.26886, 2608.27171) documented in that PR's
body. This sweep does not re-litigate that window or those papers; PR #4's
disposition of them stands pending its own merge. This sweep covers only
the window after it (2026-08-31 through 2026-09-07). Direct arXiv access
(export.arxiv.org API and arxiv.org/abs pages) worked this run; all
abstracts below were read first-hand via WebFetch against the primary.
Query table run against quant-ph, cs.NI, cs.OS, cs.DC and physics.optics per
the protocol, plus a category-unfiltered "quantum network" sweep of the
window to catch anything the topic queries missed. Candidates checked and
rejected as non-hits: arXiv 2609.04524 ("DPRQ: A Dynamic Programming-based
Qubit Routing Algorithm for Collective Communication in Distributed Quantum
Computing") optimizes inter-node qubit routing at the circuit-compilation
layer to cut communication overhead between processors — a compiler pass
over a fixed circuit, not runtime scheduling of a perishable physical
resource, so it does not occupy the fence's form. arXiv 2609.02579
("Long-lived telecom-heralded single-photon storage in an absorptive
spin-rephased quantum memory") reports storage lifetimes to 3 ms (classical
regime) and cross-correlation at 180 μs, but a single store-and-retrieve
cycle per measurement, not a distribution of degradation over repeated QND
reads of the same stored state — does not answer Q3's threshold. arXiv
2609.02554 ("Experimental Evaluation of Passive Polarization Compensation
Techniques for Fiber-Distributed Polarization-Entangled Photons") reports
visibilities >93% and fidelities >94.5% after static, single-link
compensation — no cross-sectional spread across simultaneously available
paths, so it does not answer Q2's threshold. arXiv 2609.02841 ("Exponential
speedup of polarization stabilization for long distance DWDM quantum
networks") was checked closely against Q1/Q6/Q7 given its "optical
switches" and 24-hour continuous-operation claims; on the full abstract it
reports no switch actuation latency, no duty-cycle/budget figure, and no
drift-autocorrelation-vs-lead-time comparison — the switches are a
calibration-path-decomposition detail, not characterized as a
scheduled/rationed resource, so it is a component-technology foil, not a
hit.*

---

*Sweep of 2026-09-14 (seventh scheduled run). Window: submissions/revisions
2026-09-07 through 2026-09-14 (last sweep was 2026-09-07). **Access note:**
export.arxiv.org's API endpoint returned HTTP 429 (rate exceeded) for every
attempt this run; arxiv.org's own advanced-search form (`/search/advanced`)
also returned zero results for every query regardless of terms, which on
inspection turned out to be caused by the classification-archive field name
(`classification-quant_ph` does not exist; the working pair is
`classification-physics=y` + `classification-physics_archives=quant-ph`) —
even corrected, the advanced form kept returning the empty-query tips page
rather than results, cause not fully isolated. Direct `arxiv.org/abs/<id>`
pages and the plain `arxiv.org/search/?searchtype=all&query=...&order=-submitted_date`
endpoint both worked reliably and were used for the whole sweep instead;
results were sorted by submission date descending and manually filtered to
the window. Query table run against quant-ph primarily, cs.NI/cs.OS/
physics.optics secondary, using free-text term pairs per question (arXiv's
plain search AND-matches all words across all fields, so field-qualified
syntax like `cat:` or `abs:` is not supported there and was not used).
Candidates checked and rejected as non-hits: arXiv 2609.09400 ("QPS-ToR: A
Parallel Iterative Switching Algorithm for Reconfigurable Optical Datacenter
Switching") is a classical datacenter optical-circuit-switch scheduling
algorithm (cs.NI) reporting throughput and flow-completion-time gains, not a
measured switch-reconfiguration latency distribution, and carries no
quantum content — a scheduling-algorithm foil for Q1. arXiv 2605.04829
("Traffic Chunk Sizing vs. Optical Switching Speed in Future All-Optical
Satellite Networks") is a classical all-optical satellite traffic-engineering
simulation study over MEMS and integrated-photonic switch technologies; it
reports how chunk sizing drives switching-speed *requirements*, not a
measured latency distribution, and has no quantum/entanglement content — a
component-technology foil for Q1, the same shape as prior sweeps' rejected
classical-networking candidates. arXiv 2609.11922 ("A Chip-scale Space-time
Multiplexed Gaussian Boson Sampling Processor Beyond 10,000 Photons") is a
single-chip GBS computational-advantage demonstration; its "space-time
multiplexed" reconfiguration is programming one chip's own on-chip
modulators for different sampling/world-model tasks, not a switch fabric
routing entanglement between held resources across network nodes — too thin
for Q5, no custody or admission content for the fence. arXiv 2604.20376
("Interconnecting Regional QKD Networks: Hybrid Key Delivery Across Quantum
Domains") relays QKD-generated classical secret keys across domains over
PQC-secured classical WAN links; the quantum step (QKD key generation)
completes and is measured out before any inter-domain routing or custody
decision — the same demarcation-foil shape as the molten-salt entry in
Discharged, no quantum state survives a scheduling decision. arXiv
2609.02579 ("Long-lived telecom-heralded single-photon storage...") recurred
in this window's searches but was already checked and rejected by the
2026-09-07 sweep; not re-litigated.*

### arXiv 2609.11359 — Engineering Quantum Links: Noise and Quantum-State-Degradation Metrics over Metropolitan Fiber Network
*Caleffi, d'Avossa, Cacciapuoti. Submitted 2026-09-10.*
- **status:** UNREAD (abstract read 2026-09-14; the paper itself is the debt)
- **touches:** Q7 — and *possibly* Q2
- **would change:** This paper builds quantum-network analogs of classical
  link-budget metrics (a photon-counting SINR and a BER) on a 7.3 km deployed
  metropolitan fiber loop, and explicitly quantifies, for each of
  polarization/time/frequency encodings, "the channel-induced degradation
  and its drift over time." If the full paper's drift measurements yield an
  autocorrelation time or comparable timescale, that is a direct,
  hardware-measured answer to Q7's persistence-vs-lead-time threshold — from
  a deployed link rather than a lab bench. *Possibly* Q2: the paper's stated
  goal is a small set of measurable parameters that "turn quantum networking
  over deployed fiber... into an engineering design problem," adjacent to
  Q2's calibration-published-vs-true-fidelity gap, but the abstract
  characterizes one link over time, not a cross-sectional spread across
  simultaneously available paths, so a Q2 reading is inference.
- **mapping note:** this is a single deployed link measured over time, not
  multiple simultaneously available paths — the same distinction the queue
  already draws for arXiv 2608.07163 between Q7's temporal-persistence
  framing and Q2's instantaneous-spread framing. Whoever pays this debt
  should check Q7 first.

### arXiv 2604.21388 — Bayesian Phase Stabilization at the Shot-Noise Limit for Scalable Quantum Networks
*Liu, Xue, Chen, Zheng, Yang, Li, Wang, Yang, Jiang, Wan, Wang, Chen, Zhang, Pan. Submitted 2026-04-23; revised (v2) 2026-09-09.*
- **status:** UNREAD (abstract read 2026-09-14; the paper itself is the debt)
- **touches:** Q6 — and *possibly* Q1
- **would change:** Our Q6 threshold (does an actuation/reservation consume
  ANY constrained resource at the relevant rate) is currently unanswered by
  hardware data for any budgeted-resource class. This paper reports a
  phase-stabilization protocol for trapped-ion memory nodes bounded to "a
  duty cycle less than 6.5%" specifically "to avoid disturbing fragile
  quantum states," and states the resulting memory-memory entanglement at
  10 km "survives beyond the average time required to establish it." If the
  full paper's duty-cycle bound is a hardware-imposed limit (not a chosen
  operating point) that generalizes to other near-memory operations
  including switch actuation, it would give Q6 its first real number for a
  constrained-resource class of exactly the kind the question names
  (duty-cycle limit tied to avoiding quantum-state disturbance). *Possibly*
  Q1: the "survives beyond the average time required to establish it" claim
  mirrors Q1's replenishment-vs-reserve-margin quantile ask — if the full
  paper reports the actual generation-cadence distribution against memory
  lifetime (not just one favorable comparison), it could supply a first
  real number there too.
- **mapping note:** the duty-cycle figure governs phase-stabilization probe
  pulses on trapped-ion nodes, not photonic switch-fabric actuation — a
  close analog to Q6's ask, not a verbatim answer, so Q6 is primary but not
  yet a direct hit until the full paper is read for whether the constraint
  generalizes. Q1 rests on one comparative sentence in the abstract, not a
  reported cadence distribution, so it is marked possible. This is a v2
  revision of an April 2026 submission (predating this project's question
  list); it is queued now because the revision date falls in this sweep's
  window and the paper was not previously discharged or queued.
