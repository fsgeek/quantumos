# Cross-Platform OTS Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the evidence core into a recoverable Windows/WSL and native-Linux commit workflow with tracked hooks, repair, upgrades, and a pre-push guardrail.

**Architecture:** The tracked hooks are tiny POSIX launchers used by Git for Windows and native Git. Python workflow code owns discovery and state transitions; one OTS adapter selects WSL `uvx` on Windows or `.venv/bin/ots` on Linux. Post-commit attempts evidence creation, repair completes interrupted work, and pre-push performs read-only validation without claiming to be an enforcement authority.

**Tech Stack:** Python 3.14+ stdlib, PowerShell 7/Windows PowerShell 5.1-compatible wrappers, POSIX shell, Git 2.45+, `uv` 0.11+, Ubuntu WSL `uvx`, OpenTimestamps client 0.7.2, GnuPG, pytest.

## Global Constraints

- Requires the completed `2026-07-18-ots-evidence-core.md` plan and its passing suite.
- Hooks are enabling guardrails: intentional bypass remains possible and is reported honestly.
- Windows Git alone creates refs, stages, signs, commits, and pushes; WSL never runs Git or GPG.
- `post-commit` never deletes or rewrites the substantive commit and cannot make Git undo it.
- `pre-push` never mutates history, invokes OTS, repairs evidence, or contacts the remote itself.
- Valid `PENDING` and `BITCOIN_ANCHORED` evidence are push-eligible; missing, malformed, or invalid evidence is not.
- Hooks stage only `timestamps/<hash>.json` and `.json.ots`; upgrades stage only changed recognized `.ots` files.
- Existing `.git/hooks` files are untouched; installation changes only repository-local `core.hooksPath` after preflight.
- All generated commits use `git commit -S`; recursion is controlled by `QUANTUMOS_OTS_REENTRY=1`, never by subject alone.

---

## File Structure

- Create `tools/provenance/ots_adapter.py` — WSL/native discovery, path mapping, stamp/info/upgrade.
- Create `tools/provenance/workflow.py` — post-commit attempt, repair, upgrade, and exact staging/signing.
- Create `tools/provenance/push_guard.py` — parse pre-push stdin and validate introduced commits.
- Modify `tools/provenance/cli.py` — workflow commands with stable exit codes.
- Create `.githooks/post-commit` and `.githooks/pre-push` — tracked launchers.
- Create `scripts/install-hooks.ps1`; replace `scripts/install-hooks.sh` — idempotent platform installers.
- Create `scripts/repair-timestamps.ps1` and `.sh` — one recovery command per platform.
- Create `scripts/verify-timestamp.ps1` and `.sh` — verifier wrappers.
- Create `scripts/ots-upgrade.ps1`; replace `scripts/ots-upgrade.sh` — safe signed upgrades.
- Delete `scripts/hooks/post-commit` after tracked hooks are active.
- Create `tests/provenance/test_ots_adapter.py`, `test_workflow.py`, `test_push_guard.py`, `test_installers.py`, and `test_host_integration.py`.

---

### Task 1: OTS adapter with Windows/WSL and native-Linux boundaries

**Files:**
- Create: `tools/provenance/ots_adapter.py`
- Modify: `tools/provenance/cli.py`
- Test: `tests/provenance/test_ots_adapter.py`

**Interfaces:**
- Produces `OtsAdapter.discover(repo, runner, platform) -> OtsAdapter`, `stamp(path)`, `info(path)`, and `upgrade(path)`.
- Windows command prefix is `wsl.exe -d <discovered-distribution> -- <discovered-uvx> --from opentimestamps-client==0.7.2 ots`.
- Linux command prefix is `<repo>/.venv/bin/ots`; its `--version` output must identify 0.7.2.
- Windows path mapping uses `wsl.exe -d DISTRO -- wslpath -a <absolute-windows-path>` and validates the result begins with `/mnt/` or another absolute mount returned by WSL; usernames and drive letters are never hardcoded.

- [ ] **Step 1: Write failing discovery, mapping, and failure-boundary tests**

```python
def test_windows_stamp_passes_only_mapped_manifest(fake_runner, repo):
    adapter = OtsAdapter.discover(repo, fake_runner, platform="win32")
    adapter.stamp(repo / "timestamps" / f"{H}.json")
    assert fake_runner.last.argv[-2:] == ["stamp", f"/mnt/c/repo/timestamps/{H}.json"]
    assert all("git" not in arg.lower() for arg in fake_runner.last.argv)


@pytest.mark.parametrize("boundary", [
    "wsl-list", "uvx-discovery", "wslpath", "ots-startup", "calendar-submit",
])
def test_failure_names_exact_boundary(boundary, configured_failure):
    with pytest.raises(OtsBoundaryError, match=boundary):
        configured_failure.discover_or_stamp()
```

- [ ] **Step 2: Run and observe missing adapter failure**

Run: `uv run pytest tests/provenance/test_ots_adapter.py -v`

Expected: import fails for `tools.provenance.ots_adapter`.

- [ ] **Step 3: Implement deterministic discovery and commands**

Use `wsl.exe --list --quiet`, discard blank and NUL characters, prefer the current default distribution when it passes preflight, otherwise select the first passing distribution in returned order. Discover `uvx` with `sh -lc 'command -v uvx'` only inside WSL; never interpolate the repository path into shell source. Pass the mapped artifact as a separate argv item. `stamp` succeeds only when the expected sibling `.ots` exists and binds to the source according to `ots info`.

- [ ] **Step 4: Run focused tests and read-only host preflight**

Run: `uv run pytest tests/provenance/test_ots_adapter.py -v`

Run: `uv run python -m tools.provenance.cli ots-preflight --json`

Expected on this host: Windows adapter, Ubuntu distribution, `/home/tony/.local/bin/uvx`, client 0.7.2, and no repository mutation.

- [ ] **Step 5: Commit and let the explicit schema-v2 command create its evidence pair**

Commit message: `provenance: add bounded Windows WSL OTS adapter`. Until hooks are installed, use the explicit evidence sequence from the evidence-core plan.

---

### Task 2: Stamp, repair, and upgrade workflows

**Files:**
- Create: `tools/provenance/workflow.py`
- Modify: `tools/provenance/cli.py`
- Create: `scripts/repair-timestamps.ps1`
- Create: `scripts/repair-timestamps.sh`
- Create: `scripts/ots-upgrade.ps1`
- Modify: `scripts/ots-upgrade.sh`
- Test: `tests/provenance/test_workflow.py`

**Interfaces:**
- Produces `stamp_head(repo, adapter, signer) -> WorkflowReport`, `repair(repo, upstream, adapter, signer) -> list[WorkflowReport]`, and `upgrade_all(repo, adapter, signer) -> UpgradeReport`.
- CLI commands: `post-commit`, `repair [--upstream REF]`, and `upgrade`.
- `stamp_head` creates the preservation ref first, creates and self-verifies the manifest, stamps it, stages exactly two paths, and runs `git -c commit.gpgsign=true commit -S -m "ots: stamp <hash>"` with `QUANTUMOS_OTS_REENTRY=1`.

- [ ] **Step 1: Write failing lifecycle and interruption tests**

```python
def test_stamp_creates_ref_manifest_proof_and_one_signed_commit(workflow_repo):
    report = workflow_repo.stamp_head()
    assert report.target == workflow_repo.substantive_oid
    assert workflow_repo.ref(report.target) == report.target
    assert workflow_repo.changed_paths(report.evidence_commit) == {
        f"timestamps/{report.target}.json",
        f"timestamps/{report.target}.json.ots",
    }
    assert workflow_repo.signature_is_good(report.evidence_commit)


@pytest.mark.parametrize("boundary", ["manifest", "ots", "stage", "sign"])
def test_failure_preserves_commit_ref_and_partial_artifacts(boundary, interrupted_workflow):
    result = interrupted_workflow.fail_at(boundary)
    assert interrupted_workflow.substantive_commit_exists()
    assert interrupted_workflow.preservation_ref_exists()
    assert result.message.startswith("EVIDENCE INCOMPLETE")
    interrupted_workflow.repair()
    assert interrupted_workflow.verify().state in {EvidenceState.PENDING,
                                                    EvidenceState.BITCOIN_ANCHORED}
```

- [ ] **Step 2: Run and observe missing workflow failure**

Run: `uv run pytest tests/provenance/test_workflow.py -v`

Expected: import fails for `tools.provenance.workflow`.

- [ ] **Step 3: Implement idempotent state transitions**

Before every write, inspect Git and filesystem state. Existing valid manifests/proofs are reused; mismatched existing artifacts cause `INVALID` and are never overwritten. Repair walks `git rev-list --reverse <upstream>..HEAD`, excludes only structurally valid maintenance commits and exact exemptions, and finishes one target at a time. Upgrade hashes each proof before and after `ots upgrade`, stages only byte-changed recognized proofs, and creates no commit when the count is zero. Every generated commit sets the re-entry variable and explicitly signs.

The PowerShell wrappers are exactly:

```powershell
$ErrorActionPreference = 'Stop'
$root = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Set-Location -LiteralPath $root
uv run python -m tools.provenance.cli repair @args
exit $LASTEXITCODE
```

The shell wrappers use `set -eu`, resolve `git rev-parse --show-toplevel`, `cd` there, and `exec uv run python -m tools.provenance.cli <command> "$@"`.

- [ ] **Step 4: Run workflow tests including aggressive garbage collection**

Run: `uv run pytest tests/provenance/test_workflow.py -v`

Expected: all tests pass, including amend/rebase preimages remaining reachable after `git reflog expire --expire=now --all` and `git gc --prune=now`.

- [ ] **Step 5: Commit and explicitly create its schema-v2 evidence pair**

Commit message: `provenance: add recoverable stamp and upgrade workflows`.

---

### Task 3: Tracked post-commit hook and read-only pre-push guardrail

**Files:**
- Create: `.githooks/post-commit`
- Create: `.githooks/pre-push`
- Create: `tools/provenance/push_guard.py`
- Modify: `tools/provenance/cli.py`
- Test: `tests/provenance/test_hooks.py`
- Test: `tests/provenance/test_push_guard.py`

**Interfaces:**
- `post-commit` exits immediately when `QUANTUMOS_OTS_REENTRY=1`; otherwise it invokes `uv run python -m tools.provenance.cli post-commit` and preserves its diagnostic exit.
- `pre-push` forwards remote name, remote URL, and stdin bytes to CLI `pre-push`.
- `validate_updates(repo, updates, remote) -> PushReport` uses each `<local-sha> <remote-sha>` pair to enumerate newly introduced commits and accepts only valid pending/anchored evidence, structural maintenance, or exact exemptions.

- [ ] **Step 1: Write failing recursion and push-range tests**

```python
def test_reentry_makes_post_commit_noop(hook_repo):
    result = hook_repo.run_post_commit(env={"QUANTUMOS_OTS_REENTRY": "1"})
    assert result.returncode == 0
    assert hook_repo.commit_count_unchanged()


def test_missing_evidence_blocks_before_remote_contact(push_repo):
    result = push_repo.run_pre_push(new_branch_update())
    assert result.returncode != 0
    assert "no remote update occurred" in result.stderr
    assert push_repo.remote_receive_count == 0


def test_valid_pending_evidence_is_eligible(push_repo):
    push_repo.add_pending_evidence()
    assert push_repo.run_pre_push(new_branch_update()).returncode == 0
```

- [ ] **Step 2: Run and observe missing hook/guard failures**

Run: `uv run pytest tests/provenance/test_hooks.py tests/provenance/test_push_guard.py -v`

Expected: tests fail because `.githooks` and `push_guard` do not exist.

- [ ] **Step 3: Implement launchers and read-only range validation**

Parse pre-push lines as four fields; all-zero local OID is deletion and needs no work. For a new remote ref use `git rev-list <local-sha> --not --remotes=<remote>`; for update use `git rev-list <remote-sha>..<local-sha>`. Deduplicate commits across updates. Never run a shell command, OTS, `git add`, `git commit`, or `git update-ref` from validation. Print every affected hash/subject/reason and the single platform-specific repair command.

- [ ] **Step 4: Run tests with a fake receive endpoint**

Run: `uv run pytest tests/provenance/test_hooks.py tests/provenance/test_push_guard.py -v`

Expected: all pass; missing evidence prevents the fake endpoint from receiving an update, and deletion updates pass unchanged.

- [ ] **Step 5: Commit and explicitly create its schema-v2 evidence pair**

Commit message: `provenance: add tracked commit and push guardrails`.

---

### Task 4: Idempotent Windows and Linux installers

**Files:**
- Create: `scripts/install-hooks.ps1`
- Modify: `scripts/install-hooks.sh`
- Delete: `scripts/hooks/post-commit`
- Test: `tests/provenance/test_installers.py`

**Interfaces:**
- Installers perform all read-only preflight before `git config --local core.hooksPath .githooks`.
- Existing effective `core.hooksPath` values other than `.githooks` are reported as conflicts and never overwritten.
- Windows preflight checks repository identity, Git/GPG configuration, exact configured signing fingerprint, `uv`, WSL distribution, `uvx`, OTS 0.7.2, path mapping, executable hook files, policy audit, and verifier startup.
- Linux preflight performs the corresponding native `.venv/bin/ots` checks.

- [ ] **Step 1: Write failing idempotence and conflict tests**

```python
def test_installer_changes_only_local_hook_path(clean_clone):
    before_global = clean_clone.git_config_global()
    clean_clone.install_windows()
    assert clean_clone.local_config("core.hooksPath") == ".githooks"
    assert clean_clone.git_config_global() == before_global
    first = clean_clone.snapshot()
    clean_clone.install_windows()
    assert clean_clone.snapshot() == first


def test_unrelated_hook_path_is_a_visible_conflict(clean_clone):
    clean_clone.set_local_hook_path("company-hooks")
    result = clean_clone.install_windows()
    assert result.returncode != 0
    assert clean_clone.local_config("core.hooksPath") == "company-hooks"
```

- [ ] **Step 2: Run and observe installer test failure**

Run: `uv run pytest tests/provenance/test_installers.py -v`

Expected: fail because the Windows installer does not exist and the Linux installer has overwrite behavior.

- [ ] **Step 3: Implement transactional preflight then one config write**

PowerShell must use `Resolve-Path -LiteralPath`, argv arrays, `$LASTEXITCODE` checks, and no global configuration writes. Shell must use quoted variables and `git config --local`. Neither installer installs packages implicitly. Remove the obsolete `scripts/hooks/post-commit` only in the same commit that adds `.githooks/post-commit`.

- [ ] **Step 4: Run installer tests and a disposable host integration install**

Run: `uv run pytest tests/provenance/test_installers.py -v`

Run: `pwsh -NoProfile -File scripts/install-hooks.ps1 -WhatIf`

Expected: tests pass; `-WhatIf` reports every preflight and the single proposed local config change without mutating the live repository.

- [ ] **Step 5: Install hooks in the live repository, commit, and verify automatic evidence**

Run: `pwsh -NoProfile -File scripts/install-hooks.ps1`

Then commit with message `provenance: install cross-platform tracked hooks`. This substantive commit is the first acceptance of the automatic lifecycle: its `post-commit` must create exactly one signed evidence commit, and `git status --short` must be empty afterward.

---

### Task 5: Host integration, contributor documentation, and acceptance

**Files:**
- Create: `tests/provenance/test_host_integration.py`
- Modify: `docs/provenance.md`
- Modify: `README.md`

**Interfaces:**
- Host tests are opt-in with `QUANTUMOS_HOST_INTEGRATION=1`; ordinary tests never submit QuantumOS content, create a live release, or alter global Git configuration.
- Disposable fixture verifies real WSL stamping, Windows GPG signing, complete two-commit lifecycle, interruption/repair, pre-push block before remote contact, and native Linux path when available.

- [ ] **Step 1: Add the opt-in acceptance test and confirm it skips by default**

```python
@pytest.mark.skipif(os.environ.get("QUANTUMOS_HOST_INTEGRATION") != "1",
                    reason="explicit host integration opt-in required")
def test_real_windows_wsl_two_commit_lifecycle(host_fixture):
    substantive, evidence = host_fixture.commit_one_file()
    assert host_fixture.good_signature(substantive)
    assert host_fixture.good_signature(evidence)
    assert host_fixture.verify(substantive).state is EvidenceState.PENDING
    assert host_fixture.status_porcelain() == ""
```

- [ ] **Step 2: Run the default suite**

Run: `uv run pytest tests/provenance -v`

Expected: all deterministic tests pass and host tests skip with the exact opt-in reason.

- [ ] **Step 3: Run the real disposable-host suite**

Run: `$env:QUANTUMOS_HOST_INTEGRATION='1'; uv run pytest tests/provenance/test_host_integration.py -v`

Expected: all host tests pass; only disposable repositories and disposable manifests contact OTS calendars.

- [ ] **Step 4: Document the four normal commands and enabling posture**

Contributor quick start must be exactly:

```text
Install once.
Commit normally.
If evidence creation was interrupted, run scripts/repair-timestamps.ps1.
PENDING is push-eligible but is not Bitcoin-anchored.
```

Maintenance documentation explains Linux equivalents, upgrade, independent verify, key rotation, policy activation, intentional bypass limitation, and how to uninstall by removing only local `core.hooksPath` after showing its current value.

- [ ] **Step 5: Run the full suite and commit under the installed hooks**

Run: `uv run pytest`

Commit message: `docs: document recoverable OTS contribution workflow`.

Expected: full suite passes; the installed hook creates exactly one signed evidence commit; working tree is clean.

---

## Self-Review

- Spec coverage: WSL/native adapters, recovery, upgrades, exact staging, recursion, structural pre-push validation, idempotent installers, hook-path conflict, garbage-collection survival, and host acceptance are covered.
- Enabling posture: the plan calls pre-push a local guardrail, tests bypass as technically possible, and makes no remote-governance claim.
- External publication remains absent; no hook or installer calls GitHub.
- Placeholder scan: no generic error-handling step, unnamed failure, or deferred implementation appears.
- Interface consistency: all workflows consume the evidence-core `Policy`, `GitRepository`, `VerificationReport`, and exit states without renaming them.
