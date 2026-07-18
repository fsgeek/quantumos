# OTS Evidence Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic schema-v2 evidence creation, policy, history classification, and independent verification without installing hooks or publishing externally.

**Architecture:** A stdlib-only `tools.provenance` package reads canonical Git objects, creates a canonical JSON manifest, and verifies schema-v1 and schema-v2 evidence. Git, GPG, and OTS are process boundaries behind small injectable runners so temporary repositories and fakes cover deterministic behavior. This stage is independently useful through an explicit CLI and does not enforce contributor behavior.

**Tech Stack:** Python 3.14+, standard library, Git 2.45+, GnuPG, OpenTimestamps client 0.7.2, pytest via `uv run pytest`.

## Global Constraints

- This is an enabling mechanism, not a governance or enforcement authority.
- Windows Git owns repository state; Windows GPG owns signatures; WSL receives only an explicitly named evidence artifact.
- New evidence is schema v2; existing raw-hash evidence remains schema v1 and is never rewritten.
- Canonical JSON is UTF-8, `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=True`, with exactly one trailing LF.
- The OTS client is pinned exactly to `opentimestamps-client==0.7.2`; installed cryptographic packages are never patched.
- Commits are signed with full fingerprint `1D7C4A68252F6EC1ACD2FC8E934778A0EB5EABB1`; verification never equates repository possession of that public key with human identity.
- The five schema-v1 exemptions are exactly the hashes in design section 9; no subject, date, or ancestry pattern creates another exemption.
- TDD per task: failing test, observed failure, minimal implementation, passing focused tests, full provenance tests, signed commit.
- Before hook installation, create schema-v2 evidence for each substantive implementation commit explicitly and commit it separately as `ots: stamp <full-hash>`.

---

## File Structure

- Create `provenance/policy.json` — versioned evidence paths, algorithms, key records, and exact legacy exemptions.
- Create `provenance/keys/tony-mason-1D7C4A68.asc` — armored public verification key only.
- Create `tools/__init__.py` and `tools/provenance/__init__.py` — importable tooling packages.
- Create `tools/provenance/model.py` — immutable result/status records and exit codes.
- Create `tools/provenance/process.py` — injectable subprocess runner with byte-preserving output.
- Create `tools/provenance/git_objects.py` — canonical commit bytes, raw tree enumeration, digests, signatures, refs.
- Create `tools/provenance/policy.py` — strict policy loader and activation/key lookup.
- Create `tools/provenance/manifest.py` — schema-v2 construction and canonical serialization.
- Create `tools/provenance/classify.py` — maintenance-commit classification and history audit.
- Create `tools/provenance/verify.py` — schema-v1/v2 verification and honest proof states.
- Create `tools/provenance/cli.py` — `create`, `verify`, and `audit` entry points.
- Create `tests/provenance/` — temporary-repository, object, manifest, classification, verifier, and CLI tests.

---

### Task 1: Policy, Git object binding, and manifest creator

**Files:**
- Create: `provenance/policy.json`
- Create: `provenance/keys/tony-mason-1D7C4A68.asc`
- Create: `tools/__init__.py`
- Create: `tools/provenance/__init__.py`
- Create: `tools/provenance/model.py`
- Create: `tools/provenance/process.py`
- Create: `tools/provenance/git_objects.py`
- Create: `tools/provenance/policy.py`
- Create: `tools/provenance/manifest.py`
- Create: `tools/provenance/cli.py`
- Test: `tests/provenance/conftest.py`
- Test: `tests/provenance/test_manifest.py`
- Test: `tests/provenance/test_policy.py`

**Interfaces:**
- Produces: `Policy.load(repo: Path) -> Policy`, `GitRepository(repo: Path, runner: Runner)`, `build_manifest(repo, commit, policy) -> dict[str, object]`, `canonical_json(value) -> bytes`, and CLI `python -m tools.provenance.cli create COMMIT`.
- Produces evidence path `timestamps/<full-commit-oid>.json` and preservation ref `refs/quantumos/timestamps/<full-commit-oid>`.
- Tree digest input is `b"QOS-TREE-V1\0"` followed by path-sorted framed records. Each frame is `u32(mode_len)|mode|u32(type_len)|type|u64(path_len)|path|u32(value_len)|value`; integer fields are unsigned big-endian. Blob `value` is the 32 raw bytes of SHA-256(blob bytes); gitlink `value` is the ASCII object identifier. No checkout bytes participate.

- [ ] **Step 1: Write failing policy and manifest tests**

```python
def test_manifest_is_canonical_and_binds_commit_tree_and_policy(repo_with_signed_commit):
    repo, oid = repo_with_signed_commit
    policy = Policy.load(repo)
    first = build_manifest(repo, oid, policy)
    second = build_manifest(repo, oid, policy)
    encoded = canonical_json(first)
    assert encoded == canonical_json(second)
    assert encoded.endswith(b"\n") and not encoded.endswith(b"\n\n")
    assert first["schema"] == "quantumos-ots-evidence-v2"
    assert first["git"]["commit_oid"] == oid
    assert len(bytes.fromhex(first["git"]["commit_object_sha256"])) == 32
    assert len(bytes.fromhex(first["git"]["complete_tree_sha256"])) == 32
    assert first["policy"]["sha256"] == hashlib.sha256(
        (repo / "provenance/policy.json").read_bytes()
    ).hexdigest()


def test_tree_digest_distinguishes_content_mode_symlink_and_gitlink(tmp_path):
    # Build five commits in a fixture repository: base, changed blob, executable-bit
    # change, symlink target change, and gitlink OID change.
    digests = fixture_tree_digests(tmp_path)
    assert len(set(digests.values())) == len(digests)


def test_policy_has_only_the_five_declared_exemptions(repo_root):
    policy = Policy.load(repo_root)
    assert policy.legacy_exemptions == frozenset({
        "8cea0f3ee5e8dd12fb8f6e5754bd5e849be4688f",
        "c2b88885ddbb00ed65b23eaf3d32021c7bccc14b",
        "9a45cb17fd86f3331fd4fbcf966be207e5177759",
        "ea7b434e11cad5755b2063f9071311ecddeafd7b",
        "bd45e58e6826db714ce6e4728f5784fbbfc85c82",
    })
```

- [ ] **Step 2: Run tests and observe the missing-package failure**

Run: `uv run pytest tests/provenance/test_policy.py tests/provenance/test_manifest.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'tools.provenance'`.

- [ ] **Step 3: Add the exact policy and public key**

`provenance/policy.json` must contain this complete structure (the exported armored key is generated with the command below, never hand-authored):

```json
{
  "schema": "quantumos-ots-policy-v1",
  "evidence": {
    "legacy_target": "timestamps/{commit}",
    "legacy_proof": "timestamps/{commit}.ots",
    "v2_manifest": "timestamps/{commit}.json",
    "v2_proof": "timestamps/{commit}.json.ots"
  },
  "algorithms": {
    "commit": "git-canonical-object-sha256-v1",
    "tree": "quantumos-flat-tree-sha256-v1",
    "json": "canonical-json-lf-v1"
  },
  "ots_client": "opentimestamps-client==0.7.2",
  "preservation_ref": "refs/quantumos/timestamps/{commit}",
  "keys": [{
    "fingerprint": "1D7C4A68252F6EC1ACD2FC8E934778A0EB5EABB1",
    "public_key": "provenance/keys/tony-mason-1D7C4A68.asc",
    "active_from": "8cea0f3ee5e8dd12fb8f6e5754bd5e849be4688f"
  }],
  "legacy_exemptions": [
    "8cea0f3ee5e8dd12fb8f6e5754bd5e849be4688f",
    "c2b88885ddbb00ed65b23eaf3d32021c7bccc14b",
    "9a45cb17fd86f3331fd4fbcf966be207e5177759",
    "ea7b434e11cad5755b2063f9071311ecddeafd7b",
    "bd45e58e6826db714ce6e4728f5784fbbfc85c82"
  ]
}
```

Run: `& 'C:\Program Files\GnuPG\bin\gpg.exe' --armor --output provenance/keys/tony-mason-1D7C4A68.asc --export 1D7C4A68252F6EC1ACD2FC8E934778A0EB5EABB1`

Expected: `gpg --show-keys --with-colons` reports the exact full fingerprint and no private-key packet is present.

- [ ] **Step 4: Implement the deterministic creator**

Use these exact records and constants in `model.py` and `manifest.py`:

```python
class EvidenceState(StrEnum):
    INVALID = "INVALID"
    PENDING = "PENDING"
    BITCOIN_ANCHORED = "BITCOIN_ANCHORED"

EXIT_ANCHORED = 0
EXIT_PENDING = 10
EXIT_INVALID = 20


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("utf-8")


def git_object_bytes(kind: str, body: bytes) -> bytes:
    return kind.encode("ascii") + b" " + str(len(body)).encode("ascii") + b"\0" + body


def frame(mode: bytes, kind: bytes, path: bytes, value: bytes) -> bytes:
    return (len(mode).to_bytes(4, "big") + mode +
            len(kind).to_bytes(4, "big") + kind +
            len(path).to_bytes(8, "big") + path +
            len(value).to_bytes(4, "big") + value)
```

`GitRepository` must use `git cat-file commit`, `git ls-tree -rz --full-tree -r`, `git cat-file blob`, `git verify-commit --raw`, and `git update-ref`. It must pass argument arrays without a shell, preserve byte output, reject abbreviated OIDs, parse `[GNUPG:] VALIDSIG <fingerprint>`, and refuse a signature whose fingerprint is not active in the loaded policy. `build_manifest` writes asserted author/committer timestamps from `%aI` and `%cI`, algorithm identifiers from policy, commit object SHA-256, complete-tree SHA-256, policy SHA-256, and implementation version `1`.

- [ ] **Step 5: Run focused and full provenance tests**

Run: `uv run pytest tests/provenance/test_policy.py tests/provenance/test_manifest.py -v`

Expected: all tests pass, including filenames with spaces, non-ASCII names represented as raw Git path bytes, empty blobs, executable modes, symlinks, and gitlinks.

- [ ] **Step 6: Commit and explicitly timestamp the substantive commit**

```powershell
git add provenance tools tests/provenance
git commit -S -m "provenance: add deterministic schema-v2 evidence core"
$commit = git rev-parse HEAD
uv run python -m tools.provenance.cli create $commit
wsl.exe -d Ubuntu -- /home/tony/.local/bin/uvx --from opentimestamps-client==0.7.2 ots stamp "/mnt/c/Users/TonyMason/source/repos/quantumos/timestamps/$commit.json"
git add "timestamps/$commit.json" "timestamps/$commit.json.ots"
git commit -S -m "ots: stamp $commit"
```

Expected: both commits have good signatures; `ots info` labels the new proof pending until Bitcoin completion.

---

### Task 2: Structural maintenance classification and historical audit

**Files:**
- Create: `tools/provenance/classify.py`
- Modify: `tools/provenance/cli.py`
- Test: `tests/provenance/test_classify.py`
- Test: `tests/provenance/test_audit.py`

**Interfaces:**
- Produces `classify_commit(repo, oid, policy) -> CommitKind` where kinds are `SUBSTANTIVE`, `STAMP`, `UPGRADE`, `LEGACY_EXEMPTION`.
- Produces `audit_history(repo, tip, policy) -> AuditReport` and CLI `audit [TIP] --json`.
- A stamp is maintenance only when the exact subject names its first parent and its diff adds exactly the policy-selected manifest and proof for that parent. An upgrade is maintenance only when its exact count matches changed existing recognized `.ots` files. Merge commits cannot be maintenance.

- [ ] **Step 1: Write failing adversarial classification tests**

```python
@pytest.mark.parametrize("subject,paths,expected", [
    ("ots: stamp " + H, {f"timestamps/{H}.json", f"timestamps/{H}.json.ots"}, "STAMP"),
    ("ots: stamp " + H, {"qsim/core/engine.py"}, "SUBSTANTIVE"),
    ("ots: harmless", {f"timestamps/{H}.json.ots"}, "SUBSTANTIVE"),
    ("ots: upgrade 2 timestamp(s)", {"timestamps/a.ots"}, "SUBSTANTIVE"),
])
def test_subject_is_never_sufficient(fixture_repo, subject, paths, expected):
    oid = fixture_repo.commit_with_diff(subject, paths)
    assert classify_commit(fixture_repo.git, oid, fixture_repo.policy).value == expected
```

Also assert the live repository audit returns exactly five exemptions and no unexplained gaps when evaluated at the plan's starting commit; derive all non-exempt counts from Git rather than freezing another count in the test.

- [ ] **Step 2: Run and observe import failure**

Run: `uv run pytest tests/provenance/test_classify.py tests/provenance/test_audit.py -v`

Expected: import fails for `tools.provenance.classify`.

- [ ] **Step 3: Implement exact-subject plus tree-shape classification**

Parse changes with `git diff-tree --root --no-commit-id --name-status -z -r <oid>`. Reject copies, renames, merges, malformed UTF-8 policy paths, abbreviated hashes, count mismatches, overwritten stamp artifacts, and any additional path. `audit_history` walks `git rev-list --reverse <tip>`, indexes evidence paths visible at the tip, and emits per-commit reason codes rather than booleans.

- [ ] **Step 4: Run focused tests and audit the live history**

Run: `uv run pytest tests/provenance/test_classify.py tests/provenance/test_audit.py -v`

Run: `uv run python -m tools.provenance.cli audit HEAD --json`

Expected: tests pass; audit reports exactly the five declared exemptions and no additional exemption.

- [ ] **Step 5: Commit, create schema-v2 evidence, and commit that evidence**

Use the Task 1 Step 6 sequence with message `provenance: classify evidence history structurally`.

---

### Task 3: Independent schema-v1/schema-v2 verifier

**Files:**
- Create: `tools/provenance/verify.py`
- Modify: `tools/provenance/cli.py`
- Test: `tests/provenance/test_verify.py`
- Test: `tests/provenance/test_cli.py`

**Interfaces:**
- Produces `verify_commit(repo, oid, policy, ots_runner) -> VerificationReport`.
- CLI `verify COMMIT [--json]` exits `0` for `BITCOIN_ANCHORED`, `10` for valid `PENDING`, and `20` for `INVALID` or incomplete evidence.
- `VerificationReport` always includes target OID, schema, state, target/evidence/upgrade signature fingerprints, asserted Git dates, proof target SHA-256, Bitcoin block height/time when anchored, and trust assumptions.

- [ ] **Step 1: Write failing state and tamper tests**

```python
def test_pending_is_valid_but_not_anchored(v2_fixture, fake_ots_pending):
    report = verify_commit(v2_fixture.repo, v2_fixture.oid,
                           v2_fixture.policy, fake_ots_pending)
    assert report.state is EvidenceState.PENDING
    assert report.bitcoin is None
    assert report.asserted_committer_time.endswith("+00:00")


@pytest.mark.parametrize("mutation", [
    "manifest_byte", "commit_object", "tree_blob", "mode", "policy",
    "target_signature", "evidence_signature", "proof_target", "fingerprint",
])
def test_any_bound_input_mutation_is_invalid(v2_fixture, mutation):
    v2_fixture.mutate(mutation)
    assert v2_fixture.verify().state is EvidenceState.INVALID
```

Add schema-v1 tests proving only raw target/proof binding and signature availability are reported; schema-v1 must never claim the schema-v2 complete-tree binding.

- [ ] **Step 2: Run and observe missing verifier failure**

Run: `uv run pytest tests/provenance/test_verify.py tests/provenance/test_cli.py -v`

Expected: import fails for `tools.provenance.verify`.

- [ ] **Step 3: Implement layered verification without state collapse**

Verification order is: resolve full OID; locate schema; load exact policy bytes and compare SHA-256; verify target signature; locate structurally valid stamp and applicable upgrade commits; verify their signatures; recompute commit/tree hashes; verify proof binds exact target bytes; parse `ots info` into pending or Bitcoin-complete; when complete run `ots verify`; assemble claims and non-claims. Never contact a calendar merely to turn malformed evidence into pending.

The human output must use `asserted author time` and `asserted committer time`, and must print `Bitcoin upper bound` only for an anchored proof. JSON uses the same field names and values.

- [ ] **Step 4: Run focused tests and verify one live schema-v1 proof**

Run: `uv run pytest tests/provenance/test_verify.py tests/provenance/test_cli.py -v`

Run: `uv run python -m tools.provenance.cli verify 2ebe8dc054876b5831b579cf57e54477b62466f9 --json`

Expected: focused tests pass; live verification returns exit `10` and state `PENDING` until upgraded.

- [ ] **Step 5: Commit, create schema-v2 evidence, and commit that evidence**

Use the Task 1 Step 6 sequence with message `provenance: verify signed OTS evidence independently`.

---

### Task 4: Core documentation and acceptance gate

**Files:**
- Create: `docs/provenance.md`
- Test: `tests/provenance/test_repository_acceptance.py`
- Modify: `README.md`

**Interfaces:**
- Documents the three states, exact technical claim, non-claims, independent commands, public-key trust limitation, schema compatibility, and key-rotation retention rule.
- Acceptance test runs creator and verifier in a disposable signed repository, then copies only the Git objects, policy, public key, manifest, and proof into a fresh repository and repeats verification.

- [ ] **Step 1: Write the failing fresh-repository acceptance test**

```python
def test_fresh_repository_can_recompute_all_local_bindings(exported_fixture):
    fresh = exported_fixture.clone_without_source_worktree()
    report = fresh.verify_with_fake_pending_ots()
    assert report.state is EvidenceState.PENDING
    assert report.target_signature.valid
    assert report.evidence_signature.valid
    assert report.commit_object_sha256_matches
    assert report.complete_tree_sha256_matches
    assert report.policy_sha256_matches
```

- [ ] **Step 2: Run and confirm the fixture exposes any missing export dependency**

Run: `uv run pytest tests/provenance/test_repository_acceptance.py -v`

Expected: failure names an exact missing object, policy, key, or verification field; no network is used.

- [ ] **Step 3: Complete documentation and the minimal export fixture support**

`docs/provenance.md` must show these exact user-facing commands:

```text
uv run python -m tools.provenance.cli create <commit>
uv run python -m tools.provenance.cli verify <commit>
uv run python -m tools.provenance.cli audit HEAD
```

It must state: OTS proves an upper bound; Git dates are signed assertions; `PENDING` is not anchored; existence is not exhaustiveness; local refs are preservation rather than publication; intentional hook bypass remains possible.

- [ ] **Step 4: Run the provenance suite and the existing repository suite**

Run: `uv run pytest tests/provenance -v`

Run: `uv run pytest`

Expected: all tests pass.

- [ ] **Step 5: Commit, create schema-v2 evidence, and commit that evidence**

Use the Task 1 Step 6 sequence with message `docs: document independent provenance verification`.

---

## Self-Review

- Spec coverage: schema v1/v2, canonical object/tree binding, policy/key retention, structural classification, three proof states, verifier output, exact exemptions, and fresh-repository verification all have tasks.
- Deliberately deferred to the next plan: WSL/native OTS execution selection, hooks, repair, upgrades, pre-push guardrail, and installers.
- Deliberately deferred to the publication plan: Git bundles as release assets, GitHub API operations, confirmation, receipts, and anchor releases.
- Placeholder scan: the plan contains no unresolved marker, generic error-handling instruction, or unnamed test.
- Type consistency: `Policy`, `GitRepository`, `EvidenceState`, `VerificationReport`, and CLI exit codes are defined once and reused verbatim.
