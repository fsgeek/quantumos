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

### arXiv 2607.15262 — Dynamic Entanglement Distribution for Multi-User and Multi-Protocol Quantum Networking
*Wang, Clark, Alia, Bahrani, Aktas, Peranić, Stipčević, Lončarić, Rarity, Joshi, Simeonidou. Submitted 2026-07-16.*
- **status:** UNREAD (abstract read 2026-07-25; the paper itself is the debt)
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

### arXiv 2608.07163 — Rate-Fidelity Control for Wide-Area Quantum Links
*Clayton, Nunn, Carmack, McKenzie, Richards, Wu, Bhattacharjee. Submitted 2026-08-07.*
- **status:** UNREAD (abstract read 2026-08-17; the paper itself is the debt)
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

### arXiv 2608.04093 — An optical-fibre-integrated buffer for packet-switched quantum networks
*Spegel-Lexne, Argillander, Clason, Claesson, Hey Tow, Lima, Pereira, Xavier. Submitted 2026-08-04.*
- **status:** UNREAD (abstract read 2026-08-17; the paper itself is the debt)
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
