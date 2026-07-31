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
