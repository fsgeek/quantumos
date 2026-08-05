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
