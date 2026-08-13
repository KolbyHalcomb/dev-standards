#!/usr/bin/env python3
"""
CHANGELOG-discipline gate.

Fails if a tracked living-reference doc changed without a corresponding
CHANGELOG entry in the same diff. This originally lived as inline Bash inside a
CI workflow, where it could only be exercised by opening a real PR; the logic
lives here so it can be unit-tested.

Usage:
    check_changelog.py <base-sha> <head-sha> [--root PATH]

Configuration (both required -- there is no sensible cross-repo default):
    $TRACKED_DOCS      docs whose change demands a CHANGELOG entry
    $CHANGELOG_FILES   any one of these satisfies the requirement

Both accept a whitespace- or comma-separated list, so a multi-line YAML block
scalar works. Keep $TRACKED_DOCS aligned with the living-reference and
living-runbook groups of the consuming repo's file index. A repo's own brain
file is usually NOT tracked: its churn is meta, not an as-built change.

Compares the two commits with `git diff --name-only` and evaluates the result.
The pure decision lives in evaluate() so tests never need a real diff.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

import docfiles


def evaluate(changed_files, tracked: frozenset[str], changelogs: frozenset[str]) -> tuple[bool, str]:
    """Return (ok, message) for the given set of changed file paths."""
    changed = set(changed_files)
    tracked_changed = sorted(tracked & changed)

    if not tracked_changed:
        return True, "OK: No tracked doc files changed -- CHANGELOG not required"

    if changed & changelogs:
        return True, "OK: CHANGELOG updated alongside: " + " ".join(tracked_changed)

    lines = ["ERROR: These files changed without a CHANGELOG entry:"]
    lines += [f"  - {doc}" for doc in tracked_changed]
    lines += ["", "Add a dated entry describing what changed in the real world."]
    lines += ["Any of these satisfies the gate: " + ", ".join(sorted(changelogs))]
    return False, "\n".join(lines)


def changed_files(base: str, head: str, root) -> list:
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=root, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', help='base commit SHA')
    parser.add_argument('head', help='head commit SHA')
    parser.add_argument('--root', help='repo root (default: $DOCS_ROOT, then cwd)')
    args = parser.parse_args(argv)

    root = docfiles.resolve_root(args.root)
    tracked = docfiles.env_set('TRACKED_DOCS')
    changelogs = docfiles.env_set('CHANGELOG_FILES')

    # An unconfigured run would find nothing tracked and pass every PR -- the
    # vacuous pass this whole suite is written to refuse.
    if not tracked:
        print("ERROR: $TRACKED_DOCS is empty. With nothing tracked this gate "
              "passes every PR, which is worse than not running it.")
        return 1
    if not changelogs:
        print("ERROR: $CHANGELOG_FILES is empty. Nothing could satisfy this "
              "gate, so every PR touching a tracked doc would fail.")
        return 1

    ok, message = evaluate(changed_files(args.base, args.head, root), tracked, changelogs)
    print(message)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
