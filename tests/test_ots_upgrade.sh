#!/bin/bash
set -euo pipefail

SOURCE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$SOURCE_ROOT/scripts/ots-upgrade.sh"
TEST_ROOT=$(mktemp -d)
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

assert_contains() {
    local haystack=$1
    local needle=$2
    [[ "$haystack" == *"$needle"* ]] || fail "expected output to contain: $needle"
}

cd "$TEST_ROOT"
git init -q
git config user.name "OTS Test"
git config user.email "ots-test@example.invalid"
git config commit.gpgsign false

mkdir -p .venv/bin timestamps
cat > .venv/bin/ots <<'FAKE_OTS'
#!/bin/bash
set -e

if [ "$1" != "upgrade" ]; then
    echo "unsupported fake OTS command: $1" >&2
    exit 2
fi

proof=$2
case "$(cat "$proof")" in
    complete)
        echo "Success! Timestamp complete"
        ;;
    ready)
        cp "$proof" "$proof.bak"
        printf 'complete' > "$proof"
        echo "Success! Timestamp complete"
        ;;
    pending)
        echo "Calendar proof is not ready" >&2
        exit 1
        ;;
    *)
        echo "unexpected proof fixture" >&2
        exit 2
        ;;
esac
FAKE_OTS
chmod +x .venv/bin/ots

# Fixtures: an already-complete proof WITH its bare <hash> target file (the
# backlog-migration case), a calendar-ready proof, and a still-pending one.
printf 'fixture repository\n' > README.md
printf 'complete-target' > timestamps/complete
printf 'complete' > timestamps/complete.ots
printf 'ready' > timestamps/ready.ots
printf 'pending' > timestamps/pending.ots
git add README.md timestamps
git commit -qm "test: initial fixtures"

printf 'must remain outside the OTS commit\n' > unrelated.txt
git add unrelated.txt

output=$(bash "$SCRIPT")

assert_contains "$output" "already complete: timestamps/complete.ots"
assert_contains "$output" "upgraded: timestamps/ready.ots"
assert_contains "$output" "pending:  timestamps/pending.ots"

subject=$(git log -1 --format=%s)
[ "$subject" = "ots: upgrade 1 timestamp(s), 2 anchored" ] || \
    fail "unexpected commit subject: $subject"

# The commit carries exactly: the moves of both completed triples (old paths
# as deletions, new paths as additions) and the freshly created .bak.
changed=$(git diff-tree --no-commit-id --name-only -r HEAD | sort)
expected=$(printf '%s\n' \
    timestamps/anchored/complete \
    timestamps/anchored/complete.ots \
    timestamps/anchored/ready.ots \
    timestamps/anchored/ready.ots.bak \
    timestamps/complete \
    timestamps/complete.ots \
    timestamps/ready.ots | sort)
[ "$changed" = "$expected" ] || \
    fail "unexpected paths in upgrade commit: $changed"

# Directory state: only the pending proof remains scannable; anchored
# triples moved wholesale.
remaining=$(find timestamps -maxdepth 1 -type f | sort)
[ "$remaining" = "timestamps/pending.ots" ] || \
    fail "unexpected files left in timestamps/: $remaining"
[ -f timestamps/anchored/complete ] || fail "bare target file did not move"
[ -f timestamps/anchored/ready.ots.bak ] || fail ".bak did not move"

staged=$(git diff --cached --name-only)
[ "$staged" = "unrelated.txt" ] || \
    fail "unrelated staged content was not preserved: $staged"

head_before=$(git rev-parse HEAD)
second_output=$(bash "$SCRIPT")
head_after=$(git rev-parse HEAD)

[ "$head_before" = "$head_after" ] || \
    fail "a no-change run created a commit"
assert_contains "$second_output" "No timestamps ready to upgrade yet."
assert_contains "$second_output" "pending:  timestamps/pending.ots"

echo "PASS: OTS upgrade accounting, anchoring moves, and commit isolation"
