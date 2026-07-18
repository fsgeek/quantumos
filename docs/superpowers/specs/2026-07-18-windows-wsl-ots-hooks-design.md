# Cross-platform signed OpenTimestamps hook design

**Date:** 2026-07-18
**Status:** APPROVED DESIGN — implementation not begun
**Scope:** repository contribution mechanics only; no simulator or paper-content changes

## 1. Purpose

Make the repository's signed OpenTimestamps workflow automatic, auditable, and easy
for future human and AI contributors to use from the Windows host while preserving a
native Linux path.

After one installation command, the healthy path must require no timestamp-specific
knowledge: a contributor makes one ordinary signed commit, and the repository creates
and signs its timestamp-evidence commit automatically. If timestamping is interrupted,
the contributor receives one explicit recovery command. Work is never destroyed to
repair provenance, and incomplete provenance cannot be pushed accidentally.

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

## 3. Goals and non-goals

### 3.1 Goals

- Preserve Windows Git as the sole authority for repository state.
- Preserve Windows GPG as the signer of substantive and OTS evidence commits.
- Use WSL only to execute a pinned OTS client against an explicitly named hash file.
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
- Make installation and recovery idempotent.

### 3.2 Non-goals

- Patch installed `site-packages` or vendor cryptographic loader code.
- Make WSL the project development environment.
- Add Git LFS to a repository that does not use it.
- Delete, rewrite, or manufacture historical timestamps.
- Make a `post-commit` failure undo a substantive commit; Git does not permit that.
- Hide a failure merely to preserve an apparently clean working tree.

## 4. Authority boundary

### 4.1 Windows Git owns

- commit creation and history;
- staging timestamp artifacts;
- creation of the generated `ots:` commit;
- GPG signing of both commit kinds;
- push validation and execution.

### 4.2 WSL owns only

- execution of pinned `opentimestamps-client` 0.7.2;
- reading one hash file in the mounted Windows checkout;
- writing or upgrading that file's `.ots` proof.

WSL must not run Git, stage files, create commits, sign commits, edit project content,
or execute the simulator test suite as part of this workflow.

### 4.3 Linux hosts

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

The hook calls one repository-owned adapter with a target hash-file path. The adapter
selects:

- Windows: `wsl.exe`, the discovered distribution, and pinned OTS through WSL `uvx`;
- Linux: the project-native `.venv/bin/ots`.

The adapter returns success only when the expected `.ots` artifact exists. It preserves
any partial artifact on failure and emits a diagnostic naming the failed boundary.

### 5.4 Repair command

`scripts/repair-timestamps.ps1` is the only recovery command a Windows contributor must
remember. It finds unpublished, non-exempt, non-OTS commits that lack committed evidence
or have uncommitted evidence, then completes the same stamp-stage-sign sequence in
history order. It is safe to run repeatedly. A Linux wrapper exposes the same behavior.

### 5.5 Timestamp policy

A tracked policy file defines:

- the evidence path convention `timestamps/<full-commit-hash>.ots`;
- the generated commit subject convention `ots: stamp <full-commit-hash>`;
- the upgrade subject convention `ots: upgrade <count> timestamp(s)`;
- the permitted tree shape for stamp and upgrade maintenance commits;
- the exact historical exemptions in section 9;
- the rule that all other substantive commits introduced by a push require evidence.

The policy is data, not a hidden list embedded in hook code.

## 6. Normal commit lifecycle

1. Windows Git creates and signs the substantive commit.
2. `post-commit` exits immediately when an explicit re-entry environment marker is set.
3. Otherwise it records the new full commit hash in `timestamps/<hash>`.
4. The executor invokes OTS in the appropriate environment against that file.
5. The hook verifies that `timestamps/<hash>.ots` now exists.
6. Windows Git stages only the hash file and its proof.
7. Windows Git creates an explicitly signed `ots: stamp <hash>` commit while setting
   the re-entry marker.
8. The generated commit's `post-commit` invocation observes the marker and exits.
9. The healthy outcome is a clean working tree with the substantive commit immediately
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

An OTS stamp commit qualifies as maintenance only when its subject names its first
parent's full hash and its diff introduces exactly that hash file and proof under
`timestamps/`. An OTS upgrade commit qualifies only when its subject count matches its
diff and every changed path is an existing `timestamps/*.ots` proof. A commit that
merely begins its subject with `ots:` but changes any other path is substantive and
requires its own timestamp.

## 7. Push invariant

`post-commit` is an automatic attempt, not an enforcement point: its exit status cannot
undo the commit that triggered it. `pre-push` is the enforcement point.

For each ref update received on standard input, `pre-push` enumerates commits newly
introduced to that remote ref. For every commit that is neither a structurally valid
OTS maintenance commit nor an exact historical exemption, it verifies that the pushed
tip contains the corresponding `timestamps/<hash>.ots` artifact. A missing artifact
aborts the push and prints:

- every missing commit hash and subject;
- the fact that no remote update occurred; and
- the single repair command.

The validation hook never mutates history, invokes OTS, or attempts repair during a
push. Deletion updates contain no new commits and require no timestamp action. New refs
still apply the exact exemption policy, so branching from old history does not exempt
new work.

## 8. Failure and recovery contract

The governing rule is: **never destroy work to repair provenance, and never submit work
whose provenance is incomplete.**

- If substantive signing fails, Git creates no commit and timestamping does not begin.
- If timestamping fails, the signed substantive commit remains intact. The hook emits
  `OTS PENDING` prominently and preserves the hash file and any partial proof.
- If evidence-commit signing fails, the evidence files remain available for recovery;
  they are not committed unsigned.
- Offline commits are permitted. Publication is blocked until evidence is repaired.
- Repair discovers state from Git history, the remote-tracking boundary, the policy,
  and the evidence tree; it does not depend solely on terminal output or an ephemeral
  marker.
- Amend and rebase create new commit hashes and therefore new timestamp obligations.
  Old proofs remain historical evidence and are never deleted automatically.
- A proof that already exists is validated or committed rather than overwritten.
- Failure messages identify whether discovery, path mapping, WSL startup, OTS startup,
  calendar submission, artifact verification, staging, or GPG signing failed.

## 9. Historical boundary

At design time the repository contains 201 commits: 95 substantive commits and 106
`ots:` commits. Ninety substantive commits have filesystem OTS proofs. The following
five earliest substantive commits predate the established timestamp practice and are
the only legacy exemptions:

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
- Hooks stage only the named hash file and proof, never broad working-tree changes.
- Existing proofs are never silently replaced.
- Hook installation is repository-local and does not modify global Git configuration.
- An unrelated existing `core.hooksPath` is a human-visible conflict, not an overwrite.
- Bypassing local hooks remains technically possible in Git, so remote signed-submission
  policy remains an independent defense. The local workflow reduces accidents; it does
  not claim to replace repository governance.

## 11. Test design

### 11.1 Deterministic temporary-repository tests

Tests use disposable Git repositories and controllable fake executor/signing boundaries
where appropriate. They cover:

- one substantive commit produces exactly one evidence commit;
- recursion cannot occur;
- stamp and upgrade maintenance commits are recognized only when both subject and tree
  shape satisfy policy;
- an `ots:`-prefixed commit that changes non-timestamp content remains substantive;
- paths containing spaces;
- idempotent installation and repair;
- unrelated hook-path configuration is preserved;
- OTS, WSL, network, artifact, staging, and signing failure injection;
- preservation of the substantive commit and partial artifacts on every failure;
- pre-push rejection before remote contact when evidence is absent;
- successful push validation after repair;
- amend and rebase obligations;
- new branches rooted in old history;
- exact handling of the five historical exemptions; and
- refusal of any undeclared exemption.

### 11.2 Host integration tests

Outside the QuantumOS repository history, a disposable fixture verifies:

- real pinned OTS startup and stamping through Ubuntu WSL;
- real Windows Git/GPG signed commits and signature verification;
- the complete two-commit lifecycle;
- simulated interruption followed by the public repair command; and
- the Linux executor path inside WSL where practical.

External calendar interaction uses only a disposable hash file. No QuantumOS content or
signing key crosses into WSL.

### 11.3 Repository acceptance

Acceptance requires:

1. both installers are idempotent;
2. the historical audit reports exactly the five declared exemptions and no unexplained
   gaps;
3. the complete QuantumOS test suite passes;
4. a successful real commit cycle leaves a clean working tree;
5. both the substantive and generated evidence commits verify as signed;
6. the target proof verifies as present and committed;
7. a deliberately missing proof blocks a disposable test push before remote contact;
   and
8. the recovery command restores the disposable ref to a push-eligible state.

## 12. Bootstrap and rollout

The design document is committed before implementation using a one-time explicit
bootstrap:

1. create the signed design commit with Windows Git;
2. create its hash file;
3. invoke pinned OTS through WSL manually;
4. stage only the hash and proof; and
5. create the signed `ots:` evidence commit with Windows Git.

Implementation then proceeds from a separately approved plan. The completed hooks are
installed before their own implementation commit, making that commit the first full
acceptance of the automatic lifecycle. The obsolete installer behavior is replaced,
not retained as a second competing path.

## 13. Documentation outcome

The contributor-facing documentation should explain only:

```text
Install once.
Commit normally.
If you see OTS PENDING, run the repair command.
Push is blocked until provenance is complete.
```

The diagnosis, dependency boundary, platform adapters, exemption policy, and failure
semantics remain available in this design and implementation documentation for future
instances that need to maintain the system, but they are not burdens imposed on every
contributor.
