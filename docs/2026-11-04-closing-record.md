# QuantumOS closing record

**Date:** 2026-11-04. **Written by:** the instance that owns `quantumos` (Opus 5.5).

QuantumOS started as a discrete-event simulator for operating-system resource management in an
entanglement-first quantum computer. From August on, its purpose was to find out whether the work
held something provocative enough for a HotOS paper. This record says what it produced, what left
it, and what was tested and failed. It closes the search for a paper. It does not delete or freeze
anything.

## What it produced

- **qsim**: a tested M0 simulator (keyed RNG, paired-policy comparison, JSONL traces,
  post-hoc views) and its sweeps and run notes. It was a sensitivity instrument, and it is cited for
  what it showed: for example, quality-aware scheduling is worthless at a 100 µs retry and decisive at
  250 ms.
- **A method record.** It holds OTS-stamped pre-registrations, results and corrections, including
  rescoring a PI bet that had been scored against the analyst's gloss (`d45de75`). It is
  practice-grade by Tony's own statement (2026-07-09).
- **The object-model admission rule** (README): no quantity enters the model unless it names the
  decision that reads it, the lead time it is read at, and why it can't be derived from cheaper
  represented state.

## What left it

- **The admission rule went to tupay** (2026-10-27) as a design constraint for its witness tool.
- **Corrections to the governance calibration study** (§8 check, 2026-10-13, all adopted): the
  practice-grade register is keyed to the instrument; a bettor code covers analyst text written in
  the PI's name; the study flags corrections committed after it made contact.
- **A first measurement of findability** on a real 28.4M-file personal corpus (Indaleko dump,
  2025-03-27; aggregates only):
  - storage rewrites the time cue in transit (creation dates mostly record arrival on the volume;
    about 45% of files, an upper bound, sit on 27 bulk-rewrite days);
  - for human-type files at equal precision, findability within 100 results fell about 4x between
    2005 and 2024;
  - the recall deficit grew from 2.7 to 10.8 missing bits between 1998 and 2024.

## What was tested and failed

| Candidate | How it was tested | Why it failed |
|---|---|---|
| Fungibility ("the OS decides when resources may become fungible") | one-page, outline | agreeable, didn't change a reader's mind |
| Repair without the truth (failure x repair-source grid) | cold read #1 | strawman premise; the taxonomy had no consequence |
| Nines of findable data | cold read #2 | metric undefined without a reader model; ranking ignored |
| Findability as the dual of k-anonymity | cold read #3 | duality already known (Sweeney; Narayanan–Shmatikov) |
| Data-driven findability decline | cold read #4 + denominator test | the claim survives but narrows (4x); it is bin-population arithmetic |
| Coherence protocol for externalized indexes | prior-art check | 7 of 8 elements known (HTTP validators, `plocate -e`, Perkeep, git-annex) |
| Commit with perishable prepared state | two novelty checks | anticipated by Timed Atomic Commitment (Davidson, Lee & Wolfe 1991) and QNP (Kozlowski, Dahlberg & Wehner, CoNEXT 2020); the premise that physics forces abort was wrong |

Drafts, cold reads, scripts and aggregates are in the gitignored `docs/drafts/` on this machine.

## What a successor could still pick up

These are small items, each a claim narrower than a paper:
- unrepairable abort residue in multi-site quantum operations beyond two-party pairs, where
  coordinated EXPIRE fails;
- a measurement of which tools strip which file metadata;
- pricing outside cues (location, calendar, who) in bits against the measured recall deficit.

None of these was judged interesting enough to pursue as it stands. One exception is conditional.
A storage-workshop paper on findability decay could be worth writing, if it finds a second corpus
(n = 1 is fatal) and survives positioning against Agrawal, Bolosky, Douceur & Lorch, "A Five-Year
Study of File-System Metadata" (FAST '07). Checked on 2026-11-04. **Positioning survives:** copy-reset creation
times are prior art (Douceur & Bolosky, SIGMETRICS 1999; Agrawal et al., FAST '07), but bulk-rewrite
days over 30 years, rate-driven findability decay and the recall deficit were not found. **Second
corpus:** no public multi-decade personal dataset exists. The best candidate is the Microsoft
2000–2004 metadata study on SNIA IOTTA (thousands of corporate desktops; behind a license and a
browser check). Status: go only if that data can be obtained; otherwise no paper.
