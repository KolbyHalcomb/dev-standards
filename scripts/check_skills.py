#!/usr/bin/env python3
"""Assert every SKILL.md stays portable across Claude Code, Cursor, and Codex.

The whole reason one plugin directory can serve three clients is that the skills use only the core
Agent Skills frontmatter: `name` and `description`. A client-specific key (`allowed-tools`, `model`,
`context`, `disable-model-invocation`, ...) is read by one client and ignored by the others, so a
skill carrying one is portable in name only -- it behaves differently depending on who loaded it.

This check keeps that guarantee mechanical rather than remembered.

Exits non-zero on a forbidden or missing key, on a name that disagrees with its directory, or on a
vacuous run that discovered no skills at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_KEYS = {"name", "description"}

# Keys that only one client understands. Listed explicitly rather than allow-listing, so the error
# message can say which client the key belongs to.
CLIENT_SPECIFIC_KEYS = {
    "allowed-tools": "Claude Code",
    "context": "Claude Code",
    "disable-model-invocation": "Claude Code",
    "model": "Claude Code",
    "argument-hint": "Claude Code",
    "user-invocable": "Claude Code",
}

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Return top-level frontmatter keys, or None if the file has no frontmatter block."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None

    keys: dict[str, str] = {}
    current: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        # A continuation line of a folded value is indented; only column-0 lines start a key.
        if line[0].isspace():
            if current is not None:
                keys[current] += " " + line.strip()
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        current = key.strip()
        keys[current] = value.strip()
    return keys


def check_skill(skill_md: Path) -> list[str]:
    try:
        rel = skill_md.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        # Off-tree (a test fixture, or an unusual checkout layout) -- report the
        # full path rather than crashing on the cosmetic part of the message.
        rel = str(skill_md)
    keys = parse_frontmatter(skill_md)
    if keys is None:
        return [f"{rel}: no YAML frontmatter block"]

    failures = []

    for missing in sorted(REQUIRED_KEYS - keys.keys()):
        failures.append(f"{rel}: missing required key {missing!r}")

    for key in sorted(keys.keys() - REQUIRED_KEYS):
        owner = CLIENT_SPECIFIC_KEYS.get(key)
        if owner:
            failures.append(f"{rel}: {key!r} is {owner}-only and breaks portability")
        else:
            failures.append(f"{rel}: unexpected key {key!r} (only name and description are portable)")

    # The directory name is what users type. A frontmatter name that disagrees with it is a
    # silent rename.
    declared = keys.get("name")
    if declared and declared != skill_md.parent.name:
        failures.append(
            f"{rel}: name {declared!r} does not match its directory {skill_md.parent.name!r}"
        )

    if not keys.get("description"):
        failures.append(f"{rel}: description is empty -- it is how a model decides to load the skill")

    return failures


def main() -> int:
    skill_files = sorted(REPO_ROOT.glob("plugins/*/skills/*/SKILL.md"))
    if not skill_files:
        print("ERROR: discovered zero SKILL.md files -- this check inspected nothing.")
        return 1

    failures = []
    for skill_md in skill_files:
        failures.extend(check_skill(skill_md))

    if failures:
        print(f"Portability problems across {len(skill_files)} skill(s):\n")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"OK: {len(skill_files)} skill(s) checked, frontmatter is name + description only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
