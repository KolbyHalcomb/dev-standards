#!/usr/bin/env python3
"""
TBD placeholder inventory.

Reports all unresolved TBD values so you can see what is still unknown or
in-progress in the docs.

Findings are informational -- any number of unresolved TBDs still exits 0.
The one non-zero exit is a broken walk (zero .md files discovered), because
"OK: No TBD placeholders found" is a false statement when the inventory never
looked at anything.

Usage:
    check_tbd.py [--root PATH]

Configuration:
    $DOCS_ROOT       docs root, if --root is not given
    $TBD_SKIP_FILES  filenames to exclude (default: instruction files and changelogs)
    $EXTRA_SKIP_DIRS additional directory names to skip
"""

from __future__ import annotations

import argparse
import re
import sys

import docfiles

TBD_RE = re.compile(r'\bTBD\b')

# Skip files that aren't current state: agent instruction files, and changelogs
# (which mention past TBDs as historical record, not as current unknowns).
DEFAULT_SKIP_FILES = frozenset({
    'AGENTS.md',
    'CLAUDE.md',
    'README.md',
    'CHANGELOG.md',
})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', help='docs root (default: $DOCS_ROOT, then cwd)')
    args = parser.parse_args()
    root = docfiles.resolve_root(args.root)

    skip_files = docfiles.env_set('TBD_SKIP_FILES', DEFAULT_SKIP_FILES)
    skip_dirs = docfiles.SKIP_DIRS | docfiles.env_set('EXTRA_SKIP_DIRS')

    findings = []

    # Shared discovery: skips the vendored agent-skill trees by *relative* path,
    # so a run from a git worktree under .claude/ still sees the whole tree.
    md_files = docfiles.find_md_files(root, skip_dirs=skip_dirs, skip_files=skip_files)

    if not md_files:
        print(docfiles.vacuous_pass_error(root))
        return 1

    for f in md_files:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if TBD_RE.search(line):
                findings.append((str(f.relative_to(root)), i, line.strip()))

    if findings:
        print(f"TBD PLACEHOLDERS ({len(findings)} unresolved):\n")
        current_file = None
        for filepath, lineno, line in findings:
            if filepath != current_file:
                print(f"  {filepath}")
                current_file = filepath
            print(f"    line {lineno:>3}: {line}")
        print()
        print("Fill these in as values are confirmed. Not a CI failure.")
    else:
        print(f"OK: No TBD placeholders found ({len(md_files)} files checked)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
