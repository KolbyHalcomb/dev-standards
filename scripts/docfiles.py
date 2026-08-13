#!/usr/bin/env python3
"""
Shared markdown-file discovery for the docs-CI checkers.

Every checker that walks a doc tree needs the same two things, and both were
originally copy-pasted per checker -- so both were wrong in the same silent way
in check_links.py and check_tbd.py at once. The walk lives here once instead.

1. Skip vendored agent-skill trees, matching each file's path *relative to the
   docs root*. Testing absolute `Path.parts` breaks whenever the repo itself
   sits beneath a directory named in SKIP_DIRS -- a repo that creates git
   worktrees under `.claude/worktrees/<name>/` matched `.claude` on every single
   file from inside one and discovered zero of them.

2. Refuse to report success on an empty walk. A doc checker that finds no files
   is a broken checker, not a clean bill of health. Callers pair find_md_files()
   with vacuous_pass_error() and exit non-zero.

Reusable across repos: the docs root comes from --root, then $DOCS_ROOT, then
the working directory -- never from this file's own location, because in a
reusable workflow these scripts are checked out somewhere other than the repo
being checked.
"""

from __future__ import annotations

import os
from pathlib import Path

# Vendored agent-skill trees installed by `npx skills` (.agents / .claude), git
# internals, exported LLM context bundles, caches, and dependency directories.
# pytest's cache ships its own README.md, so a local `pytest` run followed by a
# checker run used to inventory a vendored file as if it were an authored doc.
SKIP_DIRS = frozenset({
    '.git',
    '.llm-context',
    '.agents',
    '.claude',
    '.cursor',
    '.codex',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    '.venv',
    'node_modules',
    'site-packages',
})


def resolve_root(cli_root: str | None = None) -> Path:
    """Resolve the docs root: --root, then $DOCS_ROOT, then the working directory.

    Deliberately not derived from __file__. Under a reusable workflow this file
    lives in the standards checkout while the docs being checked live in the
    caller's checkout, so a path relative to this script would check the wrong
    tree -- and would very likely find zero files and look like a pass.
    """
    return Path(cli_root or os.environ.get('DOCS_ROOT') or '.').resolve()


def env_set(name: str, default: frozenset[str] = frozenset()) -> frozenset[str]:
    """Read a whitespace- or comma-separated list from the environment.

    Workflow inputs arrive as strings; a multi-line YAML block scalar and a
    space-separated one both work.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    items = {item.strip() for chunk in raw.split(',') for item in chunk.split()}
    return frozenset(item for item in items if item)


def find_md_files(root, skip_dirs=SKIP_DIRS, skip_files=frozenset()) -> list:
    """Return the sorted .md files under `root`, minus skipped dirs and names.

    `skip_dirs` is matched against each file's path *relative to* `root`, so a
    checkout living beneath a directory of the same name is unaffected.
    `skip_files` is matched against the bare filename.
    """
    root = Path(root)
    found = []
    for f in root.rglob('*.md'):
        if f.name in skip_files:
            continue
        try:
            relative_parts = f.relative_to(root).parts
        except ValueError:
            # rglob only yields descendants, so this is unreachable in practice.
            # Skip rather than crash if a symlink ever escapes the tree.
            continue
        if skip_dirs.intersection(relative_parts):
            continue
        found.append(f)
    return sorted(found)


def vacuous_pass_error(root) -> str:
    """The message for a walk that discovered nothing -- always a bug, never a pass."""
    return (
        f"ERROR: no .md files found under {root}\n"
        "A doc checker that finds zero files is broken, not passing. Check that "
        "the docs root resolved correctly (--root / $DOCS_ROOT) and that "
        "SKIP_DIRS is not matching every path."
    )
