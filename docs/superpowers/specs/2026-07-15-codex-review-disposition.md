# Disposition of the external skeleton review (Codex, 2026-07-15)

**Date:** 2026-07-15 (evening)
**Reviewed artifact:** `2026-07-15-arxiv-paper-skeleton.md` (35e425e)
**Review verified before disposition:** both load-bearing repo citations check out —
the taxonomy note does state that all of qsim today is the pre-cloning degenerate case
(objects coincide), and the S1 run note does bound the transition result to the
retain-and-retry protocol branch. The review's four external citations (QNodeOS
Nature 2025; ESDI 2303.17540; noisy-memory scheduling 2205.06300; fidelity-age
2602.09562) are NOT yet verified by us and enter the literature matrix as claims.
Test-suite claim (463 green) matches the v0.1.0 tag record.

## Adopted

1. **The mismatch gate (the review's central finding, confirmed).** The skeleton's
   most novel claim (the carrier/claim/warrant/exercise-gate split under encrypted
   cloning) and its empirical instrument describe different systems: no split state is
   admitted into qsim. No prose-drafting campaign begins until the sprint below
   produces a result of the form *"the conflated lease makes decision X incorrectly;
   the split abstraction preserves invariant Y or improves outcome Z"* — or fails to,
   in which case the long paper does not proceed as designed. The skeleton's status
   is now GATED accordingly.
2. **The validation sprint** (bounded; mostly work the record already ordered):
   a. **Literature matrix** — upgraded from the existing "verify shelf pointers"
      citation gate to an adversarial differentiation pass: does anyone in the
      entanglement-scheduling literature (the four cited systems plus neighbors on
      recoverability, one-shot resources, authority) already hold the
      presence-vs-recoverability split? The perishability premise alone is treated as
      occupied territory until the matrix shows otherwise.
   b. **Implement hedged-placement Stage 1** — the minimal carrier/claim/warrant/gate
      model the review demands ALREADY EXISTS as a human-approved preregistration
      (2026-07-13 charter + Stage 1 prereg, approved 2026-07-14): its deciding
      question is exactly the review's demonstration target (late binding vs prebound
      policy; gains vs key fragility and structural cost), and it is envelope-shaped
      (an exact region map, not one operating point) — which also discharges the
      review's "test across a parameter envelope" demand by prior design.
   c. **Physicist review of claim/key decay semantics** — the ask channel, already
      committed as Q1–Q7; the sprint makes the claim/key-decay portion the priority
      ask.
3. **Maintenance amplification stays motivation-grade.** The 76% figure is one
   low-water policy at one operating point; it appears with that bound in the same
   sentence, never as an architectural law.
4. **Decode experiment demoted in the technical argument.** Out of the technical core
   entirely; in the long position paper it shrinks from 1.5 pages to a bounded short
   subsection or sidebar (final size is Tony's call — the audience model was his).
5. **Photonic as deployment context, not established scope** — already the skeleton's
   §0.2 decision; affirmed.

## Pushed back

1. **Genre.** The review evaluated the long arXiv version as a systems-contribution
   paper and found it wanting by that genre's standard. The long version is a
   POSITION paper: its deliverable is the named abstraction plus seven instrument-
   earned questions with decisions attached — an ask channel that functions even with
   zero new systems results. The review itself scores the question list "useful
   agenda." The genre distinction stands. What is conceded: even a position paper
   dies if its central abstraction is occupied (matrix decides) or unexercised
   (Stage 1 decides) — so the sprint gates BOTH papers, and that is adopted above.
2. **Inversion, half.** The review's proposed narrow paper ("Carrier, Claim, and
   Gate: OS Semantics for Single-Use Quantum Recoverability") is, to a first
   approximation, the HotOS distillation already in the two-paper strategy — HotOS is
   a ~5-page position venue with a Jan 2027 deadline. Adopted: the ORDER inverts
   (sprint → narrow technical core → long position paper), and the long version
   grows from the core's evidence. Rejected: discarding the long version's narrative
   architecture; it serves the outreach function the narrow core cannot.
3. **Reviewer citations are claims.** The four external systems are exactly the kind
   of prior art the matrix must verify at first hand; nothing is conceded to them
   sight-unseen, and nothing is claimed against them sight-unseen either.

## Net plan (supersedes the skeleton's build order until the gate clears)

1. Sprint item (b): implement hedged-placement Stage 1 per its preregistration
   (stamp before implementation, per its own rule).
2. Sprint item (a): literature matrix, adversarial framing.
3. Sprint item (c): route the claim/key-decay ask.
4. Gate review: proceed to the narrow core only on a demonstration; proceed to long-
   version prose only with the core in hand. If the demonstration fails, the honest
   products are the cold-chain essay, the instrument record, and the question list —
   per the review's own closing, and per this project's standing negative-result
   framing (HSD precedent).
