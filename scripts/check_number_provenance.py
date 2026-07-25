#!/usr/bin/env python3
"""Report numeric claims in a draft that carry no entry in the provenance registry.

Provenance is lost at citation boundaries, not at creation: a number is computed
with a trace in the section that earns it, then quoted into a later section as
support, and the quotation drops the trace. This script makes that loss loud
instead of silent.

It deliberately does NOT verify anything. A registry entry proves a number was
written down, not that anyone opened the artifact — see the `status` field, and
prefer `recorded-not-rederived` over `verified` unless you re-derived it blind.

Usage:
    python scripts/check_number_provenance.py [draft.md ...]

Exit status is 1 if any unregistered numeric claim is found, so this can gate a
release build. The draft itself is gitignored, so this is a pre-submission check
rather than a commit hook.
"""

import json
import pathlib
import re
import sys

REGISTRY = pathlib.Path(__file__).resolve().parent.parent / "docs" / "number-provenance.json"
DEFAULT_DRAFTS = ["docs/drafts/2026-07-15-arxiv-draft.md"]

# Percentages, ratios, and multipliers — the forms this paper actually asserts in.
# Bare integers are excluded: section numbers, years and question indices would
# swamp the signal, and this project's empirical claims are not stated as bare
# integers.
CLAIM_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:%|×|:1\b)")

# Lines that quote a source's own numbers, or that are the registry's own
# bookkeeping, are not our claims to provenance.
SKIP_LINE = re.compile(r"(arxiv|doi|nature|ACM ToS|\.txt:|Draft note:)", re.IGNORECASE)


def load_registered() -> set[str]:
    with REGISTRY.open() as fh:
        data = json.load(fh)
    return {c["literal"] for c in data["claims"]}


def scan(path: pathlib.Path, registered: set[str]) -> list[tuple[int, str, str]]:
    findings = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if SKIP_LINE.search(line):
            continue
        for literal in CLAIM_PATTERN.findall(line):
            if literal not in registered:
                findings.append((lineno, literal, line.strip()[:90]))
    return findings


def main(argv: list[str]) -> int:
    drafts = argv[1:] or DEFAULT_DRAFTS
    registered = load_registered()
    total = 0

    for name in drafts:
        path = pathlib.Path(name)
        if not path.exists():
            print(f"skip (absent): {name}")
            continue
        findings = scan(path, registered)
        total += len(findings)
        print(f"\n{name}: {len(findings)} unregistered numeric claim(s)")
        for lineno, literal, context in findings:
            print(f"  L{lineno}: {literal}  |  {context}")

    print(f"\n{len(registered)} literal(s) registered; {total} unregistered.")
    if total:
        print("Unregistered numbers are not necessarily wrong — they are untraceable.")
        print("Add each to docs/number-provenance.json with its artifact, or delete it.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
