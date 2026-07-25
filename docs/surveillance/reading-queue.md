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

*(none yet — first sweep pending)*
