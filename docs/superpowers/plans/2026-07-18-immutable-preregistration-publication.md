# Immutable Preregistration Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, confirmation-gated command that publishes a reconstructible preregistration as a GitHub immutable release and later publishes a linked Bitcoin-anchor release.

**Architecture:** A pure preparation layer builds and signs all assets locally; a narrow GitHub adapter performs capability checks and remote operations through argv-only `gh` calls. Preview and declined confirmation are write-free. After confirmation, a signed tag and draft release are created, assets are verified before publication, immutable release verification is required, and a local receipt records the public identity.

**Tech Stack:** Completed evidence core and hook workflow, Python 3.14+ stdlib, Git/GPG, Git bundles, GitHub CLI with `gh release verify` and `gh release verify-asset` capabilities, GitHub REST API version `2026-03-10`, pytest with a fake GitHub boundary.

## Global Constraints

- This layer is optional and never called by post-commit, pre-push, repair, upgrade, or installers.
- Publication is an explicit external act; no remote write occurs before a preview and exact confirmation naming repository, tag, commit, and irreversible release identity.
- The command refuses when the repository is private, immutable releases are disabled, required `gh` verification capabilities are absent, evidence is invalid, or the deciding-run statement is absent.
- The command never enables immutable releases, upgrades `gh`, authenticates, deletes a tag/release, or falls back to a mutable release automatically.
- Initial preregistration may be valid `PENDING`; it is labeled pending and never Bitcoin-anchored.
- Anchor publication requires `BITCOIN_ANCHORED` from the independent verifier and creates a new immutable release; the preregistration release is never edited.
- The claim is forgery/backdating/substitution resistance for the disclosed registration, not proof that undisclosed alternatives never existed.
- Ordinary tests use a fake GitHub adapter. A real immutable release is created only for an intentionally named scientific preregistration with execution-time approval.

---

## File Structure

- Create `tools/provenance/registration.py` — canonical statement, asset digests, signed tag, detached statement signature, and bundle.
- Create `tools/provenance/github_release.py` — read-only capability checks and remote draft/publish/verify operations.
- Create `tools/provenance/publication.py` — preview, confirmation, preregistration, anchor, and receipt state machine.
- Modify `tools/provenance/cli.py` — `publish-preregistration`, `publish-anchor`, and `publication-preflight`.
- Create `scripts/publish-preregistration.ps1` and `.sh` — explicit wrappers only.
- Create `scripts/publish-anchor.ps1` and `.sh` — explicit wrappers only.
- Create `tests/provenance/test_registration.py`, `test_github_release.py`, `test_publication.py`, and `test_bundle_verification.py`.
- Modify `docs/provenance.md` — publication protocol, failure recovery, claims, and non-claims.

---

### Task 1: Canonical signed registration assets and reconstructible bundle

**Files:**
- Create: `tools/provenance/registration.py`
- Test: `tests/provenance/test_registration.py`
- Test: `tests/provenance/test_bundle_verification.py`

**Interfaces:**
- Produces `prepare_registration(repo, target, name, protocol, deciding_run_unbegun, out_dir) -> RegistrationAssets`.
- Stable tag is `prereg/<name>`; anchor tag is `prereg/<name>/bitcoin-anchor`.
- Assets are `<name>.bundle`, `<target>.json`, `<target>.json.ots`, `policy.json`, every required `.asc` public key, `registration.json`, `registration.json.asc`, and `SHA256SUMS`.
- `registration.json` binds registration name, target/evidence commit OIDs, tag name and tag-object OID, protocol identifier, `deciding_run_unbegun: true`, proof state, core-asset SHA-256 values, exact technical claim, and non-claims. `SHA256SUMS` covers every asset except itself; `registration.json` covers all evidence assets except itself/signature/checksum to avoid circularity. The detached signature authenticates `registration.json`; the immutable release attestation covers the complete asset set.

- [ ] **Step 1: Write failing deterministic asset and fresh-bundle tests**

```python
def test_registration_requires_unbegun_deciding_run(valid_target, tmp_path):
    with pytest.raises(RegistrationRefusal, match="deciding run has not begun"):
        prepare_registration(valid_target.repo, valid_target.oid, "t1-stage2",
                             "docs/protocol.md", False, tmp_path)


def test_bundle_reconstructs_target_and_signatures(valid_target, tmp_path):
    assets = prepare_registration(valid_target.repo, valid_target.oid,
                                  "t1-stage2", "docs/protocol.md", True, tmp_path)
    fresh = init_fresh_repo(tmp_path / "fresh")
    fresh.fetch_bundle(assets.bundle, f"refs/tags/{assets.tag}")
    assert fresh.verify_tag(assets.tag)
    assert fresh.verify_commit(valid_target.oid)
    assert fresh.verify_commit(assets.evidence_commit)
    assert fresh.verify_evidence(valid_target.oid).state in {
        EvidenceState.PENDING, EvidenceState.BITCOIN_ANCHORED,
    }
```

- [ ] **Step 2: Run and observe missing registration module**

Run: `uv run pytest tests/provenance/test_registration.py tests/provenance/test_bundle_verification.py -v`

Expected: import fails for `tools.provenance.registration`.

- [ ] **Step 3: Implement preparation without external writes**

Validate `name` against `^[a-z0-9][a-z0-9._-]{0,79}$` and reject an existing local or remote identity supplied by the caller. Run the independent verifier first. Create a signed annotated tag locally with message containing registration name, target OID, evidence OID, proof state, and protocol identifier; it must not contain the later statement digest because that would be circular with the bundle containing the tag. Create the bundle with `git bundle create <path> refs/tags/<tag>` and validate it with `git bundle verify`. Record the resulting tag-object OID and bundle SHA-256 in `registration.json`. Export/copy only policy-selected public keys. Sign `registration.json` using `gpg --armor --detach-sign --local-user <full-fingerprint> --output registration.json.asc registration.json`. Write files with exclusive creation and refuse to overwrite any output directory entry.

- [ ] **Step 4: Run focused tests including spaces and hostile names**

Run: `uv run pytest tests/provenance/test_registration.py tests/provenance/test_bundle_verification.py -v`

Expected: all pass; bundle verification succeeds in a fresh repository and invalid names cannot alter paths or refs.

- [ ] **Step 5: Commit under installed hooks**

Commit message: `provenance: prepare signed preregistration bundles`.

Expected: automatic evidence commit follows and the working tree is clean.

---

### Task 2: Narrow GitHub immutable-release adapter

**Files:**
- Create: `tools/provenance/github_release.py`
- Test: `tests/provenance/test_github_release.py`

**Interfaces:**
- Produces `GitHubReleaseClient.preflight(remote) -> GitHubCapabilities`, `create_draft(...) -> DraftRelease`, `upload_assets(...)`, `publish(...) -> PublishedRelease`, and `verify_immutable(...) -> AttestationReceipt`.
- Read-only preflight resolves `OWNER/REPO` from `gh repo view --json nameWithOwner,isPrivate,url`, checks authentication with `gh auth status`, checks `GET repos/OWNER/REPO/immutable-releases` using API `2026-03-10`, and capability-probes `gh release verify --help` plus `gh release verify-asset --help`.
- Remote writes are individually typed so tests can prove none occur before confirmation.

- [ ] **Step 1: Write failing capability and no-fallback tests**

```python
@pytest.mark.parametrize("missing", [
    "authentication", "public-repository", "immutable-enabled",
    "release-verify", "release-verify-asset",
])
def test_preflight_refuses_each_missing_capability(fake_gh, missing):
    fake_gh.remove(missing)
    with pytest.raises(PublicationRefusal, match=missing):
        GitHubReleaseClient(fake_gh).preflight("origin")
    assert fake_gh.write_calls == []


def test_adapter_never_enables_immutability(fake_gh):
    fake_gh.immutable_enabled = False
    with pytest.raises(PublicationRefusal):
        GitHubReleaseClient(fake_gh).preflight("origin")
    assert not any(call.method == "PUT" for call in fake_gh.calls)
```

- [ ] **Step 2: Run and observe missing adapter failure**

Run: `uv run pytest tests/provenance/test_github_release.py -v`

Expected: import fails for `tools.provenance.github_release`.

- [ ] **Step 3: Implement argv-only `gh` operations**

Use this exact read-only API call shape:

```text
gh api --method GET -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2026-03-10" repos/OWNER/REPO/immutable-releases
```

Accept only HTTP success with JSON `{"enabled": true, ...}`. Draft creation uses `gh release create TAG --draft --verify-tag --title TITLE --notes-file FILE -R OWNER/REPO` after the signed tag has been pushed. Query the new draft and require an empty asset list, then upload each asset explicitly with `gh release upload TAG PATH -R OWNER/REPO`; the command's default refusal to overwrite is preserved by never passing `--clobber`. Publication uses `gh release edit TAG --draft=false`; verification requires both `gh release verify TAG -R OWNER/REPO` and `gh release verify-asset TAG LOCAL_PATH -R OWNER/REPO` for every asset. Parse only JSON-producing commands for identities and URLs.

- [ ] **Step 4: Run adapter tests and read-only live preflight**

Run: `uv run pytest tests/provenance/test_github_release.py -v`

Run: `uv run python -m tools.provenance.cli publication-preflight --remote origin --json`

Expected: deterministic tests pass. On the current host, preflight refuses without writes until `gh release verify` and `verify-asset` are available; it prints the missing capabilities and does not upgrade `gh`.

- [ ] **Step 5: Commit under installed hooks**

Commit message: `provenance: add immutable GitHub release boundary`.

---

### Task 3: Confirmation-gated preregistration publication state machine

**Files:**
- Create: `tools/provenance/publication.py`
- Modify: `tools/provenance/cli.py`
- Create: `scripts/publish-preregistration.ps1`
- Create: `scripts/publish-preregistration.sh`
- Test: `tests/provenance/test_publication.py`

**Interfaces:**
- CLI: `publish-preregistration --commit OID --name NAME --protocol PATH --remote REMOTE [--yes]`.
- `--yes` is accepted only when `QUANTUMOS_APPROVE_IRREVERSIBLE_PUBLICATION` exactly equals the computed release identity shown in preview; it is not a generic noninteractive bypass.
- Receipt path is `provenance/receipts/<name>-preregistration.json`; receipt creation is local after remote verification and requires a later ordinary signed commit.

- [ ] **Step 1: Write failing preview, decline, and ordered-write tests**

```python
def test_preview_and_decline_make_no_external_write(publication_fixture):
    preview = publication_fixture.preview()
    assert preview.names_remote_tag_commit_assets_and_nonclaims()
    publication_fixture.answer("no")
    assert publication_fixture.github.write_calls == []
    assert publication_fixture.git.push_calls == []


def test_confirmed_publication_verifies_before_receipt(publication_fixture):
    publication_fixture.answer_exact_identity()
    result = publication_fixture.publish()
    assert publication_fixture.events == [
        "push-signed-tag", "create-draft", "upload-assets",
        "verify-draft-assets", "publish", "verify-immutable",
        "verify-release-assets", "write-receipt",
    ]
    assert result.receipt["proof_state"] == "PENDING"
```

- [ ] **Step 2: Run and observe missing publication module**

Run: `uv run pytest tests/provenance/test_publication.py -v`

Expected: import fails for `tools.provenance.publication`.

- [ ] **Step 3: Implement explicit state transitions and failure receipts**

States are `PREPARED`, `TAG_PUSHED`, `DRAFT_CREATED`, `ASSETS_VERIFIED`, `PUBLISHED`, `IMMUTABLE_VERIFIED`, `RECEIPT_WRITTEN`. Before confirmation only preparation and read-only preflight are allowed. After confirmation, persist a local recovery journal after each state. If failure occurs after a remote write, preserve local assets/journal, print the exact remote object, and stop; never delete or automatically retry an irreversible step. A rerun reads the journal, verifies remote state, and resumes only the next safe state after repeating the exact confirmation.

The release notes must repeat: proof state; target/evidence OIDs; protocol; declaration that the deciding run had not begun; OTS upper-bound semantics; asserted Git dates; public-key identity limitation; and no-exhaustiveness claim.

- [ ] **Step 4: Run publication tests with every boundary interrupted**

Run: `uv run pytest tests/provenance/test_publication.py -v`

Expected: all pass; failure injection at each state never produces a false published receipt and never calls delete.

- [ ] **Step 5: Commit under installed hooks**

Commit message: `provenance: add confirmed preregistration publication`.

---

### Task 4: Linked Bitcoin-anchor publication

**Files:**
- Modify: `tools/provenance/publication.py`
- Modify: `tools/provenance/cli.py`
- Create: `scripts/publish-anchor.ps1`
- Create: `scripts/publish-anchor.sh`
- Test: `tests/provenance/test_anchor_publication.py`

**Interfaces:**
- CLI: `publish-anchor --name NAME --remote REMOTE [--yes]`.
- Reads the verified preregistration receipt, requires current evidence state `BITCOIN_ANCHORED`, prepares a new signed statement linking original release URL/tag/attestation to Bitcoin block height/time, and publishes tag `prereg/<name>/bitcoin-anchor` as a separate immutable release.

- [ ] **Step 1: Write failing pending-refusal and linkage tests**

```python
def test_anchor_refuses_pending_evidence(anchor_fixture):
    anchor_fixture.verifier_state = EvidenceState.PENDING
    with pytest.raises(PublicationRefusal, match="BITCOIN_ANCHORED"):
        anchor_fixture.preview()
    assert anchor_fixture.github.write_calls == []


def test_anchor_statement_links_original_release(anchor_fixture):
    anchor_fixture.verifier_state = EvidenceState.BITCOIN_ANCHORED
    statement = anchor_fixture.prepare().statement
    assert statement["original_release_url"] == anchor_fixture.receipt["release_url"]
    assert statement["original_attestation"] == anchor_fixture.receipt["attestation"]
    assert statement["bitcoin"]["height"] > 0
```

- [ ] **Step 2: Run and observe missing anchor command failure**

Run: `uv run pytest tests/provenance/test_anchor_publication.py -v`

Expected: command/function import fails.

- [ ] **Step 3: Implement anchor preparation through the same state machine**

Reuse the publication states and GitHub adapter, but require a distinct tag/release identity and include completed `.ots` proof plus both signed statements and the original receipt. Never edit, upload to, retag, or delete the preregistration release.

- [ ] **Step 4: Run focused and complete publication suites**

Run: `uv run pytest tests/provenance/test_anchor_publication.py tests/provenance/test_publication.py tests/provenance/test_bundle_verification.py -v`

Expected: all pass.

- [ ] **Step 5: Commit under installed hooks**

Commit message: `provenance: add linked Bitcoin anchor publication`.

---

### Task 5: Publication documentation and non-mutating acceptance

**Files:**
- Modify: `docs/provenance.md`
- Modify: `README.md`
- Test: `tests/provenance/test_publication_acceptance.py`

**Interfaces:**
- Acceptance builds a complete preregistration and anchor against a fake GitHub server, downloads assets into a fresh repository, and independently verifies both identities.
- Live acceptance stops after read-only preflight unless a user supplies a real preregistration name, protocol, commit, and execution-time confirmation.

- [ ] **Step 1: Add the fake-remote end-to-end acceptance test**

```python
def test_fresh_consumer_verifies_both_immutable_records(fake_github, target):
    prereg = publish_to_fake(fake_github, target, state=EvidenceState.PENDING)
    anchor = publish_anchor_to_fake(fake_github, prereg,
                                    state=EvidenceState.BITCOIN_ANCHORED)
    consumer = download_into_fresh_repo(fake_github, prereg, anchor)
    assert consumer.verify_preregistration().public_identity == prereg.identity
    assert consumer.verify_anchor().links_to == prereg.identity
    assert consumer.claims.exhaustiveness is False
```

- [ ] **Step 2: Run complete deterministic publication acceptance**

Run: `uv run pytest tests/provenance/test_publication_acceptance.py -v`

Expected: pass without network access.

- [ ] **Step 3: Document operator and independent-consumer procedures**

Document exact preview, confirmation, recovery-journal, preregistration, anchor, bundle fetch, signature verification, asset verification, and OTS verification commands. State that the current host must update GitHub CLI before publication preflight can succeed, but the repository tooling never performs that update.

- [ ] **Step 4: Run all tests and read-only live preflight**

Run: `uv run pytest`

Run: `uv run python -m tools.provenance.cli publication-preflight --remote origin --json`

Expected: all tests pass. Live preflight either reports every capability present or refuses with exact missing capabilities and zero writes.

- [ ] **Step 5: Commit under installed hooks; do not publish**

Commit message: `docs: document immutable preregistration verification`.

Expected: automatic evidence commit follows; no tag is pushed and no release is created.

---

## Self-Review

- Spec coverage: explicit preview/confirmation, public immutable release, bundle, signed statement, policy/keys, asset hashes, draft ordering, attestation verification, receipt, pending label, separate anchor, and fresh reconstruction are covered.
- Enabling posture: no automatic publication, generic `--yes` bypass, repository-setting mutation, CLI upgrade, or false exhaustiveness claim exists.
- Failure safety: remote partial state is journaled and reported; deletion is never an automated recovery action.
- Live irreversibility: tests stop at read-only preflight; the first live release requires a genuine scientific preregistration decision from the user.
- Interface consistency: publication consumes evidence-core `VerificationReport` and workflow artifacts without redefining their meanings.
