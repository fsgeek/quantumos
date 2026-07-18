# Cross-platform signed OpenTimestamps hook design

**Date:** 2026-07-18
**Status:** APPROVED DIRECTION — revised design awaiting final review; implementation not begun
**Scope:** repository contribution mechanics only; no simulator or paper-content changes

## 1. Purpose

Make the repository's signed OpenTimestamps workflow automatic, auditable, and easy
for future human and AI contributors to use from the Windows host while preserving a
native Linux path.

After one installation command, the healthy path must require no timestamp-specific
knowledge: a contributor makes one ordinary signed commit, and the repository creates
and signs its timestamp-evidence commit automatically. If timestamping is interrupted,
the contributor receives one explicit recovery command. Work is never destroyed to
repair provenance, and missing or invalid evidence cannot be pushed accidentally. A
cryptographically valid calendar proof may still be pending Bitcoin confirmation, but
that state is always reported honestly.

For commits explicitly designated as preregistrations, a separate confirmation-gated
publication step creates a third-party-visible, independently verifiable commitment.
Routine timestamping and public preregistration are deliberately distinct: the former
is automatic local provenance; the latter is an authorized external act.

## 2. Current findings

The repository declares `opentimestamps-client` 0.7.2 and the Windows virtual
environment contains its `ots.exe`. The executable fails at import time, before command
dispatch, through this dependency chain:

```text
opentimestamps-client 0.7.2
  -> opentimestamps 0.4.5
    -> python-bitcoinlib 0.12.2
      -> bitcoin.core.key
        -> ctypes searches for ssl.35, ssl, or legacy libeay32
          -> Windows library discovery returns no loadable DLL
```

The failure reproduces on Windows CPython 3.13 and 3.14, so it is not specific to the
project's Python 3.14 requirement. The same pinned client runs successfully in the
installed Ubuntu WSL distribution. The Windows checkout is available to WSL under
`/mnt/c`, so WSL can act as a narrow OTS execution boundary without becoming the
repository's Git, signing, editing, or test environment.

The clone's `.git/hooks` contains generic Git LFS hooks, but the repository has no
`.gitattributes` and `git lfs ls-files` is empty. The existing
`scripts/install-hooks.sh` would overwrite the LFS `post-commit` hook and install an OTS
wrapper that assumes `.venv/bin/ots`, which does not exist in the Windows virtual
environment.

The existing evidence format timestamps a file whose content is the 40-character SHA-1
Git object identifier. OTS internally SHA-256-hashes that file, but this does not give
an independent SHA-256 binding to the commit object or its complete tree. The repository
uses hardened SHA-1 Git object storage; Git's own transition documentation nevertheless
classifies SHA-1 as weak and chooses SHA-256 as its successor.

The current history also exposes four evidentiary boundaries that the original design
did not state:

- a completed Bitcoin attestation establishes only that the evidenced data existed no
  later than the attesting block time;
- Git author and committer dates are signed assertions, not independently established
  event times;
- a pending calendar proof is not yet a Bitcoin anchor and must never be described as
  anchored;
- existence of one commitment does not prove that no undisclosed alternatives existed.

A signed Git commit embeds its GPG signature in the commit object. Preserving and
timestamping that exact object therefore also establishes that the signature existed by
the Bitcoin upper bound, which is useful when a key later expires, is revoked, or is
reported compromised. That composition is valid only while the exact commit object and
the verification key remain available.

## 3. Goals and non-goals

### 3.1 Goals

- Preserve Windows Git as the sole authority for repository state.
- Preserve Windows GPG as the signer of substantive and OTS evidence commits.
- Use WSL only to execute a pinned OTS client against one explicitly named evidence
  artifact.
- Give Linux contributors the same repository-level lifecycle using a native OTS
  executor.
- Keep hook logic tracked and reviewable.
- Attempt timestamp creation after every non-OTS commit.
- Classify OTS maintenance commits by both exact subject and tree shape, never by a
  permissive subject prefix alone.
- Prevent pushes containing new non-OTS commits without committed timestamp evidence.
- Recover safely after offline work, WSL failure, OTS failure, signing failure, amend,
  or rebase.
- Preserve all pre-existing evidence and distinguish historical gaps from new failures.
- Pin timestamped commit objects against local garbage collection.
- Add an independent SHA-256 binding to the canonical commit object and complete tree.
- Provide a tracked verifier that a skeptical third party can run without the author.
- Report pending and Bitcoin-anchored proofs as different states.
- Provide an explicit public-preregistration operation that preserves and discloses the
  selected commitment before its deciding run.
- Make installation and recovery idempotent.

### 3.2 Non-goals

- Patch installed `site-packages` or vendor cryptographic loader code.
- Make WSL the project development environment.
- Add Git LFS to a repository that does not use it.
- Delete, rewrite, or manufacture historical timestamps.
- Make a `post-commit` failure undo a substantive commit; Git does not permit that.
- Hide a failure merely to preserve an apparently clean working tree.
- Treat Git dates as independently proven timestamps.
- Describe a pending calendar proof as Bitcoin-anchored.
- Prove that no private branch, draft, or contradictory hypothesis ever existed.
- Publish any commit or preregistration without an explicit confirmation at execution
  time.
- Offer an opinion about legal admissibility; the design specifies technical evidence
  and its limits.

## 4. Authority boundary

### 4.1 Windows Git owns

- commit creation and history;
- generation of the canonical evidence manifest;
- creation of local preservation refs;
- staging timestamp artifacts;
- creation of the generated `ots:` commit;
- GPG signing of both commit kinds;
- push validation and execution.

### 4.2 WSL owns only

- execution of pinned `opentimestamps-client` 0.7.2;
- reading one evidence artifact in the mounted Windows checkout;
- writing or upgrading that file's `.ots` proof.

WSL must not run Git, stage files, create commits, sign commits, edit project content,
or execute the simulator test suite as part of this workflow.

### 4.3 Public GitHub remote owns only after explicit publication

- the immutable preregistration release and its locked tag;
- the attached portable Git bundle, evidence manifest, OTS proof, exact policy, and
  required public verification keys;
- GitHub's release attestation and public transparency record; and
- the later linked anchor release when the OTS proof becomes Bitcoin-complete.

The automatic commit hook never contacts the GitHub API and never creates a release.
Public registration is a separate command with a human-visible preview and confirmation.

### 4.4 Linux hosts

Linux uses the same tracked hooks, policy, evidence layout, and failure contract. Its
executor invokes the project's native `.venv/bin/ots` after preflight. Platform
detection changes only the executor adapter.

## 5. Components

### 5.1 Tracked hook directory

A repository-owned hook directory contains `post-commit` and `pre-push`. Installation
sets repository-local `core.hooksPath` to that directory. Existing `.git/hooks` files
are neither overwritten nor composed implicitly.

### 5.2 Installer

The Windows installer is one idempotent PowerShell command. It:

1. verifies that it is running in this repository;
2. checks Windows Git identity, `commit.gpgsign`, signing-key configuration, and signing
   executable availability;
3. discovers an available WSL distribution without hardcoding the Windows or Linux
   username;
4. discovers `uvx` inside that distribution and verifies pinned OTS startup;
5. verifies that the Windows repository path maps into WSL;
6. inspects the effective and local `core.hooksPath` values;
7. refuses to replace an unrelated hook-path configuration without explicit human
   resolution;
8. configures the tracked hook path only after all preflights pass; and
9. runs a read-only timestamp-policy audit.

Re-running the installer makes no additional changes after a successful installation.
A Linux installer performs the corresponding native checks and configures the same
tracked hooks.

### 5.3 OTS executor adapter

The hook calls one repository-owned adapter with a target evidence-artifact path. The
adapter selects:

- Windows: `wsl.exe`, the discovered distribution, and pinned OTS through WSL `uvx`;
- Linux: the project-native `.venv/bin/ots`.

The adapter returns success only when the expected `.ots` artifact exists. It preserves
any partial artifact on failure and emits a diagnostic naming the failed boundary.

### 5.4 Evidence manifest and preservation ref

For each new substantive commit `<hash>`, Windows Git creates
`refs/quantumos/timestamps/<hash>` pointing to the exact commit before invoking OTS.
This ref prevents local garbage collection after amend or rebase. It is preservation
state, not proof of publication; a local ref alone makes no third-party claim.

The OTS target for new evidence is canonical UTF-8 JSON at
`timestamps/<hash>.json`, serialized with sorted keys, no insignificant whitespace, and
one trailing newline. It contains at least:

- schema version, evidence-policy version, and SHA-256 of the policy file;
- Git object format and full commit object identifier;
- SHA-256 of the canonical Git commit object bytes
  (`"commit " + decimal_length + NUL + commit_body`);
- a SHA-256 digest of a canonical flattened representation of the complete tree,
  derived from sorted, length-delimited records containing path bytes, mode, object
  kind, and SHA-256 of each blob's bytes;
- explicit records containing each gitlink object identifier, whose external submodule
  content is not claimed;
- the signing-key fingerprint read from the commit signature and the tracked public-key
  identifier that verifies it;
- author and committer times labeled `asserted_*`; and
- the evidence-format implementation version.

The tree algorithm is specified byte-for-byte in the implementation documentation and
shared by creator and verifier. It may not depend on locale, checkout line endings,
filesystem enumeration order, or archive metadata. The resulting OTS proof is
`timestamps/<hash>.json.ots`.

Historical raw-hash proofs remain valid under evidence schema v1. New evidence uses
schema v2; no historical proof is rewritten merely to adopt the new format.

### 5.5 Repair command

`scripts/repair-timestamps.ps1` is the only recovery command a Windows contributor must
remember. It finds unpushed, non-exempt, non-OTS commits that lack committed evidence
or have uncommitted evidence, then completes the same stamp-stage-sign sequence in
history order. It is safe to run repeatedly. A Linux wrapper exposes the same behavior.

### 5.6 Independent verifier

Tracked Windows and Linux entry points invoke one common verifier. Given a commit, it:

1. locates schema-v1 or schema-v2 evidence and its exact policy version;
2. proves that the evidence names the requested commit and, for schema v2, that the
   policy bytes match the manifest's policy SHA-256;
3. locates the structurally valid evidence commit that introduced the target files and
   any valid upgrade commit supplying the current proof, then verifies those commits'
   signatures and the target commit's signature plus their exact signing-key
   fingerprints against the policy-selected tracked public keys;
4. recomputes and compares the schema-v2 commit-object and complete-tree SHA-256
   digests;
5. verifies the OTS proof against its target file;
6. reports `INVALID`, `PENDING`, or `BITCOIN_ANCHORED` without collapsing states;
7. reports the Bitcoin block height and block time when anchored;
8. reports Git author and committer times only as signed assertions; and
9. states the source and trust assumptions for the public key, Bitcoin headers, remote
   release metadata, and any calendar lookup.

Exit status `0` means all checks pass and the proof is Bitcoin-anchored; a distinct
nonzero status means valid-but-pending; all invalid or incomplete evidence fails with a
separate status. Machine-readable JSON and concise human output carry the same fields.

### 5.7 Public preregistration command

`scripts/publish-preregistration.ps1` accepts an explicit commit, stable registration
name, and remote. It is never called by a hook. Before any external write it displays
the exact commit, evidence commit, tag, remote URL, proof state, assets, and non-claims,
then requires confirmation.

The command requires a public GitHub remote with immutable releases enabled. It refuses
to fall back silently to a mutable tag or ordinary release. After confirmation it:

1. verifies the commit, signature, manifest, and at-least-pending OTS proof;
2. creates a signed annotated tag pointing to the evidence commit;
3. creates a self-contained Git bundle preserving the target, evidence commit, and
   objects necessary to reconstruct and inspect the target tree;
4. prepares the bundle, evidence manifest, OTS proof, exact evidence policy, required
   armored public verification keys, and a signed registration statement as release
   assets. The statement names the deciding protocol, declares that its deciding run
   has not begun, identifies the proof state, and repeats the evidentiary non-claims;
5. creates a draft release, attaches all assets, verifies their SHA-256 digests, and
   publishes the release immutably;
6. verifies remote visibility, tag immutability, and the generated release attestation;
   and
7. writes a local receipt containing the immutable release URL, tag, asset digests, and
   attestation identity for later committed audit.

The initial release may honestly contain a pending OTS proof because immediate public
disclosure closes the registration-to-run selective-disclosure window when the stated
protocol treats only earlier public registrations as eligible. The command refuses a
statement that does not declare the deciding run unbegun. After OTS completion, the
upgrade workflow creates a separately named, immutable anchor release containing the
completed proof and a signed statement linking it to the original registration release.
Neither release is amended or replaced.

This procedure proves public commitment to the disclosed registration. It does not
prove that no undisclosed drafts ever existed; the scientific protocol must state that
only publicly registered commitments are eligible to govern a deciding run.

### 5.8 Timestamp policy

A tracked policy file defines:

- schema-v1 legacy paths and schema-v2 manifest/proof paths;
- the canonical commit-object and complete-tree SHA-256 algorithms;
- the generated commit subject convention `ots: stamp <full-commit-hash>`;
- the upgrade subject convention `ots: upgrade <count> timestamp(s)`;
- the permitted tree shape for stamp and upgrade maintenance commits;
- the exact historical exemptions in section 9;
- authorized signing-key fingerprints, tracked public-key paths, activation history,
  and the rule that historical verification keys are retained after rotation;
- policy-version activation commits and the rule that policy changes are not applied
  retroactively;
- preservation-ref naming and retention rules;
- preregistration and anchor-release naming rules;
- the rule that all other substantive commits introduced by a push require evidence.

The policy is data, not a hidden list embedded in hook code.

## 6. Normal commit lifecycle

1. Windows Git creates and signs the substantive commit.
2. `post-commit` exits immediately when an explicit re-entry environment marker is set.
3. Otherwise Windows Git creates `refs/quantumos/timestamps/<hash>` and verifies that it
   resolves to the exact new commit.
4. The manifest generator writes and self-verifies `timestamps/<hash>.json`.
5. The executor invokes OTS in the appropriate environment against the manifest.
6. The hook verifies that `timestamps/<hash>.json.ots` now exists and binds to that
   manifest.
7. Windows Git stages only the manifest and its proof.
8. Windows Git creates an explicitly signed `ots: stamp <hash>` commit while setting
   the re-entry marker.
9. The generated commit's `post-commit` invocation observes the marker and exits.
10. The healthy outcome is a clean working tree with the substantive commit immediately
   followed by its signed evidence commit.

The environment marker is the recursion authority. The `ots:` subject remains a
human-readable convention and one input to policy classification, not the sole
recursion guard or a sufficient exemption from timestamping.

### 6.1 OTS upgrade lifecycle

The existing delayed-upgrade operation uses the same executor adapter: WSL on Windows
and the native client on Linux. It upgrades existing proofs, stages only `.ots` files
whose bytes changed, and creates an explicitly signed
`ots: upgrade <count> timestamp(s)` commit with the re-entry marker set. A no-change run
creates no commit. Upgrade commits do not themselves require timestamp proofs.

Push eligibility accepts a cryptographically well-formed pending proof; it does not
require waiting hours for Bitcoin confirmation. The upgrade command and verifier must
continue to label such a proof `PENDING`. Only successful independent verification of a
Bitcoin attestation permits `BITCOIN_ANCHORED` language.

An OTS stamp commit qualifies as maintenance only when its subject names its first
parent's full hash and its diff introduces exactly the policy-selected evidence files
for that hash under `timestamps/`. An OTS upgrade commit qualifies only when its subject
count matches its diff and every changed path is an existing policy-recognized `.ots`
proof. A commit that
merely begins its subject with `ots:` but changes any other path is substantive and
requires its own timestamp.

## 7. Push invariant

`post-commit` is an automatic attempt, not an enforcement point: its exit status cannot
undo the commit that triggered it. `pre-push` is the enforcement point.

For each ref update received on standard input, `pre-push` enumerates commits newly
introduced to that remote ref. For every commit that is neither a structurally valid
OTS maintenance commit nor an exact historical exemption, it verifies that the pushed
tip contains the policy-selected evidence files for that commit and that the independent
verifier reports either `PENDING` or `BITCOIN_ANCHORED`. Missing, invalid, or structurally
unreachable evidence aborts the push and prints:

- every affected commit hash and subject plus the missing or invalid condition;
- the fact that no remote update occurred; and
- the single repair command.

The validation hook never mutates history, invokes OTS, or attempts repair during a
push. Deletion updates contain no new commits and require no timestamp action. New refs
still apply the exact exemption policy, so branching from old history does not exempt
new work.

## 8. Failure and recovery contract

The governing rule is: **never destroy work to repair provenance, and never submit work
whose required evidence is missing or invalid.** A valid pending calendar proof is
eligible for push but is not represented as Bitcoin-anchored.

- If substantive signing fails, Git creates no commit and timestamping does not begin.
- If timestamping fails, the signed substantive commit remains intact. The hook emits
  `EVIDENCE INCOMPLETE` prominently and preserves the manifest, local preservation ref,
  and any partial proof. `PENDING` is reserved for a valid calendar-attested proof.
- If evidence-commit signing fails, the evidence files remain available for recovery;
  they are not committed unsigned.
- Offline commits are permitted. Push is blocked until evidence is repaired to at least
  a valid pending state.
- Repair discovers state from Git history, the remote-tracking boundary, the policy,
  and the evidence tree; it does not depend solely on terminal output or an ephemeral
  marker.
- Amend and rebase create new commit hashes and therefore new timestamp obligations.
  Old proofs and preservation refs remain historical evidence and are never deleted
  automatically. The verifier must be able to inspect the old object through the ref.
- A proof that already exists is validated or committed rather than overwritten.
- Failure to create an immutable public registration leaves the local commit and proof
  unchanged and produces no claim of public registration. A draft remote release is
  either completed after asset verification or explicitly reported for human cleanup;
  it is never mistaken for a published registration.
- Failure messages identify whether discovery, path mapping, WSL startup, OTS startup,
  calendar submission, artifact verification, staging, or GPG signing failed.

## 9. Historical boundary

The initial audit, before this design's first commit, found 201 commits: 95 substantive
commits and 106 `ots:` commits. Ninety substantive commits had filesystem OTS proofs.
The design and its one-time evidence commit then brought the pre-revision baseline to
203 commits: 96 substantive commits, 107 `ots:` commits, and 91 substantive commits
with proofs. The following five earliest substantive commits predate the established
timestamp practice and remain the only legacy exemptions:

```text
8cea0f3ee5e8dd12fb8f6e5754bd5e849be4688f  Initial project commit.
c2b88885ddbb00ed65b23eaf3d32021c7bccc14b  Add design spec for the quantum OS sensitivity simulator
9a45cb17fd86f3331fd4fbcf966be207e5177759  Build qsim/entities layer: OS object model as inert dataclasses
ea7b434e11cad5755b2063f9071311ecddeafd7b  Build qsim/models layer: five physics surfaces + negative controls
bd45e58e6826db714ce6e4728f5784fbbfc85c82  Add entities package-level re-exports to match the frozen contract
```

They must not be stamped retroactively: a proof created now would establish present
existence, not their historical commit dates. The policy records the gap explicitly
rather than obscuring it. No pattern, date range, ancestor relationship, or commit
subject may create additional exemptions.

## 10. Security and integrity properties

- OTS executes from a pinned package version in the selected adapter environment.
- No cryptographic dependency is patched in place.
- WSL receives no signing authority.
- Generated commits use explicit signing rather than relying only on ambient defaults.
- Hooks stage only the named evidence manifest and proof, never broad working-tree
  changes.
- Tracked armored public keys are matched by full fingerprint and retained for
  historical verification after rotation; repository possession of a key does not by
  itself prove the human identity behind it.
- Schema-v2 evidence binds both the signed commit object and complete tree through
  SHA-256 independently of the repository's SHA-1 object names.
- Local preservation refs are never advertised as public evidence.
- Existing proofs are never silently replaced.
- Hook installation is repository-local and does not modify global Git configuration.
- An unrelated existing `core.hooksPath` is a human-visible conflict, not an overwrite.
- Bypassing local hooks remains technically possible in Git, so remote signed-submission
  policy remains an independent defense. The local workflow reduces accidents; it does
  not claim to replace repository governance.
- Public preregistration always requires an execution-time confirmation naming the
  remote and irreversible release identity.

### 10.1 Evidentiary claims and non-claims

For schema-v2 evidence, a successful independent verification supports this technical
statement:

> The preserved target commit object and complete tree match the SHA-256 evidence
> manifest; the named key signed the target commit; the manifest and each committed
> proof state were included in signed OTS maintenance history; and Bitcoin attests that
> the manifest existed no later than the reported block.

It does not independently establish when the author wrote the content, when Git created
the commit, who controlled the key as a matter of human identity, whether the key was
uncompromised before the attestation, whether the work was publicly disclosed before a
registration release, or whether undisclosed alternatives existed. Git dates are
reported as signed assertions. The difference between an asserted Git date and Bitcoin
block time is operational metadata, not an independently proven creation-to-anchor
interval.

A public immutable preregistration release adds a narrower statement: the selected
registration and its assets were disclosed through the named third-party record before
the deciding run. Scientific materials must cite the release identity and must not
upgrade that statement into proof of exhaustive hypothesis generation.

### 10.2 Public-disclosure option disposition

The design considered the materially distinct practical mechanisms:

- **OpenTimestamps alone, an RFC 3161 authority, or a direct blockchain transaction:**
  supplies third-party time evidence with different trust and cost profiles, but a
  digest alone is not a durable, intelligible public disclosure of the registered Git
  objects and protocol statement.
- **Ordinary signed Git tag:** low burden and preserves reachability while present, but
  the tag and hosted evidence remain mutable or deletable.
- **Direct Sigstore Rekor entry:** append-only and independently auditable, but adds a
  new CLI, entry schema, identity flow, and service-specific maintenance path.
- **Zenodo version:** durable and DOI-addressable, but too heavyweight for each
  preregistration and poorly matched to immediate iteration.
- **Software archive or content-addressed network:** improves replication or content
  addressing, but availability, ingestion delay, and independently established public
  disclosure time vary and still require a signed registration statement.
- **Email, website, or issue disclosure:** third-party-visible in some deployments but
  inconsistent, difficult to verify uniformly, and not a durable artifact protocol.
- **GitHub immutable release:** native to the existing public remote, locks the tag and
  assets, generates a cryptographic release attestation, and records that attestation in
  a public transparency system while supporting portable bundle assets.

The immutable GitHub release is selected because it provides the best evidence-to-burden
ratio for this repository. Direct Rekor publication is rejected for now as duplicative
of the release-attestation transparency path, not because it lacks evidentiary value.
The publication command refuses when immutability is unavailable rather than weakening
the contract silently.

## 11. Test design

### 11.1 Deterministic temporary-repository tests

Tests use disposable Git repositories and controllable fake executor/signing boundaries
where appropriate. They cover:

- one substantive commit produces exactly one evidence commit;
- recursion cannot occur;
- canonical manifest serialization is byte-for-byte deterministic across repeated runs;
- the manifest's canonical Git commit-object SHA-256 and complete-tree SHA-256 change
  when their respective inputs change and remain stable otherwise;
- paths with arbitrary valid Git bytes, file modes, object types, empty blobs, symlinks,
  and nested trees are encoded without ambiguity;
- gitlinks are identified and their stated external-content limitation is preserved;
- stamp and upgrade maintenance commits are recognized only when both subject and tree
  shape satisfy policy;
- an `ots:`-prefixed commit that changes non-timestamp content remains substantive;
- paths containing spaces;
- idempotent installation and repair;
- unrelated hook-path configuration is preserved;
- OTS, WSL, network, artifact, staging, and signing failure injection;
- preservation of the substantive commit and partial artifacts on every failure;
- preservation refs keep amended or rebased preimages reachable through aggressive
  reflog expiry and garbage-collection simulation;
- pre-push rejection before remote contact when evidence is absent;
- successful push validation after repair;
- amend and rebase obligations;
- new branches rooted in old history;
- schema-v1 historical proof compatibility alongside schema-v2 manifests;
- verifier outcomes and exit codes for `INVALID`, `PENDING`, and `BITCOIN_ANCHORED`;
- verifier rejection of a mismatched public-key fingerprint, commit object, tree,
  manifest, signature, or proof;
- signing-key rotation preserves verification of old evidence while applying the new
  policy only from its declared activation point;
- honest reporting of asserted Git dates, OTS calendar attestations, Bitcoin block time,
  and the trust assumptions for each;
- publication preview performs no external write;
- declining confirmation performs no external write;
- publication refuses a mutable release configuration and never falls back silently;
- mocked publication verifies the tag, bundle, manifest, proof, public key, signed
  statement, asset hashes, release immutability, and attestation receipt;
- a fresh disposable clone can reconstruct the registered commit from the bundle and
  independently verify its Git signature and schema-v2 evidence;
- a pending preregistration is labeled `PENDING` and a later linked anchor registration
  is accepted only when the verifier reports a valid Bitcoin attestation;
- exact handling of the five historical exemptions; and
- refusal of any undeclared exemption.

### 11.2 Host integration tests

Outside the QuantumOS repository history, a disposable fixture verifies:

- real pinned OTS startup and stamping through Ubuntu WSL;
- real Windows Git/GPG signed commits and signature verification;
- the complete two-commit lifecycle;
- simulated interruption followed by the public repair command; and
- the Linux executor path inside WSL where practical.

External calendar interaction uses only a disposable schema-v2 evidence manifest. No
QuantumOS content or private signing key crosses into WSL.

Ordinary integration tests do not publish live immutable GitHub releases. They validate
the remote's immutable-release capability read-only and use a fake publication boundary
for failure and ordering cases. The first intentionally named preregistration, approved
at execution time, is the live end-to-end publication acceptance test.

### 11.3 Repository acceptance

Acceptance requires:

1. both installers are idempotent;
2. the historical audit reports exactly the five declared exemptions and no unexplained
   gaps;
3. the complete QuantumOS test suite passes;
4. a successful real commit cycle leaves a clean working tree;
5. both the substantive and generated evidence commits verify as signed;
6. the target manifest and proof verify as present, committed, deterministic, and
   mutually consistent;
7. a deliberately missing proof blocks a disposable test push before remote contact;
8. the recovery command restores the disposable ref to a push-eligible state;
9. the preservation ref keeps the target commit reachable after rewrite and aggressive
   garbage collection;
10. a fresh disposable repository reconstructs and verifies an exported registration
    bundle without relying on the working repository; and
11. read-only preflight confirms that the selected public remote supports immutable
    releases before the publication command is declared available.

## 12. Bootstrap and rollout

The design document and this evidentiary revision are committed before implementation
using the repository's existing schema-v1 practice as a one-time explicit bootstrap:

1. create the signed design commit with Windows Git;
2. create its hash file;
3. invoke pinned OTS through WSL manually;
4. stage only the hash and proof; and
5. create the signed `ots:` evidence commit with Windows Git.

Those bootstrap proofs timestamp the raw Git SHA-1 text and are therefore explicitly
schema-v1 evidence. They do not acquire schema-v2 properties retroactively.

Implementation then proceeds from a separately approved plan. The completed hooks are
installed before their own implementation commit, making that commit the first full
acceptance of the automatic schema-v2 lifecycle. The obsolete installer behavior is
replaced, not retained as a second competing path. The first live preregistration is a
separate, deliberately named acceptance event and is not required merely to install or
test the local hooks.

## 13. Documentation outcome

The contributor-facing documentation should explain only:

```text
Install once.
Commit normally.
If evidence creation was interrupted, run the repair command.
PENDING evidence may be pushed, but it must never be described as Bitcoin-anchored.
Publish a preregistration only with the explicit publication command and confirmation.
Publication is public and immutable; a later linked release records the Bitcoin anchor.
```

The diagnosis, dependency boundary, platform adapters, exemption policy, and failure
semantics remain available in this design and implementation documentation for future
instances that need to maintain the system, but they are not burdens imposed on every
contributor.

## 14. Primary references

- [OpenTimestamps](https://opentimestamps.org/) describes calendar attestations and
  Bitcoin timestamp verification.
- [OpenTimestamps Git integration](https://github.com/opentimestamps/opentimestamps-client/blob/master/doc/git-integration.md)
  describes pending versus Bitcoin-complete proofs and the interaction with signed Git
  history.
- [Git garbage collection](https://git-scm.com/docs/git-gc) defines reachability and
  pruning behavior relevant to preservation refs.
- [Git hash-function transition](https://git-scm.com/docs/hash-function-transition)
  documents the repository object's SHA-1 and SHA-256 security context.
- [Sigstore transparency logging](https://docs.sigstore.dev/logging/overview/) describes
  Rekor's public append-only log and provides the direct-transparency alternative.
- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
  defines locked tags and assets plus release attestations.
